# Eval: 2026-09-10-migration-deltas
*Run 2026-09-10 14:57, model qwen3.5:4b, whisper n/a (text replay)*

## Metrics
- Chunks: 84
- Ops emitted / applied: 68 / 68
- Silent chunks (model chose no ops): 21
- Merge failures (all retries exhausted): 0
- Editorial passes: 3
- Final item count: 44
- Invariant violations: 0

## Fact checks
- [FAIL] DECISION: experiment turned on before/with the migration, not after (any of: before the migration, before migration, before running the migration, then start the migration, experiment on first)
- [FAIL] DECISION: first load targets single legal entity companies only (any of: single legal entity, single-entity, single entity)
- [PASS] 1.4 million company cohort (any of: 1.4 million)
- [PASS] document migration/reconciliation mechanics (contact Keith) (any of: Keith)
- [PASS] Snowflake vs SOL data discrepancies to investigate (any of: Snowflake)
- [PASS] multi legal entity companies excluded from first batch (any of: legal entit, multiple legal)
- [PASS] deactivation script needs company-level scope (any of: deactivat, disabled)
- [PASS] use-case/acceptance-criteria doc for QA (any of: use case, acceptance criteria, QA)

## Final notes

# Live Meeting Notes

*The team agreed to launch the experiment immediately on a 50-50 split for single legal entities only, accepting data drift between SOL and EOS while halting migration for multi-country users until their intent is clarified.*

## Decisions
- Agreed to launch the experiment immediately on a 50-50 split for single legal entities only, accepting data drift between SOL and EOS as acceptable since SOL remains the master source, and holding back users with multiple countries/regions until their intent regarding multiple legal entities is clarified.

## Action Items
- Shruthi to run ETL and validate a subset of companies and members fit for launch within one week, noting Marjane is provisioning 1.4 million companies from the deactivated bucket.
- Launch the experiment on the dual reason rights feature on a 50-50 split to validate impact before rolling it out to everyone, specifically restricting the cohort to single legal entities only.
- Truthies team to implement the reconciliation process and push changes to the ledger.
- Evaluate running the experiment in staging first to verify migration edge cases, noting that staging saves only about a week compared to the full migration timeline.
- Document the hourly reconciliation process to replace informal Slack discussions.
- Dave to document the reconciliation process mechanics to replace informal Slack discussions.
- James and Mita to document the specific test cases and scenarios required for the experiment launch.
- Stravas to schedule a conversation with the company management team to prioritize bumping up the disabled cohort list to address login issues for users without opt-out accounts and manage the situation with them.
- Chris and Jeffrey to provide additional details regarding company-level and member-level logic requirements by Monday to prioritize the necessary script updates.
- DSA to provide include and exclude guidance from Snowflake data and DLH to provide notes on missing exclusion sequences, with ownership and validation sets assigned to engineering for products.
- James and Chris to coordinate with Keith and Richard to finalize documentation and testing details for the Delta environment.
- Craig to extract available transcript data and create a separate page in the working document set to address the missing transcript issue.

## Open Questions
- ~~Are there data problems that could affect the experiment? (resolved, limited records missing from Snowflake fall under understandable edge cases like SK admin user type)~~ — **Limited records missing from Snowflake are understandable edge cases (e.g., SK admin users) and do not affect the experiment.**
- ~~Can you explain what the hourly reconciliation process does?~~ — **The hourly reconciliation process compares SOL and EOS data to minimize delta noise, with SOL remaining the master source.**
- Who is responsible for documenting the scenarios required to test the experiment?
- Kasey needs to answer a specific question regarding the institution's answers to provide reassurance.
- What are the specific test cases that need to be documented and verified for the experiment launch?
- What are the specific mechanics and inner workings of the reconciliation migration process to enable comprehensive scenario planning?
- What are the specific use cases for the migration and reconciliation processes that need to be understood to avoid assumptions about their reliability?
- Will moving the experiment to the active base of companies instead of the 1.1 million non-active companies change the timeframe for reconciliation and migration?
- What is the expected impact of data drift between the start and end points of the initial batch migration process?
- Is there a mechanism for companies to move from the exclusion list to the inclusion list if the system is limited to the initial 1.4 million companies?
- Will multi-country companies be able to set up legal entities themselves in the product, or is there an expectation that the system will provide pre-configured options for them?
- How should we survey the 46,000 active companies to determine their intent regarding legal entity setup given the lack of time to manage a full UI change process?
- Will users be able to opt-in to the new legal entities feature, or will the functionality remain hidden until a future phase?
- Is the specific problem being tested in the current experiment fully documented?
- What are the specific use cases for the migration and reconciliation processes that need to be understood to avoid assumptions about their reliability?

