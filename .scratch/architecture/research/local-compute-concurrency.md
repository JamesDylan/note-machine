# Research: local compute concurrency (Ollama, faster-whisper, sounddevice, Python process model)

Label: wayfinder:research
Question ticket: module seams & process model — what are the real concurrency limits on this Mac?
Researched: 2026-09-14/15. Read-only inspection; no models loaded, no benchmarks run.

## Answer (short)

- **The LLM is strictly serial for this model.** Ollama 0.24.0 forces `numParallel = 1` for the `qwen35` architecture no matter what `OLLAMA_NUM_PARALLEL` says. Requests to `qwen3.5:4b` run one at a time, in FIFO order (queue up to 512, then HTTP 503). Merge, editorial, query and a future coach all share that one line. Setting `OLLAMA_NUM_PARALLEL` cannot fix this. The only ways to get two LLM calls at once are a *second model* (Ollama loads it alongside if memory fits, up to 3 per GPU), or doing fewer or shorter calls.
- **Transcription is not blocked by the GIL.** CTranslate2 releases the GIL in all compute methods, and HTTP to Ollama is socket I/O, which also releases it. One Python process with a few threads and `queue.Queue` hand-offs gives real parallelism between transcribe and LLM wait. The GIL is not the bottleneck, so multiprocessing and asyncio buy nothing here.
- **The real problem today is coupling, not compute.** Because transcription waits on the merge and the editorial pass, a slow LLM call delays the next transcription. The next chunk also comes back bigger. Separating a *transcriber thread* from a *single-writer engine thread* stops that. Audio and the raw log keep flowing, and only note updates fall behind (merges can batch queued chunks to catch up).
- **Metal whisper is optional, not required.** Moving Whisper to the GPU would compete with Ollama for that same GPU. whisper.cpp's Core ML encoder runs on the ANE and avoids that, but needs source builds. Keep faster-whisper on CPU, and put the transcriber behind a seam so it can be swapped later.
- **Two bugs found along the way.** (1) `answer_query` sends no `num_ctx`, while the merge and editorial calls send 16384. Ollama reloads the runner when options differ, so a wake-phrase query probably triggers a model reload each way. (2) No `requests.post` has a `timeout`, so a hung Ollama stalls the loop forever.

## This machine (facts found)

| Fact | Value | How found |
|---|---|---|
| SoC | Apple M5, 4 performance + 6 efficiency cores (10 total) | `sysctl machdep.cpu.brand_string hw.perflevel0/1.physicalcpu hw.ncpu` |
| Unified memory | 24 GiB (25,769,803,776 B) | `sysctl hw.memsize` |
| GPU wired limit override | none (`iogpu.wired_limit_mb: 0` = OS default) | `sysctl iogpu.wired_limit_mb` |
| macOS | 26.6.2 (25G83) | `sw_vers` |
| Ollama | 0.24.0, Homebrew `ollama serve` (not the .app) | `ollama --version`, `/api/version`, `ps` |
| Ollama env overrides | none set (`launchctl getenv` empty for NUM_PARALLEL / MAX_LOADED_MODELS / KEEP_ALIVE) | `launchctl getenv` |
| Models on disk | qwen3.5:4b (3.4 GB), qwen2.5-coder:14b, phi4, qwen2.5:14b (~9 GB each) | `ollama list` |
| qwen3.5:4b architecture | `qwen35`, 4.7B params, Q4_K_M. Hybrid: 32 blocks, full attention every 4th block (8 attention layers, 4 KV heads, key/value length 256), the other 24 are SSM / linear-attention blocks (state_size 128, inner_size 4096) | `ollama show -v`, `/api/show` `head_count_kv` array |
| Python | 3.14.5, standard GIL build (`Py_GIL_DISABLED=0`), switch interval 0.005 s | venv python |
| faster-whisper / ctranslate2 / sounddevice | 1.2.1 / 4.8.2 / 0.5.6 | `pip show` |
| CTranslate2 CPU backend | linked against `Accelerate.framework`; CPU compute types `int8`, `int8_float32`, `float32`; no GPU device | `otool -L libctranslate2.4.8.2.dylib`, `get_supported_compute_types('cpu')` |

