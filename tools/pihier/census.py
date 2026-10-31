"""The census: the build's inputs, the census rows merged into one record per PI, and each PI's lab.
R-HIER-01 (one own lab per PI; a census lab unit is reused only with this PI as its single leader), R-HIER-02 (collectives
are not labs: COLLECTIVE)."""
import collections, re

from .common import AFF, INST, as_list, collection_work_matcher, read
from .names import Name, nick_ok, toks
from .periods import listings_after_move, pi_listings, pi_mine, pi_periods

COLLECTIVE = re.compile(r'\b(cent(?:er|re)|initiative|consortium|program(?:me)?|project|cluster|institute)\b', re.I)  # not labs (owner, 2026-10-21)


def load(ctx):
    """The school's census (plus census/<school>-additions.json), its collection (a school's own collection.json.gz, else
    the site's), the faculty periods (collection + periods/<school>-faculty-periods.json), the charter's institution and
    affiliation pattern, the collection's person links and the collection-work matcher."""
    HERE, SITE, school = ctx.here, ctx.site, ctx.school
    cf = HERE / f'census/{school}-faculty-hierarchy.json'  # a school whose census path another chain owns (Berkeley) keeps its own
    census = read(cf if cf.exists() else HERE / f'census/{school}-faculty.json')
    census = census.get('faculty', census) if isinstance(census, dict) else census
    if (HERE / f'census/{school}-additions.json').exists():  # listed faculty the census missed (tools/listed_not_in_census.py)
        census = list(census) + read(HERE / f'census/{school}-additions.json')
    own_c = HERE / 'hierarchy' / school / 'collection.json.gz'  # a school without a site collection (Berkeley) brings its own
    C = read(own_c if own_c.exists() else SITE / f'collection-{school}.json.gz')
    people = C['people'] if isinstance(C['people'], list) else list(C['people'].values())
    Pid = {p['id']: p for p in people}; units = {u['id']: u for u in C['units']}; works = C['works']
    periods = list(C.get('facultyPeriods') or [])
    pf = HERE / f'periods/{school}-faculty-periods.json'
    if pf.exists():
        x = read(pf); periods += x if isinstance(x, list) else x.get('periods', [])
    inst = 'https://openalex.org/' + INST[school]; aff = re.compile(AFF[school], re.I)
    pls = collections.defaultdict(list)
    for l in C['personLinks']:
        pls[l['person']].append(l)
    ctx.census, ctx.C, ctx.people, ctx.Pid, ctx.units, ctx.works, ctx.periods = census, C, people, Pid, units, works, periods
    ctx.inst, ctx.aff, ctx.pls, ctx.cwork = inst, aff, pls, collection_work_matcher(works)


def reviewed_inputs(ctx):
    """The verified yearly listings (listings/<school>/listings.json), the reviewed census overrides of the school
    (hierarchy/census-overrides.json) and the researched gap labs (hierarchy/<school>/gap-evidence.json), which add
    exclusions, identity and the collection person to the overrides."""
    HERE, school = ctx.here, ctx.school
    yearly = collections.defaultdict(list)  # listings/<school>/listings.json: verified yearly department listings (one row per person-year)
    lf = HERE / 'listings' / school / 'listings.json'
    for r in (read(lf) if lf.exists() else []):
        if not r.get('future_start_note') and r.get('sha256') and r.get('quote'):
            yearly[r['pi']].append(r)
    ov = read(HERE / 'hierarchy/census-overrides.json').get(school, {}) if (HERE / 'hierarchy/census-overrides.json').exists() else {}
    ge = {r['pi']: r for r in read(HERE / 'hierarchy' / school / 'gap-evidence.json')} if (HERE / 'hierarchy' / school / 'gap-evidence.json').exists() else {}
    for pi_, r in ge.items():  # researched gap labs: status, identity, the PI's collection person
        o = ov.setdefault(pi_, {})
        if r.get('status') == 'not_pi_in_window' and r.get('status_evidence'):
            o.setdefault('exclude', True); o.setdefault('why', 'Researched: not a PI at the school in 2016-2026 (gap-evidence.json): ' + str(r.get('notes') or '')[:200])
        idn = r.get('identity') or {}
        o['openalex'] = list(o.get('openalex') or []) + [a if a.startswith('http') else 'https://openalex.org/' + a for a in idn.get('openalex') or []]
        o['orcid'] = as_list(o.get('orcid')) + as_list(idn.get('orcid'))
        o['dblp'] = as_list(o.get('dblp')) + as_list(idn.get('dblp'))
        if r.get('collection_person_id') and not o.get('collection_person_id'):
            o['collection_person_id'] = r['collection_person_id']
    ctx.yearly, ctx.ov, ctx.ge = yearly, ov, ge


