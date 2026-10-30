"""Adviser-name queries to DSpace@MIT for listed faculty whose PhD advising the stored captures do not show, in the
format the leftover 2026-10-22 session used (six names per request, theses issued 2016-2026, outside the EECS orgunit
already harvested by year). One request per 100 s (mpcap GAPS, shared lock with sister processes); a 429 is stored and
retried once after its Retry-After. Every page of a result is fetched.
usage: dspace_queries.py
"""
import json, sys, time
from pathlib import Path
from urllib.parse import quote_plus
sys.path.insert(0, str(Path(__file__).parent))
import mpcap  # noqa: E402

BATCHES = [
    [('Entekhabi', ['Dara']), ('Hogan', ['Neville']), ('Vielma', ['Juan']), ('Turitsyn', ['Konstantin']), ('Barton', ['Paul']), ('Willcox', ['Karen'])],
    [('Peraire', ['Jaime']), ('Wang', ['Qiqi']), ('Fudenberg', ['Drew']), ('Stirling', ['Leia']), ('Makris', ['Nicholas']), ('Rahwan', ['Iyad'])],
    [('Simester', ['Duncan']), ('Zheng', ['Yanchong']), ('Catalini', ['Christian']), ('Farboodi', ['Maryam']), ('Zhang', ['Juanjuan']), ('Nagakura', ['Takehiko'])],
    [('Zaman', ['Tauhid']), ('Jones', ['Graham']), ('Balakrishnan', ['Hamsa']), ('Jacquillat', ['Alexandre']), ('Perakis', ['Georgia']), ('Hidalgo', ['Cesar', 'César'])],
    [('Urschel', ['John']), ('Pataranutaporn', ['Pat', 'Pattarawat']), ('Zuckerman', ['Ethan']), ('Casalegno', ['Federico'])],
]


def url(batch, page):
    q = 'dc.contributor.advisor:(' + ' OR '.join(f"({s} AND ({' OR '.join(g)}))" for s, g in batch) + ') AND NOT dc.relation.orgunit:"Electrical Engineering and Computer Science"'
    return ('https://dspace.mit.edu/server/api/discover/search/objects?query=' + quote_plus(q) +
            f'&dsoType=ITEM&size=100&page={page}&f.dateIssued=' + quote_plus('[2016 TO 2026],equals') + '&sort=' + quote_plus('dc.date.accessioned,ASC'))


def get(u):
    for attempt in range(3):
        r = mpcap.fetch(u)
        if r.get('status') == 200 and not r.get('error'):
            return r
        ra = 900
        if r.get('error', '') and 'retry-after' in r['error']:
            try:
                ra = int(r['error'].split()[-1])
            except ValueError:
                pass
        print('retry after', ra, r.get('status'), r.get('error'), flush=True)
        time.sleep(min(ra, 900) + 5)
    return None


for b in BATCHES:
    page, pages = 0, 1
    while page < pages:
        r = get(url(b, page))
        if not r:
            print('FAILED', [s for s, _ in b], page, flush=True); break
        d = json.loads(r['text'])['_embedded']['searchResult']['page']
        pages = d['totalPages']
        print([s for s, _ in b], 'page', page, d, flush=True)
        page += 1
