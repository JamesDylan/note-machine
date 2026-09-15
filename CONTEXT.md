# note-machine

A live meeting writer: it listens to a meeting and keeps a structured, always-shareable set of notes up to date while the meeting is still happening, trusting the human's edits over its own.

## Language

### Sessions and people

**Meeting**:
The real-world conversation note-machine listens to. note-machine does not own it; it is named only when talking about who attended and what kind of meeting it is.
_Avoid_: Call

**Session**:
One Meeting as captured by note-machine — one identity, one transcript, one set of notes. Stopping and resuming (after a crash, or for the second half of a workshop) continues the same Session; a Session is defined by its identity, not by continuous capture.
_Avoid_: Recording, live notes, run

**Operator**:
The person running note-machine for a Session. The Operator answers Proposals, sees Left for review and Nudges, and decides which Commands from others may change the Notes directly.
_Avoid_: User, owner, host

**Attendee**:
A person present in the Meeting, known by name so that transcription and Items spell them correctly.
_Avoid_: Participant, speaker

**Template**:
A named kind of Meeting — 1:1, standup, planning — that sets how the Notes are laid out and what the agent should pay most attention to (its focus). It never decides which kinds of Item exist or hides current Items. Changing it mid-Session applies only from then on, and is not an Op.
_Avoid_: Meeting type, profile, preset, format

**Run**:
A replay of a Session's transcript through one variant of the pipeline, for evaluation. A live Session is never a Run.
_Avoid_: Session (for replays), test

### Capture

**Source**:
One channel of captured speech in a Session — the Operator's mic, system audio, an imported recording. Every Chunk comes from exactly one Source.
_Avoid_: Input, device, stream

**Chunk**:
A span of captured audio from one source, handed to transcription. Its boundaries are acoustic (a time window or a silence), never about meaning.
_Avoid_: Transcript chunk, segment

**Transcript line**:
One short stretch of transcribed, corrected speech with its own start and end time and its source. A Chunk yields one or more Transcript lines; topic boundaries never shape them.
_Avoid_: Log line, utterance, sentence

**Transcript**:
The append-only, ordered Transcript lines of a Session — the ground truth everything else is traced back to. Never rewritten.
_Avoid_: Raw log, raw transcript

**Gist**:
A one-sentence, past-tense account of what was said over a range of Transcript lines — including stretches that yield no Items. Defined by the lines it covers, not by the step that produced it. Never part of the Notes.
_Avoid_: Summary, chunk summary

**Catch-up**:
The ordered Gists of a Session: a record of the conversation for someone who lost the thread. Sits beside the Notes, not in them.
_Avoid_: Feed, gist log

### Notes

**Notes**:
The shareable account of a Session: a Summary, the Attendees, and the current Items — only what is still relevant and true, never the history of how it got there. It is what lands in Slack if you copy mid-meeting; Catch-up, Proposals and Nudges sit outside it. Once the Session has ended, the Notes also show Left for review, which is not shared.
_Avoid_: Document, doc, state, live notes, output

**Summary**:
The one- or two-sentence account at the top of the Notes of what the Meeting is about and where it has got to, rewritten as the Meeting goes on.
_Avoid_: Gist, overview

**Item**:
One thought in the Notes, with a stable identity for the life of the Session and exactly one kind: Decision, Action, Question or Topic. An Item never changes kind, and is never deleted from the Session — it is either current or retired.
_Avoid_: Note, bullet, entry

**Decision**:
An Item recording something the Meeting agreed.
_Avoid_: Agreement, outcome

**Action**:
An Item recording a commitment by an owner to do something; it is either open or done, and a done Action is still current.
_Avoid_: Action item, task, todo

**Question**:
An Item recording something raised that needs an answer; it is either open or answered, and an answered Question with its answer is still current. When a Question is settled by agreement, it is answered and a separate Decision records the agreement.
_Avoid_: Open question (as the kind name)

**Topic**:
An Item recording a subject the Meeting discussed that is not a Decision, Action or Question.
_Avoid_: Note, discussion point

**Topic group**:
A short heading gathering related Topics. Only Topics are grouped.
_Avoid_: Theme, section

**Current**:
An Item still relevant and true. Only current Items appear in the Notes.
_Avoid_: Live, active

**Retired**:
An Item no longer current, kept in the Session with a record of how it was retired but absent from the Notes. An Item is retired only by being Superseded or Tombstoned.
_Avoid_: Deleted, removed, archived, resolved

