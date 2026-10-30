"""Princeton in the census format of the other schools, so tools/pi_hierarchy.py builds all five the same way.

PIs        the 91 own-lab PIs (claude-pi-own-labs-20261021) with their lab unit and leader person, plus CS faculty on the
           captured CS faculty listings 2016-2026 who advised a PhD student in the window (a named adviser field on the
           graduate roster, a PhD alumni entry from 2016 on, or an FPO announcement; senior-thesis and master's-only
           advising do not make a PI). Associated faculty of the CS listing who head a lab elsewhere come from
           EXTRA_PIS with their lab-page evidence.
sources    every dated listing row (claude-princeton-listings-20261022/listings.json, re-verified there) for the 91; for the
           added PIs, the (name, rank) entries read from the same stored captures, each checked as a substring of the
           capture's collapsed text.
periods    the reviewed arrival statements (claude-princeton-periods-20261021/periods/princeton-arrivals-reviewed.json)
           -> periods/princeton-faculty-periods.json, in the collection's facultyPeriods shape.
-> census/princeton-faculty.json, periods/princeton-faculty-periods.json
"""
import collections, datetime, json, re, sqlite3, sys, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
HERE = P.WORK; SW = P.SWEEPS
SITE = P.SITE_ROOT
LST = SW / 'claude-princeton-listings-20261022'
sys.path.insert(0, str(LST / 'scripts')); sys.path.insert(0, str(HERE / 'tools'))
import extract, match  # noqa: E402  (the listings sweep's own text extraction)
from pi_hierarchy import Name, read  # noqa: E402

ADDED = {  # CS faculty with PhD advising stated in 2016-2026 (graduate roster / PhD alumni / FPO adviser field)
    'Zhuang Liu': 'Boya Zeng — Advisers Zhuang Liu',
    'Victoria Dean': 'Anha Khan — Advisers Victoria Dean',
    'Robert Sedgewick': 'Alex Iriza Graduate Student airiza (@cs.princeton.edu) (609) 258-1781 001B Computer Science Adviser(s): Robert Sedgewick',
    'Robert Schapire': 'Haipeng Luo — Haipeng Luo Adviser(s): Robert Schapire Degree: PhD, 2016',
    'Larry Peterson': 'Soner Sevinc',
    'Andrea LaPaugh': 'Muneeb Ali — Muneeb Ali Adviser(s): Andrea LaPaugh Degree: PhD, 2017',
    'Yoram Singer': 'Udaya Ghai',
}


