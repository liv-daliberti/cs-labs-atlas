"""Render DATA/results (cn_analysis.py) into ai-writing/diversity/reports/CITATION-NOVELTY.md. Every number comes from the tables; nothing is typed in.

  cn_report.py [--out PATH]
"""
import argparse
import json
import sqlite3
import time

import numpy as np
import pandas as pd

import cn_common as C

NAMES = {'z_p10': 'Uzzi z, 10th percentile (low = atypical)', 'z_med': 'Uzzi z, median (high = conventional)', 'cd1': 'CD1 disruption (low = consolidating when high)',
         'cd_av': 'CD to end-2025 (variable window)', 'cd2': 'CD2', 'cd3': 'CD3', 'cd5': 'CD5', 'rs_sub': 'Rao-Stirling (subfields)', 'rs_field': 'Rao-Stirling (fields)',
         'h_venue': 'cited-venue entropy (bits)', 'h_sub': 'cited-subfield entropy (bits)', 'jac': 'lab reference overlap, Jaccard', 'cos': 'lab reference overlap, cosine',
         'jac_prev': 'overlap with lab\'s previous 3 years, Jaccard', 'cos_prev': 'overlap with previous 3 years, cosine', 'ref_age_med': 'median reference age (years)'}
SCHOOLS = ['berkeley', 'cmu', 'epfl', 'gatech', 'michigan', 'mit', 'princeton', 'stanford', 'uchicago']


def fmt(b, lo, hi, d=3):
    if b is None or not np.isfinite(b):
        return 'n/a'
    return f'{b:.{d}f} [{lo:.{d}f}, {hi:.{d}f}]' if np.isfinite(lo) else f'{b:.{d}f}'


def md(df, cols=None):
    cols = cols or list(df.columns)
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    for r in df[cols].itertuples(index=False):
        out.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    return '\n'.join(out)


