# Harvard supported partial package — 2026-11-07

Owner decision: “lets add what we have / release what we have for washington university, harvard, and JHU (and then keep working on improving them)?” This report describes the supported onboarding package; publication and release status belong to the coordinator.

## Scope and evidence

The complete current CS faculty filter was captured from three official SEAS directory pages on 2026-11-06: 58 faculty entries, including 38 supported PIs (37 ladder faculty and one Harvard Business School faculty member explicitly affiliated with CS). Teaching and emeritus entries without an own-group basis are retained in the faculty census but do not become PIs. The current observation supports 2026 only; it does not establish an appointment start.

Five reviewed appointment periods have explicit dated evidence: David Brooks (2002), Madhu Sudan (2015), Jonathan Zittrain (2010), David Alvarez-Melis (2023), and Kianté Brantley (2024-07-01). Other PIs retain their 2026 listing evidence without an inferred historical interval. The reviewed home corrections place Stephen Casper at the Kennedy School and Jonathan Zittrain at Harvard Law School; Hima Lakkaraju's HBS home and CS affiliate role remain explicit.

Eleven lab rosters supply 58 manually reviewed student relations (50 explicit PhD entries and eight generic student entries). They support the observation year only. Current lab membership is not treated as a joining date. Michelle Si and Yiyu Liu each appear in two supported lab rosters; their shared person identifiers preserve both relations.

The local OpenAlex snapshot sweep contains 598,232 works across 2016–2026. Its sanity check passes, with zero duplicate work identifiers, duplicate DOI rate 0.000752, and institution share 1.0. A sweep is a candidate pool, not a claim that every work belongs to a supported CS lab.

Raw official captures are saved in `hierarchy/harvard/raw/school-captures.sqlite`; admitted evidence preserves source URLs, SHA-256 hashes, and verbatim quotations. Access receipts cover 70 faculty-linked and publication-source hosts. Blocked robots/challenge responses were respected. No archive request or external API budget was used for this partial build.

## Remaining historical work

CS department-year listing coverage for 2016–2025 remains open. The finite stage-1 completeness exception records those exact ten findings and the owner's decision. An older saved nonexact Wayback URL lacks a resolved archive timestamp, and the RESEARCH 2023–24 report has an academic-year label; neither establishes a calendar-year listing.

Historical discovery, broader CS-related faculty discovery, complete lab roster and publication-page coverage, and local full-text collection remain work in progress. Unknown years, unchecked sources and missing copies must remain visible. Evidence, schema, identity and attribution failures are not completeness exceptions.

## Build and review

The supported package contains 38 PIs, 56 unique students in 58 lab-student pairs, and 112 student-paper links. The initial 493 lab-paper rows represented 467 distinct papers. The first manual accuracy review checked 35 lab-paper claims, 40 student-paper claims and 15 independent DBLP coverage records: all precision claims were correct, while only 12/15 coverage records were present (0.800). The complete initial draw, judgments and summary are preserved in `accuracy/*-harvard-initial-20261107.*`.

That review found two recoverable affiliation/metadata misses. A 2017 ICALP publisher PDF explicitly ties Madhu Sudan's name marker to Harvard, contradicting the snapshot's Microsoft affiliation. A 2026 TMLR record for Stephanie Gil is tied to a Harvard first page through the primary TMLR accepted-paper listing and the official REACT lab's citation of its earlier-title author preprint. The accepted OpenReview PDF returned 403 and was not retried; the independently author-linked arXiv PDF allowed this use, with its 15-second crawl delay and shared host reservation respected. Both PDF byte hashes and the version-linking sources are preserved under immutable raw filenames.

These are curated source records for the existing generic DBLP first-page recovery rule, not hardcoded builder exceptions. `bin/atlas run tools/paper_recoveries.py harvard` verifies every saved source hash and materializes `reviewed/paper-recovery-review.json` into the generic `dblp-recovered.jsonl.gz` input before a build. It has been run for both the branch overlay and the canonical data root. The recovered package has 495 lab-paper rows representing 469 distinct papers. Procaccia's sampled journal article remains a known date/scope gap: DBLP's formal year is 2026, while the snapshot online publication date is 2025 and this partial package currently has only his 2026 directory observation.

The student audit found zero duplicate records within labs, across-lab identity conflicts, duplicate links on one paper, or detectable missed byline matches. Fifteen current student records have no linked paper; fourteen of those remain unexplained coverage gaps. Current roster observation alone is never used as a joining date or a reason to close such a gap.

Snapshot job 32137357 and metadata job 32137992 completed. Initial offline quality job 32138100 checked 17 schema-covered files with zero violations. Every claim-level evidence category passed; its ledger had zero missing/stale entries, 304 found-not-in-catalog records and 163 incomplete checks among 467 nonlocal papers. Recovery quality job 32138462 completed its build and offline checks after the two recoveries. The final package has 17 schema-covered files with zero violations and zero claim-level evidence, missing-ledger or stale-ledger failures.

The finite gate exceptions cover only the exact remaining listing, broader-discovery, roster/link and separate lab-page copy-channel completeness findings. All open findings remain visible. Stage 9 accuracy is not waived. Publication and final canonical-build/ID revalidation are coordinator actions.

## Final measured accuracy and copy completeness

| Measure | Initial panel | Original fixed panel and fresh draw |
|---|---:|---:|
| Uniform lab-paper precision | 25/25 | 25/25 |
| All lab-paper precision strata | 35/35 | 35/35 |
| Uniform student-link precision | 25/25 | 25/25 |
| All student-link precision strata | 40/40 | 40/40 |
| DBLP lab-paper coverage | 12/15 (0.800) | 14/15 (0.9333) |

