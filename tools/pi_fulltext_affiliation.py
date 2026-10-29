"""Lab papers whose affiliation OpenAlex never recorded: the PI's own works (by their anchored OpenAlex author ids) whose
PI authorship lists no institution, checked against page 1 of the paper itself.

works    every 2016-2026 work of each PI's anchored or reviewed OpenAlex author ids (hierarchy/<school>/pis.json
         oaAuthorIds + reviewedOpenAlex), 25 PIs per list query, cached in hierarchy/<school>/pi-works.sqlite
pdf      for a work whose PI authorship lists no institution at all and that has an arXiv id: version 1 of its arXiv PDF
         from arXiv's public bulk copy (storage.googleapis.com/arxiv-dataset; never arxiv.org), page 1 through
         pdftotext. The first version shows where the work was done. The PDF itself is not kept: its sha256, the page-1
         text and the matched passage are. A work without an arXiv id whose PDF the school's full-text catalog already
         holds (homogenizing-science/data/fulltext/<school>/catalog.sqlite, matched by DOI or <school>_oa_<W id>) is
         read from that local copy instead (pages.arxiv is null, pages.url is 'local:<catalog id>').
rule     page 1 ties the school to the PI (the same institutional pattern as pi_hierarchy.AFF, never a bare town name):
           marker  the PI's name carries an affiliation marker ("Adams1", "Adams*") and the line with that marker names
                   the school;
           near    the school is named within 160 characters after the PI's name (author blocks "Name / Department /
                   University");
           single  the school is the only institution named in the author block (the text before the abstract).
         A school named anywhere else on the page (a co-author's affiliation, a reference) does not count. The quotes
         are the passage with the PI's name and the passage naming the school, both substrings of the page text.
-> hierarchy/<school>/pi-works.sqlite (tables works, pages), read by pi_hierarchy.py
usage: pi_fulltext_affiliation.py works <school> | pdf <school> [--workers 4]
"""
import hashlib, json, os, re, sqlite3, subprocess, sys, tempfile, time, zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
from pi_hierarchy import INST, AFF, read  # noqa: E402
HERE = P.WORK
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
FT = P.STORES
SELECT = 'id,doi,title,publication_year,publication_date,type,authorships,ids,primary_location,locations'


def db(school):
    c = sqlite3.connect(HERE / 'hierarchy' / school / 'pi-works.sqlite', timeout=60)
    c.execute('create table if not exists queries (batch text primary key, done int)')
    c.execute('create table if not exists works (id text primary key, body blob)')
    c.execute('create table if not exists pages (work text primary key, arxiv text, url text, status text, pdf_sha256 text, page1 blob, school_named int, quote text, fetched_at text)')
    return c


def works(school):
    key = os.environ['OPENALEX_API_KEY']; floor = int(os.environ.get('OPENALEX_FLOOR') or 1500)
    c = db(school); s = requests.Session(); s.headers['User-Agent'] = UA
    pis = read(HERE / 'hierarchy' / school / 'pis.json')
    ids = sorted({a.rsplit('/', 1)[-1] for p in pis for a in (p.get('oaAuthorIds') or [])[:6] + (p.get('reviewedOpenAlex') or [])})
    for i in range(0, len(ids), 25):
        batch = '|'.join(ids[i:i + 25])
        if c.execute('select done from queries where batch=?', (batch,)).fetchone():
            continue
        cursor = '*'
        while cursor:
            for attempt in range(5):
                try:
                    r = s.get('https://api.openalex.org/works', timeout=120, params={'api_key': key, 'filter': f'author.id:{batch},publication_year:2016-2026',
                                                                                     'per-page': 200, 'cursor': cursor, 'select': SELECT})
                    if r.status_code == 200:
                        break
                except requests.RequestException:
                    pass
                time.sleep(5 * (attempt + 1))
            else:
                print(json.dumps(dict(school=school, failed_batch=i))); return
            j = r.json()
            for w in j['results']:
                c.execute('insert or replace into works values (?,?)', (w['id'], zlib.compress(json.dumps(w).encode())))
            cursor = j['meta'].get('next_cursor') if j['results'] else None
            if int(r.headers.get('X-RateLimit-Remaining') or 10**6) < floor:
                c.commit(); print(json.dumps(dict(school=school, stopped='credit floor'))); return
            time.sleep(0.25)
        c.execute('insert into queries values (?,1)', (batch,)); c.commit()
    print(json.dumps(dict(school=school, author_ids=len(ids), works=c.execute('select count(*) from works').fetchone()[0])))


