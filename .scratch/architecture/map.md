# Map — note-machine long-term architecture

Label: wayfinder:map
Charted: 2026-09-14

## Destination

**Revised 2026-09-16** (was: locked blueprint before any code moves). The destination is now a working architecture reached through small, shippable slices, not a document finished before building starts:

- Decide just enough of a contract (item/op/provenance, single writer, module seams, extension shape, eval gate) to make **one next slice safe**, then stop deciding.
- Build that slice as real code, behind the existing eval gate (`evals/run_evals.py`), and use it in a real meeting — not a demo.
- Let what the slice teaches feed back into the next decision. A slice that breaks or surprises is evidence, not a failure.
- The tool stays usable throughout — slices extend or sit behind current behavior (strangler fig), never a big-bang rewrite.
- `CONTEXT.md`, `docs/adr/`, `docs/architecture.md`, and a repo-level `CLAUDE.md` still get written, but incrementally, as each slice's decisions harden — not as one upfront document.

## Notes

- **Domain:** note-machine — live mic → Whisper → LLM merge → structured, always-shareable meeting notes (Python, one 1,205-line `live_notes.py` today; Ollama `qwen3.5:4b`, faster-whisper `small.en`; Obsidian vault as the file surface).
- **"Lightweight" means lightweight to maintain:** small modules, few abstractions, easy for an agent to hold in its head. Where it runs (local vs hosted) is deliberately left open — don't decide it, don't foreclose it.
- **Horizon the seams must accommodate:** live browser view + UI edits; commands (voice/silent/typed) + coach/nudges; business context (glossary, project context, Jira, internal-doc research); more capture sources (system audio, speaker attribution, imported recordings). Plus the eval A/B workbench. Longer-term: note-machine reaching out to the Operator's other tools and agents (Jira, Claude, Rovo, OpenClaw) to link mentions, fetch status and answer questions or resolve actions in real time — not being built, but the extension seam must not foreclose it.
- **Skills:** `/grilling` + `/domain-modeling` by default (update `CONTEXT.md` inline, offer ADRs sparingly); `/codebase-design` for seams/extension/agent-framework tickets; `/prototype` for the op-vocabulary ticket; `/research` for AFK facts.
- **Source docs:** `note-machine-concept-memo.html` (bundled page — extract the `__bundler/template` script's JSON string to read it), `PLAN.md`, `Feature scratchpad.md`, `README.md`, `evals/run_evals.py`, session `state_*.json` files as evidence.
- **Tracker:** local markdown (GitHub remote `JamesDylan/note-machine` not reachable from the active `gh` account). Tickets in `issues/`, research findings on `research/<name>` branches.
- Output docs are explicitly requested by this effort (overrides the parent vault's "no proactive .md files" rule for these four artefacts only).

## Decisions so far

<!-- one line per closed ticket: [title](issues/NN-slug.md) — gist -->

- [Eval tooling fit for sequential document replay](issues/03-eval-tooling-fit.md) — no tool records accumulating A/B verdicts locally without heavy setup; build a small own workbench (run file, op log, verdict log, metrics module) and keep `run_evals.py` exit code as the gate
- [Local compute concurrency (Whisper + LLM + coach)](issues/04-local-compute-concurrency.md) — Ollama does one call at a time for this model and the GIL isn't the bottleneck; proposed model is one process, four threads on queues (single engine thread, slow lane only when the merge backlog is empty); stay on faster-whisper CPU behind a seam
- [Local-first peer architectures (Anarlog, Meetily)](issues/02-local-first-peer-architectures.md) — both are one process piping capture → VAD → STT → LLM → storage with an event-out UI; Meetily abandoned a split backend. Copy segment type, per-source channels, event fan-out, propose-only agents; skip plugin SDKs and vendor registries
- [Core domain language](issues/01-core-domain-language.md) — `CONTEXT.md` written (42 terms). Items are current or retired, never deleted. Locks are time-based. Provenance is per-Op segment-level lines. Merge is the pass and Combine is the op. Anyone can give a Command, with non-Operator changes becoming Proposals. Outside Findings reach the Notes only via Proposal
- [Op vocabulary: does update survive?](issues/05-op-vocabulary.md) — no: Merge ops are add / supersede / resolve, and fixing an Item retires it and writes a new one. Add-only repeated points and lost facts; update and supersede tied, and supersede was chosen because it keeps history. The Editorial pass's reword, Combine and Split also supersede and apply directly, not as Proposals
- [Benchmark local pipeline latency](issues/12-benchmark-local-pipeline-latency.md) — merge_chunk ~5.9s and editorial_pass ~127s at realistic 62k-char context (a ~22x gap, confirming editorial needs a distinct slow lane); concurrent Whisper decode costs merge ~+35% in the steady state. Whisper's own per-chunk latency is still unmeasured (benchmark used synthetic noise, which VAD rejected instantly rather than transcribing it) — treat process-model timing as provisional until a real-speech measurement exists. Editorial pass also mostly failed to apply its own edits (5/7 rejected on invented IDs) — a quality finding for 06/10, not latency
- [Capture-source split: mic vs system audio](issues/13-capture-source-split.md) — binary split only (`mic`=Operator, `system`=everyone else, no diarization); per-source chunking independent but Merge batches across sources on a fixed tick so cadence doesn't double; no echo cancellation; a one-time headphone-detection gate at Session start decides whether the split is trusted, else fall back to today's single-source behavior; one shared Whisper instance queued for both sources; whole-system audio tap for now; mechanism failure degrades to mic-only, visibly. Feasibility unknowns (PyObjC callback reliability, macOS version floor, AudioCap behavior) split off to ticket 14

## Not yet specified

- **Engine ↔ UI transport** — how a browser view gets state and posts edits (localhost server, push vs poll, file-watch). Hangs on the single-writer and process-model decisions. The peer research suggests the view is one more event subscriber that posts op proposals rather than writing directly.
- **Capture-source details (remaining)** — importing recordings/transcripts; streaming Silero via onnxruntime for silence cuts. The mic-vs-system-audio half of this is decided (ticket 13); whether the tap mechanism actually works is now ticket 14 (feasibility spike).
- **Business-context store** — where project/initiative context lives, how it's retrieved per chunk without bloating a 4B model's prompt, and whether it links to the main memory system (`~/hobbes/memory_system`, `ingest`). Also how Findings are requested from Outside agents (Jira, Claude, Rovo, OpenClaw) and carried as Proposals.
- **Session lifecycle** — what "done" is for a meeting (auto-stop on silence, final editorial pass, clean Ctrl+C), session folder layout, where finished notes land long-term. Session end is now meaningful: it is when Left for review appears, and resuming continues the same Session.
- **Configuration model** — module-level constants and import-time path resolution → something per-session/per-run that evals can vary (A vs B) without code edits.
- **Migration path** — how to get from the single file to the target modules without breaking live use (incremental extraction behind the eval gate vs rewrite).

## Out of scope

- Slices bigger than "decide just enough, ship, learn" — no slice should require locking more than one contract to be safe to build.
- Feature UX specs (live view layout, coach card design, command phrasing) — slices only need to guarantee the seam, not the final UX.
- Prompt and model-quality tuning, model selection for quality — except where a slice needs a comparison run to validate itself.
- Choosing a hosting / multi-user deployment target — deliberately left open.

## Slices

<!-- one line per slice: [title](issues/NN-slug.md) — what it ships, what it tests, real-use verdict -->

- Next up: **Item & provenance contract as a real module** (ticket 06) — extract the Item/state logic out of `live_notes.py` into its own file, identical behavior, gated by `evals/run_evals.py`, used in the next real meeting. Tests: can a module be pulled out without breaking a live session; validates 06's decisions against real use.
- Decided, not yet built: **Capture-source split — mic vs system audio** (ticket 13, decided; building it is blocked by 06) — same mechanism (separate mic/system channels) fixes the headphones one-sided-transcript gap and delivers "me vs. them" provenance without diarization. Slots in right after 06, ahead of 08 (module seams), since 08's process model needs to account for a second capture source. Needs ticket 14 (feasibility spike) run first, to confirm the tap mechanism this ticket assumes actually works.
- Queued: single-writer reconciliation for the two writers that exist today (07); session lifecycle auto-stop + "Left for review" marker; configuration model as one per-session file; ticket 14 (capture-source feasibility spike) ahead of building 13.
