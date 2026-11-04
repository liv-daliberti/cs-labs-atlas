"""Channel s2_bulk (2026-11-04, owner: bulk open-access sources, 2): the Semantic Scholar bulk release (Datasets API, ODC-BY), filtered on
Slurm to our lab papers by fulltext-push/s2_bulk.py (`papers` for the corpusid by DOI, then ArXiv id, then normalized title + first author;
`s2orc` for the PDF URLs S2 parsed and Unpaywall's oaInfo). This channel only reads that local table
(FT_RAW/bulk-oa/s2/<release>/*.jsonl.gz); it asks nothing from the network except the PMC open-data listing for a PMC id.

Candidates (each only a fetch candidate: the collectors read robots.txt, pace themselves and check the file's title and first author):
  pdfUrls / oaInfo.url   on hosts the collectors may use (s2_key_lookup.ok_pdf, core_search.usable)
  ArXiv id               -> arXiv's bulk copy on GCS, when no arXiv link is known for the work
  PubMedCentral id       -> the PMC open-data files on S3
  ACL id                 -> https://aclanthology.org/<id>.pdf
Attribution (ODC-BY): Kinney et al. 2023, "The Semantic Scholar Open Data Platform"; Lo et al. 2020, "S2ORC".
"""
import json
from collections import defaultdict

NAME = 's2_bulk'
_T = {}


def table():
    if not _T:
        import s2_bulk as S
        recs, rel = S.read()
        by = defaultdict(list)
        for r in recs.values():
            for sch, key, _w in r['targets']:
                by[(sch, key)].append(r)
        _T.update(by=by, release=rel)
    return _T


def APPLIES(school, paper):
    return (school, paper.key) in table()['by']


def discover(school, papers, ctx):
    import ftp_common as F
    import lab_channels as L
    import s2_key_lookup as s2k
    import core_search as cs
    t = table()
    ctx.n['s2_bulk_release'] = t['release']
    arx, pmc, rows = {}, {}, defaultdict(list)
    for p in papers:
        for r in t['by'][(school, p.key)]:
            det = json.dumps(dict(matched_by=r['how'], corpusid=r['corpusid'], s2_release=t['release']))
            urls = list(r.get('pdfurls') or [])
            oa = r.get('oainfo') or {}
            if oa.get('openaccessurl') or oa.get('url'):
                urls.append(oa.get('openaccessurl') or oa.get('url'))
            for u in dict.fromkeys(urls):
                if u and s2k.ok_pdf(u) and cs.usable(u):
                    rows[p.work_id].append(dict(work_id=p.work_id, url=u, landing_url=None, version=None, license=oa.get('license'), source='s2_bulk', detail=det))
            if r.get('arxiv') and not L.has_arxiv(p.known):
                arx.setdefault(p.work_id, r['arxiv'])
            if r.get('pmc') and not any('pmc-oa-opendata' in u for u in p.known):
                pmc.setdefault(p.work_id, set()).add(str(r['pmc']).replace('PMC', ''))
            if r.get('acl'):
                rows[p.work_id].append(dict(work_id=p.work_id, url=f"https://aclanthology.org/{r['acl']}.pdf", landing_url=None, version=None, source='s2_bulk', detail=det))
    brows, ctx.n['s2_bulk_arxiv_not_in_bulk'] = F.bulk_rows(arx, 's2_bulk_arxiv') if arx else ([], 0)
    memo, sess = {}, ctx.session()
    prows = [x for w, ids in pmc.items() for x in F.pmc_rows(w, ids, memo, sess)]
    for x in brows + prows:
        rows[x['work_id']].append(x)
    for p in papers:
        got = list({x['url']: x for x in rows[p.work_id]}.values())
        yield ctx.result(p, 'found' if got else 'none', got, query=f"Semantic Scholar bulk release {t['release']} (local table), corpusids {[r['corpusid'] for r in t['by'][(school, p.key)]][:3]}")
