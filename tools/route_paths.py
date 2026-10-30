"""Find, and rewrite, absolute project paths written into code (2026-10-30): every location must come from
tools/atlas_paths.py (Python) or paths.sh (shell, Slurm), so that moving the project is "move the directories + flip
atlas_paths.LAYOUT_DEFAULT".

usage: route_paths.py check [FILE ...]   list hardcoded paths in tracked code (.py .sh .slurm); exit 1 if any.
                                         Comments and docstrings are reported as notes, not failures (relocate_project.py
                                         --rewrite-refs updates them at the move)
       route_paths.py fix FILE ...       rewrite them:
         Python  a string literal holding a project path becomes an expression on atlas_paths
                 ('/n/fs/.../work/hierarchy/x' -> str(P.HIERARCHY / 'x'); a path inside a longer or f-string -> f'{P.SLOT}/...'),
                 and `import atlas_paths as P` is added when the file has no handle on it yet
         shell   the path becomes ${CS_ATLAS_<SLOT>}/..., paths.sh is sourced relative to the script (Slurm: from the
                 submit directory, i.e. submit from the code root), #SBATCH --output/--error become code-relative
       Every rewrite is checked: the new expression must give the old path under today's layout.
Interpreters: the old Anaconda Python becomes COLLECTOR_PY in fulltext-push/ and PY elsewhere; the py310 env ENV_PY/ENV_LIB.
"""
import io, os, re, subprocess, sys, tokenize
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import atlas_paths as AP  # noqa: E402

REPO = HERE.parent
ANACONDA = '/usr/local/anaconda3/2024.02/bin/python'
# files that hold the legacy locations on purpose
ALLOW = {'tools/atlas_paths.py', 'tools/relocate_project.py', 'tools/route_paths.py', 'tools/vendor_sync.py',
         'tests/test_relocate_project.py', 'tests/test_atlas_paths.py', 'tests/test_route_paths.py', 'paths.sh'}
ALLOW_DIRS = ('vendor/', 'docs/')
SUFFIXES = ('.py', '.sh', '.slurm')
PATH_RX = re.compile(r"(?:/n/fs/resemble/(?:cs-atlas[a-z-]*|cs-labs-atlas|maxent-grpo|homogenizing-science)"
                     r"|/usr/local/anaconda3/2024\.02/bin/python)(?:/[A-Za-z0-9._%*-]*)*")
# old paths that are links to a slot (same files, other spelling): accepted although the text differs
EQUIV = ('/n/fs/resemble/cs-atlas/stores', '/n/fs/resemble/cs-atlas/env/')
_SKIP_SLOTS = {'ROOT', 'ARCHIVE', 'EXTERNAL', 'MIGRATIONS', 'SITE_HISTORY', 'ENV', 'PY', 'COLLECTOR_PY', 'WORK',
               'GITHUB_EXPORT', 'HOMOGENIZING'}


def slots():
    """(legacy absolute path, slot) longest first, from today's defaults (not the caller's overrides)."""
    d = AP._resolve({'CS_ATLAS_LAYOUT': 'legacy'})
    out = [(str(v), k) for k, v in d.items() if k not in _SKIP_SLOTS]
    out += [('/n/fs/resemble/cs-atlas/stores', 'STORES'), ('/n/fs/resemble/cs-atlas', 'ROOT_OLD'),
            ('/n/fs/resemble/cs-atlas/env/py310/bin/python', 'ENV_PY'), ('/n/fs/resemble/cs-atlas/env/py310/lib', 'ENV_LIB'),
            ('/n/fs/resemble/cs-atlas/env/hf-cache', 'HF_HOME'),
            (str(d['SITE_HISTORY']), 'SITE_HISTORY')]
    return sorted(out, key=lambda x: -len(x[0]))


def classify(path, rel_file):
    """(slot, rest) for an absolute path, or None. ROOT_OLD (the old cs-atlas root) has no slot: reported."""
    if path.startswith(ANACONDA):
        return ('COLLECTOR_PY' if rel_file.startswith('fulltext-push/') else 'PY'), path[len(ANACONDA):].lstrip('/')
    for base, slot in slots():
        if path == base or path.startswith(base + '/'):
            return slot, path[len(base):].lstrip('/')
    return None


