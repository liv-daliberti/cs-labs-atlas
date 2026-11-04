"""Shared constants and helpers of the all-papers embeddings study (README.md in this directory).

Paths come from tools/atlas_paths.py (slot EMBEDDINGS = ai-writing/data/embeddings in the main checkout, git-ignored).
Importable with numpy only (the store, the text hashing and the novelty maths are tested on fixtures in the atlas env).
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path (ai-writing is exempt from the sys.path test)
import atlas_paths as P  # noqa: E402
import hashlib, json, os, time  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

EMB = P.EMBEDDINGS                      # <model>/<school>/<kind>.npz + <kind>.index.sqlite; shared tables next to them
PARTS = EMB / 'parts'                   # <model>/<kind>/part_<job>_<seq>.npz: resumable chunks of a run, merged into the containers
RESULTS = EMB / 'results'               # analysis tables (Parquet)
REPORTS = _Path(__file__).resolve().parents[1] / 'diversity' / 'reports'
UNIVERSE_DB = EMB / 'universe.sqlite'   # papers, lab_papers (this study's paper list)
OA_FIELDS = EMB / 'oa_fields.sqlite'    # OpenAlex abstract_inverted_index + topics of the universe's works (from the bulk snapshot)
TEXTS_DB = EMB / 'texts.sqlite'         # abstracts and full-text bodies (zlib) with their hashes, keyed by paper id

SCHOOLS = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan', 'uchicago', 'gatech']  # the 7 released + 2 onboarding
RELEASED = ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford', 'michigan']
MIN_ABSTRACT_WORDS = 10                 # shorter strings are scraps ("Abstract", a DOI), not abstracts
SEED = 20261104


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(**kw):
    print(json.dumps(kw, default=str), flush=True)


def text_hash(s):
    return hashlib.sha1(s.encode('utf-8', 'ignore')).hexdigest()[:16]


def atomic_write(path, writer):
    """writer(tmp_path) writes the file; it is renamed into place, so a reader never sees a partial file."""
    path = _Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('tmp_' + str(os.getpid()) + '_' + path.name)
    try:
        writer(tmp)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


class Timer:
    def __init__(self):
        self.t0 = time.time()

    def __call__(self):
        return time.time() - self.t0


def use_extras():
    """Put env/embeddings-extra (adapters, bertopic, umap-learn, hdbscan, plotly: pip --target, none of them in the py310 env) at the END of
    sys.path, so the py310 packages win where both have one."""
    extra = str(P.ENV / 'embeddings-extra')
    if extra not in _sys.path:
        _sys.path.append(extra)
