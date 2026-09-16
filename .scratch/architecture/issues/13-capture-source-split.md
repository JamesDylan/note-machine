# Capture-source split: mic vs system audio

Type: grilling
Status: resolved
Blocked by: 01, 02, 06

## Question

What's the seam for capturing mic and system audio as separate channels/sources — tagged onto the segment type from 06 — so note-machine can (a) work when the Operator is on headphones, where system audio no longer leaks back into the mic, and (b) tell Operator speech from others' on every segment, giving "me vs. them" without diarization?

## Context

- **Trigger:** on headphones the built-in mic only picks up the Operator's voice — meeting audio never reaches it, so the transcript is one-sided. Today's pipeline (`live_notes.py:780`) opens one mono `sd.InputStream` with no system-audio capture at all; it works on speakers only because the mic incidentally picks up the room's own playback.
- **From 02 (Local-first peer architectures):** Anarlog keeps mic and speaker as separate channels, getting "me vs. them" without diarization. Both peers use a macOS Core Audio process tap (14.2+) for system audio; the clean route for a Python tool is a small Swift helper based on AudioCap (BSD-2) piping to stdout — not BlackHole (GPL-3.0, manual driver install).
- **From Core domain language (01):** only the Operator's Commands apply directly; everyone else's speech becomes a Proposal. Capture has no way to make that distinction today — this ticket is what would make it possible.
- **Open sub-questions carried from map.md "Capture-source details":** how chunk boundaries (VAD-cut vs fixed 10s) interact across two sources; whether PyObjC can run the tap's real-time callback without glitches; minimum macOS version (Apple docs say 14.2, AudioCap's README says 14.4).
- **Dependency on 06:** needs the Item/segment provenance shape decided there to know where a per-segment "source" (mic vs system) tag lives, so a Merge op can carry it through to authorship.

## Why brought forward

Originally listed under map.md "Not yet specified" behind the full capture-source backlog (imported recordings, business context, etc.). Pulled forward on its own because the same mechanism (separate mic/system channels) closes an active usability gap (headphones) and delivers a horizon feature (speaker attribution) in one slice, rather than two.

## Answer

**The source split is binary and permanent: `mic` = Operator, `system` = everyone else, mixed and undifferentiated.** No per-attendee attribution, now or as a step toward diarization later — `Author` for non-Operator speech is already resolved by the existing Proposal-acceptance rule (an accepted Proposal's Ops are authored by the Operator who accepted it), so `source` never needs to know which attendee spoke, only whether it was the Operator.

**Per-source chunking stays independent; Merge triggering is batched across sources, not per-chunk.** Each source keeps cutting its own chunks on its own acoustic terms, unchanged from today. Merge fires on a fixed cadence tick that gathers whatever new Transcript lines exist from either or both sources since the last tick, rather than firing the instant one source's chunk finishes decoding. A silent source contributes nothing that tick and never blocks the other. This keeps Merge/Gist granularity and Editorial cadence exactly as they are today — triggering Merge per-source-chunk would have roughly doubled Merge/Gist frequency and halved the wall-clock gap between Editorial passes (expensive, per 12's benchmark), while also fragmenting each Gist to only half a conversation window at a time.

**No echo cancellation.** Mic bleed on speakers (the mic picking up the room's own playback) is the same cross-correlation problem AEC libraries solve, but 02 already put "in-app mixing and echo cancellation" in the Skip list. Reopening it wasn't justified against the instruction to keep this simple.

**A headphone-detection gate, checked once at Session start, decides whether `mic`=Operator is trusted.** On headphones, system audio never reaches the mic and the split is clean, so it's trusted. Off headphones, fall back entirely to today's single-source, undifferentiated behavior — no attempt at "them" attribution, avoiding the risk of bled-through attendee speech being misrouted as a directly-applied Operator Command. The check is one-time at Session start, not continuous; catching a mid-meeting headphones↔speakers switch is deliberately deferred, not decided against — **flagged as future scope**.

**One shared Whisper model instance, queued, serves both sources.** Not two separate instances. Two instances would roughly double memory/compute cost for a benefit (low-latency handling of simultaneous mic+system speech) that's likely rare; a shared queue accepts a small latency cost on the rare overlap case instead.

**The system-audio tap covers whole system output, not a specific process.** Per-process tapping (Core Audio 14.2+ supports it) would need a way to identify "which process is the meeting" and was judged unnecessary for now. Revisit if whole-system noise (notifications, other apps) proves too disruptive in practice.

**A mechanism failure degrades to mic-only, visibly.** If headphones are detected but the tap/helper itself fails (crash, permission denied, unsupported macOS) at Session start, degrade to mic-only and print a message — matching the pipeline's existing visible-drop-reason pattern (e.g. `[dropped: hallucinated silence]`). Don't block Session start over it; don't degrade silently either.

Findings for later tickets:
- **06** still owes the mechanics of how the Merge pass uses `source` (already a Transcript-line field per 01) to decide an Op's Author/Command-routing (Operator-direct vs. Proposal). This ticket assumed that rule exists but didn't design it.
- **08** (module seams/process model) needs to account for: two independently-clocked capture sources, one shared Whisper instance behind a decode queue, and the Merge-batching tick described above.
- Split off as its own ticket: **14 — capture-source feasibility spike** (PyObjC real-time callback reliability, true macOS version floor, AudioCap/AudioTee behavior in practice). Every decision above assumes the tap mechanism works; nothing here confirms that it does.
