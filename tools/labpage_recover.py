"""Recover lab papers that a PI's own lab publications page lists but the hierarchy lacks (hierarchy/<school>/labpage-pubs.jsonl.gz).

parse    each lab-page row -> a clean title (citation tails cut: run-in author lists, venues, 'Publication date ...',
         '(with ...)', '[pdf]') and the listing year. Junk is dropped and counted by reason: filter bars and headings,
         venue-only lines, author lines, talks, patents, theses (the student's, with the PI as director), service / award /
         news lines, fragments. A title field that is not a title (an author name, a venue, an award) is re-read from the
         entry's quote when the quote holds a citation.
held     the PI's lab papers (hierarchy/<school>/lab_papers.jsonl.gz, editions included) by normalized title
         (pi_hierarchy.norm_title): equal, a held title of 30+ characters inside the citation, or a 30+ character prefix
         either way; after resolution also by the resolved work's OpenAlex id or DOI.
resolve  the remaining titles to works, in this order (a work matches when its normalized title equals the clean title, is
         inside the citation (30+ characters), or one is the other plus a subtitle (40+ characters); its year 2 before to
         1 after the listing):
           sweep        hierarchy/<school>/openalex-sweep.sqlite
           pi_works     hierarchy/<school>/pi-works.sqlite
           arxiv        arXiv ids the entry links, else the local arXiv OAI-PMH index (../claude-cmu-20261017/raw/arxiv_oai;
                        the PI's family name among the authors, first version 3 years before to 1 after the listing);
                        their OpenAlex records through the arXiv DOI
           proceedings  open proceedings PDFs the entry links (dblp_recover.pdf_url: PMLR, CVF, NeurIPS, ACL, OpenReview ...)
           openalex     the DOI the entry links, then OpenAlex title search for what is still unresolved (phrase titles OR'd,
                        25 per query, 10 credits each, capped by --title-credits). List queries are cached in the sqlite.
rule     (tools/pi_hierarchy.py) per edition: the PI on the byline (pi_hierarchy.Name over the pis.json names; reviewed
         namesake author ids never count); the edition's year in a reviewed period or a listing year (the same test
         pi_hierarchy applies when it ingests the rows); that authorship lists the school (OpenAlex institution lineage or
         affiliation text) -> 'openalex_authorship'. An authorship listing only other institutions -> other_institution.
         One listing none -> page 1 of the arXiv v1 PDF (arXiv's bulk copy on GCS) or of the open proceedings PDF must tie the
         school to the PI (pi_fulltext_affiliation.tie) and carry the title -> 'page1_arxiv' / 'page1_open'. A paper written
         at the PI's previous institution fails the appointment or the school test whatever the lab page says.
-> hierarchy/<school>/labpage-recovered.jsonl.gz: every accepted row ever (table accepted, not only this run's candidates),
   read by pi_hierarchy.py as identity 'labpage_listing'; hierarchy/<school>/labpage-recover.sqlite: parsed rows, every try,
   page-1 texts and PDF sha256 (never the PDFs), OpenAlex answers, arXiv index hits, run reports.
Fetching: robots.txt and one request per 2 s per host across processes (hierarchy/missing-pi-tools/mpcap.py); dblp.org,
eScholarship and Scholar are refused.
usage: labpage_recover.py run <school> [--workers 6] [--title-credits 600] | write <school> | report <school>
"""
import argparse, collections, difflib, gzip, hashlib, html, json, os, re, sqlite3, subprocess, sys, tempfile, threading, time, zlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

import requests

sys.path.insert(0, str(Path(__file__).parent))
from pi_hierarchy import read, HERE, INST, AFF, ndoi, norm_title, Name, toks, given, contains, TODAY, NOT_PAPERS  # noqa: E402
from pi_fulltext_affiliation import tie, arxiv_id  # noqa: E402
from dblp_recover import pdf_url, OPEN_HOSTS  # noqa: E402
sys.path.insert(0, str(HERE / 'hierarchy' / 'missing-pi-tools'))
import mpcap  # noqa: E402

import atlas_paths as P  # noqa: E402  (every path in one place)
ARXIV_OAI = P.archive_sweep('claude-cmu-20261017') / 'raw' / 'arxiv_oai'
GCS = 'https://storage.googleapis.com/arxiv-dataset/arxiv/arxiv/pdf/{yymm}/{aid}v1.pdf'
OA = 'https://api.openalex.org/works'
SELECT = 'id,doi,title,publication_year,publication_date,type,authorships,ids,primary_location,locations'
STEPS = ('sweep', 'pi_works', 'arxiv', 'proceedings', 'openalex')

# ---------------------------------------------------------------- parse

YEAR = re.compile(r'(?<!\d)(?:19|20)\d{2}(?!\d)')
PARTICLES = {'van', 'von', 'de', 'der', 'den', 'da', 'del', 'di', 'la', 'le', 'du', 'dos', 'das', 'el', 'al', 'bin', 'ben', 'y'}
VENUE_WORD = re.compile(r'\b(proceedings|proc\.|conference|journal|transactions|workshop|symposium|letters|arxiv|preprint|magazine|'
                        r'icml|neurips|nips|iclr|cvpr|iccv|eccv|acl|emnlp|naacl|sigmod|vldb|osdi|sosp|nsdi|sigcomm|usenix|ccs|crypto|'
                        r'eurocrypt|stoc|focs|soda|chi|uist|isca|micro|asplos|pldi|popl|icse|fse|kdd|aaai|ijcai|icra|iros|rss|corl|'
                        r'siggraph|tog|jmlr|tpami|ieee|acm|ubicomp|iscas|mobisys|sensys|ipsn|nature|science|allerton|colt|'
                        r'aistats|uai|interspeech|icassp|isit|infocom)\b', re.I)
VENUE_START = re.compile(r'^(?:the\s+)?(?:\d{4}\s+)?(?:\d+(?:st|nd|rd|th)\s+)?(?:ieee|acm|usenix|international|annual|proceedings|proc\.|'
                         r'conference|journal|transactions|symposium|workshop|advances in neural|neural information|'
                         r'in proc|in proceedings|presented at|accepted (?:at|to)|to appear)\b', re.I)
