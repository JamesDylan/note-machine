# Module seams & process model

Type: grilling
Blocked by: 02, 04, 06, 07, 12, 13

## Question

What modules does note-machine split into, what does each own, what are the interfaces between them, and what runs concurrently (threads / processes / async)? Sized for "lightweight to maintain" — small deep modules, few abstractions — and including where model-provider and capture-source swapping happen. Result feeds `docs/architecture.md`.

## Context

- `live_notes.py` is 1,205 lines in one loop; module-level constants and import-time path resolution (`SESSION_SLUG` at `:136`).
- Use `/codebase-design` vocabulary.
- Starting proposal from Local compute concurrency (Whisper + LLM + coach): one process, four threads joined by queues (audio callback, transcriber, single engine thread, slow lane). Chunks are merged in batches, and editorial and coach calls run only when the merge backlog is empty.
- Local-first peer architectures (Anarlog, Meetily) agrees: stay in one process (Meetily abandoned its split Python backend). Stages are sources → segmenter → transcriber → state owner → renderers, with a narrow segment type after capture and separate channels per source. Only Ollama, a Swift system-audio helper and hook commands run outside the process.
