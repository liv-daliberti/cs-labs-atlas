"""A protocol school's faculty-listing captures -> one row per (person, listing capture): protocol stages 1-2.

Reads the plan the listings pipeline wrote (listings/<key>/captures.sqlite, table plan, status ok: one Wayback id_
capture per slot and half-year, listings/scripts/plan_fetch.py driven by the charter's [[departments.listings]]), parses
each capture with tools/listing_formats.py, and writes listings/<key>/rows.json.
Reviewed live-listing-sources.json supplements the plan from saved school_web live pages, using their actual
fetch dates and URLs. A complete group must match its reviewed expected entry count; no archive URL is invented.

row      name (given-first, as the page spells it), name_listed ('Last, First M.'), dept (the slot's department code),
         slot, kind (the slot's kind), year, observed (capture timestamp), titles (as listed), dept_title (the title lines
         that name the department, by the charter's [[departments]].title_match), rank (classified from dept_title, else
         from every title: emeritus | courtesy | adjunct | visiting | lecturer | research | teaching | ladder | other),
         homepage, profile (the department's own profile page, when the listing links one instead of a homepage), capture_url, sha256 (of the capture body as stored), quote (the person's name through their last
         title, from the capture's whitespace-collapsed text; disjoint verbatim excerpts use [...] to omit contact lines)
coverage listings/<key>/coverage.json: department x year -> slots with an ok capture, and the plan's reason for each
         half-year without one (nocapture | unusable | out_of_scope)
usage: listing_rows.py <key>
"""
import collections, hashlib, json, re, sqlite3, subprocess, sys, tempfile, urllib.parse, zlib
from datetime import datetime
from bs4 import BeautifulSoup

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import listing_formats as LF  # noqa: E402
from school_web import body as wb_body, extract as html_extract, wb as _wb  # noqa: E402  (stored capture bytes, gunzipped)
wb_text = _wb.text

RANKS = [('emeritus', r'emerit'), ('courtesy', r'courtesy|\baffiliate\s+faculty'), ('adjunct', r'\badjunct\b|\badjoint\b'), ('visiting', r'\bvisiting\b'),
         ('lecturer', r'\blecturer\b|\binstructor\b'), ('research', r'\bresearch\s+(?:scientist|investigator|professor|fellow|faculty)|\bresearch\s+assistant\s+professor'),
         ('teaching', r'\bteaching\s+professor|\binstructional\s+professor|\bclinical\s+(?:assistant\s+|associate\s+)?professor|professor\s+of\s+(?:the\s+)?practice'),
         ('ladder', r'\bprofessor\b')]
NOT_NAME = re.compile(r'\s*\((?:video|website|web|on leave|he/him|she/her|they/them)\)', re.I)  # page furniture after a name ('Mars, Jason (Video)')
SUFFIX = re.compile(r',?\s*\b(Jr|Sr|II|III|IV)\.?$')


def given_first(n):
    """'Ackerman, Mark S.' -> 'Mark S. Ackerman'; 'Smith, John, Jr.' -> 'John Smith Jr.'"""
    n = ' '.join(NOT_NAME.sub(' ', n).split()).strip(' ,')
    suf = SUFFIX.search(n)
    core = n[:suf.start()].strip(' ,') if suf else n
    if ',' in core:
        last, first = core.split(',', 1)
        core = f'{first.strip()} {last.strip()}'
    return core + (f' {suf.group(1)}.' if suf else '')


def rank_of(titles, extra=None):
    """The rank a title list reads as. `extra` = the charter's [census].rank_words ({rank = regex}): title words of one school that
    join the shared RANKS patterns for that rank (UChicago PROTOCOL-FRICTION 17, R3), so a new school never edits the shared table."""
    t = ' | '.join(titles)
    if re.search(r'\b(?:incoming|future)\s+(?:\w+\s+){0,5}professor\b', t, re.I) \
            or re.search(r'professor\W{0,3}\(?\s*(?:arriving|joining|starting)\b', t, re.I):   # 'Associate Professor (Arriving January 2027)' (UW Allen 2026-11-22)
        return 'other'  # an announced future appointment is not a dated faculty appointment
    for r, rx in RANKS:
        if extra and extra.get(r):
            rx = f'(?:{rx})|(?:{extra[r]})'
        if re.search(rx, t, re.I):
            # A charter can explicitly identify local ladder titles such as
            # University Lecturer. Retain the earlier emeritus/visiting guards.
            if r == 'lecturer' and extra and extra.get('ladder') and re.search(extra['ladder'], t, re.I):
                continue
            return r
    return 'other'


def listing_rank(titles, dept_titles, kind=None, extra=None):
    """Classify titles, retaining explicit courtesy, adjunct or emeritus slot context."""
    rank = rank_of(dept_titles, extra) if dept_titles else 'other'
    if rank == 'other':
        rank = rank_of(titles, extra)
    return kind if kind in ('courtesy', 'adjunct', 'emeritus') and rank == 'ladder' else rank


def page_links(page, e):
    """The entry's homepage / profile links as absolute URLs of the listed page (a Wayback capture resolves against its original URL):
    UW listings link '/people/marina-meila' and '/people/faculty/profile/jmankoff' relatively, which the website register then read as
    a site (2026-11-22). A link that is not http(s) after joining is dropped. homepage is always present (None when there is none)."""
    base = re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', page or '')
    out = {}
    for f in ('homepage', 'profile'):
        if e.get(f):
            u = urllib.parse.urljoin(base, e[f])
            if urllib.parse.urlsplit(u).scheme in ('http', 'https'):
                out[f] = u
    out.setdefault('homepage', None)
    return out


