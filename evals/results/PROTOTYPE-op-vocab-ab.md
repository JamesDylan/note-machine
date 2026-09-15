# PROTOTYPE — op vocabulary A/B/C
*2026-09-15 15:38, model qwen3.5:4b, one run per cell, temperature 0*

A = add/update/resolve (today) · B = add/resolve · C = add/supersede/resolve

## 2026-09-10-cycle-planning

| metric | A-update | B-add-only | C-supersede |
|---|---|---|---|
| chunks | 58 | 58 | 58 |
| facts captured | 6/6 | 5/6 | 6/6 |
| final items | 44 | 33 | 44 |
| median item words | 7.5 | 7 | 7.0 |
| longest item words | 14 | 16 | 14 |
| duplicate rate | 0.0 | 0.0 | 0.0 |
| ops applied | 45 | 32 | 40 |
| ops emitted | {"add": 39, "update": 7} | {"add": 33, "resolve": 1} | {"add": 40} |
| revisions applied | 0 | 0 | 0 |
| revisions refused | 0 | 0 | 0 |
| max revision chain | 0 | 0 | 0 |
| silent chunks | 15 | 25 | 19 |
| seconds | 438 | 511 | 542 |

- B-add-only missed: communication plan early next week

## 2026-09-10-migration-deltas

| metric | A-update | B-add-only | C-supersede |
|---|---|---|---|
| chunks | 79 | 79 | 79 |
| facts captured | 7/8 | 6/8 | 8/8 |
| final items | 64 | 69 | 61 |
| median item words | 7.0 | 7 | 8 |
| longest item words | 13 | 13 | 14 |
| duplicate rate | 0.0 | 0.0 | 0.0 |
| ops applied | 63 | 63 | 60 |
| ops emitted | {"add": 67, "update": 2} | {"add": 64} | {"add": 59, "supersede": 2} |
| revisions applied | 0 | 0 | 2 |
| revisions refused | 0 | 0 | 0 |
| max revision chain | 0 | 0 | 1 |
| silent chunks | 15 | 19 | 20 |
| seconds | 760 | 1449 | 2141 |

- A-update missed: DECISION: experiment turned on before/with the migration, not after
- B-add-only missed: DECISION: experiment turned on before/with the migration, not after, document migration/reconciliation mechanics (contact Keith)

## 2026-09-10-tool-test

| metric | A-update | B-add-only | C-supersede |
|---|---|---|---|
| chunks | 16 | 16 | 16 |
| facts captured | 2/3 | 2/3 | 2/3 |
| final items | 6 | 6 | 4 |
| median item words | 5.5 | 6.5 | 9.5 |
| longest item words | 6 | 16 | 11 |
| duplicate rate | 0.0 | 0.333 | 0.0 |
| ops applied | 6 | 6 | 5 |
| ops emitted | {"add": 7} | {"add": 7} | {"add": 7} |
| revisions applied | 0 | 0 | 0 |
| revisions refused | 0 | 0 | 0 |
| max revision chain | 0 | 0 | 0 |
| silent chunks | 9 | 9 | 9 |
| seconds | 105 | 98 | 102 |

- A-update missed: action to ask Claude / investigate why notes stopped
- B-add-only missed: action to ask Claude / investigate why notes stopped
- C-supersede missed: action to ask Claude / investigate why notes stopped

---

# Final notes, side by side

## 2026-09-10-cycle-planning — A-update

# Meeting Notes — Tue 15 Sep 2026

> The team agreed to test new cycle planning formats (videos and revamped slides) to improve visibility and product thinking without forcing attendance.

## Decisions
- [13:59] Test video recordings and revamped slide decks as alternatives to traditional presentations. <!--D23-->
- [14:03] Use two slides per PM: one for goals/metrics and one for engineering delivery info. <!--D42-->
- [14:03] Invite engineering partners as audience without changing the existing invite list. <!--D43-->
- [14:03] Align cycle planning cadence with Francis's update schedule to reduce redundant reporting. <!--D44-->

## Action Items
- [ ] [13:57] **PMs** — PMs record 2-5 minute videos on cycle plan storyline. <!--A14-->
- [ ] [13:57] Test video recording as alternative to slide deck. <!--A17-->
- [ ] [14:02] **Speaker** — PMs send completed surveys for feedback. <!--A41-->

## Open Questions
- (none yet)

