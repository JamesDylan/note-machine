# Single writer

Type: grilling
Blocked by: 01

## Question

Who is allowed to write the notes file and session state, and how do all other actors — Obsidian hand edits, a browser UI, voice/silent commands, the editorial pass, the coach — get their changes in? Includes the conflict rule when a human and the agent touch the same item in the same cycle.

## Context

- Today: `write_notes` diffs the file against the last render and `reconcile_user_edits` adopts the difference (`live_notes.py:1103`, `:956`).
- Memo principle 6 ("the file stays the source of truth") and §06 "Who writes the file while the browser is open?"
- Local compute concurrency (Whisper + LLM + coach) proposes one engine thread as the only thing that changes state or writes notes. Every other actor sends an event to its queue. Test that proposal here.
- From Core domain language: anyone can give a Command. The Operator's Commands apply directly, and others become Proposals unless allowed. Findings and Query answers reach the Notes only as accepted Proposals. Left for review is a derived view at Session end, not a write. Locked Items can be superseded only by lines said after the lock.