def legacy_value(slot, rest):
    d = AP._resolve({'CS_ATLAS_LAYOUT': 'legacy'})
    base = ANACONDA if slot in ('PY', 'COLLECTOR_PY') else str(d[slot])
    return base + ('/' + rest if rest else '')


def tracked():
    out = subprocess.run(['git', '-C', str(REPO), 'ls-files'], capture_output=True, text=True, check=True).stdout.split()
    return [f for f in out if f.endswith(SUFFIXES) and f not in ALLOW and not f.startswith(ALLOW_DIRS)]


# ------------------------------------------------------------------------------------------------------------- Python
def _tokens(src):
    """tokenize, with each f-string as one STRING token (Python 3.12 splits it into FSTRING_START ... FSTRING_END)."""
    raw = list(tokenize.generate_tokens(io.StringIO(src).readline))
    start_t = getattr(tokenize, 'FSTRING_START', None)
    if start_t is None:
        return raw
    lines = src.splitlines(keepends=True)

    def text(a, b):
        if a[0] == b[0]:
            return lines[a[0] - 1][a[1]:b[1]]
        return lines[a[0] - 1][a[1]:] + ''.join(lines[a[0]:b[0] - 1]) + lines[b[0] - 1][:b[1]]
    out, i = [], 0
    while i < len(raw):
        t = raw[i]
        if t.type == start_t:
            depth, j = 0, i
            while True:
                if raw[j].type == start_t:
                    depth += 1
                elif raw[j].type == tokenize.FSTRING_END:
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            out.append(tokenize.TokenInfo(tokenize.STRING, text(t.start, raw[j].end), t.start, raw[j].end, t.line))
            i = j + 1
        else:
            out.append(t)
            i += 1
    return out


def _docstring_tokens(src):
    """Start positions of STRING tokens that are docstrings or bare expression strings."""
    toks = _tokens(src)
    doc = set()
    for i, t in enumerate(toks):
        if t.type != tokenize.STRING:
            continue
        j = i - 1
        while j >= 0 and toks[j].type in (tokenize.NL, tokenize.COMMENT):
            j -= 1
        k = i + 1
        while k < len(toks) and toks[k].type == tokenize.STRING:
            k += 1
        if (j < 0 or toks[j].type in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT)) and \
                toks[k].type in (tokenize.NEWLINE, tokenize.ENDMARKER):
            doc.add(t.start)
    return toks, doc


def _split_prefix(s):
    m = re.match(r'([rRbBuUfF]*)(\'\'\'|"""|\'|")', s)
    return m.group(1), m.group(2), s[len(m.group(0)):-len(m.group(2))]


def py_findings(src):
    toks, doc = _docstring_tokens(src)
    code, notes = [], []
    for t in toks:
        if t.type == tokenize.STRING:
            for m in PATH_RX.finditer(t.string):
                (notes if t.start in doc else code).append((t.start[0], m.group(0)))
        elif t.type == tokenize.COMMENT:
            for m in PATH_RX.finditer(t.string):
                notes.append((t.start[0], m.group(0)))
    return code, notes


def _handle(src):
    """The name this module reaches atlas_paths by, or None."""
    m = re.search(r'^\s*import atlas_paths as (\w+)', src, re.M)
    if m:
        return m.group(1)
    m = re.search(r'^import ftp_common as F\b', src, re.M)
    if m and not PATH_RX.search(src[:m.start()]):  # only when it is imported before the first path
        return 'F.P'
    return None


def _free_name(src):
    names = {t.string for t in tokenize.generate_tokens(io.StringIO(src).readline) if t.type == tokenize.NAME}
    for n in ('P', 'AP', '_AP'):
        if n not in names:
            return n
    raise SystemExit('no free name for atlas_paths')


def _import_block(rel, name):
    depth = len(Path(rel).parts) - 1
    return ('import sys as _sys  # noqa: E402\nfrom pathlib import Path as _Path  # noqa: E402\n'
            f"_sys.path.append(str(_Path(__file__).resolve().parents[{depth}] / 'tools'))  # atlas_paths: every path\n"
            f'import atlas_paths as {name}  # noqa: E402\n')


