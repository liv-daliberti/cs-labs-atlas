# Writing-style homogenization (owner decision 2026-11-05)

Question: do papers sound more alike, apart from topic? Report: `ai-writing/diversity/reports/STYLE-HOMOGENIZATION.md` (generated).
Code: `style_features.py` (features of one text: sentence length, MTLD, function words, punctuation, hedging, readability, Kobak rate; no POS: spaCy is not in the study env), `style_extract.py` (features per paper,
resumable), `style_analyze.py` (topic residualization, dispersion/convergence, AI link, all-AI bound, labs), `style_report.py`, `style.slurm`, `run_all.sh`.

One command: `STYLE_TAG=<id> [STYLE_AI=<detector parquet>] [STYLE_FULLTEXT_DB=<texts db with the section-split main body>] ai-writing/style/run_all.sh`.
Outputs go to `STYLE_OUT/<tag>` (default `ai-writing/data/style`, git-ignored): `features_*.parquet`, `tables/*.csv`.
