"""Institutional-repository harvests over OAI-PMH (KiltHub: Figshare's OAI-PMH set for the CMU portal), 2026-11-04 (owner: "full harvest of each
school's institutional repository over its standard bulk interface, politely; author manuscripts often live only there").

One generic harvester, configured per school in the charter (schools/<key>.toml, section [oai_repo]):
    verdict       "harvest" | "skip"          skip: the reason is recorded (docs/CHANNELS.md "Repository harvests") and nothing is fetched
    base          the OAI-PMH base URL
    prefix        metadataPrefix (oai_dc, oai_openaire)
    sets          explicit setSpecs; or sets_regex (+ sets_prefix) resolved against ListSets by set name; neither = whole repository
    delay         seconds between requests (raised to the host's Crawl-delay; sequential; one harvest per host through a flock)
    landing       template for a record's landing page from the OAI identifier tail, "https://host/records/{id}"
    relation_dois true: the DOIs in dc:relation are the record's own (MIT: the published version, dc:relation.isversionof)
    relation_links regex: a dc:relation URL matching it is a landing page of the record (Figshare: figshare.com/articles/...)
    enrich        "figshare": the files of a record that matched are read from the public API (channels/oai_repo.py)
robots.txt is read first: the harvest refuses to start when the base path is disallowed for this client's user agent, ClaudeBot or
anthropic-ai, and it stops on a 403, a 202 (bot challenge), a non-XML body or an OAI error. Nothing behind a paywall or login is fetched.

The records go to ONE SQLite file per school (raw/oai_repo/<school>.sqlite: tables records, state, sets_resolved); never per-record files.
Resumable: the resumption token and the per-set 'from' watermark live in `state`, so a re-run continues a half-finished set and a
finished one is only re-asked for what changed since (incremental harvest).
usage: oai_repo.py robots <school> | harvest <school> [--max-pages N] | harvest-rest <school> [--max-pages N] | stats <school>
The matching of the records to the lab papers is channels/oai_repo.py (docs/CHANNELS.md).
"""
import fcntl
import html
import json
import re
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402

AI_AGENTS = ('ClaudeBot', 'anthropic-ai')
DOI_RX = re.compile(r'10\.\d{4,9}/[^\s"<>]+', re.I)
HANDLE_RX = re.compile(r'(?:hdl\.handle\.net/|/handle/|handle:|^|\b)(\d{4,6}\.\d+/\d+|20\.500\.\d+/\d+|\d{4,6}/\d+)(?![\d.])')
NOT_LANDING = re.compile(r'orcid\.org|doi\.org|ror\.org|isni\.org|scopus\.com|issn', re.I)
YEAR_RX = re.compile(r'\b(19|20)\d\d\b')
DEFAULT_DELAY = 10.0
BACKOFF = (60, 300, 900, 1800, 1800, 1800)  # seconds before asking again after a 429/5xx without Retry-After


class Blocked(Exception):
    """The host answered with a refusal (403, a challenge, a non-XML page): the harvest stops, it never works around it."""


class Transient(Blocked):
    """The host kept answering 500/502/503/504 or dropping connections through every back-off: not a refusal. A long-running crawl
    waits and asks again (etd_crawl.crawl); a harvest stops and resumes from its stored token."""


def cfg(school):
    import school_config as SC
    return dict(SC.field(SC.get(school), 'oai_repo', {}) or {})


def db_path(school):
    return F.P.FT_RAW / 'oai_repo' / f'{school}.sqlite'


