# Research: can off-the-shelf eval tooling fit note-machine's A/B eval workbench?

Label: research (map ticket: eval workbench & regression gate)
Researched: 2026-09-14/15. Every claim links to a primary source (official docs, source code, or the GitHub/PyPI API). Versions are the latest at research time; items marked **UNVERIFIED** are inferences I could not confirm from a primary source.

Versions checked: Promptfoo 0.123.0 (2026-09-10), Langfuse server v4.35.0 (2026-09-11) / Python SDK 4.15.2, Inspect AI 0.3.263, Arize Phoenix 20.11.0 (2026-09-12), DeepEval python-v4.2.0 (2026-08-24), Datasette 0.65.4 stable / 1.0a9 alpha, openai/evals last commit 2026-04-14. Sources: GitHub releases API and PyPI JSON (links in Sources).

---

## 1. Answer (short)

**Partly.** Every candidate can run the whole ~200-call replay, because each one accepts arbitrary Python as the "system under test". Treat one transcript × one variant as a single test case, and compute document-level metrics in plain Python on the final state and markdown. Requirements 3 (custom deterministic metrics) and 4 (per-call traces) are well covered by Promptfoo, Langfuse, Inspect and Phoenix.

**None of them natively records a pairwise human verdict (A better / B better / too close) that accumulates per transcript per change.** That is the owner's core ask:

- **Promptfoo** has only per-cell pass/fail/score/comment, and its source code refuses to save ratings in eval-comparison mode.
- **Langfuse** comes closest: a side-by-side experiment compare view with a baseline, plus human scores recorded in that view. But it is a six-service Docker stack.
- **Inspect** has no side-by-side view of two runs.
- **DeepEval** and **Braintrust** keep their compare UI behind a cloud account (or an Enterprise plan).
- **OpenAI Evals** does not fit.

**A before/after change is really two git revisions, not two prompts in one config.** That favours "run A, run B separately, compare the saved runs", which the tools either don't support well (Promptfoo, Inspect) or support at a heavy infrastructure cost (Langfuse).

**Recommendation:** build a tiny, dependency-free workbench:
- a run-record file per run
- a shared `metrics.py`
- a stdlib compare-and-verdict page that appends to `verdicts.jsonl`

Keep `run_evals.py`'s exit code as the regression gate. Shape the run record and trace log so Langfuse or Phoenix can be bolted on later if the page stops being enough.

---

## 2. Requirement-by-tool matrix

Legend: **Yes** = native · **Partial** = possible with glue or with caveats · **No** = not supported, or needs a cloud account.

