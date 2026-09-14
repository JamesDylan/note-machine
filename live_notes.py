"""
Live meeting notes engine — Phase 1: delta-based merge.

Captures mic audio in memory, transcribes rolling ~10s chunks with
faster-whisper (no files touched), and updates a fixed-section structured
note via a local Ollama call, writing the result to a markdown file that
auto-refreshes if opened in Obsidian/VSCode preview.

Two-loop architecture:
- FAST loop (every ~10s chunk): the model emits OPS (add / update /
  resolve) describing only what the new chunk changes; this code owns the
  state and applies them. Items carry stable IDs (D1, A2, Q3, T4). There
  is no delete op, so the model can never silently wipe notes.
- EDITORIAL loop (every ~5 min): re-reads the recent raw transcript
  alongside the notes — context the fast loop never has — to catch
  decisions that emerge across minutes of discussion, close answered
  questions, merge duplicates, split run-ons, group topics under
  headings, and refresh the doc's summary. Merges and splits are the
  only paths that remove items, both information-preserving and guarded
  against over-shrinking.

If a chunk contains the wake phrase ("hey note machine" / "note machine"),
it's routed to direct Q&A instead of being merged into notes: answered via
Ollama (using current meeting state as context when relevant), spoken aloud
with macOS's built-in `say`, and logged in an "Asked" section.

The notes file is a two-way interface. Every rendered bullet carries its
item ID in a trailing HTML comment (invisible in Obsidian preview), so
edits you make to the file mid-meeting are read back before the next
write: reworded bullets update the item AND lock it so the model can
never overwrite your wording, and deleted bullets become tombstones that
suppress the item and block it being re-added.

No .wav files are ever written to disk — audio stays in memory as numpy
arrays and is discarded after each chunk is transcribed.
"""

import sounddevice as sd
import numpy as np
import requests
import json
import os
import re
import sys
import subprocess
import time
from datetime import datetime

# --- Config ---
SAMPLE_RATE = 16000
CHUNK_SECONDS = 10
OLLAMA_MODEL = "qwen3.5:4b"   # swap for whatever's pulled locally
OLLAMA_URL = "http://localhost:11434/api/generate"
LATEST_NOTES_PATH = "live_notes.md"  # always mirrors whichever session is active — keep this open in Obsidian
SESSION_POINTER_PATH = ".current_session"
WHISPER_MODEL_SIZE = "small.en"  # noticeably better than base.en on meeting audio; drop back if too slow
TRIGGER_PHRASES = ["hey note machine", "note machine"]
ITEM_SECTIONS = ("decisions", "action_items", "open_questions", "topics")
SECTION_PREFIXES = {"decisions": "D", "action_items": "A", "open_questions": "Q", "topics": "T"}
MAX_MERGE_RETRIES = 1
EDITORIAL_EVERY_N_CHUNKS = 30   # ~5 min at 10s/chunk — the slow "editor" loop
EDITORIAL_WINDOW_LINES = 40     # recent transcript lines shown to the editor
MAX_UPDATE_WORDS = 40           # an update longer than this is rejected as accretion
GLOSSARY_PATH = "glossary.json"
TEMPLATES_PATH = "templates.json"

# --- Transcription hardening ---
# Whisper regurgitates its own initial_prompt when handed near-silence: 60-81%
# of the lines in some earlier raw logs were the prompt read back as speech,
# which then drove the notes model into repeating the same bullet for minutes.
# Three defences, cheapest first: an energy gate before Whisper runs at all,
# Whisper's own VAD + no-speech thresholds, and a text filter on the output.
SILENCE_RMS = 0.004             # below this the chunk never reaches Whisper
MAX_NO_SPEECH_PROB = 0.6        # per-segment: discard anything Whisper itself doubts
PROMPT_ECHO_THRESHOLD = 0.65    # share of a line's words that must come from the prompt to count as an echo
HALLUCINATION_PHRASES = [       # Whisper's stock filler on silence, from training-data subtitles
    "thank you for watching", "thanks for watching", "please subscribe",
    "subscribe to my channel", "like and subscribe", "see you next time",
    "transcription by", "subtitles by", "www.", ".com",
]

# --- Duplicate suppression ---
DUP_THRESHOLD = 0.82            # token containment above which two items are "the same note"
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "with",
    "that", "this", "it", "is", "are", "was", "were", "be", "been", "being",
    "as", "at", "by", "from", "they", "we", "i", "he", "she", "you", "their",
    "speaker", "discussing", "noting", "regarding", "about", "will", "would",
}


