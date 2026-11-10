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
| Rows with typed period / 2026 listing | 1669 / 113 | 4850 / 183 |
| Residual flagged rows (not held: sibling editions, 11 non-paper types) | 1 | 21 |
| Candidate student links | 207 | 436 |

Stage-9 style draw (`accuracy/sample.py` method, 90 of 105 rows: no thesis-adviser relations exist for the student-coverage part), hand judgement on stored evidence, no primary-PDF check: lab precision 35 of 35; student precision 38 of 40 (0.95, 4 doubtful, 35 undated); lab coverage 13 of 15 (0.867). Gates: lab precision pass; student precision (0.97) and coverage (0.90) NOT met. Student links stay candidates (`verified` 0); 161 earlier and 388 of 436 links have no start date in their source.
Copies: nothing measured; stored records point to an open PDF URL for 1969 of 4620 works (upper bound; nothing fetched).
