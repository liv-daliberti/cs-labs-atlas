"""sha256 manifest of a school's gitignored build inputs (derived/, raw/, listings/<school>/), so a clean checkout can tell what is missing or changed.

Only reviewed/ and reports/ are tracked in git; the build also reads derived, raw and listings files that git ignores. A manifest is one JSON
file per school, hierarchy/<school>/inputs-manifest.sha256.json (itself gitignored, beside the data), listing path -> {sha256, bytes} for every
file under hierarchy/<school>/{derived,raw}, listings/<school>/{derived,raw} that is not a build OUTPUT (the files a build writes are compared by
scratch/verify-build-1113/compare.py, not pinned here) and not under tmp/ or work/.

  input_manifest.py write <school> [--root <code root>]      hash the inputs and write the manifest (a rewrite replaces the file, never the data)
  input_manifest.py check <school> [--root <code root>]      re-hash; exit 1 and name every missing / changed / new file (a changed append-only
                                                             collector store, MUTABLE, is printed as a warning and does not fail)
Paths come from atlas_paths (CODE) unless --root is given (tests)."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

OUTPUTS = ('pis.json', 'students.json', 'lab_papers.jsonl.gz', 'student_papers.jsonl.gz', 'report.json')   # pi_hierarchy.py products: not inputs
INPUT_DIRS = (('hierarchy', 'derived'), ('hierarchy', 'raw'), ('listings', 'derived'), ('listings', 'raw'))
MANIFEST = 'inputs-manifest.sha256.json'
MUTABLE = ('school-captures.sqlite', 'labpage-audit-captures.sqlite', 'labpage-audit-discovery.jsonl', 'pi-works.sqlite', 'captures.sqlite')   # append-only stores that live collectors keep writing in main (overlay_root.MUTABLE_RAW): a changed sha is a WARNING, not a failure
CHUNK = 8 * 1024 * 1024   # block I/O: the OpenAlex sweeps are 0.5-1 GB


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(CHUNK), b''):
            h.update(block)
    return h.hexdigest()


def manifest_path(root, school):
    return Path(root) / 'hierarchy' / school / MANIFEST


def input_files(root, school):
    """{relative path: Path} of every gitignored input file of the school (symlinks are followed, so a sha-pinned link is hashed by content)."""
    root = Path(root)
    found = {}
    for top, sub in INPUT_DIRS:
        base = root / top / school / sub
        if not base.is_dir():
            continue
        for f in sorted(base.iterdir()):   # one level: these dirs are flat; no recursion into shared stores
            if f.is_file() and f.name not in OUTPUTS and not f.name.startswith('.'):
                found[f'{top}/{school}/{sub}/{f.name}'] = f
    return found


def build(root, school):
    return {rel: {'sha256': sha256(p), 'bytes': p.stat().st_size} for rel, p in input_files(root, school).items()}


def write(root, school):
    files = build(root, school)
    out = manifest_path(root, school)
    out.write_text(json.dumps({'school': school, 'outputs_excluded': list(OUTPUTS), 'files': files}, indent=1, sort_keys=True) + '\n')
    return files


def check(root, school):
    """[(path, why)] for each manifest entry that is missing or changed, and each input file the manifest does not list."""
    out = manifest_path(root, school)
    if not out.exists():
        return [(str(out), 'no manifest')]
    want = json.loads(out.read_text())['files']
    have = input_files(root, school)
    bad = []
    for rel, meta in sorted(want.items()):
        p = have.get(rel)
        if p is None:
            bad.append((rel, 'missing'))
        elif p.stat().st_size != meta['bytes']:
            bad.append((rel, f"size {p.stat().st_size} != {meta['bytes']}"))
        elif sha256(p) != meta['sha256']:
            bad.append((rel, 'sha256 changed (mutable store: a collector appended since the manifest)' if p.name in MUTABLE else 'sha256 changed'))
    bad += [(rel, 'not in the manifest') for rel in sorted(set(have) - set(want))]
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cmd', choices=('write', 'check'))
    ap.add_argument('school')
    ap.add_argument('--root')
    a = ap.parse_args(argv)
    if a.root:
        root = a.root
    else:
        import atlas_paths as P
        root = P.CODE
    if a.cmd == 'write':
        files = write(root, a.school)
        print(f'{a.school}: {len(files)} input files, {sum(m["bytes"] for m in files.values())} bytes -> {manifest_path(root, a.school)}')
        return 0
    bad = check(root, a.school)
    for rel, why in bad:
        print(f'{a.school}: {rel}: {why}')
    bad = [(rel, why) for rel, why in bad if 'mutable store' not in why]   # warnings above, failures below
    print(f'{a.school}: {"OK" if not bad else f"{len(bad)} problem(s)"}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