def parse_cli(argv) -> tuple:
    """`--new [title]` starts a fresh session; the optional title becomes
    part of the filenames (e.g. live_notes_20260910-130240-zac-1-1.md).
    `--attendees "Lilly, Remy, Craig"` tells transcription and the notes
    model who is in the room — hugely improves name accuracy.
    `--template 1-1` picks the section layout and the "what matters in this
    kind of meeting" hint fed to both model loops (see templates.json)."""
    start_new, title, attendees, template = False, "", [], ""
    i = 0
    while i < len(argv):
        if argv[i] == "--new":
            start_new = True
            if i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                title = re.sub(r"[^A-Za-z0-9_-]+", "-", argv[i + 1]).strip("-").lower()
                i += 1
        elif argv[i] == "--attendees" and i + 1 < len(argv):
            attendees = [a.strip() for a in argv[i + 1].split(",") if a.strip()]
            i += 1
        elif argv[i] == "--template" and i + 1 < len(argv):
            template = argv[i + 1].strip().lower()
            i += 1
        i += 1
    return start_new, title, attendees, template


def resolve_session(start_new: bool, title: str) -> str:
    """Plain launch resumes whatever session the pointer file names.
    `--new` starts a fresh timestamped session and repoints to it —
    old session files are never touched, so they form a running archive."""
    if start_new or not os.path.exists(SESSION_POINTER_PATH):
        slug = datetime.now().strftime("%Y%m%d-%H%M%S")
        if title:
            slug += f"-{title}"
        with open(SESSION_POINTER_PATH, "w") as f:
            f.write(slug)
        print(f"Starting new session: {slug}")
    else:
        with open(SESSION_POINTER_PATH) as f:
            slug = f.read().strip()
        print(f"Resuming session: {slug} (run with --new to start a fresh one instead)")
    return slug


START_NEW, SESSION_TITLE, CLI_ATTENDEES, CLI_TEMPLATE = parse_cli(sys.argv[1:])
SESSION_SLUG = resolve_session(START_NEW, SESSION_TITLE)
NOTES_PATH = f"live_notes_{SESSION_SLUG}.md"
STATE_PATH = f"state_{SESSION_SLUG}.json"
RAW_LOG_PATH = f"raw_transcript_{SESSION_SLUG}.log"  # append-only, never overwritten — the ground truth if anything else breaks

DEFAULT_GLOSSARY = {
    "SOL": ["soul", "sole", "so long"],
    "B4B": ["bee for bee", "b for b", "before b", "before be", "bee 4 bee"]
}


def load_glossary(path: str) -> dict:
    """correct_term -> [common Whisper mishearings]. Auto-creates the file
    with a starter example on first run; edit it directly to add more
    terms as you notice new mishearings."""
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(DEFAULT_GLOSSARY, f, indent=2)
        return dict(DEFAULT_GLOSSARY)
    with open(path) as f:
        return json.load(f)


def build_whisper_prompt(glossary: dict, attendees: list) -> str:
    """Whisper supports biasing toward likely vocabulary via initial_prompt.
    Not a hard guarantee, but nudges the decoder toward these terms/names.

    Deliberately a bare comma-separated list rather than a sentence: given
    near-silence Whisper reads its own prompt back as speech, and a fluent
    sentence comes back as a plausible-looking transcript line. A fragment
    list is both less likely to be echoed and obvious when it is."""
    parts = list(attendees) + list(glossary.keys())
    return ", ".join(parts)


def correct_transcript(text: str, glossary: dict) -> str:
    """Safety net for whatever the initial_prompt bias doesn't catch —
    deterministic find/replace of known mishearings."""
    for correct_term, mishearings in glossary.items():
        for wrong in mishearings:
            pattern = re.compile(re.escape(wrong), re.IGNORECASE)
            text = pattern.sub(correct_term, text)
    return text


def glossary_context_note(glossary: dict) -> str:
    """Third layer: give the summarizer model the same glossary so it can
    self-correct at the sentence level using full context, catching cases
    the regex pass misses (different phrasing, partial matches, etc)."""
    if not glossary:
        return ""
    terms = ", ".join(glossary.keys())
    return f"\nKnown terms/acronyms used in this meeting: {terms}. If the transcript contains a phonetically similar but clearly wrong version of one of these, use the correct term instead.\n"


def attendees_note(state: dict) -> str:
    names = state.get("attendees", [])
    if not names:
        return ""
    return (f"\nPeople in this meeting: {', '.join(names)}. Use these exact "
            f"names; if the transcript has a phonetically similar wrong name, "
            f"substitute the correct one.\n")