**Superseded**:
Retired because newer Items replace it; it points at them. Combining and splitting Items supersede the originals, and the results are new Items.
_Avoid_: Overwritten, replaced, updated

**Tombstone**:
The mark on an Item a human removed: retired, and the same thought is blocked from being added again. Only a human Author tombstones.
_Avoid_: Deleted

**Locked**:
An Item a human has touched, as of the moment of that human Op. Nothing said before the lock can change it; what is said after the lock may supersede it, but its wording is never rewritten by the agent. Order is judged by when things were said, not when they were processed.
_Avoid_: Pinned, protected, frozen

### Changing the Notes

**Merge**:
The frequent pass that reads newly transcribed Transcript lines and turns them into Ops against the Notes, plus a Gist.
_Avoid_: Merge call, fast loop, update

**Editorial pass**:
The infrequent pass that reviews the whole Notes against a longer stretch of Transcript — catching what the Merge missed, answering Questions, tightening and grouping Items, refreshing the Summary.
_Avoid_: Editorial loop, compaction, cleanup

**Combine**:
Several Items of the same kind becoming one.
_Avoid_: Merge (reserved for the pass), dedupe

**Op**:
One atomic, named change to the Items, Summary or Attendees of the Notes. Every such change is an Op, whoever made it — the Merge, the Editorial pass, a Command, or a hand edit.
_Avoid_: Edit (for model changes), delta, patch, operation

**Author**:
Who an Op came from: a named human, or the agent. A Command's Ops are authored by whoever gave it; an accepted Proposal's Ops by the Operator who accepted it.
_Avoid_: Source (reserved for capture), actor

**Provenance**:
The specific Transcript lines that justify an Op — not everything the pass read. An Item's provenance is that of the Ops that shaped it. Housekeeping Ops inherit the provenance of the Items they act on; a new claim with no provenance is invalid. A human Op has no provenance; it is placed on the Transcript timeline by when it happened.
_Avoid_: Source, citation, evidence

**Proposal**:
One or more Ops note-machine wants to apply but that wait for a human to accept or dismiss. Its Ops change the Notes only once accepted.
_Avoid_: Suggestion, pending edit

**Left for review**:
The Proposals still unanswered when a Session ends, shown privately at the foot of the Notes. Derived from the Proposals themselves — never written by an Op; accepting one applies its Ops and removes it.
_Avoid_: Lapsed proposals, backlog

**Command**:
A request addressed to note-machine by anyone in the Meeting — spoken after the wake phrase, typed, or given silently; the channel makes no difference. The Operator's Commands that change the Notes apply directly; anyone else's become Proposals unless the Operator has allowed that Command. A Command's words stay in the Transcript but never become Items.
_Avoid_: Trigger, instruction, prompt

**Query**:
A Command that asks rather than changes. Answered the way it was asked; the answer reaches the Notes only as an accepted Proposal.
_Avoid_: Question (reserved for the Item kind), ask

**Nudge**:
A private prompt to the Operator about the Meeting in progress, pointing at something only a person in the room can act on. It carries no Ops and is never part of the Notes; if note-machine could make the fix itself with provenance, it is a Proposal instead.
_Avoid_: Alert, tip, card, notification

**Coach**:
The part of note-machine that watches the Meeting — including how the Operator is running it — and raises Nudges.
_Avoid_: Assistant, advisor

### Outside the Meeting

**Glossary**:
The terms note-machine should hear and spell correctly, each with the ways it is misheard. About recognition only, never meaning; not tied to one Session.
_Avoid_: Dictionary, vocabulary, jargon list

**Business context**:
What note-machine knows about the world outside the Meeting — what projects, initiatives and phases are and where they stand. It may clarify what an Item refers to, but never adds a fact the Meeting did not state.
_Avoid_: Knowledge base, memory, enrichment data

**Link**:
An Item's pointer to something outside the Meeting that the Meeting mentioned, such as a Jira ticket.
_Avoid_: Reference, attachment

**Finding**:
A piece of information note-machine obtained from outside the Meeting — from Business context or an Outside agent — carrying where it came from. Never part of the Notes on its own: it reaches them only as an accepted Proposal.
_Avoid_: Answer, result, research

**Outside agent**:
A tool or assistant belonging to the Operator that note-machine can ask for a Finding — another AI assistant, or a system like Jira.
_Avoid_: Integration, plugin, connector
