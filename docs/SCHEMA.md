# Schema notes for derived per-lab measures

This file documents measures that are computed per lab and carried next to the lab's identity. It is the place to look
for the columns of `lab_ai_scores_2025.json` and for how the research export would carry them.

## Lab AI-use score, 2025 (`ai-writing/dose/lab_ai_score.py`, `method_version` main-body-1)

Output: `AI_SCORES/results/lab_ai/lab_ai_scores_2025.json` = `{meta, labs: {<lab id>: record}}`. A slim copy for the site
(`lab_ai/site/lab_ai_scores_2025.json`) carries only the fields the pages read; `tools/ai_release.py` collects it as the optional
`ai/lab_ai_scores_2025.json` of a release and the site's `import-ai-release.py` registers it as a data asset.

**Key.** The site lab id (`cs-pi-labs` / `cs-hierarchy` lab id, e.g. `mit-pi-lab-adam-belay`). The record also carries `pi_id`
(`<school>:<slug>`, as in `data/schools/<school>/pis.csv`) and `atlas_lab_id` (`atl:l:<school>:<slug>`) where the (school, PI name)
join to the package is unique.

| field | meaning |
|---|---|
| `score` | 0-10, one decimal; null when fewer than `meta.min_papers` papers have a usable main body |
| `interval` | [low, high], 95% bootstrap over the lab's papers (and over the false-alarm floor's papers) |
| `reason` | null, or `insufficient_2025_papers` |
| `n_papers_2025` | papers the site lists for the lab in 2025 |
| `n_full_text` | of those, papers with a stored full text that the splitter read |
| `n_scored` | of those, papers with a usable main body (>= 1,000 main words and >= 3 scored main passages): the papers behind the score |
| `coverage` | `n_scored / n_papers_2025` |
| `main_share` | unweighted mean over the scored papers of the paper's flagged share of main-body passages (before correction) |
| `fulltext_crosscheck` | `{ai_share, n, score_equiv}`: the older full-text `ai_share` (every stored body passage, appendix included when it sat before the references), mean over the lab's 2025 papers, and the same correction applied; reported beside the score, never mixed into it |
| `abstract_crosscheck` | `{flag_share, n}`: share of the lab's 2025 abstracts the v1 abstract detector flags (uncorrected) |
| `kobak_ft` | mean Kobak-style marker-word rate of the scored papers (per 1,000 tokens) |
| `score_ipw` | optional IPW-weighted variant (config `ipw_weights`); null without weights. The displayed score is never weighted |
| `detector`, `method_version`, `generated` | provenance |

Formula: paper share = flagged / scored main-body passages (P(AI) >= the detector's 1% false-alarm cut; passages under 100 words are
dropped); lab share = mean of paper shares; `score = 10 * max(0, (share - floor) / (1 - floor))` with the floor the same
statistic on 2016-2021 papers the detector never trained on. One config point (`lab_ai_score_config.json`, `detector`) selects the detector.

### Proposal (not landed): carrying the score in the research export
`tools/export_release.py` writes `data/schools/<school>/pis.csv` with one row per PI lab (`pi_id`, `lab_id`, `atlas_lab_id`, ...).
Two options, in order of preference:
1. **A per-school `data/schools/<school>/lab_ai_scores.csv`**, columns `pi_id, lab_id, atlas_lab_id, score, interval_low,
   interval_high, n_papers_2025, n_full_text, n_scored, reason, fulltext_ai_share, detector, method_version, generated`, one row per
   lab, null score cells empty. A separate file keeps `pis.csv` stable (its column list is checked by `tests/verify_release.py`) and lets a
   new detector version replace the file without touching the roster. It joins to `pis.csv` on `pi_id`.
2. Appending `ai_use_2025`, `ai_use_2025_low`, `ai_use_2025_high`, `ai_use_2025_n` to `pis.csv`. Simpler for readers, but every
   detector change then rewrites the roster file and its hash.
Either way the export reads the file from the release (`ai/lab_ai_scores_2025.json` is already collected), never from the working path,
and `verify_release.py` should check: one row per `pi_id` in `pis.csv`, `n_scored >= 5` iff `score` is set, 0 <= score <= 10.
