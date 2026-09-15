# Local compute concurrency (Whisper + LLM + coach)

Type: research
Status: resolved
Blocked by: —

## Question

On an Apple Silicon Mac, what are the real concurrency limits of running faster-whisper (CTranslate2, CPU int8) continuously alongside Ollama serving merge calls every ~10s, an editorial pass every ~5 min, and a possible second model for commands/coach? Cover Ollama request queuing and parallelism settings, keep-alive and multi-model memory, whether CTranslate2 releases the GIL (threads vs processes vs asyncio in Python), the `sounddevice` callback's constraints, and whether Metal-backed alternatives (whisper.cpp, MLX) change the picture.

## Context

- Main loop today is a single-threaded `while True` in `live_notes.py:1136` — transcribe, merge, editorial and TTS all block the next chunk.
- Memo §06: "On a 4B local model, the coach competes with the merge for the same CPU."
- Findings: branch `research/local-compute-concurrency` (commit `f328b01`), file `.scratch/architecture/research/local-compute-concurrency.md` on that branch.

## Answer

**The LLM does one call at a time.** Ollama 0.24.0 forces one request at a time for the `qwen35` architecture, whatever `OLLAMA_NUM_PARALLEL` says. Merge, editorial, query and coach all queue in first-come order. Real parallelism means loading a second model, which gets its own queue: about 4 GB extra on this 24 GB M5, plus some slowdown from sharing the GPU.

**Python's GIL isn't the bottleneck.** CTranslate2 releases the GIL while it computes, and HTTP waits release it too. Plain threads are enough; multiprocessing and asyncio add nothing.

**Audio isn't at risk.** The `sounddevice` callback runs on its own thread, so a stalled loop only lengthens the next chunk.

**Metal transcription doesn't change the model.** mlx-whisper or whisper.cpp on Metal would compete with Ollama for the GPU. Stay on faster-whisper on CPU, behind a swappable seam.

**Recommended process model:** one process, four threads, joined by queues:
- the audio callback
- a transcriber thread
- one engine thread, the only thing that changes state or writes notes
- a slow-lane thread for editorial and coach work

Everything that changes the notes arrives as an event on the engine's queue: chunks, queries, UI edits, commands, slow-lane results. The engine merges queued chunks in one call. Editorial and coach calls run only when the merge backlog is empty. That scheduling rule, not more parallelism, is what stops slow calls stalling the notes.

**Not yet measured:** transcription time per 10s chunk on this machine, merge time with a 16k prompt, and how much the two slow each other when they overlap. See ticket 12.
