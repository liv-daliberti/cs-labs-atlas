"""Completion of the stage-3 lab-page discovery step, recorded explicitly (R3d, 2026-11-17).

`labpage_audit.py discover` appends one record per PI to labpage-audit-discovery.jsonl, so the file exists after the first PI. The stage
runner used to treat the file's existence as "the step ran": a discover job that hit its time limit after 200 of 369 PIs (Purdue, ~212 s per
PI) left a partial file that read as finished, and the audit then ran on 200 PIs. A step is done only when every PI of pis.json has a record.
`discover` writes labpage-audit-discovery.done.json when it gets there (an audit trail; the decision is recomputed from the records, so a
pis.json that gained a PI afterwards makes the step open again). Light imports only: stage_gate calls this for every step check.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

RECORDS = 'labpage-audit-discovery.jsonl'
MARKER = 'labpage-audit-discovery.done.json'


def recorded(school):
    """PI names that have a record; a half-written last line (a killed job) is not a record."""
    out = set()
    p = Path(P.data(RECORDS, school))
    if not p.exists():
        return out
    with open(p, encoding='utf-8') as f:
        for line in f:
            try:
                out.add(json.loads(line)['pi'])
            except (ValueError, KeyError, TypeError):
                continue
    return out


def expected(school):
    """PI names the discovery must cover: pis.json, the file `discover` itself iterates."""
    p = Path(P.data('pis.json', school))
    if not p.exists():
        return []
    return sorted({x['pi'] for x in json.loads(p.read_text(encoding='utf-8')) if x.get('pi')})


def digest(names):
    return hashlib.sha256('\n'.join(names).encode()).hexdigest()


def status(school):
    """-> dict(complete, recorded, expected, missing (first 10), marker)."""
    exp, rec = expected(school), recorded(school)
    missing = [n for n in exp if n not in rec]
    marker = None
    mp = Path(P.data(MARKER, school))
    if mp.exists():
        try:
            marker = json.loads(mp.read_text(encoding='utf-8'))
        except ValueError:
            marker = None
    return dict(complete=bool(exp) and not missing, recorded=len(rec), expected=len(exp), missing=missing[:10],
                marker=bool(marker) and marker.get('pis_sha256') == digest(exp))


def write_marker(school, now):
    s = status(school)
    if not s['complete']:
        return None
    exp = expected(school)
    Path(P.data(MARKER, school)).write_text(json.dumps(dict(school=school, completed_at=now, pis=len(exp), pis_sha256=digest(exp)), indent=1) + '\n', encoding='utf-8')
    return True


if __name__ == '__main__':   # exit 0 = complete, so it also works as a stage_gate `check`
    st = status(sys.argv[1])
    print(json.dumps(st))
    sys.exit(0 if st['complete'] else 1)
