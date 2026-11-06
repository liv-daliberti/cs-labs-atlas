"""Render DATA/results/revision_<detector>_* (rv_analysis.py) into ai-writing/diversity/reports/AI-IN-REVISION.md. Every number comes from the tables.

  rv_report.py --detector v2 [--out PATH]
"""
import argparse
import json
import time

import numpy as np
import pandas as pd

import rv_common as C

LABEL = {'dai': 'flagged-passage share (ai_share)', 'dst': 'strict share (p >= 0.5)', 'dab': 'abstain band (flagged, not strict)', 'daf': 'abstract flag (v1 abstract detector)',
         'dpa': 'mean P(AI) of the abstract (detector, uncalibrated for abstracts)', 'dko': 'Kobak style words per 1,000 tokens (abstract)'}


def fmt(b, lo, hi, d=3):
    if b is None or not np.isfinite(b):
        return 'n/a'
    return f'{b:.{d}f} [{lo:.{d}f}, {hi:.{d}f}]' if np.isfinite(lo) else f'{b:.{d}f}'


def md(df, cols=None):
    cols = cols or list(df.columns)
    df = df.rename(columns=str); cols = [str(c) for c in cols]
    out = ['| ' + ' | '.join(cols) + ' |', '|' + '---|' * len(cols)]
    for r in df[cols].itertuples(index=False):
        out.append('| ' + ' | '.join(str(x) for x in r) + ' |')
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--detector', default='v2')
    ap.add_argument('--out', default=str(C.REPORTS / 'AI-IN-REVISION.md'))
    a = ap.parse_args()
    pref = C.RESULTS / f'revision_{a.detector}'
    fun = json.load(open(f'{pref}_funnel.json'))
    L, P = [], None
    P = L.append
    P(f'# AI added in revision: arXiv v1 against the later version (Experiment B, detector {a.detector})\n')
    dj = fun["detector"]
    if a.detector == 'v3':
        P(f'Generated {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} by `ai-writing/revision/rv_report.py`. Detector v3 (main body only, `fulltext_sections.split_text` for the arXiv texts and the v3 container for the stored copies; '
          f'abstained passages excluded): flagged passage = v3 score z >= {dj["threshold"]:.2f} (0.3% false-alarm rate on calibration passages; human passages wrongly flagged 0.30%, 0.27-0.32%), '
          f'strict = z >= {dj["strict"]} (P(AI) >= 0.5); passages between the two cuts are the abstain band (flagged, not confident). '
          'All intervals: cluster bootstrap over first labs. Years end at 2025. v3 shares are not comparable in level with the v2 report.\n')
    else:
        P(f'Generated {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} by `ai-writing/revision/rv_report.py`. Detector {a.detector}: flagged passage = P(AI) >= {dj["threshold"]:.3g} '
          f'(1% passage false-positive rate by design on pre-ChatGPT text), strict = P(AI) >= {dj["strict"]}; passages between the two cuts are the abstain band. '
          'All intervals: cluster bootstrap over first labs. Years end at 2025.\n')
    P('## Summary\n')
    for kind in ('S', 'A'):
        try:
            ct = pd.read_parquet(f'{pref}_{kind}_contrasts.parquet'); cl = pd.read_parquet(f'{pref}_{kind}_cells.parquet')
        except FileNotFoundError:
            continue
        r = ct[(ct['outcome'] == 'dai') & (ct['treat'] == 'pre_post') & (ct['ctrl'] == 'pre_pre') & (~ct['matched'].astype(bool))]
        m = ct[(ct['outcome'] == 'dai') & (ct['treat'] == 'pre_post') & (ct['ctrl'] == 'pre_pre') & (ct['matched'].astype(bool))]
        c = cl[(cl['outcome'] == 'dai') & (cl['cell'] == 'pre_post')]
        if len(r) and len(c):
            r, c = r.iloc[0], c.iloc[0]
            P(f'**Kind {kind}, v1 before Dec 2022 and later text after:** {int(c["n"])} pairs; mean change in flagged-passage share {fmt(c["mean"], c["lo"], c["hi"], 4)} '
              f'(v1 level {c["v1_mean"]:.3f}); against the pre_pre baseline {fmt(r["diff"], r["lo"], r["hi"], 4)}'
              + (f', matched {fmt(m.iloc[0]["diff"], m.iloc[0]["lo"], m.iloc[0]["hi"], 4)} ({int(m.iloc[0]["treat_kept"])} of {int(m.iloc[0]["treat_total"])} pairs kept)' if len(m) else '') + '. Shares are fractions of passages (0.01 = one point).')
    P(f'Every difference is a fraction of passages; the detector flags about {"0.3" if a.detector == "v3" else "1"}% of human passages by design, so effects of a few tenths of a point are near its floor. Details, strict cut, abstract and Kobak rows below.\n')
    P('## 1. Pairs\n')
    P('Pair kinds: **S** = arXiv v1 (public cloud-mirror copy) against the lab paper\'s stored full text (the version our stores captured), dated by its publication date; '
      '**A** = arXiv v1 against the latest arXiv version in the mirror (dated by the margin stamp). The mirror does not hold late revisions of old arXiv papers (a 2022 paper\'s latest mirrored '
      'version is uploaded within the month of v1), so only kind S can show "v1 before Dec 2022, final after".\n')
    rows = []
    for k, f in fun['funnel'].items():
        rows.append(dict(kind=k, pairs_scored=f['pairs_scored'], v1_title_found=f['title_found_v1'], same_work=f['same_work'], dated=f['dated'], valid=f['valid'], valid_to_2025=f['valid_to_2025'],
                         cells=', '.join(f'{c}: {n}' for c, n in sorted(f['cells'].items()))))
    P(md(pd.DataFrame(rows)) + '\n')
    P('Filters (exact pairing): the arXiv record\'s DOI equals the paper\'s DOI with compatible titles, or the paper\'s own arXiv DOI, or an identical normalised title with a single arXiv record within -1 to +3 years; '
      'the v1 PDF shows the arXiv title on page 1; >= 10 passages and >= 1,000 body words in both texts; >= 20% of v1\'s 8-word shingles occur in the later text (same work); the later text is dated. '
      'Cell names: v1 period _ final period, `pre` = before 1 Dec 2022 (final of kind S: before 1 Jan 2023; papers published in Dec 2022 are left out as the transition month).\n')
    for kind in ('S', 'A'):
        try:
            cells = pd.read_parquet(f'{pref}_{kind}_cells.parquet')
        except FileNotFoundError:
            continue
        P(f'## 2{kind}. Change in AI wording, kind {kind}\n')
        P('Mean change (later text minus v1) per cell, with `v1` the mean level in v1; `pre_pre` is the revision-noise and false-positive baseline (both texts predate ChatGPT: any change is revision, extraction '
          'and detector noise, since the flagged share of human text is about 1% by design).\n')
        t = cells.copy(); t['change'] = [fmt(b, lo, hi) for b, lo, hi in zip(t['mean'], t['lo'], t['hi'])]; t['v1'] = t['v1_mean'].round(3)
        t['outcome'] = t['outcome'].map(LABEL)
        P(md(t.pivot_table(index='outcome', columns='cell', values='change', aggfunc='first').reset_index().fillna('-'), None) + '\n')
        n = t[t['outcome'] == LABEL['dai']][['cell', 'n', 'v1']]
        P('Pairs and mean v1 level by cell (flagged share):\n')
        P(md(n) + '\n')
        try:
            ct = pd.read_parquet(f'{pref}_{kind}_contrasts.parquet')
            P(f'### Contrasts, kind {kind}\n')
            P('Difference between cells in the mean change. `matched`: control pairs reweighted to the treated pairs\' school x v1-year bin x revision-lag bin distribution (coarsened exact; strata without control are dropped, '
              '`kept` = treated pairs retained).\n')
            c = ct.copy(); c['diff (95% CI)'] = [fmt(b, lo, hi) for b, lo, hi in zip(c['diff'], c['lo'], c['hi'])]
            c['outcome'] = c['outcome'].map(LABEL); c['kept'] = c['treat_kept'].astype(str) + '/' + c['treat_total'].astype(str)
            c['contrast'] = c['treat'] + ' - ' + c['ctrl']
            P(md(c, ['outcome', 'contrast', 'matched', 'diff (95% CI)', 'n_treat', 'n_ctrl', 'kept']) + '\n')
        except FileNotFoundError:
            pass
        try:
            rg = pd.read_parquet(f'{pref}_{kind}_regression.parquet')
            P(f'### Regression, kind {kind}\n')
            P('Change = cell dummies (pre_pre is the base) + controls: school FE, field FE, revision lag (months), log length ratio, v1 level; clustered by first lab.\n')
            rg['estimate'] = [fmt(b, lo, hi) for b, lo, hi in zip(rg['beta'], rg['lo'], rg['hi'])]; rg['outcome'] = rg['outcome'].map(LABEL)
            P(md(rg.pivot_table(index=['outcome', 'term'], columns='spec', values='estimate', aggfunc='first').reset_index().fillna('-')) + '\n')
        except FileNotFoundError:
            pass
        try:
            ad = pd.read_parquet(f'{pref}_{kind}_added.parquet')
            P(f'### Pairs where AI looks added, kind {kind}\n')
            ad['share'] = [fmt(b * 100, lo * 100, hi * 100, 1) for b, lo, hi in zip(ad['share'], ad['lo'], ad['hi'])]
            P(md(ad.pivot_table(index='rule', columns='cell', values='share', aggfunc='first').reset_index().fillna('-')) + '\n')
            P('(per cent of pairs; the `pre_pre` share is the false-positive floor of the rule.)\n')
        except FileNotFoundError:
            pass
        try:
            pv = pd.read_parquet(f'{pref}_{kind}_pivot.parquet')
            pv = pv[(pv['count'] >= 20)]
            P(f'### Mean change in flagged share by year of v1 (rows) and year of the later text (columns), kind {kind}, cells with >= 20 pairs\n')
            P(md(pv.pivot_table(index='y1', columns='y2', values='mean').round(3).fillna('').reset_index().astype(str)) + '\n')
        except Exception:
            pass
    P('## 3. Reading and limits\n')
    P('- A positive `pre_post - pre_pre` difference is the extra rise in flagged wording between v1 and a later text when the later text was written in the ChatGPT era, over the rise that revision alone gives. '
      'For kind S the later text is the stored (usually published) version, whose extraction differs from the arXiv PDF\'s; `pre_pre` carries the same mismatch, so the contrast removes it to first order.')
    P('- v1 of a post-2022 paper may already contain AI wording, so `post_post` changes understate use; `pre_post` begins from human v1 texts and is the cleaner contrast, but its pairs sit mostly in 2022-2023 '
      '(the earliest months of use), where the flagged-share rise is small.')
    P(f'- The passage detector flags about {"0.3" if a.detector == "v3" else "1"}% of human passages by design; with roughly 60 passages per paper a single paper\'s change is noisy, so conclusions rest on cell means and the share of pairs, not on single papers.')
    P('- Kobak style words in abstracts are detector-free; for kind S the later abstract is OpenAlex\'s (the published abstract), for A the arXiv PDF\'s, extracted by a heading rule (`Abstract` ... `Introduction`).')
    C.REPORTS.mkdir(parents=True, exist_ok=True)
    open(a.out, 'w').write('\n'.join(L) + '\n')
    print(json.dumps(dict(report=a.out, lines=len(L))))


if __name__ == '__main__':
    main()