def _insert_at(src):
    """Line index after the module docstring and __future__ imports."""
    import ast
    tree = ast.parse(src)
    line = 0
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(getattr(node, 'value', None), ast.Constant) and \
                isinstance(node.value.value, str) and node is tree.body[0]:
            line = node.end_lineno
        elif isinstance(node, ast.ImportFrom) and node.module == '__future__':
            line = node.end_lineno
        else:
            break
    return line


def _expr(h, slot, rest):
    return f'{h}.{slot}' + (f" / {rest!r}" if rest else '')


def py_fix(rel, src):
    toks, doc = _docstring_tokens(src)
    h = _handle(src)
    need_import = h is None
    if need_import:
        h = _free_name(src)
    lines = src.splitlines(keepends=True)
    edits, unresolved = [], []
    sig = [t for t in toks if t.type not in (tokenize.NL, tokenize.COMMENT)]
    adjacent = set()
    for x, y in zip(sig, sig[1:]):
        if x.type == tokenize.STRING and y.type == tokenize.STRING:
            adjacent |= {x.start, y.start}
    for t in toks:
        if t.type != tokenize.STRING or t.start in doc or not PATH_RX.search(t.string):
            continue
        pre, q, body = _split_prefix(t.string)
        if 'b' in pre.lower():
            unresolved.append((t.start[0], 'bytes literal'))
            continue
        ms = list(PATH_RX.finditer(body))
        cls = [classify(m.group(0), rel) for m in ms]
        if any(c is None or c[0] == 'ROOT_OLD' for c in cls):
            unresolved.append((t.start[0], body[:120]))
            continue
        for m, (slot, rest) in zip(ms, cls):
            if '{' in rest or '$' in rest or '*' in rest:
                continue
            if legacy_value(slot, rest).rstrip('/') != m.group(0).rstrip('/') and not m.group(0).startswith(EQUIV):
                raise SystemExit(f'{rel}:{t.start[0]}: {m.group(0)} would not resolve the same')
        if len(ms) == 1 and ms[0].group(0) == body and 'f' not in pre.lower() and t.start not in adjacent and not body.endswith('/') and '{' not in body and \
                not any(c in cls[0][1] for c in '*$'):
            new = f'str({_expr(h, *cls[0])})'
        else:
            out, last = [], 0
            fbody = body
            if 'f' not in pre.lower():
                pieces = []
                for m in ms:
                    pieces.append(body[last:m.start()].replace('{', '{{').replace('}', '}}'))
                    pieces.append(m.group(0).replace('{', '{{').replace('}', '}}'))
                    last = m.end()
                pieces.append(body[last:].replace('{', '{{').replace('}', '}}'))
                fbody = ''.join(pieces)
            last = 0
            for m in PATH_RX.finditer(fbody):
                slot, rest = classify(m.group(0).replace('{{', '{').replace('}}', '}'), rel)
                base = legacy_value(slot, '')
                out.append(fbody[last:m.start()])
                out.append('{' + f'{h}.{slot}' + '}' + m.group(0)[len(base):])
                last = m.end()
            out.append(fbody[last:])
            new = ('f' + pre.replace('f', '').replace('F', '')) + q + ''.join(out) + q
        edits.append((t.start, t.end, new))
    for (sl, sc), (el, ec), new in sorted(edits, reverse=True):
        if sl != el:
            unresolved.append((sl, 'multi-line string: fix by hand'))
            continue
        ln = lines[sl - 1]
        lines[sl - 1] = ln[:sc] + new + ln[ec:]
    out = ''.join(lines)
    if edits and need_import and h != 'F.P':
        at = _insert_at(out)
        ls = out.splitlines(keepends=True)
        out = ''.join(ls[:at]) + ('\n' if at and not ls[at - 1].endswith('\n') else '') + _import_block(rel, h) + ''.join(ls[at:])
    return out, len(edits), unresolved


