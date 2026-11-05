"""Main body of the split vs today's stored body: 10-word shingle containment and passage overlap.
usage: compare.py SAMPLE.json OUTDIR [--db ft.sqlite]"""
import json, sqlite3, sys, zlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'diversity'))
from common import passages  # noqa: E402  (numpy-only; the splitter the detector and the embeddings use)


def sh(text, k=10):
    w = text.split()
    return {' '.join(w[i:i + k]) for i in range(0, max(0, len(w) - k + 1))}


rows = json.load(open(sys.argv[1])); res = {}
for l in open(Path(sys.argv[2]) / 'res.jsonl'):
    r = json.loads(l); res[r['i']] = r
db = sqlite3.connect(sys.argv[4] if len(sys.argv) > 4 else '/tmp/od2961-sections/ft.sqlite')
out = []
for i, r in enumerate(rows):
    x = res[i]
    row = db.execute('select body from texts where key=?', (r['key'],)).fetchone()
    if 'error' in x or not row or not row[0]:
        continue
    old = zlib.decompress(row[0]).decode(); new = x['main']
    so, sn = sh(old), sh(new)
    po, pn = passages(old), passages(new)
    sp_o, sp_n = set(po), set(pn)
    out.append(dict(i=i, kind=r['kind'], app=x['flags']['appendix_found'], pos=x['flags']['appendix_position'], old_w=len(old.split()), new_w=len(new.split()),
                    old_in_new=len(so & sn) / max(1, len(so)), new_in_old=len(so & sn) / max(1, len(sn)),
                    pas_old=len(po), pas_new=len(pn), pas_exact=len(sp_o & sp_n), pas_jacc=len(sp_o & sp_n) / max(1, len(sp_o | sp_n))))
json.dump(out, open(Path(sys.argv[2]) / 'compare.json', 'w'))
import statistics as st
def summ(name, g):
    if not g: return
    print(f"{name:28s} n={len(g):3d}  old_in_new med={st.median(x['old_in_new'] for x in g):.3f}  new_in_old med={st.median(x['new_in_old'] for x in g):.3f}  "
          f"words new/old med={st.median(x['new_w'] / max(1, x['old_w']) for x in g):.3f}  passage jaccard med={st.median(x['pas_jacc'] for x in g):.3f}  "
          f">=0.95 both ways: {sum(x['old_in_new'] >= .95 and x['new_in_old'] >= .95 for x in g) / len(g):.2f}")
summ('all', out)
summ('no appendix found', [x for x in out if not x['app']])
summ('appendix after refs', [x for x in out if x['pos'] == 'after_refs'])
summ('appendix before/split refs', [x for x in out if x['pos'] in ('before_refs', 'split')])
summ('pdf', [x for x in out if x['kind'] == 'pdf']); summ('xml', [x for x in out if x['kind'] == 'xml'])
