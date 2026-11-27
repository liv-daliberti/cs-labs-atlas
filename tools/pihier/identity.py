"""Identity: is the authorship that matches the PI's name the PI? The anchors (the PI's DBLP person page from the cached
lists and the DBLP dump, the DBLP-verified collection works, the PI's institutional and lab publication lists, reviewed
OpenAlex ids, ORCIDs, advisees as co-authors) and the authorships of the sweep and of pi-works.sqlite matched to PIs.
R-PAP-04 (the order of identities), R-PAP-05 (the DBLP dump), R-PAP-06 (mixed ids), R-PAP-07 (initials), R-PAP-24 (page 1
for DBLP-anchored works)."""
import collections, gzip, html, json, re, sqlite3, zlib

import atlas_paths as P  # every path in one place
from .common import DBLP, NOT_PAPERS, accepted_additions, as_list, ndoi, norm_title, read, school_scope_work, sweep_works
from .names import han_reading, tie_for_pi, Name, all_initials, byline_name, clean_person_name, full_pair, given_conflict, middle_conflict, name_conflict, name_toks, names_full_form, nosuffix, toks
from . import primary_affiliations, reviewed_claims
from .periods import before_window
from .students import (ADV_RX, RESEARCHED_FILES, advising_label, dspace_advisors, named_advisers, own_roster_entry,
                       relation_is_weak, relation_names_other_adviser, renamed_pis)

DUMP_PERSONS = None  # hierarchy/dblp-dump-persons.json.gz, read once per process

# These old, reviewed relationship-basis statements predate the explicit relationship enum.
# They are finite prior source decisions, not a rule that an owned Students page implies advising.
LEGACY_ADVISER_BASES = {
    'PI-owned personally named roster',
    'PI personal Students and Postdoctoral Fellows; explicit dates and full co-adviser statements',
}
LEGACY_CURRENT_STUDENTS_BASIS = re.compile(
    r'PI-owned current Students roster; source explicitly names [^;\n]+ appointment, no doctoral inference')
ADVISER_RELATIONS = {'academic_advising', 'researched_advising', 'source_advising_context',
                     'pi_basis_advising', 'academic_adviser', 'thesis_adviser', 'phd_advising', 'research_advising'}
ACADEMIC_ADVISER_LABEL = re.compile(r'\b(?:academic|program|major)\s+advis[oe]r', re.I)
MY_ADVISEE = re.compile(r'\bmy\s+(?:(?:former|current|ph\.?d\.?|doctoral|master\x27?s?|undergraduate|graduate)\s+)*(?:students?|advisees?|supervisees?)\b', re.I)


def _adviser_source_key(source):
    """No URL/hash/quote aliasing: a source decision applies only to its exact native preimage."""
    if (source.get('url') and re.fullmatch(r'[0-9a-f]{64}(?:,[0-9a-f]{64})*', str(source.get('sha256') or ''))
            and isinstance(source.get('quote'), str) and source['quote'].strip()):
        return source['url'], source['sha256'], source['quote']
    return None


def adviser_source_claims(ctx):
    """Recover reviewed/contextual advising omitted from compiled relations, without changing members.

    Keys bind PI, literal member name and the exact source tuple. Explicit membership wins for the
    same key. Unknown historical context stays unavailable; a degree or relationship type is no proof.
    """
    claims = {}
    pis = {p['pi']: p for p in ctx.pis}
    renames = renamed_pis(ctx.pis, ctx.school, ctx.here)

    def add(pi, name, source, basis):
        key = _adviser_source_key(source)
        if pi in pis and name and key:
            key = pi, clean_person_name(name), key
            if claims.get(key) != 'explicit_reviewed_membership':
                claims[key] = basis

    groups = list((getattr(ctx, 'ge', {}) or {}).items())
    chair_rows = []
    for filename in RESEARCHED_FILES:
        path = P.data(filename, ctx.school, root=ctx.here)
        if path.exists():
            records = read(path)
            groups += [(r['pi'], r) for r in records]
            if filename == 'thesis-committee-chair-evidence.json':
                chair_rows += [(r['pi'], s) for r in records for s in r.get('students') or []]
    rows, owned_bodies = [], set()
    for pi, group in groups:
        pi = renames.get(pi, pi)
        rows += [(pi, s) for s in group.get('students') or []]
        if pi not in pis:
            continue
        context = group.get('pi_context_evidence') or {}
        official, owned = context.get('official_role') or {}, context.get('owned_role') or {}
        outbound = context.get('official_outbound') or context.get('ownership') or {}
        literal = context.get('literal_official_href') or outbound.get('literal_href')
        names = pis[pi].get('names') or [pi]
        # A finite, already reviewed literal ownership chain; never normalize URLs or infer redirects.
        if (_adviser_source_key(official) and _adviser_source_key(owned) and _adviser_source_key(outbound)
                and official['url'] == outbound['url'] == context.get('profile')
                and official['sha256'] == outbound['sha256']
                and names_full_form(official['quote'], names)
                and literal == context.get('home') == owned['url'] and literal in outbound['quote']
                and (names_full_form(owned['quote'], names) or context.get('owned_named_PI_alias') in names)):
            owned_bodies.add((pi, owned['url'], owned['sha256']))
    for pi, row in chair_rows:
        pi = renames.get(pi, pi)
        note = row.get('note') or ''
        chair = re.search(r'\bCommittee\s+Chair\s*:?\s*([^|;\n]+)', row.get('quote') or '', re.I)
        if (pi in pis and row.get('relationship') != 'membership' and chair
                and 'R-STU-23' in note and re.search(r'Approved by (?:the )?owner', note, re.I)
                and names_full_form(chair.group(1), pis[pi].get('names') or [pi])):
            add(pi, row.get('name'), row, 'reviewed_R_STU23_committee_chair')
    rows += [(s['pi'], s) for s in accepted_additions(ctx.school, 'students', ctx.here, collections.Counter())]
    for pi, row in rows:
        pi = renames.get(pi, pi)
        if pi not in pis:
            continue
        names = pis[pi].get('names') or [pi]
        relationship = row.get('relationship')
        if relationship == 'membership':
            add(pi, row.get('name'), row, 'explicit_reviewed_membership')
        elif relationship == 'advising':
            add(pi, row.get('name'), row, 'explicit_reviewed_advising')
        elif relationship is None and row.get('reviewed') is True:
            owner = row.get('source_owner_PI')
            role_source = row.get('PI_role_source') or {}
            section = row.get('section') or ''
            if owner in names and _adviser_source_key(role_source) and names_full_form(role_source['quote'], names):
                if re.search(r'\badvisees\b|\bsupervised students\b', section, re.I):
                    add(pi, row.get('name'), row, 'reviewed_owned_advising_section')
                elif (row.get('relationship_basis') in LEGACY_ADVISER_BASES
                      or LEGACY_CURRENT_STUDENTS_BASIS.fullmatch(row.get('relationship_basis') or '')):
                    add(pi, row.get('name'), row, 'reviewed_legacy_relationship_basis')
        if (relationship is None and (row.get('reviewed') is True or (row.get('reviewed_by') and row.get('reviewed_on')))
                and (pi, row.get('url'), row.get('sha256')) in owned_bodies):
            quote = row.get('quote') or ''
            name = row.get('name') or ''
            immediate = any(re.match(re.escape(name) + r'(?!\w)', quote[m.end():].lstrip(' :,-'), re.I)
                            for m in MY_ADVISEE.finditer(quote)) if name else False
            if immediate or MY_ADVISEE.fullmatch((row.get('section') or '').strip(' :')):
                add(pi, name, row, 'reviewed_owned_first_person_advising')

    member_ids, member_names = collections.defaultdict(set), collections.defaultdict(set)
    for pi in pis:
        for member in ctx.stu[pi].values():
            member_ids[member['person']].add(pi)
            for name in [member['name']] + list(member.get('aliases') or []):
                member_names[clean_person_name(name)].add(pi)
    for person in getattr(ctx, 'people', []):
        for context in person.get('contexts') or []:
            if context.get('type') not in ADVISER_RELATIONS:
                continue
            advisers = [context.get('advisorName'), context.get('advisor')] + list(context.get('advisors') or [])
            ids = {context.get('advisorPersonId'), context.get('advisorPerson')} - {None}
            candidates = member_ids[person['id']] | member_names[clean_person_name(person['name'])]
            for pi in sorted(candidates):
                p = pis[pi]
                if ids & set(p.get('personIds') or []) or any(isinstance(a, str) and names_full_form(a, p.get('names') or [pi]) for a in advisers):
                    for source in context.get('sources') or []:
                        if (not ACADEMIC_ADVISER_LABEL.search(source.get('quote') or '')
                                and names_full_form(source.get('quote') or '', p.get('names') or [pi])):
                            add(pi, person['name'], source, 'named_adviser_collection_context')
    for pi, p in pis.items():
        basis = p.get('piBasis') or {}
        if basis.get('kind') == 'advises_phd':
            for member in ctx.stu[pi].values():
                for relation in member.get('relations') or []:
                    if relation.get('type') == 'pi_basis_advising':
                        add(pi, member['name'], basis, 'reviewed_PI_advises_phd_basis')
    return claims


