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

## Review and audit (2026-11-25)
Units complete (18, `units-check` rc 0 with the worktree charter). `cs_related_school.py review ucsd`: 486 decisions = 77 accepted (added to the census builder), 3 faculty_not_computing, 5 research_or_other_rank,
397 no_source_covers_window + 8 identity_collision (excluded_unresolved via `excluded_audit.py convert`, never a proven absence). Profile proofs recorded by `cs_related_school.py profile` (cs-related-hand.json) for HDSI/COGS/MAE new hires.
D-0069: Roger Levy is `[census].not_pi` (LING captures start 2023 and do not show him; his CSE rows say "Affiliate Professor (MIT)"). Census: 222 persons, 134 PIs; +77 accepted additions pending stage-3/4 rerun.
Borderline rule outcomes for the owner: Zhijian Liu (HDSI, Assistant Professor, 0 DBLP records naming UCSD) and Meenakshi Khosla (COGS) fail the share test as new hires; Duncan Watson-Parris (HDSI, climate ML) fails at 2/62.
Strong references still without a decision (no profile page with a dated professor title fetched): Drusvyatskiy (MATH, directory is a script shell), Sherman, Jun-Kun Wang, Yip, Malladi, Fainman (ECE directory is a script shell; old Jacobs bio URLs time out); Sam Lau is an Assistant Teaching Professor (needs D-0009 PI-basis).
D-0068 SDSC/QI/SIO people (Wuerthwein, Majumdar, Baru, DeFanti, J. Tan, Kirkpatrick, Zheng) have no per-person profile proof yet: excluded_unresolved no_source_covers_window.
Audit: `stage_audit.py draw ucsd excluded --worker claude-ucsd-1124` seed 74282cbf1bd1, population 405, sample 50, file hierarchy/ucsd/reviewed/excluded-unresolved-audit.json (reviewer: claude-coordinator-ucsd-review).

## Rework after the coordinator's audit (2026-11-25): title-less directories
Audit seed 74282cbf1bd1: 48 pass, 2 fail (Leok, Warnke). Root cause: the review reads a unit capture as faculty evidence only when a professor title follows the name; the 2016-2021 MATH Faculty page prints no titles (and the R5 shell test flags it).
Fix through the supported reviewed-hand route (`cs-related-hand.json`, each entry bound to a stored capture sha256 and a verbatim quote): (1) the MATH Faculty page "Last, First" entries of every capture 2016-2021 count as ladder for that capture year, marked in a `note`
(the page does not mark lecturers, so a lecturer listed there would be read as faculty; the review's DBLP/share test still applies); (2) the live MATH page ("Professor Lutz Warnke") for 2026; (3) MAE Bitmead and McEneaney from the 2024-26 captures (the tool's next-person heuristic misread
"Professor Distinguished Professor"); (4) ECE/HDSI/PHYS entries for Jun-Kun Wang, Yip, Fainman, Drusvyatskiy, Wuerthwein (current captures, dated title); (5) research-scientist dispositions (`candidate_review` research_or_other_rank, source-bound) for SCCN Makeig, Delorme, Nakanishi, Wu,
HDSI Pazzani (Distinguished Researcher) and SE Bazilevs (Adjunct heading).
Result: accepted 88 (was 77: + Leok, Nie, Meyer, Suk, Rhoades, Verstraete, Warnke, Bitmead, McEneaney, Yip, Wuerthwein), research_or_other_rank 11, faculty_not_computing 5 (+ Fainman 5/190 and Drusvyatskiy 0 DBLP records: rule outcomes), excluded_unresolved 389 (381 no_source_covers_window, 8 identity_collision). Zhijian Liu/Khosla/Watson-Parris and the business/biology acceptances were not touched (owner).
Still open: Bo Li (two UCSD-Math DBLP pids 50/3402-7 with a Minnesota history and 50/3402-78; the directory proves a MATH professor "Li, Bo" 2016-21, but candidate_review cannot admit; recommendation: -7), Imani Sherman and Sadhika Malladi (no 2026 unit capture names them), Sam Lau (Assistant Teaching Professor: D-0009), SDSC/QI/SIO staff (no faculty proof; SDSC staff directory is a CGI page not fetched).
Census 222 persons, 134 PIs (Levy out); recall (name-match, indicative): 122 of 170 strong references match a PI, 25 non-PI, 8 decided negative, 3 excluded_unresolved, 14 undecided of which 11 are name-form misses of people already accepted or in the census (Cloninger, Warstadt, Yip, Naghizadeh Ardabili, Rose Yu, Snoeren, Simunic, Hollan, Sejnowski, Kuester, Lau/Samuel Lau) and 3 real (Sherman, Malladi, Sam Lau).