## Discussion
### Engineering Leadership Challenges
- [13:56] Engineering team in flux <!--T1-->
- [13:56] Forcing mechanisms impacting partners and engineering managers <!--T2-->
- [13:56] Forcing partners to sync on forward leadership <!--T3-->
- [13:56] Product managers engaging partners on leadership level <!--T4-->

### Slide Deck Structure
- [13:56] Confirm two slides per PM for product board. <!--T5-->
- [13:56] Testing product board format for slide deck <!--T6-->
- [13:56] Include thinking exercises in product board format <!--T7-->
- [13:56] Include first slide with goals, success metrics, and lifecycle status <!--T8-->
- [13:56] Create end-to-end storyline for product board <!--T10-->
- [13:57] Revamp slide deck to follow first slide format. <!--T16-->

### Testing New Formats
- [13:57] Test two versions of cycle planning format <!--T11-->
- [13:57] Part-out managers follow cadence for V2 <!--T12-->
- [13:58] Test new cycle plan version with confident visibility and dependency call-outs. <!--T21-->
- [13:59] Engineering managers present lighter weight format. <!--T24-->

### Preparation and Tools
- [13:59] Create separate practice run for information spine construction. <!--T25-->
- [13:59] Use Giro for pre-work to simplify slide and cycle deck creation. <!--T26-->
- [14:00] Teams struggle with gathering information for decks. <!--T30-->
- [14:01] Finalize communication skeleton before sharing with PMs. <!--T36-->
- [14:01] Communicate plan early next week for preparation time. <!--T37-->

### Reporting and Syncs
- [14:00] Align cycle planning with Francis's update cadence. <!--T27-->
- [14:00] Engineering leadership reporting on low-level information. <!--T28-->
- [14:00] Invite engineering partners as audience without changing invite list. <!--T29-->
- [14:00] PMs must clearly communicate sync status with the team. <!--T31-->
- [14:00] PMs surface engineering team insights to understand their viewpoint. <!--T32-->

### Engagement and Backlog
- [14:00] Apply learned insights immediately rather than letting them disappear. <!--T33-->
- [14:01] Attendees lack full engagement during presentations. <!--T34-->
- [14:01] PMs drive story through ownership of what they look after. <!--T35-->
- [14:01] Teams struggle to fill backlogs. <!--T38-->
- [14:01] Shift focus from cycle planning due to roadmap changes. <!--T39-->
- [14:02] Forcing standards helps pin down logic despite time cost. <!--T40-->

### Other
- [13:56] Engineering teams present from product engineering angle <!--T9-->
- [13:57] PM Group think-out session for storyline clarity <!--T13-->
- [13:57] Test video recording as alternative to slide deck. <!--T15-->
- [13:57] Provide visibility into work without forcing attendance. <!--T18-->
- [13:58] Improve product thinking via small value slices. <!--T19-->
- [13:58] Revisit cycle plan storyline deeply. <!--T20-->
- [13:58] Include pause and reflection stories in objective level. <!--T22-->

---
*Edit any bullet above and the change sticks — it will not be overwritten. Delete a bullet and it stays gone.*

## 2026-09-10-cycle-planning — B-add-only

# Meeting Notes — Tue 15 Sep 2026

> Team redesigned cycle planning to improve visibility and engagement, testing video and simplified slide formats.

## Decisions
- [14:11] Agreed to test a new format with two slides per PM and a lighter engineering presentation. <!--D33-->

## Action Items
- [ ] [14:05] **PMs** — Record a short video explaining the cycle plan storyline. <!--A16-->
- [ ] [14:08] **PMs** — PMs create two slides per team. <!--A22-->
- [ ] [14:10] **Speaker** — Speaker completes survey before 11 AM meeting. <!--A32-->

## Open Questions
- (none yet)

## Discussion
### Audience and Engagement
- [14:03] Engineering team in flux <!--T1-->
- [14:03] Forcing partners to sync on forward leadership <!--T3-->
- [14:03] Forcing product managers to engage partners at leadership level <!--T4-->
- [14:04] Force engineering teams to present from product engineering angle <!--T9-->
- [14:04] Require EMs to provide lessons learned and changes <!--T10-->
- [14:07] Engineering managers to present lighter weight cycle plan. <!--T21-->
- [14:08] Engineering teams attend cycle planning as audience. <!--T26-->
- [14:09] PMs must ensure team sync and address uncertainties with their engineering manager. <!--T28-->

