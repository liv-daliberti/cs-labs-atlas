# Data layout: raw, reviewed, derived (ROADMAP item 10)

**Status: phase A (design; nothing has moved), 2026-10-31.** The table below is `tools/atlas_paths.py` `DATA_FILES`;
`tests/test_schemas.py` checks that every entry is listed here. The move itself (phase B) is a dry-run tool and an owner
decision; it has not been run.

## The rules

| kind | what | who writes it | in git |
|---|---|---|---|
| `raw` | captures and bulk pulls: the OpenAlex sweep, pi-works, page captures, DBLP pulls, listing captures | the collectors and capture tools, once per capture; never rewritten (a re-capture adds rows, never edits them) | no (too large; the releases carry hashes) |
| `reviewed` | human or agent decisions with their evidence: overrides, corrections, researched evidence, review files | review tools and hand edits, through commits | yes (the `.gitignore` whitelist) |
| `derived` | what the build makes: packages, copies, ledger, audits, diagnoses, the census built from listings | only the build (`hierarchy/rebuild.sh` and the stage tools that build) | no; rebuilt, never hand-edited |
| `work` | tool state that can be rebuilt from raw + reviewed: recovery databases, recovered rows, `tmp/` | the tool that owns it | no |
| `logs`, `reports` | run logs; generated Markdown reports (`*-AUDIT.md`, `STAGE-*.md` are reviewed reports and stay tracked) | the runs | reports: tracked when reviewed |

## The target layout

```
hierarchy/
  <school>/
    raw/        openalex-sweep.sqlite, pi-works.sqlite, *-captures.sqlite, dblp_pubs.json.gz, school-captures.sqlite
    reviewed/   gap-evidence.json, few-students-evidence.json, relation-evidence.json, labpage-additions.json, ...,
                census-additions.json, faculty-periods.json   (from census/ and periods/)
    derived/    pis.json, students.json, lab_papers.jsonl.gz, student_papers.jsonl.gz, report.json, copies.json,
                unavailable*.json*, link-diagnosis.json, sweep-check.json, census-faculty*.json, collection.json.gz
    work/       *-recover.sqlite, *-recovered.jsonl.gz, labpage-pubs.jsonl.gz, tmp/
    reports/    STAGE-*.md, REQUESTS-FOR-BUILDER.md
  raw/         dblp-dump-persons.json.gz
  reviewed/    census-overrides.json, student-corrections.json, student-identity-review.json, home-departments.json,
               chain-reasons.json, zero-paper-review.json, cs-venues.json, nicknames/
  derived/     chain-audit.json, student-audit.json, EVIDENCE-CHECK.json, BUILD-REGRESSION.json, VALIDATION.json,
               zero-paper-labs.json, ids/
  logs/        every *.log (today scattered over hierarchy/ and hierarchy/<school>/tmp/)
  reports/     CHAIN-AUDIT.md, EVIDENCE-CHECK.md, BUILD-REGRESSION.md, SCHOOL-PROFILES.md, LABPAGE-AUDIT.md
listings/<school>/raw/captures.sqlite, listings/<school>/derived/{rows,listings,coverage,...}.json
```

`census/` and `periods/` are absorbed into the schools' `reviewed/` and `derived/`; `captures/<school>.sqlite` becomes the
school's `raw/school-captures.sqlite`. The stores (`stores/<school>/`) and the releases keep their own layout.

## How the code finds a file

- `atlas_paths.data(name, school=None, root=None, layout=None)` gives a data file's path from `DATA_FILES`. `DATA_LAYOUT`
  (`CS_ATLAS_DATA_LAYOUT`) is `flat` today: every path is the old one. After the move it becomes `split`, and the code does
  not change. This is the same pattern as `LAYOUT_DEFAULT` for the project move. `root` points a trial build or a test at a
  copy; without it each top directory follows its slot (`HIERARCHY`, `CENSUS`, `LISTINGS`, `PERIODS`, `CAPTURES`).
- New slots: `RATE_STAMPS` (`<ROOT>/cache/rate-stamps`) and `LOCKS` (`/tmp/cs-atlas-locks`, below). No new top-level
  slot is needed for the kinds; they are directories inside `HIERARCHY` and `LISTINGS`.
