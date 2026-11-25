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
Units1 had captured 3 of its 7 units after 4 h of its 6 h limit, so units2 (6 h, 13 units left) cannot finish either. Units are resumable (captures are
reused from the SQLite store; units-done.json is written only at the end), so job 32548062 (12 h, afterany units2) continues the same command, and the
stage-4 fetch 32545271 now also waits on it (Wayback refuses concurrent fetchers).

## Rank review of the 2016-17 Jacobs search rows (2026-11-24, claude-ucsd-1124)
No rank-map or override change: every PI keeps at least one row whose own printed title is a professor title (or the 2020+ "Full"/"Faculty" section heading). Calls:
- "Faculty , CSE" (5 rows, 2016-17, no rank word) stays `other` for those rows; those people are listed with real titles from 2017H2, which carries the PI basis.
- Multi-title rows take their rank from the department-matching title (CSE): "Professor , CSE; Faculty-Affiliate , Calit2" is ladder, correct. Sejnowski's "Co Dir/INC , CSE; Prof/HHMI Invsgtr , CSE"
  is ladder in 2016-17 (printed "Prof"), then adjunct in the CSE listings from 2017H2: a rank step as the source states it, not a misread. Whether he is a UCSD-CSE PI is a stage-3 D-0009/home question.
- Rows with no CSE-unit title but a professor title elsewhere ("Professor , ECE", "Professor , BENG", "Professor , NENG", "Professor , SE") are courtesy/adjunct for CSE.
- "Affiliate Professor (X)" 2017-2019 rows (Kuester, Bansal, Bewley, Dow, Dubnov, Guo, A. Gupta, Javidi, Kirsh, Levy, Mesirov, Norman, Tesler, A. Yu, Bharadia, Dameff, Mirarab) are courtesy_faculty and are the 16-17 homes held in stage 3. Roger Levy's affiliation is printed "(MIT)": his home is another university, so he is excluded in stage 2/3 (not UCSD faculty).
- "Chancellor , CSE" (Khosla) and "Interim Dean" rows are administrative titles; rank `other`/ladder as printed, to be settled by the home/basis rules.

## Same-person scan (census names)
Same surname in one unit: Cottrell (Garrison W. / Gary) = one DBLP pid c/GWCottrell with both names and ORCID 0000-0001-7538-1715: merged by a reviewed alias (below).
Unmerged, no source shows identity: Te Hu / T. C. Hu and Stanley Williamson / S. Gill Williamson (emeritus-only, non-PI either way, so no effect on PI counts); Mohammed A. Vahdat (adjunct 2016-17) / Amin Vahdat
(2019): DBLP lists only "Amin Vahdat", the Jacobs profile (fmp_recid 214) is not fetched; open item for the identity stage, affects Vahdat's PI years only.
Not the same person: Ronald Graham / Fan Chung Graham, Henrik Jensen / Carlos Jensen, George / Leo Porter, Rajesh / Amarnath Gupta, Arun / Deepak / Rakesh Kumar.

## Dry-run recall (2026-11-24, before unit review)
Reference set (discovery leads only; CSRankings is never copied): CSRankings UCSD entries 196, DBLP-affiliated >=5 records, OpenAlex rule: 170 strong references. 100 match a PI (59%, name matching is loose: CSR short forms
such as "Mark Alexander Connell Snoeren", "Tajana Simunic" count as misses), 27 census non-PI, 43 undecided (about 25 distinct people). Routes of the undecided: ECE (Koushanfar, Atanasov, Vasconcelos, Naghizadeh, Kang, Xie, Parhi, Antipa),
HDSI/SCIDS (Cloninger, Warstadt, Huang, Saab, Lau, Liao, Geiger, Watson-Parris), COGS (Bergen, Khosla, Hollan), MAE/BE not yet captured (Tolley, Gravish, Yip, Weng); all arrive through listing units
(captured or pending) and the DBLP/OpenAlex candidate files. SDSC/Qualcomm/SIO/CWC/Jacobs people arrive only via the DBLP route (SDSC: Wuerthwein, Majumdar, Baru, Kirkpatrick, Zheng, A. Singh; QI: DeFanti; SIO: J. Tan) and the OpenAlex rule.
`missed_labs_leads`: 1,250 leads (OpenAlex 1,015, DBLP 361, listed 10), top by computing output: Krstic, Cortes, Koushanfar, Atanasov, Vasconcelos (ECE/MAE), the rest mostly non-UCSD DBLP namesakes.

Update 2026-11-24 21:00: the Cottrell alias is `reviewed/census-name-aliases.json` (evidence: the school DBLP dump persons file from job 32548096, hash-checked); census_build now gives 222 persons, 135 PIs.
`listed_not_in_census`: 10 names, 0 likely missing PIs (unchanged).