def merge_census_rows(census, ov, n):
    """The census rows that are PIs (is_pi, or a reviewed is_pi), grouped by person: census duplicate pairs (same DBLP
    PID, same collection person, the same name tokens) and same family name with a nickname-equal given name.
    Returns ({key: [rows]}, [[first name, merged name], ...])."""
    dblp_of = lambda x: as_list(x.get('dblp'))
    merged, first, by_family, nick_merges = collections.defaultdict(list), {}, collections.defaultdict(list), []
    for x in census:  # census duplicate pairs (one person listed twice): same DBLP PID or same collection person
        if not (x.get('is_pi') or (ov.get(x['name']) or {}).get('is_pi')) or x.get('not_faculty'):  # a reviewed is_pi wins
            continue
        nk = 'name:' + ' '.join(toks(x['name']))  # spelling variants of one name ("O’Toole" / "O'Toole") are one person too
        k = next((first[q] for q in dblp_of(x) + [x.get('collection_person_id'), nk] if q and q in first), None)
        t = toks(x['name'])
        if not k and len(t) >= 2:  # "Dan Klein" / "Daniel Klein", "David A. Wagner" / "David Wagner": same family name, nickname-equal given name
            k = next((k_ for g_, k_ in by_family[t[-1]] if g_ == t[0] or nick_ok(g_, t[0])), None)
            if k:
                n['census_rows_merged_by_nickname'] += 1; nick_merges.append([merged[k][0]['name'], x['name']])
        k = k or x['name']
        for q in dblp_of(x) + [x.get('collection_person_id'), nk]:
            if q:
                first.setdefault(q, k)
        if len(t) >= 2:
            by_family[t[-1]].append((t[0], k))
        merged[k].append(x)
    return merged, nick_merges


def choose_lab(x, units, Pid, ids, names):
    """The PI's lab (R-HIER-01, R-HIER-02): a census lab unit whose single leader is this PI and that is not a
    collective, else a new own lab (named after a proposed non-collective unit, else '<PI> group')."""
    lab = None
    collective = lambda nm_: bool(COLLECTIVE.search(nm_ or '')) and not re.search(r'\b(lab|laboratory|group)\b', nm_ or '', re.I)
    for lu in x.get('lab_units') or []:
        if isinstance(lu, str) and lu in units:
            u = units[lu]; leaders = [l if isinstance(l, str) else l.get('person') or l.get('id') or l.get('name') for l in u.get('leaders') or []]
            if len(leaders) == 1 and not collective(u['name']) and (leaders[0] in ids or Name(names).match(Pid[leaders[0]]['name'] if leaders[0] in Pid else leaders[0])):
                lab = dict(unitId=lu, name=u['name'], basis='single_leader_unit'); break
    if lab is None:
        prop = next((lu for lu in x.get('lab_units') or [] if isinstance(lu, dict) and not collective(lu.get('name'))), None)
        lab = dict(unitId=None, name=(prop or {}).get('name') or f"{x['name']} group", url=(prop or {}).get('url') or x.get('profile_url'),
                   basis='new_own_lab', evidence=(prop or {}).get('evidence') or x.get('pi_basis'),
                   collectives=[lu for lu in x.get('lab_units') or [] if isinstance(lu, str)])
    return lab


