"""Per-PI release (owner decision D-0001, 2026-11-17): publish the PIs that are done, hold the open ones.

A release carries, per school, the PIs that are `done` or `excluded_with_reason` in tools/pi_states.py (an open PI is HELD; a PI
whose only gaps are ratchet-tolerated coverage gaps is not held, pi_states._hard_open) with their labs, papers and students, plus every PI an earlier
release already published (CARRIED: published rows are never removed; if such a PI is open now it stays in and is listed in the notes).

  plan(key)                    -> included / carried / held (with the blocking reasons) / school items, and `included_sha`
  filtered_bytes(key, f, inc)  -> the package file `f` restricted to the included PIs (deterministic bytes)
  package_hashes(key, inc)     -> sha256 of the filtered content of the five accuracy files (binds the stage-9 sample to the subset)
  scope_statement(plan)        -> the per-school field the site reads (release-scope.json: status complete|partial, counts, held list)
  compare(new, old)            -> monotone check: ids (PI, lab, student, paper) present in the last published package and missing now
  python3 tools/pi_release.py <school> [--published <release dir>]    dry run, nothing is written

Nothing here publishes or uploads. docs/PER-PI-ADMISSION.md, section "Per-PI release".
"""
import argparse, collections, gzip, hashlib, io, json, sys
from pathlib import Path

import atlas_paths as P  # noqa: E402

PACKAGE = ['pis.json', 'students.json', 'lab_papers.jsonl.gz', 'student_papers.jsonl.gz', 'copies.json']
# school-wide files of a release that name every PI of the school: tools/pi_release_derived.py restricts them for a partial school (Q-0340); listed in the scope only when --allow-derived-unfiltered ships them as they are
DERIVED_UNFILTERED = ['report.json', 'unavailable.jsonl.gz', 'unavailable-summary.json', 'link-diagnosis.json', 'reader/', 'home-departments.json',
                      'zero-paper-labs.json', 'school-profiles.json', 'missing-papers-audit.json', 'chain-audit.json', 'student-audit.json']


def _jsonl_gz(path):
    with gzip.open(path, 'rt') as f:
        return [json.loads(l) for l in f if l.strip()]


def _read_json(path):
    return json.loads(Path(path).read_text())


def package_dir(key, base=None):
    """The directory holding a school's package files: the working build, or `base`/<school> of a flat release (hierarchy/<school>/)."""
    return P.SchoolDir(key) if base is None else Path(base) / 'hierarchy' / key


def published_pis(key, release):
    """PI names of the school's package in a published release dir (None when the release has no such school)."""
    p = package_dir(key, release) / 'pis.json'
    return [x['pi'] for x in _read_json(p)] if p.exists() else None


def _published_pi_ids(key, release):
    p = package_dir(key, release) / 'pis.json'
    return {x['atlasId'] for x in _read_json(p) if x.get('atlasId')} if p.exists() else set()


def plan(key, res=None, published=None):
    """Who goes into a release of `key`. `res` is pi_states.compute(key) (computed when absent); `published` is the last release dir
    (default: releases/latest). included = package PIs not hard-open, plus carried (published, open now)."""
    import pi_states as PS
    res = res or PS.compute(key)
    pkg_rows = _read_json(package_dir(key) / 'pis.json')
    pkg = [x['pi'] for x in pkg_rows]
    hard_open = set(res['open_pis'])
    held_all = {pi: [f"stage {s}: {res['pis'][pi][s]['reasons'][0]}" for s in PS.ALL if res['pis'][pi][s]['state'] == 'open'] for pi in sorted(hard_open) if pi in res['pis']}
    done = [pi for pi in pkg if pi not in hard_open]
    if published is None:
        latest = Path(P.RELEASES) / 'latest'
        published = latest if latest.exists() else None
    prev = (published_pis(key, published) or []) if published else []
    rec = load_corrections(key, published) if published else None
    prev = prev + list((rec or {}).get('pi_renames', {}).values())   # a PI the census renamed (record `pi_renames`: old spelling -> current) is the published PI, carried
    prev_ids = _published_pi_ids(key, published) if published else set()   # a renamed PI (census alias) keeps its atlas id and stays carried (2026-11-18, Sahinidis)
    carried = [x['pi'] for x in pkg_rows if x['pi'] in hard_open and (x['pi'] in set(prev) or (x.get('atlasId') and x['atlasId'] in prev_ids))]
    included = [pi for pi in pkg if pi in set(done) or pi in set(carried)]
    held = {pi: r for pi, r in held_all.items() if pi in set(pkg) and pi not in set(carried)}
    for pi in pkg:                       # an open PI the state table does not know (should not happen) is held, never silently included
        if pi not in res['pis'] and pi not in set(included):
            held[pi] = ['no pi-states row']
    sha = hashlib.sha256('\n'.join(sorted(included)).encode()).hexdigest()
    hl = _held_links(key, res, included, published, rec)
    return dict(school=key, package_pis=len(pkg), done=len(done), carried=carried, included=included, held=held, included_sha=sha, held_links=hl,
                school_items={s: v for s, v in (res.get('school_items') or {}).items() if v},
                partial=bool(held), published_from=Path(published).resolve().name if published else None)


