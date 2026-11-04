"""Channel oai_repo (2026-11-04, owner): the lab papers still without a copy, matched to the records of their school's institutional
repository harvest (fulltext-push/oai_repo.py -> raw/oai_repo/<school>.sqlite; the school's charter [oai_repo] says which repository).

Match, in this order (a paper takes the first rule that fires, and the record must not be deleted):
  doi     the paper's DOI equals a DOI the record names as its own (dc:identifier / datacite identifiers; never dc:relation)
  link    a handle or landing URL of the record is already among the paper's known URLs (a repository page another channel listed)
  title   the normalized title is equal (>= 25 characters), the years are within 2, and the authors agree under the identity rule:
          byline family names (fulltext-push/identity_rule.fam) against the record's creators: at least half of the smaller side
          shared (at least one), and one of the paper's PIs among the record's creators. No title-only match is ever written.
Candidates: the record's open file URLs (oai_openaire files that are not 'metadata only' or restricted; Figshare files) as
`acceptedVersion`-agnostic rows, else its landing / handle page (the collector extracts citation_pdf_url from a landing page, as it does for
MIT handles). Rows go through the catalog lock after a catalog backup (catalog_lock.backup_catalog); known URLs are not written again.
Figshare (KiltHub, set portal_231 of Figshare's OAI): the OAI record has creators and the DOI but no files, so a record that matched is
fetched once from the public API (/v2/articles/<id>, 3 s apart) for its open PDF files (never embargoed or confidential ones).
"""
import json
import re
from collections import Counter

NAME = 'oai_repo'
MIN_TITLE = 25
RESTRICTED = ('c_16ec', 'c_f1cf', 'c_14cb')  # COAR access-right codes: restricted, embargoed, metadata only


def _cfg(school):
    import oai_repo as O
    try:
        return O.cfg(school)
    except Exception:  # noqa: BLE001
        return {}


def APPLIES(school, paper):
    import oai_repo as O
    c = _cfg(school)
    return c.get('verdict') == 'harvest' and O.db_path(school).exists()


def families(names):
    import identity_rule as IR
    return {f for f in (IR.fam(n) for n in names or []) if f}


