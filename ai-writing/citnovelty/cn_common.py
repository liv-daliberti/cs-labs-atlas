"""Shared constants and loaders of the citation-based novelty study (README.md in this directory).

All paths come from tools/atlas_paths.py (slots EMBEDDINGS, AI_SCORES, SCRATCH, AI_WRITING); `CN_DATA` overrides the output directory and
`CN_REPORT_DIR` the report directory, so a re-run on another paper set or detector only changes configuration (cn_run.sh).
"""
import json
import os
import sqlite3
import sys as _sys
import zlib
from pathlib import Path as _Path

_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths (ai-writing is exempt from the sys.path test)
import atlas_paths as P  # noqa: E402

AIW = _Path(__file__).resolve().parents[1]
for _d in (AIW / 'dose', AIW / 'embeddings'):
    if str(_d) not in _sys.path:
        _sys.path.append(str(_d))

EMB = P.EMBEDDINGS
UNIVERSE_DB = _Path(os.environ.get('CN_UNIVERSE_DB') or EMB / 'universe.sqlite')     # papers, lab_papers: the paper set (swap for the final set after release 20261105i)
OA_EXTRA = _Path(os.environ.get('CN_OA_EXTRA') or EMB / 'oa_extra.sqlite')           # reference lists of the universe's works (dose/oa_extra.py)
OA_FIELDS = EMB / 'oa_fields.sqlite'
DATA = _Path(os.environ.get('CN_DATA') or P.CODE / 'ai-writing' / 'data' / 'citnovelty')      # git-ignored container directory
DB = DATA / 'citnovelty.sqlite'                                                     # stream results: meta of referenced works, citation counts
RESULTS = DATA / 'results'
REPORTS = _Path(os.environ.get('CN_REPORT_DIR') or AIW / 'diversity' / 'reports')
SCRATCH = P.SCRATCH
FIRST_YEAR, LAST_YEAR = 2016, 2025            # owner rule: no 2026 in any plot, series or estimate
MAX_DY = 10                                    # citation-year offsets stored: 0..10 (papers of 2016..2026 cited by works up to 2026)
SAMPLE_MOD = int(os.environ.get('CN_SAMPLE_MOD', '16'))   # n_k is estimated from the works whose id number % SAMPLE_MOD == 0, scaled by SAMPLE_MOD
BREAK = 2023                                   # post period starts 2023 (ChatGPT 30 Nov 2022; 2022 is the transition year)
PRE_YEARS = range(2016, 2022)
POST_YEARS = range(2023, LAST_YEAR + 1)


def log(**kw):
    print(json.dumps(kw, default=str), flush=True)


def wnum(u):
    return int((u or '').rsplit('/', 1)[-1].lstrip('W'))


def focal_works(first_year=2008):
    """[(oa_id 'W123', year, refs list of int)] of every universe work with an OpenAlex id, from oa_extra; deterministic order (by id)."""
    db = sqlite3.connect(f'file:{OA_EXTRA}?mode=ro', uri=True)
    out = []
    for i, y, n, b in db.execute('select id, year, n_refs, refs from works where year is not null order by id'):
        if y < first_year:
            continue
        s = zlib.decompress(b).decode() if b else ''
        out.append((i, y, [int(x) for x in s.split(',')] if s else []))
    db.close()
    return out


def universe_papers():
    """papers (paper_id, oa, year, home_school) and lab_papers (paper_id, lab_id, school, year) of the paper set."""
    import pandas as pd
    db = sqlite3.connect(f'file:{UNIVERSE_DB}?mode=ro', uri=True)
    papers = pd.read_sql('select paper_id, oa, doi, title, year, home_school from papers', db)
    lp = pd.read_sql('select paper_id, school, lab_id, year from lab_papers', db)
    db.close()
    return papers, lp


def local_tmp(need_bytes=1 << 30):
    """A node-local directory with room: $TMPDIR or /tmp, else /dev/shm."""
    import shutil
    for d in (os.environ.get('TMPDIR'), '/tmp', '/dev/shm'):
        if d and os.path.isdir(d) and shutil.disk_usage(d).free > need_bytes:
            return _Path(d)
    raise RuntimeError('no node-local directory with free space')
