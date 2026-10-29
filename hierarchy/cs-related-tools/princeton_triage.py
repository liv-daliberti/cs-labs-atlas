"""Triage table for the Princeton CS-related review: the universe (candidates, thesis advisers), the department-list scan
and extra names, each with DataSpace PhD advising 2016-2025 (any department), stored listing entries (dept, years, titles)
and the author-index CS-venue count on the given OpenAlex ids (book chapters of one SIAM/Springer book count once).
-> <out>/princeton-triage.json
usage: princeton_triage.py <out_dir>
"""
import collections, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'hierarchy/cs-related-tools'))
import helpers  # noqa: E402
from helpers import Name, toks  # noqa: E402

out = Path(sys.argv[1])
U = json.load(open(out / 'princeton-universe.json'))
S = json.load(open(out / 'princeton-scan.json'))
PA = json.load(open(out / 'princeton-phd-advising.json'))
E = json.load(open(out / 'princeton-listing-entries.json'))
A = helpers.index('princeton')
EXTRA = [('Daniel I. Rubenstein', ['Daniel Rubenstein'], 'author-index-scan')]


def distinct_cs(ids):
    seen = set(); n = 0
    for w in helpers.cs_works('princeton', ids):
        k = (w['venue'], w['year']) if re.search(r'eBooks', w['venue']) or w['title'].startswith('Chapter') else w['oa']
        if k not in seen:
            seen.add(k); n += 1
    return n


rows = collections.OrderedDict()
for r in U:
    rows[r['name']] = dict(name=r['name'], aliases=r['aliases'], sources=sorted(set(r['sources'])), oa=[m['id'] for m in r['openalex_matches']],
                           thesis_years=r.get('thesis_years'), cand=r.get('cand'))
for r in S:
    if r['existing_pi']:
        continue
    nm = Name([r['name']])
    k = next((k for k, v in rows.items() if nm.match(v['name']) or Name([v['name']] + v['aliases']).match(r['name'])), None)
    if k:
        rows[k]['sources'] = sorted(set(rows[k]['sources']) | {'dept-list-scan'}); rows[k]['aliases'] = list(dict.fromkeys(rows[k]['aliases'] + ([r['name']] if r['name'] != rows[k]['name'] else [])))
        continue
    rows[r['name']] = dict(name=r['name'], aliases=[], sources=['dept-list-scan'], oa=[o['id'] for o in r['oa']])
for n, al, src in EXTRA:
    rows[n] = dict(name=n, aliases=al, sources=[src], oa=[m['id'] for m in helpers.oa_matches('princeton', [n] + al)])
for k, r in rows.items():
    nm = Name([r['name']] + r['aliases'])
    adv = [p for p in PA if p['role'] == 'phd' and len(toks(p['adviser'])) <= 4 and nm.match(p['adviser'])]
    r['phd'] = dict(n=len(adv), years=sorted({p['year'] for p in adv}), depts=sorted({p['dept'] for p in adv})[:3])
    le = [e for e in E if nm.match(e['name'])]
    r['listed'] = {d: sorted({e['year'] for e in le if e['dept'] == d}) for d in sorted({e['dept'] for e in le})}
    r['titles'] = [t for t, _ in collections.Counter(e['title'] for e in le).most_common(3)]
    r['cs_raw'] = sum(A.get(i, {}).get('cs', 0) for i in r['oa']); r['cs_distinct'] = distinct_cs(r['oa'])
json.dump(list(rows.values()), open(out / 'princeton-triage.json', 'w'), indent=1, ensure_ascii=False)
print(len(rows))