def quote_of(flat, e, raw=None):
    if 'quote_parts' in e:
        parts = e['quote_parts']
        if not isinstance(parts, list) or not parts or any(not isinstance(p, str) or not p.strip() for p in parts):
            return None
        parts = [' '.join(p.split()) for p in parts]
        if (any(p not in flat for p in parts) or e['name_listed'] not in parts[0]
                or any(not any(t in p for p in parts) for t in e['titles'])):
            return None
        # Name and title can be separated by contact details or a biography.
        # Each excerpt is verbatim; an explicit omission never retains either.
        return ' [...] '.join(parts)
    if 'quote_raw' in e and raw is not None:
        quote = e['quote_raw']
        return quote if quote in raw and e['name_listed'] in quote and all(t in quote for t in e['titles']) else None
    if 'quote' in e:
        # A card-specific quote avoids an earlier navigation copy of the name.
        # Require the literal source string to include its stated role.
        quote = ' '.join(e['quote'].split())
        return quote if (quote and quote in flat and e['name_listed'] in quote
                         and all(t in quote for t in e['titles'])) else None
    shown = e.get('quote_name') or e['name_listed']  # a format whose page prints the name in another order than name_listed (CMU CSD 2016-2018: 'Acar Umut' in two cells) names the printed form
    i = flat.find(shown)
    if i < 0:
        return None
    end = i + len(shown)
    for t in e['titles']:
        j = flat.find(t, end)
        if j >= 0 and j - end < 400:
            end = j + len(t)
    return flat[i:end]


def live_listing_rows(key, cfg, rw, tm, title_filters, kind_of):
    """Import reviewed saved live pages; dates and hashes come from the raw store, never the wall clock.

    sources: [{dept, slot, format?, complete, expected_entries, pages: [{url, sha256, fetched_at?}]}].
    A group explicitly reviews all pages of one listing. Incomplete groups supply sourced person rows, but
    never an ok coverage entry. This reads cached bytes only and does not fetch or create archive plan rows.
    """
    manifest = P.data('live-listing-sources.json', key)
    rows, n, coverage = [], collections.Counter(), []
    if not manifest.exists():
        return rows, n, coverage
    sources = json.loads(manifest.read_text())['sources']
    slots = {(d['code'], s['slot']) for d in S.listing_units(cfg) for s in d.get('listings') or []}
    db = P.data('school-captures.sqlite', key)
    with sqlite3.connect(f'file:{db}?mode=ro', uri=True) as c:
        for source in sources:
            dept, slot = source['dept'], source['slot']
            if (dept, slot) not in slots:
                raise ValueError(f'live listing names an unknown department/slot: {dept}/{slot}')
            if not source.get('pages'):
                raise ValueError(f'live listing has no reviewed pages: {slot}')
            complete = source.get('complete') is True
            expected = source.get('expected_entries')
            if complete and (type(expected) is not int or expected < 1):
                raise ValueError(f'complete live listing needs a positive expected_entries: {slot}')
            def normalized(url):
                parsed = urllib.parse.urlsplit(url)
                query = urllib.parse.urlencode(sorted(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)))
                return parsed._replace(query=query, fragment='').geturl()
            reviewed_urls = {normalized(p['url']) for p in source['pages']}
            group_rows, buckets = [], set()
            for page in source['pages']:
                url = page['url']
                cached = c.execute('select fetched_at,status,sha256,raw_zlib,content_type from live where url=?', (url,)).fetchone()
                if not cached or cached[1] != 200 or not cached[3]:
                    raise ValueError(f'live listing lacks a saved HTTP 200 body: {url}')
                fetched, _, sha, raw, ct = cached
                data = zlib.decompress(raw)
                if page['sha256'] != sha or hashlib.sha256(data).hexdigest() != sha:
                    raise ValueError(f'live listing hash mismatch: {url}')
                if page.get('fetched_at', fetched) != fetched:
                    raise ValueError(f'live listing fetch date mismatch: {url}')
                observed = datetime.fromisoformat(fetched.replace('Z', '+00:00'))
                year, half = observed.year, ('H1' if observed.month <= 6 else 'H2')
                buckets.add((year, half))
                html = data.decode('utf-8', 'replace')
                missing = {normalized(u) for u in LF.page_links(html, url).values()} - reviewed_urls
                if complete and missing:
                    raise ValueError(f'complete live listing has unreviewed linked pages: {slot}: {sorted(missing)}')
                fmt, entries = LF.parse(html, source.get('format'))
                flat = ' '.join(' '.join(t for _, t in html_extract.blocks(data, ct, url)).split())
                n[f'live_captures_{fmt}'] += 1
                for entry in entries:
                    if slot in title_filters and not any(title_filters[slot].search(t) for t in entry['titles']):
                        n['entries_outside_title_filter'] += 1
                        continue
                    quote = quote_of(flat, entry)
                    if not quote:
                        n['entries_without_quote'] += 1
                        continue
                    titles = entry['titles']
                    dt = [t for t in titles if tm[dept].search(t)]
                    links = {f: urllib.parse.urljoin(url, entry[f]) for f in ('homepage', 'profile') if entry.get(f)}
                    links = {f: u for f, u in links.items() if urllib.parse.urlsplit(u).scheme in ('http', 'https')}
                    group_rows.append(dict(name=given_first(entry['name_listed']), name_listed=entry['name_listed'], dept=dept,
                                           slot=slot, kind=kind_of[slot], year=year, half=half, observed=observed.strftime('%Y%m%d%H%M%S'),
                                           titles=titles, dept_title=dt, rank=listing_rank(titles, dt, kind_of[slot], rw), division=entry.get('division'),
                                           homepage=links.pop('homepage', None), **links, capture_url=url, sha256=sha, quote=quote,
                                           source_kind='live', fetched_at=fetched))
            if len(buckets) != 1:
                raise ValueError(f'live listing pages must belong to one observed half-year: {slot}')
            if expected is not None and len(group_rows) != expected:
                raise ValueError(f'live listing entry count mismatch for {slot}: reviewed {expected}, parsed {len(group_rows)}')
            year, half = next(iter(buckets))
            coverage.append((dept, year, f'{slot} live {half}', 'ok' if complete else 'partial: reviewed live listing is incomplete'))
            rows.extend(group_rows)
            n['live_rows'] += len(group_rows)
    return rows, n, coverage


