"""Home departments of a protocol school's PIs, from the titles on their dated department listings: protocol stage 3.

rule      the PI's latest 2016-2026 listing row decides:
            a professor title in the listing's own department (the charter's [[departments]].title_match; not courtesy,
            affiliate, adjunct, visiting, emeritus) -> that department (charter name); a person listed with such a title
            by two departments takes the one with more such years, the other goes to `also`
            a courtesy / affiliate appointment -> the unit of the row's first professor title that is not the
            department's (census pi_basis.home_unit: 'School of Information', 'Linguistics')
            otherwise (emeritus or adjunct only in the latest row) -> the department of their last professor title
          the other units the row names go to `also`; the quote is the listing row (url + sha256 + quote)
status    accepted when one unit results; hold when none does (written, never a placeholder home)
-> hierarchy/<key>/home-departments.json, and the school's rows of the shared hierarchy/home-departments.json (re-read
   immediately before writing; only rows of this school are replaced)
usage: home_departments_school.py <key> [--write-shared]
"""
import collections, json, re, sys, unicodedata

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import census_overrides as CO  # noqa: E402

NOT_HOME = re.compile(r'courtesy|affiliate|adjunct|visiting|emerit|lecturer|research (?:scientist|investigator)|status-only', re.I)
PROF = re.compile(r'\bprofessor\b', re.I)
UNIT = re.compile(r'professor(?:\s*\([^)]*\))?(?: of [^,]+)?,\s*(.+)$', re.I)


def sourced_pi_key(row):
    """Match a middle-initial variant only when its faculty quote is identical."""
    basis = row.get('pi_basis') or {}
    if not (basis.get('sha256') and basis.get('quote')):
        return None
    ascii_name = ''.join(c for c in unicodedata.normalize('NFKD', row['name']) if not unicodedata.combining(c))
    name = re.sub(r'\b[A-Z]\.\s*', '', ascii_name).casefold().split()
    return (' '.join(name), basis['sha256'], basis['quote'])


SCHOOL_LEVEL = re.compile(r'^(?:Medical School|School of|College of|Rackham)', re.I)


def home_title(prof):
    """The (row, title) that names the home among a person's professor titles in listing order: the latest regular one; a later adjunct,
    emeritus or visiting title in another unit never outranks it (UW Tim Althoff, 2026-11-22: CSE 'Associate Professor' and iSchool 'Adjunct
    Associate Professor' in the same years). Only when every title is such a title does the latest one stand."""
    return ([p for p in prof if not NOT_HOME.search(p[1])] or prof)[-1]


def listed_title_unit(quote):
    """The unit a listing row's own professor title names ('... Professor of Psychology' -> 'Psychology'), or None; never for an adjunct,
    affiliate or courtesy title (those name another unit's appointment, not the home)."""
    if re.search(r'adjunct|affiliate|courtesy|emerit', quote or '', re.I):
        return None
    m = re.search(r'\bProfessor of (?:the )?([A-Z][A-Za-z&,\- ]{2,80}?)\s*(?:$|[;(]| and (?:Adjunct|Affiliate))', (quote or '').strip())
    return m.group(1).strip(' ,') if m else None


def unit_of(title):
    """'Professor, School of Information' -> 'School of Information'; 'Assistant Professor of Computational Medicine and
    Bioinformatics, Medical School' -> 'Computational Medicine and Bioinformatics' (the department, not the school)."""
    m = UNIT.search(title)
    if not m:
        return None
    u = m.group(1).strip()
    of = re.search(r'professor of (.+?),', title, re.I)
    return of.group(1).strip() if of and SCHOOL_LEVEL.match(u) else u


NOT_A_UNIT = re.compile(r"^(?:joint\b|starting\b|effective\b|beginning\b|as of\b)|…|\.\.\.|\b(?:chair|director|dean|head|fellow|professor|emerit\w*|lecturer)\b", re.I)
JOINT = re.compile(r'^joint\s+(?:with|w/)\s*(?:the\s+)?', re.I)