- Routed so far (phase A): the builder (`tools/pihier/`), `tools/provenance.py`, `tools/validate.py`, the nickname tables.
  The equivalence run proves no output change. Still joining paths directly: 192 places in 37 files (below). They are routed the same way,
  one tool at a time, each with a stage-level equivalence check, before the move. Not ours to change: `tools/labpage_audit.py` and
  `hierarchy/labpage-tools-*` (the lab-page agent), `fulltext-push/**` (the downloads agent); their paths are mapped here.

## Locks and rate stamps (decided 2026-10-31)

- **Rate stamps are shared**, in `RATE_STAMPS` on project storage: one stamp file per host, flock'd. The NFS mount has
  `local_lock=none` (NFSv3 with NLM), so a flock is seen by every node, and the I/O is one tiny file per request. The
  Wayback throttle (`listings/scripts/wb.py`, `tools/school_web.py`) and `tools/mpcap.py`'s per-host spacing use it, so
  Slurm jobs on different nodes keep one request rate per host. Before this they were node-local and did not coordinate.
- **Node-local `LOCKS`** (`/tmp/cs-atlas-locks`) is for true mutexes inside one host. Nothing uses it today.
- The lab-page agent's `lpcap` still uses its own directory (`labpage_audit.py` sets `$TMPDIR/lp-ratelimit` for `lpcap`
  and `mpcap`). Pointing it at `RATE_STAMPS/hosts` would make all three share one stamp per host. That is for the lab-page agent.

## Every file in the table: today and after the move

Tracked: tracked files / files on disk today, across the schools. Size: the largest class in the inventory.