def catalog_listing_coverage(key):
    """Accept a dated official catalog roster only after checking its saved original and every reviewed role line.

    These catalogs print initials in some years. They establish source coverage here; person identity and
    appointment periods remain separate review decisions in later stages.
    """
    manifest = P.data('catalog-listing-sources.json', key)
    if not manifest.exists():
        return []
    if key == 'utaustin':
        _record, _entries = utaustin_catalog_entries()
        return [('CS', 2018, 'official catalog spring 2018', 'ok')]
    data = json.loads(manifest.read_text())
    assert data['school'] == key
    db = P.data('catalog-captures.sqlite', key)
    out = []
    with sqlite3.connect(f'file:{db}?mode=ro', uri=True) as c:
        for record in data['records']:
            year, url, sha = record['start_year'], record['source_url'], record['raw_sha256']
            saved = c.execute('select year,status,sha256,raw_zlib,content_type from captures where url=?', (url,)).fetchone()
            if not saved or saved[0] != year or saved[1] != 200 or saved[2] != sha:
                raise ValueError(f'catalog source metadata mismatch: {key} {year} {url}')
            raw = zlib.decompress(saved[3])
            if hashlib.sha256(raw).hexdigest() != sha:
                raise ValueError(f'catalog source hash mismatch: {key} {year} {url}')
            if raw.startswith(b'%PDF-'):
                with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
                    f.write(raw); f.flush()
                    text = subprocess.run(['pdftotext', '-layout' if year == 2016 else '-raw', f.name, '-'],
                                          capture_output=True, check=True, text=True).stdout
            elif 'html' in (saved[4] or '').lower():
                text = BeautifulSoup(raw, 'html.parser').get_text(' ', strip=True)
            else:
                raise ValueError(f'catalog source is neither a PDF nor HTML: {key} {year} {url}')
            flat = ' '.join(text.split())
            lines = record['role_lines']
            if not lines or not any(x.startswith('Professors:') for x in lines) or not any(x.startswith('Assistant Professors:') for x in lines):
                raise ValueError(f'catalog lacks a reviewed CS faculty section: {key} {year}')
            if any(' '.join(line.split()) not in flat for line in lines):
                raise ValueError(f'catalog role line missing from saved original: {key} {year}')
            out.append(('CS', year, f'official catalog {year}–{year + 1}', 'ok'))
    return out


def utaustin_catalog_entries():
    """Validate the immutable UT catalog and its complete CS faculty entry set."""
    key = 'utaustin'
    manifest = P.data('catalog-listing-sources.json', key)
    data = json.loads(manifest.read_text())
    assert data['school'] == key and len(data['records']) == 1
    record = data['records'][0]
    assert record['source_type'] == 'official_UT_undergraduate_catalog'
    assert record['start_year'] == 2018 and record['academic_year'] == '2018–2020'
    db = P.data('catalog-captures.sqlite', key)
    with sqlite3.connect(f'file:{db}?mode=ro', uri=True) as c:
        saved = c.execute('select year,status,sha256,raw_zlib,content_type from captures where url=?',
                          (record['source_url'],)).fetchone()
    if not saved or saved[:3] != (2018, 200, record['raw_sha256']) or 'html' not in (saved[4] or '').lower():
        raise ValueError('UT Austin 2018 catalog source metadata mismatch')
    raw = zlib.decompress(saved[3])
    if hashlib.sha256(raw).hexdigest() != record['raw_sha256']:
        raise ValueError('UT Austin 2018 catalog source hash mismatch')
    soup = BeautifulSoup(raw, 'html.parser')
    if 'The following faculty list represents those appointed in the 2018 spring semester.' not in soup.get_text(' ', strip=True):
        raise ValueError('UT Austin catalog does not establish spring 2018 appointment date')
    entries = []
    for p in soup.select('p.faculty_entry'):
        if not any(x.get_text(' ', strip=True) == 'Computer Science' for x in p.select('.faculty_dept')):
            continue
        name = p.select_one('.faculty_name')
        title = p.select_one('.faculty_title')
        if not name:
            raise ValueError('UT Austin catalog has a CS faculty entry without a name')
        entries.append((name.get_text(' ', strip=True), title.get_text(' ', strip=True) if title else ''))
    digest = hashlib.sha256('\n'.join('\t'.join(x) for x in sorted(entries)).encode()).hexdigest()
    if len(entries) != record['cs_entry_count'] or len(set(entries)) != len(entries) or digest != record['cs_entries_sha256']:
        raise ValueError('UT Austin catalog CS faculty entry review mismatch')
    return record, entries