| | Fully local, no cloud account | 1. Side-by-side A/B of two runs | 2. Pairwise human verdicts that accumulate | 3. Custom deterministic metrics | 4. Per-call traces | Ops weight |
|---|---|---|---|---|---|---|
| **Promptfoo** (MIT) | **Yes.** No login for local runs; data in SQLite under `~/.promptfoo`; telemetry is opt-out via `PROMPTFOO_DISABLE_TELEMETRY=1` [P3][P4] | **Partial.** Within one eval, providers or variants show as columns; across two separate evals, "Diff against another eval (green = added, red = removed)" [P2] | **Partial/No.** Per cell: 👍/👎, a 0–1 score, or a comment, persisted and exportable [P2]. No pairwise verdict. `ResultsTable.tsx` shows the toast *"Ratings are not saved in comparison mode"* [P7] | **Yes.** Python `get_assert` returns `namedScores`, shown as metrics in the UI; provider `metadata` is available in the assertion context [P5] | **Yes.** Built-in OTLP receiver; a Python provider can emit spans through `traceparent`; traces are stored in SQLite (30-day retention) and shown as a "Trace Timeline" per result [P6] | Low. Node/npx CLI plus YAML [P2] |
| **Langfuse** (MIT core, `ee/` dirs commercial) [L1] | **Yes, but heavy.** Self-host needs web, worker, Postgres, ClickHouse, Redis/Valkey and S3/MinIO [L2][L3]. The VM guidance is 4 cores / 16 GiB; Docker Compose "lacks high-availability, scaling capabilities, and backup functionality" [L3]. Core eval features are free when self-hosted [L4] | **Yes.** Select two experiment runs, click Compare, set a baseline; inputs and outputs side by side with score, cost and latency deltas [L5][L6] | **Partial (closest).** Human scores can be recorded in the compare view; annotation queues exist [L6][L7]. Scores can be `CATEGORICAL`, so a verdict like `A_better`/`B_better`/`too_close` is expressible [L8]. Not a native pairwise concept: you attach the verdict to one run's item. **UNVERIFIED:** exact UX for categorical score configs inside the compare view | **Yes.** `run_experiment(evaluators=[...])` returns `Evaluation(name, value, comment)`; run-level evaluators too [L9] | **Yes (best).** OpenTelemetry-based SDK v4 (`@observe`, `start_as_current_observation`); each experiment task creates a trace [L9][L10] | High. Six services, version migrations (v4 now) [L3] |
| **Inspect AI** (MIT, UK AISI) | **Yes.** pip install; `inspect view` serves logs locally [I1] | **No.** The viewer shows one log's samples, messages and events; nothing documented for comparing two logs side by side [I1]. Comparison is done in pandas over `evals_df`/`samples_df` across many logs [I2] | **Partial (API only).** `edit_score()` records `ProvenanceData(author, reason)` and keeps the full history (added 0.3.140, Oct 2025) [I3][I4]. **UNVERIFIED:** whether score editing is possible in the viewer UI. No pairwise verdict | **Yes.** A custom `@scorer` can return a dict value with several metrics [I5]; a solver can run arbitrary Python and set `state.output` without calling `generate` [I6] | **Partial.** Model calls made through Inspect's model API appear in the sample transcript [I1]. **UNVERIFIED:** calls `live_notes.py` makes directly to Ollama won't appear unless routed through Inspect's model API | Low. pip, plus log files |
| **Arize Phoenix** (Elastic License 2.0) [X1] | **Yes.** `pip install arize-phoenix && phoenix serve`; SQLite in the working dir by default [X1][X2] | **Yes.** Experiment compare view with side-by-side outputs and evaluator scores; charts across recent experiments [X3][X4] | **Partial.** Human annotations through the UI "Annotate" button on traces and spans, or via the SDK [X5]. No pairwise verdict documented. **UNVERIFIED:** annotating experiment runs directly in the compare view | **Yes.** Code evaluators on experiments [X3] | **Yes.** OpenTelemetry-native tracing [X1] | Low–medium. Single process, SQLite |
| **DeepEval** (Apache-2.0) | **Partial.** Runs locally; "A Confident AI account is optional" [D1]. Local results are JSON, and `deepeval inspect` is a terminal UI [D2] | **No (locally).** A run-comparison UI is part of Confident AI, the cloud product [D1][D3] | **No.** `ArenaTestCase` is pairwise but judged only by an LLM (`ArenaGEval`) [D4] | **Yes.** `BaseMetric` subclass [D1] | **Partial.** `@observe` traces; local viewing through the terminal UI [D1][D2] | Low, but the UI value sits in the cloud |
| **Braintrust** | **No.** `braintrust eval --no-send-logs` runs locally but produces no UI [B1]. Self-host keeps the UI and auth control plane on Braintrust and is "only available on the Enterprise plan" [B2] | Cloud only | Cloud only | Yes (SDK scorers) [B1] | Cloud only | n/a |
| **OpenAI Evals** (repo) | **Partial.** The repo runs locally, but its registry is aimed at OpenAI models; the README says "we are currently not accepting evals with custom code"; the dashboard is hosted [O1]. Last commit 2026-04-14 | No | No | Custom-code evals not accepted upstream [O1] | No | Not a fit |
| **Datasette** (+ notebook) | **Yes.** Local SQLite browser [S1] | **No** diff view out of the box [S1] | **Partial.** The write API is in the 1.0 alphas only (stable is 0.65.4); needs tokens and permissions [S2][S3] | You compute metrics yourself | No | Low, but it's just a table browser |

**Fit notes specific to note-machine:**

- **A/B = two git revisions.** The owner's use is "before/after a change". Today a variant is a code or prompt edit, and settings are module-level constants [map.md, "Configuration model"]. So an A/B is two checkouts run separately, not two providers in one config. Promptfoo's side-by-side columns only work *within* one eval, and ratings don't save in cross-eval comparison mode [P2][P7]. Langfuse and Phoenix compare separately recorded runs natively [L5][X3].
- **Runs must be serial.** `run_evals.py` monkeypatches the module global `ln.apply_ops` to count ops, and all merges hit one local Ollama model. Any tool integration must therefore run test cases one at a time:
  - Promptfoo: `-j 1` [P3]; the Python provider's `workers` defaults to 1, and global state isn't shared across workers [P1]
  - Langfuse: `max_concurrency=1` [L9]
