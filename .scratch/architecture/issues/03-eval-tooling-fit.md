# Eval tooling fit for sequential document replay

Type: research
Status: resolved
Blocked by: —

## Question

Can off-the-shelf eval tooling (Promptfoo, Langfuse, and credible alternatives such as Inspect or DeepEval) evaluate a *document assembled over ~200 sequential LLM merge calls* replayed from a transcript — fully locally — with a side-by-side A/B view, recorded human verdicts, and custom deterministic metrics (median item length, duplicate rate, rewrite depth)? What is the minimum integration with the existing Python runner, and is borrowing a viewer cheaper than a tiny purpose-built one?

## Context

- `evals/run_evals.py` replays real transcripts through the production path; memo §05 suggests keeping it as the runner and borrowing only the viewing layer.
- Findings: branch `research/eval-tooling-fit` (commit `b88281c`), file `.scratch/architecture/research/eval-tooling-fit.md` on that branch.

## Answer

Only partly. Promptfoo, Langfuse, Inspect and Phoenix can all replay a whole transcript locally as one test case with custom metrics. None records an accumulating "A better / B better / too close" verdict per transcript per change:
- Promptfoo has per-cell ratings only.
- Langfuse comes closest, but self-hosting it means six services.
- Inspect has no view for comparing two runs.

DeepEval and Braintrust need a cloud account to compare runs. OpenAI Evals doesn't take custom code.

Before/after runs are two git commits, so this is comparing two separately recorded runs, not variants inside one config.

**Recommendation:** build our own. It's about 400–500 lines of plain Python with no new dependencies:
- one file per run (stats, state, markdown, op log)
- a shared metrics module
- a localhost compare page that shows A and B blind and appends to `verdicts.jsonl`
- a per-call log

Keep the `run_evals.py` exit code as the gate. The decision worth locking is those four file formats, not which viewer to use. They map onto Langfuse and Phoenix concepts, so either could be added later as an exporter.

**Requirements for other decisions:**
- The configuration model must let a variant run from a checkout without code edits.
- The op log must carry item ids, which rewrite depth and traces both depend on.

**Unverified:**
- how Langfuse's categorical scores behave inside its compare view
- whether Inspect's viewer lets you edit scores
- whether Phoenix lets you annotate in its compare view