What the current code does, from `live_notes.py`:
- `WhisperModel("small.en", device="cpu", compute_type="int8")` with no `cpu_threads` or `num_workers`, so it gets the defaults: 4 intra-op threads, 1 worker.
- The merge (line ~620) and editorial (line ~819) calls send `options: {temperature: 0, num_ctx: 16384}`. `answer_query` (line ~1060) sends **no options**. No call passes `keep_alive` or `timeout`.
- The audio callback does `buffer.append(indata.copy())`. The main thread does `np.concatenate(buffer)` and then `buffer.clear()` as two separate steps. A callback that runs between them gets its block cleared without being transcribed, so a small amount of audio is lost now and then. This is inferred from the code, not observed.

## Ollama

**Parallel slots.** `OLLAMA_NUM_PARALLEL` defaults to 1 and `OLLAMA_MAX_QUEUE` to 512 ([envconfig v0.24.0 / main][envcfg]). The scheduler reads `numParallel := max(int(envconfig.NumParallel()), 1)`. It then **forces it to 1** for `mllama, qwen3vl, qwen3vlmoe, qwen35, qwen35moe, qwen3next, lfm2, lfm2moe, nemotron_h, nemotron_h_moe, nemotron_h_omni`, logging "model architecture does not currently support parallel requests" ([sched.go v0.24.0][sched024]; still present on [main][schedmain]). *Version-dependent:* this list will change as the hybrid/SSM runners gain batching. For `qwen3.5:4b` today, every call runs one after another.

**Queueing.** Pending requests go into a buffered channel sized `OLLAMA_MAX_QUEUE`. When it is full, the request fails with `ErrMaxQueue` ("server busy…"), which the FAQ says comes back as a 503 ([sched.go][sched024], [FAQ][faq]). The FAQ says queued requests "will be processed in order" ([FAQ][faq]). There is no priority, so a coach or editorial call queued ahead of a merge delays that merge.

**Memory cost of parallel slots.** The FAQ says parallelism "results in increasing the context size by the number of parallel requests", with memory scaling as `OLLAMA_NUM_PARALLEL * OLLAMA_CONTEXT_LENGTH` ([FAQ][faq]). In code, `effectiveModelContext(numCtx, f) * max(numParallel, 1)` ([sched.go main][schedmain]). Rough numbers for qwen3.5:4b at 16k, estimated from the model metadata above, not measured:
- KV cache (f16): 2 × 8 attention layers × 4 KV heads × 256 × 2 bytes ≈ 32 KiB/token → **~512 MiB at 16,384 tokens per slot**.
- SSM recurrent state: roughly 24 layers × 32 × 128 × 128 × 4 bytes ≈ **~50 MiB per slot**. It does not grow with context.
- Weights: ~3.4 GB.

So roughly 4–4.5 GB resident, plus compute buffers. Extra slots would cost ~0.55 GB each, but the parallel limit above makes that moot for this model. `OLLAMA_KV_CACHE_TYPE` (`f16` default, `q8_0`, `q4_0`) and `OLLAMA_FLASH_ATTENTION` can shrink the KV cache ([FAQ][faq], [envconfig][envcfg]).

**Two different models at once.** `OLLAMA_MAX_LOADED_MODELS` defaults to 0, which means `defaultModelsPerGPU (3) × GPU count`, i.e. 3 on this Mac ([sched.go][sched024], [FAQ][faq]). When a request arrives for a model that isn't loaded, the scheduler checks whether "the new one fits" alongside the loaded ones. It loads it in parallel if so, and otherwise evicts the least-recently-used runner ([sched.go v0.24.0][sched024]). Each model gets its own runner process and its own FIFO, so **calls to two different models can run at the same time**. They still share one GPU, so each slows the other while both run. That slowdown is inferred; it wasn't measured. On 24 GB, a second small model (e.g. a ~1–4B model at 3–4 GB plus KV) fits. The 9 GB 14B models together with qwen3.5:4b are likely to force eviction.

