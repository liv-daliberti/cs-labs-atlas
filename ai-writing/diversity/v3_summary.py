"""V3-SUMMARY.md: the detector-v3 rerun of every AI-detection result, v2 and v3 side by side (owner 2026-11-05).

usage: v3_summary.py [--out reports/V3-SUMMARY.md]   (run with the study interpreter; reads the v2 and v3 containers and the rerun outputs, all git-ignored data)
Sections that are numbers (how much AI, dose versus novelty, lab scores) are generated here from the tables; the sections that quote the experiment reports
(lineage, style, topics, event study, citation novelty, revision) are generated from each report's own summary bullets, v2 next to v3, and the
reading is written by hand in HANDWRITTEN below. v3 shares are NOT comparable in level with v2's (0.3% against 1% threshold, abstain rule): compare direction only.
"""
import argparse
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path('/n/fs/resemble/homogenizing-science')
D = ROOT / 'code' / 'ai-writing' / 'data'
V2, V3 = D / 'ai-scores', D / 'ai-scores-v3'
WT = ROOT / 'worktrees'
YEARS = range(2016, 2026)
rng = np.random.default_rng(1)


def boot(x, B=500):
    x = np.asarray(x, float)
    m = x.mean()
    idx = rng.integers(0, len(x), (B, len(x)))
    lo, hi = np.percentile(x[idx].mean(1), [2.5, 97.5])
    return m, lo, hi


def pc(m, lo, hi, d=1):
    return f'{100 * m:.{d}f}% [{100 * lo:.{d}f}, {100 * hi:.{d}f}]'


def papers(path):
    db = sqlite3.connect(f'file:{path}/ai_scores.sqlite?mode=ro', uri=True)
    df = pd.read_sql('select paper_id, home_school, year, ai_share from papers', db)
    db.close()
    return df[df['year'].between(2016, 2025) & df['ai_share'].notna()]


def how_much():
    a, b = papers(V2), papers(V3)
    v3y = pd.read_parquet(V3 / 'results' / 'v3_yearly_school.parquet')
    L = ['| year | v2: papers >= 25% flagged | v3: papers >= 25% flagged | v2: mean dose | v3: mean dose | v3 abstained passages | v3 mean dose, main + appendix |', '|---|---|---|---|---|---|---|']
    for y in YEARS:
        ra, rb = a[a['year'] == y]['ai_share'], b[b['year'] == y]['ai_share']
        r3 = v3y[(v3y['school'] == 'all') & (v3y['year'] == y)].iloc[0]
        L.append(f"| {y} | {pc(*boot(ra >= .25), 2)} (n={len(ra):,}) | {pc(*boot(rb >= .25), 2)} (n={len(rb):,}) | {pc(*boot(ra), 2)} | {pc(*boot(rb), 2)} | "
                 f"{100 * r3['abstained_share_main']:.1f}% | {100 * r3['mean_dose_with_appendix']:.2f}% |")
    S = ['| school (home) | v2 2025: >= 25% flagged | v3 2025: >= 25% flagged | v3 n | v3 2023 | v3 2024 |', '|---|---|---|---|---|---|']
    for s in sorted(b['home_school'].dropna().unique()):
        ra, rb = a[(a['year'] == 2025) & (a['home_school'] == s)]['ai_share'], b[(b['year'] == 2025) & (b['home_school'] == s)]['ai_share']
        r23 = b[(b['year'] == 2023) & (b['home_school'] == s)]['ai_share']; r24 = b[(b['year'] == 2024) & (b['home_school'] == s)]['ai_share']
        va = pc(*boot(ra >= .25)) + f' (n={len(ra)})' if len(ra) >= 30 else f'n={len(ra)}, too few'
        S.append(f"| {s} | {va} | {pc(*boot(rb >= .25)) if len(rb) >= 30 else 'too few'} | {len(rb)} | {pc(*boot(r23 >= .25)) if len(r23) >= 30 else '-'} | {pc(*boot(r24 >= .25)) if len(r24) >= 30 else '-'} |")
    return '\n'.join(L), '\n'.join(S)


def fits(path):
    out = {}
    for f in sorted(Path(path).glob('boot_*_abstract.parquet')):
        out[f.name.split('_abstract')[0][5:]] = pd.read_parquet(f)
    return out


