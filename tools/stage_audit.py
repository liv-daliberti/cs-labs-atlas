"""One seeded 50-row independent audit and ONE reviewer template for every judgement class (process v4, owner decision 2, 2026-11-17).

Generalises tools/excluded_audit.py (stage 2's excluded_unresolved class, whose file and gate it keeps) to the other classes a gate used to need a fresh hand round for:

  class        stage  population (one row per key)                                           row fails when a source proves it ...
  excluded     2      excluded_unresolved census rows (tools/excluded_audit.py)               ... admissible (CS-related ladder-equivalent faculty in the window)
  homes        3      accepted home departments (home-departments-school.json)               ... the person's home department is another unit
  websites     3      lab-website register rows with a URL or a reason (lab-websites.json)   ... the URL is not the person's page, or the reason is false
  identity     5      reviewed no_identity / no_papers holds (census-overrides)               ... an identity or papers exist (DBLP, ORCID, OpenAlex, homepage)
  students     6      admitted student rows (students.json, key 'PI | student')              ... the person is not a student of that PI in that period

  stage_audit.py draw <key> <class> --worker NAME [--n 50] [--seed S] [--redraw]
  stage_audit.py review-page <key> <class> [--out FILE]   the ONE reviewer template: the draw's rows with their recorded evidence and the verdict skeleton
  stage_audit.py record <key> <class> --reviewer NAME --verdicts FILE.json     FILE: [{"name", "verdict": "pass"|"fail", "evidence", "fixed": bool}]
  stage_audit.py show <key> [class]

Rules (the 2026-11-17 gate-2 rule, now the same everywhere): 50 rows per class per school, the seed and sample hash recorded, an independent reviewer (not the worker),
every verdict row carries reviewed_by, seed and sample_hash. A draw is invalidated only when the build hash of its inputs changes: a row added, removed or changed since the
draw (a row that is a recorded failure may change or leave: that is its fix). A repeat `draw` of an unchanged population returns the same file; the draw never moves per attempt.
Pass when at most MAX_FAIL rows fail and each failed row has been fixed (its fingerprint changed or it left the class); more failures = rework the class, then redraw. Fail closed:
a missing, unreviewed or stale audit is a gate finding (school item: it holds the release, never another PI's downloads); a failed row that is still unfixed holds that PI.
The gates read it through `items(key, stage)` for onboarding schools; a released school's audit state is reported (`status`), not enforced retroactively.

Where it is written: a store-sourced school (charter [evidence] source = "store") keeps the audit in its evidence store (table `audit_run`, created on first use, one row per class
and draw; not a reviewed-file layer, so export/check are untouched); every other school keeps hierarchy/<key>/reviewed/audit-<class>.json.
"""
import argparse
import datetime
import hashlib
import json
import random
import sqlite3
import sys
from pathlib import Path

import atlas_paths as P  # noqa: E402
import excluded_audit as EA  # noqa: E402

DEFAULT_N = EA.DEFAULT_N
MAX_FAIL = EA.MAX_FAIL
CLASSES = {'excluded': '2', 'homes': '3', 'websites': '3', 'identity': '5', 'students': '6'}
VOLATILE = ('audited', 'audited_at', 'checks', 'at', 'generated_at', 'built_at')
TIMEOUT = 30


def _read(path, default=None):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def _fp(obj):
    body = {k: v for k, v in obj.items() if k not in VOLATILE} if isinstance(obj, dict) else obj
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


# ---- populations: {row key: (fingerprint, facts shown to the reviewer)} ---------------------------------------------------------------------------
def pop_excluded(key):
    rows = EA.excluded_rows((_read(EA.review_path(key), {}) or {}).get('decisions', []))
    return {n: (EA.fingerprint(r), dict(reason=r.get('reason'), reason_code=r.get('reason_code'), sources_tried=r.get('sources_tried'))) for n, r in rows.items()}


def pop_homes(key):
    out = {}
    for r in _read(P.data('home-departments-school.json', key), []) or []:
        if r.get('status') == 'accepted' and r.get('home_department'):
            out[r['name']] = (_fp(dict(h=r['home_department'], also=r.get('also'), b=r.get('home_basis'), e=(r.get('evidence') or {}).get('sha256'))),
                              dict(home_department=r['home_department'], also=r.get('also'), basis=r.get('home_basis'), evidence=r.get('evidence'), note=r.get('note')))
    return out


def pop_websites(key):
    out = {}
    for r in (_read(P.data('lab-websites.json', key), {}) or {}).get('labs', []):
        if r.get('url') or r.get('reason_code'):
            out[r['pi']] = (_fp(dict(u=r.get('url'), c=r.get('reason_code'), s=r.get('sha256'), r=r.get('reason'), st=r.get('status'))),
                            dict(url=r.get('url'), status=r.get('status'), reason_code=r.get('reason_code'), reason=r.get('reason'), sha256=r.get('sha256'), found_via=r.get('found_via')))
    return out