**Reloads from option drift.** `needsReload` returns true when runner options differ from the loaded runner's (for non-MLX models) ([sched.go][sched024]). `num_ctx` is one of those options. Every caller of a given model must send **identical `num_ctx`**. Otherwise calls alternate between reloads, and a reload is a multi-second stall that also blocks the queue. The current `answer_query` violates this. The default context when none is sent is itself version-dependent: the FAQ says 4096, while envconfig says "4k/32k/256k based on VRAM" when `OLLAMA_CONTEXT_LENGTH` is unset ([FAQ][faq], [envconfig][envcfg]).

**keep_alive.** Models stay loaded for 5 minutes by default. A per-request `keep_alive` overrides `OLLAMA_KEEP_ALIVE`, and a negative value keeps the model loaded indefinitely ([FAQ][faq], [envconfig][envcfg]). With merges every ~10 s the model never expires mid-meeting. A long silence (over 5 min, where the RMS gate skips the LLM) would cause a cold reload on the next chunk. `keep_alive: -1` or `"30m"` on the merge call avoids that.

**Env vars on macOS.** For the .app, the FAQ says to set them with `launchctl setenv` and restart the app ([FAQ][faq]). This machine runs the Homebrew `ollama serve` instead, so they must be in that service's environment. The env-var route isn't needed for any recommendation here.

**Metal / MLX engine.** Ollama 0.19 (2026-03-30) added an MLX engine preview. The blog requires "a Mac with more than 32GB of unified memory", and the preview targeted Qwen3.5-35B-A3B ([Ollama blog][mlxblog]). This Mac has 24 GB and the model is GGUF Q4_K_M, so it uses the GGML/Metal path. *Version-dependent;* later releases may widen MLX coverage. Either way, Metal GPU time is shared by every model runner, and by any other Metal user such as a Metal whisper.

## Whisper / CTranslate2

**GIL.** CTranslate2 docs: "Parallelization with multiple Python threads is possible because all computation methods release the Python GIL" ([CT2 parallel][ct2par]). One faster-whisper caveat: `transcribe()` returns a **lazy generator**, and "the transcription only starts when you iterate over it" ([faster-whisper README][fwreadme], [transcribe.py][fwtx]). So the thread that *iterates* the segments is the one doing the work. Iterate in the transcriber thread, not the consumer.

**Threads.**
- `cpu_threads` means "Number of threads to use when running on CPU (4 by default). A non zero value overrides the OMP_NUM_THREADS environment variable". It maps to CT2 `intra_threads`.
- `num_workers` maps to `inter_threads`. It only matters "when transcribe() is called from multiple Python threads … at the cost of increased memory usage" ([transcribe.py][fwtx], [CT2 Whisper API][ct2whisper]).

With one transcriber thread, keep `num_workers=1`. The Silero VAD used by `vad_filter=True` runs in onnxruntime with `intra_op_num_threads = 1` and `inter_op_num_threads = 1`, and the model is cached ([vad.py][fwvad]).

**Contention with Ollama.** With qwen3.5:4b fully on Metal, Ollama's CPU use during a call is mostly scheduling and sampling, so whisper's 4 intra-op threads on 4 performance cores and Ollama mostly use different processors. Unified memory bandwidth and thermals are still shared, so expect some mutual slowdown. This is inference, not measured, since no benchmarks were run. A sensible default is to leave `cpu_threads=4` and measure before tuning. `ollama ps` shows whether the model is "100% GPU" ([FAQ][faq]). If it ever shows CPU/GPU split, CPU contention gets much worse.