glossary = load_glossary(GLOSSARY_PATH)


# --- Templates ---
# A template changes two things: the order and labels of the rendered
# sections, and a "focus" line telling both model loops what matters in
# this kind of meeting. It never changes what state can hold, so a section
# with items always renders even if the template omits it.
SECTION_LABELS = {"decisions": "Decisions", "action_items": "Action Items",
                  "open_questions": "Open Questions", "topics": "Discussion"}

DEFAULT_TEMPLATES = {
    "default": {
        "title": "Meeting Notes",
        "sections": ["decisions", "action_items", "open_questions", "topics"],
        "focus": ""
    },
    "1-1": {
        "title": "1:1 Notes",
        "sections": ["action_items", "open_questions", "decisions", "topics"],
        "focus": ("This is a one-on-one. What matters most: commitments each person makes, "
                  "feedback given or received, blockers and frustrations raised, and career "
                  "or development topics. Attribute action items to the person who owns them.")
    },
    "standup": {
        "title": "Standup Notes",
        "sections": ["action_items", "open_questions", "decisions", "topics"],
        "focus": ("This is a standup. What matters most: what each person is working on, "
                  "what is blocked and who is blocking it, and anything slipping its date. "
                  "Keep every item to one short line.")
    },
    "planning": {
        "title": "Planning Notes",
        "sections": ["decisions", "action_items", "open_questions", "topics"],
        "focus": ("This is a planning session. What matters most: scope decisions, what is "
                  "explicitly in and out, sequencing and dependencies, estimates, and the "
                  "owner of each piece of work.")
    },
    "interview": {
        "title": "Interview Notes",
        "sections": ["topics", "open_questions", "action_items", "decisions"],
        "focus": ("This is a user or candidate interview. What matters most: what the "
                  "interviewee actually said in their own words, problems and workarounds "
                  "they describe, and follow-up questions worth asking. Do not summarise "
                  "away specifics — keep concrete details, numbers, and examples.")
    },
}


def load_templates(path: str) -> dict:
    """Auto-creates templates.json on first run; edit it to add your own
    meeting shapes without touching this file."""
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(DEFAULT_TEMPLATES, f, indent=2)
        return json.loads(json.dumps(DEFAULT_TEMPLATES))
    try:
        with open(path) as f:
            loaded = json.load(f)
        merged = json.loads(json.dumps(DEFAULT_TEMPLATES))
        merged.update(loaded)
        return merged
    except Exception as e:
        print(f"(templates.json unreadable, using defaults: {e})")
        return json.loads(json.dumps(DEFAULT_TEMPLATES))


templates = load_templates(TEMPLATES_PATH)


def get_template(state: dict) -> dict:
    name = state.get("template") or "default"
    return templates.get(name) or templates["default"]


def focus_note(state: dict) -> str:
    focus = get_template(state).get("focus", "")
    return f"\n{focus}\n" if focus else ""


# --- Transcript hygiene ---

def tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9']+", text.lower()) if w not in STOPWORDS}


def containment(inner: set, outer: set) -> float:
    """Share of `inner` present in `outer`. Asymmetric on purpose: it's how
    we spot one item being a restatement of (or a superset of) another."""
    if not inner:
        return 0.0
    return len(inner & outer) / len(inner)


def collapse_repeats(text: str) -> str:
    """Whisper stutters whole sentences when the audio is thin
    ("This meeting may reference these terms. This meeting may reference
    these terms."). Keep the first of each run of identical sentences."""
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for part in parts:
        key = re.sub(r"[^a-z0-9]+", "", part.lower())
        if key and out and key == re.sub(r"[^a-z0-9]+", "", out[-1].lower()):
            continue
        out.append(part)
    return " ".join(out).strip()


def is_hallucination(text: str, whisper_prompt: str) -> bool:
    """True when a line is Whisper filling silence rather than transcribing:
    an echo of our own initial_prompt, stock subtitle filler, or too
    threadbare to carry meaning."""
    stripped = text.strip()
    if len(stripped) < 4:
        return True
    lower = stripped.lower()
    if any(phrase in lower for phrase in HALLUCINATION_PHRASES):
        return True
    line_tokens = tokens(stripped)
    if not line_tokens:
        return True
    if containment(line_tokens, tokens(whisper_prompt)) >= PROMPT_ECHO_THRESHOLD:
        return True
    return False


def rms(audio) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio))))


