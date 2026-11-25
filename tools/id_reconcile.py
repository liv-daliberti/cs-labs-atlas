"""Reviewed id reconciliation before an ID-preserving school promotion (2026-11-25; docs/IDS.md "Reviewed id reconciliation").

A native rebuild of a school carries no atlas ids; `atlas_ids.py` then finds each entity through its anchors. When the
rebuilt record carries different anchors from the ones its id was issued with, the registry would mint a second id or
pick the earlier-issued one of two. This tool applies, in an ISOLATED registry copy and package tree only, the exact
reviewed decisions that keep every issued id (`hierarchy/<school>/reviewed/id-reconciliation.json`, version 1):

  pi_redirects     two issued person ids (and lab ids) that one source-proven duplicate PI split between them: the survivor
                   keeps the id, the alias becomes a redirect and its anchors move (D-0001 repair, docs/IDS.md)
  anchor_bindings  a current anchor of a record is registered to the id the record was issued with, when the record still
                   carries the name+url fallback anchor that id was minted from (the PI gained an identifier since)
  student_rekeys   a student record keyed by a faculty collection id is re-keyed to its issued ext: key before the ID stage
                   (R-STU-07 for a merged alias the rebuilt PI no longer lists)

Every entry names the exact registry before-state (rows and anchors); a changed preimage refuses. Nothing here accepts a
name-only join: a binding needs the issued id's own name+url anchor to match the record's name and a url the record cites.

  id_reconcile.py apply  --registry COPY --dir HIER --review JSON [--today D]   (refuses the live registry)
  id_reconcile.py verify --before PKGDIR --dir HIER --registry-before DB --registry-after DB --review JSON
  id_reconcile.py finish --dir HIER --live-report IDS-REPORT.json --review JSON
  id_reconcile.py plan   --pair SRC=DST ... --out PLAN      /     swap --plan PLAN [--apply]
"""
import argparse, gzip, hashlib, json, os, shutil, sqlite3, sys
from datetime import datetime, timezone
from pathlib import Path

import atlas_paths as P  # noqa: E402
import atlas_ids as A  # noqa: E402


class ReconcileRefused(ValueError):
    pass


