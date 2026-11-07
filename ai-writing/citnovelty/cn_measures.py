"""Per-paper and per-lab-year citation measures (Experiment A) from the stream results (cn_stream.py merge) and the universe's reference lists.

  cn_measures.py paper     -> DATA/results/paper_measures.parquet   one row per universe paper (paper_id, oa_id, year, school)
  cn_measures.py lab       -> DATA/results/lab_overlap.parquet      one row per lab-year: reference overlap among the lab's papers

Per paper
  n_refs, n_refs_meta            references listed in the snapshot / of which the snapshot knows year, source or subfield
  z_p10, z_med, n_pairs          Uzzi et al. (2013) atypicality: for every pair of cited venues (OpenAlex source ids of journals, conferences and book series;
                                 repositories and unknown sources are left out), z = (observed - null mean) / null sd of the pair's count among the universe's papers
                                 of the SAME YEAR. The null (K label permutations, `K_NULL`) shuffles the venue labels over the year's reference slots, which keeps every
                                 paper's number of references and every venue's total count (the degree-preserving null); duplicates within a paper are collapsed to
                                 a venue set. Low z = atypical. z_p10 is the 10th percentile (conventional novelty), z_med the median (conventional). Needs >= 10 pairs.
  cd1, cd2, cd3, cd5 (+ n_cites_w)  disruption index CD_w = (n_i - n_j) / (n_i + n_j + n_k) over citing works published in years 0..w after the paper's year (Funk & Owen-Smith
                                 2017; Park, Leahey & Funk 2023 use w = 5). n_i, n_j exact; n_k = SAMPLE_MOD * (sampled works citing a reference of the paper) - n_j. A window counts
                                 only when year + w <= LAST_YEAR (a window that fits); `cd_av` uses every citing year up to 2025 (variable window: compare only within a year).
                                 Needs n_refs >= 5 and at least 3 citing works in the window.
  rs_sub, rs_field, h_sub, h_venue  Rao-Stirling diversity of the references' primary subfields / fields (distance = 1 - cosine similarity of the subfields' co-citation
                                 profiles over all universe reference lists), Shannon entropy (bits) of the subfields and of the cited venues; needs >= 5 references with meta
  ref_age_med                    median age (paper year - reference year) of the references: a control for citing recent work
"""
import argparse
import sqlite3

import numpy as np
import pandas as pd

import cn_common as C

K_NULL = 10
VENUE_TYPES = ('journal', 'conference', 'book series')
MIN_PAIRS = 10
SEED = 20261105


def load_stream():
    z = np.load(C.DATA / 'counts.npz')
    db = sqlite3.connect(f'file:{C.DB}?mode=ro', uri=True)
    meta = pd.read_sql('select * from meta', db)
    info = dict(db.execute('select k, v from info').fetchall())
    db.close()
    return z, meta, info


def focal_table():
    foc = C.focal_works()
    return foc


def uzzi_year(papers, rng, K=K_NULL):
    """papers: list of (row id, array of venue codes (with repeats, one per reference slot)). -> {row id: (z_p10, z_med, n_pairs)}."""
    if not papers:
        return {}
    rows = np.concatenate([np.full(len(s), i) for i, (_, s) in enumerate(papers)])
    labels = np.concatenate([s for _, s in papers])
    nv = int(labels.max()) + 1
    tri = {}

    def pairs_of(u):
        k = len(u)
        if k < 2:
            return None
        if k not in tri:
            tri[k] = np.triu_indices(k, 1)
        a, b = tri[k]
        return u[a].astype(np.int64) * nv + u[b]

    def keys_for(lab):
        out, owner = [], []
        start = 0
        for i, (_, s) in enumerate(papers):
            seg = lab[start:start + len(s)]; start += len(s)
            u = np.unique(seg)
            p = pairs_of(u)
            if p is not None:
                out.append(p); owner.append(np.full(len(p), i))
        return (np.concatenate(out), np.concatenate(owner)) if out else (np.zeros(0, np.int64), np.zeros(0, np.int64))

    obs_keys, owner = keys_for(labels)
    uk, inv = np.unique(obs_keys, return_inverse=True)
    obs_count = np.bincount(inv, minlength=len(uk)).astype(float)
    s1 = np.zeros(len(uk)); s2 = np.zeros(len(uk))
    for _ in range(K):
        perm = rng.permutation(labels)
        pk, _o = keys_for(perm)
        pu, pc = np.unique(pk, return_counts=True)
        pos = np.searchsorted(pu, uk); pos[pos >= len(pu)] = max(len(pu) - 1, 0)
        c = np.where((len(pu) > 0) & (pu[pos] == uk), pc[pos], 0).astype(float) if len(pu) else np.zeros(len(uk))
        s1 += c; s2 += c * c
    mu = s1 / K
    sd = np.sqrt(np.maximum(s2 / K - mu * mu, 0))
    ok = sd > 0
    zz = np.where(ok, (obs_count - mu) / np.where(ok, sd, 1), np.nan)
    zp = zz[inv]
    out = {}
    order = np.argsort(owner, kind='stable')
    own_s, z_s = owner[order], zp[order]
    bounds = np.searchsorted(own_s, np.arange(len(papers) + 1))
    for i, (rid, _) in enumerate(papers):
        v = z_s[bounds[i]:bounds[i + 1]]
        v = v[np.isfinite(v)]
        out[rid] = (float(np.percentile(v, 10)), float(np.median(v)), int(len(v))) if len(v) >= MIN_PAIRS else (np.nan, np.nan, int(len(v)))
    return out


