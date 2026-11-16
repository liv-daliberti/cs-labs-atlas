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