| name | kind | today | after the move | tracked | size |
|---|---|---|---|---|---|
| `pis.json` | derived | `hierarchy/{school}/pis.json` | `hierarchy/{school}/derived/pis.json` | 0/7 | <100MB |
| `students.json` | derived | `hierarchy/{school}/students.json` | `hierarchy/{school}/derived/students.json` | 0/7 | <100MB |
| `lab_papers.jsonl.gz` | derived | `hierarchy/{school}/lab_papers.jsonl.gz` | `hierarchy/{school}/derived/lab_papers.jsonl.gz` | 0/7 | <100MB |
| `student_papers.jsonl.gz` | derived | `hierarchy/{school}/student_papers.jsonl.gz` | `hierarchy/{school}/derived/student_papers.jsonl.gz` | 0/7 | <100MB |
| `report.json` | derived | `hierarchy/{school}/report.json` | `hierarchy/{school}/derived/report.json` | 0/7 | <1MB |
| `copies.json` | derived | `hierarchy/{school}/copies.json` | `hierarchy/{school}/derived/copies.json` | 0/6 | <100MB |
| `unavailable.jsonl.gz` | derived | `hierarchy/{school}/unavailable.jsonl.gz` | `hierarchy/{school}/derived/unavailable.jsonl.gz` | 0/6 | <100MB |
| `unavailable-summary.json` | derived | `hierarchy/{school}/unavailable-summary.json` | `hierarchy/{school}/derived/unavailable-summary.json` | 0/6 | <1MB |
| `link-diagnosis.json` | derived | `hierarchy/{school}/link-diagnosis.json` | `hierarchy/{school}/derived/link-diagnosis.json` | 0/6 | <100MB |
| `listed-not-in-census.json` | derived | `hierarchy/{school}/listed-not-in-census.json` | `hierarchy/{school}/derived/listed-not-in-census.json` | 0/7 | <100MB |
| `sweep-check.json` | derived | `hierarchy/{school}/sweep-check.json` | `hierarchy/{school}/derived/sweep-check.json` | 0/7 | <1MB |
| `cs-related-candidates.json` | derived | `hierarchy/{school}/cs-related-candidates.json` | `hierarchy/{school}/derived/cs-related-candidates.json` | 0/7 | <100MB |
| `oa-author-stats.json.gz` | derived | `hierarchy/{school}/oa-author-stats.json.gz` | `hierarchy/{school}/derived/oa-author-stats.json.gz` | 0/1 | <100MB |
| `collection.json.gz` | derived | `hierarchy/{school}/collection.json.gz` | `hierarchy/{school}/derived/collection.json.gz` | 0/3 | <1MB |
| `census-faculty.json` | derived | `census/{school}-faculty.json` | `hierarchy/{school}/derived/census-faculty.json` | 0/7 | <100MB |
| `census-faculty-hierarchy.json` | derived | `census/{school}-faculty-hierarchy.json` | `hierarchy/{school}/derived/census-faculty-hierarchy.json` | 0/1 | <1MB |
| `listings.json` | derived | `listings/{school}/listings.json` | `listings/{school}/derived/listings.json` | 0/7 | <100MB |
| `openalex-sweep.sqlite` | raw | `hierarchy/{school}/openalex-sweep.sqlite` | `hierarchy/{school}/raw/openalex-sweep.sqlite` | 0/7 | >=100MB |
| `pi-works.sqlite` | raw | `hierarchy/{school}/pi-works.sqlite` | `hierarchy/{school}/raw/pi-works.sqlite` | 0/7 | >=100MB |
| `dblp_pubs.json.gz` | raw | `hierarchy/{school}/raw/dblp_pubs.json.gz` | `hierarchy/{school}/raw/dblp_pubs.json.gz` | 0/1 | <1MB |
| `relation-captures.sqlite` | raw | `hierarchy/{school}/relation-captures.sqlite` | `hierarchy/{school}/raw/relation-captures.sqlite` | 0/3 | >=100MB |
| `pubs-pages.sqlite` | raw | `hierarchy/{school}/pubs-pages.sqlite` | `hierarchy/{school}/raw/pubs-pages.sqlite` | 0/1 | <100MB |
| `gap-captures.sqlite` | raw | `hierarchy/{school}/gap-captures.sqlite` | `hierarchy/{school}/raw/gap-captures.sqlite` | 0/5 | <100MB |
| `few-students-captures.sqlite` | raw | `hierarchy/{school}/few-students-captures.sqlite` | `hierarchy/{school}/raw/few-students-captures.sqlite` | 0/5 | <100MB |
| `thesis-captures.sqlite` | raw | `hierarchy/{school}/thesis-captures.sqlite` | `hierarchy/{school}/raw/thesis-captures.sqlite` | 0/6 | >=100MB |
| `cs-related-captures.sqlite` | raw | `hierarchy/{school}/cs-related-captures.sqlite` | `hierarchy/{school}/raw/cs-related-captures.sqlite` | 0/5 | >=100MB |
| `labpage-captures.sqlite` | raw | `hierarchy/{school}/labpage-captures.sqlite` | `hierarchy/{school}/raw/labpage-captures.sqlite` | 0/6 | >=100MB |
| `labpage-audit-captures.sqlite` | raw | `hierarchy/{school}/labpage-audit-captures.sqlite` | `hierarchy/{school}/raw/labpage-audit-captures.sqlite` | 0/7 | >=100MB |
| `school-captures.sqlite` | raw | `captures/{school}.sqlite` | `hierarchy/{school}/raw/school-captures.sqlite` | 0/4 | >=100MB |
| `listings-captures.sqlite` | raw | `listings/{school}/captures.sqlite` | `listings/{school}/raw/captures.sqlite` | 0/6 | >=100MB |
| `gap-evidence.json` | reviewed | `hierarchy/{school}/gap-evidence.json` | `hierarchy/{school}/reviewed/gap-evidence.json` | 5/5 | <100MB |
| `few-students-evidence.json` | reviewed | `hierarchy/{school}/few-students-evidence.json` | `hierarchy/{school}/reviewed/few-students-evidence.json` | 6/6 | <100MB |
| `thesis-evidence.json` | reviewed | `hierarchy/{school}/thesis-evidence.json` | `hierarchy/{school}/reviewed/thesis-evidence.json` | 0/6 | <100MB |
| `thesis-held-years-evidence.json` | reviewed | `hierarchy/{school}/thesis-held-years-evidence.json` | `hierarchy/{school}/reviewed/thesis-held-years-evidence.json` | 0/1 | <100MB |
| `labpage-evidence.json` | reviewed | `hierarchy/{school}/labpage-evidence.json` | `hierarchy/{school}/reviewed/labpage-evidence.json` | 0/6 | <100MB |
| `labpage-acceptance.json` | reviewed | `hierarchy/{school}/labpage-acceptance.json` | `hierarchy/{school}/reviewed/labpage-acceptance.json` | 1/1 | <10KB |
| `labpage-additions.json` | reviewed | `hierarchy/{school}/labpage-additions.json` | `hierarchy/{school}/reviewed/labpage-additions.json` | 2/4 | <100MB |
| `relation-evidence.json` | reviewed | `hierarchy/{school}/relation-evidence.json` | `hierarchy/{school}/reviewed/relation-evidence.json` | 3/3 | <100MB |
| `pi-publication-lists.json` | reviewed | `hierarchy/{school}/pi-publication-lists.json` | `hierarchy/{school}/reviewed/pi-publication-lists.json` | 0/2 | <100MB |
| `cs-related-review.json` | reviewed | `hierarchy/{school}/cs-related-review.json` | `hierarchy/{school}/reviewed/cs-related-review.json` | 7/7 | <100MB |
| `missing-pi-review.json` | reviewed | `hierarchy/{school}/missing-pi-review.json` | `hierarchy/{school}/reviewed/missing-pi-review.json` | 7/7 | <1MB |
| `openalex-identity-review.json` | reviewed | `hierarchy/{school}/openalex-identity-review.json` | `hierarchy/{school}/reviewed/openalex-identity-review.json` | 1/1 | <10KB |
| `census-additions.json` | reviewed | `census/{school}-additions.json` | `hierarchy/{school}/reviewed/census-additions.json` | 7/7 | <100MB |
| `faculty-periods.json` | reviewed | `periods/{school}-faculty-periods.json` | `hierarchy/{school}/reviewed/faculty-periods.json` | 5/5 | <1MB |
| `dblp-recovered.jsonl.gz` | work | `hierarchy/{school}/dblp-recovered.jsonl.gz` | `hierarchy/{school}/work/dblp-recovered.jsonl.gz` | 0/7 | <1MB |
| `labpage-recovered.jsonl.gz` | work | `hierarchy/{school}/labpage-recovered.jsonl.gz` | `hierarchy/{school}/work/labpage-recovered.jsonl.gz` | 0/3 | <1MB |
| `labpage-pubs.jsonl.gz` | work | `hierarchy/{school}/labpage-pubs.jsonl.gz` | `hierarchy/{school}/work/labpage-pubs.jsonl.gz` | 0/6 | <100MB |
| `dblp-recover.sqlite` | work | `hierarchy/{school}/dblp-recover.sqlite` | `hierarchy/{school}/work/dblp-recover.sqlite` | 0/7 | <100MB |
| `labpage-recover.sqlite` | work | `hierarchy/{school}/labpage-recover.sqlite` | `hierarchy/{school}/work/labpage-recover.sqlite` | 0/5 | <100MB |
| `census-overrides.json` | reviewed | `hierarchy/census-overrides.json` | `hierarchy/reviewed/census-overrides.json` | 1/1 | <100MB |
| `student-corrections.json` | reviewed | `hierarchy/student-corrections.json` | `hierarchy/reviewed/student-corrections.json` | 1/1 | <10KB |
| `student-identity-review.json` | reviewed | `hierarchy/student-identity-review.json` | `hierarchy/reviewed/student-identity-review.json` | 1/1 | <1MB |
| `home-departments.json` | reviewed | `hierarchy/home-departments.json` | `hierarchy/reviewed/home-departments.json` | 1/1 | <1MB |
| `chain-reasons.json` | reviewed | `hierarchy/chain-reasons.json` | `hierarchy/reviewed/chain-reasons.json` | 1/1 | <1MB |
| `zero-paper-review.json` | reviewed | `hierarchy/zero-paper-review.json` | `hierarchy/reviewed/zero-paper-review.json` | 1/1 | <1MB |
| `zero-paper-labs.json` | derived | `hierarchy/zero-paper-labs.json` | `hierarchy/derived/zero-paper-labs.json` | 1/1 | <10KB |
| `cs-venues.json` | reviewed | `hierarchy/cs-venues.json` | `hierarchy/reviewed/cs-venues.json` | 1/1 | <1MB |
| `nicknames` | reviewed | `hierarchy/nicknames` | `hierarchy/reviewed/nicknames` | 0/1 | dir |
| `dblp-dump-persons.json.gz` | raw | `hierarchy/dblp-dump-persons.json.gz` | `hierarchy/raw/dblp-dump-persons.json.gz` | 0/1 | <100MB |
| `chain-audit.json` | derived | `hierarchy/chain-audit.json` | `hierarchy/derived/chain-audit.json` | 0/1 | <100MB |
| `student-audit.json` | derived | `hierarchy/student-audit.json` | `hierarchy/derived/student-audit.json` | 0/1 | <1MB |
| `EVIDENCE-CHECK.json` | derived | `hierarchy/EVIDENCE-CHECK.json` | `hierarchy/derived/EVIDENCE-CHECK.json` | 0/1 | <1MB |
| `BUILD-REGRESSION.json` | derived | `hierarchy/BUILD-REGRESSION.json` | `hierarchy/derived/BUILD-REGRESSION.json` | 0/1 | <10KB |
| `VALIDATION.json` | derived | `hierarchy/VALIDATION.json` | `hierarchy/derived/VALIDATION.json` | - | - |
| `ids` | derived | `hierarchy/ids` | `hierarchy/derived/ids` | 0/1 | dir |
| `logs` | work | `hierarchy/logs` | `hierarchy/logs` | 0/1 | dir |
| `listings-pages.json` | derived | `listings/{school}/pages.json` | `listings/{school}/derived/pages.json` | - | <100MB |
| `listings-gaps.json` | derived | `listings/{school}/gaps.json` | `listings/{school}/derived/gaps.json` | - | <100MB |
| `listings-ambiguous.json` | derived | `listings/{school}/ambiguous.json` | `listings/{school}/derived/ambiguous.json` | - | <100MB |
| `listings-summary.json` | derived | `listings/{school}/summary.json` | `listings/{school}/derived/summary.json` | - | <100MB |
| `listings-verify.json` | derived | `listings/{school}/verify.json` | `listings/{school}/derived/verify.json` | - | <100MB |
| `listings-input.json` | reviewed | `hierarchy/listings-input-{school}.json` | `hierarchy/reviewed/listings-input-{school}.json` | - | <100MB |
| `COLLECTORS-STATUS.md` | derived | `hierarchy/COLLECTORS-STATUS.md` | `hierarchy/derived/COLLECTORS-STATUS.md` | - | <100MB |
| `COLLECTORS-STATUS.json` | derived | `hierarchy/COLLECTORS-STATUS.json` | `hierarchy/derived/COLLECTORS-STATUS.json` | - | <100MB |
| `labpage-parts` | work | `hierarchy/{school}/labpage-parts` | `hierarchy/{school}/work/labpage-parts` | - | <100MB |
| `labpage-input.json` | reviewed | `hierarchy/{school}/labpage-input.json` | `hierarchy/{school}/reviewed/labpage-input.json` | - | <100MB |
| `labpage-pubs-report.json` | derived | `hierarchy/{school}/labpage-pubs-report.json` | `hierarchy/{school}/derived/labpage-pubs-report.json` | - | <100MB |
| `labpage-audit.jsonl.gz` | derived | `hierarchy/{school}/labpage-audit.jsonl.gz` | `hierarchy/{school}/derived/labpage-audit.jsonl.gz` | - | <100MB |
| `labpage-audit-discovery.jsonl` | raw | `hierarchy/{school}/labpage-audit-discovery.jsonl` | `hierarchy/{school}/raw/labpage-audit-discovery.jsonl` | - | <100MB |
| `labpage-audit-recover` | work | `hierarchy/{school}/labpage-audit-recover` | `hierarchy/{school}/work/labpage-audit-recover` | - | <100MB |
| `labpage-handcheck.json` | reviewed | `hierarchy/{school}/labpage-handcheck.json` | `hierarchy/{school}/reviewed/labpage-handcheck.json` | - | <100MB |
| `labpage-departure-review.json` | reviewed | `hierarchy/labpage-departure-review.json` | `hierarchy/reviewed/labpage-departure-review.json` | - | <100MB |
| `labpage-audit-summary.json` | derived | `hierarchy/labpage-audit-summary.json` | `hierarchy/derived/labpage-audit-summary.json` | - | <100MB |
| `tobagi-review.json` | reviewed | `hierarchy/{school}/tobagi-review.json` | `hierarchy/{school}/reviewed/tobagi-review.json` | - | <100MB |
| `link-sweep.json` | derived | `hierarchy/link-sweep/{school}.json` | `hierarchy/derived/link-sweep/{school}.json` | - | <100MB |
| `reader.jsonl.gz` | derived | `hierarchy/reader/{school}.jsonl.gz` | `hierarchy/derived/reader/{school}.jsonl.gz` | - | <100MB |
| `reader-SUMMARY.json` | derived | `hierarchy/reader/SUMMARY.json` | `hierarchy/derived/reader/SUMMARY.json` | - | <100MB |
| `reader-hosted-files.tsv` | derived | `hierarchy/reader/hosted-files.tsv` | `hierarchy/derived/reader/hosted-files.tsv` | - | <100MB |
| `reader-not-permitted.tsv` | derived | `hierarchy/reader/currently-hosted-not-permitted.tsv` | `hierarchy/derived/reader/currently-hosted-not-permitted.tsv` | - | <100MB |
| `reader-README.md` | derived | `hierarchy/reader/README.md` | `hierarchy/derived/reader/README.md` | - | <100MB |
| `sweep.log` | work | `hierarchy/sweep-{school}.log` | `hierarchy/work/sweep-{school}.log` | - | <100MB |
| `tmp` | work | `hierarchy/{school}/tmp` | `hierarchy/{school}/work/tmp` | - | <100MB |
| `gaps.json` | derived | `hierarchy/{school}/gaps.json` | `hierarchy/{school}/derived/gaps.json` | - | <100MB |
| `coverage.json` | derived | `listings/{school}/coverage.json` | `listings/{school}/derived/coverage.json` | - | <100MB |
| `missing-pi-captures.sqlite` | raw | `hierarchy/missing-pi-captures.sqlite` | `hierarchy/raw/missing-pi-captures.sqlite` | - | <100MB |
| `home-departments-school.json` | derived | `hierarchy/{school}/home-departments.json` | `hierarchy/{school}/derived/home-departments.json` | - | <100MB |
| `school-profiles.json` | derived | `hierarchy/school-profiles.json` | `hierarchy/derived/school-profiles.json` | - | <100MB |
| `missing-papers-audit.json` | derived | `hierarchy/missing-papers-audit.json` | `hierarchy/derived/missing-papers-audit.json` | - | <100MB |
| `CHAIN-AUDIT.md` | derived | `hierarchy/CHAIN-AUDIT.md` | `hierarchy/derived/CHAIN-AUDIT.md` | - | <100MB |
| `EVIDENCE-CHECK.md` | derived | `hierarchy/EVIDENCE-CHECK.md` | `hierarchy/derived/EVIDENCE-CHECK.md` | - | <100MB |
| `BUILD-REGRESSION.md` | derived | `hierarchy/BUILD-REGRESSION.md` | `hierarchy/derived/BUILD-REGRESSION.md` | - | <100MB |
| `SCHOOL-PROFILES.md` | derived | `hierarchy/SCHOOL-PROFILES.md` | `hierarchy/derived/SCHOOL-PROFILES.md` | - | <100MB |
| `LABPAGE-AUDIT.md` | derived | `hierarchy/LABPAGE-AUDIT.md` | `hierarchy/derived/LABPAGE-AUDIT.md` | - | <100MB |
| `rows.json` | derived | `listings/{school}/rows.json` | `listings/{school}/derived/rows.json` | - | <100MB |
| `pi-basis-evidence.json` | reviewed | `hierarchy/{school}/pi-basis-evidence.json` | `hierarchy/{school}/reviewed/pi-basis-evidence.json` | - | <100MB |
| `dblp-ids.json` | derived | `hierarchy/{school}/dblp-ids.json` | `hierarchy/{school}/derived/dblp-ids.json` | - | <100MB |
| `homepage-identity.json` | derived | `hierarchy/{school}/homepage-identity.json` | `hierarchy/{school}/derived/homepage-identity.json` | - | <100MB |
| `census-report.md` | derived | `census/{school}-report.md` | `hierarchy/{school}/derived/report.md` | - | <100MB |
| `dblp-affiliated.json` | derived | `hierarchy/{school}/dblp-affiliated.json` | `hierarchy/{school}/derived/dblp-affiliated.json` | - | <100MB |
| `cs-related-candidates-openalex.json` | derived | `hierarchy/{school}/cs-related-candidates-openalex.json` | `hierarchy/{school}/derived/cs-related-candidates-openalex.json` | - | <100MB |
| `defense-evidence.json` | reviewed | `hierarchy/{school}/defense-evidence.json` | `hierarchy/{school}/reviewed/defense-evidence.json` | - | <100MB |
| `directory-evidence.json` | reviewed | `hierarchy/{school}/directory-evidence.json` | `hierarchy/{school}/reviewed/directory-evidence.json` | - | <100MB |
| `labpage-students-report.json` | derived | `hierarchy/{school}/labpage-students-report.json` | `hierarchy/{school}/derived/labpage-students-report.json` | - | <100MB |
| `holds.json` | derived | `periods/{school}-holds.json` | `hierarchy/{school}/derived/holds.json` | - | <100MB |
| `gap-year-evidence.json` | reviewed | `hierarchy/{school}/gap-year-evidence.json` | `hierarchy/{school}/reviewed/gap-year-evidence.json` | - | <100MB |
| `profile-year-evidence.json` | reviewed | `hierarchy/{school}/profile-year-evidence.json` | `hierarchy/{school}/reviewed/profile-year-evidence.json` | - | <100MB |

