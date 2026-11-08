# 12-school pre/post-ChatGPT homogenization study (owner decision 2026-11-07)

One command: `ai-writing/study/run_study.sh [SNAPSHOT_ID] [snapshot]` (Slurm chain, every job <= 59 min). With `snapshot` it first rebuilds and seals the snapshot from `releases/latest`
(`study_snapshot.py build`, `study_delta_oa.py` for abstracts/topics of papers the earlier build never saw, `study_snapshot.py seal`).

Steps: `study_prep.py` (panel + strict lab membership) -> `study_analyze.py ai|topics|citation|embed|event` -> `study_figures.py` -> `study_report.py` (RESULTS.md).
Inputs only from `studies/homogenization/snapshots/<id>/` (MANIFEST.json lists every file with sha256 and rows; `study_snapshot.py verify` re-hashes).
Outputs in `studies/homogenization/results/<id>/` (tables CSV + parquet, figures, RESULTS.md). Post = 2023-2025, pre = 2016-2022, no 2026; intervals are lab-cluster
bootstrap percentiles stratified by school (`study_labstats.py`). The lab event study reuses `ai-writing/labstudy/event_study.py` and its pre-registration.
Layers computed on the snapshot: AI share (v3, main vs main + appendix, IPW, false-positive correction), topics, embedding diversity (7 models), citation novelty, event study.
Carried over from earlier 9-school runs (not recomputed): lineage, style, AI-in-revision, paired rewrite control (snapshot `carryover/`).
Tests: `tests/test_study_labstats.py`, `tests/test_study_snapshot.py` (pandas; they skip in env/atlas, run in the py310 env).
