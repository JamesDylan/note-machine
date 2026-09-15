# Local-first peer architectures (Anarlog, Meetily)

Type: research
Status: resolved
Blocked by: —

## Question

How do the closest local-first meeting-note tools — Anarlog (ex-Hyprnote, `fastrepl/anarlog`) and Meetily — structure their pipelines: capture (mic + macOS system audio), VAD/segmentation, transcription, LLM-provider abstraction (local ↔ BYOK), extension surface (plugins, MCP, webhooks, Obsidian export) and storage? Which of those seams are worth copying for a small Python codebase, which are over-engineered for it, and which capture/VAD libraries could be reused rather than re-solved?

## Context

- Memo §01 Cluster B: "their audio + VAD layer is a solved problem you're about to re-solve."
- Findings: branch `research/local-first-peers` (commit `a0c27e0`), file `.scratch/architecture/research/local-first-peers.md` on that branch.

## Answer

**Both tools have the same shape.** Each is one desktop process running capture → VAD → speech-to-text → LLM → local storage. The UI only sends commands in and receives events out.

**Meetily tried a separate Python backend and gave it up.** Its old FastAPI server and standalone Whisper server are archived as unsupported. That's direct evidence against splitting note-machine into services.

**macOS system audio.** Both use a Core Audio process tap (macOS 14.2+). Neither uses ScreenCaptureKit or BlackHole in current code. For a Python tool, the cleanest route is a small Swift helper based on AudioCap (BSD-2) that pipes audio to stdout. BlackHole is GPL-3.0 and needs a manual driver install.

**VAD.**
- Meetily cuts segments on silence with Silero, after mixing mic and system audio.
- Anarlog keeps mic and speaker as separate channels, so it knows "me vs. them" without diarization.
- faster-whisper's built-in VAD resets on every call, so it can't set chunk boundaries while streaming.
- Streaming Silero through `onnxruntime` (already installed with faster-whisper) can set boundaries without pulling in torch.

**Copy:**
- a narrow segment type between capture and everything else, with imported recordings as just another source
- separate channels per source instead of mixing
- silence-cut segments with a wait window and a maximum length
- separate transcription and LLM seams, using one OpenAI-compatible client, with no silent fallback to cloud
- an event fan-out that the browser view and coach subscribe to
- hooks as shell commands
- agents only propose edits and one owner applies them

**Skip:**
- actor supervision trees
- registries of 20+ speech-to-text vendors
- in-app mixing and echo cancellation
- plugin SDKs
- SQLite migrations and sync
- whole-transcript map-reduce summaries

**Implication for the seams and process model:** one Python process with stages joined by queues: sources → segmenter → transcriber → state owner → renderers. Only Ollama, the Swift audio helper and hook commands run outside it. The browser view is one more event subscriber and sends op proposals, not direct writes.

**Unconfirmed:**
- whether PyObjC can run the tap's real-time callback without glitches
- how accurate webrtcvad is compared with Silero
- the minimum macOS version: Apple's docs say 14.2, AudioCap's README says 14.4
- AudioTee has no licence file, so treat it as a design reference only
