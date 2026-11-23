"""Every figure, per school (owner 2026-11-23: "for the 1000 per school, make sure we have all the figures from above").

A school qualifies with >= MIN_POST scored and embedded full texts in 2023-2025. Each gets a view directory WORK/schools/<school>/ holding its own
papers_scored.parquet (its home-school papers), links to the shared vectors, run metadata and citation ages, and its own analysis/ and figures/.
Every stage of analyze.py runs on the view with the ALL-schools 50 topic clusters (looked up by paper key), so entropy is on one scale for every
school. A stage a school is too small for is logged and skipped; the rest still run. Each saved figure carries the school's name in its corner.
usage: schools.py prep | run <school> | list | index      (Slurm: e32_schools.slurm, one array task per school)
"""
import argparse
import json
import os
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze as A  # noqa: E402
import e32  # noqa: E402

MIN_POST = 1000
STAGES = ['curve', 'paper', 'lab', 'map', 'figure', 'timeband', 'distshift', 'entropy_scale', 'centroid', 'entropy_full', 'fullsample', 'allyears']
LABEL = {'cmu': 'CMU', 'mit': 'MIT', 'epfl': 'EPFL', 'gatech': 'Georgia Tech', 'hkust': 'HKUST', 'ntu': 'NTU', 'nus': 'NUS', 'pku': 'Peking',
         'sjtu': 'SJTU', 'cuhk': 'CUHK', 'zju': 'Zhejiang', 'jhu': 'Johns Hopkins', 'utaustin': 'UT Austin', 'uchicago': 'UChicago', 'vt': 'Virginia Tech'}


def base(a):
    return e32.work_dir(a.id)


def eligible(a):
    d = pd.read_parquet(base(a) / 'papers_scored.parquet', columns=['home_school', 'year', 'has_emb', 'ai_share_main'])
    d = d[d.has_emb & d.ai_share_main.notna() & d.year.between(2023, 2025)]
    n = d.home_school.value_counts()
    return n[n >= MIN_POST].sort_values(ascending=False)


def cmd_prep(a):
    B = base(a)
    P = pd.read_parquet(B / 'papers_scored.parquet')
    w, df, X = A.load(a)                     # refresh the all-schools cluster caches (adds the paper keys)
    for m in A.METRICS:
        A.clusters(w, df, X, m)
    el = eligible(a)
    for s in el.index:
        v = B / 'schools' / s
        (v / 'analysis').mkdir(parents=True, exist_ok=True); (v / 'figures').mkdir(exist_ok=True)
        P[P.home_school == s].to_parquet(v / 'papers_scored.parquet')
        for name in ('X_specter2_base.npy', 'RUN.json', 'citeage'):
            link = v / name
            if not link.exists():
                link.symlink_to(B / name)
    (B / 'schools' / 'SCHOOLS.json').write_text(json.dumps({s: int(n) for s, n in el.items()}, indent=1))
    print(json.dumps(dict(schools=len(el), list=list(el.index))))


def global_clusters(a):
    out = {}
    for m in A.METRICS:
        z = np.load(base(a) / 'analysis' / f'clusters_{m}.npz')
        out[m] = (dict(zip(z['keys'].astype(str), z['labels'])), z['centers'])
    return out


def cmd_run(a):
    import matplotlib.figure as MF
    s = a.school
    if s is None:   # array task beyond the eligible list (the refresh submits a fixed 0-39 range)
        print('no school for this array index'); return
    v = base(a) / 'schools' / s
    A.GLOBAL_CLUSTERS = global_clusters(a)
    # one school is ~1-10k papers: smaller equal-size draws and cell minimums than the all-schools run (still equal within the school)
    A.BAND_N, A.BAND_MIN, A.SCALE_N, A.ALLY_MIN = 50, 60, 300, 60
    e32.work_dir = lambda run_id, _v=v: _v               # every stage reads and writes the school's view
    name = LABEL.get(s, s.capitalize())
    orig = MF.Figure.savefig

    def savefig(self, *x, **k):                            # the school's name on every figure
        if not getattr(self, '_school_banner', False):
            self.text(0.995, 0.995, name, ha='right', va='top', fontsize=15, fontweight='bold', color='#2a78d6')
            self._school_banner = True
        return orig(self, *x, **k)
    MF.Figure.savefig = savefig
    log = {}
    for st in STAGES:
        try:
            if st == 'figure':
                import figure
                figure.main(v)
            else:
                getattr(A, 'stage_' + st)(a)
            log[st] = 'ok'
        except Exception as e:  # noqa: BLE001  a school too small for one stage still gets the others
            log[st] = f'{type(e).__name__}: {e}'[:300]
            traceback.print_exc()
        print(json.dumps(dict(school=s, stage=st, result=log[st])), flush=True)
    (v / 'STAGES.json').write_text(json.dumps(log, indent=1))


def cmd_list(a):
    for s in json.loads((base(a) / 'schools' / 'SCHOOLS.json').read_text()):
        print(s)


def cmd_index(a):
    """A table of which figure exists for which school -> schools/FIGURES.md"""
    B = base(a) / 'schools'
    sch = json.loads((B / 'SCHOOLS.json').read_text())
    figs = sorted({f.name for s in sch for f in (B / s / 'figures').glob('*.png')})
    lines = ['| school | 2023–25 papers | ' + ' | '.join(f.replace('.png', '') for f in figs) + ' |', '|' + '---|' * (len(figs) + 2)]
    for s, n in sch.items():
        lines.append(f'| {s} | {n:,} | ' + ' | '.join('✓' if (B / s / 'figures' / f).exists() else '—' for f in figs) + ' |')
    (B / 'FIGURES.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['prep', 'run', 'list', 'index'])
    ap.add_argument('school', nargs='?')
    ap.add_argument('--id', default='20261123')
    a = ap.parse_args()
    if a.cmd == 'run' and not a.school:
        a.school = json.loads((base(a) / 'schools' / 'SCHOOLS.json').read_text()).__iter__().__next__() if os.environ.get('SLURM_ARRAY_TASK_ID') is None else \
            (list(json.loads((base(a) / 'schools' / 'SCHOOLS.json').read_text())) + [None] * 64)[int(os.environ['SLURM_ARRAY_TASK_ID'])]
    globals()['cmd_' + a.cmd](a)


if __name__ == '__main__':
    main()