JUNK_TITLE = [
    ('filter_or_heading', re.compile(r'^(?:years?|filter(?:s| by)?|sort(?: by)?|show(?: all)?|all|types?|topics?|(?:selected |recent |all |journal |'
                                     r'conference |workshop )?(?:publications?|papers|articles|preprints)|book chapters?|books?|theses|'
                                     r'talks|patents|software|datasets?|other|bibtex|abstract|citations?|google scholar)\b[\s:.]*'
                                     r'(?:\W*(?:all|19\d\d|20\d\d|and|by|year|type|\W)*)$', re.I)),
    ('talk', re.compile(r'\((?:keynote|invited talk|talk|interview|tutorial|lecture|slides)\)|\b(?:keynote (?:talk|address|at)|invited talk|'
                        r'distinguished lecture|lecture (?:at|series)|talk at|tutorial at|panel(?:ist)? at|podcast|testimony|'
                        r'opening statement|webinar|seminar at|fireside chat)\b|^(?:talk|lecture|keynote|slides|videos?|video tutorials?|'
                        r'recording|interview)\b(?=(?:\W+\w+){0,3}\W*$)|\bgive a talk\b', re.I)),
    ('patent', re.compile(r'\bpatent|\bsaid\b|^(?:a |an )?(?:method|system|device|apparatus)s?\s+(?:and|for|of)\b.*\b(?:method|system|device|apparatus)\b', re.I)),
    ('service_award_news', re.compile(r'\b(?:program committee|tpcs?\b|pc (?:member|chair)|general chair|program chair|co-?chair(?:ing)?|'
                                      r'steering committee|area chair|office hours?|soda hall|joining the faculty|will be joining|'
                                      r'joined the faculty|dissertation award|best (?:paper|demo|student paper) (?:award|at|runner)|'
                                      r'(?:research|faculty|career|test.of.time) award|award for|curator|exhibition|hackathon|'
                                      r'we.re hiring|organi[sz]ing committee|application impact|editorial board|associate editor)|'
                                      r'^in memoriam\b|^(?:best paper|honorable mention|outstanding paper)\b', re.I)),
    ('fragment', re.compile(r'^(?:presented|an earlier version|earlier version|also (?:presented|appeared|in)\b|pdf\b|code\b|'
                            r'journal[- ]version|preprint\b|table of contents|see\s|available\b|project page|[\[@]|\d+[-–]day\b|'
                            r'(?:[a-z]\.\s?)+[a-z][a-z]+ et al)|@|https?://|www\.|\bbibtex\b|\bdownload\b', re.I)),
]
THESIS_Q = re.compile(r'\(Dir\.\)|\b(?:ph\.?\s?d\.?|doctoral|master\W?s?|bachelor\W?s?|semester|diploma|habilitation)\s+(?:thesis|dissertation|project|defen[cs]e)\b|'
                      r'\bdoctoral thesis\b|\bthesis\b(?! award)|\bdissertation\b(?! award)', re.I)
NEWS_Q = re.compile(r'^.{0,200}?\s(?:19|20)\d{2}/\d{1,2}/\d{1,2}\s?:')  # 'Title 2021/12/02: Our paper ...' (lab news items)
_venues = {}


def known_venues(school):
    """Normalized venue names: hierarchy/cs-venues.json and the venues of the school's lab papers."""
    if school not in _venues:
        v = {norm_title(x['name']) for x in json.load(open(HERE / 'hierarchy' / 'cs-venues.json'))}
        lp = HERE / 'hierarchy' / school / 'lab_papers.jsonl.gz'
        for line in gzip.open(lp, 'rt') if lp.exists() else []:
            r = json.loads(line)
            v.add(norm_title(r.get('venue')))
        _venues[school] = {x for x in v if len(x) >= 6}
    return _venues[school]


_given = None
NOT_GIVEN = {'the', 'on', 'of', 'and', 'in', 'for', 'with', 'to', 'a', 'an', 'data', 'deep', 'learning', 'from', 'by', 'at', 'via', 'we',
             'is', 'are', 'new', 'art', 'can', 'may', 'see', 'self', 'large', 'fast', 'safe', 'all', 'one', 'two', 'open', 'human', 'game', 'light'}


def given_name(w):
    """A given name of the lab-page pass's name lexicon (hierarchy/labpage-tools-epfl-berkeley/name_lexicon.json, 5+ uses)."""
    global _given
    if _given is None:
        lx = HERE / 'hierarchy' / 'labpage-tools-epfl-berkeley' / 'name_lexicon.json'
        _given = {k for k, v in json.load(open(lx))['given'].items() if (v or 0) >= 5} - NOT_GIVEN if lx.exists() else set()
    return fold(w).lower().strip('.') in _given


def name_like(seg):
    """'S Ye*', 'MW Mathis**', 'F.-C. Chou', 'Vittorio Caggiano', 'Jason D. Lee', '...' / 'et al.': initials or a known given name first"""
    s0 = re.sub(r'^(?:and|&)\s+', '', seg.strip())
    s = s0.replace('*', '').replace('†', '').replace('‡', '').replace('+', '').strip(' .')
    if s in ('...', '…', 'et al', 'et al.') or re.fullmatch(r'\.{2,}|…', s):
        return True
    w = s.split()
    if not 2 <= len(w) <= 4 or re.search(r'\d', s):
        return False
    if not (all(x[0].isupper() or x.lower() in PARTICLES for x in w) and len(w[-1].strip('.')) >= 2 and w[-1][0].isupper()):
        return False
    return bool(re.fullmatch(r"[A-Z]{1,3}\.?|[A-Z]\.-?[A-Z]\.?", w[0]) or given_name(w[0].split('-')[0]) or '*' in s0)


def strong_name(seg, fams):
    """A name-like segment that is surely a person: an initial ('S Ye', 'J. Lin', 'MW Mathis'), a marker ('*'), or the PI's surname."""
    s = re.sub(r'^(?:and|&)\s+', '', seg.strip())
    w = s.replace('*', ' ').replace('†', ' ').split()
    return name_like(seg) and ('*' in s or '†' in s or any(re.fullmatch(r"[A-Z]{1,3}\.?|[A-Z]\.-?[A-Z]\.?", x) for x in w[:-1])
                               or (w and fam(w[-1]) in fams))


def name_list(s):
    segs = [x for x in re.split(r'\s*[,;&]\s*|\s+and\s+', s) if x.strip()]
    return len(segs) >= 2 and name_like(segs[0]) and sum(name_like(x) for x in segs) >= 0.6 * len(segs)


def author_run(rest, fams):
    segs = [x for x in re.split(r'\s*[,;]\s*|\s+and\s+', rest) if x.strip()]
    return len(segs) >= 2 and name_like(segs[0]) and segs[0].strip() not in ('...', '…') and \
        sum(name_like(x) for x in segs[:3]) >= 2 and any(strong_name(x, fams) for x in segs[:4])


