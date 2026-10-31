"""The automatic identity rule for a downloaded file whose catalog title the collector's own check did not find (identity
'provider_link_only_review_pending'; 2026-10-31, owner). One module, imported by fulltext-push/identity_review.py (the
review of copies already in the catalogs) and by vendor/cmu_tools/collector_wrapper.py (at download time), so the two
cannot drift. docs/UNAVAILABLE.md, "Copies that do not count".

judge(page1, title, first_author, doi, download_url, mapped_arxiv) -> (verdict, evidence):
  pass_title  at least 80% of the title's significant words (>= 3 of them; a shorter title: every word, and the
              author) are in page 1's title region (its first 600 characters), and the first author's family name
              (letters only; a two-letter name as a whole word) or the DOI is on page 1
  pass_arxiv  page 1's arXiv stamp is the arXiv id the file was downloaded as, the work's DOI maps to that id (Semantic
              Scholar / OpenAlex) and the first author is on page 1
  fail        positive evidence of another document, in a readable title region: none of the title's words there, or a
              known first author absent from page 1 with under half of the title's words
  undecided   everything else (no text layer; a title partly matched; no author or DOI to confirm it): the file keeps
              the pending state (never a pass without evidence) and does not count
"""
import gzip, json, re, sqlite3, subprocess, unicodedata
from pathlib import Path

PENDING = 'provider_link_only_review_pending'
TAGS = {'pass_title': 'auto_title_author_page1', 'pass_arxiv': 'auto_arxiv_id_doi_mapping'}
STOP = set('a an the of for and in on to with via from by at is are as its into using toward towards over under through '
           'what when how why which this that these those can be we our or not'.split())
HERE = Path(__file__).resolve().parent


def norm_words(t):
    t = unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower()
    return re.findall(r'[a-z0-9]+', t)


def fam(name):
    name = unicodedata.normalize('NFKD', name or '').encode('ascii', 'ignore').decode().lower()
    if ',' in name:
        return re.sub(r'[^a-z]', '', name.split(',', 1)[0])
    toks = [t for t in re.sub(r'[^a-z \-]', ' ', name).split() if t not in {'jr', 'sr', 'ii', 'iii', 'iv'}]
    return re.sub(r'[^a-z]', '', toks[-1]) if toks else ''


def page_text(path, first=1, last=1):
    try:
        return subprocess.run(['pdftotext', '-f', str(first), '-l', str(last), str(path), '-'], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ''


def ndoi(s):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(s or '').strip(), flags=re.I).lower()


