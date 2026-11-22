"""The census: the build's inputs, the census rows merged into one record per PI, and each PI's lab.
R-HIER-01 (one own lab per PI; a census lab unit is reused only with this PI as its single leader), R-HIER-02 (collectives
are not labs: COLLECTIVE)."""
import collections, re

import atlas_paths as P  # data paths (DATA_FILES)
import census_overrides as CO  # reviewed overrides: shared file + an onboarding school's own

from .common import AFF, INST, as_list, collection_work_matcher, read
from .names import Name, literal_cjk_name, nick_ok, nosuffix, placeholder_name, toks
from .periods import listings_after_move, pi_listings, pi_mine, pi_periods

COLLECTIVE = re.compile(r'\b(cent(?:er|re)|initiative|consortium|program(?:me)?|project|cluster|institute)\b', re.I)  # not labs (owner, 2026-10-21)


def fold_dblp_ids(additions, dblp_ids):
    """Stage 5's DBLP ids (tools/dblp_ids_school.py) for reviewed census additions that carry none, the way tools/census_build.py folds
    them into listing rows: a hand row written before stage 5 ran ('dblp': []) otherwise never gets its id (UW 2026-11-22: Choi, Levine,
    Guestrin, Fox and nine more departed or adjunct PIs). An addition's own DBLP id or ORCID is never replaced."""
    out = []
    for a in additions:
        d_ = dblp_ids.get(a.get('name')) or {}
        if not a.get('dblp') and d_.get('pid'):
            a = dict(a, dblp=[d_['pid']], dblp_basis=d_.get('basis'),
                     dblp_evidence={k: d_[k] for k in ('url', 'dump', 'sha256', 'quote') if k in d_} or None,
                     orcid=a.get('orcid') or list(d_.get('orcid') or []))
        out.append(a)
    return out


def load(ctx):
    """The school's census (plus census/<school>-additions.json), its collection (a school's own collection.json.gz, else
    the site's), the faculty periods (collection + periods/<school>-faculty-periods.json), the charter's institution and
    affiliation pattern, the collection's person links and the collection-work matcher."""
    HERE, SITE, school = ctx.here, ctx.site, ctx.school
    cf = P.data('census-faculty-hierarchy.json', school, root=HERE)  # a school whose census path another chain owns (Berkeley) keeps its own
    census = read(cf if cf.exists() else P.data('census-faculty.json', school, root=HERE))
    census = census.get('faculty', census) if isinstance(census, dict) else census
    if P.data('census-additions.json', school, root=HERE).exists():  # listed faculty the census missed (tools/listed_not_in_census.py)
        census = list(census) + fold_dblp_ids(read(P.data('census-additions.json', school, root=HERE)),
                                              read(P.data('dblp-ids.json', school, root=HERE)) if P.data('dblp-ids.json', school, root=HERE).exists() else {})
    own_c = P.data('collection.json.gz', school, root=HERE)  # a school without a site collection (Berkeley) brings its own
    C = read(own_c if own_c.exists() else SITE / f'collection-{school}.json.gz')
    people = C['people'] if isinstance(C['people'], list) else list(C['people'].values())
    Pid = {p['id']: p for p in people}; units = {u['id']: u for u in C['units']}; works = C['works']
    periods = list(C.get('facultyPeriods') or [])
    pf = P.data('faculty-periods.json', school, root=HERE)
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
    lf = P.data('listings.json', school, root=HERE)
    for r in (read(lf) if lf.exists() else []):
        if not r.get('future_start_note') and r.get('sha256') and r.get('quote'):
            yearly[r['pi']].append(r)
    # R-PAP-37: the years each department's listing was captured and read (listings/<school>/coverage.json); a PI absent from a covered
    # year was dropped from that listing. Emeritus slots do not count (an emeritus page never lists the active faculty).
    cov_f = P.data('coverage.json', school, root=HERE)
    covered = {}  # {department: {years}}; only the per-department format (Michigan, Georgia Tech, UChicago); the per-person coverage files of the older schools say nothing about a department's years
    for dept, years_ in (read(cov_f) if cov_f.exists() else {}).items():
        if isinstance(years_, dict) and all(isinstance(v, dict) for v in years_.values()):
            covered[dept] = {int(y) for y, slots in years_.items() if any(str(v).startswith('ok') for k, v in slots.items() if 'emeritus' not in k.lower())}
    ctx.listing_covered = covered
    ge_f = P.data('gap-evidence.json', school, root=HERE)
    ov = CO.section(school, lambda n, s=None: P.data(n, s, root=HERE))
    ge = {r['pi']: r for r in read(ge_f)} if ge_f.exists() else {}
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
    aliases_path = P.data('census-name-aliases.json', school, root=HERE)
    ctx.native_pi_merges = (read(aliases_path) if aliases_path.exists() else {}).get('native_pi_merges', [])