CUTS = [re.compile(p, re.I) for p in (r'\s+publication date\b', r'\s+authors?\s*:?\s', r'\s*\(with\s', r'\s+pdf\b', r'\s+joint with\b',
                                      r'\s*\[\s*(?:pdf|paper|arxiv|code|slides|video|bib|link|web|preprint|project)',
                                      r',?\s*(?:in review|under review|submitted|to appear|accepted|conditionally accepted)\b',
                                      r'\s+(?:the\s+)?(?:journal of|proceedings of|proc\.|in proc|ieee trans|acm trans)\b')]


def clean_title(t, fams, raw=True):
    """Cut a citation's tail. raw: the field is the whole citation line (author runs and venues may follow the title)."""
    t = re.sub(r'\s+', ' ', html.unescape(t or '')).strip()
    t = re.sub(r'^title\s*=\s*\{(.*)\}\s*,?$', r'\1', t)
    for rx in CUTS[:1] + (CUTS[1:] if raw else []):
        m = rx.search(t)
        if m and len(t[:m.start()].split()) >= 4:
            t = t[:m.start()]
    if raw:
        words = list(re.finditer(r'\S+', t))
        for i in range(3, len(words)):
            if author_run(t[words[i].start():], fams):
                t = t[:words[i].start()]
                break
    return t.strip(' .,;:-–"“”\'‘’{}')


def venue_only(t, venues=()):
    t = t.strip(' .,;:')
    t2 = re.sub(r'[\s,.()]+', ' ', t).strip()
    w = t2.split()
    if re.match(r"^In\s+[A-Z][\w&]*['’]\d{2}\b", t) or norm_title(t) in venues or norm_title(YEAR.sub('', t)) in venues:
        return True
    if VENUE_START.match(t) and len(w) <= 16 and ':' not in t:
        return True
    return len(w) <= 6 and bool(YEAR.search(t)) and bool(VENUE_WORD.search(t)) and len(YEAR.sub('', t2).split()) <= 4


def title_from_quote(q, fams, venues):
    """The first citation segment of the entry's quote that is neither an author list nor a venue (4+ words). BibTeX title
    fields, APA '(2016). Title.' and DBLP 'Authors: Title.' come first."""
    q = re.sub(r'\s+', ' ', html.unescape(q or ''))
    m = re.search(r'\btitle\s*=\s*[{"]+(.+?)[}"]+\s*[,}]', q)
    if m:
        return m.group(1).strip()
    first = []
    m = re.search(r'\((?:19|20)\d{2}[a-z]?\)\.?\s+(.+)$', q)
    if m:
        first.append(m.group(1).split('. ')[0])
    m = re.match(r'^(.{5,400}?)\s?:\s+(.+)$', q)
    if m and (name_list(m.group(1)) or author_run(m.group(1), fams)):
        first.append(m.group(2).split('. ')[0])
    for s in first:
        s = clean_title(s.strip(' ,.;:'), fams)
        if len(s.split()) >= 4 and not venue_only(s, venues):
            return s
    for s in re.split(r'\s+\.\s+|(?<=[a-z0-9\)\]\?!])\.\s+(?=[A-Z0-9])|["“”]|\s\|\s', q):
        s = s.strip(' ,.;:')
        if len(s.split()) < 4 or author_run(s, fams) or name_list(s) or venue_only(s, venues) or re.match(r'^(?:in|eds?\.|pp\.|vol\.)\b', s, re.I):
            continue
        s = clean_title(s, fams)
        if len(s.split()) >= 4 and not author_run(s, fams) and not venue_only(s, venues):
            return s
    return None


def classify(r, fams, venues):
    """(reason or None, clean title, flags) for one lab-page row."""
    raw = re.sub(r'\s+', ' ', html.unescape(r.get('title') or '')).strip()
    q = re.sub(r'\s+', ' ', html.unescape(r.get('quote') or '')).strip()
    links = ' '.join(r.get('links') or [])
    flags0 = []
    m = re.search(r'\btitle\s*=\s*[{"]+(.+?)[}"]+\s*[,}]', q) if re.match(r'\s*@\w+\s*\{|\s*title\s*=', q, re.I) else None
    if m:  # a BibTeX entry: its title field
        raw, flags0 = re.sub(r'[{}]', '', m.group(1)).strip(), ['title_from_bibtex']
    ys = YEAR.findall(raw)
    if len(set(ys)) >= 3 and (len(ys) >= 0.3 * len(raw.split()) or JUNK_TITLE[0][1].search(raw.split(':')[0] + ':')):
        return 'filter_or_heading', raw, []
    if THESIS_Q.search(q) or THESIS_Q.search(raw) or re.search(r'epfl-thesis|EPFL_TH\d', links):
        return 'thesis', raw, []
    if re.search(r'\bpatent', q + ' ' + links, re.I):
        return 'patent', raw, []
    if NEWS_Q.match(q):
        return 'service_award_news', raw, []
    tail = q[q.find(raw) + len(raw):][:60] if raw and raw in q else ''
    if re.match(r'\W*(?:keynote|invited talk|talk|lecture|tutorial|panel|seminar|presentation)\b', tail, re.I):
        return 'talk', raw, []
    is_raw = norm_title(raw) == norm_title(q) or len(raw) >= 0.9 * len(q)
    for reason, rx in JUNK_TITLE:
        if rx.search(raw):
            reread = (reason in ('service_award_news', 'fragment') or (reason == 'talk' and re.match(r'^(?:talk|slides|video)\b', raw, re.I))) \
                and norm_title(q) != norm_title(raw)
            t = title_from_quote(q, fams, venues) if reread else None
            if t and not any(rx2.search(t) for _, rx2 in JUNK_TITLE) and not norm_title(t).startswith(norm_title(raw)):  # a mislabelled title field: the citation sits in the quote
                return None, t, ['title_from_quote']
            return reason, raw, []
    t = clean_title(raw, fams, is_raw)
    words = t.split()
    after = q[len(raw):].lstrip() if q.startswith(raw) else ''
    person = len(words) <= 5 and name_like(t) and ('*' in t or (after[:1] in (',', ';') and author_run(q, fams)))
    if venue_only(t, venues) or person or len(words) < 2:
        why = 'venue_only' if venue_only(t, venues) else ('author_line' if person else 'fragment')
        t2 = title_from_quote(q, fams, venues) if norm_title(q) != norm_title(raw) else None
        if t2 and not any(rx2.search(t2) for _, rx2 in JUNK_TITLE) and not norm_title(t2).startswith(norm_title(t)):
            return None, t2, ['title_from_quote']
        return why, t, []
    return None, t, flags0 + (['title_cleaned'] if t != raw.strip(' .,;:-–"“”\'‘’') else [])


