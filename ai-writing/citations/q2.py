"""Question 2: what share of the cited works ("citables") are themselves AI-written, published vs preprint-only, and do
papers with more AI text cite more of them?

Scores: score_out_*.sqlite (v1 abstract detector, p unrounded) for cited works with a title and a >= 50-word OpenAlex
abstract: every one published 2022 or later, and a calibration sample published 2016-2021 (all preprint-only ones up
to 15,000 and 15,000 of the others, drawn at random once the fetch was complete).
Thresholds:
  v1      the detector's own threshold (1% FPR on held-out human lab-paper-style abstracts, metrics.json)
  cal1    the 99th percentile of the 2016-2021 calibration scores, i.e. 1% FPR on the cited-works population itself
  p50     p >= 0.5 (insensitive to the low-p tail)
Outputs (results/):
  q2_labchk.json            does this pipeline reproduce v1's stored flags on lab papers
  q2_by_cited_year.csv      flagged share by cited year x class (published / preprint / all), per work and per
                            citation, each threshold, Wilson 95% intervals
  q2_floor_by_field.csv     the 2016-2021 floor by OpenAlex field and class
  q2_citing.csv             per AI group of the citing paper and citing year: flagged share of its scored 2023+
                            references, its own 2016-2021 calibration references (the group's own floor), the excess,
                            lab-cluster bootstrap intervals
  q2_within.csv             lab x year fixed-effect regressions: cited-AI share on own AI; narrowing measures on cited-AI share
"""
import gzip, json, sqlite3
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
AIW = HERE.parent
DATA, RES = HERE / 'data', HERE / 'results'
CACHE = Path('/n/fs/resemble/cs-atlas-cache/citations')
SEED = 20261022


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan, np.nan
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, c - h, c + h


def load_scores():
    kind, p = {}, {}
    for f in sorted(CACHE.glob('score_input_*.sqlite')):
        for i, k in sqlite3.connect(f).execute('select id, kind from texts'):
            kind[i] = k
    for f in sorted(CACHE.glob('score_out_*.sqlite')):
        for i, v in sqlite3.connect(f).execute('select id, p from scores'):
            p[i] = v
    S = pd.DataFrame(dict(id=list(p), p=list(p.values())))
    S['kind'] = S.id.map(kind)
    return S


