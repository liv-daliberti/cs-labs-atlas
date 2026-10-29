# AI-written text and lab research diversity, v2 (full papers)

Owner request, 2026-10-22:

1. Use the full paper, not only the abstract.
2. Use a bigger Qwen model.
3. Explore diversity in many different ways.
4. Show, per lab, how the amount of AI usage relates to diversity.

Scope: the CS PI labs of Princeton, CMU, EPFL, MIT and Berkeley (`hierarchy/<school>/lab_papers.jsonl.gz`), 2016–2026.

## 1. AI usage: what each paper's text says

| Level | Detector | Training data |
|---|---|---|
| Abstract (v1, kept) | ModernBERT-large, title + abstract | Pre-ChatGPT human abstracts vs. their polish / outline-then-expand versions by Qwen2.5-3B, Qwen2.5-7B and, new, **Qwen2.5-72B** |
| Paragraph (v2, new) | ModernBERT-large on single paragraphs of the full text | Pre-ChatGPT body paragraphs (2016–2021 lab papers) vs. Qwen2.5-72B / 7B rewrites of them: polish, paraphrase, and write-from-notes |

- **Validation:**
  - Leave one generator out (train without Qwen-72B, test on it).
  - A 1% false-positive threshold set on held-out human text.
  - The flagged share in real 2016–2021 papers must stay near 1%.
- **Per-paper variables:**
  - `p_ai_abstract`: the abstract score.
  - `ai_share`: the share of a paper's body paragraphs flagged. This is a dose, not a yes/no.
  - `ai_any`: at least one flagged section.
- **Per-lab variable** (per period and per year): the lab's mean `ai_share`, and its share of papers with `ai_share` ≥ 0.25.

## 2. Diversity, many ways

Every set-level measure is computed on equal-size random draws of a lab's papers. The draws are 1,000 per lab-period, n = the smallest group being compared, at least 5. Size alone therefore never makes a lab look more diverse.

### Semantic (SPECTER2 title + abstract; and the full text as the mean of paragraph embeddings)

- **S1 knowledge extent:** the largest distance from the centroid (Hao et al. M8).
- **S2 dispersion:** the mean distance from the centroid.
- **S3 mean pairwise cosine distance.**
- **S4 Vendi score:** the effective number of distinct papers, from the similarity matrix's eigenvalues.
- **S5 topic entropy over 50 global k-means clusters,** and **S6** its exponential (the effective number of topics).
- **S7 Rao–Stirling diversity:** topic shares weighted by the distances between topics.
- **S8 within-paper spread:** the dispersion of one paper's own paragraph embeddings (full text only).

### Lexical and stylistic (full text)

- **L1 MATTR:** the type–token ratio over a moving 1,000-token window.
- **L2 unigram entropy.**
- **L3 homogeneity:** the mean pairwise TF-IDF cosine between a lab's papers. Higher means more alike.
- **L4 n-gram novelty:** the share of a paper's trigrams new to the lab, against its own earlier papers.
- **L5 sentence-length mean and SD,** and **L6** the spread of readability scores.
- **L7 LLM-marker words:** the rate of Kobak et al.'s excess style words. This is a check on the detector, not a diversity measure.
- **L8 compression diversity:** the gzip size of a lab's concatenated texts against the sum of their individual sizes.

### Novelty against the field

- **N1:** the distance to the nearest paper of the previous year in a fixed-size background sample of arXiv CS.
- **N2:** the share of a lab's papers in topic clusters new to the lab.

### Citations (S2 reference lists, where held)

- **C1:** the entropy of the references' venues.
- **C2:** the mean Jaccard overlap of reference lists within the lab.
- **C3:** the spread of reference ages.
- **C4:** the share of self-lab references.

## 3. Analyses

1. **Lab level:**
   - The change in each measure, post (2023–2026) minus pre (2016–2022), plotted against the lab's post-period AI usage.
   - A robust regression with lab-size and school controls.
   - One standardized slope per measure, shown as a forest plot with 95% CIs.
2. **Within lab:** papers with more and less AI in the same lab-year, compared on the paper-level measures: distance to the lab centroid, N1, L1, L4 and S8.
3. **Placebo:** the same lab-level analysis with a fake break inside the pre-period (2019 or 2020). Its slopes give the null spread.
4. **Topic control:** the same with topic-cluster fixed effects, so that "AI users work on LLM topics" cannot drive a result alone.
5. **Per school,** and Figure 3 redone on full texts.

## Outputs

- `lab_diversity.csv`: one row per lab × period, with every measure, the n of papers, and AI usage.
- `figures/`:
  - a per-lab scatter for each measure;
  - the forest plot;
  - Figure 3 on full texts;
  - the flagged share by year (abstract and paragraph detectors).
- `REPORT.md`: numbers, caveats and placebo results.