# ---------------------------------------------------------------- store


def db(school):
    c = sqlite3.connect(HERE / 'hierarchy' / school / 'labpage-recover.sqlite', timeout=120, check_same_thread=False)
    c.execute('create table if not exists rows (pi text, key text, title text, year int, status text, reason text, flags text, row text, '
              'at text, primary key (pi, key))')
    c.execute('create table if not exists tries (pi text, key text, step text, url text, status text, pdf_sha256 text, page1 blob, '
              'accepted int, evidence text, at text, primary key (pi, key, step, url))')
    c.execute('create table if not exists accepted (pi text, key text, row text, at text, primary key (pi, key))')
    c.execute('create table if not exists oa_cache (q text primary key, body blob, credits int, at text)')
    c.execute('create table if not exists pdfs (url text primary key, status text, pdf_sha256 text, page1 blob, at text)')
    c.execute('create table if not exists arxiv_hits (pi text, key text, hits text, primary key (pi, key))')
    c.execute('create table if not exists runs (at text primary key, report text)')
    return c


def now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


# ---------------------------------------------------------------- matching


class Index:
    """Candidate rows by clean title, 30-character shingles of the citation, and 40-character title prefixes."""
    def __init__(self, cands):
        self.exact, self.sh, self.pre = collections.defaultdict(list), collections.defaultdict(set), collections.defaultdict(list)
        self.c = cands
        for i, x in enumerate(cands):
            if x['ct']:
                self.exact[x['ct']].append(i)
            if len(x['ct']) >= 40:
                self.pre[x['ct'][:40]].append(i)
            for s in x['cite']:
                for j in range(0, max(0, len(s) - 29)):
                    self.sh[s[j:j + 30]].add(i)

    def match(self, k, year, lo=-2, hi=1):
        out = {}
        for i in self.exact.get(k, ()):
            out[i] = 'exact_title'
        if len(k) >= 30:
            for i in self.sh.get(k[:30], ()):
                if i not in out and any(k in s for s in self.c[i]['cite']):
                    out[i] = 'title_in_citation'
        if len(k) >= 40:
            for i in self.pre.get(k[:40], ()):
                ct = self.c[i]['ct']
                if i not in out and (k.startswith(ct) or ct.startswith(k)):
                    out[i] = 'title_with_or_without_subtitle'
        return {i: how for i, how in out.items() if not year or lo <= int(year) - self.c[i]['year'] <= hi}


def compact(w):
    """What the rule needs from an OpenAlex work."""
    return dict(id=w['id'], doi=ndoi(w.get('doi')) or None, title=w.get('title'), year=w.get('publication_year'), date=w.get('publication_date'),
                type=w.get('type'), venue=((w.get('primary_location') or {}).get('source') or {}).get('display_name'),
                authorships=[dict(raw=a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or '',
                                  aid=(a.get('author') or {}).get('id'),
                                  inst=[dict(id=i.get('id'), name=i.get('display_name'), lineage=i.get('lineage') or []) for i in a.get('institutions') or []],
                                  aff=a.get('raw_affiliation_strings') or []) for a in w.get('authorships') or []],
                arxiv=arxiv_id(w), locs=[u for l in [w.get('primary_location') or {}] + list(w.get('locations') or [])
                                         for u in (l.get('landing_page_url'), l.get('pdf_url')) if u],
                has_locations='locations' in w)


def sweep_pages(path):
    c = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    for (body,) in c.execute('select body from pages order by year, page'):
        yield from json.loads(zlib.decompress(body))


def pi_work_bodies(path):
    c = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    for (b,) in c.execute('select body from works'):
        yield json.loads(zlib.decompress(b))


def pi_fams(p):
    return {f for _, f in name_forms(p['names'])} | {fam(n) for n in p['names']}


def fam(n):
    import unicodedata
    t = re.sub(r'[^a-z ]', ' ', unicodedata.normalize('NFKD', n or '').encode('ascii', 'ignore').decode().lower()).split()
    return t[-1] if t else ''


def arxiv_year(aid):
    m = re.match(r'(\d{2})(\d{2})\.\d{4,5}$', aid or '')
    return 2000 + int(m.group(1)) if m else None


# ---------------------------------------------------------------- fetching


class Fetcher:
    def __init__(self, c, lock):
        self.c, self.lock = c, lock

    def pdf(self, url):
        """(status, sha256, page-1 text) for a PDF URL; cached in table pdfs (page-1 text only, never the PDF)."""
        with self.lock:
            hit = self.c.execute('select status, pdf_sha256, page1 from pdfs where url=?', (url,)).fetchone()
        if hit and hit[0] not in ('fetch_error',):
            return hit[0], hit[1], zlib.decompress(hit[2]).decode() if hit[2] else None
        st, sha, txt = self._get(url)
        with self.lock:
            self.c.execute('insert or replace into pdfs values (?,?,?,?,?)', (url, st, sha, zlib.compress(txt.encode()) if txt else None, now()))
            self.c.commit()
        return st, sha, txt

    def _get(self, url):
        if mpcap.blocked(url):
            return 'off_limits', None, None
        host = urlsplit(url).hostname or ''
        if host in mpcap._challenged:
            return 'host_challenged', None, None
        try:
            if not mpcap.robots_allowed(url):
                return 'robots_disallowed', None, None
        except RuntimeError:
            return 'robots_unreachable', None, None
        mpcap._wait(host)
        try:
            r = requests.get(url, headers={'User-Agent': mpcap.UA}, timeout=(15, 120), allow_redirects=True)
        except requests.RequestException:
            return 'fetch_error', None, None
        if mpcap.CHALLENGE_RX.search(r.content[:20000]):
            mpcap._challenged.add(host)
            return 'bot_challenge', None, None
        if r.status_code != 200 or not r.content.startswith(b'%PDF'):
            return f'http_{r.status_code}' if r.status_code != 200 else 'not_pdf', None, None
        with tempfile.NamedTemporaryFile(suffix='.pdf', dir=os.environ.get('TMPDIR') or None) as f:
            f.write(r.content); f.flush()
            try:
                txt = subprocess.run(['pdftotext', '-l', '1', f.name, '-'], capture_output=True, text=True, timeout=120).stdout
            except subprocess.TimeoutExpired:
                return 'pdftotext_timeout', hashlib.sha256(r.content).hexdigest(), None
        return 'ok', hashlib.sha256(r.content).hexdigest(), txt