def _published_students(key, published, rec):
    """{PI name in the CURRENT package: {student ids}} of the students the published release already carried (a renamed PI is read under its new name)."""
    if not published or not (package_dir(key, published) / 'students.json').exists():
        return {}
    ren = (rec or {}).get('pi_renames') or {}
    return {ren.get(pi, pi): {x.get('person') or x.get('id') or x.get('name') for x in v} for pi, v in _read_json(package_dir(key, published) / 'students.json').items()}


def _held_links(key, res, included, published, rec):
    """D-0017: the stage-7 chain-audit `links` flags of the included PIs, minus the links the published release already carried (D-0001: published rows are
    never removed). {pi: [{student, id, diagnosis, detail}]}."""
    out = {}
    pub = _published_students(key, published, rec)
    for pi in included:
        rows = [h for h in (res.get('held_links') or {}).get(pi, []) if (h.get('id') or h.get('student')) not in pub.get(pi, set())]
        if rows:
            out[pi] = rows
    return out


def held_set(pl_or_links):
    """{(pi, student id)} of a plan's (or a `held_links` map's) held links, in the key the package files use (student person id, else name)."""
    links = (pl_or_links.get('held_links') or {}) if isinstance(pl_or_links, dict) and 'included' in pl_or_links else pl_or_links
    return {(pi, h.get('id') or h.get('student')) for pi, v in (links or {}).items() for h in v}


def filtered_rows_and_json(key, name, included, base=None, held=None):
    """The package file `name` as Python data restricted to `included` PIs: list (pis.json), dict (students.json, copies.json) or rows.
    `held` ({(pi, student id)}, `held_set`) drops exactly those student links: the student's row in students.json and any student-paper row (D-0017)."""
    inc = set(included)
    held = held or set()
    d = package_dir(key, base) / name
    if name == 'pis.json':
        return [x for x in _read_json(d) if x['pi'] in inc]
    if name == 'students.json':
        return {pi: [x for x in v if (pi, x.get('person') or x.get('id') or x.get('name')) not in held] for pi, v in _read_json(d).items() if pi in inc}
    if name == 'student_papers.jsonl.gz':
        return [r for r in _jsonl_gz(d) if r.get('pi') in inc and (r['pi'], r.get('student')) not in held]
    if name.endswith('.jsonl.gz'):
        return [r for r in _jsonl_gz(d) if r.get('pi') in inc]
    if name == 'copies.json':
        c = _read_json(d)
        oa = {r['oa'] for r in _jsonl_gz(package_dir(key, base) / 'lab_papers.jsonl.gz') if r.get('pi') in inc}
        out = dict(c)
        out['papers'] = {k: v for k, v in (c.get('papers') or {}).items() if k in oa}
        out['summary_scope'] = 'the school-wide build summary; papers are restricted to the included PIs'
        return out
    raise ValueError(name)


def filtered_bytes(key, name, included, base=None, held=None):
    """Deterministic bytes of the filtered package file (gzip mtime 0, sorted-free JSON in source key order)."""
    data = filtered_rows_and_json(key, name, included, base, held)
    if name.endswith('.jsonl.gz'):
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode='wb', mtime=0) as g:
            for r in data:
                g.write((json.dumps(r, ensure_ascii=False) + '\n').encode())
        return buf.getvalue()
    return (json.dumps(data, indent=1, ensure_ascii=False) + '\n').encode()


