"""A protocol school's faculty census, built from its dated department listings (protocol stages 2-3), in the census
format the builder reads (Stanford's st_census.py output), plus the small collection a school without a site collection
brings (hierarchy/<key>/collection.json.gz, the Berkeley/Stanford pattern).

persons   listings/<key>/rows.json (tools/listing_rows.py): one person per name (rows merged across departments, slots
          and years when the given-name/family-name pair matches, nicknames included: pi_hierarchy.Name), plus the
          accepted CS-related candidates of other units (census/<key>-additions.json, merged by the builder itself).
          Reviewed source-profile identities qualify ambiguous displayed names before name-based grouping.
rank      per year, the best rank the year's rows give (ladder > research > teaching > lecturer > adjunct > visiting >
          courtesy > emeritus > other); `rank` is the latest year's
PI        (protocol stage 3, owner rules 2026-10-21/22) in a department with coverage "full":
            ladder_faculty     a 2016-2026 listing row whose department title is a professor rank (assistant,
                               associate, full, collegiate or named), not courtesy, adjunct, visiting, research, teaching,
                               lecturer or emeritus; the quote is that row
            courtesy_faculty   a courtesy / affiliate appointment in the department whose same row also gives a professor
                               rank in the person's home unit (computing is the object or method of their work: the
                               department itself appointed them); the home unit goes to home-departments.json (stage 3)
          in a department with coverage "affiliated" (Michigan ECE): ladder_faculty as above AND an accepted decision in
          hierarchy/<key>/cs-related-review.json (computing is the object or method of their work); until reviewed the
          person is not a PI (`not_pi_reason` says so)
          research / teaching / lecturer / adjunct ranks and emeritus-only people: only with reviewed basis evidence
          (hierarchy/<key>/pi-basis-evidence.json: advises_phd | own_group with url + sha256 + quote)
listings  listings/<key>/listings.json: one row per (person, department, year): the year's first listing capture
          (rows the builder reads for R-PAP-01; rank_as_listed, emeritus, visiting flags)
-> census/<key>-faculty.json, census/<key>-report.md, hierarchy/<key>/collection.json.gz, listings/<key>/listings.json
usage: census_build.py <key>
"""
import collections, datetime, gzip, hashlib, json, re, sqlite3, sys, unicodedata, urllib.parse, zlib
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
from pi_hierarchy import Name, toks as _toks, nick_ok, EAST_ASIAN_FAMILY, nosuffix, SUFFIX  # noqa: F401,E402
from pihier.names import literal_cjk_name

ORDER = ['ladder', 'research', 'teaching', 'lecturer', 'adjunct', 'visiting', 'courtesy', 'emeritus', 'other']
# a title or an endowed-chair string is never a person's name or alias (ROADMAP #42)
CLONE_OF = re.compile(r'^Clone of\s+', re.I)  # Georgia Tech 2016: a cloned Drupal faculty card ('Clone of Hadi Esmaeilzadeh') is the same person, not a new one
TITLE_NAME = re.compile(r'\b(?:Chair|Chaired|Professor|Professorship|Endowed|Distinguished)\b')  # not Dean or Director: given names and surnames
HOME_PROF = re.compile(r'^(?:[A-Z][\w.\'\- ]+ )?(?:Assistant |Associate )?Professor(?! Emerit)(?: of [^,]+)?, (?!Electrical Engineering and Computer Science)(.+)$')


def toks(n):
    """Name tokens without a generational suffix ('Charles Isbell, Jr.' is charles/isbell). Read with the suffix as the family
    name, every 'X Jr.' of a school was one 'jr' family and nickname-equal first names merged them (Georgia Tech 2026-11-04:
    Isbell, Lever and Sutlief became one person)."""
    return nosuffix(_toks(n))


def has_suffix(n):
    return any(t in SUFFIX for t in _toks(n)[1:])  # at the end ('Moore II.') or inside ('Elliot II Moore'): listing formats differ


def display_name(rs, names, prefer_latin=False):
    """The latest listed spelling; when the person is also listed without the generational suffix, the latest such
    spelling ('Charles Isbell', not 'Charles Isbell Jr.': ROADMAP #42). prefer_latin (a school whose profile ids join a
    Latin and a native-script spelling, [census].profile_id_pattern): the latest spelling with no CJK letters when one exists."""
    plain = [r['name'] for r in rs if not has_suffix(r['name'])]
    pool = plain or [rs[-1]['name']]
    if prefer_latin:
        latin = [n for n in pool if not HAN_RUN.search(n)] or [r['name'] for r in rs if not HAN_RUN.search(r['name'])]
        if latin:
            return latin[-1]
    return pool[-1]


