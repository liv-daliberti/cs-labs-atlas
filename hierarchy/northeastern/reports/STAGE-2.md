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

## Rework after the second draw (2026-11-26, claude-agentE-census-1126)
Draw 2 (seed d7a034464aa7) failed 2 of 50. Yang Lee: the review row is named "Yang Lee"; the unit sweep dropped the single-letter token of "Yang W. Lee", so slug yang-w-lee never matched. D'Amore-McKim captures 2019 and 2025 print "Associate Professor, Supply Chain and Information Management": accepted (share test 6 of 12 school works DBLP-indexed, 0.50).
Dana H. Brooks: the sweep had found him; the official COE profile prints "Research Professor, Electrical and Computer Engineering" in the 2019 and 2024 captures and "Professor Emeritus" in 2026, so no official dated source gives a ladder rank in the window. Decision: research_or_other_rank (D-0009), source-bound. The reviewer's evidence (tmslab.org, third party, undated: ECE professor since 1991) is not a dated official source.
Owner question: if the owner accepts the lab page or an NU faculty record showing him as tenured ECE professor before he became Emeritus, admit him for those years; recommendation: keep research_or_other_rank until a dated official listing is found.
Class rework: (a) live probe of coe.northeastern.edu/people/<surname>-<given>/ for all 469 no-slug rows: 0 pages; (b) looser slug re-match against the stored CDX slug lists: 3 hits: Yang Lee (accepted), Pedro Cruz (CAMD live page: Associate professor of art, accepted by the share test), Purnima Ratilal (page has no title; stays excluded). accepted 94 -> 96, research_or_other_rank 1, excluded_unresolved 554 (492 + 62 identity_collision).
Both failed rows are `fixed` in excluded-unresolved-audit.draw2-20261126.json. Draw 3: seed 8ea5521ab613 (fresh random), population 554, n=50, unreviewed.