def package_hashes(key, included, base=None, held=None):
    """{file: sha256 of the filtered content} for the five accuracy files; content-hash, so the gzip framing does not matter."""
    out = {}
    for f in PACKAGE:
        if not (package_dir(key, base) / f).exists():
            continue
        data = filtered_rows_and_json(key, f, included, base, held)
        h = hashlib.sha256()
        for r in (data if isinstance(data, list) else [data]):
            h.update(json.dumps(r, sort_keys=True, ensure_ascii=False).encode() + b'\n')
        out[f] = h.hexdigest()
    return out


def scope_statement(pl, release_id=None):
    """The field the site reads. status: complete (nothing held) | partial."""
    pis = {}
    try:
        pis = {x['pi']: x for x in _read_json(package_dir(pl['school']) / 'pis.json')}
    except OSError:
        pass
    return dict(school=pl['school'], release=release_id, status='partial' if pl['held'] else 'complete',
                pis_total=pl['package_pis'], pis_included=len(pl['included']), pis_held=len(pl['held']), pis_carried_open=len(pl['carried']),
                included_sha=pl['included_sha'], held_links_n=sum(len(v) for v in (pl.get('held_links') or {}).values()),
                held_links=[dict(pi=pi, student=h.get('student'), id=h.get('id'), why=h.get('diagnosis') or 'no linked paper') for pi, v in sorted((pl.get('held_links') or {}).items()) for h in v],
                held=[dict(pi=pi, atlasId=pis.get(pi, {}).get('atlasId'), labId=pis.get(pi, {}).get('labId'), blocking=r) for pi, r in sorted(pl['held'].items())],
                carried_open=[dict(pi=pi, atlasId=pis.get(pi, {}).get('atlasId')) for pi in pl['carried']],
                school_items_reported=sum(len(v) for v in pl['school_items'].values()))


def render_notes(statements):
    """RELEASE-SCOPE.md: held PIs and their blocking reasons, per school."""
    out = ['# Release scope (per PI)', '', 'Published: PIs that are done or excluded with a recorded reason, with their labs, papers and students.',
           'Held: PIs with an open item; they are not in this release and are listed with the reason. A school with held PIs is partial.', '']
    for s in statements:
        out.append(f"## {s['school']}: {s['status']} ({s['pis_included']} of {s['pis_total']} PIs included, {s['pis_held']} held)")
        if s.get('held_links_n'):
            out.append(f"{s['held_links_n']} student links are held (chain-audit stage 7: the student has no linked paper yet; D-0017): the student is not in the PI's lab in this release unless published earlier.")
        if s['pis_carried_open']:
            out.append(f"{s['pis_carried_open']} PIs published earlier are carried although open now (published rows are never removed).")
        for h in s['held']:
            out.append(f"- {h['pi']}: " + '; '.join(h['blocking'])[:300])
        out.append('')
    return '\n'.join(out)


def _has_ids(key, base=None):
    pis = _read_json(package_dir(key, base) / 'pis.json')
    return bool(pis) and all(str(x.get('atlasId', '')).startswith('atl:p:') and str(x.get('labId', '')).startswith('atl:l:') for x in pis)


def _ids(key, base=None, inc=None, legacy=False, held=None):
    """Key sets of a package: PIs, labs, (lab, student) pairs, (lab, paper) and (lab, student, paper) links. Atlas ids (docs/IDS.md) when
    `legacy` is false; the pre-id keys (PI name, student person id, OpenAlex id) when a package has no ids yet."""
    d = package_dir(key, base)
    pis = _read_json(d / 'pis.json')
    keep = {x['pi'] for x in pis} if inc is None else set(inc)
    lab_of = {x['pi']: (x['pi'] if legacy else x.get('labId')) for x in pis if x['pi'] in keep}
    out = dict(pi={(x['pi'] if legacy else x.get('atlasId')) for x in pis if x['pi'] in keep}, lab=set(lab_of.values()),
               student=set(), lab_paper=set(), student_paper=set())
    for pi, ss in _read_json(d / 'students.json').items():
        if pi in keep:
            out['student'] |= {(lab_of.get(pi), s.get('person') if legacy else s.get('atlasId')) for s in ss
                               if (pi, s.get('person') or s.get('id') or s.get('name')) not in (held or ())}
    for r in _jsonl_gz(d / 'lab_papers.jsonl.gz'):
        if r.get('pi') in keep:
            out['lab_paper'].add((lab_of.get(r['pi']), r.get('oa') if legacy else r.get('atlasWorkId')))
    for r in _jsonl_gz(d / 'student_papers.jsonl.gz'):
        if r.get('pi') in keep and (r['pi'], r.get('student')) not in (held or ()):
            out['student_paper'].add((lab_of.get(r['pi']), r.get('student') if legacy else r.get('studentAtlasId'), r.get('oa') if legacy else r.get('atlasWorkId')))
    return out


