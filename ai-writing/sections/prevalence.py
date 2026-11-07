"""Prevalence of appendices in pilot draws, post-stratified to the stored copies (school x kind x year bucket).
usage: prevalence.py DB SAMPLE:RES [SAMPLE:RES ...]"""
import gzip, json, sqlite3, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'tools'))
import atlas_paths as P  # noqa: E402
from pilot import bucket  # noqa: E402
meta = {}
for l in gzip.open(P.AI_WRITING / 'papers.jsonl.gz', 'rt'):
    p = json.loads(l)
    try:
        y = int(p['year'])
    except (TypeError, ValueError):
        continue
    meta[p['key']] = (y, p.get('type'))
db = sqlite3.connect(sys.argv[1]); pop = Counter()
for k, school, kind in db.execute('select key, school, kind from texts'):
    if k in meta and meta[k][0] <= 2025:
        pop[(school, kind, bucket(meta[k][0]))] += 1
rows, seen = [], set()
for arg in sys.argv[2:]:
    s, r = arg.split(':'); S = json.load(open(s)); R = {}
    for l in open(Path(r) / 'res.jsonl'):
        x = json.loads(l); R[x['i']] = x
    for i, w in enumerate(S):
        if w['key'] in seen or 'flags' not in R[i]:
            continue
        seen.add(w['key']); f = R[i]['flags']
        rows.append(dict(school=w['school'], kind=w['kind'], year=w['year'], b=bucket(w['year']), type=w.get('type'), app=f['appendix_found'], rule=f['appendix_rule'],
                         pos=f['appendix_position'], mw=f['main_words'], aw=f['appendix_words'], trunc=f['truncated'], pages=f.get('pages')))
cnt = Counter((r['school'], r['kind'], r['b']) for r in rows)
for r in rows:
    r['w'] = pop[(r['school'], r['kind'], r['b'])] / cnt[(r['school'], r['kind'], r['b'])]
tot = sum(r['w'] for r in rows)
def rate(g, f=lambda r: r['app']):
    w = sum(r['w'] for r in g); return sum(r['w'] for r in g if f(r)) / w if w else float('nan')
print('papers', len(rows), 'pop', sum(pop.values()))
print('appendix (any rule) weighted', round(rate(rows), 3), '| unweighted', round(sum(r['app'] for r in rows) / len(rows), 3))
print('  appendix proper (rule appendix/lettered/xml_back)', round(rate(rows, lambda r: r['app'] and r['rule'] != 'supplementary'), 3), '| supplementary-only', round(rate(rows, lambda r: r['app'] and r['rule'] == 'supplementary'), 3))
for key in ('b', 'school', 'kind', 'type'):
    print(key, {k: (round(rate([r for r in rows if r[key] == k]), 3), sum(r[key] == k for r in rows)) for k in sorted({str(r[key]) for r in rows})} if key != 'type' else {k: (round(rate([r for r in rows if str(r[key]) == k]), 3), sum(str(r[key]) == k for r in rows)) for k in sorted({str(r[key]) for r in rows})})
print('position', Counter(r['pos'] for r in rows if r['app']))
g = [r for r in rows if r['app']]
import statistics as st
print('appendix share of words (flagged): median', round(st.median(r['aw'] / (r['aw'] + r['mw']) for r in g), 3), 'mean', round(st.mean(r['aw'] / (r['aw'] + r['mw']) for r in g), 3))
print('  weighted share of all words in appendix', round(sum(r['w'] * r['aw'] for r in rows) / sum(r['w'] * (r['aw'] + r['mw']) for r in rows), 3))
print('truncated', sum(r['trunc'] for r in rows), 'pages>=60', sum((r['pages'] or 0) >= 60 for r in rows), 'pages>=400', sum((r['pages'] or 0) >= 400 for r in rows))
print('pages of papers with appendix after refs: 60-page cap would have cut', sum(1 for r in g if (r['pages'] or 0) > 60))
