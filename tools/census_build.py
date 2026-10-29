"""A protocol school's faculty census, built from its dated department listings (protocol stages 2-3), in the census
format the builder reads (Stanford's st_census.py output), plus the small collection a school without a site collection
brings (hierarchy/<key>/collection.json.gz, the Berkeley/Stanford pattern).

persons   listings/<key>/rows.json (tools/listing_rows.py): one person per name (rows merged across departments, slots
          and years when the given-name/family-name pair matches, nicknames included: pi_hierarchy.Name), plus the
          accepted CS-related candidates of other units (census/<key>-additions.json, merged by the builder itself).
rank      per year, the best rank the year's rows give (ladder > research > teaching > lecturer > adjunct > visiting >
          courtesy > emeritus > other); `rank` is the latest year's
PI        (protocol stage 3, owner rules 2026-10-21/22) in a department with coverage "full":
            ladder_faculty     a 2016-2026 listing row whose department title is a professor rank (assistant,
                               associate, full, collegiate or named), not courtesy, adjunct, visiting, research, teaching,
                               lecturer or emeritus; the quote is that row
            courtesy_faculty   a courtesy / affiliate appointment in the department whose same row also gives a professor
                               rank in the person's home unit (computing is the object or method of their work: the
                               department itself appointed them); the home unit goes to home-departments.json (stage 3)
          in a department with coverage "affiliated" (Michigan ECE): ladder_faculty as above AND an accepted decision in
          hierarchy/<key>/cs-related-review.json (computing is the object or method of their work); until reviewed the
          person is not a PI (`not_pi_reason` says so)
          research / teaching / lecturer / adjunct ranks and emeritus-only people: only with reviewed basis evidence
          (hierarchy/<key>/pi-basis-evidence.json: advises_phd | own_group with url + sha256 + quote)
listings  listings/<key>/listings.json: one row per (person, department, year): the year's first listing capture
          (rows the builder reads for R-PAP-01; rank_as_listed, emeritus, visiting flags)
-> census/<key>-faculty.json, census/<key>-report.md, hierarchy/<key>/collection.json.gz, listings/<key>/listings.json
usage: census_build.py <key>
"""
import collections, datetime, gzip, json, re, sys, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
from pi_hierarchy import Name, toks, nick_ok, EAST_ASIAN_FAMILY  # noqa: E402

