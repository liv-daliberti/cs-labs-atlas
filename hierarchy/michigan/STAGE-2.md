# Michigan, stage 2: faculty census

Date: 2026-10-29, updated 2026-10-30. Gate: **passed (2026-10-30)**. See the update at the end: the sweep's 2022
anomaly, the OpenAlex candidates, the computing-share test, and 30 decisions.

## What was done
- **Census.** `tools/census_build.py michigan` built the census from the 5,804 listing rows of stage 1.
  - Rows were merged within the school when the family name matches and the given names are compatible: nicknames, 3+
    letter prefixes, initials, or a middle name used as the first name.
  - Rows were also merged when two name forms link the same personal homepage. This caught
    'H.V.'/'HV'/'Jag' Jagadish, 'Georgios'/'George' Tzimpragos, 'Noel'/'Chris' Giebink, 'Q. Vera'/'Qingzi' Liao and
    'Zhuoqing Morley'/'Z. Morley'/'Morley' Mao.
  - Output: `census/michigan-faculty.json`, `census/michigan-report.md`, `hierarchy/michigan/collection.json.gz` and
    `listings/michigan/listings.json` (3,233 person × department × year rows for the builder's R-PAP-01).
- **Parser check.**
  - Every listing capture's parsed entries equal its own entry count (`Division:` blocks, or `eecs_person_wrapper`
    divs).
  - One fix was needed: 2018–2019 entries without a homepage link (bare `<b>` name, e.g. Semyon Meerkov) had been
    dropped.
- **CS-related review.** `tools/cs_related_school.py candidates|units|review michigan` produced 568 candidates:
  - 103 ladder faculty of ECE, the department with `coverage = "affiliated"`;
  - 465 DBLP persons whose dump record names the University of Michigan, with 5 or more records in 2016–2026, who are
    not in the census.
- **Unit listings.** Captured yearly from Wayback for 8 units: UMSI, STATS, ROB, IOE, MATH, LING, BIOSTAT (SPH faculty
  index) and ME.
  - No archived faculty list was found for Computational Medicine and Bioinformatics (medschool.umich.edu) or Ross.
  - The faculty evidence must follow the name directly and is cut at the entry's own furniture. This prevents reading
    the next person's title.
- **Listed-not-in-census.** `tools/listed_not_in_census.py michigan` found 39 names.
  - All 39 were read by hand. None is a person: 20 are endowed-chair names printed above the holder's title, and 19
    are headings or menu items.
  - The decisions are in `hierarchy/michigan/missing-pi-review.json`.

## Counts
- **Census.** 454 persons; 214 PIs (195 `ladder_faculty`, 19 `courtesy_faculty`).
  - By department: CSE 158 PIs; ECE 80 PIs.
  - Not PI, by reason: lecturer 57, research 50, emeritus 30, courtesy without a home professor rank 29, adjunct 19,
    visiting 6, plus the CS-related decisions below.
- **Additions.** 37 accepted CS-related faculty of other units, in `census/michigan-additions.json`: UMSI 17, Robotics
  14, Mathematics 4, IOE 1, ME 1.
- **Decisions** (`hierarchy/michigan/cs-related-review.json`):

  | source | accepted | faculty_not_computing | pending_openalex | not_faculty_listed | research_or_other_rank | census_alias |
  |---|---|---|---|---|---|---|
  | ECE ladder faculty | 58 | 27 | **18** | – | – | – |
  | DBLP persons naming Michigan | 37 | – | – | 409 | 2 | 2 |

  15 DBLP records duplicated a name already decided.

## Gate
- **Chain-audit `coverage`:** 609 items; 78 pass, 531 decided, **0 open**.
  - It was run in-process with a wired copy of the builder. `tools/wire_charters.py` was applied to a copy in
    `hierarchy/michigan/tmp/wiretest`; the builder's own files were not edited.
- **Stricter check:** `tools/stage_gate.py michigan 2` counts `pending_openalex` as open, so this gate **fails with 18
  open items**.

## Exceptions with reasons
1. **18 ECE ladder faculty are `pending_openalex`.**
   - Their names have DBLP namesakes, and none of the records names Michigan, links the listed homepage, or is the
     unique exact-name record.
   - They are: Cynthia Finelli, L. Jay Guo, Mohammed N. Islam, Hun-Seok Kim, Pei-Cheng Ku, Somin Lee, Johanna Mathieu,
     Becky Peterson, Jasprit Singh, Zhengya Zhang, Zheshen Zhang, Jun Gao, Souvik Biswas, Minji Kim, Sushil Varma, Joyce Yan-Ran Wang, Matthew Willsey and Kevin
     Zhou.
   - The decision needs the OpenAlex sweep: the DBLP-indexed share of each person's Michigan works, as for Stanford EE.
   - A missing Michigan note in DBLP is not evidence that a person has no computing output. Deciding them negatively
     would have dropped obvious computing faculty.