### Deck Structure and Content
- [14:03] Forcing mechanisms affecting partners and engineering managers <!--T2-->
- [14:03] Revisit the presentation deck <!--T5-->
- [14:04] Test product board format for accuracy <!--T6-->
- [14:04] Define spine of first slide covering CNC lifecycle movement and current motion. <!--T8-->
- [14:04] Create end-to-end storyline for product board <!--T11-->
- [14:04] Expand the first slide of the new cycle planning deck <!--T12-->
- [14:06] Previous cycle planning format was too difficult. <!--T18-->
- [14:06] Revisit cycle plan storyline deeply <!--T19-->
- [14:06] Test new cycle plan version with visibility and dependency call-outs. <!--T20-->
- [14:08] Practice constructing information spine before complex topics. <!--T23-->
- [14:09] Make information provision for decks default behavior. <!--T27-->

### Reporting Cadence and Learning
- [14:04] Envisage two versions of cycle planning format <!--T13-->
- [14:05] Part-out managers to follow new cadence <!--T14-->
- [14:05] PM Group think-out session for storyline clarity <!--T15-->
- [14:06] Use video format for cycle plan storyline <!--T17-->
- [14:08] Align cycle planning with Francis's separate update cadence. <!--T24-->
- [14:08] Engineering leadership reporting low-level info repeatedly <!--T25-->
- [14:09] Teams struggle to connect learning to exponential value delivery. <!--T30-->
- [14:10] Consider renaming cycle planning format. <!--T31-->

### Other
- [14:04] Strengthen thinking skills via product board exercises <!--T7-->
- [14:09] Learning insights are currently being lost. <!--T29-->

---
*Edit any bullet above and the change sticks — it will not be overwritten. Delete a bullet and it stays gone.*

## 2026-09-10-cycle-planning — C-supersede

# Meeting Notes — Tue 15 Sep 2026

> The team redesigned cycle planning to improve partner visibility and reduce friction by testing simplified formats.

## Decisions
- [14:16] Test simplified cycle planning formats (videos, one-way recording, revamped slides) to improve partner engagement. <!--D23-->
- [14:19] Solidify communication early next week. <!--D37-->
- [14:21] Test simplified formats: one-way videos, synchronized recordings, and revamped two-slide decks. <!--D42-->
- [14:21] Align engineering manager updates with cycle planning to reduce redundant reporting burdens. <!--D43-->
- [14:21] Preserve the pause-and-reflection storytelling element while reducing meeting duration. <!--D44-->

## Action Items
- [ ] [14:14] **Partners** — Partners record 2-5 minute videos on cycle plan storyline. <!--A15-->
- [ ] [14:16] **PMs** — PMs create two slides per partner covering delivery team learning. <!--A25-->
- [ ] [14:19] **Speaker** — Speaker completes survey before 11 AM meeting. <!--A40-->
- [ ] [14:20] **Partners** — Partners complete feedback form. <!--A41-->

## Open Questions
- (none yet)

## Discussion
### Forcing Mechanisms
- [14:12] Engineering team in flux <!--T1-->
- [14:12] Forcing mechanisms affecting partners and engineering managers <!--T2-->
- [14:12] Forcing partners to sync on forward leadership <!--T3-->
- [14:12] Product managers engaging partners at leadership level <!--T4-->

### Product Board Format
- [14:12] Revisit presentation deck <!--T5-->
- [14:12] Testing product board format <!--T6-->
- [14:12] Strengthening thinking skills via product board exercises <!--T7-->
- [14:12] Defining CNC lifecycle movement on first slide <!--T8-->
- [14:13] Creating end-to-end storyline for product board <!--T10-->
- [14:13] Refining product board presentation to include clear goal definition and next steps. <!--T11-->
- [14:17] Using information spine to practice product board storyline. <!--T26-->

### Execution & Visibility
- [14:13] Engineering teams must present lessons learned from product board exercises. <!--T9-->
- [14:13] PM Group leads think-out session for product board storyline. <!--T14-->
- [14:15] Revisiting cycle plan storyline deeply <!--T21-->

### Testing Formats
- [14:13] Exploring simplified vs full-cycle planning formats for engineering and product managers. <!--T12-->
- [14:14] Testing one-way video recording format. <!--T16-->
- [14:14] Using revamped slide deck for product board. <!--T17-->
- [14:15] Testing simplified cycle plan format for visibility. <!--T22-->
- [14:16] Testing lighter weight presentation format for engineering managers. <!--T24-->

