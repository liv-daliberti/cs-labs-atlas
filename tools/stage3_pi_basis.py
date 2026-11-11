"""Stage-3 PI basis from a census PI's own dated listing sources (url + sha256 + verbatim quote), for the legacy schools whose census
carries `sources` but a `pi_basis` without evidence (Princeton 'owner_own_lab_census_20261021', MIT/Berkeley/CMU stragglers).

rule      the PI's latest listing source whose quote names the person with a professor title (not courtesy, affiliate, adjunct,
          visiting, emeritus, lecturer, research scientist, 'associated faculty', 'joining'/'appointment starts') is the basis;
          the source's url, sha256 and quote are copied verbatim; the prior pi_basis keys (kind, lab) stay.
          No such source -> the person is listed in the `unresolved` output for hand review (never guessed).
usage: stage3_pi_basis.py <key> [--apply]    --apply patches census-faculty.json / census-additions.json in place (sha256 backup in
          scratch/stage3-released-1110/backups/) and writes the decisions to the path in PI_BASIS_LOG
"""
import glob, hashlib, json, os, re, shutil, sqlite3, sys, zlib, gzip
from pathlib import Path

import atlas_paths as P  # noqa: E402

BAD = re.compile(r'courtesy|affiliate|adjunct|visiting|emerit|lecturer|research (?:scientist|scholar|investigator)|associated faculty|joining|appointment starts|arrives|postdoc', re.I)
PROF = re.compile(r'\bprofessor\b', re.I)


def norm(s):
    return re.sub(r'\s+', ' ', (s or '').lower())


def title_window(q, names):
    """The text that follows the person's name in the quote, cut at the next person/field marker: the title must sit right after the name."""
    t = re.sub(r'\s+', ' ', q)
    for n in names:
        parts = n.split()
        for m in re.finditer(re.escape(parts[-1]), t, re.I):
            w = t[m.end():m.end() + 90]
            # 'Last, First Title' puts the given name after the comma
            w = re.sub(r'^,?\s*(?:%s)\b\.?' % re.escape(parts[0]), '', w, flags=re.I)
            w = re.split(r'Read full bio|Email|E-mail|Phone|Office|@|\|', w)[0]
            if PROF.search(w) and not BAD.search(w):
                return w
    return None


def pick(x):
    names = [norm(n) for n in [x['name']] + list(x.get('aliases') or [])]
    best = None
    for s in x.get('sources') or []:
        q = s.get('quote') or ''
        if not (s.get('url') and s.get('sha256') and q):
            continue
        if not PROF.search(q) or BAD.search(q) or s.get('emeritus') or s.get('visiting'):
            continue
        if not title_window(q, names):
            continue
        if not any(n in norm(q) or (n.split()[0] in norm(q).split() and n.split()[-1] in norm(q).split()) for n in names):
            continue
        if best is None or str(s.get('observed') or '') >= str(best.get('observed') or ''):
            best = s
    return best


def capture_sha(key, url, quote):
    """sha256 of a stored capture of `url` whose text contains `quote` (whitespace-normalized); None if no capture verifies it."""
    want = norm(quote)
    for f in sorted(glob.glob(str(P.HIERARCHY / key / 'raw' / '*captures*.sqlite'))):
        try:
            c = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            rows = c.execute('select sha256, content from captures where status=200 and (url=? or final_url=? or capture_url=?)', (url, url, url)).fetchall()
        except sqlite3.Error:
            continue
        for sha, blob in rows:
            if not sha or blob is None:
                continue
            b = blob if isinstance(blob, bytes) else str(blob).encode()
            for dec in (lambda z: z, gzip.decompress, zlib.decompress):
                try:
                    t = dec(b).decode('utf-8', 'replace')
                except Exception:
                    continue
                t = re.sub(r'<[^>]+>', ' ', t)
                if want in norm(re.sub(r'&nbsp;|&#160;', ' ', t)) or all(w in norm(t) for w in want.split()[:12]) and False:
                    return sha
    return None


def pick_listed(x):
    """Hand-reviewed fallback: the latest listing source that names the person, whatever the title (staff, emeritus). The PI standing itself rests on the kind's own evidence."""
    names = [norm(n) for n in [x['name']] + list(x.get('aliases') or [])]
    best = None
    for s in x.get('sources') or []:
        q = s.get('quote') or ''
        if s.get('url') and s.get('sha256') and q and any(n in norm(q) or (n.split()[-1] in norm(q).split() and n.split()[0][:4] in norm(q)) for n in names) and (best is None or str(s.get('observed') or '') >= str(best.get('observed') or '')):
            best = s
    return best


def hand_names(key):
    for base in (Path(__file__).resolve().parents[1] / 'hierarchy' / key / 'reviewed', Path(P.HIERARCHY) / key / 'reviewed'):
        f = base / 'pi-basis-hand.json'
        if f.exists():
            return json.loads(f.read_text())
    return {}


