# note-machine — Review & Plan

*Written 2026-09-10, based on a review of the Phase 0 MVP (`live_notes.py`), the feature scratchpad, and the outputs from the 2026-09-09 and 2026-09-10 sessions.*

## Where this is heading

The long-term vision, roughly in order of distance:

1. **Now** — live mic transcription → structured meeting notes, updated in real time, shareable mid-meeting.
2. **Next** — talk to the tool during the meeting: answer questions on the fly, make specifically requested edits to the doc.
3. **Later** — business context: glossary of company jargon, awareness of Jira tickets/initiatives so mentions get enriched with real status.
4. **Distant** — proactive: actions/questions raised in the meeting get researched against internal documentation and answered live; content generated on request.

The key architectural takeaway from the review: the current pipeline shape (audio → Whisper chunks → LLM merge into structured state → render markdown) is the right skeleton for all four stages. Everything later stacks on the structured state — so making that state stable and trustworthy is the prerequisite for everything else.

## What's working (keep these)

- **Append-only raw transcript log**, written before anything else touches the text. This is the ground truth and already covers scratchpad item "retain the transcript in a separate doc". Underused today — it should feed merges and recovery.
- **Session slug + `.current_session` pointer** — resume-after-crash works, old sessions form an archive.
- **Three-layer glossary correction** (Whisper initial_prompt bias → regex find/replace → summarizer context note).
- **Compaction pass with an over-pruning guard** (discard if >50% of items vanish).
- **Schema validation + retry** on merge output.

## The core problem: full-state rewrite every 10 seconds

Nearly every pain point on the scratchpad (notes wiped, actions overwritten, context loss) traces to one choice: **each merge asks the 4B model to regenerate the entire state JSON from scratch**. Every 10 seconds is a fresh chance for the model to silently drop items. Validation protects the *schema*, not the *content* — the >50% shrink guard only exists on the compaction path, not the merge path.

Evidence in the outputs: `Zac 1-1 meeting.md` has raw Python dicts rendered into Decisions, and a Topics section that exploded into ~40 keyword fragments — the model losing the plot as state grows.

### The fix: delta-based merge

Make the model emit **operations, not documents**:

- Model returns deltas per chunk: `add_action_item`, `add_decision`, `update_item(id, ...)`, `resolve_question(id)`.
- Our code owns the state and applies the ops. Items get stable IDs.
- Deletion becomes impossible outside the explicit compaction pass.
- The model's per-chunk job shrinks from "rewrite everything" to "what's new in the last 10 seconds" — much better suited to a small local model.

This one change addresses scratchpad items #1 (notes wiped), #7 (actions overwritten), and most output-quality issues.

## Second problem: transcript quality caps everything downstream

The 2026-09-10 raw transcript contains "expine of thinking", "the inflammation transcribing", "Soll" for SOL. No summarizer can recover from that input.

- **Cut chunks at silence, not fixed 10s.** faster-whisper has built-in VAD; segmenting on pauses stops Whisper mistranscribing clipped mid-sentence audio, and gives silence detection for auto-stop (scratchpad #5) essentially for free.
- **Bump the model.** `base.en` is too rough for meeting audio; `small.en` or `distil-small.en` is still real-time on Apple Silicon.
- **Merge less often than you transcribe.** Transcribe every chunk; merge every 3–4 chunks with the recent transcript window as context. Fewer LLM calls, each with more coherent input.

## Smaller known issues

- **Wake-phrase bug**: `extract_trigger` discards everything in a chunk *before* the wake phrase, so real meeting content in that same 10s never reaches the notes.
- **Ctrl+C (scratchpad #8)**: no KeyboardInterrupt handling; needs a try/finally that flushes state and exits cleanly.
- **`--new <title>` (scratchpad #3)**: allow a meeting title in the slug/filename so the archive is browsable.
- **Not a git repo** — init one before restructuring.
- **Outputs mixed with code**: move session files (notes/state/transcripts) into a `sessions/` subfolder, keeping the vault root clean.

## Proposed plan

### Phase 1 — Stabilise the core ✅ DONE 2026-09-10
1. ✅ Delta-based merge: ops schema, stable item IDs, code-owned state, no deletions.
2. ✅ Content guards + anti-accretion cap on updates.
3. ✅ (added) Gist-per-chunk observability; temperature 0; `num_ctx` 16384 (Ollama's default 4096 silently truncated grown prompts — major failure source).
4. ✅ (added) Eval harness in `evals/` with real-transcript replay, invariants, fact checks; gold-standard case from the Gemini-covered migration meeting.
5. ✅ (added) Editorial loop every ~5 min: reads recent transcript + notes, promotes emerged decisions, resolves answered questions with answers, merges/splits/groups, maintains a living summary. Replaces the old compaction pass.
6. ✅ (added) `--new <title>` named sessions and `--attendees` for name accuracy.

### Phase 2 — Transcript quality
7. ✅ Upgrade Whisper model to `small.en`.
8. VAD-based chunking (replaces fixed 10s windows).
9. Auto-stop after ~3 min of silence (falls out of VAD).

### Phase 3 — Quality of life
10. Clean shutdown on Ctrl+C (flush state, run one final editorial pass, print summary).
11. `git init` + move session outputs to `sessions/`.
12. Fixed meeting template support (scratchpad #6).

### Phase 4 — Toward the vision (spec these properly first)
12. Voice-requested edits to the doc (extend the wake-phrase path from Q&A to edit ops — the delta architecture makes this nearly free).
13. Business context injection: richer glossary, Jira ticket lookup on mention.
14. On-demand doc generation mid-meeting.
15. Proactive research against internal documentation.

## Open questions for the spec

- "Settle" logic: should a new bullet wait N chunks before being considered stable, so half-finished thoughts don't produce premature items?
- System audio capture (BlackHole) — when to add the other side of the call; doesn't change the core engine.
- Local model ceiling: is `qwen3.5:4b` enough once merges are delta-based, or is a bigger/cloud model warranted for the merge step specifically?
- Where do finished notes land long-term — stay in this vault, or route into the main memory system via `ingest`?