### Cycle Planning Process
- [14:13] V2 cadence requires partners to sync with engineering managers. <!--T13-->
- [14:14] Providing visibility without forcing attendance. <!--T18-->
- [14:15] Cycle planning preparation timeline is two weeks. <!--T20-->
- [14:17] Aligning engineering manager updates with cycle planning. <!--T28-->
- [14:17] Current cycle planning process requires excessive reporting. <!--T30-->
- [14:17] Reducing cycle planning meeting duration by limiting speakers to PMs. <!--T31-->
- [14:18] Engineering information gathering should be a default process. <!--T32-->
- [14:19] Shifting cycle planning focus due to roadmap changes. <!--T38-->
- [14:19] Forcing cycle planning standards improves logic clarity. <!--T39-->

### Other
- [14:15] Current cycle planning format is too difficult for partners. <!--T19-->
- [14:17] Creating a slide decker to automate cycle planning. <!--T27-->
- [14:17] Engineering leadership reporting on low-level information. <!--T29-->
- [14:18] PMs must confirm team sync status and address uncertainties. <!--T33-->
- [14:18] PMs surfacing engineering team insights <!--T34-->
- [14:18] Learning insights are currently lost and not being applied. <!--T35-->
- [14:18] Recording dinner sessions for partner visibility. <!--T36-->

---
*Edit any bullet above and the change sticks — it will not be overwritten. Delete a bullet and it stays gone.*

## 2026-09-10-migration-deltas — A-update

# Meeting Notes — Tue 15 Sep 2026

> Meeting addresses data mismatch risks during company migration and agrees to align experiment start with ETL.

## Decisions
- [14:25] Agreed to flip experiment start to match ETL migration window for reduced delta. <!--D21-->
- [14:29] Agreed to exclude multiple legal entities and split single-income entities into two runs. <!--D46-->

## Action Items
- [ ] [14:23] **Truthies team** — Truthies team handles reconciliation and pushes ledger changes. <!--A12-->
- [ ] [14:24] **Speaker** — Ask Dave to document token scenarios. <!--A20-->
- [ ] [14:25] Dave to document token scenarios and happy, edge, and delta cases. <!--A22-->
- [ ] [14:25] **James, Mita** — James and Mita to document edge cases. <!--A25-->
- [ ] [14:26] **Stravas** — Schedule meeting with company management. <!--A34-->
- [ ] [14:27] **Unknown** — Update script for company and member levels. <!--A35-->
- [ ] [14:32] **James, Chris** — James and Chris to discuss Delta with Keith and Richard. <!--A59-->
- [ ] [14:32] **Craig** — Craig to document token scenarios and transcript issues. <!--A62-->
- [ ] [14:32] QA team to review migration concerns. <!--A63-->
- [ ] [14:32] QA team to document migration issues. <!--A64-->

## Open Questions
- [14:27] Limited missing records are understandable edge cases. <!--Q38-->
- [14:29] Is the feature used as a language or currency tool? <!--Q45-->
- [14:29] Purpose of multiple legal entities unclear. <!--Q47-->
- [14:31] How to survey 46,000 active companies on setup preferences. <!--Q54-->
- [14:32] QA team involvement unclear for live migration. <!--Q60-->
- [14:32] Documentation gaps exist for live migration. <!--Q61-->

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
- [14:21] Gap in company migration for first experiment launch. <!--T1-->
- [14:21] Subset of companies selected one week prior to first experiment launch. <!--T3-->
- [14:21] EOS and SOL databases will not match on day one. <!--T4-->
- [14:21] Flip experiment start to match ETL migration window. <!--T5-->
- [14:23] Test migration in staging environment. <!--T13-->
- [14:23] Verify concerns in lower environments before production. <!--T14-->

