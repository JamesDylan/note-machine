"""
Item & state contract for note-machine — Phase 1 slice of ticket 06
(.scratch/architecture/issues/06-item-and-provenance-contract.md), extracted
from live_notes.py with identical behavior (no logic changes), gated by
evals/run_evals.py.

Owns the item schema (DEFAULT_STATE), id minting, load/save, dedup, and the
only two ways state may be mutated: apply_ops (the fast merge loop) and
apply_edits (the editorial loop). Everything else in live_notes.py --
rendering, prompts, the mic/transcribe loop -- reads this module rather
than the other way around, so it stays a leaf module with no dependency
back on live_notes.py.
"""

import json
import os
import re
from datetime import datetime

ITEM_SECTIONS = ("decisions", "action_items", "open_questions", "topics")
SECTION_PREFIXES = {"decisions": "D", "action_items": "A", "open_questions": "Q", "topics": "T"}
MAX_UPDATE_WORDS = 40           # an update longer than this is rejected as accretion

# --- Duplicate suppression ---
DUP_THRESHOLD = 0.82            # token containment above which two items are "the same note"
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "with",
    "that", "this", "it", "is", "are", "was", "were", "be", "been", "being",
    "as", "at", "by", "from", "they", "we", "i", "he", "she", "you", "their",
    "speaker", "discussing", "noting", "regarding", "about", "will", "would",
}

DEFAULT_STATE = {
    "summary": "",       # 1-2 sentence living summary, refreshed by the editorial pass
    "attendees": [],     # from --attendees; fed to Whisper + every prompt
    "template": "default",
    "decisions": [],
    "action_items": [],
    "open_questions": [],
    "topics": [],
    "asked": [],  # {"q": ..., "a": ...} pairs from wake-phrase queries
    "next_id": 1
}


def tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOPWORDS}


def containment(inner: set, outer: set) -> float:
    """Share of `inner` present in `outer`. Asymmetric on purpose: it's how
    we spot one item being a restatement of (or a superset of) another."""
    if not inner:
        return 0.0
    return len(inner & outer) / len(inner)