FIELD_MEMBER = re.compile(r'Field Member', re.I)
DEPT_PROFILE = re.compile(r'Faculty \(Department\)\s+(.+?)(?=\s+Faculty \(|$)')
RANK_UNIT = re.compile(r'Professor(?:\s*\([^)]*\))?\s*(?:[;:,]|\s(?:of|in|at)\b)\s*(?:the\s+)?(.+)$', re.I)
BARE_FIELD_UNIT = re.compile(r'^(?!.*Professor)(.+?)[,;]?\s*CS Field Member$', re.I)


def profile_home(titles):
    """R-HOME-01 on a directory row that carries a graduate-field marker (Cornell, 2026-11-25; its homes audit failed 20 of 50): a `Faculty (Field) X` profile or
    a `CS Field Member` suffix is a graduate-field membership, never a home. The home is the `Faculty (Department) X` unit; else the unit the title names
    ('Associate Professor of Electrical and Computer Engineering', 'Professor; Information Science, CS Field Member', 'Professor in Energy Systems Engineering');
    the field is an `also`. -> (home or None, [also...], 'faculty_department'|'listed_title'|'primary_unresolved') or None when the row has no field marker."""
    joined = ' '.join(titles or [])
    if 'Faculty (Field)' not in joined and 'Faculty (Department)' not in joined and not FIELD_MEMBER.search(joined):
        return None
    m = DEPT_PROFILE.search(joined)
    if m:
        return m.group(1).strip(), [], 'faculty_department'
    for t in titles or []:
        if re.search(r'courtesy|affiliate|adjunct|emerit|visiting', t, re.I):
            continue
        if NAMED_CHAIR.search(t):   # 'Laibe/Acheson Professor of Business Management', 'Zak Professor in Energy Systems Engineering': an endowed chair, not a unit
            continue
        u = RANK_UNIT.search(t) or BARE_FIELD_UNIT.search(t)
        if not u:
            continue
        parts = [x.strip() for x in re.split(r'[;,]', FIELD_MEMBER.sub('', u.group(1))) if x.strip()]
        parts = [x for x in parts if not re.fullmatch(r'CS', x)]
        if parts and not NOT_A_UNIT_TITLE.search(parts[0]):
            return parts[0], parts[1:], 'listed_title'
    return None, [], 'primary_unresolved'


NAMED_CHAIR = re.compile(r'^(?:the\s+)?(?!(?:(?:Assistant|Associate|Senior|Full)\s+)?Professor\b)(?:(?:Assistant|Associate|Senior)\s+)?[A-Z][^\s,;:]*(?:[ /&.\'’-]+[A-Za-z][^\s,;:]*)*?\s+(?:Family\s+)?(?:Assistant\s+|Associate\s+)?Professor\b')
NOT_A_UNIT_TITLE = re.compile(r'\b(?:chair|director|dean|head|provost|fellow)\b', re.I)


def clean_unit(u):
    """(home candidate, joint unit) from the text after a title's comma. 'Joint with the School of Math' is the OTHER unit of a joint appointment (-> also),
    'Starting Fall'26', 'KUKA Chair of Robotics, and Director of IRIM' and anything cut off with an ellipsis are not units at all (Georgia Tech R8: 16 PIs got such
    strings as their home department). A real unit text ('School of Information') is the home candidate."""
    if not u:
        return None, None
    if JOINT.match(u):
        j = JOINT.sub('', u).strip()
        return None, (None if NOT_A_UNIT.search(j) or '…' in j else j)
    return (None if NOT_A_UNIT.search(u) else u), None