### Migration Risks and Strategy
- [14:22] Dual reason rights will be non-existent post-migration. <!--T6-->
- [14:22] Alerting and dashboards will show mismatches. <!--T8-->
- [14:22] Hourly reconciliation updates platform with SOL changes. <!--T9-->
- [14:23] Product team increasing company usage risk. <!--T15-->
- [14:23] Dual rights flow covers reconciliation to SOL. <!--T16-->
- [14:24] Reconciliation documentation currently relies on Slack messages. <!--T17-->
- [14:24] Reconciler repo scores B4B experiences via AI. <!--T19-->
- [14:26] Need real measurement data matching production shape. <!--T28-->
- [14:26] Disabled script required for companies with no login or deactivation requests. <!--T33-->
- [14:27] Identify companies in SOL via tagging. <!--T36-->
- [14:27] Snowflake and SOL company mappings are not one-to-one. <!--T37-->
- [14:27] DSA provides include and exclude guidance from Snowflake. <!--T39-->
- [14:27] DLH provides notes on exclusion sequel regarding missing Snowflake data. <!--T40-->
- [14:27] Admin accounts without SSO access excluded from inclusion list. <!--T41-->
- [14:28] Admin access currently only available in SOL. <!--T42-->

### Inclusion and Exclusion Logic
- [14:25] Phased loading of single legal entities considered. <!--T26-->
- [14:25] Focus migration on active base companies. <!--T27-->
- [14:26] Phased loading of initial batch may cause temporary data drift. <!--T29-->
- [14:26] Inclusion and exclusion list drift expected. <!--T30-->
- [14:26] Exclusion list cannot be entered without a winner. <!--T31-->
- [14:26] Exclude customers waiting to be removed from migration. <!--T32-->

### Legal Entities and Multi-Country Companies
- [14:28] Exclusion list required for multiple legal entities. <!--T43-->
- [14:28] 1.4 million companies split into two runs for single-income entities. <!--T44-->
- [14:30] Legal entities concept added to product via new platform. <!--T48-->
- [14:30] Multi-legal entities required only for multi-country companies. <!--T49-->
- [14:30] Multi-country companies introduced to legal entity concept. <!--T50-->
- [14:30] Migrating single-income entities today avoids confusion if not split. <!--T51-->
- [14:31] Split companies into legal entities for future targeting. <!--T57-->

### Feature Rollout and Admin Flags
- [14:30] Phase three hides country and region UI. <!--T52-->
- [14:31] Multiple legal entity ownership unclear. <!--T53-->
- [14:31] Stop new customer registrations with countries and regions. <!--T55-->
- [14:31] Keep companies in current state to avoid delays. <!--T56-->
- [14:31] Admin flags required to target features before phase two. <!--T58-->


---
*Edit any bullet above and the change sticks — it will not be overwritten. Delete a bullet and it stays gone.*

## 2026-09-10-migration-deltas — B-add-only

# Meeting Notes — Tue 15 Sep 2026

> Meeting agrees to flip experiment launch to start before ETL completion and focuses migration on active single-legal-entity companies.

## Decisions
- [14:42] Agreed to flip experiment launch to start before ETL completion. <!--D46-->
- [14:42] Decided to focus migration on active base companies rather than full phased loading. <!--D47-->
- [14:42] Agreed to prioritize disabling preloaded companies without registration dates. <!--D48-->

## Action Items
- [ ] [14:39] **Jacqui** — Schedule meeting with company management. <!--A34-->
- [ ] [14:42] [DSA] Provide include/exclude guidance from Snowflake data. <!--A49-->
- [ ] [14:42] [DLH] Document missing records from Snowflake in exclusion list. <!--A50-->
- [ ] [14:42] [Product Team] Clarify migration and reconciliation use cases for B4B experience. <!--A51-->
- [ ] [14:45] **James and Chris** — Document Delta listing for testing. <!--A63-->
- [ ] [14:45] **James and Chris** — Follow up with Richard on Snowflake Delta. <!--A64-->
- [ ] [14:45] QA team to review migration documentation. <!--A69-->

## Open Questions

**Answered**
- ~~Will product experience be impacted by the migration gap?~~ → **Product experience will be impacted by a temporary data gap until ETL reconciliation stabilizes.** <!--Q5-->
- ~~Is the migration edge case documentation complete?~~ → **Migration edge case documentation is incomplete and requires formalization by the Product Team.** <!--Q13-->
- ~~Is the feature used for language or currency?~~ → **Feature usage for language or currency is currently unknown and requires user surveying.** <!--Q45-->
- ~~Is multi-country usage for costing or legal entities?~~ → **Multi-country usage is currently unclear; companies are being parked for Phase Three legal entity setup.** <!--Q52-->

