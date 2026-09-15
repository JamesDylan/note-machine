# Op vocabulary: does update survive?

Type: prototype
Blocked by: 01

## Question

What is the minimal set of operations the model may emit against the notes — does `update_item` survive, or is the vocabulary add / supersede / resolve, with merge / split / rewrite demoted to proposals? Decide by replaying the eval transcripts with a throwaway variant that removes update ("variant B") and comparing against main on facts captured, final item count, median item length and duplicate rate.

## Context

- Accretion evidence: memo §02 (D12 → D43 → D70 → D74 in `state_20260914-090307-agentic-workflow-overview.json`).
- `apply_ops`, `apply_edits`, `editorial_pass` in `live_notes.py`; `evals/run_evals.py`.
- Prototype lives on a throwaway branch; link it here, don't merge it.
- From Core domain language: the duplicate-joining op is now **Combine** (Merge is the pass). Combine and Split must supersede, never delete. A new claim with no provenance lines is invalid. The agent may supersede a Locked Item only on lines said after the lock. Anything beyond the agent's direct Ops is a Proposal. See `CONTEXT.md`.
