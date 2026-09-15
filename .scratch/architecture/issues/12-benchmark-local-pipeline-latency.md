# Benchmark local pipeline latency

Type: task
Blocked by: —

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