def pop_identity(key):
    import census_overrides as CO
    out = {}
    for pi, o in CO.section(key).items():
        if not isinstance(o, dict):
            continue
        hold = {k: o[k] for k in ('no_identity', 'why_no_identity', 'no_papers', 'why_no_papers') if o.get(k)}
        if (o.get('no_identity') and o.get('why_no_identity')) or (o.get('no_papers') and o.get('why_no_papers')):
            out[pi] = (_fp(hold), hold)
    # PIs whose stage-5 identity rests on owned per-work evidence only (stage_gate.per_work_evidence): never a hold, so they join the population and are always drawn
    import stage_gate as SG
    lists = _read(P.data('pi-publication-lists.json', key), {}) or {}
    sec = CO.section(key)
    for x in SG.pis_of(key):
        o = sec.get(x['name']) or {}
        if SG.identity_basis(x, o, lists.get(x['name'])) == 'owned_per_work':
            r = o['source_owned_publication_review']
            facts = dict(owned_per_work_only=True, review=dict(reviewed_by=r.get('reviewed_by') or o.get('reviewer'), reviewed_on=r.get('reviewed_on') or o.get('reviewed_on'), why=r.get('why')),
                         source_items=[dict(url=e.get('url'), sha256=e.get('sha256'), quote=(e.get('quote') or '')[:200]) for e in (r.get('evidence') or []) + ((o.get('dblp_identity_review') or {}).get('evidence') or [])][:3],
                         credited_works=[dict(title=w.get('title'), year=w.get('year'), url=w.get('url'), sha256=w.get('sha256')) for w in (lists.get(x['name']) or [])][:3])
            out[x['name']] = (_fp(facts), facts)
    return out


def must_draw(cls, pop):
    """Rows that every draw of the class includes: the owned-per-work identity rows (decision 2026-11-25)."""
    return sorted(k for k, v in pop.items() if cls == 'identity' and isinstance(v, dict) and v.get('owned_per_work_only'))


def pop_students(key):
    out = {}
    for pi, rows in (_read(P.data('students.json', key), {}) or {}).items():
        for r in rows:
            rel = (r.get('relations') or [{}])[0]
            out[f"{pi} | {r.get('name')}"] = (_fp(r), dict(roles=r.get('roles'), years=rel.get('years'), type=rel.get('type'),
                                                         sources=[dict(url=s.get('url'), quote=s.get('quote')) for s in (rel.get('sources') or [])[:2]]))
    return out


POPULATIONS = dict(excluded=pop_excluded, homes=pop_homes, websites=pop_websites, identity=pop_identity, students=pop_students)


def pi_of(cls, rowkey):
    return rowkey.split(' | ')[0] if cls == 'students' else rowkey.split(' [')[0]


def population(key, cls):
    return POPULATIONS[cls](key)


def pick(keys, n, seed, key, cls):
    return sorted(random.Random(f'{key}:{cls}:{seed}').sample(sorted(keys), min(n, len(keys))))


def drawn_sample(key, cls, pop, n, seed):
    """The seeded draw of `pop` ({row: fingerprint}), with the class's must-draw rows (current population facts) always included."""
    must = must_draw(cls, {k: v[1] for k, v in population(key, cls).items()})
    if not must:
        return pick(pop, n, seed, key, cls)
    return sorted(set(must) | set(pick([k for k in pop if k not in must], max(0, n - len(must)), seed, key, cls)))


def sample_hash(sample, pop):
    return hashlib.sha256(json.dumps([[k, pop[k]] for k in sample], sort_keys=True).encode()).hexdigest()[:16]


# ---- storage -------------------------------------------------------------------------------------------------------------------------------------
def _store_sourced(key):
    import evidence_store as E
    return E.source_of(key) == 'store'


def _store_con(key):
    import evidence_store as E
    sp = E.store_path(key)
    if not sp.exists():
        raise SystemExit(f'{key}: no evidence store at {sp}')
    con = E.connect(sp)
    con.execute('CREATE TABLE IF NOT EXISTS audit_run (id INTEGER PRIMARY KEY, class TEXT NOT NULL, written_at TEXT NOT NULL, doc TEXT NOT NULL)')
    return con


def json_path(key, cls):
    return Path(P.data(f'audit-{cls}.json', key))


def load(key, cls):
    if cls == 'excluded':
        return _read(EA.audit_path(key))
    if _store_sourced(key):
        con = _store_con(key)
        try:
            row = con.execute('SELECT doc FROM audit_run WHERE class=? ORDER BY id DESC LIMIT 1', (cls,)).fetchone()
        except sqlite3.Error:
            return None
        finally:
            con.close()
        return json.loads(row[0]) if row else None
    return _read(json_path(key, cls))


