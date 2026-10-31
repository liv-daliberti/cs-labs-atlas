# Adding a school: the standard protocol

**Version 2.2, 2026-10-30.**
- Version 1 was drafted from how Princeton, CMU, EPFL, MIT, Berkeley and Stanford were built.
- Version 2 is version 1 corrected by its first run, on the University of Michigan, the seventh school (`hierarchy/michigan/STAGE-*.md`).
- Version 2.1 adds what Michigan's stages 2–8 taught on 2026-10-30, marked **Learned from Michigan (2026-10-30)**:
  - the bulk-pull sanity gate;
  - gzip-encoded Wayback captures;
  - the computing-share test;
  - gap-year evidence;
  - the reviewed OpenAlex identity tool;
  - the previous-school, alumni-text and student-directory rules;
  - the unavailability ledger.
- Version 2.2 adds the lab-page audit gates to stages 3, 6 and 7 (`tools/labpage_audit.py`, `docs/LAB-PAGES.md`), marked
  **Lab-page audit (v2.2)**.
- Each change is marked **Learned from Michigan (2026-10-29)** or **(2026-10-30)**.

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
  - **Learned from Michigan (2026-10-30):** `pub.orcid.org/robots.txt` is `User-agent: * / Disallow: /`. The ORCID public
    API is therefore not a usable period source, although one Berkeley period (Giuseppe Loianno) cites
    `pub.orcid.org/v3.0/.../employments`; the owner should review that citation.
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
- **Learned from Michigan (2026-10-30):**
  - **Bulk-pull sanity gate (owner standard).** After every OpenAlex sweep and every DBLP dump pull, run
    `tools/sweep_check.py <key>`. It is wired into `hierarchy/<key>/run_sweep.sh`, and `stage_gate.py` reads the result
    for stage 2 and stage 7. It writes `hierarchy/<key>/sweep-check.json` with:
    - per-year raw and paper-only counts, and stored-vs-API-count completeness;
    - the duplicate rate by work id and by DOI;
    - a year-outlier test: 3× (or ⅓×) the median of the other years, or a robust z above 8 with the MAD floored at
      5% of the median; the current year is exempt on the low side;
    - the share of works carrying a charter institution id, and that every lineage id occurs;
    - for DBLP: the dump file, the PIs' per-year records, duplicate keys, and PI ids missing from the dump-persons file.

    It exits 1 when a test trips, unless the charter's `[sweep_check].exceptions` holds a reviewed exception with a
    reason. With `verify = "papers_normal"` the check re-verifies the stated cause: the paper-only count must be normal.
  - Michigan's 2022 had 434,618 ENCODE dataset records (one UM author). The back-test on the released sweeps found
    Berkeley 2026 with 36,836 PNNL dataset records; there is no exception recorded for it yet. Both are non-papers that
    every reader drops (`pi_hierarchy.NOT_PAPERS`). A tool that reads the sweep must drop them too:
    `cs_related_candidates.py` did not.
  - The DBLP part needs `pis.json`, so run the check again after the first build of stage 3 or 7. Regenerate
    `hierarchy/dblp-dump-persons.json.gz` (`tools/dblp_dump_persons.py`) after the PI set changes.

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
- **Learned from Michigan (2026-10-30):** **Wayback `id_` captures can be gzip-encoded.** Wayback serves the archived
  bytes with their original Content-Encoding, even to a request asking for identity.
  - Stored raw, they parse as an empty page. Michigan's "31 KB script-rendered shells" of the CSE list were full 230 KB
    lists, gzipped.
  - Read stored bytes through `wb.body()` (`school_web.body`). It gunzips, while the sha256 stays the hash of the
    bytes as served.
  - `school_web.repair_gzip(con)` re-derives blocks and text for stored rows. Before calling a capture unusable, check
    `zlib.decompress(raw)[:2] == b'\x1f\x8b'`.

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
- **Gate:** the chain audit has 0 open `coverage` items, and `tools/stage_gate.py <key> 2` passes.
  - `stage_gate.py` is stricter than the audit: it also counts `pending_openalex` decisions as open. It checks the gates of stages 1–5 from the stage files.
  - Until `pi_hierarchy.py` and `chain_audit.py` read the charters, run them from a wired copy: `tools/wire_charters.py` applied to a copy of `tools/` under `hierarchy/<key>/tmp/`. Then call `chain_audit.audit('<key>')` in-process; never write the shared `chain-audit.json` that way.
