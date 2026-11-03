# University of Chicago, stage 2: faculty census

Date: 2026-11-03. Gate (`atlas stage-gate uchicago 2`): **pass** (347 candidates, every one decided; sweep check pass).

## Mechanical steps
- Snapshot extension merge (job 32079156) completed; stage 0 gate passes (412,159 works of I40347166 in `ext-uchicago.sqlite`).
- `atlas pipeline onboard-data SCHOOLS=uchicago --from-worktree`: DBLP affiliation pass 32084717 (5 min), sweep from the snapshot extension 32084718 (33 min,
  164,395 works), sweep check 32084719 (pass, 2016-2026 complete), candidates 32084720 (crashed on a missing pis.json: PROTOCOL-FRICTION 22; rerun alone as 32085355, 31 s).
- `cs_related_school.py candidates`: 347 (56 affiliated-department people, 144 DBLP-affiliation, 147 OpenAlex rule). `units` (DSI, BOOTH, MATH, CDAC) re-run after
  the Mathematics host move (friction 25). `review`: **36 accepted** (23 additions to the census), 22 faculty_not_computing, 21 too_few_school_works,
  267 not_faculty_listed, 1 census alias. The computing-share test ran inside `review` (oa-author-stats.json.gz present).
- Census: 270 people, 88 PIs (CS + TTIC ladder faculty) + 23 computing-related additions from Booth, Statistics, Mathematics, DSI and others.

## Reading the result
- `not_faculty_listed` is mostly Argonne staff (D3: the lineage stays whole; non-PI Argonne staff never become PIs) and people of other universities whose DBLP
  record names Chicago (Kalai, Ahmed, Dahua Lin). Four names appear in a searched unit page without a faculty title only before the Mathematics URL was added.
- Accepted additions include Booth (Birge, Chintagunta, Dube, Budish, ...), Statistics (Gao, Ma, Liang, Wu), Medical Imaging (Giger), applied mathematics and
  computational science (Anitescu, Weare, Khoo, Hoskins), Mathematics (Hirschfeldt, Malliaris, Weinberger), 
  Imaging (Giger) and Computational Science (Anitescu, Weare, Khoo, Hoskins). Whether logic and topology count as "computing as object" rests on the DBLP and
  share tests; the owner may drop them in stage 3 review.
- Units not searched: Physics, Economics, Harris, Pritzker Molecular Engineering, Psychology, Linguistics. Their computing people appear only through the DBLP and
  OpenAlex rules; a person listed only there with a professor title elsewhere is `not_faculty_listed`. Candidate for an extra round if the owner wants it.
