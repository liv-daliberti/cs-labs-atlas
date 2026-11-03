"""Copy a school's git-trackable files (reports/*.md, reviewed/*.json: whatever .gitignore admits) from the MAIN checkout's data tree into
this worktree, so they can be committed on the worktree's branch.

Tools write every data path into the main checkout (atlas_paths), but a worktree commits its own tree: before this tool each report and
reviewed input was copied across by hand (UChicago onboarding, PROTOCOL-FRICTION #11). Only files that .gitignore does NOT ignore are
copied, and only when the content differs; nothing is deleted.

usage: sync_school_files.py <key> [--dry-run]       (run from the worktree; prints one line per copied file)
"""
import argparse, shutil, subprocess, sys
from pathlib import Path


def sync(key, src_root, dst_root, dry=False):
    """Copy files of <src_root>/hierarchy/<key>/{reports,reviewed,derived} that the destination repo does not ignore; returns the list copied."""
    src_root, dst_root = Path(src_root), Path(dst_root)
    done = []
    base = src_root / 'hierarchy' / key
    for f in sorted(p for p in base.rglob('*') if p.is_file() and 'tmp' not in p.relative_to(base).parts):
        rel = f.relative_to(src_root)
        if subprocess.run(['git', '-C', str(dst_root), 'check-ignore', '-q', str(rel)], capture_output=True).returncode == 0:
            continue  # data, not code or a reviewed input
        dst = dst_root / rel
        if dst.exists() and dst.read_bytes() == f.read_bytes():
            continue
        done.append(str(rel))
        if not dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dst)
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key'); ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    import atlas_paths as P
    here = Path(__file__).resolve().parents[1]
    if here.resolve() == Path(P.CODE).resolve():
        sys.exit('sync_school_files: this is the main checkout; run it from a worktree')
    for r in sync(a.key, P.CODE, here, a.dry_run):
        print(('would copy ' if a.dry_run else 'copied ') + r)
    return 0


if __name__ == '__main__':
    sys.exit(main())
