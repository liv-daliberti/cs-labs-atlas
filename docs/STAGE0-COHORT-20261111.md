# Stage 0 cohort review, 2026-11-11

Scope: the 31 schools in `scratch/top25-goal-1107/stage0-4-current-1111.csv`. This report records a fresh automated gate run with `CS_ATLAS_SCHOOL_CONFIGS` pointing at the `agent/stage0-cohort-1111` worktree. It does not assert that the owner has approved the ten new schools' lineage decisions.

## Automated gate

All 31 `stage_gate.g0` calls returned zero issues on 2026-11-11. Toronto's 17 host receipts were refreshed in main. The ten new charters and their fresh host audits are in the branch. Their results are:

| School | Hosts | Snapshot works | Gate issues |
| --- | ---: | ---: | ---: |
| USTC | 7 | 228,965 | 0 |
| NUS | 2 | 311,554 | 0 |
| CUHK | 2 | 201,067 | 0 |
| PKU | 8 | 340,218 | 0 |
| WHU | 11 | 205,680 | 0 |
| UESTC | 1 | 149,644 | 0 |
| SEU | 9 | 194,849 | 0 |
| UT Austin | 14 | 361,327 | 0 |
| Purdue | 10 | 291,670 | 0 |
| HIT | 9 | 228,292 | 0 |

The snapshot-work counts are available through the existing filtered snapshot's lineage reader. They do not establish that a reviewed school sweep or a faculty census has completed. Stages 1 onward remain independent.

## Owner lineage decisions required by `docs/ADDING-A-SCHOOL.md`

The following are the *proposed* charter rules. Confirm or revise them before declaring manual Stage 0 complete or running a lineage sweep. The charter `ids_note` fields give the local OpenAlex institution record observations. The live ROR API was unavailable to the project client for some schools, so its relationships remain unverified independently.

| School | Proposed boundary |
| --- | --- |
| USTC | Include the USTC primary institution; exclude the shared Collaborative Innovation Center of Advanced Microstructures, Suzhou Nano Science center and Deep Space Exploration Laboratory from automatic lineage admission. |
| NUS | Include the NUS primary institution; hold NUS Health System, Duke-NUS Medical School and NUS High School out of automatic appointment inference until their relationship is decided. |
| CUHK | Include Hong Kong CUHK; exclude CUHK Shenzhen from Hong Kong appointment inference. |
| PKU | Include PKU and university-owned computing centers; exclude its affiliated high school and the HKUST Shenzhen Research Institute. Do not sweep hospitals as automatic PKU appointments. |
| WHU | Exclude Duke Kunshan from automatic WHU appointment inference; treat Zhongnan and Renmin hospitals as related only, requiring explicit WHU raw affiliation. |
| UESTC | Include UESTC and its electronic thin-film laboratory; exclude Zhongshan Institute and Chengdu College from automatic UESTC appointment inference. |
| SEU | Include SEU; exclude independent Chengxian College; do not infer SEU appointments solely from affiliated hospitals or the shared Suzhou center. |
| UT Austin | Include the university's listed lineage children; require individual faculty appointment evidence for actual PI admissions. No related-only expansion. |
| Purdue | Limit the school to West Lafayette; exclude Indianapolis, Global, System, Northwest, Fort Wayne and IUPUI from automatic West Lafayette appointments. |
| HIT | Include Harbin, Shenzhen and Weihai campuses under HIT, because the local institution snapshot does not distinguish the latter two. Require campus-specific appointment evidence later. |

## Source and host review

NUS CS and DISA use official `comp.nus.edu.sg` people pages. NUS ECE uses the official `cde.nus.edu.sg` staff directory via Wayback because the live project-client probe challenged. CUHK CSE uses its official department faculty page; IE and EE use the Faculty of Engineering's official faculty directory. UESTC's university faculty directory is challenge protected and marked Wayback only. The other seven charters' moved, challenged, disallowed and archived faculty hosts are recorded in their `[[hosts]]` entries. Every host audit reported zero inconsistent decisions.

The new NUS, CUHK and UESTC charters have only initial faculty-source scope. Stage 1 historical capture work and Stage 2 cross-unit coverage must still test that scope; this report does not certify a completed faculty census. `status = "onboarding"` remains appropriate.
