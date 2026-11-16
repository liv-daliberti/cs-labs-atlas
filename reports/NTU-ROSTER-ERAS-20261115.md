# NTU historical faculty roster recovery, 2026-11-15

The official CCDS faculty-list URL era `/computing/our-people/faculty` was omitted by the previous discovery pass, which limited detailed checks to its first forty candidates. Its successful exact CDX response has captures in both halves of 2024 and 2025. Two complete, unpaged original pages have now been captured and imported into the private listing plan; the other two half-year bodies remain pending during the shared Wayback cooldown.

| Calendar year / half | Exact capture | Raw SHA-256 | Faculty cards |
| --- | --- | --- | --- |
| 2024 H1 | `https://web.archive.org/web/20240625225031id_/https://www.ntu.edu.sg/computing/our-people/faculty` | `fd63c088a84dd3a1591ccffd69eddfcca70ca2ed0ebae6ae1852b48a7299eb87` | 94 |
| 2025 H2 | `https://web.archive.org/web/20250715202539id_/https://www.ntu.edu.sg/computing/our-people/faculty` | `dc6e50272d891542c73971a65f85c53e4493b579e9c80f00941fb18b97eb4689` | 101 |

The source is a whole faculty directory, with one `.img-card--academic` entry per card and no pager. All 195 cards have a name and explicit appointment title. The import checked the original stored HTTP status, original raw-body SHA-256, capture timestamp, parser count, absence of paging, and that each extracted name/title has a source quote. It copied the actual captured rows into the listing database and created plan records only for those two real capture receipts; it fabricated no URLs, dates, captures, or uncaptured half-year results.

The directory citation now uses two card-specific verbatim excerpts (the name heading and appointment paragraph), joined with an explicit `[...]` omission marker. The listing writer validates each excerpt against the captured text. Rechecking all 503 generated rows found zero retained contact addresses and zero titles missing from their own citation; the two Li Yi cards quote their distinct appointment paragraphs.

The existing `ntu_img_cards` parser looked for appointments only in `.img-card__interests`. These originals put appointments in `.img-card__desc`; the parser now retains the appointment paragraphs without biography or contact text. The current 2026 charter slot also now names `ntu_img_cards` explicitly: automatic detection had selected `ntu_profile_cards` from unrelated page furniture and returned zero entries. The two existing 2026 originals yield 114 and 115 cards when read through the normal gzip-aware body decoder.

The 2025 directory contains **two distinct Li Yi cards**, one linking to `https://dr.ntu.edu.sg/entities/person/Li-Yi` (CCDS), the other to `https://dr.ntu.edu.sg/entities/person/yili` (SPMS and CCDS). These source links were not fetched. The two records must not be merged on the displayed name when the census is refreshed.

Private `listing_rows.py ntu` result: 503 listing rows, 144 distinct displayed names; Stage 1 open years fall from 9 to 7. The years still open are 2016–2020 and 2022–2023. A roster proves only its captured calendar year and does not establish an appointment interval. No census or student build has been promoted by this source-only step.

The owner separately approved finite historical faculty-list access at `www3.ntu.edu.sg`, treating its short robots HTML Request Error as no rules for the exact ten SCE/SCSE staff-list paths in `docs/host-rulings.json`. Other paths remain closed. Historical main-list collection is job **32310881**, scheduled after the existing shared archive cooldown, with normal pacing and stop-on-refusal/challenge.

Private evidence root: `code/hierarchy/ntu/tmp/rosters-1115/`. Receipts are `modern-discovery.json` and `imported-modern-sources.json`; source originals are in `hierarchy/ntu/raw/school-captures.sqlite`, imported plan/originals in `listings/ntu/raw/captures.sqlite`, and generated rows/coverage in `listings/ntu/derived/`. `import_modern_samples.py` records the repeatable offline import and validates every card. Main's listing/census/student data remain unchanged pending review and integration.


## Source-qualified faculty identity repair

`hierarchy/ntu/reviewed/census-name-aliases.json` preserves the existing CS/CCDS canonical key **Yi Li** and assigns the distinct mathematical-sciences person **Yi Li [SPMS]**. The 2021 CS card links `dr.ntu.edu.sg//cris/rp/rp00572`; the 2024 card, now displayed as Li Yi, links the same legacy profile after normalizing its repeated slash. The CS/CCDS continuation links `/entities/person/Li-Yi`, while the simultaneous separate SPMS/CCDS card links `/entities/person/yili` and has its own SPMS appointments and biography. No profile page was fetched.

