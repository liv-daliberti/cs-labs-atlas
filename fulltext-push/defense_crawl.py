"""Georgia Tech PhD-defense announcements (Mercury, hg.gatech.edu) as an adviser-bearing student source (2026-11-07, owner: more GT students).

The Institute's event feed tags every announced PhD defense with the term 'Phd Defense' (https://hg.gatech.edu/taxonomy/term/100811, 15 events a page,
newest first). An event page carries the candidate's name in its title and the committee with the adviser marked ('Dr. Justin Romberg (Advisor)',
'Dr. Azad Naeemi, ECE, Chair, Advisor'). robots.txt of hg.gatech.edu: `User-agent: * / Disallow: /node/add/` (no Crawl-delay, no rule naming
ClaudeBot or anthropic-ai; read 2026-11-07 and again before every run). Pages are public HTML; nothing behind a login is read. One host, one flock,
generic User-Agent, no e-mail address, one request every 3 s.

  defense_crawl.py index [--kind defense|proposal] [--max-pages N]    the listing pages -> queue (url, listing date, title)
  defense_crawl.py crawl [--max N]           the event pages of the queue -> pages (sha256 of the bytes, the page's main text)
  defense_crawl.py stats

Store: raw/defense_crawl/hg.gatech.edu.sqlite (resumable). Evidence rows are cut from the stored text by tools/defense_students.py.
"""
import fcntl
import hashlib
import importlib.util
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

# Explicit sibling loading keeps the isolated entrypoint independent of sys.path.
_spec = importlib.util.spec_from_file_location('etd_crawl', Path(__file__).resolve().with_name('etd_crawl.py'))
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
import ftp_common as F  # noqa: E402
import oai_repo as O  # noqa: E402

HOST = 'hg.gatech.edu'
LISTINGS = {'defense': (f'https://{HOST}/taxonomy/term/100811', None, 0),
            # 'Other/Miscellaneous' holds the Ph.D. proposal oral exams (ECE, CS 'PhD Proposal by <name>'); only those titles are queued
            'proposal': (f'https://{HOST}/taxonomy/term/1788', re.compile(r'(?i)proposal'), 1_000_000)}
DELAY = 3.0
NODE_RX = re.compile(r'^/node/\d+$')
MAIN_RX = re.compile(r'Primary tabs\s*View\s*XML\s*JSON', re.I)


def db_path():
    return F.P.FT_RAW / 'defense_crawl' / f'{HOST}.sqlite'


def connect():
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(p), timeout=120)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS queue (url TEXT PRIMARY KEY, seq INTEGER, listed TEXT, title TEXT, status TEXT DEFAULT 'pending', at TEXT);
    CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, sha256 TEXT, fetched_at TEXT, title TEXT, text TEXT);
    CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT);
    """)
    return c


def listing_rows(html_bytes):
    """-> [(node path, title, listing date)] of one listing page."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_bytes, 'html.parser')
    rows = []
    for tr in soup.find_all('tr'):
        a = tr.find('a', href=NODE_RX)
        d = re.search(r'\b(20\d\d-\d\d-\d\d)\b', tr.get_text(' '))
        if a and d:
            rows.append((a['href'], re.sub(r'\s+', ' ', a.get_text(' ')).strip(), d.group(1)))
    return rows


