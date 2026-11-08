"""Shared pieces of the non-text sameness measures (README-SAMENESS in sameness_report.py's header): loaders, the year x draw contrast tables, bootstrap weights.

Every measure produces V[b, t]: its value in bootstrap draw b (row 0 = the point estimate) and year t = 2016..2025. Period values are the plain mean of the year values
(each year weighs the same), so a contrast is mean(post years) - mean(pre years); intervals are 2.5/97.5 percentiles over the lab-cluster draws (stratified by school).
`direction` tells which way is "more alike": +1 when a rise means more sameness (overlap, concentration), -1 when a fall does (distances, entropy).
"""
import zlib

import numpy as np
import pandas as pd

import study_common as C
import study_labstats as LS

YEARS = LS.YEARS
CONTRASTS = LS.CONTRASTS
B = 400
SEED = 20261108
SAMPLES = ('refs10', 'journal')     # reference-complete papers (>= 10 references); journal papers only (reference coverage stable over time)


def scope_schools():
    """(scope name, school list): ALL, EXCL_PARTIAL, then each school (the layout of study_analyze.scopes)."""
    yield 'ALL', C.SCHOOLS
    yield 'EXCL_PARTIAL', [s for s in C.SCHOOLS if s not in C.PARTIAL]
    for s in C.SCHOOLS:
        yield s, [s]


def interval(draws, est, center=False, axis=0):
    """95% percentile interval of bootstrap draws. center=True re-centres it on the point estimate (est + percentile - median of the draws): resampling labs with
    replacement duplicates their references, which inflates count-based concentration, so the raw percentile interval of such a measure sits off its estimate."""
    d = np.asarray(draws, float)
    with np.errstate(all='ignore'):
        if not np.isfinite(d).any():
            return np.full(np.shape(est), np.nan), np.full(np.shape(est), np.nan)
        lo, med, hi = (np.nanpercentile(d, q, axis=axis) for q in (2.5, 50, 97.5))
    if center:
        return est + lo - med, est + hi - med
    return lo, hi


def contrast_rows(meta, V, contrasts=CONTRASTS, center=False):
    """V: (B+1, T) -> (series DataFrame, contrasts DataFrame). NaN years are ignored in a period mean. center: see interval()."""
    est = V[0]
    lo, hi = interval(V[1:], est, center)
    ser = pd.DataFrame(dict(meta, year=YEARS, est=est, lo=lo, hi=hi))
    rows = []
    for name, (post, pre) in contrasts.items():
        ip = [y - YEARS[0] for y in post]
        ir = [y - YEARS[0] for y in pre]
        with np.errstate(all='ignore'):
            a = np.nanmean(V[:, ip], axis=1)
            b = np.nanmean(V[:, ir], axis=1)
        d = a - b
        lo_, hi_ = (float(x) for x in interval(d[1:], d[0], center)) if np.isfinite(d[1:]).sum() >= 30 else (np.nan, np.nan)
        rows.append(dict(meta, contrast=name, est=float(d[0]), lo=lo_, hi=hi_, pre=float(b[0]), post=float(a[0])))
    return ser, pd.DataFrame(rows)


def decode_refs(blob):
    if blob is None:
        return np.empty(0, np.int64)
    t = zlib.decompress(blob).decode()
    return np.array(t.split(','), dtype=np.int64) if t else np.empty(0, np.int64)


def load_papers(snap, out):
    """Panel + reference lists: DataFrame k, year, school, source_type, n_refs, refs (np arrays of numeric OpenAlex ids). Papers outside oa_extra have no list."""
    import sqlite3
    pan = pd.read_parquet(out / 'work' / 'panel.parquet', columns=['k', 'year', 'school', 'topic_name', 'topic_sub', 'has_abs'])
    db = sqlite3.connect(f'file:{snap / "universe" / "oa_extra.sqlite"}?mode=ro', uri=True)
    ex = pd.read_sql('select id as k, source_type, n_refs, refs from works', db)
    db.close()
    ex['refs'] = [decode_refs(b) for b in ex.pop('refs')]
    return pan.merge(ex, on='k', how='left')


def sample_mask(p, sample):
    ok = p['n_refs'].fillna(0) >= 10
    if sample == 'journal':
        ok &= p['source_type'].eq('journal')
    return ok


def lab_index(lp):
    """All labs in a stable order with their school: (labs array, school array)."""
    d = lp.drop_duplicates('lab_id').sort_values('lab_id')
    return d['lab_id'].to_numpy(), d['school'].to_numpy()


def weights_for(lp, B_=B, seed=SEED):
    labs, sch = lab_index(lp)
    return labs, sch, LS.weights(sch, B_, seed)
