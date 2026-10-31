# Lab pages: the audit standard

Owner request (2026-10-30), verbatim:

> make sure we're scraping every lab page for every student + paper on the lab page:
> (1) every lab has a lab page
> (2) document reason if can't find any lab page
> (3) for every lab page we have all students (and alumni of lab)
> (4) document reason if not
> (5) every lab paper listed on the lab page
> (6) document reason if not — do this for all the universities

A **lab** is a PI (`hierarchy/<school>/pis.json`) and their advisees (R-HIER-01). Its **lab page** is the lab's own site
(people and publications pages), or, when there is none, the PI's own homepage, which is then audited as the lab page.
The tool is `tools/labpage_audit.py`; it runs on Slurm with `hierarchy/labpage-audit.slurm`.

## Outputs

| file | what |
|---|---|
| `hierarchy/<school>/labpage-audit.jsonl.gz` | one record per PI lab: `lab_page`, `students`, `papers` (schema below) |
| `hierarchy/<school>/labpage-additions.json` | proposed students and papers, each with url, sha256, verbatim quote and the admitting rule; **not read by the build** |
| `hierarchy/<school>/labpage-audit-discovery.jsonl` | every place checked per lab, with date and result (append-only; the latest line per PI counts) |
| `hierarchy/<school>/labpage-audit-captures.sqlite` | the pages fetched by the audit (lpcap schema: url, capture_url, fetched_at, status, sha256, bytes) |
| `hierarchy/<school>/labpage-audit-recover/` | the private copy of `tools/labpage_recover.py`'s store: every listed paper's resolution and verdict |
| `hierarchy/labpage-audit-summary.json`, `hierarchy/LABPAGE-AUDIT.md` | the per-school summary and its table |

## Method

1. **Discover** (network). For every PI lab:
   - the 2026-10-22 lab-page pass's record (`labpage-evidence.json`) and its dossier of pages fetched;
   - the department listing (the PI's latest listing URLs in `pis.json`), the PI's **school profile** found on it by
     anchor name (or named in the PI's period evidence), and the profile's website / lab / group links;
   - the **DBLP** person's homepage URLs (the local dump extract `hierarchy/dblp-dump-persons.json.gz`; dblp.org itself is
     never fetched), the PI's **ORCID** researcher URLs (`orcid.org/<id>/person.json`; `pub.orcid.org` disallows all
     crawling in robots.txt), and **OpenAlex** (recorded as `no_homepage_field_in_schema`: author records carry no homepage);
   - earlier homepage finds (`fulltext-push/raw/pi-homepages-<school>.json`) and the PI's own evidence URLs;
   - each candidate site (live, else the newest Wayback `id_` capture): it must name the PI; a profile page is never a
     site; a site at another institution is never this school's lab page;
   - on the chosen site, its people / members, alumni and publications links (same site; on a department host only under
     the PI's own path), and up to three Wayback `id_` captures (first, middle, last; 2016-2026, from the PI's first year at
     the school) of each people and alumni page;
   - for labs the 2026-10-22 pass recorded: only other candidate sites (a missed lab site), and the alumni and publications
     links on the stored lab and people pages that pass never read.
2. **Recover** (network; OpenAlex stops at 6,000 credits left for the day (the shared key allows 10,000 a day; the downloads agent uses the rest):
   queue the step after the UTC reset with `sbatch --begin` rather than skipping it). Every listed 2016-2026 paper that is not a lab paper goes through `tools/labpage_recover.run` in
   the private shadow tree: its parse (talks, patents, theses, headings), its resolution (school sweep, the PI's works,
   arXiv, proceedings, OpenAlex DOI and title search) and the build's own rule (PI on the byline, appointment R-PAP-01,
   school authorship or page 1 R-PAP-10).