def connect(school):
    p = db_path(school)
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(p), timeout=120)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS records (oai_id TEXT PRIMARY KEY, datestamp TEXT, deleted INTEGER, sets TEXT, title TEXT, creators TEXT,
        year INTEGER, dois TEXT, links TEXT, files TEXT, rights TEXT, rtype TEXT, relations TEXT);
    CREATE TABLE IF NOT EXISTS state (k TEXT PRIMARY KEY, v TEXT);
    CREATE TABLE IF NOT EXISTS sets_resolved (spec TEXT PRIMARY KEY, name TEXT);
    """)
    return c


def state_get(c, k, default=None):
    r = c.execute('SELECT v FROM state WHERE k=?', (k,)).fetchone()
    return r[0] if r else default


def state_put(c, k, v):
    c.execute('INSERT OR REPLACE INTO state VALUES (?,?)', (k, v))


# ----------------------------------------------------------------------------------------------------------------- robots

def robots_verdict(base, get=None):
    """{'allowed': bool, 'per_agent': {agent: bool}, 'crawl_delay': float|None, 'status': http status} for the base URL's path.
    A missing robots.txt (404) allows; any other failure to read it disallows."""
    from protego import Protego
    parts = urlsplit(base)
    url = f'{parts.scheme}://{parts.netloc}/robots.txt'
    if get is None:
        import requests
        def get(u):
            return requests.get(u, headers={'User-Agent': F.UA}, timeout=(15, 30))
    try:
        r = get(url)
        status, text = r.status_code, r.text
    except Exception as e:  # noqa: BLE001
        return dict(allowed=False, per_agent={}, crawl_delay=None, status=f'error: {str(e)[:80]}')
    if status == 404:
        text = ''
    elif status != 200 or not text.strip() and status != 404:
        return dict(allowed=False, per_agent={}, crawl_delay=None, status=status)
    rp = Protego.parse(text)
    agents = (F.UA,) + AI_AGENTS
    per = {a.split('/')[0]: bool(rp.can_fetch(base, a)) for a in agents}
    delays = [rp.crawl_delay(a) for a in agents]
    return dict(allowed=all(per.values()), per_agent=per, crawl_delay=max([d for d in delays if d] or [0]) or None, status=status)


# ----------------------------------------------------------------------------------------------------------------- parsing

def local(tag):
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


def text_of(e):
    return re.sub(r'\s+', ' ', ''.join(e.itertext())).strip()


def parse_record(rec, landing=None, rel_rx=None, relation_dois=False):
    """One <record> element -> dict(oai_id, datestamp, deleted, sets, title, creators, year, dois, links, files, rights, rtype, relations).
    dois = identifiers the record names as its own (dc:identifier, datacite alternateIdentifier/identifier); DOIs found in dc:relation
    are kept apart (relations) unless the repository's charter says its dc:relation is the version-of DOI (MIT): they point at related
    items and otherwise never decide a match."""
    h = next((x for x in rec if local(x.tag) == 'header'), None)
    out = dict(oai_id='', datestamp='', deleted=0, sets=[], title='', creators=[], year=None, dois=[], links=[], files=[], rights=[], rtype='',
               relations=[])
    if h is not None:
        out['deleted'] = int(h.get('status') == 'deleted')
        for x in h:
            n = local(x.tag)
            if n == 'identifier':
                out['oai_id'] = text_of(x)
            elif n == 'datestamp':
                out['datestamp'] = text_of(x)
            elif n == 'setSpec':
                out['sets'].append(text_of(x))
    md = next((x for x in rec if local(x.tag) == 'metadata'), None)
    if md is None:
        return out
    issued = None
    dc_dates = []
    for e in md.iter():
        n, t = local(e.tag), text_of(e)
        if not t and n != 'file':
            continue
        if n == 'title' and not out['title']:
            out['title'] = t
        elif n in ('creator', 'creatorName'):
            out['creators'].append(re.sub(r'\s*\(\d+\)$', '', t))  # Figshare: 'Name (author id)'
        elif n in ('identifier', 'alternateIdentifier'):
            for d in DOI_RX.findall(t):
                out['dois'].append(F.ndoi(d.rstrip('.,;)')))
            if t.startswith('http') and not NOT_LANDING.search(t):
                out['links'].append(t)
            elif e.get('identifierType', '').lower() == 'handle' or HANDLE_RX.fullmatch(t or ''):
                out['links'].append('https://hdl.handle.net/' + t)
            elif re.fullmatch(r'\d{4,6}\.\d+/\d+|20\.500\.\d+/\d+', t):
                out['links'].append('https://hdl.handle.net/' + t)
        elif n == 'relation':
            found = [F.ndoi(d.rstrip('.,;)')) for d in DOI_RX.findall(t)]
            out['dois' if relation_dois else 'relations'] += found
            if rel_rx and re.search(rel_rx, t) and t.startswith('http'):
                out['links'].append(t)  # e.g. Figshare: the article page is the record's dc:relation
        elif n == 'date':
            if e.get('dateType') == 'Issued' and issued is None:
                issued = t
            dc_dates.append(t)
        elif n == 'rights':
            out['rights'].append(t)
        elif n in ('type', 'resourceType') and not out['rtype']:
            out['rtype'] = t
        elif n == 'file':
            if t.startswith('http'):
                out['files'].append(dict(url=t, mime=e.get('mimeType'), kind=e.get('objectType'), access=e.get('accessRightsURI')))
    for d in [issued] + dc_dates:
        m = YEAR_RX.search(d or '')
        if m:
            out['year'] = int(d[m.start():m.start() + 4])
            break
    out['dois'] = list(dict.fromkeys(out['dois']))
    out['links'] = list(dict.fromkeys(out['links']))
    if landing and out['oai_id']:
        out['landing'] = landing.format(id=out['oai_id'].rsplit(':', 1)[-1])
        if out['landing'] not in out['links']:
            out['links'].append(out['landing'])
    return out


def parse_page(body):
    """(records, resumption token or '', completeListSize or None, error code or None) of one OAI-PMH response body (bytes or str)."""
    root = ET.fromstring(body)
    err = next((e for e in root.iter() if local(e.tag) == 'error'), None)
    if err is not None:
        return [], '', None, err.get('code', 'error')
    recs = [r for r in root.iter() if local(r.tag) == 'record']
    tok = next((e for e in root.iter() if local(e.tag) == 'resumptionToken'), None)
    return recs, (html.unescape(text_of(tok)) if tok is not None else ''), (tok.get('completeListSize') if tok is not None else None), None


def store_records(c, parsed, set_spec=None):
    n = 0
    for p in parsed:
        if not p['oai_id']:
            continue
        old = c.execute('SELECT sets FROM records WHERE oai_id=?', (p['oai_id'],)).fetchone()
        sets = sorted(set(p['sets']) | set(json.loads(old[0]) if old and old[0] else []) | ({set_spec} if set_spec else set()))
        c.execute('INSERT OR REPLACE INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                  (p['oai_id'], p['datestamp'], p['deleted'], json.dumps(sets), p['title'], json.dumps(p['creators']), p['year'],
                   json.dumps(p['dois']), json.dumps(p['links']), json.dumps(p['files']), json.dumps(p['rights'][:6]), p['rtype'],
                   json.dumps(p['relations'][:6])))
        n += 1
    return n


# ----------------------------------------------------------------------------------------------------------------- transport

class Client:
    """Sequential, paced GETs with Retry-After; refusals raise Blocked."""

    def __init__(self, delay, session=None, sleep=time.sleep, clock=time.monotonic, low_priority=False):
        import requests
        self.s = session or requests.Session()
        self.s.headers['User-Agent'] = F.UA
        self.delay, self.last, self.sleep, self.clock = delay, -1e9, sleep, clock
        self.requests = 0
        self.low = low_priority   # evidence crawls yield to the download loops on a host with a shared clock (host_throttle)

    def get(self, url, params=None, tolerate=()):
        import host_throttle as HT
        host = urlsplit(url).hostname
        shared = host in HT.SHARED_INTERVAL
        for attempt in range(6):
            if shared:   # one request clock and one 429 cooldown for every client of this host (loops included)
                try:
                    self.sleep(HT.cooldown_left(host))
                    self.sleep(HT.reserve(host, self.delay, low=self.low))
                except OSError:
                    shared = False
            if not shared:
                self.sleep(max(0, self.delay - (self.clock() - self.last)))
            self.last = self.clock()
            self.requests += 1
            try:
                r = self.s.get(url, params=params, timeout=(20, 180))
            except Exception as e:  # noqa: BLE001
                print(json.dumps(dict(error=str(e)[:120], attempt=attempt)), flush=True)
                self.sleep(60 * (attempt + 1))
                continue
            if r.status_code == 429 and shared:
                HT.record_429(host)   # everyone pauses; the next loop turn waits the cooldown out
                print(json.dumps(dict(status=429, shared_cooldown=round(HT.cooldown_left(host)), at=F.now())), flush=True)
                continue
            if r.status_code in (429, 500, 502, 503, 504):
                wait = min(int(r.headers.get('Retry-After') or BACKOFF[min(attempt, len(BACKOFF) - 1)]), 1800)
                print(json.dumps(dict(status=r.status_code, wait=wait, at=F.now())), flush=True)
                self.sleep(wait)
                continue
            if r.status_code in tolerate:
                return r
            if r.status_code != 200:
                raise Blocked(f'HTTP {r.status_code} from {urlsplit(url).netloc}')
            return r
        raise Transient('repeated transient failures')


def resolve_sets(c, conf, client):
    """setSpecs to harvest: explicit `sets`, else ListSets filtered by sets_regex on the set name (and sets_prefix on the spec);
    [None] (the whole repository) when neither is configured. Stored in sets_resolved so the choice is auditable."""
    if conf.get('sets'):
        return list(conf['sets'])
    if not conf.get('sets_regex'):
        return [None]
    rx, pre = re.compile(conf['sets_regex'], re.I), conf.get('sets_prefix', '')
    if not c.execute('SELECT 1 FROM sets_resolved LIMIT 1').fetchone() or state_get(c, 'listsets_done') != '1':
        tok = state_get(c, 'listsets_token')
        while True:
            params = dict(verb='ListSets', resumptionToken=tok) if tok else dict(verb='ListSets')
            r = client.get(conf['base'], params)
            root = ET.fromstring(r.content)
            for s in (e for e in root.iter() if local(e.tag) == 'set'):
                spec = next((text_of(x) for x in s if local(x.tag) == 'setSpec'), None)
                name = next((text_of(x) for x in s if local(x.tag) == 'setName'), '')
                if spec:
                    c.execute('INSERT OR REPLACE INTO sets_resolved VALUES (?,?)', (spec, name))
            t = next((html.unescape(text_of(e)) for e in root.iter() if local(e.tag) == 'resumptionToken'), '')
            state_put(c, 'listsets_token', t)
            c.commit()
            if not t:
                state_put(c, 'listsets_done', '1')
                c.commit()
                break
            tok = t
    return [s for s, n in c.execute('SELECT spec, name FROM sets_resolved ORDER BY spec') if s.startswith(pre) and rx.search(n)]


# ----------------------------------------------------------------------------------------------------------------- harvests

def seed_from_pages(c, conf, set_spec, out=print):
    """MIT: the OA Articles collection was already harvested whole on 2026-10-30 (raw/mit_oa_articles.sqlite, zlib pages of the same
    ListRecords oai_dc request). Its pages are parsed into the table without a request, and the set's `from` watermark is the day
    before that harvest started, so the next incremental run asks only for what changed since."""
    import zlib
    src = F.P.FT_RAW / f"{conf['seed']}.sqlite"
    key = set_spec or '*'
    if not src.exists() or state_get(c, f'complete:{key}') == '1' or state_get(c, f'token:{key}') is not None:
        return 0
    s = sqlite3.connect(f'file:{src}?mode=ro', uri=True)
    last = s.execute('SELECT next_token FROM pages ORDER BY n DESC LIMIT 1').fetchone()
    if not last or last[0]:
        return 0  # the earlier harvest never finished: harvest afresh
    first = s.execute('SELECT MIN(fetched_at) FROM pages').fetchone()[0][:10]
    n = 0
    for (body,) in s.execute('SELECT body FROM pages ORDER BY n'):
        recs, _, _, err = parse_page(zlib.decompress(body))
        n += store_records(c, [parse_record(x, conf.get('landing'), conf.get('relation_links'), bool(conf.get('relation_dois'))) for x in recs], set_spec)
    since = time.strftime('%Y-%m-%dT00:00:00Z', time.gmtime(time.mktime(time.strptime(first, '%Y-%m-%d')) - 86400))
    state_put(c, f'done:{key}', since)
    state_put(c, f'token:{key}', '')
    state_put(c, f'complete:{key}', '1')
    c.commit()
    out(json.dumps(dict(seeded=key, records=n, from_=since)))
    return n


def harvest_oai(school, conf, client, max_pages=None, out=print):
    c = connect(school)
    sets = resolve_sets(c, conf, client)
    out(json.dumps(dict(school=school, sets=len(sets), first=sets[:5])))
    pages = 0
    for sp in sets:
        key = sp or '*'
        if conf.get('seed') and sp == conf.get('seed_set'):
            seed_from_pages(c, conf, sp, out)
        tok = state_get(c, f'token:{key}')
        since = state_get(c, f'done:{key}')
        started = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        while True:
            if tok:
                params = dict(verb='ListRecords', resumptionToken=tok)
            else:
                params = dict(verb='ListRecords', metadataPrefix=conf.get('prefix', 'oai_dc'))
                if sp:
                    params['set'] = sp
                if since:
                    params['from'] = since
                state_put(c, f'started:{key}', started)
            r = client.get(conf['base'], params)
            if not r.content.lstrip()[:5] == b'<?xml' and b'<OAI-PMH' not in r.content[:2000]:
                raise Blocked('non-XML body (challenge or error page)')
            recs, nxt, total, err = parse_page(r.content)
            if err == 'noRecordsMatch':
                nxt, recs = '', []
            elif err:
                raise Blocked(f'OAI error {err} (set {key})')
            n = store_records(c, [parse_record(x, conf.get('landing'), conf.get('relation_links'), bool(conf.get('relation_dois'))) for x in recs], sp)
            state_put(c, f'token:{key}', nxt)
            pages += 1
            if not nxt:
                state_put(c, f'done:{key}', state_get(c, f'started:{key}'))
                state_put(c, f'complete:{key}', '1')
            c.commit()
            if pages % 25 == 1 or not nxt:
                out(json.dumps(dict(set=key, page=pages, records=n, total=total, more=bool(nxt), at=F.now())))
            tok = nxt
            if not nxt:
                break
            if max_pages and pages >= max_pages:
                return stats(school)
    return stats(school)


def md_values(md, key):
    return [v.get('value') for v in (md.get(key) or []) if v.get('value')]


def rest_record(obj, scope):
    """One DSpace 7 REST discovery object (an item with its metadata) -> the records-table dict. oai_id is rest:<item uuid>."""
    md = obj.get('metadata') or {}
    year = next((int(m.group(0)) for d in md_values(md, 'dc.date.issued') for m in [YEAR_RX.search(d)] if m), None)
    handle = obj.get('handle')
    return dict(oai_id=f"rest:{obj['uuid']}", datestamp=(md_values(md, 'dc.date.modified') or md_values(md, 'dc.date.accessioned') or [''])[0][:20],
                deleted=0, sets=[scope], title=(md_values(md, 'dc.title') or [''])[0], creators=md_values(md, 'dc.contributor.author'), year=year,
                dois=[F.ndoi(d) for d in md_values(md, 'dc.identifier.doi') if DOI_RX.search(d)],
                links=[f'https://hdl.handle.net/{handle}'] if handle else [], files=[], rights=md_values(md, 'datacite.rights')[:6],
                rtype=(md_values(md, 'dc.type') or [''])[0], relations=[])


def harvest_rest(school, conf, client, max_pages=None, out=print):
    """DSpace 7 REST enumeration (Infoscience, 2026-11-04: the OAI endpoint answered 405 at page ~282): /server/api/discover/search/objects
    per collection, 100 items a page, sorted by accession date, resumable by page number (state `page:<scope>`). Collections are named by
    handle (`scopes`) and resolved through /pid/find. The files of a record come later, only for records that match (channels/oai_repo.py)."""
    c = connect(school)
    base = conf['rest_base'].rstrip('/')
    pages = 0
    for handle in conf['scopes']:
        key = f'rest:{handle}'
        uuid = state_get(c, f'uuid:{handle}')
        if not uuid:
            uuid = client.get(f'{base}/pid/find', dict(id=f'hdl:{handle}')).json()['uuid']
            state_put(c, f'uuid:{handle}', uuid)
            c.commit()
        if state_get(c, f'complete:{key}') == '1':
            continue
        page = int(state_get(c, f'page:{key}', '0'))
        while True:
            r = client.get(f'{base}/discover/search/objects', dict(scope=uuid, dsoType='ITEM', size=100, page=page, sort='dc.date.accessioned,ASC'))
            try:
                res = r.json()['_embedded']['searchResult']
            except (ValueError, KeyError) as e:
                raise Blocked('unexpected REST answer') from e
            objs = [o['_embedded']['indexableObject'] for o in res['_embedded']['objects']]
            store_records(c, [rest_record(o, key) for o in objs], key)
            pages += 1
            page += 1
            state_put(c, f'page:{key}', str(page))
            last = page >= res['page']['totalPages']
            if last:
                state_put(c, f'complete:{key}', '1')
            c.commit()
            if pages % 25 == 1 or last:
                out(json.dumps(dict(scope=handle, page=page, of=res['page']['totalPages'], at=F.now())))
            if last:
                break
            if max_pages and pages >= max_pages:
                return stats(school)
    return stats(school)


def stats(school):
    c = connect(school)
    n = c.execute('SELECT COUNT(*), SUM(deleted=0) FROM records').fetchone()
    return dict(school=school, records=n[0], live=n[1] or 0, with_doi=c.execute("SELECT COUNT(*) FROM records WHERE dois!='[]'").fetchone()[0],
                with_files=c.execute("SELECT COUNT(*) FROM records WHERE files!='[]'").fetchone()[0],
                complete_sets=sum(1 for k, v in c.execute("SELECT k, v FROM state WHERE k LIKE 'complete:%'") if v == '1'))


def harvest(school, max_pages=None, out=print, client=None, rest=False):
    conf = cfg(school)
    if rest:
        conf = dict(conf, **conf.get('rest', {}))
    if conf.get('verdict') != 'harvest':
        out(json.dumps(dict(school=school, skipped=conf.get('verdict') or 'no [oai_repo] section', reason=conf.get('reason'))))
        return None
    v = robots_verdict(conf['rest_base'] if rest else conf['base'])
    out(json.dumps(dict(school=school, robots=v)))
    if not v['allowed']:
        out(json.dumps(dict(school=school, stop='robots.txt disallows the base path for this client or an AI agent')))
        return None
    delay = max(float(conf.get('delay') or DEFAULT_DELAY), float(v['crawl_delay'] or 0))
    host = urlsplit(conf['rest_base'] if rest else conf['base']).netloc
    lockf = F.P.FT_RAW / 'oai_repo' / f'{host}.lock'
    lockf.parent.mkdir(parents=True, exist_ok=True)
    with open(lockf, 'w') as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            out(json.dumps(dict(school=school, stop=f'another harvest of {host} is running')))
            return None
        client = client or Client(delay)
        try:
            return (harvest_rest if rest else harvest_oai)(school, conf, client, max_pages, out)
        except Blocked as e:
            out(json.dumps(dict(school=school, blocked=str(e), stats=stats(school))))
            return None


def main(argv):
    cmd, school = argv[0], argv[1]
    if cmd == 'robots':
        print(json.dumps(robots_verdict(cfg(school)['base'])))
    elif cmd == 'harvest':
        mp = int(argv[argv.index('--max-pages') + 1]) if '--max-pages' in argv else None
        print(json.dumps(harvest(school, mp)))
    elif cmd == 'harvest-rest':
        mp = int(argv[argv.index('--max-pages') + 1]) if '--max-pages' in argv else None
        print(json.dumps(harvest(school, mp, rest=True)))
    elif cmd == 'stats':
        print(json.dumps(stats(school)))


if __name__ == '__main__':
    main(sys.argv[1:])