2. **All acceptances are provisional on the computing-share test.**
   - The test (DBLP-indexed share of school works ≥ 20%, the Stanford EE rule) needs the sweep.
   - DBLP indexes many IEEE journals, so EM, photonics and MEMS faculty can pass a count of 5 or more DBLP records.
     Expect some to fail the share test: Kamal Sarabandi, Leung Tsang, Anthony England, Eric Michielssen, Khalil
     Najafi, Euisik Yoon, Zetian Mi, Anthony Grbic.
   - Mathematics acceptances need the same check: Alexander Barvinok, Jeffrey Lagarias, Asaf Cohen, Erhan Bayraktar.
3. **"Not faculty listed" is bounded by the units searched.** The searched units are UMSI, STATS, ROB, IOE, MATH, LING,
   BIOSTAT and ME. Faculty of unsearched units (Aerospace, Civil, BME, the Medical School) who publish in CS venues
   come in once the OpenAlex candidates rule (`tools/cs_related_candidates.py` on the Michigan sweep) is run.
4. **UMSI faculty whose DBLP record does not name Michigan** are not candidates yet. They come in through the same
   OpenAlex pass.

## To finish this stage (after the sweep completes)
```
PY=/n/fs/resemble/cs-atlas-env/py310/bin/python; export LD_LIBRARY_PATH=/n/fs/resemble/cs-atlas-env/py310/lib
$PY tools/cs_related_candidates.py michigan     # OpenAlex author stats rule -> hierarchy/michigan/cs-related-candidates.json
# then extend cs_related_school.py review with the OpenAlex share (cs_share >= 0.20) for (a) and the provisional acceptances
$PY tools/cs_related_school.py review michigan && $PY tools/census_build.py michigan && $PY tools/stage_gate.py michigan 2
```
- `cs_related_candidates.py` writes the same file that `cs_related_school.py candidates` writes. Merge them, keeping
  both sources, before review. This is debt: one candidates step should read both.
- It also rewrites the shared `hierarchy/cs-venues.json` from the five default schools' sweeps on every run (about 1M
  works). Run it only when no builder is running. This is debt too: the venue step should be split out and the per-school
  candidate pass made streaming-only.

## Update, 2026-10-29 21:40 UTC
- **Four fewer pending.** The stage-5 co-authorship round decided the DBLP records of Raj Nadakuditi, Vijay Subramanian,
  Robert Gregg and Jiasi Chen. Their records share 5 or more 2016–2026 records with already-decided Michigan PIs. All
  four are now accepted. 18 remain `pending_openalex`.
- **Provisional, pending the owner.** These parts of the census rest on defaults the owner has not confirmed:
  - The 19 `courtesy_faculty` PIs: the rule "a courtesy appointment counts".
  - Every acceptance: the computing-share test, which needs the sweep. The ambiguous ones are listed above.
  - Every Michigan Medicine authorship: the related-id rule. This matters from stage 7.
  - Every capture of a challenged umich.edu host: read only from existing Wayback captures; no live requests are made
    to challenged hosts.

## Update, 2026-10-30: sweep check, OpenAlex candidates, computing-share test. Gate passed

### The 2022 anomaly in the OpenAlex sweep
- **What it was.** The per-year sweep log showed 19–25k works a year, but 455,386 in 2022. A read-only query of
  `openalex-sweep.sqlite` found:
  - 455,386 distinct work ids, so there are no duplicate rows and no repeated pages;
  - 434,618 of them are OpenAlex type `dataset` from the source "ENCODE Datasets": DOI prefix 10.17989, title an ENCODE
    accession (`ENCSR159GAJ`), a single author "A Boyle" tagged University of Michigan, publication dates 22–25 March
    2022.
  - The filter page was correct, and so was the related id. OpenAlex holds these records with a Michigan authorship.
  - Without datasets and the other non-paper types, 2022 has about 21k works, like the other years.
- **Handling.** The sweep was not re-run and no row was deleted.
  - The builder already drops `dataset` (R-PAP-17, `pi_hierarchy.NOT_PAPERS`).
  - `tools/cs_related_candidates.py` did not. It now skips every `NOT_PAPERS` type, which removes 440,912 datasets and
    6,677 other non-papers over 2016–2026. Without that, a single author with 435k works would have distorted the
    authorship statistics.