3. **Audit** (offline). Students: every name the member extractor (`autom.extract`) finds on the people and alumni pages and
   their captures, with the disposition the lab-page rules give it, grouped by person within the lab (R-HIER-03; a
   one-transposition misspelling of the same first name joins), matched against the lab's students in the build
   (`names.match`: nicknames, initials, accents, compound and swapped names). Papers: every entry the publication
   extractor (`pubx.extract`, with the 2026-10-22 reviewer's per-page spec) finds, matched against the lab's papers and
   their editions by DOI, then arXiv id, then normalized title (the coverage counter's rule), then a 30+ character title
   inside the citation or a 30+ character prefix (the recovery's held test).

**Fetching** (all steps): robots.txt is honoured, including groups that name ClaudeBot, anthropic-ai, Claude-Web,
Claude-User or Claude-SearchBot; at least 3 s between requests to one host (Wayback 6 s); a bot challenge is stored and
never retried, and the host is then read only from existing Wayback `id_` captures; dblp.org, Google Scholar and
eScholarship are never fetched; no e-mail address is sent. Michigan is audited read-only from its own lab-page outputs
(the owner's never-used sources: Deep Blue, news.umich.edu, record.umich.edu).

## Record schema (`labpage-audit.jsonl.gz`)

```
{school, pi, labId, departments, audited_at,
 lab_page: {status: found|none_found|not_applicable, urls: {lab_site, people_page, alumni_page, pubs_page},
            evidence: {url, capture_url?, sha256, quote}, title, reason_code, reason, source,
            checks: [{source, url, at, result, ...}], discovery_run, prior_record},
 students: {page_status, pages, listed_current: [{name, role, years}], listed_alumni: [...], matched_in_build,
            missing_from_build: [{name, role, years, quote, url, sha256, section?, detail?, reason_code}],
            extra_in_build_not_on_page, reason_code, reason},
 papers:   {pubs_page_status, pages: [{url, capture_url, sha256, entries, spec}], listed, in_window_2016_2026,
            matched_in_lab_papers, matched_outside_window,
            missing: [{title, year, venue, url, sha256, quote?, detail?, reason_code}], reason_code, reason}}
```

## Reason vocabularies

### Lab pages (`lab_page.reason_code`)

| code | status | meaning |
|---|---|---|
| `lab_site` | found | a lab or group site exists and was audited |
| `pi_homepage_only_no_lab_site` | none_found | no lab site; the PI's homepage is the lab page and its students and papers were audited |
| `profile_only_no_homepage` | none_found | only the department profile exists; nothing links a homepage or lab site |
| `no_web_presence_found` | none_found | no homepage or lab site at any source checked |
| `site_dead_no_wayback` | none_found | the known site no longer answers and Wayback holds no capture |
| `host_blocked_by_robots` | none_found | robots.txt disallows the site (for our agent or AI agents by name) and Wayback holds no capture |
| `host_challenge_no_wayback` | none_found | the host serves a bot challenge and Wayback holds no capture |
| `pi_left_school_site_moved` | none_found | the PI left; the only site found is at the new institution |
| `site_at_other_institution` | none_found | the only site found is at another institution (joint or previous appointment) |
| `new_arrival_no_site_yet` | none_found | joined in 2025 or later; no school lab site yet |
| `emeritus_or_admin_no_lab` | none_found | emeritus or administrative appointment, no lab site |

Classification: a page is a **lab site** when its title names a lab, laboratory, group, team or centre, or its host is a
lab/group host, or its people page is a separate members page; otherwise it is the PI's homepage.

### Students (`students.page_status`, `missing_from_build[].reason_code`)

`page_status`: `audited`, `no_people_section` (the page lists no members), `no_lab_page`, `page_not_captured`.

| code | meaning |
|---|---|
| `genuinely_missing` | a listed member placeable in 2016-2026 at this school who is not in the build: **a gap, proposed as an addition** |
| `evidence_not_in_build` | in `labpage-evidence.json` but in no student record of the lab: a build-side loss to check |
| `dropped_by_review` | removed by `hierarchy/student-corrections.json` |
| `at_previous_school` | stated years end before the PI's appointment here, or a PhD finished within 4 years of the PI's arrival (begun before it) |
| `outside_2016_2026` | stated years end before 2016 |
| `undated_alumni_cannot_place` | an undated alumni entry, never seen as current on a 2016+ capture, of a lab older than the window |
| `undated_cannot_place` | the page lists every era without dates and the reviewer required dates |
| `not_in_people_section` | on an archived capture (or an automatic plan's page) outside any people heading |
| `reviewer_excluded` | the 2026-10-22 reviewer excluded the name or its section (non-person, collaborator, other lab) |
| `not_a_student` | a faculty / collaborator / staff section, another PI of the school, a co-adviser ('joint with'), a rotation student |
| `name_unresolved` | a fragment, a first name only, a site credit or footer, or a quote that fails the verbatim check |

**Strict rules** (labs discovered by the audit, and the re-parse of labs another school's pass recorded): a name counts
only under a member section (students, PhD, postdocs, alumni, members, team, people ...; on a homepage used as the people
page only students / PhD / postdocs / advisees / alumni / group sections), never under committee, publications, theses,
talks, courses, collaborators, press or service headings, never in a byline or citation (the PI's family name or a venue in
the entry's text), never a site credit, a co-adviser ('joint with'), a rotation or high-school student, an initial-only or
implausible name; the section heading's role outranks a bio's degree words; a stated start year before the PI's arrival
(PI from 2010 on) is `at_previous_school`; and in a lab the school's own pass reviewed, an undated name the pass did not keep
counts only when marked current ('current' heading, 'Nth-year', 'candidate').

The build admits every lab-page row with a quote and hash whatever its role (R-STU-01), so postdocs, undergraduates,
visitors and staff listed on a lab page are lab members here too; their role is kept.

### Papers (`papers.pubs_page_status`, `missing[].reason_code`)

`pubs_page_status`: `audited`, `no_pubs_page`, `external_index_only` (the site points to DBLP / Scholar instead of a
list), `no_lab_page`, `page_not_captured`, `page_unparseable`.

| code | meaning |
|---|---|
| `genuinely_missing` | resolves to a work that passes the build rule but is not a lab paper: **proposed as an addition** |
| `pi_not_author` | the resolved work's byline lacks the PI (a student-only paper: the lab-paper rule needs the PI as author) |
| `from_previous_school` | dated before the PI's appointment here (R-PAP-01) |
| `outside_appointment` | outside the PI's reviewed periods and listed years here (R-PAP-01) |
| `other_institution_affiliation` | the PI's authorship lists only other institutions |
| `no_school_affiliation_evidence` | the PI's authorship lists no institution and page 1 does not tie the school to the PI |
| `unresolved_metadata` | no OpenAlex, arXiv or proceedings record matches the listed title |
| `not_a_paper` | a talk, patent, thesis, award, service or news line |
| `parse_artifact` | a heading, venue-only or author-only line, or a fragment |
| `outside_window` | listed outside 2016-2026 |
| `undated_entry` | no year shown, and no lab paper matches |
| `not_yet_resolved` | the recovery step has not judged it yet (a pass condition failure) |

## Additions and their rules

`hierarchy/<school>/labpage-additions.json`: `{school, generated_at, rules, students: [...], papers: [...]}`.

- **LP-STU-01** (students): a person listed on the PI's own lab page (people, members or alumni section; the live page or
  a Wayback `id_` capture), under a people heading, not the PI, not in a faculty / collaborator / staff section, not another
  PI of the school, not a co-adviser, whose stated years do not end before 2016 or before the PI's appointment here, and who
  is dated or listed as current on a 2016+ capture (undated alumni only when the lab has only ever been at this school), is
  a lab member. This is the admission the 2026-10-22 rows already had (R-STU-01 researched advisees). Each row has the
  `labpage-evidence.json` row shape (`name, role, years, url, capture_url, sha256, quote, note`) plus `pi`, `alumni`,
  `rule`, and `auto: true`.
- **LP-PAP-01** (papers): a paper listed on the PI's own publications page whose resolved work carries the PI on the
  byline, falls in the appointment (R-PAP-01) and whose PI authorship lists the school (or page 1 ties the school to the
  PI) is a lab paper with identity `labpage_listing` (R-PAP-04). Each row has the `labpage-recovered.jsonl.gz` row shape
  (`pi, key, title, year, doi, venue, byline, arxiv, evidence`).

**Integration (to apply in the next full rebuild, not by the audit):**

- students: in `tools/pi_hierarchy.py`, where the researched-students files are read (the loop over
  `('few-students-evidence.json', 'thesis-evidence.json', 'labpage-evidence.json', 'thesis-held-years-evidence.json')`),
  also read `labpage-additions.json` and append each `students[]` row to `fe[row['pi']]['students']`; the rows already carry
  `auto: true`, which that loop keeps on the relation.
- papers: in the loop over `(('dblp', 'dblp_person_page'), ('labpage', 'labpage_listing'))`, for `kind == 'labpage'` also
  iterate `labpage-additions.json` `papers[]` (same schema), after `labpage-recovered.jsonl.gz`, so the `seen` check keeps
  one row per work.

## Acceptance bar for wiring additions (owner's coordinator, 2026-10-31)

1. A school's `labpage-additions.json` is wired into the build only when a fresh random hand check of 20 proposed students
   has at most 1 membership error and at most 2 role/year errors, and 20 proposed papers have at most 1 error. A doubtful
   item counts as half an error; a paper whose metadata is wrong (a title with a byline) counts as an error.
2. A school that fails gets its rule fixed, is re-run, and is re-sampled with a NEW random 20 (a new seed). The same sample
   is never re-checked after a fix: that measures the fix, not the rate.
3. After any rule change, 10 students are re-sampled at every school already accepted.
4. Every round, failed ones included, is recorded in `hierarchy/<school>/labpage-handcheck.json` (`rounds`: date, seed,
   sample sizes, errors by type, the items, the result) and in the hand-check table of `hierarchy/LABPAGE-AUDIT.md`. The
   accepted round is written to `hierarchy/<school>/labpage-acceptance.json` (the round, the additions file's
   `generated_at` and sha256, the counts), which is checked before wiring.
5. After 3 failed rounds at a school the work stops and the error patterns are reported, rather than patched further.

Roles and years in additions are only what the entry states: `role` / `years` are null with `role_basis` / `years_basis`
`none` when the entry does not state them (`entry_role`, `entry_years`); the build keeps undated students.

## Pass condition (per school)

1. Every PI in `pis.json` has a `lab_page` record with a status, a reason code from the vocabulary and at least one dated check.
2. Every lab whose page is found, or whose homepage is the lab page, has its `students` and `papers` sections audited
   (`page_status` / `pubs_page_status` not missing), or a section-level reason from the vocabulary.
3. No paper is `not_yet_resolved`, and no student is `evidence_not_in_build` without a note.
4. `genuinely_missing` students and papers are each at most the whitelisted share (`docs/evidence-whitelist.json`,
   key `labpage_genuinely_missing`; 0 once the additions are wired), and every one of them is in `labpage-additions.json`.
5. A hand check of at least 20 random proposed additions per school (both kinds) is recorded in the school's report with its
   error count; additions do not go into the build before it.

## Per-school adapters

| school | adapter | status |
|---|---|---|
| princeton, mit | the reviewed plan modules (`plan_<school>.py`: people pages, Wayback history, reviewer drops, per-page publication specs), re-run through `lpauto`'s own rules with every disposition kept | princeton audited 2026-10-30 |
| cmu | `adapter_plan`: `labpage-evidence.json` `people_pages` (live and Wayback) and `pubs_pages`; strict re-parse | |
| epfl, berkeley | `adapter_plan`: `labpage-evidence.json` pages, publications pages from `labpage-pubs.jsonl.gz`, reviewer overrides in `labpage-tools-epfl-berkeley/manual_pages.json` | |
| stanford | no evidence file: `labpage-tools-stanford/decisions.json` pages seed the discovery of every lab | |
| michigan | `adapter_plan` over the Michigan pass's `labpage-evidence.json`; discovery for every other lab under the charter's host policy (`schools/michigan.toml`: Deep Blue, news.umich.edu, record.umich.edu never used, Wayback included; umich.edu hosts read only from Wayback `id_` captures) | |

Every school's charter host policy is applied to every fetch (`school_config.host_use`: `none` is refused, live or
Wayback; `wayback-only` is read from Wayback `id_` captures only). When `pubx` finds no entries on a publications page the
school's earlier parse of that page (`labpage-pubs.jsonl.gz` rows) stands in, flagged `from_prior_parse`.
