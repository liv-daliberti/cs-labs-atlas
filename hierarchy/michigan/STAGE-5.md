# Michigan, stage 5: identity

Date: 2026-10-29. Gate: **not passed. 19 PIs have no anchor yet**, and the OpenAlex author review waits on the sweep.

## What was done
- `tools/dblp_ids_school.py michigan` searched the DBLP dump (dblp-2026-09-01; dblp.org is never fetched) in two
  passes.
  - Pass 1 finds the person records whose names carry each PI's (given, family) pair.
  - Pass 2 counts each candidate's 2016–2026 records.
  - It covered 296 people: the PIs, the additions and the ECE ladder faculty under CS-related review.
- **Decisions, in order:**

| basis | rule | census PIs (211) |
|---|---|---|
| `homepage_url` | the DBLP record links the homepage the department listing links | 65 |
| `school_affiliation` | exactly one candidate's affiliation note (or URL) names the University of Michigan | 60 |
| `unique_exact_name` | exactly one candidate carries the full name, has no homonym number, and no candidate has more records | 34 |
| `unique_name` | the only candidate of the name (R-PAP-05) | 33 |
| none | several namesakes, none decided | 19 |

The 37 additions carry the DBLP record that named Michigan in their candidate pass.

- **Evidence.** Each id carries the person page URL, the dump file name, the sha256 of the person record's XML as it
  stands in the dump, and the quote (the affiliation note, the `<url>` or the name). `census_build.py` folds the pid and
  the record's ORCIDs into the census.
- **Anchors** (`tools/stage_gate.py michigan 5`): DBLP and ORCID 127, DBLP only 102, none 19.

## What the rules learned on the way (folded into the protocol)
- **The affiliation note alone leaves many PIs without an id.** With the note and the strict unique-name rule, the
  first run left 45 of 164 PIs without one.
  - Many DBLP records of Michigan faculty carry no note at all.
  - The homepage the department listing links is the best anchor. It decided 65 PIs.
  - An exact full-name match with no homonym number settles more of them: Danai Koutra, Eric Gilbert and Lingjia Tang
    were decided by `unique_exact_name`.
- **A unique record must not be rejected because its notes name another institution.** Faculty who moved away keep
  only their new institution in DBLP: Pascal Van Hentenryck now names Georgia Tech.
- **An exact-name record must not win over a busier namesake record.** "Vijay Subramanian" (3 records) is not
  "Vijay G. Subramanian". The guard sends the case back to review.

## Open (19)
Marios Papaefthymiou, Long Nguyen, Zeeshan H. Syed, Joshua Welch, Jie Liu, Vineet Kamat, Wei Hu, Lin Ma, Stella Yu,
Jiasi Chen, Krisztián Flautner, Todd Hollon, Jeong Joon Park, Gokul Ravi, Alexander Rodríguez, Ke Wu, Hao-Wen (Herman)
Dong, Q. Vera Liao, Majdi Radaideh.
- These are common names with several DBLP records, none of which names Michigan or links the listed homepage.
- Each needs the OpenAlex author review: the author id that holds the PI's Michigan works, recorded as
  `reviewedOpenAlex` in `census-overrides.json` with evidence. Alternatively, an ORCID from the PI's own page.

## Not done yet
- **OpenAlex author ids for all PIs.** The sweep starts after the 00:00 UTC credit reset (`sweep_daily.sh`).
- **`tools/dblp_dump_persons.py`.** It now includes onboarding schools, but rewrites the shared
  `hierarchy/dblp-dump-persons.json.gz`, which the builder reads. Run it after the builder agent's release.
- **Name aliases for the builder** in `census-overrides.json` (shared, reviewed): for example "Satinder Singh Baveja" is
  DBLP's "Satinder Singh", and "Chad Jenkins" is "Odest Chadwicke Jenkins". Write them after the builder agent's
  release.