**Speed reference.** The README's CPU benchmark (Intel i7-12700K, 8 threads, 13 min of audio) gives `small` INT8 1m42s and 1477 MB, and batched INT8 51s and 3608 MB ([faster-whisper README][fwreadme]). That is about 0.13× real time, so a 10 s chunk takes on the order of 1–2 s on similar hardware. The M5 number is unmeasured.

**Streaming / overlapping transcription.**
- Possible, but not cheap on CPU. The reference approach is ÚFAL's whisper_streaming: a "local agreement policy with self-adaptive latency", reported at 3.3 s latency, with faster-whisper and mlx-whisper backends. Its README says it is "becoming outdated in 2025" and is being replaced by SimulStreaming ([whisper_streaming][wstream]).
- SimulStreaming targets Whisper large-v3 on PyTorch with a GPU of at least 10 GB VRAM, so it isn't a fit here ([SimulStreaming][simul]).
- Local agreement re-decodes a growing window every step, which multiplies CPU work by roughly window/step. That competes with Ollama and with the 10 s budget.
- whisper.cpp's `whisper-stream` samples "every half a second" with `--step 500 --length 5000` ([whisper.cpp][wcpp]). It relies on Metal/ANE to afford that.

**Recommendation:** keep non-overlapping chunks. If lower latency is wanted later, cut chunks at VAD pauses instead of every fixed 10 s, which also avoids splitting words. The transcriber seam should emit *finalised text segments*, so a streaming implementation can replace it without touching the engine.

## Audio callback

**Constraints.** "The PortAudio stream callback runs at very high or real-time priority. Do not allocate memory, access the file system, call library functions or call other functions from the stream callback that may block or take an unpredictable amount of time to complete" ([sounddevice streams][sdstreams]; same wording in [PortAudio][pa]). Exceptions raised in the callback are not propagated to the main thread ([sounddevice streams][sdstreams]).

**In practice for Python.**
- sounddevice wraps the callback with `_ffi.callback('PaStreamCallback', error=_lib.paAbort)`, which calls into Python (local `sounddevice.py` 0.5.6, lines ~845 and 2774). The callback therefore has to take the GIL, which only one thread holds at a time ([threading docs][pythreading]). Threads trade the GIL at the switch interval, 0.005 s here ([sys docs][pysys] + local `sys.getswitchinterval()`).
- So the rule is: nothing in the process should hold the GIL for long stretches. CT2 compute and socket I/O release it ([CT2 parallel][ct2par], [C-API threads][pycapi]).
- The project's own example does exactly `q.put(indata.copy())` into a `queue.Queue` ([rec_unlimited.py][sdrec]). That small copy is accepted practice despite the "no allocation" wording.
- **Don't** print large output, write files, run numpy DSP, call RMS/VAD, or touch the notes state inside the callback. The current `print(status)` only fires on errors and is tolerable.

**What happens if the main loop stalls.**
- The callback runs on PortAudio's own thread, independent of the main loop. A stalled consumer does **not** cause a PortAudio overflow. The Python list or queue just grows at 16 kHz × 4 B = 64 KB/s (~3.8 MB/min), which is harmless.
- The cost is latency: the next chunk is longer, takes longer to transcribe, and delays stack up.
- `input_overflow` means "data prior to the first sample of the input buffer was discarded … possibly because the stream callback is using too much CPU time" ([PortAudio][pa]). It occurs only when the *callback itself* can't run in time. In this app that would mean GIL starvation or a system under heavy load.
- Use a `queue.Queue` (or swap the list reference atomically) instead of the current concatenate-then-clear, which can drop blocks.
- With `latency` at its default `'high'` and `blocksize=0`, PortAudio chooses a variable, host-optimal block size ([sounddevice streams][sdstreams]). That is the most forgiving setting for a Python callback, so keep it.

## Python process model options

Where the GIL is and isn't held in this workload:

