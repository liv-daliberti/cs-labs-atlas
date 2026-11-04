"""Polite crawl of a repository's dissertation item pages for the ADVISER field (2026-11-04, owner), as an adviser-bearing student source.

Why: stage 6 prefers dissertations with an advisor field, but the two onboarding repositories give it only on the item page (Georgia Tech's
OAI-PMH is disallowed; UChicago's oai_dc carries no contributors). Configuration per school in the charter, section [etd_crawl]:
    host         the one host crawled (one flock per host, strictly sequential)
    delay        seconds between requests (raised to the host's Crawl-delay)
    enumerate    "sitemap"  sitemap (index) URL + url_rx: the item URLs the robots-listed sitemap names
                 "oai"      the school's OAI harvest (raw/oai_repo/<school>.sqlite) rows whose type matches oai_type_rx; the record
                            pages are the queue (only dissertations are fetched)
    parser       "dspace7" (Georgia Tech SMARTech item pages: Author(s) / Advisor(s) / Resource Subtype) | "invenio" (UChicago Knowledge)
robots.txt (this client, ClaudeBot, anthropic-ai) is checked for every URL before it is fetched; a 403/429-after-retries, a login page 25 times
running or a non-HTML body stops the crawl (state kept). Resumable: raw/etd_crawl/<school>.sqlite (queue, pages), one file per school.
Only the fields we need are stored per page: title, author, degree/type, year, department, advisors, URL, sha256 of the page, and a short
verbatim quote of the metadata block. Nothing else of the page is kept.
usage: etd_crawl.py enumerate <school> | add <school> <urls-or-sitemap file> [--rx R] [--front] | crawl <school> [--max N] | evidence <school> [--out FILE] | stats <school>
`evidence` matches each dissertation's advisor to the school's PIs (full name, pihier.names.Name) and writes thesis-evidence rows:
{pi, students: [{name, role, years, url, sha256, quote, note}]} (the format tools/pihier/students.py RESEARCHED_FILES reads).
"""
import fcntl
import hashlib
import json
import re
import sqlite3
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402
import oai_repo as O  # noqa: E402

WINDOW = (2016, 2026)
LOGIN_STOP = 25
TRANSIENT_STOP = 12
DISS_RX = re.compile(r'dissertation|doctoral|ph\.?\s?d|doctor of', re.I)


def cfg(school):
    import school_config as SC
    return dict(SC.field(SC.get(school), 'etd_crawl', {}) or {})


def db_path(school):
    return F.P.FT_RAW / 'etd_crawl' / f'{school}.sqlite'


