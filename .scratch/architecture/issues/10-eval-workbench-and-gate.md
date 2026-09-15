# Eval workbench & regression gate

Type: grilling
Blocked by: 03, 06

## Question

What shape does the eval framework take — run identity (git sha + config + model), where results live, which deterministic metrics and human A/B verdicts are recorded, how a live "flag for eval" promotes a case, and what gate an agent must pass before a pipeline change is accepted?

## Context

- `evals/run_evals.py`, `evals/expected/*.json`, README add-a-case ritual; memo §05 (side-by-side, three missing metrics, verdict as score).
- Scratchpad: "don't reinvent the wheel".
- From Core domain language: **Run** = an eval replay of a Session's Transcript through one variant. Rewrite depth follows from Superseded chains and the Op log, and nothing is deleted.
