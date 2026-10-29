"""NSF Public Access Repository (par.nsf.gov) for the US schools' lab papers without a local copy (2026-10-26).

NSF requires funded papers' accepted manuscripts (or the published article) to be deposited in PAR, where they are
public - often the only open copy of an IEEE / ACM / Springer paper. The method is the Princeton stage's
(../../claude-princeton-20261015/tools/cs_nsf_par.py, whose parser this reuses): an exact-title-phrase search
(par.nsf.gov/search/term:"<title words>"; robots.txt sets no rule for general crawlers), one request per 3 s; a
result counts only when its normalized title equals the paper's; its full-text link servlets/purl/<id> becomes the
candidate, with PAR's own version label. Searches are cached by normalized title in raw/nsf_par.sqlite (shared by the
schools; the Princeton stage's earlier answers are reused, never repeated).
search  papers missing at princeton, mit, cmu, berkeley (year >= 2015, title >= 30 normalized characters), the paywalled
        publishers first (IEEE, ACM, Springer, Elsevier, Wiley, Optica, SPIE, Cambridge, ...)
add     candidates for every school from the cached answers (lab_channels.write: catalogs / Princeton packages)
usage: nsf_par_lab.py search [<school> ...] | add [<school> ...]
"""
import gzip, json, re, sqlite3, sys, time
from collections import Counter
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

SCHOOLS = ['mit', 'cmu', 'berkeley', 'princeton']
DB = F.HERE / 'raw' / 'nsf_par.sqlite'
PRIN_RAW = Path('/n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015/cs-structure/raw/nsf_par')
PAYWALLED = ('10.1109', '10.1145', '10.1007', '10.1016', '10.1002', '10.1111', '10.1364', '10.1117', '10.1017', '10.1080', '10.1137', '10.1287',
             '10.1049', '10.1142', '10.1177', '10.1115', '10.1061', '10.1093', '10.1162', '10.1063', '10.1021', '10.1039')


def db():
    c = sqlite3.connect(str(DB))
    c.execute('CREATE TABLE IF NOT EXISTS searches (t TEXT PRIMARY KEY, title TEXT, query TEXT, status TEXT, results TEXT, at TEXT)')
    return c


def seed_from_princeton(c):
    if c.execute("SELECT COUNT(*) FROM searches WHERE query LIKE 'princeton-stage:%'").fetchone()[0]:
        return
    rows = []
    for f in sorted(PRIN_RAW.glob('results_*.json.gz')):
        for r in json.loads(gzip.decompress(f.read_bytes())):
            if r.get('status') == 200:
                rows.append((F.nt(r['title']), r['title'], 'princeton-stage:' + r['query'], '200', json.dumps(r['results']), r['at']))
    c.executemany('INSERT OR IGNORE INTO searches VALUES (?,?,?,?,?,?)', rows); c.commit()


def todo(schools):
    import lab_channels as L
    out = {}
    for school in schools:
        miss, known, base = L.plan_for(school)
        for r, w in miss:
            t = F.nt(r['title'])
            if len(t) < 30 or not (r.get('year') and int(r['year']) >= 2015) or any('par.nsf.gov' in u for u in known[w]):
                continue
            d = F.ndoi(r.get('doi'))
            pri = 0 if d.split('/')[0] in PAYWALLED else 1 if not d else 2
            if t not in out or pri < out[t][0]:
                out[t] = (pri, r['title'])
    return out


def search(schools):
    import requests
    sys.path.insert(0, '/n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015/tools')
    from cs_nsf_par import parse
    c = db(); seed_from_princeton(c)
    done = {t for (t,) in c.execute("SELECT t FROM searches WHERE status = '200'")}
    want = sorted(((p, t, title) for t, (p, title) in todo(schools).items() if t not in done), key=lambda x: x[0])
    print(json.dumps(dict(to_search=len(want), cached=len(done))), flush=True)
    s = requests.Session(); s.headers['User-Agent'] = F.UA
    last, hits = 0.0, 0
    for i, (p, t, title) in enumerate(want):
        words = re.sub(r'[^A-Za-z0-9 ]+', ' ', title).split()
        url = 'https://par.nsf.gov/search/term:' + quote('"' + ' '.join(words) + '"')
        time.sleep(max(0, 3 - (time.monotonic() - last))); last = time.monotonic()
        try:
            r = s.get(url, timeout=(15, 60))
            status, res = r.status_code, (parse(r.text) if r.status_code == 200 else [])
        except Exception as e:
            status, res = type(e).__name__, []
        if status == 429 or (isinstance(status, int) and status >= 500) or not isinstance(status, int):
            print(json.dumps(dict(status=status, pause_s=300)), flush=True); time.sleep(300)
        c.execute('INSERT OR REPLACE INTO searches VALUES (?,?,?,?,?,?)', (t, title, url, str(status), json.dumps(res), F.now())); c.commit()
        hits += any(F.nt(x['title']) == t for x in res)
        if i % 200 == 199:
            print(json.dumps(dict(searched=i + 1, of=len(want), exact_hits=hits, at=F.now())), flush=True)
    print(json.dumps(dict(searched=len(want), exact_hits=hits)), flush=True)


def add(schools):
    import lab_channels as L
    c = db()
    ans = {t: json.loads(res) for t, res in c.execute("SELECT t, results FROM searches WHERE status = '200'")}
    for school in schools:
        miss, known, base = L.plan_for(school)
        rows, n = [], Counter()
        for r, w in miss:
            t = F.nt(r['title'])
            for m in ans.get(t, []):
                if F.nt(m['title']) != t:
                    continue
                n['exact_title'] += 1
                ver = 'acceptedVersion' if any('Accepted' in l for l in m['labels']) else 'publishedVersion' if any('Published' in l for l in m['labels']) else None
                rows.append(dict(work_id=w, url=f"https://par.nsf.gov/servlets/purl/{m['purl']}",
                                 landing_url=f"https://par.nsf.gov/biblio/{m['biblio']}" if m['biblio'] else None, version=ver, source='nsf_par_exact_title',
                                 detail=json.dumps(dict(purl=m['purl'], par_title=m['title'], labels=m['labels'], title=r['title'], doi=r.get('doi')))))
        rows = L.new_rows(rows, known)
        added = L.write(school, rows, 'nsfpar')
        rec = dict(at=F.now(), school=school, step='nsfpar', missing_in_catalog=len(miss), rows=len(rows), works=len({r['work_id'] for r in rows}),
                   candidates_added=added, dry=False, **n)
        print(json.dumps(rec), flush=True)
        with open(F.HERE / 'logs' / 'channels.jsonl', 'a') as f:
            f.write(json.dumps(rec) + '\n')


if __name__ == '__main__':
    cmd, schools = sys.argv[1], sys.argv[2:] or SCHOOLS
    {'search': search, 'add': add}[cmd](schools)
