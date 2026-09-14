# Research: local-first meeting-note peers (Anarlog, Meetily) — pipeline structure and reusable seams

Label: wayfinder:research
Researched: 2026-09-15
Question owner: note-machine architecture map, "module seams & process model" and "capture-source details".

Snapshots read (shallow clones, all file citations are pinned to these commits):

- **Anarlog** (formerly Hyprnote; `fastrepl/hyprnote` now redirects to `fastrepl/anarlog`), MIT community edition, commit `eebd438` (2026-09-14).
- **Meetily** (`Zackriya-Solutions/meeting-minutes` now resolves to `Zackriya-Solutions/meetily`), MIT, commit `a2cb62e` (2026-09-10).

Legend: **[code]** = read in source; **[doc]** = the project's own docs/README (vendor-stated, not traced to code); **[inferred]** = my reading, not stated anywhere; **[unverified]** = could not confirm from a primary source.

---

## 1. Answer (short)

Both tools are **one desktop process** (Tauri: Rust core + web UI) with the same five-stage spine: **capture sources → VAD/segmenter → STT provider → LLM provider → local storage**. The UI talks to the core only through commands (in) and typed events (out).

- **Capture on macOS (both tools).** Both use a **Core Audio process tap**: a global mono tap wrapped in a private aggregate device, called through the `cidre` Rust bindings. Neither uses ScreenCaptureKit or BlackHole in the current capture code; BlackHole survives only as device-name detection and UI hints in Meetily.
- **VAD.**
  - Meetily runs **Silero** (via `silero-rs`) on a **mixed mic+system signal** and dispatches one speech segment per burst.
  - Anarlog keeps **mic and speaker as separate channels**. Its live path uses a cheap **earshot** VAD mask that zeroes non-speech frames, and leaves live segmentation to the streaming STT provider. Its batch/import path uses a **Silero ONNX** speech chunker.
- **Two provider seams, chosen independently: transcription and "intelligence".**
  - Meetily: a small STT trait plus an LLM enum where most providers are just an OpenAI-compatible base URL.
  - Anarlog: 20+ STT adapters behind a Deepgram-shaped wire protocol, and the Vercel AI SDK for LLMs.
- **Extension surface.**
  - Meetily has essentially none: no plugins, MCP, webhooks or Obsidian export found in the source.
  - Anarlog has a lot: shell-command hooks, signed webhooks, a local CLI + MCP server whose writes are limited to **staged proposals a human applies**, a plugin SDK, Markdown export, and paid automations.
- **Storage.** Both use SQLite plus a per-meeting folder of plain files. Meetily's folder holds `audio.mp4` and `transcripts.json`; Anarlog's holds `_meta.json`, `_memo.md` and `transcript.json`.

**For note-machine:**

- **Copy:**
  - the stage split with a narrow segment contract;
  - per-source channels instead of mixing;
  - streaming VAD boundaries with a silence "redemption" window;
  - one OpenAI-compatible LLM client with a base-URL switch;
  - a typed event fan-out for UI and coach;
  - hooks-as-shell-commands;
  - Anarlog's "agents propose, the single writer applies" rule;
  - atomic file writes.
- **Skip:**
  - actor supervision trees;
  - adapter registries and wire protocols;
  - in-app mixing/ducking/AEC;
  - plugin SDKs, sync, and SQLite migration machinery.
- **Reuse rather than re-solve:**
  - `sounddevice` for mic capture;
  - a tiny Swift process-tap helper (modelled on BSD-2 AudioCap) piping PCM to Python for system audio;
  - a stateful streaming VAD for segment boundaries, keeping faster-whisper's built-in VAD as the within-segment filter.

---

## 2. Per-tool breakdown

### 2.1 Anarlog (ex-Hyprnote)

**Shape.** A pnpm + Rust monorepo: Tauri v2 desktop app, ~150 Rust crates, ~50 Tauri plugins, optional hosted API/web/mobile [doc][a-readme] [doc][a-agents]. "Sessions are the core entity: all notes are backed by sessions" [doc][a-agents]. This is a product platform, not a small codebase. The listener crate alone is ~10.9k lines of Rust [code][a-listener-tree].

**Pipeline stages:**

