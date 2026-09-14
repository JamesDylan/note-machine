# note-machine — Phase 1

Live-updating structured meeting notes. Mic-only (no system audio yet),
nothing written to disk except the notes/state files themselves.

Two-loop architecture:
- **Fast loop** (every ~10s chunk): the model emits deltas (add/update/
  resolve ops) against items with stable IDs; the code owns the state
  and nothing can be deleted. The terminal prints a one-line "gist" for
  every chunk — if notes ever stop updating, read the gists to see what
  the model thought it heard.
- **Editorial loop** (every ~5 min): re-reads the recent transcript
  alongside the notes to catch decisions that emerged across minutes of
  discussion, close answered questions (answer shown inline), merge
  duplicates, split run-on items, group topics under headings, and
  refresh the summary at the top of the doc. This is what makes the
  document gain structure as the meeting goes on.

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

Optionally name the session (goes into the filenames) and list who's in
the room — attendee names dramatically improve name accuracy in both
transcription and the notes:
```bash
python3 live_notes.py --new "migration deltas" --attendees "Lilly, Remy, Chris, Craig, Pratima, Louise, Daryl, Andre"
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

**Talking to it mid-meeting:** say "hey note machine" followed by a
question — it answers out loud and logs the Q&A in the Asked section.
Anything said *before* the wake phrase in the same breath still goes
into the notes. It can only answer questions right now — it cannot edit
the notes or stop the recording by voice (that's a later phase); Ctrl+C
stops the session.

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

## Evals

`evals/` replays real meeting transcripts through the exact production
merge pipeline (same merge code, compaction at the real cadence,
temperature 0 so runs are reproducible) and reports:

- **capture metrics** — ops emitted/applied, silent chunks, final item count
- **invariant check** — items must never disappear outside compaction;
  any violation fails the run
- **fact checks** — per-transcript "must capture" facts, pass/fail

### Running the evals

Run after **any change to the merge prompt, compaction prompt, Ollama
model, or Whisper model** — before trusting the change in a real meeting.
Ollama must be running; venv active; run from the project folder:

```bash
python evals/run_evals.py
```

A full run takes ~10–15 minutes with the local model. To run just one
transcript (name without extension):

```bash
python evals/run_evals.py 2026-09-10-cycle-planning
```

Exit code is 0 only if every fact check and invariant passes — but don't
pipe the output (e.g. through `tail`), or the pipe's exit code masks the
runner's.

### Reading the results

The run prints a one-line summary per transcript. Full reports land in
`evals/results/<name>.md` — metrics, fact pass/fail, and the complete
final rendered notes. **Always eyeball the final notes**, not just the
metrics: keyword checks catch missing facts, but only reading catches
mangled or over-merged wording.

### Adding a new eval case (do this after any good/bad real meeting)

1. Copy the meeting's raw transcript into `evals/transcripts/` with a
   readable name:
   ```bash
   cp raw_transcript_<slug>.log evals/transcripts/2026-09-15-roadmap-review.log
   ```
   Any transcript works — the engine's own `[HH:MM:SS] text` log format,
   or plain text with one chunk per line (so transcripts from other
   tools can be pasted in too).
2. Optionally create `evals/expected/2026-09-15-roadmap-review.json`
   (same name, `.json`) listing facts the notes must contain:
   ```json
   {
     "must_capture": [
       {"name": "survey before the 11am meeting", "any_of": ["survey"]},
       {"name": "async video trial", "any_of": ["video", "record"]}
     ]
   }
   ```
   A fact passes if **any** keyword in `any_of` appears in the final
   notes (case-insensitive substring). `name` is just a label for the
   report. Pick 3–6 facts you'd be annoyed to lose, and keep keywords
   short and distinctive.
3. Run the suite. Done — the case runs on every future eval.

### Current baseline (2026-09-10, after editorial-loop rework)

- `2026-09-10-cycle-planning`: **6/6** facts (the editorial loop fixed the
  "product board" loss the old compaction pass caused).
- `2026-09-10-migration-deltas`: **8/8** facts — the gold-standard case,
  judged against Gemini's post-meeting notes, including both decisions
  that only emerged across minutes of discussion.
- `2026-09-10-tool-test`: **2/3** — known failure, tracked on purpose:
  meta-talk about the tool itself is captured patchily; hardest-case
  transcript.

Fact keywords are substring matches, so a legitimately-captured fact can
"fail" on phrasing — before treating a failure as real, read the final
notes in the report; if the fact is there, loosen that fact's `any_of`.

## Known rough edges (expected at this stage)
- Mic-only: only captures your side of a call. Adding system audio
  (BlackHole virtual driver) is a separate, later step — doesn't change
  the core engine.
- 10s chunking means sentences can get cut mid-thought; whisper.cpp/
  faster-whisper will sometimes mistranscribe a cut-off sentence.
- No "settle" logic yet — every chunk gets merged immediately, so a
  half-finished thought can produce a rough or premature bullet. This
  is one of the open questions in the project brief.
- Whisper model is `small.en` (bumped from `base.en` for accuracy). If
  transcription ever lags behind the 10s chunk cadence, drop
  `WHISPER_MODEL_SIZE` back down in `live_notes.py`.
- Talking *about* the tool without the wake phrase still gets treated
  as meeting content and can produce garbled notes — only things said
  after "hey note machine" are routed away from the notes.
