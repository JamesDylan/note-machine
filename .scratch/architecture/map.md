# Map — note-machine long-term architecture

Label: wayfinder:map
Charted: 2026-09-14

## Destination

A **locked architecture blueprint**: target module layout and core contracts (item/op/provenance, single writer, module seams and process model, extension shape, eval workbench and gate) decided and written down as `CONTEXT.md` (glossary), `docs/adr/`, `docs/architecture.md` (module map) and a repo-level `CLAUDE.md` agent guide — ready to slice into build tickets with `/to-tickets`. No code moved.

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

## Not yet specified

- **Engine ↔ UI transport** — how a browser view gets state and posts edits (localhost server, push vs poll, file-watch). Hangs on the single-writer and process-model decisions. The peer research suggests the view is one more event subscriber that posts op proposals rather than writing directly.
- **Capture-source details** — system audio on macOS, speaker attribution, importing recordings/transcripts; how chunk boundaries (VAD-cut vs fixed 10s) interact with multiple sources. Leads from research: a Core Audio process-tap Swift helper piping to stdout (AudioCap, BSD-2); separate mic and speaker channels give "me vs. them" without diarization; streaming Silero via onnxruntime for silence cuts. Unconfirmed: PyObjC real-time viability, macOS 14.2 vs 14.4. Commands can come from anyone, but only the Operator's apply directly, so capture must be able to tell the Operator's speech from others'.
- **Business-context store** — where project/initiative context lives, how it's retrieved per chunk without bloating a 4B model's prompt, and whether it links to the main memory system (`~/hobbes/memory_system`, `ingest`). Also how Findings are requested from Outside agents (Jira, Claude, Rovo, OpenClaw) and carried as Proposals.
- **Session lifecycle** — what "done" is for a meeting (auto-stop on silence, final editorial pass, clean Ctrl+C), session folder layout, where finished notes land long-term. Session end is now meaningful: it is when Left for review appears, and resuming continues the same Session.
- **Configuration model** — module-level constants and import-time path resolution → something per-session/per-run that evals can vary (A vs B) without code edits.
- **Migration path** — how to get from the single file to the target modules without breaking live use (incremental extraction behind the eval gate vs rewrite).

## Out of scope

- Doing the refactor / building features — this map ends at the blueprint.
- Feature UX specs (live view layout, coach card design, command phrasing) — the blueprint only guarantees their seams.
- Prompt and model-quality tuning, model selection for quality — except where the op-vocabulary prototype needs a comparison run.
- Choosing a hosting / multi-user deployment target — deliberately left open.
