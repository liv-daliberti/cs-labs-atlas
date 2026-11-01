"""Build regression check: compare the packages a rebuild just wrote with the snapshot taken before it.

snapshot  counts of the current packages (or of a backup directory laid out like hierarchy/): per school the report.json
          counts, the rows of lab_papers / student_papers, the lab-student pairs and PIs, the lab papers per PI, and a
          digest of each row set (sha256 over the sorted, key-sorted JSON rows; equal digests mean identical row sets)
check     the current packages against a snapshot -> hierarchy/BUILD-REGRESSION.md and BUILD-REGRESSION.json; flags
            a school-level count that moves more than 5% (and by 5 or more),
            a PI losing more than 30% of their lab papers and at least 10 (or vanishing with 10 or more),
            a PI gaining more than 100% and at least 20,
            an unavailability-ledger reason count (hierarchy/<school>/unavailable-summary.json by_reason; docs/UNAVAILABLE.md)
            moving more than 25% and by 20 or more papers, or the ledger vanishing (2026-10-30). The ledger moves as the
            collectors download and re-check, so its threshold is wider than the school counts'.
          Exit status 2 when anything is flagged (hierarchy/rebuild.sh then holds the release), 0 otherwise.

usage: build_regression.py snapshot --out counts.json [--from DIR]
       build_regression.py check --before counts.json [--after counts.json | --from DIR] [--md PATH] [--json PATH]
"""
import argparse, collections, gzip, hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)

SCHOOL_PCT, SCHOOL_MIN = 0.05, 5
PI_LOSS_PCT, PI_LOSS_MIN = 0.30, 10
PI_GAIN_PCT, PI_GAIN_MIN = 1.00, 20
KEY_COUNTS = ['pis', 'lab_papers', 'students', 'lab_student_pairs', 'student_paper_links', 'pis_with_lab_papers',
              'pis_with_students', 'pis_complete_chain', 'labs_with_student_papers']
ROWS = ['lab_papers', 'student_papers', 'lab_student_pairs', 'pis']
LEDGER_PCT, LEDGER_MIN = 0.25, 20


def ledger(d):
    """The ledger's counts by reason_code (docs/UNAVAILABLE.md): {built_at, papers, by_reason}, None without a summary."""
    p = Path(d) / 'unavailable-summary.json'
    if not p.exists():
        return None
    x = json.loads(p.read_text())
    return dict(built_at=x.get('built_at'), papers=x.get('papers'), by_reason=dict(sorted((x.get('by_reason') or {}).items())))


def jsonl(p):
    with gzip.open(p, 'rt') as f:
        return [json.loads(l) for l in f]


def digest(rows):
    lines = sorted(json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows)
    h = hashlib.sha256()
    for l in lines:
        h.update(l.encode() + b'\n')
    return h.hexdigest()


