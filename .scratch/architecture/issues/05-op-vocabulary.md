# Op vocabulary: does update survive?

Type: prototype
Status: resolved
Blocked by: 01
Assignee: James

## Question

What is the minimal set of operations the model may emit against the notes — does `update_item` survive, or is the vocabulary add / supersede / resolve, with merge / split / rewrite demoted to proposals? Decide by replaying the eval transcripts with a throwaway variant that removes update ("variant B") and comparing against main on facts captured, final item count, median item length and duplicate rate.

## Context

- Accretion evidence: memo §02 (D12 → D43 → D70 → D74 in `state_20260914-090307-agentic-workflow-overview.json`).
- `apply_ops`, `apply_edits`, `editorial_pass` in `live_notes.py`; `evals/run_evals.py`.
- Prototype lives on a throwaway branch; link it here, don't merge it.
- From Core domain language: the duplicate-joining op is now **Combine** (Merge is the pass). Combine and Split must supersede, never delete. A new claim with no provenance lines is invalid. The agent may supersede a Locked Item only on lines said after the lock. Anything beyond the agent's direct Ops is a Proposal. See `CONTEXT.md`.

## Answer

**No, `update` does not survive. The Merge's ops are add / supersede / resolve.** When the model fixes an Item, the old one is retired as Superseded and a new Item replaces it, pointing back. The Editorial pass's reword, Combine and Split also supersede, and it applies them **directly**, not as Proposals.

How this was decided: a prototype replayed the three eval transcripts once for each version, on `qwen3.5:4b`, with only the fix op changed.
- **Add-only (no fixing) was weaker.** It wrote the same point again as new Items. The migration notes say "flip the experiment to start first" three times. It went silent on more chunks (25 against 15 in cycle planning). It lost two facts: communicating the plan early next week, and talking to Keith. One of those may be chance.
- **Update and supersede came out even.** Both kept every real fact, with the same Item counts (44/44 and 64/61) and length (median 7–8 words). Fixes are rare: 0–7 per meeting.
- **No run bloated.** The longest Item in any run was 16 words.
- **Supersede was chosen for its design, not its quality.** It matches `CONTEXT.md` (nothing is overwritten or deleted) and keeps history, so rewrite depth can be measured.
- **The Editorial pass applies its changes directly.** Nothing is deleted, so a bad Combine stays visible and can be undone. Proposals are kept for other people's Commands and for Findings.

Findings for later tickets:
- The 14 Sep accretion chain (D12 → D74, 40 → 102 words) came before the accretion guard, which was committed at 14:23 that day. Every saved session predates the guard.
- The Editorial pass has no word cap in code; only its prompt asks for one. The same session's 82-word Decisions and 217-word Topics are longer than the Merge's 40-word cap allows, so they came from the Editorial pass. It didn't happen in the replay, but the risk remains → Item & provenance contract.
- A Superseded Item must not block the same thought being added again. Only a Tombstone should. Today `find_duplicate` checks every retired Item.
- Gaps in the evals: keyword fact checks mark rewordings as misses (A's "flip experiment start to match ETL migration window" was scored as a miss). The duplicate rate misses the same point reworded. One run per version can't tell close versions apart → Eval workbench & regression gate.

Prototype: branch `prototype/op-vocabulary` (commit `6a8e0e3`), harness `evals/PROTOTYPE_op_vocab_ab.py`, report `evals/results/PROTOTYPE-op-vocab-ab.md`. Do not merge.
