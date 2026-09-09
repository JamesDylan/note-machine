"""
Live meeting notes engine — Phase 0 MVP + wake-phrase Q&A + validate/compact.

Captures mic audio in memory, transcribes rolling ~10s chunks with
faster-whisper (no files touched), merges each chunk into a fixed-section
structured note via a local Ollama call, and writes the result to a
markdown file that auto-refreshes if opened in Obsidian/VSCode preview.

If a chunk contains the wake phrase ("hey note machine" / "note machine"),
it's routed to direct Q&A instead of being merged into notes: answered via
Ollama (using current meeting state as context when relevant), spoken aloud
with macOS's built-in `say`, and logged in an "Asked" section.

Every merge call re-sends the full instructions from scratch (stateless
/api/generate, no accumulated chat history) — so the schema never
"disappears". What CAN happen is the state itself growing large enough
that the fixed instruction block carries less relative weight, so every
COMPACT_EVERY_N_CHUNKS a compaction pass dedupes/condenses the state
(no new info added) to keep the working set small and current.

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
from faster_whisper import WhisperModel

# --- Config ---
SAMPLE_RATE = 16000
CHUNK_SECONDS = 10
OLLAMA_MODEL = "qwen3.5:4b"   # swap for whatever's pulled locally
OLLAMA_URL = "http://localhost:11434/api/generate"
LATEST_NOTES_PATH = "live_notes.md"  # always mirrors whichever session is active — keep this open in Obsidian
SESSION_POINTER_PATH = ".current_session"
WHISPER_MODEL_SIZE = "base.en"  # small/fast; upgrade to "small.en" if accuracy is too rough
TRIGGER_PHRASES = ["hey note machine", "note machine"]
PLAIN_STRING_SECTIONS = ("decisions", "action_items", "open_questions", "topics")
MAX_MERGE_RETRIES = 1
COMPACT_EVERY_N_CHUNKS = 18  # ~3 min at 10s/chunk — tune as needed
GLOSSARY_PATH = "glossary.json"


def resolve_session() -> str:
    """Plain launch resumes whatever session the pointer file names.
    `--new` starts a fresh timestamped session and repoints to it —
    old session files are never touched, so they form a running archive."""
    start_new = "--new" in sys.argv
    if start_new or not os.path.exists(SESSION_POINTER_PATH):
        slug = datetime.now().strftime("%Y%m%d-%H%M%S")
        with open(SESSION_POINTER_PATH, "w") as f:
            f.write(slug)
        print(f"Starting new session: {slug}")
    else:
        with open(SESSION_POINTER_PATH) as f:
            slug = f.read().strip()
        print(f"Resuming session: {slug} (run with --new to start a fresh one instead)")
    return slug


SESSION_SLUG = resolve_session()
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


def build_whisper_prompt(glossary: dict) -> str:
    """Whisper supports biasing toward likely vocabulary via initial_prompt.
    Not a hard guarantee, but nudges the decoder toward these terms."""
    terms = ", ".join(glossary.keys())
    return f"This meeting may reference these terms and acronyms: {terms}."


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


glossary = load_glossary(GLOSSARY_PATH)
WHISPER_PROMPT = build_whisper_prompt(glossary)

# --- Whisper model (downloads once on first run, then cached locally) ---
whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

# --- Structured state (fixed sections — never fully regenerated, only merged) ---
DEFAULT_STATE = {
    "decisions": [],
    "action_items": [],
    "open_questions": [],
    "topics": [],
    "asked": []  # {"q": ..., "a": ...} pairs from wake-phrase queries — the ONLY section that's objects
}


def load_state(path: str) -> dict:
    """Loads the current session's state file if it exists (mid-meeting
    restart), otherwise starts fresh. --new always gets a brand new slug
    so this naturally returns fresh state without deleting anything."""
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return dict(DEFAULT_STATE)


def save_state(state: dict, path: str):
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


state = load_state(STATE_PATH)


def flatten_item(item) -> str:
    """Coerce any stray non-string item into readable text, so a schema
    slip never renders as a raw Python object dump."""
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("decision", "action_item", "item", "text", "content", "topic", "question"):
            if item.get(key):
                return str(item[key])
        return "; ".join(f"{k}: {v}" for k, v in item.items())
    return str(item)


def validate_state(candidate: dict, expected_keys) -> tuple:
    """Strict schema check. Returns (is_valid, error_message)."""
    if not isinstance(candidate, dict):
        return False, "response was not a JSON object"
    missing = [k for k in expected_keys if k not in candidate]
    if missing:
        return False, f"missing keys: {missing}"
    for section in PLAIN_STRING_SECTIONS:
        if not isinstance(candidate.get(section), list):
            return False, f"'{section}' must be a list"
        if any(not isinstance(i, str) for i in candidate[section]):
            return False, f"'{section}' must contain only plain strings, found a non-string item"
    if not isinstance(candidate.get("asked"), list):
        return False, "'asked' must be a list"
    return True, None


def merge_chunk(state: dict, transcript_chunk: str) -> dict:
    base_prompt = f"""You are maintaining a live structured meeting notes document.

