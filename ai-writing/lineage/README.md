# Advisor-student lineage (owner decision 2026-11-05)

Question: do students' papers become more like their advisor's, and like each other's, after 2023, and does AI use change that?
Report: `ai-writing/diversity/reports/LINEAGE.md` (generated). Code: `lineage_common.py` (paths, links, vectors), `lineage_build.py` (link tables), `lineage_run.py` (measures + estimates per model and kind),
`lineage_fit.py` (fixed-effects estimator, closed-form cluster bootstrap), `lineage_report.py`, `lineage.slurm`, `run_all.sh`.

Re-run on new data with one command: `LINEAGE_HIER=<hierarchy snapshot or live packages> LINEAGE_TAG=<id> [LINEAGE_AI=<detector parquet>] ai-writing/lineage/run_all.sh`.
Inputs are snapshots: copy `hierarchy/<school>/derived/{students.json,student_papers.jsonl.gz,lab_papers.jsonl.gz,pis.json}` into `<snapshot>/<school>/` (write the time to `<snapshot>/SNAPSHOT_TIME`);
a live `hierarchy/<school>/derived/` layout works too. Outputs go to `LINEAGE_OUT/<tag>` (default `ai-writing/data/lineage`, git-ignored). Study labs are strict: PI papers = `lab_papers` rows (PI on the byline).