def main():
    pis = read(LST / 'input-pis.json'); pis = pis if isinstance(pis, list) else pis['pis']
    rep = read(SITE / 'research/claude-pi-own-labs-20261021/report.json')
    lab = {r['pi']: r for r in rep['labs'] if r.get('lab')}
    C = read(SITE / 'atlas/data/collection-princeton.json.gz')
    people = C['people'] if isinstance(C['people'], list) else list(C['people'].values()); Pid = {p['id']: p for p in people}
    units = {u['id']: u for u in C['units']}
    lead = collections.defaultdict(collections.Counter)  # a lab's paper links name its leader's person id
    for l in C['unitLinks']:
        if l.get('leader'):
            lead[l['unit']][l['leader']] += 1
    nver = collections.Counter(l['person'] for l in C['personLinks'] if l.get('status') == 'verified')

    def person_of(name, aliases, unit):
        if lead.get(unit):
            return lead[unit].most_common(1)[0][0]
        nm = Name([name] + list(aliases or []))
        c = [q for q in people if nm.match(q['name'])]
        c.sort(key=lambda q: (-nver[q['id']], 'cs.princeton.edu/people/profile' not in str(q.get('profileUrl') or '')))
        if len(c) == 1:  # the only person of that name in the collection
            return c[0]['id']
        return c[0]['id'] if c and (nver[c[0]['id']] or 'cs.princeton.edu/people/profile' in str(c[0].get('profileUrl') or '')) else None

    rows = collections.defaultdict(list)
    for r in read(LST / 'listings.json'):
        rows[r['pi']].append(r)
    ident = {}  # the lab-by-lab records' reviewed identity: OpenAlex author ids and DBLP person
    for f in (SW / 'claude-labrecords-20261019/records/princeton').glob('*/record.json'):
        x = read(f); ident[x['pi']] = x.get('identity') or {}
    out = []
    for p in pis:
        r = lab.get(p['pi']); u = units.get((r or {}).get('lab'))
        out.append(dict(name=p['pi'], aliases=p.get('aliases') or [], collection_person_id=person_of(p['pi'], p.get('aliases'), (r or {}).get('lab')),
                        departments=[p.get('homeDepartment') or 'Computer Science'] + [d for d in p.get('departments') or [] if d != p.get('homeDepartment')],
                        is_pi=True, pi_basis=dict(kind='owner_own_lab_census_20261021', lab=(r or {}).get('lab')),
                        dblp=ident.get(p['pi'], {}).get('dblp') or [], openalex=ident.get(p['pi'], {}).get('openalex') or [],
                        lab_units=[r['lab']] if r else [], years_listed=sorted({x['year'] for x in rows[p['pi']]}),
                        sources=[dict(url=x['capture_url'], sha256=x['sha256'], quote=x['quote'], observed=x['observed_on'], kind='dept_listing:' + x['department'],
                                      rank=x.get('rank_as_listed'), emeritus=x.get('emeritus'), visiting=x.get('visiting')) for x in rows[p['pi']]]))
    # added PIs: their entries on the stored CS captures
    con = sqlite3.connect(f'file:{LST}/captures/listings.sqlite?mode=ro', uri=True)
    caps = con.execute("select capture_url, wayback_timestamp, content_type, raw_zlib, sha256 from captures where department='Computer Science' and http_status=200").fetchall()
    NAME = re.compile(r"^[A-ZÀ-Ž][\w'’.\-À-ž]+(?: [A-ZÀ-Ž(][\w'’.\-À-ž)]*){1,4}$")
    found = collections.defaultdict(dict)
    for url, ts, ct, raw, sha in caps:
        b = [t.strip() for _, t in extract.blocks(zlib.decompress(raw), ct)]; text = extract.collapse('\n'.join(b))
        for i in range(len(b) - 1):
            n, t = b[i], b[i + 1]
            if not (NAME.match(n) and match.FAC_RX.search(t) and len(t) < 90):
                continue
            for a in ADDED:
                q = f'{n} {t}'
                if Name([a]).match(n) and q in text:
                    found[a].setdefault(int(ts[:4]), dict(url=url, sha256=sha, quote=q, observed=f'{ts[:4]}-{ts[4:6]}-{ts[6:8]}', kind='dept_listing:Computer Science', rank=t))
    for a, q in ADDED.items():
        pid = person_of(a, [], None)
        out.append(dict(name=a, aliases=[], collection_person_id=pid, departments=['Computer Science'], is_pi=True,
                        pi_basis=dict(kind='advises_phd', quote=q, note='named adviser field: graduate roster, PhD alumni entry or FPO announcement'),
                        lab_units=[], years_listed=sorted(found[a]), sources=[found[a][y] for y in sorted(found[a])]))
    json.dump(out, open(HERE / 'census/princeton-faculty.json', 'w'), indent=1, ensure_ascii=False)
    # reviewed arrival statements as faculty periods
    arr = read(SW / 'claude-princeton-periods-20261021/periods/princeton-arrivals-reviewed.json'); per = []
    byname = {x['name']: x for x in out}
    for x in arr:
        if x.get('status') != 'accepted' or x['pi'] not in byname:
            continue
        ev = [dict(url=x.get('fetched_url') or x['url'], sha256=x['sha256'], quote=x['quote'], kind='faculty_start')]
        if x.get('left') and x.get('left_quote'):
            ev.append(dict(url=x['left_url'], sha256=x['left_sha256'], quote=x['left_quote'], kind='faculty_end_' + (x.get('left_kind') or 'moved')))
        per.append(dict(id=f"princeton_faculty_period_arrival_{len(per)}", personId=byname[x['pi']]['collection_person_id'], name=x['pi'], school='princeton',
                        facultyStart=str(x['arrived']), facultyEnd=str(x['left']) if x.get('left') else None,
                        ongoingAsOf=None if x.get('left') else (x.get('last_confirmed') or datetime.date.today().isoformat()), evidence=ev))
    json.dump(per, open(HERE / 'periods/princeton-faculty-periods.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(dict(pis=len(out), added=len(ADDED), added_with_person=sum(bool(x['collection_person_id']) for x in out[-len(ADDED):]),
                          added_listing_years={a: sorted(found[a]) for a in ADDED}, periods=len(per),
                          without_person=[x['name'] for x in out if not x['collection_person_id']])))


if __name__ == '__main__':
    main()
