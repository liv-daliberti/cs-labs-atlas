"""Where fulltext-push/ joins its own data directories by hand (2026-10-31, ROADMAP item 10).

The collectors keep raw/, checks/, logs/, review-<stamp>/ and local-reuse/ data next to their code. A job that runs from a code
snapshot (tools/job_code_snapshot.sh) must find that data in the main checkout, so every read and write goes through the
atlas_paths slots FT_RAW, FT_CHECKS, FT_LOGS, FT_LOCAL_REUSE and ft_review(<stamp>) (shell: $CS_ATLAS_FT_RAW, ... ). This
lists the places that still join by hand.

usage: route_ft_data.py [--root DIR]      prints file:line: text, and the count; exit 1 when any remain
"""
import argparse, re, sys
from pathlib import Path

DIRS = r'(?:raw|checks|logs|local-reuse|review-[0-9A-Za-z-]+)'
PY = re.compile(r"""(?:HERE|FULLTEXT_PUSH|parent|__file__\)[^/]*|FT_DATA)\s*/\s*['"]""" + DIRS + r"""['"/]""")
SH = re.compile(r"""(?:^|[\s"'=>(<;|@]|\$HERE/|\$CS_ATLAS_FULLTEXT_PUSH/|\./)(?:raw|logs|checks)/[A-Za-z0-9_.$*{}-]""")
LR = re.compile(r"""\bHERE\s*/\s*['\"]""")  # inside local-reuse/, every HERE / '<name>' join is data (code is not joined)
SKIP_FILES = {'job_snapshot.sh'}


FT_JOIN = re.compile(r"""(?:FULLTEXT_PUSH|FT_DATA|['"]fulltext-push['"])\s*/\s*['"]""" + DIRS + r"""['"/]""")
FT_SH = re.compile(r'\$\{?CS_ATLAS_FULLTEXT_PUSH\}?/(?:raw|logs|checks|local-reuse|review-)')
OUTSIDE = ('tools', 'vendor', 'hierarchy', 'listings', 'accuracy', 'ai-writing')   # code outside fulltext-push/ that names its data dirs
SELF = {'tools/route_ft_data.py'}


def scan_outside(code_root):
    """Joins onto FULLTEXT_PUSH (or CS_ATLAS_FULLTEXT_PUSH) whose next segment is a data directory, in the rest of the repository: a job
    running from a code snapshot would read and write them inside the snapshot (2026-11-01: s2-pace, labpage_audit)."""
    out = []
    for top in OUTSIDE:
        for f in sorted((Path(code_root) / top).rglob('*')) if (Path(code_root) / top).is_dir() else []:
            rel = f.relative_to(code_root).as_posix()
            if f.suffix not in ('.py', '.sh', '.slurm') or '__pycache__' in f.parts or rel in SELF or '/tests/' in rel:
                continue
            for n, line in enumerate(f.read_text(errors='replace').splitlines(), 1):
                t = line.strip()
                if t.startswith(('#', '"""', "'''")):
                    continue
                if (f.suffix == '.py' and FT_JOIN.search(line)) or (f.suffix != '.py' and FT_SH.search(line)):
                    out.append((f, n, t))
    return out


def scan(root):
    out = []
    for f in sorted(Path(root).rglob('*')):
        if f.suffix not in ('.py', '.sh', '.slurm') or '__pycache__' in f.parts or f.name in SKIP_FILES or f.parent.name == 'fulltext-push' and f.parent.parent.name == 'fulltext-push':
            continue
        for n, line in enumerate(f.read_text(errors='replace').splitlines(), 1):
            t = line.strip()
            if t.startswith(('#', '"""', "'''")):
                continue
            if 'local-reuse' in f.parts and f.suffix == '.py' and LR.search(line) and 'FT_' not in line:
                out.append((f, n, t))
            elif f.suffix == '.py' and PY.search(line) and 'FT_' not in line and 'ft_review' not in line:
                out.append((f, n, t))
            elif f.suffix in ('.sh', '.slurm') and SH.search(line) and 'CS_ATLAS_FT_' not in line and not t.startswith('#SBATCH'):
                out.append((f, n, t))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=str(Path(__file__).resolve().parents[1] / 'fulltext-push'))
    a = ap.parse_args(argv)
    hits = scan(a.root)
    for f, n, t in hits:
        print(f'{Path(f).relative_to(a.root)}:{n}: {t[:150]}')
    code = Path(a.root).parent
    outside = scan_outside(code)
    for f, n, t in outside:
        print(f'{Path(f).relative_to(code)}:{n}: {t[:150]}')
    hits += outside
    print(f'{len(hits)} hand-joined data paths in {len({h[0] for h in hits})} files')
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main())