| Stage | What it does | Evidence |
|---|---|---|
| Capture (mic) | Rust `audio-actual` crate: mic stream plus per-OS speaker streams (`speaker/macos.rs`, `windows.rs`, `linux.rs`, `mock.rs`) | [code][a-audio-actual] |
| Capture (macOS system audio) | `ca::TapDesc::with_mono_global_tap_excluding_processes(...)` → `create_process_tap()` → private aggregate device whose tap list holds the tap UID (via `cidre`) | [code][a-speaker-macos] |
| Frame contract | `CaptureFrame { raw_mic, raw_speaker, aec_mic: Option }`; `CaptureConfig { sample_rate, chunk_size, mic_device, enable_aec }`. Mic and speaker stay separate end to end | [code][a-audio-lib] |
| Echo cancellation | Optional ONNX AEC crate; pipeline prefers the AEC'd mic track when present | [code][a-aec] [code][a-pipeline] |
| VAD (live) | `VadMask` built on the `earshot` detector zeroes non-speech frames in place (hangover 6 frames, amplitude floor 0.0005). A mask, not a segmenter: the audio stream stays continuous | [code][a-vadmask] [code][a-vadstream] [code][a-pipeline] |
| VAD (batch/import) | `audio-chunking` `SpeechChunker` with the `silero-onnx` feature, used by `listener2-core` batch and `transcribe-core` | [code][a-chunking-cargo] [code][a-l2-local] |
| Process model inside the core | `ractor` actor tree: session supervisor with children `Source`, `Listener`, `Recorder`; typed event enums for lifecycle, progress, data and errors | [code][a-children] [code][a-events] [code][a-listener-cargo] |
| STT seam | `owhisper-client` adapters (Deepgram, Soniox, AssemblyAI, OpenAI, whisper.cpp, Argmax, Apple Speech, Soniqo/Parakeet, …) behind one Deepgram-shaped response type (`Word { word, start, end, confidence, speaker }`) | [code][a-adapters] [code][a-owhisper-stream] |
| Channel handling | `ChannelMode::{MicOnly, SpeakerOnly, MicAndSpeaker}`; responses carry a channel index, so "me vs. them" attribution comes from the channel | [code][a-listener-mod] |
| Local STT server | On-device whisper runs as a local HTTP/WS service exposing the same `/v1/listen` path as the cloud protocol, so local and cloud share one client | [code][a-whisper-local] [code][a-whisper-local-lib] |
| LLM seam ("Intelligence") | Desktop TS uses the Vercel AI SDK; one `switch` over providers (anthropic, openai, openrouter, azure, google, ollama via `createOpenAICompatible` with an Origin header fix, …) | [code][a-usellm] |
| Provider policy | Transcription and Intelligence are independent selections. A local model that is down gives an error, never a silent cloud fallback. BYOK keys live in the OS credential store, not the DB | [doc][a-models] |
| Storage | Canonical SQLite schema (`sessions`, `session_documents`, `transcripts`, `session_participants`, `action_items`, `entity_mentions`, `humans`, `organizations`, …) plus a Tantivy search index. Older file layout per session (`_meta.json`, `_memo.md`, `transcript.json`, `<uuid>.md` notes) is read by `fs-sync-core`. A `storage_migration_state` table with a `shadow` phase / `parity_verified` / `rollback_until` shows a staged migration between the two | [code][a-schema] [code][a-session-content] [doc][a-models] |
| Import | Audio (WAV/MP3/OGG/MP4/M4A/FLAC/WebM/AAC) through the selected STT; transcripts as `.vtt`/`.srt` | [doc][a-import] |

**Extension surface:**

- **Hooks.** A JSON config `{ "version": 0, "on": { "<event>": [ { "command": "…" } ] } }`. Events are `beforeListeningStarted` / `afterListeningStopped`; each event's args become CLI flags on the spawned command [code][a-hook-event] [code][a-hook-config]. This is the cheapest seam in either repo.
- **Webhooks.** Signed JSON POSTs (`meeting.completed`, `note.enhanced`, `webhook.test`), 10 s timeout, retries at 5 s and 30 s; they fire only while the desktop app runs [doc][a-webhooks].
- **CLI + local MCP.**
  - `rmcp` tools: `list_meetings`, `get_meeting`, `get_meeting_transcript`, `get_recurring_meeting_history`, `propose_summary_edit`, `propose_memo_edit`, `list_proposals`, `get_proposal` [code][a-mcp].
  - Policy: agents may not apply note changes. They stage a proposal and a human applies the diff in the app. Reads are bounded. Agents must not touch SQLite directly [doc][a-agents-doc].
- **Plugin SDK.** A TS `PluginModule { id, onload(ctx) }` whose `ctx` offers `registerView`, `openTab`, `events`, `registerCleanup`. This is UI-level extension [code][a-plugin-sdk].
- **Export.** One `export` command taking `{ enhanced_md, memo_md, transcript{items[speaker,text]}, metadata }`, with Typst rendering [code][a-export-types] [code][a-export-manifest]. No Obsidian-specific export in app code: "Obsidian" appears only in marketing articles under `apps/web/content` [code: grep].
- **Automations (Pro).** After a meeting ends: Slack recap, Notion append, Linear issues, Markdown export to a folder [doc][a-automations].

### 2.2 Meetily

**Shape.** A Tauri 2 app: Rust core + Next.js UI. The older **Python/FastAPI backend, Docker setup and standalone whisper-server are "archived … unsupported"**. Current guidance says not to reintroduce a separate backend tier [doc][m-claude]. So Meetily has already tried, and walked back, a multi-process Python + STT-server design.

**Pipeline stages:**