def arxiv_id(w):
    for loc in [w.get('primary_location') or {}] + list(w.get('locations') or []):
        for u in (loc.get('landing_page_url') or '', loc.get('pdf_url') or ''):
            m = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', u or '')
            if m:
                return m.group(1)
    m = re.search(r'10\.48550/arxiv\.(\d{4}\.\d{4,5})', (w.get('doi') or '').lower())
    return m.group(1) if m else None


INSTITUTION = re.compile(r"universit|institute|college|école|ecole|eth z|inria|cnrs|max planck|laborator|research\b|\binc\b|corporation|google|microsoft|meta\b|"
                         r"facebook|amazon|ibm|nvidia|deepmind|openai|apple|adobe|intel\b|hospital|school of", re.I)


def tie(flat, names, aff):
    """(how, quotes) when page 1 ties the school to the PI, else (None, [])."""
    head = flat[:re.search(r'\babstract\b', flat[:6000], re.I).start()] if re.search(r'\babstract\b', flat[:6000], re.I) else flat[:2500]
    for first, last in names:
        rx = re.compile(r'(?<![A-Za-z])' + re.escape(first[0]) + (re.escape(first[1:]) if len(first) > 1 else r'\.?') +
                        r'[\w.\-]*(?:\s+[A-Z][\w.\-]*){0,2}\s+' + re.escape(last) + r'(?![a-z])', re.I)
        for m in rx.finditer(head):
            tail = head[m.end():m.end() + 14]
            mk = re.match(r'\s?([0-9,\s∗*†‡§¶♯]+)', tail)
            if mk:
                for sym in [x for x in re.split(r'[,\s]+', mk.group(1)) if x]:
                    for line in re.finditer(r'(?:^|\s)' + re.escape(sym) + r'\s?([^0-9∗*†‡§¶♯]{5,160})', head[m.end() + len(mk.group(0)):]):
                        if aff.search(line.group(1)):
                            return 'marker', [head[m.start():m.end() + len(mk.group(0))], line.group(0).strip()]
            near = head[m.end():m.end() + 160]
            a = aff.search(near)
            if a and not re.search(r'(?<![A-Za-z])[A-Z][a-z]+\s+[A-Z][a-z]+\s*[0-9∗*†‡]', near[:a.start()]):  # no other author's name in between
                return 'near', [head[m.start():m.end() + a.end()]]
            insts = {i.group(0).lower() for i in INSTITUTION.finditer(head)}
            if aff.search(head) and len(insts) <= 1:
                a2 = aff.search(head)
                return 'single', [head[m.start():m.end()], head[max(0, a2.start() - 60):a2.end() + 20]]
    return None, []


def local_pdfs(school):
    """{doi or catalog id: absolute path} of every downloaded PDF in the school's full-text catalog (read in rowid chunks:
    collectors write it over NFS)."""
    root = FT / school; out = {}
    cat = sqlite3.connect(f'file:{root / "catalog.sqlite"}?mode=ro', uri=True, timeout=60)
    hi = cat.execute('select max(rowid) from works').fetchone()[0] or 0
    for lo in range(0, hi + 1, 2000):
        for i, d, fp in cat.execute("select id, doi, file_path from works where rowid >= ? and rowid < ? and status = 'downloaded' and file_path like '%.pdf'", (lo, lo + 2000)):
            out[i] = (str(root / fp), i)
            d = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', d or '', flags=re.I).lower()
            if d:
                out.setdefault(d, (str(root / fp), i))
        time.sleep(0.02)
    return out