PRACTICE_TITLE = re.compile(r'Professor of (?:the )?Practice', re.I)  # teaching-stream: any year's title of a person with one keeps the home-unit opt-in off (Harvard Brennan: Associate Professor of Education 2020-23, Professor of Practice 2026)
HOME_PROF_OF = re.compile(r"^(?:[A-Z][\w.'\u201c\u201d\- ]+ )?(?:Assistant |Associate )?Professor of ([^,]+?)(?: and [A-Z](?:(?! and )[^,])* (?:Scholar|Director|Chair)\b.*)?$")  # 'Bessie Darling Massey Professor of Biomedical Engineering' (opt-in: [census].courtesy_title_of)
HOME_PROF_I = re.compile(HOME_PROF.pattern, re.I)  # 'Associate professor, Department of Philosophy' (lowercase p)
NOT_HOME_CLAUSE = re.compile(r'courtesy|affiliat|emerit|adjunct|visiting', re.I)
HOME_HEAD = re.compile(r'^(?:head|chair|director|dean)[^,]*, (.+)$', re.I)


def home_professor(title):
    """(match, home unit) when a courtesy row's title also gives a professor rank in the person's own unit, else (None, None).
    A title is one clause ('Professor of Medicine, Medical School') or several joined by ';' ('Professor, Bradley Department of
    Electrical and Computer Engineering; professor by courtesy, Department of Computer Science', the CS listing of a courtesy
    appointment): the courtesy / affiliate / emeritus clause is the appointment the department made, never the home rank. A named
    professorship without a unit ('Fred D. Durham Professor of Engineering; head, Kevin T. Crofton Department of ...') takes the
    unit of the head / chair clause that follows it. Learned 2026-11-18 (VT: 12 professors of other units were excluded because
    the whole title contained 'courtesy')."""
    if 'emerit' in title.lower():
        return None, None
    if 'courtesy' not in title.lower() and (m := HOME_PROF.match(title)):
        return m, m.group(1).strip()
    clauses = [c.strip() for c in re.split(r';\s*(?:and\s+)?', title) if c.strip()]
    for i, c in enumerate(clauses):
        if NOT_HOME_CLAUSE.search(c):
            continue
        if m := HOME_PROF_I.match(c):
            return m, m.group(1).strip()
        if re.search(r'\bprofessor\b', c, re.I) and not re.search(r'\bprofessor\b[^,]*,', c, re.I):
            for later in clauses[i + 1:]:
                if not NOT_HOME_CLAUSE.search(later) and (h := HOME_HEAD.match(later)):
                    return re.match(r'.*', c), h.group(1).strip()
    return None, None


def home_professor_of(title):
    """Opt-in ([census].courtesy_title_of, owner 2026-11-18, VT/JHU pattern): (match, unit) when a clause of a courtesy row's title is a professorship
    OF the home unit with no comma ('Assistant Professor of Statistics; Affiliate in Computer Science'). A Professor of the Practice is a teaching-stream
    title and never counts; courtesy / affiliate / emeritus / adjunct / visiting clauses are the appointment the department made."""
    if 'emerit' in title.lower():
        return None, None
    for c in (c.strip() for c in re.split(r';\s*(?:and\s+)?', title)):
        if c and not NOT_HOME_CLAUSE.search(c) and not PRACTICE_TITLE.search(c) and (m := HOME_PROF_OF.match(c)):
            return m, m.group(1).strip()
    return None, None


def slug(s):
    original = s
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-') or 'name-' + hashlib.sha256(original.encode()).hexdigest()[:24]


