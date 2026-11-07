"""Shared pieces of the advisor-student lineage study (README.md): paths, the link tables, the vectors.

Every path is configurable by environment (one command re-runs on new data):
  LINEAGE_HIER   hierarchy directory: <hier>/<school>/{students.json, student_papers.jsonl.gz, lab_papers.jsonl.gz, pis.json}
                 (a snapshot) or the live <hier>/<school>/derived/ layout; default P.HIERARCHY (live)
  LINEAGE_OUT    output directory; default <ai-writing>/data/lineage (git-ignored)
  LINEAGE_TAG    subdirectory of OUT for one run (default 'latest')
  LINEAGE_AI     per-paper detector table (parquet with paper_id, ai_share, flag_abstract); default AI_SCORES/papers.parquet
Years: no 2026 anywhere; series 2017-2025 (the PI history window starts 2016), post = 2023-2025.
"""
import gzip
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
AIW = HERE.parent
for _d in (AIW / 'embeddings',):
    if str(_d) not in sys.path:
        sys.path.append(str(_d))
import ecommon as C  # noqa: E402
import store  # noqa: E402

P = C.P
HIER = Path(os.environ.get('LINEAGE_HIER') or P.HIERARCHY)
OUT = Path(os.environ.get('LINEAGE_OUT') or (P.AI_WRITING / 'data' / 'lineage'))
TAG = os.environ.get('LINEAGE_TAG') or 'latest'
RUN = OUT / TAG
AI_TABLE = Path(os.environ.get('LINEAGE_AI') or (P.AI_SCORES / 'papers.parquet'))
SCHOOLS = C.SCHOOLS
Y0, Y1 = 2016, 2025            # no 2026
POST = (2023, 2025)
HIST = 3                       # years of PI history
M_POOL = 6                     # size-matched PI pool
K_NN = 3
REPS = 20
MODELS_ABS = ['specter2_base', 'specter2_proximity', 'scincl', 'qwen3_0p6b', 'gte_qwen2_1p5b', 'bge_m3', 'nomic_v15']
MODELS_FT = ['specter2_base', 'specter2_proximity', 'qwen3_0p6b', 'gte_qwen2_1p5b', 'bge_m3', 'nomic_v15']


def hfile(school, name):
    for p in (HIER / school / name, HIER / school / 'derived' / name):
        if p.exists():
            return p
    return None


def log(**kw):
    C.log(**kw)


def norm_name(s):
    s = re.sub(r'[^a-z ]', '', re.sub(r'\s+', ' ', str(s or '').lower().replace('-', ' ')))
    return ' '.join(sorted(s.split()))


def role_of(rec):
    """phd / other / unspecified from students.json roles (and relation roles)."""
    txt = ' '.join([str(r) for r in rec.get('roles', [])] + [str(x.get('role', '')) for x in rec.get('relations', []) if isinstance(x, dict)]).lower()
    if 'phd' in txt or 'doctoral' in txt or 'ph.d' in txt:
        return 'phd'
    if any(k in txt for k in ('undergrad', 'master', 'postdoc', 'bachelor', 'visiting', 'intern', 'researcher', 'other', 'staff')):
        return 'other'
    return 'unspecified'


def universe_index():
    db = sqlite3.connect(f'file:{C.UNIVERSE_DB}?mode=ro', uri=True, timeout=600)
    up = pd.read_sql('select paper_id, oa, year from papers', db)
    db.close()
    up['okey'] = up['oa'].fillna('').str.rsplit('/', n=1).str[-1]
    return up


def build_links(schools=None):
    """(student_papers df, pi_papers df, students df) from the hierarchy packages, mapped onto universe paper ids."""
    up = universe_index()
    by_oa = dict(zip(up['okey'], up['paper_id']))
    year = dict(zip(up['paper_id'], up['year']))
    sp_rows, pp_rows, st_rows = [], [], []
    for s in schools or SCHOOLS:
        f_sp, f_lp, f_st = hfile(s, 'student_papers.jsonl.gz'), hfile(s, 'lab_papers.jsonl.gz'), hfile(s, 'students.json')
        if not (f_sp and f_lp and f_st):
            continue
        roles, pi_of = {}, {}
        for pi, lst in json.load(open(f_st)).items():
            for rec in lst:
                for k in (rec.get('person'), rec.get('atlasId')):
                    if k:
                        roles[(pi, k)] = (role_of(rec), rec.get('name'))
        with gzip.open(f_lp, 'rt') as f:
            for line in f:
                r = json.loads(line)
                pid = r.get('atlasWorkId') or by_oa.get((r.get('oa') or '').rsplit('/', 1)[-1])
                if pid and pid in year:
                    pp_rows.append((s, r['pi'], pid, year[pid], '|'.join(norm_name(b) for b in (r.get('byline') or []))))
        with gzip.open(f_sp, 'rt') as f:
            for line in f:
                r = json.loads(line)
                pid = r.get('atlasWorkId') or by_oa.get((r.get('oa') or '').rsplit('/', 1)[-1])
                sid = r.get('studentAtlasId') or r['student']
                role, nm = roles.get((r['pi'], r['student']), roles.get((r['pi'], sid), ('unspecified', r.get('name'))))
                st_rows.append((s, r['pi'], f'{s}:{sid}', nm or r.get('name'), role))
                if pid and pid in year:
                    sp_rows.append((s, r['pi'], f'{s}:{sid}', pid, year[pid], r['status']))
    sp = pd.DataFrame(sp_rows, columns=['school', 'pi', 'student', 'paper_id', 'year', 'status']).drop_duplicates()
    pp = pd.DataFrame(pp_rows, columns=['school', 'pi', 'paper_id', 'year', 'byline']).drop_duplicates(['school', 'pi', 'paper_id'])
    stu = pd.DataFrame(st_rows, columns=['school', 'pi', 'student', 'name', 'role']).drop_duplicates(['school', 'pi', 'student'])
    # a pair is verified when any of its papers is: the status of a paper link stays per row
    sp['lab'] = sp['school'] + '|' + sp['pi']
    pp['lab'] = pp['school'] + '|' + pp['pi']
    stu['lab'] = stu['school'] + '|' + stu['pi']
    return sp, pp, stu


def load_vectors(model, kind):
    """(ids list, float32 matrix) of a model's per-paper vectors over the school containers (raw, not centred)."""
    ids, mats = [], []
    for s in SCHOOLS:
        if not store.container_path(model, s, kind).exists():
            continue
        c = store.load(model, s, kind)
        ids += [str(i) for i in c['ids']]
        mats.append(c['M'].astype(np.float32))
    return ids, (np.vstack(mats) if mats else np.zeros((0, 1), np.float32))


def unit(Z):
    """Centre on the mean and normalise (the study's convention)."""
    Z = Z - Z.mean(0, keepdims=True)
    return Z / np.clip(np.linalg.norm(Z, axis=1, keepdims=True), 1e-9, None)
