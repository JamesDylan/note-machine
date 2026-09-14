# Eval: 2026-09-10-migration-deltas
*Run 2026-09-14 14:37, model qwen3.5:4b, whisper n/a (text replay)*

## Metrics
- Chunks: 78
- Ops emitted / applied: 66 / 62
- Silent chunks (model chose no ops): 16
- Merge failures (all retries exhausted): 0
- Editorial passes: 3
- Final item count: 62
- Invariant violations: 0

## Fact checks
- [FAIL] DECISION: experiment turned on before/with the migration, not after (any of: before the migration, before migration, experiment immediately, experiment on first, experiment first, then start the migration)
- [PASS] DECISION: first load targets single legal entity companies only (any of: single legal entit, single-entit, single entit)
- [FAIL] 1.4 million company cohort (any of: 1.4 million)
- [PASS] document migration/reconciliation mechanics (contact Keith) (any of: Keith)
- [PASS] Snowflake vs SOL data discrepancies to investigate (any of: Snowflake)
- [PASS] multi legal entity companies excluded from first batch (any of: legal entit, multiple legal)
- [PASS] deactivation script needs company-level scope (any of: deactivat, disabled)
- [PASS] use-case/acceptance-criteria doc for QA (any of: use case, acceptance criteria, QA)

## Final notes

# Meeting Notes — Mon 14 Sep 2026

> Meeting addresses data mismatch risks during company migration and agrees to flip experiment start to align with ETL.

## Decisions
- (none yet)

## Action Items
- [ ] [14:28] **Truthies team** — Truthies team handles reconciliation and pushes ledger changes. <!--A12-->
- [ ] [14:30] **Speaker** — Ask Dave to document token scenarios. <!--A20-->
- [ ] [14:31] **James, Mita** — James and Mita document edge cases. <!--A23-->
- [ ] [14:31] **Ruthie** — Ruthie provides loading timeline. <!--A26-->
- [ ] [14:32] **Jacqui** — Schedule meeting with company management. <!--A33-->
- [ ] [14:32] **Chris, Jeffrey** — Update script for company and member levels. <!--A34-->
- [ ] [14:32] **DSA** — DSA identifies SOL company tagging method. <!--A35-->
- [ ] [14:32] **DSA** — DSA provides include and exclude guidance from Snowflake. <!--A38-->
- [ ] [14:32] **DLH** — DLH provides note on exclusion sequel about missing Snowflake data. <!--A39-->
- [ ] [14:33] **Marjane** — Marjane moves companies from deactivated to migrated bucket. <!--A41-->
- [ ] [14:33] **Truthies team** — Truthies team splits 1.4M companies into two entities. <!--A44-->
- [ ] [14:36] **James, Chris** — James and Chris discuss Delta with Keith and Richard. <!--A59-->
- [ ] [14:36] **Craig** — Craig documents transcript problem. <!--A61-->
- [ ] [14:36] **Speaker** — QA team reviews migration concern document. <!--A62-->

## Open Questions
- [14:34] Users with multiple countries/regions may not intend multiple legal entities. <!--Q46-->
- [14:36] QA teams are not fully known for staging checks. <!--Q60-->

**Answered**
- ~~Will company migration impact product experience?~~ → **Company migration will impact product experience by hiding country/region UI for active companies.** <!--Q2-->
- ~~Data problems identified in previous environments.~~ → **No data problems exist; SOL is the master source of truth for customer information.** <!--Q7-->
- ~~Missing document covering happy, edge, and delta cases.~~ → **A new document covering happy, edge, and delta cases is being created by James and Chris.** <!--Q10-->
- ~~Who is responsible for providing the documented scenarios?~~ → **James and Chris are responsible for documenting the migration and reconciliation scenarios.** <!--Q11-->
- ~~Reconciliation mechanics are unclear.~~ → **Reconciliation mechanics are handled via hourly updates and a disabled script for excluded users.** <!--Q18-->
- ~~Missing documented use cases for migration and reconciliation.~~ → **Use cases for migration and reconciliation are being documented in a new working document.** <!--Q21-->
- ~~Clarify migration and reconciliation roles for edge cases.~~ → **Roles for edge cases are clarified: Truthies handles reconciliation, DSA manages tagging.** <!--Q22-->

## Discussion
### Migration Strategy and Timing
- [14:27] Gap in company migration for first experiment launch. <!--T1-->
- [14:27] Subset of companies selected one week prior to first experiment launch. <!--T3-->
- [14:28] Dual reason rights will be non-existent post-migration. <!--T6-->
- [14:28] Alerting and dashboards will show mismatches. <!--T8-->
- [14:28] Test migration in staging environment. <!--T13-->
- [14:29] Verify concerns in lower environments before production. <!--T14-->
- [14:31] Proposed moving active base to simplify product usage. <!--T25-->
- [14:31] Need production-like data to measure experiment failures. <!--T27-->
- [14:31] Initial batch timing and data drift between timelines. <!--T28-->
- [14:31] Inclusion and exclusion list drift expected. <!--T29-->
- [14:31] Exclusion list cannot be exited and re-entered. <!--T30-->

### Migration Timing and Drift
- [14:27] EOS and SOL databases will not match on day one. <!--T4-->
- [14:27] Flip experiment start to match ETL migration window. <!--T5-->
- [14:28] Hourly reconciliation updates platform with SOL changes. <!--T9-->
- [14:31] Phased loading avoids initial load complications. <!--T24-->

### Product Risk and Reconciliation
- [14:29] Product team increasing company usage risk. <!--T15-->
- [14:29] Dual rights flow covers reconciliation to SOL. <!--T16-->
- [14:29] Reconciliation documentation currently relies on Slack messages. <!--T17-->
- [14:30] Reconciler repo scores B4B experiences via AI. <!--T19-->

### Data Mapping and Exclusions
- [14:32] Serko agreement on customer data and migration scope. <!--T31-->
- [14:32] Disabled script required for companies with no login or deactivation requests. <!--T32-->
- [14:32] Snowflake and SOL company mappings are not one-to-one. <!--T36-->
- [14:32] Limited missing records are edge cases involving SK admin users. <!--T37-->
- [14:32] Admin accounts without SSO access excluded from inclusion list. <!--T40-->
- [14:33] Admin access currently limited to SOL. <!--T42-->
- [14:33] Exclusion list required for multiple legal entities. <!--T43-->
- [14:33] Migration scope limited to single legal entity. <!--T45-->

### Legal Entity and Multi-Country Strategy
- [14:35] Multi-legal entities required for multi-country companies. <!--T48-->
- [14:35] Multi-country companies introduced to legal entity concept. <!--T49-->
- [14:35] Proposed migrating companies to single legal entities. <!--T50-->
- [14:35] Multiple legal entity ownership unclear; handled in phase three. <!--T52-->

### Feature Rollout and User Consent
- [14:35] Surveying 46,000 active companies to determine setup intent. <!--T53-->
- [14:35] Stop new customer registrations with countries and regions. <!--T55-->
- [14:35] Companies expecting a feature must remain unmigrated. <!--T56-->
- [14:36] Currency feature availability tied to legal entity split. <!--T58-->

### Other
- [14:34] Product lacks legal entity concept; new platform required if added. <!--T47-->
- [14:35] Phase three hides country and region UI. <!--T51-->
- [14:35] Avoiding complex change processes for company setup. <!--T54-->
- [14:36] User consent needed for legal entity splitting. <!--T57-->

---
*Edit any bullet above and the change sticks — it will not be overwritten. Delete a bullet and it stays gone.*