def read(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def reviewed_name_aliases(key):
    """Only explicitly sourced name pairs may override the ordinary name matcher."""
    doc = read(P.data('census-name-aliases.json', key), {}) or {}
    if not doc:
        return []
    assert doc['school'] == key
    from bs4 import BeautifulSoup
    out = []
    for item in doc['rows']:
        a, b, ev = item['name_a'], item['name_b'], item['evidence']
        if isinstance(ev, list):
            # Source-reviewed duplicate listing (surname-first old page, given-first new page; CUHK 2026-11-20): each item is a saved page
            # (hash and quote re-checked here, fail closed). The census keeps both spellings as separate rows: the pair is applied by the
            # builder as a `native_pi_merges` entry (pihier/census.py), and pi_records/stage_gate.pis_of group by it. Never a name-only merge.
            assert a != b and len(ev) >= 2, f'alias pair needs two evidence items: {a} / {b}'
            for e in ev:
                raw = (P.CODE / e['artifact']).resolve()
                assert raw.is_relative_to(P.CODE.resolve()) and hashlib.sha256(raw.read_bytes()).hexdigest() == e['sha256'], f'alias evidence hash: {e["url"]}'
                assert ' '.join(e['quote'].split()) in ' '.join(' '.join(BeautifulSoup(raw.read_bytes(), 'html.parser').stripped_strings).split()), f'alias evidence quote: {e["url"]}'
            continue
        assert a != b and (''.join(toks(a)[1:]) == ''.join(toks(b)[1:]) or toks(a)[-1] == toks(b)[-1])   # one family name; 'De Choudhury' / 'DeChoudhury' differ only by a space
        path = (P.ROOT / ev['raw_path']).resolve()
        assert path.is_relative_to(P.ROOT.resolve())
        if ev.get('kind') == 'shared_dblp_pid':   # both spellings are one DBLP person: the pinned dump record carries the ORCID and the school affiliation
            import gzip
            rec = json.loads(gzip.decompress(path.read_bytes()))['persons'][ev['pid_url']]
            core = {k: rec[k] for k in ('names', 'orcid', 'affiliations')}
            assert hashlib.sha256(json.dumps(core, sort_keys=True).encode()).hexdigest() == ev['sha256']
            assert ev['orcid'] in rec['orcid'] and ev['quote'] in ' | '.join(rec['affiliations'])
            out.append((a, b))
            continue
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == ev['sha256']
        text = ' '.join(BeautifulSoup(raw, 'html.parser').stripped_strings)
        assert ev['quote'] in text
        if ev.get('additional_quote'):
            assert ev['additional_quote'] in text
        out.append((a, b))
    return out


def profile_key(url):
    """Exact source profile identity, normalizing transport and repeated slashes only."""
    p = urllib.parse.urlsplit(url or '')
    if p.scheme not in ('http', 'https') or not p.netloc or p.query or p.fragment:
        return None
    return p.netloc.lower() + re.sub(r'/+', '/', p.path).rstrip('/')



def wayback_original(url):
    """The archived page's original URL of a Wayback capture URL (https://web.archive.org/web/<ts>id_/<original>)."""
    m = re.match(r'https?://web\.archive\.org/web/\d+[a-z_]*/(.+)$', url or '')
    return m.group(1) if m else url


def reviewed_source_names(key, rows, doc):
    """Canonicalize only exact reviewed source rows, including headings without a profile.

    A row binding proves its original and parsed heading, not bibliographic identity
    or employment continuity. A new observation of a reviewed spelling needs its
    own source review instead of silently gaining the canonical identity.
    """
    bindings = doc.get('source_names') or []
    if not bindings:
        return rows
    if doc.get('school') != key:
        raise ValueError('source-name review school mismatch')
    import listing_formats as LF
    from listing_rows import quote_of
    from school_web import body, wb
    def pointer(url):
        return profile_key(url) or url or None
    def row_key(url, sha, listed, profile, quote):
        return (url, sha, listed, pointer(profile), quote)
    mapping, spellings, canonical_names = {}, set(), set()
    qualified_profiles = {profile_key(item.get('profile')) for item in doc.get('profile_names') or []} - {None}
    db = P.data('listings-captures.sqlite', key)
    with sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True) as c:
        for item in bindings:
            name = item.get('canonical_name')
            if not isinstance(name, str) or not name.strip() or not item.get('evidence'):
                raise ValueError('source-name review lacks canonical name or evidence')
            canonical_names.add(name)
            for ev in item['evidence']:
                saved = c.execute('select http_status,sha256,raw_zlib,text from captures where capture_url=?', (ev['url'],)).fetchone()
                if not saved:   # a reviewed current (live) listing page lives in school-captures.sqlite's live table (tools/live_listing_manifest.py)
                    with sqlite3.connect(P.data('school-captures.sqlite', key).resolve().as_uri() + '?mode=ro', uri=True) as lc:
                        saved = lc.execute('select status,sha256,raw_zlib,text from live where url=?', (ev['url'],)).fetchone()
                if not saved or saved[0] != 200 or not saved[2] or saved[1] != ev['sha256'] or hashlib.sha256(zlib.decompress(saved[2])).hexdigest() != ev['sha256']:
                    raise ValueError('source-name evidence hash mismatch: ' + ev['url'])
                html = wb.text(body(saved[2]))
                _, entries = LF.parse(html, ev['format'])
                flat = ' '.join((saved[3] or '').split())
                if '/web/' not in ev['url']:   # a live page: the flat text listing_rows.live_listing_rows builds from the raw bytes
                    from school_web import extract as html_extract
                    flat = ' '.join(' '.join(t for _, t in html_extract.blocks(zlib.decompress(saved[2]), 'text/html', ev['url'])).split())
                if '/web/' not in ev['url']:   # a live page's rows carry absolute profile urls (listing_rows.live_listing_rows)
                    entries = [dict(e, profile=urllib.parse.urljoin(ev['url'], e['profile'])) if e.get('profile') else e for e in entries]
                else:   # a Wayback capture resolves relative profile links against its ORIGINAL url, as listing_rows does (UMD links '/people/hal3')
                    entries = [dict(e, profile=urllib.parse.urljoin(wayback_original(ev['url']), e['profile'])) if e.get('profile') else e for e in entries]
                matches = [e for e in entries if e['name_listed'] == ev['name_listed']
                           and pointer(e.get('profile')) == pointer(ev.get('profile'))
                           and quote_of(flat, e, html) == ev['quote']]
                if len({(e['name_listed'], pointer(e.get('profile')), quote_of(flat, e, html)) for e in matches}) != 1:
                    raise ValueError('source-name heading mismatch: ' + ev['url'])
                binding = row_key(ev['url'], ev['sha256'], ev['name_listed'], ev.get('profile'), ev['quote'])
                if binding in mapping:
                    raise ValueError('duplicate reviewed source-name row: ' + ev['url'])
                mapping[binding] = name
                spellings.add(ev['name_listed'])
    out = []
    for row in rows:
        listed = row.get('name_listed', row['name'])
        binding = row_key(row.get('capture_url'), row.get('sha256'), listed, row.get('profile'), row.get('quote'))
        if binding in mapping:
            name = mapping[binding]
            forms = list(dict.fromkeys([row['name'], listed]))
            row = dict(row, name=name, reviewed_profile_name=name, reviewed_name_forms=forms)
        elif (listed in spellings or row['name'] in canonical_names) and profile_key(row.get('profile')) not in qualified_profiles:
            raise ValueError('unreviewed source row for canonical faculty name: ' + listed)
        out.append(row)
    return out