def judge(p1, title, first, doi, download_url, mapped, p12=None, author_authoritative=True):
    if len(re.sub(r'\s+', '', p1 or '')) < 50:
        return 'undecided', dict(why='no text layer on page 1')
    head_text = re.sub(r'\s+', ' ', p1)[:600]
    head = set(norm_words(head_text))
    # letters only: a title set in small caps comes out of pdftotext split ('MMW ORLD', 'DATA R ECIPES')
    head_letters = re.sub(r'[^a-z0-9]', '', unicodedata.normalize('NFKD', head_text).encode('ascii', 'ignore').decode().lower())
    letters1 = re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', p1[:4000]).encode('ascii', 'ignore').decode().lower())
    tw = [x for x in norm_words(title) if len(x) >= 3 and x not in STOP]
    frac = sum(x in head or (len(x) >= 4 and x in head_letters) for x in tw) / max(1, len(tw))
    # a title in another script (Cyrillic, Thai, Japanese: nothing survives the ASCII folding): its own characters, in
    # order, at the top of page 1
    if len(tw) < 3:
        t_raw = re.sub(r'[\W_]', '', (title or '').lower())
        if len(t_raw) >= 8 and sum(not ch.isascii() for ch in t_raw) > len(t_raw) / 2:
            if t_raw[:40] in re.sub(r'[\W_]', '', p1[:2000].lower()):
                frac, tw = 1.0, ['_'] * 3
    first = first or ''
    author_ok = (len(first) >= 3 and first in letters1) or (len(first) == 2 and first in set(norm_words(p1)))
    d = ndoi(doi)
    doi_ok = bool(d) and d in p1.lower()
    ev = dict(title_words_found=round(frac, 2), first_author=first or None, author_on_page1=author_ok, doi_on_page1=doi_ok)
    title_ok = (len(tw) >= 3 and frac >= 0.8) or (1 <= len(tw) < 3 and frac == 1.0 and author_ok)
    if title_ok and (author_ok or doi_ok):
        return 'pass_title', ev
    stamp = re.search(r'arXiv:(\d{4}\.\d{4,5})', p1)
    url_ax = re.search(r'(\d{4}\.\d{4,5})(?:v\d+)?\.pdf', download_url or '')
    mapped = re.sub(r'v\d+$', '', mapped) if mapped else None
    ev.update(arxiv_stamp=stamp.group(1) if stamp else None, arxiv_mapped=mapped)
    # the id the file was downloaded as, when the URL is known (the collector passes the final URL; a URL without an
    # arXiv id, e.g. a repository copy of the preprint, leaves the stamp and the DOI mapping to decide)
    url_ok = bool(url_ax and stamp and url_ax.group(1) == stamp.group(1)) if (download_url and url_ax) else True
    if stamp and url_ok and stamp.group(1) == mapped and author_ok:
        return 'pass_arxiv', ev
    # reject only on positive evidence of another document (a hand check on 2026-10-31 found 14 of 15 rejections of the
    # earlier 'not confirmed = rejected' rule to be the paper, retitled or abbreviated)
    # A second fresh sample (2026-10-31) still found retitled papers among 'under half of the title' rejections (Puff
    # trains -> Speech can produce jet-like transport; Hot band sound): only these count as another document:
    #   none of the title's words in a readable title region (a reviewer response, another paper), or
    #   a known first author absent from page 1 with under half of the title's words
    nonspace = re.sub(r'\s', '', head_text)
    # readable: mostly letters, and real words (a font without a Unicode map comes out as a letter-shifted jumble,
    # '&DOFXODWLQJ...', which is all letters but no words; third sample)
    common = {'the', 'of', 'and', 'in', 'to', 'a', 'for', 'on', 'with', 'is', 'by', 'from', 'at', 'an', 'we', 'this', 'that', 'university', 'department'}
    readable = (bool(nonspace) and sum(ch.isalpha() for ch in nonspace) / len(nonspace) >= 0.6
                and sum(w in common for w in norm_words(head_text)) >= 2)
    # a cover, disclaimer or licence page in front of the paper: the title on page 2 is no mismatch (third sample)
    later = p12 if p12 is not None else p1
    later_words = set(norm_words(later[:6000]))
    frac12 = sum(x in later_words for x in tw) / max(1, len(tw))
    # the first author must be an authoritative one (the lab paper's byline, the work's own author list); the school
    # people a catalog graph lists are not its first author, so their absence proves nothing (third sample: 'braverman')
    if readable and frac12 < 0.5 and ((len(tw) >= 3 and frac == 0) or (first and author_authoritative and not author_ok and frac < 0.5)):
        return 'fail', ev
    return 'undecided', dict(ev, why='not confirmed and not contradicted: title partly matched or no author / DOI to confirm it')


def reason(ev):
    return (f"{ev.get('title_words_found', 0):.0%} of the title's words in page 1's title region, first author "
            f"{'on' if ev.get('author_on_page1') else 'not on'} page 1, DOI {'on' if ev.get('doi_on_page1') else 'not on'} page 1")


# ---------------------------------------------------------------- inputs (lazy, cached per process)
_LAB, _S2, _OA = {}, {}, {}


