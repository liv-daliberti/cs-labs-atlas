# Michigan, stage 7: papers and links

Date: 2026-10-30. Gate: **not passed**.
- The `papers` check has 3 zero-paper labs marked `fix`.
- The `links` check has 89 open items, which wait on stage 6's students.
- The evidence check is not run for an onboarding school.

The builder path is the released schools' path. Stage 6 has not passed (source-limited), so this stage was run to
measure and not taken further: per the coordinator's instruction, stages 8–9 were not started.

## What was done (Michigan only)
1. `tools/pi_hierarchy.py michigan`, the first build, which anchors the OpenAlex ids.
2. `tools/pi_fulltext_affiliation.py works michigan`: 405 author ids, 24,343 works (OpenAlex; credit floor 150).
3. `tools/pi_fulltext_affiliation.py pdf michigan`: 1,534 page-1 candidates, 571 pages read from the arXiv bulk copy or
   local copies.
4. `tools/dblp_dump_persons.py`, regenerated with Michigan's PIs: 3,751 persons, 272,975 records.
5. `tools/dblp_recover.py michigan`: 1,648 DBLP records not yet lab papers. 395 accepted (255 OpenAlex authorship, 139
   arXiv page 1, 1 open proceedings), 555 at another institution, 698 none.
6. `tools/periods_school.py gaps|extend michigan` (stage 4), then builds 3 and 4.
7. `tools/student_audit.py` for all seven schools; the chain audit in-process; `tools/sweep_check.py michigan` passes.
- **Not run:** `labpage_recover.py`. Michigan has no `labpage-pubs.jsonl.gz`, and each released school built its
  lab-publication pages with its own `labpage-tools-*` script. A generic protocol tool is debt.

## Counts (build 4, 2026-10-30 ~15:00)
- Lab papers: 14,149. Student–paper links: 3,175. 288 PIs and 288 labs; 278 labs have papers.
- Funnel: `outside_appointment` 1,967 (2,611 before the profile years); DBLP-recovered lab papers 262;
  `school_via_unaffiliated_byline_advisee` 190; `unaffiliated_page1_elsewhere` 7; 84 unaffiliated rows not read on page 1.
- Chain checks:

| check | total | pass | explained | open |
|---|---|---|---|---|
| coverage | 752 | 137 | 615 | 0 |
| pi | 288 | 288 | 0 | 0 |
| students | 288 | 117 | 0 | 171 |
| papers | 288 | 278 | 0 | 10 |
| links | 683 | 525 | 69 | 89 |
| copies | 12455 | 0 | 0 | 12455 |
| one_person | 683 | 683 | 0 | 0 |

- **Zero-paper labs** (`hierarchy/zero-paper-review.json`, `michigan`):
  - `zero_is_right` (7): Compton (emeritus), Pollack (left in 2017), Pilanci (see stage 4), Jalani Williams (from 2025),
    Seah Kim (from Fall 2026), Ankit Goyal (2026), Gary Olson (no school work).
  - `fix` (3): Steven Abney (identity), John Leslie King (UMSI 2016–2025 unproven), A. Galip Ulsoy (2016–2023 unproven).
- **Copies:** 12,455 lab-paper rows and 0 local copies. Stage 8 has not run: the catalog is empty and
  `fulltext-push/michigan-collector.slurm` is prepared. `sbatch --test-only` gives node915 with no preemption; the job
  was not submitted.

## Gate
- `papers`: 278/288; 7 reviewed zeros, 3 `fix`.
- `links`: 525 pass, 69 explained, 89 open. These are students without a co-authored lab paper. `link_diagnosis.py`
  has not been run for Michigan.
- Evidence check: not run. It reads the released schools.

**Not passed.**