| Stage | Nature | GIL held? |
|---|---|---|
| Audio callback | tiny Python function on the PortAudio thread | yes, briefly |
| RMS gate, concatenate, text heuristics, markdown render | pure Python / numpy, milliseconds | yes, briefly |
| faster-whisper encode/generate | native CT2 compute, seconds | **released** ([CT2][ct2par]) |
| Silero VAD | onnxruntime, single-threaded, fast | native (short) |
| HTTP to Ollama (merge, editorial, query, coach) | socket wait, seconds | **released** ([C-API][pycapi]) |
| `say` | child process | n/a if run with `Popen` |

**Threads + `queue.Queue` (recommended).** Stdlib only, and the pattern the sounddevice docs use themselves. All the slow stages release the GIL, so threads already give real parallelism where it matters. Queues make the seams explicit: audio blocks → transcriber → transcript events → engine. The downside is shared-state discipline. Fix it with one rule: **only the engine thread mutates notes state and writes files** (this matches the "single writer" contract). Python docs: "threading is still an appropriate model if you want to run multiple I/O-bound tasks simultaneously" ([threading][pythreading]).

**multiprocessing.** Pays off only when *Python-level* CPU work is the bottleneck ([threading][pythreading]), and it isn't here. The costs: macOS uses spawn, so every process re-imports and re-loads models; state crosses by pickling; debugging is harder; and model memory is duplicated if more than one process loads Whisper. Ollama is already a separate process, which is where the heavy compute is isolated. Revisit only if a future stage holds the GIL for long, e.g. a pure-Python diarizer.

**asyncio.** Fits many concurrent network calls or an ASGI web UI. But faster-whisper and `requests` are blocking, so they'd need `asyncio.to_thread` anyway, and asyncio "colours" every function in the call path. That is more abstraction for no throughput gain, because Ollama serialises this model regardless. Acceptable *inside* a UI thread if the chosen web framework is ASGI, while the core stays threaded.

**Free-threaded 3.14.** Not needed, and not installed: the local build has the GIL ([threading][pythreading]).

**Ceiling set by Ollama, not Python.** Because qwen3.5:4b runs one request at a time, putting the editorial pass or coach in their own threads *does not add LLM throughput*. It only changes who waits in Ollama's FIFO. The design lever is **scheduling and batching**: merge several queued chunks in one call, run the editorial/coach only when the merge backlog is empty, and keep prompts short. A **second model** gives true concurrency for commands/coach only if its extra memory (~4 GB for a 4B-class model) and GPU sharing are acceptable.

## Metal alternatives

| Option | Latency / compute | GPU contention with Ollama | Integration & maintenance |
|---|---|---|---|
| **faster-whisper CPU (today)** | ~0.1–0.2× real time for small INT8 on desktop CPUs (README); M5 unmeasured | none; uses CPU (Accelerate) | pip wheel, VAD built in, already tuned with anti-hallucination knobs |
| **mlx-whisper** (Apple ml-explore) | Metal GPU; `pip install mlx-whisper` ([README][mlxw]) | **yes**, shares the GPU with Ollama's Metal runner, so each slows the other while both run (inferred) | `transcribe(audio: str \| np.ndarray \| mx.array, …)` supports `initial_prompt`, `condition_on_previous_text`, `no_speech_threshold`, `hallucination_silence_threshold` ([transcribe.py][mlxtx]), but **no Silero `vad_filter`** (it uses no-speech probability only), so a VAD would need adding. Apple-maintained examples repo. |
| **whisper.cpp via pywhispercpp** | Metal GPU, or Core ML encoder on the **ANE** ("more than x3 faster" than CPU; first run slow while compiling) ([whisper.cpp][wcpp]) | Metal build: yes. Core ML/ANE encoder: mostly no, since the ANE is a separate accelerator (decoder still on CPU/GPU) | `whisper_full` wrapper takes a numpy array and uses `py::gil_scoped_release` ([pywhispercpp main.cpp][pywcpp-src]). Metal/Core ML need **source builds** with `GGML_METAL=1` / `WHISPER_COREML=1`, since the prebuilt wheels are CPU-only ([pywhispercpp][pywcpp]). Separate GGML model files, and anti-hallucination knobs would need re-tuning. |
| **lightning-whisper-mlx** | claims "10x faster than Whisper CPP, 4x faster than current MLX Whisper" (batched decode) ([repo][lwm]) | yes (GPU) | file-path `transcribe(audio_path)` API; **last commit 2024-05-08** ([commits][lwmc]), so effectively unmaintained. Avoid. |

