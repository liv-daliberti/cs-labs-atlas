# Owned publication lists, 2026-11-09 (T115)

Source class: titles listed verbatim on the PI-named official SJTU profile or on the owned homepage that the official profile links (website status `verified_website`). Offline scan of the cached page bytes against the 303,961 stored works (`scratch/sjtu-ownedlists-1109/scan_lists.py`, job 32177405): a work is a candidate only if its normalized title (28+ characters) occurs verbatim in the page text and the page states the work's year (or one year either side) within 220 characters. Every record in `reviewed/pi-publication-lists.json` carries url, page sha256, observed time and a verbatim quote.

This file is a separate input from the DBLP-derived person records. It is read by the native as the `pi_institutional_publication_list` identity route: a work also needs a byline name matching the PI alias, the exact listed title within one year, and the ordinary school, appointment and type gates.

PIs without an owned DBLP record are un-held only when the byline alias is evidenced: the alias is the byline name present in at least 60 percent of the PI's listed works and consistent with the profile URL slug (王士林 added by hand: two spellings, 17 of 17 works). 84 PIs were un-held this way, 20 PIs with DBLP bindings also gain a list, 104 lists and 2445 records in total. Faculty periods are unchanged: a PI without a dated period contributes only works dated to the 2026 listing year.

Also held: 沈为 "Image Stitching" (book chapter), from the corrected 27-PID package.

## Final native (job 32177967, runtime 4ca6712 only, input commit b829ca9 before rebase)

Sealed, guards pass, 0 verified links. 2347 hold decisions (each with stored-record evidence; the rule that flagged each row is in `flag_rule`). OpenAlex-author-id anchoring expands every un-held PI's list to the whole author profile, so rows credited that way are held unless the byline shares a coauthor with 3 or more co-publications among the PI's DBLP- or page-evidenced works.

| Measure | 27-PID DBLP-only package | Final package |
| --- | ---: | ---: |
| PIs with papers | 25 | 107 |
| Rows / distinct works | 1782 / 1741 | 5033 / 4620 |
| Rows with typed period / 2026 listing | 1669 / 113 | 4837 / 196 |
| Residual flagged rows (not held: sibling editions, 11 non-paper types) | 1 | 21 |
| Candidate student links | 207 | 436 |

Stage-9 style draw (`accuracy/sample.py` method, 90 of 105 rows: no thesis-adviser relations exist for the student-coverage part), hand judgement on stored evidence, no primary-PDF check: lab precision 35 of 35; student precision 38 of 40 (0.95, 4 doubtful, 35 undated); lab coverage 13 of 15 (0.867). Gates: lab precision pass; student precision (0.97) and coverage (0.90) NOT met. Student links stay candidates (`verified` 0); 388 of 436 links have no start date in their source.
Copies: nothing measured; stored records point to an open PDF URL for 1969 of 4620 works (upper bound; nothing fetched).

## Final native 32177967 (runtime 4ca6712, input commit b829ca9) and review

Sealed: 5033 rows, 4620 distinct works, 107 PIs with papers, 0 guard violations, 0 verified links, 436 candidate student links, registry untouched (c5df145c; isolated ID rehearsal not rerun on this package).

| Stratum | Rows (distinct) | Basis |
| --- | ---: | --- |
| Source-backed: DBLP person record or page-quoted owned list | 2728 | stored records or verbatim quotes with page sha256 |
| Heuristic: OpenAlex author-id anchor corroborated by 3+ co-publications with the PI's evidenced coauthors | 2051 | my overlap rule, NOT source evidence |
| Residual flagged rows (now added as 21 holds for the next native) | 21 | 11 uncorroborated, 10 book/chapter |

Only the source-backed stratum counts toward the 2500 target and any admission claim; the heuristic stratum is a candidate set until independently validated.

Hand judgement with evidence cards (seed 20261112; `scratch/sjtu-ownedlists-1109/stage9-final/cards.json`): 45 source-backed rows and 60 heuristic rows, judged on raw byline name, SJTU affiliation text, appointment, type, venue and coauthor consistency with the PI's evidenced works. 45/45 and 60/60 plausible, no primary-source PDF page-1 check, no copy check; the judge's topic knowledge is part of the evidence, so this is a plausibility judgement, not proof.

Student links: 436; 14 fail the automatic name or date test (9 name mismatches, 5 starts after the paper year), 388 are undated and cannot be checked: 422/436 = 96.8%, below the 97% gate. The 14 are listed in `scratch/sjtu-ownedlists-1109/PROPOSED-STUDENT-LINK-EXCLUSIONS.json`; the gate is not claimed.

Copies: stored-record open-copy pointers 1969 PDF URL, 259 landing page, 2392 none of 4620 (an upper bound; no copy fetched or verified).

Listing plan: SJTU has no plan or capture rows (only the 2026 directory); the Chinese-listing fix has nothing to re-plan here, and historical SJTU listings were never fetched.

## Distinct-work counts and the formal checks (2026-11-10)

Counted in distinct works (normalized title, which equals distinct OpenAlex ids here), after the proposed holds: source-backed 2832 (DBLP person record 1523 + 132 rows, page-quoted owned list 1303 rows); heuristic anchored rows 2054 rows / 1930 works, of which 1767 works are not already source-backed; 4597 distinct works in all. The 2500 target is met by source-backed works alone (2832), but admission is not claimed: other gates below are unmet.

