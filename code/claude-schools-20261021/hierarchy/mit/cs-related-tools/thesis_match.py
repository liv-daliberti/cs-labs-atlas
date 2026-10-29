"""Theses each candidate supervised, from the thesis index (thesis_index.py): adviser strings split on 'and' / ';' and
matched on folded given name (or initial when the adviser string has only an initial) plus surname.
usage: thesis_match.py <theses.jsonl> <out.json>
"""
import json, re, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from scan_listings_lib import fold, natural  # noqa: E402

H = '/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021'


def toks(s):
    return [t for t in re.split(r"[\s.]+", fold(s).lower().replace(',', ' ')) if t]


def split_adv(a):
    a = re.sub(r'\.$', '', a.strip())
    parts = re.split(r'\s*;\s*|\s+and\s+|\s*&\s*', a)
    out = []
    for p in parts:
        p = p.strip().strip(',')
        if p.count(',') == 1 and not re.search(r',\s*(Jr|Sr|II|III)\b', p):
            x, y = [z.strip() for z in p.split(',')]
            p = f'{y} {x}'
        p = re.sub(r'\([^)]*\)', ' ', p)
        out.append(p)
    return [p for p in out if p]


def same(cand_forms, adv):
    t = toks(adv)
    if len(t) < 2:
        return False
    for g, s in cand_forms:
        if s not in t[1:]:
            continue
        i = t.index(s, 1)
        if s != t[-1] and not all(x in ('jr', 'sr', 'ii', 'iii') for x in t[i + 1:]):
            continue
        given = t[:i]
        if given and (given[0] == g or (len(given[0]) == 1 and given[0] == g[0]) or (len(given) > 1 and given[1] == g)):
            return True
    return False


def forms(names):
    f = set()
    for n in names:
        t = toks(natural(n))
        t = [x for x in t if x not in ('jr', 'sr', 'ii', 'iii')]
        if len(t) >= 2:
            gs = [x for x in t[:-1] if len(x) > 1]
            for g in gs[:2]:
                f.add((g, t[-1]))
            if '-' in t[-1]:
                for g in gs[:1]:
                    f.add((g, t[-1].split('-')[-1]))
    return f


def main(src, out):
    th = [json.loads(l) for l in open(src)]
    cands = json.load(open(f'{H}/hierarchy/mit/cs-related-candidates.json'))
    res = {}
    for c in cands:
        fm = forms([c['name']] + c.get('names', []))
        hits = []
        for r in th:
            if any(same(fm, a) for adv in r['advisers'] for a in split_adv(adv)):
                ds = ' '.join(r['degree_statement'] + r['degree'])
                phd = bool(re.search(r'Ph\.\s?D|Sc\.\s?D|Doctor|Ph D|PhD', ds))
                y = int(str(r['issued'])[:4]) if r.get('issued') and str(r['issued'])[:4].isdigit() else None
                hits.append(dict(r, phd=phd, year=y))
        by = {}
        for h in hits:
            by.setdefault(h['handle'], h)
        hs = list(by.values())
        res[c['author']] = dict(name=c['name'], n=len(hs), phd=sum(h['phd'] for h in hs if h['year'] and 2016 <= h['year'] <= 2026),
                                years=sorted({h['year'] for h in hs if h['year']}), theses=hs)
    json.dump(res, open(out, 'w'), ensure_ascii=False)
    print(sum(v['phd'] > 0 for v in res.values()), 'candidates with a PhD thesis 2016-2026;', sum(v['n'] > 0 for v in res.values()), 'with any thesis')


main(*sys.argv[1:])
