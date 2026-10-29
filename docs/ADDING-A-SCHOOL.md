# Adding a school: the standard protocol

**Version 2, 2026-10-29.**
- Version 1 was drafted from how Princeton, CMU, EPFL, MIT, Berkeley and Stanford were built.
- Version 2 is version 1 corrected by its first run, on the University of Michigan, the seventh school (`hierarchy/michigan/STAGE-*.md`).
- Each change is marked **Learned from Michigan (2026-10-29)**.

Each stage has inputs, tools, outputs, a gate (what must be true before the next stage starts) and a stage report. A school is "in" only when every gate passes and it ships in a release.

The protocol is config-driven. A school is a charter, `schools/<key>.toml`, and the stage tools take the school key as their argument and read everything else from the charter. A new school needs a new charter, not a new script.
- If a page format is new, add a function to `tools/listing_formats.py`.
- If a rule is new, add it to the charter's schema in `schools/TEMPLATE.toml` and to the tool that applies it.
- The few files that still list schools by hand are named under "Files that must learn a new school" below.

## Scope (owner rules; see `docs/RULES.md`)
- **Unit of analysis.**
  - The hierarchy is school → department → PI lab → papers + students.
  - Centres, institutes and multi-PI groups are not labs. A collective can only contain labs.
- **Who counts.**
  - Computing-related faculty in any department: computing must be the object or the method of their research.
  - Administrative advisers are not PIs.
- **Window.** 2016–2026.
- **Evidence.**
  - Every fact carries `url + sha256 + verbatim quote`.
  - Appointment intervals are never inferred from roster years.
  - A dated department faculty listing proves an appointment for its own calendar year only, and not after an evidenced move-out.
- **Students.**
  - Students are named as the public sources name them, with advisor, role, years and source, and no contact details.
  - Name merges happen only within one lab.
- **Access.**
  - No paywalls, logins or bot challenges. Stop using a host as soon as it serves a challenge.
  - Respect robots.txt. **Learned from Michigan (2026-10-29):** this includes rules that disallow AI agents by name (ClaudeBot, anthropic-ai, Claude-Web). This project's fetchers are Claude agents, so such a host is not used, whatever User-Agent string the tools send, and not through its Wayback captures either. `tools/school_web.py` enforces this.
  - dblp.org is never fetched; use the local dump (`atlas_paths.DBLP_DUMP`).
  - API keys live in `~/.config/cs-atlas/*.env` and are never printed. The owner's email is never sent anywhere.
- **Compute.**
  - Follow `/etc/claude-code/CLAUDE.md`.
  - Slurm jobs carry mem, time and cpus. Run `sbatch --test-only` first, use `--exclude=node302`, and leave 60 s or more between polls.
  - Local runs use `nice`. One heavy builder runs at a time.
  - Temporary files go in `hierarchy/<key>/tmp/` (ignored by git), never in login `/tmp`.

