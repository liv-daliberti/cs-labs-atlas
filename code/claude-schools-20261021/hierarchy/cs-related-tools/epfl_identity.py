"""EPFL: identity check of candidate OpenAlex author ids against their own works. For each id, the EPFL-affiliated works
of the sweep (2016-2026) carrying it, how many have a co-author who is a PhD student the person directed (Infoscience
thesis records, hierarchy/thesis-tools/records.py), and the ORCIDs on the authorships.
usage: epfl_identity.py <spec.json> <out.json>   spec: {person: {"ids": [...], "adviser_raw": [...]}}"""
import collections, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import helpers
from author_index import works
from pi_hierarchy import Name

spec = json.load(open(sys.argv[1]))
R = json.load(open(helpers.IDX_DIR / 'epfl-theses.json'))
inst = 'https://openalex.org/I5124864'
students = {p: [Name([r['student']]) for r in R if r['role'] == 'phd' and set(r['advisers']) & set(s['adviser_raw'])] for p, s in spec.items()}
owner = collections.defaultdict(list)
for p, s in spec.items():
    for i in s['ids']:
        owner[i].append(p)
out = {p: {i: dict(works=0, with_advisee=0, examples=[], orcids=collections.Counter()) for i in s['ids']} for p, s in spec.items()}
for w in works('epfl'):
    au = w.get('authorships') or []
    for a in au:
        aid = (a.get('author') or {}).get('id')
        if aid not in owner or not any(inst in (x.get('lineage') or [x.get('id')]) for x in a.get('institutions') or []):
            continue
        others = [(x.get('raw_author_name') or (x.get('author') or {}).get('display_name') or '') for x in au if x is not a]
        for p in owner[aid]:
            o = out[p][aid]; o['works'] += 1
            if (a.get('author') or {}).get('orcid'):
                o['orcids'][a['author']['orcid'].rsplit('/', 1)[-1]] += 1
            hit = next((n for n in others for s_ in students[p] if s_.match(n)), None)
            if hit:
                o['with_advisee'] += 1
                if len(o['examples']) < 3:
                    o['examples'].append(dict(oa=w['id'], year=w.get('publication_year'), title=(w.get('title') or '')[:120], advisee=hit))
for p in out:
    for i in out[p]:
        out[p][i]['orcids'] = dict(out[p][i]['orcids'])
    out[p]['_students'] = len(students[p])
json.dump(out, open(sys.argv[2], 'w'), indent=1, ensure_ascii=False)
