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
           footnote (R8, 2026-10-29) the PI's symbol marker opens a footnote line at the foot of page 1 that names the
                   school (mathematics papers: 'Jacob Fox∗' ... '∗ Stanford University, Stanford, CA.').
usage: pi_fulltext_affiliation.py works <school> | pdf <school> [--workers 4] | retie <school>
"""
import unicodedata
import hashlib, json, os, re, sqlite3, subprocess, sys, tempfile, time, zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
from pi_hierarchy import INST, AFF, read  # noqa: F401,E402
HERE = P.WORK
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
FT = P.STORES
SELECT = 'id,doi,title,publication_year,publication_date,type,authorships,ids,primary_location,locations'


def db(school):
    c = sqlite3.connect(P.data('pi-works.sqlite', school), timeout=60)
    c.execute('create table if not exists queries (batch text primary key, done int)')
    c.execute('create table if not exists works (id text primary key, body blob)')
    c.execute('create table if not exists pages (work text primary key, arxiv text, url text, status text, pdf_sha256 text, page1 blob, school_named int, quote text, fetched_at text)')
    return c


def works_from_snapshot(school):
    """pi-works from the OpenAlex snapshot (the school's extension holds every work of our PIs' author ids, tools/oa_snapshot.py): no API credit.
    Returns the author ids it found no work for (the caller may ask the API for those only)."""
    import oa_snapshot as O
    c = db(school)
    pis = read(P.data('pis.json', school))
    ids = sorted({a.rsplit('/', 1)[-1] for p in pis for a in (p.get('oaAuthorIds') or [])[:6] + (p.get('reviewedOpenAlex') or [])})
    missing = []
    for a in ids:
        n = 0
        for w in O.works_by_author(a):
            if 2016 <= (w.get('publication_year') or 0) <= 2026:
                c.execute('insert or replace into works values (?,?)', (w['id'], zlib.compress(json.dumps(w).encode()))); n += 1
        if not n:
            missing.append(a)
    c.commit()
    print(json.dumps(dict(school=school, source='snapshot', author_ids=len(ids), without_snapshot_works=len(missing), works=c.execute('select count(*) from works').fetchone()[0])))
    return missing


def works(school):
    if '--from-snapshot' in sys.argv:
        works_from_snapshot(school)
        return
    key = os.environ['OPENALEX_API_KEY']; floor = int(os.environ.get('OPENALEX_FLOOR') or 1500)
    c = db(school); s = requests.Session(); s.headers['User-Agent'] = UA
    pis = read(P.data('pis.json', school))
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


FOOTNOTE_UNIT = re.compile(r'^(?:[A-Z][\w&.\-]*,?\s+){0,8}?(?:Department|Dept|School|Institute|Laborator|Center|Centre|University|College|Group|Lab)\b')
COLLECTIVE_FOOTNOTE = re.compile(r'(?i)\b(?:all |the )?authors? (?:are|is) (?:with|associated with|affiliated with|at|from)\b')


def norm_quotes(s):
    """Curly and modifier apostrophes as the plain one ('Una-May O’Reilly' is the PI's name 'O'Reilly')."""
    return re.sub(r"[\u2018\u2019\u02bc\u2032]", "'", s)


def fold(s):
    """ASCII fold of letters ('Atamtürk', precomposed or with a combining diaeresis, -> 'Atamturk'), so name forms (which toks() reduces
    to ASCII) match accented bylines; every other character stays."""
    out = []
    for c in s:
        if unicodedata.category(c) == 'Mn':
            continue
        d = unicodedata.normalize('NFKD', c)[:1] if ord(c) > 127 else c
        out.append(d if d and d.isascii() and d.isalpha() else c)
    return ''.join(out)


def loose(word):
    """A name as a pattern that tolerates the apostrophe or hyphen toks() drops ('oreilly' also reads O'Reilly, 'jones' Jones)."""
    return r"['\-]?".join(re.escape(c) for c in word)


def tie(flat, names, aff):
    """(how, quotes) when page 1 ties the school to the PI, else (None, []). The author block is the text before 'Abstract'; when the
    block names no school, the text after 'Abstract' is read too (2026-11-12: arXiv layouts that put the affiliations after the word:
    'Samyukta Yagati UC Berkeley ... Abstract Raluca Ada Popa UC Berkeley'), and so are footnotes at the foot of page 1: a numbered
    unit footnote ('1 Machine Learning Department, Carnegie Mellon University') and a collective one ('All authors are with the
    Department of ..., University of California, Berkeley'; 'The authors are associated with the ... Department, Stanford
    University'). The PI's own name must still stand in the author block, and the affiliation must name the school."""
    flat = fold(norm_quotes(flat))
    ab = re.search(r'\babstract\b', flat[:6000], re.I)
    head = flat[:ab.start()] if ab else flat[:2500]
    names = [(norm_quotes(f), norm_quotes(l)) for f, l in names]
    r = _tie_in(head, flat, head, names, aff, True)
    if r[0] is None and ab:
        r = _tie_in(flat[:ab.end() + 2500], flat, head, names, aff, False)
    return r


def _tie_in(block, flat, head, names, aff, allow_single):
    for first, last in names:
        rx = re.compile(r'(?<![A-Za-z])' + re.escape(first[0]) + (re.escape(first[1:]) if len(first) > 1 else r'\.?') +
                        r'[\w.\-]*(?:\s+[A-Z][\w.\-]*){0,2}(?:\s+\([A-Za-z.\- ]{1,20}\))?\s+' + loose(last) + r'(?:(?=[a-d](?:,[a-d])*[,\u2217*\u2020\s])|(?![a-z]))', re.I)
        for m in rx.finditer(block):
            tail = block[m.end():m.end() + 14]
            mk = re.match(r'\s?([0-9,\s∗*†‡§¶♯]+)', tail)
            if mk and not mk.group(1).strip(' ,'):
                mk = None   # only whitespace after the name: no marker
            if mk:
                for sym in [x for x in re.split(r'[,\s]+', mk.group(1)) if x]:
                    for line in re.finditer(r'(?:^|\s)' + re.escape(sym) + r'\s?([^0-9∗*†‡§¶♯]{5,160})', block[m.end() + len(mk.group(0)):]):
                        a_ = aff.search(line.group(1))
                        if a_ and (allow_single or not re.search(r'(?i)equal|contribut|work (?:was )?done|intern', line.group(1)[:a_.start()])):
                            return 'marker', [block[m.start():m.end() + len(mk.group(0))], line.group(0).strip()]
                    # (R8, 2026-10-29) a symbol marker's footnote at the foot of page 1, as mathematics papers place the
                    # affiliations ('Jacob Fox∗' ... '∗ Stanford University, Stanford, CA.'): the first footnote line after
                    # the author block that starts with the symbol and a capital letter, naming the school in its first 120
                    # characters
                    if sym in '∗*†‡§¶♯':
                        fn = re.search(r'(?:^|\s)' + re.escape(sym) + r'\s?([A-Z][^∗*†‡§¶♯]{4,160})', flat[len(head):])
                        a_ = aff.search(fn.group(1)[:120]) if fn else None
                        if a_ and not re.search(r'(?i)equal|contribut|correspond|work (?:was )?done|intern', fn.group(1)[:a_.start()]):
                            return 'footnote', [block[m.start():m.end() + len(mk.group(0))], fn.group(0).strip()]
                    elif sym.isdigit():   # 2026-11-12: the same for a numbered footnote beyond the head cut, when it opens with a unit or institution
                        for fn in re.finditer(r'(?:^|\s)' + re.escape(sym) + r'\s*([A-Z][^0-9∗*†‡§¶♯]{4,160})', flat[len(head):]):
                            a_ = aff.search(fn.group(1)[:120])
                            if a_ and FOOTNOTE_UNIT.match(fn.group(1)) and not re.search(r'(?i)equal|contribut|correspond|work (?:was )?done|intern', fn.group(1)[:a_.start()]):
                                return 'footnote', [block[m.start():m.end() + len(mk.group(0))], fn.group(0).strip()]
                    # a collective footnote with the marker ('1 The authors are associated with the ... Department, Stanford University')
                    for cf in re.finditer(r'(?:^|\s)' + re.escape(sym) + r'\s?(?:The |All )?authors? (?:are|is) (?:with|associated with|affiliated with|at|from)\b([^{}]{0,220})', flat[len(head):], re.I):
                        if aff.search(cf.group(1)):
                            return 'footnote', [block[m.start():m.end() + len(mk.group(0))], cf.group(0).strip()]
            near = block[m.end():m.end() + 160]
            a = aff.search(near)
            if a and not allow_single and (a.start() > 40 or re.search(r'[.;:]\s', near[:a.start()])):
                a = None   # after 'Abstract' the affiliation must follow the name closely, in the same sentence
            if a and not re.search(r'(?<![A-Za-z])[A-Z][a-z]+\s+[A-Z][a-z]+\s*[0-9∗*†‡]', near[:a.start()]):  # no other author's name in between
                return 'near', [block[m.start():m.end() + a.end()]]
            insts = {i.group(0).lower() for i in INSTITUTION.finditer(block)}
            if allow_single and aff.search(block) and len(insts) <= 1:
                a2 = aff.search(block)
                return 'single', [block[m.start():m.end()], block[max(0, a2.start() - 60):a2.end() + 20]]
            if not mk:   # a footnote naming all the authors' unit, for a byline with no markers
                for cf in COLLECTIVE_FOOTNOTE.finditer(flat):
                    if aff.search(flat[cf.end():cf.end() + 220].split('{')[0]):
                        return 'footnote', [block[m.start():m.end()], flat[cf.start():cf.end() + 200].split('{')[0].strip()]
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


def dblp_pages(pis):
    """{pi: (DOIs, normalized titles)} of each PI's DBLP person page in the DBLP dump extract
    (hierarchy/dblp-dump-persons.json.gz), for the PI's DBLP ids in pis.json."""
    import html as html_
    from pi_hierarchy import norm_title
    f = P.data('dblp-dump-persons.json.gz')
    if not f.exists():
        return {}
    DP = read(f)['persons']; out = {}
    for p in pis:
        dois, titles = set(), set()
        for q in p.get('dblp') or []:
            for r in (DP.get(q) or {}).get('pubs') or []:
                dois |= {d.lower() for d in r.get('dois') or []}
                t = norm_title(html_.unescape(r.get('title') or '').rstrip('.'))
                if t:
                    titles.add(t)
        out[p['pi']] = (dois, titles)
    return out


def unaffiliated_pi_authorship(w, mine):
    """The authorship of one of the school's PIs (author id in `mine`) that lists no institution and no raw affiliation string, or None.
    Every PI authorship on the byline is considered, not just the first (2026-11-13, Princeton: Odysseus W7160129578 lists Danqi Chen with an
    institution first, so Chi Jin's affiliation-less authorship was never page-1 read)."""
    return next((x for x in w.get('authorships') or [] if (x.get('author') or {}).get('id') in mine
                 and not x.get('institutions') and not x.get('raw_affiliation_strings')), None)


CROSS_KINDS = {'company', 'nonprofit', 'government', 'facility', 'other', 'archive'}   # pihier.papers.CROSS_KINDS (R-PAP-29)


def cross_affiliated_pi_authorship(w, mine, inst_url):
    """(R-PAP-29, 2026-11-18) The authorship of one of the school's PIs (author id in `mine`) credited only to companies, agencies or other non-university
    institutions while another author of the byline is credited to the school: the byline the cross-affiliation route would admit. Its page 1 is read so the
    route can be refused when page 1 credits the PI elsewhere (Tambe's AAAI-23 paper: Google Research India; the co-author is Harvard's)."""
    school_co = any(inst_url in (i.get('lineage') or [i.get('id')]) or i.get('id') == inst_url
                    for x in w.get('authorships') or [] for i in x.get('institutions') or [])
    if not school_co:
        return None
    return next((x for x in w.get('authorships') or [] if (x.get('author') or {}).get('id') in mine and x.get('institutions')
                 and {i.get('type') for i in x['institutions']} <= CROSS_KINDS), None)


def candidates(school):
    """Works of the school's PIs whose PI authorship lists no institution (needs page 1): (work, arXiv id or None, name forms,
    local catalog PDF or None). Two kinds: (a) a work of one of the PI's anchored or reviewed OpenAlex author ids; (b) (R8,
    2026-10-29, owner: accuracy sample) a work on the PI's own DBLP person page (DOI or title) whose authorship at the PI's
    name, under any author id, lists no institution (Jacob Fox's JCTB 2025 paper: OpenAlex gives Fox no affiliation)."""
    c = db(school); pis = read(P.data('pis.json', school))
    mine = {a for p in pis for a in (p.get('oaAuthorIds') or [])[:6] + (p.get('reviewedOpenAlex') or [])}
    from pi_hierarchy import toks, given, Name, norm_title
    names_of, forms_of = {}, {}
    for p in pis:
        forms = sorted({(given(t[0]), t[-1]) for n in p['names'] for t in [toks(n)] if len(t) >= 2} | {(t[1], t[-1]) for n in p['names'] for t in [toks(n)] if len(t) >= 3 and len(t[0]) == 1})
        forms_of[p['pi']] = forms
        for a in (p.get('oaAuthorIds') or [])[:6] + (p.get('reviewedOpenAlex') or []):
            names_of[a] = forms
    by_doi, by_title = {}, {}
    for pi, (dois, titles) in dblp_pages(pis).items():
        for d in dois:
            by_doi.setdefault(d, []).append(pi)
        for t in titles:
            by_title.setdefault(t, []).append(pi)
    nm = {p['pi']: Name(p['names']) for p in pis}
    inst_url = 'https://openalex.org/' + INST[school]
    done = {r[0] for r in c.execute('select work from pages')}
    local = local_pdfs(school)
    out = []
    for (b,) in c.execute('select body from works'):
        w = json.loads(zlib.decompress(b))
        if w['id'] in done:
            continue
        a = unaffiliated_pi_authorship(w, mine); cross = False
        forms = names_of.get((a.get('author') or {}).get('id')) if a else None
        if a is None:
            a = None  # (b) the PI's DBLP page names the work and the PI's own authorship lists no institution
            d = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', w.get('doi') or '', flags=re.I).lower()
            for pi in dict.fromkeys(by_doi.get(d, []) + by_title.get(norm_title(w.get('title')), [])):
                a = next((x for x in w.get('authorships') or [] if not x.get('institutions') and not x.get('raw_affiliation_strings')
                          and nm[pi].match(x.get('raw_author_name') or (x.get('author') or {}).get('display_name') or '')), None)
                if a is not None:
                    forms = forms_of[pi]; break
            if a is None:
                a = cross_affiliated_pi_authorship(w, mine, inst_url); cross = a is not None
                forms = names_of.get((a.get('author') or {}).get('id')) if a else None
            if a is None:
                continue
        ax = arxiv_id(w)
        loc = None if ax else (local.get(re.sub(r'^https?://(?:dx\.)?doi\.org/', '', w.get('doi') or '', flags=re.I).lower())
                               or local.get(f"{school}_oa_{w['id'].rsplit('/', 1)[-1]}"))
        if not ax and not loc and cross:
            # (R-PAP-29, 2026-11-18) a cross-affiliated byline's page 1 from an open proceedings PDF named by OpenAlex (AAAI: Tambe's SAHELI paper)
            import dblp_recover as DR
            for lo in [w.get('primary_location') or {}] + list(w.get('locations') or []):
                u = lo.get('pdf_url') or ''
                if u and any(h in u for h in DR.OPEN_HOSTS):
                    loc = 'url:' + u; break
        if ax or loc:
            out.append((w['id'], ax, forms, loc))
    # (R-PAP-29, 2026-11-18) cross-affiliated bylines of the sweep (works pi-works does not hold: Tambe's SAHELI paper): the sweep's records carry no locations,
    # so the arXiv id or open PDF comes from OpenAlex's singleton DOI lookup (free)
    seen = {r[0] for r in out}
    sweep = P.data('openalex-sweep.sqlite', school)
    if sweep.exists():
        import dblp_recover as DR
        sc = sqlite3.connect(f'file:{sweep}?mode=ro', uri=True)
        for (b,) in sc.execute('select body from pages'):
            for w in json.loads(zlib.decompress(b)):
                if w['id'] in done or w['id'] in seen:
                    continue
                a = cross_affiliated_pi_authorship(w, mine, inst_url)
                if a is None:
                    continue
                forms = names_of.get((a.get('author') or {}).get('id'))
                ax = arxiv_id(w); loc = None
                doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', w.get('doi') or '', flags=re.I).lower()
                if not ax and doi:
                    try:
                        r = requests.get(f'https://api.openalex.org/works/doi:{doi}', params={'select': 'id,locations,primary_location,ids'}, headers={'User-Agent': UA}, timeout=60)
                        full = r.json() if r.status_code == 200 else {}
                    except (requests.RequestException, ValueError):
                        full = {}
                    ax = arxiv_id(dict(w, **{k: v for k, v in full.items() if k != 'id'}))
                    for lo in [] if ax else [full.get('primary_location') or {}] + list(full.get('locations') or []):
                        u = lo.get('pdf_url') or ''
                        if u and any(h in u for h in DR.OPEN_HOSTS):
                            loc = 'url:' + u; break
                if ax or loc:
                    out.append((w['id'], ax, forms, loc)); seen.add(w['id'])
    return out


def page1(school, wid, ax, aff, names, loc=None):
    if isinstance(loc, str) and loc.startswith('url:'):   # an open proceedings PDF (robots.txt, host throttle: dblp_recover.polite_get)
        import dblp_recover as DR
        url = loc[4:]; r = DR.polite_get(url)
        if r is None or r.status_code != 200 or r.content[:4] != b'%PDF':
            return (wid, None, url, 'fetch_error' if r is None else f'http_{r.status_code}', None, None, None, None)
        with tempfile.NamedTemporaryFile(suffix='.pdf', dir=os.environ.get('TMPDIR', '/tmp')) as f:
            f.write(r.content); f.flush()
            txt = subprocess.run(['pdftotext', '-l', '1', f.name, '-'], capture_output=True, text=True, timeout=120).stdout
        flat = re.sub(r'\s+', ' ', txt); how, quotes = tie(flat, names, aff)
        return (wid, None, url, 'ok' if how else ('ok_untied' if aff.search(flat) else 'ok_absent'), hashlib.sha256(r.content).hexdigest(),
                zlib.compress(txt.encode()), int(bool(how)), json.dumps(dict(how=how, quotes=quotes)) if how else None)
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


def retie_work(w, flat, aff, by_sur, nm, forms_of, toks, stored=None):
    """Page-1 ties of every PI on the work's byline, one per (work, PI) (2026-11-12): {pi: {how, quotes}} for the PIs whose own name the
    page ties to the school. `stored` (the row's current quote, when it already tied one PI) seeds the result."""
    out = {}
    for a in w.get('authorships') or []:
        raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
        t = toks(raw)
        for pi in (by_sur.get(t[-1], set()) if len(t) >= 2 else set()):
            if pi in out or not nm[pi].match(raw):
                continue
            how, quotes = tie(flat, forms_of[pi], aff)
            if how:
                out[pi] = dict(how=how, quotes=quotes)
    return out


def retie(school):
    """Re-read the stored page-1 texts with the current tie() rule for every PI whose name is on the work's byline (no download: the text
    is in the pages table), R8, 2026-10-29. Rows that named the school without a tie (status ok_untied) become ties; since 2026-11-12 each
    work keeps one tie per PI: the first PI's tie is the row's quote and the other PIs' ties are its `also` list (the row already tied for
    one PI gains the others'), which pihier.names.tie_for_pi applies per PI."""
    from pi_hierarchy import toks, given, Name
    c = db(school); aff = re.compile(AFF[school], re.I); pis = read(P.data('pis.json', school))
    forms_of, nm, by_sur = {}, {}, {}
    for p in pis:
        forms_of[p['pi']] = sorted({(given(t[0]), t[-1]) for n in p['names'] for t in [toks(n)] if len(t) >= 2} | {(t[1], t[-1]) for n in p['names'] for t in [toks(n)] if len(t) >= 3 and len(t[0]) == 1})
        nm[p['pi']] = Name(p['names'])
        for f, l in nm[p['pi']].forms:
            by_sur.setdefault(l, set()).add(p['pi'])
    k = k2 = 0
    for wid, txt, status, quote in c.execute("select work, page1, status, quote from pages where status='ok_untied' or school_named=1").fetchall():
        b = c.execute('select body from works where id=?', (wid,)).fetchone()
        if not b or not txt:
            continue
        w = json.loads(zlib.decompress(b[0])); flat = re.sub(r'\s+', ' ', zlib.decompress(txt).decode('utf-8', 'replace'))
        ties = retie_work(w, flat, aff, by_sur, nm, forms_of, toks)
        if status == 'ok_untied':
            if not ties:
                continue
            first = next(iter(ties.values()))
            q = dict(first, **({'also': list(ties.values())[1:]} if len(ties) > 1 else {}))
            c.execute("update pages set status='ok', school_named=1, quote=? where work=?", (json.dumps(q), wid)); k += 1
        else:   # a tied row: add the ties of other PIs (whose quotes name them) beside the stored one
            try:
                q = json.loads(quote or '{}')
            except ValueError:
                continue
            have = [q] + list(q.get('also') or [])
            from pihier.names import quotes_name_pi
            add = [t for pi, t in ties.items() if not any(quotes_name_pi(next(p['names'] for p in pis if p['pi'] == pi), e.get('quotes') or []) for e in have)]
            if add:
                q['also'] = list(q.get('also') or []) + add
                c.execute("update pages set quote=? where work=?", (json.dumps(q), wid)); k2 += 1
    c.commit()
    print(json.dumps(dict(school=school, retied=k, other_pi_ties_added=k2)))


if __name__ == '__main__':
    cmd, school = sys.argv[1], sys.argv[2]
    {'works': lambda: works(school), 'retie': lambda: retie(school)}.get(cmd, lambda: pdf(school, int(sys.argv[4]) if len(sys.argv) > 4 else 4))()
