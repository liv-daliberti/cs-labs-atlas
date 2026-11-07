# University cohort (owner decision 2026-11-07)

The atlas's university universe is the ShanghaiRanking Global Ranking of Academic Subjects 2025, Computer Science & Engineering,
ranks 1-300 (https://www.shanghairanking.com/rankings/gras/2025/AS0210). It replaced the ARWU 2025 top 300 (the QS idea of the
same day was dropped). Only ranks and bands are recorded; never indicator scores.

| file | what |
|---|---|
| `gras-2025-cse-roster.tsv` | the roster the site reads (copy of the site's `deployment/cohort/gras-2025-cse-top300.tsv`): 300 in the cohort, 107 kept but outside it |
| `gras-2025-cse-openalex-map.tsv` | each cohort row to its OpenAlex institution id: method, confidence, notes, related (predecessor) ids |
| `gras-2025-cse-vs-arwu-2025.tsv` | kept / added / dropped against ARWU 2025, with shown labs and lab-paper links of the dropped |

Rules: nothing outside the cohort is deleted (inventories, evidence, labs and paper links stay); it is only not shown.
Additions are phased by rank (A: ranks through the 151-200 band, B: 201-300) and linked from the local OpenAlex snapshot,
filtered by the PIs found, not the API. `tests/test_cohort_roster.py` ties the roster to the school charters.
