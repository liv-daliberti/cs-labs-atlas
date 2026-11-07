"""Per-lab 2025 AI-use score out of 10, from the MAIN BODY of the lab's 2025 papers (owner 2026-11-05).

  lab_ai_score.py build [--config C] [--out DIR]       -> lab_ai_scores_2025.json (+ .csv, validation.json) in DIR (default AI_SCORES/results/lab_ai)
  lab_ai_score.py handread [--n 5] [--min-scored 8]     the papers behind the highest and lowest scored labs (stdout), for the hand check

Formula (method_version main-body-1)
  paper share   s_p = flagged main-body passages / scored main-body passages. A passage is flagged when the detector score is >= its calibrated false-alarm (v2: 1%, v3: 0.3%)
                threshold. Main body = the passages the section tags mark (references and appendix passages are excluded: tags come from
                fulltext_sections.py); passages under `min_passage_words` (the short tail passage, 8% false alarms) are dropped. A paper is usable when
                its main text has >= `min_main_words` words and >= `min_scored_passages` scored main passages.
  lab share     m_L = unweighted mean of s_p over the lab's usable papers of the year (a paper in several labs counts for each).
  floor         f = mean over 2016-2021 of the year-mean of s_p over usable papers the detector never trained on (same detector, same filters).
  score         10 * max(0, (m_L - f) / (1 - f)), one decimal. Interval: 95% bootstrap over the lab's papers (and over the floor's papers).
  null          fewer than `min_papers` usable papers: score null, reason insufficient_2025_papers, with the counts (all papers / with full text / usable).
Lab membership: the site's lab records (cs-pi-labs / cs-hierarchy, id = the lab record id): the lab's papers with the year as the package lists them.
Cross-checks (never mixed into the score): the legacy full-text ai_share (all body passages), the abstract flag (v1), and the Kobak marker-word rate.
The detector is one config point (lab_ai_score_config.json: detector); an optional IPW-weighted variant reads `ipw_weights` (paper_id, w).
"""
import argparse
import glob
import gzip
import json
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

import dcommon as D

HERE = Path(__file__).resolve().parent
OUT = D.RESULTS / 'lab_ai'
PRE = list(range(2016, 2022))


def load_config(path=None):
    cfg = json.loads(Path(path or HERE / 'lab_ai_score_config.json').read_text())
    det = cfg['detectors'][cfg['detector']]
    if det.get('threshold') is None:
        raise SystemExit(f"detector {cfg['detector']!r} has no threshold in the config")
    return cfg, det


def slot(path):
    """'AI_SCORES/x' style path -> real path (the container slot, from atlas_paths)."""
    head, _, rest = path.partition('/')
    base = {'AI_SCORES': D.SCORES, 'AI_SCORES_V3': Path(os.environ.get('AI_SCORES_V3_DIR') or (D.P.CODE / 'ai-writing' / 'data' / 'ai-scores-v3'))}.get(head)
    return (base / rest) if base else Path(path)


def load_passages(det):
    spec = det['passages']
    if ':' in spec and not spec.endswith('.parquet'):
        path, table = spec.rsplit(':', 1)
        db = sqlite3.connect(f'file:{slot(path)}?mode=ro', uri=True)
        df = pd.read_sql(f'select paper_id, pidx, words, p from {table}', db)
        db.close()
        return df
    return pd.read_parquet(slot(spec), columns=['paper_id', 'pidx', 'words', 'p'])