def main():
    thr_v1 = json.load(open(AIW / 'detector' / 'all' / 'metrics.json'))['threshold']
    S = load_scores()
    # 1. lab-paper reproduction check
    lab = S[S.kind == 'labchk'].set_index('id')
    v1 = {}
    for line in gzip.open(AIW / 'scores.jsonl.gz', 'rt'):
        r = json.loads(line)
        if r['key'] in lab.index:
            v1[r['key']] = (r['p_ai'], r['flagged'])
    lab = lab.join(pd.DataFrame.from_dict(v1, orient='index', columns=['p_v1', 'flag_v1']))
    lab['flag_new'] = lab.p >= thr_v1
    chk = dict(n=len(lab), agree=float((lab.flag_new == lab.flag_v1).mean()), flagged_v1=int(lab.flag_v1.sum()), flagged_new=int(lab.flag_new.sum()),
               both=int((lab.flag_new & lab.flag_v1).sum()), max_abs_dp=float((lab.p.round(5) - lab.p_v1).abs().max()))
    json.dump(chk, open(RES / 'q2_labchk.json', 'w'), indent=1)
    print(json.dumps(dict(labchk=chk)))
    # 2. cited works
    W = pd.read_parquet(DATA / 'works_oa.parquet')
    W['id'] = 'W' + W.wid.astype(str)
    C = S[S.kind.isin(['cited', 'calib'])].merge(W[['id', 'wid', 'year', 'pubclass', 'pubclass_s2', 'field', 'type']], on='id', how='left')
    cal = C[(C.kind == 'calib') & C.year.between(2016, 2021)]
    thr = {'v1': thr_v1, 'cal1': float(np.quantile(cal.p, 0.99)), 'p50': 0.5}
    # calibration sample: preprints were taken whole (up to 15k) and published/other subsampled, so pooled 'all' rates in
    # 2016-2021 are reweighted by the class mix among all scorable 2016-2021 cited works
    E = pd.read_parquet(DATA / 'edges_oa.parquet')
    ncite = E.wid.value_counts()
    C['ncite'] = C.wid.map(ncite).fillna(0).values
    C['cls'] = C.pubclass.where(C.pubclass == 'preprint', 'published')  # 'other' (few with abstracts) joins published
    rows = []
    for tn, t in thr.items():
        C['f'] = C.p >= t
        for y in ['2016–2021', 2022, 2023, 2024, 2025, 2026]:
            d = cal if y == '2016–2021' else C[(C.kind == 'cited') & (C.year == y)]
            d = d.assign(f=d.p >= t, cls=d.pubclass.where(d.pubclass == 'preprint', 'published'))
            for cls in ('published', 'preprint', 'all'):
                x = d if cls == 'all' else d[d.cls == cls]
                if cls == 'all' and y == '2016–2021':
                    continue
                k, n = int(x.f.sum()), len(x)
                p, lo, hi = wilson(k, n)
                wc = x.wid.map(ncite).fillna(0).values
                pc = float((wc * x.f).sum() / wc.sum()) if wc.sum() else np.nan
                rows.append(dict(threshold=tn, cited_year=str(y), cls=cls, works=n, flagged=k, share=p, lo=lo, hi=hi, share_per_citation=pc))
    Q = pd.DataFrame(rows); Q.to_csv(RES / 'q2_by_cited_year.csv', index=False)
    print(Q[Q.threshold == 'v1'].round(4).to_string())
    print(json.dumps(dict(thresholds=thr)))
    # field floor
    fl = []
    for tn in ('v1', 'cal1'):
        for (fld, cls), x in cal.assign(cls=cal.pubclass.where(cal.pubclass == 'preprint', 'published')).groupby(['field', 'cls']):
            if len(x) >= 200:
                p, lo, hi = wilson(int((x.p >= thr[tn]).sum()), len(x))
                fl.append(dict(threshold=tn, field=fld, cls=cls, n=len(x), share=p, lo=lo, hi=hi))
    pd.DataFrame(fl).to_csv(RES / 'q2_floor_by_field.csv', index=False)
    # 3. citing side
    P = pd.read_parquet(DATA / 'paper_measures.parquet')
    sc = C.set_index('wid')[['p', 'kind', 'year']]
    E2 = E.merge(sc, left_on='wid', right_index=True, how='inner')
    Pc = pd.read_parquet(DATA / 'citing.parquet')[['key']].reset_index().rename(columns={'index': 'ci_all'})
    # edges_oa ci indexes citing.parquet rows; paper_measures rows keep their key
    E2 = E2.merge(Pc, left_on='ci', right_on='ci_all').drop(columns='ci_all')
    out, within = [], []
    for tn, t in thr.items():
        E2['f'] = E2.p >= t
        rec = E2[(E2.kind == 'cited') & (E2.year >= 2023)].groupby('key').f.agg(['sum', 'size']).rename(columns={'sum': 'k_rec', 'size': 'n_rec'})
        old = E2[(E2.kind == 'calib')].groupby('key').f.agg(['sum', 'size']).rename(columns={'sum': 'k_old', 'size': 'n_old'})
        X = P.set_index('key').join(rec).join(old).reset_index()
        X[['k_rec', 'n_rec', 'k_old', 'n_old']] = X[['k_rec', 'n_rec', 'k_old', 'n_old']].fillna(0)
        X['grp'] = np.where(X.ai_share <= 0, 'none', np.where(X.ai_share < 0.25, 'some', 'flagged'))
        X['lab0'] = X.labs.map(lambda s: json.loads(s)[0])
        rng = np.random.default_rng(SEED)
        for yr in ['2023–2026', 2023, 2024, 2025, 2026]:
            for g in ('none', 'some', 'flagged'):
                x = X[(X.grp == g) & ((X.year >= 2023) if yr == '2023–2026' else (X.year == yr))]
                if x.n_rec.sum() < 30:
                    continue
                labs = x.groupby('lab0')[['k_rec', 'n_rec', 'k_old', 'n_old']].sum()
                A = labs.values
                tot = A.sum(0)
                bs = []
                for _ in range(1000):
                    c = np.bincount(rng.integers(0, len(A), len(A)), minlength=len(A))
                    s = c @ A
                    bs.append((s[0] / s[1], s[2] / s[3] if s[3] else np.nan))
                bs = np.array(bs)
                ex = bs[:, 0] - bs[:, 1]
                out.append(dict(threshold=tn, citing_year=str(yr), group=g, papers=len(x), papers_with_recent=int((x.n_rec > 0).sum()),
                                recent_refs=int(tot[1]), share=tot[0] / tot[1], lo=np.nanpercentile(bs[:, 0], 2.5), hi=np.nanpercentile(bs[:, 0], 97.5),
                                old_refs=int(tot[3]), floor=tot[2] / tot[3] if tot[3] else np.nan,
                                excess=tot[0] / tot[1] - (tot[2] / tot[3] if tot[3] else np.nan),
                                ex_lo=np.nanpercentile(ex, 2.5), ex_hi=np.nanpercentile(ex, 97.5)))
        # within-lab regressions
        if tn in ('v1', 'cal1'):
            import within as Wt
            X['cai'] = np.where(X.n_rec >= 3, X.k_rec / X.n_rec.clip(lower=1), np.nan)
            X['flag'] = (X.ai_share >= 0.25).astype(float); X['dose10'] = X.ai_share * 10
            L = Wt.long_by_lab(X[X.year >= 2023])
            L['labyear'] = L.lab + '|' + L.year.astype(str)
            for spec, xs in (('cai ~ flag', ['flag', 'log_nrefs']), ('cai ~ dose10', ['dose10', 'log_nrefs'])):
                b, lo, hi, n, nl = Wt.fe_boot(L, 'cai', xs, ['labyear'])
                within.append(dict(threshold=tn, y='cai', x=xs[0], beta=b, lo=lo, hi=hi, papers=n, labs=nl))
            for m in ('canon', 'top1', 'logcbc_adj', 'venue_div', 'field_div', 'preprint'):
                b, lo, hi, n, nl = Wt.fe_boot(L, m, ['cai', 'dose10', 'log_nrefs', 'recent'], ['labyear'])
                within.append(dict(threshold=tn, y=m, x='cai (with own dose, log refs, recent share)', beta=b, lo=lo, hi=hi, papers=n, labs=nl,
                                   sd_y=float(X.loc[X.year >= 2023, m].std()), sd_x=float(X.cai.std())))
    O = pd.DataFrame(out); O.to_csv(RES / 'q2_citing.csv', index=False)
    print(O[O.threshold == 'v1'].round(4).to_string())
    Wd = pd.DataFrame(within); Wd.to_csv(RES / 'q2_within.csv', index=False)
    print(Wd.round(4).to_string())


if __name__ == '__main__':
    main()
