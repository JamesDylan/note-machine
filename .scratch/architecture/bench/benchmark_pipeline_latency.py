"""
Throwaway benchmark for .scratch/architecture/issues/12-benchmark-local-pipeline-latency.md

Measures real local-pipeline latencies on this machine:
  A. faster-whisper small.en CPU int8, one 10s chunk
  B. Ollama qwen3.5:4b merge_chunk() call at realistic (~62k char) context
  C. Ollama qwen3.5:4b editorial_pass() call
  D. merge_chunk() latency while a background thread hammers Whisper
     (approximates transcription/merge contention on one machine)

No production code is touched. Run from the note-machine repo root with the
venv active and Ollama already serving:

    python .scratch/architecture/bench/benchmark_pipeline_latency.py

Results print to stdout; nothing is written back to repo state.
"""

import sys
import os
import json
import copy
import time
import threading
import statistics

import numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, REPO_ROOT)
import live_notes as ln  # noqa: E402

sys.path.insert(0, os.path.join(REPO_ROOT, "evals"))
from run_evals import parse_chunks  # noqa: E402

STATE_PATH = os.path.join(REPO_ROOT, "state_20260914-101147-james-lilly-1-on-1.json")
TRANSCRIPT_PATH = os.path.join(REPO_ROOT, "evals", "transcripts", "2026-09-10-migration-deltas.log")

WHISPER_REPEATS = 3
MERGE_REPEATS = 5
EDITORIAL_REPEATS = 5


def load_grown_state() -> dict:
    with open(STATE_PATH) as f:
        return json.load(f)


def load_real_chunk_and_window() -> tuple:
    chunks = parse_chunks(TRANSCRIPT_PATH)
    chunk = chunks[len(chunks) // 2]  # a representative mid-meeting chunk
    window = "\n".join(chunks[:ln.EDITORIAL_WINDOW_LINES])
    return chunk, window


def synthetic_audio(seconds: int = ln.CHUNK_SECONDS, seed: int = 0) -> np.ndarray:
    """Mono float32 16kHz noise above SILENCE_RMS so Whisper actually decodes it.
    Content doesn't matter for timing purposes -- decode cost tracks audio
    duration and model size, not transcript accuracy."""
    rng = np.random.default_rng(seed)
    n = seconds * ln.SAMPLE_RATE
    audio = rng.normal(0, 0.05, n).astype(np.float32)
    return audio


def summarize(label: str, samples: list) -> None:
    med = statistics.median(samples)
    print(f"  {label}: median={med:.2f}s  min={min(samples):.2f}s  max={max(samples):.2f}s  raw={[round(s, 2) for s in samples]}")


def bench_whisper(model) -> list:
    print("\n[A] Whisper small.en CPU int8 -- one 10s chunk")
    audio = synthetic_audio(seed=1)
    # warmup (first call pays one-time init cost)
    segments, _ = model.transcribe(audio, language="en", temperature=0, vad_filter=True,
                                    vad_parameters={"min_silence_duration_ms": 400},
                                    condition_on_previous_text=False, no_speech_threshold=0.6,
                                    compression_ratio_threshold=2.4, hallucination_silence_threshold=2.0)
    list(segments)  # force generator to run

    samples = []
    for i in range(WHISPER_REPEATS):
        audio = synthetic_audio(seed=100 + i)
        started = time.perf_counter()
        segments, _ = model.transcribe(audio, language="en", temperature=0, vad_filter=True,
                                        vad_parameters={"min_silence_duration_ms": 400},
                                        condition_on_previous_text=False, no_speech_threshold=0.6,
                                        compression_ratio_threshold=2.4, hallucination_silence_threshold=2.0)
        list(segments)
        samples.append(time.perf_counter() - started)
    summarize("transcribe(10s chunk)", samples)
    return samples


def bench_merge(state: dict, chunk: str) -> list:
    print(f"\n[B] merge_chunk() at realistic context (outline ~{len(ln.state_outline(state))} chars)")
    # warmup -- first Ollama call pays model-load/cold-start cost
    ln.merge_chunk(copy.deepcopy(state), chunk)

    samples = []
    for i in range(MERGE_REPEATS):
        started = time.perf_counter()
        ln.merge_chunk(copy.deepcopy(state), chunk)
        samples.append(time.perf_counter() - started)
    summarize("merge_chunk()", samples)
    return samples


def bench_editorial(state: dict, window: str) -> list:
    print("\n[C] editorial_pass()")
    ln.editorial_pass(copy.deepcopy(state), window)  # warmup

    samples = []
    for i in range(EDITORIAL_REPEATS):
        started = time.perf_counter()
        ln.editorial_pass(copy.deepcopy(state), window)
        samples.append(time.perf_counter() - started)
    summarize("editorial_pass()", samples)
    return samples


def bench_contention(model, state: dict, chunk: str) -> list:
    print("\n[D] merge_chunk() while Whisper runs concurrently on a background thread")
    stop = threading.Event()

    def whisper_loop():
        i = 0
        while not stop.is_set():
            audio = synthetic_audio(seed=1000 + i)
            segments, _ = model.transcribe(audio, language="en", temperature=0, vad_filter=True,
                                            vad_parameters={"min_silence_duration_ms": 400},
                                            condition_on_previous_text=False, no_speech_threshold=0.6,
                                            compression_ratio_threshold=2.4, hallucination_silence_threshold=2.0)
            list(segments)
            i += 1

    t = threading.Thread(target=whisper_loop, daemon=True)
    t.start()
    try:
        samples = []
        for i in range(MERGE_REPEATS):
            started = time.perf_counter()
            ln.merge_chunk(copy.deepcopy(state), chunk)
            samples.append(time.perf_counter() - started)
        summarize("merge_chunk() under whisper contention", samples)
    finally:
        stop.set()
        t.join(timeout=30)
    return samples


def main():
    print(f"Repo root: {REPO_ROOT}")
    print(f"State file: {os.path.basename(STATE_PATH)}")
    print(f"Transcript: {os.path.basename(TRANSCRIPT_PATH)}")

    state = load_grown_state()
    chunk, window = load_real_chunk_and_window()

    from faster_whisper import WhisperModel
    print("\nLoading WhisperModel(small.en, cpu, int8)...")
    model_load_started = time.perf_counter()
    model = WhisperModel(ln.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    print(f"  model load: {time.perf_counter() - model_load_started:.2f}s")

    whisper_samples = bench_whisper(model)
    merge_samples = bench_merge(state, chunk)
    editorial_samples = bench_editorial(state, window)
    contention_samples = bench_contention(model, state, chunk)

    print("\n=== Summary ===")
    print(f"Whisper transcribe (10s):      median {statistics.median(whisper_samples):.2f}s")
    print(f"merge_chunk (solo):            median {statistics.median(merge_samples):.2f}s")
    print(f"editorial_pass:                median {statistics.median(editorial_samples):.2f}s")
    print(f"merge_chunk (under contention): median {statistics.median(contention_samples):.2f}s")
    slowdown = statistics.median(contention_samples) / statistics.median(merge_samples)
    print(f"Contention slowdown factor:    {slowdown:.2f}x")


if __name__ == "__main__":
    main()