## Discussion
### Migration Timeline and Scope
- [14:33] Gap in companies migrated for first experiment launch <!--T1-->
- [14:33] 1.4 million companies migration target <!--T3-->
- [14:34] One week ETL and validation required before experiment launch. <!--T4-->
- [14:34] Subset of companies and members selected one week before experiment launch. <!--T6-->
- [14:34] Flip experiment launch to start on ETL process <!--T8-->
- [14:34] Experiment launch to precede migration <!--T10-->

### Single Legal Entity Cohort Growth
- [14:33] Single legal entity company migration cohort is increasing. <!--T2-->

### Data Discrepancies and Rights
- [14:34] EOS data may differ from SOL on experiment day one. <!--T7-->
- [14:34] Dual reason rights will be non-existent for migrated companies. <!--T9-->

### Reconciliation Mechanics and Alerts
- [14:34] Alerting and dashboards will show mismatches due to Eos data differences. <!--T11-->
- [14:35] Hourly reconciliation updates platform from SOL. <!--T12-->
- [14:35] Truthies team handles reconciliation and ledger updates. <!--T15-->
- [14:36] Version 1 assumes perfect data verification with no deltas. <!--T18-->

### Testing and Documentation Gaps
- [14:35] Migration scenario documentation required for testing. <!--T14-->
- [14:35] Test migration in staging environment <!--T16-->
- [14:36] Verify concerns in lower environments before production. <!--T17-->
- [14:45] Migration documentation gaps identified. <!--T66-->
- [14:45] Migration documentation and transcript completeness required. <!--T67-->

### Product Features and Legal Entities
- [14:36] Product team increasing company usage risk <!--T19-->
- [14:36] Reconciliation to SOL covers dual rights flow. <!--T20-->
- [14:37] Reconciliation documentation needs to be formalized. <!--T21-->
- [14:37] Reconciliation mechanics unclear for scenario planning <!--T22-->
- [14:38] Phased loading of 1.4 million companies is not required. <!--T26-->
- [14:39] Need production-like data for accurate failure measurement. <!--T28-->
- [14:39] Clarify impact of initial batch timing on data drift. <!--T29-->
- [14:39] Inclusion and exclusion list drift expected <!--T30-->
- [14:39] Exclusion list stability maintained for 1.4 million cohort <!--T31-->
- [14:39] Only preloaded companies remain on the right side. <!--T32-->
- [14:40] Company level migration requires additional steps beyond user-based script. <!--T35-->
- [14:40] Limited missing records fall under understandable edge cases. <!--T37-->
- [14:40] Provisioning 1.4 million companies from deactivated to migrated bucket. <!--T40-->
- [14:40] Admin access currently limited to SOL. <!--T41-->
- [14:41] 1.4 million companies split into two entities <!--T42-->
- [14:41] Legal entities, countries, and currencies used for content switching. <!--T44-->
- [14:43] Legal entities concept added to product later via new platform. <!--T53-->
- [14:43] Multi-country companies introduced to legal entity concept. <!--T54-->
- [14:43] Phase three allows moving people to linguistics while hiding countries and regions UI. <!--T56-->
- [14:44] Survey active companies on setup preferences. <!--T58-->

### Reconciliation and Use Cases
- [14:37] AI scoring mechanism for B4B experiences via reconciler <!--T23-->
- [14:38] Migration and reconciliation use cases require clarification. <!--T24-->
- [14:38] Distinguish migration scope from reconciliation coverage <!--T25-->
- [14:45] Define migration and reconciliation use cases <!--T68-->

### Active Single-Entity Focus
- [14:38] Focus migration on active base companies <!--T27-->
- [14:41] Migration scope limited to single legal entities. <!--T43-->
- [14:43] Migrate companies into single legal entities today. <!--T55-->
- [14:44] Legal entities to be handled in phase three. <!--T57-->
- [14:44] Split companies into legal entities. <!--T61-->

### Handling Preloaded and Multi-Country Companies
- [14:39] Pre-loaded companies without registration dates require disabling. <!--T33-->
- [14:44] Stop new customer registrations with countries and regions. <!--T59-->
- [14:44] Keep unmigrated companies to avoid delays. <!--T60-->

### Data Mapping and Missing Records
- [14:40] Snowflake and Soil company mappings are not one-to-one. <!--T36-->
- [14:40] DSA provides include and exclude guidance. <!--T38-->
- [14:40] DLH notes missing records from Snowflake. <!--T39-->

