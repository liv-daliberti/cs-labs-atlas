"""Evidence per triage row: DataSpace records naming the person as adviser (by role) or as author, the stored department
listing entries naming them (any department, incl. CS), and the author-index counts.
-> <out>/princeton-evidence.json
usage: princeton_evidence.py <csrel_dir> <out_dir>
"""
import collections, json, re, sqlite3, sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import princeton_lib as L  # noqa: E402
import helpers  # noqa: E402
from helpers import Name, toks  # noqa: E402

csrel, out = Path(sys.argv[1]), Path(sys.argv[2])
T = json.load(open(csrel / 'princeton-triage.json'))
TI = json.load(open(out / 'princeton-thesis-index.json'))
con = sqlite3.connect(f'file:{L.LST}?mode=ro', uri=True)
caps = con.execute('select department, page_url, capture_url, wayback_timestamp from captures where http_status=200 order by wayback_timestamp').fetchall()
texts = {cu: L.listing_text(cu) for _, _, cu, _ in caps}
res = {}
for r in T:
    names = [r['name']] + r['aliases']
    nm = Name(names)
    t = toks(r['name'])
    forms = []
    for n in names:
        tt = n.replace(',', ' ').split()
        if ',' in n:
            fam, giv = n.split(',', 1); tt = giv.split() + fam.split()
        if len(tt) >= 2:
            forms.append((tt[0], tt[-1]))
    adv = [a for a in TI['advisers'] if nm.match(a['adviser']) and len(toks(a['adviser'])) <= 4]
    auth = [a for a in TI['authors'] if nm.match(a['student']) or nm.match(a['author_raw'])]
    lst = []
    for d, pu, cu, ts in caps:
        q = L.find_listing_quote(texts[cu], forms) if forms else None
        if q:
            lst.append(dict(dept=d, page_url=pu, capture_url=cu, ts=ts, **q))
    res[r['name']] = dict(adv_roles=dict(collections.Counter(a['role'] for a in adv)), adv_examples=[a for a in adv if a['quote']][:3] + [a for a in adv if a['quote'] and a['role'] == 'phd'][:2],
                          authored=[a for a in auth][:3],
                          listings=lst)
json.dump(res, open(out / 'princeton-evidence.json', 'w'), ensure_ascii=False, indent=0)
for k, v in res.items():
    ls = collections.OrderedDict()
    for x in v['listings']:
        ls.setdefault((x['dept'][:12], x['quote'][:70], x['section']), []).append(x['ts'][:4])
    print(k, '| adv', v['adv_roles'], '| auth', [(a['role'], a['year'], a['dept'][:30]) for a in v['authored']], '| lst', [(a, b, c, min(y), max(y)) for (a, b, c), y in list(ls.items())[:3]])
