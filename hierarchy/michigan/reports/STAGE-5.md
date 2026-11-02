# Michigan, stage 5: identity

Date: 2026-10-29, updated 2026-10-30. Gate: **passed** (see the update at the end).

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

## Update, 2026-10-29 21:40 UTC: identity review without the sweep
- **Co-authorship round.** `tools/dblp_ids_school.py` gained a second round, `school_coauthors`. Among several namesake
  DBLP records, it takes the one that shares 5 or more 2016–2026 records with Michigan PIs already decided, when no
  other candidate shares any.
  - The threshold is 5. At 3, borderline cases came in: Joshua Welch, whose only shared co-author was David Blaauw.
  - Decided this way (9): Raj Nadakuditi (13 records, with Fessler, Norris, Michielssen), Marios Papaefthymiou, Vijay
    Subramanian (12, with Teneketzis, Schoenebeck, M. Liu), Robert Gregg, Vineet Kamat, Jiasi Chen, Krisztián Flautner,
    Todd Hollon and Gokul Ravi.
- **Homepage links.** `tools/homepage_links_school.py michigan` reads the stored homepages for DBLP and ORCID links. It
  added Stella Yu and Ke Wu (`pi_homepage_link`) and 4 ORCIDs.
  - One conflict, recorded and not applied: J. Alex Halderman's homepage links `pid/79/7583`, while the dump decision
    is `pid/h/JAlexHalderman`.
- **Regenerated:** `tools/dblp_dump_persons.py` (3,694 persons, 269,857 records, Michigan included).
- **Census PIs (214) by basis:** homepage_url 65, school_affiliation 60, unique_exact_name 34, unique_name 33,
  school_coauthors 9, pi_homepage_link 2, none 11.
- **Gate:** **not passed, 11 open.** Long Nguyen, Zeeshan H. Syed, Joshua Welch, Jie Liu, Wei Hu, Lin Ma, Jeong Joon
  Park, Alexander Rodríguez, Hao-Wen (Herman) Dong, Q. Vera Liao and Majdi Radaideh need the OpenAlex author review.
  The sweep starts after 00:10 UTC.


## Update, 2026-10-30: OpenAlex identity review. Gate passed
- **The 11 open PIs were reviewed by hand** against `hierarchy/michigan/oa-author-stats.json.gz`, the per-author school
  works of the sweep with names, ORCIDs, venues and years. Decisions are in
  `hierarchy/michigan/openalex-identity-review.json`:
  - by ORCID: Zeeshan H. Syed, Joshua Welch (2 ids), Jie Liu, Lin Ma, Jeong Joon Park, Alexander Rodríguez, Hao-Wen
    (Herman) Dong (2), Q. Vera Liao (2), Majdi Radaideh;
  - by name with field and years: Wei Hu (NeurIPS 2023–2025);
  - Long Nguyen is XuanLong Nguyen. The listing links `~xuanlong`, and the id has 37 Statistics works; the alias was
    added.
  - Namesakes set aside: 'Jeong M. Park' (transplant pharmacology), 'Wei-Hsiu Hu' (concrete), a Singapore 'Lin Ma'
    (economics).
- **The 42 accepted people without a DBLP id** (OpenAlex-rule candidates and new ECE acceptances) take the ids of their
  share test. The identity rule is ORCID, or full name with namesakes set aside.
- **`tools/oa_identity_school.py michigan`** (new) writes `openalex`, `why_openalex` and `openalex_evidence` into
  Michigan's section of `hierarchy/census-overrides.json`. The evidence is one sweep work per id: url = the API url,
  sha256 = the stored record, quote = "<raw author name> | <raw affiliation string>". 53 PIs; no id lacked evidence.
- **Stella Yu** is reviewed as DBLP `58/5089`, "Stella X. Yu", ORCID 0000-0002-3507-5761. Berkeley's PI carries the
  same ids.
  - Her 2022 Michigan homepage links `pid/172/9071`, which is not a person in the 2026-09-01 dump, so it is not used.
  - This also lets stage 6 recognise her Berkeley advisees.
- **Gate** (`tools/stage_gate.py michigan 5`): **pass**. 288 PIs: DBLP+ORCID 130, DBLP 105, OpenAlex 53.
