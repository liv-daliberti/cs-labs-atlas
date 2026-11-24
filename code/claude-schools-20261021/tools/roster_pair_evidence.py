"""Evidence-confirmed UChicago roster pairs -> hierarchy/uchicago/reviewed/roster-evidence.json (R-STU-18, owner 2026-11-04).

Reads the 41 `true` pairs of reviewed/roster-pair-verdicts.json and, for each cited page, finds the stored capture (the roster deep dive's
roster-dive-captures.sqlite or the lab-page audit's labpage-audit-captures.sqlite) whose text names the student, then writes a researched-evidence row
(thesis-evidence shape: pi, students[name, role, years, url, capture_url, sha256, quote, note]) with a VERBATIM quote cut from that capture and the sha256 of
its bytes. `unsettled` and `not` pairs are never read. A pair whose page text does not name the student is listed and left out, never guessed.

  python3 tools/roster_pair_evidence.py            # rewrite roster-evidence.json
"""
import html
import json
import re
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

WT = Path(__file__).resolve().parent.parent
VERDICTS = WT / 'hierarchy' / 'uchicago' / 'reviewed' / 'roster-pair-verdicts.json'
OUT = WT / 'hierarchy' / 'uchicago' / 'reviewed' / 'roster-evidence.json'
RAW = Path(P.HIERARCHY) / 'uchicago' / 'raw'
DBS = ['roster-dive-captures.sqlite', 'labpage-audit-captures.sqlite']
ALIASES = {'Rong Jiang': ['Hugh (Rong) Jiang', 'Rong) Jiang'], 'Suzanna Parkinson': ['Sue Parkinson']}  # the verdict file's own alias notes

# Years: the roster years, narrowed where the cited page gives an earlier graduation (owner 2026-11-04). (pi, student) -> (end year, the text that must sit in the
# quote). A page date never extends the roster years, and every PI here is listed through 2026, so the years stay inside the appointment.
PAGE_END = {('Daniel Sanz-Alonso', 'Ruiyi Yang'): (2022, 'graduated Spring 2022'), ('Daniel Sanz-Alonso', 'Yuming Chen'): (2023, 'graduated Spring 2023'),
            ('Daniel Sanz-Alonso', 'Hwanwoo Kim'): (2024, 'graduated Spring 2024'),
            ('Lek-Heng Lim', 'Zehua Lai'): (2023, '2018–2023'), ('Lek-Heng Lim', 'Zhen Dai'): (2023, '2018–2023')}


def fold(s):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode())


def to_text(raw, ctype):
    if raw[:4] == b'%PDF':
        with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
            f.write(raw); f.flush()
            return subprocess.run(['pdftotext', '-layout', f.name, '-'], capture_output=True, text=True, timeout=60).stdout
    t = raw.decode('utf-16', 'replace') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') or raw[1:2] == b'\x00' else raw.decode('utf-8', 'replace')
    t = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', t)
    return html.unescape(re.sub(r'<[^>]+>', ' ', t))


def captures(url):
    """(capture_url, sha256, text) of every stored 200 capture of the page, newest first."""
    out = []
    for db in DBS:
        c = sqlite3.connect(f'file:{RAW / db}?mode=ro', uri=True)
        for cu, sha, blob, ct in c.execute('select capture_url, sha256, content, content_type from captures where url=? and status=200 and content is not null order by id desc', (url,)):
            try:
                raw = zlib.decompress(blob)
            except zlib.error:
                raw = blob
            out.append((cu or url, sha, to_text(raw, ct)))
    return out


def window(text, names):
    """A verbatim snippet of the page text around the first occurrence of one of the names (case-insensitive on the folded text)."""
    t = re.sub(r'\s+([.,;:)])', r'\1', re.sub(r'\s+', ' ', text))
    for nm in names:
        m = re.search(re.escape(fold(nm)), fold(t), re.I)
        if m and len(fold(t)) == len(t):
            return t[max(0, m.start() - 70): m.end() + 110].strip()
        m = re.search(re.escape(nm), t, re.I)
        if m:
            return t[max(0, m.start() - 70): m.end() + 110].strip()
    return None


def build(d=None, get_captures=None):
    d = d or json.load(open(VERDICTS))
    get_captures = get_captures or captures
    by_pi, miss, cache = {}, [], {}
    for p in d['pairs']:
        if p['verdict'] != 'true':
            continue
        names = [p['student']] + ALIASES.get(p['student'], [])
        found = None
        for s in p['sources']:
            caps = cache.setdefault(s['url'], get_captures(s['url']))
            for cu, sha, text in caps:
                q = window(text, [g for g in [s['quote']] + s['quote'].split(' ... ') if 30 <= len(g) < 200 and (g == s['quote'] or any(fold(n).lower() in fold(g).lower() for n in names + [p['pi'].split()[-1]]))] + names)  # a person's own page may not repeat their name next to the statement
                if q and sha:
                    found = dict(url=s['url'], capture_url=cu, sha256=sha, quote=q, note=f"roster pair verdict {p['basis']}: {p['note']}".strip(': '))
                    break
            if found:
                break
        if not found:
            miss.append((p['student'], p['pi']))
            continue
        y0, y1 = min(p['roster_years']), max(p['roster_years'])
        if (p['pi'], p['student']) in PAGE_END:
            end, token = PAGE_END[(p['pi'], p['student'])]
            assert token in found['quote'], (p['student'], token)
            y1 = min(y1, end); y0 = min(y0, y1)
            found['note'] += f'; years end at {end}: page says {token!r}'
        row = dict(name=p['student'], role='phd', years=[y0, y1], **found)
        by_pi.setdefault(p['pi'], []).append(row)
    out = [dict(pi=pi, students=sorted(rows, key=lambda r: r['name']), notes='Evidence-confirmed Statistics and CAM roster pairs (roster-pair-verdicts.json verdict true), quote cut from the stored capture.')
           for pi, rows in sorted(by_pi.items())]
    return out, miss


if __name__ == '__main__':
    out, miss = build()
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')
    print(sum(len(o['students']) for o in out), 'pairs written;', 'missing:', miss)