## Files outside the table (inventory of 2026-10-31)

The inventory (`os.scandir` at depth 2 or less on known paths; 666 paths in 342 patterns) puts the rest into these groups.
Each group has one rule for the move:

| group | paths | rule |
|---|---|---|
| logs (`*.log`, `hierarchy/logs/`) | 186 | to `hierarchy/logs/` (shared) or `<school>/work/logs/`; never inputs |
| named by code, not yet in the table | 69 | added to `DATA_FILES` when the tool that names them is routed (the list below) |
| lab-page agent files (`labpage-audit*`, `labpage-parts/`, `labpage-handcheck.json`, ...) | 50 | mapped with the lab-page agent: captures to `raw/`, the hand checks to `reviewed/`, the audit to `derived/`, parts to `work/` |
| one-off outputs nothing reads (`period-targets-*.json`, `*-captures-<school>.sqlite`, ...) | 34 | to `hierarchy/archive-data/` with a dated note, or deleted after review |
| reports (`*.md`) | 21 | to `reports/`; the reviewed ones stay tracked |
| `hierarchy/<school>/tmp/` | 21 | to `<school>/work/tmp/` |
| leftover directories of the archived tools (untracked state, caches) | 19 | to `hierarchy/archive-data/<dir>/`; their code is in `archive/` |