- **Gate.** The new bulk-pull check (`tools/sweep_check.py michigan` -> `sweep-check.json`) flags 2022 as a year
  outlier: more than 3× the median of the other years.
  - It is excused only by the reviewed exception in the charter (`[sweep_check]`) with `verify = "papers_normal"`. The
    check re-verifies that the paper-only count of 2022 is not an outlier.
  - Duplicate rate by work id: 0. DOIs carried by 2+ works: 0.04%. Every work carries a charter institution.
- **Back-test on the released sweeps.** CMU, EPFL, MIT, Stanford and Princeton pass. Princeton passes after the MAD
  floor; its 2016 is a trend, not an outlier.
  - **Berkeley fails on 2026:** 49,645 works against a median of 14,610. 36,836 are DOE PNNL repository datasets (DOI
    prefix 10.25582), and the paper-only count is normal. The builder drops them, so the release is unaffected.
  - Berkeley's charter needs the same reviewed exception. It was not added here because Berkeley is released; the owner
    should confirm it.

### Gzip-encoded Wayback captures
- Wayback `id_` returns the archived bytes with their original Content-Encoding. 7 of the 61 listing captures and 65
  other captures (homepages, lab pages, unit lists) were stored gzip-encoded and read as near-empty pages.
- The CSE spring captures of 2023–2025, which stage 1 called "31 KB script-rendered shells", are such pages. They hold
  149–164 entries each.
- `listings/scripts/wb.body()` now decodes stored bytes. `school_web.repair_gzip` re-derived blocks and text; raw
  bytes and sha256 stay as served.
- CSE 2023 H1 and 2024 H1 were re-planned as usable. `listing_rows.py`: 6,106 rows, 28 more person-years, and no new
  or lost people.

### OpenAlex candidates and four more units
- `tools/cs_related_candidates.py --no-venues --stats --out cs-related-candidates-openalex.json michigan`:
  - 88,301 school authors and 366 candidates. 206 match no PI, and 145 of those are new to the review. The shared
    `cs-venues.json` was left alone.
  - Authorships tagged only with Michigan Medicine count when their raw string matches the charter regex (owner
    decision 1).
- The candidates came from units nobody had searched. Four units were captured yearly from Wayback: Aerospace, CLASP,
  BME and CEE (`/people/` pages), 124 captures.
- Searched units: AERO, BIOSTAT, BME, CEE, CLASP, IOE, LING, MATH, ME, ROB, STATS, UMSI.
- **Limitation:** the Aerospace `/people/` captures do not name Ilya Kolmanovsky. His decision is `not_faculty_listed`,
  bounded by the units searched.