_TITLE_DOTS = re.compile(r'\b(Prof|Dr|Mr|Ms|Mrs|Assoc|Asst|[A-Z])\.')
CHAIR_ADVISER = re.compile(r'\b(?:Dr|Prof)\.?\s+([^,;|\n]{3,60}?),\s*(?:(?!Dr\b|Prof\b)[^,;|\n]{1,40},\s*)?(?:Co-?)?(?:Chair,\s*)?(?:Co-?)?Advis[oe]rs?\b')


def _undot_titles(text):
    """Drop the period after a title or a single-letter initial so an adviser field is not cut inside the name."""
    return _TITLE_DOTS.sub(r'\1', text)


def adviser_anchor_basis(pi, member, pi_names, claims):
    """R-PAP-04/11/12 require a stated advisee, not a degree-labelled lab member.

    This is advisory-anchor eligibility only, not a person, membership or paper rejection.
    One genuine research-advising episode suffices; unrelated membership/weak episodes remain intact.
    """
    names = [member['name']] + list(member.get('aliases') or [])
    for relation in member.get('relations') or []:
        if (relation.get('type') not in ADVISER_RELATIONS or relation.get('weak')
                or relation.get('role') == 'Postdoctoral Faculty Sponsor'
                or relation_is_weak(relation, names) or relation_names_other_adviser(relation, pi_names)):
            continue
        for source in relation.get('sources') or []:
            key = _adviser_source_key(source)
            if not key:
                continue
            bases = {claims.get((pi, clean_person_name(name), key)) for name in names} - {None}
            if 'explicit_reviewed_membership' in bases:
                continue
            quote = source['quote']
            if advising_label(quote, names) == 'Postdoctoral Faculty Sponsor':
                continue
            if own_roster_entry(quote, names, pi_names) in {'names_other', 'unknown'}:
                continue
            if bases:
                return dict(basis=sorted(bases)[0], source=key)
            if source.get('names_pi') is False:
                continue
            named = named_advisers(quote) if not ACADEMIC_ADVISER_LABEL.search(quote) else ''
            if names_full_form(named, pi_names) or any(names_full_form(n, pi_names) for n in dspace_advisors(quote)):
                return dict(basis='literal_named_adviser', source=key)
            # Figshare's labelled adviser field, and an explicitly named advising sentence.
            fields = re.findall(r'"name"\s*:\s*"Advis[oe]r(?:\(s\))?"\s*,\s*"value"\s*:\s*"([^"]+)"', quote, re.I)
            undotted = _undot_titles(quote)  # 'Prof. Ümit V. Çatalyürek' must not end the field at its first period
            fields += re.findall(r'\b(?:co[- ]?)?(?:advised|supervised)\s+(?:by|with)\s+([^.;\n]{3,160})', undotted, re.I)
            fields += re.findall(r'\b(?:Ph\.?D\.?|doctoral|master\x27?s?)\s+student\s+of\s+([^.;\n]{3,160})', undotted, re.I)
            if '|' in quote and not ACADEMIC_ADVISER_LABEL.search(quote):  # flattened DSpace 'Advisor(s) A, B; C, D | Date ...'
                fields += re.findall(r'\bAdvis[oe]rs?(?:\(s\))?\s*:?\s*([^|\n]+)', quote, re.I)
            if not ACADEMIC_ADVISER_LABEL.search(quote):  # thesis-committee line 'Dr. A B, CoC, Chair, Advisor'
                fields += CHAIR_ADVISER.findall(quote)
            if not ACADEMIC_ADVISER_LABEL.search(quote):
                fields += [match.group(1) for rx in ADV_RX for match in rx.finditer(quote)]
            if any(names_full_form(value, pi_names) for value in fields):
                return dict(basis='literal_named_supervision', source=key)
    return None