def apply_reviewed_homes(rows, overrides, normalize):
    """A sourced school-local home decision can correct an ambiguous directory title."""
    for row in rows:
        decision = overrides.get(row['name']) or {}
        home = decision.get('home_department')
        if not home:
            continue
        evidence = decision.get('home_department_evidence') or []
        if not isinstance(evidence, list) or not evidence or any(
            not isinstance(e, dict) or not e.get('url') or not str(e.get('quote') or '').strip()
            or not re.fullmatch(r'[0-9a-f]{64}', str(e.get('sha256') or '')) for e in evidence
        ):
            raise SystemExit(f"{row['name']}: reviewed home_department requires evidence with url, SHA-256 and verbatim quote")
        selection = decision.get('home_selection_basis')
        if selection is not None:
            kinds = {'first_listed_site': 'faculty_owned_site',
                     'first_listed_publication': 'authored_publication'}
            ordered = evidence[0].get('ordered_departments') or []
            if (selection not in kinds or decision.get('primary_stated') or decision.get('primary_unresolved')
                    or evidence[0].get('kind') != kinds.get(selection) or not isinstance(ordered, list) or not ordered
                    or any(not isinstance(u, str) or not u.strip() for u in ordered)
                    or normalize(ordered[0]) != normalize(home)):
                raise SystemExit(f"{row['name']}: first-listed selection requires ordered source units, matching home, and no stated/unresolved primary")
        old = row.get('home_department')
        home = normalize(home)
        also = [a for a in dict.fromkeys([old] + list(row.get('also') or [])
                                        + list(row.get('primary_unresolved') or [])
                                        + list(decision.get('also_home_departments') or [])) if a and a != home]
        # R-HOME-01 retains real secondary appointments. An explicitly reviewed
        # correction of an erroneous inferred unit must not manufacture one.
        superseded = decision.get('superseded_home_department')
        if superseded is not None:
            reason = decision.get('why_superseded_home_department')
            if not isinstance(superseded, str) or not superseded.strip() or not isinstance(reason, str) or not reason.strip():
                raise SystemExit(f"{row['name']}: superseded_home_department requires a unit and a researched reason")
            rejected = normalize(superseded)
            named = [normalize(u) for u in (decision.get('also_home_departments') or []) + (decision.get('primary_unresolved') or [])]
            if row.get('primary_unresolved') or decision.get('primary_unresolved'):
                raise SystemExit(f"{row['name']}: superseded_home_department conflicts with unresolved appointments")
            if rejected == home or rejected in named:
                raise SystemExit(f"{row['name']}: superseded_home_department conflicts with a retained appointment")
            previous = row.get('superseded_home_department') or {}
            if rejected == normalize(old):
                previous = dict(home_department=old, evidence=row.get('evidence'), reason=reason)
            elif (old != home or not isinstance(previous, dict)
                  or normalize(previous.get('home_department')) != rejected or previous.get('reason') != reason):
                raise SystemExit(f"{row['name']}: superseded_home_department does not match the previous home")
            also = [a for a in also if normalize(a) != rejected]
            row['superseded_home_department'] = previous
        row.update(home_department=home, also=also, status='accepted', evidence=evidence[0],
                   reviewed_home_evidence=evidence, note=decision.get('why_home_department') or 'reviewed home department with sourced evidence')
        if 'no_academic_department' in decision:
            if not isinstance(decision['no_academic_department'], bool):
                raise SystemExit(f"{row['name']}: no_academic_department must be a boolean")
            row['no_academic_department'] = decision['no_academic_department']
        # Owner-delegated rule 2026-11-09 (docs/RULES.md R-HOME-01): the home is the primary appointment the official page states. When the page names several
        # units and does not say which is primary, the decision lists them in `primary_unresolved`: the row keeps `home_department` only as the reporting
        # unit, marks home_basis 'primary_unresolved', and every listed unit stays visible (the others in `also`).
        unresolved = [normalize(u) for u in decision.get('primary_unresolved') or []]
        if unresolved:
            if len(unresolved) < 2 or home not in unresolved:
                raise SystemExit(f"{row['name']}: primary_unresolved needs two or more units including home_department")
            row.update(home_basis='primary_unresolved', primary_unresolved=unresolved,
                       also=[a for a in dict.fromkeys(unresolved + also) if a != home])
        else:
            row['home_basis'] = selection or ('primary_stated' if decision.get('primary_stated') else 'listed_title')
            if selection:
                row['home_selection_basis'] = selection
            else:
                row.pop('home_selection_basis', None)
            row.pop('primary_unresolved', None)
    return rows


