"""Check that every {url, sha256, quote} in the staged (or written) CMU CS-related outputs is an exact substring of the
text of a stored capture in hierarchy/cmu/cs-related-captures.sqlite with that url/capture_url and that sha256.
Evidence citing other stores (census rows: source census/cmu-faculty.json) is checked against its declared source only by
presence. usage: verify.py <additions.json> <periods.json> <home_departments.json> <review.json>"""
import json, sqlite3, sys
from pathlib import Path
HERE = Path(__file__).resolve().parents[3]
con = sqlite3.connect(f"file:{HERE / 'hierarchy/cmu/cs-related-captures.sqlite'}?mode=ro", uri=True)
idx = {}
for u, cu, sha, t in con.execute('select url, capture_url, sha256, text from captures where status=200 and error is null and text is not null'):
    for k in (u, cu):
        if k:
            idx.setdefault((k, sha), t)
bad, n = [], 0


def chk(where, e, field='quote'):
    global n
    if not e or not e.get('url') or e.get('source'):
        return
    n += 1
    t = idx.get((e['url'], e.get('sha256')))
    if t is None:
        bad.append((where, 'no stored capture', e['url'][:100])); return
    if e.get(field) and e[field] not in t:
        bad.append((where, 'quote not in text', e[field][:80]))


A, P, H, R = (json.load(open(a)) for a in sys.argv[1:5])
for a in A:
    for s in a['sources']:
        chk(a['name'] + ':source', s)
    chk(a['name'] + ':pi_basis', a['pi_basis']); chk(a['name'] + ':pi_basis', a['pi_basis'], 'quote_student')
for nm, o in P.items():
    for p in o['periods']:
        for e in p['evidence']:
            chk(nm + ':period', e)
for h in H:
    chk(h['name'] + ':home', h['evidence'])
for r in R:
    for e in r.get('evidence') or []:
        chk(f"{r['index']}:{r['name']}:review", e)
print(json.dumps(dict(checked=n, bad=len(bad))))
for b in bad[:30]:
    print(b)
