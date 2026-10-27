# Code

The tools that built the data, copied as they were run. They are here so every step is inspectable and can be
re-implemented; they are **not** a turnkey pipeline:

- **Paths are the original NFS paths** of the build machine (`/n/fs/similarity/maxent-grpo/...`). The tools expect that
  directory layout, the earlier per-school collections and stage sweeps they read, and the page-capture stores (SQLite
  files of fetched pages) they write and re-verify against. None of those stores, PDFs or raw page captures are
  distributed.
- `claude-schools-20261021/` mirrors `.research-sweeps/claude-schools-20261021/` (the five-school PI hierarchy);
  `princeton-live-20261015/scripts/` holds the site builders that place PIs in departments and mark the atlas's CS scope.
- API keys (OpenAlex `OPENALEX_API_KEY`, Semantic Scholar, CORE `CORE_API_KEY`) were read from environment files that are
  not part of this repository; no key appears in the code.
- **Redactions in the copies:** every e-mail address was replaced. The owner's address (in User-Agent / mailto strings)
  would read `you@example.org`; third-party addresses that appear inside quoted evidence in decision scripts read
  `[email removed]` (so those quotes are no longer byte-exact substrings of their pages). Counts are in
  `MANIFEST.json` (`export.code.redactions`). Nothing else was changed.
- Requirements: Python 3.9+ (some tools were run with 3.11), `requests`, `pdftotext` (poppler) for first-page checks;
  `numpy` for the DBLP dump index.
- `hierarchy/nicknames/names.csv` is the carltonnorthern/nicknames table (Apache-2.0); `extras.csv` adds curated pairs.

## Pipeline order

Steps 1–4 ran per school; most research steps (5–6) were done in review rounds, each followed by a rebuild (step 4).

1. **Census of the computing departments** (who is faculty, in which years, with dated listings)
   - `tools/princeton_census.py`, `tools/epfl_census.py` (+ `epfl_profiles.py`), `tools/berkeley_census.py`
     (+ `berkeley_pubs.py`), `census/build_mit_census.py`, `census/tools/build_cmu_census.py` (+ `build_cmu_report.py`,
     `fetch_listings.py`)
   - `listings/scripts/` — yearly department faculty listings 2016–2026 (live and Wayback): `discover.py`,
     `plan_fetch.py`, `wb.py`, `extract.py`, `match.py`, `build.py`, `verify.py`, `report.py`, per-school `config_*.py`
     → `listings/<school>/listings.json`
   - `tools/listed_not_in_census.py`, `hierarchy/missing-pi-tools/` — faculty a listing names but the census missed
2. **Appointment periods** — `tools/faculty_periods.py` (arrival / departure statements with quotes),
   `hierarchy/period-tools/` (reviewed periods, bridges between listed years, overrides → `hierarchy/census-overrides.json`),
   `hierarchy/period-targets-method.py`
3. **OpenAlex sweep** — `tools/oa_sweep.py` (`hierarchy/run_sweeps.sh`): every 2016–2026 work with an authorship affiliated
   to the school
4. **Build the package** — `tools/pi_hierarchy.py <school>` → `hierarchy/<school>/{pis.json, lab_papers.jsonl.gz,
   students.json, student_papers.jsonl.gz, report.json}` (the rules are in its docstring and in `docs/METHODS.md`)
5. **Gap research** (labs missing papers or students, reviewed with quotes)
   - `tools/diagnose_gaps.py` (why a lab is thin)
   - `hierarchy/gap-tools-*` → `gap-evidence.json` (identity, status, students of gap labs)
   - `hierarchy/few-students-tools*` → `few-students-evidence.json`
   - `hierarchy/labpage-tools-*` → `labpage-evidence.json`, `labpage-pubs.jsonl.gz` (lab people and publication pages)
   - `hierarchy/thesis-tools/` → `thesis-evidence.json` (thesis repositories: adviser fields, 2016–2026)
   - `hierarchy/home-dept-tools/` → `hierarchy/home-departments.json` (reviewed home departments)
6. **CS-related scope** (faculty of any department who publish in CS venues)
   - `tools/dblp_dump_index.py` (+ `.slurm`) — DOI / title index of DBLP's monthly XML dump
   - `tools/cs_related_candidates.py` (+ `.slurm`) — DBLP-heavy school authors not yet in the census
   - `hierarchy/cs-related-tools/`, `hierarchy/<school>/cs-related-tools/` — review, evidence and decisions →
     `census/<school>-additions.json`, `hierarchy/<school>/cs-related-review.json`
7. **Paper recovery** (papers the OpenAlex affiliation misses)
   - `tools/pi_fulltext_affiliation.py` (`hierarchy/run_page1*.sh`) — the PI's own works with no recorded affiliation,
     checked on page 1 of the paper
   - `tools/dblp_recover.py` (`hierarchy/run_dblp_recover*.sh`) — papers on the PI's DBLP page
   - `tools/labpage_recover.py` (`hierarchy/run_labpage_recover.sh`) — papers on the lab's publications page
   - `tools/missing_papers_audit.py` — coverage against DBLP (the independent reference)
8. **Ledgers and profiles** — `tools/zero_paper_ledger.py` (`zero-paper-labs.json`), `tools/lab_paper_copies.py` and
   `fulltext-push/` (local full-text copies used for page-1 checks and the profiles' full-text share; copies not
   distributed), `tools/school_profiles.py` (`school-profiles.json`, `SCHOOL-PROFILES.md`)
9. **Site** — `princeton-live-20261015/scripts/build-cs-hierarchy.py` (departments, the per-school CS view), then
   `build-cs-scope.py` (with `cs_scope.py`, `lazy_atlas.py`): the atlas's CS scope and visibility
10. **Release** — `tools/export_release.py <repo dir>` writes `data/`, `docs/SCHOOL-PROFILES.md`, `MANIFEST.json`,
    the README coverage table and this directory's copies, then runs `tests/verify_release.py`

The wider 300-university atlas (`data/atlas/`) was built earlier by the site's inventory pipelines
(`princeton-live-20261015/scripts/` and `research/`), which are not copied here beyond the two builders above; its
records keep their own provenance fields.

## Adding a school

Build its package (steps 1–8) so that `hierarchy/<school>/pis.json` exists, add it to `SCHOOLS` in
`scripts/build-cs-hierarchy.py` (so the department rule knows it) and to `school_profiles.py`, then rerun
`tools/export_release.py <repo dir>`: the exporter lists every school whose package exists.