| Stage | What it does | Evidence |
|---|---|---|
| Capture (mic) | `cpal` 0.15 | [code][m-cargo] |
| Capture (macOS system audio) | `cidre` global mono process tap in a private aggregate device named `meetily-audio-tap`. Comments record an echo bug from adding both the output device and its tap. Needs `NSAudioCaptureUsageDescription` on macOS 14.4+; a denied permission gives silence, not an error | [code][m-coreaudio] [code][m-system] |
| Stale docs | CLAUDE.md still says macOS system audio "Uses ScreenCaptureKit" and "Requires virtual audio device (BlackHole)". The code uses the process tap; BlackHole appears only in device-name detection and a UI hint | [doc][m-claude] vs [code][m-coreaudio] [code][m-devdetect] [code][m-permwarn] |
| Mixing | `AudioMixerRingBuffer` aligns mic/system into 50 ms windows; `ProfessionalAudioMixer` does RMS ducking and clipping prevention; then **the mixed signal** goes to VAD + STT | [code][m-pipeline] [doc][m-claude] |
| VAD / segmentation | `silero-rs` `VadSession` at 16 kHz, 30 ms frames. Thresholds 0.50/0.35, `min_speech_time` 250 ms, pre-pad 300 ms, post-pad 400 ms. `redemption_time` (silence needed to close a segment) is **500 ms live** and **2000 ms for import/retranscribe**. Segments under 800 samples are dropped; a flush on stop. Comment: "bounded uninterrupted-speech delivery is tracked in #756" (no max segment length yet) | [code][m-vad] [code][m-pipeline] |
| STT seam | `TranscriptionProvider` trait: `transcribe(audio_16k_mono, language) -> { text, confidence?, is_partial }`, `is_model_loaded`, `get_current_model`, `provider_name`. Implementations: Whisper (`whisper-rs` with Metal/CoreML) and Parakeet (`ort`) | [code][m-provider] [code][m-cargo] |
| Speaker attribution | Migration adds `transcripts.speaker` with values `'mic'` / `'system'`. The live path transcribes the mixed signal, so per-source labels can't come from that path [inferred from pipeline.rs] | [code][m-mig-speaker] [code][m-pipeline] |
| LLM seam | `enum LLMProvider { OpenAI, Claude, Groq, Ollama, OpenRouter, BuiltInAI, CustomOpenAI }`. Every provider except Claude and BuiltInAI is an OpenAI-compatible `/chat/completions` URL (+ key). Claude gets its own `/v1/messages` shape. Includes cancellation tokens and an Ollama reasoning-effort fallback | [code][m-llm] |
| Built-in local LLM | `llama-helper` sidecar process managed over stdin/stdout with health check and keep-alive | [code][m-sidecar] |
| Summarisation | Map-reduce: character-based `chunk_text` with overlap, per-chunk summary, combine, final report. For Ollama the chunk size is derived from the model's reported context size minus 300 tokens | [code][m-processor] [code][m-service] |
| Templates | JSON files (`standard_meeting`, `daily_standup`, `retrospective`, …) of `sections[{ title, instruction, format: paragraph\|list\|string, item_format? }]` | [code][m-template-types] [code][m-templates-dir] |
| Storage | SQLx SQLite: `meetings`, `transcripts`, `summary_processes`, `transcript_chunks`, `settings` (API keys in columns), `meeting_notes(notes_markdown, notes_json)`. Plus a per-meeting folder with `audio.mp4` and an atomically written `transcripts.json` (temp file + rename) | [code][m-schema] [code][m-mig-notes] [code][m-common] [code][m-saver] |
| Import | `import.rs` decodes a file and runs the same Silero chunker (`get_speech_chunks_with_progress`) before the STT engine | [code][m-import] |
| UI transport | Tauri commands in, `app.emit("transcript-update" / "speech-detected" / "transcription-error" …)` out | [code][m-worker] [doc][m-claude] |

**Extension surface:** a grep for `mcp|webhook|obsidian` across `frontend/src` and `frontend/src-tauri/src` found nothing [code: grep]. The extension story is limited to BYOK/custom OpenAI endpoints and JSON templates. README positions richer exports and "custom summary workflows" as **Meetily PRO** [doc][m-readme].

### 2.3 Side-by-side: the seams that matter to note-machine

| Seam | Anarlog | Meetily | note-machine today |
|---|---|---|---|
| Process model | 1 app process, actor tree; optional local STT server; hooks spawn processes | 1 app process, async tasks; LLM sidecar; old Python backend abandoned | 1 Python process, one loop in `main()` |
| Source contract | `CaptureFrame` (mic/speaker/aec_mic kept apart) | mixed f32 @48 kHz → `SpeechSegment{samples,start_ms,end_ms,confidence}` | fixed 10 s mono float32 buffer (`live_notes.py` `callback`/`InputStream` loop) |
| Segment boundaries | provider-side (live); Silero chunker (batch) | Silero, 500 ms redemption live | fixed `CHUNK_SECONDS` + RMS gate; `vad_filter` inside the window |
| Attribution | channel index | column exists, not fed per source | none |
| STT seam | adapter registry + wire protocol | 4-method trait | direct `WhisperModel.transcribe` call |
| LLM seam | AI SDK switch; no silent cloud fallback | enum → base URL | direct Ollama `requests` calls |
| Writes by agents/tools | proposals only, human applies | n/a | ops applied by code-owned state (single writer) |
| Extension | hooks, webhooks, MCP/CLI, plugin SDK, export | none | wake phrase → Q&A |
| Storage | SQLite canonical + session files (migrating) | SQLite + meeting folder | JSON state + Markdown notes + raw log in vault |