The mapping is applied before census name grouping, validates original HTTP-200 captures, raw SHA-256 and the exact source-profile/name/title card, and introduces no unqualified Yi Li/Li Yi name alias. Original `name_listed` spellings and source quotes remain unchanged. A newly observed unreviewed profile for either ambiguous spelling stops the refresh. This is a faculty-source identity repair; it authorizes no bibliographic author ID, paper claim or appointment interval.

The lightweight private census check yields 143 people and 120 PIs. CS/CCDS Yi Li retains `ntu_fac_yi-li` with listing years 2021, 2024, 2025 and 2026; SPMS Yi Li is separate as `ntu_fac_yi-li-spms` with listing years 2025 and 2026. The source mapping does not infer SPMS faculty time from the biography's 2016 sentence. Main's census has not been replaced by this validation run.


Legacy SCE and SCSE faculty lists recovered on 2026-11-15

The successful exact main-faculty index queried 2016–2025. SCE has one 2016 capture; SCSE has 28 captures from 2016-04-19 through 2021-04-16, covering both halves of every 2016–2020 year. That successful exact index has no 2022 or 2023 record. Body requests for 2018 onward remain pending after the shared archive guard stopped on a 429; the index alone does not establish roster coverage.

Three complete, unpaged original HTTP200 faculty lists are saved in the private school raw store and historical-samples directory:

- SCE 2016-03-04 15:57:07: 99 rows; SHA256 `88381f55ea881aff1b5ebaeeda1030a2fed72c6eb99b680ea009c35e1c214644`.
- SCSE 2016-06-19 21:19:03: 98 rows; SHA256 `d092630cbbe784c8c35b286e793fb4c474bed4125f365c048008a2ec80f3efe9`.
- SCSE 2017-06-02 22:48:54: 104 rows; SHA256 `d2ca837ca2c60bdd97f5a00d1c7e481c2518ff656ba8076cee04aa830806cd4b`.

The `ntu_moss_faculty` parser reads a photo row's name and parenthesized rank, retaining literal abbreviations and parenthesized personal names. It emits only that heading as the source quote and a name-linked HTTP faculty URL as metadata; degrees, contact links and research-interest cells are omitted. Every parsed name/rank quote is a verbatim substring of its original. The charter classifies literal `Assoc Prof` and `Asst Prof` titles as ladder, while adjunct, visiting, lecturer and research designations keep their normal exclusions. No appointment intervals or identity links are inferred from list dates. The newly recovered historical cohort still needs the normal census identity review before any native rebuild.


The normal shared archive retry completed on 2026-11-15 after its cooldown. SCSE originals for 2018-06-02 (97 rows, SHA `15f38099ef1f7d55dbbd900606e0543111d07160ce878f3e7d9a86c0d7edc2d0`), 2019-07-19 (101 rows, SHA `5b244f02dbf760c3711736bc4711c1980f81d568b5589a825378959c5d3b7f57`) and 2020-06-23 (81 rows, SHA `0bfcc36fe78fcaa197c641fb6ebeabc9719edc7af770f4e76652005227a08907`) match their complete photo-row counts. All six legacy originals are unpaged and every parsed heading matches the original. Source-only promotion increased main listing rows to 1083 (580 legacy, 503 modern), with a whole SQLite and rows/coverage backup in `scratch/ntu-historical-rosters-promote-1115-second`. The recorded strict stage-1 gate now has two open years, 2022 and 2023, and no waivers.

A bounded all-MIME HTTP200 exact backing-endpoint prefix query for `/scse/research/faculty-directory/GetAcademicProfiles/`, 2022–2023, completed successfully with zero records. This establishes that query's result only. It does not establish that no complete faculty roster was published elsewhere.

