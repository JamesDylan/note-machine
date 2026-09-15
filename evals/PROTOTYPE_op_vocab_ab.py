"""
PROTOTYPE — throwaway. Answers wayfinder ticket 05, "Op vocabulary: does
update survive?". Do not merge to main.

Replays the eval transcripts through the production merge path three times,
changing only the op vocabulary the merge prompt offers:

  A  update     add / update / resolve          (production today)
  B  add-only   add / resolve                   (no revision at merge time;
                                                 the editorial pass keeps reword)
  C  supersede  add / supersede / resolve       (revision retires the old item
                                                 and mints a new one, per CONTEXT.md)

Everything else — guidance, retries, num_ctx, temperature, the editorial
pass, the duplicate guard — is identical across variants, because the
variant is applied by rewriting three known lines of the merge prompt on
its way out of live_notes.merge_chunk rather than by forking the code.

Run:  python evals/PROTOTYPE_op_vocab_ab.py [transcript-name ...]
Out:  evals/results/PROTOTYPE-op-vocab-ab.md  (side by side + full notes)
"""

import sys
import os
import json
import glob
import time
import statistics
from datetime import datetime

EVALS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(EVALS_DIR))
import live_notes as ln
import run_evals as ev

# --- the three vocabularies -------------------------------------------------

UPDATE_OP_LINE = ('- {"op": "update", "section": "<section>", "id": "<existing ID>", '
                  '"text": "..."} — ONLY when the chunk clearly refines or supersedes '
                  'that exact existing item')
UPDATE_GUIDANCE = ('- An "update" REPLACES the item\'s text. It must be shorter than 25 words '
                   'and must not simply restate the existing item with an extra clause appended '
                   '— if the chunk adds genuinely new content, that is an "add", not an "update". '
                   'Updates that grow an item are refused.')
LOCKED_GUIDANCE = "- Items marked LOCKED were edited by hand. Never update or reword them."

SUPERSEDE_OP_LINE = ('- {"op": "supersede", "section": "<section>", "id": "<existing ID>", '
                     '"text": "..."} — ONLY when the chunk clearly refines or supersedes '
                     'that exact existing item; the old item is retired and this wording '
                     'replaces it as a new item')
SUPERSEDE_GUIDANCE = ('- A "supersede" RETIRES the item and replaces it with this wording. It must be '
                      'shorter than 25 words and must not simply restate the existing item with an '
                      'extra clause appended — if the chunk adds genuinely new content, that is an '
                      '"add", not a "supersede". Supersedes that grow an item are refused.')
ADDONLY_GUIDANCE = ('- There is no way to revise an item mid-meeting. If the chunk only rewords or '
                    'sharpens something already listed, say nothing; if it carries genuinely new '
                    'content, that is an "add".')

VARIANTS = {
    "A-update":    {"op_line": UPDATE_OP_LINE,    "guidance": UPDATE_GUIDANCE,    "revise": "update"},
    "B-add-only":  {"op_line": None,              "guidance": ADDONLY_GUIDANCE,   "revise": None},
    "C-supersede": {"op_line": SUPERSEDE_OP_LINE, "guidance": SUPERSEDE_GUIDANCE, "revise": "supersede"},
}


def rewrite_prompt(prompt: str, variant: dict) -> str:
    """Swap the revision op out of the merge prompt. Loud on mismatch — a
    silent no-op here would make the A/B meaningless."""
    for needle in (UPDATE_OP_LINE, UPDATE_GUIDANCE):
        if needle not in prompt:
            raise SystemExit(f"PROTOTYPE out of date: merge prompt no longer contains:\n{needle}")
    op_line = variant["op_line"]
    prompt = (prompt.replace(UPDATE_OP_LINE + "\n", op_line + "\n") if op_line
              else prompt.replace(UPDATE_OP_LINE + "\n", ""))
    prompt = prompt.replace(UPDATE_GUIDANCE, variant["guidance"])
    if variant["revise"] != "update":
        verb = "supersede" if variant["revise"] else "change"
        prompt = prompt.replace(LOCKED_GUIDANCE,
                                f"- Items marked LOCKED were edited by hand. Never {verb} or reword them.")
    return prompt


# --- variant-aware ops ------------------------------------------------------