Existing state (JSON):
{json.dumps(state, indent=2)}

New transcript chunk (last ~{CHUNK_SECONDS} seconds of conversation):
\"\"\"{transcript_chunk}\"\"\"

Update the state based on the new chunk. Only add or modify sections
affected by this chunk. Do not remove existing items unless the new
chunk clearly supersedes them. If the chunk is small talk or has
nothing note-worthy, return the state unchanged. Write full, clear
phrases for each item — not compressed telegraphic fragments — so
someone skimming later understands it without re-listening.

STRICT SCHEMA RULE: "decisions", "action_items", "open_questions", and
"topics" must each be a flat list of plain strings — one sentence per
item. NEVER an object/dict, never nested fields like {{"decision": ...,
"context": ...}}. If a point has a decision plus context plus an owner,
write ONE sentence containing all of that, not a structured object.
Only "asked" is allowed to contain objects — leave it exactly as given.
{glossary_context_note(glossary)}
Return ONLY valid JSON matching this exact schema, nothing else:
{{"decisions": ["...", "..."], "action_items": ["...", "..."], "open_questions": ["...", "..."], "topics": ["...", "..."], "asked": {json.dumps(state.get("asked", []))}}}
"""

    prompt = base_prompt
    for attempt in range(MAX_MERGE_RETRIES + 1):
        resp = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "think": False
        })
        try:
            candidate = json.loads(resp.json()["response"])
        except Exception as e:
            print(f"Merge attempt {attempt}: not valid JSON ({e})")
            candidate, err = None, str(e)
        else:
            valid, err = validate_state(candidate, state.keys())
            if valid:
                for section in PLAIN_STRING_SECTIONS:
                    candidate[section] = [flatten_item(i) for i in candidate[section]]
                return candidate
            print(f"Merge attempt {attempt}: schema invalid ({err})")

        if attempt < MAX_MERGE_RETRIES:
            prompt = base_prompt + f"\n\nYour previous response was invalid: {err}. Fix it and return corrected JSON only."

    print("Merge failed after retries, keeping old state.")
    return state


def total_items(state: dict) -> int:
    return sum(len(state.get(s, [])) for s in PLAIN_STRING_SECTIONS)


def compact_state(state: dict) -> dict:
    """Periodic housekeeping pass: dedupe/condense the existing state with
    no new transcript info, so the working set doesn't grow unbounded
    over a long meeting. Guarded against the model over-pruning: if the
    result has less than half the items it started with, that's treated
    as a bug, not real deduplication, and discarded."""
    prompt = f"""You are tidying a live meeting notes document — no new
information is being added right now, this is a housekeeping pass only.

Current state (JSON):
{json.dumps(state, indent=2)}

Merge near-duplicate items within each section, remove anything truly
redundant, and tighten wording — but do not delete distinct decisions,
action items, open questions, or topics. Do not invent anything new.
Leave "asked" exactly as given.

STRICT SCHEMA RULE: "decisions", "action_items", "open_questions", and
"topics" must each remain a flat list of plain strings.

