"""
Eval harness for the note-machine merge pipeline.

Replays real meeting transcripts through the exact production code path
(merge every chunk, editorial pass at the production cadence plus one
final pass at transcript end) and reports,
per transcript:

  - capture metrics: ops emitted/applied, chunks that produced nothing,
    schema failures, invalid ops skipped
  - invariant check: item count never decreases outside editorial passes
    (the core Phase 1 guarantee — a violation fails the whole run)
  - fact checks: each "must_capture" expectation passes if any of its
    keywords appears in the final rendered notes

Usage (from the note-machine folder, venv active, Ollama running):

    python evals/run_evals.py             # run every transcript
    python evals/run_evals.py <name>      # run one, e.g. 2026-09-10-cycle-planning

Adding a new eval case:
  1. Drop the transcript in evals/transcripts/<name>.log — either the
     engine's own raw log format ("[HH:MM:SS] text" per line) or plain
     text (each non-empty line becomes one chunk).
  2. Optionally add evals/expected/<name>.json:
       {"must_capture": [
           {"name": "survey before 11am", "any_of": ["survey"]},
           {"name": "async video trial", "any_of": ["video", "record"]}
       ]}
     Keywords are case-insensitive substrings matched against the final
     rendered markdown. "name" is just a label for the report.

Results land in evals/results/<name>.md (full notes + metrics, overwritten
each run) — eyeball those after a prompt/model change to judge quality
beyond what keyword checks can see. Exit code is non-zero if any fact
check or invariant fails, so this can gate future automation.
"""

import sys
import os
import json
import re
import glob
from datetime import datetime

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(EVALS_DIR))
import live_notes as ln

TRANSCRIPTS_DIR = os.path.join(EVALS_DIR, "transcripts")
EXPECTED_DIR = os.path.join(EVALS_DIR, "expected")
RESULTS_DIR = os.path.join(EVALS_DIR, "results")

RAW_LINE_RE = re.compile(r"^\[\d\d:\d\d:\d\d\]\s*(.*)$")


def parse_chunks(path: str) -> list:
    """Accept the engine's raw log format or plain text, one chunk per line.
    Mirrors main(): hallucinated-silence lines and repeats of the previous
    chunk are dropped before merging, and wake-phrase queries are excluded
    while any meeting content before the phrase still merges."""
    chunks = []
    # Transcripts recorded before the VAD fix are full of Whisper echoing the
    # old sentence-shaped initial_prompt; filter against it so replays see
    # what the engine would see today.
    legacy_prompt = "This meeting may reference these terms and acronyms"
    last = ""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = RAW_LINE_RE.match(line)
            text = m.group(1) if m else line
            query, rest = ln.extract_trigger(text)
            if query is not None:
                text = rest or ""
            text = ln.collapse_repeats(text.strip())
            if not text or ln.is_hallucination(text, legacy_prompt):
                continue
            if ln.tokens(text) and ln.containment(ln.tokens(text), ln.tokens(last)) >= ln.DUP_THRESHOLD:
                continue
            last = text
            chunks.append(text)
    return chunks


def run_transcript(path: str) -> dict:
    name = os.path.splitext(os.path.basename(path))[0]
    chunks = parse_chunks(path)
    state = json.loads(json.dumps(ln.DEFAULT_STATE))

    stats = {
        "name": name,
        "chunks": len(chunks),
        "ops_emitted": 0,
        "ops_applied": 0,
        "silent_chunks": 0,   # merges where the model emitted zero ops
        "merge_failures": 0,  # merges that fell through all retries
        "editorial_passes": 0,
        "invariant_violations": [],
    }

    # Count ops by wrapping the same function production uses — no forked logic.
    orig_apply = ln.apply_ops

    def counting_apply(st, ops):
        stats["ops_emitted"] += len(ops)
        applied = orig_apply(st, ops)
        stats["ops_applied"] += applied
        if not ops:
            stats["silent_chunks"] += 1
        return applied

    ln.apply_ops = counting_apply
    try:
        for i, chunk in enumerate(chunks):
            before = ln.total_items(state)
            merges_before = stats["ops_emitted"] + stats["silent_chunks"]
            state = ln.merge_chunk(state, chunk)
            if stats["ops_emitted"] + stats["silent_chunks"] == merges_before:
                stats["merge_failures"] += 1  # apply_ops never ran: fell through all retries
            after = ln.total_items(state)
            if after < before:
                stats["invariant_violations"].append(
                    f"chunk {i + 1}: items dropped {before} -> {after} outside editorial pass")
            if (i + 1) % ln.EDITORIAL_EVERY_N_CHUNKS == 0:
                window = "\n".join(chunks[max(0, i + 1 - ln.EDITORIAL_WINDOW_LINES):i + 1])
                state = ln.editorial_pass(state, window)
                stats["editorial_passes"] += 1

        # Final editorial pass at end of transcript — mirrors what the last
        # few minutes of a real meeting get, and where end-of-meeting
        # agreements land.
        if chunks:
            window = "\n".join(chunks[-ln.EDITORIAL_WINDOW_LINES:])
            state = ln.editorial_pass(state, window)
            stats["editorial_passes"] += 1
    finally:
        ln.apply_ops = orig_apply

    markdown = ln.render_markdown(state)
    stats["final_items"] = ln.total_items(state)
    return {"stats": stats, "state": state, "markdown": markdown}


