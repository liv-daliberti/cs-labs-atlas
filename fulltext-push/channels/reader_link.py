"""Channel reader_link (2026-11-03, owner: "make sure we are getting every paper we can"): the open-copy link the release's reader
confirmed for a link-only paper (reader/<school>.jsonl.gz, decision 'link', no stored copy, link_basis openalex_location /
arxiv_id_doi / landing_page_metadata), as a candidate of the paper's catalog work when the work does not hold it yet.

The download loops only ask the collector for the candidates a catalog already holds; the reader's confirmed URL reaches the
catalog only through a channel, and 120 of the 2,000 queued link-only papers had a confirmed URL that was no candidate (an
http/https or handle-suffix variant of one that was, a repository page another school's channel never listed). The row goes
through the collector like every candidate: robots.txt (with the AI-crawler groups), per-host pacing, the title check. Hosts the
other channels never use (s2_key_lookup.BAD_HOSTS: publishers that refuse automated clients) are skipped as there.
  arXiv   an arxiv.org/abs/<id> link -> arXiv's bulk copy on GCS (ftp_common.bulk_rows), never arxiv.org
  a URL   -> itself
The queued papers come from the priority file (priority_file.py: found_awaiting_download / pending_retry); without one the channel
applies to nothing.
"""
import gzip
import json
import re

NAME = 'reader_link'
_CACHE = {}
ARXIV = re.compile(r'arxiv\.org/(?:abs|pdf)/([^\s?#]+?)(?:v\d+)?(?:\.pdf)?$', re.I)


def reader_links(school, release=None):
    """{catalog work id: reader row} of the school's queued link-only papers in the release (priority_file's rule)."""
    import priority_file as PF
    rel = PF.release_dir(release)
    key = (school, str(rel))
    if key not in _CACHE:
        queued = {e[0] for e in PF.queued_entries(school, rel)}
        out = {}
        with gzip.open(rel / 'reader' / f'{school}.jsonl.gz', 'rt') as f:
            for line in f:
                r = json.loads(line)
                if r.get('catalog_work') in queued and (r.get('source_url') or '').startswith('http'):
                    out[r['catalog_work']] = r
        _CACHE[key] = out
    return _CACHE[key]


def APPLIES(school, paper):
    return paper.work_id in reader_links(school)


def discover(school, papers, ctx):
    import ftp_common as F
    import s2_key_lookup as s2k
    import core_search as cs
    arx, rows = {}, {}
    for p in papers:
        r = reader_links(school)[p.work_id]
        u = r['source_url'].strip()
        m = ARXIV.search(u)
        if m:
            arx[p.work_id] = m.group(1)
        elif s2k.ok_pdf(u) and cs.usable(u):
            rows[p.work_id] = dict(work_id=p.work_id, url=u, landing_url=None, version=r.get('version'), source='reader_link',
                                   detail=json.dumps(dict(link_basis=r.get('link_basis'), reader_key=r.get('key'))))
    brows, ctx.n['reader_link_arxiv_not_in_bulk'] = F.bulk_rows(arx, 'reader_link_arxiv_bulk') if arx else ([], 0)
    by_w = {w: [x] for w, x in rows.items()}
    for x in brows:
        by_w.setdefault(x['work_id'], []).append(x)
    for p in papers:
        yield ctx.result(p, 'found' if by_w.get(p.work_id) else 'none', by_w.get(p.work_id, []),
                         query='confirmed reader link: ' + reader_links(school)[p.work_id]['source_url'][:150])
