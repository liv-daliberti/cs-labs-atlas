# Schema

All tables are UTF-8 JSON Lines, gzip-compressed (`*.jsonl.gz`), one record per line, rows sorted by their id. A table
that would exceed ~45 MB compressed is written as a directory of shards `<table>/<university_id>.jsonl.gz` instead (none
does in this release). Missing values are `null`; lists are `[]` when empty. Years are integers; dates are ISO strings
(`YYYY`, `YYYY-MM` or `YYYY-MM-DD`, as precise as the source).

**Evidence object.** Wherever a claim is sourced, it carries one or more evidence objects:

| field | meaning |
|---|---|
| `url` | the page the claim was read from (often a Wayback `id_` capture URL, which pins the exact archived bytes) |
| `final_url` | the URL after redirects, when different |
| `sha256` | SHA-256 of the captured page bytes (the captures themselves are not distributed; re-fetch the URL to compare) |
| `quote` | a verbatim excerpt of the page (whitespace collapsed) that states the claim; contact details replaced by `[email removed]`, `[phone removed]`, `[address removed]` |
| `kind` | the kind of source (e.g. `dept_listing:Computer Science`, `wayback_csd_faculty_directory`, `pi_basis:advises_phd`) |
| `observed` | when the page was observed or dated (`YYYY-MM-DD`) |
| `note` | how the quote was represented, when stated |

Not every evidence object has every field; older collection records may have only `url`.

---

## data/schools/&lt;school&gt;/

Schools: `princeton`, `cmu`, `epfl`, `mit`, `berkeley` (and any later school, e.g. `stanford`).

### pis.jsonl.gz — one row per PI lab

| field | meaning |
|---|---|
| `pi_id` | stable id `<school>:<name slug>` (e.g. `princeton:jennifer-rexford`) |
| `school` | school id |
| `name` | the PI's name as the census records it |
| `name_forms` | every name form used for matching (aliases, merged census rows, collection names) |
| `merged_census_rows` | other census rows found to be the same person (same DBLP id, collection person or nickname-equal name) |
| `department` | the department the site places the PI in (site rule; see METHODS) |
| `department_coverage` | `full` (a computing department covered in full) or `affiliated` (another department, covered through its CS-related PIs) |
| `departments_as_listed` | departments / codes as the census sources list them (e.g. `CSD`, `MLD`, `EECS`, `STI/IEM`) |
| `home_department_review` | the reviewed home department for PIs a computing department lists but who are homed elsewhere: `home_department`, `also`, `no_academic_department`, `evidence`, `note`; else `null` |
| `scope` | `core_computing_department` or `cs_related_addition` (added by the CS-related-scope review, any department) |
| `rank` | normalized rank (`ladder`, `research`, `emeritus`, `adjunct`, `full_professor`, … — vocabulary differs per school) |
| `title` | title as listed |
| `identifiers.dblp` | DBLP person page URLs |
| `identifiers.dblp_basis` | why a DBLP id without a census source was accepted (unique exact-name DBLP person), else `null` |
| `identifiers.dblp_dropped` | census DBLP ids rejected because that DBLP person never carries the PI's name |
| `identifiers.openalex_reviewed` | OpenAlex author ids confirmed by review |
| `identifiers.openalex_anchored` | OpenAlex author ids that sit at the PI's name on identity-anchored works, most frequent first |
| `identifiers.openalex_not_this_person` | reviewed namesake author ids that are never this PI |
| `identifiers.orcid` | ORCID iDs |
| `identifiers.collection_person_ids` | ids of the PI in the project's earlier per-school people collection |
| `pi_basis` | why this person is a PI: `kind` (`advises_phd`, `advises_phd_or_postdoc`, `lab_head`, `own_group`, `named_lab`, `named_group`, `sole_unit_leader`, `listed_faculty_missing_from_census`, `owner_own_lab_census_20261021`) plus its evidence (student, url, quote, …) |
| `lab.lab_id` | the lab id the site uses: the reused collection unit id, or `<school>-pi-lab-<name slug>` for a new own lab |
| `lab.name`, `lab.url` | lab name (`<PI> group` when none is stated) and homepage |
| `lab.basis` | `single_leader_unit` (an existing unit led by this PI alone) or `new_own_lab` |
| `lab.collection_unit_id` | the reused unit id, else `null` |
| `lab.atlas_unit_id` | the matching unit in `data/atlas/units.jsonl.gz`, when the atlas has it |
| `lab.evidence` | the source for a new own lab |
| `lab.collectives` | multi-leader or umbrella units the PI belongs to (centres etc.; not labs) |
| `periods[]` | reviewed faculty appointment periods: `period_id`, `start`, `end` (`null` = ongoing), `as_of`, `evidence[]` |
| `listings[]` | dated department faculty listings naming the PI, one per year: `year`, `url`, `sha256`, `quote`, `kind`, `rank_as_listed`, `emeritus`, `visiting` |
| `counts` | `labPapers`, `students`, `studentPaperLinks`, `verifiedWorks` (collection works verified for the PI) |
| `funnel` | where the PI's candidate papers dropped out: `name_hits`, `school_affiliated`, `identity`, `in_appointment`, `outside_appointment_<year>`, `dblpTitles`, `dblpDois`, `verifiedWorks` |