def refuse(msg):
    raise ReconcileRefused(msg)


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def member_sha(rec):
    return hashlib.sha256(json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def load_review(path):
    r = json.loads(Path(path).read_text())
    if r.get('version') != 1 or not r.get('school') or not r.get('reviewed_by') or not r.get('reviewed_on'):
        refuse('review needs version 1, school, reviewed_by and reviewed_on')
    for k in ('pi_redirects', 'anchor_bindings', 'student_rekeys'):
        r.setdefault(k, [])
    return r


def row(db, table, key):
    col = 'id' if table == 'ids' else 'anchor'
    return db.execute(f'select * from {table} where {col}=?', (key,)).fetchone()


def anchors_of(db, i):
    return sorted(a for (a,) in db.execute('select anchor from anchors where id=?', (i,)))


def need_state(db, i, row_, anchors, what):
    """The exact before-state of an issued id: its registry row and every anchor it owns."""
    got = row(db, 'ids', i)
    if got is None or list(got) != list(row_):
        refuse(f'{what}: registry row of {i} changed: {got}')
    if anchors_of(db, i) != sorted(anchors):
        refuse(f'{what}: anchors of {i} changed: {anchors_of(db, i)}')


def pi_anchor_strings(school, p):
    """The strong and collection anchors the ID stage derives for a PI record (atlas_ids._run)."""
    a = {('orcid', o) for o in map(A.norm_orcid, (p.get('orcid') or []) + (p.get('orcidFromDblp') or [])) if o}
    mixed = {A.norm_oa(x) for x in p.get('mixedOpenAlex') or []}
    a |= {('openalex', x) for x in map(A.norm_oa, p.get('reviewedOpenAlex') or []) if x and x not in mixed}
    a |= {('dblp', d) for d in map(A.norm_dblp_pid, p.get('dblp') or []) if d}
    a |= {('coll', f'{school}:{i}') for i in p.get('personIds') or [] if i and not str(i).startswith('ext:')}
    return {A.person_anchor_str(k, v) for k, v in a}


def pi_urls(p):
    u = {l.get('url') for l in p.get('listings') or []} | {e.get('url') for q in p.get('periods') or [] for e in q.get('evidence') or []}
    u |= {(p.get('piBasis') or {}).get('url')}
    return {x for x in u if x}


def read_school(hdir, school):
    D = P.SchoolDir(school, hdir)
    return json.loads((D / 'pis.json').read_text()), json.loads((D / 'students.json').read_text()), D


def live_registry(path):
    live = Path(P.data('ids') / 'registry.sqlite')
    return live.exists() and Path(path).resolve() == live.resolve()


# ------------------------------------------------------------------ apply

def check_pi_redirect(db, e, school, pis, merges):
    s, a = e['survivor'], e['alias']
    if s['id'] == a['id'] or s['lab'] == a['lab']:
        refuse('survivor and alias must differ')
    for who in (s, a):
        for key, kind in (('id', 'person'), ('lab', 'lab')):
            r = row(db, 'ids', who[key])
            if r is None or r[1] != kind or r[4] != 'active':
                refuse(f"{e['canonical']}: {who[key]} is not an active {kind} id")
    need_state(db, s['id'], e['registry_before']['survivor']['row'], e['registry_before']['survivor']['anchors'], e['canonical'])
    need_state(db, a['id'], e['registry_before']['alias']['row'], e['registry_before']['alias']['anchors'], e['canonical'])
    for key, who in (('survivor_lab', s), ('alias_lab', a)):
        need_state(db, who['lab'], e['registry_before'][key]['row'], e['registry_before'][key]['anchors'], e['canonical'])
    for who in (s, a):
        la = f"l|lab:{school}:{who['id']}"
        if (row(db, 'anchors', la) or [None, None])[1] != who['lab']:
            refuse(f"{e['canonical']}: lab anchor {la} no longer maps to {who['lab']}")
    pi = next((p for p in pis if p['pi'] == e['canonical']), None)
    if pi is None:
        refuse(f"{e['canonical']}: PI not in the package")
    # the reviewed source-proven duplicate (census-name-aliases native_pi_merges) names this canonical and alias
    if not any(m.get('canonical') == e['canonical'] and e['alias_name'] in (m.get('aliases') or []) and m.get('evidence') for m in merges):
        refuse(f"{e['canonical']}: no reviewed native_pi_merges entry with evidence for {e['alias_name']}")
    if e['alias_name'] not in (pi.get('mergedCensusRows') or []):
        refuse(f"{e['canonical']}: package PI does not list {e['alias_name']} as a merged census row")
    hits = {A.resolve(db, r[1]) for x in pi_anchor_strings(school, pi) if (r := row(db, 'anchors', x))}
    if not hits or not hits <= {s['id'], a['id']}:
        refuse(f"{e['canonical']}: the PI's anchors reach {sorted(hits)}, not only the reviewed ids")


def do_pi_redirect(db, e):
    s, a = e['survivor'], e['alias']
    for old, new in ((a['id'], s['id']), (a['lab'], s['lab'])):
        db.execute("update ids set status='redirect', redirect_to=? where id=? and status='active'", (new, old))
        db.execute('update anchors set id=? where id=?', (new, old))
    assert A.resolve(db, a['id']) == s['id'] and A.resolve(db, a['lab']) == s['lab']


def check_binding(db, e, school, pis):
    i = e['id']
    need_state(db, i, e['registry_before']['row'], e['registry_before']['anchors'], e['subject']['pi'])
    r = row(db, 'ids', i)
    if r[1] != 'person' or r[4] != 'active':
        refuse(f'{i} is not an active person id')
    if row(db, 'anchors', e['anchor']) is not None:
        refuse(f"{e['anchor']} is already registered")
    pi = next((p for p in pis if p['pi'] == e['subject']['pi']), None)
    if pi is None:
        refuse(f"binding subject {e['subject']['pi']} is not in the package")
    if e['anchor'] not in pi_anchor_strings(school, pi):
        refuse(f"the package PI does not carry {e['anchor']}")
    name_anchors = [x for x in anchors_of(db, i) if x.startswith('p|name:')]
    if len(name_anchors) != 1 or r[2] != name_anchors[0]:
        refuse(f'{i} was not minted from its own single name+url anchor')
    prefix = f"p|name:{school}:{A.nname(pi['pi'])}:"
    if not name_anchors[0].startswith(prefix) or name_anchors[0][len(prefix):] not in pi_urls(pi):
        refuse(f"the issued name+url anchor of {i} is not the record's name and a url it cites (a name alone never binds)")
    if A.resolve(db, i) != i:
        refuse(f'{i} is a redirect')


def check_rekey(db, e, school, students):
    group = students.get(e['pi']) or []
    rec = next((r for r in group if r.get('person') == e['from_person']), None)
    if rec is None:
        return None
    if member_sha(rec) != e['expected_member_sha256']:
        refuse(f"student {e['from_person']} under {e['pi']} changed; review required")
    if any(r.get('person') == e['to_person'] for r in group):
        refuse(f"{e['to_person']} already exists under {e['pi']}")
    urls = A.student_urls(rec)
    anchor = f"p|name:{school}:{A.nname(rec['name'])}:{urls[0]}" if len(urls) == 1 else None
    if anchor is None or (row(db, 'anchors', anchor) or [None, None])[1] != e['issued_id']:
        refuse(f"student {e['to_person']}: issued name+url anchor does not map to {e['issued_id']}")
    if not e['to_person'].startswith('ext:'):
        refuse('a re-key goes to an ext: key')
    return rec


def apply(db, review, hdir, today=None):
    school = review['school']
    pis, students, D = read_school(hdir, school)
    merges = json.loads((D / 'census-name-aliases.json').read_text()).get('native_pi_merges') if (D / 'census-name-aliases.json').exists() else []
    today = today or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    for e in review['pi_redirects']:
        check_pi_redirect(db, e, school, pis, merges or [])
    for e in review['anchor_bindings']:
        check_binding(db, e, school, pis)
    rekeys = [(e, check_rekey(db, e, school, students)) for e in review['student_rekeys']]
    for e in review['pi_redirects']:
        do_pi_redirect(db, e)
    for e in review['anchor_bindings']:
        db.execute('insert into anchors (anchor, id, kind, first_seen) values (?,?,?,?)', (e['anchor'], e['id'], 'person', today))
    done = []
    for e, rec in rekeys:
        if rec is None:
            continue
        rec['person'] = e['to_person']; rec.setdefault('rekeyedFrom', []).append(e['from_person'])
        done.append(e['to_person'])
    if done:
        tmp = D.tmp('students.json', '.reconcile-tmp'); tmp.write_text(json.dumps(students, indent=1, ensure_ascii=False)); tmp.replace(D / 'students.json')
    db.commit()
    return dict(pi_redirects=[(e['alias']['id'], e['survivor']['id']) for e in review['pi_redirects']],
                lab_redirects=[(e['alias']['lab'], e['survivor']['lab']) for e in review['pi_redirects']],
                anchor_bindings=[(e['anchor'], e['id']) for e in review['anchor_bindings']], student_rekeys=done)


# ------------------------------------------------------------------ verify

def jl(p):
    with gzip.open(p, 'rt') as f:
        return [json.loads(x) for x in f]


def package_ids(root, school=None):
    root = Path(root)
    pis = json.loads((root / 'pis.json').read_text()); st = json.loads((root / 'students.json').read_text())
    lp = jl(root / 'lab_papers.jsonl.gz')
    return pis, st, lp


def verify(before, hdir, reg_before, reg_after, review):
    """Every issued id of the current package survives; nothing is orphaned; the registry only gains rows (and the
    reviewed redirects). Returns a dict with `pass`."""
    school = review['school']
    bpis, bst, blp = package_ids(before)
    npis, nst, nlp = package_ids(P.SchoolDir(school, hdir))
    db0 = sqlite3.connect(f'file:{reg_before}?mode=ro', uri=True); db1 = sqlite3.connect(f'file:{reg_after}?mode=ro', uri=True)
    out, bad = {}, []
    bp = {p['pi']: p for p in bpis}; np_ = {p['pi']: p for p in npis}
    out['pis'] = dict(before=len(bp), after=len(np_))
    if set(bp) != set(np_):
        bad.append(('pi set changed', sorted(set(bp) ^ set(np_))))
    out['pi_ids_equal'] = sum(1 for n in bp if n in np_ and bp[n]['atlasId'] == np_[n]['atlasId'])
    out['lab_ids_equal'] = sum(1 for n in bp if n in np_ and bp[n]['labId'] == np_[n]['labId'])
    bad += [('pi id differs', n, bp[n]['atlasId'], np_[n]['atlasId']) for n in bp if n in np_ and bp[n]['atlasId'] != np_[n]['atlasId']]
    bad += [('lab id differs', n, bp[n]['labId'], np_[n]['labId']) for n in bp if n in np_ and bp[n]['labId'] != np_[n]['labId']]
    sk = lambda st: sorted((pi, r['atlasId']) for pi, rs in st.items() for r in rs)  # noqa: E731
    b, n_ = sk(bst), sk(nst)
    out['students'] = dict(before=len(b), after=len(n_), missing=len(set(b) - set(n_)), added=len(set(n_) - set(b)))
    bad += [('student id missing', x) for x in sorted(set(b) - set(n_))]
    wk = lambda rows: {(r['pi'], r.get('oa') or r.get('doi') or r.get('title')): r['atlasWorkId'] for r in rows}  # noqa: E731
    bw, nw = wk(blp), wk(nlp)
    dropped = sorted(set(bw) - set(nw))
    out['works'] = dict(rows_before=len(blp), rows_after=len(nlp), new_rows=len(set(nw) - set(bw)), dropped_rows=len(dropped),
                        id_changed=sum(1 for k in bw if k in nw and bw[k] != nw[k]))
    bad += [('work id differs', k) for k in bw if k in nw and bw[k] != nw[k]]
    used = {p['atlasId'] for p in npis} | {p['labId'] for p in npis} | {r['atlasId'] for rs in nst.values() for r in rs} | set(nw.values())
    gone = ({p['atlasId'] for p in bpis} | {p['labId'] for p in bpis} | {r['atlasId'] for rs in bst.values() for r in rs}) - used
    gone_w = {bw[k] for k in dropped} - used
    resolve = lambda i: A.resolve(db1, i)  # noqa: E731
    out['issued_ids_not_in_new_package'] = sorted(gone)
    bad += [('issued id vanished without a redirect', i) for i in sorted(gone) if resolve(i) == i]
    out['dropped_work_ids_unused'] = sorted(gone_w)   # science drops: the id stays issued and active, never reissued
    # registry: only additions, plus the reviewed redirects and anchor moves
    allowed_alias = {e['alias']['id'] for e in review['pi_redirects']} | {e['alias']['lab'] for e in review['pi_redirects']}
    ids0 = {r[0]: r for r in db0.execute('select * from ids')}; ids1 = {r[0]: r for r in db1.execute('select * from ids')}
    removed = [i for i in ids0 if i not in ids1]
    changed = [i for i in ids0 if i in ids1 and ids0[i] != ids1[i]]
    out['registry_ids'] = dict(before=len(ids0), after=len(ids1), removed=len(removed), changed=sorted(changed), added=len(ids1) - len(ids0))
    bad += [('registry id removed', i) for i in removed] + [('registry id changed outside the review', i) for i in changed if i not in allowed_alias]
    bad += [('redirect changed shape', i) for i in changed if i in allowed_alias and (ids1[i][:4] != ids0[i][:4] or ids1[i][4] != 'redirect')]
    a0 = {r[0]: r for r in db0.execute('select * from anchors')}; a1 = {r[0]: r for r in db1.execute('select * from anchors')}
    moved = [k for k in a0 if k in a1 and a0[k][1] != a1[k][1]]
    out['registry_anchors'] = dict(before=len(a0), after=len(a1), removed=len([k for k in a0 if k not in a1]), moved=len(moved), added=len(a1) - len(a0))
    bad += [('anchor removed', k) for k in a0 if k not in a1] + [('anchor moved outside the review', k) for k in moved if a0[k][1] not in allowed_alias]
    new_nonwork = sorted((r[0], r[1], r[2]) for i, r in ids1.items() if i not in ids0 and r[1] != 'work')
    out['new_non_work_ids'] = new_nonwork
    bad += [('person or lab id minted for an existing entity', x) for x in new_nonwork]
    rep = json.loads((P.hfile(hdir, 'ids') / 'IDS-REPORT.json').read_text())
    out['ids_report'] = dict(stats=rep['stats'], conflicts_refused=rep['conflicts_refused'], coadvising_holds_skipped=len(rep['coadvising_holds_skipped']))
    bad += [('conflicts refused', rep['conflicts_refused'])] if rep['conflicts_refused'] else []
    for e in review['student_rekeys']:
        if not any(r['atlasId'] == e['issued_id'] for rs in nst.values() for r in rs):
            bad.append(('rekeyed student lost its issued id', e['issued_id']))
    out['violations'] = bad; out['pass'] = not bad
    return out


# ------------------------------------------------------------------ report, plan, swap

def finish_report(hdir, live_report, applied, review):
    """The school run writes a partial IDS-REPORT; keep every key the live report has that the run does not produce."""
    path = P.hfile(hdir, 'ids') / 'IDS-REPORT.json'
    rep = json.loads(path.read_text()); live = json.loads(Path(live_report).read_text())
    for k, v in live.items():
        rep.setdefault(k, v)
    rep.setdefault('reviewedIdReconciliations', []).append(dict(
        at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), school=review['school'], reviewed_by=review['reviewed_by'],
        reviewed_on=review['reviewed_on'], review_sha256=review.get('_sha256'), **applied))
    path.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + '\n')
    return rep