The inventory's writer and reader columns come from `git grep`, so a tool that builds a path from parts is missed.
`missing-pi-captures.sqlite` (`tools/mpcap.py`) shows up as unreferenced for that reason. Each file is checked by hand when its tool is routed.

## Still to route (direct path joins in live code, comments excluded)

| file | places |
|---|---|
| `tools/make_release.py` | 22 |
| `tools/periods_school.py` | 15 |
| `tools/labpage_students_school.py` | 15 |
| `tools/labpage_recover.py` | 13 |
| `tools/cs_related_school.py` | 12 |
| `tools/census_build.py` | 12 |
| `tools/stage_gate.py` | 10 |
| `tools/relation_recapture.py` | 7 |
| `tools/oa_identity_school.py` | 6 |
| `tools/dblp_recover.py` | 6 |
| `tools/cs_related_candidates.py` | 6 |
| `tools/sweep_check.py` | 5 |
| `tools/pi_fulltext_affiliation.py` | 5 |
| `tools/missing_papers_audit.py` | 5 |
| `tools/listed_not_in_census.py` | 5 |
| `tools/home_departments_school.py` | 5 |
| `tools/export_release.py` | 5 |
| `tools/lab_paper_copies.py` | 4 |
| `tools/dblp_ids_school.py` | 4 |
| `tools/zero_paper_ledger.py` | 3 |
| `tools/listing_rows.py` | 3 |
| `tools/diagnose_gaps.py` | 3 |
| `tools/sweep_school.py` | 2 |
| `tools/school_web.py` | 2 |
| `tools/school_profiles.py` | 2 |
| `tools/organize_tree.py` | 2 |
| `tools/dblp_dump_persons.py` | 2 |
| `tools/atlas_ids.py` | 2 |
| `tools/school_hosts.py` | 1 |
| `tools/oa_sweep.py` | 1 |
| `tools/mpcap.py` | 1 |
| `tools/homepage_links_school.py` | 1 |
| `tools/dblp_affiliated.py` | 1 |
| `tools/build_regression.py` | 1 |
| `hierarchy/rebuild.sh` | 1 |
| `accuracy/sample.py` | 1 |
| `accuracy/record.py` | 1 |