def washu_catalog_listing_coverage(key):
    """Count only complete, source-checked faculty sections in dated WashU bulletins.

    Academic editions establish a roster for their start year. They do not
    establish an individual person's appointment dates or identity.
    """
    return [(dept, year, slot, status) for dept, year, slot, status, _ in _washu_bulletin_sections(key)]


# Rank headings of the McKelvey graduate Bulletin faculty sections (2016-17 .. 2019-20), longest first. A heading is
# only read as one where an entry's name follows it directly (a title such as 'Fullgraf Professor in the Department'
# sits after the profile link, never before a name).
WASHU_BULLETIN_HEADS = [
    ('Associate Endowed Professors', 'ladder'), ('Associate Endowed Professor', 'ladder'), ('Assistant Endowed Professors', 'ladder'),
    ('Assistant Endowed Professor', 'ladder'), ('Endowed Professors', 'ladder'), ('Endowed Professor', 'ladder'),
    ('Faculty Chair', 'ladder'), ('Senior Professors', 'ladder'), ('Senior Professor', 'ladder'), ('Senior Emeritus Professor', 'emeritus'), ('Professor Emeritus', 'emeritus'), ('Professors Emeriti', 'emeritus'), ('Emeriti Faculty', 'emeritus'),
    ('Research Associate Professors', 'research'), ('Research Assistant Professors', 'research'), ('Research Associate Professor', 'research'),
    ('Research Assistant Professor', 'research'), ('Research Professors', 'research'), ('Research Faculty', 'research'),
    ('Professors of the Practice', 'teaching'), ('Professor of the Practice', 'teaching'), ('Professors of Practice', 'teaching'),
    ('Professor of Practice', 'teaching'), ('Senior Lecturers', 'lecturer'), ('Senior Lecturer', 'lecturer'), ('Lecturers', 'lecturer'),
    ('Lecturer', 'lecturer'), ('Instructors', 'lecturer'),
    ('Associate Professors', 'ladder'), ('Assistant Professors', 'ladder'), ('Joint Faculty', 'courtesy'),
    ('Affiliated Faculty', 'courtesy'), ('Adjunct Faculty', 'adjunct'), ('Visiting Faculty', 'visiting'), ('Professors', 'ladder'),
]
_WB_HEAD = re.compile(r'(?<!\S)(' + '|'.join(re.escape(h) for h, _ in WASHU_BULLETIN_HEADS) + r')(?=\s)')
_WB_DEGREE = re.compile(r'(?<!\S)(?:PhD|DSc|ScD|MD|MS|BS|MA|MBA|JD|DPhil|MSc|BA|BSE|MSE|DEng|EdD)(?=,)')
_WB_LINK = re.compile(r'\((https?://[^)]*)\)')
_WB_NAME_TOKEN = re.compile(r'''^(?:[A-Z][A-Za-zÀ-ÿ'’\-]*[a-zà-ÿ]|[A-Z]{1,2}|[A-Z]\.|[A-Z][a-z]{0,3}\.|Jr\.?|II|III|IV|\([A-Z][a-z]+\)|"[A-Z][a-z]+"|'[A-Z][a-z]+')$''')
_WB_MIDDLE = re.compile(r'''^(?:[A-Z]\.|Jr\.?|II|III|IV|\([A-Z][a-z]+\)|"[A-Z][a-z]+"|'[A-Z][a-z]+')$''')  # a token that marks a run of 3+ as one name
# Printed names of three or more words with no initial (the generic rule keeps the last two words of such a run).
WASHU_BULLETIN_LONG_NAMES = {'Tzyh Jong Tarn', 'Abhinav Kumar Jha'}
# Entries whose endowed title sits between the name and the degree, without a profile link: read by name (reviewed 2026-11-23).
WASHU_BULLETIN_TITLED = ('Mark A. Franklin', 'R. Martin Arthur')
# A printed short form whose own Bulletin profile link is the person's official profile page under the full name the
# later directories list (engineering.wustl.edu/faculty/I-Ting-Angelina-Lee.html): the row takes that name; name_listed
# and the quote keep the printed form (reviewed 2026-11-23).
WASHU_BULLETIN_PROFILE_NAMES = {'I-Ting-Angelina-Lee': 'I-Ting Angelina Lee'}
_WB_NOT_NAME = {'Professor', 'Professors', 'Faculty', 'Chair', 'Endowed', 'Associate', 'Assistant', 'Senior', 'Research', 'Lecturer',
                'Lecturers', 'Emeriti', 'Practice', 'Joint', 'Affiliated', 'Adjunct', 'Visiting', 'Instructors', 'Bulletin', 'Engineering',
                'Science', 'Sciences', 'School', 'University', 'Institute', 'Department', 'Principal', 'Distinguished', 'Dean', 'Director'}
_WB_INLINE_TITLE = re.compile(r'^,\s*((?:Principal |Senior )?Lecturer|Teaching Professor|Professor of the Practice)\s*$')


def _wb_name_before(text, end):
    """The printed name that ends at text[:end]: the longest run (2-5) of name-like tokens before it, or None."""
    toks = list(re.finditer(r'\S+', text[:end]))
    run = []
    for m in reversed(toks):
        t = m.group(0)
        if t in _WB_NOT_NAME or not _WB_NAME_TOKEN.match(t) or len(run) == 5:
            break
        run.insert(0, m)
    while run and re.match(r'^(?:(?:Jr\.?|II|III|IV)$|[("\'])', run[0].group(0)):  # a run never opens on a suffix or a nickname
        run.pop(0)
    if len(run) < 2:
        return None
    return run