def oa_list(c, lock, filt, key, budget, per_page=200):
    """One OpenAlex list query (all pages), cached by its filter. budget: dict(credits=, floor=) shared across calls."""
    with lock:
        hit = c.execute('select body from oa_cache where q=?', (filt,)).fetchone()
    if hit:
        return json.loads(zlib.decompress(hit[0]))
    out, cursor, spent = [], '*', 0
    while cursor:
        cost = 10 if '.search' in filt else 1
        if budget['credits'] < cost:
            return None
        for attempt in range(5):
            mpcap._wait('api.openalex.org')
            try:
                r = requests.get(OA, timeout=120, headers={'User-Agent': mpcap.UA},
                                 params={'api_key': key, 'filter': filt, 'per-page': per_page, 'cursor': cursor, 'select': SELECT})
            except requests.RequestException:
                time.sleep(5 * (attempt + 1)); continue
            if r.status_code == 200:
                break
            if r.status_code in (400, 404):
                with lock:
                    c.execute('insert or replace into oa_cache values (?,?,?,?)', (filt, zlib.compress(b'[]'), 0, now())); c.commit()
                return []
            time.sleep(10 * (attempt + 1))
        else:
            return None
        used = int(r.headers.get('X-RateLimit-Credits-Used') or cost)
        budget['credits'] -= used; spent += used
        if int(r.headers.get('X-RateLimit-Remaining') or 10 ** 6) < budget['floor']:
            budget['credits'] = 0
        j = r.json()
        out += j.get('results') or []
        cursor = j['meta'].get('next_cursor') if j.get('results') else None
        if '.search' in filt and len(out) >= 600:  # a phrase that matches too much: three pages are enough
            cursor = None
    with lock:
        c.execute('insert or replace into oa_cache values (?,?,?,?)', (filt, zlib.compress(json.dumps(out).encode()), spent, now())); c.commit()
    return out


# ---------------------------------------------------------------- the run


def open_host(u):
    """An open proceedings host of dblp_recover (the ACM DL refuses automated clients: never asked)."""
    return any(h in u for h in OPEN_HOSTS) and 'dl.acm.org' not in u


def in_window(year):
    return bool(year) and 2016 <= int(year) <= 2026


def appointment(p, year):
    """pi_hierarchy's ingest test for recovered rows: a reviewed period that contains the year, else a listing of that year."""
    if not year:
        return None
    per = next((q for q in p['periods'] if contains(q['start'], q['end'], str(year), q['asof'] or TODAY) == 'supported'), None)
    if per:
        return dict(periodId=per['id'])
    lst = next((l for l in p['listings'] if l['year'] == int(year)), None)
    return dict(listing=lst['year']) if lst else None


def name_forms(names):
    return sorted({(given(t[0]), t[-1]) for n in names for t in [toks(n)] if len(t) >= 2} |
                  {(t[1], t[-1]) for n in names for t in [toks(n)] if len(t) >= 3 and len(t[0]) == 1})


def fold(s):
    import unicodedata
    return ''.join(ch for ch in unicodedata.normalize('NFKD', s) if not unicodedata.combining(ch))


def same_paper(t, page):
    """The title on page 1: whole, or a shared run of 20+ characters (arXiv v1 titles often differ from the final one)."""
    if not t:
        return False
    if t in page:
        return True
    m = difflib.SequenceMatcher(None, t, page, autojunk=False).find_longest_match(0, len(t), 0, len(page))
    return m.size >= min(20, len(t))


def split_markers(s):
    """'Mathis6‡' -> 'Mathis6 ‡': a composite marker (affiliation number + equal-contribution sign) as two markers."""
    return re.sub(r'(?<=[A-Za-z])(\d{1,2})([∗*†‡§¶♯]+)', r'\1 \2', s)


def page1_tie(txt, names, aff, titles):
    """(how, quotes, text variant) when page 1 carries the title and pi_fulltext_affiliation.tie() ties the school to the
    PI on the text as extracted, else with accents folded ('Süsstrunk' against the toks() forms), else with composite markers
    split. The quotes are substrings of that variant of the page-1 text, which is stored."""
    flat = re.sub(r'\s+', ' ', txt or '')
    head = norm_title(flat[:5000])
    if not any(same_paper(t, head) for t in titles):
        return 'title_not_on_page1', [], None
    for variant, text in (('as_extracted', flat), ('accents_folded', fold(flat)), ('markers_split', split_markers(fold(flat)))):
        how, quotes = tie(text, names, aff)
        if how:
            return how, quotes, variant
    return None, [], None


