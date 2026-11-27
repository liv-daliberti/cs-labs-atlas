"""Per-school paths written by hand in live code (2026-11-26, SCHOOL-LAYOUT-PLAN.md): every read or write of a school's data goes through
tools/atlas_paths.py (data()/data_w(), store(), checks_db(), school_dir(), ai_dir(); shell: paths.sh variables), so the per-school move
is a flip of the placement and needs no compatibility links.

scan(repo)   [(path, line number, text)] for the code lines (comments and docstrings are skipped; a line carrying `route-ok` is accepted)
             of tracked .py/.sh/.slurm/.sbatch files that join a per-school path by hand: hierarchy/<school>/, stores/<school>,
             fulltext-push/checks, listings/<school>, captures/<school>, HIERARCHY/LISTINGS/CENSUS/PERIODS slot joins, absolute paths.
usage: route_school_paths.py [--all] [--root DIR]   prints the hits; exit 1 when any is outside ALLOW_PREFIXES (--all: also the allowed ones)
"""
import argparse
import ast
import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _school_keys():
    return {f.stem for f in (REPO / 'schools').glob('*.toml') if f.stem != 'TEMPLATE'} | {'princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford'}


RX = [
    re.compile(r'hierarchy/(\{school\}|\{s\}|\{key\}|<school>|<s>|\$\{?[A-Za-z_]*[sS]chool[A-Za-z_]*\}?|\$\{?s\}?|\$1|%s)/'),
    re.compile(r'listings/(\{school\}|\{s\}|\{key\}|<school>|<s>|\$\{?[A-Za-z_]*[sS]chool\}?|\$\{?s\}?|%s)\b'),
    re.compile(r'stores?/(\{school\}|\{s\}|<school>|<s>|\$\{?[A-Za-z_]*[sS]chool\}?|\$\{?s\}?)|\bSTORES\s*/|STANFORD_STORE|CS_ATLAS_STORES'),
    re.compile(r'FT_CHECKS|fulltext-push/checks|CS_ATLAS_FT_CHECKS'),
    re.compile(r'captures/(\{school\}|\{s\}|<school>|\$\{?s\}?)|\bCAPTURES\s*/'),
    re.compile(r'\b(HIERARCHY|LISTINGS|CENSUS|PERIODS)\s*/\s*[A-Za-z_(\'"]'),
    re.compile(r'/n/fs/resemble/homogenizing-science/(code/)?(hierarchy|listings|stores|schools|census|periods|captures)/'),
]
RX_CODE = [   # not applied to tests/ (fixtures build their own trees; tests/test_tests_use_atlas_paths.py polices those)
    re.compile(r'\b(HIERARCHY|LISTINGS|CENSUS|PERIODS|CAPTURES|STORES)\)\s*/\s*[A-Za-z_(\'"]'),
    re.compile(r'\{(?:P|AP)\.(HIERARCHY|LISTINGS|CENSUS|PERIODS|CAPTURES|STORES)\}\s*/\s*\{'),
    re.compile(r'\b(?:P|AP|atlas_paths)\.(STORES|CAPTURES|FT_CHECKS|LISTINGS|CENSUS|PERIODS|SCHOOLS_TREE|STANFORD_STORE)\b'),
    # a school's non-reviewed parts (reviewed/ stays in git at hierarchy/<school>/reviewed in every placement): string and Path-join spellings,
    # with a placeholder or a literal school key
    re.compile(r'hierarchy/[A-Za-z0-9_{}$<>%\[\]\'"() .-]+?/(raw|derived|work|reports|tmp)\b'),
    re.compile(r'[\'"]hierarchy[\'"]\s*/\s*[A-Za-z_][A-Za-z_0-9.()]*\s*/\s*[\'"](raw|derived|work|reports|tmp)\b'),
    re.compile(r'[\'"]hierarchy[\'"]\s*/\s*[A-Za-z_][A-Za-z_0-9.()\[\]]*\s*(\)|$|,|\]|\})'),
    re.compile(r'[\'"]hierarchy[\'"]\s*/\s*[A-Za-z_][A-Za-z_0-9.()\[\]]*\s*/\s*(?=\S)(?![\'"]reviewed[\'"/])'),
    re.compile(r'hierarchy/(?:%s)(?:[\'"]|/(?!reviewed\b|STAGE|PROVENANCE|REQUESTS))' % '|'.join(sorted(_school_keys()))),
]
SUFFIXES = ('.py', '.sh', '.slurm', '.sbatch')
# Not scanned: frozen history, docs, the placement code itself. fulltext-push/, ai-writing/ and the lab-page tool kits are a second pass
# (their owners' live sessions hold them): listed so the guard still blocks every NEW file and every other directory.
ALWAYS = ('vendor/', 'archive/', 'docs/', 'tools/atlas_paths.py', 'tools/relocate_schools.py', 'tools/relocate_project.py', 'tools/relocate_data.py',
          'tools/route_paths.py', 'tools/route_ft_data.py', 'tools/route_school_paths.py', 'tools/vendor_sync.py', 'paths.sh',
          'tests/test_relocate_schools.py', 'tests/test_atlas_paths_school_layout.py', 'tests/test_relocate_data.py',
          'tests/test_relocate_project.py', 'tests/test_atlas_paths.py', 'tests/test_route_school_paths.py')
