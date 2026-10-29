"""Princeton + EPFL CS-related review (DBLP-based candidate lists): working indexes, rebuilt from shared stores.
<out>/princeton-thesis-index.json, <out>/epfl-thesis-index.json   thesis records (hierarchy/thesis-tools/records.py): one row per
    (record, adviser) with the adviser quote, and one row per record (authors)
<out>/princeton-listing-entries.json   princeton_listing_entries.py output (non-CS department faculty lists)
<out>/ep_listrows.json                 EPFL faculty-list entries ('Name Rank' quotes via epfl_listtext.valid_quotes) per candidate
usage: pe_index.py <out_dir> [thesis|plist|elist ...]
"""
import json, re, sys, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parents[2]
out = Path(sys.argv[1]); what = sys.argv[2:] or ['thesis', 'plist', 'elist']
sys.path.insert(0, str(HERE / 'hierarchy/thesis-tools')); sys.path.insert(0, str(Path(__file__).parent))
if 'thesis' in what:
    import records
    for school in ('princeton', 'epfl'):
        adv, au = [], []
        for r in records.load(school):
            base = dict(student=r['student'], author_raw=r['author_raw'], year=r['year'], role=r['role'], dept=r['dept'],
                        title=(r['title'] or '')[:150], url=r['url'], sha256=r['sha256'], id=r['id'])
            q0 = None
            for i, a in enumerate(r['advisers']):
                try:
                    q = r['q'](a)
                except ValueError:
                    q = None
                q0 = q0 or q
                adv.append(dict(base, adviser=a, pos=i, quote=q))
            try:
                qa = r['q'](r['advisers'][0]) if r['advisers'] else None
            except ValueError:
                qa = None
            au.append(dict(base, advisers=r['advisers'], quote=qa))
        json.dump(dict(advisers=adv, authors=au), open(out / f'{school}-thesis-index.json', 'w'), ensure_ascii=False)
        print(school, len(adv), len(au), flush=True)
if 'plist' in what:
    subprocess.run([sys.executable, str(Path(__file__).parent / 'princeton_listing_entries.py'), str(out)], check=True)
if 'elist' in what:
    import epfl_listtext as E
    L = E.lists()
    C = json.load(open(HERE / 'hierarchy/epfl/cs-related-candidates.json'))

    def forms(names):
        o = set()
        for n in names:
            n = re.sub(r'\s+', ' ', n).strip()
            if n.count(',') == 1:
                a, b = [x.strip() for x in n.split(',')]; n = b + ' ' + a
            t = [x for x in n.split(' ') if x and not re.fullmatch(r'(?:[A-Z]\.)+[A-Z]?\.?|[A-Z]', x)]
            if len(t) >= 2:
                o.add((t[0], t[-1]))
                if len(t) >= 3:
                    o.add((t[0], ' '.join(t[1:])))
        return o
    EXTRA = {'Adrian M. Ionescu': ['Mihai Adrian Ionescu', 'Adrian Mihai Ionescu']}  # spellings the lists use (people.epfl.ch name)
    res = {}
    for c in C:
        fs = forms(c['names'] + EXTRA.get(c['name'], [])); rows = []
        for cap in L:
            if not any(E.present([cap], g, f) for g, f in fs):
                continue
            q = []
            for g, f in fs:
                q += E.valid_quotes(cap, g, f)
            for quote, rank in dict.fromkeys(q):
                rows.append(dict(id=cap['id'], url=cap['url'], school=cap['school'], year=cap['year'], observed=cap['observed'], quote=quote, rank=rank))
        res[c['author']] = dict(name=c['name'], rows=rows)
    json.dump(res, open(out / 'ep_listrows.json', 'w'), ensure_ascii=False)
    print('elist', len(res), flush=True)