### The computing-share test (owner decision 5)
- **Rule** (`tools/cs_related_school.py`, `share_test`):
  - **Identity.** The person's OpenAlex ids at the school are those carrying their ORCID, plus ids under their family
    name and first spelled-out given name. An id carrying another ORCID is set aside. So is an id whose works end more
    than a year before the person's first listing. With no ORCID and several among the ids, the busiest ORCID wins.
  - **Test.** Over those ids' school papers 2016–2026: computing when 5 or more are DBLP-indexed and they are 20% or
    more of the works (the candidate rule's thresholds). Not computing when it fails on 8 or more works.
  - **Fewer than 8 works.** The DBLP decision stands; with none, the person is `too_few_school_works`.
- **Scope.** The test decides:
  - the 18 pending people;
  - the 12 acceptances named in the charter's `[cs_related].share_test_settles` (owner decision 5);
  - the OpenAlex candidates;
  - anyone without 5 DBLP records.

  Any other DBLP-decided acceptance stands, and its share is recorded.
- **Flagged for the owner (13).** For these the DBLP decision stands although the test fails: Al Avestruz 0.13, Pallab
  Bhattacharya 0.00, Heath Hofmann 0.15, Zhongming Liu 0.12, Vladimir Dvorkin 0.19, Di Liang 0.16, Shubhanshu Shekhar
  0.11, Changxiao Cai 0.14, Carol C. Menassa 0.17, Charles P. Friedman 0.13, James M. Balter 0.04, Jionghua Jin 0.17,
  Jun Ni 0.10. Some are arXiv-heavy theorists, whose unpublished preprints count as works but not as DBLP-indexed.

| group | person | decision | DBLP-indexed / school works | share | DBLP records 2016–26 | OpenAlex ids |
|---|---|---|---|---|---|---|
| pending | Cynthia Finelli | faculty_not_computing | 18/118 | 0.153 | 0 | A5081616240 |
| pending | L. Jay Guo | faculty_not_computing | 5/166 | 0.03 | 0 | A5001814451,A5102376020 |
| pending | Mohammed N. Islam | faculty_not_computing | 0/20 | 0.0 | 0 | A5100445894 |
| pending | Hun-Seok Kim | accepted | 131/168 | 0.78 | 0 | A5012483480,A5014196508,A5014333100 |
| pending | Pei-Cheng Ku | faculty_not_computing | 0/8 | 0.0 | 0 | A5078328945 |
| pending | Somin Lee | faculty_not_computing | 3/33 | 0.091 | 0 | A5059263512 |
| pending | Johanna Mathieu | accepted | 43/120 | 0.358 | 0 | A5015257057 |
| pending | Becky (R.L.) Peterson | faculty_not_computing | 1/43 | 0.023 | 0 | A5023311624 |
| pending | Jasprit Singh | too_few_school_works | 0/0 | 0.0 | 0 | – |
| pending | Zhengya Zhang | accepted | 71/92 | 0.772 | 0 | A5038110244 |
| pending | Zheshen Zhang | faculty_not_computing | 2/46 | 0.043 | 0 | A5075643115 |
| pending | Jun Gao | too_few_school_works | 0/4 | 0.0 | 0 | A5020139593 |
| pending | Souvik Biswas | too_few_school_works | 0/0 | 0.0 | 0 | – |
| pending | Minji Kim | faculty_not_computing | 2/15 | 0.133 | 0 | A5100317754 |
| pending | Sushil Varma | accepted | 5/7 | 0.714 | 0 | A5018172757 |
| pending | Joyce Yan-Ran Wang | too_few_school_works | 0/0 | 0.0 | 0 | – |
| pending | Matthew Willsey | faculty_not_computing | 4/29 | 0.138 | 0 | A5012994307 |
| pending | Kevin Zhou | too_few_school_works | 0/4 | 0.0 | 0 | A5006749171 |
| ambiguous | Kamal Sarabandi | accepted | 95/301 | 0.316 | 97 | A5049740845,A5151304753 |
| ambiguous | Leung Tsang | accepted | 79/193 | 0.409 | 82 | A5090757725 |
| ambiguous | Anthony W England | accepted | 2/3 | 0.667 | 11 | A5032858518 |
| ambiguous | Eric Michielssen | faculty_not_computing | 6/46 | 0.13 | 12 | A5023427875 |
| ambiguous | Khalil Najafi | faculty_not_computing | 8/44 | 0.182 | 9 | A5111969403 |
| ambiguous | Euisik Yoon | faculty_not_computing | 16/98 | 0.163 | 17 | A5061744193,A5104111210 |
| ambiguous | Zetian Mi | faculty_not_computing | 7/373 | 0.019 | 36 | A5070775523 |
| ambiguous | Anthony Grbic | faculty_not_computing | 6/200 | 0.03 | 8 | A5070337576 |
| ambiguous | Alexander I. Barvinok | faculty_not_computing | 6/31 | 0.194 | 21 | A5082996804 |
| ambiguous | Jeffrey C. Lagarias | faculty_not_computing | 4/24 | 0.167 | 8 | A5005612207 |
| ambiguous | Asaf Cohen | accepted | 10/25 | 0.4 | 18 | A5014923299,A5128764611 |
| ambiguous | Erhan Bayraktar | accepted | 56/196 | 0.286 | 74 | A5005237318 |

- **The 18 pending:** 4 accepted, 9 `faculty_not_computing`, 5 `too_few_school_works`.
  - The five are recent hires with fewer than 8 school works (Jun Gao, Souvik Biswas, Joyce Yan-Ran Wang, Kevin Zhou)
    and an emeritus with none in the window (Jasprit Singh).
  - Jun Gao's one name-matched id is a gastroenterology namesake (4 works); it decides nothing.
- **The 12 ambiguous:** 5 kept (Sarabandi, Tsang, Cohen, Bayraktar by the test; England by DBLP, with 3 school works)
  and 7 rejected (Michielssen, Najafi, Yoon, Mi, Grbic, Barvinok, Lagarias).
- **Counts:** 713 candidates and 698 decisions.
  - By decision: 132 accepted, 43 faculty_not_computing, 5 too_few_school_works, 510 not_faculty_listed, 5
    research_or_other_rank, 3 census_alias; 15 duplicate DBLP records.
  - Additions: 75 (UMSI 34 homes, Robotics 25, Mathematics 10, IOE 8, ME 5, Aerospace 4, ...).
  - The census has 213 PIs; the total is 288.
- A bug fixed on the way: the "Professor of X" pattern ran on into a second appointment ("... School of Information and
  Research Associate Professor, ICPSR"), so Libby Hemphill read as research rank. The rank is now read up to the
  title's own "Professor".

### Gate
`tools/stage_gate.py michigan 2`: **pass**, 0 open, and the sweep check passes for the OpenAlex sweep.
- The DBLP part of the sweep check needs the dump-persons file regenerated after the build. It is re-run with stage 7.
