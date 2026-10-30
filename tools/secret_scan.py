"""Scan files for secrets before they are committed or exported. Prints only the file, line and kind of a finding,
never the matched value.

Looks for
  env values   every value in ~/.config/cs-atlas/*.env (API keys, tokens), compared as plain substrings
  token shapes Hugging Face (hf_...), OpenAI-style (sk-...), GitHub (ghp_/gho_/ghs_...), AWS access keys (AKIA...)
  emails       any email-like string whose sha256 (lower-cased) is listed in ~/.config/cs-atlas/scan-hashes.txt or
               given with --hash (the owner's address is checked by hash so the scanner never holds it)

  hashes       a listed hash itself written out in a file (hex, any case)

usage: secret_scan.py --staged [--repo DIR]      the files staged in a git repository
       secret_scan.py --history [REV-RANGE]      every blob of every commit (default: all refs), each blob once;
                                                 REV-RANGE such as origin/dev..HEAD scans what a push would add
       secret_scan.py PATH [PATH ...]            files or directories (directories are walked)
Exit status 1 when anything is found.
"""
import argparse, hashlib, os, re, subprocess, sys
from pathlib import Path

CONF = Path(os.environ.get('CS_ATLAS_CONFIG', Path.home() / '.config/cs-atlas'))
TOKEN = re.compile(rb'\b(?:hf_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_\-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16})\b')
EMAIL = re.compile(rb'[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+')


def env_values():
    vals = []
    for f in sorted(CONF.glob('*.env')) if CONF.is_dir() else []:
        for line in f.read_text(errors='ignore').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            v = line.split('=', 1)[1].strip().strip('"').strip("'")
            if len(v) >= 12:  # short values (flags, numbers) are not secrets and would match everywhere
                vals.append((f.name, v.encode()))
    return vals


def hashes(extra):
    out = set(h.lower() for h in extra)
    f = CONF / 'scan-hashes.txt'
    if f.exists():
        out |= {l.split()[0].lower() for l in f.read_text().splitlines() if l.strip() and not l.startswith('#')}
    return out


def scan_bytes(name, data, vals, hs):
    found = []
    for src, v in vals:
        if v in data:
            found.append((name, data[:data.index(v)].count(b'\n') + 1, f'value from {src}'))
    for m in TOKEN.finditer(data):
        found.append((name, data[:m.start()].count(b'\n') + 1, 'token-shaped string'))
    if hs:
        low = data.lower()
        for h in hs:
            if h.encode() in low:
                found.append((name, low[:low.index(h.encode())].count(b'\n') + 1, 'listed hash written out'))
        for m in EMAIL.finditer(data):
            if hashlib.sha256(m.group(0).lower()).hexdigest() in hs:
                found.append((name, data[:m.start()].count(b'\n') + 1, 'listed email (by hash)'))
    return found


def staged(repo):
    names = subprocess.run(['git', '-C', str(repo), 'diff', '--cached', '--name-only', '-z', '--diff-filter=ACMR'],
                           check=True, capture_output=True).stdout.split(b'\0')
    for n in filter(None, names):
        blob = subprocess.run(['git', '-C', str(repo), 'show', b':' + n], check=True, capture_output=True).stdout
        yield n.decode(), blob


def history(repo, rev_range=None):
    """(name, bytes) for every distinct blob reachable in the range (all refs by default), named commit:path#blob."""
    revs = [rev_range] if rev_range else ['--all']
    log = subprocess.run(['git', '-C', str(repo), 'log', '--format=C %h', '--raw', '--no-abbrev', '--no-renames', '-m',
                          '--diff-filter=AM', *revs], check=True, capture_output=True, text=True).stdout
    seen, todo, commit = set(), [], ''
    for line in log.splitlines():
        if line.startswith('C '):
            commit = line[2:]
        elif line.startswith(':'):
            meta, path = line.split('\t', 1)
            blob = meta.split()[3]
            if blob not in seen and set(blob) != {'0'}:
                seen.add(blob); todo.append((blob, f'{commit}:{path}#{blob}'))
    # the root commits' files appear as additions above; one cat-file process for every blob
    p = subprocess.Popen(['git', '-C', str(repo), 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for blob, name in todo:
        p.stdin.write(blob.encode() + b'\n'); p.stdin.flush()
        header = p.stdout.readline().split()
        size = int(header[2])
        data = p.stdout.read(size); p.stdout.read(1)
        yield name, data
    p.stdin.close(); p.wait()


ALLOW = Path(__file__).resolve().with_name('secret_scan_allow.tsv')


def allowed():
    """{(blob id, kind)}: findings in OLD blobs that were reviewed and accepted (tools/secret_scan_allow.tsv). Scoped to
    exact blob ids, so the same text in any new or changed file is still a finding."""
    if not ALLOW.exists():
        return set()
    rows = [l.split('\t') for l in ALLOW.read_text().splitlines() if l.strip() and not l.startswith('#')]
    return {(r[0], r[1]) for r in rows}


def split_accepted(found, ok):
    """(findings, accepted): a finding is accepted only in a history blob (name ...#<blob>) listed with its kind."""
    acc = [f for f in found if '#' in f[0] and (f[0].rsplit('#', 1)[1], f[2]) in ok]
    return [f for f in found if f not in acc], acc


def walk(paths):
    for p in map(Path, paths):
        files = [p] if p.is_file() else sorted(q for q in p.rglob('*') if q.is_file() and '.git' not in q.parts)
        for f in files:
            yield str(f), f.read_bytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='*')
    ap.add_argument('--staged', action='store_true')
    ap.add_argument('--history', nargs='?', const='', default=None, metavar='REV-RANGE')
    ap.add_argument('--repo', default='.')
    ap.add_argument('--hash', action='append', default=[])
    a = ap.parse_args()
    vals, hs = env_values(), hashes(a.hash)
    found, n = [], 0
    src = staged(a.repo) if a.staged else history(a.repo, a.history or None) if a.history is not None else walk(a.paths)
    for name, data in src:
        n += 1
        found += scan_bytes(name, data, vals, hs)
    found, accepted = split_accepted(found, allowed())
    for f, line, kind in accepted:
        print(f'accepted {kind}: {f}:{line} (tools/secret_scan_allow.tsv)')
    for f, line, kind in found:
        print(f'FOUND {kind}: {f}:{line}')
    print(f'secret_scan: {n} files, {len(found)} findings, {len(accepted)} accepted old findings '
          f'({len(vals)} env values, {len(hs)} email hashes checked)')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