Fresh reviewer `codex-sjtu-recall-1115` independently checked six narrow historical name continuities against the original DBLP person XML, original faculty captures, and frozen 180-PI native baseline. The six existing canonical names are Wentong Cai, Wee Keong NG, Sinno Jialin Pan, Alexei Sourin, Thambipillai Srikanthan and Lana Obraztsova. Exact source-row bindings retain original displayed spellings and headings, including observations with no profile link; every enumerated binding checks original HTTP200 status, raw SHA, parser format, literal name, profile pointer if any, and full parser-produced quote. A new capture or changed heading fails closed, and conflicting profile/source reviews are rejected. These source name decisions do not admit new bibliographic identifiers, ORCIDs, papers or appointment intervals. Three additional apparent name variants remain held; 21 historical candidates have no established match to the frozen native cohort and must not be silently dropped.


Root independently approved the exact two profile-less 2019/2020 `Li Yi (Asst Prof)` observations as the existing CS `Yi Li`, after reading and rehashing their own software-research cells and the original official ASE2023 scientist metadata (HTTP200, SHA `9405377f17c5cd78d1be287a0c82675331563b327571a63fd42cd6b932454157`). That original explicitly identifies an NTU SCSE assistant professor Yi Li, his owned NTU site, and the same four distinctive research topics: Software Engineering, Program Analysis, Automated Reasoning and Formal Methods. The independent review is restricted to those two captured rows. The math faculty member remains `Yi Li [SPMS]` with a separate canonical key and stable collection ID.

The final private census over all 1083 listing rows builds successfully with 207 people and 148 listing PIs. All 180 prior native PIs remain in the union with the 161 preserved reviewed additions. The six reviewed historical canonical names retain their native keys; no new author ID, ORCID, paper or appointment interval was added. Main census/native outputs remain the responsibility of the NTU pipeline worker. A namesake regression checks that a profile-less source row joins its reviewed identity while a same-name profiled faculty member stays separate.

Three additional bounded 2022–2023 all-MIME HTTP200 prefix queries completed: slashless `GetAcademicProfiles` has zero records; `faculty-directory` root has one record (the already inspected 2023 empty shell); `about-us/our-people/faculty` has zero records. Query strings were included by prefix matching. These exact query results leave the strict stage-1 gate open for 2022 and 2023; no completeness claim or waiver follows from archive absence.


Five further canonical groups passed root's fresh independent source review: historical Miao Chunyan, Kelly Ke Yi Ping, Adams Kong Wai Kin, Francis Lee Bu Sung and Chia Liang Tien Clement retain the existing native keys Miao Chun Yan, Kelly Ke Yiping, Wai Kin Adams Kong, Lee Bu Sung and Chia Liang Tien. The reviewer read and rehashed all 30 exact historical own rows and 15 current own cards, with original owned name aliases and non-contact academic context. Only those historical names change; the 25 enumerated modern observations already use the canonical names and retain them. All literal source spellings and quotes remain. No generic name matcher or global alias changed.

The resulting private listing census has 202 people and 143 PIs over the same 1083 source rows; all 180 prior native names remain represented in the union with preserved reviewed additions. The reduction removes five duplicate name groups, not historical faculty. No new author identifier, ORCID, paper or interval decision was made. In particular, diagnostic Adams PID235/7223 and Chia PID05/2952 are not admitted, and the existing Miao PID54/9809 ambiguity is not resolved by the name binding. Existing canonical-record bibliographic fields do not gain independent approval from this review.

Two further exact source groups preserve the existing Loy Chen Change and Joty Shafiq Rayhan identities across six changed-name rows and nine already canonical observations. Independent review verified all 15 original bodies and the already owned Joty homepage. These name bindings preserve literal source forms and make no identifier, work or appointment-period decision.

The finite Common Crawl lookup recorded 27 index attempts and no WARC range or roster candidate: 13 exact no-capture results, 13 attempted service/transport-pending pairs and 18 unqueried pairs. Its private result receipt is `COMMONCRAWL-FINITE-NTU-ROSTER-RESULT-20261115.json` (SHA256 `aa46c316d78e9ae0c013435a483962e223ffdc248e258a82e6380a427f30fde6`). These bounded results do not establish global archive absence; Stage 1 remains open for 2022 and 2023.

Independent review also approved three exact historical Mohamed Mostafa Sabry Aly rows under the existing Mohamed M. Sabry canonical name, with five already canonical modern observations retained. This is a contextual inference from EPFL doctorate and specific system-level design research, supported by the already owned record's literal Mohamed M. Sabry Aly alias. It does not assert a literal Mostafa expansion or visual photo match, and makes no identifier, work or appointment-period decision.