def _wb_trim(run, slug=None):
    """Drop the words of the previous entry (its institution or research areas) from the front of a name run.

    With a named profile link: the name starts at the first word the link's file name shares (an initial before it stays).
    Otherwise a run of three or more words keeps only its last two, unless a middle initial, suffix or nickname marks the
    whole run as one printed name ('Jerome R. Cox Jr.') or the run is a reviewed long name.
    """
    words = [m.group(0) for m in run]
    if slug:
        parts = [re.sub(r'[^a-z]', '', p) for p in re.split(r'[-_ ]', slug.lower())]
        hit = [i for i, w in enumerate(words) if (k := re.sub(r'[^a-z]', '', w.lower())) and len(k) >= 2
               and any(p and (p.startswith(k[:3]) or k.startswith(p[:3])) for p in parts)]
        if hit and hit[0] < len(words) - 1:  # the link names the given name: the printed name starts there
            i = hit[0]
            if i > 0 and re.match(r'^[A-Z]\.$', words[i - 1]):
                i -= 1
            return run[i:]
        if not hit:
            return None
        # only the family name agrees ('Bill-Siever' for William Siever): read the run like an unlinked one
    for i in range(len(words) - 1):
        tail = ' '.join(words[i:])
        if tail in WASHU_BULLETIN_LONG_NAMES or len(words) - i == 2 or any(_WB_MIDDLE.match(w) for w in words[i + 1:]):
            if i > 0 and re.match(r'^[A-Z]\.$', words[i - 1]):  # a leading initial ('I. Norman Katz')
                i -= 1
            return run[i:]
    return None


def _wb_name(text, end, slug=None):
    run = _wb_name_before(text, end)
    run = _wb_trim(run, slug) if run else None
    if not run or len(run) < 2:
        return None
    return run[0].start(), ' '.join(m.group(0) for m in run)


def washu_bulletin_entries(text):
    """Person entries of one WashU Bulletin faculty section (whitespace-collapsed, verbatim-verified text).

    Every entry is 'Name (profile link)[, Title] [Title] Degree, Institution Areas' or, without a link,
    'Name[, Title] Degree, ...'. A link entry's name must agree with the link's file name (family name) when the
    link carries one. The rank comes from the last rank heading that directly precedes an entry's name.
    Returns [{name, start, end, rank, heading, titles, profile}] in text order, and the degree anchors not
    attributed to any entry (an entry the pattern could not read; the caller reports them).
    """
    entries, unread = [], []
    links = [(m.start(), m.end(), re.sub(r'\s+', '', m.group(1))) for m in _WB_LINK.finditer(text)]
    degrees = [m.start() for m in _WB_DEGREE.finditer(text)]
    anchors = sorted([(s, 'link', (e, url)) for s, e, url in links] + [(d, 'degree', None) for d in degrees])
    open_link = None  # a link entry waits for its own degree
    for pos, kind, extra in anchors:
        if kind == 'link':
            slug = urllib.parse.unquote(extra[1].rsplit('/', 1)[-1].split('.aspx')[0].split('.html')[0])
            named = re.search('[A-Za-z]{3}', slug) and not re.search(r'faculty|default', slug, re.I)
            got = _wb_name(text, pos, slug if named else None)
            if not got:
                unread.append(dict(pos=pos, why=f'no printed name before the link {slug!r}'))
                open_link = None
                continue
            start, name = got
            entries.append(dict(name=name, start=start, end=extra[0], profile=extra[1], titles=[]))
            open_link = entries[-1]
            continue
        if open_link is not None:  # this degree closes the link entry; the text between is its title
            between = text[open_link['end']:pos].strip()
            if between:
                open_link['titles'].append(between.lstrip(', ').strip())
            open_link['end'] = pos
            open_link = None
            continue
        if re.search(r'(?:PhD|DSc|ScD|MD|MS|BS|MA|MBA|JD|MSc|BA),\s*$', text[:pos]):  # 'MD, PhD,': a second degree of one entry
            continue
        titled = [n for n in WASHU_BULLETIN_TITLED if (i := text.rfind(n + ' ', 0, pos)) >= 0 and i > (entries[-1]['end'] if entries else -1)]
        if titled:
            i = text.rfind(titled[0] + ' ', 0, pos)
            entries.append(dict(name=titled[0], start=i, end=pos, profile=None, titles=[text[i + len(titled[0]):pos].strip()]))
            continue
        m = re.search(r',\s*(?:Principal |Senior )?Lecturer\s*$', text[:pos])  # 'Steve Cole, Senior Lecturer PhD,'
        cut = m.start() if m else pos
        got = _wb_name(text, cut)
        if not got:
            unread.append(dict(pos=pos, why='no printed name before the degree'))
            continue
        start, name = got
        title = _WB_INLINE_TITLE.match(text[cut:pos]) if m else None
        entries.append(dict(name=name, start=start, end=pos, profile=None, titles=[title.group(1)] if title else []))
    heads = [(m.start(), m.end(), m.group(1)) for m in _WB_HEAD.finditer(text)]
    starts = {e['start'] for e in entries}
    valid = [(s, h) for s, e, h in heads if any(st == e + 1 for st in starts)]  # a heading directly followed by a name
    rank_of_head = dict(WASHU_BULLETIN_HEADS)
    for e in entries:
        before = [h for s, h in valid if s < e['start']]
        e['heading'] = before[-1] if before else None
        e['rank'] = rank_of_head.get(e['heading'], 'other')
        if any(re.search(r'\bLecturer\b', t) for t in e['titles']):
            e['rank'] = 'lecturer'
    return entries, unread


