"""Owner ruling 2026-11-17: gates check correctness, not completeness.

An unresolved census candidate (no source places the person in a unit/window or ranks them; a display-name identity
collision nobody can resolve) is EXCLUDED with decision `excluded_unresolved`, a `reason`, a `reason_code` and `sources_tried`.
It is never a proven absence (`not_faculty_listed` still needs a covering source). Stage 2 passes only with an independent audit
of a seeded random sample of those rows, stored in hierarchy/<key>/reviewed/excluded-unresolved-audit.json and read by
stage_gate.g2 (fail closed: missing, unreviewed, stale, or too many failures).

  excluded_audit.py convert <key> [--dry-run]     pending_source_coverage / pending_identity_collision -> excluded_unresolved
  excluded_audit.py draw <key> --worker NAME [--n 50] [--seed S] [--redraw]
                                                   seeded sample (repeat draw of an unchanged population returns the same file)
  excluded_audit.py record <key> --reviewer NAME --verdicts FILE.json
                                                   FILE: [{"name", "verdict": "pass"|"fail", "evidence", "fixed": bool}]
  excluded_audit.py show <key>                    counts by reason code and the audit state

Audit rule: a row fails if a source proves the person admissible (CS-related ladder-equivalent faculty in the window). Pass when
at most MAX_FAIL rows fail and each failed row has been fixed (it is no longer excluded_unresolved); more failures = rework the class.
The audit is stale when an excluded_unresolved row exists now that was not in the drawn population (or changed since the draw), or
a drawn row left the class without being a recorded failure.
"""
import argparse, collections, datetime, hashlib, json, random, shutil, sys
from pathlib import Path

import atlas_paths as P  # noqa: E402

EXCLUDED = 'excluded_unresolved'
LEGACY_PENDING = {'pending_source_coverage': 'no_source_covers_window', 'pending_identity_collision': 'identity_collision'}
DEFAULT_N = 50
MAX_FAIL = 2


def _read(path, default=None):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def audit_path(key):
    return Path(P.data('excluded-unresolved-audit.json', key))


def review_path(key):
    return Path(P.data('cs-related-review.json', key))


def fingerprint(row):
    body = {k: v for k, v in row.items() if k != 'audited'}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def excluded_rows(decisions):
    """Rows keyed by name; a name shared by several excluded rows (identity collisions) is keyed 'name [source_id]' (or '#n') so none is dropped."""
    rows = [d for d in decisions if d.get('decision') == EXCLUDED]
    count = collections.Counter(d['name'] for d in decisions)   # all decisions: a key must not change when a sibling row is fixed
    out = {}
    for i, d in enumerate(rows):
        k = d['name'] if count[d['name']] == 1 else f"{d['name']} [{d.get('source_id') or '#' + str(i)}]"
        out[k] = d
    return out


def row_errors(d):
    bad = []
    if not (d.get('reason') or '').strip():
        bad.append('no reason')
    if not (d.get('reason_code') or '').strip():
        bad.append('no reason_code')
    if not d.get('sources_tried'):
        bad.append('no sources_tried')
    return bad


def ledger_path(key):
    return review_path(key).parent / 'excluded-converted-ledger.json'


def _content(row):
    """A row's content for the converted_on ledger: everything but the stamp itself."""
    return fingerprint({k: v for k, v in row.items() if k != 'converted_on'})


def _row_key(d):
    return f"{d['name']} [{d.get('source_id') or ''}]"


def convert(key, dry=False):
    doc = _read(review_path(key), {}) or {}
    n = collections.Counter()
    today = datetime.date.today().isoformat()
    ledger = _read(ledger_path(key), {}) or {}   # row key -> {content, converted_on}: an unchanged row keeps the date it was first converted
    for d in doc.get('decisions', []):          # a file that already holds converted rows seeds the ledger
        if d.get('decision') == EXCLUDED and d.get('converted_on') and _row_key(d) not in ledger:
            ledger[_row_key(d)] = dict(content=_content(d), converted_on=d['converted_on'])
    expanded = []
    for d in doc.get('decisions', []):
        code = LEGACY_PENDING.get(d.get('decision'))
        if code == 'identity_collision' and d.get('candidate_sources') and not d.get('source_id'):
            # one excluded row per candidate source id: stage_gate g2 wants every identity sharing a display name decided on its own id
            for cs in d['candidate_sources']:
                sid = cs.get('dblp') or ''.join(cs.get('openalex') or [])
                if sid:
                    expanded.append(dict(d, source_id=sid, candidate_sources=[cs]))
            if any(e['name'] == d['name'] for e in expanded):
                d['__drop'] = True
    doc['decisions'] = [x for x in doc.get('decisions', []) if not x.get('__drop')] + expanded
    for d in doc.get('decisions', []):
        code = LEGACY_PENDING.get(d.get('decision'))
        if not code:
            continue
        d['converted_from'] = d['decision']
        d['decision'] = EXCLUDED
        d['reason_code'] = code
        d['sources_tried'] = list(d.get('units_searched') or d.get('sources_tried') or [d.get('reason', '')[:300]])
        old = ledger.get(_row_key(d))
        content = _content(d)
        if old and old.get('content') == content:
            d['converted_on'] = old['converted_on']   # unchanged since the earlier conversion: keep its stamp
        else:
            d['converted_on'] = today
            ledger[_row_key(d)] = dict(content=content, converted_on=today)
        n[code] += 1
    if n and not dry:
        f = review_path(key)
        bak = f.parent.parent / 'tmp' / (f.name + '.bak-r2')   # never beside the reviewed file: a git-ignored file in reviewed/ is a gate finding (UW 2026-11-22)
        bak.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, bak)
        f.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
        ledger_path(key).write_text(json.dumps(dict(sorted(ledger.items())), indent=1, ensure_ascii=False) + '\n')
    return dict(n)