def flatten_item(item) -> str:
    """Coerce any stray non-string value into readable text, so a schema
    slip never renders as a raw Python object dump."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("decision", "action_item", "item", "text", "content", "topic", "question"):
            if item.get(key):
                return str(item[key])
        return "; ".join(f"{k}: {v}" for k, v in item.items())
    return str(item)


def migrate_state(state: dict) -> dict:
    """Upgrade a pre-Phase-1 state file (flat string lists, no IDs) to the
    item-object format in place. Idempotent — already-migrated items pass
    through untouched."""
    next_id = state.get("next_id", 1)
    for section in ITEM_SECTIONS:
        items = []
        for raw in state.get(section, []):
            if isinstance(raw, dict) and "id" in raw and "text" in raw:
                items.append(raw)
            else:
                items.append({"id": f"{SECTION_PREFIXES[section]}{next_id}", "text": flatten_item(raw)})
                next_id += 1
        state[section] = items
    state["next_id"] = next_id
    state.setdefault("asked", [])
    state.setdefault("summary", "")
    state.setdefault("attendees", [])
    state.setdefault("template", "default")
    return state


def load_state(path: str) -> dict:
    """Loads the current session's state file if it exists (mid-meeting
    restart), otherwise starts fresh. Old-format files are migrated on
    load. --new always gets a brand new slug so this naturally returns
    fresh state without deleting anything."""
    if os.path.exists(path):
        with open(path) as f:
            return migrate_state(json.load(f))
    return json.loads(json.dumps(DEFAULT_STATE))  # deep copy


def save_state(state: dict, path: str):
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def mint_id(state: dict, section: str) -> str:
    item_id = f"{SECTION_PREFIXES[section]}{state['next_id']}"
    state["next_id"] += 1
    return item_id


def live_items(state: dict, section: str) -> list:
    """Items minus the ones you deleted by hand. Tombstones stay in state so
    their IDs are never reissued and a re-add can be recognised and blocked,
    but nothing downstream — rendering, prompts, counts — ever sees them."""
    return [it for it in state.get(section, []) if not it.get("deleted")]


def find_item(state: dict, section: str, item_id: str, include_deleted: bool = False):
    for item in state.get(section, []):
        if item["id"] == item_id and (include_deleted or not item.get("deleted")):
            return item
    return None


def total_items(state: dict) -> int:
    return sum(len(live_items(state, s)) for s in ITEM_SECTIONS)


def find_duplicate(state: dict, section: str, text: str):
    """The guard against the repeated-bullet failure. Returns an existing
    item (deleted ones included) that says substantially the same thing, in
    either direction: a near-copy, a restatement, or the same note with
    another clause bolted on. Checked before every add."""
    new_tokens = tokens(text)
    if not new_tokens:
        return None
    for item in state.get(section, []):
        existing = tokens(item.get("text", ""))
        if not existing:
            continue
        if max(containment(new_tokens, existing), containment(existing, new_tokens)) >= DUP_THRESHOLD:
            return item
    return None


# --- Ops: the only way the model changes notes ---

def norm_id(value) -> str:
    """Models sometimes echo IDs as '[T1]' or with stray whitespace."""
    return str(value).strip().strip("[]").strip()


ID_PREFIX_RE = re.compile(r"^\[?[DAQT]\d+\]?[:.\s-]+\s*")


def clean_text(value) -> str:
    """Flatten to a string and strip a leaked leading item ID ('T2 Some
    topic...') or stray leading punctuation that models occasionally emit."""
    text = ID_PREFIX_RE.sub("", flatten_item(value).strip())
    return re.sub(r"^[\s.:;,-]+", "", text)


def validate_ops(candidate) -> tuple:
    """Check the overall response shape. Returns (is_valid, error_message).
    Individual ops are validated (and skipped with a log line) in
    apply_ops — one bad op shouldn't discard the good ones beside it."""
    if not isinstance(candidate, dict):
        return False, "response was not a JSON object"
    if "ops" not in candidate:
        return False, 'missing "ops" key'
    if not isinstance(candidate["ops"], list):
        return False, '"ops" must be a list'
    if any(not isinstance(op, dict) for op in candidate["ops"]):
        return False, 'every entry in "ops" must be an object'
    return True, None


def add_item(state: dict, section: str, text: str, owner: str = "", stamp: str = None):
    """Single door into the item list, so the duplicate guard and the
    timestamp can't be bypassed. Returns the new item, or None if this note
    already exists (or you deleted it) and was therefore suppressed."""
    dup = find_duplicate(state, section, text)
    if dup is not None:
        if dup.get("deleted"):
            print(f"  [add suppressed] you deleted this note ({dup['id']}); not re-adding")
        else:
            print(f"  [add suppressed] duplicate of {dup['id']}")
        return None
    item = {"id": mint_id(state, section), "text": text,
            "t": stamp or datetime.now().strftime("%H:%M")}
    if owner:
        item["owner"] = owner
    state[section].append(item)
    return item


def apply_ops(state: dict, ops: list) -> int:
    """Apply model-emitted ops to code-owned state. There is deliberately
    no delete op — items can only be added, reworded, or (for open
    questions) marked resolved. Returns how many ops were applied;
    invalid ops are logged and skipped, never fatal."""
    applied = 0
    for op in ops:
        kind = op.get("op")
        section = op.get("section")
        if section not in ITEM_SECTIONS:
            print(f"  [op skipped] unknown section {section!r}: {op}")
            continue
        if kind == "add":
            text = clean_text(op.get("text", ""))
            if not text:
                print(f"  [op skipped] add with empty text: {op}")
                continue
            if add_item(state, section, text, owner=clean_text(op.get("owner", ""))):
                applied += 1
        elif kind == "update":
            item = find_item(state, section, norm_id(op.get("id")))
            text = clean_text(op.get("text", ""))
            if not text:
                print(f"  [op skipped] update with empty text: {op}")
                continue
            if item is None:
                # A refinement aimed at a nonexistent item is still real
                # content from the chunk — capture it rather than drop it.
                print(f"  [op downgraded to add] update with unknown id: {op}")
                if add_item(state, section, text):
                    applied += 1
                continue
            if item.get("locked"):
                print(f"  [op skipped] {item['id']} is locked by your edit")
                continue
            old_tokens = tokens(item["text"])
            new_tokens = tokens(text)
            # Accretion guard. The model's failure mode is restating an item
            # verbatim with ", and also..." bolted on, every chunk, until one
            # bullet is a 200-word paragraph. Previously an over-long update
            # was downgraded to an add, which turned one run-on into a column
            # of ever-longer near-copies. Now it is simply refused: the item
            # keeps its wording, and genuinely new content arrives as its own
            # add from this chunk or the editorial pass.
            grew = len(new_tokens) > len(old_tokens) + 6
            if grew and containment(old_tokens, new_tokens) >= DUP_THRESHOLD:
                print(f"  [op refused] update would append onto {item['id']} rather than replace it")
                continue
            if len(text.split()) > MAX_UPDATE_WORDS:
                print(f"  [op refused] update exceeds {MAX_UPDATE_WORDS} words: {item['id']}")
                continue
            item["text"] = text
            applied += 1
        elif kind == "resolve":
            if section != "open_questions":
                print(f"  [op skipped] resolve only applies to open_questions: {op}")
                continue
            item = find_item(state, section, norm_id(op.get("id")))
            if item is None:
                print(f"  [op skipped] resolve with unknown id: {op}")
                continue
            item["resolved"] = True
            applied += 1
        else:
            print(f"  [op skipped] unknown op {kind!r}: {op}")
    return applied


def apply_edits(state: dict, edits: list) -> tuple:
    """Apply editorial-pass edits to a COPY of state; returns (new_state,
    applied_count). Edits can restructure (merge, split, group, reword,
    resolve-with-answer, summary) and add — the only "removals" allowed
    are merges and splits, both of which preserve the information.
    Malformed edits are logged and skipped."""
    new_state = json.loads(json.dumps(state))
    applied = 0
    for edit in edits:
        if not isinstance(edit, dict):
            continue
        kind = edit.get("op")
        if kind == "summary":
            text = clean_text(edit.get("text", ""))
            if text:
                new_state["summary"] = text
                applied += 1
            continue
        if kind == "add":
            section = edit.get("section")
            text = clean_text(edit.get("text", ""))
            if section in ITEM_SECTIONS and text:
                if add_item(new_state, section, text, owner=clean_text(edit.get("owner", ""))):
                    applied += 1
            else:
                print(f"  [edit skipped] malformed add: {edit}")
            continue
        if kind == "resolve":
            item = find_item(new_state, "open_questions", norm_id(edit.get("id")))
            if item is None:
                print(f"  [edit skipped] resolve with unknown id: {edit}")
                continue
            item["resolved"] = True
            answer = clean_text(edit.get("answer", ""))
            if answer:
                item["answer"] = answer
            applied += 1
            continue
        if kind == "reword":
            section = edit.get("section")
            if section not in ITEM_SECTIONS:
                print(f"  [edit skipped] reword with bad section: {edit}")
                continue
            item = find_item(new_state, section, norm_id(edit.get("id")))
            text = clean_text(edit.get("text", ""))
            if item is None or not text:
                print(f"  [edit skipped] reword with unknown id or empty text: {edit}")
                continue
            if item.get("locked"):
                print(f"  [edit skipped] {item['id']} is locked by your edit")
                continue
            item["text"] = text
            applied += 1
            continue
        if kind == "merge":
            section = edit.get("section")
            ids = edit.get("ids")
            text = clean_text(edit.get("text", ""))
            if section not in ITEM_SECTIONS or not isinstance(ids, list) or len(ids) < 2 or not text:
                print(f"  [edit skipped] malformed merge: {edit}")
                continue
            ids = [norm_id(i) for i in ids]
            items = new_state[section]
            matched = [it for it in live_items(new_state, section) if it["id"] in ids]
            if len(matched) != len(ids):
                print(f"  [edit skipped] merge with unknown id(s): {ids}")
                continue
            if any(it.get("locked") for it in matched):
                print(f"  [edit skipped] merge touches an item you edited: {ids}")
                continue
            keep = matched[0]
            keep["text"] = text
            if any(it.get("resolved") for it in matched):
                keep["resolved"] = True
            new_state[section] = [it for it in items if it["id"] not in ids or it is keep]
            applied += 1
            continue
        if kind == "split":
            section = edit.get("section")
            texts = edit.get("texts")
            if section not in ITEM_SECTIONS or not isinstance(texts, list) or len(texts) < 2:
                print(f"  [edit skipped] malformed split: {edit}")
                continue
            item = find_item(new_state, section, norm_id(edit.get("id")))
            if item is None:
                print(f"  [edit skipped] split with unknown id: {edit}")
                continue
            if item.get("locked"):
                print(f"  [edit skipped] {item['id']} is locked by your edit")
                continue
            texts = [clean_text(t) for t in texts if clean_text(t)]
            if len(texts) < 2:
                print(f"  [edit skipped] split with <2 usable texts: {edit}")
                continue
            carried = {k: item[k] for k in ("group", "t", "owner") if item.get(k)}
            idx = new_state[section].index(item)
            replacements = [{"id": item["id"], "text": texts[0], **carried}]
            for t in texts[1:]:
                replacements.append({"id": mint_id(new_state, section), "text": t, **carried})
            new_state[section][idx:idx + 1] = replacements
            applied += 1
            continue
        if kind == "group":
            ids = edit.get("ids")
            title = clean_text(edit.get("title", ""))
            if not isinstance(ids, list) or not ids or not title or len(title) > 60:
                print(f"  [edit skipped] malformed group: {edit}")
                continue
            hit = False
            for i in ids:
                item = find_item(new_state, "topics", norm_id(i))
                if item is not None:
                    item["group"] = title
                    hit = True
            if hit:
                applied += 1
            else:
                print(f"  [edit skipped] group with no known topic ids: {edit}")
            continue
        print(f"  [edit skipped] unknown op: {edit}")
    return new_state, applied
