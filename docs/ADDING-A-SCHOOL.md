# Adding a school: the standard protocol

**Version 3.0, 2026-11-05.**
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
- Version 2.3 adds what the University of Chicago, the eighth school, taught in stages 0-1 (`hierarchy/uchicago/reports/PROTOCOL-FRICTION.md`),
  marked **Learned from UChicago (2026-11-02)**.
- Each change is marked **Learned from Michigan (2026-10-29)** or **(2026-10-30)**.
- **Version 3.0 merges the lessons of Michigan, the University of Chicago and Georgia Tech** (89 lessons, `docs/ONBOARDING-LESSONS.md`, ids `L-nn`)
  before Harvard, Johns Hopkins and WashU start. Each stage ends with a **v3** block: what is **automated** (a command or a gate does it), what is
  still **manual** (a person or agent decides), and the pitfalls with their lesson ids. New: the "Before you start" checklist, the trap checks
  (`atlas stage-gate <key> --traps`, also run inside each stage gate), "Reviewed files and the overlay root", "Running three schools in
  parallel", and "Before you land".

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
  - Slurm jobs carry mem, time and cpus. Run `sbatch --test-only` first, use `--exclude=node302`, and do not poll: chain jobs with dependencies and read their output files (`atlas pipeline ... --wait` makes one `sacct` call per 120 s or more).
  - Local runs use `nice`. One heavy builder runs at a time.
  - Temporary files go in `hierarchy/<key>/tmp/` (ignored by git), never in login `/tmp`.

## Before you start (v3)
Do these before `atlas new-school`; each one was a day lost at least once (lesson ids in brackets).
1. **Worktree.** `tools/agent_worktree.sh new <key>`; run `bin/atlas ...` from it. Commit before every `--from-worktree` submit: jobs run the committed HEAD [L-01, L-08, L-09].
2. **Read** `docs/ONBOARDING-LESSONS.md`, `docs/RULES.md` (R-STU-13..18, R-PAP) and the newest school's `reports/PROTOCOL-FRICTION.md`.
3. **Owner decisions that change data, before the first sweep:** which lineage children stay (Argonne-like national labs, hospitals), which institutions are
   `openalex_related` (regex-only), same-name campuses to exclude [L-06]. Changing them later cost UChicago 120 minutes and a re-run of three layers.
4. **Budgets.** The shared OpenAlex key has 10k credits a day; check what is left. A snapshot school needs none (`snapshot-ext`, 25 minutes) [L-04].
   The release may be running: never modify tracked files in the main checkout; `git -C <main> status --short` after each stage while one runs [L-48].
5. **Access.** For every host: robots.txt incl. rules naming ClaudeBot / anthropic-ai (a Crawl-delay counts), a probe fetch for a challenge, and for the thesis
   repository records x crawl delay in hours. A host that challenges or refuses automated clients (bot challenge, a 403 on robots.txt) is read through Wayback: `use = wayback-only`, always allowed (owner 2026-11-05). A host whose robots.txt disallows AI agents by name (ClaudeBot, anthropic-ai, Claude-Web) is not used in any form, not through Wayback either; its holdings reach us only through OpenAlex and CORE [L-12, L-13, L-66, L-67, L-68].
6. **Fill the whole charter now.** `atlas new-school` starts from a TEMPLATE that holds every section later stages read: affiliation regex with
   `must_match` / `must_not_match` cases (include DBLP notes, other campuses, medical centres), `loose`, `own_units`, `[dblp].affiliation_strings`,
   `[repository]` (name and link pattern, for the stage-8 ledger), `[collector].channels`, `[thesis]`, `[students]` sources, `[census].home_units` and
   `rank_words`, every `[[hosts]]` entry. The stage-0 gate fails on the ones a later stage would crash on [L-11, L-76].
7. **Branch hygiene for the data tree.** Know which files are tracked: reviewed inputs and reports are tracked, built packages are not. A new reviewed file
   name needs its `.gitignore` line in the same commit [L-59].
8. **One driver per branch.** One session submits stages; background waits (`slurm_wait.py` under `run_in_background`) never submit; record job ids in the stage report [L-16, L-17].
9. **Schedule.** Stage 1 (formats, paged directories) and the stage-2 unit search took Georgia Tech 600 of its first 900 minutes; budget a day for them,
   and four hand rounds for each of students and papers.

