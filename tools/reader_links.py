"""Source links for papers with no stored copy (owner, 2026-11-01): a catalog CANDIDATE URL becomes a "Read at source" link, and the
paper becomes readable, wherever the candidate is confirmed to be this paper. Never hosted: there is no confirmed copy.

Confirmation, strongest first, recorded per paper as `link_basis` (all from files already on disk; no network):
  arxiv_id_doi      the candidate is an arXiv URL and the cached Semantic Scholar / OpenAlex DOI -> arXiv mapping that
                    fulltext-push/identity_rule.mapped_arxiv uses ties that arXiv id to one of this work's DOIs, and the arXiv record's
                    own title (local OAI index) shares at least half of the shorter title's words (a hand check found the mapping alone
                    wrong for about 12% of the papers: datasets, software and companion papers); an id the index lacks is not accepted;
  openalex_location the candidate URL (normalised: scheme, www, trailing slash, arXiv abs/pdf/version, doi.org, handle forms) is listed
                    as a location of this same OpenAlex work (or one of its editions) in the OpenAlex records on disk;
  arxiv_metadata    the local arXiv OAI index entry of the candidate's arXiv id has a title that matches the paper's title by
                    identity_rule's rule (letters-only words, >= 80% of the significant words, both ways, and at least 3 of them)
                    and the same first-author family name;
  landing_page_metadata  a verdict file written by the downloads agent's polite landing-page check (hierarchy/reader/link-verdicts.jsonl,
                    verdict "match"); candidates that need the page's own citation_title / author tags are listed in
                    link-check-requests.tsv for that agent.
A candidate the catalog already found to be another document (an identity_mismatch attempt, an identity-unconfirmed reversal, an
identity_mismatch_pdf asset) never counts.
"""
import gzip, json, re, sys, unicodedata
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

BASES = ('arxiv_id_doi', 'openalex_location', 'arxiv_metadata', 'landing_page_metadata')
ARXIV = re.compile(r'(?:arxiv\.org/(?:abs|pdf)/|arxiv[:.]|arxiv-dataset/arxiv/arxiv/pdf/\d{4}/)((?:\d{4}\.\d{4,5})|(?:[a-z\-]+(?:\.[A-Z]{2})?/\d{7}))(?:v\d+)?', re.I)
STOP = set('a an the of for and in on to with via from by at is are as its into using toward towards over under through '
           'what when how why which this that these those can be we our or not'.split())


def arxiv_of_url(u):
    m = ARXIV.search(str(u or ''))
    return m.group(1) if m else None


def norm_url(u):
    """A comparable form of a URL: arXiv -> arxiv:<id>, doi.org -> doi:<doi>, a handle -> handle:<prefix/id>, else host + path without
    scheme, www, a trailing slash, a fragment or a trailing .pdf."""
    u = str(u or '').strip()
    if not re.match(r'https?://', u, re.I):
        m = re.match(r'(?:doi:)?(10\.\d{4,9}/\S+)$', u, re.I)
        return 'doi:' + m.group(1).lower() if m else None
    a = arxiv_of_url(u)
    if a:
        return 'arxiv:' + a.lower()
    m = re.match(r'https?://(?:dx\.)?doi\.org/(.+)$', u, re.I)
    if m:
        return 'doi:' + m.group(1).split('?')[0].lower().rstrip('/')
    m = re.search(r'/handle/(\d+(?:\.\d+)*/\d+)', u) or re.match(r'https?://hdl\.handle\.net/(\d+(?:\.\d+)*/\d+)', u, re.I)
    if m:
        return 'handle:' + m.group(1)
    s = urlsplit(u)
    host = s.netloc.lower().removeprefix('www.')
    path = re.sub(r'(\.pdf)?/*$', '', s.path.lower())
    return host + path + (('?' + s.query.lower()) if s.query and 'id=' in s.query.lower() else '')


def oa_short(oa):
    return str(oa or '').rsplit('/', 1)[-1] or None


def words(t):
    t = unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()
    return [w for w in re.findall(r'[a-z0-9]+', t) if len(w) >= 3 and w not in STOP]


def fam(name):
    name = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower()
    if ',' in name:
        return re.sub(r'[^a-z]', '', name.split(',', 1)[0])
    toks = [t for t in re.sub(r'[^a-z \-]', ' ', name).split() if t not in {'jr', 'sr', 'ii', 'iii', 'iv'}]
    return re.sub(r'[^a-z]', '', toks[-1]) if toks else ''


def title_match(a, b, min_words=3, frac=0.8):
    """identity_rule's title rule, both ways: at least `frac` of each title's significant words are in the other (letters and digits only)."""
    wa, wb = words(a), words(b)
    if len(wa) < min_words or len(wb) < min_words:
        return False
    sa, sb = set(wa), set(wb)
    return len(sa & sb) / len(sa) >= frac and len(sa & sb) / len(sb) >= frac