### papers.jsonl.gz — one row per unique lab paper

| field | meaning |
|---|---|
| `paper_id` | the OpenAlex work id (`W…`); `dblp:<key>` for a DBLP-recovered paper without an OpenAlex record; `labpage:<sha1>` for a paper recovered from a lab publications page; `doi:<doi>` for a distinct work whose DOI resolved to an OpenAlex record another of the PI's papers already uses (see `openalex_shared_with`) |
| `openalex` | OpenAlex URL, when the id is an OpenAlex work |
| `doi`, `title`, `year`, `date`, `venue`, `type`, `landing_url` | bibliographic metadata of the lead edition |
| `byline` | authors as written on the work |
| `byline_school` | the authors whose authorship lists the school |
| `collection_work` | id in the project's earlier per-school works collection, when matched |
| `openalex_shared_with` | for the few `doi:` papers, the OpenAlex id they share |
| `editions[]` | other editions merged into this paper (arXiv preprint, conference and journal versions share a normalized title; the published edition leads): `paper_id`, `collection_work`, `doi`, `year`, `venue` |
| `labs[]` | every PI lab this paper belongs to: |
| `labs[].pi_id`, `labs[].lab_id` | the lab |
| `labs[].identity` | how the authorship was tied to the PI: `reviewed_openalex_author_id`, `pi_orcid`, `dblp_verified_collection_work`, `dblp_person_page_doi`, `dblp_person_page_title`, `dblp_person_page` (recovered from the DBLP page), `pi_institutional_publication_list`, `lab_publication_page`, `labpage_listing`, `advisee_coauthor`, `anchored_author_id`, `advisee_anchored_author_id` |
| `labs[].appointment` | `{basis: "faculty_period", period_id}` or `{basis: "same_year_listing", year, url, sha256, quote, kind}` |
| `labs[].authorship` | the PI's authorship: `position`, `raw_name`, `openalex_author`, `institutions`, `raw_affiliations`, `school_via` (what ties the school to it), `page1` (`url`, `pdf_sha256`, `how`, `quotes` when the paper's first page is the evidence) |
| `labs[].source` | for recovered papers, `dblp_recover:<basis>` or `labpage_recover:<basis>` |

### students.jsonl.gz — one row per student

| field | meaning |
|---|---|
| `student_id` | `<school>:<collection person id>`, or `ext:<school>:<name slug>` for a person found by the targeted student research |
| `source_person_id` | the id in the build package |
| `name`, `aliases` | name as the sources write it; other spellings merged into this record |
| `merged_ids` | former student ids (same `student_id` form) merged into this record: nickname / spelling variants and the same person found by several sources |
| `roles` | roles as the sources state them (free text, union over labs) |
| `role_label` | normalized: `PhD student`, `PhD alumnus`, `Master’s`, `Undergraduate`, `Thesis student`, `Student`, `Postdoc`, `Lab member` |
| `advisors[]` | one per PI lab: `pi_id`, `pi_name`, `lab_id`, `relation` (`advisee`, or `member` when every relation is a direct membership of the PI's own unit), `role_label` (for this lab), `first_year`, `last_year`, `relations[]` |
| `advisors[].relations[]` | `type` (`academic_advising` from thesis/roster records, `direct_lab_membership`, `researched_advising`, `researched_membership`), `role`, `years`, `thesis_work`, `sources[]` (evidence objects) |

The build gives one student id per person across a school's labs (co-advised students appear once, with one entry per
advisor). Records merged into another keep their former ids in `merged_ids`, so an id from an earlier release or from the
project's collections can be mapped to the current one; other spellings are in `aliases`. A person whose sources could
not be tied together can still have two ids; `data/schools/student_audit.json` lists the probable cases. Counts of
"unique students" count ids.

### student_papers.jsonl.gz — one row per (PI, student, paper)