# --- Structured state ---
# Each item section holds {"id": "D1", "text": "..."} objects and may carry:
#   "t"        HH:MM the item first appeared — how you navigate a long meeting
#   "owner"    who owns an action item
#   "group"    topic heading assigned by the editorial pass
#   "resolved"/"answer"  a closed open question (kept, struck through)
#   "locked"   you edited this bullet by hand; no model op may touch it
#   "deleted"  you deleted this bullet by hand; hidden, and blocks re-adds
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


def state_outline(state: dict) -> str:
    """Human/model-readable view of the current items with their IDs —
    what the merge and editorial prompts show instead of raw JSON."""
    lines = []
    for section in ITEM_SECTIONS:
        lines.append(f"{SECTION_LABELS[section]}:")
        items = live_items(state, section)
        if not items:
            lines.append("  (none yet)")
        for item in items:
            marks = []
            if item.get("resolved"):
                marks.append("resolved")
            if item.get("locked"):
                marks.append("LOCKED - edited by the user, do not change")
            marker = f" ({'; '.join(marks)})" if marks else ""
            owner = f"[{item['owner']}] " if item.get("owner") else ""
            lines.append(f"  [{item['id']}] {owner}{item['text']}{marker}")
    return "\n".join(lines)


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


def merge_chunk(state: dict, transcript_chunk: str) -> dict:
    base_prompt = f"""You are the note-taker in a live meeting, maintaining structured notes.

Current notes (each item has a stable ID):
{state_outline(state)}

New transcript chunk (last ~{CHUNK_SECONDS} seconds of conversation, may be
mid-sentence and imperfectly transcribed):
\"\"\"{transcript_chunk}\"\"\"

First state the gist of the chunk, then capture it as ops:
{{"gist": "<one sentence: what was said in this chunk>", "ops": [<zero or more ops>]}}

Op types:
- {{"op": "add", "section": "<section>", "text": "...", "owner": "<name, action items only>"}} — a new decision, action item, open question, or topic raised in this chunk
- {{"op": "update", "section": "<section>", "id": "<existing ID>", "text": "..."}} — ONLY when the chunk clearly refines or supersedes that exact existing item
- {{"op": "resolve", "section": "open_questions", "id": "<existing ID>"}} — ONLY when the chunk clearly answers that open question

Guidance:
- Prefer capturing. If the chunk contains any statement, task, problem, or subject of discussion, record it in the best-fitting section. A periodic cleanup pass merges duplicates later, but nothing can restore what you fail to capture now.
- Anything someone says they will do, need to do, check, or follow up on is an action item. A problem or unknown they raise is an open question. A subject under discussion is a topic. An agreement or conclusion is a decision.
- <section> must be exactly one of: decisions, action_items, open_questions, topics.
- "text" is ONE sentence, UNDER 25 WORDS, in plain past tense. Say what was decided or raised, not that a speaker said it — write "Ship the migration on Friday", never "The speaker is discussing shipping the migration on Friday". Do not include IDs in text.
- An "update" REPLACES the item's text. It must be shorter than 25 words and must not simply restate the existing item with an extra clause appended — if the chunk adds genuinely new content, that is an "add", not an "update". Updates that grow an item are refused.
- Never add a note that says substantially the same thing as one already listed above. Say nothing rather than repeat.
- IDs are bare, like "Q2", and must be an item that exists in the notes above.
- Items marked LOCKED were edited by hand. Never update or reword them.
- Return "ops": [] for greetings, filler, crosstalk, or a fragment too garbled to be sure what was meant.
{focus_note(state)}{glossary_context_note(glossary)}{attendees_note(state)}
Return ONLY valid JSON, nothing else: {{"gist": "...", "ops": [...]}}
"""

    prompt = base_prompt
    for attempt in range(MAX_MERGE_RETRIES + 1):
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "think": False,
                "options": {"temperature": 0, "num_ctx": 16384}  # deterministic; num_ctx: the default 4096 silently truncates grown prompts
            })
            candidate = json.loads(resp.json()["response"])
        except Exception as e:
            print(f"Merge attempt {attempt}: not valid JSON ({e})")
            candidate, err = None, str(e)
        else:
            valid, err = validate_ops(candidate)
            if valid:
                applied = apply_ops(state, candidate["ops"])
                # Always show the model's reading of the chunk — when notes
                # aren't updating, this is the first place to look.
                print(f"  [merge] {applied} op(s). gist: {candidate.get('gist', '(none)')}")
                return state
            print(f"Merge attempt {attempt}: invalid ops ({err})")

        if attempt < MAX_MERGE_RETRIES:
            prompt = base_prompt + f"\n\nYour previous response was invalid: {err}. Fix it and return corrected JSON only."

    print("Merge failed after retries — state untouched (nothing lost).")
    return state


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