def page_text(html_bytes):
    """-> (title, main text): the text after 'Primary tabs View XML JSON' to the page footer, whitespace collapsed."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_bytes, 'html.parser')
    for t in soup(['script', 'style', 'nav', 'header', 'footer', 'noscript']):
        t.decompose()
    h1 = soup.find('h1')
    title = re.sub(r'\s+', ' ', h1.get_text(' ')).strip() if h1 else ''
    txt = re.sub(r'\s+', ' ', soup.get_text(' ')).strip()
    m = MAIN_RX.search(txt)
    if m:
        txt = txt[m.end():].strip()
    txt = re.split(r'\bSubscribe to\b|\bLog in\b|Click here to LOG IN', txt)[0].strip()
    return title, txt[:8000]


def _open():
    conf = dict(host=HOST)
    client = O.Client(DELAY, low_priority=True)
    rp, cd = E.load_robots(HOST, client)
    client.delay = max(client.delay, float(cd or 0))
    return client, rp, conf


def index(max_pages=450, out=print, client=None, kind='defense'):
    listing, keep, seq_base = LISTINGS[kind]
    skey = 'index_next' if kind == 'defense' else f'index_next_{kind}'
    lockf = F.P.FT_RAW / 'defense_crawl' / f'{HOST}.lock'
    lockf.parent.mkdir(parents=True, exist_ok=True)
    with open(lockf, 'w') as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            out(json.dumps(dict(stop='another defense crawl is running')))
            return None
        client = client or O.Client(DELAY, low_priority=True)
        try:
            rp, cd = E.load_robots(HOST, client)
        except O.Blocked as e:
            out(json.dumps(dict(blocked=str(e))))
            return None
        client.delay = max(client.delay, float(cd or 0))
        c = connect()
        row = c.execute('SELECT v FROM state WHERE k=?', (skey,)).fetchone()
        page = int(row[0]) if row else 0
        n = 0
        while page < max_pages:
            url = listing + (f'?page={page}' if page else '')
            if not E.url_allowed(rp, url):
                out(json.dumps(dict(robots_bars=url)))
                break
            r = client.get(url, tolerate=(404,))
            rows = listing_rows(r.content) if r.status_code == 200 else []
            if not rows:
                c.execute('INSERT OR REPLACE INTO state VALUES (?, ?)', (f'index_done_{kind}', str(page)))
                c.commit()
                break
            for k, (path, title, d) in enumerate(rows):
                if keep and not keep.search(title):
                    continue
                u = f'https://{HOST}{path}'
                c.execute('INSERT OR IGNORE INTO queue (url, seq, listed, title) VALUES (?,?,?,?)', (u, seq_base + page * 100 + k, d, title))
            page += 1
            c.execute('INSERT OR REPLACE INTO state VALUES (?, ?)', (skey, str(page)))
            c.commit()
            n += len(rows)
        out(json.dumps(dict(index_pages=page, rows_this_run=n, stats=stats())))
        return page


def crawl(max_pages=None, out=print, client=None):
    lockf = F.P.FT_RAW / 'defense_crawl' / f'{HOST}.lock'
    lockf.parent.mkdir(parents=True, exist_ok=True)
    with open(lockf, 'w') as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            out(json.dumps(dict(stop='another defense crawl is running')))
            return None
        client = client or O.Client(DELAY, low_priority=True)
        try:
            rp, cd = E.load_robots(HOST, client)
        except O.Blocked as e:
            out(json.dumps(dict(blocked=str(e))))
            return None
        client.delay = max(client.delay, float(cd or 0))
        c = connect()
        done = 0
        try:
            while True:
                row = c.execute("SELECT url FROM queue WHERE status='pending' ORDER BY seq LIMIT 1").fetchone()
                if not row or (max_pages and done >= max_pages):
                    break
                url = row[0]
                if urlsplit(url).netloc != HOST or not E.url_allowed(rp, url):
                    c.execute("UPDATE queue SET status='robots', at=? WHERE url=?", (F.now(), url))
                    c.commit()
                    continue
                r = client.get(url, tolerate=(404, 410))
                if r.status_code in (404, 410):
                    st = 'gone'
                elif b'<html' not in r.content[:4000].lower() and b'<!doctype' not in r.content[:200].lower():
                    st = 'nonhtml'
                else:
                    title, txt = page_text(r.content)
                    if not title and not txt:
                        raise O.Blocked('an empty event page: stopping, not retrying')
                    c.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?)', (url, hashlib.sha256(r.content).hexdigest(), F.now(), title, txt))
                    st = 'done'
                c.execute('UPDATE queue SET status=?, at=? WHERE url=?', (st, F.now(), url))
                c.commit()
                done += 1
                if done % 100 == 0:
                    out(json.dumps(stats()))
        except O.Blocked as e:
            out(json.dumps(dict(blocked=str(e), stats=stats())))
            return None
        out(json.dumps(dict(stats=stats(), at=time.strftime('%FT%T'))))
        return stats()


def stats():
    c = connect()
    return dict(queue=dict(c.execute('SELECT status, COUNT(*) FROM queue GROUP BY status')),
                pages=c.execute('SELECT COUNT(*) FROM pages').fetchone()[0],
                listed=[c.execute('SELECT MIN(listed) FROM queue').fetchone()[0], c.execute('SELECT MAX(listed) FROM queue').fetchone()[0]])


def main(argv):
    cmd = argv[0]
    if cmd == 'index':
        index(int(argv[argv.index('--max-pages') + 1]) if '--max-pages' in argv else 450,
              kind=argv[argv.index('--kind') + 1] if '--kind' in argv else 'defense')
    elif cmd == 'crawl':
        crawl(int(argv[argv.index('--max') + 1]) if '--max' in argv else None)
    elif cmd == 'stats':
        print(json.dumps(stats()))


if __name__ == '__main__':
    main(sys.argv[1:])