def seed_reviewed_native_homes(rows, existing_pis, reviewed, school):
    """Retain an exact existing PI's sourced home when a census omits its key."""
    emitted = {row['name'] for row in rows}
    for pi in existing_pis:
        name = pi['pi']
        if name not in emitted and (reviewed.get(name) or {}).get('home_department'):
            rows.append(dict(school=school, name=name, home_department=None, also=[],
                             no_academic_department=False, status='hold', evidence=None,
                             note='Reviewed home for an existing native PI key'))
            emitted.add(name)
    return rows


def main(key, write_shared=False):
    cfg = S.get(key)
    from listing_rows import rank_of
    rank_words = S.field(cfg, 'census.rank_words') or {}

    def faculty_title(title):
        return bool(PROF.search(title)) or rank_of([title], rank_words) == 'ladder'

    deps = {d['code']: d for d in S.listing_units(cfg)}
    tm = {c: re.compile(d.get('title_match') or '.', re.I) for c, d in deps.items()}
    census = json.loads((P.data('census-faculty.json', key)).read_text())['faculty']
    adds = json.loads((P.data('census-additions.json', key)).read_text()) if (P.data('census-additions.json', key)).exists() else []
    units = {u['code']: u['name'] for u in cfg.get('affiliated_units') or []}
    centers = set(S.field(cfg, 'census.center_units') or [])
    canon = [(re.compile(rx, re.I), name) for name, rx in (S.field(cfg, 'census.home_units') or {}).items()]
    known_homes = {name for _, name in canon}

    def norm(u):
        u = re.sub(r'\s*\((?:effective|as of)[^)]*\)', '', u or '').strip()
        u = re.sub(r'^Department of\s+', '', u)
        return next((name for rx, name in canon if rx.search(u)), u)
    rows = json.loads((P.data('rows.json', key)).read_text())
    by_name = collections.defaultdict(list)
    for r in rows:
        by_name[r['name']].append(r)
    reviewed = CO.section(key)
    # Existing PI aliases are already accepted identity bindings. A reviewed
    # canonical census record must not gain another home row for an alias.
    pi_path = P.data('pis.json', key)
    existing_pis = json.loads(pi_path.read_text()) if pi_path.exists() else []
    alias_targets = collections.defaultdict(set)
    census_names = {x['name'] for x in census}
    for pi in existing_pis:
        if pi['pi'] in census_names and (reviewed.get(pi['pi']) or {}).get('home_department'):
            for alias in pi.get('names') or []:
                if alias != pi['pi']:
                    alias_targets[alias].add(pi['pi'])
    addition_pi_names = {x['name'] for x in adds if x.get('is_pi')}
    # A name-order variant the builder merges into a canonical PI ('Jiaya Jia' into 'JIA Jiaya': reviewed native merge, same DBLP pid or collection
    # person) gets no home row of its own: the canonical PI carries the home (CUHK 2026-11-24: 22 variant rows were audited as persons).
    from stage_gate import pis_of
    gate_pis = pis_of(key)
    merged_variants = {a for x in gate_pis for a in x.get('aliases') or []} - {x['name'] for x in gate_pis}
    out, n = [], collections.Counter()
    for x in census:
        if x['name'] in merged_variants and x.get('is_pi'):
            continue
        if not x.get('is_pi'):
            # A reviewed unit affiliation is useful for teaching, emeritus and
            # other faculty records too. It does not admit another PI or lab.
            # Seed no inferred home: only the sourced decision below can accept it.
            if x['name'] not in addition_pi_names and (reviewed.get(x['name']) or {}).get('home_department'):
                out.append(dict(school=key, name=x['name'], home_department=None,
                                also=[], no_academic_department=False, status='hold',
                                evidence=None, faculty_only_record=True,
                                note='Faculty unit review; census PI eligibility unchanged'))
            continue
        rs = sorted([r for nm in [x['name']] + list(x.get('aliases') or []) for r in by_name.get(nm, [])], key=lambda r: r['observed'])
        own = collections.Counter()
        for r in rs:
            if any(PROF.search(t) and tm[r['dept']].search(t) and not NOT_HOME.search(t) for t in r['titles']):
                own[r['dept']] += 1
        b = x.get('pi_basis') or {}
        home, ev, note = None, None, None
        extra_also = []
        if b.get('kind') == 'courtesy_faculty' and b.get('home_unit'):
            home = b['home_unit']; ev = dict(url=b['url'], sha256=b['sha256'], quote=b['quote']); note = 'courtesy appointment: the home unit of the same listing row'
        elif own:
            code = own.most_common(1)[0][0]
            r = [r for r in rs if r['dept'] == code][-1]
            home = deps[code]['name']; ev = dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote'])
            note = f'professor title in the {code} listing (latest row)' + (f'; also listed by {", ".join(c for c in own if c != code)}' if len(own) > 1 else '')
        else:
            prof = [(r, t) for r in rs for t in r['titles'] if faculty_title(t) and not re.search('courtesy|affiliate|status-only', t, re.I)]
            if prof:
                # a regular professor title outranks a later adjunct/emeritus/visiting one in another unit (UW Tim Althoff: CSE 'Associate Professor',
                # iSchool 'Adjunct Associate Professor' in the same years; the adjunct row was read as the home)
                r, t = home_title(prof)
                u, joint = clean_unit(unit_of(t))
                home = deps[r['dept']]['name'] if (not u or tm[r['dept']].search(u)) else u
                if joint:
                    extra_also.append(joint)
                ev = dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote']); note = 'the last professor title listed (emeritus or adjunct later)'
        ph = profile_home(rs[-1]['titles']) if rs and not (b.get('kind') == 'courtesy_faculty' and b.get('home_unit')) else None
        if ph:   # a graduate-field listing never sets the home (R-HOME-01, profile_home)
            home, ph_also, ph_how = ph
            if home and not any(rx.search(home) for rx, _ in canon):   # only a known unit is accepted from a title; anything else is reviewed, never silently kept
                ph_also, ph_how, home = ph_also + [home], 'primary_unresolved', None
            extra_also = list(ph_also) + ['Computer Science']   # the field; dropped below when it is the home
            ev = dict(url=rs[-1]['capture_url'], sha256=rs[-1]['sha256'], quote=rs[-1]['quote'])
            note = f'home from the {ph_how.replace("_", " ")} of the latest directory row; the graduate field is an `also`'
            if home is None:
                note = 'primary_unresolved: the directory row lists only a graduate-field membership and the title names no unit'
        also = list(extra_also)
        if rs and not ph:
            for t in rs[-1]['titles']:
                u, joint = clean_unit(unit_of(t))
                if joint:
                    also.append(joint)
                if u and u != home and not any(tm[c].search(u) for c in tm if deps[c]['name'] == home):
                    also.append(u)
        also += [deps[c]['name'] for c in own if deps[c]['name'] != home]
        home = norm(home) if home else home
        also = [a_ for a_ in dict.fromkeys(norm(a_) for a_ in also) if a_ != home]
        row = dict(school=key, name=x['name'], home_department=home, also=list(dict.fromkeys(also)), no_academic_department=False,
                   status='accepted' if home else 'hold', evidence=ev, note=note or 'no professor title on any listing row')
        out.append(row); n[row['status']] += 1; n['home:' + str(home)] += 1
    census_pis = {x['name'] for x in census if x.get('is_pi')}
    census_source_keys = {sourced_pi_key(x) for x in census if x.get('is_pi')}
    for x in adds:  # accepted CS-related faculty of other units: the unit whose faculty listing proves the appointment
        if not x.get('is_pi'):
            continue
        if len(alias_targets.get(x['name'], set())) == 1:
            continue
        if x['name'] in census_pis or (sourced_pi_key(x) is not None and sourced_pi_key(x) in census_source_keys):
            continue  # the dated school census already supplied this person's home
        b = x.get('pi_basis') or {}
        code = (x.get('departments') or [None])[-1]
        # a center is never a home: hold until an academic school is evidenced; a code that names no charter unit or department is a listing
        # host token ('jhu', 'profile'), not a home: hold too (JHU/UChicago/WashU 2026-11-15: 29 PIs were accepted with the host as their department)
        unit_name = units.get(code) or (deps.get(code) or {}).get('name')
        if not unit_name and isinstance(code, str) and code[:1].isupper() and not code.isupper() and any(k.startswith('unit_listing:') for k in (s_.get('kind', '') for s_ in x.get('sources') or [])):
            unit_name = code   # UT Austin 2026-11-15: a catalog/department listing heading ('Mathematics', 'Psychology') is the unit's own name; a lower-case host token ('jhu') still is not
        # A campus-wide discovery roster identifies people, not an academic unit.
        if unit_name and 'candidate discovery only' in unit_name.casefold():
            unit_name = None
        home = None if (code in centers or not unit_name) else norm(unit_name)
        titled = listed_title_unit(b.get('quote') or '')
        if home and titled and norm(titled) != home and norm(titled) in known_homes:   # only a known unit name, never a title fragment
            home = norm(titled)   # 'Prat, Chantel Professor of Psychology' on the Linguistics listing: the title names the home (UW homes audit 2026-11-23)
        also = [a_ for a_ in dict.fromkeys(norm(units.get(c_, c_)) for c_ in (x.get('departments') or [])[:-1]) if a_ and a_ != home]   # other units with ladder evidence (the ML Center)
        also = [u for u in also if 'candidate discovery only' not in u.casefold()]
        row = dict(school=key, name=x['name'], home_department=home, also=also, no_academic_department=False, status='accepted' if home else 'hold',
                   evidence=dict(url=b.get('url'), sha256=b.get('sha256'), quote=b.get('quote')), note=f'the {code} faculty listing (cs-related-review.json)')
        out.append(row); n[row['status']] += 1; n['home:' + str(home)] += 1
    # A native PI key may have been retained from an earlier census or renamed
    # by an accepted identity review. A sourced home review for that exact
    # existing key must survive rebuilding even when neither current census
    # loop emits it. This supplies a home only; it cannot admit another PI.
    seed_reviewed_native_homes(out, existing_pis, reviewed, key)
    apply_reviewed_homes(out, reviewed, norm)
    n = collections.Counter(row['status'] for row in out)
    n.update('home:' + str(row['home_department']) for row in out)
    P.data_w('home-departments-school.json', key).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    if write_shared:
        f = P.data('home-departments.json')
        txt = f.read_text(); shared = json.loads(txt)
        ind = len(re.match(r'\[\n( *)', txt).group(1)) if re.match(r'\[\n( *)', txt) else 2  # keep the file's own layout
        shared = [r for r in shared if r.get('school') != key] + out
        f.write_text(json.dumps(shared, indent=ind, ensure_ascii='\\u' in txt) + ('\n' if txt.endswith('\n') else ''))
    print(json.dumps(dict(n.most_common(20))))


if __name__ == '__main__':
    main(sys.argv[1], '--write-shared' in sys.argv)
