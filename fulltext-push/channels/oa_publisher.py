"""Channel oa_publisher (2026-10-30): the publisher's own copy of a paper OpenAlex marks open at the publisher (oa_status
gold, hybrid, bronze or diamond) when no candidate reaches it yet. A hand check of 20 ledger entries found such papers
recorded as 'no copy' with no download attempt at all: the other channels drop publisher hosts. The collector asks the
publisher for it (its redirect rule, robots.txt with the AI-crawler
groups, pacing, the landing page's citation_pdf_url, the title check), so the paper either gains the open copy or a
recorded, precise reason (robots, challenge, paywall). The URL is the publisher's open location in the OpenAlex record
(its PDF, else its landing page), else the DOI. Not for publishers that refuse automated clients or serve a bot
challenge (ACM 10.1145, IEEE 10.1109, SSRN 10.2139): asking them again would only meet the challenge.
Source of the access status: the paper's OpenAlex check in the unavailability ledger (hierarchy/<school>/unavailable.jsonl.gz).
"""
import gzip
import json

NAME = 'oa_publisher'
OPEN = {'gold', 'hybrid', 'bronze', 'diamond'}
REFUSE = ('10.1145/', '10.1109/', '10.2139/', '10.48550/')
_CACHE = {}


def ledger(school):
    if school not in _CACHE:
        import ftp_common as F
        p = F.P.data('unavailable.jsonl.gz', school)
        out = {}
        if p.exists():
            with gzip.open(p, 'rt') as f:
                for line in f:
                    r = json.loads(line)
                    if r.get('oa_status') in OPEN and r.get('doi'):
                        out[r['key']] = r
        _CACHE[school] = out
    return _CACHE[school]


def APPLIES(school, paper):
    import ftp_common as F
    r = ledger(school).get(paper.key)
    if not r:
        return False
    d = F.ndoi(r['doi'])
    return bool(d) and not d.startswith(REFUSE) and not any(F.ndoi(u) == d for u in paper.known if 'doi.org/' in u)


def discover(school, papers, ctx):
    import ftp_common as F
    rec = ledger(school)
    for p in papers:
        r = rec[p.key]
        d = F.ndoi(r['doi'])
        oa = next((c for c in r.get('checks') or [] if c.get('source') == 'openalex'), {})
        locs = [l for l in ((oa.get('detail') or {}) if isinstance(oa.get('detail'), dict) else {}).get('locations') or []
                if l.get('is_oa') and l.get('type') in ('journal', 'conference', 'book series', 'ebook platform')]
        # the publisher's open location: its PDF, else its landing page (the collector follows citation_pdf_url); the
        # landing page is the candidate's landing_url, so the collector may follow the DOI's redirect to that host
        loc = next((l for l in locs if l.get('pdf')), locs[0] if locs else {})
        url = loc.get('pdf') or loc.get('landing') or f'https://doi.org/{d}'
        if url.startswith('http://'):
            url = 'https://' + url[7:]
        yield ctx.result(p, 'found', [dict(work_id=p.work_id, url=url, landing_url=loc.get('landing') or f'https://doi.org/{d}', version='publishedVersion',
                                           source='oa_publisher', detail=json.dumps(dict(oa_status=r['oa_status'], publisher=r.get('publisher'), doi=d)))],
                         query=f"OpenAlex oa_status {r['oa_status']}: the publisher's open copy of {d}")