def run(school, workers=6, title_credits=600, floor=4000, dry=False):
    t0 = time.time()
    c = db(school); lock = threading.Lock()
    inst = 'https://openalex.org/' + INST[school]; aff = re.compile(AFF[school], re.I)
    pis = read(HERE / 'hierarchy' / school / 'pis.json'); P = {p['pi']: p for p in pis}
    alias = {}
    for p in pis:
        for n in p['names']:
            alias.setdefault(' '.join(toks(n)), p['pi'])
    n = collections.Counter()
    log = lambda **k: print(json.dumps(dict(school=school, t=round(time.time() - t0), **k), ensure_ascii=False), flush=True)

    # 1. parse
    rows = [json.loads(l) for l in gzip.open(HERE / 'hierarchy' / school / 'labpage-pubs.jsonl.gz', 'rt')]
    n['rows_read'] = len(rows)
    held_t, held_id = collections.defaultdict(set), collections.defaultdict(set)
    for r in (json.loads(l) for l in gzip.open(HERE / 'hierarchy' / school / 'lab_papers.jsonl.gz', 'rt')):
        held_t[r['pi']].add(norm_title(r.get('title')))
        for e in [r] + list(r.get('editions') or []):
            held_id[r['pi']] |= {x for x in (e.get('oa'), ndoi(e.get('doi')), e.get('work')) if x}
    cands, seen = [], {}
    with lock:
        venues = known_venues(school)
        for r in rows:
            pi = r['pi'] if r['pi'] in P else alias.get(' '.join(toks(r['pi'])))
            reason, t, flags = classify(r, pi_fams(P[pi]) if pi else set(), venues)
            ct = norm_title(t)
            key = 'labpage:' + hashlib.sha1(ct.encode()).hexdigest()
            if pi is None:
                reason = reason or 'pi_not_in_hierarchy'
            elif not reason and len(ct) < 8:
                reason = 'fragment'
            status = 'junk' if reason else None
            if not reason and (pi, key) in seen:
                n['duplicate_listing'] += 1; continue
            if not reason:
                cite = [s for s in (norm_title(r.get('title')), norm_title(r.get('quote')), ct) if s]
                hs = held_t[pi]
                if ct in hs or any(len(h) >= 30 and any(h in s for s in cite) for h in hs) or \
                        (len(ct) >= 30 and any(len(h) >= 30 and (h.startswith(ct) or ct.startswith(h)) for h in hs)):
                    status = 'held'
                else:
                    status = 'candidate'
                    x = dict(pi=pi, key=key, title=t, ct=ct, cite=cite, year=int(r['year']), flags=flags, row=r)
                    seen[(pi, key)] = x; cands.append(x)
            n['junk:' + reason if reason else status] += 1
            if not reason or True:
                c.execute('insert or replace into rows values (?,?,?,?,?,?,?,?,?)', (pi or r['pi'], key if not reason else key + ':' + hashlib.sha1(json.dumps(r, sort_keys=True).encode()).hexdigest()[:10],
                                                                                  t, int(r['year']), status, reason, json.dumps(flags), json.dumps(r, ensure_ascii=False), now()))
        c.commit()
    log(stage='parsed', **n)
    idx = Index(cands)
    found = collections.defaultdict(list)  # cand index -> [(step, compact work, how)]
    found_ids = collections.defaultdict(set)

    def add(step, w, hits):
        cw = None
        for i, how in hits.items():
            if w['id'] in found_ids[i]:
                continue
            cw = cw or compact(w)
            found[i].append((step, cw, how)); found_ids[i].add(w['id'])

    # 2. sweep and the PI works
    for w in sweep_pages(HERE / 'hierarchy' / school / 'openalex-sweep.sqlite'):
        if w.get('title') and w.get('type') not in NOT_PAPERS:
            hits = idx.match(norm_title(w['title']), w.get('publication_year'))
            if hits:
                add('sweep', w, hits)
    log(stage='sweep', rows_with_works=len(found))
    pw = HERE / 'hierarchy' / school / 'pi-works.sqlite'
    if pw.exists():
        for w in pi_work_bodies(pw):
            if w.get('title') and w.get('type') not in NOT_PAPERS:
                hits = idx.match(norm_title(w['title']), w.get('publication_year'))
                if hits:
                    add('pi_works', w, hits)
    log(stage='pi_works', rows_with_works=len(found))

    # 3. arXiv: ids the entry links, then the OAI-PMH index (cached per row)
    ax = collections.defaultdict(dict)  # cand index -> {arxiv id: how}
    for i, x in enumerate(cands):
        for l in x['row'].get('links') or []:
            m = re.search(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})', l)
            if m:
                ax[i][m.group(1)] = 'entry_link'
    with lock:
        cached = {(a, b): json.loads(h) for a, b, h in c.execute('select pi, key, hits from arxiv_hits')}
    todo = [i for i, x in enumerate(cands) if (x['pi'], x['key']) not in cached]
    for i, x in enumerate(cands):
        for aid, how in (cached.get((x['pi'], x['key'])) or {}).items():
            ax[i].setdefault(aid, how)
    if todo:
        sub = Index([cands[i] for i in todo])
        fams = [pi_fams(P[cands[i]['pi']]) for i in todo]
        got = collections.defaultdict(dict)
        for f in sorted(ARXIV_OAI.glob('*.jsonl.gz')):
            for line in gzip.decompress(f.read_bytes()).decode().splitlines():
                if not line:
                    continue
                a = json.loads(line)
                y = arxiv_year(a['id'])
                hits = sub.match(norm_title(a['title']), y, lo=-3, hi=1)
                for j, how in hits.items():
                    if fams[j] & {fam(z) for z in a['families']}:
                        got[j][a['id']] = 'oai_' + how
        with lock:
            for j, i in enumerate(todo):
                c.execute('insert or replace into arxiv_hits values (?,?,?)', (cands[i]['pi'], cands[i]['key'], json.dumps(got.get(j) or {})))
                for aid, how in (got.get(j) or {}).items():
                    ax[i].setdefault(aid, how)
            c.commit()
    log(stage='arxiv_index', rows_with_arxiv=len(ax), scanned=len(todo))
    if dry:
        how = collections.Counter(h for L in found.values() for _, _, h in L)
        log(stage='dry', candidates=len(cands), rows_with_works=len(found), rows_with_arxiv=len(ax), match_kinds=dict(how),
            rows_with_any=sum(1 for i in range(len(cands)) if i in found or i in ax))
        return dict(cands=cands, found=found, ax=ax)

    # 4. OpenAlex records through DOIs: arXiv DOIs (step arxiv), the entry's own DOI links (step openalex), and full records
    #    (locations) of sweep works the page-1 test may need
    key = os.environ.get('OPENALEX_API_KEY')
    budget = dict(credits=10 ** 6, floor=floor)
    doi_of = collections.defaultdict(set)  # doi -> {(cand index, step)}
    for i, ids in ax.items():
        for aid in ids:
            doi_of[f'10.48550/arxiv.{aid}'].add((i, 'arxiv'))
    for i, x in enumerate(cands):
        for l in x['row'].get('links') or []:
            m = re.search(r'doi\.org/(10\.\d{4,9}/[^\s?#]+)', l)
            d = ndoi(m.group(1)).rstrip('.)]') if m else ''
            if d and not re.search(r'[,|\s]', d):
                doi_of[d].add((i, 'openalex'))
    dois = sorted(doi_of)
    for b in range(0, len(dois), 50):
        res = oa_list(c, lock, 'doi:' + '|'.join(dois[b:b + 50]), key, budget) if key else None
        for w in res or []:
            d = ndoi(w.get('doi'))
            for i, step in doi_of.get(d, ()):
                k = norm_title(w.get('title'))
                oai = step == 'arxiv' and ax[i].get(d.split('arxiv.', 1)[-1], '').startswith('oai_')  # already matched on the arXiv title
                ok = oai or idx.match(k, None).get(i) or difflib.SequenceMatcher(None, k, cands[i]['ct']).ratio() >= 0.85
                if ok and w['id'] not in found_ids[i]:
                    found[i].append((step, compact(w), 'doi_' + ('arxiv' if step == 'arxiv' else 'entry_link'))); found_ids[i].add(w['id'])
    log(stage='openalex_doi', dois=len(dois), rows_with_works=len(found), credits_spent=10 ** 6 - budget['credits'])

    # 5. OpenAlex title search for rows with nothing at all (no work, no arXiv id, no proceedings link)
    def proc_links(x):
        return [u for l in x['row'].get('links') or [] if open_host(l) for u in [pdf_url(l)] if u]
    bare = [i for i, x in enumerate(cands) if i not in found and len(x['title'].split()) >= 4 and len(x['ct']) >= 25]
    tb = dict(credits=title_credits, floor=floor)
    phrase = lambda t: re.sub(r'\s+', ' ', re.sub(r'[^\w\s\-]', ' ', t)).strip()
    searched = 0
    for b in range(0, len(bare), 25):
        grp = bare[b:b + 25]
        filt = 'title.search:' + '|'.join(f'"{phrase(cands[i]["title"])}"' for i in grp)
        res = oa_list(c, lock, filt, key, tb) if key else None
        if res is None:
            n['title_search_skipped_budget'] += len(bare) - b; break
        searched += len(grp)
        sub = Index([cands[i] for i in grp])
        for w in res:
            if w.get('title') and w.get('type') not in NOT_PAPERS:
                for j, how in sub.match(norm_title(w['title']), w.get('publication_year')).items():
                    i = grp[j]
                    if w['id'] not in found_ids[i]:
                        found[i].append(('openalex', compact(w), 'title_search_' + how)); found_ids[i].add(w['id'])
    n['title_searched'] = searched; n['title_search_credits'] = title_credits - tb['credits']
    log(stage='openalex_title', searched=searched, rows_with_works=len(found), credits=title_credits - tb['credits'])

    # full records for sweep works (the sweep keeps no locations) that may need page 1
    need = sorted({cw['id'].rsplit('/', 1)[-1] for i, L in found.items() for _, cw, _ in L if not cw['has_locations']})
    full = {}
    for b in range(0, len(need), 50):
        for w in oa_list(c, lock, 'openalex_id:' + '|'.join(need[b:b + 50]), key, budget) or []:
            full[w['id']] = compact(w)
    for i, L in found.items():
        found[i] = [(s, full.get(cw['id'], cw), how) for s, cw, how in L]
    log(stage='locations', works=len(need), credits_spent=10 ** 6 - budget['credits'])

    # 6. the rule, per row
    fetch = Fetcher(c, lock)
    order = {s: k for k, s in enumerate(STEPS)}

    def record(x, step, url, status, sha=None, txt=None, ok=0, ev=None):
        with lock:
            c.execute('insert or replace into tries values (?,?,?,?,?,?,?,?,?,?)', (x['pi'], x['key'], step, url or '', status, sha,
                      zlib.compress(txt.encode()) if txt else None, ok, json.dumps(ev, ensure_ascii=False) if ev else None, now()))
            c.commit()

    def page1(x, step, url, basis, names, titles, extra):
        st, sha, txt = fetch.pdf(url)
        if st != 'ok':
            record(x, step + ':' + basis, url, st); return None
        how, quotes, variant = page1_tie(txt, names, aff, titles)
        if how in (None, 'title_not_on_page1'):
            record(x, step + ':' + basis, url, how or ('untied' if aff.search(fold(txt or '')) else 'school_absent'), sha, txt); return None
        ev = dict(basis=basis, how=how, quotes=quotes, url=url, pdf_sha256=sha, **extra)
        if variant != 'as_extracted':
            ev['page1_text_variant'] = variant
        record(x, step + ':' + basis, url, 'ok', sha, txt, 1, ev)
        return ev

    def one(i):
        x = cands[i]; p = P[x['pi']]; nm = Name(p['names']); names = name_forms(p['names']); blocked = set(p.get('notOpenAlex') or [])
        my_fams = {f for _, f in names}
        eds = sorted(found.get(i, []), key=lambda e: order[e[0]])
        if any(cw['id'] in held_id[x['pi']] or (cw['doi'] and cw['doi'] in held_id[x['pi']]) for _, cw, _ in eds
               if any(nm.match(a['raw']) for a in cw['authorships'])):
            record(x, 'held', None, 'held_by_resolved_id'); return 'held_by_resolved_id', None
        fails = []
        tried_ax = {cw['arxiv'] for _, cw, _ in eds if cw.get('arxiv')}  # an arXiv id with an OpenAlex record is judged through that record
        for step, cw, how in eds:
            a = next((a for a in cw['authorships'] if nm.match(a['raw']) and a['aid'] not in blocked), None)
            if a is None:
                record(x, step, cw['id'], 'pi_not_on_byline'); fails.append('pi_not_on_byline'); continue
            if not in_window(cw['year']):
                record(x, step, cw['id'], f"outside_2016_2026:{cw['year']}"); fails.append('outside_2016_2026'); continue
            app = appointment(p, cw['year'])
            if app is None:
                record(x, step, cw['id'], f"outside_appointment:{cw['year']}"); fails.append('outside_appointment'); continue
            via = [i_['name'] for i_ in a['inst'] if inst == i_['id'] or inst in i_['lineage']] + ['text: ' + z for z in a['aff'] if aff.search(z)]
            base = dict(step=step, match=how, oa=cw['id'], appointment=app)
            if via:
                ev = dict(base, basis='openalex_authorship', school_via=via[:3], institutions=[i_['name'] for i_ in a['inst']], raw_affiliations=a['aff'][:3])
                record(x, step, cw['id'], 'ok', ok=1, ev=ev); return 'accepted', (step, cw, ev)
            if a['inst']:
                record(x, step, cw['id'], 'other_institution:' + '; '.join(i_['name'] or '' for i_ in a['inst'])[:300]); fails.append('other_institution'); continue
            titles = [norm_title(cw['title']), x['ct']]
            for aid in dict.fromkeys([cw['arxiv']] + [a_ for a_ in ax.get(i, {}) if a_ not in tried_ax]):
                if aid:
                    tried_ax.add(aid)
                    ev = page1(x, step, GCS.format(yymm=aid.split('.')[0], aid=aid), 'page1_arxiv', names, titles, dict(base, arxiv=aid))
                    if ev:
                        return 'accepted', (step, dict(cw, arxiv=aid), ev)
            for u in dict.fromkeys([pdf_url(l) for l in cw['locs'] + list(x['row'].get('links') or []) if open_host(l)]):
                if u:
                    ev = page1(x, step, u, 'page1_open', names, titles, base)
                    if ev:
                        return 'accepted', (step, cw, ev)
            record(x, step, cw['id'], 'no_school_evidence'); fails.append('no_school_evidence')
        # arXiv ids with no OpenAlex record, then the entry's proceedings PDFs
        for aid, how in ax.get(i, {}).items():
            if aid in tried_ax:
                continue
            tried_ax.add(aid)
            y = arxiv_year(aid)
            if not in_window(y):
                record(x, 'arxiv', aid, f'outside_2016_2026:{y}'); fails.append('outside_2016_2026'); continue
            app = appointment(p, y)
            if app is None:
                record(x, 'arxiv', aid, f'outside_appointment:{y}'); fails.append('outside_appointment'); continue
            ev = page1(x, 'arxiv', GCS.format(yymm=aid.split('.')[0], aid=aid), 'page1_arxiv', names, [x['ct']], dict(step='arxiv', match=how, appointment=app, arxiv=aid))
            if ev:
                return 'accepted', ('arxiv', dict(id=None, doi=f'10.48550/arxiv.{aid}', title=x['title'], year=y, venue='arXiv', authorships=[], arxiv=aid), ev)
            fails.append('no_school_evidence')
        for u in dict.fromkeys(proc_links(x)):
            app = appointment(p, x['year'])
            if app is None:
                record(x, 'proceedings', u, f"outside_appointment:{x['year']}"); fails.append('outside_appointment'); continue
            ev = page1(x, 'proceedings', u, 'page1_open', names, [x['ct']], dict(step='proceedings', match='entry_link', appointment=app))
            if ev:
                return 'accepted', ('proceedings', dict(id=None, doi=None, title=x['title'], year=x['year'], venue=x['row'].get('venue'), authorships=[], arxiv=None), ev)
            fails.append('no_school_evidence')
        if not fails:
            record(x, 'none', None, 'unresolved'); return 'unresolved', None
        for why in ('other_institution', 'no_school_evidence', 'outside_appointment', 'outside_2016_2026', 'pi_not_on_byline'):
            if why in fails:
                return why, None

    res = collections.Counter(); acc_step = collections.Counter(); acc_lab = collections.Counter(); resolved = 0
    with ThreadPoolExecutor(workers) as ex:
        for k, (i, (status, got)) in enumerate(zip(range(len(cands)), ex.map(one, range(len(cands))))):
            x = cands[i]
            resolved += bool(found.get(i) or ax.get(i) or (status not in ('unresolved',)))
            res[status] += 1
            if status == 'accepted':
                step, cw, ev = got
                ev = dict(ev, labpage=dict(url=x['row'].get('url'), capture_url=x['row'].get('capture_url'), sha256=x['row'].get('sha256'),
                                           quote=x['row'].get('quote'), listed_title=x['row'].get('title'), listed_year=x['year']))
                out = dict(pi=x['pi'], key=x['key'], title=cw.get('title') or x['title'], year=cw.get('year') or x['year'], doi=cw.get('doi'),
                           venue=cw.get('venue') or x['row'].get('venue'), byline=[a['raw'] for a in cw.get('authorships') or []],
                           arxiv=cw.get('arxiv'), evidence=ev)
                with lock:
                    c.execute('insert or replace into accepted values (?,?,?,?)', (x['pi'], x['key'], json.dumps(out, ensure_ascii=False), now())); c.commit()
                acc_step[f"{step}:{ev['basis']}"] += 1; acc_lab[x['pi']] += 1
            with lock:
                c.execute('update rows set status=? where pi=? and key=?', (status, x['pi'], x['key']))
                if status not in ('accepted', 'held_by_resolved_id'):  # re-judged under the current rule: no longer accepted
                    if c.execute('delete from accepted where pi=? and key=?', (x['pi'], x['key'])).rowcount:
                        record(x, 'revoked', None, 'revoked:' + status); n['revoked_on_rejudgement'] += 1
                c.commit()
            if k % 100 == 0:
                log(stage='rule', done=k, **res)
    n.update({'result:' + k: v for k, v in res.items()})
    n['resolved'] = sum(1 for i in range(len(cands)) if found.get(i) or ax.get(i) or proc_links(cands[i]))
    rep = dict(school=school, at=now(), counts=dict(n), accepted_by_step=dict(acc_step), top_labs=acc_lab.most_common(15),
               accepted_total_ever=c.execute('select count(*) from accepted').fetchone()[0])
    with lock:
        c.execute('insert or replace into runs values (?,?)', (rep['at'], json.dumps(rep, ensure_ascii=False))); c.commit()
    write_accepted(school, c)
    log(stage='done', report=rep)
    return rep


