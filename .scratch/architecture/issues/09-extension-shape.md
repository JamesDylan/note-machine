# One extension shape

Type: grilling
Blocked by: 08

## Question

Is there one extension shape that commands, the coach/nudges, business-context enrichment and additional capture sources all fit — what it receives (transcript window, state, context), what it may emit (ops, proposals, cards), and on what cadence — or do some of them genuinely need a different seam?

## Context

- Scratchpad: non-disruptive agent feedback, meeting coach, business context.
- Memo principle 5 ("the coach writes, it doesn't talk") and §06 "Is the nudge worth a second model call?"
- Today's only extension is `extract_trigger` → `answer_query` → `speak`.
- Pattern from Local-first peer architectures (Anarlog, Meetily): an event fan-out that the browser view and coach subscribe to, hooks as shell commands, and agents that only propose edits. Plugin SDKs were judged over-engineered.
- From Core domain language: Nudge (no Ops, private, a person must act) vs Proposal (Ops with provenance) vs Finding (outside information, reaches the Notes only via Proposal). Queries are answered the way they were asked. Outside agents (the Operator's Claude, Rovo, OpenClaw, Jira) must fit the shape as Finding sources. Template focus applies forward only.