Return ONLY valid JSON matching this exact schema, nothing else:
{{"decisions": ["...", "..."], "action_items": ["...", "..."], "open_questions": ["...", "..."], "topics": ["...", "..."], "asked": {json.dumps(state.get("asked", []))}}}
"""
    resp = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "think": False
    })
    try:
        candidate = json.loads(resp.json()["response"])
        valid, err = validate_state(candidate, state.keys())
        if valid:
            for section in PLAIN_STRING_SECTIONS:
                candidate[section] = [flatten_item(i) for i in candidate[section]]
            before, after = total_items(state), total_items(candidate)
            if before > 0 and after < before * 0.5:
                print(f"Compaction shrank state suspiciously ({before} -> {after} items) — discarding, keeping pre-compaction state.")
                return state
            print("Compaction pass complete.")
            return candidate
        print(f"Compaction produced invalid schema ({err}), skipping.")
        return state
    except Exception as e:
        print(f"Compaction failed ({e}), skipping.")
        return state


def render_markdown(state: dict) -> str:
    lines = ["# Live Meeting Notes", ""]
    lines.append("## Decisions")
    lines += [f"- {d}" for d in state.get("decisions", [])] or ["- (none yet)"]
    lines.append("\n## Action Items")
    lines += [f"- {a}" for a in state.get("action_items", [])] or ["- (none yet)"]
    lines.append("\n## Open Questions")
    lines += [f"- {q}" for q in state.get("open_questions", [])] or ["- (none yet)"]
    lines.append("\n## Topic Notes")
    lines += [f"- {t}" for t in state.get("topics", [])] or ["- (none yet)"]
    lines.append("\n## Asked")
    asked = state.get("asked", [])
    if asked:
        for qa in asked:
            lines.append(f"- **Q:** {qa['q']}\n  **A:** {qa['a']}")
    else:
        lines.append("- (none yet)")
    return "\n".join(lines)


def extract_trigger(text: str):
    """Return (query, remaining_notes_text) if a wake phrase is found, else (None, text)."""
    lower = text.lower()
    for phrase in TRIGGER_PHRASES:
        idx = lower.find(phrase)
        if idx != -1:
            query = text[idx + len(phrase):].strip(" ,.:;-")
            return query, None
    return None, text


def answer_query(question: str, state: dict) -> str:
    prompt = f"""You are a voice assistant embedded in a live meeting notes tool.
The user just addressed you directly with a question during a meeting.

Current meeting state (only use this if the question is about the meeting itself):
{json.dumps(state, indent=2)}

Question: "{question}"

Answer directly and concisely, 1-3 sentences. If it's about the meeting
(action items, decisions, questions raised), answer from the state above.
Otherwise answer from general knowledge. Do not mention you're an AI,
don't explain your reasoning, just answer.
{glossary_context_note(glossary)}"""
    resp = requests.post(OLLAMA_URL, json={
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "think": False
    })
    try:
        return resp.json()["response"].strip()
    except Exception as e:
        return f"(couldn't get an answer: {e})"


def speak(text: str):
    try:
        subprocess.run(["say", text])
    except Exception as e:
        print(f"(couldn't speak answer: {e})")


def main():
    print(f"Listening... writing live notes to {NOTES_PATH} (mirrored to {LATEST_NOTES_PATH}). Ctrl+C to stop.")
    print(f"Say '{TRIGGER_PHRASES[0]}' followed by a question to get a direct spoken answer.")
    buffer = []
    chunk_count = 0

    def callback(indata, frames, time_info, status):
        if status:
            print(status)
        buffer.append(indata.copy())

    global state
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32', callback=callback):
        while True:
            time.sleep(CHUNK_SECONDS)
            if not buffer:
                continue

            audio = np.concatenate(buffer, axis=0).flatten()
            buffer.clear()  # discard raw audio immediately, nothing saved to disk

            segments, _ = whisper_model.transcribe(audio, language="en", initial_prompt=WHISPER_PROMPT)
            text = " ".join(seg.text for seg in segments).strip()
            if not text:
                continue
            text = correct_transcript(text, glossary)

            # Append-only raw log — written before anything else touches the
            # text, so it survives regardless of what merge/compact/schema
            # issues happen downstream.
            with open(RAW_LOG_PATH, "a") as f:
                f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n")

            query, _ = extract_trigger(text)
            if query:
                print(f"\n[query] {query}")
                answer = answer_query(query, state)
                print(f"[answer] {answer}")
                speak(answer)
                state["asked"].append({"q": query, "a": answer})
            else:
                print(f"\n[chunk] {text}")
                state = merge_chunk(state, text)
                chunk_count += 1
                if chunk_count % COMPACT_EVERY_N_CHUNKS == 0:
                    state = compact_state(state)

            with open(NOTES_PATH, "w") as f:
                f.write(render_markdown(state))
            with open(LATEST_NOTES_PATH, "w") as f:
                f.write(render_markdown(state))
            save_state(state, STATE_PATH)
            print("Notes updated.")


if __name__ == "__main__":
    main()