def apply_cached_lists(pis, pubs, dblp_doi, dblp_title, n, excluded_pids=None):
    """R-PAP-05 with the pre-protocol schools' cached DBLP publication lists (`pubs`: key -> record with authors {pid:
    name}): a census DBLP id whose names never carry the PI's name is dropped; a PI without one takes the one DBLP person
    of exactly that name; every record of the PI's ids anchors by DOI and title."""
    pis = [p for p in pis if not p.get('identityHold')]
    excluded_pids = excluded_pids or {}
    for p in pis:
        p['dblp'] = [q for q in p['dblp'] if q.rstrip('/') not in excluded_pids.get(p['pi'], set())]
    by_dname = collections.defaultdict(set)  # a PI without a census DBLP id: the one DBLP person of exactly that name, if unique
    for rec in pubs.values():
        for q, dn in (rec.get('authors') or {}).items():
            if not re.search(r'\d{4}$', dn or ''):
                by_dname[' '.join(toks(dn))].add(q)
    dname = collections.defaultdict(set)
    for rec in pubs.values():
        for q, dn in (rec.get('authors') or {}).items():
            dname[q].add(re.sub(r'\s+\d{4}$', '', dn or ''))
    n['dblp_ids_dropped_name_mismatch'] = 0
    for p in pis:  # a census DBLP id whose person never carries the PI's name is someone else's (e.g. 'Jun Zhu' for Jun-Yan Zhu)
        keep = [q for q in p['dblp'] if q not in dname or any((not name_conflict(p['names'], dn) and not middle_conflict(p['names'], dn)) or han_reading(p['names'], dn) for dn in dname[q])]
        if len(keep) < len(p['dblp']):
            n['dblp_ids_dropped_name_mismatch'] += len(p['dblp']) - len(keep); p['dblpDropped'] = sorted(set(p['dblp']) - set(keep)); p['dblp'] = keep
    for p in pis:
        if not p['dblp']:
            c_ = {q for n_ in p['names'] for q in by_dname.get(' '.join(toks(n_)), set())
                  if q.rstrip('/') not in excluded_pids.get(p['pi'], set())}
            if len(c_) == 1:
                p['dblp'] = sorted(c_); p['dblpBasis'] = 'unique DBLP person of that exact name among the cached publication co-authors'
    owner = collections.defaultdict(list)
    for p in pis:
        for q in p['dblp']:
            owner[q].append(p['pi'])
    for rec in pubs.values():
        for q in rec.get('authors') or {}:
            for pi in owner.get(q, []):
                if rec.get('doi'):
                    dblp_doi[pi].add(ndoi(rec['doi']))
                if title_key := norm_title((rec.get('title') or '').rstrip('.')):
                    dblp_title[pi][title_key] = rec.get('year')


NAME_ONLY_MIN_COLLEAGUE_RECORDS = 3  # 2016-2026 records a name-only DBLP record must share with the school's own PIs


def school_signal(rec, school):
    """The school's own mark on a DBLP person record (2026-11-19, namesake audit): an affiliation note that matches the charter's
    affiliation regex, or a URL on one of the school's web domains. None when the record carries neither."""
    if not school:
        return None
    import school_config as S  # local: the tests that never name a school need no charter
    try:
        rx, cfg = S.aff_rx(school), S.get(school)
    except KeyError:
        return None
    doms = [d.lower() for d in (cfg.get('web') or {}).get('domains') or []]
    excl = [d.lower() for d in (cfg.get('web') or {}).get('excluded_hosts') or []]
    note = next((a for a in rec.get('affiliations') or [] if rx.search(a)), None)
    if note:
        return ('affiliation', note)
    for u in rec.get('urls') or []:
        h = re.sub(r'^https?://', '', u).split('/')[0].split(':')[0].lower()
        if any(h == d or h.endswith('.' + d) for d in doms) and not any(h == x or h.endswith('.' + x) for x in excl):
            return ('homepage', u)
    return None


def colleague_records(rec, colleague_names, lo=2016, hi=2026):
    """Records of a DBLP person (2016-2026) whose author list also names one of the school's other PIs (their DBLP name strings)."""
    own = set(rec.get('names') or [])
    k = 0
    for r_ in rec.get('pubs') or []:
        y = r_.get('year')
        if y is None or not (lo <= int(y) <= hi):
            continue
        if any((a[0] if isinstance(a, (list, tuple)) else a) in colleague_names and (a[0] if isinstance(a, (list, tuple)) else a) not in own
               for a in r_.get('authors') or []):
            k += 1
    return k