def washu_bulletin_person_rows(key):
    """Person rows from the verified 2016-17 .. 2019-20 WashU Bulletin faculty sections (lab hunt 2026-11-23).

    The sections are checked against the stored PDF bytes by _washu_bulletin_sections (the same check as the
    roster coverage). Each person is one row for the edition's start year, the year the document prints its date;
    the row's quote is the verbatim entry text, from the printed name through the profile link (or the degree).
    """
    out = []
    for dept, year, slot, _, record in _washu_bulletin_sections(key):
        text = ' '.join(record['quote'].split())
        entries, unread = washu_bulletin_entries(text)
        for u in unread:
            print(json.dumps(dict(washu_bulletin_unread=record['academic_edition'], dept=dept, **u, context=text[max(0, u['pos'] - 80):u['pos'] + 10])), flush=True)
        for e in entries:
            quote = text[e['start']:e['end']].strip()
            assert quote in text and quote.startswith(e['name'])
            titles = ([e['heading']] if e['heading'] else []) + e['titles']
            tail = (e['profile'] or '').rsplit('/', 1)[-1].split('.aspx')[0]
            name = WASHU_BULLETIN_PROFILE_NAMES.get(tail, e['name'])
            out.append(dict(name=name, name_listed=e['name'], dept=dept, slot=slot, kind='main', year=year, half='academic_year',
                            observed=record['printed_date'], titles=titles, dept_title=titles, rank=e['rank'], division=None, homepage=None,
                            **({'profile': e['profile']} if e['profile'] else {}), capture_url=record['source_url'], sha256=record['sha256'],
                            quote=quote, source_kind='official_graduate_bulletin', identity_status='full_name_as_printed_unmerged'))
    return out


_WASHU_SECTIONS = {}


def _washu_bulletin_sections(key):
    """The verified (dept, year, slot, status, record) of every 2016-19 WashU Bulletin faculty section (cached per key)."""
    if key != 'washu':
        return []
    manifest = P.data('historical-source-review.json', key)
    db = P.data('catalog-captures.sqlite', key)
    ck = (key, str(manifest), hashlib.sha256(manifest.read_bytes()).hexdigest(), str(db), db.stat().st_mtime_ns if db.exists() else None)
    if ck not in _WASHU_SECTIONS:   # the coverage and the person rows read the same verified sections once per build
        _WASHU_SECTIONS[ck] = _washu_bulletin_sections_read(key)
    return _WASHU_SECTIONS[ck]


def _washu_bulletin_sections_read(key):
    manifest = P.data('historical-source-review.json', key)
    data = json.loads(manifest.read_text())
    assert data['school'] == key
    db = P.data('catalog-captures.sqlite', key)
    expected = {(year, dept) for year in range(2016, 2020) for dept in ('BME', 'CSE', 'ESE')}
    found, out = set(), []
    with sqlite3.connect(f'file:{db}?mode=ro', uri=True) as c:
        for record in data['records']:
            year = int(record['academic_edition'][:4])
            dept = record['dept']
            if (year, dept) not in expected:
                continue
            if (year, dept) in found or record['academic_edition'] != f'{year}-{str(year + 1)[-2:]}':
                raise ValueError(f'duplicate or misdated WashU catalog section: {year} {dept}')
            found.add((year, dept))
            url, sha = record['source_url'], record['sha256']
            saved = c.execute('select year,status,sha256,raw_zlib,content_type from captures where url=?', (url,)).fetchone()
            if not saved or saved[:3] != (year, 200, sha) or saved[4] != 'application/pdf':
                raise ValueError(f'WashU catalog source mismatch: {year} {dept}')
            raw = zlib.decompress(saved[3])
            if not raw.startswith(b'%PDF-') or hashlib.sha256(raw).hexdigest() != sha:
                raise ValueError(f'WashU catalog hash mismatch: {year} {dept}')
            with tempfile.NamedTemporaryFile(suffix='.pdf') as f:
                f.write(raw); f.flush()
                text = subprocess.run(['pdftotext', '-raw', f.name, '-'],
                                      capture_output=True, check=True, text=True).stdout
            quote = ' '.join(record['quote'].split())
            if len(quote) < 1000 or not quote.startswith('Faculty Chair ') or quote not in ' '.join(text.split()):
                raise ValueError(f'WashU faculty section absent or partial: {year} {dept}')
            out.append((dept, year, f'official graduate bulletin {year}–{year + 1}', 'ok', record))
    if found != expected:
        raise ValueError(f'WashU catalog sections missing: {sorted(expected - found)}')
    return out