def load_tags(cfg, det):
    files = sorted(glob.glob(str(slot(det.get('tags') or cfg['sections']['tags']))))
    if not files:
        raise SystemExit(f"no section tags at {cfg['sections']['tags']} (run lab_ai_main_tags.py)")
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def paper_table(cfg, det):
    """One row per tagged paper: n_scored, n_flag, share, usable, plus the legacy and abstract measures."""
    tags = load_tags(cfg, det)
    tg = pd.read_parquet(slot(det['targets']) if det.get('targets') else D.RESULTS / 'lab_ai' / 'targets.parquet')[['paper_id', 'year', 'home_school', 'trained_on']]
    tags = tags.merge(tg, on='paper_id')
    ok = tags[tags['error'].isna() & tags['main_pidx'].astype(bool)]
    main = ok[['paper_id', 'main_pidx']].copy()
    main['pidx'] = main['main_pidx'].str.split(',')
    main = main.explode('pidx')
    main['pidx'] = main['pidx'].astype(int)
    ps = load_passages(det)
    ps = ps[ps['paper_id'].isin(set(main['paper_id']))]
    ps = ps.merge(main[['paper_id', 'pidx']], on=['paper_id', 'pidx'])
    ps = ps[ps['words'] >= cfg['min_passage_words']]
    ps['flag'] = ps['p'] >= det['threshold']
    g = ps.groupby('paper_id').agg(n_scored=('flag', 'size'), n_flag=('flag', 'sum'))
    t = tags.merge(g, left_on='paper_id', right_index=True, how='left')
    t['n_scored'] = t['n_scored'].fillna(0).astype(int)
    t['n_flag'] = t['n_flag'].fillna(0).astype(int)
    t['share'] = np.where(t['n_scored'] > 0, t['n_flag'] / t['n_scored'].clip(lower=1), np.nan)
    t['usable'] = t['error'].isna() & (t['main_words'].fillna(0) >= cfg['min_main_words']) & (t['n_scored'] >= cfg['min_scored_passages'])
    db = sqlite3.connect(f'file:{D.DB}?mode=ro', uri=True)
    sc = pd.read_sql('select paper_id, ai_share, flag_abstract, kobak_abs, kobak_ft, p_ai_abstract from papers', db)
    allp = pd.read_sql('select paper_id, year, flag_abstract from papers where year between 2016 and 2021 and flag_abstract is not null', db)
    db.close()
    return t.merge(sc, on='paper_id', how='left'), allp


def lab_members(year):
    """DataFrame lab_id, school, lab, pi, paper_id (universe id or None), n rows: every paper the site lists for the lab in `year`."""
    root = D.P.SITE / 'atlas' / 'data'
    db = sqlite3.connect(f'file:{D.UNIVERSE_DB}?mode=ro', uri=True)
    uni = pd.read_sql('select paper_id, oa from papers', db)
    db.close()
    by_oa = {(u or '').rsplit('/', 1)[-1]: p for p, u in zip(uni['paper_id'], uni['oa']) if u}
    known = set(uni['paper_id'])
    rows, labs = [], []
    for f in sorted((root / 'cs-pi-labs').glob('*.json.gz')):
        d = json.load(gzip.open(f, 'rt'))
        h = json.load(gzip.open(root / 'cs-hierarchy' / f"{d['school']}.json.gz", 'rt'))
        P = h['papers']
        for l in d['labs']:
            if not l.get('csShown'):
                continue
            hl = h['labs'][l['hierarchy']['index']]
            assert hl['id'] == l['id']
            labs.append(dict(lab_id=l['id'], school=d['school'], lab=l['name'], pi=l['pi'], pi_ids=(hl.get('pi') or {}).get('ids') or []))
            seen = set()
            for i in hl['papers']:
                i = i[0] if isinstance(i, list) else i
                p = P[i]
                if p['y'] != year or i in seen:
                    continue
                seen.add(i)
                a = p.get('atlasId')
                pid = a if a in known else by_oa.get((p.get('oa') or '').rsplit('/', 1)[-1])
                rows.append((l['id'], pid))
    labs = pd.DataFrame(labs)
    # the package's own lab id (atl:l:<school>:<slug>; pi_id is the same without the prefix) by (school, PI name), where that is unique
    db = sqlite3.connect(f'file:{D.UNIVERSE_DB}?mode=ro', uri=True)
    ul = pd.read_sql('select distinct school, pi, lab_id from lab_papers', db)
    db.close()
    one = ul.groupby(['school', 'pi'])['lab_id'].agg(lambda x: x.iloc[0] if len(set(x)) == 1 else None).to_dict()
    labs['atlas_lab_id'] = [one.get((s, p)) for s, p in zip(labs['school'], labs['pi'])]
    labs['pi_id'] = labs['atlas_lab_id'].map(lambda a: a.replace('atl:l:', '', 1) if a else None)
    return labs, pd.DataFrame(rows, columns=['lab_id', 'paper_id'])