def apply_dump(pis, dump, dblp_doi, dblp_title, n, school=None, excluded_pids=None, excluded_orcids=None):
    """R-PAP-05 with DBLP's own dump (`dump`: hierarchy/dblp-dump-persons.json.gz, {persons, by_name}): name conflicts
    drop an id, a PI still without one takes the unique person of exactly that name (no disambiguation record), every
    record anchors by DOI and title, and the person's ORCIDs join the PI's."""
    pis = [p for p in pis if not p.get('identityHold')]
    excluded_pids = excluded_pids or {}
    excluded_orcids = excluded_orcids or {}
    for p in pis:
        p['dblp'] = [q for q in p['dblp'] if q.rstrip('/') not in excluded_pids.get(p['pi'], set())]
        if excluded_orcids.get(p['pi']):
            p['orcid'] = [q for q in p.get('orcid') or [] if re.sub(r'^https?://orcid\.org/', '', q).rstrip('/') not in excluded_orcids[p['pi']]]
    DP, DN = dump['persons'], dump['by_name']
    n.setdefault('dblp_ids_dropped_name_mismatch', 0)  # report.schema requires the counter even when nothing is dropped (protocol schools skip apply_cached_lists)
    for p in pis:
        keep = [q for q in p['dblp'] if q not in DP or any((not name_conflict(p['names'], re.sub(r'\s+\d{4}$', '', dn)) and not middle_conflict(p['names'], re.sub(r'\s+\d{4}$', '', dn))) or han_reading(p['names'], dn) for dn in DP[q]['names'])]
        if len(keep) < len(p['dblp']):
            n['dblp_ids_dropped_name_mismatch'] += len(p['dblp']) - len(keep)
            p['dblpDropped'] = sorted(set(p.get('dblpDropped') or []) | (set(p['dblp']) - set(keep))); p['dblp'] = keep
    for p in pis:  # a Han-only PI matches Latin bylines under the name its bound DBLP record carries (a pinyin reading of the listed name; never invented)
        if p['dblp'] and p['names'] and all(not re.search('[A-Za-z]', nm_) for nm_ in p['names']):
            forms = [re.sub(r'\s+\d{4}$', '', dn) for q in p['dblp'] if q in DP for dn in DP[q]['names']]
            forms = [f for f in dict.fromkeys(forms) if han_reading(p['names'], f) and len(f.split()) >= 2]
            if forms:
                p['latinFromDblp'] = forms
                p['names'] = list(p['names']) + forms
                n['han_pis_latin_from_dblp'] = n.get('han_pis_latin_from_dblp', 0) + 1
    # A name alone never binds a DBLP record (2026-11-19, namesake audit): 'unique' only means no other record carries the exact
    # token string, so 'Rajeev Ram' (one 2016 paper, no affiliation) hid 'Rajeev J. Ram' (the MIT professor). The record must show the
    # school (affiliation note or URL on a school domain) or share >= 3 2016-2026 records with the school's other PIs.
    colleagues = {nm for p in pis if not p.get('dblpBasis') for q in p['dblp'] for nm in (DP.get(q) or {}).get('names') or []}
    n.setdefault('dblp_name_only_held', 0)
    CACHED = 'unique DBLP person of that exact name among the cached publication co-authors'
    for p in pis:  # the cached-list rule is a name-only bind too: it needs the same signal, read from the person's dump record
        if p.get('dblpBasis') == CACHED and p['dblp'] and school:
            q = p['dblp'][0]
            sig = school_signal(DP[q], school) if q in DP else None
            if sig:
                p['dblpSignal'] = dict(kind=sig[0], quote=sig[1])
            elif q in DP and (k_ := colleague_records(DP[q], colleagues)) >= NAME_ONLY_MIN_COLLEAGUE_RECORDS:
                p['dblpSignal'] = dict(kind='colleague_records', quote=f"{k_} 2016-2026 records co-written with the school's other PIs")
            else:
                p['dblpHeld'] = [dict(pid=q, why='name only: the record carries no school affiliation or homepage and fewer than '
                                      f'{NAME_ONLY_MIN_COLLEAGUE_RECORDS} records with the school\'s other PIs'
                                      + ('' if q in DP else ' (the person is not in the DBLP dump)'))]
                p['dblp'] = []; p.pop('dblpBasis')
                dblp_doi[p['pi']].clear(); dblp_title[p['pi']].clear()  # the namesake's cached records anchored nothing of the PI's
                n['dblp_name_only_held'] += 1
    for p in pis:
        if not p['dblp']:
            c_ = {q for n_ in p['names'] for q in DN.get(' '.join(toks(n_)), [])
                  if q.rstrip('/') not in excluded_pids.get(p['pi'], set())}
            if len(c_) == 1 and not any(DP[q].get('disambiguation') for q in c_):
                q = next(iter(c_))
                sig = school_signal(DP[q], school) if school else ('unchecked', None)
                if sig:
                    signal = None if sig[0] == 'unchecked' else dict(kind=sig[0], quote=sig[1])
                elif (k_ := colleague_records(DP[q], colleagues)) >= NAME_ONLY_MIN_COLLEAGUE_RECORDS:
                    signal = dict(kind='colleague_records', quote=f"{k_} 2016-2026 records co-written with the school's other PIs")
                else:
                    p['dblpHeld'] = [dict(pid=q, why='name only: the record carries no school affiliation or homepage and fewer than '
                                          f'{NAME_ONLY_MIN_COLLEAGUE_RECORDS} records with the school\'s other PIs')]
                    n['dblp_name_only_held'] += 1
                    continue
                p['dblp'] = [q]; p['dblpBasis'] = 'unique DBLP person of that exact name in the DBLP dump'; n['dblp_ids_from_dump_name'] += 1
                if signal:
                    p['dblpSignal'] = signal
    for p in pis:
        for q in p['dblp']:
            rec_ = DP.get(q)
            if not rec_:
                continue
            k0 = len(dblp_title[p['pi']])
            for r_ in rec_['pubs']:
                for d_ in r_.get('dois') or []:
                    dblp_doi[p['pi']].add(ndoi(d_))
                t_ = norm_title(html.unescape(r_.get('title') or '').rstrip('.'))
                if t_:
                    dblp_title[p['pi']].setdefault(t_, r_.get('year'))
            n['dblp_dump_titles_added'] += len(dblp_title[p['pi']]) - k0
            candidates = [o_ for o_ in rec_.get('orcid') or []
                          if re.sub(r'^https?://orcid\.org/', '', o_).rstrip('/') not in excluded_orcids.get(p['pi'], set())]
            policy = p.get('dblpOrcidReview')
            if policy is not None:
                prior = set(p.get('dblpOrcidsWithheld') or [])
                withheld = {o_ for o_ in candidates if o_ not in policy['allowed'] and o_ not in p['orcid']}
                if withheld:
                    p['dblpOrcidsWithheld'] = sorted(prior | withheld)
                    n['dblp_orcids_withheld_by_review'] += len(withheld - prior)
                candidates = [o_ for o_ in candidates if o_ in policy['allowed']]
            new_orcid = [o_ for o_ in candidates if o_ not in p['orcid']]
            if new_orcid:
                p['orcid'] = list(p['orcid']) + new_orcid; p['orcidFromDblp'] = new_orcid; n['pis_orcid_from_dblp'] += 1


