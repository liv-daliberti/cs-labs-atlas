"""Scan files for secrets before they are committed or exported. Prints only the file, line and kind of a finding,
never the matched value.

Looks for
  env values   every value in ~/.config/cs-atlas/*.env (API keys, tokens), compared as plain substrings
  token shapes Hugging Face (hf_...), OpenAI-style (sk-...), GitHub (ghp_/gho_/ghs_...), AWS access keys (AKIA...)
  emails       any email-like string whose sha256 (lower-cased) is listed in ~/.config/cs-atlas/scan-hashes.txt or
               given with --hash (the owner's address is checked by hash so the scanner never holds it)

usage: secret_scan.py --staged [--repo DIR]      the files staged in a git repository
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


def walk(paths):
    for p in map(Path, paths):
        files = [p] if p.is_file() else sorted(q for q in p.rglob('*') if q.is_file() and '.git' not in q.parts)
        for f in files:
            yield str(f), f.read_bytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='*')
    ap.add_argument('--staged', action='store_true')
    ap.add_argument('--repo', default='.')
    ap.add_argument('--hash', action='append', default=[])
    a = ap.parse_args()
    vals, hs = env_values(), hashes(a.hash)
    found, n = [], 0
    for name, data in (staged(a.repo) if a.staged else walk(a.paths)):
        n += 1
        found += scan_bytes(name, data, vals, hs)
    for f, line, kind in found:
        print(f'FOUND {kind}: {f}:{line}')
    print(f'secret_scan: {n} files, {len(found)} findings ({len(vals)} env values, {len(hs)} email hashes checked)')
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