def make_apply_ops(variant: dict, tally: dict):
    """Wraps production apply_ops, adding the supersede op for variant C and
    counting ops by kind. Supersede reuses the existing retirement flag so
    render / outline / counts already ignore the old item, and marks it
    superseded_by so the duplicate guard lets its replacement through —
    only a human Tombstone blocks a re-add (CONTEXT.md)."""
    orig = ln.apply_ops
    orig_find_dup = ln.find_duplicate

    def find_duplicate_skipping_superseded(state, section, text):
        pruned = dict(state)
        pruned[section] = [it for it in state.get(section, []) if not it.get("superseded_by")]
        return orig_find_dup(pruned, section, text)

    def apply(state, ops):
        for op in ops:
            tally["emitted"][op.get("op")] = tally["emitted"].get(op.get("op"), 0) + 1
        tally["chunks_with_ops"] += 1 if ops else 0
        passthrough, applied = [], 0
        for op in ops:
            if op.get("op") == "supersede" and variant["revise"] == "supersede":
                applied += apply_supersede(state, op, tally)
            else:
                passthrough.append(op)
        ln.find_duplicate = find_duplicate_skipping_superseded
        try:
            applied += orig(state, passthrough)
        finally:
            ln.find_duplicate = orig_find_dup
        tally["applied"] += applied
        return applied

    def apply_supersede(state, op, tally):
        section = op.get("section")
        if section not in ln.ITEM_SECTIONS:
            return 0
        item = ln.find_item(state, section, ln.norm_id(op.get("id")))
        text = ln.clean_text(op.get("text", ""))
        if item is None or not text:
            return 0
        if item.get("locked"):
            return 0
        old_t, new_t = ln.tokens(item["text"]), ln.tokens(text)
        grew = len(new_t) > len(old_t) + 6
        if grew and ln.containment(old_t, new_t) >= ln.DUP_THRESHOLD:
            tally["revisions_refused"] += 1
            return 0
        if len(text.split()) > ln.MAX_UPDATE_WORDS:
            tally["revisions_refused"] += 1
            return 0
        new_item = {"id": ln.mint_id(state, section), "text": text,
                    "t": item.get("t") or datetime.now().strftime("%H:%M")}
        for k in ("owner", "group", "resolved", "answer"):
            if item.get(k):
                new_item[k] = item[k]
        new_item["supersedes"] = item["id"]
        item["deleted"] = True          # retired: invisible to render, outline, counts
        item["superseded_by"] = new_item["id"]
        state[section].append(new_item)
        tally["revision_chain"][new_item["id"]] = tally["revision_chain"].get(item["id"], 0) + 1
        tally["revisions_applied"] += 1
        return 1

    return apply


# --- metrics ----------------------------------------------------------------

def current_items(state):
    out = []
    for section in ln.ITEM_SECTIONS:
        for it in ln.live_items(state, section):
            out.append((section, it))
    return out


def duplicate_rate(state) -> float:
    """Share of current items that say substantially the same thing as
    another current item in the same section — the accretion smell."""
    flagged, total = 0, 0
    for section in ln.ITEM_SECTIONS:
        items = ln.live_items(state, section)
        total += len(items)
        for i, a in enumerate(items):
            ta = ln.tokens(a.get("text", ""))
            if not ta:
                continue
            for j, b in enumerate(items):
                if i == j:
                    continue
                tb = ln.tokens(b.get("text", ""))
                if tb and max(ln.containment(ta, tb), ln.containment(tb, ta)) >= ln.DUP_THRESHOLD:
                    flagged += 1
                    break
    return (flagged / total) if total else 0.0