def plan(pairs, out):
    items = []
    for src, dst in pairs:
        items.append(dict(source=str(Path(src).resolve()), target=str(Path(dst)), prepared_sha256=sha_file(src),
                          preimage_sha256=sha_file(dst) if Path(dst).exists() else None))
    Path(out).write_text(json.dumps(items, indent=1) + '\n')
    return items


def swap(plan_path, apply_=False):
    """Compare-and-swap: every target must still hold its preimage and every source its prepared hash; targets are staged
    next to themselves and renamed in plan order (list the registry and ids exports first, then the packages: the registry only gains rows, so readers never see an unknown id). Dry run unless apply_."""
    items = json.loads(Path(plan_path).read_text())
    for it in items:
        dst = Path(it['target'])
        if (sha_file(dst) if dst.exists() else None) != it['preimage_sha256']:
            refuse(f'target changed since the plan: {dst}')
        if sha_file(it['source']) != it['prepared_sha256']:
            refuse(f"source changed since the plan: {it['source']}")
    if not apply_:
        return dict(dry_run=True, files=len(items))
    staged = []
    try:
        for it in items:
            dst = Path(it['target']); tmp = dst.with_name(f'.{dst.name}.{os.getpid()}.new')
            shutil.copy2(it['source'], tmp); tmp.chmod(0o644)
            if sha_file(tmp) != it['prepared_sha256']:
                refuse(f'staged copy differs: {tmp}')
            staged.append((tmp, dst))
    except BaseException:
        for tmp, _ in staged:
            tmp.unlink(missing_ok=True)
        raise
    for tmp, dst in staged:
        os.replace(tmp, dst)
    return dict(dry_run=False, files=len(items))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('apply'); a.add_argument('--registry', required=True); a.add_argument('--dir', required=True); a.add_argument('--review', required=True); a.add_argument('--today'); a.add_argument('--out')
    v = sub.add_parser('verify'); v.add_argument('--before', required=True); v.add_argument('--dir', required=True)
    v.add_argument('--registry-before', required=True); v.add_argument('--registry-after', required=True); v.add_argument('--review', required=True)
    f = sub.add_parser('finish'); f.add_argument('--dir', required=True); f.add_argument('--live-report', required=True); f.add_argument('--review', required=True); f.add_argument('--applied', required=True)
    pl = sub.add_parser('plan'); pl.add_argument('--pair', action='append', required=True, help='SRC=DST'); pl.add_argument('--out', required=True)
    sw = sub.add_parser('swap'); sw.add_argument('--plan', required=True); sw.add_argument('--apply', action='store_true')
    x = ap.parse_args(argv)
    try:
        if x.cmd == 'apply':
            if live_registry(x.registry):
                refuse('refusing the live registry: apply to an isolated copy')
            review = load_review(x.review)
            db = A.open_registry(x.registry, seed=False)
            res = apply(db, review, x.dir, x.today); db.close()
            if x.out:
                Path(x.out).write_text(json.dumps(res, indent=1) + '\n')
        elif x.cmd == 'verify':
            res = verify(x.before, x.dir, x.registry_before, x.registry_after, load_review(x.review))
        elif x.cmd == 'finish':
            review = load_review(x.review); review['_sha256'] = sha_file(x.review)
            finish_report(x.dir, x.live_report, json.loads(Path(x.applied).read_text()), review); res = dict(ok=True)
        elif x.cmd == 'plan':
            res = plan([tuple(p.split('=', 1)) for p in x.pair], x.out)
        else:
            res = swap(x.plan, x.apply)
    except ReconcileRefused as e:
        print(f'REFUSED: {e}', file=sys.stderr)
        return 2
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    return 0 if not isinstance(res, dict) or res.get('pass', True) else 1


if __name__ == '__main__':
    sys.exit(main())
