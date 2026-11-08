"""Paths and constants of the 12-school homogenization study (README.md). Importable with the standard library (pandas where noted)."""
import json
import subprocess
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[2] / 'tools'
sys.path.append(str(_TOOLS))   # atlas_paths: every path (ai-writing is exempt from the sys.path test)
import atlas_paths as P  # noqa: E402

SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan', 'uchicago', 'gatech', 'harvard', 'jhu', 'washu']
PARTIAL = ['harvard', 'jhu', 'washu']
EMB_SCHOOLS = SCHOOLS[:9]        # the schools the earlier build embedded and scored (home-school containers)
MODELS = ['specter2_proximity', 'specter2_base', 'scincl', 'qwen3_0p6b', 'gte_qwen2_1p5b', 'bge_m3', 'nomic_v15']
HEADLINE_MODEL = 'specter2_proximity'
FIRST, LAST = 2016, 2025         # no 2026 in any figure or estimate
PRE_END, POST_START = 2022, 2023 # ChatGPT launched 2022-11-30; post = 2023 onward; 2022 is in the pre period (sensitivity: dropped)
STUDY = Path(P.HOMOGENIZATION_STUDY)


def sources():
    d = Path(P.AI_WRITING) / 'data'
    return {'ai_scores_v3': d / 'ai-scores-v3', 'detector_v3': Path(P.AI_WRITING) / 'detector_v3', 'sections': d / 'sections',
            'embeddings': d / 'embeddings', 'citnovelty_v3': d / 'citnovelty-v3', 'labstudy': d / 'labstudy',
            'reports': Path(P.AI_WRITING) / 'diversity' / 'reports', 'labstudy_code': Path(__file__).resolve().parents[1] / 'labstudy'}


def release_dir(name='latest'):
    return Path(P.RELEASES) / name


def snapshot_dir(snap_id):
    return STUDY / 'snapshots' / snap_id


def results_dir(snap_id):
    return STUDY / 'results' / snap_id


def git_commit():
    try:
        return subprocess.run(['git', '-C', str(Path(__file__).resolve().parent), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=20).stdout.strip() or None
    except Exception:  # noqa: BLE001
        return None


def oa_short(x):
    """'https://openalex.org/W123' -> 'W123'; None stays None."""
    return x.rsplit('/', 1)[-1] if isinstance(x, str) and x else None


def coverage(snap):
    """Per-school coverage of the release membership by the earlier build's scores and embeddings (needs pandas)."""
    import gzip

    import sqlite3

    import pandas as pd
    uni = pd.read_parquet(snap / 'ai' / 'papers_v3.parquet', columns=['paper_id', 'flag_abstract', 'ai_share_main'])
    db = sqlite3.connect(f'file:{snap / "universe" / "universe.sqlite"}?mode=ro', uri=True)
    u = pd.read_sql('select paper_id, oa from papers', db)
    db.close()
    u['oa'] = u['oa'].map(oa_short)
    emb = set()
    for sc in EMB_SCHOOLS:
        ip = snap / 'embeddings' / HEADLINE_MODEL / sc / 'abstract.index.sqlite'
        if ip.exists():
            d2 = sqlite3.connect(f'file:{ip}?mode=ro', uri=True)
            emb.update(r[0] for r in d2.execute('select paper_id from papers'))
            d2.close()
    dl = snap / 'delta' / 'delta_scores.parquet'
    if dl.exists():     # papers scored and embedded after the earlier build (study_delta_build.py)
        dp = pd.read_parquet(dl)
        dpap = pd.read_json(snap / 'delta' / 'delta_papers.jsonl.gz', lines=True)[['paper_id', 'oa']]
        dpap['oa'] = dpap['oa'].map(oa_short)
        if 'flag_abstract' not in dp:
            dp['flag_abstract'] = float('nan')
        uni = pd.concat([uni, dp[['paper_id', 'flag_abstract', 'ai_share_main']]], ignore_index=True)
        u = pd.concat([u, dpap], ignore_index=True)
        for ip in sorted((snap / 'delta' / 'embeddings' / HEADLINE_MODEL).glob('*/abstract.index.sqlite')):
            d3 = sqlite3.connect(f'file:{ip}?mode=ro', uri=True)
            emb.update(r[0] for r in d3.execute('select paper_id from papers'))
            d3.close()
    u['emb'] = u['paper_id'].isin(emb)
    u = u.drop_duplicates('paper_id').merge(uni.drop_duplicates('paper_id'), on='paper_id', how='left').dropna(subset=['oa']).drop_duplicates('oa').set_index('oa')
    hp = snap / 'delta' / 'copies_held.parquet'
    hm = dict(pd.read_parquet(hp)[['k', 'has_copy']].drop_duplicates('k').itertuples(index=False)) if hp.exists() else None
    out = {}
    for s in SCHOOLS:
        ids = {}
        for line in gzip.open(snap / 'release' / 'hierarchy' / s / 'lab_papers.jsonl.gz', 'rt'):
            r = json.loads(line)
            if not r.get('year') or not FIRST <= r['year'] <= LAST:
                continue
            k = oa_short(r.get('oa')) or r.get('atlasWorkId')
            ids[k] = ids.get(k, False) or bool((r.get('appointment') or {}).get('periodId'))
        n = max(len(ids), 1)
        inu = [k for k in ids if k in u.index]
        sub = u.loc[inu] if inu else u.iloc[:0]
        pis = len(json.loads((snap / 'release' / 'hierarchy' / s / 'pis.json').read_text()))
        out[s] = {'lab_papers_2016_2025': len(ids), 'pis': pis, 'in_universe': len(inu) / n, 'abstract_embedded': float(sub['emb'].sum()) / n,
                  'abstract_flag': float(sub['flag_abstract'].notna().sum()) / n, 'fulltext_v3': float(sub['ai_share_main'].notna().sum()) / n,
                  'period_supported': sum(ids.values()) / n,
                  'held': (sum(1 for k in ids if hm.get(k)) / n) if hm is not None else None}
    return {'by_school': out}