def pi_records(ctx):
    """One record per PI (pis.json): merged rows, reviewed corrections (census-overrides.json), identity, listings,
    periods and the lab; the reviewed exclusions are kept apart."""
    census, ov, yearly, Pid, units, periods, n = ctx.census, ctx.ov, ctx.yearly, ctx.Pid, ctx.units, ctx.periods, ctx.n
    dblp_of = lambda x: as_list(x.get('dblp'))
    pis = []
    merged, nick_merges = merge_census_rows(census, ov, n)
    excluded = []
    for group in merged.values():
        hit = next((ov[g['name']] for g in group if ov.get(g['name'], {}).get('exclude')), None)
        if hit:  # reviewed: no faculty appointment at the school in the window
            excluded.append(dict(pi=group[0]['name'], why=hit.get('why'))); continue
        x = dict(group[0]); x['aliases'] = list(dict.fromkeys(list(x.get('aliases') or []) + [g['name'] for g in group[1:]] + [a for g in group[1:] for a in g.get('aliases') or []]))
        x['sources'] = [s_ for g in group for s_ in g.get('sources') or []]; x['lab_units'] = [l for g in group for l in g.get('lab_units') or []]
        x['dblp'] = list(dict.fromkeys(q for g in group for q in dblp_of(g)))
        x['collection_person_id'] = next((g['collection_person_id'] for g in group if g.get('collection_person_id') in Pid), None)
        x['mergedCensusRows'] = [g['name'] for g in group[1:]]
        o = ov.get(x['name'], {})  # reviewed corrections: aliases, person, identity (hierarchy/census-overrides.json)
        if o.get('collection_person_id'):
            x['collection_person_id'] = o['collection_person_id']
        x['aliases'] = list(x.get('aliases') or []) + list(o.get('aliases') or [])
        x['dblp'] = list(dict.fromkeys(list(x['dblp']) + as_list(o.get('dblp'))))
        x['openalex'] = list(dict.fromkeys(as_list(x.get('openalex')) + as_list(o.get('openalex'))))
        x['orcid'] = list(dict.fromkeys(re.sub(r'^https?://orcid\.org/', '', z) for z in as_list(x.get('orcid')) + as_list(o.get('orcid'))))  # additions give one ORCID as a string
        ids = [i for i in [x.get('collection_person_id')] + list(x.get('collection_person_candidates') or []) if i and i in Pid][:1]
        names = [x['name']] + list(x.get('aliases') or []) + [Pid[i]['name'] for i in ids]
        listings = pi_listings(x, yearly, n)
        mine = pi_mine(periods, ids, x['name'])
        after_move = listings_after_move(listings, mine, o.get('periods'))  # stale listings after an evidenced move
        n['listing_years_after_move'] += len(after_move)
        lab = choose_lab(x, units, Pid, ids, names)
        pis.append(dict(pi=x['name'], personIds=ids, names=list(dict.fromkeys(names)), dblp=x['dblp'], reviewedOpenAlex=x['openalex'], orcid=x['orcid'],
                        notOpenAlex=list(o.get('not_openalex') or []),  # reviewed namesake author ids: never this PI
                        # reviewed mixed author ids (2026-10-29): OpenAlex records of another person that also hold some of the
                        # PI's works (Song Mei's Berkeley papers sit in five Chinese namesakes' records); such an id neither
                        # anchors nor blocks: each of its authorships needs per-work evidence (DBLP page, ORCID, advisee)
                        mixedOpenAlex=list(o.get('mixed_openalex') or []),
                        mergedCensusRows=x['mergedCensusRows'], rank=x.get('rank'), title=x.get('title_as_listed'),
                        departments=x.get('departments') or x.get('units') or [], piBasis=o.get('pi_basis') or x.get('pi_basis'), lab=lab,  # a reviewed basis (census-overrides.json) wins
                        periods=pi_periods(mine, o),  # collection periods + reviewed periods (census-overrides.json)
                        listings=[listings[y] for y in sorted(listings) if y not in after_move],
                        listingsAfterMove=[after_move[y] for y in sorted(after_move)]))
    n['pis_excluded_by_review'] = len(excluded)
    n['pis'] = len(pis); n['pis_without_person'] = sum(not p['personIds'] for p in pis)
    n['labs_reused'] = sum(p['lab']['unitId'] is not None for p in pis); n['labs_new'] = n['pis'] - n['labs_reused']
    ctx.pis, ctx.excluded, ctx.nick_merges = pis, excluded, nick_merges


def index_pis(ctx):
    """The PI tables the later stages look up: by name, by collection unit, name matchers, and by family name."""
    pis = ctx.pis
    pid0 = {p['pi']: p for p in pis}
    by_unit = collections.defaultdict(list)
    for p in pis:
        if p['lab']['unitId']:
            by_unit[p['lab']['unitId']].append(p['pi'])
    nm = {p['pi']: Name(p['names']) for p in pis}
    by_sur = collections.defaultdict(list)
    for p in pis:
        for f, l in nm[p['pi']].forms:
            by_sur[l].append(p['pi'])

    # an adviser field names a PI by full given name only through the PI's full-name forms (an 'H. Balakrishnan' alias of
    # Hamsa must not take 'Balakrishnan, Hari' theses, 2026-10-28); an initials-only field goes to no PI when another PI of
    # the school shares that family name and initial
    nm_full = {p['pi']: Name([x for x in p['names'] if len((toks(x) or [''])[0]) > 1] or p['names']) for p in pis}
    ctx.pid0, ctx.by_unit, ctx.nm, ctx.by_sur, ctx.nm_full = pid0, by_unit, nm, by_sur, nm_full