def reviewed_profile_names(key, rows):
    """Apply sourced profile-qualified names before ordinary name grouping.

    A known ambiguous spelling with a new profile fails closed for review. No
    name-only alias is introduced, and literal source spellings/quotes remain.
    """
    doc = read(P.data('census-name-aliases.json', key), {}) or {}
    rows = reviewed_source_names(key, rows, doc)
    bindings = doc.get('profile_names') or []
    if not bindings:
        return rows
    if doc.get('school') != key:
        raise ValueError('profile-name review school mismatch')
    import listing_formats as LF
    from bs4 import BeautifulSoup
    from listing_rows import quote_of
    from school_web import body, wb
    mapping, reviewed_spellings = {}, set()
    db = P.data('listings-captures.sqlite', key)
    with sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True) as c:
        for item in bindings:
            profile = profile_key(item['profile'])
            name = item['canonical_name']
            spellings = item.get('listed_names') or []
            if not profile or not name.strip() or not spellings or not item.get('evidence'):
                raise ValueError('profile-name review lacks profile, name, spellings, or evidence')
            if profile in mapping:
                raise ValueError('duplicate reviewed source profile: ' + item['profile'])
            forms = item.get('source_forms') or list(spellings)
            if any(not any(sorted(toks(f)) == sorted(toks(n)) for n in spellings) for f in forms):
                raise ValueError('source form is not a reviewed name ordering')
            seen_forms = set()
            for ev in item['evidence']:
                saved = c.execute('select http_status,sha256,raw_zlib,text from captures where capture_url=?', (ev['url'],)).fetchone()
                if not saved or saved[0] != 200 or not saved[2] or saved[1] != ev['sha256'] or hashlib.sha256(zlib.decompress(saved[2])).hexdigest() != ev['sha256']:
                    raise ValueError('profile-name evidence hash mismatch: ' + ev['url'])
                html = wb.text(body(saved[2]))
                _, entries = LF.parse(html, ev['format'])
                matches = [e for e in entries if profile_key(e.get('profile')) == profile and e['name_listed'] == ev['name_listed']]
                flat = ' '.join((saved[3] or '').split())
                if len(matches) != 1 or ev['name_listed'] not in spellings or quote_of(flat, matches[0], html) != ev['quote']:
                    raise ValueError('profile-name source card mismatch: ' + ev['url'])
                cards = [card for card in BeautifulSoup(html, 'html.parser').select('.img-card--academic')
                         if (a := card.select_one('.img-card__title a')) and profile_key(a.get('href')) == profile]
                for card in cards:
                    text = ' '.join(card.get_text(' ', strip=True).split())
                    seen_forms.update(f for f in forms if f in text)
            if set(forms) - seen_forms:
                raise ValueError('source name form is absent from the reviewed profile card')
            mapping[profile] = (name, set(spellings), forms)
            reviewed_spellings.update(spellings)
    out = []
    for row in rows:
        profile = profile_key(row.get('profile'))
        listed = row.get('name_listed', row['name'])
        if row.get('reviewed_profile_name'):
            if profile in mapping and mapping[profile][0] != row['reviewed_profile_name']:
                raise ValueError('conflicting source-row and profile canonical names: ' + listed)
            out.append(row)
            continue
        if profile in mapping:
            name, spellings, forms = mapping[profile]
            if listed not in spellings:
                raise ValueError('unreviewed spelling at reviewed profile: ' + listed)
            row = dict(row, name=name, reviewed_profile_name=name, reviewed_name_forms=list(forms))
        elif listed in reviewed_spellings:
            raise ValueError('unreviewed source profile for ambiguous faculty name: ' + listed)
        out.append(row)
    return out


