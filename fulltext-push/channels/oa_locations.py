"""Channel oa_locations (2026-11-04, owner: bulk open-access sources, 1): every open location of every OpenAlex record that is the
lab paper, from our local OpenAlex snapshot (docs/OPENALEX-SNAPSHOT.md; main store plus the ext-<school> stores). OpenAlex's
locations are Unpaywall's data, so this is the Unpaywall source at no cost (no API call at all).

Beyond the `openalex` channel (the paper's own record, the usual hosts):
  - the other OpenAlex records of the same paper: the record with the paper's DOI, and the records with the same normalized title
    (>= 20 characters) and the same first author's family name published within 2 years (a preprint and its journal version are often
    two works); every location of each of them is read, not just best_oa_location. Tightened after the hand check of 2026-11-04 (a handbook
    chapter matched for its book): a sibling counts only when its OpenAlex `type` equals the paper's own record's and that type is an article-like
    one (not book, book-chapter, dataset, report, ...); no own record, no siblings
  - best_oa_location and open_access.oa_url, which `locations` may lack
  - repository versions: a repository location's PDF or landing page even when OpenAlex marks it not open; an accepted or
    submitted manuscript's landing page on any host the collectors may use
  - arXiv locations of the paper's OWN record only (-> arXiv's bulk copy on GCS, never arxiv.org), and only when the id's title in the local arXiv
    harvest, if the id is in it, is compatible with the paper's title (bulk_oa.title_compatible) and PubMed Central locations (-> the PMC open-data files)
The collectors' identity check (the catalog title in the file, page 1) applies to every candidate; the matching of sibling
records is the local rule of fulltext-push/bulk_oa.py (title + first author, year within 2).
"""
NAME = 'oa_locations'


def APPLIES(school, paper):
    return True


def _first_family(body):
    import bulk_oa as B
    for a in (body or {}).get('authorships') or []:
        n = (a.get('author') or {}).get('display_name')
        if n:
            return B.fam(n)
    return ''


ARTICLE_LIKE = {'article', 'preprint', 'review', 'letter'}


def siblings(p, stores, tix, own=None):
    """Other OpenAlex records of the paper: same DOI, or same normalized title + first author's family + year within 2; only of the own
    record's type, which must be article-like (a book and its chapters share titles)."""
    if not own or own.get('type') not in ARTICLE_LIKE:
        return []
    import bulk_oa as B
    import ftp_common as F
    out, seen = [], {p.r.get('oa'), own.get('id')}
    for b in B.oa_by_doi(stores, p.r.get('doi')) if p.r.get('doi') else []:
        if b.get('id') not in seen:
            seen.add(b.get('id')); out.append(('doi', b))
    nt = F.nt(p.r.get('title'))
    fam0 = B.fam((p.r.get('byline') or [''])[0])
    if len(nt) >= 20 and fam0:
        for wid in tix.get(nt, []):
            if wid in seen:
                continue
            b = B.oa_by_id(stores, wid)
            if not b or _first_family(b) != fam0:
                continue
            y, y0 = b.get('publication_year'), p.r.get('year')
            if y and y0 and abs(int(y) - int(y0)) > 2:
                continue
            seen.add(wid); out.append(('title_author', b))
    return [(h, b) for h, b in out if b.get('type') == own.get('type')]


def extra_locations(body):
    """best_oa_location and open_access.oa_url as location dicts when `locations` does not hold them."""
    have = {(l.get('pdf_url'), l.get('landing_page_url')) for l in body.get('locations') or []}
    out = []
    b = body.get('best_oa_location')
    if b and (b.get('pdf_url'), b.get('landing_page_url')) not in have:
        out.append(b)
    u = (body.get('open_access') or {}).get('oa_url')
    if u and not any(u in k for k in have):
        out.append(dict(pdf_url=u if u.lower().split('?')[0].endswith('.pdf') else None, landing_page_url=u, is_oa=True))
    return out


def manuscript_rows(work_id, body):
    """An accepted or submitted manuscript's landing page on a host the collectors may use, when the plain location rule kept nothing of it."""
    import s2_key_lookup as s2k
    import core_search as cs
    rows = []
    for loc in body.get('locations') or []:
        land = loc.get('landing_page_url') or ''
        if loc.get('version') in ('acceptedVersion', 'submittedVersion') and land and s2k.ok_pdf(land) and cs.usable(land):
            rows.append(dict(work_id=work_id, url=land, landing_url=land, version=loc.get('version'), license=loc.get('license'),
                             source='oa_locations', detail=(loc.get('source') or {}).get('display_name')))
    return rows


def discover(school, papers, ctx):
    import json
    from collections import defaultdict
    import bulk_oa as B
    import ftp_common as F
    import lab_channels as L
    from channels import arxiv_bulk as AB
    stores, tix = B.oa_stores(), B.title_index()
    bodies = F.oa_bodies(school, [p.r['oa'] for p in papers])
    rows, arx, pmc = defaultdict(list), {}, {}
    for p in papers:
        own = bodies.get(p.r['oa'])
        recs = ([('own', own)] if own else []) + siblings(p, stores, tix, own)
        ctx.n['oa_locations_sibling_records'] += sum(1 for h, _ in recs if h != 'own')
        for how, b in recs:
            lb = dict(b, locations=list(b.get('locations') or []) + extra_locations(b))
            rs, pm = F.oa_location_rows(p.work_id, lb)
            rs += manuscript_rows(p.work_id, lb)
            for r in rs:
                r['source'] = 'oa_locations'
                r['detail'] = json.dumps(dict(record=b.get('id'), found_by=how, host=r.get('detail')))
            rows[p.work_id] += rs
            if pm and not any('pmc-oa-opendata' in u for u in p.known):
                pmc.setdefault(p.work_id, set()).update(pm)
            a = F.arxiv_of(dict(doi=None), lb) if how == 'own' else None   # arXiv ids from the paper's own record only
            if a and not L.has_arxiv(p.known):
                known_rec = AB.index()['by_id'].get(a)
                if known_rec is None or B.title_compatible(p.r.get('title') or '', known_rec[1] or ''):
                    arx.setdefault(p.work_id, a)
                else:
                    ctx.n['oa_locations_arxiv_title_incompatible'] += 1
    brows, ctx.n['oa_locations_arxiv_not_in_bulk'] = F.bulk_rows(arx, 'oa_locations_arxiv_bulk') if arx else ([], 0)
    memo, sess = {}, ctx.session()
    prows = [x for w, ids in pmc.items() for x in F.pmc_rows(w, ids, memo, sess)]
    for x in brows + prows:
        rows[x['work_id']].append(x)
    for p in papers:
        got = list({r['url']: r for r in rows[p.work_id]}.values())
        yield ctx.result(p, 'found' if got else 'none', got, query=f"OpenAlex snapshot, all locations of {p.r.get('oa')} and its same-DOI / same-title records")