def candidates(school):
    """Works of the school's PIs whose PI authorship lists no institution (needs page 1): (work, arXiv id or None, name forms,
    local catalog PDF or None)."""
    c = db(school); pis = read(HERE / 'hierarchy' / school / 'pis.json')
    mine = {a for p in pis for a in (p.get('oaAuthorIds') or [])[:6] + (p.get('reviewedOpenAlex') or [])}
    from pi_hierarchy import toks, given
    names_of = {}
    for p in pis:
        forms = sorted({(given(t[0]), t[-1]) for n in p['names'] for t in [toks(n)] if len(t) >= 2} | {(t[1], t[-1]) for n in p['names'] for t in [toks(n)] if len(t) >= 3 and len(t[0]) == 1})
        for a in (p.get('oaAuthorIds') or [])[:6] + (p.get('reviewedOpenAlex') or []):
            names_of[a] = forms
    done = {r[0] for r in c.execute('select work from pages')}
    local = local_pdfs(school)
    out = []
    for (b,) in c.execute('select body from works'):
        w = json.loads(zlib.decompress(b))
        if w['id'] in done:
            continue
        a = next((x for x in w.get('authorships') or [] if (x.get('author') or {}).get('id') in mine), None)
        if a is None or a.get('institutions') or a.get('raw_affiliation_strings'):
            continue
        ax = arxiv_id(w)
        loc = None if ax else (local.get(re.sub(r'^https?://(?:dx\.)?doi\.org/', '', w.get('doi') or '', flags=re.I).lower())
                               or local.get(f"{school}_oa_{w['id'].rsplit('/', 1)[-1]}"))
        if ax or loc:
            out.append((w['id'], ax, names_of[(a.get('author') or {}).get('id')], loc))
    return out


def page1(school, wid, ax, aff, names, loc=None):
    if loc:  # the full-text catalog's own copy
        path, cid = loc
        try:
            data = open(path, 'rb').read()
        except OSError:
            return (wid, None, 'local:' + cid, 'local_missing', None, None, None, None)
        txt = subprocess.run(['pdftotext', '-l', '1', path, '-'], capture_output=True, text=True, timeout=120).stdout
        flat = re.sub(r'\s+', ' ', txt); how, quotes = tie(flat, names, aff)
        return (wid, None, 'local:' + cid, 'ok' if how else ('ok_untied' if aff.search(flat) else 'ok_absent'), hashlib.sha256(data).hexdigest(),
                zlib.compress(txt.encode()), int(bool(how)), json.dumps(dict(how=how, quotes=quotes)) if how else None)
    url = f'https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/{ax.split(".")[0]}/{ax}v1.pdf'
    try:
        r = requests.get(url, headers={'User-Agent': UA}, timeout=120)
    except requests.RequestException:
        return (wid, ax, url, 'fetch_error', None, None, None, None)
    if r.status_code != 200 or not r.content.startswith(b'%PDF'):
        return (wid, ax, url, f'http_{r.status_code}', None, None, None, None)
    with tempfile.NamedTemporaryFile(suffix='.pdf', dir=os.environ.get('TMPDIR', '/tmp')) as f:
        f.write(r.content); f.flush()
        txt = subprocess.run(['pdftotext', '-l', '1', f.name, '-'], capture_output=True, text=True, timeout=120).stdout
    flat = re.sub(r'\s+', ' ', txt); how, quotes = tie(flat, names, aff)
    return (wid, ax, url, 'ok' if how else ('ok_untied' if aff.search(flat) else 'ok_absent'), hashlib.sha256(r.content).hexdigest(),
            zlib.compress(txt.encode()), int(bool(how)), json.dumps(dict(how=how, quotes=quotes)) if how else None)


def pdf(school, workers=4):
    aff = re.compile(AFF[school], re.I); c = db(school); todo = candidates(school)
    print(json.dumps(dict(school=school, pdf_candidates=len(todo))), flush=True)
    with ThreadPoolExecutor(workers) as ex:
        for k, row in enumerate(ex.map(lambda t: page1(school, t[0], t[1], aff, t[2], t[3]), todo)):
            c.execute('insert or replace into pages values (?,?,?,?,?,?,?,?,?)', row + (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),))
            if k % 50 == 0:
                c.commit()
    c.commit()
    n = c.execute('select count(*), sum(school_named) from pages where status="ok"').fetchone()
    print(json.dumps(dict(school=school, pages=n[0], school_named=n[1])))


if __name__ == '__main__':
    cmd, school = sys.argv[1], sys.argv[2]
    works(school) if cmd == 'works' else pdf(school, int(sys.argv[4]) if len(sys.argv) > 4 else 4)
