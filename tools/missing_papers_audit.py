"""How many of each PI's papers are we missing? DBLP person pages as the independent reference.

For every PI with a DBLP person id (census or the unique-name lookup in pi_hierarchy), every DBLP publication of
2016-2026 in a year the PI's appointment covers (a listing year or inside a faculty period) is checked against the PI's
lab papers (hierarchy/<school>/lab_papers.jsonl.gz, by DOI or normalized title). A missing one is classified with the
OpenAlex sweeps:
  in_sweep_no_school    OpenAlex has it with an authorship naming the PI, but the PI's authorship lists no school
  in_pi_works_no_inst   the PI's OpenAlex works have it, with no institution on the PI's authorship (page-1 candidates)
  not_in_openalex_sets  neither the school sweep nor the PI's OpenAlex works contain it (no OpenAlex record, or the
                        PI's author id is not anchored)
  outside_or_other      found, but excluded by the appointment rule or identity
DBLP type 'Informal' (CoRR preprints) is reported separately, since a preprint often duplicates a published version.
-> hierarchy/missing-papers-audit.json
usage: missing_papers_audit.py <school> ...
"""
import collections, gzip, json, sqlite3, sys, zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from pi_hierarchy import read, HERE, DBLP, ndoi, norm_title  # noqa: E402
import atlas_paths as P  # noqa: E402  (every path in one place)


def run(school):
    pis = read(HERE / 'hierarchy' / school / 'pis.json')
    dp = HERE / 'hierarchy' / school / 'raw/dblp_pubs.json.gz'
    if not dp.exists():
        dp = P.archive_sweep(DBLP.get(school, '')) / 'raw/dblp_pubs.json.gz'
    if not dp.exists() or not (DBLP.get(school) or 'hierarchy' in str(dp)):
        return dict(school=school, note='no DBLP cache')
    pubs = read(dp)['pubs']
    rows = [json.loads(l) for l in gzip.open(HERE / 'hierarchy' / school / 'lab_papers.jsonl.gz', 'rt')]
    mine = collections.defaultdict(lambda: (set(), set()))
    for r in rows:
        d, t = mine[r['pi']]
        if r.get('doi'):
            d.add(ndoi(r['doi']))
        t.add(norm_title(r.get('title')))
    sweep_t, sweep_d = set(), set()
    c = sqlite3.connect(f'file:{HERE}/hierarchy/{school}/openalex-sweep.sqlite?mode=ro', uri=True)
    for (b,) in c.execute('select body from pages'):
        for w in json.loads(zlib.decompress(b)):
            sweep_t.add(norm_title(w.get('title'))); sweep_d.add(ndoi(w.get('doi')))
    pw_t = set()
    pw = HERE / 'hierarchy' / school / 'pi-works.sqlite'
    if pw.exists():
        for (b,) in sqlite3.connect(f'file:{pw}?mode=ro', uri=True).execute('select body from works'):
            pw_t.add(norm_title(json.loads(zlib.decompress(b)).get('title')))
    owner = collections.defaultdict(list)
    for p in pis:
        for q in p.get('dblp') or []:
            owner[q].append(p)
    n = collections.Counter(); per = collections.Counter(); per_miss = collections.Counter()
    for rec in pubs.values():
        y = rec.get('year')
        if not y or not (2016 <= int(y) <= 2026):
            continue
        for q in rec.get('authors') or {}:
            for p in owner.get(q, []):
                years = {l['year'] for l in p['listings']}
                in_per = any((q_['start'] or '9999')[:4] < str(y) < (q_['end'] or '9999')[:4] for q_ in p['periods'])
                if int(y) not in years and not in_per:
                    continue
                kind = 'preprint' if rec.get('type') == 'Informal' or 'CoRR' in str(rec.get('venue')) else 'published'
                d, t = mine[p['pi']]; tt = norm_title((rec.get('title') or '').rstrip('.'))
                have = (rec.get('doi') and ndoi(rec['doi']) in d) or tt in t
                n[(kind, 'have' if have else 'missing')] += 1; per[p['pi']] += 1
                if not have:
                    per_miss[p['pi']] += 1
                    why = 'in_sweep_no_school' if tt in sweep_t or (rec.get('doi') and ndoi(rec['doi']) in sweep_d) else \
                          'in_pi_works_no_inst' if tt in pw_t else 'not_in_openalex_sets'
                    n[(kind, why)] += 1
    pub = n[('published', 'have')] + n[('published', 'missing')]
    out = dict(school=school, pis_with_dblp=sum(bool(p.get('dblp')) for p in pis),
               published=dict(total=pub, have=n[('published', 'have')], missing=n[('published', 'missing')],
                              coverage=round(n[('published', 'have')] / max(1, pub), 3),
                              why={k[1]: v for k, v in n.items() if k[0] == 'published' and k[1] not in ('have', 'missing')}),
               preprints=dict(total=n[('preprint', 'have')] + n[('preprint', 'missing')], have=n[('preprint', 'have')]),
               worst=[(pi, per_miss[pi], per[pi]) for pi, _ in sorted(per_miss.items(), key=lambda x: -x[1])[:12]])
    return out


if __name__ == '__main__':
    res = [run(s) for s in sys.argv[1:]]
    json.dump(res, open(HERE / 'hierarchy/missing-papers-audit.json', 'w'), indent=1)
    for r in res:
        print(json.dumps(r))