def write_accepted(school, c=None):
    """Every accepted row of every run (table accepted), not only this run's candidates: earlier recoveries are lab papers by now."""
    c = c or db(school)
    rows, seen = [], set()
    for (r,) in c.execute('select row from accepted order by at, pi, key'):  # one row per PI and work (OpenAlex id, DOI, arXiv id)
        r = json.loads(r)
        ids = {(r['pi'], v) for v in (r['evidence'].get('oa'), r.get('doi'), r.get('arxiv')) if v}
        if ids & seen:
            continue
        seen |= ids; rows.append(r)
    tmp = HERE / 'hierarchy' / school / 'labpage-recovered.jsonl.gz.tmp'
    with gzip.open(tmp, 'wt') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    os.replace(tmp, HERE / 'hierarchy' / school / 'labpage-recovered.jsonl.gz')
    return len(rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'write', 'report', 'parse'])
    ap.add_argument('school')
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--title-credits', type=int, default=600)
    ap.add_argument('--floor', type=int, default=4000)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'run':
        run(a.school, a.workers, a.title_credits, a.floor, a.dry)
    elif a.cmd == 'write':
        print(json.dumps(dict(school=a.school, written=write_accepted(a.school))))
    elif a.cmd == 'report':
        r = db(a.school).execute('select report from runs order by at desc limit 1').fetchone()
        print(r[0] if r else '{}')
    else:  # parse only: classification counts and samples, no writes
        rows = [json.loads(l) for l in gzip.open(HERE / 'hierarchy' / a.school / 'labpage-pubs.jsonl.gz', 'rt')]
        cnt = collections.Counter(); ex = collections.defaultdict(list)
        P = {p['pi']: p for p in read(HERE / 'hierarchy' / a.school / 'pis.json')}
        al = {' '.join(toks(nm)): p for p in P.values() for nm in p['names']}
        venues = known_venues(a.school)
        for r in rows:
            p = P.get(r['pi']) or al.get(' '.join(toks(r['pi'])))
            reason, t, flags = classify(r, pi_fams(p) if p else set(), venues)
            cnt[reason or ('quote' if 'title_from_quote' in flags else ('cleaned' if flags else 'ok'))] += 1
            ex[reason or ('quote' if 'title_from_quote' in flags else ('cleaned' if flags else 'ok'))].append((r['pi'], r['title'][:150], t[:150], (r.get('quote') or '')[:150]))
        print(json.dumps(cnt))
        import random
        random.seed(3)
        for k, v in ex.items():
            print('=====', k, len(v))
            if k in ('ok', 'thesis', 'cleaned') and '--all' not in sys.argv:
                continue
            for e in random.sample(v, min(len(v), 14)):
                print('  ', ' | '.join(e)[:240])