## Automation legend
**automated** = one command or a gate does it and a test covers it; **manual** = a person or agent decides (the tool prints what to review); **debt** = open (ROADMAP #52-#56).
`atlas stage-gate <key> --traps` runs every trap check of `tools/onboarding_traps.py` (charter completeness, collector restart, capture store, school-local
outputs, git-ignored reviewed files, additions vs acceptance, `sources_exhausted` reasons, stale gate files). Each stage's gate also runs its own.

## Running a stage: `atlas stage-gate` (ROADMAP #39)
`atlas new-school <key> --name "..."` makes stage 0's scaffolding. After that every stage is one command:
```
atlas stage-gate <key> <n> --run [--submit]    # the stage's mechanical steps, up to its first review step; then the gate
atlas stage-gate <key> [n ...]                 # only the gates (0-10), from the files the stages wrote
```
- `--run` runs the light steps here, queues the heavy ones as one Slurm chain (`--submit`: `afterok` dependencies from a code snapshot, `sbatch --test-only` first, refused on `Preempts:`; read the output files when the jobs end, or `atlas pipeline ... --wait`), skips a step whose output exists (`--force` re-runs), and stops at a failed step or at a **hand step**, printing what to review. Re-run the stage after the review: it continues and checks the gate.
- It refuses a released school, and a step that writes a shared file (home departments, the DBLP dump persons) needs `--allow-shared`.
- It writes `hierarchy/<key>/reports/stage-<n>-gate.json` (steps, result). The hand-written `STAGE-<n>.md` report stays yours.
- The step table is `STEPS` in `tools/stage_gate.py`; a stage's checks are its `g<n>` function. A rule learned in a stage becomes a check there (stage 4 refuses compact dates like `20261029`).
- An onboarding completeness exception is recorded in `hierarchy/<key>/reviewed/gate-exceptions.json` as
  `{"1": {"reason": "...", "by": "owner", "decided": "2026-11-07", "owner_quote": "...", "allow_items": ["CS 2016: never planned"]}}`.
  `allow_items` matches exact current finding strings; every unmatched finding keeps the gate failed. All findings
  remain visible in `items`/`open`, with `waived_items` and `unwaived_items` showing their scope. Completeness
  authorization never includes evidence, schema, identity, precision or stale-build failures. Legacy recorded
  exceptions of released schools retain their previous behavior when they have no `allow_items` field.

## Stage 0: charter and config
- **Do:**
  - **`atlas new-school <key> --name "University of X"`** (`tools/new_school.py`) does the next two bullets' scaffolding in one step: the charter from `TEMPLATE.toml`, `hierarchy/<key>/` (raw, reviewed, derived, work, reports, tmp), the store with an EMPTY `catalog.sqlite` of the standard schema (never a copy of another school's store), the folders a collector needs and a receipts row; it refuses an existing school and lists what the charter still lacks. Then fill the charter in.
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
    - `atlas sweep <key>` (`tools/sweep_school.py`): the OpenAlex institution sweep (`tools/oa_sweep.py`) and its sanity check
      (`tools/sweep_check.py`), for stages 2 and 7; `--daily` repeats it after each credit reset until the window is stored;
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
    - every host that disallows AI agents by name is marked `none`;
    - a host on the never-contact list (`school_hosts.NEVER_CONTACT`: dblp.org, www.dblp.org, dblp.uni-trier.de, orcid.org, pub.orcid.org, web.archive.org, web-static.archive.org) with `use = none` is recorded as `robots: not_fetched` without any request, not even robots.txt (R-HOST-01); DBLP data comes from the local dump only.
  - The charter is reviewed and committed.
- **Learned from Michigan (2026-10-29):**
  - **The host gate needs a probe fetch.** robots.txt allowing a host proves nothing about a Cloudflare challenge in front of it. At Michigan, every umich.edu host but one challenged a plain request. The charter's `[web].wayback_only_suffixes` makes a whole domain Wayback-only, and `school_config.host_use()` applies it.
  - **The OpenAlex lineage may not contain the school's medical centre.** Michigan Medicine is "related" to the university, not a child. List such ids as `openalex_related`: they are swept, and an authorship tagged only with them counts when its raw string matches the regex. This needs the owner's agreement once per school.
  - **Test the affiliation regex against DBLP notes as well as OpenAlex strings.** "University of Michigan – Shanghai Jiao Tong University Joint Institute" and "University of Michigan at Dearborn" matched the first regex.
  - **Check the shared OpenAlex key's credits before starting the sweep.** It had 492 left on 2026-10-29. `atlas sweep <key> --daily` reruns the sweep after each 00:00 UTC reset until it is complete.
- **Learned from Michigan (2026-10-30):**
  - **Bulk-pull sanity gate (owner standard).** After every OpenAlex sweep and every DBLP dump pull, run
    `tools/sweep_check.py <key>`. It is wired into `tools/sweep_school.py` (`atlas sweep <key>`), and `stage_gate.py` reads the result
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
    `hierarchy/dblp-dump-persons.json.gz` (`tools/dblp_dump_persons.py`) after the PI set changes, then its page counts
    `hierarchy/dblp-dump-pages.json.gz` (`tools/dblp_dump_pages.py`, R-PAP-27).