**Does it change the picture?**
- Somewhat for latency, not for the process model. Whisper on the GPU frees CPU cores but adds a second GPU client. At the moment it matters most, a merge arriving right after transcription, both jobs slow each other down.
- The ANE route is the only one that keeps compute actually separate, and it costs a source-built native dependency.
- The bottleneck is serial LLM calls, not whisper, so none of these fixes the stall.
- Recommendation: stay on faster-whisper CPU. Keep the transcriber behind a one-function seam (`transcribe(audio: np.ndarray) -> list[Segment]`) so mlx-whisper or pywhispercpp can be A/B'd through the eval workbench later.

## Recommended minimal process model

**One Python process, four long-lived threads plus the PortAudio callback, connected by `queue.Queue`. One thread owns state.**

```
PortAudio thread ── callback: q_audio.put(indata.copy())
        │
[capture/transcriber thread]  pull audio → accumulate to chunk (10 s or VAD pause)
        │                     → RMS gate → faster-whisper (iterate segments here; GIL released)
        │                     → hallucination/dup filters → append raw log → q_events.put(TranscriptChunk)
        ▼
[engine thread = single writer]  get() one event, drain any others already queued (batch)
        │   TranscriptChunk(s) → one merge call (Ollama, blocking HTTP, GIL released) → apply ops
        │   WakeQuery          → answer call → state["asked"] → Popen(["say", …]) (don't wait)
        │   UIEdit / Command   → apply op
        │   SlowResult         → apply editorial/coach ops
        │   → render markdown, save state, publish snapshot for UI
        │
        ├─ when q_events is empty and editorial/coach is due → hand a *snapshot* to:
        ▼
[slow-lane thread]  editorial pass / coach nudges on the snapshot → q_events.put(SlowResult)
        (Ollama serialises same-model calls anyway; this thread just keeps the engine free
         to accept events. The engine may drop a SlowResult if the state moved on too far.)

[UI thread, later]  local HTTP server (stdlib ThreadingHTTPServer, or an ASGI app in its own loop)
        reads the engine's published snapshot; posts edits as UIEdit onto q_events.
```

**Why this shape.**
1. **Removes the stall where it hurts.** Capture and transcription never wait on the LLM, so no audio is lost and the raw log stays live. Only note freshness depends on Ollama.
2. **Matches where compute actually is.** CT2 and HTTP both release the GIL, so plain threads run whisper and the LLM wait truly in parallel. Ollama is already its own process.
3. **Honours Ollama's real limit.** qwen35 is forced to `numParallel=1`. The engine batches backed-up chunks into one merge, and the slow lane only fires when the engine is idle, so editorial/coach calls don't sit in the FIFO ahead of merges. This scheduling rule replaces any need for an Ollama priority queue.
4. **Single writer is enforced by construction.** Everything that changes notes becomes an event on `q_events`: transcript, query, UI edit, command, slow-lane result. That is also the natural seam for the op/provenance contract and for evals, which can replay the event queue without audio.
5. **Few abstractions.** Stdlib `threading` + `queue`, one event type per source, no framework. Each thread is a `while True: x = q.get()` loop an agent can hold in its head.

