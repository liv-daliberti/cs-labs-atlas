# UCSD onboarding, stage 2 (faculty census) - in progress, 2026-11-24

Census from the CSE listings: 223 people, 136 PIs (basis ladder_faculty), 87 non-PI (lecturer, adjunct, emeritus-only, courtesy, research). Known identity issue to settle in stage 5/review:
"Garrison W. Cottrell" (2016-17 Jacobs search) and "Gary Cottrell" (2017+) are one person listed under two name forms and are not merged by the given-name rule.

Candidate routes (`cs_related_school.py candidates ucsd`): 485 = 362 DBLP-affiliated (5+ records) + 123 OpenAlex rule (job 32542535, sweep 420,614-work extension, 204 new
author ids before name matching). SDSC, Qualcomm Institute and SIO people do arrive through the DBLP route (spot-check: Wuerthwein, Majumdar, Baru, Kirkpatrick, DeFanti, Zheng,
Alok Singh at SDSC; Jing Tan at SIO), as do Qualcomm-industry coauthors that the review must exclude. `listed_not_in_census`: 10 names, 0 likely missing PIs.

Units: ECE, HDSI, COGS captured; job 32543022 continues (MATH, MAE, BE, SCCN); job 32545383 (afterany) covers 11 more unit directories added in the charter
(DBMI, BSB, Physics, Linguistics, Communication, Political Science, Rady, Visual Arts, Structural Eng., NANO, Design Lab). Music (`music-cms.ucsd.edu`) disallows AI agents by
name and is not used. `cs_related_school.py review` refuses until units-done.json covers the charter, so decisions, the final census refresh and the excluded audit draw wait on that.
Wayback captures run at ~10 minutes each while stage-3 discovery shares the lock (owner: leave sharing as is).
Stage 4 periods chain 32545271-32545276 is held on both (discovery 32543240, units2 32545383).
