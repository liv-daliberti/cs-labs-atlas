# Adding a school: the standard protocol

Version 1, 2026-10-29. This was drafted from how Princeton, CMU, EPFL, MIT, Berkeley and Stanford were built. It is
being tested on the University of Michigan, the seventh school. Each stage has inputs, outputs, a gate (what must be
true before the next stage starts) and a stage report. A school is "in" only when every gate passes and it ships in a
release.

## Scope (owner rules; see `docs/RULES.md`)
- **Unit of analysis.** School → department → PI lab → papers + students. Centres, institutes and multi-PI groups are
  not labs; a collective can only contain labs.
- **Who counts.** Computing-related faculty in any department: computing must be the object or the method of their
  research. Administrative advisers are not PIs.
- **Window.** 2016–2026.
- **Evidence.** Every fact carries `url + sha256 + verbatim quote`. Appointment intervals are never inferred from roster
  years. A dated department faculty listing proves an appointment for its own calendar year only, and not after an
  evidenced move-out.
- **Students.** Named as the public sources name them, with advisor, role, years and source, and no contact details.
  Name merges happen only within one lab.
- **Access.** No paywalls, logins or bot challenges. Respect robots.txt. Stop using a host as soon as it serves a
  challenge. dblp.org is never fetched; use the local dump (`atlas_paths.DBLP_DUMP`). API keys live in
  `~/.config/cs-atlas/*.env` and are never printed. The owner's email is never sent anywhere.
- **Compute.** Follow `/etc/claude-code/CLAUDE.md`: Slurm jobs carry mem, time and cpus; run `sbatch --test-only`
  first; `--exclude=node302`; leave 60 s or more between polls; local runs use `nice`; one heavy builder at a time.

## Stage 0: charter and config
- **Output:**
  - `schools/<key>.toml`, from `schools/TEMPLATE.toml`, holding:
    - name and key;
    - OpenAlex institution id(s) and lineage, and the ROR id;
    - web and email domains;
    - the affiliation regex (names, abbreviations, the school's own unit names);
    - departments, each with a URL, coverage `full | affiliated`, and its listing URLs;
    - the thesis repository: kind, base URL and robots status;
    - lab-page hints, DBLP affiliation strings, the language exception for book titles, and the store path.
  - `hierarchy/<key>/` and the store directory.
- **Gate:**
  - every host named in the config has been checked against its robots.txt and has served no challenge;
  - the config is reviewed and committed.

## Stage 1: sources and captures
- **Do:**
  - Capture each department's faculty listing once per year for 2016–2026. Prefer Wayback `id_` URLs, one capture per
    year, spring first.
  - Capture the current directory, the thesis-repository index and the lab pages.
  - Store everything in `captures/<key>.sqlite` (url, sha256, fetched_at, body).
- **Output:** `census/<key>-sources.md`: a department × year coverage table, with gaps explained.
- **Gate:** every department has a listing for most years. Each missing year has a recorded reason (no capture, page
  did not exist, challenge).

## Stage 2: faculty census
- **Do:**
  - List every person on any listing, with their rank as listed per year, emeritus and visiting flags, and a verbatim
    quote. Write `census/<key>-faculty.json` and `census/<key>-report.md`.
  - Find computing-related faculty in other departments through:
    - DBLP affiliation strings in the dump;
    - the OpenAlex institution sweep, using the share of each person's works in CS concepts;
    - cross-listings.

    Each candidate gets a decision with evidence in `hierarchy/<key>/cs-related-review.json`.
  - Run the listed-not-in-census cross-check (`tools/listed_not_in_census.py`).
- **Gate:** the chain audit has 0 open `coverage` items.

## Stage 3: PIs and labs
- **Do:**
  - Decide each PI's basis: ladder faculty, or research faculty with a stated group or advisees.
  - Map each PI to a lab: a single-leader lab page, or a new own lab.
  - Assign each PI a reviewed home department and record it in `hierarchy/home-departments.json`. No placeholders.
- **Gate:** the `pi` check is 100%, and every PI has a home department.

## Stage 4: appointment periods
- **Do:**
  - Run `tools/faculty_periods.py fetch|extract <key>` to get periods with verbatim start and end quotes, from a CV,
    bio, news item or arrival announcement.
  - Mark a departure as `faculty_end_moved` when the person's own page says they moved.
- **Output:** `periods/<key>-faculty-periods.json` and holds.
- **Gate:** every PI has a period, or a listing for each year that has papers.

## Stage 5: identity
- **Do:**
  - Review each PI's OpenAlex author ids, recording them as `reviewedOpenAlex`, `not_openalex` or `mixed_openalex`
    with evidence.
  - Add ORCID, and the DBLP person page from the dump (`tools/dblp_dump_persons.py`).
- **Gate:** every PI has at least one anchor: a reviewed OpenAlex id, an ORCID or a DBLP page. Namesakes are reviewed.

## Stage 6: students
Use sources in this order of preference:
1. Dissertations in the thesis repository with an advisor field (DSpace `dc.contributor.advisor`, or the committee
   chair).
2. Department PhD rosters, defence and FPO lists, and graduation lists, from Wayback.
3. Lab member pages, current and in Wayback.
4. Program-level listings ("Doctoral (Program)", "Reader"), only when the student co-wrote a lab paper.

OpenAlex co-authorship is never on its own evidence of advising.

- **Do:** record each relation with role, years and `url + sha256 + quote`.
- **Gate:** the `students` and `one_person` checks are 100% or explained.

## Stage 7: papers and links
- **Do:**
  - Run the OpenAlex institution sweep (`tools/oa_sweep.py`) and the PI works (`tools/pi_fulltext_affiliation.py
    works <key>`).
  - Run the DBLP and lab-page recovery (`tools/dblp_recover.py`, `tools/labpage_recover.py`) and the page-1 reader.
  - Build with `tools/pi_hierarchy.py <key>`.
- **Gate:**
  - the `papers` check passes: every zero-paper lab is reviewed and has a reason in `zero-paper-labs.json`;
  - the `links` check has 0 open items;
  - the evidence check passes.

## Stage 8: full texts
- **Do:**
  - Create the store catalog, then add the lab papers (`fulltext-push/add_works.py`).
  - Run the channels (`run_steps.sh <key> oa_arxiv openalex proceedings arxiv_title dblp_ee s2 core europepmc pmc figshare labpages <school repository>`).
  - Start the download loop (`downloads.slurm`, adding the school to the array).
- **Gate:** copies are measured. The target is 85% of lab papers; every lab paper without a copy has a reason (only
  paywalled or login copies were found, or no open copy exists).

## Stage 9: accuracy
- **Do:** run the hand-checked sample (`accuracy/sample.py`, 105 judgments per school).
- **Gate:** lab-paper precision ≥ 0.95, student-link precision ≥ 0.97, and lab-paper coverage ≥ 0.90. Below a
  threshold, add a general rule with a test, never a one-off fix.

## Stage 10: release
- **Do:**
  - Run `hierarchy/rebuild.sh`: snapshot, build, audits, tests, regression, copies, release, tree.
  - Run the GitHub export from the release.
  - Hand off to the site (Codex adds the school to the site builder's `SCHOOLS`, its department mapping and the page
    copy).
  - Upload to Hugging Face.
- **Gate:** the release exists, and the school appears in `schools/`, the export and the handoff.

## Stage reports
After each stage, write `hierarchy/<key>/STAGE-<n>.md`: what was done, the counts, the gate result, and every exception
with its reason. These reports are how a school's onboarding is reviewed.