def dose_novelty():
    f2, f3 = fits(V2 / 'results'), fits(V3 / 'results')
    rows = ['| model | design | v2 post | v3 post | v2 placebo 2017-21 | v3 placebo 2017-21 (out of sample) | direction |', '|---|---|---|---|---|---|---|']
    for m in f3:
        for d in ('pooled', 'withinlab'):
            def get(f, per):
                g = f[m][(f[m]['scope'] == 'all') & (f[m]['k'] == 3) & (f[m]['measure'] == 'nov_nn_cap') & (f[m]['exposure'] == 'ai_share') & (f[m]['period'] == per) & (f[m]['design'] == d)]
                return g.iloc[0] if len(g) else None
            vals = {}
            for tag, f in (('v2', f2), ('v3', f3)):
                if m not in f:
                    continue
                for per in ('post', 'pre'):
                    r = get(f, per)
                    vals[(tag, per)] = r
            cell = lambda r: f"{r['beta']:+.4f} [{r['lo']:+.4f}, {r['hi']:+.4f}]" if r is not None else '-'
            p2, p3 = vals.get(('v2', 'post')), vals.get(('v3', 'post'))
            dr = '-' if p2 is None or p3 is None else ('same sign' if np.sign(p2['beta']) == np.sign(p3['beta']) else 'sign flips') + (', v3 excludes 0' if (p3['lo'] > 0 or p3['hi'] < 0) else ', v3 includes 0')
            rows.append(f"| {m} | {d} | {cell(p2)} | {cell(p3)} | {cell(vals.get(('v2', 'pre')))} | {cell(vals.get(('v3', 'pre')))} | {dr} |")
    return '\n'.join(rows)


def lab_did():
    a, b = pd.read_csv(V2 / 'results' / 'did_all_fits.csv'), pd.read_csv(V3 / 'results' / 'did_all_fits.csv') if (V3 / 'results' / 'did_all_fits.csv').exists() else None
    if b is None:
        fs = sorted((V3 / 'results').glob('did_*_abstract.parquet'))
        b = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    rows = ['| model | outcome | v2 DiD | v3 DiD | v2 placebo 2019 | v3 placebo 2019 |', '|---|---|---|---|---|---|']
    for m in sorted(b['model'].unique()):
        for o in ('disp', 'mpd', 'vendi'):
            def g(t, spec):
                x = t[(t['model'] == m) & (t['outcome'] == o) & (t['dose'] == 'dose') & (t['spec'] == spec) & (t['kind'] == 'abstract')]
                return f"{x.iloc[0]['beta']:+.3f} [{x.iloc[0]['lo']:+.3f}, {x.iloc[0]['hi']:+.3f}]" if len(x) else '-'
            rows.append(f"| {m} | {o} | {g(a, 'did')} | {g(b, 'did')} | {g(a, 'placebo2019')} | {g(b, 'placebo2019')} |")
    return '\n'.join(rows)


