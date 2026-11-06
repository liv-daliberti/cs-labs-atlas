"""Shared pieces of the AI-dose study (README.md in this directory): paths, the v1 abstract text surface, thresholds.

Paths come from tools/atlas_paths.py: AI_SCORES (the container, parts and tables) and EMBEDDINGS (the inputs) live in the main
checkout, git-ignored. The detector models are data too (ai-writing/detector*/ ... models), also read from the main checkout,
whatever code snapshot a job runs from.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path (ai-writing is exempt from the sys.path test)
import atlas_paths as P  # noqa: E402
import json, os, re, sys, time  # noqa: E402

AIW = _Path(__file__).resolve().parents[1]   # this checkout's (or snapshot's) ai-writing: the code
for _d in (AIW / 'detector_v2', AIW / 'diversity', AIW / 'embeddings'):
    if str(_d) not in sys.path:
        sys.path.append(str(_d))   # v2common (the detector's normalizer and passage splitter) and diversity/common

SCORES = P.AI_SCORES
PARTS = SCORES / 'parts'
DB = SCORES / 'ai_scores.sqlite'
RESULTS = SCORES / 'results'
EMB = P.EMBEDDINGS
TEXTS_DB = EMB / 'texts.sqlite'
UNIVERSE_DB = EMB / 'universe.sqlite'
OA_FIELDS = EMB / 'oa_fields.sqlite'
MAIN_AIW = P.CODE / 'ai-writing'            # the main checkout: models and old scores are not in a code snapshot
V1_MODEL = MAIN_AIW / 'detector' / 'all'
V2_MODEL = MAIN_AIW / 'detector_v2' / 'models' / 'all' / 'model'
V1_THRESHOLD = 1.2460367611311106e-06       # detector/all/metrics.json: 1% of validation human abstracts
V2_THRESHOLD = 0.0008531202983449121     # detector_v2/results/all/metrics.json: 99th percentile of 59,838 calibration passages (1% FPR by design)
DETECTOR_VERSION = 'v1abs+v2par'
if os.environ.get('AI_DETECTOR') == 'v3':      # owner 2026-11-05: the v3 container (dose_build_v3.py): main-body passages, 0.3% threshold on z, abstained passages excluded
    V2_THRESHOLD = json.load(open(MAIN_AIW / 'detector_v3' / 'results' / 'operating_point.json'))['thr_z']
    DETECTOR_VERSION = 'v3main'
SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan', 'uchicago', 'gatech']
PRE_YEARS = range(2016, 2022)               # the placebo window: before ChatGPT (30 Nov 2022), so the "dose" there is detector noise
LAST_FULL_YEAR = 2025                       # owner 2026-11-04: 2026 is a partial year, so it appears in no plot and in no post-period estimate (it stays in the containers)
POST_YEARS = range(2023, LAST_FULL_YEAR + 1)


def log(**kw):
    print(json.dumps(kw, default=str), flush=True)


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def norm1(t):
    """ai-writing/detector.py norm (v1), copied: the v1 detector's surface for abstracts."""
    t = re.sub(r'<[^>]+>', ' ', str(t or ''))
    t = re.sub(r'\*\*|__|^#+\s*', '', t, flags=re.M)
    t = re.sub(r'^\s*(?:abstract|summary)\s*[:.\-—]?\s*', '', t, flags=re.I)
    return re.sub(r'\s+', ' ', t).strip()


def text1(title, abstract):
    return f'{norm1(title)} | {norm1(abstract)}'


def local_tmp():
    """Node-local scratch directory (not NFS) for sqlite files that are written."""
    import getpass
    import os
    import tempfile
    d = _Path(os.environ.get('TMPDIR') or tempfile.gettempdir()) / f'ai-dose-{getpass.getuser()}'
    d.mkdir(parents=True, exist_ok=True)
    return d


def publish(src, dest):
    """Copy a locally written file next to `dest` and rename it into place (atomic for readers); the local copy is removed."""
    import shutil
    dest = _Path(dest)
    part = dest.with_name('.tmp-' + dest.name)
    shutil.copyfile(src, part)
    part.replace(dest)
    _Path(src).unlink(missing_ok=True)