def reviewed_romanization(key):
    """{profile id: record} from reviewed/profile-romanization.json (tools/profile_romanization_school.py): a Latin name the person's OWN profile page states
    next to the native-script name (quote, url and sha256 kept), or romanization_missing. Nothing is matched by name across profile ids."""
    doc = read(P.data('profile-romanization.json', key), {}) or {}
    if not doc:
        return {}
    if doc.get('school') != key:
        raise ValueError('profile-romanization school mismatch')
    out = {}
    for r in doc['rows']:
        if r['status'] == 'page_stated' and (not r.get('name_latin') or r['name_latin'] not in r['evidence']['quote']):
            raise ValueError('romanization quote does not hold the Latin name: ' + r['name_hangul'])
        out[r['profile_id']] = r
    return out


def given_compatible(a, b, fam):
    """Two given-name token lists of one family name in one school's faculty listings are one person when: the first
    given names are nickname-equal; one is a 3+ letter prefix of the other ('Raj' / 'Rajesh', 'Mack' / 'Mackillo',
    'Clay' / 'Clayton'; never under an East Asian family name, R-LNK-02a); one side is initials that spell the other's
    given names ('P.C.' / 'Pei-Cheng'); or one side's first given name is the other's second ('L. Jay' / 'Jay',
    'S. Sandeep' / 'Sandeep'). Learned from Michigan 2026-10-29: the CSE/ECE lists spell one person several ways."""
    if not a or not b:
        return False
    if nick_ok(a[0], b[0]):
        return True
    if fam not in EAST_ASIAN_FAMILY and min(len(a[0]), len(b[0])) >= 3 and (a[0].startswith(b[0]) or b[0].startswith(a[0])):
        return True
    for x, y in ((a, b), (b, a)):
        if all(len(t) == 1 for t in x) and len(x) <= len(y) and all(y[i].startswith(x[i]) for i in range(len(x))):
            return True
        if len(x) >= 2 and len(x[0]) == 1 and x[1] == y[0]:
            return True
    return False


HAN_RUN = re.compile(r'[\u3400-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af]+')


def latin_part(name):
    """Opt-in ([census].han_suffix_merge, HKUST 2026-11-18): 'Dit-Yan YEUNG 楊瓞仁' and 'Dit-Yan YEUNG' are one spelling. The Latin part of a mixed
    name when it keeps two or more tokens, else the name itself; a pure Han name is untouched (it still merges only by profile)."""
    if not HAN_RUN.search(name):
        return name
    rest = ' '.join(HAN_RUN.sub(' ', name).replace('|', ' ').split())
    return rest if len(toks(rest)) >= 2 else name