- **Learned from Michigan (2026-10-29):**
  - **Build the census from the listings.** v1 assumed a census existed before the listings, as it did for the site-collection schools. A protocol school's census is built from its dated listings, so stages 1 and 2 are one pipeline.
  - **Courtesy and affiliate appointments in a full-coverage department are the cross-listing.** They count as PIs when the same listing row gives a professor rank in the person's home unit (basis `courtesy_faculty`). The home unit goes to `home-departments.json`.
  - **DBLP-affiliation candidates are mostly students, postdocs and alumni.** A "not faculty" decision is only as good as the units searched, so name them in the decision.
  - **A DBLP record that does not name the school is not evidence of no computing output.** Decide an affiliated-department person negatively only when no DBLP record of the name has output in the window. Otherwise the person is `pending_openalex` until the sweep gives the DBLP-indexed share of their school works.
  - **Name forms in one school's listings:** merge forms that link the same personal homepage ('H.V.' / 'Jag' Jagadish, 'Georgios' / 'George' Tzimpragos).
  - **Parser completeness:** assert, per capture, that the parsed entries equal the page's own entry markers. The first Michigan parser silently dropped 2018–19 entries that had no homepage link.
- **Learned from Michigan (2026-10-30):**
  - **Run the OpenAlex candidate rule for one school** with
    `tools/cs_related_candidates.py --no-venues --stats --out cs-related-candidates-openalex.json <key>`.
    - It leaves the shared `cs-venues.json` alone and writes `hierarchy/<key>/oa-author-stats.json.gz` (every author
      id with 3+ school papers).
    - It counts papers only, and authorships of `openalex_related` institutions only when the raw string matches the
      regex.
    - `cs_related_school.py candidates` merges these candidates as source `openalex_rule`.
  - **Search the units the OpenAlex candidates come from.** At Michigan they came from Aerospace, CLASP, BME, CEE and
    the Medical School, none of which had been searched. A unit's faculty list is often its `/people/` page, not
    `/people/faculty/`: exact-URL CDX both.
  - **Computing-share test** (`cs_related_school.share_test`, owner decision 2026-10-30).
    - Identity: ORCID ids, plus ids under the family name and first spelled-out given name, with namesakes set aside
      (another ORCID, or works ending before the first listing).
    - Computing when 5+ school papers are DBLP-indexed and they are ≥ 20% of the papers. Not computing when it fails
      on 8+ papers. Below 8, the DBLP decision stands; with no DBLP decision, `too_few_school_works`, which is a
      decision, not open.
    - It decides pending people, OpenAlex candidates, people without 5 DBLP records, and the acceptances the owner
      names in `[cs_related].share_test_settles`. Other DBLP acceptances stand, with `share_flag` when the test fails.
      The owner rules on those.
    - It is noisy for arXiv-heavy theorists with few school works: unpublished preprints count as papers but not as
      DBLP-indexed.
  - **Read a listed rank up to its own "Professor".** "Associate Professor of Information, School of Information and
    Research Associate Professor, ICPSR" is a ladder title.
  - **Reviewed OpenAlex ids** (`tools/oa_identity_school.py <key>`) come from `hierarchy/<key>/openalex-identity-review.json`
    (hand decisions) and from the accepted people's share-test ids. They go into the school's section of
    `census-overrides.json` with sweep-work evidence.

## Stage 3: PIs and labs
- **Do:**
  - Decide each PI's basis (`census_build.py`):
    - `ladder_faculty`: a listing row with a professor title in the department, not courtesy, adjunct, visiting, research, teaching, lecturer or emeritus;
    - `courtesy_faculty` (see stage 2);
    - research and teaching faculty only with reviewed evidence of a group or advisees (`hierarchy/<key>/pi-basis-evidence.json`).
  - Map each PI to a lab. A single-leader lab page becomes the lab; otherwise the PI gets a new own lab (`pi_hierarchy.py`).
  - Assign each PI a reviewed home department with `tools/home_departments_school.py <key> --write-shared`. It replaces only this school's rows in `hierarchy/home-departments.json`. No placeholders: a PI without a result is `hold`.