ALLOW_PREFIXES = ALWAYS + ('fulltext-push/', 'ai-writing/', 'hierarchy/labpage-tools-')


def _doc_lines(src):
    """Line numbers inside docstrings (module, class, function)."""
    out = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                out.update(range(first.lineno, first.end_lineno + 1))
    return out


def _py_code_lines(src):
    """{line number: code text without comments} for the lines of a Python file outside docstrings."""
    skip = _doc_lines(src)
    lines = src.splitlines()
    res = {}
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError):
        return {n: t for n, t in enumerate(lines, 1) if n not in skip and not t.lstrip().startswith('#')}
    comment_at = {t.start[0]: t.start[1] for t in toks if t.type == tokenize.COMMENT}
    for n, t in enumerate(lines, 1):
        if n in skip:
            continue
        res[n] = t[:comment_at[n]] if n in comment_at else t
    return res


def _sh_code_lines(src):
    res = {}
    for n, t in enumerate(src.splitlines(), 1):
        if t.lstrip().startswith('#') and not t.startswith('#SBATCH'):
            continue
        res[n] = re.sub(r'\s#\s.*$', '', t)
    return res


def scan_text(path, src):
    code = _py_code_lines(src) if path.endswith('.py') else _sh_code_lines(src)
    raw = src.splitlines()
    rx = RX if path.startswith('tests/') else RX + RX_CODE
    return [(path, n, raw[n - 1].strip()) for n, t in sorted(code.items())
            if any(r.search(t) for r in rx) and 'route-ok' not in raw[n - 1]]


def tracked(repo):
    r = subprocess.run(['git', '-C', str(repo), 'ls-files', '-z'], stdout=subprocess.PIPE, check=True)
    return [p for p in r.stdout.decode().split('\0') if p.endswith(SUFFIXES)]


def scan(repo=REPO, allow=()):
    """All hits of tracked live code, except files under the `allow` prefixes."""
    out = []
    for p in tracked(repo):
        if p.startswith(allow):
            continue
        f = Path(repo) / p
        if f.is_file():
            out += scan_text(p, f.read_text(errors='replace'))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--all', action='store_true', help='also the second-pass directories (fulltext-push, ai-writing, lab-page kits)')
    ap.add_argument('--root', default=str(REPO))
    a = ap.parse_args(argv)
    hits = scan(a.root, ALWAYS if a.all else ALLOW_PREFIXES)
    for p, n, t in hits:
        print(f'{p}:{n}: {t[:200]}')
    print(f'{len(hits)} hits in {len({h[0] for h in hits})} files', file=sys.stderr)
    return 1 if hits else 0


if __name__ == '__main__':
    sys.exit(main())