## The collectors' data directories (decided 2026-10-31)

`fulltext-push/` keeps data next to its code. A job that runs from a code snapshot (docs/CONTRIBUTING.md) has no such data, so
each directory has an atlas_paths slot derived from `CODE` (the main checkout), not from `FULLTEXT_PUSH` (which a snapshot moves).
Flat layout today: the slot is the same directory the code used. `tools/route_ft_data.py` lists the places that still join by hand.

| slot (shell: `$CS_ATLAS_<NAME>`) | today | kind | holds |
|---|---|---|---|
| `FT_DATA` | `fulltext-push/` | (container) | the four below and `review-<stamp>/` |
| `FT_RAW` | `fulltext-push/raw/` | raw, and state | OpenAlex works caches, work-id lists, DBLP-ee / NSF-PAR / homepages pulls; state: `openalex_budget.jsonl` (the shared daily quota log), `downloads_stopped_for_disk`, `mit_oa_articles.done` |
| `FT_CHECKS` | `fulltext-push/checks/` | derived | `<school>.sqlite`: the ledger's recorded checks, rebuilt by the ledger |
| `FT_LOGS` | `fulltext-push/logs/` | logs, and state | run logs, `channels.jsonl`, yield files; state: the per-channel `run_steps-<step>.lock` files |
| `FT_LOCAL_REUSE` | `fulltext-push/local-reuse/` (data files only) | raw, and work | `inventory.sqlite`, `ident/`, `lists/`, `missing.jsonl.gz`, `stores.jsonl.gz`, `logs/` (the code beside them stays code) |
| `ft_review(<stamp>)` | `fulltext-push/review-<stamp>/` | reviewed | access, identity-review and quarantine plans with their verdicts |

