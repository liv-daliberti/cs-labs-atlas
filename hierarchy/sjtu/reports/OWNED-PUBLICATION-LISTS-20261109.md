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

## Student-link sample on the sealed native 32181138 package (2026-11-10)

792 candidate links (742 undated). Fresh stratified sample, seed 20261118: 108 links (dated or undated x PI with 40 or more links or fewer, 27 each; the 19 automatically failing links excluded), judged by three independent subagent reviewers who did not build the rows, on whether the roster quote names the person as the PI's student, advisee or member and the byline and paper fit that lab (dates not judged). Result: 91 correct, 17 doubtful, 0 incorrect; with doubtful as half an error the point precision is 92.1%, below the 97% bar, so the student gate is NOT met. The doubtful links concentrate in rosters that give only a name and a topic with no student label (Yang Yang's group, 12 of 17) and in alumni or other-institution entries. Evidence: `scratch/sjtu-coverage-1110/student-sample-32-verdicts.json`.

### Round 2 after holding unlabelled roster links (seed 20261119)

71 links whose roster quote is a bare name next to a topic, with no student label, are proposed holds (`scratch/sjtu-coverage-1110/PROPOSED-STUDENT-LINK-HOLDS-UNLABELLED.json`; 33 under 杨旸, 30 under 吴晨涛, 5 under 冯宇, 3 under 张倬胜); with the 19 automatic failures the eligible population is 702 links. Fresh sample of 108 (27 per stratum), three new independent reviewers: 103 correct, 5 doubtful, 0 incorrect. Point precision with doubtful as half an error: 97.7% (Wilson 95% lower bound 93.0%). This meets the project's point-estimate bar (0.97) on the eligible links only if the 71 unlabelled and 19 failing links are excluded from the package; no package rebuild was run, so the 792-link package still contains them. Evidence: `student-sample-33-verdicts.json`. Exact next step: add the 90 links to the student-link exclusion input (or hold the 71 rows in the roster file) and rebuild in the next native.

## Final sealed package, native 32183331 (input commit c64f4d0, 2026-11-10)

Sealed (198 PIs, 87 identity-held, 2521 decisions, 0 violations, 0 advisee hits), 42 owned DBLP persons (15 name-checked R-PAP-44 bindings added; five of their OpenAlex ids marked mixed). Rows 5571, distinct works 5080; after the proposed holds 5453 rows and 4962 distinct works, of which source-backed 3326 and heuristic 1842 (1636 not source-backed); 106 PIs with papers. Lab coverage against the DBLP pool of the 42 owned persons: 2325 of 2876 = 80.8%, below the 0.90 gate (the pool grew with the new bindings). Student links 804; post-seal filter removes 19 automatic name/date failures and 74 unlabelled name-plus-topic links, leaving 711 (`scratch/sjtu-coverage-1110/student-filter-33.json`). Student precision: the round-2 sample (108) plus 9 links new to this package judged by a fresh reviewer: 110 correct, 7 doubtful, 0 incorrect, 97.0% with doubtful as half an error (113.5/117), at the 0.97 point bar. This holds only for the filtered 711 links; the package files themselves still contain the 93 filtered links.

<<<<<<< HEAD
## Stage 1: the listing slots exist (CDX evidence, 2026-11-10)

CDX probes (one low-priority Wayback job, 32186895 and 32187003; `scratch/sjtu-coverage-1110/cdx-evidence*.json`) show archived faculty listings for every year, so the open stage 1 items are not gaps: `www.cs.sjtu.edu.cn/Faculty.aspx` (2016-2024, with `/en/Faculty.aspx` every year), `cs.sjtu.edu.cn/cse/Faculty.aspx` (2025) and the script-rendered `active/ajax_teacher_list.html` (2025-2026). `listings/scripts/config_sjtu.py` records the slots. Not yet run: `WAYBACK_LOW=1 listings/scripts/run_school.sh sjtu` behind the Wayback chain, the charter host `web.archive.org` changed from `none` to `wayback-only` (owner decision), a Chinese-list format for `listing_rows.py`, and then `listing_pi_years.py`.
=======
## Coverage diagnosis on the sealed 42-person package and the holds released (2026-11-10)

DBLP pool: 2876 records of the 42 owned persons, dated 2016-2026 inside the PI's period; found in the package 2325 (80.8%). The 551 misses by cause (DOI and title lookup in the stored OpenAlex works and the PI works cache): 258 no OpenAlex work by DOI or title; 156 an OpenAlex work exists but the affiliation, identity or period gate dropped it; 111 held by my coauthor-overlap rule although the work is on the PI's own DBLP person record; 20 other holds (7 advisee-route, 6 earlier byline-repair, 3 book/chapter, 3 non-SJTU affiliation, 1 mixed); 6 non-paper types. The 111 are released: the DBLP person record is per-work evidence, so the overlap rule should not hold them (116 decisions removed from `paper-claim-review.json`; the removed decisions stay in git history and in `scratch/sjtu-coverage-1110/claim-holds-released-20261110.json`). Expected coverage after the next native: about 2436 of 2876 = 84.7%, still below 0.90; the remainder is mostly works OpenAlex does not carry or gates that must stay.
>>>>>>> 54d439f (SJTU: release 116 holds on works that are on the PI's own DBLP person record)

## Native 32186593 (input commit d3cf8cf, runtime 0b9fc0c): the package carries the exclusions

Sealed (198 PIs, 87 identity-held, 2405 decisions, 0 violations). Rows 5678; student links 713, with the 93 reviewed exclusions applied by the engine (`student_links_excluded` 93, 0 unmatched; the automatic name/date failures are gone from the package). The 116 released holds raised lab coverage to 2436 of 2876 = 84.7%. The 97.0% student precision (110 correct, 7 doubtful of 117) was measured on the same filtered links and now applies to the package itself.