- **Timeouts.** One transcript replay takes minutes; a full suite takes 10–15 min (README). Promptfoo's Python provider timeout defaults to 5 minutes, so raise `timeout` [P1].
- **Rewrite depth needs history.** "Rewrite depth per item" can't be computed from final state alone. The runner must also emit an op log (per item: number of `update` ops applied). Whatever the tool, that is a runner change, and it ties to the item/op/provenance contract ticket.
- **Maintenance risk.** OpenAI acquired Promptfoo in March 2026 and says it "will remain open source under the current license" [P8]. Its roadmap is pointed at security and red-teaming for OpenAI Frontier [P8]. Langfuse's OSS/EE split is by directory [L1].

---

## 3. Integration sketches (top two borrowed options) against `run_evals.py`

Both sketches assume the same small runner change first. It is needed for the purpose-built option too:

- `run_transcript()` also returns `oplog`: per chunk, the ops emitted and applied plus item ids. `run_evals.py` already wraps `ln.apply_ops`, so this is a few lines.
- A new flag, `run_evals.py --json <name>`, prints `{stats, state, markdown, oplog, git_sha, model}`.
- A shared `evals/metrics.py` holds `compute(result, expected) -> dict`: facts captured, final item count, median item length, near-duplicate rate (reusing `ln.tokens` + `ln.containment`, which already exist), and rewrite depth from `oplog`.

### 3a. Promptfoo (lowest infrastructure; weak on verdicts)

```yaml
# evals/promptfooconfig.yaml
description: note-machine transcript replay
prompts: ["{{transcript}}"]            # placeholder; the provider reads vars
providers:
  - id: file://pf_provider.py
    label: A-baseline
    timeout: 1800000                    # default is 5 min [P1]
    config: { checkout: ../../nm-baseline }   # git worktree at the baseline sha
  - id: file://pf_provider.py
    label: B-candidate
    timeout: 1800000
    config: { checkout: ../.. }
defaultTest:
  assert:
    - type: python
      value: file://pf_assert.py
tests:
  - vars: { transcript: 2026-09-10-cycle-planning }
  - vars: { transcript: 2026-09-10-migration-deltas }
tracing: { enabled: true, otlp: { http: { enabled: true } } }   # optional [P6]
```

```python
# evals/pf_provider.py   — call_api(prompt, options, context) [P1]
import json, subprocess, sys
def call_api(prompt, options, context):
    cfg = options.get("config", {})
    name = context["vars"]["transcript"]
    out = subprocess.run([sys.executable, "evals/run_evals.py", "--json", name],
                         cwd=cfg["checkout"], capture_output=True, text=True, check=True)
    r = json.loads(out.stdout)
    return {"output": r["markdown"], "metadata": {k: r[k] for k in ("state", "stats", "oplog", "git_sha")}}

# evals/pf_assert.py     — get_assert(output, context) -> GradingResult [P5]
from metrics import compute
def get_assert(output, context):
    m = compute({"markdown": output, **context["metadata"]}, context["vars"]["transcript"])
    ok = m["facts_passed"] == m["facts_total"] and m["invariant_violations"] == 0
    return {"pass": ok, "score": m["facts_passed"] / max(m["facts_total"], 1),
            "reason": f"{m['facts_passed']}/{m['facts_total']} facts", "namedScores": m}
```

Run with `PROMPTFOO_DISABLE_TELEMETRY=1 npx promptfoo@0.123.0 eval -c evals/promptfooconfig.yaml -j 1 --no-cache`, then `npx promptfoo view` [P3][P4].

- **What you get:** a per-transcript row with A and B markdown in adjacent columns, metrics per cell, filters, eval history, and optional trace timelines.
- **What you don't get:**
  - An A/B/tie verdict. You'd put a convention in a cell comment, then `promptfoo export eval <id>` and parse it [P3].
  - Accumulation of verdicts across evals.
  - Ratings in cross-eval compare mode [P7].
  - The baseline has to be re-run each time unless you keep a baseline worktree around.

**Glue:** about 40 lines of Python, 25 of YAML, a Node toolchain, and a verdict-export script.

### 3b. Langfuse self-hosted (best compare + traces; heaviest infrastructure)

