"""Lab publication pages as an open-copy channel (2026-10-26): a lab paper without a local copy gains the free PDF its own
PI's lab pages link (author copy, arXiv, lab or university server) - most of what remains is paywalled at IEEE, ACM and
Springer, and the labs often post their own copies.

labpages  the lab pages the lab-pages passes already captured (hierarchy/<school>/labpage-captures.sqlite, zlib HTML /
          BibTeX, live or Wayback id_ captures), each assigned to the PIs whose lab-page evidence names it
          (hierarchy/<school>/labpage-evidence.json: lab_site, people_page(s), pubs_pages, the pages students were
          quoted from) or lies under one of their site roots (a root another PI's root lies under is too general and is
          dropped). A missing lab paper of that PI matches a bibliography entry when
            - the smallest HTML block containing its normalized title (pi_hierarchy.norm_title, >= 30 characters) is one
              entry (at most max(1500, 3 x title + 600) normalized characters), or else the links within 150 characters
              before / 350 after the title in the page's text stream, or a BibTeX entry whose title field equals it; or
            - a link's URL carries the paper's DOI (or its arXiv id).
          Usable links: arXiv abs/pdf (-> arXiv's bulk copy on GCS, never arxiv.org), and PDFs (a .pdf path, or an anchor
          reading pdf / paper / preprint / author copy) on the lab's, a university's or another open host; never
          publisher hosts that need a login (IEEE Xplore, ACM DL, Springer, ScienceDirect, Wiley, ...), OpenReview (403
          to automated clients), ResearchGate / Academia.edu, Google Drive / Dropbox; never slides, posters, talks,
          supplements or BibTeX files. At most two PDFs per entry (nearest to the title first).
pihomes   fallback for the lab papers still missing: each PI's personal homepage / lab site and the publication pages
          they link (an anchor reading publications / papers / bibliography on the same site) that the captures lack,
          fetched once (robots.txt honoured, one request per 3 s per run, cached in raw/pihomes.sqlite), plus a homepage
          for PIs without lab-page evidence when raw/pi-homepages-<school>.json names one; then the labpages matcher.
The collectors fetch the candidates (robots.txt, per-host pacing, the title check on page 1) - nothing here downloads a
PDF. Imported by lab_channels.py (steps labpages, pihomes).
"""
import html, json, re, sqlite3, sys, unicodedata, zlib
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F

DRY = False
MIN_T = 30
DENY = ('ieeexplore.ieee.org', 'ieee.org', 'dl.acm.org', 'acm.org', 'link.springer.com', 'springer.com', 'sciencedirect.com', 'elsevier.com',
        'onlinelibrary.wiley.com', 'wiley.com', 'tandfonline.com', 'jstor.org', 'researchgate.net', 'academia.edu', 'scholar.google.com',
        'books.google.com', 'drive.google.com', 'docs.google.com', 'dropbox.com', 'dropboxusercontent.com', 'openreview.net', 'proquest.com',
        'ebscohost.com', 'ingentaconnect.com', 'emerald.com', 'cell.com', 'pubs.acs.org', 'iopscience.iop.org', 'pubs.aip.org', 'opg.optica.org',
        'spiedigitallibrary.org', 'ascelibrary.org', 'annualreviews.org', 'karger.com', 'liebertpub.com', 'epubs.siam.org', 'worldscientific.com',
        'degruyter.com', 'cambridge.org', 'academic.oup.com', 'journals.aps.org', 'journals.sagepub.com', 'nature.com', 'science.org',
        'pnas.org', 'mdpi.com', 'frontiersin.org', 'linkedin.com', 'twitter.com', 'x.com', 'facebook.com', 'youtube.com', 'vimeo.com',
        'scitation.org', 'informs.org', 'pubsonline.informs.org', 'muse.jhu.edu', 'taylorfrancis.com', 'igi-global.com', 'inderscience.com',
        'sciencemag.org', 'thelancet.com', 'nejm.org', 'jamanetwork.com', 'bmj.com', 'sci-hub.se', 'sci-hub.ru', 'libgen.rs')
