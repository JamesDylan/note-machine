# Meeting Notes — Wed 16 Sep 2026

> Meeting confirmed October migration scope excludes company cards, established automated failover for SDK errors, and set up New Relic dashboards for monitoring.

**Attendees:** Zac, James, Lilly

## Decisions
- [14:56] Remove feature for all new companies. <!--D33-->
- [14:57] Disable feature for all new companies. <!--D35-->

## Action Items
- [ ] [14:42] No business time available in October. <!--A8-->
- [ ] [14:45] **Renee** — Implement error threshold for 500 SDK failures. <!--A12-->
- [ ] [14:49] Review high company credit card payment options. <!--A21-->
- [ ] [14:58] **Jacqui** — Disable new registrations for the feature. <!--A39-->

## Open Questions
- (none yet)

## Discussion
### Results Timeline
- [14:39] Country and region results available in an hour. <!--T1-->
- [14:39] Results arriving in stages for languages and legal entities. <!--T3-->

### Migration Scope
- [14:41] Company migration scope document received. <!--T4-->
- [14:47] Scope limited to travel accounts and Booking.com. <!--T17-->
- [14:47] Company credit cards excluded from scope. <!--T18-->
- [14:48] Booking.com leisure profile cards used instead of Serko. <!--T19-->

### Monitoring Setup
- [14:42] New Relic Dashboard for legacy payment errors. <!--T6-->
- [14:42] Use New Relic dashboard to compare Delta results. <!--T7-->

### Failover Strategy
- [14:43] Immediate rollback to legacy path if B4B experiment causes harm. <!--T9-->
- [14:44] Agreed failover strategy for Y label conference page. <!--T11-->
- [14:45] Switch to Booking.com white label due to lack of rollback. <!--T13-->
- [14:46] Automatic switching based on 500 SDK errors. <!--T15-->
- [14:46] Automated failover for third-party services. <!--T16-->

### Other
- [14:39] Quantify the issue to win it back with the new version. <!--T2-->
- [14:43] Booking.com white label payment integration. <!--T10-->
- [14:46] Checkout split into two pages. <!--T14-->
- [14:49] Corporate card sharing solution scales to punch outs. <!--T20-->
- [14:49] Corporate card sharing required for hotel funnel. <!--T22-->
- [14:51] Remove duplicate bookings from SOL and Eos. <!--T23-->
- [14:51] SOL team addresses small user experience issue. <!--T24-->
- [14:52] Users reported missing options when selecting preferences. <!--T25-->
- [14:52] Ship the forked SOL front end code. <!--T26-->
- [14:54] Eos migration scope includes partial company inclusion. <!--T27-->
- [14:54] Clean up duplicate bookings to protect team capacity. <!--T28-->
- [14:54] Delete pre-loaded jams. <!--T29-->
- [14:55] Determine target criteria via SOL database flag. <!--T30-->
- [14:56] Delete pre-loaded companies only. <!--T31-->
- [14:56] Traxxo discontinuing relationship with walking.com. <!--T32-->
- [14:57] Booking.com supplies on-border clients including Serko. <!--T34-->
- [14:57] A.B. test to hide feature for non-users. <!--T36-->
- [14:58] Booking.com ending Traxco service. <!--T37-->
- [14:58] Create offboarding workflow for current users. <!--T38-->
- [14:58] Offload Delta users by year-end. <!--T40-->

---
*Edit any bullet above and the change sticks — it will not be overwritten. Delete a bullet and it stays gone.*