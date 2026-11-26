# Northeastern stage 2 (faculty census): audit rework, 2026-11-26 (claude-agentE-census-1126)

Audit draw (seed 0c3fe46fd481, population 598) failed 5 of 50 (Ramezani, Offenhuber, Forlano, Leeser, Ciuccarelli). Causes: (1) an alias bug (hand evidence keyed by 'Miriam E. Leeser' not found for
'Miriam Leeser'; fixed in cs_related_school.py 29290c49), (2) the COE hand-evidence batch targets omitted Ramezani, (3) CAMD (and BOUVE, DMSB, LAW, COS) profile directories had never been searched.
Class rework: job 32559801 (`ne-unitsweep`, scratch/northeastern-unitsweep-1125/unitsweep.json) matched all 536 no_source_covers_window rows against archived profile slugs of coe/camd/bouve/damore-mckim/law/cos:
35 ladder (hand entries written by the job), 32 captured_no_ladder_title, 469 no_slug. The 32 were read by hand: Offenhuber (Chair, Professor), Forlano (Professor), Whitney (Associate Professor),
Dorsey (Associate Professor), Ghoreishi (Assistant Professor) and Tunik (Professor, Bouve) got hand entries from the stored capture; the rest are postdocs, research/teaching ranks or emeriti, or
pages whose capture shows no title (Noor-E-Alam, Dehghanimohammadabadi, Jin Kim, Herrero) and stay excluded_unresolved.
Review re-run: accepted 94 (was 52: +40 from excluded, +2 from too_few_school_works), faculty_not_computing 6, excluded_unresolved 557 (495 no_source_covers_window, 62 identity_collision).
All five failed rows are accepted (recorded `fixed` in `excluded-unresolved-audit.draw1-20261125.json`). Census rebuilt: 614 persons, 175 PIs (155 ladder_faculty, 18 courtesy, 2 own_group).
Stage 3 now lists the new PIs without a home decision (not part of this change). Draw 2: seed d7a034464aa7 (fresh random), population 557, sample 50, unreviewed; the reviewer must not be the worker.