def editorial_pass(state: dict, transcript_window: str) -> dict:
    """The slow loop: every few minutes, re-read the recent raw transcript
    alongside the current notes and improve structure and clarity — the
    context a 10-second merge can never see. This is where decisions that
    emerge across minutes of discussion get caught, answered questions get
    closed, run-on items get split, and topics get grouped under headings.
    All edits go through apply_edits on a copy, with an over-shrink guard."""
    ungrouped = [t for t in live_items(state, "topics") if not t.get("group")]
    if len(ungrouped) >= 6:
        ungrouped_note = (f"There are {len(ungrouped)} ungrouped discussion notes — an unreadable "
                          f"wall of bullets. Spend most of your edits on \"group\" ops until every "
                          f"one sits under a heading.")
    else:
        ungrouped_note = "Group any related discussion notes that still lack a heading."
    prompt = f"""You are the editor of live meeting notes. Improve their structure and
clarity WITHOUT losing information, using the recent transcript for context.

Current notes (each item has a stable ID):
Summary so far: {state.get('summary') or '(none yet)'}
{state_outline(state)}

Transcript of the last few minutes:
\"\"\"{transcript_window}\"\"\"

Return JSON {{"edits": [...]}} using these ops:
- {{"op": "summary", "text": "..."}} — 1-2 sentences: what this meeting is about and where it has got to. ALWAYS include this op.
- {{"op": "add", "section": "decisions", "text": "..."}} — IMPORTANT: scan the transcript for agreements that emerged across several turns of discussion (e.g. "yeah let's do that", "I'm 100% with you", consensus forming) — these are decisions the notes are missing. Also add any other clearly missed item (sections: decisions, action_items, open_questions, topics).
- {{"op": "resolve", "id": "<Q id>", "answer": "..."}} — an open question that the transcript shows was answered; include the answer.
- {{"op": "merge", "section": "<section>", "ids": ["<ID>", "<ID>"], "text": "..."}} — near-duplicates combined into one clear sentence (2+ ids, same section).
- {{"op": "split", "section": "<section>", "id": "<ID>", "texts": ["...", "..."]}} — a run-on item split into separate clear items.
- {{"op": "reword", "section": "<section>", "id": "<ID>", "text": "..."}} — tighter wording, same meaning, under 25 words.
- {{"op": "group", "ids": ["T1", "T3"], "title": "Short Heading"}} — related topic notes grouped under a 2-4 word heading (topics only).

Rules:
- Return AT MOST 8 edits — the highest-value ones only. Another pass runs in a few minutes; you do not need to fix everything now.
- Never drop information — merge and split preserve it, nothing deletes it.
- Prefer decisive edits over none; a long meeting deserves grouping and splitting.
- Every item must be ONE sentence UNDER 25 WORDS. Any item longer than that is your top priority: split it into separate items, or reword it tighter. A reader should skim the list, not read a paragraph.
- Write what happened, not that someone said it. "Ship the migration Friday", never "The speaker is discussing shipping the migration".
- {ungrouped_note}
- Items marked LOCKED were edited by hand. Never reword, merge, or split them.
{focus_note(state)}{glossary_context_note(glossary)}{attendees_note(state)}
Return ONLY valid JSON, nothing else: {{"edits": [...]}}
"""
    edits = None
    for attempt in range(2):
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "think": False,
                "options": {"temperature": 0, "num_ctx": 16384}
            })
            candidate = json.loads(resp.json()["response"])
            if isinstance(candidate.get("edits"), list):
                edits = candidate["edits"]
                break
            print(f"Editorial attempt {attempt}: invalid shape.")
        except Exception as e:
            print(f"Editorial attempt {attempt}: failed ({e}).")
    if edits is None:
        print("Editorial pass skipped after retries.")
        return state

    before = total_items(state)
    new_state, applied = apply_edits(state, edits)
    if not applied:
        print("Editorial pass: no edits.")
        return state
    after = total_items(new_state)
    if before > 0 and after < before * 0.6:
        print(f"Editorial pass shrank state suspiciously ({before} -> {after} items) — discarding.")
        return state
    print(f"Editorial pass: {applied} edit(s) applied ({before} -> {after} items).")
    return new_state


