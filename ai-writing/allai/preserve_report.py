"""Content-preservation summary of a rewrite style: embedding cosine original vs rewrite per model, the automatic number / named-term checks, the detector.

  preserve_report.py --style polish|paraphrase  -> EMB/allai/results/preservation_<style>.json
cosine: raw (the stored pooled vectors) and after centring each corpus on its own mean; `random` = the cosine of a paper's original with another paper's
rewrite (a floor: how similar two unrelated papers look in this model). Checks: flags_<style>.parquet (build_texts.py). Detector: detect_<style>.parquet.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'embeddings'))
import ecommon as C  # noqa: E402
import emb_load as L  # noqa: E402
from models import ORDER  # noqa: E402

ALLAI = C.EMB / 'allai'
SUF = {'polish': '__allai', 'paraphrase': '__para'}


def unit(X):
    X = X.astype(np.float32)
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)


def main(style):
    out = {'style': style, 'cosine': {}}
    fl = pd.read_parquet(ALLAI / f'flags_{style}.parquet')
    ok = fl[fl['ok'] == 1]
    out['rewrites'] = int(len(fl)); out['ok'] = int(len(ok)); out['kept'] = int(fl['keep'].sum())
    out['filtered_reasons'] = fl[fl['keep'] == 0]['reason'].value_counts().to_dict()
    out['any_number_lost_share'] = float((ok['num_lost'] > 0).mean()); out['any_number_added_share'] = float((ok['num_new'] > 0).mean())
    out['any_term_lost_share'] = float((ok['term_lost'] > 0).mean())
    has_n = ok[ok['n_num'] > 0]; has_t = ok[ok['n_term'] > 0]
    out['numbers_lost_share_of_numbers'] = float(has_n['num_lost'].sum() / has_n['n_num'].sum()); out['terms_lost_share_of_terms'] = float(has_t['term_lost'].sum() / has_t['n_term'].sum())
    out['papers_with_numbers'] = int(len(has_n)); out['papers_with_terms'] = int(len(has_t))
    out['len_ratio_median'] = float(ok['len_ratio'].median())
    dp = ALLAI / f'detect_v1_{style}.parquet'   # the v1 ABSTRACT detector (the v2 paragraph detector must not be used on abstracts)
    if dp.exists():
        d = pd.read_parquet(dp)
        d = d[d['year'] <= 2025]   # 2026 is a partial year
        out['detector'] = {'detector': 'v1 abstract detector (ai-writing/detector.py), 1% false-positive threshold on validation human abstracts, title | abstract'}
        out['detector'].update({k: dict(n=int(len(g)), flagged=float(g['flagged'].mean())) for k, g in d.groupby('kind')})
        o = d[d['kind'] == 'original']; r = d[d['kind'] == 'rewrite']
        for name, g in (('original_pre2023', o[o.year < 2023]), ('original_post2023', o[o.year >= 2023]), ('rewrite_pre2023', r[r.year < 2023]), ('rewrite_post2023', r[r.year >= 2023])):
            out['detector'][name] = dict(n=int(len(g)), flagged=float(g['flagged'].mean()))
        kept = set(fl[fl['keep'] == 1]['paper_id'])
        out['detector']['original_kept_papers'] = dict(n=int(o['paper_id'].isin(kept).sum()), flagged=float(o[o['paper_id'].isin(kept)]['flagged'].mean()))
        out['detector']['rewrite_kept_papers'] = dict(n=int(r['paper_id'].isin(kept).sum()), flagged=float(r[r['paper_id'].isin(kept)]['flagged'].mean()))
    rng = np.random.default_rng(C.SEED)
    for m in ORDER:
        try:
            ids_o, Xo, _ = L.vectors(m, 'abstract'); ids_a, Xa, _ = L.vectors(m + SUF[style], 'abstract')
        except Exception:
            continue
        if not ids_a:
            continue
        ro = {p: i for i, p in enumerate(ids_o)}
        keep = [(ro[p], j) for j, p in enumerate(ids_a) if p in ro]
        io, ia = np.array([a for a, _ in keep]), np.array([b for _, b in keep])
        A, B = Xo[io], Xa[ia]
        raw = (unit(A) * unit(B)).sum(1)
        Ac, Bc = unit(A - A.mean(0)), unit(B - B.mean(0))
        cen = (Ac * Bc).sum(1)
        perm = rng.permutation(len(B))
        rnd = (Ac * Bc[perm]).sum(1)
        pct = lambda v: {k: float(x) for k, x in zip(('mean', 'p05', 'median'), (v.mean(), np.percentile(v, 5), np.median(v)))}  # noqa: E731
        # share of papers whose own rewrite is the nearest of 2,000 random rewrites (identity retrieval)
        sel = rng.choice(len(B), min(2000, len(B)), replace=False)
        S = Ac[sel] @ Bc[sel].T
        out['cosine'][m] = dict(papers=int(len(io)), raw=pct(raw), centred=pct(cen), random_centred=pct(rnd), retrieval_at_1=float((S.argmax(1) == np.arange(len(sel))).mean()))
        C.log(model=m, style=style, **out['cosine'][m]['centred'])
    (ALLAI / 'results').mkdir(exist_ok=True)
    (ALLAI / 'results' / f'preservation_{style}.json').write_text(json.dumps(out, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--style', default='polish')
    main(ap.parse_args().style)
