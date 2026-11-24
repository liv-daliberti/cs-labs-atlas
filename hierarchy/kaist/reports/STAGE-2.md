# KAIST onboarding, stage 2 - 2026-11-24 (IN PROGRESS: stopped before the audit draw)

Not complete. The stage-2 gate has not been recorded and no 50-row audit has been drawn: the affiliated-unit search (`cs_related_school.py units kaist`, job 32542312) is still on the shared Wayback clock (about 4-5 min per CDX query or capture; EE alone is a paged directory). All 16 units are in the charter (EE, GSAI, KDS, ISYSE, MAS, GSIS, CT, ME, SEMI, AISEMI, BIOENG, AE, PHYS, CEE, NQE, CBE); the draw must wait for all of them (D-0003, coordinator 2026-11-24).

## Done so far
- Census (`census_build.py`, commit e135055f): 273 listing-name rows merged on the School of Computing's own profile id (`[census].profile_id_pattern`, `/people/view?idx=N`) into 166 persons, 77 PIs (53 ladder, 17 emeritus, 7 courtesy). The earlier 129 "PIs" were duplicate spellings of 77 persons. Sung-Eui Yoon (idx 20: 'Sungeui Yoon', 'Sung-Eui Yoon', '윤성의') is one ladder PI, years 2016-2026. No name-similarity merge exists anywhere.
- Hangul-only persons (no Latin spelling in any capture): 18 now (the coordinator counted 19 before the merge). The Latin name is taken only from the same profile page when it states `<Hangul>(<Latin>)` (`tools/profile_romanization_school.py`, reviewed/profile-romanization.json, quote + url + sha256): 1 found, 17 `romanization_missing`.
- Sweep from the snapshot extension: 56,613 papers, sweep check pass; DBLP dump persons naming KAIST: 542; OpenAlex candidate rule: 345 author ids (264 not matching a census name). All three feed `cs_related_school.py candidates|review` after the units land.
- Stage 3 preview on the corrected PIs (live-first, no Wayback): 77 PIs, homes School of Computing for all 77 (listing-row evidence, status accepted), website discovery done; 10 PIs open (9 `website archive evidence pending`, 1 `website official discovery link not recorded`); the homes audit draw is not taken.

## Still to do
units search -> `candidates` -> `review` (decide every candidate; unresolved = `excluded_unresolved` with reason) -> census-refresh/homes/build/discover for the added PIs -> `excluded_audit.py draw kaist --worker claude-kaist-1124` (stop; independent reviewer).