def title_overlap(a, b):
    """Share of the shorter title's significant words that the other title has (0 when either has none)."""
    wa, wb = set(words(a)), set(words(b))
    return len(wa & wb) / min(len(wa), len(wb)) if wa and wb else 0.0


MAPPING_MIN_OVERLAP = 0.5   # the DOI -> arXiv mapping must not be contradicted by the arXiv record's own title


class ArxivIndex:
    """id -> (title, [author family names]) from the local arXiv OAI index (archive sweep raw/arxiv_oai), read once for the ids asked for."""

    def __init__(self, directory=None):
        self.dir = Path(directory) if directory else P.archive_sweep('claude-cmu-20261017') / 'raw' / 'arxiv_oai'
        self.rec, self.scanned = {}, set()

    def lookup(self, ids):
        need = {i for i in ids if i not in self.scanned}
        if need and self.dir.is_dir():
            for f in sorted(self.dir.glob('*.jsonl.gz')):
                with gzip.open(f, 'rt') as fh:
                    for line in fh:
                        if '"id"' not in line:
                            continue
                        d = json.loads(line)
                        if d['id'] in need:
                            self.rec[d['id']] = (d.get('title'), d.get('families') or [])
            self.scanned |= need
        return {i: self.rec[i] for i in ids if i in self.rec}


def clean_candidates(cands, bad_urls):
    """[(url, is_landing)] of the usable candidates: unique, http(s), not a URL the catalog found to be another document."""
    bad = {norm_url(u) for u in bad_urls}
    out, seen = [], set()
    for c in cands:
        for u, landing in ((c.get('landing_url'), True), (c.get('url'), False)):
            n = norm_url(u)
            if u and re.match(r'https?://', u, re.I) and n and n not in bad and (u, landing) not in seen:
                seen.add((u, landing)); out.append((u, landing))
    return out


def confirm(paper, urls, locs, mapped_arxiv, arx_index, verdicts=None):
    """-> (basis, [confirmed urls]) or (None, []). paper = {doi: [..], oa: [W ids], title, first_author}; urls = clean_candidates(...);
    locs = {W id: set(norm urls)}; mapped_arxiv(doi) -> arXiv id or None; arx_index = ArxivIndex."""
    arx = {}
    for u, _ in urls:
        a = arxiv_of_url(u)
        if a:
            arx.setdefault(a.lower(), []).append(u)
    # 1. a DOI -> arXiv mapping ties the candidate's arXiv id to this work
    for doi in paper['doi']:
        m = mapped_arxiv(doi)
        m = re.sub(r'v\d+$', '', m).lower() if m else None
        if m and m in arx:
            # the S2 / OpenAlex mapping also ties datasets, software and companion papers to a paper (a hand check of 208 found ~12% wrong):
            # it counts only when the arXiv record's own title, where the local index holds it, shares half of the title's words
            rec = arx_index.lookup([m]).get(m)
            if rec and title_overlap(paper['title'], rec[0]) >= MAPPING_MIN_OVERLAP:
                return 'arxiv_id_doi', arx[m]
    # 2. the candidate is a listed location of this very OpenAlex work
    listed = set()
    for w in paper['oa']:
        listed |= locs.get(w, set())
    hit = [u for u, _ in urls if norm_url(u) in listed]
    if hit:
        return 'openalex_location', hit
    # 3. the arXiv record's own title and first author are this paper's
    if arx:
        found = arx_index.lookup(list(arx))
        for a, (t, fams) in found.items():
            if title_match(paper['title'], t) and fams and paper['first_author'] and fam(fams[0]) == paper['first_author']:
                return 'arxiv_metadata', arx[a]
    # 4. a polite landing-page check by the downloads agent said so
    for u, _ in urls:
        if verdicts and verdicts.get((paper['key'], norm_url(u))) == 'match':
            return 'landing_page_metadata', [u]
    return None, []


def load_verdicts(path):
    out = {}
    p = Path(path)
    if p.exists():
        for line in open(p):
            d = json.loads(line)
            if d.get('verdict') in ('match', 'mismatch', 'unreachable') and d.get('robots_ok', True) is not False:
                out[(d['key'], norm_url(d['url']))] = d['verdict']
    return out


def request_rows(school, key, paper, urls):
    """Rows for link-check-requests.tsv: one per unconfirmed candidate URL, with what the landing page must match."""
    return [(urlsplit(u).netloc.lower().removeprefix('www.'), school, key, paper['title'] or '', ';'.join(paper['doi']), paper['first_author'] or '', u,
             'landing' if landing else 'file') for u, landing in urls]
