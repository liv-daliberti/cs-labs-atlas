"""For each Princeton qualifier, every stored department-list capture (listings sweep store, and this review's store for
pages it fetched) that names them: year, page, quote (name + title, or section heading through the name), section.
-> <out>/princeton-gather.json
usage: princeton_gather.py <out_dir> <config.json>
"""
import json, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import princeton_lib as L  # noqa: E402

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / 'hierarchy/missing-pi-tools'))
import mpcap  # noqa: F401,E402

out, cfg = Path(sys.argv[1]), json.load(open(sys.argv[2]))
texts = {}


def caps_for(pattern):
    rows = [dict(src='listings', dept=d, page_url=pu, capture_url=cu, ts=ts, sha256=sha) for d, pu, cu, ts, sha in L.listing_captures(pattern)]
    c2 = sqlite3.connect(f"file:{HERE / 'hierarchy/cs-related-captures-princeton.sqlite'}?mode=ro", uri=True)
    for cu, sha in c2.execute("select capture_url, sha256 from captures where capture_url like ? and status=200 and error is null", ('%' + pattern.strip('%') + '%',)):
        if not any(r['capture_url'] == cu for r in rows):
            rows.append(dict(src='review', dept=None, page_url=cu.split('id_/', 1)[-1], capture_url=cu, ts=cu.split('/web/')[1][:14], sha256=sha))
    return rows


def text_of(r):
    if r['capture_url'] not in texts:
        if r['src'] == 'listings':
            texts[r['capture_url']] = L.listing_text(r['capture_url'])
        else:
            c2 = sqlite3.connect(f"file:{HERE / 'hierarchy/cs-related-captures-princeton.sqlite'}?mode=ro", uri=True)
            texts[r['capture_url']] = c2.execute('select text from captures where capture_url=? and status=200 order by id desc limit 1', (r['capture_url'],)).fetchone()[0]
    return texts[r['capture_url']]


res = {}
for name, c in cfg.items():
    hits = []
    for pat in c['pages']:
        for r in caps_for(pat):
            q = L.find_listing_quote(text_of(r), [tuple(f) for f in c['forms']])
            if q:
                hits.append(dict(r, year=int(r['ts'][:4]), **q))
    res[name] = sorted(hits, key=lambda h: h['ts'])
json.dump(res, open(out / 'princeton-gather.json', 'w'), indent=1, ensure_ascii=False)
for n, h in res.items():
    print('==', n)
    for y in sorted({x['year'] for x in h}):
        xs = [x for x in h if x['year'] == y]
        print('  ', y, len(xs), '|', xs[0]['page_url'][-45:], '|', xs[0]['section'], '|', xs[0]['quote'][:110])