ORDER = ['ladder', 'research', 'teaching', 'lecturer', 'adjunct', 'visiting', 'courtesy', 'emeritus', 'other']
HOME_PROF = re.compile(r'^(?:[A-Z][\w.\'\- ]+ )?(?:Assistant |Associate )?Professor(?! Emerit)(?: of [^,]+)?, (?!Electrical Engineering and Computer Science)(.+)$')


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def read(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def given_compatible(a, b, fam):
    """Two given-name token lists of one family name in one school's faculty listings are one person when: the first
    given names are nickname-equal; one is a 3+ letter prefix of the other ('Raj' / 'Rajesh', 'Mack' / 'Mackillo',
    'Clay' / 'Clayton'; never under an East Asian family name, R-LNK-02a); one side is initials that spell the other's
    given names ('P.C.' / 'Pei-Cheng'); or one side's first given name is the other's second ('L. Jay' / 'Jay',
    'S. Sandeep' / 'Sandeep'). Learned from Michigan 2026-10-29: the CSE/ECE lists spell one person several ways."""
    if not a or not b:
        return False
    if nick_ok(a[0], b[0]):
        return True
    if fam not in EAST_ASIAN_FAMILY and min(len(a[0]), len(b[0])) >= 3 and (a[0].startswith(b[0]) or b[0].startswith(a[0])):
        return True
    for x, y in ((a, b), (b, a)):
        if all(len(t) == 1 for t in x) and len(x) <= len(y) and all(y[i].startswith(x[i]) for i in range(len(x))):
            return True
        if len(x) >= 2 and len(x[0]) == 1 and x[1] == y[0]:
            return True
    return False


def merge_people(rows):
    """Group listing rows into persons: same family name and compatible given names (given_compatible); rows of one
    school only, never across schools."""
    groups, by_fam = [], collections.defaultdict(list)
    for r in sorted(rows, key=lambda r: r['observed']):
        t = toks(r['name'])
        if len(t) < 2:
            continue
        g = next((g for g in by_fam[t[-1]] if any(given_compatible(toks(n)[:-1], t[:-1], t[-1]) for n in g['names'])), None)
        if g is None:
            g = dict(names=[], rows=[]); groups.append(g); by_fam[t[-1]].append(g)
        if r['name'] not in g['names']:
            g['names'].append(r['name'])
        g['rows'].append(r)
    # the same personal homepage under one family name is one person ('H.V.' / 'Jag' Jagadish, 'Georgios' / 'George'
    # Tzimpragos, 'Noel' / 'Chris' Giebink: learned from Michigan 2026-10-29); a shared department or lab page is not personal
    def home_key(u):
        u = re.sub(r'^https?://(?:www\.|web\.)?', '', (u or '').lower()).rstrip('/')
        return u if u and not re.fullmatch(r'(?:[\w-]+\.)?(?:engin\.)?[\w-]+\.edu(?:/people(?:/.*)?)?', u) else None  # a bare site root or people page
    merged = True
    while merged:
        merged = False
        for fam, gs in by_fam.items():
            for i, a in enumerate(gs):
                ha = {home_key(r.get('homepage')) for r in a['rows']} - {None}
                for b in gs[i + 1:]:
                    if ha & ({home_key(r.get('homepage')) for r in b['rows']} - {None}):
                        a['names'] += [n for n in b['names'] if n not in a['names']]; a['rows'] += b['rows']
                        gs.remove(b); groups.remove(b); merged = True
                        break
                if merged:
                    break
            if merged:
                break
    for g in groups:
        g['rows'].sort(key=lambda r: r['observed'])
    return groups


def main(key):
    cfg = S.get(key); lo, hi = cfg.get('window') or [2016, 2026]
    coverage = {d['code']: d.get('coverage') or 'full' for d in cfg.get('departments') or []}
    rows = read(P.LISTINGS / key / 'rows.json', [])
    review = {r['name']: r for r in read(P.HIERARCHY / key / 'cs-related-review.json', {}).get('decisions', [])} \
        if isinstance(read(P.HIERARCHY / key / 'cs-related-review.json', {}), dict) else {}
    basis_ev = {r['pi']: r for r in read(P.HIERARCHY / key / 'pi-basis-evidence.json', [])}
    dblp_ids = read(P.HIERARCHY / key / 'dblp-ids.json', {})  # stage 5 (tools/dblp_ids_school.py); folded in when present
    for nm_, h_ in read(P.HIERARCHY / key / 'homepage-identity.json', {}).items():  # the PI's own homepage links (stage 5)
        d0 = dblp_ids.setdefault(nm_, {})
        if not d0.get('pid') and h_.get('dblp'):
            d0.update(pid=h_['dblp']['pid'], basis='pi_homepage_link', url=h_['dblp']['url'], sha256=h_['dblp']['sha256'], quote=h_['dblp']['quote'],
                      dump=None)
        d0['orcid'] = sorted(set(d0.get('orcid') or []) | {o['orcid'] for o in h_.get('orcid') or []})
    census, people, listing_rows, n = [], [], [], collections.Counter()
    for g in merge_people(rows):
        rs = [r for r in g['rows'] if lo <= r['year'] <= hi]
        if not rs:
            continue
        name = rs[-1]['name']  # the latest spelling
        ranks_by_year = collections.defaultdict(set)
        for r in rs:
            ranks_by_year[r['year']].add(r['rank'])
        best = {y: min(v, key=ORDER.index) for y, v in ranks_by_year.items()}
        depts = sorted({r['dept'] for r in rs}, key=lambda d: list(coverage).index(d) if d in coverage else 99)
        latest = max(rs, key=lambda r: r['observed'])
        sources = []
        seen = set()
        for r in rs:
            k = (r['dept'], r['year'], r['half'])
            if k in seen:
                continue
            seen.add(k)
            sources.append(dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], kind=f"dept_listing:{r['dept']}", observed=r['observed'],
                                rank_as_listed='; '.join(r['dept_title'] or r['titles']), rank=r['rank'], slot=r['slot']))
        # PI basis
        basis, why_not = None, None
        lad = [r for r in rs if r['rank'] == 'ladder']
        lad_full = [r for r in lad if coverage.get(r['dept']) == 'full']
        lad_aff = [r for r in lad if coverage.get(r['dept']) == 'affiliated']
        court = [r for r in rs if r['rank'] == 'courtesy' and coverage.get(r['dept']) == 'full']
        dec = review.get(name) or next((review[a] for a in g['names'] if a in review), None)
        if lad_full:
            r = lad_full[0]
            basis = dict(kind='ladder_faculty', url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], observed=r['observed'], role='; '.join(r['dept_title']))
        elif lad_aff and dec and dec.get('decision') == 'accepted':
            r = lad_aff[0]
            basis = dict(kind='ladder_faculty', url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], observed=r['observed'], role='; '.join(r['dept_title']),
                         cs_related=dict(decision='accepted', basis=dec.get('basis'), evidence=dec.get('evidence')))
        elif court:
            home = [(r, m) for r in court for t in r['titles'] for m in [HOME_PROF.match(t)] if m and 'courtesy' not in t.lower() and 'emerit' not in t.lower()]
            if home:
                r, m = home[0]
                hu = m.group(1).strip(); of = re.search(r'Professor of (.+?),', m.group(0))
                if of and re.match(r'(?:Medical School|School of|College of)', hu):  # 'Professor of X, Medical School': the department X
                    hu = of.group(1).strip()
                basis = dict(kind='courtesy_faculty', url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], observed=r['observed'],
                             role='; '.join(r['titles']), home_unit=hu)
            else:
                why_not = 'courtesy or affiliate appointment without a professor rank in a home unit'
        elif lad_aff:
            why_not = 'pending CS-related review (department coverage affiliated)' if not dec else f"CS-related review: {dec.get('decision')}"
        if basis is None and name in basis_ev:
            e = basis_ev[name]; basis = {k: e[k] for k in ('kind', 'url', 'sha256', 'quote', 'observed', 'role') if k in e}
        if basis is None and why_not is None:
            why_not = f"rank {best[max(best)]} without reviewed advising or own-group evidence"
        is_pi = basis is not None
        n[f'pi:{is_pi}'] += 1; n[f"basis:{(basis or {}).get('kind')}"] += 1
        cid = f'{key}_fac_' + slug(name)
        homepage = next((r['homepage'] for r in reversed(rs) if r.get('homepage')), None)
        census.append(dict(name=name, aliases=[a for a in g['names'] if a != name], collection_person_id=cid, structure_name=name,
                           profile_url=homepage, dblp=[d_['pid']] if (d_ := dblp_ids.get(name) or {}).get('pid') else [],
                           dblp_basis=d_.get('basis'), dblp_evidence={k: d_[k] for k in ('url', 'dump', 'sha256', 'quote') if k in d_} or None,
                           orcid=list(d_.get('orcid') or []), rank=best[max(best)], title_as_listed='; '.join(latest['titles']),
                           departments=depts, listed_in=depts, years_listed=sorted(best), ranks_by_year={str(y): sorted(v, key=ORDER.index) for y, v in sorted(ranks_by_year.items())},
                           sources=sources, is_pi=is_pi, pi_basis=basis, not_pi_reason=None if is_pi else why_not,
                           lab_units=[], collectives=[], emeritus_since=min((y for y, b in best.items() if b == 'emeritus'), default=None)))
        people.append(dict(id=cid, name=name, roles=['faculty'], contexts=[], profileUrl=homepage))
        by_dy = {}
        for r in rs:
            by_dy.setdefault((r['dept'], r['year']), r)
        for (d, y), r in sorted(by_dy.items()):
            listing_rows.append(dict(pi=name, school=key, department=d, year=y, capture_url=r['capture_url'], sha256=r['sha256'], quote=r['quote'],
                                     rank_as_listed='; '.join(r['dept_title'] or r['titles']), rank=r['rank'], emeritus=r['rank'] == 'emeritus',
                                     visiting=r['rank'] == 'visiting', observed=r['observed'], slot=r['slot']))
    for x in read(P.CENSUS / f'{key}-additions.json', []):  # accepted CS-related faculty of other units: a person record each
        if x.get('collection_person_id') and all(p_['id'] != x['collection_person_id'] for p_ in people):
            people.append(dict(id=x['collection_person_id'], name=x['name'], roles=['faculty'], contexts=[], profileUrl=x.get('profile_url')))
    rule = __doc__.split('\n-> ')[0]
    (P.CENSUS / f'{key}-faculty.json').write_text(json.dumps(dict(school=key, built_at=datetime.datetime.utcnow().isoformat() + 'Z', rule=rule, faculty=census),
                                                             indent=1, ensure_ascii=False))
    (P.LISTINGS / key / 'listings.json').write_text(json.dumps(listing_rows, indent=0, ensure_ascii=False))
    C = dict(people=people, works={}, personLinks=[], unitLinks=[], units=[], facultyPeriods=[],
             source=f'tools/census_build.py {key} (no site collection exists for this school)')
    (P.HIERARCHY / key).mkdir(parents=True, exist_ok=True)
    (P.HIERARCHY / key / 'collection.json.gz').write_bytes(gzip.compress(json.dumps(C, ensure_ascii=False).encode(), mtime=0))
    by = collections.Counter((x['rank'], x['is_pi']) for x in census)
    dep = collections.Counter((d, x['is_pi']) for x in census for d in x['departments'])
    L = [f"# {cfg['name']}: faculty census", '', f"Built {datetime.date.today()} by `tools/census_build.py {key}` from `listings/{key}/rows.json`.", '',
         f"- persons: {len(census)}; PIs: {sum(x['is_pi'] for x in census)}", f"- listing rows (person, department, year): {len(listing_rows)}", '',
         '| rank (latest) | PI | not PI |', '|---|---|---|']
    for r in ORDER:
        if by[(r, True)] or by[(r, False)]:
            L.append(f'| {r} | {by[(r, True)]} | {by[(r, False)]} |')
    L += ['', '| department | PI | not PI |', '|---|---|---|'] + [f'| {d} | {dep[(d, True)]} | {dep[(d, False)]} |' for d in coverage]
    L += ['', '## PI basis', ''] + [f'- {k[6:]}: {v}' for k, v in sorted(n.items()) if k.startswith('basis:') and k != 'basis:None']
    L += ['', '## Not PI, by reason', ''] + [f'- {k}: {v}' for k, v in collections.Counter(x['not_pi_reason'] for x in census if not x['is_pi']).most_common()]
    (P.CENSUS / f'{key}-report.md').write_text('\n'.join(L) + '\n')
    print(json.dumps(dict(persons=len(census), pis=sum(x['is_pi'] for x in census), listing_rows=len(listing_rows), **{k: v for k, v in n.items()})))


if __name__ == '__main__':
    main(sys.argv[1])