- **Gate:** the `pi` check is 100%, and every PI has a home department.
- **Lab-page audit (v2.2) gate:** `tools/labpage_audit.py discover <key>` has run (Slurm: `hierarchy/labpage-audit.slurm <key>`,
  STEPS=discover). Every PI in `pis.json` has a `lab_page` record in `hierarchy/<key>/labpage-audit.jsonl.gz` with a status,
  a reason code from `docs/LAB-PAGES.md`, and dated checks of the school profile, DBLP, ORCID and homepage sources. A lab
  whose only site is at another institution is never audited as this school's lab.
- **Learned from Michigan (2026-10-29):** a PI's home department comes from the same listing row that proves the appointment. No separate profile crawl is needed when the listing carries every title.

## Stage 4: appointment periods
- **Do:**
  - Run `tools/periods_school.py fetch|extract <key>`. It fetches each PI's listed homepage, live where `host_use` allows and otherwise the Wayback captures nearest 2026 and nearest the first listed year. It extracts appointment statements with `faculty_periods.candidates()`.
  - Mark a departure as `faculty_end_moved` when the person's own page says they moved.
- **Output:** `periods/<key>-faculty-periods.json` and `periods/<key>-holds.json`.
- **Learned from Michigan (2026-10-29):**
  - `faculty_periods.candidates()` matches case-sensitively, so pass the school pattern as `(?i:...)`.
  - Homepage fetching shares the Wayback lock with every other capture (6 s per request), so start it as soon as the census exists: 248 PIs take about 3 hours.
  - A closed range followed by later professor-rank listings is a rank step, not a departure ('2014-2020: Assistant Professor').
  - A closing statement that says the PI moved is written as `faculty_end_moved` evidence, which the builder's R-PAP-03 uses to set stale listings aside. At Michigan, Cafarella's 6 adjunct years after his move to MIT were set aside.
  - Wayback starts refusing connections when several fetchers run at once, even under the shared 6 s lock. Run one fetching stage at a time.
- **Gate:** every PI has a period, or a listing for each year that has papers. Before stage 7 there are no papers yet,
  so check that every year of the PI's professor-rank span (first to last ladder or courtesy year) has a listing of
  any rank (`stage_gate.span_gaps`).
- **Learned from Michigan (2026-10-30):**
  - **Gap years.** `tools/periods_school.py gaps <key>` reads, for each year missing from the span, dated Wayback
    captures of that year: the PI's homepage, the unit listing that lists them, and the unit's per-person profile
    page.
    - A capture naming the PI with a ladder title proves that calendar year, like a dated listing. A homepage must
      also name the school.
    - When every gap year is proven, a bridged period goes to `census-overrides.json`
      (`reviewed: periods_school_gaps_<date>`).
    - Roster years alone never bridge a gap.
  - **The span is set by professor rank.** A research-scientist year does not open it (Ziyou Song: research 2020,
    visiting 2024, ladder 2025–). An adjunct year inside it still counts as listed (Jason Corso, 2021).
  - **"Assistant Professor (beginning 9/2017)" is a future start** (R-PAP-02). Census ranks should not count it as
    ladder. Mert Pilanci is in Michigan's census for 2016–2018 and is also Stanford's PI, so the owner should review
    him.
  - **Profile pages.** UMSI profile pages (`www.si.umich.edu/people/<first>-<last>`) closed the gap years the
    paginated UMSI directory missed.
  - **Unit directories miss whole years, not just gaps.** UMSI's directory is paginated in Wayback for 2021–2025, so its
    faculty were listed in 2020 and 2026 only, and their lab papers in between fell outside the appointment.
    - `tools/periods_school.py extend <key>` checks every unlisted window year of a census addition against the
      dated captures of its unit profile page. The URL shapes are the charter's `[periods].profile_patterns`, for
      example `www.si.umich.edu/people/{first}-{last}`, `robotics.umich.edu/profile/{all}/` and
      `bme.umich.edu/people/{last}-{first}/`.
    - Each contiguous run of proven years becomes a reviewed period.
    - Run it before the stage 7 build. It reads one CDX per URL for the whole window.
  - **Periods written by a tool must use ISO dates** (`2026-10-29`). `pi_hierarchy.contains()` reads `20261029` as
    unresolved, so every paper falls outside the period.
  - **A suffix is not the family name in listing quotes either** (R-PAP-08, fixed in `pi_hierarchy` 2026-10-30).
    'Lionel P. Robert Jr.' is listed as 'Lionel Robert'.
  - **Wayback shells.** Robotics' 2025 directory captures are 2.4 KB script shells; 2025 needs the per-person profiles.

