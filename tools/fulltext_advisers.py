"""Adviser statements in full text we already hold (no crawling): thesis front matter, acknowledgements, author footnotes.

scan   <school> --shard K --shards N [--out DIR]   restartable: reads the store catalog (never walks the PDF tree), extracts the
        first MAX_PAGES pages of each in-scope copy with pdftotext (JATS xml: tags stripped), and records every explicit adviser
        statement as a candidate hit in DIR/<school>-<K>of<N>.sqlite (table hits; table done lists the finished work ids, so a
        restarted job skips them).
scope: a copy is read when it is a thesis candidate (>= THESIS_PAGES pages), has a single-author byline, or the school is a
        priority school (every copy: page-1 footnotes). Everything else is not opened.
patterns (kind): front  'Thesis Supervisor: X', 'Advisor: X', 'Committee Chair: X', 'Dissertation Director: X'  (first FRONT_PAGES pages)
                 ack    'my (PhD) advisor X', 'X, my advisor', 'advised by X', 'under the supervision of X'
Only explicit adviser words count; 'thank X for discussions' never matches. The builder (fulltext_advisers_build.py) maps hits to
students/PIs and applies R-STU-03/R-STU-14.
"""
import argparse
import gzip
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

MAX_PAGES = 40
FRONT_PAGES = 8
THESIS_PAGES = 40
PRIORITY = {'gatech', 'michigan', 'uchicago', 'harvard', 'jhu', 'washu'}
CTX = 260

_N = r"[A-Z][^\W\d_]+(?:[’'\-][A-Z]?[^\W\d_]+)*\.?"
NAME = rf"(?:(?:Prof(?:essor)?|Dr)\.?[ \t]+)?{_N}(?:[ \t]+(?:[A-Z]\.|van|von|de|der|di|da|del|bin|ibn|al|el|{_N})){{1,3}}"
ROLE_PRE = r"(?:(?:Ph\.?[ \t]?D\.?|doctoral|graduate|thesis|research|academic|master[’']?s|main|primary|principal|dissertation|co-?|former|first)[ \t-]+)*"
ADV = r"(?:advis[eo]r|supervisor)"
FRONT_RX = [
    ('front', re.compile(rf"Thesis[ \t]+(?:Supervisor|Advis[eo]r)s?[ \t]*[:\-–][ \t]*({NAME})")),
    ('front', re.compile(rf"(?:Research|Dissertation|Doctoral|Ph\.?D\.?|Academic|Graduate)?[ \t]*(?:Advis[eo]r|Supervisor|Director)s?[ \t]*:[ \t]*({NAME})")),
    ('front', re.compile(rf"Committee[ \t]+Chair[ \t]*:?[ \t]*({NAME})")),
    ('front', re.compile(rf"Dissertation[ \t]+Director[ \t]*:?[ \t]*({NAME})")),
    ('front', re.compile(rf"(?:Certified|Supervised)[ \t]+by[ \t]*:?[ \t]*({NAME})[ \t,\n]+Thesis[ \t]+Supervisor")),
]
ACK_RX = [
    ('ack_my', re.compile(rf"\b(?:[Mm]y|[Oo]ur)[ \t]+{ROLE_PRE}{ADV}s?[ \t]*,?[ \t]*(?:is[ \t]+)?({NAME})")),
    ('ack_my2', re.compile(rf"({NAME})[ \t]*,?[ \t]*(?:who[ \t]+(?:is|was)[ \t]+|is[ \t]+|was[ \t]+)?(?:my|our)[ \t]+{ROLE_PRE}{ADV}\b")),
    ('advised_by', re.compile(rf"\b(?:co-?)?(?:advised|supervised)[ \t]+by[ \t]+({NAME})")),
    ('under_sup', re.compile(rf"under[ \t]+the[ \t]+(?:supervision|guidance|direction|advisement)[ \t]+of[ \t]+({NAME})")),
]
WS = re.compile(r'\s+')


def flat(t):
    return WS.sub(' ', t.replace('\x0c', ' ')).strip()