def lab_first_authors(code_root, school):
    """{work id / 'doi:..' / 't:..': first author family} from hierarchy/<school>/lab_papers.jsonl.gz (byline order)."""
    if school not in _LAB:
        out = {}
        p = Path(code_root) / 'hierarchy' / school / 'lab_papers.jsonl.gz'
        if p.exists():
            for line in gzip.open(p, 'rt'):
                r = json.loads(line)
                f = fam((r.get('byline') or [''])[0]) or (fam((r.get('pis') or [''])[0]) if not r.get('byline') else '')
                if not f:
                    continue
                oa = (r.get('oa') or '').rsplit('/', 1)[-1]
                for k in (r.get('work'), f'{school}_oa_{oa}' if oa else None, 'doi:' + ndoi(r.get('doi')) if r.get('doi') else None,
                          't:' + re.sub(r'[^a-z0-9]', '', (r.get('title') or '').lower())):
                    if k:
                        out.setdefault(k, f)
        _LAB[school] = out
    return _LAB[school]


def graph_first_author(g):
    """(family, authoritative): the first of a catalog work's own 'authors' list (authoritative), else the first school
    person its graph lists (not the paper's first author: it may confirm, never contradict)."""
    try:
        g = json.loads(g or '{}') if isinstance(g, str) else (g or {})
    except ValueError:
        return '', False
    for a in g.get('authors') or []:
        n = a.get('name') if isinstance(a, dict) else a
        if n:
            return fam(n), True
    for k, v in g.items():
        if isinstance(v, list) and k.endswith(('_faculty', '_students', '_postdocs')) and v:
            n = v[0].get('name') if isinstance(v[0], dict) else v[0]
            if n:
                return fam(n), False
    return '', False


def first_author(code_root, school, work_id, title, doi, graph_json=None, catalog=None):
    """(family, authoritative): the lab paper's first byline author, else graph_first_author."""
    lab = lab_first_authors(code_root, school)
    f = lab.get(work_id) or (lab.get('doi:' + ndoi(doi)) if doi else None) or lab.get('t:' + re.sub(r'[^a-z0-9]', '', (title or '').lower()))
    if f:
        return f, True
    if graph_json is None and catalog is not None:
        db = sqlite3.connect(f'file:{catalog}?mode=ro', uri=True, timeout=60)
        row = db.execute('SELECT graph_json FROM works WHERE id=?', (work_id,)).fetchone()
        db.close()
        graph_json = row[0] if row else None
    return graph_first_author(graph_json)


def mapped_arxiv(doi, s2_cache_path=None, oa_cache_path=None, oa_id=None):
    """The arXiv id Semantic Scholar (cached /paper/batch answers) or OpenAlex (the ledger's cached records) gives the DOI."""
    d = ndoi(doi)
    if s2_cache_path and '_' not in _S2 and Path(s2_cache_path).exists():
        for line in open(s2_cache_path):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            dd = r.get('data') or {}
            a = (dd.get('externalIds') or {}).get('ArXiv') if isinstance(dd, dict) else None
            if a and str(r.get('id', '')).startswith('DOI:'):
                _S2[r['id'][4:].lower()] = a
        _S2['_'] = 1
    if d and d in _S2:
        return _S2[d]
    if oa_cache_path and '_' not in _OA and Path(oa_cache_path).exists():
        arx = re.compile(r'arxiv\.org[:/](?:abs/|pdf/)?(\d{4}\.\d{4,5})', re.I)
        for line in open(oa_cache_path):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            for loc in ((r.get('body') or {}).get('locations') or []):
                m = arx.search(' '.join(str(loc.get(k) or '') for k in ('landing_page_url', 'pdf_url')))
                if m:
                    _OA[r['id']] = m.group(1)
                    dd = ndoi((r.get('body') or {}).get('doi'))
                    if dd:
                        _OA['doi:' + dd] = m.group(1)
                    break
        _OA['_'] = 1
    return (_OA.get(oa_id) if oa_id else None) or (_OA.get('doi:' + d) if d else None)
