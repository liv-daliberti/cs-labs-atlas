"""Berkeley EECS (CS) in the census format of the other schools, plus the small collection pi_hierarchy.py reads.

Berkeley has no site collection: its first build chain (claude-berkeley-20261021) stalls at the DBLP step while
sparql.dblp.org does not answer. Everything here comes from that sweep's captured pages:
faculty    people/dept_berkeley.json faculty rows: one per person-year of the EECS CS faculty list (Wayback, sha256, quote)
           -> years_listed and dated listing sources; rank from `appointment` (ladder, emeritus, lecturer, teaching, adjunct)
students   the same file's PhD student and postdoc rows (advisers as listed) and people/berkeley_theses.json (a thesis on a
           faculty member's own EECS dissertations page has that faculty member as adviser)
labs       people/units.json: a unit whose only listed leader is the PI is the PI's own lab; others are collectives
PI         a faculty member with a stated PhD advisee or postdoc in 2016-2026, or the sole leader of a lab unit
merged    with the Berkeley chain's own census (census/berkeley-faculty.json, written by claude-berkeley-20261021/tools/
          bk_census.py): its DBLP person ids and aliases join each person, and a person is a PI when either census says so
-> census/berkeley-faculty-hierarchy.json (the chain owns census/berkeley-faculty.json), hierarchy/berkeley/collection.json.gz
"""
import collections, gzip, hashlib, json, re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
HERE = P.WORK; BK = P.sweep('claude-berkeley-20261021') / 'people'


def slug(s):
    return re.sub('[^a-z0-9]+', '-', s.lower()).strip('-')


def main():
    d = json.loads((BK / 'dept_berkeley.json').read_text()); theses = json.loads((BK / 'berkeley_theses.json').read_text())['theses']
    units = json.loads((BK / 'units.json').read_text())['units']
    fac = collections.OrderedDict()
    for r in d['people']:
        if r['role'] == 'faculty':
            fac.setdefault(r['name'], []).append(r)
    by_hp = {rows[0].get('homepage_id'): n for n, rows in fac.items() if rows[0].get('homepage_id')}
    people, adv = {}, collections.Counter()
    for n, rows in fac.items():
        people[n] = dict(id='berkeley_fac_' + slug(n), name=n, roles=['faculty'], contexts=[], profileUrl=rows[-1].get('profile'))
    def student(name):
        k = 'berkeley_stu_' + slug(name)
        return people.setdefault('stu:' + name, dict(id=k, name=name, roles=[], contexts=[]))
    for r in d['people']:
        if r['role'] == 'faculty':
            continue
        s = student(r['name']); s['roles'] = list(dict.fromkeys(s['roles'] + [r['role']]))
        for a in r.get('advisers') or []:
            s['contexts'].append(dict(type='academic_advising', advisor=a, year=r.get('year'), years=[r.get('year')] if r.get('year') else [],
                                      role=r['role'], sources=[r['source']]))
            if 2016 <= (r.get('year') or 0) <= 2026:
                adv[a] += 1
    for t in theses:
        hp = t['source']['url'].rsplit('/', 1)[-1].removesuffix('.html'); a = by_hp.get(hp)
        if not a:
            continue
        s = student(t['author']); s['roles'] = list(dict.fromkeys(s['roles'] + ['phd_alumnus']))
        s['contexts'].append(dict(type='thesis_adviser', advisor=a, year=t.get('year'), years=[t['year']] if t.get('year') else [], role=t.get('title'),
                                  sources=[t['source']], work=t.get('report')))
        if 2016 <= (t.get('year') or 0) <= 2026:
            adv[a] += 1
    cunits, own = [], collections.defaultdict(list)
    for u in units:
        uid = 'berkeley_unit_' + (u.get('acronym') or slug(u['name']))
        leaders = list((u.get('leaders') or {}).keys())
        cunits.append(dict(id=uid, name=u['name'], kind=u.get('unitType'), leaders=leaders, url=(u.get('urls') or [None])[0], sources=list((u.get('leaders') or {}).values())))
        for l in leaders:
            own[l].append(uid)
    census = []
    for n, rows in fac.items():
        rows = sorted(rows, key=lambda r: r['year']); last = rows[-1]
        mine = [u for u in cunits if u['id'] in own.get(n, [])]
        solo = [u['id'] for u in mine if len(u['leaders']) == 1]
        is_pi = adv[n] > 0 or bool(solo)
        census.append(dict(name=n, aliases=[], collection_person_id=people[n]['id'], profile_url=last.get('profile'), dblp=[], rank=last.get('appointment'),
                           title_as_listed=last.get('title'), departments=['EECS'], years_listed=sorted({r['year'] for r in rows}),
                           sources=[dict(url=r['source']['url'], sha256=r['source']['sha256'], quote=r['source']['quote'], kind='dept_listing:EECS-CS',
                                         observed=f"{r['source']['capture'][:4]}-{r['source']['capture'][4:6]}-{r['source']['capture'][6:8]}" if r['source'].get('capture') else None)
                                    for r in rows if r.get('source', {}).get('sha256')],
                           is_pi=is_pi, pi_basis=dict(kind='advises_phd_or_postdoc', advisees_2016_2026=adv[n]) if adv[n] else (dict(kind='sole_unit_leader', units=solo) if solo else None),
                           lab_units=solo + [u['id'] for u in mine if len(u['leaders']) > 1]))
    chain = HERE / 'census/berkeley-faculty.json'
    if chain.exists():
        ch = json.loads(chain.read_text()); ch = ch.get('faculty', ch) if isinstance(ch, dict) else ch
        by = {r['name']: r for r in ch}
        for x in census:
            r = by.get(x['name'])
            if r:
                x['dblp'] = list(dict.fromkeys(list(x['dblp']) + list(r.get('dblp') or [])))
                x['aliases'] = list(dict.fromkeys(list(x['aliases']) + list(r.get('aliases') or [])))
                if r.get('is_pi') and not x['is_pi']:
                    x['is_pi'], x['pi_basis'] = True, dict(kind='berkeley_chain_census', basis=r.get('pi_basis'))
    (HERE / 'census/berkeley-faculty-hierarchy.json').write_text(json.dumps(census, indent=1, ensure_ascii=False))
    C = dict(people=list(people.values()), works={}, personLinks=[], unitLinks=[], units=cunits, facultyPeriods=[],
             source='tools/berkeley_census.py from claude-berkeley-20261021/people (no site collection exists for Berkeley yet)')
    (HERE / 'hierarchy/berkeley').mkdir(parents=True, exist_ok=True)
    (HERE / 'hierarchy/berkeley/collection.json.gz').write_bytes(gzip.compress(json.dumps(C, ensure_ascii=False).encode(), mtime=0))
    print(json.dumps(dict(faculty=len(census), pis=sum(x['is_pi'] for x in census), by_rank=dict(collections.Counter(x['rank'] for x in census if x['is_pi'])),
                          not_pi=[x['name'] for x in census if not x['is_pi'] and x['rank'] in ('ladder',)], students=len(people) - len(fac), units=len(cunits))))


if __name__ == '__main__':
    main()