def lab_scores():
    v2 = json.load(open(V2 / 'results' / 'lab_ai' / 'validation.json'))
    v3 = json.load(open(V3 / 'results' / 'lab_ai' / 'out' / 'validation.json'))
    L = [f"Floor (mean 2016-2021 out-of-sample share): v2 {100 * v2['floor']:.2f}%, v3 {100 * v3['floor']:.2f}%. Labs with a score: v2 {v2['with_score']}, v3 {v3['with_score']} of {v3['labs_2025']}.",
         '', '| school | v2 scored / median / max | v3 scored / median / max | v2 paper coverage | v3 paper coverage |', '|---|---|---|---|---|']
    for s, b in v3['per_school_2025'].items():
        a = v2['per_school_2025'].get(s)
        L.append(f"| {s} | {a['scored']} / {a['median']} / {a['max']} | {b['scored']} / {b['median']} / {b['max']} | {a['coverage_papers']} | {b['coverage_papers']} |" if a else '')
    pl = v3['placebo']; po = v3['placebo_out_of_sample']; p2 = v2['placebo']
    L += ['', f"2019 placebo (labs scored on 2019 papers; every score should be about 0): v2 {p2['scored']} labs, median {p2['median']}, p90 {p2['p90']}, max {p2['max']}; "
          f"v3 {pl['scored']} labs, median {pl['median']}, p90 {pl['p90']}, max {pl['max']}, {100 * pl['share_zero']:.0f}% exactly 0; out-of-sample only: {po['scored']} labs, median {po['median']}, p90 {po['p90']}, max {po['max']}.",
          '', 'Cross-checks (Pearson of the lab score with): ' + '; '.join(f"{k} v2 {v2['correlations'][k]['pearson']} / v3 {v3['correlations'][k]['pearson']}" for k in v3['correlations'])]
    d2 = pd.DataFrame.from_dict(json.load(open(V2 / 'results' / 'lab_ai' / 'lab_ai_scores_2025.json'))['labs'], orient='index')
    d3 = pd.DataFrame.from_dict(json.load(open(V3 / 'results' / 'lab_ai' / 'out' / 'lab_ai_scores_2025.json'))['labs'], orient='index')
    j = d2[['score']].join(d3[['score']], rsuffix='3', how='inner').dropna()
    L += ['', f"Same labs scored in both ({len(j)}): Pearson {j.corr().iloc[0, 1]:.3f}, Spearman {j.corr(method='spearman').iloc[0, 1]:.3f}, median absolute change {(j.score3 - j.score).abs().median():.1f} points; "
          f"top-50 overlap {len(set(d2.score.nlargest(50).index) & set(d3.score.nlargest(50).index))} of 50."]
    g = d3[d3['school'] == 'gatech']
    L += ['', f"**Georgia Tech (full texts now scored).** {len(g)} labs, {int(g.n_papers_2025.sum())} papers in 2025, {int(g.n_full_text.sum())} with a full text, {int(g.n_scored.sum())} usable "
          f"({100 * g.n_scored.sum() / g.n_papers_2025.sum():.0f}%); {int(g.score.notna().sum())} labs reach the 5-paper minimum and get a score (median {g.score.median():.1f}, 90th percentile {g.score.quantile(.9):.1f}, max {g.score.max():.1f}). "
          'v2 scored none (coverage 0.3%).']
    return '\n'.join(L)


def bullets(path, n=10):
    p = Path(path)
    if not p.exists():
        return '(report not available)'
    t = p.read_text().split('\n')
    out = []
    start = next((i for i, l in enumerate(t) if l.startswith('## ') and ('Answer' in l or 'Summary' in l)), None)
    if start is None:
        return '(no summary section)'
    for l in t[start + 1:]:
        if l.startswith('## '):
            break
        if l.strip().startswith(('-', '**')) and len(l) > 40:
            out.append('> ' + l.strip()[:700])
        if len(out) >= n:
            break
    return '\n'.join(out) or '(summary has no bullets)'


