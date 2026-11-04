"""Channel arxiv_bulk (2026-11-04, owner: bulk open-access sources, 4): arXiv's metadata in bulk matched LOCALLY to the lab papers, the PDFs
from arXiv's public cloud mirror (gs://arxiv-dataset, storage.googleapis.com), never arxiv.org.

Metadata source: the local arXiv OAI-PMH harvest of 2026-10-18 (cs, stat, eess, q-bio, quant-ph, math; every record, with its DOI field),
which vendor/cmu_tools/arxiv_oai.py made from arXiv's official OAI-PMH endpoint. It replaces the Kaggle snapshot: the Kaggle copy needs a login,
and its mirror in the bucket (metadata-v5/, 4.5 GB) stops in 2020, while the harvest is current. Other physics categories are not in it.
Terms (arXiv bulk access page, read 2026-11-04): metadata is openly available, the PDFs of most articles carry the default arXiv licence
(arXiv may distribute them; builders of indexes must link back to arXiv: every candidate carries its https://arxiv.org/abs/<id> page as landing URL).

Matching order (bulk_oa-style, local): (1) the record's DOI field equals the paper's DOI (the author-supplied journal DOI of the preprint) and the titles are compatible (bulk_oa.title_compatible);
(2) an arXiv id the paper already names (10.48550 DOI); (3) the normalized title equal and the same author set (arxiv_loose.same_authors: every
byline family of the first 8, long bylines 6 of 8 plus every PI) with the first version from 3 years before to 1 year after the paper's year,
and no second record that ties. The collector's page-1 identity rule (fulltext-push/identity_rule.py: title and first author, or the arXiv stamp
against the DOI) still applies to the downloaded file.
"""
import gzip
import json
import re
from collections import defaultdict

NAME = 'arxiv_bulk'
_IX = {}


def index():
    if not _IX:
        import ftp_common  # noqa: F401  (puts vendor/cmu_tools on sys.path)
        import arxiv_oai as ao
        import ftp_common as F
        by_doi, by_t, by_id = {}, defaultdict(list), {}
        n = 0
        for f in sorted(ao.RAW.glob('*.jsonl.gz')):
            for line in gzip.decompress(f.read_bytes()).decode().splitlines():
                if not line:
                    continue
                r = json.loads(line)
                n += 1
                rec = (re.sub(r'v\d+$', '', r['id']), r['title'], tuple(r.get('families') or ()), int((r.get('created') or '0')[:4] or 0))
                by_id[rec[0]] = rec
                for d in (r.get('doi') or '').lower().split():
                    by_doi.setdefault(F.ndoi(d), rec)
                k = F.nt(r['title'])
                if len(k) >= 20:
                    by_t[k].append(rec)
        _IX.update(by_doi=by_doi, by_t=by_t, by_id=by_id, n=n)
    return _IX


def APPLIES(school, paper):
    import lab_channels as L
    return not L.has_arxiv(paper.known)


def match(r, ix):
    """-> (how, (arxiv id, title)) or (None, detail)."""
    import ftp_common as F
    from channels.arxiv_loose import same_authors, _fam
    d = F.ndoi(r.get('doi'))
    if d and d in ix['by_doi']:
        rec = ix['by_doi'][d]
        import bulk_oa as B
        if B.title_compatible(r.get('title') or '', rec[1] or ''):  # an author may give two parts of a series one DOI (hand check 2026-11-04)
            return 'doi', rec
        return None, dict(doi_title_incompatible=rec[0])
    a = F.arxiv_of(r, None)
    if a:
        return 'arxiv_id', (a, None, (), 0)
    k = F.nt(r.get('title'))
    y0 = r.get('year')
    hits = []
    for rec in ix['by_t'].get(k, []):
        aid, title, fams, y = rec
        if y0 and y and not -1 <= int(y0) - y <= 3:
            continue
        if not same_authors(r.get('byline') or [], r.get('pis') or [], fams):
            continue
        by = [_fam(x) for x in r.get('byline') or [] if _fam(x)]
        if len(by) <= 2 and (not fams or _fam(fams[0]) != by[0]):
            continue
        hits.append(rec)
    if len({h[0] for h in hits}) == 1:
        return 'title_author', hits[0]
    return None, dict(ambiguous=len(hits) > 1)


def discover(school, papers, ctx):
    import ftp_common as F
    ix = index()
    ctx.n['arxiv_bulk_index_records'] = ix['n']
    want, det = {}, {}
    for p in papers:
        how, rec = match(p.r, ix)
        if how:
            want[p.work_id] = rec[0]
            det[p.work_id] = dict(matched_by=how, arxiv=rec[0], arxiv_title=rec[1])
            ctx.n['arxiv_bulk_by_' + how] += 1
    rows, ctx.n['arxiv_bulk_not_in_bulk'] = F.bulk_rows(want, 'arxiv_bulk') if want else ([], 0)
    by_w = {x['work_id']: [x] for x in rows}
    for x in rows:
        x['detail'] = json.dumps(det[x['work_id']])
    for p in papers:
        yield ctx.result(p, 'found' if by_w.get(p.work_id) else 'none', by_w.get(p.work_id, []),
                         query=f"arXiv OAI harvest, DOI / arXiv id / title + authors: {p.r.get('doi') or p.r.get('title')}"[:300])