def authors_agree(paper_row, creators):
    """The identity rule's author side: shared families >= half of the smaller side (>= 1) and a PI of the paper among the creators."""
    byl = families(paper_row.get('byline'))
    rec = families(creators)
    if not byl or not rec:
        return False
    shared = byl & rec
    if len(shared) < max(1, (min(len(byl), len(rec)) + 1) // 2):
        return False
    pis = families(paper_row.get('pis'))
    return bool(pis & rec) if pis else True


def handle_key(u):
    import oai_repo as O
    m = O.HANDLE_RX.search(u or '')
    return m.group(1) if m else None


def norm_link(u):
    return re.sub(r'^https?://(www\.)?', '', (u or '').strip().lower()).rstrip('/')


def load_index(school):
    """-> (by_doi, by_title, by_link, rows by oai_id) over the live records."""
    import oai_repo as O
    c = O.connect(school)
    by_doi, by_t, by_link, rows = {}, {}, {}, {}
    for oid, ds, title, creators, year, dois, links, files, rights, rtype, sets in c.execute(
            'SELECT oai_id, datestamp, title, creators, year, dois, links, files, rights, rtype, sets FROM records WHERE deleted=0'):
        from ftp_common import nt
        r = dict(oai_id=oid, datestamp=ds, title=title, creators=json.loads(creators), year=year, dois=json.loads(dois), links=json.loads(links),
                 files=json.loads(files), rights=json.loads(rights), rtype=rtype, sets=json.loads(sets))
        rows[oid] = r
        for d in r['dois']:
            by_doi.setdefault(d, []).append(oid)
        k = nt(title)
        if len(k) >= MIN_TITLE:
            by_t.setdefault(k, []).append(oid)
        for u in r['links']:
            by_link.setdefault(norm_link(u), []).append(oid)
            h = handle_key(u)
            if h:
                by_link.setdefault('handle:' + h, []).append(oid)
    return by_doi, by_t, by_link, rows


def match_paper(paper, idx):
    """-> (record, how) or (None, None)."""
    from ftp_common import ndoi, nt
    by_doi, by_t, by_link, rows = idx
    r = paper.r
    d = ndoi(r.get('doi'))
    if d and d in by_doi:
        return rows[by_doi[d][0]], 'doi'
    for u in paper.known:
        for key in (norm_link(u), 'handle:' + (handle_key(u) or '')):
            if key in by_link:
                return rows[by_link[key][0]], 'link'
    k = nt(r.get('title'))
    if len(k) >= MIN_TITLE and k in by_t:
        for oid in by_t[k]:
            rec = rows[oid]
            if r.get('year') and rec['year'] and abs(int(r['year']) - rec['year']) > 2:
                continue
            if rec['creators'] and not authors_agree(r, rec['creators']):
                continue
            if not rec['creators']:
                rec = dict(rec, needs_authors=True)
            return rec, 'title'
    return None, None


def is_closed(rec):
    """A record whose rights say restricted / embargoed / metadata only / closed (EPFL lists files of 'restricted access' records)."""
    t = ' '.join(rec.get('rights') or []).lower()
    return any(w in t for w in ('restricted', 'embargo', 'metadata only', 'closedaccess', 'closed access'))


def open_files(rec):
    out = []
    if is_closed(rec):
        return out
    for f in rec.get('files') or []:
        if any(code in (f.get('access') or '') for code in RESTRICTED):
            continue
        u = f.get('url') or ''
        if not u.startswith('http'):
            continue
        if f.get('kind') in (None, 'fulltext') and (f.get('mime') in (None, 'application/pdf') or u.lower().endswith('.pdf')):
            out.append(u)
    return out


def figshare_files(school, ctx, rec, pace=3.0):
    """KiltHub: the open PDF files of one article from the public API (/v2/articles/<id>, one GET, 3 s apart), -> (urls, license)."""
    m = re.search(r'article/(\d+)', rec['oai_id'])
    if not m:
        return [], None
    body = ctx.polite_get(_cfg(school)['enrich_base'].rstrip('/') + f'/articles/{m.group(1)}', pace)
    try:
        j = json.loads(body) if body else None
    except ValueError:
        j = None
    if not j or j.get('is_embargoed') or j.get('is_confidential') or j.get('is_metadata_record'):
        return [], None
    urls = [f['download_url'] for f in j.get('files') or [] if f.get('download_url') and str(f.get('name') or '').lower().endswith('.pdf')]
    return urls, (j.get('license') or {}).get('name')


def candidate_rows(school, work_id, rec, how, paper_row, license=None):
    if is_closed(rec):
        return []
    files = open_files(rec)
    landing = next((u for u in rec['links'] if u.startswith('http') and 'doi.org' not in u), None) or (rec['links'][0] if rec['links'] else None)
    urls = files or ([landing] if landing else [])
    detail = json.dumps(dict(match=how, oai_id=rec['oai_id'], title=paper_row.get('title'), record_title=rec['title'], sets=rec.get('sets', [])[:4]))
    return [dict(work_id=work_id, url=u, landing_url=landing, version=None, license=license, source=f'oai_repo_{school}', detail=detail)
            for u in dict.fromkeys(urls)]


def discover(school, papers, ctx):
    idx = load_index(school)
    ctx.n['oai_records'] = len(idx[3])
    fig = _cfg(school).get('enrich') == 'figshare'
    found = {}
    for p in papers:
        rec, how = match_paper(p, idx)
        if not rec:
            continue
        lic = None
        if rec.get('needs_authors'):
            ctx.n['oai_title_no_authors'] += 1
            continue
        if fig:  # the files of a matched record come from the public API (the OAI record has none)
            urls, lic = figshare_files(school, ctx, rec)
            rec = dict(rec, files=[dict(url=u, mime='application/pdf', kind='fulltext') for u in urls])
        rows = candidate_rows(school, p.work_id, rec, how, p.r, lic)
        if rows:
            found[p.key] = (p, rows, how)
            ctx.n[f'oai_matched_{how}'] += 1
    new = [dict(x) for p, rows, _ in found.values() for x in rows if x['url'] not in ctx.known[p.work_id]]
    ctx.n['oai_new_candidate_rows'] = len(new)
    if new and not ctx.dry:
        import ftp_common as F
        import catalog_lock
        catalog_lock.backup_catalog(F.FT / school, 'oai_repo')
        ctx.n['candidates_added'] += ctx.write(new, NAME)
        for r in new:
            ctx.known[r['work_id']].add(r['url'])
    written = {(r['work_id'], r['url']) for r in new} if not ctx.dry else set()
    for p in papers:
        if p.key in found:
            _, rows, how = found[p.key]
            urls = [dict(x, written_by_step=True) if (x['work_id'], x['url']) in written else x for x in rows]
            yield ctx.result(p, 'found', urls, query=f'oai_repo {school}: {how}', detail=dict(how=how))
        else:
            yield ctx.result(p, 'none', [], query=f'oai_repo {school}: doi/link/title+authors')
    ctx.n['oai_by_how'] = dict(Counter(h for _, _, h in found.values()))