## Stage 5: identity
- **Do:**
  - Review each PI's OpenAlex author ids, recording them as `reviewedOpenAlex`, `not_openalex` or `mixed_openalex` with evidence. This needs the sweep.
  - Add DBLP ids from the dump with `tools/dblp_ids_school.py <key>`. The rules, in order:
    - `homepage_url`: the record links the homepage the department listing links;
    - `school_affiliation`: exactly one candidate's note or URL names the school;
    - `unique_exact_name`: exactly one record carries the full name, with no homonym number and no busier namesake;
    - `unique_name`: the only record of the name.

    The evidence is the dump record's sha256 and the quote (the note, the `<url>` or the name). The tool also counts each candidate's records in the window, which the CS-related review uses.
  - Add ORCIDs from the DBLP person's URLs. `census_build.py` folds both into the census.
  - Run `tools/dblp_dump_persons.py`. It includes onboarding schools.
- **Gate:** every PI has at least one anchor: a reviewed OpenAlex id, an ORCID or a DBLP page. Namesakes are reviewed.
- **Learned from Michigan (2026-10-29):**
  - With the affiliation note and the strict unique-name rule alone, 27% of PIs got no DBLP id (45 of 164 in the first run). With the listing's homepage URL, the exact-name rule and the relaxed unique-name rule, 9% got none (19 of 211), before any OpenAlex review.
  - A unique record must not be rejected for naming another institution: a PI who moved away has only the new one in DBLP.
  - An exact-name record must not win over a busier middle-initial record ('Vijay Subramanian' / 'Vijay G. Subramanian').
  - A co-authorship round decides more namesakes: among several namesake records, take the one that shares 5 or more window records with the school's already-decided PIs, when no other candidate shares any (`school_coauthors`). At 3, false matches came in.
  - The PI's own homepage often links DBLP and ORCID (`tools/homepage_links_school.py`).
  - The remaining PIs have common names and need the OpenAlex review.
  - Listing names can differ from DBLP names ("Satinder Singh Baveja" is DBLP's "Satinder Singh"; "Jag Jagadish" is "H. V. Jagadish"). Record such aliases in `census-overrides.json`.
- **Learned from Michigan (2026-10-30):**
  - **The OpenAlex review is a file, then a tool.** Write the hand decisions to `hierarchy/<key>/openalex-identity-review.json`
    as `{name: {openalex, why, aliases?}}`, then run `tools/oa_identity_school.py <key>`. Read the candidates from
    `oa-author-stats.json.gz` (names, ORCIDs, venues, years per author id).
  - **First-given-name matching admits namesakes.** 'Jeong M. Park' matches 'Jeong Joon Park'. Check venues against the
    PI's field and years against the listing.
  - **A homepage's DBLP link can point to a pid that is not in the dump** (Stella Yu: `pid/172/9071`, merged or
    retired). Prefer the dump person carrying the PI's ORCID, and the id the PI's lab at another atlas school carries.
  - **Cross-school PIs** (Stella Yu: Berkeley to Michigan in 2022; Jia Deng, Matthew Johnson-Roberson, Pei Zhang,
    Michael Cafarella, Leia Stirling, Prabal Dutta, Mert Pilanci) should carry the same DBLP id or ORCID in both
    schools. Stage 6 and the atlas ids rely on it.

## Stage 6: students
Use sources in this order of preference:
1. Dissertations in the thesis repository with an advisor field (DSpace `dc.contributor.advisor`, or the committee chair). **Learned from Michigan (2026-10-29):** check the repository's robots.txt for AI-agent rules first. Deep Blue disallows them by name, so Michigan starts at source 2.
2. Department PhD rosters, defence and FPO lists, and graduation lists, from Wayback.
3. Lab member pages, current and in Wayback.
4. Program-level listings ("Doctoral (Program)", "Reader"), only when the student co-wrote a lab paper.

OpenAlex co-authorship is never on its own evidence of advising.