def anchors(ctx):
    """The identity anchors of every PI: verified collection works, DBLP DOIs and titles, the PI's own and lab
    publication lists, the lab's advisee names."""
    reviewed_claims.prepare(ctx)
    HERE, school, pis, pls, stu, n = ctx.here, ctx.school, ctx.pis, ctx.pls, ctx.stu, ctx.n
    n['pis_with_reviewed_identity_hold'] = sum(bool(p.get('identityHold')) for p in pis)
    # identity anchors: the PI's own DBLP publication list, the PI's DBLP-verified collection works, a stated advisee as co-author
    verified = {p['pi']: {l['work'] for i in p['personIds'] for l in pls[i]
                           if l.get('status') == 'verified' and l.get('role', 'author') == 'author'
                           and not reviewed_claims.excluded(ctx, p['pi'], dict(ctx.works.get(l['work']) or {}, work=l['work']))} for p in pis}
    dblp_doi, dblp_title = collections.defaultdict(set), collections.defaultdict(dict)
    overrides = getattr(ctx, 'ov', {})
    excluded_pids = {p['pi']: {q.rstrip('/') for name in [p['pi'], p.get('censusName'), *p['names']]
                              for q in as_list(overrides.get(name, {}).get('dblp_drop'))} for p in pis}
    excluded_orcids = {p['pi']: {re.sub(r'^https?://orcid\.org/', '', q).rstrip('/')
                                for name in [p['pi'], p.get('censusName'), *p['names']]
                                for q in as_list(overrides.get(name, {}).get('orcid_drop'))} for p in pis}
    dp = P.archive_sweep(DBLP.get(school, '')) / 'raw/dblp_pubs.json.gz'
    own_pubs = P.data('dblp_pubs.json.gz', school, root=HERE)
    if own_pubs.exists():  # Princeton: converted from the lab records' cached DBLP answers
        dp = own_pubs
    if dp.exists() and dp.name == 'dblp_pubs.json.gz' and (DBLP.get(school) or dp == own_pubs):   # (was: 'hierarchy' in str(dp), which the school placement breaks)
        pubs = read(dp)['pubs']
        apply_cached_lists(pis, pubs, dblp_doi, dblp_title, n, excluded_pids=excluded_pids)
    # the PI's full DBLP person page from DBLP's own dump (tools/dblp_dump_persons.py -> hierarchy/dblp-dump-persons.json.gz;
    # 2026-10-29): the cached lists above hold only what the census queries returned, so a PI found as a co-author there
    # (Song Mei: 13 of 96 records) or added to the census later had a partial or empty list. Every record of the PI's
    # DBLP person anchors identity by DOI or title, as the cached lists do; a PI still without a DBLP id takes the one
    # person record of exactly that name in the dump when no other record carries the name (no homonyms); a census id
    # whose dump names never carry the PI's name is dropped as with the cached lists. ORCIDs on the person record (DBLP's
    # curated person links) join the PI's ORCIDs.
    dd_f = P.data('dblp-dump-persons.json.gz', root=HERE)
    if dd_f.exists():
        global DUMP_PERSONS
        if DUMP_PERSONS is None:
            DUMP_PERSONS = read(dd_f)
    dd_s = P.data('dblp-dump-persons-school.json.gz', school, root=HERE)  # an onboarding school's own persons (tools/dblp_dump_persons.py <key>)
    dump = None
    if dd_f.exists() or dd_s.exists():
        dump = DUMP_PERSONS if dd_f.exists() else {'persons': {}, 'by_name': {}}
        if dd_s.exists():
            own = read(dd_s)
            dump = dict(dump, persons={**dump.get('persons', {}), **own['persons']},
                        by_name={k: sorted(set(dump.get('by_name', {}).get(k, [])) | set(own['by_name'].get(k, []))) for k in {*dump.get('by_name', {}), *own['by_name']}})
        apply_dump(pis, dump, dblp_doi, dblp_title, n, school=school, excluded_pids=excluded_pids, excluded_orcids=excluded_orcids)
        if any(p.get('latinFromDblp') for p in pis) and getattr(ctx, 'nm', None) is not None:
            from . import census as _census  # Han-only PIs gained the Latin form of their bound DBLP record: rebuild the byline matchers
            _census.index_pis(ctx)
    # Venue dates, author counts and page filters need the same school-augmented records.
    # Keep this per build; the shared read-once cache must not absorb school-local records.
    ctx.dblp_persons = dump
    n['pis_with_dblp_list'] = sum(bool(dblp_title[p['pi']]) for p in pis)
    own_list = collections.defaultdict(dict)  # the PI's own institutional publication list (hierarchy/<school>/pi-publication-lists.json)
    pl_f = P.data('pi-publication-lists.json', school, root=HERE)
    for pi_, rows_ in (read(pl_f) if pl_f.exists() else {}).items():
        for r_ in rows_:
            if title_key := norm_title(r_.get('title')):
                own_list[pi_][title_key] = r_.get('year')
    n['pis_with_own_publication_list'] = sum(bool(own_list[p['pi']]) for p in pis)
    lab_page = collections.defaultdict(list)  # the lab's own publications page (labpage-pubs.jsonl.gz): citation strings, title inside
    lp_f = P.data('labpage-pubs.jsonl.gz', school, root=HERE)
    for line in (gzip.open(lp_f, 'rt') if lp_f.exists() else []):
        r_ = json.loads(line)
        if r_.get('sha256') and r_.get('quote'):
            lab_page[r_['pi']].append((norm_title(r_.get('title')), r_.get('year')))
    n['pis_with_lab_publication_page'] = sum(bool(lab_page[p['pi']]) for p in pis)
    claims = adviser_source_claims(ctx)
    advisees = {p['pi']: [s_ for s_ in stu[p['pi']].values()
                         if adviser_anchor_basis(p['pi'], s_, p.get('names') or [p['pi']], claims)] for p in pis}
    advisee_names = {pi: [Name([s_['name']]) for s_ in members] for pi, members in advisees.items()}
    adv_full = {pi: {fp_ for s_ in members for nm_ in [s_['name']] + list(s_.get('aliases') or [])
                     for fp_ in [full_pair(clean_person_name(nm_))] if fp_} for pi, members in advisees.items()}
    ctx.verified, ctx.dblp_doi, ctx.dblp_title, ctx.own_list, ctx.lab_page = verified, dblp_doi, dblp_title, own_list, lab_page
    ctx.advisee_names, ctx.adv_full = advisee_names, adv_full


def _cluster_key(raw):
    """'Zhao, Ben Y.' / 'Ben Y. Zhao' -> 'ben zhao': first given name and family name."""
    t = nosuffix(toks(byline_name(raw)))
    return f'{t[0]} {t[-1]}' if len(t) >= 2 else (t[0] if t else '')


