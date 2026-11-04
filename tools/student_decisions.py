"""Per-person reviewed decisions about lab-page students (owner 2026-11-04: pre-joining and mixed-institution pages are decided person by person).

hierarchy/<key>/reviewed/student-decisions.json  {pi: {student name: {decision: uchicago | not | unclear, why, url?, quote?, observed?}}}
A row of a lab page whose person is decided `not` or `unclear` is not read by labpage_students_school.extract and not proposed by labpage_audit;
`uchicago` (evidenced as a student of the school) and anything undecided pass on to the standard rules. Names compare folded, whole.
"""
import json
import re
import unicodedata
from pathlib import Path

import atlas_paths as P  # noqa: E402


def fold(n):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKD', str(n or '')).lower()))


def load(key):
    f = Path(P.data('student-decisions.json', key))
    return json.loads(f.read_text()) if f.exists() else {}


def excluded(decisions, pi, name):
    """True when the person is decided `not` or `unclear` for this PI's lab."""
    d = (decisions.get(pi) or {})
    hit = next((v for k, v in d.items() if fold(k) == fold(name)), None)
    return bool(hit) and hit.get('decision') in ('not', 'unclear')