def pick(names, n, seed, key):
    names = sorted(names)
    return sorted(random.Random(f'{key}:{seed}').sample(names, min(n, len(names))))


def draw(key, worker, n=DEFAULT_N, seed=None, redraw=False):
    rows = excluded_rows((_read(review_path(key), {}) or {}).get('decisions', []))
    pop = {name: fingerprint(r) for name, r in rows.items()}
    old = _read(audit_path(key))
    seed = seed if seed is not None else (old or {}).get('seed') or hashlib.sha256(json.dumps(pop, sort_keys=True).encode()).hexdigest()[:12]
    if old and not redraw and old.get('population') == pop and old.get('seed') == seed and old.get('n') == n:
        return old
    doc = dict(school=key, drawn_at=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), seed=seed, n=n,
               worker=worker, population=pop, sample=pick(pop, n, seed, key), reviewer=None, verdicts=[])
    audit_path(key).parent.mkdir(parents=True, exist_ok=True)
    audit_path(key).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    return doc


def record(key, reviewer, verdicts):
    doc = _read(audit_path(key))
    if not doc:
        raise SystemExit('no audit drawn')
    if reviewer.strip() == (doc.get('worker') or '').strip():
        raise SystemExit('the reviewer must not be the worker who wrote the exclusions')
    doc['reviewer'] = reviewer
    doc['reviewed_at'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    doc['verdicts'] = verdicts
    audit_path(key).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    return doc


def findings(key, decisions):
    """Gate findings for the excluded_unresolved class; (bad, counts)."""
    rows = excluded_rows(decisions)
    counts = dict(excluded_unresolved=len(rows),
                  excluded_unresolved_by_reason=dict(collections.Counter(r.get('reason_code') or 'missing' for r in rows.values())))
    bad = [f"{name}: excluded_unresolved without {', '.join(row_errors(r))}" for name, r in rows.items() if row_errors(r)]
    if not rows:
        return bad, counts
    a = _read(audit_path(key))
    if not a:
        return bad + [f'excluded_unresolved audit missing: {len(rows)} rows (excluded_audit.py draw {key}, review the sample with a fresh independent reviewer, record)'], counts
    pop = a.get('population') or {}
    now = {name: fingerprint(r) for name, r in rows.items()}
    verdicts = {v.get('name'): v for v in a.get('verdicts') or []}
    fails = [v for v in verdicts.values() if v.get('verdict') == 'fail']
    new = sorted(n for n in now if pop.get(n) != now[n])
    gone = sorted(n for n in pop if n not in now and not (verdicts.get(n) or {}).get('verdict') == 'fail')
    counts.update(audit_sample=len(a.get('sample') or []), audit_failed=len(fails), audit_seed=a.get('seed'))
    if new or gone:
        bad.append(f'excluded_unresolved audit stale: {len(new)} rows added/changed and {len(gone)} rows removed since the draw ({(new + gone)[0]}...); redraw and re-review')
        return bad, counts
    if sorted(a.get('sample') or []) != pick(pop, a.get('n') or DEFAULT_N, a.get('seed'), key) or len(a['sample']) != min(a.get('n') or DEFAULT_N, len(pop)):
        bad.append('excluded_unresolved audit: sample is not the seeded draw of the population (redraw)')
    if not a.get('reviewer') or a.get('reviewer') == a.get('worker'):
        bad.append('excluded_unresolved audit: no independent reviewer recorded')
    elif set(verdicts) != set(a['sample']) or any(v.get('verdict') not in ('pass', 'fail') for v in verdicts.values()):
        bad.append('excluded_unresolved audit: verdicts do not cover exactly the drawn sample')
    else:
        if len(fails) > MAX_FAIL:
            bad.append(f'excluded_unresolved audit: {len(fails)} of {len(verdicts)} sampled rows failed (> {MAX_FAIL}): rework the class, then redraw')
        bad += [f"excluded_unresolved audit: failed row {v['name']} is still excluded (fix it, then record fixed)" for v in fails if v['name'] in now]
    return bad, counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('convert', 'draw', 'record', 'show'))
    ap.add_argument('key')
    ap.add_argument('--n', type=int, default=DEFAULT_N)
    ap.add_argument('--seed')
    ap.add_argument('--worker')
    ap.add_argument('--reviewer')
    ap.add_argument('--verdicts')
    ap.add_argument('--redraw', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    if a.cmd == 'convert':
        print(json.dumps(convert(a.key, a.dry_run)))
    elif a.cmd == 'draw':
        if not a.worker:
            ap.error('--worker is required (who wrote the exclusions)')
        d = draw(a.key, a.worker, a.n, a.seed, a.redraw)
        print(json.dumps(dict(seed=d['seed'], population=len(d['population']), sample=d['sample'], file=str(audit_path(a.key))), ensure_ascii=False))
    elif a.cmd == 'record':
        record(a.key, a.reviewer, json.loads(Path(a.verdicts).read_text()))
        print('recorded')
    else:
        bad, counts = findings(a.key, (_read(review_path(a.key), {}) or {}).get('decisions', []))
        print(json.dumps(counts), *bad[:10], sep='\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