# -------------------------------------------------------------------------------------------------------------- shell
SOURCE_RX = re.compile(r'^\s*(?:\.|source)\s+["\']?(?:/n/fs/resemble/cs-atlas/work|\$CS_ATLAS_WORK|\$CS_ATLAS_CODE)/paths\.sh["\']?.*$', re.M)
SBATCH_IO = re.compile(r'^(#SBATCH\s+--(?:output|error)=)/n/fs/resemble/cs-atlas/work/', re.M)


def _source_line(rel):
    if rel.endswith('.slurm'):
        return ('. "${CS_ATLAS_CODE:-${SLURM_SUBMIT_DIR:?}}/paths.sh" || exit 1  '
                '# every path in one place (tools/atlas_paths.py); submit from the code root')
    up = '/'.join(['..'] * (len(Path(rel).parts) - 1)) or '.'
    return (f'. "$(cd "$(dirname "${{BASH_SOURCE[0]}}")/{up}" && pwd)/paths.sh" || exit 1  '
            '# every path in one place (tools/atlas_paths.py)')


def sh_fix(rel, src):
    out = SBATCH_IO.sub(r'\1', src)
    had_source = bool(SOURCE_RX.search(out))
    out = SOURCE_RX.sub(lambda m: _source_line(rel), out)
    unresolved, n = [], 0
    res = []
    for i, line in enumerate(out.splitlines(keepends=True), 1):
        if line.lstrip().startswith('#') and not line.startswith('#!'):
            res.append(line)
            continue
        new, last = [], 0
        for m in PATH_RX.finditer(line):
            c = classify(m.group(0), rel)
            if c is None or c[0] == 'ROOT_OLD' or line[:m.start()].count("'") % 2:
                unresolved.append((i, line.strip()[:120]))
                continue
            slot, rest = c
            new.append(line[last:m.start()] + '${CS_ATLAS_' + slot + '}' + ('/' + rest if rest else ''))
            last = m.end(); n += 1
        new.append(line[last:])
        res.append(''.join(new))
    out = ''.join(res)
    if (n or had_source) and not SOURCE_RX.search(out) and 'paths.sh' not in out:
        ls = out.splitlines(keepends=True)
        at = 0
        while at < len(ls) and (ls[at].startswith('#') or not ls[at].strip() or ls[at].startswith('set ')):
            at += 1
        out = ''.join(ls[:at]) + _source_line(rel) + '\n' + ''.join(ls[at:])
    return out, n, unresolved


def check(files):
    bad = 0
    for rel in files:
        src = (REPO / rel).read_text(errors='replace')
        if rel.endswith('.py'):
            try:
                code, notes = py_findings(src)
            except (tokenize.TokenError, SyntaxError, IndentationError):
                code, notes = [(0, 'unparseable')], []
        else:
            code, notes = [], []
            for i, line in enumerate(src.splitlines(), 1):
                for m in PATH_RX.finditer(line):
                    (notes if line.lstrip().startswith('#') and not line.startswith('#!') else code).append((i, m.group(0)))
        for ln, p in code:
            print(f'HARDCODED {rel}:{ln}: {p}'); bad += 1
        for ln, p in notes:
            print(f'note      {rel}:{ln}: {p} (comment/docstring)')
    print(f'route_paths check: {len(files)} files, {bad} hardcoded paths in code')
    return 1 if bad else 0


def fix(files):
    total = 0
    for rel in files:
        p = REPO / rel
        src = p.read_text()
        out, n, unresolved = (py_fix if rel.endswith('.py') else sh_fix)(rel, src)
        if rel.endswith('.py') and out != src:
            compile(out, rel, 'exec')
        if out != src:
            p.write_text(out); total += n
            if os.access(p, os.X_OK) is False and src.startswith('#!'):
                pass
        for ln, what in unresolved:
            print(f'UNRESOLVED {rel}:{ln}: {what}')
        if n:
            print(f'fixed {rel}: {n}')
    print(f'route_paths fix: {total} rewrites')
    return 0


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ('check', 'fix'):
        print(__doc__); return 2
    files = a[1:] or tracked()
    return check(files) if a[0] == 'check' else fix(files)


if __name__ == '__main__':
    sys.exit(main())