def subfield_distance(ref_lists, level):
    """d[i, j] = 1 - cosine similarity of the co-occurrence profiles of categories i, j over the reference lists; returns (index dict, matrix)."""
    cats = sorted({c for r in ref_lists for c in r})
    ix = {c: i for i, c in enumerate(cats)}
    n = len(cats)
    M = np.zeros((n, n))
    for r in ref_lists:
        u, c = np.unique([ix[x] for x in r], return_counts=True)
        if len(u) < 2:
            continue
        M[np.ix_(u, u)] += np.outer(c, c)
    np.fill_diagonal(M, 0)
    nrm = np.linalg.norm(M, axis=1, keepdims=True)
    Z = M / np.maximum(nrm, 1e-12)
    d = 1 - Z @ Z.T
    np.fill_diagonal(d, 0)
    return ix, np.clip(d, 0, 1)


def entropy_bits(codes):
    _, c = np.unique(codes, return_counts=True)
    p = c / c.sum()
    return float(-(p * np.log2(p)).sum())


def cmd_paper():
    z, meta, info = load_stream()
    foc = focal_table()
    ids = z['ids']
    assert len(ids) == len(foc) and all(int(f[0][1:]) == int(i) for f, i in zip(foc[:50], ids[:50])), 'focal order changed since the stream: re-run prepare + stream'
    meta = meta.set_index('id')
    years = z['years'].astype(int)
    nf = len(foc)
    mi, mj, mrc = z['ni'].astype(float), z['nj'].astype(float), z['rc'].astype(float)
    mod = int(z['sample_mod'])
    # --- reference meta per focal paper
    mid = meta.index.to_numpy()
    sub_of = meta['subfield'].to_dict(); fld_of = meta['field'].to_dict(); src_of = meta['source_id'].to_dict()
    sty_of = meta['source_type'].to_dict(); yr_of = meta['year'].to_dict()
    venue_code = {}
    ref_sub, ref_fld, ref_ven, ref_age = [], [], [], []
    ven_slots = []
    n_meta = np.zeros(nf, int)
    for k, (_, y, refs) in enumerate(foc):
        sub = [int(sub_of[r]) for r in refs if r in sub_of and pd.notna(sub_of[r])]
        fl = [int(fld_of[r]) for r in refs if r in fld_of and pd.notna(fld_of[r])]
        ven = [src_of[r] for r in refs if r in src_of and isinstance(src_of[r], str) and sty_of.get(r) in VENUE_TYPES]
        codes = np.array([venue_code.setdefault(v, len(venue_code)) for v in ven], dtype=np.int64)
        n_meta[k] = sum(1 for r in refs if r in sub_of)
        ref_sub.append(sub); ref_fld.append(fl); ven_slots.append(codes)
        ref_age.append([y - int(yr_of[r]) for r in refs if r in yr_of and pd.notna(yr_of[r]) and yr_of[r] >= 1900])
    C.log(step='meta joined', focal=nf, venues=len(venue_code))
    rng = np.random.default_rng(SEED)
    # --- Uzzi per year
    zres = {}
    for y in sorted(set(years)):
        idx = [k for k in range(nf) if years[k] == y and len(ven_slots[k]) >= 2]
        zres.update(uzzi_year([(k, ven_slots[k]) for k in idx], rng))
        C.log(step='uzzi', year=int(y), papers=len(idx))
    # --- Rao-Stirling
    ix_s, d_s = subfield_distance([r for r in ref_sub if len(r) >= 2], 'subfield')
    ix_f, d_f = subfield_distance([r for r in ref_fld if len(r) >= 2], 'field')

    def rs(refs, ix, d):
        if len(refs) < 5:
            return np.nan
        u, c = np.unique([ix[x] for x in refs], return_counts=True)
        p = c / c.sum()
        return float(p @ d[np.ix_(u, u)] @ p)
    rows = []
    last = C.LAST_YEAR
    cdw = {}
    for w in (1, 2, 3, 5):
        a = mi[:, :w + 1].sum(1); j = mj[:, :w + 1].sum(1); r = mrc[:, :w + 1].sum(1)
        nk = np.maximum(mod * r - j, 0)
        den = a + j + nk
        cd = np.where((a + j >= 3) & (den > 0), (a - j) / np.where(den > 0, den, 1), np.nan)
        fits = (years + w) <= last
        cdw[w] = (np.where(fits, cd, np.nan), a + j)
    # variable window up to LAST_YEAR
    cd_av = np.full(nf, np.nan); ncit_av = np.zeros(nf)
    for k in range(nf):
        w = last - years[k]
        if w < 0:
            continue
        w = min(w, C.MAX_DY)
        a = mi[k, :w + 1].sum(); j = mj[k, :w + 1].sum(); r = mrc[k, :w + 1].sum()
        nk = max(mod * r - j, 0)
        ncit_av[k] = a + j
        if a + j >= 3 and a + j + nk > 0:
            cd_av[k] = (a - j) / (a + j + nk)
    for k, (oid, y, refs) in enumerate(foc):
        zr = zres.get(k, (np.nan, np.nan, 0))
        ok_refs = len(refs) >= 5
        rows.append(dict(oa_id=oid, year=int(y), n_refs=len(refs), n_refs_meta=int(n_meta[k]), z_p10=zr[0], z_med=zr[1], n_pairs=zr[2],
                         cd1=cdw[1][0][k] if ok_refs else np.nan, cd2=cdw[2][0][k] if ok_refs else np.nan, cd3=cdw[3][0][k] if ok_refs else np.nan,
                         cd5=cdw[5][0][k] if ok_refs else np.nan, cd_av=cd_av[k] if ok_refs else np.nan,
                         n_cites_av=int(ncit_av[k]), n_cites_w1=int(cdw[1][1][k]), n_cites_w5=int(cdw[5][1][k]),
                         rs_sub=rs(ref_sub[k], ix_s, d_s), rs_field=rs(ref_fld[k], ix_f, d_f),
                         h_sub=entropy_bits(ref_sub[k]) if len(ref_sub[k]) >= 5 else np.nan,
                         h_venue=entropy_bits(ven_slots[k]) if len(ven_slots[k]) >= 5 else np.nan,
                         ref_age_med=float(np.median(ref_age[k])) if len(ref_age[k]) >= 5 else np.nan))
    df = pd.DataFrame(rows)
    papers, lp = C.universe_papers()
    papers['oa_id'] = papers['oa'].str.rsplit('/', n=1).str[-1]
    out = papers[['paper_id', 'oa_id', 'home_school']].merge(df, on='oa_id', how='left')
    C.RESULTS.mkdir(parents=True, exist_ok=True)
    out.to_parquet(C.RESULTS / 'paper_measures.parquet', index=False)
    C.log(step='paper_measures', rows=len(out), with_refs=int((out['n_refs'] >= 5).sum()), z=int(out['z_p10'].notna().sum()), cd5=int(out['cd5'].notna().sum()),
          cd1=int(out['cd1'].notna().sum()), rs=int(out['rs_sub'].notna().sum()))


