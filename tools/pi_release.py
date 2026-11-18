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
import argparse, gzip, hashlib, io, json, sys
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


def plan(key, res=None, published=None):
    """Who goes into a release of `key`. `res` is pi_states.compute(key) (computed when absent); `published` is the last release dir
    (default: releases/latest). included = package PIs not hard-open, plus carried (published, open now)."""
    import pi_states as PS
    res = res or PS.compute(key)
    pkg = [x['pi'] for x in _read_json(package_dir(key) / 'pis.json')]
    hard_open = set(res['open_pis'])
    held_all = {pi: [f"stage {s}: {res['pis'][pi][s]['reasons'][0]}" for s in PS.ALL if res['pis'][pi][s]['state'] == 'open'] for pi in sorted(hard_open) if pi in res['pis']}
    done = [pi for pi in pkg if pi not in hard_open]
    if published is None:
        latest = Path(P.RELEASES) / 'latest'
        published = latest if latest.exists() else None
    prev = (published_pis(key, published) or []) if published else []
    carried = [pi for pi in pkg if pi in hard_open and pi in set(prev)]
    included = [pi for pi in pkg if pi in set(done) or pi in set(carried)]
    held = {pi: r for pi, r in held_all.items() if pi in set(pkg) and pi not in set(carried)}
    for pi in pkg:                       # an open PI the state table does not know (should not happen) is held, never silently included
        if pi not in res['pis'] and pi not in set(included):
            held[pi] = ['no pi-states row']
    sha = hashlib.sha256('\n'.join(sorted(included)).encode()).hexdigest()
    return dict(school=key, package_pis=len(pkg), done=len(done), carried=carried, included=included, held=held, included_sha=sha,
                school_items={s: v for s, v in (res.get('school_items') or {}).items() if v},
                partial=bool(held), published_from=Path(published).resolve().name if published else None)


def filtered_rows_and_json(key, name, included, base=None):
    """The package file `name` as Python data restricted to `included` PIs: list (pis.json), dict (students.json, copies.json) or rows."""
    inc = set(included)
    d = package_dir(key, base) / name
    if name == 'pis.json':
        return [x for x in _read_json(d) if x['pi'] in inc]
    if name == 'students.json':
        return {pi: v for pi, v in _read_json(d).items() if pi in inc}
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


def filtered_bytes(key, name, included, base=None):
    """Deterministic bytes of the filtered package file (gzip mtime 0, sorted-free JSON in source key order)."""
    data = filtered_rows_and_json(key, name, included, base)
    if name.endswith('.jsonl.gz'):
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode='wb', mtime=0) as g:
            for r in data:
                g.write((json.dumps(r, ensure_ascii=False) + '\n').encode())
        return buf.getvalue()
    return (json.dumps(data, indent=1, ensure_ascii=False) + '\n').encode()


def package_hashes(key, included, base=None):
    """{file: sha256 of the filtered content} for the five accuracy files; content-hash, so the gzip framing does not matter."""
    out = {}
    for f in PACKAGE:
        if not (package_dir(key, base) / f).exists():
            continue
        data = filtered_rows_and_json(key, f, included, base)
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
                included_sha=pl['included_sha'],
                held=[dict(pi=pi, atlasId=pis.get(pi, {}).get('atlasId'), labId=pis.get(pi, {}).get('labId'), blocking=r) for pi, r in sorted(pl['held'].items())],
                carried_open=[dict(pi=pi, atlasId=pis.get(pi, {}).get('atlasId')) for pi in pl['carried']],
                school_items_reported=sum(len(v) for v in pl['school_items'].values()))


def render_notes(statements):
    """RELEASE-SCOPE.md: held PIs and their blocking reasons, per school."""
    out = ['# Release scope (per PI)', '', 'Published: PIs that are done or excluded with a recorded reason, with their labs, papers and students.',
           'Held: PIs with an open item; they are not in this release and are listed with the reason. A school with held PIs is partial.', '']
    for s in statements:
        out.append(f"## {s['school']}: {s['status']} ({s['pis_included']} of {s['pis_total']} PIs included, {s['pis_held']} held)")
        if s['pis_carried_open']:
            out.append(f"{s['pis_carried_open']} PIs published earlier are carried although open now (published rows are never removed).")
        for h in s['held']:
            out.append(f"- {h['pi']}: " + '; '.join(h['blocking'])[:300])
        out.append('')
    return '\n'.join(out)


def _has_ids(key, base=None):
    pis = _read_json(package_dir(key, base) / 'pis.json')
    return bool(pis) and all(str(x.get('atlasId', '')).startswith('atl:p:') and str(x.get('labId', '')).startswith('atl:l:') for x in pis)


def _ids(key, base=None, inc=None, legacy=False):
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
            out['student'] |= {(lab_of.get(pi), s.get('person') if legacy else s.get('atlasId')) for s in ss}
    for r in _jsonl_gz(d / 'lab_papers.jsonl.gz'):
        if r.get('pi') in keep:
            out['lab_paper'].add((lab_of.get(r['pi']), r.get('oa') if legacy else r.get('atlasWorkId')))
    for r in _jsonl_gz(d / 'student_papers.jsonl.gz'):
        if r.get('pi') in keep:
            out['student_paper'].add((lab_of.get(r['pi']), r.get('student') if legacy else r.get('studentAtlasId'), r.get('oa') if legacy else r.get('atlasWorkId')))
    return out


def compare(key, included, release):
    """Monotone check: {kind: {'old', 'new', 'n_removed', 'added', 'removed'}} of the filtered new package against the package of the published
    `release` dir. Any n_removed > 0 is a flag. Compared by atlas ids when both packages carry them, else by the pre-id keys (`basis`); a school
    absent from the old release has nothing to compare."""
    if not (package_dir(key, release) / 'pis.json').exists():
        return dict(school=key, compared=False, flags=0)
    legacy = not (_has_ids(key) and _has_ids(key, release))
    new, old = _ids(key, inc=included, legacy=legacy), _ids(key, base=release, legacy=legacy)
    res = {k: dict(old=len(old[k]), new=len(new[k]), n_removed=len(old[k] - new[k]), added=len(new[k] - old[k]),
                   removed=sorted(map(str, old[k] - new[k]))[:5]) for k in old}
    return dict(school=key, compared=True, release=Path(release).resolve().name, basis='legacy keys (a package has no atlas ids yet)' if legacy else 'atlas ids',
                kinds=res, flags=sum(v['n_removed'] for v in res.values()))


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
    cmp_ = compare(a.school, pl['included'], pub or (Path(P.RELEASES) / 'latest')) if (pub or (Path(P.RELEASES) / 'latest').exists()) else None
    if a.json:
        print(json.dumps(dict(scope=st, compare=cmp_), ensure_ascii=False))
        return 1 if cmp_ and cmp_['flags'] else 0
    print(f"{a.school}: {st['status']}: {st['pis_included']}/{st['pis_total']} included ({pl['done']} done, {st['pis_carried_open']} carried open), {st['pis_held']} held, school items {st['school_items_reported']}")
    for h in st['held'][:8]:
        print('  held', h['pi'], '|', '; '.join(h['blocking'])[:200])
    if cmp_ and cmp_['compared']:
        print(f"vs release {cmp_['release']} by {cmp_['basis']}: removed {cmp_['flags']}", {k: (v['old'], v['new'], v['n_removed']) for k, v in cmp_['kinds'].items()})
    elif cmp_:
        print('vs last release: school not in it (nothing to compare)')
    return 1 if cmp_ and cmp_['flags'] else 0


if __name__ == '__main__':
    sys.exit(main())