PDFWORD = re.compile(r'^\W*(?:pdf|paper|preprint|full ?text|full ?paper|author\W?s? (?:copy|version|pdf)|manuscript|download(?: pdf| paper)?|'
                     r'(?:paper|preprint|article|camera\W?ready) ?(?:pdf)?|pdf ?(?:file|version|preprint|paper)?|e?print|local copy|'
                     r'accepted (?:version|manuscript)|postprint)\W*(?:\(\s*[\d.]+\s*[kmg]i?b\s*\))?\W*$', re.I)
NOTPAPER = re.compile(r'slide|poster|talk|present|video|supp|appendi|bibtex|\bbib\b|abstract|\bcode\b|github|errat|tutorial|\bcv\b|resume|'
                      r'teaser|demo|\bppt|keynote|handout|lecture|syllabus|dataset|website|project page|blog|press|news|thesis|dissertation|'
                      r'review|citation|cite|award|cover', re.I)
NOTPAPER_FILE = re.compile(r'slide|poster|talk|supp|appendi|present|handout|\bppt|\.bib$|-sm\.|_sm\.', re.I)
WB = re.compile(r'^https?://web\.archive\.org/web/\d+[a-z_]*/(.+)$', re.I)


def unwrap(u):
    m = WB.match(u or '')
    if m:
        u = m.group(1)
        if not re.match(r'https?://', u):
            u = 'http://' + u.lstrip('/')
    return u


def host(u):
    return (urlsplit(u).hostname or '').lower()


def denied(u):
    h = host(u)
    return any(h == b or h.endswith('.' + b) for b in DENY)


OPEN_LANDING = ('par.nsf.gov', 'dspace.mit.edu', 'infoscience.epfl.ch', 'hal.science', 'hal.archives-ouvertes.fr', 'kilthub.cmu.edu',
                'osti.gov', 'cbmm.mit.edu', 'eprints.whiterose.ac.uk', 'zenodo.org', 'repository.tudelft.nl', 'research-collection.ethz.ch')


def same_site(a, b):
    a, b = a.split('.'), b.split('.')
    return len(a) >= 2 and len(b) >= 2 and a[-2:] == b[-2:]


def classify(u, text, title_anchor=False, page_url=None):
    """('arxiv', id) | ('pdf', url) | ('landing', url) | ('openreview', url) | None for one link of an entry. A landing
    page is the paper's own page on the lab's site or an open repository, reached by the title link or a "pdf" /
    "paper" anchor: the collector takes its one primary PDF link (citation_pdf_url / an unambiguous PDF link)."""
    from cs_open_copies import arxiv_id
    import s2_key_lookup as s2k, core_search as cs
    if not u or not u.startswith('http'):
        return None
    h = host(u)
    if h.endswith('arxiv.org'):
        a = arxiv_id(re.sub(r'[?#].*$', '', u))
        return ('arxiv', re.sub(r'v\d+$', '', a)) if a else None
    if h == 'openreview.net' or h.endswith('.openreview.net'):
        return ('openreview', u)
    if denied(u) or not s2k.ok_pdf(u) or not cs.usable(u):
        return None
    t = re.sub(r'\s+', ' ', text or '').strip()
    if not title_anchor and NOTPAPER.search(t) and not PDFWORD.match(t):
        return None
    path = unquote(urlsplit(u).path)
    last = path.rsplit('/', 1)[-1]
    if NOTPAPER_FILE.search(last):
        return None
    if re.search(r'\.pdf$', path, re.I) or re.search(r'[?&](?:file|f|download|name)=[^&]*\.pdf', u, re.I):
        return ('pdf', u)
    if PDFWORD.match(t) and not re.search(r'\.(?:html?|php|aspx?|bib|ps|gz|zip|tgz|pptx?|docx?|mp4|txt)$', path, re.I):
        return ('pdf', u)  # an anchor reading "pdf" / "paper" to an extensionless file on an open host; the collector checks the type
    if (title_anchor or PDFWORD.match(t)) and not re.search(r'\.(?:bib|ps|gz|zip|tgz|pptx?|docx?|mp4|mov|txt|png|jpe?g|gif)$', path, re.I) \
            and h not in ('github.com', 'gitlab.com', 'colab.research.google.com', 'huggingface.co') \
            and (any(h == b or h.endswith('.' + b) for b in OPEN_LANDING) or (page_url and same_site(h, host(page_url)))) \
            and path.strip('/') and nurl(u) != nurl(page_url or ''):
        return ('landing', u)
    return None