PAIRS = {
    'Lineage (student-advisor similarity)': ('exp-lineage-style/ai-writing/diversity/reports/LINEAGE.md', 'exp-lineage-style/ai-writing/diversity/reports/LINEAGE-v3.md'),
    'Writing style': ('exp-lineage-style/ai-writing/diversity/reports/STYLE-HOMOGENIZATION.md', 'exp-lineage-style/ai-writing/diversity/reports/STYLE-HOMOGENIZATION-v3.md'),
    'Topic convergence': ('exp-topics-event-ipw/ai-writing/diversity/reports/TOPIC-CONVERGENCE.md', 'exp-topics-event-ipw/ai-writing/diversity/reports/v3/TOPIC-CONVERGENCE.md'),
    'Lab event study': ('exp-topics-event-ipw/ai-writing/diversity/reports/LAB-EVENT-STUDY.md', 'exp-topics-event-ipw/ai-writing/diversity/reports/v3/LAB-EVENT-STUDY.md'),
    'Full-text selection (IPW)': ('exp-topics-event-ipw/ai-writing/diversity/reports/FULLTEXT-SELECTION-IPW.md', 'exp-topics-event-ipw/ai-writing/diversity/reports/v3/FULLTEXT-SELECTION-IPW.md'),
    'Citation novelty': ('exp-citation-revision/ai-writing/diversity/reports/CITATION-NOVELTY.md', 'exp-citation-revision/ai-writing/diversity/reports/v3/CITATION-NOVELTY.md'),
    'AI in revision': ('exp-citation-revision/ai-writing/diversity/reports/AI-IN-REVISION.md', 'exp-citation-revision/ai-writing/diversity/reports/v3/AI-IN-REVISION.md'),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(Path(__file__).parent / 'reports' / 'V3-SUMMARY.md'))
    ap.add_argument('--hand', default=str(Path(__file__).parent / 'v3_summary_hand.md'))
    a = ap.parse_args()
    ck = json.load(open(V3 / 'results' / 'v3_checks.json'))['appendix_check']
    hm, hs = how_much()
    md = ['# Every AI-detection result, rerun on detector v3 (v2 and v3 side by side)\n',
          'Owner decision 2026-11-05: "rescore everything with v3". **v3 shares are not comparable in level with v2 shares**: v3 flags at a 0.3% false-alarm threshold (v2: 1%), abstains on passages under 100 words or heading-heavy (5.6% of test passages; excluded, with their share shown), and scores the main body only. '
          'Compare direction, not level. Headline condition: **main body only**; intervals are 95%; 2026 is in no series; detector-training papers (`trained_on_v3`) are out of every false-alarm floor and placebo.\n',
          '**Detector v3 error table** (`detector_v3/results/tables.md`): human passages wrongly flagged 0.30% (0.27-0.32%); misses on model families never seen in training 0.9-6.6% (leave-one-family-out; Qwen the hardest); partial edits (a human text with some sentences rewritten) are missed far more often (about 10-47% by generator) and are reported separately, not folded into the calibration figure.\n',
          f"**Appendix false-alarm check** (2016-2021 appendix passages, papers outside the training split, {ck['appendix']['papers']:,} papers / {ck['appendix']['passages']:,} passages): flagged {pc(ck['appendix']['flagged'], ck['appendix']['lo'], ck['appendix']['hi'], 2)}; main body {pc(ck['main']['flagged'], ck['main']['lo'], ck['main']['hi'], 2)}. "
          f"Limit 1.5%: **{'passes' if ck['passes'] else 'fails'}**, so main + appendix is shown as the secondary condition (one column below).\n",
          '## 1. How much AI, by year and school\n', 'Papers with a scored full text (share of passages flagged >= 25% is the "AI paper" cut of the site pages), all schools, home-school papers; v2 = 1% threshold, whole body; v3 = main body, 0.3% threshold.\n', hm,
          '\nBy school (home papers):\n', hs, '\n![](.)\n'.replace('![](.)\n', ''),
          '## 2. Dose versus novelty and diversity (paper level)\n', 'Coefficient of embedding novelty (size-matched, k = 3, scope all) on ai_share, 0 -> 1, cluster bootstrap over labs, 2023-2025 (post) and the 2017-2021 placebo (v3: papers outside the detector training split only).\n', dose_novelty(),
          '\nLab level (difference-in-differences of lab-year diversity on the lab AI dose; placebo break 2019), abstract embeddings:\n', lab_did(), '\n']
    md += ['## 3. All-AI rewrite\n', 'The all-AI rewrite study (`ALL-AI-REWRITE.md`: every abstract rewritten by Qwen2.5-7B, then embedded) does not depend on the passage detector; its numbers are unchanged. The abstract-level detector there is still v1. '
           'Where v3 enters is the AI-versus-not groups: the topic-matched test and `ai_vs_not` (AI paper = >= 25% flagged main-body passages) with the wording control on rewritten abstracts; see the site data `matched_test.json` and `ai_vs_not.json.gz` in the new site-data directory.\n']
    n = 4
    for title, (v2p, v3p) in PAIRS.items():
        n += 1
        md += [f'## {n}. {title}\n', f'v2 report: `{v2p}`; v3 report: `{v3p}`.\n', '**v2**\n', bullets(WT / v2p), '\n**v3**\n', bullets(WT / v3p), '\n']
    md += [f'## {n + 1}. Lab AI scores (2025, out of 10)\n', lab_scores(), '\n']
    hp = Path(a.hand)
    md += [hp.read_text() if hp.exists() else '## What changed\n\n(to be written)\n']
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text('\n'.join(md))
    print(a.out)


if __name__ == '__main__':
    main()
