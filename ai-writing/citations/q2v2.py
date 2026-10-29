"""Question 2 with the passage detector (detector_v2, the one behind paragraph_scores.jsonl.gz): how many cited works are
AI-written, published vs preprint-only, and do AI-written lab papers cite more of them?

Two kinds of citable:
  lab      cited works that are themselves lab papers of the corpus (matched on OpenAlex id, else DOI): their own
           paragraph score (usable full text, flag = ai_share >= 0.25)
  sample   the other cited works: ftsample.py's citation-weighted (PPS) sample of open full texts per stratum,
           scored by v2score.py; ai_share = flagged passages / passages with the v2 threshold (detector_v2/results/
           all/metrics.json), usable-text rule as for lab papers, flag = ai_share >= 0.25
Strata: cited year {2016-2021 floor, 2023, 2024, 2025, 2026} x {published, preprint-only}.
Estimates per stratum (shares of CITATIONS from the covered lab papers):
  sample  plain mean of the flag over the sample (PPS by citations, so this is citation-weighted), Wilson 95% CI;
          also the share per work (Hajek weights 1/ncite)
  lab     citation-weighted flag share of the lab-paper citables
  all     the two combined by their citation totals in the stratum frame
Citing side: for each citing paper, its references to scored citables (lab or sample) published 2023+, and to
2016-2021 ones (its own floor); pooled per citing AI group x citing year, lab-cluster bootstrap. expected_mix = the share
expected from the cited-year x class mix of those references alone (each reference scored at its stratum's combined
share); mix_excess = observed - expected, i.e. AI-flagged works cited beyond what citing newer work implies. cai_mix is
the per-paper version used in the within-lab fit.
Bias of the open subset: the v1 abstract flag rate, arXiv share, field and citations of the works obtained vs the
whole stratum frame (all cited works with a v1 abstract score).
-> results/q2v2_strata.csv, q2v2_coverage.csv, q2v2_bias.csv, q2v2_citing.csv, q2v2_versions.csv, q2v2_within.csv
"""
import glob, gzip, json, sqlite3
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


def stratum(year, pubclass):
    if pd.isna(year):
        return None
    y = int(year)
    s = '2016-2021' if 2016 <= y <= 2021 else str(y) if 2023 <= y <= 2026 else None
    return None if s is None else f"{s}|{'preprint' if pubclass == 'preprint' else 'published'}"


def sample_scores():
    thr = json.load(open(AIW / 'detector_v2' / 'results' / 'all' / 'metrics.json'))['threshold']
    n, k = {}, {}
    for f in sorted(glob.glob(str(CACHE / 'v2scores' / 'shard-*.jsonl.gz'))):
        for line in gzip.open(f, 'rt'):
            r = json.loads(line)
            n[r['key']] = n.get(r['key'], 0) + 1; k[r['key']] = k.get(r['key'], 0) + (r['p'] >= thr)
    us = {}
    for f in sorted(glob.glob(str(CACHE / 'v2scores' / 'papers-*.jsonl.gz'))):
        for line in gzip.open(f, 'rt'):
            r = json.loads(line); us[r['key']] = r['usable']
    S = pd.DataFrame(dict(key=list(n), n_pass=list(n.values()), n_flag=[k[x] for x in n]))
    S['usable'] = S.key.map(us).fillna(False)
    S = S[S.usable & (S.n_pass > 0)]
    S['ai_share'] = S.n_flag / S.n_pass; S['flag'] = S.ai_share >= 0.25
    return S, thr


def lab_citables(W):
    """works_oa rows that are lab papers with a paragraph score: (wid, ai_share)."""
    sc = {}
    for line in gzip.open(AIW / 'paragraph_scores.jsonl.gz', 'rt'):
        s = json.loads(line)
        if s.get('ai_share') is not None and s.get('n_paragraphs'):
            sc[s['key']] = float(s['ai_share'])
    byw, byd = {}, {}
    for line in gzip.open(AIW / 'papers.jsonl.gz', 'rt'):
        p = json.loads(line)
        if p['key'] not in sc:
            continue
        oa = p.get('oa') or ''
        if oa.startswith('https://openalex.org/W'):
            byw[int(oa.rsplit('/W', 1)[1])] = sc[p['key']]
        if p.get('doi'):
            byd[p['doi'].lower().replace('https://doi.org/', '')] = sc[p['key']]
    return byw, byd