def code_commit():
    try:
        return subprocess.run(['git', '-C', str(P.WORK), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def counts(base):
    out = {}
    for s in P.SCHOOL_IDS:
        d = Path(base) / s
        if not (d / 'report.json').exists():
            continue
        rep = json.loads((d / 'report.json').read_text())
        lp, sp = jsonl(d / 'lab_papers.jsonl.gz'), jsonl(d / 'student_papers.jsonl.gz')
        stu = json.loads((d / 'students.json').read_text())
        pis = json.loads((d / 'pis.json').read_text())
        pairs = [dict(r, _lab=pi) for pi, rs in sorted(stu.items()) for r in rs]
        per_pi = collections.Counter(r['pi'] for r in lp)
        out[s] = dict(builtAt=rep.get('builtAt'), report=rep.get('counts') or {},
                      rows=dict(lab_papers=len(lp), student_papers=len(sp), lab_student_pairs=len(pairs), pis=len(pis)),
                      digests=dict(lab_papers=digest(lp), student_papers=digest(sp), students=digest(pairs), pis=digest(pis)),
                      per_pi={p['pi']: per_pi.get(p['pi'], 0) for p in pis}, ledger=ledger(d))
    return dict(at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), source=str(base), code=code_commit(), schools=out)


def pct(a, b):
    return (b - a) / a if a else (float('inf') if b else 0.0)


def compare(before, after):
    res = dict(before=dict(at=before['at'], source=before['source'], code=before.get('code')),
               after=dict(at=after['at'], source=after['source'], code=after.get('code')),
               thresholds=dict(school_pct=SCHOOL_PCT, school_min=SCHOOL_MIN, pi_loss_pct=PI_LOSS_PCT, pi_loss_min=PI_LOSS_MIN,
                               pi_gain_pct=PI_GAIN_PCT, pi_gain_min=PI_GAIN_MIN, ledger_pct=LEDGER_PCT, ledger_min=LEDGER_MIN),
               schools={}, flags=[])
    for s in P.SCHOOL_IDS:
        b, a = before['schools'].get(s), after['schools'].get(s)
        if not b or not a:
            if b or a:
                res['flags'].append(dict(school=s, kind='school_missing', detail='only in ' + ('before' if b else 'after')))
            continue
        r = dict(builtAt=dict(before=b['builtAt'], after=a['builtAt']), rows={}, report={}, identical={}, pis_changed=[])
        for k in ROWS:
            r['rows'][k] = dict(before=b['rows'][k], after=a['rows'][k])
            if abs(pct(b['rows'][k], a['rows'][k])) > SCHOOL_PCT and abs(a['rows'][k] - b['rows'][k]) >= SCHOOL_MIN:
                res['flags'].append(dict(school=s, kind='school_rows', count=k, before=b['rows'][k], after=a['rows'][k]))
        for k in sorted(set(b['report']) | set(a['report'])):
            x, y = b['report'].get(k, 0), a['report'].get(k, 0)
            if x != y:
                r['report'][k] = dict(before=x, after=y)
                if k in KEY_COUNTS and abs(pct(x, y)) > SCHOOL_PCT and abs(y - x) >= SCHOOL_MIN:
                    res['flags'].append(dict(school=s, kind='school_count', count=k, before=x, after=y))
        r['identical'] = {k: b.get('digests', {}).get(k) == a.get('digests', {}).get(k) for k in a.get('digests', {})}
        for pi in sorted(set(b['per_pi']) | set(a['per_pi'])):
            x, y = b['per_pi'].get(pi), a['per_pi'].get(pi)
            if x == y:
                continue
            r['pis_changed'].append(dict(pi=pi, before=x, after=y))
            x0, y0 = x or 0, y or 0
            if y0 < x0 and (x0 - y0) >= PI_LOSS_MIN and (y is None or (x0 - y0) / x0 > PI_LOSS_PCT):
                res['flags'].append(dict(school=s, kind='pi_vanished' if y is None else 'pi_loss', pi=pi, before=x, after=y))
            elif y0 > x0 and (y0 - x0) >= PI_GAIN_MIN and pct(x0, y0) > PI_GAIN_PCT:
                res['flags'].append(dict(school=s, kind='pi_new' if x is None else 'pi_gain', pi=pi, before=x, after=y))
        lb, la = b.get('ledger'), a.get('ledger')  # the unavailability ledger's reason counts (2026-10-30)
        r['ledger'] = {}
        if lb and not la:
            res['flags'].append(dict(school=s, kind='ledger_missing', detail='unavailable-summary.json only in before'))
        elif lb and la:
            for code in sorted(set(lb['by_reason']) | set(la['by_reason'])):
                x, y = lb['by_reason'].get(code, 0), la['by_reason'].get(code, 0)
                if x != y:
                    r['ledger'][code] = dict(before=x, after=y)
                    if abs(pct(x, y)) > LEDGER_PCT and abs(y - x) >= LEDGER_MIN:
                        res['flags'].append(dict(school=s, kind='ledger_reason', count=code, before=x, after=y))
        res['schools'][s] = r
    return res


def md(res):
    L = ['# Build regression', '',
         f"Before: {res['before']['source']} (snapshot {res['before']['at']}, code {str(res['before']['code'])[:10]}). "
         f"After: {res['after']['source']} (counted {res['after']['at']}, code {str(res['after']['code'])[:10]}). "
         'Written by tools/build_regression.py.', '',
         f"Flags: school counts moving more than {SCHOOL_PCT:.0%} (and by {SCHOOL_MIN}+), a PI losing more than {PI_LOSS_PCT:.0%} "
         f"and {PI_LOSS_MIN}+ lab papers, a PI gaining more than {PI_GAIN_PCT:.0%} and {PI_GAIN_MIN}+, an unavailability-ledger "
         f"reason count moving more than {LEDGER_PCT:.0%} and by {LEDGER_MIN}+.", '',
         f"**{len(res['flags'])} flagged.**", '',
         '| School | lab papers | student-paper links | lab-student pairs | PIs | row sets identical | PIs changed |', '|---|---|---|---|---|---|---|']
    for s, r in res['schools'].items():
        cell = lambda k: f"{r['rows'][k]['before']} → {r['rows'][k]['after']}"
        same = ', '.join(k for k, v in r['identical'].items() if v) or 'none'
        L.append(f"| {s} | {cell('lab_papers')} | {cell('student_papers')} | {cell('lab_student_pairs')} | {cell('pis')} | {same} | {len(r['pis_changed'])} |")
    if res['flags']:
        L += ['', '## Flagged', '']
        for f in res['flags']:
            L.append('- ' + ', '.join(f'{k}: {v}' for k, v in f.items()))
    for s, r in res['schools'].items():
        if r['report'] or r['pis_changed'] or r.get('ledger'):
            L += ['', f'## {s}', '']
            if r['report']:
                L.append('Report counts that changed: ' + '; '.join(f"{k} {v['before']} → {v['after']}" for k, v in r['report'].items()))
            if r.get('ledger'):
                L += [''] if r['report'] else []
                L.append('Ledger reasons that changed: ' + '; '.join(f"{k} {v['before']} → {v['after']}" for k, v in r['ledger'].items()))
            big = sorted(r['pis_changed'], key=lambda x: -abs((x['after'] or 0) - (x['before'] or 0)))[:15]
            if big:
                L.append('')
                L.append('Largest per-PI changes: ' + '; '.join(f"{x['pi']} {x['before']} → {x['after']}" for x in big))
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    a1 = sub.add_parser('snapshot'); a1.add_argument('--out', required=True); a1.add_argument('--from', dest='src', default=str(P.HIERARCHY))
    a2 = sub.add_parser('check'); a2.add_argument('--before', required=True); a2.add_argument('--after'); a2.add_argument('--from', dest='src', default=str(P.HIERARCHY))
    a2.add_argument('--md', default=str(P.data('BUILD-REGRESSION.md'))); a2.add_argument('--json', default=str(P.data('BUILD-REGRESSION.json')))
    a = ap.parse_args(argv)
    if a.cmd == 'snapshot':
        c = counts(a.src)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(c, indent=1, ensure_ascii=False))
        print(json.dumps({s: v['rows'] for s, v in c['schools'].items()}))
        return 0
    before = json.loads(Path(a.before).read_text())
    after = json.loads(Path(a.after).read_text()) if a.after else counts(a.src)
    res = compare(before, after)
    Path(a.json).write_text(json.dumps(res, indent=1, ensure_ascii=False))
    Path(a.md).write_text(md(res))
    print(json.dumps(dict(flags=len(res['flags']), identical={s: r['identical'] for s, r in res['schools'].items()})))
    for f in res['flags'][:30]:
        print('FLAG', json.dumps(f, ensure_ascii=False))
    return 2 if res['flags'] else 0


if __name__ == '__main__':
    sys.exit(main())
