"""An overlay code root for one onboarding school: the procedure that works around ROADMAP #44 (reviewed files resolve to the MAIN checkout).

`atlas_paths.data()` resolves hierarchy/<school>/{reviewed,reports,...} under CS_ATLAS_CODE, the main checkout, so a build or audit run from a
worktree reads main's copies of the school's reviewed files, and a writer puts them there (a tracked file dirty in main while a release runs).
The overlay is a directory of symlinks that looks like the main code root, except that
  - the code directories (tools, atlas_cli, bin, schools, tests, vendor, docs, accuracy) are the WORKTREE's;
  - hierarchy/<school>/reviewed and reports hold a symlink per file: the worktree's file where the branch tracks one (so branch edits are live,
    and a writer's output lands in the worktree, ready to commit), else main's file;
  - hierarchy/reviewed (the shared reviewed files: census-overrides.json, ...) is overlaid the same way, per file, recursively (a branch's override was
    silently dropped when the overlay linked main's directory);
  - hierarchy/<school>/work is a REAL directory of the overlay (fixed 2026-11-05): a run wrote main's hierarchy/michigan/work/dblp-recover.sqlite through
    the old symlink. `atlas_paths.data()` resolves work files into it, and `data_w()` seeds a copy of main's file there when the file is first written
    (the marker .overlay.json at the overlay root names main). The three compressed recovery/publication inputs are copied
    at overlay creation so a read-only build retains them without first running a collector. Main's work files are never opened for writing;
  - hierarchy/<school>/derived, raw and tmp are main's (build outputs stay where the release and the other tools read them) UNLESS `--private`: then derived,
    the mutable raw stores and listings/<school> are real copies, a rebuild of the overlay PRESERVES them (never deletes a private copy), the overlay holds a
    sha256 receipt of main's school derived files (main-derived.sha256.json) and `--verify` fails when main's files changed since;
  - everything else in the main root is a symlink to main.
Run any tool against it with `CS_ATLAS_CODE=<out> bin/atlas <command>` (from the worktree). Nothing in main's tracked files is touched.

  overlay_root.py <school> --out <dir> [--worktree <dir>] [--private] [--verify]      (<dir> under hierarchy/<school>/tmp/, which git ignores; rebuilt if it exists)
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import atlas_paths as P  # noqa: E402

CODE_DIRS = ('tools', 'atlas_cli', 'bin', 'schools', 'tests', 'vendor', 'docs', 'accuracy')
SCHOOL_REAL = ('reviewed', 'reports', 'work')   # work: real but empty (seeded on first write); reviewed, reports: a link per file
SEEDED_EMPTY = ('work',)
WORK_READ_INPUTS = ('dblp-recovered.jsonl.gz', 'labpage-recovered.jsonl.gz', 'labpage-pubs.jsonl.gz')
SHARED_REVIEWED = 'reviewed'   # hierarchy/reviewed/: shared reviewed files
# Private copies (2026-11-09, Harvard incident: a builder run through the default symlinks overwrote main's derived files, and a later overlay
# rebuild deleted a private captures store a running job was filling). `--private` makes these real copies; a rebuild PRESERVES them.
MUTABLE_RAW = ('school-captures.sqlite', 'labpage-audit-captures.sqlite', 'labpage-audit-discovery.jsonl', 'pi-works.sqlite')
COPY_LIMIT = 100 * 1024 * 1024   # raw files above this stay main's symlinks (the OpenAlex sweep); atlas_paths.data_w refuses to write through them
RECEIPT = 'main-derived.sha256.json'


def private_paths(school):
    """Overlay-relative paths that hold private copies once `--private` made them."""
    return [Path('hierarchy') / school / 'derived', Path('hierarchy') / school / 'raw', Path('listings') / school]


def is_private(out, rel):
    p = Path(out) / rel
    return p.is_dir() and not p.is_symlink()


def main_hashes(main, school):
    """sha256 of every file in main's school derived and listings dirs (the files a builder run through a symlink would overwrite)."""
    h = {}
    for d in (Path(main) / 'hierarchy' / school / 'derived', Path(main) / 'listings' / school / 'derived'):
        for f in sorted(d.rglob('*')) if d.is_dir() else []:
            if f.is_file():
                h[str(f.relative_to(main))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return h


def make_private(out, school, main):
    """Replace the overlay's derived / raw / listings-<school> symlinks by private copies (idempotent; an existing private dir is left alone)."""
    out, main = Path(out), Path(main)
    d = out / 'hierarchy' / school / 'derived'
    if d.is_symlink():
        d.unlink()
        shutil.copytree(main / 'hierarchy' / school / 'derived', d)
    r = out / 'hierarchy' / school / 'raw'
    if r.is_symlink():
        r.unlink()
        r.mkdir()
        for f in sorted((main / 'hierarchy' / school / 'raw').iterdir()):
            if f.is_file() and f.stat().st_size <= COPY_LIMIT:   # every small raw file is a real copy (2026-11-10 HKUST incident: a tool wrote main's raw .json.gz through a symlink); only the big sweep stays a read-only link
                shutil.copy2(f, r / f.name)
            else:
                link(r / f.name, f)
    li = out / 'listings'
    if li.is_symlink():
        li.unlink()
        li.mkdir()
        for f in sorted((main / 'listings').iterdir()):
            if f.name != school:
                link(li / f.name, f)
    sd = li / school
    if not sd.exists():
        sd.mkdir()
        if (main / 'listings' / school / 'derived').is_dir():
            shutil.copytree(main / 'listings' / school / 'derived', sd / 'derived')
        (sd / 'raw').mkdir(exist_ok=True)


def verify(out, school=None):
    """Compare main's school derived files with the receipt written when the overlay was built. Returns the list of changed paths."""
    out = Path(out)
    meta = json.loads((out / '.overlay.json').read_text())
    school = school or meta['school']
    before = json.loads((out / RECEIPT).read_text())
    now = main_hashes(meta['main'], school)
    return sorted(k for k in set(before) | set(now) if before.get(k) != now.get(k))


def tracked(worktree, rel):
    r = subprocess.run(['git', '-C', str(worktree), 'ls-files', '--', rel], capture_output=True, text=True)
    return [Path(x) for x in r.stdout.split('\n') if x]


def link(dst, src):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        dst.unlink()
    dst.symlink_to(Path(src).resolve())


def overlay_dir(d, src, worktree, rel_dir):
    """Fill the real directory d with a symlink per file: main's files under src (recursively), then the branch's tracked files of rel_dir over them.
    Returns the number of branch files linked."""
    d.mkdir(parents=True, exist_ok=True)

    def walk(s, t):
        for f in sorted(s.iterdir()) if s.is_dir() else []:
            if f.is_dir():
                walk(f, t / f.name)
            else:
                link(t / f.name, f)
    walk(src, d)
    n = 0
    for rel in tracked(worktree, rel_dir):   # the branch's tracked file wins over main's copy
        link(d / rel.relative_to(rel_dir), worktree / rel)
        n += 1
    return n


def build(school, out, worktree=None, main=None, private=False):
    main = Path(main or P.CODE).resolve()
    worktree = Path(worktree or Path(__file__).resolve().parents[1]).resolve()
    out = Path(out).absolute()
    if out == main or main in out.parents and not (main / 'hierarchy' / school / 'tmp') in out.parents:
        raise SystemExit(f'refused: {out} is inside the main checkout outside hierarchy/{school}/tmp/')
    keep = {}
    park = out.parent / (out.name + '.private-park')
    if out.exists():
        # never delete a private copy (a running job may hold it): park it, rebuild, put it back
        if park.exists():
            raise SystemExit(f'refused: {park} exists (an earlier rebuild was interrupted); restore or remove it by hand')
        for rel in private_paths(school):
            if is_private(out, rel):
                (park / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(out / rel), str(park / rel))
                keep[rel] = park / rel
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for e in sorted(main.iterdir()):
        if e.name == 'hierarchy':
            continue
        src = worktree / e.name if e.name in CODE_DIRS and (worktree / e.name).exists() else e
        link(out / e.name, src)
    hier = out / 'hierarchy'
    hier.mkdir()
    for e in sorted((main / 'hierarchy').iterdir()):
        if e.name not in (school, SHARED_REVIEWED):
            link(hier / e.name, e)
    n_shared = overlay_dir(hier / SHARED_REVIEWED, main / 'hierarchy' / SHARED_REVIEWED, worktree, f'hierarchy/{SHARED_REVIEWED}')
    sch = hier / school
    sch.mkdir()
    for e in sorted((main / 'hierarchy' / school).iterdir()):
        if e.name not in SCHOOL_REAL:
            link(sch / e.name, e)
    n_branch = 0
    for part in SCHOOL_REAL:
        d = sch / part
        d.mkdir()
        if part in SEEDED_EMPTY:
            # These work files are also builder inputs. data_w() cannot seed them in a read-only build.
            for name in WORK_READ_INPUTS:
                src = main / 'hierarchy' / school / part / name
                if src.is_file():
                    shutil.copy2(src, d / name)
            continue
        n_branch += overlay_dir(d, main / 'hierarchy' / school / part, worktree, f'hierarchy/{school}/{part}')
    (out / '.overlay.json').write_text(json.dumps(dict(main=str(main), school=school, worktree=str(worktree))))
    if private or keep:
        make_private(out, school, main)
    for rel, src in keep.items():   # the preserved private copy replaces whatever the rebuild linked or copied
        dst = out / rel
        if dst.is_symlink():
            dst.unlink()
        elif dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    if keep:
        shutil.rmtree(park, ignore_errors=True)
    (out / RECEIPT).write_text(json.dumps(main_hashes(main, school), indent=0, sort_keys=True))
    return out, n_branch + n_shared


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('school')
    ap.add_argument('--out', required=True)
    ap.add_argument('--worktree')
    ap.add_argument('--private', action='store_true', help='private copies of derived / raw (mutable stores) / listings/<school>: builders and fetchers write there, never main')
    ap.add_argument('--verify', action='store_true', help="compare main's school derived files with the receipt of the overlay build; exit 1 on any difference")
    a = ap.parse_args(argv)
    if a.verify:
        changed = verify(a.out, a.school)
        print('main derived files unchanged since the overlay was built' if not changed else 'MAIN CHANGED: ' + ', '.join(changed))
        return 1 if changed else 0
    out, n = build(a.school, a.out, a.worktree, private=a.private)
    print(f'overlay {out}: code from the worktree, {n} reviewed/report files from its branch')
    print(f'run: CS_ATLAS_CODE={out} bin/atlas <command>      (commit the files a writer changes in the worktree; main stays clean)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
