"""Seeded 50-row audit packet for the reviewed Han-name joins of a listing-continuity school (tools/cjk_name_review.py output).

  name_join_audit.py draw <key> --worker <who wrote the joins> [--seed N]    -> <scratch>/name-join-audit-<key>.json (repeat = same file)
  name_join_audit.py show <key> <i>                                         one row's rows with the stored page text around each quote
  name_join_audit.py record <key> <verdicts.json> --reviewer <who>          verdict rows {canonical_name, verdict: pass|fail, why} -> reviewed/census-name-audit.json

A row FAILS only if a stored source proves the join wrong: two different people under one name (different profile pages that describe different
people, different departments, the same name twice in one capture) or a joined row that is not the same Han name. Nothing is judged from pinyin.
Pass rule: at most 2 failures of 50 and each failed identity fixed (split by profile in census-name-aliases.json); more failures redraw.
"""
import hashlib
import json
import random
import re
import sqlite3
import sys

import atlas_paths as P  # noqa: E402

SCR = '/n/fs/resemble/homogenizing-science/scratch/ns-a-1118'


def rows(key):
    return json.loads(P.data('census-name-aliases.json', key).read_text())['source_names']


def draw(key, worker, seed=20261118, n=50):
    sn = sorted(rows(key), key=lambda x: (x['canonical_name'], json.dumps(x['evidence'][0], sort_keys=True)))
    pick = random.Random(seed).sample(range(len(sn)), min(n, len(sn)))
    out = dict(school=key, seed=seed, worker=worker, population=len(sn), sample_hash=hashlib.sha256(json.dumps([sn[i]['canonical_name'] for i in sorted(pick)], ensure_ascii=False).encode()).hexdigest(),
               rows=[sn[i] for i in sorted(pick)])
    f = f'{SCR}/name-join-audit-{key}.json'
    json.dump(out, open(f, 'w'), ensure_ascii=False, indent=1)
    print(f, len(out['rows']), out['sample_hash'][:12])


def show(key, i, width=220):
    d = json.load(open(f'{SCR}/name-join-audit-{key}.json'))
    r = d['rows'][i]
    print(f"[{i}] {r['canonical_name']}  split={r['identity_basis']['split']}  profiles={json.dumps(r['identity_basis']['profiles'], ensure_ascii=False)}")
    c = sqlite3.connect(f'file:{P.data("listings-captures.sqlite", key)}?mode=ro', uri=True)
    for ev in r['evidence']:
        t = (c.execute('select text from captures where sha256=?', (ev['sha256'],)).fetchone() or [''])[0] or ''
        k = re.sub(r'\s+', '', ev['name_listed'])
        flat = re.sub(r'[\s\u3000]+', '', t)
        j = flat.find(k)
        print(f"  - {ev['url']}\n    format={ev['format']} profile={ev['profile']} times_on_page={flat.count(k)}\n    ...{flat[max(0, j - width):j + len(k) + width]}...")


def record(key, verdicts, reviewer):
    d = json.load(open(f'{SCR}/name-join-audit-{key}.json'))
    v = {x['canonical_name'] + '|' + str(x.get('i', '')): x for x in json.load(open(verdicts))}
    names = [(r['canonical_name'], i) for i, r in enumerate(d['rows'])]
    got = {x['i']: x for x in json.load(open(verdicts))}
    miss = [n for n, i in names if i not in got]
    if miss or reviewer == d['worker']:
        raise SystemExit(f'verdicts missing for {miss} or reviewer is the worker')
    fails = [x for x in got.values() if x['verdict'] == 'fail']
    out = dict(school=key, seed=d['seed'], sample_hash=d['sample_hash'], worker=d['worker'], reviewed_by=reviewer, population=d['population'],
               failures=len(fails), passed=len(fails) <= 2,
               rows=[dict(canonical_name=r['canonical_name'], verdict=got[i]['verdict'], why=got[i].get('why', '')) for i, r in enumerate(d['rows'])])
    f = P.data_w('census-name-audit.json', key) if False else None
    json.dump(out, open(f'{SCR}/name-join-audit-{key}-record.json', 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(dict(failures=len(fails), passed=out['passed'])))


if __name__ == '__main__':
    cmd, key = sys.argv[1], sys.argv[2]
    if cmd == 'draw':
        draw(key, sys.argv[sys.argv.index('--worker') + 1], int(sys.argv[sys.argv.index('--seed') + 1]) if '--seed' in sys.argv else 20261118)
    elif cmd == 'show':
        for i in sys.argv[3:]:
            show(key, int(i))
    elif cmd == 'record':
        record(key, sys.argv[3], sys.argv[sys.argv.index('--reviewer') + 1])