def floor_of(pt, col, boot_rng=None, B=0):
    """Mean over years 2016-2021 of the year-mean of `col` over out-of-sample usable papers; with B, also B bootstrap floors."""
    sub = pt[pt['year'].isin(PRE) & ~pt['trained_on'] & pt['usable'] & pt[col].notna()]
    ys = [g[col].to_numpy() for _, g in sub.groupby('year')]
    f = float(np.mean([y.mean() for y in ys]))
    if not B:
        return f, None
    boots = np.mean([[y[boot_rng.integers(0, len(y), len(y))].mean() for y in ys] for _ in range(B)], axis=1)
    return f, boots


def correct(m, f):
    return np.clip((m - f) / (1 - f), 0, None)


def score_labs(labs, members, pt, floor, floor_boot, cfg, label, ipw=None):
    rng = np.random.default_rng(cfg['seed'])
    B = cfg['bootstrap']
    share = pt.set_index('paper_id')
    gen = pd.Timestamp.now('UTC').strftime('%Y-%m-%dT%H:%M:%SZ')
    out = {}
    mem = members.groupby('lab_id')['paper_id'].apply(list).to_dict()
    for l in labs.itertuples():
        pids = mem.get(l.lab_id, [])
        n_all = len(pids)
        have = [p for p in pids if p and p in share.index]
        ft = [p for p in have if share.at[p, 'n_scored'] > 0 or share.at[p, 'main_words'] > 0]
        use = [p for p in have if share.at[p, 'usable']]
        rec = dict(school=l.school, lab=l.lab, pi=l.pi, pi_id=l.pi_id, atlas_lab_id=l.atlas_lab_id, n_papers_2025=n_all, n_full_text=len(ft), n_scored=len(use), detector=label,
                   method_version=cfg['method_version'], generated=gen, score=None, interval=None, reason=None, main_share=None,
                   fulltext_crosscheck=None, abstract_crosscheck=None, kobak_ft=None, score_ipw=None)
        rec['coverage'] = round(len(use) / n_all, 3) if n_all else None
        sub = share.loc[use]
        if len(use) >= cfg['min_papers']:
            s = sub['share'].to_numpy()
            m = float(s.mean())
            rec['main_share'] = round(m, 4)
            rec['score'] = round(10 * float(correct(m, floor)), 1)
            idx = rng.integers(0, len(s), (B, len(s)))
            bs = 10 * correct(s[idx].mean(1), floor_boot)
            lo, hi = np.percentile(bs, [2.5, 97.5])
            rec['interval'] = [round(float(lo), 1), round(float(hi), 1)]
            if ipw is not None:
                w = np.array([ipw.get(p, np.nan) for p in use])
                if np.isfinite(w).all() and w.sum() > 0:
                    rec['score_ipw'] = round(10 * float(correct((w * s).sum() / w.sum(), floor)), 1)
        else:
            rec['reason'] = 'insufficient_2025_papers'
        if len(have):
            leg = share.loc[have, 'ai_share'].dropna()
            if len(leg):
                rec['fulltext_crosscheck'] = dict(ai_share=round(float(leg.mean()), 4), n=int(len(leg)))
            ab = share.loc[have, 'flag_abstract'].dropna()
            if len(ab):
                rec['abstract_crosscheck'] = dict(flag_share=round(float(ab.mean()), 4), n=int(len(ab)))
            kb = share.loc[use, 'kobak_ft'].dropna() if use else []
            if len(kb):
                rec['kobak_ft'] = round(float(np.mean(kb)), 2)
        out[l.lab_id] = rec
    return out


def add_floor_equiv(out, leg_floor):
    for r in out.values():
        c = r['fulltext_crosscheck']
        if c:
            c['score_equiv'] = round(10 * float(correct(c['ai_share'], leg_floor)), 1)


def summarize(out, labs):
    df = pd.DataFrame.from_dict(out, orient='index')
    df['has'] = df['score'].notna()
    per = {}
    for s, g in df.groupby('school'):
        v = g.loc[g['has'], 'score']
        per[s] = dict(labs=int(len(g)), scored=int(g['has'].sum()), null=int((~g['has']).sum()),
                      coverage_papers=round(float(g['n_scored'].sum() / max(1, g['n_papers_2025'].sum())), 3),
                      median=round(float(v.median()), 2) if len(v) else None, p10=round(float(v.quantile(.1)), 2) if len(v) else None,
                      p90=round(float(v.quantile(.9)), 2) if len(v) else None, max=round(float(v.max()), 1) if len(v) else None,
                      share_zero=round(float((v < 0.05).mean()), 3) if len(v) else None)
    return df, per