**Guardrails that go with it (small, concrete).**
- Send the same `options` (`num_ctx`, `temperature`) on **every** call to a given model, including `answer_query`, to avoid runner reloads ([sched.go][sched024]).
- Set `keep_alive` (e.g. `"30m"` or `-1`) on calls so silences don't cause cold reloads ([FAQ][faq]).
- Add `timeout=` to every `requests.post`, and treat a timeout as "skip this merge; chunks stay queued".
- Replace the callback list with `queue.Queue` to remove the concatenate/clear race ([rec_unlimited.py][sdrec]).
- Leave `cpu_threads=4, num_workers=1`. Measure merge latency against chunk period before tuning.
- If commands/coach need to respond while a merge is running, use a **second, small model** for them. Ollama loads it alongside, up to 3 models per GPU if memory fits ([sched.go][sched024]), and it gets its own queue. Budget ~4 GB on this 24 GB Mac, keep its `num_ctx` small and fixed, and expect some GPU sharing slowdown.
- Health signal for the UI: `q_events.qsize()` (merge backlog) and seconds since the last merge. If the backlog grows steadily, merges are slower than speech and batching or a shorter prompt is needed.

**Open questions (measure, don't guess; needs a benchmark ticket).**
- Actual `small.en` INT8 time per 10 s chunk on the M5.
- qwen3.5:4b merge latency at ~16k prompt, and how much each slows the other when they overlap.
- Whether a 1–2B second model is good enough for commands.

## Sources

- [envcfg]: https://github.com/ollama/ollama/blob/main/envconfig/config.go — Ollama env var defaults (NUM_PARALLEL 1, MAX_LOADED_MODELS 0, MAX_QUEUE 512, KEEP_ALIVE 5m, CONTEXT_LENGTH, KV_CACHE_TYPE, FLASH_ATTENTION)
- [sched024]: https://github.com/ollama/ollama/blob/v0.24.0/server/sched.go — scheduler at the locally installed version: numParallel forced to 1 for qwen35 et al., defaultModelsPerGPU=3, "fits" check / eviction, ErrMaxQueue, needsReload
- [schedmain]: https://github.com/ollama/ollama/blob/main/server/sched.go — same checks on main (qwen35 still in the list, 2026-09-14); context × numParallel
- [faq]: https://github.com/ollama/ollama/blob/main/docs/faq.mdx — concurrent requests, queueing/503, keep_alive, launchctl env vars, flash attention, KV cache types, `ollama ps` processor column
- [mlxblog]: https://ollama.com/blog/mlx — MLX engine preview, Ollama 0.19, >32 GB requirement
- [ct2par]: https://opennmt.net/CTranslate2/parallel.html — "all computation methods release the Python GIL"; intra/inter threads
- [ct2whisper]: https://opennmt.net/CTranslate2/python/ctranslate2.models.Whisper.html — Whisper constructor: inter_threads, intra_threads, max_queued_batches
- [fwtx]: https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py — cpu_threads/num_workers docstrings and mapping to CT2; lazy segment generator
- [fwvad]: https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/vad.py — Silero VAD onnxruntime session, 1 intra/inter thread
- [fwreadme]: https://github.com/SYSTRAN/faster-whisper/blob/master/README.md — CPU benchmarks, "transcription only starts when you iterate", streaming community projects
- [wstream]: https://github.com/ufal/whisper_streaming — LocalAgreement streaming, 3.3 s latency, "becoming outdated in 2025"
- [simul]: https://github.com/ufal/SimulStreaming — successor; large-v3, GPU ≥10 GB
- [sdstreams]: https://python-sounddevice.readthedocs.io/en/latest/api/streams.html — callback restrictions, CallbackFlags, latency, blocksize
- [sdrec]: https://github.com/spatialaudio/python-sounddevice/blob/master/examples/rec_unlimited.py — `q.put(indata.copy())` queue pattern
- [pa]: https://www.portaudio.com/docs/v19-doxydocs/portaudio_8h.html — paInputOverflow definition; callback restrictions
- [pythreading]: https://docs.python.org/3/library/threading.html — GIL note; threading appropriate for I/O-bound; free-threaded builds not default
- [pycapi]: https://docs.python.org/3/c-api/threads.html — "the global interpreter lock is released around blocking I/O operations"
- [pysys]: https://docs.python.org/3/library/sys.html#sys.setswitchinterval — thread switch interval (0.005 s confirmed locally)
- [mlxw]: https://github.com/ml-explore/mlx-examples/blob/main/whisper/README.md — mlx-whisper install/usage
- [mlxtx]: https://github.com/ml-explore/mlx-examples/blob/main/whisper/mlx_whisper/transcribe.py — accepts np.ndarray; decode options
- [wcpp]: https://github.com/ggml-org/whisper.cpp — Metal, Core ML/ANE encoder (>3× vs CPU, slow first run), whisper-stream, VAD
- [pywcpp]: https://github.com/absadiki/pywhispercpp — bindings, GGML_METAL / WHISPER_COREML build flags
- [pywcpp-src]: https://github.com/absadiki/pywhispercpp/blob/main/src/main.cpp — `py::gil_scoped_release` around `whisper_full`; `py::array_t<float>` input
- [lwm]: https://github.com/mustafaaljadery/lightning-whisper-mlx — speed claims, API
- [lwmc]: https://github.com/mustafaaljadery/lightning-whisper-mlx/commits/main — last commit 2024-05-08
- Local: `/Users/jamesscholz/hobbes/note-machine/live_notes.py` (lines ~620, ~819, ~1060, 1078–1201); venv `sounddevice.py` 0.5.6 (lines ~845, 2774); `sysctl`, `ollama show -v`, `/api/show`, `/api/version`, `otool -L`, `pip show`.

[envcfg]: https://github.com/ollama/ollama/blob/main/envconfig/config.go
[sched024]: https://github.com/ollama/ollama/blob/v0.24.0/server/sched.go
[schedmain]: https://github.com/ollama/ollama/blob/main/server/sched.go
[faq]: https://github.com/ollama/ollama/blob/main/docs/faq.mdx
[mlxblog]: https://ollama.com/blog/mlx
[ct2par]: https://opennmt.net/CTranslate2/parallel.html
[ct2whisper]: https://opennmt.net/CTranslate2/python/ctranslate2.models.Whisper.html
[fwtx]: https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py
[fwvad]: https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/vad.py
[fwreadme]: https://github.com/SYSTRAN/faster-whisper/blob/master/README.md
[wstream]: https://github.com/ufal/whisper_streaming
[simul]: https://github.com/ufal/SimulStreaming
[sdstreams]: https://python-sounddevice.readthedocs.io/en/latest/api/streams.html
[sdrec]: https://github.com/spatialaudio/python-sounddevice/blob/master/examples/rec_unlimited.py
[pa]: https://www.portaudio.com/docs/v19-doxydocs/portaudio_8h.html
[pythreading]: https://docs.python.org/3/library/threading.html
[pycapi]: https://docs.python.org/3/c-api/threads.html
[pysys]: https://docs.python.org/3/library/sys.html#sys.setswitchinterval
[mlxw]: https://github.com/ml-explore/mlx-examples/blob/main/whisper/README.md
[mlxtx]: https://github.com/ml-explore/mlx-examples/blob/main/whisper/mlx_whisper/transcribe.py
[wcpp]: https://github.com/ggml-org/whisper.cpp
[pywcpp]: https://github.com/absadiki/pywhispercpp
[pywcpp-src]: https://github.com/absadiki/pywhispercpp/blob/main/src/main.cpp
[lwm]: https://github.com/mustafaaljadery/lightning-whisper-mlx
[lwmc]: https://github.com/mustafaaljadery/lightning-whisper-mlx/commits/main
