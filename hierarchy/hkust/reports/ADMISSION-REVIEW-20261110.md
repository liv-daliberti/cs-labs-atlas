# HKUST expanded trial: scientific admission review (T110, 2026-11-10)

Scope: the isolated round-2 native (job 32173556, 2,449 PI-paper rows, 2,411 title-distinct works) and the second native with 15 new source-bound DBLP identities. Nothing here changes the saved site candidate (782 works), the IDs registry or a release. Every external check below keeps its URL, original-body SHA-256 and a literal quote; the raw bytes sit in `scratch/hkust-expanded-admission-1109/evidence/`.

## 1. Two false Lei school flags: resolved (the works stay; the derived flag is wrong)
Both works carry `school_via: advisee at the school on the byline` with a wrong advisee (Jiachuan Wang is at Tsukuba; Caleb Chen Cao is not Lei's HKUST student). The works are Lei Chen's own on printed first-page evidence, so the admission rests on that evidence and not on the advisee flag.

| Work | Evidence | SHA-256 | Quote |
|---|---|---|---|
| arXiv 2602.11114v1, W7128700990 | arxiv.org/pdf/2602.11114v1 p.1 | a3f2f8921e7624280f6b303ed244839f8561c812c005b9c227b48eddda35e8d5 | "Lei Chen12" with "leichen@cse.ust.hk" and "1 Hong Kong University of Science and Technology, Hong Kong SAR, China" |
| arXiv 2604.14805v1, W7154702160 | arxiv.org/pdf/2604.14805v1 p.1 | 3a2b60c245e6716dfce2e2208c06ce1e6032df9d36c5eacfffd5f0cd0e2802ec | "Lei Chen∗,b,c" (b HKUST Guangzhou, c "The Hong Kong University of Science and Technology") and "leichen@cse.ust.hk (Lei Chen)" |
| Lei Chen's own page | cse.hkust.edu.hk/~leichen/ (captured 2026-11-07) | bcb1817b598b33898358116f2964ba42aca98bdb0fe549eea07099e068f078bd | "Email: leichen@cse.ust.hk" |

The mailbox printed on both papers is the one on his own page, so the byline is this PI (exact-work identity), not a namesake. The flag itself is a builder artifact (advisee route) that a rebuild still emits; it is not an admission reason.

## 2. Two unresolved Chung author claims: resolved
Both are Bioengineering (MDPI) 2024 papers by Han Zhang and Albert C. S. Chung. Europe PMC's publisher-fed records give the department-level HKUST affiliation for both authors, and the publisher XML carries Chung's authenticated ORCID, which is the ORCID on his DBLP person (pid/45/6335) that the census already holds.

| DOI | Europe PMC | SHA-256 (body) | Quote |
|---|---|---|---|
| 10.3390/bioengineering11010101 | PMC11326508 fullTextXML | de6d5e73b241cb6bbd3e40451fe8e5debb3ff7da57c61ae7a9f587c567ad1269 | affiliation "Department of Computer Science and Engineering, The Hong Kong University of Science and Technology, Clear Water Bay, Hong Kong." (search record sha 5b9b25b8e0aa...) |
| 10.3390/bioengineering11100998 | PMC11503988 fullTextXML | 3b34c20fbc76dbf1d396685dced591099001d5eab93e2ac3616e2a37f7ea4e71 | `orcid authenticated="true">https://orcid.org/0000-0003-4400-9261` on the author `Chung, Albert C. S.`; same department affiliation |

The 2024 years fall in his second HKUST phase (August 2023 on, `hkust_chung_professor_return_2023_08`). Type and date are the publisher's (article, 2024-01-22 and 2024-10).

## 3. Song Guo: 207 new relations and the 2023 boundary
All 207 are ORCID-anchored (0000-0001-9831-2202, from his own CSE page) with `hkust_faculty_period_reviewed_hkust_fac_song-guo` (CV: "Full Professor, Department of Computer Science and Engineering 2023-present", sha 03d7464d...). Independent Crossref check (every DOI with Crossref affiliations, 155 of 155): the author block names Hong Kong University of Science and Technology. 29 are arXiv preprints, 21 Crossref records list no affiliations (byline affiliation then rests on OpenAlex), 2 have no DOI. Types: 125 articles, 51 conference papers, 29 preprints, 1 book chapter, 1 data paper (CRA5, Scientific Data), no title duplicates inside his rows or in the package.

2023 boundary: 15 rows. All 15 bylines print HKUST (CSE) in OpenAlex and Crossref; 13 are online-first Sept-Dec 2023 (Crossref issue year 2024), VeriDKG is Dec 2023, and "Federated Meta-Learning for Few-Shot Fault Diagnosis" (IEEE TIM) has only a year (OpenAlex 2023-01-01 is a placeholder). The CV gives the start at year precision, so the build's inclusive start-year rule admits them and the byline affiliation is the independent evidence. Residual: the CV does not say which month in 2023; the one year-only work could pre-date the move. It is flagged, not removed (owner decision 2).

## 4. Source-title guard (R-PAP-41) on the round-2 package
`tools/source_title_guard.py lab_papers.jsonl.gz bulk_arxiv.json bulk_crossref.json`: 375 arXiv ids (DataCite titles, because export.arxiv.org's robots.txt disallows all) and 2,000 non-arXiv DOIs (Crossref; 8 returned 404, not judged). Result: 2 holds, both the same work (arXiv 2606.01143, Binhang Yuan and Kai Chen). Cleared as a genuine retitling: arxiv.org/abs/2606.01143v1 (sha 426f745e4efe435db261301876717aec5f184643d4a588f247e261d0fc0a89c2) carries the record's title "Schedule-Level Shared-Prefix Reuse for LLM RL Training"; the current version (sha dbcb0b9ee20f456ee122ecc126254bd7bb116ea7d7de2b19b7d0a01d11cb17a0) is "PrefixFlow: Training-Time KV Caching for Schedule-Level Prefix Reuse in LLM RL Training". Corrupted titles: 0.

## 5. Congress-abstract and Zenodo rules
`papers.not_a_paper` and `non_research_record` (R-PAP-19 congress, R-PAP-33 Zenodo deliverable) applied to all 2,449 rows: 0 drops (HKUST has no Neuromodulation/ERS DOIs and no deliverable-coded Zenodo records). Three Zenodo DOIs were read by hand: Yuan "Revision Provably Reduces Sequential Computation in Diffusion Language Models" (preprint, stays), Narechania "From Interaction to Intent" (arXiv-venue preprint with a Zenodo DOI, stays), Wang "OSDI21 Artifact for SANRAZOR" (an artifact deposit, a software record, not a paper). Those four rows (the artifact deposit, two "Message from ..." editorials, "Epilogue") were held and are now dropped by R-PAP-43 (code commit 2394a3a); the later natives exclude them.

## 6. Identity bindings added (stage 5) and what the current code does with them
Twenty-two PIs gained a DBLP person from the 2026-09-01 dump (record sha256 and the HKUST affiliation note or the PI's own cse.ust.hk homepage URL as the quote; same-name records recorded in `dblp_identity_review`): Tang, Lin, N. Zhang, Ding, Horner, Ng, Chan, Bo Li, Luo, X. Zhou, D. Xu, Jia, Quan, Sander (alias 'Pedro V. Sander'), Yike Guo, Wei Wang (homepage ~weiwa, uname 王威), Shuai Wang, Ma, L'Yi, C. Li, M. Zhou, Parreaux, Yinghao Xu (career match, not the bare-name record). Bo Li's research-portal ORCID (0000-0003-2955-750X, an empty public record) differs from the ORCID DBLP lists for him (0000-0003-2083-9105); both are kept as recorded and neither is relied on. Yike Guo: portal biography (Imperial College professor since 2002, HKUST provost 2022-12) plus unique-name DBLP g/YikeGuo.

Main's current code (commit 1803966, "source-stated advising for PI paper anchors") no longer admits the advisee-route identities the round-2 trial used (round 2: 416 `advisee_anchored_author_id` + 355 `advisee_coauthor` relations). Rebuilt on current code with the bindings above, the PIs that relied on them (Lei Chen 386, Wei Wang 138, Shuai Wang 158, Ma 33, Papadopoulos 5) recover through their own DBLP persons (Lei and Papadopoulos from the reviewed dump extract, the rest newly bound).

## 7. Isolated natives (overlay roots, never main's derived package)
| run | job | relations | distinct works | PIs with papers | zero-paper PIs |
|---|---|---|---|---|---|
| round 2 (old code) | 32173556 | 2,449 | 2,411 | 37 | 16 |
| a1: 15 binds, partial persons file | 32176605 | 2,564 | 2,537 | 41 | 12 |
| a3: 21 binds, current code | 32177098 | 2,932 | 2,843 | 48 | 5 |
| a6: 24 binds, Zihan rejects, no-paper reasons | 32177396 | 2,935 | 2,849 | 49 | 4 |

The target of 2,500 distinct works is met on admissible rows (2,849 on current rules; no padding: every added row is a bound-identity, HKUST-bylined, in-appointment work). The four PIs still without papers have reasons in `lab-coverage-reasons.json`: Jin (works are MPhil-era), L'Yi (2026 hire), Horner and Ng (works exist but no sourced appointment years; 1,780+ HKUST-credited relations across about 30 PIs are withheld as `outside_appointment` for the same reason).

## 8. Fresh accuracy draw (seed 20261029 on the a6 package; accuracy/sample-hkust.json)
Lab precision, 35 rows (25 uniform and 5 each of listing and identity-not-reviewed): the first draw (a5) held one error, three security papers attached to Zihan Zhang by DBLP pid 178/8599 (a bare-name record of 375 mixed-person records). Evidence: the papers are Dongdong She's students' work (his page lists Zesen Liu, Yuchong Xie, Kaikai Zhang and 'Zihan Zhang (2027-Fall PhD)'), while the faculty member's profile lists reinforcement learning and game theory. Three exact `reject` reviews were added; after the rebuild the redraw is 35 of 35 correct. Independent affiliation checks: Crossref author-level affiliation names HKUST for 18 rows; 6 arXiv rows were read on the PDF first page (HKUST affiliation or an ust.hk address); 9 rows have no Crossref affiliation and stand on the bound identity plus the byline affiliation in OpenAlex. Titles agree with Crossref/DataCite for all 35. Point estimate 1.00 (35/35), Wilson 95% lower bound about 0.90; the standing bar of 0.95 is not statistically established by 35 rows.
Not done: student-link precision (40 rows drawn, not judged), lab coverage (15 drawn; 9 are in the build, 6 are not and need hand judgment: Yike Guo ReChoreoNet, Kai Chen FLB and TII, Long Quan Neurocomputing, Shuai Wang remote sensing, Parreaux DARTS artifact), student coverage (no candidates). The summary file is not written, so stage 9 stays open.

## 9. Gates on the isolated a6 package (`atlas stage-gate hkust N`, rc 1 = fail)
| stage | result | open items |
|---|---|---|
| 1 | fail | 11 historical listing years never planned |
| 2 | fail | cs-related candidates and sweep-check files missing |
| 3 | fail | 60 PIs without an accepted home department |
| 4 | fail | one non-ISO start ('2024 (fall)' for Ouyang) |
| 5 | fail (2 open; was 42) | Horner, Ng: anchors yield 0 papers (appointment years unsourced) |
| 6 | fail | lab-page student acceptance missing; 30 labs without students or reasons |
| 7 | fail (2 open; was 3) | lab-page paper acceptance missing; 79 of 255 links unexplained; papers check passes |
| 8 | fail | no ledger, no lab-page capture store; 8 of 2,849 papers local (0.3%); the store catalog is empty, so copies were never collected |
| 9 | fail | summary missing (student precision and coverage unjudged) |

Everything above 2 is a collection stage this review did not run (historical Wayback listings, home departments, lab-page rounds, full-text collection, ledger); stages 1-4 and 6 were already open before it.

## 10. Final package with archived listing years (native b1, job 32177445; re-check against b2)
Added after the first sections: the CSE directory's archived captures (2016-2024) now prove listing years for the 53 current PIs (`tools/listing_pi_years.py`; 18 of 22 half-years ok, 2022 and 2025 have no archived capture and stay unbridged, `listing_continuity = false`). b1: 4,186 PI-paper rows, 4,048 distinct works, 51 of 53 labs with papers (Jin and L'Yi have recorded reasons), 1,617 rows admitted by a dated listing, 2,327 by a reviewed period. Song Guo is unchanged by it (207 rows, 15 in 2023, all period-admitted). Title guard on b1 (1,647 further DOIs): 4 holds on 3 works. arXiv 2606.01143 (Yuan, Chen) and 2606.24033 (Jia, v1 title 'RoPE-Aware Bit Allocation for KV-Cache Quantization', sha 7fd3c444...) are retitlings, cleared. arXiv 2403.07257 (Lei Chen) is a 39-author EDA paper whose first author is credited to Huawei Noah's Ark Lab; arXiv v1 (sha 0f7faa456d85f13f9c39c7a3e5a6190903b2f520245cd59fc86a74a5463dcd78) is 'The Dawn of AI-Native EDA', not the record's title: rejected for this exact work (paper-claim-review.json). Crossref/DataCite sample of 105 rows on each of two packages: 0 title mismatches, 0 contradicting affiliations. The final counts are re-stated from native b2 (job 32177945) once it has run.

## 11. Reference package: native b2 (job 32177945, commit b3c3910)
b2 is the reference, not a6 (2,849 works) or b1: 4,185 PI-paper rows, 4,047 distinct works, 53 PIs, 51 with papers (Jin and L'Yi have recorded reasons). It differs from b1 only by the rejected Lei Chen EDA paper. Source-title guard on b2: 3 holds, all cleared retitles. Scoped-ID preparation on b2 against registry c5df145c (read-only, job 32178208): registry sha256 unchanged, 53 PI ids, 53 lab ids, 255 members (252 ids), 4,047 work ids, 646 student links, 3,289 new ids, 0 changed or removed issued ids, nothing without an id. Gates on the b2 overlay (exit codes): stage 5 rc 0; stages 7, 8, 9 rc 1 (lab-page acceptance and 70 unexplained links; copies and lab-page captures missing; accuracy summary missing). Since then: stage 3 homes 53 of 53 accepted (Computer Science and Engineering); stage 4 Ouyang's start stored at year precision; stage 1 plain CSE directory URL era added to the charter for 2022 and 2025 (captures exist there) and re-planned; stage 0 hosts.json and stage 2 candidates (none) written in the private overlay.

## 12. Native b3 and a retracted namesake call
b3 (job 32183164, commit 15ec4ce, overlay5; scratch package, not sealed): 4,403 rows, 4,256 distinct works, 53 PIs, 2 zero-paper (Jin, L'Yi), 655 students in 33 labs, 3,067 student-paper links; 6 lab-page students wired, 1 lab-page paper set aside (Ke Yi 2021, source type unproven). The Lei Chen EDA paper is gone. Source-title guard on b3: the same 3 cleared retitles. Retraction: the `mixed_openalex` entry for Wei Wang's A5076987000 was withdrawn. That authorship (arXiv 2609.10346, HKUST) carries ORCID 0000-0002-4585-4152, which is one of the ORCIDs on his DBLP person 35/7092-30, so the row has per-work evidence and b3 keeps it (identity pi_orcid). The tools/mixed_openalex_check.py criterion flagged the id because the sweep holds only that one work under it.
