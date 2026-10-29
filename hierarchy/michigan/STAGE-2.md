# Michigan, stage 2: faculty census

Date: 2026-10-29. Gate: **not passed. 18 documented open items wait on the OpenAlex sweep**, which runs after the
00:00 UTC credit reset. Everything else is decided. These numbers are after the stage-5 DBLP ids were folded back in.

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