**Learned from Michigan (2026-10-29):**
- **Lab pages.** `tools/labpage_students_school.py links|extract <key>` turns the PIs' homepages, and the people pages
  they link, into the builder's `labpage-evidence.json` with `lpdom.member_candidates`. Quotes run from the heading to the
  name. Faculty names, alumni without a year and pre-window entries are dropped.
- **Precision.** About 4,000 of 4,500 raw candidates are not names. A homepage can list students from the PI's previous
  school. Mark the rows `auto: true` for the accuracy sample.
- **Defense announcements.** On the EECS sites an announcement names the adviser only as "Faculty Host" (about 1 in 6
  captures). The defenses index pages name no chair.
- **Program directories without advisers** (the CSE PhD directory) help only after stage 7, through the
  co-authorship rule.
  **Corrected 2026-10-30:** they do not, through co-authorship. R-STU-02 keeps a weak tie that already names the lab,
  and a directory without an adviser names none. They help through the students' own websites (below).

**Learned from Michigan (2026-10-30):**
- **Students' own websites.** `tools/labpage_students_school.py directory <key>` reads the charter's
  `[students].directories`: program PhD directories that list each student's website, with no adviser.
  - It fetches each website like a lab page.
  - It keeps a relation when the page names the school, says PhD, and puts an adviser phrase ('advised by', 'under
    the supervision of', 'my advisor is', 'Advisor:') directly before a PI's full name. 'Working with' does not count.
  - Years are the directory years that list the student. The evidence is the student's page (url, sha256, quote), plus
    the directory capture.
- **Alumni sections without heading elements.** An 'Alumni' line that is plain text leaves the role headings under it
  looking current (Stella Yu's Berkeley PhD alumni and postdocs).
  - `alumni_in_text`: an alumni marker before the section heading, with no 'Current' marker between, makes the
    section alumni.
  - The quote then starts at the marker, and alumni without a year are dropped as before.
- **Students from the PI's previous school.** A lab-page student whom the same PI's lab at a released school already
  holds is that school's student. The PI is matched by a shared DBLP id or ORCID.
  - Such a student is dropped unless the page states a start year in or after the PI's first listing here
    (`previous_school_students`).
  - At Michigan this dropped 11 students under 8 cross-school PIs. Stella Yu's are the ones Berkeley lists.
- **The Mathematics Genealogy Project** (no robots.txt) has advisers for many CS dissertations. It was offline from
  21 October 2026 (a PHP vulnerability), so try it when it is back.
- **Gzip-encoded captures** (stage 1) also hid lab pages: Stella Yu's 2026 page was one of 12 such lab pages.
- **Run `tools/student_audit.py` with every school** (`princeton cmu epfl mit berkeley stanford <key>`). It rewrites
  the shared `hierarchy/student-audit.json`, and a one-school run drops the released schools' entries.
- **PIs' homepages from DBLP.** `periods_school.targets` adds the URLs of the PI's DBLP person record, skipping
  authority records. Most PIs of other units have no homepage in their unit listing.
- **Gate result at Michigan (2026-10-30): source-limited.** 116 of 288 labs have students. With the thesis
  repository excluded, a school needs a researched few-students pass over the remaining labs before stage 6 passes.

- **Do:** record each relation with role, years and `url + sha256 + quote`.
- **Gate:** the `students` and `one_person` checks are 100% or explained.
- **Lab-page audit (v2.2) gate:** every found lab page, and every homepage used as the lab page, has its students section
  audited, alumni included (`students.page_status` set). Every listed member is in the build or carries a reason code.
  `genuinely_missing` is at most the whitelisted share, and every such member is in `hierarchy/<key>/labpage-additions.json`
  (rule LP-STU-01). The additions are wired only when a fresh random 20 proposed students has at most 1 membership error and
  at most 2 role/year errors (doubtful = half); a failed round means a rule fix, a re-run and a NEW sample of 20, and after 3
  failed rounds the work stops and is reported. Every round is recorded (`labpage-handcheck.json`, `LABPAGE-AUDIT.md`); the
  accepted one is `labpage-acceptance.json`. After any rule change, 10 students are re-sampled at every accepted school.

## Stage 7: papers and links
- **Do:**
  - Run the OpenAlex institution sweep (`tools/oa_sweep.py`) and the PI works (`tools/pi_fulltext_affiliation.py works <key>`).
  - Run the DBLP and lab-page recovery (`tools/dblp_recover.py`, `tools/labpage_recover.py`) and the page-1 reader.
  - Build with `tools/pi_hierarchy.py <key>`.
- **Gate:**
  - the `papers` check passes: every zero-paper lab is reviewed and has a reason in `zero-paper-labs.json`;
  - the `links` check has 0 open items;
  - the evidence check passes;
  - **Lab-page audit (v2.2):** every listed 2016-2026 paper on a lab page is a lab paper or carries a reason code; no paper
    is `not_yet_resolved` (run the `recover` step after the OpenAlex daily reset if the budget ran out; it stops at 6k
    credits left); `genuinely_missing` papers are in `labpage-additions.json` (rule LP-PAP-01); a fresh random 20 proposed
    papers has at most 1 error (doubtful = half, wrong metadata = an error) before they are wired, under the same rounds rule
    as stage 6.
- **Debt:** `dblp_recover.py` reads a pre-protocol school's cached DBLP lists (`pi_hierarchy.DBLP`). A protocol school needs it to read `hierarchy/dblp-dump-persons.json.gz` instead, or a `hierarchy/<key>/raw/dblp_pubs.json.gz` written from it.

## Stage 8: full texts
- **Do:**
  - Create the store catalog (stage 0), then add the lab papers (`fulltext-push/add_works.py`).
  - Run the channels (`run_steps.sh <key> oa_arxiv openalex proceedings arxiv_title dblp_ee s2 core europepmc pmc figshare labpages <school repository>`).
  - Start the download loop (`downloads.slurm`, adding the school to the array).
  - **Learned from Michigan (2026-10-30):**
    - Compute nodes have no `/usr/local/anaconda3`, while the collector child (`vendor/cmu_tools/collector_wrapper.py`)
      needs `protego`.
    - Run the school's channels and its loop as one Slurm job modelled on `<school>-collector.slurm`
      (`fulltext-push/michigan-collector.slurm`). Use `CS_ATLAS_COLLECTOR_PY` / `FTP_PY` set to the project env on
      shared storage (`env/atlas/bin/python`, which has protego and bs4).
    - Seed the catalog with `add_works.py <key>` on the login host first.
  - Measure: `tools/lab_paper_copies.py <key>` -> `hierarchy/<key>/copies.json`.
  - **Unavailability ledger (owner standard 2026-10-30; spec and vocabulary: `docs/UNAVAILABLE.md`).** Run
    `fulltext-push/unavailable_ledger.py <key>` (collector Python, `-I`) after `copies.json` exists. Output: an
    unavailability ledger for every lab paper without a copy, `hierarchy/<key>/unavailable.jsonl.gz` and
    `unavailable-summary.json`: one reason code per paper from the fixed vocabulary, with its evidence and check date, and
    `incomplete_check` when any applicable source was not checked. It attaches `unavailable_reason` to `copies.json` and
    records its checks in `fulltext-push/checks/<key>.sqlite`. Options: `--max-age-days N` (default 30; OpenAlex 7),
    `--offline`, `--only <paper key>`, `--no-network-sources s2,s2_title,core,dblp,wayback_acm`. The release step is
    `ledger`, after `copies`, in `hierarchy/rebuild.sh`.
- **Gate:**
  - copies are measured. The target is 85% of lab papers.
  - every non-local lab paper has a ledger entry, and `incomplete_check` is at most the whitelisted threshold
    (`docs/evidence-whitelist.json`; the evidence check's categories `unavailable_missing`, `unavailable_stale` and
    `unavailable_incomplete`).

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
- The stage tools added for protocol v2: `school_web.py`, `school_hosts.py`, `dblp_affiliated.py`, `listing_formats.py`, `listing_rows.py`, `census_build.py`, `cs_related_school.py`, `dblp_ids_school.py`, `homepage_links_school.py`, `home_departments_school.py`, `periods_school.py`, `labpage_students_school.py` and `stage_gate.py`.
- Builder changes a protocol school needs while another agent owns the builder go to `hierarchy/<key>/REQUESTS-FOR-BUILDER.md`.

**Applied 2026-10-29** (commit `65b50eb`, by the coordinator after release 2026-10-29.3): `tools/wire_charters.py` made these read the charters. The six released schools' tables are unchanged.
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