def in_blocked_cluster(pid, w):
    """R-PAP-32 (2026-11-05, owner: UChicago stage-9 sample): a reviewed blocked cluster (census-overrides `blocked_clusters`:
    `coauthors`, `min_coauthors`, `why`, `evidence`) names a namesake's group. A work whose byline carries `min_coauthors` or more of
    the cluster's coauthors is the namesake's, whatever the PI's DBLP person page says: Yuxin Chen's DBLP page 'Yuxin Chen 0001' mixes
    in a security-HCI namesake whose coauthors are Ben Zhao, Haitao Zheng and Pedro Lopes."""
    cl = pid.get('blockedClusters') or []
    if not cl:
        return None
    names = {_cluster_key(x.get('raw_author_name') or (x.get('author') or {}).get('display_name') or '') for x in w.get('authorships') or []}
    for c in cl:
        if len(names & {_cluster_key(x) for x in c.get('coauthors') or []}) >= int(c.get('min_coauthors') or 2):
            return c
    return None


NAME_ONLY_IDENTITY = {'dblp_person_page_doi', 'dblp_person_page_title', 'pi_institutional_publication_list', 'lab_publication_page'}


def authorship_identity(ctx, pi, w, a, cw):
    """R-PAP-35 (2026-11-05, owner: round-r2 Michigan namesake): an identity that rests on the name through a DBLP person page or a publication list
    (not an author id, an ORCID, a verified collection work or an advisee) does not stand when the byline's middle names contradict the PI's.
    Mark W Newman's DBLP id in the census was the physicist M. E. J. Newman's page, which credited a Physics paper to him."""
    ident = _authorship_identity(ctx, pi, w, a, cw)
    if ident in NAME_ONLY_IDENTITY:
        raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
        if middle_conflict(ctx.pid0[pi].get('names') or [pi], raw):
            ctx.n['namesake_middle_name_conflicts'] += 1
            return None
    return ident


def _advisee_coauthor(advisee_names, others, pi_full):
    """Index possible Name.match surname/mono keys, retaining its exact final verdict.

    Name.match only compares these candidate family keys (or an exact single-name form). The index avoids
    normalizing every byline once per advisee; it neither removes authors nor changes the full-name guard.
    """
    if not advisee_names:
        return False
    by_family = collections.defaultdict(list)
    by_mono = collections.defaultdict(list)
    for raw in others:
        if not pi_full:
            full_tokens = nosuffix(toks(byline_name(raw)))
            if len(full_tokens) < 2 or len(full_tokens[0]) <= 1:
                continue
        t = nosuffix(name_toks(raw))
        if len(t) == 1:
            by_mono[t[0]].append(raw)
        elif len(t) >= 2:
            for family in {t[-1], ''.join(t[1:]), ''.join(t[-2:])}:
                by_family[family].append(raw)
    for name in advisee_names:
        for family in {last for _, last in name.forms}:
            if any(name.match(raw) for raw in by_family.get(family, ())):
                return True
        for mono in name.mono:
            if any(name.match(raw) for raw in by_mono.get(mono, ())):
                return True
    return False


def reviewed_author_matches(ctx, pi, w, aid):
    """R-PAP-04: an optional exact-work scope restricts a reviewed author ID.

    Mixed bibliographic records can have a positively verified authorship without
    verifying the entire author cluster. An explicit malformed scope fails closed.
    Independent DOI, bibliography and other per-work evidence remain available.
    """
    if aid not in ctx.reviewed_oa[pi]:
        return False
    review = getattr(ctx, 'ov', {}).get(pi, {})
    if 'openalex_work_scope' not in review:
        return True
    scope = review['openalex_work_scope']
    works = scope.get(aid) if isinstance(scope, dict) else None
    return (isinstance(works, list) and bool(works)
            and all(isinstance(wid, str) and re.fullmatch(r'https://openalex.org/W\d+', wid) for wid in works)
            and w.get('id') in works)


def _authorship_identity(ctx, pi, w, a, cw):
    """R-PAP-04, R-PAP-07: the identity that makes authorship `a` of work `w` (collection work `cw`) the PI's, in order,
    or None. An id reviewed as someone else's (or another PI's reviewed id) is never the PI."""
    if ctx.pid0[pi].get('identityHold'):
        ctx.n['authorships_withheld_by_identity_review'] += 1
        return None
    blocked, reviewed_oa, orcids, verified = ctx.blocked, ctx.reviewed_oa, ctx.orcids, ctx.verified
    dblp_doi, dblp_title, own_list, lab_page = ctx.dblp_doi, ctx.dblp_title, ctx.own_list, ctx.lab_page
    advisee_names, pid0 = ctx.advisee_names, ctx.pid0
    if (a.get('author') or {}).get('id') in blocked[pi]:
        return None
    if in_blocked_cluster(pid0[pi], w):
        return None
    if reviewed_author_matches(ctx, pi, w, (a.get('author') or {}).get('id')):
        return 'reviewed_openalex_author_id'
    if re.sub(r'^https?://orcid\.org/', '', (a.get('author') or {}).get('orcid') or '') in orcids[pi]:
        return 'pi_orcid'
    if cw and cw in verified[pi]:
        return 'dblp_verified_collection_work'
    if ndoi(w.get('doi')) in dblp_doi[pi]:
        return 'dblp_person_page_doi'
    title_key = norm_title(w.get('title'))
    y = dblp_title[pi].get(title_key) if title_key else None
    if y is not None and (not y or not w.get('publication_year') or abs(int(y) - w['publication_year']) <= 1):
        return 'dblp_person_page_title'
    y = own_list[pi].get(title_key, -1) if title_key else -1
    if y != -1 and (not y or not w.get('publication_year') or abs(int(y) - w['publication_year']) <= 1):
        return 'pi_institutional_publication_list'
    t_ = norm_title(w.get('title'))
    if len(t_) >= 30 and any(t_ in c_ and (not y_ or not w.get('publication_year') or abs(int(y_) - w['publication_year']) <= 1) for c_, y_ in lab_page[pi]):
        return 'lab_publication_page'  # the title inside a citation the PI's lab lists (title, authors, venue run together)
    others = [(x.get('raw_author_name') or (x.get('author') or {}).get('display_name') or '') for x in w.get('authorships') or [] if x is not a]
    # two initials prove nothing (2026-10-29: 'M. Wang' with 'J. Zhang' on EAST plasma papers made a Hefei M. Wang
    # Mengdi Wang's, and 'Y. L. Chen' with 'H. Hu' a Nanjing Y. L. Chen Yuxin Chen's): the PI or the advisee must be
    # written with a full given name
    def full(x):
        t_ = nosuffix(toks(byline_name(x)))
        return len(t_) >= 2 and len(t_[0]) > 1
    pi_raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
    # ... unless the initials spell every given name of a PI with two or more ('M.T. Islam' is Md Tauhidul Islam;
    # 'Y. L. Chen' is still not Yuxin Chen, 'M. Wang' still not Mengdi Wang) (2026-10-29, owner: best judgement)
    pi_full = full(pi_raw) or all_initials(pid0[pi].get('names') or [pi], pi_raw)
    if _advisee_coauthor(advisee_names[pi], others, pi_full):
        return 'advisee_coauthor'
    return None