```python
# evals/lf_experiment.py   — run once per checkout (baseline, candidate)
import subprocess
from langfuse import get_client, Evaluation, observe     # SDK v4 [L9][L10]
import run_evals as re_, live_notes as ln
from metrics import compute

lf = get_client()   # LANGFUSE_BASE_URL=http://localhost:3000 + project keys [L10]
ds = lf.get_dataset("note-machine/transcripts")           # item.input = {"transcript": name}
ln.merge_chunk = observe(name="merge_chunk")(ln.merge_chunk)          # per-call spans
ln.editorial_pass = observe(name="editorial_pass")(ln.editorial_pass)
# note: replace the module attributes before run_transcript runs, so its ln.merge_chunk calls go through the wrapper

def task(*, item, **kw):
    return re_.run_transcript(re_.path_for(item.input["transcript"]))  # path_for: small helper to add

def doc_metrics(*, input, output, expected_output, metadata, **kw):   # kwargs per [L9]
    return [Evaluation(name=k, value=v) for k, v in compute(output, input["transcript"]).items()]

sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
ds.run_experiment(name=f"{sha}-{ln.OLLAMA_MODEL}", task=task,
                  evaluators=[doc_metrics], max_concurrency=1)
lf.flush()
```

- **Workflow:** run the script in the baseline checkout, then in the candidate checkout. In the UI, go to Experiments, select both runs, click Compare, and set the baseline [L5][L6].
- **Recording verdicts:** define a categorical score config `verdict` with `A_better | B_better | too_close`. Record it as a human score on the candidate item in the compare view [L6][L8]. Verdicts then accumulate in Langfuse's DB and can be queried per dataset item (transcript) per run (sha).
- **Traces:** each `merge_chunk` call is a nested span you can open from a failing item [L6].

**Glue:** about 40 lines of Python. The real cost is running and upgrading six services.