def build(cfg_path=None, out_dir=None):
    cfg, det = load_config(cfg_path)
    out_dir = Path(out_dir or OUT)
    out_dir.mkdir(parents=True, exist_ok=True)
    pt, allabs = paper_table(cfg, det)
    rng = np.random.default_rng(cfg['seed'] + 1)
    f, fboot = floor_of(pt, 'share', rng, cfg['bootstrap'])
    # cross-check floors (same out-of-sample rule): legacy full-text share, v1 abstract flag
    leg = pt[pt['year'].isin(PRE) & ~pt['trained_on'] & pt['ai_share'].notna()].groupby('year')['ai_share'].mean().mean()
    ab_floor = float(allabs.groupby('year')['flag_abstract'].mean().mean())
    ipw = None
    if cfg.get('ipw_weights'):
        w = pd.read_parquet(slot(cfg['ipw_weights']))
        ipw = dict(zip(w['paper_id'], w[cfg.get('ipw_column', 'w')]))
    D.log(stage='floor', floor=f, legacy_floor=float(leg), abstract_flag_floor=ab_floor, floor_boot_sd=float(fboot.std()))
    res = {}
    for year in (cfg['year'], cfg['placebo_year']):
        labs, members = lab_members(year)
        sub = pt[pt['year'] == year]
        out = score_labs(labs, members, sub, f, fboot, cfg, det['label'], ipw)
        add_floor_equiv(out, float(leg))
        res[year] = (out, labs, members)
        D.log(stage='scored', year=year, labs=len(out), with_score=sum(r['score'] is not None for r in out.values()))
    out25, labs25, mem25 = res[cfg['year']]
    meta = dict(method_version=cfg['method_version'], year=cfg['year'], detector=det['label'], detector_threshold=det['threshold'],
                scale='10 x the corrected share of the lab\'s 2025 main-text passages that the detector flags', false_alarm_floor=round(f, 5),
                min_papers=cfg['min_papers'], min_main_words=cfg['min_main_words'], min_scored_passages=cfg['min_scored_passages'],
                min_passage_words=cfg['min_passage_words'], bootstrap=cfg['bootstrap'], generated=pd.Timestamp.now('UTC').strftime('%Y-%m-%dT%H:%M:%SZ'),
                note='Estimated share of the main text of the lab\'s papers that reads as AI-written, corrected for the detector\'s false-alarm rate.')
    (out_dir / 'lab_ai_scores_2025.json').write_text(json.dumps(dict(meta=meta, labs=out25), indent=None, separators=(',', ':'), sort_keys=True))
    SITE_KEYS = ('score', 'interval', 'n_papers_2025', 'n_full_text', 'n_scored', 'reason', 'fulltext_crosscheck', 'detector', 'method_version', 'generated')
    slim = {k: {f: r[f] for f in SITE_KEYS} for k, r in out25.items()}
    (out_dir / 'site').mkdir(exist_ok=True)
    (out_dir / 'site' / 'lab_ai_scores_2025.json').write_text(json.dumps(dict(meta=dict(meta, last_year=cfg['year']), labs=slim), separators=(',', ':'), sort_keys=True))
    df, per = summarize(out25, labs25)
    flat = df.drop(columns=['fulltext_crosscheck', 'abstract_crosscheck', 'has']).copy()
    flat['interval_lo'] = flat['interval'].map(lambda v: v[0] if v else None)
    flat['interval_hi'] = flat['interval'].map(lambda v: v[1] if v else None)
    flat['fulltext_ai_share'] = [r['fulltext_crosscheck']['ai_share'] if r['fulltext_crosscheck'] else None for r in out25.values()]
    flat.drop(columns=['interval']).rename_axis('lab_id').to_csv(out_dir / 'lab_ai_scores_2025.csv')
    # validation: placebo and correlations
    val = dict(floor=f, per_school_2025=per, labs_2025=len(df), with_score=int(df['has'].sum()))
    pl_out = res[cfg['placebo_year']][0]
    pdf = pd.DataFrame.from_dict(pl_out, orient='index')
    ps = pdf[pdf['score'].notna()]
    val['placebo'] = dict(year=cfg['placebo_year'], labs=len(pdf), scored=len(ps), median=float(ps['score'].median()), p90=float(ps['score'].quantile(.9)),
                          share_below_0_5=float((ps['score'] < .5).mean()), share_below_1=float((ps['score'] < 1).mean()), share_zero=float((ps['score'] < .05).mean()),
                          max=float(ps['score'].max()), interval_covers_zero=float(np.mean([r['interval'][0] <= 0.05 for r in pl_out.values() if r['interval']])))
    # placebo again on papers the detector never trained on
    ptoos = pt[~pt['trained_on']]
    labs19, mem19 = res[cfg['placebo_year']][1], res[cfg['placebo_year']][2]
    o2 = score_labs(labs19, mem19, ptoos[ptoos['year'] == cfg['placebo_year']], f, fboot, cfg, det['label'])
    p2 = pd.DataFrame.from_dict(o2, orient='index')
    p2 = p2[p2['score'].notna()]
    val['placebo_out_of_sample'] = dict(scored=len(p2), median=float(p2['score'].median()), p90=float(p2['score'].quantile(.9)),
                                        share_below_0_5=float((p2['score'] < .5).mean()), share_below_1=float((p2['score'] < 1).mean()), max=float(p2['score'].max()))
    sc = df[df['has']].copy()
    sc['leg'] = sc['fulltext_crosscheck'].map(lambda c: c['score_equiv'] if c else np.nan)
    sc['abs'] = sc['abstract_crosscheck'].map(lambda c: c['flag_share'] if c else np.nan)
    corr = {}
    for name, col in (('fulltext_ai_share_equiv', 'leg'), ('kobak_ft', 'kobak_ft'), ('abstract_flag_share', 'abs')):
        v = sc[['score', col]].dropna()
        corr[name] = dict(n=int(len(v)), pearson=round(float(v['score'].corr(v[col])), 3), spearman=round(float(v['score'].corr(v[col], method='spearman')), 3))
    val['correlations'] = corr
    val['coverage_all'] = dict(papers_2025=int(df['n_papers_2025'].sum()), usable=int(df['n_scored'].sum()))
    (out_dir / 'validation.json').write_text(json.dumps(val, indent=1, default=float))
    print(json.dumps(val, indent=1, default=float))