def connect(school):
    p = db_path(school)
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(p), timeout=120)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS queue (url TEXT PRIMARY KEY, seq INTEGER, hint TEXT, status TEXT DEFAULT 'pending', at TEXT);
    CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, sha256 TEXT, fetched_at TEXT, dissertation INTEGER, title TEXT, author TEXT,
        degree TEXT, year INTEGER, department TEXT, advisors TEXT, quote TEXT);
    CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT);
    """)
    return c


# ------------------------------------------------------------------------------------------------------------------ parsers

def _soup(html_bytes):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html_bytes, 'lxml')


def _text(node):
    return re.sub(r'\s+', ' ', node.get_text(' ')).strip()


def _meta(soup, name):
    return [m.get('content', '').strip() for m in soup.find_all('meta', attrs={'name': name}) if m.get('content')]


def parse_dspace7(body):
    """Georgia Tech SMARTech (DSpace 7 server-side render): Author(s) / Advisor(s) / Date / Resource Subtype blocks. A page the renderer
    answered with its login view has no item and gives None (counted as 'login')."""
    s = _soup(body)
    title = (s.title.get_text() if s.title else '').strip()
    if title.endswith(':: Login') or not _meta(s, 'citation_title'):
        return None
    fields = {}
    for h in s.find_all('h2', class_='simple-view-element-header'):
        body_el = h.find_next_sibling('div')
        if not body_el:
            continue
        names = [_text(a) for a in body_el.select('a, span.dont-break-out') if _text(a)]
        fields[_text(h)] = names or ([_text(body_el)] if _text(body_el) else [])
    advisors = [n for n in fields.get('Advisor(s)', []) if n]
    authors = _meta(s, 'citation_author') or fields.get('Author(s)', [])
    sub = ' '.join(fields.get('Resource Subtype', []))
    date = ' '.join(fields.get('Date', [])) or (_meta(s, 'citation_publication_date') or [''])[0]
    units = [n for n in fields.get('Associated Organization(s)', []) if n]
    ym = re.search(r'\b(19|20)\d\d\b', date)
    quote = f"Author(s) {'; '.join(authors)} | Advisor(s) {'; '.join(advisors)} | Date {date} | Resource Subtype {sub}"
    return dict(title=_meta(s, 'citation_title')[0], author=authors[0] if authors else '', degree=sub, year=int(ym.group(0)) if ym else None,
                department='; '.join(units[:3]), advisors=advisors, dissertation=bool(DISS_RX.search(sub)), quote=quote[:400])


def parse_invenio(body):
    """UChicago Knowledge (InvenioRDM record page): Creators, 'Advisor:' contributors, 'Published <Month> <Year>', Department(s)."""
    s = _soup(body)
    if not _meta(s, 'citation_title'):
        return None
    advisors, committee = [], []
    for h in s.find_all('h3', class_='creatibutors-header'):
        ul = h.find_next_sibling('ul')
        names = [_text(n) for n in (ul.select('.creatibutor-name') if ul else [])]
        label = _text(h).lower()
        if label.startswith('advisor') or label.startswith('adviser') or 'chair' in label:
            advisors += names
        else:
            committee += names
    txt = _text(s)
    ym = re.search(r'Published\s+(?:[A-Z][a-z]+\s+)?((?:19|20)\d\d)', txt)
    dep = ''
    for dt in s.find_all('dt'):
        if _text(dt).startswith('Department'):
            dd = dt.find_next_sibling('dd')
            dep = _text(dd) if dd else ''
    authors = _meta(s, 'citation_author')
    rt = re.search(r'Version v\d+\s+(\w[\w ]*?)\s+(?:Open|Restricted|Embargoed|Closed)\b', txt)
    typ = rt.group(1) if rt else ''
    quote = f"Creators {'; '.join(authors)} | Advisor: {'; '.join(advisors)} | Published {ym.group(1) if ym else ''} | {typ} | Department(s) {dep}"
    return dict(title=_meta(s, 'citation_title')[0], author=authors[0] if authors else '', degree=typ, year=int(ym.group(1)) if ym else None,
                department=dep, advisors=advisors, dissertation=bool(DISS_RX.search(typ)), quote=quote[:400])


PARSERS = dict(dspace7=parse_dspace7, invenio=parse_invenio)


# ------------------------------------------------------------------------------------------------------------------ enumerate

def sitemap_urls(client, url, rx, tries=4):
    """Item URLs of a sitemap or sitemap index (nested sitemaps followed), in listed order, filtered by regex. A response that ends before its
    closing tag (a 7 MB sitemap cut off on 2026-11-04) is asked again, up to `tries` times, never parsed as complete."""
    sizes = []
    for attempt in range(tries):
        text = client.get(url).content.decode('utf8', 'replace')
        if re.search(r'</(urlset|sitemapindex)>\s*$', text):
            break
        sizes.append(len(text))
        print(json.dumps(dict(sitemap_truncated=url, bytes=len(text), attempt=attempt)), flush=True)
        if len(sizes) >= 2 and sizes[-1] == sizes[-2]:
            # the same cut twice: the server ends the file there (Georgia Tech sitemap1.xml, 955,812 bytes, 2026-11-04). The complete <loc>
            # entries before the cut are used; the entries after it are not listed anywhere we may read, and the crawl says so.
            text = text[:text.rfind('</url>') + 6] if '</url>' in text else text
            print(json.dumps(dict(sitemap_cut_server_side=url, bytes=len(text))), flush=True)
            break
        client.sleep(60 * (attempt + 1))
    else:
        raise O.Blocked(f'sitemap {url} stays truncated')
    locs = [u.strip() for u in re.findall(r'<loc>\s*([^<]+?)\s*</loc>', text)]
    if '<sitemapindex' in text[:2000]:
        return [u for sm in locs for u in sitemap_urls(client, sm, rx, tries)]
    return [u for u in locs if re.search(rx, u)]


def enumerate_queue(school, conf, client=None, out=print):
    c = connect(school)
    if conf.get('enumerate') == 'oai':
        src = sqlite3.connect(f'file:{O.db_path(school)}?mode=ro', uri=True)
        rows = []
        for links, rtype, year in src.execute('SELECT links, rtype, year FROM records WHERE deleted=0'):
            if re.search(conf.get('oai_type_rx', 'doctoralThesis'), rtype or ''):
                u = next((x for x in json.loads(links) if '/records/' in x), None)
                if u:
                    rows.append((u, json.dumps(dict(rtype=rtype, year=year))))
    else:
        urls = sitemap_urls(client, conf['sitemap'], conf['url_rx'])
        rows = [(u, None) for u in urls]
    n0 = c.execute('SELECT COUNT(*) FROM queue').fetchone()[0]
    seq = n0
    for u, hint in rows:
        if not c.execute('SELECT 1 FROM queue WHERE url=?', (u,)).fetchone():
            c.execute('INSERT INTO queue (url, seq, hint) VALUES (?,?,?)', (u, seq, hint))
            seq += 1
    c.commit()
    out(json.dumps(dict(school=school, enumerated=len(rows), new=seq - n0)))
    return seq - n0


# ------------------------------------------------------------------------------------------------------------------ crawl

def url_allowed(rp_by_agent, url):
    return all(rp.can_fetch(url, a) for a, rp in rp_by_agent.items())


def load_robots(host, client):
    from protego import Protego
    r = client.s.get(f'https://{host}/robots.txt', timeout=(15, 30))
    text = r.text if r.status_code == 200 else ('' if r.status_code == 404 else 'User-agent: *\nDisallow: /\n')
    rp = Protego.parse(text)
    agents = (F.UA,) + O.AI_AGENTS
    return {a: rp for a in agents}, max([rp.crawl_delay(a) or 0 for a in agents])


def crawl(school, max_pages=None, out=print, client=None):
    conf = cfg(school)
    if not conf:
        out(json.dumps(dict(school=school, skipped='no [etd_crawl] section')))
        return None
    host = conf['host']
    lockf = F.P.FT_RAW / 'etd_crawl' / f'{host}.lock'
    lockf.parent.mkdir(parents=True, exist_ok=True)
    with open(lockf, 'w') as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            out(json.dumps(dict(school=school, stop=f'another crawl of {host} is running')))
            return None
        client = client or O.Client(max(float(conf.get('delay') or 10), 10.0))
        rp, cd = load_robots(host, client)
        client.delay = max(client.delay, float(cd or 0))
        out(json.dumps(dict(school=school, host=host, delay=client.delay, robots=dict(zip(['self', 'ClaudeBot', 'anthropic-ai'],
                                                                                           [rp[a].can_fetch(f'https://{host}/', a) for a in rp])))))
        c = connect(school)
        if not c.execute('SELECT 1 FROM queue LIMIT 1').fetchone():
            enumerate_queue(school, conf, client, out)
        parser = PARSERS[conf['parser']]
        done = logins = transients = 0
        try:
            while True:
                row = c.execute("SELECT url, hint FROM queue WHERE status='pending' ORDER BY seq LIMIT 1").fetchone()
                if not row or (max_pages and done >= max_pages):
                    break
                url, hint = row
                hint = json.loads(hint) if hint else {}
                if urlsplit(url).netloc != host or not url_allowed(rp, url):
                    c.execute("UPDATE queue SET status='robots', at=? WHERE url=?", (F.now(), url))
                    c.commit()
                    continue
                try:
                    r = client.get(url, tolerate=(404, 410))
                except O.Transient as e:  # the server is ill, not refusing: wait and ask again; the URL stays pending
                    transients += 1
                    out(json.dumps(dict(school=school, transient=str(e), wait=1800, in_a_row=transients, at=F.now())))
                    if transients >= TRANSIENT_STOP:
                        raise O.Blocked(f'{TRANSIENT_STOP} failed rounds in a row (each after the client\'s own back-offs)') from e
                    client.sleep(1800)
                    continue
                transients = 0
                st = 'done'
                if r.status_code in (404, 410):
                    st = 'gone'
                elif b'<html' not in r.content[:4000].lower() and b'<!doctype' not in r.content[:200].lower():
                    raise O.Blocked('non-HTML body')
                else:
                    p = parser(r.content)
                    if p is None:
                        st = 'login'
                        logins += 1
                        if logins >= LOGIN_STOP:
                            raise O.Blocked(f'{LOGIN_STOP} login views in a row: the host does not serve item pages to this client')
                    else:
                        logins = 0
                        if hint.get('rtype') and re.search(r'doctoral', hint['rtype'], re.I):
                            p['dissertation'] = True
                            p['degree'] = f"{p['degree']} (OAI type {hint['rtype'].rsplit('/', 1)[-1]})"
                        c.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                                  (url, hashlib.sha256(r.content).hexdigest(), F.now(), int(p['dissertation']), p['title'], p['author'], p['degree'],
                                   p['year'] or hint.get('year'), p['department'], json.dumps(p['advisors']), p['quote']))
                c.execute('UPDATE queue SET status=?, at=? WHERE url=?', (st, F.now(), url))
                c.commit()
                done += 1
                if done % 100 == 0:
                    out(json.dumps(stats(school)))
        except O.Blocked as e:
            out(json.dumps(dict(school=school, blocked=str(e), stats=stats(school))))
            return None
        out(json.dumps(dict(school=school, stats=stats(school))))
        return stats(school)


def add_urls(school, urls, front=False):
    """Queue more URLs (the one paced crawler fetches them; never a second client). front: ahead of everything pending. -> number added."""
    conf = cfg(school)
    c = connect(school)
    lo, hi = c.execute('SELECT COALESCE(MIN(seq), 0), COALESCE(MAX(seq), -1) FROM queue').fetchone()
    n = 0
    for u in urls:
        if urlsplit(u).netloc != conf['host'] or c.execute('SELECT 1 FROM queue WHERE url=?', (u,)).fetchone():
            continue
        seq = lo - 1 - n if front else hi + 1 + n
        c.execute('INSERT INTO queue (url, seq) VALUES (?,?)', (u, seq))
        n += 1
    c.commit()
    return n


def stats(school):
    c = connect(school)
    q = dict(c.execute('SELECT status, COUNT(*) FROM queue GROUP BY status'))
    return dict(school=school, queue=q, pages=c.execute('SELECT COUNT(*) FROM pages').fetchone()[0],
                dissertations=c.execute('SELECT COUNT(*) FROM pages WHERE dissertation=1').fetchone()[0],
                with_advisor=c.execute("SELECT COUNT(*) FROM pages WHERE dissertation=1 AND advisors!='[]'").fetchone()[0])


# ------------------------------------------------------------------------------------------------------------------ evidence

def natural(name):
    """'Last, First M.' -> 'First M. Last'."""
    n = re.sub(r'\s+', ' ', name or '').strip()
    if ',' in n:
        last, _, first = n.partition(',')
        return f'{first.strip()} {last.strip()}'.strip()
    return n


def role_of(degree):
    d = (degree or '').lower()
    if re.search(r'dissertation|doctoral|ph\.?\s?d|doctor of', d):
        return 'phd'
    return 'other'


def build_evidence(school, pis, window=WINDOW):
    """-> (rows in thesis-evidence.json shape, counts). pis: [{pi, names}] (hierarchy/<school>/derived/pis.json)."""
    if str(F.P.TOOLS) not in sys.path:
        sys.path.insert(0, str(F.P.TOOLS))
    from pihier.names import Name
    idx = {p['pi']: Name(list(dict.fromkeys([p['pi']] + list(p.get('names') or [])))) for p in pis}
    c = connect(school)
    out, counts = {}, dict(dissertations=0, no_advisor=0, outside_window=0, no_pi=0, rows=0, ambiguous=0)
    for url, sha, title, author, degree, year, dep, advisors, quote in c.execute(
            'SELECT url, sha256, title, author, degree, year, department, advisors, quote FROM pages WHERE dissertation=1 ORDER BY url'):
        counts['dissertations'] += 1
        advs = json.loads(advisors)
        if not advs:
            counts['no_advisor'] += 1
            continue
        if not year or not (window[0] <= year <= window[1]):
            counts['outside_window'] += 1
            continue
        hit = False
        for a in advs:
            nat = natural(a)
            pi_hits = [p for p, nm in idx.items() if nm.match(nat)]
            if len(pi_hits) > 1:
                counts['ambiguous'] += 1
                continue
            for p in pi_hits:
                hit = True
                out.setdefault(p, []).append(dict(
                    name=natural(author), role=role_of(degree), years=[year, year], url=url, sha256=sha, quote=quote,
                    note=f"{school} repository item page ({degree}; {dep}): '{title}'; advisor '{a}' = {p}"))
                counts['rows'] += 1
        if not hit:
            counts['no_pi'] += 1
    rows = [dict(pi=p, students=sorted(v, key=lambda s: (s['years'][0], s['name'])),
                 notes=f'Dissertation item pages crawled {time.strftime("%Y-%m-%d")} (etd_crawl.py): advisor field matched to the PI by full name.')
            for p, v in sorted(out.items())]
    return rows, counts


def main(argv):
    cmd, school = argv[0], argv[1]
    if cmd == 'enumerate':
        conf = cfg(school)
        client = O.Client(max(float(conf.get('delay') or 10), 10.0))
        enumerate_queue(school, conf, client)
    elif cmd == 'crawl':
        mx = int(argv[argv.index('--max') + 1]) if '--max' in argv else None
        crawl(school, mx)
    elif cmd == 'add':  # add <school> <file of URLs, or a saved sitemap> [--rx REGEX] [--front]
        conf = cfg(school)
        text = Path(argv[2]).read_text()
        rx = argv[argv.index('--rx') + 1] if '--rx' in argv else conf.get('url_rx', '.')
        urls = re.findall(r'<loc>\s*([^<]+?)\s*</loc>', text) if '<loc>' in text else text.split()
        print(json.dumps(dict(school=school, added=add_urls(school, [u for u in urls if re.search(rx, u)], '--front' in argv))))
    elif cmd == 'stats':
        print(json.dumps(stats(school)))
    elif cmd == 'evidence':
        pis = json.loads(F.P.data('pis.json', school).read_text())
        rows, counts = build_evidence(school, pis)
        outp = Path(argv[argv.index('--out') + 1]) if '--out' in argv else None
        if outp:
            outp.write_text(json.dumps(rows, indent=1, ensure_ascii=False))
        print(json.dumps(counts))


if __name__ == '__main__':
    main(sys.argv[1:])
