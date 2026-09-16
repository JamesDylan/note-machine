# Benchmark local pipeline latency

Type: task
Status: resolved
Blocked by: —
Assignee: James

## Question

What are the real latencies on this Mac (M5, 24 GB)?
- faster-whisper `small.en` CPU int8 time to transcribe one 10s chunk
- Ollama `qwen3.5:4b` time for one merge call with a realistic 16k-context prompt
- editorial-pass call time
- how much transcription and merge slow each other when they overlap

Record the numbers. They set the latency budget for chunk batching and the slow lane in Module seams & process model.

## Context

- Surfaced by Local compute concurrency (Whisper + LLM + coach), which was read-only and couldn't load models.
- Use a real transcript from `evals/transcripts/` and a grown `state_*.json` as the prompt source. No production code changes; keep any script throwaway.
- From Op vocabulary: does update survive?: one merge call on an empty state took 9.3s (first call, model possibly cold). Replays of the same transcript varied by 2–3× between runs, so control for machine load.

## Answer

Measured on this Mac (M5, 24GB), Ollama already warm, `qwen3.5:4b`, against `state_20260914-101147-james-lilly-1-on-1.json` (188 items, `state_outline()` = 62,377 chars, ~9.7k words) and a real chunk/window from `evals/transcripts/2026-09-10-migration-deltas.log`. 1 warmup call + N timed repeats each; raw values kept, not just medians (run-to-run variance is real, see below).

| Call | Repeats | Median | Range |
|---|---|---|---|
| `merge_chunk()` solo, 62k-char context | 5 | **5.86s** | 5.84–5.98s |
| `editorial_pass()` | 5 | **127.3s** (>2 min) | 124.4–138.3s |
| `merge_chunk()` while Whisper runs concurrently on a background thread | 5 | 8.01s | 7.79s–**79.78s** (1 outlier) |
| Whisper `small.en` CPU int8, one 10s chunk | 3 | 0.02s | — **not trustworthy, see caveat** |

**Caveats — read before using these numbers for budgeting:**
- **Whisper's 0.02s is an artifact, not a real number.** The benchmark fed synthetic Gaussian noise instead of real speech (no recorded audio exists in this repo). `vad_filter=True` correctly classified the noise as silence and Whisper returned almost instantly without decoding anything. This measures "VAD reject speed," not transcription speed. **Whisper's real per-chunk latency is still unmeasured** — needs a real 10s speech clip (record one, or extract audio from a future session) to answer honestly.
- **Editorial pass is far heavier than merge — 127s vs 5.9s, a ~22x gap.** It ran every 30 chunks (~5 min of meeting) in production cadence, so 127s fits inside that window today, but it eats a large chunk of the "idle" time the slow-lane proposal (ticket 04) assumed was available, and leaves little margin if the meeting gets busier or the model gets slower.
- **Editorial pass mostly failed to apply its own edits**: 5 of 7 candidate edits were rejected every run ("resolve/split/reword with unknown id") — the model invented IDs (T178–T186) that don't exist in this state file's section. Only 2/7 applied, and the same 2 applied identically across all 5 repeats (deterministic at `temperature=0`). This is a quality/correctness finding for Item & provenance contract (06) and Eval workbench (10), not a latency one — flagging it here since it surfaced during this run.
- **Contention (1.37x median slowdown) has one wild outlier** (79.78s on the first sample, ~10x the rest) — likely the background Whisper thread and/or Ollama still settling at the start of the run. The steady-state repeats (7.79–8.96s) are consistent and are the more trustworthy read: expect roughly **+35% merge latency when Whisper is running concurrently**, not an order-of-magnitude penalty — but budget for occasional worse spikes until we understand the outlier's cause.

**What this sets for Module seams (08):** merge (~6s) and editorial (~2min) are far enough apart that they can't share a naive time budget — editorial genuinely needs to be a distinct "slow lane," matching ticket 04's proposal. Concurrent Whisper decode is a moderate (not severe) tax on merge latency in the common case. Real Whisper latency remains an open gap — treat the process-model decision as provisional on that until a real-speech measurement exists.

Benchmark script (throwaway, kept for reproducibility): `.scratch/architecture/bench/benchmark_pipeline_latency.py`.