STOP = {'with', 'from', 'that', 'this', 'their', 'using', 'based', 'into', 'over', 'under', 'via', 'towards', 'toward', 'about', 'when',
        'which', 'what', 'learning', 'analysis', 'model', 'models', 'system', 'systems', 'approach', 'method', 'methods', 'study', 'data'}
class Page:
    """One captured page: blocks (text + links with anchor text, a parent's including its children's) and the page's
    normalized text stream with each link's position in it."""
    TAGS = {'li', 'p', 'tr', 'dd', 'dt', 'td', 'div', 'section', 'article', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'ul', 'ol',
            'table', 'body', 'span', 'font'}
    BREAK = {'li', 'p', 'tr', 'dd', 'dt', 'div', 'section', 'article', 'br', 'hr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'ul', 'ol'}

    def __init__(self, body, base):
        self.blocks, self.stream, self.links = [], [], []  # stream: normalized text pieces; links: (pos, url, anchor text)
        stack = [dict(tag='root', text=[], links=[])]
        pos = [0]
        cur = [None]  # the open <a>: [url, text parts, pos]
        outer = self

        def close_to(i):
            while len(stack) > i:
                b = stack.pop()
                outer.blocks.append(b)
                stack[-1]['text'] += b['text']; stack[-1]['links'] += b['links']

        class P(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag in ('script', 'style'):
                    self.skip = tag
                if tag in Page.TAGS:
                    stack.append(dict(tag=tag, text=[], links=[]))
                if tag == 'a':
                    h = dict(attrs).get('href')
                    if h and not h.strip().lower().startswith(('mailto:', 'javascript:', '#')):
                        try:
                            u = unwrap(urljoin(base, html.unescape(h.strip())))
                        except ValueError:
                            u = None
                        cur[0] = [u, [], pos[0]] if u else None

            def handle_endtag(self, tag):
                if tag in ('script', 'style'):
                    self.skip = None
                if tag == 'a' and cur[0]:
                    u, parts, p = cur[0]
                    link = (u, ' '.join(parts).strip(), p)
                    stack[-1]['links'].append(link); outer.links.append(link)
                    cur[0] = None
                if tag in Page.TAGS and len(stack) > 1:
                    for i in range(len(stack) - 1, 0, -1):
                        if stack[i]['tag'] == tag:
                            close_to(i); break

            def handle_data(self, data):
                if getattr(self, 'skip', None):
                    return
                stack[-1]['text'].append(data)
                if cur[0]:
                    cur[0][1].append(data)
                k = F.nt(data)
                outer.stream.append(k); pos[0] += len(k)

        p = P(convert_charrefs=True)
        try:
            p.feed(body); p.close()
        except Exception:
            pass
        close_to(1)
        b = stack.pop(); self.blocks.append(b)
        for b in self.blocks:
            b['nt'] = F.nt(' '.join(b['text']))
        self.text = ''.join(self.stream)

    def entry(self, t, raw=''):
        """[(url, anchor text, distance)] of the bibliography entry carrying normalized title t."""
        best = None
        for b in self.blocks:
            if t in b['nt'] and (best is None or len(b['nt']) < len(best['nt'])):
                best = b
        s = self.text.find(t)
        if best is not None and len(best['nt']) <= max(1500, 3 * len(t) + 600):
            return [(u, a, abs(p - s) if s >= 0 else 0) for u, a, p in dict.fromkeys(best['links'])], 'block'
        if s < 0:
            return [], None
        e = s + len(t)
        near = [(u, a, abs(p - s)) for u, a, p in self.links if s - 100 <= p <= e + 250]
        own = [x for x in near if F.nt(x[1]) and (t in F.nt(x[1]) or (len(F.nt(x[1])) >= MIN_T and F.nt(x[1]) in t))]
        if own:  # the title is itself the link: that link is the entry's
            return own, 'window_title_link'
        # otherwise a link near the title is the entry's only when its file name shares a word with the title, or it is
        # the nearest "pdf" / "paper" anchor after the title (a neighbouring entry's links sit in the same window)
        raw = unicodedata.normalize('NFKD', raw or '').encode('ascii', 'ignore').decode().lower()
        words = {w for w in re.findall(r'[a-z0-9]{4,}', raw) if w not in STOP}
        out = [x for x in near if words & set(re.findall(r'[a-z0-9]{4,}', unquote(urlsplit(x[0]).path.rsplit('/', 1)[-1]).lower()))]
        after = sorted((x for x in self.links if s <= x[2] <= e + 250 and PDFWORD.match(x[1] or '')), key=lambda x: x[2])
        if after:
            out.append((after[0][0], after[0][1], after[0][2] - s))
        return out, 'window'


BIB_ENTRY = re.compile(r'@\s*\w+\s*[{(]')


def bib_field(entry, name):
    m = re.search(r'(?<![a-z])' + name + r'\s*=\s*', entry, re.I)
    if not m:
        return None
    i = m.end()
    if i < len(entry) and entry[i] == '{':
        depth, j = 0, i
        while j < len(entry):
            if entry[j] == '{':
                depth += 1
            elif entry[j] == '}':
                depth -= 1
                if depth == 0:
                    return entry[i + 1:j]
            j += 1
        return None
    if i < len(entry) and entry[i] == '"':
        j = entry.find('"', i + 1)
        return entry[i + 1:j] if j > 0 else None
    return None


def bib_entries(text, base):
    """[(normalized title, [(url, field name)])] of the BibTeX entries in a text (a .bib file or a <pre> block)."""
    out = []
    starts = [m.start() for m in BIB_ENTRY.finditer(text)]
    for i, s in enumerate(starts):
        e = text[s:starts[i + 1] if i + 1 < len(starts) else len(text)]
        t = bib_field(e, 'title')
        if not t:
            continue
        links = []
        for f in ('pdf', 'url', 'paper', 'preprint', 'eprint', 'arxiv', 'link', 'file'):
            v = bib_field(e, f)
            if not v:
                continue
            v = v.strip()
            if f in ('eprint', 'arxiv') and re.fullmatch(r'\d{4}\.\d{4,5}(v\d+)?', v):
                v = 'https://arxiv.org/abs/' + v
            try:
                links.append((unwrap(urljoin(base, v)), f))
            except ValueError:
                pass
        out.append((F.nt(t), links))
    return out


def decode(content):
    try:
        b = zlib.decompress(content)
    except Exception:
        b = content or b''
    return b.decode('utf-8', 'replace') if isinstance(b, bytes) else str(b)


def nurl(u):
    p = urlsplit(unwrap(u or ''))
    h = (p.hostname or '').lower()
    h = h[4:] if h.startswith('www.') else h
    return h + (p.path or '/')


def root_of(u):
    r = nurl(u)
    if not r.endswith('/'):
        last = r.rsplit('/', 1)[-1]
        r = r.rsplit('/', 1)[0] + '/' if ('.' in last or r.count('/') > 1) else r + '/'
    return r


def pi_pages(school):
    """{PI: set of normalized URLs named in their lab-page evidence}, {PI: site roots} (roots that are not more general
    than another PI's root)."""
    ev = json.loads((F.SCHOOLS / 'hierarchy' / school / 'labpage-evidence.json').read_text())
    urls, roots = defaultdict(set), defaultdict(set)
    for x in ev:
        pi = x['pi']
        us = [x.get('lab_site'), x.get('people_page')] + [p.get('url') if isinstance(p, dict) else p for p in (x.get('people_pages') or [])]
        us += [p.get('url') if isinstance(p, dict) else p for p in (x.get('pubs_pages') or [])]
        for st in x.get('students') or []:
            us.append(st.get('url'))
            for a in st.get('also') or []:
                us.append(a.get('url'))
        for u in us:
            if u and isinstance(u, str) and u.startswith('http'):
                urls[pi].add(nurl(u))
        for u in [x.get('lab_site'), x.get('people_page')] + [p.get('url') if isinstance(p, dict) else p for p in (x.get('pubs_pages') or [])]:
            if u and isinstance(u, str) and u.startswith('http'):
                roots[pi].add(root_of(u))
    allroots = [(r, pi) for pi, rs in roots.items() for r in rs]
    for pi in list(roots):
        keep = set()
        for r in roots[pi]:
            # too general: another PI's root lies strictly under it, or it is a bare host shared by other PIs' roots
            if any(q != pi and r2 != r and r2.startswith(r) for r2, q in allroots):
                continue
            keep.add(r)
        roots[pi] = keep
    return urls, roots


def page_owners(url, final, urls, roots):
    out = set()
    for u in {nurl(url), nurl(final or url)}:
        for pi, us in urls.items():
            if u in us:
                out.add(pi)
        for pi, rs in roots.items():
            if any(u.startswith(r) for r in rs):
                out.add(pi)
    return out


def iter_captures(school):
    db = sqlite3.connect(f"file:{F.SCHOOLS / 'hierarchy' / school / 'labpage-captures.sqlite'}?mode=ro", uri=True, timeout=60)
    hi = db.execute('SELECT MAX(id) FROM captures').fetchone()[0] or 0
    for lo in range(0, hi + 1, 200):
        for row in db.execute("SELECT url, final_url, capture_url, content_type, content FROM captures WHERE id >= ? AND id < ? AND status = 200 "
                              "AND content IS NOT NULL", (lo, lo + 200)).fetchall():
            ct = (row[3] or '').lower()
            if 'json' in ct or 'pdf' in ct or 'image' in ct or '/cdx/' in (row[0] or ''):
                continue
            yield row
    db.close()


def match_pages(pages, by_pi, known, n, source, has_arxiv):
    """pages: [(url, owners, body, content type)] -> candidate rows (PDFs) and {work: (arXiv id, page)}."""
    rows, arx = [], {}
    done = set()
    for url, owners, body, ct in pages:
        items = [(r, w) for pi in owners for r, w in by_pi.get(pi, [])]
        if not items:
            continue
        items = list({w: (r, w) for r, w in items}.values())
        is_bib = 'bibtex' in ct or url.lower().endswith('.bib') or (body.lstrip()[:1] == '@')
        page = None if is_bib else Page(body, url)
        bibs = bib_entries(html.unescape(body) if not is_bib else body, url) if (is_bib or '@inproceedings' in body.lower() or '@article' in body.lower()) else []
        bib_by_t = defaultdict(list)
        for t, links in bibs:
            bib_by_t[t] += links
        for r, w in items:
            t = F.nt(r['title'])
            found = []  # (kind, value, distance, how)
            if len(t) >= MIN_T:
                for u, f in bib_by_t.get(t, []):
                    c = classify(u, 'pdf' if f in ('pdf', 'paper', 'preprint', 'file') else '', False)
                    if c:
                        found.append((c[0], c[1], 0, 'bibtex'))
                if page is not None and t in page.text:
                    links, how = page.entry(t, r['title'])
                    for u, a, d in links:
                        na = F.nt(a)
                        c = classify(u, a, title_anchor=bool(na) and (t in na or (na in t and len(na) >= MIN_T)), page_url=url)
                        if c:
                            found.append((c[0], c[1], d, how))
            d_ = F.ndoi(r.get('doi'))
            ax = r.get('arxiv')
            if page is not None and (len(d_) >= 10 or ax):
                for u, a, p in page.links:
                    lu = unquote(u).lower()
                    if len(d_) >= 10 and not d_.startswith('10.48550/') and d_ in lu and not lu.startswith(('https://doi.org', 'http://doi.org', 'https://dx.doi.org', 'http://dx.doi.org')):
                        c = classify(u, a or 'pdf')
                        if c:
                            found.append((c[0], c[1], 0, 'doi_in_link'))
                    if ax and ax in lu and 'arxiv.org' in lu:
                        found.append(('arxiv', re.sub(r'v\d+$', '', ax), 0, 'arxiv_id_in_link'))
            if page is not None and len(t) >= MIN_T and t in page.text:
                n[f'{source}_title_on_page'] += 1
            if not found:
                continue
            n[f'{source}_entries_matched'] += 1
            arxs = [v for k, v, _, _ in found if k == 'arxiv']
            if any(k == 'openreview' for k, *_ in found):
                n[f'{source}_openreview_links_skipped'] += 1
            if arxs and not has_arxiv(known[w]) and w not in arx:
                arx[w] = (arxs[0], url)
            pdfs = sorted({v: d for k, v, d, _ in found if k == 'pdf'}.items(), key=lambda x: x[1])[:2]
            if not pdfs and not arxs:  # no PDF in the entry: the paper's own landing page (one only)
                lands = sorted({v: d for k, v, d, _ in found if k == 'landing'}.items(), key=lambda x: x[1])
                if len(lands) == 1:
                    pdfs = lands; n[f'{source}_landing_pages'] += 1
            for v, _ in pdfs:
                if (w, v) in done:
                    continue
                done.add((w, v))
                hows = sorted({h for k, vv, _, h in found if vv == v})
                rows.append(dict(work_id=w, url=v, landing_url=url, version=None, source=source,
                                 detail=json.dumps(dict(pis=sorted(set(owners) & set(r.get('pis') or [])), lab_page=url, link=v, match=hows,
                                                        title=r['title'], doi=r.get('doi')))))
                n[f'{source}_pdf_links'] += 1
    return rows, arx


def by_pi_of(miss):
    by_pi = defaultdict(list)
    for r, w in miss:
        for pi in r.get('pis') or []:
            by_pi[pi].append((r, w))
    return by_pi


def bulk(arx, source, n):
    if not arx:
        return []
    if DRY:
        n[f'{source}_arxiv_dry'] = len(arx)
        return []
    rows, n[f'{source}_arxiv_not_in_bulk'] = F.bulk_rows({w: a for w, (a, _) in arx.items()}, source + '_arxiv_bulk')
    for r in rows:
        r['detail'] = json.dumps(dict(arxiv=r['detail'], lab_page=arx[r['work_id']][1]))
    n[f'{source}_arxiv'] = len(rows)
    return rows


def step_labpages(school, miss, known, n, has_arxiv):
    urls, roots = pi_pages(school)
    by_pi = by_pi_of(miss)
    n['labpages_pis_with_missing'] = sum(1 for pi in by_pi if pi in urls)
    pages, seen = [], 0
    for url, final, cap, ct, content in iter_captures(school):
        seen += 1
        owners = page_owners(url, final, urls, roots)
        if owners & set(by_pi):
            base = unwrap(final or url)
            pages.append((base if base.startswith('http') else unwrap(url), owners, decode(content), (ct or '').lower()))
    n['labpages_captures'] = seen
    n['labpages_pages_used'] = len(pages)
    rows, arx = match_pages(pages, by_pi, known, n, 'labpages', has_arxiv)
    return rows + bulk(arx, 'labpages', n)


# ---------------------------------------------------------------- PI homepages (fallback)

PUBWORD = re.compile(r'^\W*(?:(?:selected|recent|all|full|my|complete|refereed|journal|conference)\s+)?(?:publications?|papers|publication list|'
                     r'bibliography|research papers|research|preprints|articles|pubs)(?:\s+(?:list|by year|by topic))?\W*$', re.I)


def step_pihomes(school, miss, known, n, has_arxiv):
    import requests
    from lab_channels import Pacer, polite_get
    urls, roots = pi_pages(school)
    ev = json.loads((F.SCHOOLS / 'hierarchy' / school / 'labpage-evidence.json').read_text())
    by_pi = by_pi_of(miss)
    sites = defaultdict(list)
    for x in ev:
        for u in (x.get('lab_site'), x.get('people_page')):
            if u and u.startswith('http'):
                sites[x['pi']].append(u)
    extra = F.HERE / 'raw' / f'pi-homepages-{school}.json'
    if extra.exists():
        for pi, us in json.loads(extra.read_text()).items():
            for u in us:
                sites[pi].append(u)
                urls[pi].add(nurl(u)); roots[pi].add(root_of(u))
    captured = {}
    for url, final, cap, ct, content in iter_captures(school):
        for u in (url, final):
            if u:
                captured.setdefault(nurl(u), (unwrap(url), decode(content), (ct or '').lower()))
    s = requests.Session(); s.headers['User-Agent'] = F.UA
    pacer, robots = Pacer(3.0), {}
    cache = sqlite3.connect(str(F.HERE / 'raw' / 'pihomes.sqlite'))
    cache.execute('CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, ok INT, fetched_at TEXT, body BLOB)')

    def get(u):
        k = nurl(u)
        if k in captured:
            return captured[k][1], True
        row = cache.execute('SELECT ok, body FROM pages WHERE url=?', (u,)).fetchone()
        if row:
            return (zlib.decompress(row[1]).decode('utf-8', 'replace') if row[0] else None), False
        if DRY:
            n['pihomes_would_fetch'] += 1
            return None, False
        body = polite_get(s, u, pacer, robots)
        cache.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?)', (u, int(body is not None), F.now(), zlib.compress((body or '').encode())))
        cache.commit()
        n['pihomes_fetched'] += 1
        return body, False

    pages = []
    for pi in sorted(by_pi):
        if pi not in sites:
            n['pihomes_pis_without_site'] += 1
            continue
        got = []
        for root in list(dict.fromkeys(sites[pi]))[:3]:
            body, cap = get(root)
            if body is None:
                continue
            if not cap:
                got.append((root, body))
            h = host(root)
            subs = []
            for m in re.finditer(r'<a\s[^>]*href\s*=\s*["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', body, re.S | re.I):
                txt = html.unescape(re.sub(r'<[^>]+>', '', m.group(2))).strip()
                if PUBWORD.match(txt):
                    try:
                        u = unwrap(urljoin(root, html.unescape(m.group(1))))
                    except ValueError:
                        continue
                    if host(u).split('.')[-2:] == h.split('.')[-2:] and not re.search(r'\.(pdf|ps|gz|zip)$', u, re.I):
                        subs.append(u)
            for u in list(dict.fromkeys(subs))[:3]:
                b, cap = get(u)
                if b and not cap:
                    got.append((u, b))
        n['pihomes_pis_with_pages'] += bool(got)
        for u, b in got:
            ct = 'bibtex' if u.lower().endswith('.bib') else 'html'
            pages.append((u, {pi}, b, ct))
    cache.close()
    n['pihomes_pages'] = len(pages)
    rows, arx = match_pages(pages, by_pi, known, n, 'pihomes', has_arxiv)
    return rows + bulk(arx, 'pihomes', n)