def render_item(section: str, item: dict) -> str:
    """One bullet. The trailing HTML comment carries the item ID: invisible
    in Obsidian's preview, but it's what lets an edit you make in the file
    be matched back to the right item instead of looking like a new note."""
    stamp = f"[{item['t']}] " if item.get("t") else ""
    tail = f" <!--{item['id']}-->"
    if section == "open_questions" and item.get("resolved"):
        answer = item.get("answer", "resolved")
        return f"- ~~{item['text']}~~ → **{answer}**{tail}"
    if section == "action_items":
        owner = f"**{item['owner']}** — " if item.get("owner") else ""
        return f"- [ ] {stamp}{owner}{item['text']}{tail}"
    return f"- {stamp}{item['text']}{tail}"


NOTE_LINE_RE = re.compile(
    r"^\s*[-*]\s+(?:\[[ xX]\]\s*)?(?P<body>.*?)\s*<!--\s*(?P<id>[DAQT]\d+)\s*-->\s*$")
NEW_LINE_RE = re.compile(r"^\s*[-*]\s+(?:\[[ xX]\]\s*)?(?P<body>.+?)\s*$")
STAMP_RE = re.compile(r"^\[(\d{1,2}:\d{2})\]\s*")
OWNER_RE = re.compile(r"^\*\*(?P<owner>[^*]{1,40})\*\*\s*[—-]\s*")
RESOLVED_RE = re.compile(r"^~~(?P<text>.*?)~~(?:\s*→\s*\*\*(?P<answer>.*?)\*\*)?\s*$")


def parse_item_body(body: str) -> dict:
    """Inverse of render_item: strip the decorations back off a bullet so we
    compare and store the text the same way we produced it."""
    out = {}
    m = RESOLVED_RE.match(body.strip())
    if m:
        out["resolved"] = True
        if m.group("answer"):
            out["answer"] = m.group("answer").strip()
        body = m.group("text")
    m = STAMP_RE.match(body.strip())
    if m:
        out["t"] = m.group(1)
        body = STAMP_RE.sub("", body.strip())
    m = OWNER_RE.match(body.strip())
    if m:
        out["owner"] = m.group("owner").strip()
        body = OWNER_RE.sub("", body.strip())
    out["text"] = body.strip()
    return out


def render_markdown(state: dict) -> str:
    template = get_template(state)
    title = template.get("title", "Meeting Notes")
    lines = [f"# {title} — {datetime.now().strftime('%a %d %b %Y')}", ""]
    if state.get("summary"):
        lines += [f"> {state['summary']}", ""]
    if state.get("attendees"):
        lines += [f"**Attendees:** {', '.join(state['attendees'])}", ""]

    # Template order first, then any section it omits that has items — a
    # template chooses emphasis, it can never hide a note.
    order = [s for s in template.get("sections", list(ITEM_SECTIONS)) if s in ITEM_SECTIONS]
    order += [s for s in ITEM_SECTIONS if s not in order and live_items(state, s)]

    for section in order:
        items = live_items(state, section)
        lines.append(f"## {SECTION_LABELS[section]}")
        if not items:
            lines += ["- (none yet)", ""]
            continue
        if section == "open_questions":
            # Unresolved first: what's still live is what you're scanning for.
            lines += [render_item(section, q) for q in items if not q.get("resolved")]
            closed = [q for q in items if q.get("resolved")]
            if closed:
                lines += ["", "**Answered**"]
                lines += [render_item(section, q) for q in closed]
        elif section == "topics":
            # Grouped topics render under their heading (first-appearance
            # order), ungrouped ones follow. Headings are what keeps an
            # hour-long meeting from becoming one undifferentiated block.
            seen = []
            for t in items:
                g = t.get("group")
                if g and g not in seen:
                    seen.append(g)
            for g in seen:
                lines += [f"### {g}"]
                lines += [render_item(section, t) for t in items if t.get("group") == g]
                lines.append("")
            ungrouped = [t for t in items if not t.get("group")]
            if ungrouped:
                if seen:
                    lines.append("### Other")
                lines += [render_item(section, t) for t in ungrouped]
        else:
            lines += [render_item(section, it) for it in items]
        lines.append("")

    asked = state.get("asked", [])
    if asked:
        lines.append("## Asked")
        for qa in asked:
            lines.append(f"- **Q:** {qa['q']}\n  **A:** {qa['a']}")
        lines.append("")
    lines += ["---", "*Edit any bullet above and the change sticks — it will not be overwritten. "
              "Delete a bullet and it stays gone.*"]
    return "\n".join(lines)