def merge_census_rows(census, ov, n, reviewed_merges=()):
    """The census rows that are PIs (is_pi, or a reviewed is_pi), grouped by person: census duplicate pairs (same DBLP
    PID, same collection person, the same name tokens) and same family name with a nickname-equal given name.
    Returns ({key: [rows]}, [[first name, merged name], ...])."""
    dblp_of = lambda x: as_list(x.get('dblp'))
    canonical_for = {}
    present = {x['name'] for x in census
               if (x.get('is_pi') or (ov.get(x['name']) or {}).get('is_pi')) and not x.get('not_faculty')}
    for review in reviewed_merges:
        canonical, aliases = review.get('canonical'), review.get('aliases')
        evidence = review.get('evidence')
        if (not isinstance(canonical, str) or not isinstance(aliases, list) or not aliases
                or canonical in aliases or len(set(aliases)) != len(aliases)
                or not review.get('reviewed_by') or not review.get('why')
                or not isinstance(evidence, list) or not evidence
                or any(not isinstance(e, dict) or not e.get('url') or not e.get('quote')
                       or not re.fullmatch(r'[0-9a-f]{64}', str(e.get('sha256') or '')) for e in evidence)):
            raise ValueError('Native census merge requires an explicit canonical name, aliases, reviewer, reason and source evidence')
        for name in [canonical, *aliases]:
            if name not in present or name in canonical_for:
                raise ValueError('Missing or overlapping reviewed census merge name: ' + name)
            canonical_for[name] = canonical
    merged, first, by_family, nick_merges = collections.defaultdict(list), {}, collections.defaultdict(list), []
    for x in census:  # census duplicate pairs (one person listed twice): same DBLP PID or same collection person
        if not (x.get('is_pi') or (ov.get(x['name']) or {}).get('is_pi')) or x.get('not_faculty'):  # a reviewed is_pi wins
            continue
        t = toks(x['name'])
        personal = nosuffix(t)
        suffix = tuple(t[len(personal):])
        nk = 'name:' + ' '.join(t) if t else None  # an empty token set never identifies a person
        if literal_cjk_name(x['name']):
            # Same written CJK names can be different faculty. Only the same profile or an explicit person/PID joins rows.
            profile = (x.get('profile_url') or '').rstrip('/')
            nk = nk + ':profile:' + profile if profile else None
        reviewed_key = ('reviewed_person:' + canonical_for[x['name']]) if x['name'] in canonical_for else None
        anchors = [reviewed_key, *dblp_of(x), x.get('collection_person_id'), nk]
        k = next((first[q] for q in anchors if q and q in first), None)
        if not k and len(personal) >= 2:  # A generational suffix is not a family name; conflicting explicit generations stay separate.
            k = next((k_ for g_, k_, suffix_ in by_family[personal[-1]]
                      if (g_ == personal[0] or nick_ok(g_, personal[0]))
                      and not (suffix and suffix_ and suffix != suffix_)), None)
            if k:
                n['census_rows_merged_by_nickname'] += 1; nick_merges.append([merged[k][0]['name'], x['name']])
        if not k:
            k = x['name']
            if k in merged:
                k = (x['name'], len(merged))  # distinct source identities; display-name ambiguity is checked before indexing
        for q in anchors:
            if q:
                first.setdefault(q, k)
        if len(personal) >= 2:
            by_family[personal[-1]].append((personal[0], k, suffix))
        merged[k].append(x)
    for group in merged.values():
        canonical = {canonical_for[x['name']] for x in group if x['name'] in canonical_for}
        if len(canonical) > 1:
            raise ValueError('Conflicting source-reviewed census merge groups')
        if canonical:
            target = next(iter(canonical))
            group.sort(key=lambda x: x['name'] != target)
            n['census_rows_merged_by_source_review'] += sum(x['name'] != target for x in group)
    return merged, nick_merges


