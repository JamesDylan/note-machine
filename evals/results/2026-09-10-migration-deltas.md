# Eval: 2026-09-10-migration-deltas
*Run 2026-09-16 13:20, model qwen3.5:4b, whisper n/a (text replay)*

## Metrics
- Chunks: 79
- Ops emitted / applied: 69 / 63
- Silent chunks (model chose no ops): 15
- Merge failures (all retries exhausted): 0
- Editorial passes: 3
- Final item count: 64
- Invariant violations: 0

## Fact checks
- [FAIL] DECISION: experiment turned on before/with the migration, not after (any of: before the migration, before migration, experiment immediately, experiment on first, experiment first, then start the migration)
- [PASS] DECISION: first load targets single legal entity companies only (any of: single legal entit, single-entit, single entit)
- [PASS] 1.4 million company cohort (any of: 1.4 million)
- [PASS] document migration/reconciliation mechanics (contact Keith) (any of: Keith)
- [PASS] Snowflake vs SOL data discrepancies to investigate (any of: Snowflake)
- [PASS] multi legal entity companies excluded from first batch (any of: legal entit, multiple legal)
- [PASS] deactivation script needs company-level scope (any of: deactivat, disabled)
- [PASS] use-case/acceptance-criteria doc for QA (any of: use case, acceptance criteria, QA)

## Final notes

# Meeting Notes — Wed 16 Sep 2026

> Meeting addresses data mismatch risks during company migration and agrees to align experiment start with ETL.

## Decisions
- [13:08] Agreed to flip experiment start to match ETL migration window for reduced delta. <!--D21-->
- [13:14] Agreed to exclude multiple legal entities and split single-income entities into two runs. <!--D46-->

## Action Items
- [ ] [13:06] **Truthies team** — Truthies team handles reconciliation and pushes ledger changes. <!--A12-->
- [ ] [13:07] **Speaker** — Ask Dave to document token scenarios. <!--A20-->
- [ ] [13:08] Dave to document token scenarios and happy, edge, and delta cases. <!--A22-->
- [ ] [13:09] **James, Mita** — James and Mita to document edge cases. <!--A25-->
- [ ] [13:10] **Stravas** — Schedule meeting with company management. <!--A34-->
- [ ] [13:10] **Unknown** — Update script for company and member levels. <!--A35-->
- [ ] [13:18] **James, Chris** — James and Chris to discuss Delta with Keith and Richard. <!--A59-->
- [ ] [13:18] **Craig** — Craig to document token scenarios and transcript issues. <!--A62-->
- [ ] [13:19] QA team to review migration concerns. <!--A63-->
- [ ] [13:19] QA team to document migration issues. <!--A64-->

## Open Questions
- [13:11] Limited missing records are understandable edge cases. <!--Q38-->
- [13:13] Is the feature used as a language or currency tool? <!--Q45-->
- [13:14] Purpose of multiple legal entities unclear. <!--Q47-->
- [13:16] How to survey 46,000 active companies on setup preferences. <!--Q54-->
- [13:18] QA team involvement unclear for live migration. <!--Q60-->
- [13:18] Documentation gaps exist for live migration. <!--Q61-->

**Answered**
- ~~Will company migration impact product experience?~~ → **Company migration will impact product experience by temporarily hiding country/region UI for active companies.** <!--Q2-->
- ~~Data problems identified in previous environments.~~ → **No data problems exist; SOL remains the single source of truth for customers.** <!--Q7-->
- ~~Missing document covering happy, edge, and delta cases.~~ → **Documentation covering happy, edge, and delta cases is missing and needs to be created.** <!--Q10-->
- ~~Who is responsible for providing the documented scenarios?~~ → **James, Chris, and Craig are responsible for documenting token scenarios and migration cases.** <!--Q11-->
- ~~Reconciliation mechanics are unclear.~~ → **Reconciliation mechanics are unclear; hourly updates will push SOL changes to the platform.** <!--Q18-->
- ~~Missing documented use cases for migration and reconciliation.~~ → **Migration and reconciliation use cases are being documented by James, Mita, and Dave.** <!--Q23-->
- ~~Clarify migration and reconciliation roles for edge cases.~~ → **Roles for edge cases are clarified: exclusion list handles removals, inclusion list handles active companies.** <!--Q24-->

## Discussion
### Migration Timing and Drift
- [13:03] Gap in company migration for first experiment launch. <!--T1-->
- [13:04] Subset of companies selected one week prior to first experiment launch. <!--T3-->
- [13:04] EOS and SOL databases will not match on day one. <!--T4-->
- [13:04] Flip experiment start to match ETL migration window. <!--T5-->
- [13:06] Test migration in staging environment. <!--T13-->
- [13:06] Verify concerns in lower environments before production. <!--T14-->

### Migration Risks and Strategy
- [13:04] Dual reason rights will be non-existent post-migration. <!--T6-->
- [13:05] Alerting and dashboards will show mismatches. <!--T8-->
- [13:05] Hourly reconciliation updates platform with SOL changes. <!--T9-->
- [13:06] Product team increasing company usage risk. <!--T15-->
- [13:07] Dual rights flow covers reconciliation to SOL. <!--T16-->
- [13:07] Reconciliation documentation currently relies on Slack messages. <!--T17-->
- [13:07] Reconciler repo scores B4B experiences via AI. <!--T19-->
- [13:09] Need real measurement data matching production shape. <!--T28-->
- [13:10] Disabled script required for companies with no login or deactivation requests. <!--T33-->
- [13:10] Identify companies in SOL via tagging. <!--T36-->
- [13:11] Snowflake and SOL company mappings are not one-to-one. <!--T37-->
- [13:11] DSA provides include and exclude guidance from Snowflake. <!--T39-->
- [13:11] DLH provides notes on exclusion sequel regarding missing Snowflake data. <!--T40-->
- [13:11] Admin accounts without SSO access excluded from inclusion list. <!--T41-->
- [13:12] Admin access currently only available in SOL. <!--T42-->

### Inclusion and Exclusion Logic
- [13:09] Phased loading of single legal entities considered. <!--T26-->
- [13:09] Focus migration on active base companies. <!--T27-->
- [13:09] Phased loading of initial batch may cause temporary data drift. <!--T29-->
- [13:10] Inclusion and exclusion list drift expected. <!--T30-->
- [13:10] Exclusion list cannot be entered without a winner. <!--T31-->
- [13:10] Exclude customers waiting to be removed from migration. <!--T32-->

### Legal Entities and Multi-Country Companies
- [13:12] Exclusion list required for multiple legal entities. <!--T43-->
- [13:12] 1.4 million companies split into two runs for single-income entities. <!--T44-->
- [13:15] Legal entities concept added to product via new platform. <!--T48-->
- [13:15] Multi-legal entities required only for multi-country companies. <!--T49-->
- [13:15] Multi-country companies introduced to legal entity concept. <!--T50-->
- [13:15] Migrating single-income entities today avoids confusion if not split. <!--T51-->
- [13:17] Split companies into legal entities for future targeting. <!--T57-->

### Feature Rollout and Admin Flags
- [13:16] Phase three hides country and region UI. <!--T52-->
- [13:16] Multiple legal entity ownership unclear. <!--T53-->
- [13:17] Stop new customer registrations with countries and regions. <!--T55-->
- [13:17] Keep companies in current state to avoid delays. <!--T56-->
- [13:17] Admin flags required to target features before phase two. <!--T58-->


---
*Edit any bullet above and the change sticks — it will not be overwritten. Delete a bullet and it stays gone.*