def id_sets(ctx):
    """Per PI: reviewed OpenAlex ids, ORCIDs, blocked ids (reviewed as not the PI, unless mixed; and every other PI's
    reviewed id, 2026-10-28) and mixed ids (R-PAP-06)."""
    pis, n = ctx.pis, ctx.n
    reviewed_oa = {p['pi']: set(p.get('reviewedOpenAlex') or []) for p in pis}
    orcids = {p['pi']: set(p.get('orcid') or []) for p in pis}
    blocked = {p['pi']: set(p.get('notOpenAlex') or []) - set(p.get('mixedOpenAlex') or []) for p in pis}
    mixed = {p['pi']: set(p.get('mixedOpenAlex') or []) for p in pis}
    # another PI's reviewed author id is never this PI's (2026-10-28: S. Simon Wong's advisees co-wrote with H.-S. Philip
    # Wong, so the advisee rule anchored Philip Wong's reviewed id to Simon Wong through the 'S.' in 'H.-S.')
    # An exact-work review does not claim ownership of the whole mixed cluster.
    all_reviewed = collections.Counter(a for pi, s_ in reviewed_oa.items()
                                       if 'openalex_work_scope' not in getattr(ctx, 'ov', {}).get(pi, {}) for a in s_)
    for p in pis:
        blocked[p['pi']] |= {a for a in all_reviewed if a not in reviewed_oa[p['pi']]}
    n['other_pi_reviewed_ids_blocked'] = sum(len(v) for v in blocked.values())
    ctx.reviewed_oa, ctx.orcids, ctx.blocked, ctx.mixed = reviewed_oa, orcids, blocked, mixed


def candidate_pis(ctx, raw):
    """Exact opaque single-name forms, else the established first/family candidate index. No transliteration."""
    t = nosuffix(name_toks(raw))
    if len(t) == 1:
        return sorted(set(getattr(ctx, 'by_mono', {}).get(t[0], [])))
    if not t:
        return []
    return sorted(set(ctx.by_sur.get(t[-1], []) + ctx.by_sur.get(''.join(t[1:]), []) + ctx.by_sur.get(t[0], [])))


def author_id_name_conflict(pi_names, raw):
    """An author ID cannot override contradictory full given names on this byline.

    Opaque names and initial-only aliases cannot erase a known full-name conflict.
    Retain compatible initials, joined given names, nicknames, family-first forms
    and an additional given name (Zhiwei Steven Wu / Steven Wu).
    """
    full = []
    for name in pi_names:
        t = nosuffix(name_toks(name))
        if len(t) >= 3 and len(t[0]) == 1 and len(t[1]) > 1:
            t = t[1:]  # M. Frans Kaashoek also writes Frans Kaashoek
        if len(t) >= 2 and len(t[0]) > 1:
            full.append(' '.join(t))
            if len(t) >= 3:
                full.append(''.join(t[:-1]) + ' ' + t[-1])
    if full and compact_initials_compatible(pi_names, raw):
        return False   # 'RW Picard' / 'HH Asada' / 'DK Roy': joined given initials, the first one the PI's own, are not a contradicting full name
    return bool(full) and not Name(full).match(raw) and given_conflict(full, raw, strict=True)


def compact_initials_compatible(pi_names, raw):
    """A byline whose given part is 1-3 capital letters written together ('RW Picard', 'HH Asada', 'JA Paradiso', 'DK ROY') carries only
    initials: it conflicts with no full given name unless its first letter is no initial of any given word of the PI's forms."""
    words = re.sub(r'[.,]', ' ', raw or '').split()
    if len(words) < 2 or not re.fullmatch(r'[A-Z]{2,3}', words[0]):
        return False
    firsts = set()
    for name in pi_names:
        t = nosuffix(name_toks(name))
        if len(t) >= 2:
            firsts |= {w[0] for w in t[:-1] if w}
    return words[0][0].lower() in firsts