def handread(n, min_scored, cfg_path=None, out_dir=None):
    cfg, det = load_config(cfg_path)
    d = json.loads((Path(out_dir or OUT) / 'lab_ai_scores_2025.json').read_text())['labs']
    df = pd.DataFrame.from_dict(d, orient='index')
    df = df[df['n_scored'] >= min_scored].dropna(subset=['score'])
    df = df.sort_values('score')
    pick = list(df.index[-n:][::-1]) + list(df.index[:n])
    pt, _ = paper_table(cfg, det)
    labs, mem = lab_members(cfg['year'])
    abstracts = sqlite3.connect(f'file:{D.TEXTS_DB}?mode=ro', uri=True)
    for lid in pick:
        r = d[lid]
        print('=' * 100)
        print(lid, r['lab'], r['school'], 'score', r['score'], r['interval'], 'n', r['n_scored'], '/', r['n_papers_2025'])
        ids = [p for p in mem[mem['lab_id'] == lid]['paper_id'] if p]
        sub = pt[pt['paper_id'].isin(ids) & pt['usable']].sort_values('share', ascending=False)
        for x in sub.itertuples():
            row = abstracts.execute('select title, abstract from abstracts where paper_id = ?', (x.paper_id,)).fetchone() or ('', '')
            print(f'-- {x.paper_id} share={x.share:.2f} ({x.n_flag}/{x.n_scored}) kobak={x.kobak_ft}  {row[0][:100]}')
            print('   ', (row[1] or '')[:600].replace('\n', ' '))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['build', 'handread'])
    ap.add_argument('--config')
    ap.add_argument('--out')
    ap.add_argument('--n', type=int, default=5)
    ap.add_argument('--min-scored', type=int, default=8)
    a = ap.parse_args()
    build(a.config, a.out) if a.cmd == 'build' else handread(a.n, a.min_scored, a.config, a.out)