(Inspect and Phoenix: Inspect would be a `@solver` that calls `run_transcript` and sets `state.output`, plus a dict-valued `@scorer` [I5][I6]. That is clean, but it has no two-run compare view, which fails requirement 1. Phoenix is the lighter-weight analogue of 3b: single process, SQLite, compare view, annotations [X1]–[X5]. Its pairwise-verdict story is no better than Langfuse's, and the ELv2 licence is fine for internal use. Treat it as the fallback if a borrowed viewer is ever wanted without Docker.)

---

## 4. Build-our-own baseline cost

Dependency-free, Python stdlib only.

| Piece | What | Size (est.) |
|---|---|---|
| Runner change (needed by every option) | `oplog` capture + `--json`; write `evals/runs/<git_sha>-<label>/<transcript>.json` (stats, metrics, state, markdown, oplog, model, timestamp) | ~40 lines |
| `evals/metrics.py` (needed by every option) | facts via keyword (move `check_facts`), final item count, median item length, near-duplicate rate (`ln.tokens`/`ln.containment`), rewrite depth from `oplog` | ~80–120 lines |
| `evals/review.py` | `python evals/review.py <runA> <runB>` starts `http.server` on localhost. Serves one page per transcript: metrics table with deltas, both markdown documents side by side with left/right **randomised** (blind), an optional `difflib.HtmlDiff` tab [Y1], and three buttons. `POST /verdict` appends `{transcript, run_a, run_b, verdict, note, ts}` to `evals/verdicts.jsonl` (committed, so verdicts accumulate per transcript per change) | ~150 lines Python + ~100 lines HTML/JS |
| Per-call traces | `evals/runs/.../<transcript>.calls.jsonl`: chunk index, prompt, raw response, ops, applied count, item count. Written by the same wrapper that already counts ops; rendered as a collapsible per-chunk list on the review page | ~30 lines + ~30 in page |
| Gate | Unchanged: `run_evals.py` exit code (facts + invariant), optionally plus metric thresholds vs a stored baseline run | ~20 lines |

**Total:** about 400–500 lines, roughly a day of focused work with an agent. No new runtime dependencies, nothing to upgrade, and every artefact is a plain file an agent can read.

**What you give up versus a borrowed viewer:**
- filtering and search across many runs
- charts
- multi-user annotation queues
- polished trace timelines

At one owner, ~3–10 transcripts and a handful of changes per week, none of those is on the critical path.

**Is borrowing cheaper?** Not for this requirement set.
- **Promptfoo:** glue is comparable in size (~70 lines plus a verdict-export script), but it still leaves requirement 2 unmet and adds Node.
- **Langfuse:** meets 1, 3 and 4 best and 2 approximately, but trades ~150 lines of page code for a six-service stack. That runs against "lightweight to maintain".

---

## 5. Recommendation

1. **Build the purpose-built workbench (section 4)**, keeping `run_evals.py` as the regression gate. The decisive requirement is the accumulating pairwise human verdict on two runs from different git revisions. No off-the-shelf tool models that natively [P7][L6][I1][D4], and the page that does it is small.
2. **Make the workbench's contracts the architecture decision, not the viewer.** Define:
   - **Run record** — `evals/runs/<sha>-<label>/<transcript>.json`
   - **Call log** — `*.calls.jsonl`
   - **Verdict log** — `evals/verdicts.jsonl`
   - **Metrics module** — `compute(result, expected) -> dict[str, float]`

   These map one-to-one onto the borrowed tools' concepts:
   - dataset item = transcript
   - experiment run = sha + label
   - evaluator = metric
   - categorical score = verdict
   - span = call-log line

   So Langfuse (or Phoenix, if Docker is unwanted) can be added later as an exporter without changing the runner.
3. **Don't adopt Promptfoo for this workbench.** Its compare-mode rating limitation [P7] and single-eval column model conflict with before/after-a-commit A/B testing. It remains a reasonable choice later for a CI-style gate or prompt matrix, e.g. testing the merge prompt across several models.
4. **Don't adopt DeepEval, Braintrust or OpenAI Evals.** Their comparison UIs need a cloud account or Enterprise plan, or the tool doesn't accept custom code [D1][B2][O1].

**Trade-offs accepted:**
- You own ~250 lines of UI code. Mitigation: stdlib only, one file each.
- No cross-run analytics UI. Mitigation: run records are JSON, so an agent or pandas can answer ad-hoc questions.
- No team annotation. Not needed today; the Langfuse exporter is the escape hatch.

**Implications for other map tickets:**
- **Configuration model:** a variant needs a label and must be runnable from a checkout without code edits.
- **Item/op/provenance contract:** the single writer must emit an op log carrying item ids. This is required for rewrite depth and per-call traces whichever tooling is chosen.

---

## 6. Sources

Retrieved 2026-09-14/15.

**Promptfoo**
- [P1] Python provider — https://www.promptfoo.dev/docs/providers/python/ (source md: https://github.com/promptfoo/promptfoo/blob/main/site/docs/providers/python.md)
- [P2] Web viewer (compare/diff, cell ratings, persistence) — https://www.promptfoo.dev/docs/usage/web-ui/
- [P3] CLI (local storage `~/.promptfoo`, no login for local, `-j`, `--no-cache`, `export`) — https://www.promptfoo.dev/docs/usage/command-line/
- [P4] Telemetry — https://www.promptfoo.dev/docs/configuration/telemetry/
- [P5] Python assertions (`get_assert`, `namedScores`, context metadata) — https://www.promptfoo.dev/docs/configuration/expected-outputs/python/
- [P6] Tracing — https://www.promptfoo.dev/docs/tracing/
- [P7] Source: "Ratings are not saved in comparison mode" — https://github.com/promptfoo/promptfoo/blob/1bac48c459ab437ce3442a914b8e186029b09537/src/app/src/pages/eval/components/ResultsTable.tsx (around line 1760, main @ 1bac48c)
- [P8] Acquisition — https://www.promptfoo.dev/blog/promptfoo-joining-openai/ and https://openai.com/index/openai-to-acquire-promptfoo/ (2026-03-09)
- Exec provider (alternative to P1) — https://www.promptfoo.dev/docs/providers/custom-script/
- Release 0.123.0 — https://github.com/promptfoo/promptfoo/releases

**Langfuse**
- [L1] Licence (MIT except `ee/`, `web/src/ee/`, `worker/src/ee/`) — https://github.com/langfuse/langfuse/blob/main/LICENSE
- [L2] Self-hosting architecture — https://langfuse.com/self-hosting
- [L3] Docker Compose (resources, not for production) — https://langfuse.com/self-hosting/docker-compose; images in https://github.com/langfuse/langfuse/blob/main/docker-compose.yml (langfuse:4, langfuse-worker:4, clickhouse 25.12, minio, redis 7, postgres 17)
- [L4] OSS vs Enterprise feature table — https://langfuse.com/pricing-self-host
- [L5] Compare view baseline support (changelog 2025-11-06) — https://langfuse.com/changelog/2025-11-06-compare-view-baseline-support
- [L6] Compare experiments — https://langfuse.com/docs/evaluation/experiments/compare-experiments
- [L7] Human annotation / queues — https://langfuse.com/docs/evaluation/evaluation-methods/annotation
- [L8] Scores via SDK (`create_score`, CATEGORICAL) — https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk
- [L9] Experiments via SDK (`run_experiment`, evaluators, `max_concurrency`) — https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk
- [L10] Python SDK v4 overview (OTel, `@observe`, `LANGFUSE_BASE_URL`, `flush`) — https://langfuse.com/docs/observability/sdk/overview
- Datasets — https://langfuse.com/docs/evaluation/experiments/datasets
- Versions: server v4.35.0 (https://github.com/langfuse/langfuse/releases), SDK 4.15.2 (https://pypi.org/project/langfuse/)

**Inspect AI**
- [I1] Log viewer — https://inspect.aisi.org.uk/log-viewer.html
- [I2] Dataframes — https://inspect.aisi.org.uk/dataframe.html
- [I3] Editing logs / `edit_score` + provenance — https://inspect.aisi.org.uk/eval-logs.html
- [I4] CHANGELOG (0.3.140 `edit_score`; 0.3.162 editing unscored samples) — https://github.com/UKGovernmentBEIS/inspect_ai/blob/main/CHANGELOG.md
- [I5] Scorers — https://inspect.aisi.org.uk/scorers.html; scoring workflow / `inspect score` — https://inspect.aisi.org.uk/scoring-workflow.html
- [I6] Solvers — https://inspect.aisi.org.uk/solvers.html
- Version 0.3.263 — https://pypi.org/project/inspect-ai/

**Arize Phoenix**
- [X1] README (ELv2, `phoenix serve`, features) — https://github.com/Arize-ai/phoenix
- [X2] Default SQLite — https://github.com/Arize-ai/phoenix/blob/main/src/phoenix/config.py ("By default, Phoenix uses an SQLite database and stores it in the working directory.")
- [X3] Datasets & experiments — https://arize.com/docs/phoenix/datasets-and-experiments/overview-datasets; run experiments — https://arize.com/docs/phoenix/datasets-and-experiments/how-to-experiments/run-experiments
- [X4] Experiment charts release note (2026-07-28) — https://arize.com/docs/phoenix/release-notes/07-2026/07-28-2026-experiment-charts-span-downloads-and-root-span-filters
- [X5] Annotating in the UI — https://arize.com/docs/phoenix/tracing/how-to-tracing/feedback-and-annotations/annotating-in-the-ui
- Self-hosting — https://arize.com/docs/phoenix/self-hosting

**DeepEval**
- [D1] Evaluation intro (local-first, Confident AI optional, `BaseMetric`, `@observe`) — https://deepeval.com/docs/evaluation-introduction
- [D2] Flags and configs (`DEEPEVAL_RESULTS_FOLDER`, `deepeval inspect` TUI, `deepeval view`) — https://deepeval.com/docs/evaluation-flags-and-configs
- [D3] Repo — https://github.com/confident-ai/deepeval
- [D4] Arena test cases (LLM-judged only) — https://deepeval.com/docs/evaluation-arena-test-cases

**Braintrust**
- [B1] Run evaluations (`--no-send-logs`) — https://www.braintrust.dev/docs/platform/experiments/run
- [B2] Self-hosting (Enterprise only; control plane hosted) — https://www.braintrust.dev/docs/guides/self-hosting

**OpenAI Evals**
- [O1] https://github.com/openai/evals (README; last commit 2026-04-14 per GitHub API)

**Datasette**
- [S1] Getting started — https://docs.datasette.io/en/stable/getting_started.html
- [S2] JSON write API (latest/1.0 docs) — https://docs.datasette.io/en/latest/json_api.html
- [S3] Versions (0.65.4 stable, 1.0a9 alpha) — https://pypi.org/project/datasette/

**Python stdlib**
- [Y1] `difflib.HtmlDiff` — https://docs.python.org/3/library/difflib.html#difflib.HtmlDiff

**Local context read:** `/Users/jamesscholz/hobbes/note-machine/evals/run_evals.py`, `/Users/jamesscholz/hobbes/note-machine/README.md` (Evals section), `/Users/jamesscholz/hobbes/note-machine/.scratch/architecture/map.md`.