def reconcile_user_edits(state: dict, text: str) -> int:
    """Read the notes file back and fold your hand edits into state. A
    reworded bullet updates the item and LOCKS it, so no later model op can
    undo your wording; a bullet you removed becomes a tombstone, hidden and
    blocked from being re-added; a bullet you typed yourself under a section
    heading becomes a new locked item. Returns how many edits were adopted."""
    seen_ids, changes = set(), 0
    section = None
    reverse_labels = {v.lower(): k for k, v in SECTION_LABELS.items()}
    typed = []

    for raw in text.splitlines():
        line = raw.rstrip()
        heading = re.match(r"^##\s+(.*?)\s*$", line)
        if heading:
            section = reverse_labels.get(heading.group(1).strip().lower())
            continue
        if section is None:
            continue
        m = NOTE_LINE_RE.match(line)
        if m:
            item = find_item(state, section, m.group("id"), include_deleted=True)
            if item is None:
                continue
            seen_ids.add(item["id"])
            parsed = parse_item_body(m.group("body"))
            if parsed["text"] and parsed["text"] != item["text"]:
                print(f"  [your edit] {item['id']} reworded and locked")
                item["text"] = parsed["text"]
                item["locked"] = True
                changes += 1
            for key in ("owner", "answer"):
                if parsed.get(key) and parsed[key] != item.get(key):
                    item[key] = parsed[key]
                    changes += 1
            if parsed.get("resolved") and not item.get("resolved"):
                item["resolved"] = True
                changes += 1
            continue
        new = NEW_LINE_RE.match(line)
        if new and "(none yet)" not in new.group("body"):
            body = new.group("body").strip()
            if body and not body.startswith("*"):
                typed.append((section, parse_item_body(body)))

    rendered_ids = {it["id"] for s in ITEM_SECTIONS for it in live_items(state, s)}
    missing = rendered_ids - seen_ids
    # Guard against a half-written or truncated file looking like a mass
    # delete: only honour removals when most of the notes are still there.
    if missing and len(seen_ids) >= len(rendered_ids) * 0.5:
        for s in ITEM_SECTIONS:
            for item in state.get(s, []):
                if item["id"] in missing:
                    print(f"  [your edit] {item['id']} deleted")
                    item["deleted"] = True
                    changes += 1
    elif missing:
        print(f"  [reconcile] ignoring {len(missing)} missing item(s) — file looks incomplete")

    for s, parsed in typed:
        item = add_item(state, s, parsed["text"], owner=parsed.get("owner", ""),
                        stamp=parsed.get("t"))
        if item:
            item["locked"] = True
            print(f"  [your edit] added {item['id']} from your own bullet")
            changes += 1
    return changes


def extract_trigger(text: str):
    """Return (query, remaining_notes_text). If a wake phrase is found, the
    query is what follows it, and remaining_notes_text is what preceded it
    (real meeting content in the same chunk still reaches the notes)."""
    lower = text.lower()
    for phrase in TRIGGER_PHRASES:
        idx = lower.find(phrase)
        if idx != -1:
            query = text[idx + len(phrase):].strip(" ,.:;-")
            before = text[:idx].strip()
            return query, before
    return None, text


def answer_query(question: str, state: dict) -> str:
    prompt = f"""You are a voice assistant embedded in a live meeting notes tool.
The user just addressed you directly with a question during a meeting.

Current meeting notes (only use this if the question is about the meeting itself):
{state_outline(state)}

Question: "{question}"

Answer directly and concisely, 1-3 sentences. If it's about the meeting
(action items, decisions, questions raised), answer from the notes above.
Otherwise answer from general knowledge. Do not mention you're an AI,
don't explain your reasoning, just answer.

IMPORTANT: You can ONLY answer questions. You cannot edit the notes, add
or change items, or stop/start the recording — never claim you did. If
asked to edit the notes, say voice editing isn't supported yet and the
request was logged in the Asked section. If asked to stop recording, say
to press Ctrl+C in the terminal.
{glossary_context_note(glossary)}"""
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "think": False
        })
        return resp.json()["response"].strip()
    except Exception as e:
        return f"(couldn't get an answer: {e})"


def speak(text: str):
    try:
        subprocess.run(["say", text])
    except Exception as e:
        print(f"(couldn't speak answer: {e})")