def load_corrections(key, release):
    """The reviewed release-corrections record of a school (reviewed/release-corrections.json) when it was written against `release`, else None.
    It lists, per class, published rows the new package lacks for a reason an owner rule explains (Q-0339, 2026-11-18): each class carries its
    rule and its rows (pi, oa, labId, atlasWorkId); a student-paper link whose lab paper is listed follows it (cascade)."""
    p = P.data('release-corrections.json', key)
    if not p.exists():
        return None
    rec = _read_json(p)
    return rec if rec.get('against_release') == Path(release).resolve().name else None


def _accepted_lab_papers(rec, legacy):
    """{(lab, work): class id} of the corrected lab papers, keyed like `_ids` (pre-id keys when `legacy`, else atlas ids)."""
    out = {}
    for cl in rec.get('classes') or []:
        for r in cl.get('rows') or []:
            out[(rec.get('pi_renames', {}).get(r['pi'], r['pi']), r['oa']) if legacy else (r.get('labId'), r.get('atlasWorkId'))] = cl['id']
    return out


def _accepted_links(rec, legacy):
    """{(lab, student, work): class id} of corrected student-paper LINKS whose lab paper stays (class key `links`: a rule that drops the link, not the paper)."""
    out = {}
    for cl in rec.get('classes') or []:
        for r in cl.get('links') or []:
            out[(rec.get('pi_renames', {}).get(r['pi'], r['pi']), r['student'], r['oa']) if legacy else (r.get('labId'), r.get('studentAtlasId'), r.get('atlasWorkId'))] = cl['id']
    return out


def _accepted_students(rec, legacy):
    """{(lab, student): class id} of corrected removed students (class key `students`: rows pi, student / labId, studentAtlasId); their student-paper links follow them."""
    out = {}
    renames = rec.get('pi_renames') or {}
    for cl in rec.get('classes') or []:
        for r in cl.get('students') or []:
            out[(renames.get(r['pi'], r['pi']), r['student']) if legacy else (r.get('labId'), r.get('studentAtlasId'))] = cl['id']
    return out