def merge_people(rows, explicit_aliases=(), han_suffix=False, profile_id_rx=None):
    """Group listing rows into persons: same family name and compatible given names (given_compatible); rows of one
    school only, never across schools. profile_id_rx ([census].profile_id_pattern): rows whose `profile` URL carries the same id
    under this pattern are one person on that site's own identifier (KAIST CS /people/view?idx=N: a Latin and a Hangul spelling of
    the same card), never a name match; groups the name rules already split are joined here."""
    groups, by_fam = [], collections.defaultdict(list)
    for r in sorted((dict(r, name=CLONE_OF.sub('', r['name'])) for r in rows), key=lambda r: r['observed']):   # a Drupal 'Clone of X' card is X
        K = latin_part if han_suffix else (lambda s: s)
        t = toks(K(r['name']))
        literal = literal_cjk_name(r['name'])
        if (len(t) < 2 and not literal) or TITLE_NAME.search(r['name']):
            continue
        identity = r.get('reviewed_profile_name')
        if identity:
            g = next((g for g in groups if g.get('reviewed_profile_name') == identity), None)
        elif literal:
            profile = (r.get('profile') or r.get('homepage') or '').rstrip('/')
            g = next((g for g in by_fam[t[-1]] if profile and any(
                (q.get('profile') or q.get('homepage') or '').rstrip('/') == profile for q in g['rows'])), None)
        else:
            g = next((g for g in by_fam[t[-1]] if not g.get('reviewed_profile_name') and any(given_compatible(toks(K(n))[:-1], t[:-1], t[-1]) for n in g['names'])), None)
        if g is None:
            g = dict(names=[], rows=[])
            if identity:
                g['reviewed_profile_name'] = identity
            groups.append(g); by_fam[t[-1]].append(g)
        if r['name'] not in g['names']:
            g['names'].append(r['name'])
        g['rows'].append(r)
    # the same personal homepage under one family name is one person ('H.V.' / 'Jag' Jagadish, 'Georgios' / 'George'
    # Tzimpragos, 'Noel' / 'Chris' Giebink: learned from Michigan 2026-10-29); a shared department or lab page is not personal
    def home_key(u):
        u = re.sub(r'^https?://(?:www\.|web\.)?', '', (u or '').lower()).rstrip('/')
        return u if u and not re.fullmatch(r'(?:[\w-]+\.)?(?:engin\.)?[\w-]+\.edu(?:/people(?:/.*)?)?', u) else None  # a bare site root or people page
    merged = True
    while merged:
        merged = False
        for fam, gs in by_fam.items():
            for i, a in enumerate(gs):
                ha = {home_key(r.get('homepage')) for r in a['rows']} - {None}
                for b in gs[i + 1:]:
                    if a.get('reviewed_profile_name') != b.get('reviewed_profile_name'):
                        continue
                    if any(literal_cjk_name(n) for n in a['names'] + b['names']):
                        continue  # only source-profile identity joins opaque names, never a shared lab homepage
                    if ha & ({home_key(r.get('homepage')) for r in b['rows']} - {None}):
                        a['names'] += [n for n in b['names'] if n not in a['names']]; a['rows'] += b['rows']
                        gs.remove(b); groups.remove(b); merged = True
                        break
                if merged:
                    break
            if merged:
                break
    if profile_id_rx:
        rx = re.compile(profile_id_rx)
        def pid(r):
            m = rx.search(r.get('profile') or '')
            return m.group(1) if m else None
        by_id = {}
        for g in list(groups):
            ids = {pid(r) for r in g['rows']} - {None}
            for i in sorted(ids):
                other = by_id.setdefault(i, g)
                if other is g or other not in groups or g not in groups:
                    continue
                if other.get('reviewed_profile_name') != g.get('reviewed_profile_name'):
                    raise ValueError('profile id joins groups with different reviewed profile identities: ' + i)
                other['names'] += [n for n in g['names'] if n not in other['names']]
                other['rows'] += g['rows']
                groups.remove(g)
                for lst in by_fam.values():
                    if g in lst:
                        lst.remove(g)
                for j in {pid(r) for r in g['rows']} - {None}:
                    by_id[j] = other
    for name_a, name_b in explicit_aliases:
        a = next((g for g in groups if name_a in g['names']), None)
        b = next((g for g in groups if name_b in g['names']), None)
        assert a is not None and b is not None, f'reviewed alias not present in faculty rows: {name_a} / {name_b}'
        if a is b:
            continue
        if a.get('reviewed_profile_name') != b.get('reviewed_profile_name'):
            raise ValueError('name alias contradicts reviewed profile identities')
        a['names'] += [n for n in b['names'] if n not in a['names']]
        a['rows'] += b['rows']
        groups.remove(b)
        by_fam[toks(name_b)[-1]].remove(b)
    for g in groups:
        g['rows'].sort(key=lambda r: r['observed'])
    return groups


