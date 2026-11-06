"""Shared pieces of detector v4 candidates: v3's splits, data, generators and test sets are reused unchanged (v3common); only the
outputs (models, results, logs) live under detector_v4/. v3's own outputs are never written."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'detector_v3'))
import v3common as C3  # noqa: E402

V = C3.V
AIW = C3.AIW
OUT = AIW / 'detector_v4'
DATA = C3.DATA  # v3's data, read-only
MODELS, RESULTS, LOGS = OUT / 'models', OUT / 'results', OUT / 'logs'
V3RESULTS = C3.RESULTS
for _d in (MODELS, RESULTS, LOGS):
    _d.mkdir(parents=True, exist_ok=True)
EDIT_TASKS = ('polish', 'paraphrase', 'humanize', 'partial')   # an AI edit of a human passage
WRITTEN_TASKS = ('notes', 'continue')                           # AI wrote the passage (from notes / as a continuation)