---

## 3. Reusable libraries for capture and VAD (Python)

### 3.1 Capture

| Option | Maturity / licence | Fit for note-machine | Evidence |
|---|---|---|---|
| **`sounddevice`** (PortAudio) | 0.5.6 (Aug 2026), MIT, active | Keep for mic, and for any user-installed loopback device. Already used | [pypi][p-sounddevice] [code][l-sounddevice] |
| **Core Audio process taps** (`AudioHardwareCreateProcessTap` + `CATapDescription` + aggregate device) | Apple API, **macOS 14.2+** per Apple's reference metadata. Needs `NSAudioCaptureUsageDescription` in Info.plist. AudioCap's README says 14.4 (**version discrepancy**; 14.2 is Apple's stated `introducedAt`) | **Recommended path.** It's what both peers ship. Can tap all processes or selected PIDs; no driver install | [apple][ap-tap-fn] [apple][ap-tap-sample] [doc][l-audiocap] [code][a-speaker-macos] [code][m-coreaudio] |
| ↳ **AudioCap** (Swift sample) | BSD-2-Clause, ~500★, last push Aug 2025; documentation-grade sample, not a library | Best template for a ~150-line Swift helper binary that writes 16 kHz PCM to stdout for Python to read | [code][l-audiocap] |
| ↳ **AudioTee** (Swift CLI, stdout PCM, `--sample-rate`) | ~90★; README warns "API unstable"; **no licence file in repo** (so not reusable as-is without asking the author) | Exactly the right process shape (subprocess → PCM on stdout, logs on stderr). Use as a design reference only | [doc][l-audiotee] [code: repo root listing] |
| ↳ **`pyobjc-framework-CoreAudio`** | 12.2.2 (Aug 2026), MIT; binds `AudioHardwareCreateProcessTap`/`Destroy` (test file, min OS 14.2) | Possible pure-Python route, but the IOProc callback runs on a real-time audio thread; driving it through PyObjC/GIL is **[unverified]** for glitch-free capture. Prefer the Swift helper | [code][l-pyobjc-tap] [pypi][p-pyobjc-ca] |
| **ScreenCaptureKit** (`SCStreamConfiguration.capturesAudio`) | Apple API macOS 13.0+; `pyobjc-framework-ScreenCaptureKit` 12.2.2 MIT. Meetily docs say it needs screen-recording permission [doc] | Heavier: a stream plus content filter, and a screen-recording prompt. Only worth it for macOS 13 support. Neither peer uses it in current code | [apple][ap-sck] [pypi][p-pyobjc-sck] [doc][m-claude] |
| **BlackHole** (virtual driver) | GPL-3.0; non-GPL projects need a commercial licence from Existential Audio; ~20k★, active | Zero code (it shows up as a `sounddevice` input), but the user must install a driver and build a Multi-Output Device. Licence only bites if you **bundle/redistribute** it **[inferred]**. Good as a "works today" fallback; both peers have moved past it | [code][l-blackhole-license] [doc][l-blackhole-readme] [code][m-devdetect] |

### 3.2 VAD and segmentation

| Option | Maturity / licence | Fit | Evidence |
|---|---|---|---|
| **faster-whisper built-in VAD** (`vad_filter`, `VadOptions`) | faster-whisper 1.2.1 (Oct 2025), MIT; repo last push Nov 2025 (**maintenance has slowed**). Bundles `silero_vad_v6.onnx` via `onnxruntime` | Defaults: `threshold 0.5`, `min_silence_duration_ms 2000`, `speech_pad_ms 400`, `max_speech_duration_s inf`. `SileroVADModel.__call__` zero-inits LSTM state `h`/`c` on every call and processes a whole array, so it is **stateless across calls**: fine as a within-segment filter (today's use), wrong tool for streaming boundaries | [code][l-fw-vad] [code][l-fw-transcribe] [pypi][p-fw] |
| **`silero-vad`** (pip) | 6.2.1 (Feb 2026), MIT, active. **Hard-depends on `torch` + `torchaudio`**; ONNX is only an extra | `VADIterator` is a stateful streaming detector (8/16 kHz; `min_silence_duration_ms`, `speech_pad_ms`) → emits start/end events. This is what Meetily does in Rust. The torch dependency is heavy for "lightweight" | [code][l-silero-iter] [pypi][p-silero] |
| **Silero ONNX, hand-rolled streaming** | same model file faster-whisper already ships | ~40 lines: carry `h`/`c`/context between 512-sample frames, then hysteresis (0.50/0.35) + redemption window (Meetily's numbers). No new dependency beyond `onnxruntime` (already pulled in by faster-whisper) **[inferred from l-fw-vad + m-vad]** | [code][l-fw-vad] [code][m-vad] |
| **`webrtcvad`** / **`webrtcvad-wheels`** | original 2.0.10 released 2017, last commit 2021, MIT; `-wheels` fork 2.0.14 (Sep 2024), no runtime deps | Tiny and fast, 10/20/30 ms frames. Older GMM detector; accuracy vs Silero **[unverified here]**. Fine as a cheap pre-gate; weaker for boundary quality | [code][l-webrtcvad-license] [pypi][p-webrtcvad] [pypi][p-webrtcvad-wheels] |
| **earshot** (Rust) | Apache-2.0, ~200★ | Anarlog's live mask; not usable from Python without bindings. Mentioned only to explain Anarlog | [code][a-vadstream] |
| **TEN VAD** | "Apache 2.0 **with additional conditions**" forbidding deployment that competes with Agora | Licence risk; skip | [code][l-ten-license] |
| **pyannote.audio** (diarization, for later speaker attribution) | 4.0.7 (Jun 2026), MIT code; pulls torch, lightning, torchaudio, OTel … | Heavy. Do channel-based attribution (mic = me, system = them) first; diarize only the system channel, later, maybe offline. Anarlog does the same with ONNX pyannote + wespeaker voiceprints | [pypi][p-pyannote] [code][a-crates] [doc][a-models] |

---

## 4. Copy / Skip recommendations for note-machine

### Copy (cheap, and each maps to a horizon item)

1. **A narrow segment contract between capture and everything else.** Something like `Segment(source: "mic"|"system"|"file", t_start, t_end, samples_16k_mono)`. Both peers put a single typed audio unit at this boundary (Anarlog `CaptureFrame`, Meetily `SpeechSegment`) [a-audio-lib] [m-vad]. Imported recordings then become just another source feeding the same segmenter, which is exactly how both implement import [m-import] [a-l2-local].
2. **Keep sources as separate channels; don't mix before VAD/STT.** Anarlog's `ChannelMode` gives "me vs. them" attribution for free [a-listener-mod]. Meetily mixed first, and its `speaker` column is left without a per-source feed [m-mig-speaker] [m-pipeline]. For note-machine this means one segmenter+Whisper pass per source, with segments tagged. Echo caveat: on laptop speakers the mic hears the far side. Anarlog solves this with ONNX AEC [a-aec]; for a small tool, prefer "use headphones", or drop mic segments that closely match a concurrent system segment **[inferred]**.
3. **Silence-cut segment boundaries with a redemption window, plus a max length.** Take Meetily's tuned numbers as a starting point: 500 ms live / 2000 ms import, 250 ms min speech, 300/400 ms pads [m-vad] [m-pipeline]. Also add the max-segment cap Meetily is still missing (#756). Implement as streaming Silero ONNX carried across frames (or `VADIterator` if torch is acceptable). Keep faster-whisper's `vad_filter` inside each segment as today.
4. **Two independent provider seams.**
   - *Transcriber:* a Python `Protocol` shaped like Meetily's 4-method trait [m-provider].
   - *LLM:* one OpenAI-compatible chat client keyed by `base_url` + `api_key`, which covers Ollama, OpenRouter, Groq, OpenAI and custom endpoints. That is what 5 of Meetily's 7 enum arms reduce to [m-llm]. Add one special case only if Anthropic-native is needed.
   - Copy Anarlog's rule: **a local provider that is unavailable is an error, never a silent cloud fallback** [a-models]. That keeps "local vs hosted" open without foreclosing it.
5. **Ask the model server for its context size.** Meetily reads Ollama model metadata and reserves prompt overhead [m-service]. This directly guards the `num_ctx` truncation failure note-machine already hit (PLAN.md Phase 1).
6. **A typed event fan-out as the UI/coach seam.** Both peers push lifecycle, progress, transcript-delta and error events out of the core; the UI never reaches in [a-events] [m-worker]. In Python: a small `emit(event)` over a subscriber list or queue. A localhost SSE/WebSocket endpoint for the live browser view is just another subscriber, and so are the coach and the notes renderer.
7. **"Tools and agents propose; the single writer applies."** Anarlog's MCP/CLI can only `propose_*` edits that a human applies [a-mcp] [a-agents-doc]. This matches note-machine's ops + single-writer direction. Voice/silent commands, coach nudges, business-context enrichment and UI edits should all produce *op proposals* into the one state owner, never write the notes file directly.
8. **Hooks as shell commands.** Anarlog's whole hook system is a versioned JSON map of event → `[{command}]`, with event args passed as CLI flags [a-hook-config] [a-hook-event]. A `hooks.json` with `session_started` / `session_stopped` / `notes_updated` is the cheapest integration surface: copy to `ingest`, git commit, Slack post. Add webhooks only if something remote needs push.
9. **Atomic writes, and session files as the store.** Meetily writes `transcripts.json` via temp file + rename [m-common]. note-machine's JSON state + Markdown + raw log per session already matches both peers' file layouts [a-session-content] [m-saver]; make every write atomic.
10. **Templates as data.** Meetily's `sections[{title, instruction, format}]` [m-template-types] validates note-machine's existing `templates.json` direction. Consider adopting per-section `instruction` + `format`.

### Skip (over-engineered for a small Python codebase)

- **Actor supervision trees** (Anarlog `ractor` root/session/source/listener/recorder, ~10.9k lines with reliability tests) [a-listener-tree] [a-children]. Threads + `queue.Queue` between stages in one process are enough.
- **STT adapter registry and a Deepgram-compatible wire protocol, including a local `/v1/listen` server** [a-adapters] [a-whisper-local]. It's valuable only when you must hot-swap 20 cloud STT vendors. Defer; revisit only if hosting forces STT out of process.
- **In-app mixing, ducking, ring-buffer alignment and AEC** (Meetily `pipeline.rs` mixer, Anarlog `aec`) [m-pipeline] [a-aec]. Keeping channels separate removes the need to mix; note-machine doesn't keep audio, so a mixed recording isn't needed.
- **UI plugin SDK** [a-plugin-sdk]. The browser view is first-party; hooks + events + op proposals cover third-party needs.
- **SQLite canonical store, migrations, Tantivy index, shadow-phase storage migration, CloudSync/E2EE** [a-schema]. Anarlog's `storage_migration_state` table shows the ongoing cost of switching stores. Stay on files in the vault until cross-meeting querying is a real requirement.
- **An LLM sidecar process manager** (Meetily `llama-helper`) [m-sidecar]. Ollama already is that sidecar.
- **Map-reduce whole-transcript summarisation** [m-processor]. note-machine's incremental ops + editorial pass is a different, better-fit model for live notes. Chunked summarisation is only relevant for long imported transcripts.
- **A separate Python backend tier / multi-service topology.** Meetily built it and archived it as unsupported [m-claude].

### Implications for the "module seams & process model" decision

- **One process, staged pipeline.** Neither mature peer splits the core into services. Both run capture → VAD → STT → LLM → store in one process, and expose it through commands in and events out. Recommended layout:

  ```
  sources/ (mic, system, file) → segmenter → transcriber → merger/state (single writer) → renderers (markdown, live view)
  ```

  Stages are connected by queues and events.
- **Out-of-process only where the OS or model forces it.**
  - (a) Ollama, already external.
  - (b) A macOS system-audio helper binary (Swift, process tap) piping PCM on stdout. This keeps real-time audio callbacks out of the Python GIL and needs no driver.
  - (c) Hook commands.
- **The seam list the peers validate:** `Source`, `Segmenter`, `Transcriber`, `LLMClient`, event bus, op-proposal intake, hooks. Anything beyond that (adapters, actors, plugins, DB) is platform cost these products took on for multi-vendor, multi-device, commercial reasons note-machine doesn't have.

---

## 5. Sources

Anarlog, pinned to `https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/`

[a-readme]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/README.md
[a-agents]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/AGENTS.md
[a-crates]: https://github.com/fastrepl/anarlog/tree/eebd438263e222df6ae55eae0895ed6ccd0be947/crates
[a-audio-actual]: https://github.com/fastrepl/anarlog/tree/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/audio-actual/src
[a-speaker-macos]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/audio-actual/src/speaker/macos.rs#L52-L70
[a-audio-lib]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/audio/src/lib.rs#L33-L60
[a-aec]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/aec/src/lib.rs
[a-pipeline]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/listener-core/src/actors/source/pipeline.rs#L19-L183
[a-vadmask]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/vad-masking/src/masking.rs
[a-vadstream]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/vad-masking/src/streaming.rs#L1-L19
[a-chunking-cargo]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/audio-chunking/Cargo.toml
[a-l2-local]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/listener2-core/src/batch/simple/local.rs#L12
[a-listener-tree]: https://github.com/fastrepl/anarlog/tree/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/listener-core/src/actors
[a-listener-cargo]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/listener-core/Cargo.toml
[a-children]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/listener-core/src/actors/session/supervisor/children.rs#L14-L81
[a-events]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/listener-core/src/events.rs
[a-adapters]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/listener-core/src/actors/listener/adapters.rs#L8-L201
[a-owhisper-stream]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/owhisper-interface/src/stream.rs
[a-listener-mod]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/listener-core/src/actors/listener/mod.rs#L465-L475
[a-whisper-local]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/transcribe-whisper-local/src/service/streaming.rs#L37-L61
[a-whisper-local-lib]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/transcribe-whisper-local/src/lib.rs#L76-L156
[a-usellm]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/apps/desktop/src/ai/hooks/useLLMConnection.ts#L297-L421
[a-models]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/docs/models-and-providers.mdx
[a-schema]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/db-app/migrations/20260710223922_canonical_data_model.sql
[a-session-content]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/fs-sync-core/src/session_content.rs#L6-L8
[a-import]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/docs/import-recordings.mdx
[a-hook-event]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/hooks/src/event.rs
[a-hook-config]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/hooks/src/config.rs
[a-webhooks]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/docs/reference/webhooks.mdx
[a-mcp]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/apps/cli/src/mcp.rs#L42-L260
[a-agents-doc]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/docs/agents/overview.mdx
[a-plugin-sdk]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/packages/plugin-sdk/src/index.ts
[a-export-types]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/crates/export-core/src/types.rs
[a-export-manifest]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/plugins/export/src/manifest.rs
[a-automations]: https://github.com/fastrepl/anarlog/blob/eebd438263e222df6ae55eae0895ed6ccd0be947/docs/automations.mdx

- [a-readme] README.md — [a-agents] AGENTS.md — [a-crates] crates/
- [a-audio-actual] crates/audio-actual/src — [a-speaker-macos] crates/audio-actual/src/speaker/macos.rs — [a-audio-lib] crates/audio/src/lib.rs — [a-aec] crates/aec/src/lib.rs
- [a-pipeline] crates/listener-core/src/actors/source/pipeline.rs — [a-vadmask] crates/vad-masking/src/masking.rs — [a-vadstream] crates/vad-masking/src/streaming.rs — [a-chunking-cargo] crates/audio-chunking/Cargo.toml — [a-l2-local] crates/listener2-core/src/batch/simple/local.rs
- [a-listener-tree] crates/listener-core/src/actors — [a-listener-cargo] crates/listener-core/Cargo.toml — [a-children] …/session/supervisor/children.rs — [a-events] crates/listener-core/src/events.rs
- [a-adapters] …/listener/adapters.rs — [a-owhisper-stream] crates/owhisper-interface/src/stream.rs — [a-listener-mod] …/listener/mod.rs — [a-whisper-local] crates/transcribe-whisper-local/src/service/streaming.rs — [a-whisper-local-lib] crates/transcribe-whisper-local/src/lib.rs
- [a-usellm] apps/desktop/src/ai/hooks/useLLMConnection.ts — [a-models] docs/models-and-providers.mdx
- [a-schema] crates/db-app/migrations/20260710223922_canonical_data_model.sql — [a-session-content] crates/fs-sync-core/src/session_content.rs — [a-import] docs/import-recordings.mdx
- [a-hook-event] crates/hooks/src/event.rs — [a-hook-config] crates/hooks/src/config.rs — [a-webhooks] docs/reference/webhooks.mdx — [a-mcp] apps/cli/src/mcp.rs — [a-agents-doc] docs/agents/overview.mdx — [a-plugin-sdk] packages/plugin-sdk/src/index.ts — [a-export-types] crates/export-core/src/types.rs — [a-export-manifest] plugins/export/src/manifest.rs — [a-automations] docs/automations.mdx

Meetily, pinned to `https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/` (Tauri core under `frontend/src-tauri/`)

[m-readme]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/README.md
[m-claude]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/CLAUDE.md
[m-cargo]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/Cargo.toml
[m-coreaudio]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/audio/capture/core_audio.rs#L57-L150
[m-system]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/audio/capture/system.rs
[m-devdetect]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/audio/device_detection.rs#L168-L176
[m-permwarn]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src/components/PermissionWarning.tsx#L126
[m-pipeline]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/audio/pipeline.rs
[m-vad]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/audio/vad.rs#L1-L90
[m-provider]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/audio/transcription/provider.rs
[m-mig-speaker]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/migrations/20251110000001_add_speaker_field.sql
[m-llm]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/summary/llm_client.rs#L215-L350
[m-sidecar]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/summary/summary_engine/sidecar.rs
[m-processor]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/summary/processor.rs#L218-L340
[m-service]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/summary/service.rs#L432-L445
[m-template-types]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/summary/templates/types.rs
[m-templates-dir]: https://github.com/Zackriya-Solutions/meetily/tree/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/templates
[m-schema]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/migrations/20250916100000_initial_schema.sql
[m-mig-notes]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/migrations/20251223000000_add_meeting_notes.sql
[m-common]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/audio/common.rs#L71-L98
[m-saver]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/audio/incremental_saver.rs#L116-L132
[m-import]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/audio/import.rs#L1-L25
[m-worker]: https://github.com/Zackriya-Solutions/meetily/blob/a2cb62e827da7ef59f65064c97233efb2313878e/frontend/src-tauri/src/audio/transcription/worker.rs

- [m-readme] README.md — [m-claude] CLAUDE.md — [m-cargo] frontend/src-tauri/Cargo.toml
- [m-coreaudio] src/audio/capture/core_audio.rs — [m-system] src/audio/capture/system.rs — [m-devdetect] src/audio/device_detection.rs — [m-permwarn] frontend/src/components/PermissionWarning.tsx
- [m-pipeline] src/audio/pipeline.rs — [m-vad] src/audio/vad.rs — [m-provider] src/audio/transcription/provider.rs — [m-worker] src/audio/transcription/worker.rs — [m-import] src/audio/import.rs
- [m-mig-speaker] migrations/20251110000001_add_speaker_field.sql — [m-schema] migrations/20250916100000_initial_schema.sql — [m-mig-notes] migrations/20251223000000_add_meeting_notes.sql — [m-common] src/audio/common.rs — [m-saver] src/audio/incremental_saver.rs
- [m-llm] src/summary/llm_client.rs — [m-sidecar] src/summary/summary_engine/sidecar.rs — [m-processor] src/summary/processor.rs — [m-service] src/summary/service.rs — [m-template-types] src/summary/templates/types.rs — [m-templates-dir] templates/

Apple

[ap-tap-fn]: https://developer.apple.com/documentation/coreaudio/audiohardwarecreateprocesstap(_:_:)
[ap-tap-sample]: https://developer.apple.com/documentation/coreaudio/capturing-system-audio-with-core-audio-taps
[ap-sck]: https://developer.apple.com/documentation/screencapturekit/scstreamconfiguration/capturesaudio

- [ap-tap-fn] `AudioHardwareCreateProcessTap` reference — platform metadata `macOS introducedAt 14.2` (read via Apple's JSON doc endpoint `developer.apple.com/tutorials/data/documentation/...json`).
- [ap-tap-sample] "Capturing system audio with Core Audio taps" sample — text: "macOS 14.2 or later", tap + aggregate device, Info.plist usage key required (the sample project itself is tagged Xcode/macOS 26).
- [ap-sck] `SCStreamConfiguration.capturesAudio` — `macOS introducedAt 13.0`.

Libraries

[l-sounddevice]: https://github.com/spatialaudio/python-sounddevice
[l-audiocap]: https://github.com/insidegui/AudioCap
[l-audiotee]: https://github.com/makeusabrew/audiotee/blob/main/README.md
[l-pyobjc-tap]: https://github.com/ronaldoussoren/pyobjc/blob/main/pyobjc-framework-CoreAudio/PyObjCTest/test_audiohardwaretapping.py
[l-blackhole-license]: https://github.com/ExistentialAudio/BlackHole/blob/master/LICENSE
[l-blackhole-readme]: https://github.com/ExistentialAudio/BlackHole/blob/master/README.md
[l-fw-vad]: https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/vad.py
[l-fw-transcribe]: https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py
[l-silero-iter]: https://github.com/snakers4/silero-vad/blob/master/src/silero_vad/utils_vad.py
[l-webrtcvad-license]: https://github.com/wiseman/py-webrtcvad/blob/master/LICENSE
[l-ten-license]: https://github.com/TEN-framework/ten-vad/blob/main/LICENSE
[p-sounddevice]: https://pypi.org/project/sounddevice/
[p-pyobjc-ca]: https://pypi.org/project/pyobjc-framework-CoreAudio/
[p-pyobjc-sck]: https://pypi.org/project/pyobjc-framework-ScreenCaptureKit/
[p-fw]: https://pypi.org/project/faster-whisper/
[p-silero]: https://pypi.org/project/silero-vad/
[p-webrtcvad]: https://pypi.org/project/webrtcvad/
[p-webrtcvad-wheels]: https://pypi.org/project/webrtcvad-wheels/
[p-pyannote]: https://pypi.org/project/pyannote.audio/

- [l-sounddevice] python-sounddevice (MIT) — [p-sounddevice] PyPI 0.5.6
- [l-audiocap] insidegui/AudioCap (BSD-2-Clause) — [l-audiotee] makeusabrew/audiotee README (no licence file at repo root)
- [l-pyobjc-tap] pyobjc CoreAudio process-tap binding test — [p-pyobjc-ca] PyPI 12.2.2 — [p-pyobjc-sck] PyPI 12.2.2
- [l-blackhole-license] BlackHole LICENSE (GPL-3.0) — [l-blackhole-readme] BlackHole README (commercial licence for non-GPL)
- [l-fw-vad] faster-whisper `vad.py` (VadOptions defaults L41–48, `silero_vad_v6.onnx` L323–325, stateless `__call__` L350+) — [l-fw-transcribe] `transcribe.py` (`vad_filter`/`vad_parameters` L289–290, L396–403) — [p-fw] PyPI 1.2.1
- [l-silero-iter] silero-vad `VADIterator` (L458) — [p-silero] PyPI 6.2.1 (requires torch, torchaudio)
- [l-webrtcvad-license] py-webrtcvad LICENSE (MIT) — [p-webrtcvad] PyPI 2.0.10 (2017) — [p-webrtcvad-wheels] PyPI 2.0.14 (2024)
- [l-ten-license] TEN VAD LICENSE (Apache-2.0 + non-compete conditions)
- [p-pyannote] pyannote.audio PyPI 4.0.7

Repo metadata (stars, licence key, last push) was taken from `gh repo view` on 2026-09-15; PyPI versions/dates from `pypi.org/pypi/<name>/json` on the same day.

note-machine context read: `live_notes.py` (capture loop ~L1128–1180), `PLAN.md`, `.scratch/architecture/map.md`.