def compare(key, included, release, corrections=None, held=None):
    """Monotone check: {kind: {'old', 'new', 'n_removed', 'added', 'removed'}} of the filtered new package against the package of the published
    `release` dir. Any n_removed > 0 is a flag. Compared by atlas ids when both packages carry them, else by the pre-id keys (`basis`); a school
    absent from the old release has nothing to compare. Removals that the school's release-corrections record explains (`load_corrections`, or the
    `corrections` argument) are not flags: they are counted per class under `corrected` (a lab paper by its row, a student-paper link by its lab
    paper) and `corrections_unused` counts recorded rows that are not removed now (restored)."""
    if not (package_dir(key, release) / 'pis.json').exists():
        return dict(school=key, compared=False, flags=0)
    legacy = not (_has_ids(key) and _has_ids(key, release))
    new, old = _ids(key, inc=included, legacy=legacy, held=held), _ids(key, base=release, legacy=legacy)
    rec = corrections if corrections is not None else load_corrections(key, release)
    renames = (rec or {}).get('pi_renames') or {}
    if legacy and renames:   # pre-id packages key by PI name: a census-renamed PI (recorded old -> current) is the same PI, so its rows compare under the current spelling
        rn = lambda x: tuple(renames.get(x[0], x[0]) if i == 0 else v for i, v in enumerate(x)) if isinstance(x, tuple) else renames.get(x, x)
        old = {k: {rn(x) for x in v} for k, v in old.items()}
    drift, drifted_pis = {}, set()
    if not legacy:   # a lab or person id can drift between builds when a PI loses an identity anchor (a new id is minted): follow the PI by name (and recorded rename) so the drift is reported, not counted as a removal
        o_pis, n_pis = {x['pi']: x for x in _read_json(package_dir(key, release) / 'pis.json')}, {x['pi']: x for x in _read_json(package_dir(key) / 'pis.json')}
        for pi, x in o_pis.items():
            y = n_pis.get(renames.get(pi, pi))
            if y:
                for f in ('labId', 'atlasId'):
                    if x.get(f) and y.get(f) and x[f] != y[f]:
                        drift[x[f]] = y[f]; drifted_pis.add(pi)
        if drift:
            old = {k: {(drift.get(x, x) if isinstance(x, str) else tuple(drift.get(v, v) if i == 0 else v for i, v in enumerate(x))) for x in v} for k, v in old.items()}
    acc = _accepted_lab_papers(rec, legacy) if rec else {}
    acc_links = _accepted_links(rec, legacy) if rec else {}
    acc_st = _accepted_students(rec, legacy) if rec else {}
    gone = {k: old[k] - new[k] for k in old}
    corrected = collections.Counter()
    if acc or acc_links or acc_st:
        for k, cls_of in (('lab_paper', lambda x: acc.get(x)), ('student', lambda x: acc_st.get(x)),
                          ('student_paper', lambda x: acc.get((x[0], x[2])) or acc_links.get(x) or acc_st.get(x[:2]))):
            for x in sorted(gone[k], key=str):
                if cls_of(x):
                    corrected[(k, cls_of(x))] += 1
            gone[k] = {x for x in gone[k] if not cls_of(x)}
    res = {k: dict(old=len(old[k]), new=len(new[k]), n_removed=len(gone[k]), added=len(new[k] - old[k]),
                   removed=sorted(map(str, gone[k]))[:5]) for k in old}
    out = dict(school=key, compared=True, release=Path(release).resolve().name, basis='legacy keys (a package has no atlas ids yet)' if legacy else 'atlas ids',
               kinds=res, flags=sum(v['n_removed'] for v in res.values()), id_drift=len(drifted_pis), id_drift_pis=sorted(drifted_pis))
    if rec:
        out['corrected'] = {f'{k}:{c}': n for (k, c), n in sorted(corrected.items())}
        out['corrections_unused'] = sum(1 for k in acc if k in new['lab_paper'])
        out['corrections_record'] = dict(path=str(P.data('release-corrections.json', key)), decided=rec.get('decided'), classes={c['id']: dict(rule=c.get('rule'), rows=len(c.get('rows') or [])) for c in rec.get('classes') or []})
    return out


def gate_findings(key, pl=None):
    """Gate 10, per PI (D-0001): at least one included PI and passing accuracy on the included subset. The held PIs and the school items are reported,
    not findings; a released school keeps its status (the caller returns before this)."""
    pl = pl or plan(key)
    bad = []
    if not pl['included']:
        bad.append('no PI is done: nothing to release')
    return bad, pl


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('school')
    ap.add_argument('--published', help='release dir to compare with (default releases/latest)')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    pub = Path(a.published) if a.published else None
    pl = plan(a.school, published=pub)
    st = scope_statement(pl)
    cmp_ = compare(a.school, pl['included'], pub or (Path(P.RELEASES) / 'latest'), held=held_set(pl)) if (pub or (Path(P.RELEASES) / 'latest').exists()) else None
    if a.json:
        print(json.dumps(dict(scope=st, compare=cmp_), ensure_ascii=False))
        return 1 if cmp_ and cmp_['flags'] else 0
    print(f"{a.school}: {st['status']}: {st['pis_included']}/{st['pis_total']} included ({pl['done']} done, {st['pis_carried_open']} carried open), {st['pis_held']} held, school items {st['school_items_reported']}")
    for h in st['held'][:8]:
        print('  held', h['pi'], '|', '; '.join(h['blocking'])[:200])
    if cmp_ and cmp_['compared']:
        print(f"vs release {cmp_['release']} by {cmp_['basis']}: removed {cmp_['flags']}", {k: (v['old'], v['new'], v['n_removed']) for k, v in cmp_['kinds'].items()})
        if cmp_.get('corrected'):
            print('  corrections recorded (not flags):', cmp_['corrected'], 'unused', cmp_['corrections_unused'])
    elif cmp_:
        print('vs last release: school not in it (nothing to compare)')
    return 1 if cmp_ and cmp_['flags'] else 0


if __name__ == '__main__':
    sys.exit(main())
