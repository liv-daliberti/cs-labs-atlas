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
`papers.not_a_paper` and `non_research_record` (R-PAP-19 congress, R-PAP-33 Zenodo deliverable) applied to all 2,449 rows: 0 drops (HKUST has no Neuromodulation/ERS DOIs and no deliverable-coded Zenodo records). Three Zenodo DOIs were read by hand: Yuan "Revision Provably Reduces Sequential Computation in Diffusion Language Models" (preprint, stays), Narechania "From Interaction to Intent" (arXiv-venue preprint with a Zenodo DOI, stays), Wang "OSDI21 Artifact for SANRAZOR" (an artifact deposit, a software record, not a paper). Held for the owner, never silently dropped: that artifact row and three editorial or front-matter rows the rules let through (two "Message from ..." editorials, "Epilogue"). They are excluded from the admissible count below.

## 6. Identity bindings added (stage 5)
Fifteen PIs gained a DBLP person from the 2026-09-01 dump (record sha256 and the HKUST affiliation note or the PI's own cse.ust.hk homepage URL as the quote; same-name records recorded). See `census-overrides-school.json`, `dblp_identity_review`. Bo Li (homepage ~bli), Yike Guo (portal biography: Imperial College professor since 2002, HKUST provost 2022-12; DBLP g/YikeGuo, unique name) are the two the owner named. Bo Li's research-portal ORCID (0000-0003-2955-750X, an empty public record under "Li Bo") differs from the ORCID DBLP lists for him (0000-0003-2083-9105); both are kept as recorded and neither is relied on.