### Full Topic List
- [14:44] Flag company feature preferences. <!--T62-->
- [14:45] QA team involvement in migration testing unclear. <!--T65-->


---
*Edit any bullet above and the change sticks — it will not be overwritten. Delete a bullet and it stays gone.*

## 2026-09-10-migration-deltas — C-supersede

# Meeting Notes — Tue 15 Sep 2026

> The team plans a 1.4M company migration experiment, validating ETL first and resolving data drift issues.

## Decisions
- [15:01] Run the experiment on the ETL process itself before starting the full company migration. <!--D23-->
- [15:01] Verify all concerns in lower environments before proceeding to production. <!--D24-->
- [15:33] Run ETL validation one week prior to the first experiment. <!--D63-->

## Action Items
- [ ] [14:58] **Shruthi** — Run ETL and validation one week prior to the first experiment. <!--A5-->
- [ ] [14:58] **Chris** — Run experiment on ETL process during migration. <!--A7-->
- [ ] [14:58] **Team** — Run experiment before migration starts. <!--A9-->
- [ ] [15:00] **Speaker** — Ask Dave to document token processes. <!--A21-->
- [ ] [15:01] **James, Mita** — James and Mita validate B4B edge cases. <!--A27-->
- [ ] [15:03] **Stravas** — Schedule meeting with company management on priority. <!--A37-->
- [ ] [15:03] **Speaker** — Speaker document SOL company identification method. <!--A39-->
- [ ] [15:31] **James, Chris** — James and Chris discuss Delta with Keith and Richard. <!--A59-->
- [ ] [15:32] **Team** — QA teams check staging before going live. <!--A60-->
- [ ] [15:32] **Craig** — Create separate page for transcript documentation. <!--A61-->
- [ ] [15:32] **Team** — QA team review documentation. <!--A62-->

## Open Questions
- [15:00] Reconciliation mechanics unclear for scenario coverage. <!--Q20-->
- [15:01] Use cases for migration and reconciliation are unclear. <!--Q25-->
- [15:04] Feature usage purpose unclear: language agency or currency. <!--Q47-->
- [15:30] Purpose of multi-country/region usage unclear: costing or currency. <!--Q48-->

**Answered**
- ~~Missing documentation on happy, edge, and delta cases.~~ → **Happy, edge, and delta case documentation is now missing.** <!--Q12-->
- ~~Unclear who is responsible for documenting test scenarios.~~ → **Speaker will document test scenarios and QA review sets.** <!--Q13-->
- ~~Reconciliation documentation is currently missing.~~ → **Reconciliation documentation is currently missing and needs creation.** <!--Q19-->

## Discussion
### Migration Scope and Timeline
- [14:57] Gap in company migration for first experiment launch <!--T1-->
- [14:58] Company migration target increased to 1.4 million companies <!--T3-->
- [15:02] Migration timeline extended due to congestion and scope increase. <!--T30-->
- [15:02] Migration scope limited to preloaded companies due to congestion. <!--T35-->

### Reconciliation Mechanics
- [14:58] EOS data changes preventing SOL database replica on day one <!--T6-->
- [14:58] Alert and dashboard mismatches post-migration <!--T10-->
- [14:59] Hourly reconciliation process updates platform from SOL <!--T11-->
- [15:00] Reconciliation to SOL flow covered by dual rights <!--T18-->
- [15:00] Token reconciliation requires requesting extra tokens without returns. <!--T22-->

### Data Drift and Mapping
- [15:03] Snowflake and soil company mappings are not one-to-one. <!--T40-->
- [15:03] DSA provides include and exclude guidance from Snowflake. <!--T41-->
- [15:03] DLH provides notes on exclusion sequel regarding missing Snowflake data. <!--T42-->
- [15:03] Provisioning 1.4 million companies from deactivated to migrated bucket. <!--T43-->

### Legal Entities and Multi-Country
- [15:04] Multiple legal entities excluded via separate Snowflake database. <!--T44-->
- [15:04] Truth splits 1.4 million companies into two entities. <!--T45-->
- [14:58] Migration scope limited to single legal entities. <!--T46-->
- [15:30] Legal entities will be added via new platform without SOL equivalent. <!--T49-->
- [15:30] Multi-country companies introduced to legal entity concept. <!--T50-->
- [15:30] Proposed migration to single legal entities if multi-entity skipped. <!--T51-->
- [15:31] Multiple legal entities deferred to phase three. <!--T53-->

