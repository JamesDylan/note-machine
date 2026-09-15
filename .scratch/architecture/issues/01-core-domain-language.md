# Core domain language

Type: grilling
Status: resolved
Blocked by: —
Assignee: James

## Question

What are note-machine's canonical domain terms, and where are the boundaries between them? Pin down at least: Session, Chunk (audio vs transcript), Transcript line, Gist, Item and its kinds (decision / action / question / topic), Op, Proposal, Merge, Editorial pass, Lock, Tombstone, Supersede, Provenance, Template, Glossary, Command (voice / silent / typed), Nudge, Business context. Record the result as a root `CONTEXT.md` (glossary only, no implementation).

## Context

- Code vocabulary: `state`, `ops`, `edits`, tombstoned, locked, `asked` — `live_notes.py`.
- Memo introduces proposal, nudge, catch-up rail, provenance; PLAN.md uses editorial loop, compaction (retired).
- Result: root `CONTEXT.md` (42 terms in five groups).

## Answer

The glossary is written to the root `CONTEXT.md`. These decisions shape later tickets:

**Session and capture**
- A **Session** is one Meeting's identity. Resuming continues the same Session.
- A **Run** is only an eval replay.
- A **Chunk** is acoustic, from exactly one **Source**.
- **Transcript lines** are segment-level (one Chunk → one or more lines). Topic boundaries never shape the Transcript.
- **Gists** cover line ranges, not merge calls. They're saved as **Catch-up**, including stretches with no Items.

**Notes and Items**
- The **Notes** hold only current Items (plus Summary and Attendees).
- An **Item** never changes kind and is never deleted. It is either **current** or **retired**.
- An Item is retired only by being **Superseded** (Combine and Split supersede the originals and create new Items) or **Tombstoned** (human only).
- Answered Questions and done Actions stay current.

**Locked (time-based)**
- Any human Op locks an Item, as of the moment of that Op.
- Nothing said before the lock can change it. What's said after the lock may supersede it, but its wording is never rewritten by the agent.
- Order is judged by Transcript time, not processing time.

**Ops, Provenance and Proposals**
- Every change to Items, Summary or Attendees is an **Op**, whoever made it. **Author** is a named human or the agent.
- **Provenance** belongs to Ops. It is the specific justifying lines, not the whole window the pass read.
- Housekeeping Ops inherit the provenance of the Items they act on. A new claim with no lines is invalid. Human Ops are placed on the timeline by time.
- A **Proposal** is Ops awaiting a human.
- Proposals unanswered when the Session ends show privately as **Left for review** at the foot of the Notes. It is a view, not an Op.

**Merge vs Combine**
- **Merge** is the frequent pass.
- The duplicate-joining op is renamed **Combine**.

**Commands**
- Anyone in the Meeting can give a **Command**, on any channel.
- The **Operator's** Commands that change the Notes apply directly. Anyone else's become Proposals unless the Operator has allowed that Command.
- A **Query** is answered the way it was asked.

**Outside information**
- **Glossary** is recognition only. **Business context** is meaning and status: it may clarify an Item but never adds an unstated fact.
- A **Link** points at a mentioned outside thing.
- A **Finding** (from Business context or an **Outside agent**) reaches the Notes only as an accepted Proposal.

**Nudges**
- A **Nudge** carries no Ops, is private to the Operator, and is something only a person in the room can act on. If note-machine could fix it with provenance, it's a Proposal.
- The **Coach** raises Nudges, including live feedback on the Operator's style. Post-meeting reflection is left unnamed for now.

**Differences from today's code, for later tickets:**
- Combine hard-deletes the other Items (`live_notes.py:720`).
- Split reuses the original id (`:751`).
- Owner, answer and done changes don't lock (`:976-989`).
- Items carry no provenance, only a `t` timestamp.
- The wake phrase can be triggered by anyone, and the answer is always spoken.

