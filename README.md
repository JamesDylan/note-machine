# note-machine — Phase 0 MVP

Live-updating structured meeting notes. Mic-only (no system audio yet),
nothing written to disk except the notes/state files themselves.

## Setup (one-time)

```bash
brew install portaudio
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Make sure Ollama is running and the model is pulled:

```bash
ollama serve   # if not already running
ollama pull qwen3.5:4b   # skip if already have it
```

## Run

Each new terminal session, activate the venv first:

```bash
cd /Users/jamesscholz/hobbes/note-machine
source venv/bin/activate
```

**Starting a new meeting:**
```bash
python3 live_notes.py --new
```

**Resuming the current meeting** (e.g. after a restart mid-meeting):
```bash
python3 live_notes.py
```
With no `--new` flag it automatically resumes whatever session is
currently active — no need to track filenames or delete anything.

Optional shortcut for `~/.zshrc`:
```bash
alias notes='cd /Users/jamesscholz/hobbes/note-machine && source venv/bin/activate && python3 live_notes.py'
alias notes-new='cd /Users/jamesscholz/hobbes/note-machine && source venv/bin/activate && python3 live_notes.py --new'
```

First run will prompt macOS for microphone permission (Terminal needs
it) — approve it once.

## How sessions work

Each `--new` run gets a timestamped slug (e.g. `20260909-143210`) and
writes two files:
- `live_notes_<slug>.md` — that meeting's notes, permanently kept
- `state_<slug>.json` — that meeting's structured state, for resuming

Old sessions are never touched or deleted — `ls live_notes_*.md` gives
you a running archive of past meetings.

`live_notes.md` (no slug) always mirrors whichever session is
currently active — keep that one file open in Obsidian/VSCode and you
never have to switch which file you're watching between meetings.

`.current_session` is a small hidden pointer file tracking which
session is "current." You shouldn't need to touch it directly.

## Glossary

`glossary.json` maps correct terms to common Whisper mishearings
(e.g. `"SOL": ["soul", "sole"]`). Edit it directly whenever you notice
a new mishearing — no code changes needed, just restart the script to
reload it. Terms with no known mishearing yet (e.g. company/product
names) can have an empty list — they still get biased toward
correctly via Whisper's prompt and the summarizer's context.

## Known rough edges (expected at this stage)
- Mic-only: only captures your side of a call. Adding system audio
  (BlackHole virtual driver) is a separate, later step — doesn't change
  the core engine.
- 10s chunking means sentences can get cut mid-thought; whisper.cpp/
  faster-whisper will sometimes mistranscribe a cut-off sentence.
- No "settle" logic yet — every chunk gets merged immediately, so a
  half-finished thought can produce a rough or premature bullet. This
  is one of the open questions in the project brief.
- `base.en` model is fast but rough. Bump `WHISPER_MODEL_SIZE` to
  `small.en` in `live_notes.py` if accuracy is too poor to be useful.
- Talking *about* the tool without the wake phrase still gets treated
  as meeting content and can produce garbled notes — only things said
  after "hey note machine" are routed away from the notes.