- **Learned from UChicago (2026-11-02):**
  - **Work in a worktree** (`tools/agent_worktree.sh new <school>`); `bin/atlas` there reads the worktree's own `schools/`. A raw
    `$CS_ATLAS_PY tools/x.py` run needs `export CS_ATLAS_SCHOOL_CONFIGS=$PWD/schools`. Tools write reports and reviewed inputs into the main
    checkout's data tree; `tools/sync_school_files.py <key>` copies what git admits into the worktree before a commit.
  - **Extend the OpenAlex snapshot for the new school (no API credits).** The filtered snapshot only holds the charters that existed when it
    was filtered. After the charter has its ids: `OA_DATE=<snapshot date> atlas pipeline snapshot-ext SCHOOLS=<key> --from-worktree --wait` (16 filter tasks, then the merge), or by hand: `OA_DATE=<snapshot date> OA_EXT=<key> atlas submit [--from-worktree] tools/oa_snapshot.slurm`, then
    the merge with `--dependency=afterok:<id>` (`tools/oa_snapshot_merge.slurm`, same `OA_EXT`). It writes `ext-<key>.sqlite` next to the main
    store, which is not touched; the reader consults it. About 25 minutes on 16 tasks. The next quarterly refresh folds the school in. Commit the
    charter first: the job runs a code snapshot of a commit (`--from-worktree` pins the worktree's, for unlanded onboarding code).
  - **Verify ids from the snapshot, not the API:** `atlas run tools/oa_institutions.py search <name> [--country US] [--type education]` and `lineage <id|key>` (not `python -I`: it imports its siblings) (children, associated
    institutions). **Read the children before deciding `openalex_excluded`.** UChicago's lineage holds Argonne National Laboratory and four of its
    facilities, Evanston Hospital and Chan Zuckerberg Biohub Chicago; a lineage sweep takes every one of them. Medical centres and affiliated
    institutes are 'related', not children. Verify the ROR id and its relationships at `api.ror.org/v2/organizations/<id>`.
  - **Crawl-delay counts for the groups that name Claude's agents** (`ClaudeBot`, `anthropic-ai`, ...), not only for `*`: `school_web` takes the
    maximum. A group that names them with only a Crawl-delay is allowed, at that delay.
  - **A moved department** shows in the host gate as `http 310 ->https://new.host/...`: put the new host in the charter and keep the old one's
    Wayback keys in the slots.
  - `atlas stage-gate <key> 0` checks the charter, `hosts.json` and the snapshot.

- **v3 (2026-11-05).**
  - *Automated:* `new-school` (charter, folders, empty store, checklist); `school_config --check`; `school_hosts` (robots incl. named AI agents, probe, 310 redirect naming the
    moved slots); `snapshot-ext`; the stage-0 gate (charter, hosts, snapshot, **charter traps**: affiliation cases, `[repository]`, `[dblp]`, `[thesis]`).
  - *Manual:* every lineage / related / excluded decision (needs the owner once per school), the affiliation regex cases, host `use`, the thesis `robots` value.
  - *Pitfalls:* a worktree charter is invisible to raw `$CS_ATLAS_PY` runs without `CS_ATLAS_SCHOOL_CONFIGS=$PWD/schools` [L-01]; `python -I` for download
    tools only, `atlas run` for the rest [L-07, L-19]; record job ids in `reports/STAGE-0.md` [L-17]; D-rules before the first sweep [L-06].
  - *Debt:* `new-school --like <released key>` and live URL probes (ROADMAP #54) [L-11].

## Stage 1: sources and captures
- **Current live supplements:** `tools/listing_rows.py <key>` also reads the optional reviewed input
  `hierarchy/<key>/reviewed/live-listing-sources.json`. Each `sources` entry names a charter `dept` and `slot`, a
  `format`, `complete` (a reviewed boolean), `expected_entries` (required when complete), and `pages`, a list of
  `{url, sha256}` receipts for HTTP-200 pages already saved in `school-captures.sqlite` by `school_web.live`.
  It verifies the raw hashes, actual stored fetch dates, parsed entry count, source quotes and every linked pager
  page. Relative person links resolve against their real source URL. Rows carry `source_kind: live`, the actual
  URL and observation date; a complete group covers only its observed year/half under a separate `live` coverage
  key. An incomplete group supplies sourced person rows with partial coverage. No historical years or archive
  captures are invented; this works when no archive plan database exists. A supplied optional `fetched_at` must
  match the stored value exactly. Commit the reviewed manifest before building from a code snapshot.
- **Do:**
  - Find each department's faculty listing URL eras. Use exact-URL Wayback CDX queries with `collapse=timestamp:4`. Prefix queries on a large host time out (503/504).
  - Write the eras into the charter as `[[departments.listings]]`. Entries that share a slot name are URL eras of one slot.
  - Capture one listing per slot and half-year, 2016–2026, with `listings/scripts/run_school.sh <key>`. `plan_fetch.py` takes a charter school's slots from the charter.
  - Parse the captures with `tools/listing_rows.py <key>`. It uses the formats in `tools/listing_formats.py`; add a format there when a page matches none. Contact lines are never kept.
- **Learned from UChicago (2026-11-02):**
  - `tools/discover_listings.py <key> <url>...` prints one line per URL (captures and the half-years that have one). To find URL eras, read the links
    in the 2016 homepage or people-page capture (`/directories/table/faculty` was found that way; guessing found nothing), then check each with it.
    `--offline --report <file>` checks saved exact-query CDX responses and sample bodies without network requests or cache writes, even during a
    host cooldown. `--report` records each requested sample separately. Exit 3 means evidence is pending (missing cache, failed request, empty body,
    or challenge), never that no capture exists. Only a successful empty index establishes an empty exact query. After a live failure the remaining
    URLs/samples are cache-only for that invocation. Exit 0 is completed **discovery**, not faculty-year acceptance or proof that a paged roster is complete.
  - A department site changes platform two or three times in ten years (UChicago CS: Drupal table, a `li.mix` list, WordPress cards). Write one
    format per era in `tools/listing_formats.py` (with a fixture test) and name it in the slot's `format`, before running `run_school.sh`.
  - After a parser fix, `listings/scripts/replan.py <key> <slot substring>` forgets the `unusable`/`nocapture` plan rows (captures stay), then rerun
    `run_school.sh <key>` and `tools/listing_rows.py <key>`. `listing_rows.py` prints `paged_listing` for a capture that is one page of a paged
    directory (it passes the 5-people usability rule but is partial): look for the other pages with `discover_listings.py` (`...?page=1`), else record the
    year as partial in the stage report (UChicago CS 2017: 5 of about 45 people; pages 2+ are archived only from 2019).
  - A department whose year has no archived listing at all passes the gate with a reviewed `listing_gaps = {2017 = "reason"}` in its charter table.
  - Listings that mix groups (Statistics' people page lists students and staff) are filtered in the format by the page's own group classes.
- **Learned from Georgia Tech (2026-11-03):**
  - **Write the formats before the captures.** Fetch one capture per era (`discover_listings.py <key> <url>... --sample 2016,2020,2024 --out <dir>` saves them and prints each one's format, entry count and paging), write the era's format in `tools/listing_formats.py` with a fixture test, then run `run_school.sh`.
    A first run with no format stores every capture as `unusable` and needs `replan.py` and a second pass.
  - **Paged directories are the common case, not the exception.** Georgia Tech's Drupal 7 pages show 9 people and its Drupal 9 pages 12 per page; `plan_fetch` takes one capture per half-year, so such a year
    **is fetched page by page since R3** (`plan_fetch.fetch_pages`: every `?page=N` of the same half-year, nearest in time, recorded in `plan_pages` and merged by `listing_rows`); only a page that is not
    archived in that half-year leaves a gap, which needs a reviewed `listing_gaps` entry. Check `is_paged` against the page's real pager markup.
  - **Truncated titles:** a card layout may cut long titles with an ellipsis, which loses the word "Professor"; count them (`…` in titles) before stage 2.
  - The stage's `captures` step is done when `plan_fetch.py <key> --check` passes.
  - Stages 0 and 2 never use the API sweep for a snapshot school: stage 0 ends with the `snapshot-ext` pipeline, and `atlas stage-gate <key> 2 --run --submit --from-worktree` queues the DBLP pass, the sweep from the extension, the sweep check and the OpenAlex candidates (= `atlas pipeline onboard-data`).
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

- **v3 (2026-11-05).**
  - *Automated:* `discover_listings.py` (`--sample` saves one capture per era), formats with `is_paged`, paged and A-Z page fetching (`plan_fetch.fetch_pages`),
    gzip bodies, `captures` step done = `plan_fetch.py --check`, a local step waits for queued steps, reviewed `listing_gaps`, `listing_rows` merging paged slots and
    counting `paged_listing`, the Wayback shared clock and 429 cooldown.
  - *Manual:* the page formats (one fixture test per era), `listing_gaps` reasons, the check that truncated titles ("...") are counted before stage 2.
  - *Pitfalls:* sample one capture per era and write the formats FIRST, otherwise every capture is `unusable` and a replan costs a second pass [L-25]; a department site
    changes template two or three times in ten years and pages its lists [L-24]; Wayback originals keep `:80` [L-24]; only one fetching stage runs at a time [L-28].

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

- **Re-run `census_build.py` at three points (UChicago 2026-11-03, friction 28, 34):** after `cs_related_school.py review` (the additions get their person records only then), after the stage-5 `dblp_ids_school.py` (it folds `dblp-ids.json` into the census), and after any change of the accepted candidates. Then `oa_identity_school.py` and `home_departments_school.py <key>` (school-local; `--write-shared` only when the owner says).
- **An onboarding school never writes a tracked shared file in the main checkout** (friction 30, 31): its census overrides are `hierarchy/<key>/reviewed/census-overrides-school.json` (`tools/census_overrides.py`) and its lab-page summary `derived/labpage-audit-summary-school.json`; both are committed on the school's branch. The release freeze refuses dirty tracked inputs.

- **v3 (2026-11-05).**
  - *Automated:* the `census-refresh` step, school-local `homes`, `units` (follows pages, letters and live pages, flags shells, writes `units-done.json`), the
    candidates rule from the snapshot extension and DBLP dump, the sweep check (also reading the school-local persons file), the share test, `rank_words`, `CLONE_OF`,
    the suffix-safe merge (#42), stage-2 gate (candidates file present, no `pending_openalex`).
  - *Manual:* the review decisions (`accepted`, `faculty_not_computing`, ...), `exclude` for faculty of other universities (a title like "Professor; University of X") [L-37], `[cs_related].not_faculty`.
  - *Pitfalls:* search every unit the OpenAlex candidates come from, and find each unit's list by reading its homepage links, not by guessing [L-33]; match names with middle
    initials and comma forms [L-34]; never re-run `candidates` + `review` on a census that already holds the additions unless the PI list is the census without additions [L-35];
    re-run `census_build` after the review, after `dblp-ids`, after accepted candidates change [L-36]; look for a row named "Clone of ..." or "Jr." merging title strings [L-38, L-39].

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
- When a directory title leaves a cross-school faculty member's home ambiguous, a reviewed school-local `census-overrides-school.json` entry may provide `home_department`, `home_department_evidence` (a list of URL, SHA-256 and verbatim-quote items), and `why_home_department`. `home_departments_school.py` applies that sourced decision after inference, keeps the former unit in `also`, and refuses evidence without all three fields. The stage-3 charter-home check still applies.

- **Stage 3 order (friction 26, 27, 29):** `census-refresh` -> `homes` -> `build` (pi_hierarchy: the lab-page audit reads `pis.json`) -> `labpage-discover` -> `labpage-audit`; submit with `atlas stage-gate <key> 3 --run --submit --from-worktree` while the charter is not on main.

- **v3 (2026-11-05).**
  - *Automated:* `census-refresh` -> `homes` -> `build` -> `labpage-discover` -> `labpage-audit` (stage-3 steps in that order), the stale-build check (a `pis.json` older than
    the reviewed inputs fails), `known_homes` (a home is a charter department, unit or `home_units` name; titles are not homes), `center_units`, the **shared-file and
    git-ignored trap checks** (no school section in a shared tracked file; no ignored reviewed file).
  - *Manual:* PI basis for research/teaching faculty, held homes, `skip_pages`-style judgements of department rosters.
  - *Pitfalls:* the builder runs at stage 3, before periods and identity, because the lab-page audit reads `pis.json` [L-44]; a background command must not start the next stage
    while a review is still being written [L-17, L-45]; the home department never comes from title text [L-46].

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

- **v3 (2026-11-05).**
  - *Automated:* `periods_school.py fetch` (incremental: only URLs without a stored page; reviewed `extra-lab-pages.json`, `person-urls.json`), `gaps`, `extend`, `truncated`,
    `deep --work-years`, `proven_years`, ISO dates, `homepage-dive` pipeline.
  - *Manual:* `unproven_years` + `why_unproven` for a gap searched and not closed (**debt**: the tool should write it, ROADMAP #55) [L-52]; a year-precision period from a live
    page for a new hire ("Fall 2026", R-PAP-02) [L-53]; `faculty_end_moved` readings.
  - *Pitfalls:* truncated titles hide span gaps [L-29]; a PI listed in one year with works in others never reaches `deep` without `--work-years` [L-51]; homepage fetching is hours, start it
    when the census exists; Wayback refuses concurrent fetchers [L-28, L-49].

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
  - Run `tools/dblp_dump_persons.py`, then `tools/dblp_dump_pages.py` (the page counts R-PAP-27 reads). They include onboarding schools.
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

- **A PI nothing identifies** (no DBLP id, ORCID or OpenAlex id after the DBLP, share-test and homepage/CV searches) gets `no_identity` + `why_no_identity` (with the evidence searched) in the overrides; the gate passes and no papers are attributed.

- **v3 (2026-11-05).**
  - *Automated:* `dblp_ids_school.py` (four rules), school-local `dblp_dump_persons.py` (default step, before the hand step), `oa_identity_candidates.py` (proposals; **read them before
    `--write`**), `oa_identity_school.py`, the `no_identity` pass, **the yield gate** (ROADMAP #43: a PI of the build with 0 verified works and 0 lab papers fails without a reason).
  - *Manual:* ambiguous OpenAlex ids (venues and years against the field), `no_identity` / `no_papers` reasons with the evidence searched, cross-school PIs carrying the same id.
  - *Pitfalls:* the shared persons file does not contain a new school: without the local file 64 of 138 UChicago labs had no papers [L-47]; a bare DBLP pid is not enough [L-55];
    first-given-name matches admit namesakes [L-56]; the OpenAlex identity matcher once flagged every candidate a namesake; read proposals first [L-88].

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
- **Student-recall gate (owner directive 2026-11-11, `tools/student_recall.py`).** The rounds above measure
  precision; recall is checked on a seeded, stratified sample of 30 PIs (recorded students 0 / 1-2 / 3+) drawn AFTER the last rebuild and bound to the sha256 of
  `students.json` and `pis.json`: `student_recall.py draw <key>`, then for each sampled PI `capture` its member-list page and fill the names actually listed
  (a fresh reviewer signs off), then `check <key>`. Items (thresholds are named constants in ONE place, `THRESHOLDS`): strict recall on readable PIs >= R1,
  unverifiable share <= U, PIs with no student and no researched reason <= Z, estimated whole-school current-PhD recall >= R2 (unverifiable counts as 0, so R2 <= (1-U) x R1). R1 .90, Z .05, X .20 are fixed; **U and R2 ratchet** (owner 2026-11-11): `RATCHET_LEVELS` in `tools/student_recall.py`, one constant `RATCHET_LEVEL` (now 0) that the owner raises: level 0 U <= .60, R2 >= .35; level 1 U <= .50, R2 >= .40; level 2 U <= .40, R2 >= .50; level 3 (target) U <= .30, R2 >= .60 (ceilings .36/.45/.54/.63). The gate message prints the current level, its bars and the next level's. A level change does not invalidate a record (only the bars move; `check` recomputes). All ten schools are gated, released ones included.
  Undated names outside a current-members section stay excluded (strict rule). `student_recall.py report <key>` prints the metrics for any school.
- **Per-PI coverage (owner directive 2026-11-12, `tools/pi_coverage.py`).** Every PI gets a ledger row (`pi_coverage.py report <key>`: CSV + JSON under scratch/pi-coverage-1112/ledger) and a state
  per dimension: **present** (students: >= 3 qualifying graduate-level rows for an active PI, >= 1 for one who left before 2025; lab papers: >= 3 and >= .5 per appointment year inside the appointment;
  links: >= 2 students with a student-paper link), **reason** (lab-coverage-reasons or census-overrides text that is individual, non-boilerplate and names >= 2 sources) or **gap**. Undated thesis-only or
  profile-only rows do not count (strict rule kept); an override text shared by >= 3 PIs is boilerplate, so the Han-name schools' shared `no_identity` holds are gaps, not reasons. Stage 5 (lab papers)
  and stage 6 (students, links) gain one item per dimension whose gap share exceeds the bar; the bars are `RATCHET_LEVELS` in `tools/pi_coverage.py`, one constant `RATCHET_LEVEL` (now 0 = report-only,
  no school fails; level 3 is the target). `pi_coverage.py gaps <key>` lists the gap PIs by what would unlock them; `summary` prints the counts and each level's verdict. The recall gate is untouched.

- **v3 (2026-11-05).**
  - *Automated:* sources in order (thesis list with advisers, rosters, lab pages, directories, CVs), `adviser_directories`, `is_department_roster`, `in_own_space`, `visiting` role,
    `lab_coverage.py` + `lab_coverage_reasons.py`, `student_audit.py` school-local, **traps at the gate:** school-local outputs, ignored reviewed files, `labpage-additions.json` not
    shrunk below the acceptance (R13), `sources_exhausted` reasons backed by 2+ sources and boilerplate on at most 25% of PIs.
  - *Manual:* the hand rounds (20 students, 20 papers; at most 1 / 2 / 1 errors; four rounds a kind, three failures stop the work), roster-rule pilots, per-PI decisions with evidence, the researched pass for labs left `open`.
  - *Pitfalls:* **draw a 100-row sample before round 1 and batch rule fixes**; each round of 20 finds only the next 3-5 idioms [L-62]; pilot a roster rule on 20 rows [L-63]; look at new rows by PI before
    counting a jump in labs with students [L-62, L-88]; a department's people page is not a lab page [L-64]; check the PI's first listing year before calling a page "pre-joining" [L-63];
    **never run `labpage_audit audit` after wiring without the R13 filter**, and commit the additions in the same commit as the acceptance that stamps them (restamp after any regeneration) [L-60, L-61];
    estimate records x crawl delay before crawling a thesis repository; sitemaps arrive truncated; `/items/*/full` and `/entities/*/full` are disallowed [L-66]; a repository that disallows AI agents is
    not used in any form [L-67]; Math Genealogy, OpenReview and CORE are not available [L-68]; the owner rejects `sources_exhausted` without real search effort [L-69].
  - *Debt:* acceptance keyed on the accepted rows, `restamp` refusing a shrink, round counter (ROADMAP #52) [L-61].

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

- **v3 (2026-11-05).**
  - *Automated:* `labpage_audit recover` + `audit` (snapshot title lookup first), `link_diagnosis` (idempotent; in-process chain audit), `atlas pipeline build-audit` / `link-diagnosis`,
    the zero-paper and yield checks on the rebuilt outputs, the stale-gate trap (`stage-gate <key> <n> --record`).
  - *Manual:* the hand rounds for papers, zero-paper reasons, link diagnosis review.
  - *Pitfalls:* order is recover -> hand round -> accept -> build -> audit -> restamp -> link diagnosis -> student audit [L-70, L-71]; `build` reruns only with `--force` (or when `pis.json` is deleted) [L-70];
    a recorded gate is not the truth: compare its time with the newest reviewed file before diagnosing a rule problem [L-71, L-83]; the lab-page additions must not shrink after wiring [L-60].
  - *Debt:* `build-audit` ending with the diagnosis and the student audit, naming a failed stage's log (ROADMAP #53) [L-74].

## Stage 8: full texts
- **Do:**
  - Create the store catalog (stage 0), then add the lab papers (`fulltext-push/add_works.py`).
  - Run the channels (`run_steps.sh <key> oa_arxiv openalex proceedings arxiv_title dblp_ee s2 europepmc pmc figshare labpages <school repository>`).
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
  - copies are measured. The 85% of lab papers is a **target, not a gate** (v3: reported as `copy_target_met`).
  - every non-local lab paper has a ledger entry, and `incomplete_check` is at most the whitelisted threshold
    (`docs/evidence-whitelist.json`; the evidence check's categories `unavailable_missing`, `unavailable_stale` and
    `unavailable_incomplete`).

- **v3 (2026-11-05).**
  - *Automated:* `school-collector.slurm` (SCHOOL=<key>; channels from `[collector].channels`; restarts itself with `--signal=B:USR1@900` + `loop_job.sh`), `lab_paper_copies.py`, `unavailable_ledger.py`
    (repository name and pattern from `[repository]`; reads `labpage-captures.sqlite` or the audit's `labpage-audit-captures.sqlite`), the release ledger offline for onboarding schools, **traps at the gate:**
    collector scripts restart, a capture store exists.
  - *Manual:* the access-review of `needs_access_review` copies, whitelist entries for `incomplete_check` while CORE is paused.
  - *Pitfalls:* compute nodes lack `/usr/local/anaconda3` (use `CS_ATLAS_PY`) [L-58]; a collector without `loop_job` ends at its limit and stays down [L-78]; after `scancel` a catalog may have a hot journal: open it once for
    writing, never delete it (`docs/RUNBOOK.md`) [L-79]; the ledger step needs a 59-minute slice only.
  - **The 85% copy share is a target, not a gate** (owner 2026-11-05; Georgia Tech reached 42.1% against a ceiling of 53.3%): `stage_gate.g8` reports `copy_target_met` and fails only on unmeasured copies or a missing ledger [L-80].

## Stage 9: accuracy
- **Do:** run the hand-checked sample (`accuracy/sample.py`, 105 judgments per school).
- **Gate:** lab-paper precision ≥ 0.95, student-link precision ≥ 0.97, and lab-paper coverage ≥ 0.90. Below a threshold, add a general rule with a test, never a one-off fix.

- **v3 (2026-11-05).**
  - *Automated:* `accuracy/sample.py` (reads the school-local DBLP persons file; `oalookup.aff()` falls back to the charter regex), the g9 check that the build has not changed since the draw.
  - *Manual:* the 105 judgments (or 50-row spot check), the rule for any failing measure (a general rule with a test, R-PAP-31 style).
  - *Pitfalls:* **the draw binds the build and `copies.json`**; draw once, after the last rebuild, or redo it (Georgia Tech needed draw 2) [L-81]; the 50-row spot-checks are the FIRST go/no-go gate after the rebuild, before
    freeze, export and site steps (owner 2026-11-05) [L-85].

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

**Applied 2026-10-31** (ROADMAP item 5, `docs/SCRIPT-MAP.md`): `hierarchy/organize-tree.slurm` defaults to `$CS_ATLAS_SCHOOLS`;
the one-school runners (`hierarchy/michigan/run_sweep.sh`, `sweep_daily.sh`, `hierarchy/run_stanford_sweep.sh`) are
`tools/sweep_school.py <key>`; the one-off research tools of the six pre-protocol schools and their census builders are in
`archive/`, and nothing the build, the collectors or the stage tools run reads them.

**Still by hand:** each is debt.
- `fulltext-push/downloads.slurm` (`SCHOOLS=(...)`) and the one-off collector scripts: `addworks-1029.slurm`, `newsteps.slurm`, `oa_editions.slurm`, `retry_transient.slurm`, `chain_*.sh` and `local-reuse/lr_common.py`.
- The per-school catalog builders (`fulltext-push/berkeley_catalog.py`, `stanford_catalog.py`). A protocol school should use one generic builder with the school key.
- `tools/faculty_periods.py`: `STAGES` and `SCHOOL`, for the pre-protocol schools. Protocol schools use `tools/periods_school.py`.
- The site builder's `SCHOOLS`, `FULL_CODES` and `CORE` tables (Codex's checkout).
- `ai-writing/*` school tuples. They are the study's scope, and the owner decides whether a new school enters it.

## Stage 10 additions (v3)
- **Refresh before release.** Sweeps and captures end before the release date (new hires and 2026 preprints: Qi, Tomlin): run the 2026 refresh (ROADMAP #51 trickle, or the stage-7 title lookup) before the spot-checks [L-84].
- **Release-time gates.** The zero-paper and yield checks run on the REBUILT outputs; every `reviewed/` file of the school is committed and landed first (the freeze refuses dirty tracked inputs) [L-75, L-86];
  the release ledger runs offline for onboarding schools, so run the stage-8 network ledger before [L-76].

## Reviewed files and the overlay root (ROADMAP #44, v3)
**Problem.** `atlas_paths.data()` resolves `hierarchy/<school>/reviewed/...` (and `reports/`) under `CS_ATLAS_CODE`, the MAIN checkout. A worktree build or a Slurm snapshot therefore
reads main's copy of the reviewed files, and every writer (`labpage_audit record|audit`, `oa_identity_school`, `cs_related_school review`, `lab_coverage_reasons`, census overrides) writes
there; main shows them modified until the branch lands, and a branch edit is invisible to a build [L-21].
**Rules while #44 is open.**
1. After every reviewed-file write: `tools/sync_school_files.py <key>` (copies what git admits into the worktree, keeps newer worktree files), then commit in the worktree. Land at each gate.
2. Never `git add` or edit tracked files inside the main checkout; check `git -C <main> status --short` after each stage while a release runs. A dirty tracked file for the school is restored from the branch, not committed from main.
3. When a build or audit must read the BRANCH's reviewed files (the acceptance, the additions, student decisions), run it in an overlay code root:
   ```
   tools/overlay_root.py <key> --out hierarchy/<key>/tmp/overlay       # tmp/ is git-ignored; rebuilt each time
   CS_ATLAS_CODE=$PWD/hierarchy/<key>/tmp/overlay bin/atlas build-audit <key>    # or any other command
   ```
   The overlay is a directory of symlinks: code (`tools`, `atlas_cli`, `bin`, `schools`, `tests`, `vendor`, `docs`, `accuracy`) from the worktree; `hierarchy/<key>/reviewed`, `hierarchy/<key>/reports` and the
   shared `hierarchy/reviewed/` (census-overrides.json, home-departments.json, ...) per file, the worktree's tracked file where the branch has one and main's otherwise (a writer's output lands in the
   worktree, ready to commit; a branch's census override is no longer dropped); `hierarchy/<key>/work` is a real directory of the overlay, empty at first: `atlas_paths.data()` resolves work files into it,
   and `data_w()` copies main's file in when the file is first written (so a resumable `dblp-recover.sqlite` continues, and main's copy is never written; overlay root marker `.overlay.json`). Work files
   the overlay has not written yet read as absent through `data()`. `derived`, `raw`, `tmp` and every other entry come from main. Without an overlay nothing changes.
   **Builders and fetchers write `derived`, `raw` and `listings/<school>`: build the overlay with `--private`** (real copies; a rebuild of the overlay preserves them, never deletes them; `overlay_root.py <school> --out <dir> --verify` fails when main's school derived files differ from the sha256 receipt taken at overlay build). Without `--private` those paths are symlinks into main and a builder run overwrote main's Harvard derived files on 2026-11-09. Run it from the worktree; `CS_ATLAS_CODE` must be absolute. A tracked file the branch has not committed yet is main's copy: commit first.
4. Slurm: `atlas submit --from-worktree` pins the committed HEAD but data paths still resolve against main; a job that needs branch-only reviewed files needs the overlay path in its environment (the pipeline stages inherit `CS_ATLAS_CODE`).
**Why not fixed in code on this branch.** The conversion has to route the explicit-root call sites (`HERE = P.WORK` in `pihier/common.py`, `pi_hierarchy`, `labpage_audit`, 20-odd modules) through one resolver and
split `reviewed` from `derived` under one `root`; a half-converted tree reads reviewed files from one checkout and the packages from another, and the release was running. It is ROADMAP #44 (and #56 for the resolver design).

## Running three schools in parallel (Harvard, Johns Hopkins, WashU)
**Per school (never shared):** one worktree and branch (`tools/agent_worktree.sh new harvard`, `jhu`, `washu`; keys are lower-case letters and digits), one charter, one `hierarchy/<key>/`, one store `stores/<key>`,
one `listings/<key>`, one collector job (`school-collector.slurm SCHOOL=<key>`), one driver session, one `STAGE-<n>.md` and `PROTOCOL-FRICTION.md` per school, one `reviewed/` set, one OpenAlex snapshot extension (`ext-<key>.sqlite`).
**Shared (take turns, never write twice):**
| Resource | Rule |
|---|---|
| OpenAlex key (10k credits a day) | snapshot extension first (no credits); API only for named checks; one agent at a time on credits, record the spend in the stage report |
| Wayback (shared 5 s clock, 429 cooldown) | one fetching stage at a time ACROSS the three schools; stagger stage 1 and 4 fetch jobs; every client uses `host_throttle` |
| Slurm | partition `all`, account `mltheory`, jobs of 59 minutes or less, `--exclude=node302,node014`, `sbatch --test-only` first; never submit on `Preempts:`; no polling (`slurm_wait.py` in the background) |
| Shared tracked files (`hierarchy/reviewed/census-overrides.json`, `home-departments.json`, the audit summary, `student-audit.json`, `.gitignore`, `schools/TEMPLATE.toml`, `tools/`) | an onboarding school writes only school-local files; a change to a shared tool or file is its own commit on its own `fix/` branch landed by the coordinator, then the other branches rebase |
| `DBLP dump persons`, `paths.sh`, `atlas_paths.SCHOOL_IDS` | not touched before stage 10; the school-local persons file stands in |
| The release | landing is frozen while a release runs; branches wait; reviewed files stay in the worktree |
**Landing at gates.** Each school lands when a stage gate passes: `bin/atlas test` (exit code), lint, `tools/secret_scan.py --staged`, `git rebase main`, then the coordinator fast-forwards. Charter first (stage 0) so jobs can run from main;
code fixes that all three need land as soon as they pass (they change nothing for released schools); the school's reviewed files land with the gate commit. Rebase the other two branches after every landing, and re-run
`atlas stage-gate <key> --traps` there. Three drivers, one coordinator: the coordinator owns landings, the OpenAlex budget and the Wayback turn order; the drivers own their schools.
**Claims.** Each school is a task on the shared queue (`bin/atlas task list`, `claim`, `heartbeat`, `done --commit`; docs/CONTRIBUTING.md). Claim before stage 0; a second driver for the same school is refused.
**Order of work.** Stages 0 (together, the owner D-decisions batched in one message), then stages 1-2 staggered by one day, stage 6 rounds and stage 8 collectors are the long poles; stage 9 draws after the last rebuild.

## Before you land (v3)
`bin/atlas test` (read its EXIT CODE, not the last line; a subset is not enough: tests leave other checkouts' tool modules in `sys.modules`), `bin/atlas lint`, `bin/atlas charters`, `tools/secret_scan.py --staged`,
then `atlas stage-gate <key> --traps` for the school. Stage explicit paths. Commit messages end with the Co-Authored-By line. Never push [L-87].

## Stage reports
After each stage, write `hierarchy/<key>/STAGE-<n>.md`: what was done, the counts, the gate result, and every exception with its reason. These reports are how a school's onboarding is reviewed.
