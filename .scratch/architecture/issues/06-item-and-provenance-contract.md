# Item & provenance contract

Type: grilling
Blocked by: 01, 05

## Question

What shape of Item and session state can every module and future feature rely on — id scheme, text cap, owner/due, provenance (transcript line range per op), authorship and lock (human vs agent), history (supersedes, rewrite count), tombstones — and how is the state schema versioned and migrated?

## Context

- `DEFAULT_STATE`, `migrate_state`, `add_item` in `live_notes.py`; hidden `<!--D1-->` anchors in rendered markdown.
- Memo principles 2–4 and §06 "Line ranges, retrofitted" (cheap now, painful later).
- From the eval tooling fit research: the eval workbench needs an op log with item ids for each run, to compute rewrite depth and per-call traces.
- From Core domain language: current vs retired (Superseded / Tombstone, nothing deleted). Time-based Locked (any human Op, compared by Transcript time). Provenance per Op as specific segment-level Transcript lines, with housekeeping ops inheriting and human Ops placed by time. Author is a named human or the agent. Action open/done and Question open/answered are both current. Links on Items. Saved Gists (Catch-up). See `CONTEXT.md`.