## Stage 0: charter and config
- **Do:**
  - Copy `schools/TEMPLATE.toml` to `schools/<key>.toml` and fill it in. `TEMPLATE.toml` documents every field:
    - name, key, `status = "onboarding"`, `order`;
    - OpenAlex lineage ids, related ids, excluded ids, and the ROR id, with how each was verified;
    - web domains, excluded hosts and Wayback-only suffixes;
    - the affiliation regex, with `must_match` and `must_not_match` cases, and the loose pattern and own units;
    - the DBLP affiliation strings;
    - departments with `coverage`, `title_match` and listing slots;
    - affiliated units with their listing URLs;
    - the thesis repository;
    - the store path;
    - every host with its `use` (`live | wayback-only | none`) and a probe URL.
  - Create `hierarchy/<key>/` and the store: `<STORES>/<key>/` holds `catalog.sqlite` (the schema of the other stores' catalogs), `objects/` and `discovery/`. Link it as `<ROOT>/stores/<key>`.
  - Start the slow inputs now. Later stages need them, and they cost nothing to start:
    - `tools/oa_sweep.py <key>`: the OpenAlex institution sweep, for stages 2 and 7;
    - `tools/dblp_affiliated.py <key> --pubs`: dump persons whose affiliation note or URL names the school.
- **Tools:**
  - `tools/school_config.py --check <key>`: required fields, id formats, and the regex against its test cases;
  - `tools/school_hosts.py <key>`;
  - `tools/dblp_affiliated.py`.
- **Gate:**
  - `school_config.py --check` passes.
  - `school_hosts.py <key>` reports 0 inconsistent hosts:
    - every host was checked against its robots.txt;
    - every host marked `live` was probed and served no challenge;
    - every host that disallows AI agents by name is marked `none`.
  - The charter is reviewed and committed.
- **Learned from Michigan (2026-10-29):**
  - **The host gate needs a probe fetch.** robots.txt allowing a host proves nothing about a Cloudflare challenge in front of it. At Michigan, every umich.edu host but one challenged a plain request. The charter's `[web].wayback_only_suffixes` makes a whole domain Wayback-only, and `school_config.host_use()` applies it.
  - **The OpenAlex lineage may not contain the school's medical centre.** Michigan Medicine is "related" to the university, not a child. List such ids as `openalex_related`: they are swept, and an authorship tagged only with them counts when its raw string matches the regex. This needs the owner's agreement once per school.
  - **Test the affiliation regex against DBLP notes as well as OpenAlex strings.** "University of Michigan – Shanghai Jiao Tong University Joint Institute" and "University of Michigan at Dearborn" matched the first regex.
  - **Check the shared OpenAlex key's credits before starting the sweep.** It had 492 left on 2026-10-29. `hierarchy/<key>/sweep_daily.sh` reruns the sweep after each 00:00 UTC reset until it is complete.

## Stage 1: sources and captures
- **Do:**
  - Find each department's faculty listing URL eras. Use exact-URL Wayback CDX queries with `collapse=timestamp:4`. Prefix queries on a large host time out (503/504).
  - Write the eras into the charter as `[[departments.listings]]`. Entries that share a slot name are URL eras of one slot.
  - Capture one listing per slot and half-year, 2016–2026, with `listings/scripts/run_school.sh <key>`. `plan_fetch.py` takes a charter school's slots from the charter.
  - Parse the captures with `tools/listing_rows.py <key>`. It uses the formats in `tools/listing_formats.py`; add a format there when a page matches none. Contact lines are never kept.
- **Output:**
  - `listings/<key>/captures.sqlite`: the listing captures, in the listings-pipeline schema that the period tools read.
  - `captures/<key>.sqlite`: every other capture, plus robots files, probes and the `blocked` hosts.
  - `listings/<key>/rows.json`: one row per person and capture, with the quote running from the name through the title.
  - `listings/<key>/coverage.json`: department × year.
- **Gate:** every department has a usable listing for most years. Each missing half-year has a recorded reason: `nocapture`, `unusable` (with the parse result) or `out_of_scope`.
- **Learned from Michigan (2026-10-29):**
  - **A usable capture must parse to people, not just look like a listing.** Three spring captures of the CSE list were 31 KB script-rendered shells with title-like navigation lines. `plan_fetch` now requires a charter school's capture to parse to at least 5 entries.
  - **Page formats drift inside one site.** The name moved from a bold span to `<b>` in 2018, and from `<h4>` to `p.eecs_person_name` in 2025. Re-run `listing_rows.py` and compare the people per year after every format fix.

## Stage 2: faculty census
- **Do:**
  - Build the census from the listing rows with `tools/census_build.py <key>`.
    - **People:** rows are merged within the school when the family name matches and the given names are compatible (`given_compatible`): nicknames, 3+ letter prefixes, or initials. Prefix merges are never made under an East Asian family name.
    - **Ranks** are listed per year.
    - **Output:** `census/<key>-faculty.json`, `census/<key>-report.md`, `hierarchy/<key>/collection.json.gz`, and the builder's `listings/<key>/listings.json`.
  - Find computing-related faculty outside the full-coverage departments with `tools/cs_related_school.py candidates|units|review <key>`.
    - **Candidates** are people a department with `coverage = "affiliated"` lists as ladder faculty, and dump persons whose DBLP record names the school with 5 or more records in 2016–2026. Once the sweep is complete, add `tools/cs_related_candidates.py`'s OpenAlex rule.
    - **Unit listings** are captured yearly from Wayback (`[[affiliated_units]].listings`).
    - **Decisions:** `accepted`, `faculty_not_computing`, `research_or_other_rank` or `not_faculty_listed`, each with its evidence and the units searched. They go to `hierarchy/<key>/cs-related-review.json`; accepted people of other units go to `census/<key>-additions.json`.
  - Run the listed-not-in-census cross-check (`tools/listed_not_in_census.py`). For a protocol school the census is built from the listings, so this is a consistency check.
- **Gate:** the chain audit has 0 open `coverage` items.
  - Until `pi_hierarchy.py` and `chain_audit.py` read the charters (`tools/wire_charters.py`), run the coverage check on the census directly: every candidate has a decision.
- **Learned from Michigan (2026-10-29):**
  - **Build the census from the listings.** v1 assumed a census existed before the listings, as it did for the site-collection schools. A protocol school's census is built from its dated listings, so stages 1 and 2 are one pipeline.
  - **Courtesy and affiliate appointments in a full-coverage department are the cross-listing.** They count as PIs when the same listing row gives a professor rank in the person's home unit (basis `courtesy_faculty`). The home unit goes to `home-departments.json`.
  - **DBLP-affiliation candidates are mostly students, postdocs and alumni.** A "not faculty" decision is only as good as the units searched, so name them in the decision.

## Stage 3: PIs and labs
- **Do:**
  - Decide each PI's basis (`census_build.py`):
    - `ladder_faculty`: a listing row with a professor title in the department, not courtesy, adjunct, visiting, research, teaching, lecturer or emeritus;
    - `courtesy_faculty` (see stage 2);
    - research and teaching faculty only with reviewed evidence of a group or advisees (`hierarchy/<key>/pi-basis-evidence.json`).
  - Map each PI to a lab. A single-leader lab page becomes the lab; otherwise the PI gets a new own lab (`pi_hierarchy.py`).
  - Assign each PI a reviewed home department with `tools/home_departments_school.py <key> --write-shared`. It replaces only this school's rows in `hierarchy/home-departments.json`. No placeholders: a PI without a result is `hold`.
- **Gate:** the `pi` check is 100%, and every PI has a home department.
- **Learned from Michigan (2026-10-29):** a PI's home department comes from the same listing row that proves the appointment. No separate profile crawl is needed when the listing carries every title.

## Stage 4: appointment periods
- **Do:**
  - Run `tools/periods_school.py fetch|extract <key>`. It fetches each PI's listed homepage, live where `host_use` allows and otherwise the Wayback captures nearest 2026 and nearest the first listed year. It extracts appointment statements with `faculty_periods.candidates()`.
  - Mark a departure as `faculty_end_moved` when the person's own page says they moved.
- **Output:** `periods/<key>-faculty-periods.json` and `periods/<key>-holds.json`.
- **Gate:** every PI has a period, or a listing for each year that has papers. Before stage 7 there are no papers yet, so check that each PI's listing years are contiguous from the first listed year to the last.

## Stage 5: identity
- **Do:**
  - Review each PI's OpenAlex author ids, recording them as `reviewedOpenAlex`, `not_openalex` or `mixed_openalex` with evidence. This needs the sweep.
  - Add DBLP ids from the dump with `tools/dblp_ids_school.py <key>`: `school_affiliation` when exactly one candidate's note or URL names the school; `unique_name` when the only candidate names no other institution. The evidence is the dump record's sha256 and its affiliation note.
  - Add ORCIDs from the DBLP person's URLs. `census_build.py` folds both into the census.
  - Run `tools/dblp_dump_persons.py`. It includes onboarding schools.
- **Gate:** every PI has at least one anchor: a reviewed OpenAlex id, an ORCID or a DBLP page. Namesakes are reviewed.
- **Learned from Michigan (2026-10-29):**
  - DBLP decides about 70% of PIs on its own. The rest have common names whose DBLP records name no institution, and need the OpenAlex review.
  - Listing names can differ from DBLP names ("Satinder Singh Baveja" is DBLP's "Satinder Singh"; "Jag Jagadish" is "H. V. Jagadish"). Record such aliases in `census-overrides.json`.

## Stage 6: students
Use sources in this order of preference:
1. Dissertations in the thesis repository with an advisor field (DSpace `dc.contributor.advisor`, or the committee chair). **Learned from Michigan (2026-10-29):** check the repository's robots.txt for AI-agent rules first. Deep Blue disallows them by name, so Michigan starts at source 2.
2. Department PhD rosters, defence and FPO lists, and graduation lists, from Wayback.
3. Lab member pages, current and in Wayback.
4. Program-level listings ("Doctoral (Program)", "Reader"), only when the student co-wrote a lab paper.

OpenAlex co-authorship is never on its own evidence of advising.

- **Do:** record each relation with role, years and `url + sha256 + quote`.
- **Gate:** the `students` and `one_person` checks are 100% or explained.

## Stage 7: papers and links
- **Do:**
  - Run the OpenAlex institution sweep (`tools/oa_sweep.py`) and the PI works (`tools/pi_fulltext_affiliation.py works <key>`).
  - Run the DBLP and lab-page recovery (`tools/dblp_recover.py`, `tools/labpage_recover.py`) and the page-1 reader.
  - Build with `tools/pi_hierarchy.py <key>`.
- **Gate:**
  - the `papers` check passes: every zero-paper lab is reviewed and has a reason in `zero-paper-labs.json`;
  - the `links` check has 0 open items;
  - the evidence check passes.
- **Debt:** `dblp_recover.py` reads a pre-protocol school's cached DBLP lists (`pi_hierarchy.DBLP`). A protocol school needs it to read `hierarchy/dblp-dump-persons.json.gz` instead, or a `hierarchy/<key>/raw/dblp_pubs.json.gz` written from it.

## Stage 8: full texts
- **Do:**
  - Create the store catalog (stage 0), then add the lab papers (`fulltext-push/add_works.py`).
  - Run the channels (`run_steps.sh <key> oa_arxiv openalex proceedings arxiv_title dblp_ee s2 core europepmc pmc figshare labpages <school repository>`).
  - Start the download loop (`downloads.slurm`, adding the school to the array).
- **Gate:** copies are measured. The target is 85% of lab papers; every lab paper without a copy has a reason (only paywalled or login copies were found, or no open copy exists).

## Stage 9: accuracy
- **Do:** run the hand-checked sample (`accuracy/sample.py`, 105 judgments per school).
- **Gate:** lab-paper precision ≥ 0.95, student-link precision ≥ 0.97, and lab-paper coverage ≥ 0.90. Below a threshold, add a general rule with a test, never a one-off fix.

## Stage 10: release
- **Do:**
  - Set `status = "released"` in the charter. This adds the school to `atlas_paths.SCHOOL_IDS`, and so to the build, the audits, the release, the tree and the export. Regenerate `paths.sh`.
  - Run `hierarchy/rebuild.sh`: snapshot, build, audits, tests, regression, copies, release, tree.
  - Run the GitHub export from the release.
  - Hand off to the site. Codex adds the school to the site builder's `SCHOOLS`, its department mapping and the page copy; the charter's `[site]` table holds the mapping.
  - Upload to Hugging Face.
- **Gate:** the release exists, and the school appears in `schools/`, the export and the handoff.

## Files that must learn a new school
**Config-driven:** these read `schools/<key>.toml`, or `atlas_paths.SCHOOL_IDS`, which is the released charters.
- `tools/atlas_paths.py` (`SCHOOL_IDS`) and its generated `paths.sh` (`CS_ATLAS_SCHOOLS`), and through them `hierarchy/rebuild.sh`, `tools/make_release.py` and `tools/build_regression.py`.
- `tools/oa_sweep.py`, `tools/cs_related_candidates.py`, `tools/dblp_dump_persons.py`, `tools/listed_not_in_census.py`, `tools/student_audit.py`, `tools/zero_paper_ledger.py`, `tools/link_sweep.py` and `tools/school_profiles.py`.
- `listings/scripts/wb.py` and `listings/scripts/plan_fetch.py`.
- The stage tools added for protocol v2: `school_web.py`, `school_hosts.py`, `dblp_affiliated.py`, `listing_rows.py`, `census_build.py`, `cs_related_school.py`, `dblp_ids_school.py`, `home_departments_school.py` and `periods_school.py`.

**Prepared, not applied:** `tools/wire_charters.py` makes these read the charters. Run it once the builder agent's work on them is committed. It was tested on a copy: the six released schools' tables come out identical.
- `tools/pi_hierarchy.py`: `DBLP`, `INST`, `AFF`, `SCHOOL_LOOSE`, `OWN_UNITS` and the EPFL foreign-title exception. `pi_fulltext_affiliation.py`, `dblp_recover.py`, `labpage_recover.py` and `link_diagnosis.py` follow, because they import these from it.
- `tools/chain_audit.py`: `SCHOOLS`.
- `tools/export_release.py`: `ORDER`.
- `tools/organize_tree.py`: `NAMES`.

**Still by hand:** each is debt.
- `fulltext-push/downloads.slurm` (`SCHOOLS=(...)`) and the one-off collector scripts: `addworks-1029.slurm`, `newsteps.slurm`, `oa_editions.slurm`, `retry_transient.slurm`, `chain_*.sh` and `local-reuse/lr_common.py`.
- `hierarchy/organize-tree.slurm` (default `S=`).
- The per-school catalog builders (`fulltext-push/berkeley_catalog.py`, `stanford_catalog.py`). A protocol school should use one generic builder with the school key.
- `tools/faculty_periods.py`: `STAGES` and `SCHOOL`, for the pre-protocol schools. Protocol schools use `tools/periods_school.py`.
- The site builder's `SCHOOLS`, `FULL_CODES` and `CORE` tables (Codex's checkout).
- `ai-writing/*` school tuples. They are the study's scope, and the owner decides whether a new school enters it.

## Stage reports
After each stage, write `hierarchy/<key>/STAGE-<n>.md`: what was done, the counts, the gate result, and every exception with its reason. These reports are how a school's onboarding is reviewed.
