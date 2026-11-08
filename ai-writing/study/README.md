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

## Heterogeneity layer (owner decision 2026-11-08: "please do all of these")
`run_study.sh [ID] hetero` (needs `study_prep.py` output): who is affected? Splits the AI-share, abstract-flag, within-lab and lab-to-school outcomes by PI career tier, student-led vs PI-led papers, field
(theory / systems / ML-AI / other) and the school's GRAS 2025 band. `study_hetero_authors.py` (OpenAlex publication-year histogram per PI, 1 credit each, restartable, writes only under results) ->
`study_hetero_attr.py` (group attributes; `study_hetero_fields.py` is the venue/topic field map) -> `study_hetero.py` (pre/post per group, group-difference DiD, placebo, 12-school and excl.-partial scopes, Holm and BH over the
75-contrast primary family) -> `study_hetero_report.py` (figures + `results/<ID>/heterogeneity/HETEROGENEITY.md`). Tests: `tests/test_study_hetero.py`.
Non-text sameness (owner 2026-11-08): `sameness_*.py` (reference overlap and citation concentration, benchmark/method dictionary, topic concentration, report) -> `results/<id>/sameness/SAMENESS.md`; `run_study.sh <id> sameness`; tests `tests/test_study_sameness.py`.
## Design layers (owner 2026-11-08: separating ChatGPT's effect from long-running trends)
`run_study.sh <id> designs` (needs the prep output): `study_design_prep.py` (OpenAlex affiliation scan of the panel's works, PI tables, exposures) -> `study_design_panel.py` (PI fixed effects, trends, event time)
| `study_design_exposure.py` (continuous DiD on pre-2023 style distance and non-English-country affiliation share, event studies) | `study_design_revision.py` + `_fetch.py` + `_gpu.py` (arXiv v1 against the final
version, main body and main + appendix, reusing the 11-05 AI-in-revision pairs in `ai-writing/revision`) -> `study_design_figures.py`, `study_design_report.py`. Outputs: `results/<id>/designs/` (`tables/`, `figures/`,
`headline.md`, `DESIGNS.md` for the owner). Shared estimator: `study_fe.py` (PI fixed effects, PI-specific trends, CR1 cluster-robust by PI). Tests: `tests/test_study_designs.py`.
Language exposure is the share of a team's authors with an affiliation institution outside US/GB/CA/AU/NZ/IE (OpenAlex institution country); names are never used and nothing is inferred about a person.