def catalog_person_rows(key):
    """Import full-name graduate catalog role lists after catalog_listing_coverage verified the originals.

    The undergraduate editions mostly print initials; they remain source coverage and review leads, not
    guessed person records. The graduate rows retain the academic year without inventing a capture day.
    """
    manifest = P.data('catalog-listing-sources.json', key)
    if not manifest.exists():
        return []
    if key == 'utaustin':
        record, entries = utaustin_catalog_entries()
        rw = (S.get(key).get('census') or {}).get('rank_words') or {}
        return [dict(name=name, name_listed=name, dept='CS', slot='official catalog spring 2018',
                     kind='main', year=2018, half='spring', observed='2018 spring',
                     titles=[title], dept_title=[title], rank=listing_rank([title], [title], 'main', rw),
                     division=None, homepage=None, capture_url=record['source_url'],
                     sha256=record['raw_sha256'], quote=f'{name}, {title}, Computer Science',
                     source_kind='official_undergraduate_catalog', identity_status='full_name_as_printed_unmerged')
                for name, title in entries if title]
    ranks = {'Professors': 'ladder', 'Associate Professors': 'ladder', 'Assistant Professors': 'ladder',
             'Emeriti Faculty': 'emeritus', 'Visiting Faculty': 'visiting', 'Research Professors': 'research',
             'Collegiate Associate Professors': 'teaching', 'Collegiate Assistant Professors': 'teaching',
             'Assistant Professor of Practice': 'teaching', 'Associate Professor of Practice': 'teaching',
             'Instructors': 'lecturer'}
    out = []
    for record in json.loads(manifest.read_text())['records']:
        if record['source_type'] != 'official_VT_graduate_catalog':
            continue
        year = record['start_year']
        for line in record['role_lines']:
            label, _, body = line.partition(':')
            rank = ranks.get(label)
            if not rank:
                continue
            for token in body.split(';'):
                name = ' '.join(token.strip(' .').split())
                if len(name.split()) < 2:
                    continue
                out.append(dict(name=name, name_listed=name, dept='CS', slot='official graduate catalog',
                                kind='main', year=year, half='academic_year', observed=str(year),
                                titles=[label], dept_title=[label], rank=rank, division=None,
                                homepage=None, capture_url=record['source_url'], sha256=record['raw_sha256'],
                                quote=line, source_kind='official_graduate_catalog',
                                identity_status='full_name_as_printed_unmerged' if len(name.split()[0].strip('.')) > 1 else 'initial_as_printed_unmerged'))
    return out


def vt_paired_directory_rows(key):
    """2016–21 CS initials resolved by a unique same-year, full-name registrar entry.

    Both originals and both exact quotes must still verify; this is a draft
    census identity, not a PI, lab, or paper admission.
    """
    if key != 'vt':
        return []
    manifest = P.data('faculty-directory-identity-matches.json', key)
    if not manifest.exists():
        return []
    doc = json.loads(manifest.read_text())
    assert doc['school'] == key
    sources = {r['start_year']: r for r in json.loads((P.data('catalog-listing-sources.json', key)).read_text())['records']}
    store = P.ROOT / doc['original_capture_store']
    out = []
    with sqlite3.connect(f'file:{store}?mode=ro', uri=True) as db:
        pages = {}
        for year, url, sha, blob in db.execute('select year,url,sha256,body_zlib from captures'):
            raw = zlib.decompress(blob)
            assert hashlib.sha256(raw).hexdigest() == sha
            paragraphs = {' '.join(p.stripped_strings) for p in BeautifulSoup(raw, 'html.parser').find_all('p')}
            pages[year] = (url, sha, paragraphs)
    for r in doc['records']:
        if not r['admitted_to_draft_census']:
            assert r['status'] != 'exact_year_unique'
            continue
        assert r['status'] == 'exact_year_unique' and len(r['same_year_full_name_entries']) == 1
        year = r['year']
        catalog = sources[year]
        assert r['catalog_source_url'] == catalog['source_url'] and r['catalog_source_sha256'] == catalog['raw_sha256']
        assert r['catalog_line'] in catalog['role_lines'] and r['role'] in ('Professors', 'Associate Professors', 'Assistant Professors')
        person = r['same_year_full_name_entries'][0]
        url, sha, paragraphs = pages[year]
        assert person['url'] == url and person['raw_sha256'] == sha and person['quote'] in paragraphs
        name = person['name']
        out.append(dict(name=name, name_listed=name, dept='CS', slot='official catalog + faculty directory',
                        kind='main', year=year, half='academic_year', observed=str(year),
                        titles=[r['role']], dept_title=[r['role']], rank='ladder', division=None,
                        homepage=None, capture_url=catalog['source_url'], sha256=catalog['raw_sha256'],
                        quote=r['catalog_line'], source_kind='official_catalog_directory_pair',
                        identity_status='same_year_official_directory_match',
                        identity_basis=dict(url=url, sha256=sha, quote=person['quote'])))
    assert len(out) == doc['by_status']['exact_year_unique']
    return out