Heuristic stratum, primary-source check of the 60 sampled rows (seed 20261112): 0 contradictions. Crossref (51) and arXiv API (9) show the PI name on the author list and the same title; publisher metadata names Shanghai Jiao Tong for 33; arXiv PDF page 1 shows name and SJTU for 12 more (title text on page 1 matched for 11 of them; MotionBank's name tokens did not match by text extraction while SJTU did, so treat that one as affiliation-only). 15 rows (IEEE, Springer, Elsevier, AAAI Press versions) have neither publisher affiliation nor an arXiv version; publisher pages are paywalled and were not fetched. Point precision 60/60, Wilson 95% lower bound 94.0%, below the 0.95 bar, so the stratum stays candidate (`stage9-final/crossref-check.json`, `arxiv-check.json`, `page1-check.json`).

Student precision, hand sample of 45 of the 422 links remaining after the 14 exclusions (seed 20261113), judged against the roster quote naming the person as advisee or member: 45/45 real relations, Wilson lower bound 92.1%, below the 97% gate; 388 links are undated and stay candidates, not dated by inference (`stage9-final/student-sample.json`).

Lab coverage (exhaustive over the DBLP-bound PIs): 1380 of 1699 DBLP article or inproceedings records dated inside the PI's period are in the package = 81.2%, below the 0.90 gate (sample of 15: 12 found).

Copies, sampled (no store written; PDFs deleted after hashing): of 100 random source-backed works, 37 downloaded a PDF whose first two pages carry the title, 5 a PDF with another title, 7 were disallowed by robots.txt, 3 errored, 48 had no stored PDF URL. About 37% obtainable by the stored links, against the 85% target (not a gate). A full overlay ledger was not built.

Formal stage 9 composition: lab precision 105 hand judgements (45 source-backed + 60 heuristic) with the checks above, student precision 45, coverage 15 sampled plus exhaustive; not a single formal run of `accuracy/sample.py`.

## Lab-coverage diagnosis and the pi-works build (2026-11-10)

Coverage was recounted by DOI as well as title: the earlier 81.2% undercounted DBLP records whose OpenAlex title is a short form of the DBLP title; the DOI-aware figure for the final 28-PID package is 1415 of 1699 (83.3%). Adding the PI's own OpenAlex works from the API (`pi_fulltext_affiliation.py works sjtu`: 17,716 works, 278 author ids; and `pdf sjtu`: page 1 of the arXiv version ties SJTU for 156 of 457 candidates) and rebuilding (job 32179160, runtime 4ca6712, input commit dc3a63d) raised it to 1452 of 1699 (85.5%). Package: 5519 rows, 5038 distinct works, 109 PIs; after the proposed holds 4913 distinct works, of which 2833 source-backed and 2243 heuristic (2080 heuristic only).

The seal refused (not sealed): one claim-held work (郁昱, a COVID epidemiology paper) re-entered through the pi-works route, which the runtime does not exclude by claim review. The package is complete; that row and 150 newly flagged rows are listed in `scratch/sjtu-coverage-1110/cc29.json` as holds for any further run.

| The 247 uncounted DBLP records (period-covered, 2016-2026) | Count | Fixable by the rules? |
| --- | ---: | --- |
| Not in any stored OpenAlex store by title or DOI | 131 | No input of ours; OpenAlex does not carry the work or carries a different title without DOI |
| PI authorship present but the byline name does not match the PI alias | 44 | Maybe: extra aliases per PI, each needing source evidence |
| PI authorship names another institution | 25 | No: correctly not an SJTU paper (likely not true lab papers) |
| Authorship names SJTU, work still absent | 33 | Period or identity gating; needs per-work review |
| Authorship lists no institution | 14 | Page-1 tie when an arXiv version exists |

Coverage stays below the 0.90 gate by the exhaustive count (the gate's own measure judges true lab papers by hand, which would drop the 25 other-institution records and any pre-move work).

## Mixed-id check (Tsinghua criterion) and heuristic re-sample (2026-11-10)

Criterion re-implemented over the SJTU packages: an anchored OpenAlex author id that carries no source-backed (DBLP record or page-quoted list) work of its PI is a namesake id (R-PAP-06). For SJTU anchors are created from source-backed hits, so the criterion bites little: 4 ids (28-PID package) and 6 ids (pi-works package, 沈备军 2 ids, 沈为, 周煊赫, 邢朝平, 曹健, 傅洛伊) with 7 dependent rows; they are marked `mixed_openalex` in `census-overrides-school.json` and the 7 rows are held. The real risk is merged profiles that also carry genuine works; the per-work coauthor rule (3 or more co-publications) already holds those (150 rows in the pi-works package). In total 153 further hold decisions (2521) are ingested, each bound to the stored work blob (sweep year archive or the PI works cache).

Heuristic stratum redrawn on the post-fix pi-works package (seed 20261117, 80 rows with DOIs from 2366): 80 of 80 confirmed against Crossref (61) or the arXiv API (19), PI name on the author list and matching title, 0 contradictions; Wilson 95% lower bound 95.4%. This is name-and-title metadata, not page-1 proof; affiliation is not re-checked for all rows.

Counts in distinct works, pi-works package, after the holds: source-backed 2833, heuristic 2243 (2080 not source-backed), all kept 4913 before the 153 new holds. The v3 rebuild that would apply the holds and mixed ids was not run (52 minutes, seal refused once for the pi-works route); the machine-readable split is `hierarchy/sjtu/reviewed/source-backed-split.json`.