def main():
    # Import + model load here so the module stays cheap to import (tests,
    # future tooling) — the weights download once on first run, then cache.
    from faster_whisper import WhisperModel
    whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

    state = load_state(STATE_PATH)
    if CLI_ATTENDEES:
        state["attendees"] = CLI_ATTENDEES
    if CLI_TEMPLATE:
        if CLI_TEMPLATE not in templates:
            print(f"Unknown template {CLI_TEMPLATE!r}; known: {', '.join(sorted(templates))}. Using default.")
        else:
            state["template"] = CLI_TEMPLATE
    whisper_prompt = build_whisper_prompt(glossary, state.get("attendees", []))

    print(f"Listening... writing live notes to {NOTES_PATH} (mirrored to {LATEST_NOTES_PATH}). Ctrl+C to stop.")
    print(f"Template: {state.get('template', 'default')}. Edit bullets in the notes file any time — "
          f"your wording is kept and deletions stick.")
    print(f"Say '{TRIGGER_PHRASES[0]}' followed by a question to get a direct spoken answer.")

    # What we last wrote, so a file that differs from it can only mean you
    # edited it — that diff is the whole correction mechanism.
    last_rendered = None

    def write_notes(current):
        nonlocal last_rendered
        for path in (NOTES_PATH, LATEST_NOTES_PATH):
            if last_rendered is None or not os.path.exists(path):
                continue
            with open(path) as f:
                on_disk = f.read()
            if on_disk != last_rendered:
                if reconcile_user_edits(current, on_disk):
                    break  # adopted; re-render below reflects it in both files
        rendered = render_markdown(current)
        for path in (NOTES_PATH, LATEST_NOTES_PATH):
            with open(path, "w") as f:
                f.write(rendered)
        last_rendered = rendered

    buffer = []
    chunk_count = 0
    last_chunk_text = ""
    # In-memory copy of what goes to the raw log, feeding the editorial
    # window. On a mid-meeting restart, reload it from the log so the
    # editor doesn't lose its recent context.
    transcript_lines = []
    if os.path.exists(RAW_LOG_PATH):
        with open(RAW_LOG_PATH) as f:
            transcript_lines = [re.sub(r"^\[\d\d:\d\d:\d\d\]\s*", "", ln_.strip())
                                for ln_ in f if ln_.strip()]

    def callback(indata, frames, time_info, status):
        if status:
            print(status)
        buffer.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32', callback=callback):
        while True:
            time.sleep(CHUNK_SECONDS)
            if not buffer:
                continue

            audio = np.concatenate(buffer, axis=0).flatten()
            buffer.clear()  # discard raw audio immediately, nothing saved to disk

            if rms(audio) < SILENCE_RMS:
                continue  # silence never reaches Whisper, so it can't invent speech for it

            segments, _ = whisper_model.transcribe(
                audio,
                language="en",
                initial_prompt=whisper_prompt,
                temperature=0,
                vad_filter=True,                       # drop non-speech before decoding
                vad_parameters={"min_silence_duration_ms": 400},
                condition_on_previous_text=False,      # stops one bad chunk seeding a repetition loop
                no_speech_threshold=0.6,
                compression_ratio_threshold=2.4,       # rejects degenerate repeated output
                hallucination_silence_threshold=2.0,
            )
            kept = [seg.text for seg in segments
                    if getattr(seg, "no_speech_prob", 0.0) < MAX_NO_SPEECH_PROB]
            text = collapse_repeats(" ".join(kept).strip())
            if not text:
                continue
            if is_hallucination(text, whisper_prompt):
                print(f"  [dropped: hallucinated silence] {text[:70]}")
                continue
            text = correct_transcript(text, glossary)
            if tokens(text) and containment(tokens(text), tokens(last_chunk_text)) >= DUP_THRESHOLD:
                print(f"  [dropped: repeat of previous chunk] {text[:70]}")
                continue
            last_chunk_text = text

            # Append-only raw log — written before anything else touches the
            # text, so it survives regardless of what merge/schema issues
            # happen downstream.
            with open(RAW_LOG_PATH, "a") as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n")
            transcript_lines.append(text)

            query, notes_text = extract_trigger(text)
            if query is not None:
                if notes_text:  # meeting content spoken before the wake phrase still counts
                    print(f"\n[chunk] {notes_text}")
                    state = merge_chunk(state, notes_text)
                print(f"\n[query] {query}")
                answer = answer_query(query, state)
                print(f"[answer] {answer}")
                speak(answer)
                state["asked"].append({"q": query, "a": answer})
            else:
                print(f"\n[chunk] {text}")
                state = merge_chunk(state, text)
                chunk_count += 1
                if chunk_count % EDITORIAL_EVERY_N_CHUNKS == 0:
                    window = "\n".join(transcript_lines[-EDITORIAL_WINDOW_LINES:])
                    state = editorial_pass(state, window)

            write_notes(state)
            save_state(state, STATE_PATH)
            print("Notes updated.")


if __name__ == "__main__":
    main()