General Catalog coverage (coordinator, 2026-11-25): catalog.ucsd.edu/faculty/<DEPT>.html is archived from 2021-03 only. The 2015-2020 editions
lived at www.ucsd.edu/catalog/faculty/<DEPT>.html, and www.ucsd.edu/robots.txt has `User-agent: * / Disallow: /catalog/`, so they are not
used in any form (robots is never bypassed; the Wayback route is for challenged hosts only). Catalog evidence therefore covers 2021-2026;
a candidate whose UCSD faculty years all fall in 2016-2020 in a department with no usable own directory stays excluded_unresolved
unless a profile page or another unit capture proves the appointment.

## Rework after the second audit draw (2026-11-26, claude-agentE-census-1126)
Draw 2 (seed 74282cbf1bd1, population 405) failed 3 of 50 (Abarbanel, J. Fan, Puckette; coordinator verdicts). Shared cause: the review reads unit directory captures only, so a person whose
UCSD appointment is proven only by the General Catalog faculty list (`CAT_*` captures, 2021-2026 editions) or by a unit never searched (PSYC, MUS, ECON, POLI, PHYS catalog) stayed excluded_unresolved.
Class rework: every excluded_unresolved name (and alias) was matched against all 72 stored catalog captures (13 departments), counting a row as ladder only under a Professors / Associate / Assistant
Professors heading with no Adjunct or Emeritus qualifier. 10 rows matched; 9 ladder rows became source-bound hand entries (latest ladder catalog capture, verbatim quote, `note` naming the heading), and
Sharpee (catalog heading `Adjunct Professors` only) became a source-bound `research_or_other_rank` candidate_review. Review re-run: Abarbanel, Fan, Puckette, Schachner, Shishkin, Powell, Roberts, Gentner, Ma
accepted (share/DBLP test), Sharpee research_or_other_rank; four more rows (Weng accepted; Ojeda, Truong, Anemueller research_or_other_rank) moved because earlier hand entries were not yet reflected in the review file.
Counts now: accepted 98 (was 88), research_or_other_rank 15, faculty_not_computing 5, excluded_unresolved 375 (367 no_source_covers_window, 8 identity_collision). Census rebuilt (222 persons, 134 PIs; accepted additions 98).
The three failed rows are recorded `fixed` in `excluded-unresolved-audit.draw2-20261125.json` (the draw-2 audit, kept). Draw 3: seed 45d5df40ed91 (fresh random), population 375, sample 50, unreviewed; reviewer must not be the worker.
Not covered: a faculty list only in a department whose catalog edition is 2015-2020 (robots-disallowed, unused) stays a coverage limit.

## Rework after the third draw (2026-11-26, claude-agentE-census-1126)
Draw 3 (seed 45d5df40ed91) failed 4 of 50: Knop (MATH), Liu (Radiology), Hekler (Public Health), Aronoff Spencer (Medicine). Shared cause: catalog and unit-directory matching never reached medicine, public health, radiology or pediatrics.
Class rework: every excluded no_source row (367) was looked up on profiles.ucsd.edu/<first.last> (robots allow; Crawl-Delay 10 s kept): 37 profiles found. Rows whose profile title is an unqualified Professor / Associate / Assistant Professor
(not Adjunct, Emeritus, Recall, Clinical, Research, Project, Teaching) became hand entries with the page's own quote: Muotri, Aronoff Spencer, Du, J. Wang, Bazhenov, Hekler, Cloninger, Eikey. Knop: Wayback capture 2019-01-14 of his course page
("S.E. Warschawski Assistant Professor"); Liu: live fmri.ucsd.edu page ("Professor"). Review re-run (share/DBLP test): all ten accepted. accepted 98 -> 108; excluded_unresolved 365 (357 + 8 identity_collision).
The four failed rows are `fixed` in excluded-unresolved-audit.draw3-20261126.json. Draw 4: seed bfb152171556 (fresh random), population 365, n=50, unreviewed.
Computing scope: neuroimaging (Liu), digital health (Hekler, Aronoff Spencer) passed the owner's share/DBLP rule as written; no separate ruling was applied.