def capture_text_sha(key, url):
    for f in sorted(glob.glob(str(P.HIERARCHY / key / 'raw' / '*captures*.sqlite'))):
        try:
            c = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            r = c.execute('select sha256, content from captures where status=200 and url=? limit 1', (url,)).fetchone()
        except sqlite3.Error:
            continue
        if r and r[1] is not None:
            b = r[1] if isinstance(r[1], bytes) else str(r[1]).encode()
            for dec in (zlib.decompress, gzip.decompress, lambda z: z):
                try:
                    t = dec(b).decode('utf-8', 'replace')
                except Exception:
                    continue
                return r[0], re.sub(r'&nbsp;|&#160;|&#8250;|&#xA0;', ' ', re.sub(r'<[^>]+>', ' ', t))
    return None, ''


def load(path):
    d = json.loads(Path(path).read_text())
    return d, (d['faculty'] if isinstance(d, dict) else d)


def main(key, apply=False):
    stats, unresolved, decisions = {}, [], []
    for fname in ('census-faculty.json', 'census-additions.json'):
        f = P.data(fname, key)
        if not f.exists():
            continue
        doc, rows = load(f)
        changed = 0
        for x in rows:
            b = x.get('pi_basis') or {}
            if (not x.get('is_pi') and x['name'] not in (hand_names(key).get('restore_pi') or {})) or (b.get('url') and x.get('is_pi') and b.get('sha256') and b.get('quote') and x['name'] not in (hand_names(key).get('not_pi') or {})):
                continue
            if b.get('url') and b.get('quote') and not b.get('sha256'):
                sha = capture_sha(key, b['url'], b['quote'])
                if sha:
                    x['pi_basis'] = dict(b, sha256=sha, basis_note='sha256 of the stored capture of the basis url that contains the quote (stage3_pi_basis.py)')
                    decisions.append(dict(name=x['name'], url=b['url'], sha256=sha, quote=b['quote'], via='capture'))
                    changed += 1
                    continue
            hand = hand_names(key)
            nip = (hand.get('not_pi') or {}).get(x['name'])
            if nip:   # reviewed exclusion: the row stays in the census, is_pi false with the reason (never silent; sampled by a fresh reviewer)
                x['is_pi'] = False
                x['not_pi_reason'] = nip['reason']
                x['stage3_exclusion'] = dict(nip, reviewed_by='claude-stage3-released-1110', reviewed_on='2026-11-10')
                decisions.append(dict(name=x['name'], not_pi=nip))
                changed += 1
                continue
            if x['name'] in (hand.get('restore_pi') or {}):   # a reviewed reversal of an earlier exclusion
                x['is_pi'] = True
                x.pop('not_pi_reason', None); x.pop('stage3_exclusion', None)
                changed += 1
            kd = (hand.get('basis_from_source_kind') or {}).get(x['name'])
            if kd and not (b.get('url') and b.get('sha256') and b.get('quote')):
                cands = [t for t in x.get('sources') or [] if kd in (t.get('kind') or '') and t.get('url') and t.get('sha256') and t.get('quote')]
                if cands:
                    t = max(cands, key=lambda q: str(q.get('observed') or ''))
                    x['pi_basis'] = dict(b, url=t['url'], sha256=t['sha256'], quote=t['quote'], observed=t.get('observed'), basis_note=f'latest {kd} listing source (reviewed choice)')
                    decisions.append(dict(name=x['name'], url=t['url'], sha256=t['sha256'], quote=t['quote'], via='source_kind'))
                    changed += 1
                    continue
            ex = (hand.get('explicit') or {}).get(x['name'])
            if ex:
                sha, txt = capture_text_sha(key, ex['url'])
                if sha and norm(ex['quote']) in norm(txt):
                    x['pi_basis'] = dict(b, url=ex['url'], sha256=sha, quote=ex['quote'], basis_note='reviewed explicit basis: quote verified in the stored capture (stage3_pi_basis.py)')
                    decisions.append(dict(name=x['name'], url=ex['url'], sha256=sha, quote=ex['quote'], via='explicit'))
                    changed += 1
                    continue
            s = pick(x)
            if not s and x['name'] in (hand.get('listed_title_any') or []):
                s = pick_listed(x)
            if not s:
                unresolved.append(dict(name=x['name'], file=fname, kind=b.get('kind'), titles=sorted({(t.get('quote') or '')[:90] for t in (x.get('sources') or [])})[-4:]))
                continue
            x['pi_basis'] = dict(b, url=s['url'], sha256=s['sha256'], quote=s['quote'], observed=s.get('observed'), basis_note='professor title on the latest dated listing source (stage3_pi_basis.py)')
            decisions.append(dict(name=x['name'], url=s['url'], sha256=s['sha256'], quote=s['quote'], observed=s.get('observed')))
            changed += 1
        stats[fname] = changed
        if apply and changed:
            bk = Path(os.environ['PI_BASIS_BACKUP_DIR']); bk.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256(f.read_bytes()).hexdigest()
            shutil.copy2(f, bk / f'{key}-{fname}.{h[:12]}.bak')
            f.write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    print(json.dumps(dict(school=key, patched=stats, unresolved=len(unresolved))))
    for u in unresolved:
        print('UNRESOLVED', json.dumps(u, ensure_ascii=False))
    if apply:
        Path(os.environ['PI_BASIS_LOG']).write_text(json.dumps(dict(school=key, decisions=decisions, unresolved=unresolved), indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1], '--apply' in sys.argv)