def cmd_lab():
    """Reference overlap among a lab's papers: for every lab-year with >= MIN_PAPERS papers of >= 5 references, the mean over paper pairs of Jaccard and cosine
    (bibliographic coupling / sqrt(n_a n_b)) of the reference sets; and the same against the lab's papers of the previous three years (`jac_prev`, `cos_prev`)."""
    foc = {i: set(r) for i, _, r in C.focal_works()}
    papers, lp = C.universe_papers()
    papers['oa_id'] = papers['oa'].str.rsplit('/', n=1).str[-1]
    oa = papers.set_index('paper_id')['oa_id']
    lp = lp[lp['year'].between(C.FIRST_YEAR, C.LAST_YEAR)].copy()
    lp['oa_id'] = lp['paper_id'].map(oa)
    lp['refs'] = lp['oa_id'].map(lambda i: foc.get(i))
    lp = lp[lp['refs'].map(lambda r: r is not None and len(r) >= 5)].drop_duplicates(['lab_id', 'paper_id'])
    MIN_PAPERS = 3
    rows = []
    for lab, g in lp.groupby('lab_id'):
        by = {y: list(zip(gg['paper_id'], gg['refs'])) for y, gg in g.groupby('year')}
        for y, items in by.items():
            if len(items) < MIN_PAPERS:
                continue
            jac, cs = [], []
            for a in range(len(items)):
                for b in range(a + 1, len(items)):
                    x, z = items[a][1], items[b][1]
                    i = len(x & z)
                    jac.append(i / len(x | z)); cs.append(i / np.sqrt(len(x) * len(z)))
            prev = [it for yy in (y - 1, y - 2, y - 3) for it in by.get(yy, [])]
            jp, cp = [], []
            if prev:
                for _, x in items:
                    for _, z in prev:
                        i = len(x & z)
                        jp.append(i / len(x | z)); cp.append(i / np.sqrt(len(x) * len(z)))
            rows.append(dict(lab_id=lab, year=int(y), n_papers=len(items), jac=float(np.mean(jac)), cos=float(np.mean(cs)),
                             jac_prev=float(np.mean(jp)) if jp else np.nan, cos_prev=float(np.mean(cp)) if cp else np.nan, n_prev=len(prev)))
    out = pd.DataFrame(rows)
    out.to_parquet(C.RESULTS / 'lab_overlap.parquet', index=False)
    C.log(step='lab_overlap', lab_years=len(out), labs=out['lab_id'].nunique())


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['paper', 'lab'])
    a = ap.parse_args()
    cmd_paper() if a.cmd == 'paper' else cmd_lab()