def main():
    import zlib
    W = pd.read_parquet(DATA / 'works_oa.parquet')
    E = pd.read_parquet(DATA / 'edges_oa.parquet')
    nref = E.groupby('ci').size(); okc = set(nref[nref >= 5].index)
    nc = E[E.ci.isin(okc)].wid.value_counts()
    W['ncite'] = W.wid.map(nc).fillna(0).astype(int)
    W['stratum'] = [stratum(y, c) for y, c in zip(W.year, W.pubclass)]
    byw, byd = lab_citables(W)
    W['lab_ai'] = W.wid.map(byw)
    # DOI fallback for lab papers whose OpenAlex id differs from the cited id
    oa = sqlite3.connect(f'file:{CACHE / "openalex.sqlite"}?mode=ro', uri=True)
    miss = set(W.loc[W.lab_ai.isna() & W.stratum.notna(), 'wid'])
    dmap = {}
    for wid, b in oa.execute('select wid, data from works where status > 0'):
        i = int(wid[1:])
        if i in miss:
            d = (json.loads(zlib.decompress(b)).get('doi') or '').lower().replace('https://doi.org/', '')
            if d in byd:
                dmap[i] = byd[d]
    W.loc[W.wid.isin(dmap), 'lab_ai'] = W.wid.map(dmap)
    W['is_lab'] = W.lab_ai.notna()
    S, thr = sample_scores()
    ft = sqlite3.connect(f'file:{CACHE / "ft.sqlite"}?mode=ro', uri=True)
    meta = pd.read_sql('select key, stratum, source, version, status from meta', ft)
    frame = pd.read_sql('select key, stratum, ncite, arxiv, pmcid, pdfs, pubclass, field, cbc from frame', ft)
    frame['any_source'] = frame.arxiv.notna() | frame.pmcid.notna() | (frame.pdfs != '[]')
    M = meta.merge(S, on='key', how='left').merge(frame[['key', 'ncite', 'field', 'cbc', 'arxiv']], on='key', how='left')
    labw = set('W' + W.loc[W.is_lab, 'wid'].astype(str))
    M = M[~M.key.isin(labw)]; frame = frame[~frame.key.isin(labw)]  # lab papers matched only by DOI: counted as lab
    M['scored'] = M.flag.notna()
    # v1 abstract scores (for the bias check)
    v1thr = json.load(open(AIW / 'detector' / 'all' / 'metrics.json'))['threshold']
    p1 = {}
    for f in sorted(CACHE.glob('score_out_*.sqlite')):
        for i, v in sqlite3.connect(f).execute('select id, p from scores'):
            p1[i] = v
    frame['v1'] = frame.key.map(lambda k: (p1[k] >= v1thr) if k in p1 else np.nan)
    M['v1'] = M.key.map(lambda k: (p1[k] >= v1thr) if k in p1 else np.nan)
    strata = sorted(frame.stratum.unique())
    rows, cov, bias = [], [], []
    for st in strata:
        fr = frame[frame.stratum == st]; m = M[M.stratum == st]; sc = m[m.scored]
        lab = W[(W.stratum == st) & W.is_lab & (W.ncite > 0)]
        k, n = int(sc.flag.sum()), len(sc)
        p, lo, hi = wilson(k, n)
        pw = float((sc.flag / sc.ncite).sum() / (1 / sc.ncite).sum()) if n else np.nan
        lab_c = lab.ncite.sum(); lab_p = float((lab.ncite * (lab.lab_ai >= 0.25)).sum() / lab_c) if lab_c else np.nan
        non_c = fr.ncite.sum()
        comb = (lab_c * (lab_p if lab_c else 0) + non_c * p) / (lab_c + non_c) if n else np.nan
        rows.append(dict(stratum=st, sample_texts=n, sample_flagged=k, sample_share=p, lo=lo, hi=hi, sample_share_per_work=pw,
                         sample_mean_ai_share=float(sc.ai_share.mean()) if n else np.nan,
                         lab_citables=len(lab), lab_citations=int(lab_c), lab_share=lab_p, nonlab_citations=int(non_c), combined_share=comb))
        cov.append(dict(stratum=st, frame_works=len(fr), frame_citations=int(non_c), with_open_source=int(fr.any_source.sum()),
                        with_arxiv=int(fr.arxiv.notna().sum()), attempted=len(m), usable_texts=n,
                        usable_of_attempted=n / max(1, len(m)), citations_covered=float(sc.ncite.sum() / max(1, non_c)),
                        **{f'src_{s}': int((sc.source == s).sum()) for s in ('arxiv', 'pmc', 'oa_pdf')}))
        fv = fr.v1.dropna(); sv = sc.v1.dropna()
        bias.append(dict(stratum=st, frame_v1_abstract_flag=float(fv.mean()) if len(fv) else np.nan, frame_v1_n=len(fv),
                         frame_v1_flag_cite_weighted=float((fr.ncite * fr.v1).sum() / fr.loc[fr.v1.notna(), 'ncite'].sum()) if len(fv) else np.nan,
                         sample_v1_abstract_flag=float(sv.mean()) if len(sv) else np.nan, sample_v1_n=len(sv),
                         frame_arxiv=float(fr.arxiv.notna().mean()), sample_arxiv=float(sc.arxiv.notna().mean()) if n else np.nan,
                         frame_cs=float((fr.field == 'Computer Science').mean()), sample_cs=float((sc.field == 'Computer Science').mean()) if n else np.nan,
                         frame_logcbc=float(np.log1p(fr.cbc).mean()), sample_logcbc=float(np.log1p(sc.cbc).mean()) if n else np.nan))
    R = pd.DataFrame(rows); R.to_csv(RES / 'q2v2_strata.csv', index=False)
    pd.DataFrame(cov).to_csv(RES / 'q2v2_coverage.csv', index=False)
    pd.DataFrame(bias).to_csv(RES / 'q2v2_bias.csv', index=False)
    M[M.scored].groupby(['stratum', 'source', 'version']).size().rename('texts').reset_index().to_csv(RES / 'q2v2_versions.csv', index=False)
    print(R.round(4).to_string()); print(pd.DataFrame(cov).round(3).to_string()); print(pd.DataFrame(bias).round(3).to_string())
    # citing side: references to scored citables
    fl = pd.concat([pd.DataFrame(dict(wid=W.loc[W.is_lab, 'wid'], f=W.loc[W.is_lab, 'lab_ai'] >= 0.25, src='lab')),
                    pd.DataFrame(dict(wid=M.loc[M.scored, 'key'].str[1:].astype(np.int64), f=M.loc[M.scored, 'flag'].astype(bool), src='sample'))])
    fl = fl.drop_duplicates('wid').merge(W[['wid', 'year']], on='wid')
    P = pd.read_parquet(DATA / 'paper_measures.parquet')
    Ci = pd.read_parquet(DATA / 'citing.parquet')[['key']].reset_index().rename(columns={'index': 'ci'})
    X = E.merge(fl, on='wid').merge(Ci, on='ci')
    # expected flag of each reference from its cited-year x class stratum (combined share): removes the cited-year mix
    X = X.merge(W[['wid', 'stratum']], on='wid', how='left')
    X['e'] = X.stratum.map(R.set_index('stratum').combined_share).fillna(0.0)
    rec = X[X.year >= 2023].groupby('key').agg(k_rec=('f', 'sum'), n_rec=('f', 'size'), e_rec=('e', 'sum'))
    old = X[X.year.between(2016, 2021)].groupby('key').f.agg(['sum', 'size']).rename(columns={'sum': 'k_old', 'size': 'n_old'})
    Q = P.set_index('key').join(rec).join(old).reset_index()
    Q[['k_rec', 'n_rec', 'e_rec', 'k_old', 'n_old']] = Q[['k_rec', 'n_rec', 'e_rec', 'k_old', 'n_old']].fillna(0)
    Q['grp'] = np.where(Q.ai_share <= 0, 'none', np.where(Q.ai_share < 0.25, 'some', 'flagged'))
    Q['lab0'] = Q.labs.map(lambda s: json.loads(s)[0])
    rng = np.random.default_rng(SEED); out = []
    for yr in ['2023–2026', 2023, 2024, 2025, 2026]:
        for g in ('none', 'some', 'flagged'):
            x = Q[(Q.grp == g) & ((Q.year >= 2023) if yr == '2023–2026' else (Q.year == yr))]
            if x.n_rec.sum() < 20:
                continue
            A = x.groupby('lab0')[['k_rec', 'n_rec', 'k_old', 'n_old', 'e_rec']].sum().values
            tot = A.sum(0); bs = []
            for _ in range(1000):
                s = np.bincount(rng.integers(0, len(A), len(A)), minlength=len(A)) @ A
                bs.append((s[0] / s[1] if s[1] else np.nan, s[2] / s[3] if s[3] else np.nan, (s[0] - s[4]) / s[1] if s[1] else np.nan))
            bs = np.array(bs); ex = bs[:, 0] - bs[:, 1]
            out.append(dict(citing_year=str(yr), group=g, papers=len(x), papers_with_recent=int((x.n_rec > 0).sum()), recent_refs=int(tot[1]),
                            share=tot[0] / tot[1], lo=np.nanpercentile(bs[:, 0], 2.5), hi=np.nanpercentile(bs[:, 0], 97.5),
                            old_refs=int(tot[3]), floor=tot[2] / tot[3] if tot[3] else np.nan,
                            excess=tot[0] / tot[1] - (tot[2] / tot[3] if tot[3] else np.nan), ex_lo=np.nanpercentile(ex, 2.5), ex_hi=np.nanpercentile(ex, 97.5),
                            expected_mix=tot[4] / tot[1], mix_excess=(tot[0] - tot[4]) / tot[1],
                            mix_lo=np.nanpercentile(bs[:, 2], 2.5), mix_hi=np.nanpercentile(bs[:, 2], 97.5)))
    O = pd.DataFrame(out); O.to_csv(RES / 'q2v2_citing.csv', index=False); print(O.round(4).to_string())
    # within lab: cited-AI share on own AI; narrowing measures on cited-AI share
    import within as Wt
    Q['cai'] = np.where(Q.n_rec >= 2, Q.k_rec / Q.n_rec.clip(lower=1), np.nan)
    Q['flag'] = (Q.ai_share >= 0.25).astype(float); Q['dose10'] = Q.ai_share * 10
    wr = []
    Q['cai_mix'] = np.where(Q.n_rec >= 2, (Q.k_rec - Q.e_rec) / Q.n_rec.clip(lower=1), np.nan)
    L = Wt.long_by_lab(Q[Q.year >= 2023]); L['labyear'] = L.lab + '|' + L.year.astype(str)
    for y_ in ('cai', 'cai_mix'):
        for spec, xs in (('flag', ['flag', 'log_nrefs']), ('dose10', ['dose10', 'log_nrefs'])):
            b, lo, hi, n, nl = Wt.fe_boot(L, y_, xs, ['labyear'])
            wr.append(dict(y=y_, x=xs[0], beta=b, lo=lo, hi=hi, papers=n, labs=nl))
    for m in ('canon', 'top1', 'logcbc_adj', 'venue_div', 'field_div'):
        b, lo, hi, n, nl = Wt.fe_boot(L, m, ['cai', 'dose10', 'log_nrefs', 'recent'], ['labyear'])
        wr.append(dict(y=m, x='cai (with own dose, log refs, recent share)', beta=b, lo=lo, hi=hi, papers=n, labs=nl,
                       sd_y=float(Q.loc[Q.year >= 2023, m].std()), sd_x=float(Q.cai.std())))
    pd.DataFrame(wr).to_csv(RES / 'q2v2_within.csv', index=False); print(pd.DataFrame(wr).round(4).to_string())
    json.dump(dict(v2_threshold=thr, sample_texts=int(M.scored.sum()), lab_citables_matched=int(W.is_lab.sum())), open(RES / 'q2v2_meta.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