| field | meaning |
|---|---|
| `pi_id`, `student_id`, `paper_id` | the link (the paper is a lab paper of that PI; the student is that PI's student) |
| `status` | `verified` (a verified authorship in the collection) or `candidate` (a name match) |
| `basis` | `collection_person_link`, `byline_name_with_school_affiliation` (the student's name on an authorship listing the school), `advisee_name_on_lab_paper_byline` (within three years of the recorded advising) |
| `collection_work`, `student_name` | convenience copies |

### CSV files

| file | columns |
|---|---|
| `pis.csv` | `pi_id, name, department, department_coverage, scope, rank, title, lab_id, lab_name, lab_url, atlas_unit_id, dblp, openalex, orcid, first_period_start, listing_years, lab_papers, students, student_paper_links` (multi-valued cells are space-separated) |
| `lab_papers.csv` | `pi_id, pi_name, lab_id, department, paper_id, doi, title, year, venue, type, identity, appointment_basis, appointment_ref` (one row per lab–paper pair) |
| `lab_students.csv` | `pi_id, pi_name, student_id, student_name, role_label, relation, first_year, last_year, relation_types, source_url` |
| `student_papers.csv` | `pi_id, student_id, student_name, paper_id, doi, title, year, status, basis` |

### Other per-school files

- `zero_labs.json`: `zero_papers[]` (labs with no lab paper: `pi`, `pi_id`, `diagnosis` — `joined_after_window`,
  `no_appointment_coverage`, `identity_unanchored`, `no_school_affiliation`, `not_in_school_sweep`, `no_output_found` —
  `verdict` `zero_is_right` / `fix` / `unreviewed`, `reason`, `funnel`, `periods`, `listing_years`) and `zero_students[]`.
- `excluded_pis.json`: census PIs removed by review (`pi`, `why`).
- `scope_review.json.gz`: the CS-related-scope review: `rule`, `counts`, and `decisions[]` (every DBLP-based candidate:
  `name`, `openalex`, `works`, `dblp_works`, `last_author_share`, `years`, `decision` — `accepted`, `not_faculty`,
  `faculty_no_pi_evidence`, `not_at_school_in_window`, `unresolved` — `reason`, `home_department`, `evidence[]`).
  Structure differs slightly per school.
- `build_report.json`: the package build's counters (`counts`), excluded PIs, PIs without papers / students.

### data/schools/student_audit.json

The output of `tools/student_audit.py`, one object per school: `within_lab` (pairs of records in one lab that are
probably one person), `across_labs` (one person under several ids in a school), `same_paper` (a paper linked to two ids
of one person), `missed_link` (lab papers whose school-affiliated byline has the student's family name and initial but
no link), `students_without_links`, and `counts`. Names only; for review, not applied to the tables.

### data/schools/profiles.json

One object per school (the source of the README coverage table and `docs/SCHOOL-PROFILES.md`): `pis`, `pis_core`,
`pis_cs_related_additions`, `departments`, `top_departments`, `pi_arrivals_by_year`, `pi_departures_by_year`,
`lab_papers_unique` (unique OpenAlex/DBLP/lab-page keys), `lab_paper_rows`, `lab_papers_by_year`,
`median_papers_per_pi`, `top_venues`, `students_unique`, `students_by_first_role`, `student_paper_links`,
`pis_with_students`, `pis_with_lab_papers`, `pis_complete_chain`, `dblp_reference` (coverage against the PIs' DBLP
pages), `local_fulltext` (share of lab papers with a local full-text copy in the project; the copies are not
distributed), `zero_paper_labs`, `zero_student_labs`.

---

## data/atlas/

The 300-university atlas of research units (all fields), as of its last build. Field names of the core columns are
snake_case; `extra` keeps every other source field of the record verbatim (camelCase), minus local file paths and
contact details.

### universities.jsonl.gz

`university_id`, `name`, `country`, `rank` (ranking position as text, e.g. `"1"` or `"101-150"`), `rank_low`, `url`,
`cs_scope` (CS-only counts and overview: `labs`, `counts`, `overview`, `inScope`, `hidden`, and for the five schools
`school`, `piLabs`), `counts` (unit counts by field × leadership status, with `n`, `named`, `reviewed`, `verified`,
`active`, `years`), `overview` (per-view yearly publication metrics), `discovery` (how the unit inventory was
discovered and how complete it is), `institution_audit`.

### units.jsonl.gz — one row per research unit

| field | meaning |
|---|---|
| `unit_id`, `university_id` | ids |
| `name`, `type` (`laboratory`, `research_group`, `research_center`, `adviser_group_listing`, …), `field` (one of 12 fields, e.g. `computer_and_information_sciences`) | |
| `department`, `departments`, `source_department`, `department_source` | department as recorded, all listed departments, as the source wrote it, and the URL supporting it |
| `url`, `source` | unit homepage and the official directory source |
| `aliases`, `years` | other names; years with dated evidence of activity |
| `activity` | `verified_in_window`, `unverified`, … |
| `leadership_status` | `missing_name`, `name_recorded`, `leadership_reviewed`, `publication_identity_verified` |
| `pi`, `pis`, `leadership` | the recorded leader name, verified PI identities, sourced leadership records |
| `evidence` | dated evidence of the unit's activity |
| `paper_counts` | linked papers per year in the `combined`, `reviewed` and `strict` views |
| `cs_scope`, `cs_scope_reason` | whether the unit is in CS scope, and why (`field`, `department`, `field_and_department`, `cs_department_pi_lab`) |
| `cs_shown`, `cs_hidden` | whether the CS atlas shows it; why not (`no_papers`, `replaced_by_pi_labs` at the five schools, whose PI labs are in `data/schools`) |
| `research_summary` | short description, when sourced |
| `papers_file`, `people_file` | whether the unit has paper links / people in this release |
| `people_count`, `student_count` | as recorded |
| `extra` | all other source fields (unit-type reviews, computing-scope reviews, leadership observations, …) |

### works.jsonl.gz — one row per work linked to any unit

`work_id` (e.g. `doi:10.…`, `princeton-library:paper_…`, `W…`), `openalex`, `doi`, `title`, `year`, `date`, `type`,
`venue`, `author_count`, `byline` (when recorded), `citations`, `topic`, `field`, `retracted`, `open_access`, `url`,
`arxiv`, `handle`, `canonical_graph_work_id`, `aliases`, `countries`, `extra` (source observations: explicit paper
roles, publication-affiliation evidence, source work observations, …).

### unit_papers.jsonl.gz — one row per (unit, work)

| field | meaning |
|---|---|
| `unit_id`, `university_id`, `work_id`, `openalex`, `doi`, `title`, `year` | the link and the work's ids |
| `views.strict` | verified PI identity with the university affiliation on the paper (PI last author) |
| `views.reviewed` | on the unit's own reviewed bibliography |
| `views.combined` | strict or reviewed: the atlas's default "accepted" view |
| `reason`, `review_source`, `temporal` | the attribution reason, the bibliography URL, and what is (not) claimed about time |
| `groups` | PI identity groups (`pi_identities.group_id`) per view |
| `unit_attribution_policy` | the unit-level policy, when recorded |
| `extra` | further evidence (`evidence`, `audit`, `advisorAttribution`, `labEligibility`, `unitEvidence`, `additional_observations` when the source recorded the link twice, …) |

### unit_people.jsonl.gz — one row per (unit, person)

`unit_id`, `university_id`, `school` (the collection the record came from), `person_id`, `name`, `aliases`, `roles`,
`departments`, `identity_review`, `personal_work_count`, `contexts[]`: the person's relations **to this unit** —
`context_kind` (`memberships`, `researchContexts`, `advisingContexts`, `departmentContexts`), `relationship_type`
(`direct_lab_membership`, `academic_advising`, `source_listing`, `department_roster`, …), `member_type`, `role`,
`status`, `advisor_name`, `observation_years`, `observed_on`, `start`, `end`, `evidence[]`. Personal homepage URLs
are not included.

### unit_person_papers.jsonl.gz — one row per (unit, person, work)

`unit_id`, `university_id`, `person_id`, `work_id`, `doi`, `title`, `year`, `date`, `type`, `status` (`verified`,
`candidate`, …), `role`, `lab_period` (`supported`, `outside`, unresolved), `lab_eligibility`, `identity_basis`,
`evidence`.

### pi_identities.jsonl.gz — one row per PI identity group

`group_id`, `lab_id` (a unit id), `university_id`, `pi_identity_id`, `pi_name`, `orcid`, `author_aliases` (OpenAlex
author ids), `name_aliases_json`, `group_definition`, `identity_method`, `publication_profile`,
`lab_membership_interval_status`, `observed_on`.

### Other atlas files

- `metrics.json.gz`: the atlas's precomputed metrics (`units`: count cells; `buckets`: per-view yearly publication
  aggregates by group of units), as the site uses them.
- `scope_rule.json`: the CS-scope rule (field / department pattern) and what the CS atlas shows.
- `atlas_summary.json`: as-of date, window, fields, CS-scope summary and collection summaries of the atlas build.

---

## MANIFEST.json

`export`: the export summary (counts per school and table, redaction counts, sources); `files`: every data and code
file with `bytes`, `sha256` and `rows` (for tables).