## Topic Notes

**Migration Scope and Volume**
- Gap in companies migrated for the first launch of the experiment; target increased to 1.4 million due to Booking.com's requirement to include all companies and product team intent to increase risk of uses for companies.
- Gap in companies migrated for the first launch of the experiment; target increased to 1.4 million due to Booking.com's requirement to include all companies and product team intent to increase risk of uses for companies, though initial load does not need to include all companies to avoid increasing complexity.
- Gap in companies migrated for the first launch of the experiment; target increased to 1.4 million due to Booking.com's requirement to include all companies and product team intent to increase risk of uses for companies, though initial load does not need to include all companies to avoid increasing complexity.
- Gap in companies migrated for the first launch of the experiment; target increased to 1.4 million due to Booking.com's requirement to include all companies and product team intent to increase risk of uses for companies, though initial load does not need to include all companies to avoid increasing complexity.
- Gap in companies migrated for the first launch of the experiment; target increased to 1.4 million due to Booking.com's requirement to include all companies and product team intent to increase risk of uses for companies, though initial load does not need to include all companies to avoid increasing complexity, with the reality being that everything moved to the left side except preloaded companies remaining on the right due to BBM congestion.
- Gap in companies migrated for the first launch of the experiment; target increased to 1.4 million due to Booking.com's requirement to include all companies and product team intent to increase risk of uses for companies, though initial load does not need to include all companies to avoid increasing complexity, with the reality being that everything moved to the left side except preloaded companies remaining on the right due to BBM congestion, and there is no one-to-one mapping between Snowflake and SOL companies representing a low percentage discrepancy.

**Experiment Scope & Mechanics**
- A reconciler repo exists where AI and business language can be used to determine a score for handling B4B experiences.

**Data Drift and Exclusion Logic**
- Expected impact of data drift between the start and end points of the initial batch migration process involves a shift where the exclusion list becomes less useful as the system takes all companies except those on a removal list, creating a drift between inclusion and exclusion lists.
- Expected impact of data drift between the start and end points of the initial batch migration process involves a shift where the exclusion list becomes less useful as the system takes all companies except those on a removal list, creating a drift between inclusion and exclusion lists, with everything moved to the left side except preloaded companies remaining on the right due to BBM congestion.
- Expected impact of data drift between the start and end points of the initial batch migration process involves a shift where the exclusion list becomes less useful as the system takes all companies except those on a removal list, creating a drift between inclusion and exclusion lists, with everything moved to the left side except preloaded companies remaining on the right due to BBM congestion, and a rigorous data governance system is in place to identify and manage discrepancies between the two information sources.
- Expected impact of data drift between the start and end points of the initial batch migration process involves a shift where the exclusion list becomes less useful as the system takes all companies except those on a removal list, creating a drift between inclusion and exclusion lists, with everything moved to the left side except preloaded companies remaining on the right due to BBM congestion, and the exclusion list for multiple or legal entity situations is managed in a separate Snowflake database.

**Other**
- Future addition of legal entities to the product will utilize the new platform, which will have no equivalent to SOL.
- Admin accounts do not require inclusion in the experiment list because they lack SSO access to EOS and are not receiving credit, so they can remain excluded, noting that admin access was previously assumed to be only in SOL.
- Migrating companies today is unnecessary because users won't notice a difference if they aren't moved into different legal entities; the suggestion is to migrate them as single entities instead.
- The current experiment hides the countries and regions UI to prevent users from seeing or managing that functionality, whereas a future phase three will allow users to move people to different legal entities.
- The current experiment hides the countries and regions UI to prevent users from seeing or managing that functionality, whereas a future phase three will allow users to move people to different legal entities, and the team has decided to park the handling of multiple legal entities for now due to uncertainty about user intent.

## Asked
- (none yet)