### Feature Flags and Active Companies
- [15:31] Handling 46,000 active companies regarding setup status <!--T54-->
- [15:31] Stop new customer registrations with countries and regions. <!--T55-->
- [15:31] Companies expecting a feature must remain in current state. <!--T56-->
- [15:31] Split companies into legal entities for feature flagging. <!--T57-->
- [15:31] Feature flags tied to flexible currency availability. <!--T58-->

### Other
- [14:58] Dual reason rights become non-existent post-migration <!--T8-->
- [14:59] Truthies team responsible for reconciliation and ledger updates <!--T14-->
- [14:59] Verify concerns in lower environments before production. <!--T15-->
- [15:00] Version 1 use case: perfect happy path extraction with no deltas <!--T16-->
- [15:00] Company migration increases usage risk and delta <!--T17-->
- [15:01] Clarify migration and reconciliation edge cases <!--T26-->
- [15:02] Phased loading preferred over first-load inclusion <!--T28-->
- [15:02] Focus migration on active companies to reduce scope. <!--T29-->
- [15:02] Need real production-like data for accurate measurement. <!--T31-->
- [15:02] Data drift occurs between initial batch and replay stages. <!--T32-->
- [15:02] Data drift between inclusion and exclusion lists. <!--T33-->
- [15:02] Exclusion list items cannot re-enter inclusion list in first cohort. <!--T34-->
- [15:02] Disabled companies require removal via right-to-be-forgotten script. <!--T36-->
- [15:03] Script updates needed for company-level members <!--T38-->
- [15:30] Phase three hides country and region UI. <!--T52-->

---
*Edit any bullet above and the change sticks — it will not be overwritten. Delete a bullet and it stays gone.*

## 2026-09-10-tool-test — A-update

# Meeting Notes — Tue 15 Sep 2026

> Meeting confirmed WISPR model size change and Sydney updates, but live notes generation is failing.

## Decisions
- (none yet)

## Action Items
- (none yet)

## Open Questions
- (none yet)

## Discussion
### Model Configuration
- [15:33] WISPR model size changed to small. <!--T1-->
- [15:33] Update plan.md to reflect Sydney changes. <!--T2-->
- [15:34] WISPR model work has stopped. <!--T6-->

### Live Notes Failure
- [15:34] Live Notes are not being updated. <!--T3-->
- [15:34] Live Notes update failure. <!--T4-->
- [15:34] Live Notes updates are failing. <!--T5-->


---
*Edit any bullet above and the change sticks — it will not be overwritten. Delete a bullet and it stays gone.*

## 2026-09-10-tool-test — B-add-only

# Meeting Notes — Tue 15 Sep 2026

> Meeting confirmed WISPR model size change and plan.md update, but revealed live notes are failing to update.

## Decisions
- (none yet)

## Action Items
- (none yet)

## Open Questions
- [15:36] Live notes and action items fail to update after creation. <!--Q4-->
- [15:36] Action items are not updating. <!--Q7-->

**Answered**
- ~~Live meeting action items are not updating.~~ → **Action items are not updating because the system fails to persist them after being asked.** <!--Q5-->

## Discussion
- [15:35] WISPR model size changed to small. <!--T1-->
- [15:35] Sydney update needs plan.md revision. <!--T2-->
- [15:35] Live notes update mechanism is broken and WISPR model work has stopped due to this failure. <!--T3-->

---
*Edit any bullet above and the change sticks — it will not be overwritten. Delete a bullet and it stays gone.*

## 2026-09-10-tool-test — C-supersede

# Meeting Notes — Tue 15 Sep 2026

> Meeting confirmed WISPR model size change and plan.md update, but notes generation is failing.

## Decisions
- (none yet)

## Action Items
- (none yet)

## Open Questions

**Answered**
- ~~Why live meeting notes are not being updated.~~ → **Live notes generation is failing despite asking Claude directly.** <!--Q4-->

## Discussion
### Documentation Updates
- [15:37] Update plan.md to reflect Sydney changes. <!--T2-->

### Other
- [15:37] WISPR model size bumped from base to small with cached weights. <!--T1-->
- [15:37] Mentally ticked off against phase 2 but document needs specific update. <!--T6-->

---
*Edit any bullet above and the change sticks — it will not be overwritten. Delete a bullet and it stays gone.*