def check_facts(name: str, markdown: str) -> list:
    expected_path = os.path.join(EXPECTED_DIR, f"{name}.json")
    if not os.path.exists(expected_path):
        return []
    with open(expected_path) as f:
        expected = json.load(f)
    haystack = markdown.lower()
    results = []
    for fact in expected.get("must_capture", []):
        hit = any(kw.lower() in haystack for kw in fact.get("any_of", []))
        results.append({"name": fact.get("name", "?"), "passed": hit,
                        "any_of": fact.get("any_of", [])})
    return results


def write_report(result: dict, facts: list):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    s = result["stats"]
    lines = [f"# Eval: {s['name']}",
             f"*Run {datetime.now().strftime('%Y-%m-%d %H:%M')}, model {ln.OLLAMA_MODEL}, whisper n/a (text replay)*", "",
             "## Metrics",
             f"- Chunks: {s['chunks']}",
             f"- Ops emitted / applied: {s['ops_emitted']} / {s['ops_applied']}",
             f"- Silent chunks (model chose no ops): {s['silent_chunks']}",
             f"- Merge failures (all retries exhausted): {s['merge_failures']}",
             f"- Editorial passes: {s['editorial_passes']}",
             f"- Final item count: {s['final_items']}",
             f"- Invariant violations: {len(s['invariant_violations'])}"]
    for v in s["invariant_violations"]:
        lines.append(f"  - VIOLATION: {v}")
    if facts:
        lines += ["", "## Fact checks"]
        for f_ in facts:
            mark = "PASS" if f_["passed"] else "FAIL"
            lines.append(f"- [{mark}] {f_['name']} (any of: {', '.join(f_['any_of'])})")
    lines += ["", "## Final notes", "", result["markdown"]]
    path = os.path.join(RESULTS_DIR, f"{s['name']}.md")
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path


def main():
    only = set(sys.argv[1:])
    paths = sorted(glob.glob(os.path.join(TRANSCRIPTS_DIR, "*.log")) +
                   glob.glob(os.path.join(TRANSCRIPTS_DIR, "*.txt")))
    if only:
        paths = [p for p in paths if os.path.splitext(os.path.basename(p))[0] in only]
    if not paths:
        print(f"No transcripts found in {TRANSCRIPTS_DIR}")
        sys.exit(1)

    failed = False
    summary = []
    for path in paths:
        name = os.path.splitext(os.path.basename(path))[0]
        print(f"\n=== {name} ===")
        result = run_transcript(path)
        facts = check_facts(name, result["markdown"])
        report = write_report(result, facts)
        s = result["stats"]
        fact_pass = sum(1 for f_ in facts if f_["passed"])
        line = (f"{name}: {s['ops_applied']} ops applied over {s['chunks']} chunks, "
                f"{s['silent_chunks']} silent, {s['final_items']} items")
        if facts:
            line += f", facts {fact_pass}/{len(facts)}"
        if s["invariant_violations"]:
            line += f", {len(s['invariant_violations'])} INVARIANT VIOLATIONS"
            failed = True
        if facts and fact_pass < len(facts):
            failed = True
        summary.append(line)
        print(f"  report: {report}")

    print("\n==== SUMMARY ====")
    for line in summary:
        print(line)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