def hits(ctx):
    """The authorships matched to PIs: sweep works with an authorship matching the PI's name (with its identity), surname
    hits under an anchored or reviewed id, and the PI's own works outside the sweep (pi-works.sqlite) under an anchored or
    reviewed id or tied by page 1 (R-PAP-24). Anchored author ids are counted on the way."""
    HERE, school, pis, n, nm, cwork = ctx.here, ctx.school, ctx.pis, ctx.n, ctx.nm, ctx.cwork
    pis_by_name = {p['pi']: p['names'] for p in pis}
    per_work_only = {pi for pi, o in getattr(ctx, 'ov', {}).items()
                     if (o.get('source_owned_publication_review') or {}).get('decision') == 'owned_per_work_only'
                     or 'openalex_work_scope' in o}

    def identity_of(pi, w, a, cw):
        return authorship_identity(ctx, pi, w, a, cw)
    surname_only = []
    anchored = collections.defaultdict(collections.Counter)
    via_advisee = collections.defaultdict(collections.Counter)  # an author id on 2+ works the PI wrote with their own advisees anchors too
    id_sets(ctx)
    reviewed_oa, blocked, mixed = ctx.reviewed_oa, ctx.blocked, ctx.mixed
    hits = []  # (pi, oa work, authorship, collection work, identity)
    for w in sweep_works(school, HERE, ctx.n):
        if w.get('type') in NOT_PAPERS:  # datasets, peer reviews, errata, supplements: not papers
            continue
        cw = None; done = set()
        for a in w.get('authorships') or []:
            raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
            for pi in candidate_pis(ctx, raw):  # sorted: stable hit order; opaque CJK names stay exact
                if pi in done:
                    continue
                if reviewed_claims.excluded(ctx, pi, w):
                    done.add(pi); continue
                if not nm[pi].match(raw):
                    if (a.get('author') or {}).get('id'):  # "Zhiwei Steven Wu" for Steven Wu: decided once the PI's ids are anchored
                        surname_only.append((pi, w, a))
                    continue
                if cw is None:
                    cw = cwork(w) or ''
                ident = identity_of(pi, w, a, cw)
                if ident in (None, 'reviewed_openalex_author_id', 'advisee_coauthor') and author_id_name_conflict(pis_by_name[pi], raw):
                    n['author_id_full_given_name_conflicts'] += 1
                    continue
                done.add(pi)
                if (a.get('author') or {}).get('id') in mixed[pi]:
                    pass  # a mixed record never anchors
                elif pi not in per_work_only and ident and ident != 'advisee_coauthor' and (a.get('author') or {}).get('id'):
                    anchored[pi][a['author']['id']] += 1
                elif pi not in per_work_only and ident == 'advisee_coauthor' and (a.get('author') or {}).get('id'):
                    via_advisee[pi][a['author']['id']] += 1
                hits.append((pi, w, a, cw or None, ident, None))
    for pi, c in via_advisee.items():
        for aid, k in c.items():
            if k >= 2:
                anchored[pi][aid] += 0.5  # weaker than a DBLP- or review-anchored id; recorded apart in the identity label
    n['sweep_name_hits'] = len(hits)
    seen_pw = {(h[0], h[1]['id']) for h in hits}
    for pi, w, a in surname_only:  # the same surname under an author id anchored (or reviewed) for this PI
        aid = a['author']['id']
        reviewed_match = reviewed_author_matches(ctx, pi, w, aid)
        if (pi, w['id']) in seen_pw or aid in blocked[pi] or not (anchored[pi].get(aid, 0) >= 1 or reviewed_match):
            continue
        raw = a.get('raw_author_name') or a['author'].get('display_name') or ''
        if author_id_name_conflict(pis_by_name[pi], raw):
            n['author_id_full_given_name_conflicts'] += 1
            continue
        seen_pw.add((pi, w['id'])); hits.append((pi, w, a, cwork(w) or None, 'reviewed_openalex_author_id' if reviewed_match else 'anchored_author_id', None))
        n['surname_only_hits_by_anchored_id'] += 1
    # the PI's own works outside the sweep (hierarchy/<school>/pi-works.sqlite, tools/pi_fulltext_affiliation.py): an
    # authorship whose page 1 ties the school to the PI, and works over the sweep's author cap
    pw = P.data('pi-works.sqlite', school, root=HERE)
    tied, from_pw, page_read = {}, set(), {}
    if pw.exists():
        con = sqlite3.connect(f'file:{pw}?mode=ro', uri=True)
        author_reviews = primary_affiliations.load_author_review_pages(con)
        if author_reviews is not None:
            ctx.author_review_pages, input_holds = author_reviews
            for i, evidence in enumerate(input_holds):
                if not hasattr(ctx, 'primary_affiliation_reviews'):
                    ctx.primary_affiliation_reviews = {}
                ctx.primary_affiliation_reviews[('__author_review_input__', str(i))] = (None, evidence)
            if input_holds:
                n['primary_author_review_input_holds'] += len(input_holds)
        tied = {r[0]: dict(json.loads(r[1]), url=r[2], pdf_sha256=r[3]) for r in con.execute('select work, quote, url, pdf_sha256 from pages where school_named=1')}
        page_read = {r[0]: (r[1], r[2], r[3]) for r in con.execute('select work, status, page1, url from pages')}  # R3: every page-1 read
        in_sweep = {h[1]['id'] for h in hits}
        owner = collections.defaultdict(list)
        for p in pis:
            for a_ in set(anchored[p['pi']]) | reviewed_oa[p['pi']]:
                owner[a_].append(p['pi'])
        k0 = len(hits)
        for (b_,) in con.execute('select body from works'):
            w = school_scope_work(json.loads(zlib.decompress(b_)), school)
            if w['id'] in in_sweep or w.get('type') in NOT_PAPERS:
                continue
            if before_window(str(w.get('publication_date') or w.get('publication_year') or '')):   # the sweeps fetch 2016 and later; an older record here (a re-pulled merged id) is no lab paper of the window
                n['pi_works_before_window'] += 1
                continue
            for a in w.get('authorships') or []:
                aid = (a.get('author') or {}).get('id')
                for pi in owner.get(aid, []):
                    if reviewed_claims.excluded(ctx, pi, w):
                        continue
                    raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
                    if aid in blocked[pi] or not nm[pi].match(raw):
                        continue
                    reviewed_match = reviewed_author_matches(ctx, pi, w, aid)
                    if not reviewed_match and not anchored[pi].get(aid, 0):
                        continue
                    if author_id_name_conflict(pis_by_name[pi], raw):
                        n['author_id_full_given_name_conflicts'] += 1
                        continue
                    ident = 'reviewed_openalex_author_id' if reviewed_match else ('anchored_author_id' if anchored[pi][aid] >= 1 else 'advisee_anchored_author_id')
                    hits.append((pi, w, a, cwork(w), ident, tie_for_pi(tied.get(w['id']), pis_by_name[pi]) or tied.get(w['id']))); from_pw.add((pi, w['id']))
            # R8 (R-PAP-24, 2026-10-29, owner: accuracy sample): a work whose page 1 ties the school to the PI by name, at an
            # authorship under an author id that is not (yet) anchored is the PI's when the PI's own
            # DBLP person page (or another non-advisee identity) names it. Existing index affiliations do not
            # suppress this independent primary-source route; school, appointment and type checks still run.
            if w['id'] in tied:
                for a in w.get('authorships') or []:
                    raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or ''
                    aid = (a.get('author') or {}).get('id')
                    for pi in candidate_pis(ctx, raw):
                        if reviewed_claims.excluded(ctx, pi, w):
                            continue
                        if (pi, w['id']) in from_pw or aid in blocked[pi] or not nm[pi].match(raw) \
                                or author_id_name_conflict(pis_by_name[pi], raw) or not tie_for_pi(tied[w['id']], pis_by_name[pi]):
                            continue
                        cw_ = cwork(w); ident = identity_of(pi, w, a, cw_)
                        if ident and ident != 'advisee_coauthor':
                            hits.append((pi, w, a, cw_, ident, tie_for_pi(tied[w['id']], pis_by_name[pi]))); from_pw.add((pi, w['id'])); n['pi_work_page1_dblp_hits'] += 1
        n['pi_work_list_hits'] = len(hits) - k0
    ctx.hits, ctx.anchored, ctx.tied, ctx.from_pw, ctx.page_read = hits, anchored, tied, from_pw, page_read