def main(key):
    cfg = S.get(key)
    rw = (cfg.get('census') or {}).get('rank_words') or {}
    tm = {d['code']: re.compile(d.get('title_match') or r'.', re.I) for d in S.listing_units(cfg)}
    eras = [(s['slot'], s.get('from') or '0', s.get('to') or '9', s.get('format')) for d in S.listing_units(cfg) for s in d.get('listings') or []]
    title_filters = {s['slot']: re.compile(s['title_filter'], re.I) for d in S.listing_units(cfg) for s in d.get('listings') or [] if s.get('title_filter')}
    kind_of = {s['slot']: s['kind'] for s in S.listing_slots(key)}
    # coverage_only slots (ZJU English-site faculty directory, pinyin names): the capture must parse and counts for coverage.json, but its rows are not people of the
    # census (they would double every Chinese-named person); they go to rows-coverage-only.json instead.
    coverage_only = {s['slot'] for d in S.listing_units(cfg) for s in d.get('listings') or [] if s.get('coverage_only')}
    side_rows = []
    db = P.data('listings-captures.sqlite', key)
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True) if db.exists() else None
    has_pages = bool(c and c.execute("select 1 from sqlite_master where name='plan_pages'").fetchone())
    rows, n = [], collections.Counter()
    cov = collections.defaultdict(lambda: collections.defaultdict(dict))
    has_plan = bool(c and c.execute("select 1 from sqlite_master where name='plan'").fetchone())
    plan = c.execute('select slot, dept, year, half, capture_url, status, reason from plan order by slot, year, half') if has_plan else []
    for slot, dept, year, half, cap, status, reason in plan:
        cov[dept][year][f'{slot} {half}'] = status if status == 'ok' else f'{status}: {reason}'
        if status != 'ok':
            continue
        # a paged directory (R3, Georgia Tech friction 10) is one listing: the plan row's capture is page 0, plan_pages holds the other pages' captures
        pages = [r[0] for r in c.execute('select capture_url from plan_pages where slot=? and year=? and half=? order by page', (slot, year, half))] if has_pages else []
        parsed_entries = 0
        for cap in [cap] + pages:
            raw, sha, txt, ts = c.execute('select raw_zlib, sha256, text, wayback_timestamp from captures where capture_url=?', (cap,)).fetchone()
            h = wb_text(wb_body(raw))  # gunzipped when Wayback served it gzip-encoded
            flat = ' '.join((txt or '').split())
            m = re.search(r'/web/(\d{14})id_/', cap); obs = m.group(1) if m else ts
            # one slot can have several URL eras with different page formats: the era that holds the capture date names the format; a named
            # format that finds nobody falls back to detection (era boundaries overlap; UChicago friction #13: the last era's format won for the whole slot)
            named = [f for sl, a, b, f in eras if sl == slot and f and a <= obs[:8] <= b]
            fmt, es = LF.parse(h, named[0] if named else None)
            if not es and named:
                fmt, es = LF.parse(h)
            parsed_entries += len(es)
            n[f'captures_{fmt}'] += 1
            if LF.is_paged(h) and es and not pages:
                # a paged directory: this capture holds one page of several (UChicago CS 2017: 5 of ~45 people); the next pages may not be archived
                n['captures_paged'] += 1; print(json.dumps(dict(paged_listing=cap, entries=len(es))), flush=True)
            if not es:
                n['captures_without_entries'] += 1; print(json.dumps(dict(no_entries=cap, fmt=fmt)), flush=True)
            for e in es:
                # A school-wide listing can supply one department's rows without
                # making every other discipline ladder faculty in that department.
                # Filter here, after capture usability and all-page completeness.
                if slot in title_filters and not any(title_filters[slot].search(t) for t in e['titles']):
                    n['entries_outside_title_filter'] += 1
                    continue
                q = quote_of(flat, e, h)
                if not q:
                    n['entries_without_quote'] += 1; continue
                dt = [t for t in e['titles'] if tm.get(dept, re.compile('.')).search(t)]
                (side_rows if slot in coverage_only else rows).append(dict(name=given_first(e['name_listed']), name_listed=e['name_listed'], dept=dept, slot=slot, kind=kind_of.get(slot), year=int(obs[:4]),
                                 half=half, observed=obs, titles=e['titles'], dept_title=dt, rank=listing_rank(e['titles'], dt, kind_of.get(slot), rw), division=e.get('division'),
                                 **page_links(cap, e), capture_url=cap, sha256=sha, quote=q))
                n['coverage_only_rows' if slot in coverage_only else 'rows'] += 1
        if parsed_entries == 0:
            cov[dept][year][f'{slot} {half}'] = 'unusable: capture parses zero faculty entries'
    if c:
        c.close()
    live, live_counts, live_coverage = live_listing_rows(key, cfg, rw, tm, title_filters, kind_of)
    rows.extend(live)
    n.update(live_counts)
    n['rows'] += len(live)
    catalog_coverage = catalog_listing_coverage(key) + washu_catalog_listing_coverage(key)
    catalog_rows = catalog_person_rows(key) + washu_bulletin_person_rows(key)
    rows.extend(catalog_rows)
    n['catalog_rows'] += len(catalog_rows)
    n['rows'] += len(catalog_rows)
    paired_rows = vt_paired_directory_rows(key)
    rows.extend(paired_rows)
    n['paired_directory_rows'] += len(paired_rows)
    n['rows'] += len(paired_rows)
    for dept, year, slot, status in live_coverage + catalog_coverage:
        cov[dept][year][slot] = status
    out = P.data('rows.json', key)
    out.parent.mkdir(parents=True, exist_ok=True)  # listings/<key>/derived does not exist for a new school (UChicago friction #12)
    out.write_text(json.dumps(rows, indent=0, ensure_ascii=False))
    if side_rows or P.data('rows-coverage-only.json', key).exists():
        P.data_w('rows-coverage-only.json', key).write_text(json.dumps(side_rows, indent=0, ensure_ascii=False))
    P.data_w('coverage.json', key).write_text(json.dumps({d: {str(y): v for y, v in sorted(ys.items())} for d, ys in cov.items()}, indent=1))
    people = collections.defaultdict(set)
    for r in rows:
        people[r['dept']].add(r['name'])
    print(json.dumps(dict(n, people={d: len(v) for d, v in people.items()}, out=str(out))))


if __name__ == '__main__':
    main(sys.argv[1])