def run_variant(path: str, name: str, variant: dict) -> dict:
    chunks = ev.parse_chunks(path)
    state = json.loads(json.dumps(ln.DEFAULT_STATE))
    tally = {"emitted": {}, "applied": 0, "chunks_with_ops": 0, "revisions_applied": 0,
             "revisions_refused": 0, "revision_chain": {}, "merge_failures": 0}

    orig_post, orig_apply = ln.requests.post, ln.apply_ops

    def patched_post(url, **kw):
        payload = kw.get("json") or {}
        if "Op types:" in payload.get("prompt", ""):
            payload["prompt"] = rewrite_prompt(payload["prompt"], variant)
        return orig_post(url, **kw)

    ln.requests.post = patched_post
    ln.apply_ops = make_apply_ops(variant, tally)
    started = time.time()
    try:
        for i, chunk in enumerate(chunks):
            state = ln.merge_chunk(state, chunk)
            if (i + 1) % ln.EDITORIAL_EVERY_N_CHUNKS == 0:
                window = "\n".join(chunks[max(0, i + 1 - ln.EDITORIAL_WINDOW_LINES):i + 1])
                state = ln.editorial_pass(state, window)
        if chunks:
            state = ln.editorial_pass(state, "\n".join(chunks[-ln.EDITORIAL_WINDOW_LINES:]))
    finally:
        ln.requests.post, ln.apply_ops = orig_post, orig_apply

    markdown = ln.render_markdown(state)
    lengths = [len(it["text"].split()) for _, it in current_items(state)]
    return {
        "transcript": name, "variant": variant["label"], "chunks": len(chunks),
        "seconds": round(time.time() - started),
        "emitted": tally["emitted"], "applied": tally["applied"],
        "silent_chunks": len(chunks) - tally["chunks_with_ops"],
        "revisions_applied": tally["revisions_applied"],
        "revisions_refused": tally["revisions_refused"],
        "max_revision_chain": max(tally["revision_chain"].values(), default=0),
        "final_items": ln.total_items(state),
        "median_words": statistics.median(lengths) if lengths else 0,
        "max_words": max(lengths, default=0),
        "duplicate_rate": round(duplicate_rate(state), 3),
        "facts": ev.check_facts(name, markdown),
        "markdown": markdown,
    }


def main():
    only = set(sys.argv[1:])
    paths = sorted(glob.glob(os.path.join(ev.TRANSCRIPTS_DIR, "*.log")))
    if only:
        paths = [p for p in paths if os.path.splitext(os.path.basename(p))[0] in only]

    runs = []
    for path in paths:
        name = os.path.splitext(os.path.basename(path))[0]
        for key, variant in VARIANTS.items():
            variant = dict(variant, label=key)
            print(f"\n######## {name} / {key} ########", flush=True)
            runs.append(run_variant(path, name, variant))

    os.makedirs(ev.RESULTS_DIR, exist_ok=True)
    out = os.path.join(ev.RESULTS_DIR, "PROTOTYPE-op-vocab-ab.md")
    with open(out, "w") as f:
        f.write(report(runs))
    print(f"\nreport: {out}")


def report(runs) -> str:
    L = ["# PROTOTYPE — op vocabulary A/B/C",
         f"*{datetime.now().strftime('%Y-%m-%d %H:%M')}, model {ln.OLLAMA_MODEL}, "
         f"one run per cell, temperature 0*", "",
         "A = add/update/resolve (today) · B = add/resolve · C = add/supersede/resolve", ""]
    by_transcript = {}
    for r in runs:
        by_transcript.setdefault(r["transcript"], []).append(r)
    for name, group in by_transcript.items():
        L += [f"## {name}", "",
              "| metric | " + " | ".join(r["variant"] for r in group) + " |",
              "|---|" + "---|" * len(group)]
        def row(label, fn):
            L.append(f"| {label} | " + " | ".join(str(fn(r)) for r in group) + " |")
        row("chunks", lambda r: r["chunks"])
        row("facts captured", lambda r: f"{sum(1 for x in r['facts'] if x['passed'])}/{len(r['facts'])}")
        row("final items", lambda r: r["final_items"])
        row("median item words", lambda r: r["median_words"])
        row("longest item words", lambda r: r["max_words"])
        row("duplicate rate", lambda r: r["duplicate_rate"])
        row("ops applied", lambda r: r["applied"])
        row("ops emitted", lambda r: json.dumps(r["emitted"]))
        row("revisions applied", lambda r: r["revisions_applied"])
        row("revisions refused", lambda r: r["revisions_refused"])
        row("max revision chain", lambda r: r["max_revision_chain"])
        row("silent chunks", lambda r: r["silent_chunks"])
        row("seconds", lambda r: r["seconds"])
        L.append("")
        for r in group:
            missed = [x["name"] for x in r["facts"] if not x["passed"]]
            if missed:
                L.append(f"- {r['variant']} missed: {', '.join(missed)}")
        L.append("")
    L += ["---", "", "# Final notes, side by side", ""]
    for name, group in by_transcript.items():
        for r in group:
            L += [f"## {name} — {r['variant']}", "", r["markdown"], ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