def save(key, cls, doc):
    if cls == 'excluded':
        EA.audit_path(key).parent.mkdir(parents=True, exist_ok=True)
        EA.audit_path(key).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    elif _store_sourced(key):
        con = _store_con(key)
        with con:
            con.execute('INSERT INTO audit_run (class, written_at, doc) VALUES (?,?,?)', (cls, _now(), json.dumps(doc, ensure_ascii=False)))
        con.close()
    else:
        json_path(key, cls).parent.mkdir(parents=True, exist_ok=True)
        json_path(key, cls).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')


# ---- draw / review page / record -----------------------------------------------------------------------------------------------------------------
def draw(key, cls, worker, n=DEFAULT_N, seed=None, redraw=False):
    if cls == 'excluded':
        return EA.draw(key, worker, n, seed, redraw)
    pop = {k: v[0] for k, v in population(key, cls).items()}
    old = load(key, cls)
    seed = seed if seed is not None else (old or {}).get('seed') or hashlib.sha256(json.dumps(pop, sort_keys=True).encode()).hexdigest()[:12]
    if old and not redraw and old.get('population') == pop and old.get('seed') == seed and old.get('n') == n:
        return old
    sample = drawn_sample(key, cls, pop, n, seed)
    doc = dict(school=key, cls=cls, stage=CLASSES[cls], drawn_at=_now(), seed=seed, n=n, worker=worker, population=pop, sample=sample,
               sample_hash=sample_hash(sample, pop), reviewer=None, verdicts=[])
    save(key, cls, doc)
    return doc


def review_page(key, cls):
    """The ONE reviewer template: markdown with the draw's rows, the evidence the build recorded for each, the rule and the verdict skeleton."""
    doc = load(key, cls)
    if not doc:
        raise SystemExit(f'no draw: stage_audit.py draw {key} {cls} --worker NAME')
    facts = population(key, cls)
    L = [f'# Independent audit: {key} / {cls} (stage {CLASSES[cls]})', '',
         f"seed `{doc['seed']}`, sample hash `{doc.get('sample_hash') or sample_hash(doc['sample'], doc['population'])}`, {len(doc['sample'])} of {len(doc['population'])} rows, drawn by `{doc['worker']}` (you must be someone else).", '',
         'A row FAILS only if a source you read proves it wrong (' + {'excluded': 'the person is admissible', 'homes': 'the home department is another unit',
                                                                     'websites': 'the URL is not the person\'s page or the reason is false', 'identity': 'an identity/papers exist',
                                                                     'students': 'the person is not that PI\'s student in that period'}[cls] + '). Not finding proof is a pass of the recorded evidence, not of the claim: say what you read.', '']
    for k in doc['sample']:
        L += [f'## {k}', '```json', json.dumps((facts.get(k) or (None, 'row no longer in the class'))[1], indent=1, ensure_ascii=False)[:1500], '```', '']
    L += ['## Verdict file', '', '```json', json.dumps([dict(name=doc['sample'][0] if doc['sample'] else 'ROW', verdict='pass|fail', evidence='URL + quote of what you read', fixed=False)], indent=1), '```',
          f'`record` adds reviewed_by, seed and sample_hash to every row. More than {MAX_FAIL} fails: the class is reworked, then redrawn.']
    return '\n'.join(L) + '\n'


def record(key, cls, reviewer, verdicts):
    doc = load(key, cls)
    if not doc:
        raise SystemExit('no audit drawn')
    if reviewer.strip() == (doc.get('worker') or '').strip():
        raise SystemExit('the reviewer must not be the worker who drew and wrote the rows')
    sh = doc.get('sample_hash') or sample_hash(doc['sample'], doc['population'])
    doc.update(reviewer=reviewer, reviewed_at=_now(), sample_hash=sh,
               verdicts=[dict(v, reviewed_by=reviewer, seed=doc['seed'], sample_hash=sh) for v in verdicts])
    save(key, cls, doc)
    return doc


