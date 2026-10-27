"""Berkeley EECS "Faculty Publications" pages (www2.eecs.berkeley.edu/Pubs/Faculty/<id>.html): each PI's institutional
publication list, kept as an identity anchor (a work on the PI's own list is the PI's), since dblp.org is behind a bot
challenge and sparql.dblp.org does not answer.

fetch    one request every 2.5 s (robots.txt: only /Protected is disallowed); pages stored zlib-compressed in
         hierarchy/berkeley/pubs-pages.sqlite with their sha256
extract  each <li> entry: the quoted title and the last year in the entry
-> hierarchy/berkeley/pi-publication-lists.json  {pi: [{title, year, url, sha256}]}
usage: berkeley_pubs.py fetch|extract
"""
import hashlib, html, json, re, sqlite3, sys, time, zlib
from pathlib import Path
import requests

HERE = Path(__file__).resolve().parents[1]; OUT = HERE / 'hierarchy/berkeley'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'


def db():
    c = sqlite3.connect(OUT / 'pubs-pages.sqlite')
    c.execute('create table if not exists pages (pi text primary key, url text, status int, fetched_at text, sha256 text, body blob)')
    return c


def targets():
    d = json.loads((HERE.parent / 'claude-berkeley-20261021/people/dept_berkeley.json').read_text())
    census = {x['name'] for x in json.loads((HERE / 'census/berkeley-faculty.json').read_text()) if x['is_pi']}
    seen = {}
    for r in d['people']:
        if r['role'] == 'faculty' and r['name'] in census and r.get('homepage_id'):
            seen.setdefault(r['name'], r['homepage_id'])
    return seen


def fetch():
    c = db(); s = requests.Session(); s.headers['User-Agent'] = UA
    done = {r[0] for r in c.execute('select pi from pages where status=200')}
    for pi, hp in targets().items():
        if pi in done:
            continue
        url = f'https://www2.eecs.berkeley.edu/Pubs/Faculty/{hp}.html'
        try:
            r = s.get(url, timeout=60); b = r.content; st = r.status_code
        except requests.RequestException:
            b, st = b'', 0
        c.execute('insert or replace into pages values (?,?,?,?,?,?)', (pi, url, st, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), hashlib.sha256(b).hexdigest(), zlib.compress(b)))
        c.commit(); time.sleep(2.5)
    print(json.dumps(dict(pages=c.execute('select count(*) from pages where status=200').fetchone()[0])))


def extract():
    c = db(); out = {}
    for pi, url, sha, body in c.execute('select pi, url, sha256, body from pages where status=200'):
        t = zlib.decompress(body).decode('utf-8', 'replace'); rows = []
        for li in re.findall(r'<li>(.*?)</li>', t, flags=re.S):
            x = html.unescape(re.sub(r'<[^>]+>', '', li)); x = re.sub(r'\s+', ' ', x)
            m = re.search(r'["“]([^"”]{12,400}?)[,.]?["”]', x); ys = re.findall(r'\b(19[89]\d|20[0-2]\d)\b', x)
            if m:
                rows.append(dict(title=m.group(1).strip().rstrip(','), year=int(ys[-1]) if ys else None, url=url, sha256=sha))
        out[pi] = rows
    (OUT / 'pi-publication-lists.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(pis=len(out), entries=sum(map(len, out.values())), entries_2016_on=sum(1 for v in out.values() for r in v if (r['year'] or 0) >= 2016),
                          pis_with_2016_on=sum(any((r['year'] or 0) >= 2016 for r in v) for v in out.values()))))


if __name__ == '__main__':
    {'fetch': fetch, 'extract': extract}[sys.argv[1]]()