After the move (phase B) the raw state and locks stay out of git, the review directories join the `reviewed/` kind, and `checks/` moves
under derived; only these slot values change.

## Phase B: the move (tools/relocate_data.py)

Routed 2026-11-01: no tool, toolkit or script joins a data directory by hand any more (readiness: 0 joins; the check is the `readiness` part of the dry
run, and `route-ok` on a line says why it is not a data path). Code asks `atlas_paths`: `data()`/`data_w()` for a file, `SchoolDir(school[, hdir])` and
`ListingsDir` for a school's directory, `hfile(hdir, name)` for a tool that takes a hierarchy-like directory (the live one follows the layout, a release or
a backup is flat), and `flat_of()` so releases and the export keep the flat names whatever the working layout.

    relocate_data.py                     dry run: moves, conflicts, readiness, preflight, the .gitignore translation
    relocate_data.py --settle-journals   open each sqlite file that has a stale journal once for writing (rolls it back), then plan again
    relocate_data.py --apply --approved-by WHO [--no-commit]
    relocate_data.py --verify [--record FILE]

`--apply` refuses on any conflict, readiness blocker, busy process, sqlite journal, held `.loop.lock` or project Slurm job (listed), then moves every
entry of the table: tracked files by `git mv`, the rest by `os.rename`, a sqlite file's `-journal`/`-wal`/`-shm` with it; translates the 25 `.gitignore`
whitelist lines; sets `DATA_LAYOUT_DEFAULT = 'split'`; regenerates `paths.sh`; and commits the tracked moves with those three edits as one commit.
Every action is appended to `archive/migrations/relocate-data-<date>.jsonl`; `--verify` reads it. Nothing is copied or deleted; there are no compat links.
Not moved: tracked code that lives in hierarchy/ (`rebuild.sh`, `labpage-tools-*`, `gap-tools-*`) and the files the table does not name.