# ---- gate findings ------------------------------------------------------------------------------------------------------------------------------------
def findings(key, cls):
    """(items, counts) for one class; items name the PI first ('PI: ...') when a row is at fault, else are school items. Empty population: nothing to audit."""
    if cls == 'excluded':
        dec = (_read(EA.review_path(key), {}) or {}).get('decisions', [])
        return EA.findings(key, dec)
    pop_now = {k: v[0] for k, v in population(key, cls).items()}
    if not pop_now:
        return [], {f'audit_{cls}_rows': 0}
    a = load(key, cls)
    tag = f'{cls} audit'
    if not a:
        return [f'{tag} missing: {len(pop_now)} rows (stage_audit.py draw {key} {cls}, review the page with a fresh independent reviewer, record)'], {f'audit_{cls}_rows': len(pop_now)}
    pop = a.get('population') or {}
    verdicts = {v.get('name'): v for v in a.get('verdicts') or []}
    fails = {k: v for k, v in verdicts.items() if v.get('verdict') == 'fail'}
    new = sorted(k for k in pop_now if pop.get(k) != pop_now[k] and k not in fails)
    gone = sorted(k for k in pop if k not in pop_now and k not in fails)
    counts = {f'audit_{cls}_rows': len(pop_now), f'audit_{cls}_sample': len(a.get('sample') or []), f'audit_{cls}_failed': len(fails), f'audit_{cls}_seed': a.get('seed')}
    bad = []
    if new or gone:
        return [f'{tag} stale: {len(new)} rows added/changed and {len(gone)} removed since the draw ({(new + gone)[0]}...); redraw and re-review'], counts
    if (sorted(a.get('sample') or []) != drawn_sample(key, cls, pop, a.get('n') or DEFAULT_N, a.get('seed'))
            or len(a['sample']) != min(a.get('n') or DEFAULT_N, len(pop))):
        bad.append(f'{tag}: sample is not the seeded draw of the population (redraw)')
    if not a.get('reviewer') or a.get('reviewer') == a.get('worker'):
        bad.append(f'{tag}: no independent reviewer recorded')
    elif set(verdicts) != set(a['sample']) or any(v.get('verdict') not in ('pass', 'fail') for v in verdicts.values()):
        bad.append(f'{tag}: verdicts do not cover exactly the drawn sample')
    else:
        if any(v.get('reviewed_by') != a['reviewer'] or v.get('seed') != a['seed'] for v in verdicts.values()):
            bad.append(f'{tag}: verdict rows lack reviewed_by/seed (record them with stage_audit.py record)')
        if len(fails) > MAX_FAIL:
            bad.append(f'{tag}: {len(fails)} of {len(verdicts)} sampled rows failed (> {MAX_FAIL}): rework the class, then redraw')
        for k in fails:   # still unfixed = present and unchanged since the draw
            if pop_now.get(k) == pop.get(k):
                bad.append(f'{pi_of(cls, k)}: {tag} failed row {k} is not fixed yet (fix it, then record fixed)')
    return bad, counts


def items(key, stage):
    """Gate findings of the classes of `stage` for an onboarding school; [] for a released one (reported by `status`, not enforced retroactively)."""
    import school_config as S
    try:
        if S.get(key).get('status') == 'released':
            return [], {}
    except KeyError:   # no charter (a fixture): nothing to enforce
        return [], {}
    bad, counts = [], {}
    for cls in [c for c, st in CLASSES.items() if st == str(stage) and c != 'excluded']:   # stage 2's class is read by g2 itself
        b, c = findings(key, cls)
        bad += b
        counts.update(c)
    return bad, counts


def status(key):
    return {cls: dict(zip(('items', 'counts'), findings(key, cls))) for cls in CLASSES}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('draw', 'review-page', 'record', 'show'))
    ap.add_argument('key')
    ap.add_argument('cls', nargs='?', choices=sorted(CLASSES))
    ap.add_argument('--n', type=int, default=DEFAULT_N)
    ap.add_argument('--seed')
    ap.add_argument('--worker')
    ap.add_argument('--reviewer')
    ap.add_argument('--verdicts')
    ap.add_argument('--out')
    ap.add_argument('--redraw', action='store_true')
    a = ap.parse_args(argv)
    if a.cmd != 'show' and not a.cls:
        ap.error('a class is required: ' + ', '.join(sorted(CLASSES)))
    if a.cmd == 'draw':
        if not a.worker:
            ap.error('--worker is required (who wrote the rows)')
        d = draw(a.key, a.cls, a.worker, a.n, a.seed, a.redraw)
        print(json.dumps(dict(seed=d['seed'], population=len(d['population']), sample=len(d['sample']), sample_hash=d.get('sample_hash')), ensure_ascii=False))
    elif a.cmd == 'review-page':
        text = review_page(a.key, a.cls)
        Path(a.out).write_text(text) if a.out else print(text)
    elif a.cmd == 'record':
        record(a.key, a.cls, a.reviewer, json.loads(Path(a.verdicts).read_text()))
        print('recorded')
    else:
        for cls in ([a.cls] if a.cls else sorted(CLASSES)):
            b, c = findings(a.key, cls)
            print(cls, 'stage', CLASSES[cls], json.dumps(c), *b[:4], sep='\n  ')
    return 0


if __name__ == '__main__':
    sys.exit(main())