def main(key):
    cfg = S.get(key); lo, hi = cfg.get('window') or [2016, 2026]
    coverage = {d['code']: d.get('coverage') or 'full' for d in S.listing_units(cfg)}
    rows_path = P.data('rows.json', key)
    if not rows_path.is_file():
        raise SystemExit(f'Missing required faculty listing rows: {rows_path}; existing census outputs were preserved')
    rows = read(rows_path)
    if not isinstance(rows, list) or not rows:
        raise SystemExit(f'Faculty listing rows are empty or invalid: {rows_path}; existing census outputs were preserved')
    review = {r['name']: r for r in read(P.data('cs-related-review.json', key), {}).get('decisions', [])} \
        if isinstance(read(P.data('cs-related-review.json', key), {}), dict) else {}
    basis_ev = {r['pi']: r for r in read(P.data('pi-basis-evidence.json', key), [])}
    not_pi = {x['name']: x['reason'] for x in S.field(cfg, 'census.not_pi', [])}  # owner decisions: never a PI, whatever the listing says
    dblp_ids = read(P.data('dblp-ids.json', key), {})  # stage 5 (tools/dblp_ids_school.py); folded in when present
    for nm_, h_ in read(P.data('homepage-identity.json', key), {}).items():  # the PI's own homepage links (stage 5)
        d0 = dblp_ids.setdefault(nm_, {})
        if not d0.get('pid') and h_.get('dblp'):
            d0.update(pid=h_['dblp']['pid'], basis='pi_homepage_link', url=h_['dblp']['url'], sha256=h_['dblp']['sha256'], quote=h_['dblp']['quote'],
                      dump=None)
        d0['orcid'] = sorted(set(d0.get('orcid') or []) | {o['orcid'] for o in h_.get('orcid') or []})
    census, people, listing_rows, n = [], [], [], collections.Counter()
    pid_rx = S.field(cfg, 'census.profile_id_pattern', '') or None
    groups = merge_people(reviewed_profile_names(key, rows), reviewed_name_aliases(key), han_suffix=bool(S.field(cfg, 'census.han_suffix_merge')), profile_id_rx=pid_rx)
    rom = reviewed_romanization(key) if pid_rx else {}
    labels = [display_name(g['rows'], g['names'], bool(pid_rx)) for g in groups]
    duplicates = [name for name, count in collections.Counter(labels).items() if count > 1]
    if duplicates:
        raise ValueError('Distinct faculty profiles need reviewed unique names before census output: ' + ', '.join(duplicates))
    for g in groups:
        rs = [r for r in g['rows'] if lo <= r['year'] <= hi]
        if not rs:
            continue
        name = display_name(rs, g['names'], bool(pid_rx))  # the latest spelling
        rom_rec = None
        if pid_rx and HAN_RUN.search(name):
            rx_ = re.compile(pid_rx)
            rom_rec = next((rom[m_.group(1)] for r in rs if (m_ := rx_.search(r.get('profile') or '')) and m_.group(1) in rom), None)
            if rom_rec and rom_rec['status'] == 'page_stated':
                g['names'] = [n for n in g['names'] if n != rom_rec['name_latin']] + [rom_rec['name_latin']]
                name = rom_rec['name_latin']
        ranks_by_year = collections.defaultdict(set)
        for r in rs:
            ranks_by_year[r['year']].add(r['rank'])
        best = {y: min(v, key=ORDER.index) for y, v in ranks_by_year.items()}
        depts = sorted({r['dept'] for r in rs}, key=lambda d: list(coverage).index(d) if d in coverage else 99)
        latest = max(rs, key=lambda r: r['observed'])
        sources = []
        seen = set()
        for r in rs:
            k = (r['dept'], r['year'], r['half'])
            if k in seen:
                continue
            seen.add(k)
            sources.append(dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], kind=f"dept_listing:{r['dept']}", observed=r['observed'],
                                rank_as_listed='; '.join(r['dept_title'] or r['titles']), rank=r['rank'], slot=r['slot']))
        # PI basis
        basis, why_not = None, None
        lad = [r for r in rs if r['rank'] == 'ladder']
        lad_full = [r for r in lad if coverage.get(r['dept']) == 'full']
        lad_aff = [r for r in lad if coverage.get(r['dept']) == 'affiliated']
        court = [r for r in rs if r['rank'] == 'courtesy' and coverage.get(r['dept']) == 'full']
        dec = review.get(name) or next((review[a] for a in g['names'] if a in review), None)
        if lad_full:
            r = lad_full[0]
            basis = dict(kind='ladder_faculty', url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], observed=r['observed'], role='; '.join(r['dept_title']))
        elif lad_aff and dec and dec.get('decision') == 'accepted':
            r = lad_aff[0]
            basis = dict(kind='ladder_faculty', url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], observed=r['observed'], role='; '.join(r['dept_title']),
                         cs_related=dict(decision='accepted', basis=dec.get('basis'), evidence=dec.get('evidence')))
        elif court:
            home = [(r, m, hu_) for r in court for t in r['titles'] for m, hu_ in [home_professor(t)] if m]
            if not home and S.field(cfg, 'census.courtesy_title_of') and not any(PRACTICE_TITLE.search(t) for r in court for t in r['titles']):   # owner rule (2026-11-18): a courtesy row titled 'Professor of <home unit>' counts (JHU, Harvard Janson)
                home = [(r, m, hu_) for r in court for t in r['titles'] for m, hu_ in [home_professor_of(t)] if m]
            if home:
                r, m, hu = home[0]
                of = re.search(r'Professor of (.+?),', m.group(0))
                if of and re.match(r'(?:Medical School|School of|College of)', hu):  # 'Professor of X, Medical School': the department X
                    hu = of.group(1).strip()
                basis = dict(kind='courtesy_faculty', url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], observed=r['observed'],
                             role='; '.join(r['titles']), home_unit=hu)
            else:
                why_not = 'courtesy or affiliate appointment without a professor rank in a home unit'
        elif lad_aff:
            why_not = 'pending CS-related review (department coverage affiliated)' if not dec else f"CS-related review: {dec.get('decision')}"
        if basis is None and name in basis_ev:
            e = basis_ev[name]; basis = {k: e[k] for k in ('kind', 'url', 'sha256', 'quote', 'observed', 'role', 'home_unit') if k in e}
        if basis is None and why_not is None:
            why_not = f"rank {best[max(best)]} without reviewed advising or own-group evidence"
        if name in not_pi or any(a_ in not_pi for a_ in g['names']):
            basis, why_not = None, 'owner decision: ' + not_pi.get(name, next((not_pi[a_] for a_ in g['names'] if a_ in not_pi), ''))
        is_pi = basis is not None
        n[f'pi:{is_pi}'] += 1; n[f"basis:{(basis or {}).get('kind')}"] += 1
        cid = f'{key}_fac_' + slug(name)
        homepage = next((r['homepage'] for r in reversed(rs) if r.get('homepage')), None)
        profile_url = homepage or next((r['profile'] for r in reversed(rs) if r.get('profile')), None)
        forms = list(dict.fromkeys(g['names'] + [f for r in rs for f in r.get('reviewed_name_forms') or []]))
        census.append(dict(name=name, aliases=[a for a in forms if a != name and not TITLE_NAME.search(a)], collection_person_id=cid, structure_name=name,
                           profile_url=profile_url, dblp=[d_['pid']] if (d_ := dblp_ids.get(name) or {}).get('pid') else [],
                           dblp_basis=d_.get('basis'), dblp_evidence={k: d_[k] for k in ('url', 'dump', 'sha256', 'quote') if k in d_} or None,
                           orcid=list(d_.get('orcid') or []), rank=best[max(best)], title_as_listed='; '.join(latest['titles']),
                           departments=depts, listed_in=depts, years_listed=sorted(best), ranks_by_year={str(y): sorted(v, key=ORDER.index) for y, v in sorted(ranks_by_year.items())},
                           romanization_missing=bool(pid_rx and HAN_RUN.search(name)) or None, romanization_source=(rom_rec or {}).get('evidence') if rom_rec and rom_rec['status'] == 'page_stated' else None,
                           sources=sources, is_pi=is_pi, pi_basis=basis, not_pi_reason=None if is_pi else why_not,
                           lab_units=[], collectives=[], emeritus_since=min((y for y, b in best.items() if b == 'emeritus'), default=None)))
        people.append(dict(id=cid, name=name, roles=['faculty'], contexts=[], profileUrl=profile_url))
        by_dy = {}
        for r in rs:
            by_dy.setdefault((r['dept'], r['year']), r)
        for (d, y), r in sorted(by_dy.items()):
            listing_rows.append(dict(pi=name, school=key, department=d, year=y, capture_url=r['capture_url'], sha256=r['sha256'], quote=r['quote'],
                                     rank_as_listed='; '.join(r['dept_title'] or r['titles']), rank=r['rank'], emeritus=r['rank'] == 'emeritus',
                                     visiting=r['rank'] == 'visiting', observed=r['observed'], slot=r['slot']))
    for x in read(P.data('census-additions.json', key), []):  # accepted CS-related faculty of other units: a person record each
        if x.get('collection_person_id') and all(p_['id'] != x['collection_person_id'] for p_ in people):
            people.append(dict(id=x['collection_person_id'], name=x['name'], roles=['faculty'], contexts=[], profileUrl=x.get('profile_url')))
    import period_proofs as PP  # reviewed year proofs of courtesy-listed PIs (census-overrides-school.json year_proofs; tools/period_proofs.py)
    PP.merge_year_proofs(census, key)
    rule = __doc__.split('\n-> ')[0]
    P.data_w('census-faculty.json', key).write_text(json.dumps(dict(school=key, built_at=datetime.datetime.utcnow().isoformat() + 'Z', rule=rule, faculty=census),
                                                             indent=1, ensure_ascii=False))
    P.data_w('listings.json', key).write_text(json.dumps(listing_rows, indent=0, ensure_ascii=False))
    C = dict(people=people, works={}, personLinks=[], unitLinks=[], units=[], facultyPeriods=[],
             source=f'tools/census_build.py {key} (no site collection exists for this school)')
    P.data('collection.json.gz', key).parent.mkdir(parents=True, exist_ok=True)
    P.data_w('collection.json.gz', key).write_bytes(gzip.compress(json.dumps(C, ensure_ascii=False).encode(), mtime=0))
    by = collections.Counter((x['rank'], x['is_pi']) for x in census)
    dep = collections.Counter((d, x['is_pi']) for x in census for d in x['departments'])
    L = [f"# {cfg['name']}: faculty census", '', f"Built {datetime.date.today()} by `tools/census_build.py {key}` from `listings/{key}/rows.json`.", '',
         f"- persons: {len(census)}; PIs: {sum(x['is_pi'] for x in census)}", f"- listing rows (person, department, year): {len(listing_rows)}", '',
         '| rank (latest) | PI | not PI |', '|---|---|---|']
    for r in ORDER:
        if by[(r, True)] or by[(r, False)]:
            L.append(f'| {r} | {by[(r, True)]} | {by[(r, False)]} |')
    L += ['', '| department | PI | not PI |', '|---|---|---|'] + [f'| {d} | {dep[(d, True)]} | {dep[(d, False)]} |' for d in coverage]
    L += ['', '## PI basis', ''] + [f'- {k[6:]}: {v}' for k, v in sorted(n.items()) if k.startswith('basis:') and k != 'basis:None']
    L += ['', '## Not PI, by reason', ''] + [f'- {k}: {v}' for k, v in collections.Counter(x['not_pi_reason'] for x in census if not x['is_pi']).most_common()]
    P.data_w('census-report.md', key).write_text('\n'.join(L) + '\n')
    print(json.dumps(dict(persons=len(census), pis=sum(x['is_pi'] for x in census), listing_rows=len(listing_rows), **{k: v for k, v in n.items()})))


if __name__ == '__main__':
    main(sys.argv[1])