def load(name):
    p = C.RESULTS / name
    return pd.read_parquet(p) if p.exists() else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(C.REPORTS / 'CITATION-NOVELTY.md'))
    a = ap.parse_args()
    cov, tr, did, pre, pdose, pboot = (load(n) for n in ('coverage.parquet', 'trends.parquet', 'did_citation.parquet', 'prepost_labs.parquet', 'paper_dose.parquet', 'paper_dose_boot.parquet'))
    db = sqlite3.connect(f'file:{C.DB}?mode=ro', uri=True)
    info = dict(db.execute('select k, v from info').fetchall())
    nmeta = db.execute('select count(*) from meta').fetchone()[0]
    db.close()
    L = []
    P = L.append
    P('# Citation-based novelty and diversity of lab papers (Experiment A)\n')
    P(f'Generated {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} by `ai-writing/citnovelty/cn_report.py`; data: OpenAlex bulk snapshot {info.get("snapshot_date")} (S3, no API credits), '
      f'{nmeta:,} referenced works characterised; sampling factor for n_k = {info.get("sample_mod")}. Years 2016-2025 only (owner rule); 2026 is in no table.\n')
    # ---- coverage
    P('## 1. Data coverage\n')
    al = cov[cov['school'] == 'all'].set_index('year')
    P('Share of lab papers with a usable reference list (>= 5 references in the snapshot) and with each measure, by year (all schools):\n')
    P(md(al.reset_index().assign(**{c: (al[c].to_numpy() * 100).round(1) for c in ('refs5', 'meta', 'z', 'cd1', 'cd3', 'cd5', 'rs')}).round({'mean_refs': 1}),
         ['year', 'papers', 'refs5', 'meta', 'z', 'cd1', 'cd3', 'cd5', 'rs', 'mean_refs']) + '\n')
    P('(percentages; `refs5` papers with >= 5 listed references; `meta` of those references characterised; `z` Uzzi z defined (>= 10 venue pairs); `cd1/cd3/cd5` disruption defined with a window that fits '
      'inside 2025 and >= 3 citing works; `rs` Rao-Stirling defined.) **Reference lists of recent papers are less complete in OpenAlex** (the share with >= 5 references falls after 2021): all trend '
      'comparisons below use year fixed effects, but a drop in coverage is a selection risk for the post-2022 years, so every post-period result has a `refs >= 15` robustness row.\n')
    # ---- trends
    P('## 2. Trends by school, 2016-2025\n')
    P('Mean per paper (95% interval); papers with the measure defined. CD windows: CD1 needs year <= 2024, CD3 <= 2022, CD5 <= 2020 (a window that fits); CD to end-2025 uses every citation up to 2025, '
      'so it is comparable only within a year.\n')
    for m in ('z_p10', 'z_med', 'cd1', 'cd3', 'cd5', 'rs_sub', 'h_venue'):
        t = tr[(tr['measure'] == m) & tr['year'].isin([2016, 2018, 2020, 2022, 2024, 2025])]
        if t['mean'].notna().sum() == 0:
            continue
        P(f'### {NAMES.get(m, m)}\n')
        rows = []
        for s in ['all'] + SCHOOLS:
            r = {'school': s}
            for y in (2016, 2018, 2020, 2022, 2024, 2025):
                x = t[(t['school'] == s) & (t['year'] == y)]
                r[y] = fmt(x['mean'].iloc[0], x['lo'].iloc[0], x['hi'].iloc[0]) if len(x) and np.isfinite(x['mean'].iloc[0]) else '-'
            rows.append(r)
        P(md(pd.DataFrame(rows)) + '\n')
    # ---- labs
    P('## 3. Within labs, before and after 2023\n')
    P('Lab-year means (lab fixed effects, year fixed effects; 2022 dropped; cluster bootstrap over labs). `post` = 2023-2025 against 2016-2021 within the same lab; placebo breaks at 2019-2021 use 2016-2021 only. '
      '`sd` is the standard deviation of the lab-year outcome.\n')
    if pre is not None:
        t = pre.copy()
        t['estimate'] = [fmt(b, lo, hi) for b, lo, hi in zip(t['beta'], t['lo'], t['hi'])]
        t['outcome'] = t['outcome'].map(lambda x: NAMES.get(x, x))
        P(md(t.round({'sd': 3}), ['outcome', 'spec', 'estimate', 'n', 'labs', 'sd']) + '\n')
    P('### Lab AI dose and the change (difference-in-differences)\n')
    P('y(lab, year) = lab FE + year FE + b * Post * Dose_lab, Dose = the lab\'s mean `ai_share` of 2023-2025 full-text papers (>= 4 scored; `abs_dose`: flagged-abstract share, no full-text selection). '
      'b is per unit of dose (0 to 1). Placebo rows: the same with breaks at 2019, 2020, 2021 inside 2016-2021 (detector noise as "dose"). A post estimate counts only if it lies beyond the placebo spread.\n')
    if did is not None:
        d = did[did['spec'].isin(['did', 'placebo2019', 'placebo2020', 'placebo2021', 'within_lab_year'])].copy()
        d['estimate'] = [fmt(b, lo, hi) for b, lo, hi in zip(d['beta'], d['lo'], d['hi'])]
        d['outcome'] = d['outcome'].map(lambda x: NAMES.get(x, x))
        wide = d.pivot_table(index=['outcome', 'dose'], columns='spec', values='estimate', aggfunc='first').reset_index()
        P(md(wide.fillna('-')) + '\n')
    # ---- paper-level
    P('## 4. A paper\'s AI dose and its citation measures\n')
    P('Paper-level fits of the measure on `ai_share` (full-text-scored papers; per unit of share, 0 to 1), 2023-2025 (`post`) and the 2017-2021 placebo (`pre`: the dose is detector noise). Controls as the dose report: '
      'year, school and OpenAlex-topic FE, log team size, venue type, open-access status, and log(number of references); within-lab = lab x year FE. Intervals clustered by first lab.\n')
    if pboot is not None:
        t = pboot.copy(); t['estimate'] = [fmt(b, lo, hi) for b, lo, hi in zip(t['beta'], t['lo'], t['hi'])]
        t['y_sd'] = t['y_sd'].round(3)
        t['measure'] = t['measure'].map(lambda x: NAMES.get(x, x))
        P(md(t.pivot_table(index=['measure', 'design', 'n', 'y_sd'], columns='period', values='estimate', aggfunc='first').reset_index().fillna('-')) + '\n')
    if pdose is not None:
        P('### All designs (post period, `ai_share`; robustness: no-LLM-topic papers, topic x year FE, papers with >= 15 references)\n')
        t = pdose[(pdose['period'] == 'post') & (pdose['exposure'] == 'ai_share')].copy()
        t['estimate'] = [fmt(b, lo, hi) for b, lo, hi in zip(t['beta'], t['lo'], t['hi'])]
        t['measure'] = t['measure'].map(lambda x: NAMES.get(x, x))
        P(md(t.pivot_table(index='measure', columns='design', values='estimate', aggfunc='first').reset_index().fillna('-')) + '\n')
        P('### Same, placebo period (2017-2021)\n')
        t = pdose[(pdose['period'] == 'pre') & (pdose['exposure'] == 'ai_share')].copy()
        t['estimate'] = [fmt(b, lo, hi) for b, lo, hi in zip(t['beta'], t['lo'], t['hi'])]
        t['measure'] = t['measure'].map(lambda x: NAMES.get(x, x))
        P(md(t.pivot_table(index='measure', columns='design', values='estimate', aggfunc='first').reset_index().fillna('-')) + '\n')
        P('### Abstract-flag exposure (post period; every paper with an abstract, no full-text selection)\n')
        t = pdose[(pdose['period'] == 'post') & (pdose['exposure'] == 'flag_abstract') & pdose['design'].isin(['raw', 'pooled', 'withinlab'])].copy()
        t['estimate'] = [fmt(b, lo, hi) for b, lo, hi in zip(t['beta'], t['lo'], t['hi'])]
        t['measure'] = t['measure'].map(lambda x: NAMES.get(x, x))
        P(md(t.pivot_table(index='measure', columns='design', values='estimate', aggfunc='first').reset_index().fillna('-')) + '\n')
    # ---- method and limits
    P('## 5. Method and limits\n')
    P('- **Data.** One streamed pass over all works of the OpenAlex snapshot (`cn_stream.py`; 128 CPU tasks, no API credits). For each lab paper: its reference list (from `oa_extra.sqlite`), the year, venue '
      '(source id and type) and primary subfield/field of every referenced work, and the citing works by year offset.')
    P('- **Atypicality (Uzzi et al. 2013).** Venue pairs are those of OpenAlex sources typed journal, conference or book series (repositories and unknown sources dropped). The null shuffles venue labels '
      'over the reference slots of the lab papers of the same year (10 permutations): it keeps every paper\'s reference count and every venue\'s total count. The reference population is the lab-paper set, not all of science, '
      'so z measures atypicality relative to these schools\' own citing habits.')
    P('- **Disruption (CD_w).** n_i and n_j are exact over all citing works; n_k (works citing a reference of the paper but not the paper) is estimated from the works whose OpenAlex number is divisible by the '
      'sampling factor (scaled by it, minus n_j), so CD carries sampling noise that shrinks with n_k; windows count only if year + w <= 2025; at least 5 references and 3 citing works are required (papers with '
      'fewer citations drop out, which selects on citation count). CD5 exists only for 2016-2020 papers, CD1 for 2016-2024.')
    P('- **Rao-Stirling.** Distance between subfields (fields) = 1 - cosine similarity of their co-occurrence profiles over all lab-paper reference lists (a fixed matrix, all years).')
    P('- **Lab overlap.** Mean over pairs of a lab\'s papers in a year (>= 3 papers with >= 5 references) of Jaccard and cosine (bibliographic coupling normalised) of reference sets; `prev` compares with the lab\'s papers of the previous three years.')
    P('- **Citation time and coverage.** Citation-based measures need citation time and complete reference lists: the post-2022 years are the weakest. CD for 2025 papers rests on one year of citations; OpenAlex reference '
      'lists of recent papers are less complete (section 1). `AI dose` exists only for full-text papers (selection; the abstract-flag rows cover every paper).')
    C.REPORTS.mkdir(parents=True, exist_ok=True)
    open(a.out, 'w').write('\n'.join(L) + '\n')
    print(json.dumps(dict(report=a.out, lines=len(L))))


if __name__ == '__main__':
    main()