def reviewed_dblp_orcids(group, ov):
    """An opt-in reviewed inheritance policy; positive ORCIDs need their own source evidence."""
    reviews = [ov[g['name']]['dblp_orcid_review'] for g in group if 'dblp_orcid_review' in ov.get(g['name'], {})]
    if not reviews:
        return None
    policy = reviews[0]
    if any(r != policy for r in reviews[1:]):
        raise ValueError('Conflicting DBLP ORCID reviews for merged PI: ' + group[0]['name'])
    if not isinstance(policy, dict) or set(policy) != {'allowed', 'why', 'evidence'}:
        raise ValueError('DBLP ORCID review requires allowed, why and evidence: ' + group[0]['name'])
    allowed, evidence = policy['allowed'], policy['evidence']
    valid_id = lambda s: isinstance(s, str) and bool(re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]', s))
    if not isinstance(allowed, list) or not all(valid_id(s) for s in allowed) or len(set(allowed)) != len(allowed):
        raise ValueError('DBLP ORCID allowed values must be distinct bare ORCIDs: ' + group[0]['name'])
    if not isinstance(policy['why'], str) or not policy['why'].strip() or not isinstance(evidence, list):
        raise ValueError('DBLP ORCID review needs a reason and evidence list: ' + group[0]['name'])
    for e in evidence:
        if (not isinstance(e, dict) or set(e) != {'orcid', 'url', 'sha256', 'quote'} or e['orcid'] not in allowed
                or not isinstance(e['url'], str) or not e['url'].startswith(('https://', 'http://'))
                or not isinstance(e['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', e['sha256'])
                or not isinstance(e['quote'], str) or e['orcid'] not in e['quote']):
            raise ValueError('Invalid source-bound DBLP ORCID evidence: ' + group[0]['name'])
    if set(allowed) != {e['orcid'] for e in evidence}:
        raise ValueError('Every allowed DBLP ORCID needs its own source evidence: ' + group[0]['name'])
    return policy


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


def _reviewed_merge_person_ids(ctx, group, people):
    """Preserve IDs explicitly declared by a source-reviewed duplicate merge."""
    reviews = [r for r in getattr(ctx, 'native_pi_merges', [])
               if r.get('canonical') == group[0]['name'] and 'person_ids' in r]
    if not reviews:
        return None
    ids = reviews[0]['person_ids']
    expected = {g.get('collection_person_id') for g in group}
    if (len(reviews) != 1 or not isinstance(ids, list) or not ids
            or any(not isinstance(i, str) or not i for i in ids)
            or len(set(ids)) != len(ids) or set(ids) != expected
            or not expected <= people.keys()):
        raise ValueError('Reviewed merge person IDs must exactly match its existing census people')
    return list(ids)


def pi_records(ctx):
    """One record per PI (pis.json): merged rows, reviewed corrections (census-overrides.json), identity, listings,
    periods and the lab; the reviewed exclusions are kept apart."""
    census, ov, yearly, Pid, units, periods, n = ctx.census, ctx.ov, ctx.yearly, ctx.Pid, ctx.units, ctx.periods, ctx.n
    dblp_of = lambda x: as_list(x.get('dblp'))
    pis = []
    merged, nick_merges = merge_census_rows(census, ov, n, getattr(ctx, 'native_pi_merges', []))
    excluded = []
    for group in merged.values():
        hit = next((ov[g['name']] for g in group if ov.get(g['name'], {}).get('exclude')), None)
        if hit:  # reviewed: no faculty appointment at the school in the window
            excluded.append(dict(pi=group[0]['name'], why=hit.get('why'))); continue
        identity_hold = next((ov[g['name']] for g in group if ov.get(g['name'], {}).get('no_identity')
                              and ov[g['name']].get('why_no_identity')), None)
        orcid_review = reviewed_dblp_orcids(group, ov)
        x = dict(group[0]); x['aliases'] = list(dict.fromkeys(list(x.get('aliases') or []) + [g['name'] for g in group[1:]] + [a for g in group[1:] for a in g.get('aliases') or []]))
        x['sources'] = [s_ for g in group for s_ in g.get('sources') or []]; x['lab_units'] = [l for g in group for l in g.get('lab_units') or []]
        x['dblp'] = list(dict.fromkeys(q for g in group for q in dblp_of(g)))
        x['collection_person_id'] = next((g['collection_person_id'] for g in group if g.get('collection_person_id') in Pid), None)
        x['mergedCensusRows'] = [g['name'] for g in group[1:]]
        o = ov.get(x['name'], {})  # reviewed corrections: aliases, person, identity (hierarchy/census-overrides.json)
        shown = o.get('display_name')  # R-PAP-34: a reviewed real name for a placeholder census name ('Y Z' is Yang Zhang)
        if placeholder_name(x['name']) and not shown:  # a placeholder name anchors no paper: excluded unless review names the person
            excluded.append(dict(pi=x['name'], why='placeholder name (R-PAP-34): single letters only, no reviewed display_name')); continue
        if o.get('collection_person_id'):
            x['collection_person_id'] = o['collection_person_id']
        x['aliases'] = list(x.get('aliases') or []) + list(o.get('aliases') or [])
        x['dblp'] = list(dict.fromkeys(list(x['dblp']) + as_list(o.get('dblp'))))
        if o.get('dblp_drop'):  # a reviewed conflated namesake record (2026-11-19): the PI's real record is bound, this one mixes two people
            x['dblp'] = [q for q in x['dblp'] if q.rstrip('/') not in {d.rstrip('/') for d in as_list(o['dblp_drop'])}]
        x['openalex'] = list(dict.fromkeys(as_list(x.get('openalex')) + as_list(o.get('openalex'))))
        x['orcid'] = list(dict.fromkeys(re.sub(r'^https?://orcid\.org/', '', z) for z in as_list(x.get('orcid')) + as_list(o.get('orcid'))))  # additions give one ORCID as a string
        rejected_orcids = {re.sub(r'^https?://orcid\.org/', '', z).rstrip('/') for g in group
                           for z in as_list(ov.get(g['name'], {}).get('orcid_drop'))}
        x['orcid'] = [z for z in x['orcid'] if z.rstrip('/') not in rejected_orcids]
        ids = _reviewed_merge_person_ids(ctx, group, Pid)
        if ids is None:
            ids = [i for i in [x.get('collection_person_id')] + list(x.get('collection_person_candidates') or []) if i and i in Pid][:1]
        names = ([shown] if shown else []) + [x['name']] + list(x.get('aliases') or []) + [Pid[i]['name'] for i in ids]
        listings = pi_listings(x, yearly, n)
        mine = pi_mine(periods, ids, x['name'])
        after_move = listings_after_move(listings, mine, o.get('periods'))  # stale listings after an evidenced move
        n['listing_years_after_move'] += len(after_move)
        lab = choose_lab(x, units, Pid, ids, names)
        if shown and lab.get('name') == f"{x['name']} group":
            lab['name'] = f'{shown} group'
        pis.append(dict(pi=shown or x['name'], personIds=ids, names=list(dict.fromkeys(names)), dblp=x['dblp'], reviewedOpenAlex=x['openalex'], orcid=x['orcid'],
                        **({'identityHold': dict(status='reviewed_no_identity', reason=identity_hold['why_no_identity'])}
                           if identity_hold else {}),
                        **({'dblpOrcidReview': orcid_review} if orcid_review is not None else {}),
                        notOpenAlex=list(o.get('not_openalex') or []),  # reviewed namesake author ids: never this PI
                        # reviewed mixed author ids (2026-10-29): OpenAlex records of another person that also hold some of the
                        # PI's works (Song Mei's Berkeley papers sit in five Chinese namesakes' records); such an id neither
                        # anchors nor blocks: each of its authorships needs per-work evidence (DBLP page, ORCID, advisee)
                        mixedOpenAlex=list(o.get('mixed_openalex') or []),
                        **({'censusName': x['name'], 'displayNameBasis': o.get('why_display_name')} if shown else {}),
                        # reviewed blocked clusters (R-PAP-32, 2026-11-05): a namesake's works that sit on the PI's DBLP person page under no author id
                        blockedClusters=list(o.get('blocked_clusters') or []),
                        notPapers=list(o.get('not_papers') or []),   # R-PAP-39: reviewed records that are no papers
                        mergedCensusRows=x['mergedCensusRows'], rank=x.get('rank'), title=x.get('title_as_listed'),
                        departments=x.get('departments') or x.get('units') or [], piBasis=o.get('pi_basis') or x.get('pi_basis'), lab=lab,  # a reviewed basis (census-overrides.json) wins
                        periods=pi_periods(mine, o, x['name']),  # collection periods + reviewed periods (census-overrides.json)
                        listings=[listings[y] for y in sorted(listings) if y not in after_move],
                        listingsAfterMove=[after_move[y] for y in sorted(after_move)]))
    duplicate_names = [name for name, count in collections.Counter(p['pi'] for p in pis).items() if count > 1]
    if duplicate_names:
        raise ValueError('Distinct PI identities need reviewed unique display names before indexing: ' + ', '.join(duplicate_names))
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
    by_sur, by_mono = collections.defaultdict(list), collections.defaultdict(list)
    for p in pis:
        for literal in nm[p['pi']].mono:
            by_mono[literal].append(p['pi'])
        for f, l in nm[p['pi']].forms:
            by_sur[l].append(p['pi'])

    # an adviser field names a PI by full given name only through the PI's full-name forms (an 'H. Balakrishnan' alias of
    # Hamsa must not take 'Balakrishnan, Hari' theses, 2026-10-28); an initials-only field goes to no PI when another PI of
    # the school shares that family name and initial
    nm_full = {p['pi']: Name([x for x in p['names'] if len((toks(x) or [''])[0]) > 1] or p['names']) for p in pis}
    ctx.pid0, ctx.by_unit, ctx.nm, ctx.by_sur, ctx.by_mono, ctx.nm_full = pid0, by_unit, nm, by_sur, by_mono, nm_full


def reviewed_name_pairs(school):
    """The school's reviewed (name_a, name_b) spellings of one person (census-name-aliases.json; census_build validates them)."""
    path = P.data('census-name-aliases.json', school)
    doc = (read(path) if path.exists() else {}) or {}
    return [(r['name_a'], r['name_b']) for r in doc.get('rows') or [] if isinstance(r, dict) and r.get('name_a') and r.get('name_b')]
