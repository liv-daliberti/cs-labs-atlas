"""Shared constants of the AI-in-revision study (README.md in this directory): paths, the detector parameter, dates.

All paths come from tools/atlas_paths.py; `RV_DATA` overrides the output directory, `RV_REPORT_DIR` the report directory, `RV_UNIVERSE_DB` the paper set.
The detector is a parameter everywhere: --detector v2 (default) or v3 (ai-writing/detector_v3, when trained); see rv_score.py.
"""
import json
import os
import re
import sys as _sys
from pathlib import Path as _Path

_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths (ai-writing is exempt from the sys.path test)
import atlas_paths as P  # noqa: E402

AIW = _Path(__file__).resolve().parents[1]
for _d in (AIW / 'dose', AIW / 'embeddings', AIW / 'diversity', AIW / 'detector_v2'):
    if str(_d) not in _sys.path:
        _sys.path.append(str(_d))

MAIN_AIW = P.CODE / 'ai-writing'              # the main checkout: models and stores are not in a code snapshot
EMB = P.EMBEDDINGS
UNIVERSE_DB = _Path(os.environ.get('RV_UNIVERSE_DB') or EMB / 'universe.sqlite')
TEXTS_DB = EMB / 'texts.sqlite'
DATA = _Path(os.environ.get('RV_DATA') or MAIN_AIW / 'data' / 'revision')
DB = DATA / 'revision.sqlite'                 # pairs, versions, texts (zlib), passage scores, abstract scores
RESULTS = DATA / 'results'
REPORTS = _Path(os.environ.get('RV_REPORT_DIR') or AIW / 'diversity' / 'reports')
OAI_DIR = P.SWEEPS / 'claude-cmu-20261017' / 'raw' / 'arxiv_oai'          # the local OAI-PMH harvest (vendor/cmu_tools/arxiv_oai.py)
BULK_LISTING = P.SWEEPS / 'claude-cmu-20261017' / 'raw' / 'arxiv_bulk_listing.jsonl'   # latest-version cache of the arxiv_bulk channel
BUCKET = 'https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf'   # public bulk copy; never arxiv.org
API = 'https://storage.googleapis.com/storage/v1/b/arxiv-dataset/o'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
CHATGPT = '2022-12-01'                        # v1 "before" = dated before 1 Dec 2022 (ChatGPT 30 Nov 2022)
LAST_YEAR = 2025                              # owner rule: no 2026 in any plot or series
V2_MODEL = MAIN_AIW / 'detector_v2' / 'models' / 'all' / 'model'
V2_THRESHOLD = 0.0008531202983449121          # 1% FPR by design on calibration passages (dose/dcommon.py)
V3_DIR = MAIN_AIW / 'detector_v3'


def log(**kw):
    print(json.dumps(kw, default=str), flush=True)


STAMP = re.compile(r'arXiv:\s*(\d{4}\.\d{4,5}|[a-z\-]+(?:\.[A-Z]{2})?/\d{7})v(\d+)\s+\[[^\]]+\]\s+(\d{1,2})\s+([A-Z][a-z]{2})\s+(\d{4})')
MONTHS = {m: i + 1 for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}


def stamp_date(text):
    """(version, 'YYYY-MM-DD') from the arXiv margin stamp ('arXiv:2105.01234v2 [cs.LG] 12 Oct 2021') in the first page's text; (None, None) if absent."""
    m = STAMP.search(text or '')
    if not m:
        return None, None
    return int(m.group(2)), f'{int(m.group(5)):04d}-{MONTHS[m.group(4)]:02d}-{int(m.group(3)):02d}'
