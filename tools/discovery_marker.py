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

import atlas_paths as P

RECORDS = 'labpage-audit-discovery.jsonl'
MARKER = 'labpage-audit-discovery.done.json'


def record_files(school, records=RECORDS):
    """The merged file, then the per-shard files of a sharded run (`<stem>.shard-<i>of<n>.jsonl`, oldest first): one writer per file, so no two array
    tasks ever append to one NFS file (V4a, 2026-11-17). `discover-merge` folds the shards into the merged file."""
    main = Path(P.data(records, school))
    stem = main.name[:-len('.jsonl')]
    shards = sorted(main.parent.glob(stem + '.shard-*.jsonl'), key=lambda f: (f.stat().st_mtime, f.name))
    return ([main] if main.exists() else []) + shards


def recorded(school):
    """PI names that have a record (merged file or shard files); a half-written last line (a killed job) is not a record."""
    out = set()
    for p in record_files(school):
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


def open_pis(school):
    """PI names still without a record, sorted: what a rerun or a shard has to do (per PI, never per school)."""
    rec = recorded(school)
    return [n for n in expected(school) if n not in rec]


def shard_of(pi, of):
    """Stable shard of a PI: a hash of its name, independent of which PIs are done, so shards started at different times never overlap."""
    return int(hashlib.sha256(pi.encode()).hexdigest()[:8], 16) % of


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


def merged(school):
    """Discovery complete AND every shard file folded into the merged file (`labpage_audit.py discover-merge`)."""
    main = Path(P.data(RECORDS, school))
    return status(school)['complete'] and all(f == main for f in record_files(school))


def history_pending(school):
    """PIs whose discovery found a people or alumni page (the page list `discover` keeps) but that have no Wayback history record yet (the students track's
    `labpage_audit.py history`). A PI without a people page never needs one. [] means the history step is done."""
    have = set()
    for f in record_files(school, 'labpage-audit-history.jsonl'):
        with open(f, encoding='utf-8') as fh:
            for line in fh:
                try:
                    have.add(json.loads(line)['pi'])
                except (ValueError, KeyError, TypeError):
                    continue
    out = {}
    for f in record_files(school):
        with open(f, encoding='utf-8') as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                    out[r['pi']] = r
                except (ValueError, KeyError, TypeError):
                    continue
    need = []
    for pi, r in out.items():
        ch = r.get('chosen') or {}
        pages = r.get('history_pages')
        if pages is None:   # a record written before `history_pages` existed
            pages = [ch.get(f'{k}_page') for k in ('people', 'alumni') if ch.get(f'{k}_page')] if ch.get('lab_site') else []
        if (pages or (r.get('prior_scan') or {}).get('history_pages')) and pi not in have:
            need.append(pi)
    return sorted(need)


if __name__ == '__main__':   # exit 0 = complete, so it also works as a stage_gate `check`:  <school> [merged | history]
    mode = sys.argv[2] if len(sys.argv) > 2 else ''
    if mode == 'history':
        pend = history_pending(sys.argv[1])
        print(json.dumps(dict(history_open=len(pend), first=pend[:10])))
        sys.exit(0 if not pend else 1)
    if mode == 'history-merged':
        h = Path(P.data('labpage-audit-history.jsonl', sys.argv[1]))
        left = [f.name for f in record_files(sys.argv[1], 'labpage-audit-history.jsonl') if f != h]
        print(json.dumps(dict(history_shard_files=left)))
        sys.exit(0 if not left else 1)
    if mode == 'merged':
        ok = merged(sys.argv[1])
        print(json.dumps(dict(merged=ok)))
        sys.exit(0 if ok else 1)
    st = status(sys.argv[1])
    print(json.dumps(st))
    sys.exit(0 if st['complete'] else 1)
