"""Compare two builds of school packages canonically (refactor equivalence, ROADMAP items 5 and 8).

Each file present in either tree is compared after decoding: `.gz` is decompressed; JSON is parsed and compared as data
(object key order ignored, list order kept); JSON lines are compared line by line as data; other files byte for byte.
Only the fields named by --ignore are skipped (dotted paths into a JSON file, `<file>:<path>`); by default the two build
timestamps, report.json `builtAt` and `provenance.at`. Every other difference is reported with its path.

usage: package_diff.py <old root> <new root> [--schools a b ...] [--ignore report.json:builtAt ...] [--json out.json]
       (a root holds <school>/ package directories, as PI_HIERARCHY_OUT writes them)
exit 0 when every compared file is identical, 1 otherwise
"""
import argparse
import gzip
import json
import sys
from pathlib import Path

DEFAULT_IGNORE = ['report.json:builtAt', 'report.json:provenance.at']  # build timestamps, nothing else


def _load(p):
    b = p.read_bytes()
    if p.suffix == '.gz':
        b = gzip.decompress(b)
    name = p.name[:-3] if p.suffix == '.gz' else p.name
    if name.endswith('.jsonl'):
        return 'jsonl', [json.loads(x) for x in b.decode().split('\n') if x.strip()]  # not splitlines(): U+2028 occurs inside strings
    if name.endswith('.json'):
        return 'json', json.loads(b)
    return 'bytes', b


def _drop(d, path):
    """Remove the dotted path from a JSON object (in place); returns whether it was there."""
    keys = path.split('.')
    for k in keys[:-1]:
        if not isinstance(d, dict) or k not in d:
            return False
        d = d[k]
    return isinstance(d, dict) and d.pop(keys[-1], None) is not None


def diff_paths(a, b, path='', out=None, limit=20):
    """Paths where two JSON values differ (up to `limit`)."""
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b:
                out.append(f'{path}.{k} only in ' + ('new' if k not in a else 'old'))
            elif a[k] != b[k]:
                diff_paths(a[k], b[k], f'{path}.{k}', out, limit)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f'{path} length {len(a)} -> {len(b)}')
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                diff_paths(x, y, f'{path}[{i}]', out, limit)
            if len(out) >= limit:
                break
    elif a != b:
        out.append(f'{path}: {str(a)[:80]!r} -> {str(b)[:80]!r}')
    return out


def compare_dir(old, new, ignore):
    res = {}
    for f in sorted({p.name for p in old.iterdir() if p.is_file()} | {p.name for p in new.iterdir() if p.is_file()}):
        po, pn = old / f, new / f
        if not po.exists() or not pn.exists():
            res[f] = dict(status='only in ' + ('new' if not po.exists() else 'old'))
            continue
        (ko, a), (kn, b) = _load(po), _load(pn)
        ignored = []
        for spec in ignore:
            fn, _, path = spec.partition(':')
            if fn == f and ko == 'json':
                ignored += [path] if (_drop(a, path) | _drop(b, path)) else []
        if a == b:
            res[f] = dict(status='identical', kind=ko, ignored=ignored, **({'records': len(a)} if ko == 'jsonl' else {}))
        else:
            res[f] = dict(status='differs', kind=ko, ignored=ignored,
                          diffs=diff_paths(a, b) if ko != 'bytes' else ['bytes differ'])
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('old', type=Path)
    ap.add_argument('new', type=Path)
    ap.add_argument('--schools', nargs='*')
    ap.add_argument('--ignore', nargs='*', default=DEFAULT_IGNORE)
    ap.add_argument('--json', type=Path)
    a = ap.parse_args(argv)
    schools = a.schools or sorted({p.name for p in a.old.iterdir() if p.is_dir()} | {p.name for p in a.new.iterdir() if p.is_dir()})
    rep, ok = {}, True
    for s in schools:
        if not (a.old / s).is_dir() or not (a.new / s).is_dir():
            rep[s] = {'*': dict(status='package missing in ' + ('old' if not (a.old / s).is_dir() else 'new'))}
        else:
            rep[s] = compare_dir(a.old / s, a.new / s, a.ignore)
        for f, r in rep[s].items():
            ok &= r['status'] == 'identical'
            extra = f" ({r['records']} records)" if 'records' in r else ''
            ign = f" ignored: {', '.join(r['ignored'])}" if r.get('ignored') else ''
            print(f"{s:10s} {f:28s} {r['status']}{extra}{ign}")
            for d in r.get('diffs') or []:
                print(f'{"":12s}{d}')
    if a.json:
        a.json.write_text(json.dumps(dict(ignore=a.ignore, identical=ok, schools=rep), indent=1))
    print('ALL IDENTICAL' if ok else 'DIFFERENCES FOUND')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
