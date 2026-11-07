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
  - hierarchy/<school>/derived, raw and tmp are main's (build outputs stay where the release and the other tools read them);
  - everything else in the main root is a symlink to main.
Run any tool against it with `CS_ATLAS_CODE=<out> bin/atlas <command>` (from the worktree). Nothing in main's tracked files is touched.

  overlay_root.py <school> --out <dir> [--worktree <dir>]      (<dir> under hierarchy/<school>/tmp/, which git ignores; rebuilt if it exists)
"""
import argparse
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


def build(school, out, worktree=None, main=None):
    main = Path(main or P.CODE).resolve()
    worktree = Path(worktree or Path(__file__).resolve().parents[1]).resolve()
    out = Path(out).absolute()
    if out == main or main in out.parents and not (main / 'hierarchy' / school / 'tmp') in out.parents:
        raise SystemExit(f'refused: {out} is inside the main checkout outside hierarchy/{school}/tmp/')
    if out.exists():
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
    return out, n_branch + n_shared


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('school')
    ap.add_argument('--out', required=True)
    ap.add_argument('--worktree')
    a = ap.parse_args(argv)
    out, n = build(a.school, a.out, a.worktree)
    print(f'overlay {out}: code from the worktree, {n} reviewed/report files from its branch')
    print(f'run: CS_ATLAS_CODE={out} bin/atlas <command>      (commit the files a writer changes in the worktree; main stays clean)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