The fresh same-seed draw selected the same 90 stable keys. Every one of the 75 original precision row hashes was rechecked and remained identical. The two genuine coverage failures changed only after their independent sources were admitted; the Procaccia failure remains in the final judgments. The initial, fixed-panel and current draw/summary/verdict files are saved separately under `accuracy/`. The current five package hashes match the final draw and summary. There are no documented thesis/alumni candidates in this supported current-roster subset, so thesis-advisee student coverage is unmeasured rather than zero or complete. Stage 9 passes without an exception.

The final catalog measurement is **0/469 local copies**. Two PDFs retained as raw affiliation evidence are not yet catalogued reader copies. The offline ledger records **305 found-not-in-catalog** papers and **164 incomplete checks**, with **zero missing or stale ledger records**. Unknown checks remain incomplete; no unqueried source is labelled absent.

| Source | Incomplete records missing this check |
|---|---:|
| OpenAlex | 160 |
| Semantic Scholar | 157 |
| DBLP | 164 |
| Institutional repository | 160 |
| Lab pages | 164 |
| CORE | 152 |
| ACM Wayback PDF discovery | 28 |

The source counts overlap. Exact combinations are 124 missing OpenAlex/Semantic Scholar/DBLP/repository/lab pages/CORE; 28 with those plus ACM Wayback; four missing OpenAlex/Semantic Scholar/DBLP/repository/lab pages; four missing OpenAlex/DBLP/repository/lab pages; three missing DBLP/lab pages; and one missing Semantic Scholar/DBLP/lab pages. The coordinator owns the finite school/category copy-completeness whitelist entry; no attribution, identity, missing-ledger or stale-ledger exception was added here.

Final branch gates 0, 4, 5 and 9 pass. Gates 1, 2, 3, 6, 7 and 8 have only their exact owner-authorized completeness findings waived, with all remaining items visible and no unmatched findings. The recovery build's actual provenance is preserved: snapshot commit `8b21f2e`, `dirty: false`, with the then-uncommitted gate exception listed under `other_dirty_paths`. The original recovery provenance remains intact; the subsequent canonical build and ID/copy binding are recorded below. Neither provenance flags nor scientific judgments were manually cleared.

Slurm terminal status is preserved separately from the later manual gate results: snapshot job 32137357 completed with exit 0 in 33:45, and metadata job 32137992 completed with exit 0 in 32:24. Quality jobs 32138100 and 32138462 exited 1 at their final stage-gate command after producing their build/check/ledger/draw artifacts; their pinned snapshots did not contain the subsequently completed current manual accuracy summary. After all 90 judgments were complete, a fresh branch gate evaluation found that every stage 0–9 passed or had only exact scoped completeness exceptions. No Slurm state or provenance field was rewritten.

## Canonical ID and copy binding, 2026-11-07

Canonical build job 32138560 completed with exit 0 in 2:52, pinned to clean main `c2364694f0fa91ba9222e8c3fe815ae1cd55d4c3`. All five package files were byte-identical to the accepted reviewed package before ID annotation. Its provenance records `dirty: false`, empty `dirty_paths` and empty `other_dirty_paths`.

The coordinator then completed global IDs, copies and offline ledgers in job 32138566. Read-only comparison against its preserved pre-ID Harvard files verified all existing scientific fields of 38 PIs, 58 student-lab records, 495 lab-paper rows and 112 student-paper links unchanged. Only the registered Atlas ID annotations were added, and all 112 link-to-person/lab/work references were checked. All 469 copy records remained identical; only `counted_at` and `ledger_built_at` changed. The four immutable recovery source files still match their reviewed hashes. The ledger remains 164 incomplete checks and 305 found-not-in-catalog records.

The standard sample and summarize commands were rerun against the stable canonical package. All 90 sample keys, strata and population fields remained identical, all 75 precision claim hashes still match the accepted scientific records, and every verdict file plus the initial and fixed-panel history files remained byte-identical. Only the current draw/summary package-hash bindings changed. Final uniform precision remains 25/25 for both lab papers and student links; coverage remains 14/15. The full comparison is saved at project `scratch/harvard-final-binding-20261107.json`. The coordinator's overall audit/release decision remains pending at this binding step; no package rebuild or global ID rerun was performed here.

### Follow-up identity enrichment

The legacy membership identifiers represent **56 unique people**, while the conservative registry currently assigns **58 student Atlas IDs**. The two cross-lab joins below have cached independent evidence but remain pending reviewed identity enrichment; existing per-lab claims and all accuracy judgments are unchanged.

- **Michelle Si:** the [Procaccia roster](https://procaccia.info/people/) explicitly says “Co-advised with Finale Doshi-Velez” and links [this student profile](https://sites.google.com/g.harvard.edu/msi/). Its captured-body SHA-256 is `bcae4da5a44d3ddd3ea15b00a680faa2b33a70eebfbfafe9003ef10e2f244acb`. Both sampled lab links use the same Michelle Si byline on `W7204258650`; the cached OpenAlex authorship carries `A5109772690` and ORCID `0009-0007-7739-0691`. Those cached identifiers have not been newly adopted as reviewed registry anchors.
- **Yiyu Liu:** the [Juncheng roster](https://juncheng.seas.harvard.edu/students.html) explicitly says “co-advised with Minlan Yu” (SHA-256 `d9691a4cebe237ddc4f328fd3e401c4abc0031eb0541dc1b210eb840f2e0c5da`), while the [Minlan roster](http://minlanyu.seas.harvard.edu/student.html) says “co-advised with Juncheng Yang” (SHA-256 `887a7230d647dbb79edcb96fb8af754f5099dfaec6cafd169eca49a86e73e588`). Both exact student entries link [the same personal homepage](https://lau.yeeyu.org/).

No new collection, name-only merge, precision waiver or judgment change was used for this note.
