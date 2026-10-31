"""Validate the atlas's data files against their schemas (ROADMAP item 9; schemas/*.schema.json, tools/schema_check.py,
docs/DATA-DICTIONARY.md). The rebuild stage `validate` runs it on every package and the shared derived files, and a
violation fails the stage (so the release is held).

  validate.py [school ...]          the derived per-school files (packages, copies, ledger, diagnoses) of these schools
                                    (default: the released schools)
    --shared                        also the shared derived files (chain audit, student audit, evidence check, regression)
    --reviewed                      also the reviewed-decision files (per school and shared)
    --tree / --export               also the organized tree's and the GitHub export's CSVs
    --root DIR                      read the files under DIR instead of the code root (a trial build: DIR/hierarchy/<school>/)
    --json FILE                     write the result (counts and up to 5 examples per file)
Exit 1 when any file has a violation. A missing file is reported, not a violation (not every school has every file).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place; DATA_FILES)
import schema_check as S  # noqa: E402

SCHEMAS = Path(__file__).resolve().parent.parent / 'schemas'
_FLAT = {flat.replace('{school}', '<school>'): name for name, _, flat, _ in P.DATA_FILES}


def schemas():
    out = []
    for f in sorted(SCHEMAS.glob('*.schema.json')):
        s = json.loads(f.read_text())
        out.append((f.name[:-len('.schema.json')], s))
    return out


def paths_for(xfile, school, root=None):
    """The files a schema's x-file pattern names for one school (or shared when the pattern has no <school>)."""
    if xfile in _FLAT:
        return [P.data(_FLAT[xfile], school, root=root)]
    if xfile.startswith('docs/'):
        return [Path(root or P.CODE) / xfile]
    for top, base in (('export/', P.EXPORT), ('schools/', P.SCHOOLS_TREE)):
        if xfile.startswith(top):
            rel = xfile[len(top):].replace('<school>', school or '')
            if '<pi-slug>' in rel:  # one level of lab directories, never a deeper walk
                head, tail = rel.split('<pi-slug>/')
                d = base / head
                return sorted(x / tail for x in d.iterdir() if (x / tail).exists()) if d.is_dir() else []
            return [base / rel]
    raise ValueError(f'no path for schema file pattern {xfile!r}: add it to atlas_paths.DATA_FILES')


def selected(a):
    for name, s in schemas():
        xf, kind = s.get('x-file') or '', s.get('x-kind')
        tree, export = xf.startswith('schools/'), xf.startswith('export/')
        if tree and not a.tree or export and not a.export:
            continue
        if kind == 'reviewed' and not a.reviewed:
            continue
        per_school = '<school>' in xf
        if not per_school and kind == 'derived' and not (a.shared or tree or export):
            continue
        yield name, s, per_school


def run(a):
    res, total = {}, 0
    for name, s, per_school in selected(a):
        for school in (a.schools if per_school else [None]):
            for f in paths_for(s['x-file'], school, a.root):
                key = f'{school or "shared"} {name}' + (f' {f.parent.name}' if '<pi-slug>' in s['x-file'] else '')
                if not f.exists():
                    res[key] = dict(file=str(f), status='missing'); continue
                errs = S.validate_file(f, s, limit=10 ** 7)
                total += len(errs)
                res[key] = dict(file=str(f), status='ok' if not errs else 'violations', violations=len(errs),
                                examples=[f'{p}: {m}' for p, m in errs[:5]])
    return res, total


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('schools', nargs='*')
    ap.add_argument('--shared', action='store_true')
    ap.add_argument('--reviewed', action='store_true')
    ap.add_argument('--tree', action='store_true')
    ap.add_argument('--export', action='store_true')
    ap.add_argument('--root')
    ap.add_argument('--json')
    a = ap.parse_args(argv)
    a.schools = a.schools or list(P.SCHOOL_IDS)
    res, total = run(a)
    bad = {k: v for k, v in res.items() if v['status'] == 'violations'}
    for k, v in res.items():
        if v['status'] != 'ok' or len(res) < 40:
            print(f"{k:45s} {v['status']}" + (f" {v['violations']}" if v.get('violations') else ''))
            for e in v.get('examples') or []:
                print(f'    {e[:200]}')
    checked = sum(v['status'] != 'missing' for v in res.values())
    print(f'validate: {checked} files checked, {len(bad)} with violations ({total} in all), '
          f"{sum(v['status'] == 'missing' for v in res.values())} missing")
    if a.json:
        Path(a.json).write_text(json.dumps(dict(schools=a.schools, files_checked=checked, violations=total, files=res), indent=1))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