def read_pdf(path, last):
    try:
        r = subprocess.run(['pdftotext', '-f', '1', '-l', str(last), '-layout', '-q', str(path), '-'],
                           capture_output=True, timeout=90)
    except (subprocess.TimeoutExpired, OSError):
        return None
    return r.stdout.decode('utf8', 'replace') if r.returncode == 0 else None


def read_xml(path):
    raw = Path(path).read_bytes().decode('utf8', 'replace')
    return re.sub(r'<[^>]+>', ' ', raw)


def hits_in(text):
    """-> [(kind, adviser_raw, quote)] for the explicit patterns; the front patterns only look at the first FRONT_PAGES pages."""
    pages = text.split('\x0c')
    front = '\n'.join(pages[:FRONT_PAGES])
    out = []
    for kind, rx in FRONT_RX:
        for m in rx.finditer(front):
            a, b = max(0, m.start() - 80), min(len(front), m.end() + 80)
            out.append((kind, m.group(1).strip(), flat(front[a:b])))
    ft = flat(text)
    for kind, rx in ACK_RX:
        for m in rx.finditer(ft):
            a, b = max(0, m.start() - CTX), min(len(ft), m.end() + CTX)
            out.append((kind, m.group(1).strip(), ft[a:b]))
    return out


def lab_bylines(school):
    """open-alex id -> byline (list), from the school's lab_papers package."""
    f = P.data('lab_papers.jsonl.gz', school)
    by = {}
    if f.exists():
        with gzip.open(f, 'rt') as fh:
            for ln in fh:
                r = json.loads(ln)
                if r.get('oa') and r.get('byline'):
                    by[r['oa'].rsplit('/', 1)[-1]] = r['byline']
    return by


def scan(school, shard, shards, outdir, limit=0):
    store = P.store(school)
    cat = sqlite3.connect(f'file:{store}/catalog.sqlite?mode=ro', uri=True)
    by = lab_bylines(school)
    out = Path(outdir) / f'{school}-{shard}of{shards}.sqlite'
    out.parent.mkdir(parents=True, exist_ok=True)
    o = sqlite3.connect(out, timeout=60)
    o.executescript('create table if not exists hits(work_id, school, year, kind, adviser, quote, byline, pages, sha256, path, doi, url);'
                    'create table if not exists done(work_id primary key, status);')
    done = {r[0] for r in o.execute('select work_id from done')}
    rows = cat.execute("select id, year, file_path, pages, sha256, doi, download_url, graph_json from works where status='downloaded' and file_path is not null order by id").fetchall()
    n = 0
    t0 = time.time()
    for wid, year, fp, pages, sha, doi, url, gj in rows:
        if int(hashlib.md5(wid.encode()).hexdigest(), 16) % shards != shard or wid in done:
            continue
        g = json.loads(gj or '{}')
        key = (g.get('openalex') or '').rsplit('/', 1)[-1]
        byline = by.get(key) or []
        thesis = (pages or 0) >= THESIS_PAGES
        if not (school in PRIORITY or thesis or len(byline) == 1):
            continue
        path = store / fp
        if not path.exists():
            o.execute('insert or replace into done values(?,?)', (wid, 'missing'))
            continue
        text = read_xml(path) if fp.endswith('.xml') else read_pdf(path, MAX_PAGES)
        if text is None:
            o.execute('insert or replace into done values(?,?)', (wid, 'unreadable'))
        else:
            for kind, adv, quote in hits_in(text):
                o.execute('insert into hits values(?,?,?,?,?,?,?,?,?,?,?,?)',
                          (wid, school, year, kind, adv, quote, json.dumps(byline), pages, sha, fp, doi, url))
            o.execute('insert or replace into done values(?,?)', (wid, 'ok'))
        n += 1
        if n % 200 == 0:
            o.commit()
            print(school, shard, n, f'{time.time() - t0:.0f}s', flush=True)
        if limit and n >= limit:
            break
    o.commit()
    print('done', school, shard, n, o.execute('select count(*) from hits').fetchone()[0], 'hits', flush=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['scan'])
    ap.add_argument('school')
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--shards', type=int, default=1)
    ap.add_argument('--out', required=True)
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    scan(a.school, a.shard, a.shards, a.out, a.limit)
