"""Students: who a PI lab's students are, one record per student and lab, and the weak relations that do not keep one.
R-HIER-03 (no merges across labs), R-HIER-04 (the PI is not their own student), R-STU-01 (sources), R-STU-02 (program
advising and readers), R-STU-03 (adviser names), R-STU-04 (reviewed corrections), R-STU-05 (doubled tokens), R-STU-06
(hyphen halves), R-STU-07 (a PI's person id is never a student), R-STU-08 (re-captured evidence), R-STU-09 (program-wide
advisers), R-STU-10 (the student's own roster entry), R-STU-11 (a basis record's advisor field)."""
import collections, json, re, unicodedata
from pathlib import Path

from .common import best_sources, read, source_year
from .names import Name, _fold, clean_person_name, dedupe_tokens, full_pair, names_full_form, nick_ok, same_student, toks

# Researched student evidence files, hierarchy/<school>/<file>, each a list of {pi, students: [{name, quote, sha256, url,
# ...}]}. EXTENSION POINT: a new reviewed student source (hierarchy/<school>/labpage-additions.json, docs/LAB-PAGES.md)
# is added here, by the coordinator.
RESEARCHED_FILES = ['few-students-evidence.json', 'thesis-evidence.json', 'labpage-evidence.json', 'thesis-held-years-evidence.json']

ADV_RX = [re.compile(r'(?i:advis[eo]rs?)(?:\(s\))?(?!\s*\(AC\))\s*:?\s*([^;|]+?)(?=\s*(?:Degree:|Research Area|Readers?|Examiners?|;|\||$))'),
          re.compile(r'([A-Z][\w.\- ]+?)\s*\((?:Primary )?Advis[eo]r\)')]  # named adviser fields only, never readers or examiners


ADVISING_LABEL = re.compile(r"Doctoral Dissertation (?:Co-)?Advisor \((?:AC|NonAC)\)|Doctoral Dissertation Reader \((?:AC|NonAC)\)"
                            r"|Doctoral \(Program\)|Master's Program Advisor|Undergraduate Major Advisor|Postdoctoral Faculty Sponsor"
                            r"|Postdoctoral Research Mentor")
WEAK_LABEL = re.compile(r"Reader|\(Program\)|Program Advisor|Major Advisor")


def advising_label(quote, names):
    """The Stanford Profiles advisee heading the student's name sits under in a quote ('Doctoral (Program) A, B
    Doctoral Dissertation Advisor (AC) C'), or None when the quote names no heading before the name."""
    q = unicodedata.normalize('NFKD', str(quote or '')).encode('ascii', 'ignore').decode()
    for nm in names:
        t = toks(nm)
        if not t:
            continue
        m = re.search(r'\b' + re.escape(t[-1]) + r'\b', q, re.I)
        if m:
            heads = [h for h in ADVISING_LABEL.finditer(q) if h.start() < m.start()]
            return heads[-1].group(0) if heads else None
    return None


ADVISER_NAMED = re.compile(r"advis[oe]rs?(?:\(s\))?\s*:\s*([^;\n]{3,120})|([A-Z][\w.'\- ]{2,40}?)\s*\(advis[oe]r\)", re.I)


def relation_names_other_adviser(r, pi_names):
    """Every source quote names the student's adviser(s), and none of them is this PI (2026-10-28: Princeton's roster
    line 'Kritkorn Karntikoon - Adviser(s): Bernard Chazelle' had been attached to Weinberg and Braverman too). Quotes
    that speak of co-advising or a primary advisor describe shared advising and never count as naming another."""
    fams = {unicodedata.normalize('NFKD', toks(n)[-1]).encode('ascii', 'ignore').decode().lower() for n in pi_names if toks(n)}
    quotes = [q.get('quote') or '' for q in r.get('sources') or []]
    if not quotes:
        return False
    for q in quotes:
        if re.search(r'co-?advis|primary advis', q, re.I):
            return False
        named = ' '.join((m.group(1) or m.group(2) or '') for m in ADVISER_NAMED.finditer(q))
        named = unicodedata.normalize('NFKD', named).encode('ascii', 'ignore').decode().lower()
        if not named or any(re.search(r'\b' + re.escape(f) + r'\b', named) for f in fams):
            return False
    return True


def relation_is_weak(r, names):
    """Program advising or a reader role only: every source quote puts the name under such a heading (or, with no
    quote heading, the relation's own role is one)."""
    labels = [advising_label(q.get('quote'), names) for q in r.get('sources') or []]
    labels = [l for l in labels if l] or ([r['role']] if ADVISING_LABEL.fullmatch(str(r.get('role') or '')) else [])
    return bool(labels) and all(WEAK_LABEL.search(l) for l in labels)


PROGRAM_Q = re.compile(r'Program:\s*(.+?)\s+(?:Email|Phone|Office|Academic Advisor)')
ACADEMIC_ADVISOR_Q = re.compile(r'Academic Advisor:\s*([^\n]+?)\s*$')


def program_adviser_groups(stu_all):
    """(program, academic advisor) pairs of a department directory that name one adviser for a whole program (R-STU-09,
    2026-10-29, owner: link-gap sample): a pair that holds 10+ students and 25%+ of the program's students in the school
    is the program's academic adviser (CMU: MCDS -> Eric Nyberg, 325 of 360; MIIS -> Teruko Mitamura; MSBIC -> Starzl),
    not a research adviser. Reads every relation source quote 'Program: <program> ... Academic Advisor: <name>'."""
    adv, allp = collections.defaultdict(set), collections.defaultdict(set)
    for recs in stu_all.values():
        for r in recs.values():
            for rel in r.get('relations') or []:
                for q in rel.get('sources') or []:
                    m, a = PROGRAM_Q.search(q.get('quote') or ''), ACADEMIC_ADVISOR_Q.search(q.get('quote') or '')
                    if m and a:
                        adv[(m.group(1).strip(), a.group(1).strip())].add(r['person']); allp[m.group(1).strip()].add(r['person'])
    return {k for k, v in adv.items() if len(v) >= 10 and len(v) >= 0.25 * len(allp[k[0]])}


def relation_is_program_advising(rel, groups):
    """Every source quote of the relation is a directory line of a program-wide academic adviser (program_adviser_groups)."""
    qs = [q.get('quote') or '' for q in rel.get('sources') or []]
    if not qs or not groups:
        return False
    for q in qs:
        m, a = PROGRAM_Q.search(q), ACADEMIC_ADVISOR_Q.search(q)
        if not (m and a and (m.group(1).strip(), a.group(1).strip()) in groups):
            return False
    return True


ADVISER_LABEL = re.compile(r'(?i)\badvis[eo]rs?(?:\(s\))?\s*:')


def own_roster_entry(quote, student_names, pi_names):
    """The adviser field of the student's own entry on a multi-student page (R-STU-10, 2026-10-29, owner: link-gap
    sample): a quote with 2+ 'Advisor(s):' labels is a page of many entries, and the next student's name trails any
    adviser value, so the whole quote proves nothing. The student's name is found (first given name, then up to 40
    characters, then the family name); the first adviser label after it, within 250 characters, is theirs; its value is
    cut at Publications/Office/Website/Email/Phone or at 80 characters. Returns 'single' (not a multi-entry quote),
    'names_pi', 'names_other', or 'unknown' (name or field not found). CMU's SE-PhD page: 'David Garlan' is Moreno's
    field, so Moreno is not Aldrich's or Kastner's student."""
    q = quote or ''
    labs_ = list(ADVISER_LABEL.finditer(q))
    if len(labs_) < 2:
        return 'single'
    t = _fold(q); pos = -1
    for f in student_names:
        tk = toks(clean_person_name(f))
        if len(tk) >= 2:
            m = re.search(re.escape(_fold(f).split()[0]) + r'[^.]{0,40}?\b' + re.escape(tk[-1]), t)
            if m:
                pos = m.end(); break
    if pos < 0:
        return 'unknown'
    nxt = next((m for m in labs_ if m.start() >= pos), None)
    if not nxt or nxt.start() - pos > 250:
        return 'unknown'
    seg = re.split(r'\b(?:Publications|Office|Website|Email|Phone)\b', q[nxt.end(): nxt.end() + 80])[0]
    return 'names_pi' if names_full_form(seg, pi_names) else 'names_other'


DSPACE_ADVISOR = re.compile(r'"dc\.contributor\.advisor"\s*:\s*\[(.*?)\]', re.S)


def dspace_advisors(quote):
    """The dc.contributor.advisor values of a DSpace record quote ('Freund, Robert M.' -> 'Robert M. Freund'), or []."""
    m = DSPACE_ADVISOR.search(quote or '')
    out = []
    for v in re.findall(r'"value"\s*:\s*"([^"]+)"', m.group(1)) if m else []:
        for part in re.split(r'\s+and\s+|;\s*', v.strip().rstrip('.')):
            part = part.strip().rstrip('.')
            if re.fullmatch(r"[^,]{2,40}, [^,]{2,40}", part):
                fam, giv = [x.strip() for x in part.split(',', 1)]; part = f'{giv} {fam}'
            if part:
                out.append(part)
    return out


def apply_relation_evidence(stu_all, school, here):
    """Re-captured evidence for relations the site collections gave without a quote or hash (R-STU-08, 2026-10-29, owner):
    hierarchy/<school>/relation-evidence.json (tools/relation_recapture.py; the bodies in relation-captures.sqlite) gives,
    per (cited url, person), the capture url, the sha256 of the captured bytes and a verbatim quote naming the student, and
    whether it also names the PI or the PI's lab (names_pi). A source without url+sha256+quote takes the record for its
    PI first (names_pi), else a student-only record (names_pi false, kept visible: the quote proves the page names the
    student, the collection's advising context names the PI). The source's earlier sha256 stays as original_sha256."""
    p = Path(here) / 'hierarchy' / school / 'relation-evidence.json'
    n = collections.Counter()
    if not p.exists():
        return n
    recs = collections.defaultdict(list)
    for x in json.loads(p.read_text()).get('records') or []:
        recs[(x['url'], x['person'])].append(x)
    sha = re.compile(r'^[0-9a-f]{64}$')
    ok = lambda q: bool(q.get('url')) and bool(sha.match(str(q.get('sha256') or ''))) and bool(str(q.get('quote') or '').strip())
    for pi, S in stu_all.items():
        for r in S.values():
            ids_ = [r['person']] + list(r.get('merged') or [])
            for rel in r.get('relations') or []:
                if any(ok(q) for q in rel.get('sources') or []):
                    continue
                best = None
                for j, q in enumerate(rel.get('sources') or []):
                    cands = [x for i in ids_ for x in recs.get((q.get('url'), i), [])]
                    hit = next((x for x in cands if x.get('pi') == pi and x.get('names_pi')), None) \
                        or next((x for x in cands if x.get('pi') is None and not x.get('names_pi')), None)
                    if hit and (best is None or (hit.get('names_pi') and not best[2].get('names_pi'))):
                        best = (j, q, hit)
                if best:
                    # this relation's own copy (2026-10-31): a context naming several advisers gives every lab the same
                    # source dicts, and updating them in place let the first lab processed (an order set by str hashing)
                    # decide the quote and names_pi of the others
                    j, q, x = best
                    q = dict(q); rel['sources'] = list(rel['sources']); rel['sources'][j] = q
                    if q.get('sha256') and q['sha256'] != x['sha256']:
                        q['original_sha256'] = q['sha256']
                    q.update(sha256=x['sha256'], quote=x['quote'], capture_url=x.get('capture_url'), names_pi=bool(x.get('names_pi')),
                             recaptured=dict(observed=x.get('observed'), method=x.get('method'), matches_original=x.get('matches_original')))
                    n['relation_evidence_recaptured_' + ('names_pi' if x.get('names_pi') else 'student_only')] += 1
                else:
                    n['relation_evidence_not_found'] += 1
    return n


def relation_own_entry_names_other(rel, student_names, pi_names):
    """Every source quote is a multi-entry roster whose adviser field for this student names someone else (R-STU-10)."""
    v = [own_roster_entry(q.get('quote'), student_names, pi_names) for q in rel.get('sources') or []]
    return bool(v) and all(x == 'names_other' for x in v)


def basis_advisees(quote):
    """Students a PI's basis quote names as their Ph.D. advisees, with the year when the quote dates it: a DSpace record
    ('"dc.contributor.author" : [ { "value" : "Huang, Qingqing, Ph. D. Massachusetts ...'), an SCS thesis page
    ('Kirstin Early August 2017 Ph.D. Thesis'), or a Stanford Profiles advisee heading ('Doctoral Dissertation Advisor
    (AC) Edward Gan, Sahaana Suri'; co-advisor too, never readers or program advisers)."""
    q = quote or ''; out = []
    for m in re.finditer(r'dc\.contributor\.author"\s*:\s*\[\s*\{\s*"value"\s*:\s*"([^"]+)', q):
        v = re.sub(r'\s*\([^)]*\)', '', m.group(1)); v = re.split(r',\s*Ph\.?\s*D\b', v)[0].strip().rstrip('.')
        if ',' in v:
            last, first = [x.strip() for x in v.split(',', 1)]; v = f'{first} {last}'
        out.append((v, None))
    m = re.match(r'\s*([A-Z][\w.\'\- ]+?)\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+((?:19|20)\d\d)\s+Ph\.?\s*D\.?\s+Thesis', q)
    if m:
        out.append((m.group(1).strip(), int(m.group(2))))
    m = re.search(r'Doctoral Dissertation (?:Co-)?Advisor \(AC\)\s+(.+?)(?=\s+(?:Doctoral|Postdoctoral|Master|Undergraduate|Reader|Orals|Current)|\s*$)', q)
    if m:
        out += [(x.strip(), None) for x in m.group(1).split(',') if len(x.strip().split()) >= 2]
    return [(clean_person_name(a), y) for a, y in out if a]


def rekey_pi_person_ids(labs, pi_pids, school):
    """R-STU-07 (2026-10-29, owner: accuracy sample): a PI's person id is never a student record. `labs`: {pi: {person id:
    student record}}; a record keyed by a PI's person id is re-keyed to the lab's own ext: id (merged into it when it
    exists). Returns the number re-keyed."""
    k = 0
    for pi, S in labs.items():
        for sid in [x for x in S if x in pi_pids]:
            r = S.pop(sid)
            new_id = f"ext:{school}:{re.sub('[^a-z0-9]+', '-', clean_person_name(r['name']).lower()).strip('-')}"
            r['person'] = new_id; r.setdefault('rekeyedFrom', []).append(sid)
            if new_id in S:
                S[new_id]['relations'] += r['relations']
            else:
                S[new_id] = r
            k += 1
    return k


def adviser_named(ctx, pi, a):
    """R-STU-03: an adviser field names a PI by full given name only through the PI's full-name forms (an 'H.
    Balakrishnan' alias of Hamsa must not take 'Balakrishnan, Hari' theses, 2026-10-28); an initials-only field goes to
    no PI when another PI of the school shares that family name and initial."""
    nm, nm_full, by_sur = ctx.nm, ctx.nm_full, ctx.by_sur
    t_ = toks(a)
    if not t_:
        return False
    if len(t_[0]) > 1:
        return nm_full[pi].match(a)
    return nm[pi].match(a) and not any(q != pi and nm[q].match(a) for q in by_sur.get(t_[-1], []))


def from_contexts(ctx):
    """R-STU-01: the collection's advising contexts that name the PI (by person id, a named adviser field, or the
    academic advising of a reused unit), and direct memberships of a reused lab unit. Returns {pi: {person id: record}}."""
    people, pis, pid0, by_sur, by_unit = ctx.people, ctx.pis, ctx.pid0, ctx.by_sur, ctx.by_unit

    def adviser_is(pi, a):
        return adviser_named(ctx, pi, a)
    # students: advising contexts naming the PI, and memberships of a reused unit
    stu = collections.defaultdict(dict)
    for person in people:
        for c in person.get('contexts') or []:
            t = c.get('type') or ''
            if 'advis' in t:
                advs = [c.get('advisorName') or c.get('advisor')] + list(c.get('advisors') or [])
                for s_ in c.get('sources') or []:  # adviser fields written in the quote (rosters, alumni pages, FPO announcements)
                    for rx in ADV_RX:  # senior-thesis advising counts for students (never for PI status, which the census decides)
                        for m_ in rx.finditer(s_.get('quote') or ''):
                            g = m_.group(1).strip()
                            if re.fullmatch(r"[^,]{2,40}, [^,]{2,40}", g) and all(len(toks(z)) <= 2 for z in g.split(',')):
                                advs.append(g)  # "Kernighan, Brian": one name, family name first
                            else:
                                advs += [x.strip() for x in re.split(r',| and ', g) if x.strip()]
                ids_ = {c.get('advisorPersonId'), c.get('advisorPerson'), c.get('advisorSuggestedPersonId')} - {None}
                cand = {q for a in advs if a for t_ in [toks(a)] if t_ for q in by_sur.get(t_[-1], []) + by_sur.get(''.join(t_[1:]), []) + by_sur.get(t_[0], [])}  # one-word advisers too ("Arvind.")
                cand |= {p['pi'] for p in pis if ids_ & set(p['personIds'])} | set(by_unit.get(c.get('unit'), []))
                for p in (pid0[q] for q in sorted(cand)):  # sorted: set order follows str hashing (2026-10-31)
                    if person['id'] in p['personIds']:
                        continue
                    if ids_ & set(p['personIds']) or any(a and adviser_is(p['pi'], a) for a in advs) or (c.get('unit') and c.get('unit') == p['lab']['unitId'] and t == 'academic_advising'):
                        r = stu[p['pi']].setdefault(person['id'], dict(person=person['id'], name=person['name'], roles=person.get('roles') or [], relations=[]))
                        r['relations'].append(dict(type=t, years=c.get('years') or ([c['year']] if c.get('year') else []), role=c.get('role'),
                                                   sources=best_sources(c.get('sources')), work=c.get('work')))
            elif t == 'direct_lab_membership':
                for p in pis:
                    if p['lab']['unitId'] and c.get('unit') == p['lab']['unitId'] and person['id'] not in p['personIds']:
                        r = stu[p['pi']].setdefault(person['id'], dict(person=person['id'], name=person['name'], roles=person.get('roles') or [], relations=[]))
                        r['relations'].append(dict(type=t, years=c.get('years') or ([c['year']] if c.get('year') else []), role=c.get('role'), sources=best_sources(c.get('sources'))))
    return stu


def people_by_family(people):
    """The collection's people by family name (the last name token)."""
    by_name = collections.defaultdict(list)
    for person in people:
        for t_ in [toks(person['name'])]:
            if len(t_) >= 2:
                by_name[t_[-1]].append(person)
    return by_name


def researched(ctx, stu, by_name):
    """R-STU-01: researched advisees and lab members with a quote and hash (gap-evidence.json and RESEARCHED_FILES); a
    unique collection person of that name takes the record, else an ext:<school>:<name> id."""
    HERE, school, pis, ge = ctx.here, ctx.school, ctx.pis, ctx.ge
    fe = collections.defaultdict(lambda: dict(students=[]))  # researched students: thin labs and the thesis hunt
    for fn in RESEARCHED_FILES:
        if (HERE / 'hierarchy' / school / fn).exists():
            for r in read(HERE / 'hierarchy' / school / fn):
                fe[r['pi']]['students'] = list(fe[r['pi']]['students']) + list(r.get('students') or [])
    for p in pis:  # researched students (gap-evidence.json, few-students-evidence.json): a stated advisee or lab member, with its quote
        for s_ in list((ge.get(p['pi']) or {}).get('students') or []) + list((fe.get(p['pi']) or {}).get('students') or []):
            if not (s_.get('name') and s_.get('quote') and s_.get('sha256')):
                continue
            t_ = toks(s_['name']); nm_ = Name([s_['name']])
            match_ = [q for q in by_name.get(t_[-1] if t_ else '', []) if nm_.match(q['name'])]
            sid = match_[0]['id'] if len(match_) == 1 else f"ext:{school}:{re.sub('[^a-z0-9]+', '-', s_['name'].lower()).strip('-')}"
            r = stu[p['pi']].setdefault(sid, dict(person=sid, name=match_[0]['name'] if len(match_) == 1 else s_['name'], roles=[s_.get('role') or 'student'], relations=[]))
            r['relations'].append(dict(type='researched_' + ('membership' if s_.get('role') == 'member' else 'advising'), years=[y for y in (s_.get('years') or []) if y],
                                       role=s_.get('role'), sources=[dict(url=s_.get('capture_url') or s_['url'], sha256=s_['sha256'], quote=s_['quote'])]
                                       # a defense announcement's 'Faculty Host <PI>' line, same page and hash (Michigan request 4)
                                       + ([dict(url=s_.get('capture_url') or s_['url'], sha256=s_['sha256'], quote=s_['host_quote'])] if s_.get('host_quote') else []),
                                       # automatic, unreviewed lab-page students stay marked (Michigan request 6: the accuracy sample stratifies on it)
                                       **({'auto': True} if s_.get('auto') else {})))
            if s_.get('auto'):
                r['auto'] = True


def basis_students(ctx, stu, by_name):
    """R-STU-01, R-STU-11: advisees named in the PI's own reviewed basis quote, when a DSpace record's own advisor field
    (if any) names the PI."""
    school, pis, nm_full, n = ctx.school, ctx.pis, ctx.nm_full, ctx.n
    for p in pis:  # advisees named in the PI's own reviewed basis quote (census-overrides.json pi_basis, kind advises_phd)
        b = p.get('piBasis') or {}
        if b.get('kind') != 'advises_phd' or not (b.get('quote') and b.get('sha256')):
            continue
        advs_ = dspace_advisors(b['quote'])  # R-STU-11: the record's own advisor field must name the PI (Renbo Zhao's record
        if advs_ and not any(nm_full[p['pi']].match(a) for a in advs_):  # in Van Parys's basis names Robert Freund)
            n['pi_basis_records_other_advisor'] += 1
            continue
        for sname, yr in basis_advisees(b['quote']):  # not 'nm': that is the PI name table
            t_ = toks(sname); nm_ = Name([sname])
            match_ = [q for q in by_name.get(t_[-1] if t_ else '', []) if nm_.match(q['name'])]
            sid = match_[0]['id'] if len(match_) == 1 else f"ext:{school}:{re.sub('[^a-z0-9]+', '-', sname.lower()).strip('-')}"
            r = stu[p['pi']].setdefault(sid, dict(person=sid, name=match_[0]['name'] if len(match_) == 1 else sname, roles=['phd'], relations=[]))
            r['relations'].append(dict(type='pi_basis_advising', years=[y for y in (yr or source_year(b),) if y], role='phd',
                                       sources=[dict(url=b['url'], sha256=b['sha256'], quote=b['quote'])]))
            n['pi_basis_advisees'] += 1


def merge_within_lab(ctx, stu):
    """One record per student and lab (R-HIER-03: within a lab only): names cleaned (R-STU-05), then records that are one
    person by Name.match or same_student (nicknames, prefixes, reorders, hyphen halves R-STU-06) merge, a collection
    person first. Returns the number merged."""
    pis, n = ctx.pis, ctx.n
    merged_students = 0
    for p in pis:  # one record per student and lab: nickname or spelling variants ("Liv" / "Olivia d'Aliberti") merge
        for r in stu[p['pi']].values():
            fixed = dedupe_tokens(clean_person_name(r['name']))  # R7: 'Arjun Nitin Nitin Bhagoji' -> 'Arjun Nitin Bhagoji'
            if fixed != r['name']:
                r.setdefault('aliases', []).append(r['name']); r['name'] = fixed; n['student_names_cleaned'] += 1
                if dedupe_tokens(clean_person_name(r['aliases'][-1])) != clean_person_name(r['aliases'][-1]):
                    n['student_names_doubled_token_cleaned'] += 1
            if r.get('aliases'):  # aliases are readings for the matchers: their doubled tokens go too (the raw name stays)
                r['aliases'] = list(dict.fromkeys(r['aliases'] + [dedupe_tokens(x) for x in r['aliases'] if dedupe_tokens(x) != x]))
        recs = list(stu[p['pi']].values())
        recs.sort(key=lambda r: (str(r['person']).startswith('ext:'), -len(r['relations'])))  # a collection person wins
        keep = []
        for r in recs:
            tgt = next((k for k in keep if Name([k['name']] + k.get('aliases', [])).match(r['name']) or Name([r['name']]).match(k['name'])
                        or any(same_student(r['name'], q) for q in [k['name']] + k.get('aliases', []))), None)
            if tgt is None:
                keep.append(r)
            else:
                tgt['relations'] += r['relations']; tgt.setdefault('aliases', []).append(r['name']); tgt.setdefault('merged', []).append(r['person']); merged_students += 1
        stu[p['pi']] = {r['person']: r for r in keep}
    return merged_students


def identity_review(ctx, stu):
    """R-STU-04: hierarchy/student-identity-review.json 'same_person' verdicts merge two records of one lab. Returns the
    number merged."""
    HERE, school = ctx.here, ctx.school
    merged_students = 0
    # reviewed identities (hierarchy/student-identity-review.json, from the same-name research): two records of one lab
    # that are one person merge under the canonical name; 'different_people' verdicts only feed the chain audit
    rev = read(HERE / 'hierarchy/student-identity-review.json') if (HERE / 'hierarchy/student-identity-review.json').exists() else []
    for x in rev:
        if x.get('school') != school or x.get('verdict') != 'same_person' or x.get('pi') not in stu:
            continue
        S = stu[x['pi']]
        find = lambda i: next((k for k, r in S.items() if k == i or i in (r.get('merged') or [])), None)
        a, b = find(x['a'][0]), find(x['b'][0])
        if not a or not b or a == b:
            continue
        keep_, drop_ = (a, b) if str(b).startswith('ext:') or not str(a).startswith('ext:') else (b, a)
        k, d = S[keep_], S.pop(drop_)
        k['relations'] += d['relations']; k.setdefault('aliases', []).extend([k['name'], d['name']] + list(d.get('aliases') or []))
        k.setdefault('merged', []).extend([d['person']] + list(d.get('merged') or []))
        k['name'] = x.get('canonical_name') or k['name']; k['aliases'] = [s for s in dict.fromkeys(k['aliases']) if s != k['name']]
        k.setdefault('identityReview', []).append(dict(merged=d['person'], reason=x.get('reason'), evidence=x.get('evidence')))
        merged_students += 1
    return merged_students


def corrections(ctx, stu):
    """R-STU-04: hierarchy/student-corrections.json drops, renames or replaces the evidence of a record."""
    HERE, school, n = ctx.here, ctx.school, ctx.n
    # reviewed record corrections (hierarchy/student-corrections.json): drop a misplaced student from a lab, rename a
    # record keyed to the wrong person (the old name stays an alias), or replace a relation's mis-cut evidence
    corr = read(HERE / 'hierarchy/student-corrections.json') if (HERE / 'hierarchy/student-corrections.json').exists() else []
    for x in corr:
        S = stu.get(x.get('pi')) if x.get('school') == school else None
        k = next((k for k, r in (S or {}).items() if k == x['student'] or x['student'] in (r.get('merged') or [])), None)
        if not k:
            continue
        r = S[k]
        if x['action'] == 'drop':
            S.pop(k)
        elif x['action'] == 'rename':
            r.setdefault('aliases', []).append(r['name']); r['name'] = x['name']
            if x.get('person'):
                r.setdefault('merged', []).append(k); r['person'] = x['person']; S[x['person']] = S.pop(k)
        elif x['action'] == 'replace_sources':
            r['relations'] = [dict(type=x.get('type', 'researched_advising'), years=x['years'], role=x.get('role'), sources=x['sources'])]
        r.setdefault('corrections', []).append(dict(action=x['action'], reason=x['reason'], evidence=x.get('evidence')))
        n['student_corrections_' + x['action']] += 1


def gather(ctx):
    """Every lab's students, before the links: ctx.stu {pi: {person id: record}} and ctx.self_listed (R-HIER-04)."""
    HERE, school, pis, n = ctx.here, ctx.school, ctx.pis, ctx.n
    stu = from_contexts(ctx)
    by_name = people_by_family(ctx.people)
    researched(ctx, stu, by_name)
    basis_students(ctx, stu, by_name)
    # a PI's person id is never a student record (R-STU-07, 2026-10-29, owner: accuracy sample): Berkeley's faculty John
    # Wright ('berkeley_fac_john-wright') had become the record of the hardware PhD student John Wright in Nikolić's lab
    # (a unique name match), which also lent the student the faculty member's person links. Such a record is re-keyed to
    # the lab's own ext: id; its relations and evidence stay.
    n['student_records_rekeyed_from_pi_person_id'] = rekey_pi_person_ids(stu, {i for p in pis for i in p['personIds']}, school)
    merged_students = merge_within_lab(ctx, stu)
    merged_students += identity_review(ctx, stu)
    corrections(ctx, stu)
    n['student_records_merged'] = merged_students
    # re-captured evidence for the site collections' bare-URL relations (R-STU-08, 2026-10-29)
    n.update(apply_relation_evidence(stu, school, HERE))
    # program-wide academic advisers are program advising, not research advising (R-STU-09, 2026-10-29)
    prog_groups = program_adviser_groups(stu)
    n['program_adviser_groups'] = len(prog_groups)
    for S_ in stu.values():
        for r in S_.values():
            for rel in r['relations']:
                if relation_is_program_advising(rel, prog_groups):
                    rel['weak'] = 'program_adviser'; n['relations_program_adviser'] += 1
    # the PI is not their own student (2026-10-29): lab rosters list their head ('Jim Glass' and 'John W. Fisher III' as
    # principal_investigator, 'Christos Faloutsos' as faculty). A record whose full first given name and family name are
    # the PI's own (nickname-equal, generational suffix ignored, initials never count) and that holds no student or
    # postdoc role is the PI; it leaves the lab's students (kept in the report as pisListedAsOwnStudent). (full_pair)
    studentish = re.compile(r'phd|student|master|undergrad|postdoc|graduate|thesis|visitor|intern', re.I)
    self_listed = []
    for p in pis:
        own = {full_pair(x) for x in p['names']} - {None}
        for sid, r in list(stu[p['pi']].items()):
            fp = full_pair(r['name'])
            roles_ = [str(x) for x in list(r.get('roles') or []) + [rel.get('role') for rel in r['relations']] if x]
            if fp and any(fp[1] == o[1] and nick_ok(fp[0], o[0]) for o in own) and not any(studentish.search(x) for x in roles_):
                self_listed.append(dict(pi=p['pi'], student=sid, name=r['name'], roles=sorted(set(roles_))))
                del stu[p['pi']][sid]
    n['pi_listed_as_own_student_dropped'] = len(self_listed)
    # Across labs, a matching name alone does not make one person (owner 2026-10-27: merge name variants only within a
    # lab, under the same PI; AGENTS.md: consolidate alternate names only with explicit identity evidence). Records in
    # several labs share an id only when their sources already resolved to the same person record; same-name records
    # in other labs are counted here and listed by tools/student_audit.py (across_labs) as candidates for review.
    seen_names = collections.defaultdict(set)
    for p in pis:
        for r in stu[p['pi']].values():
            t_ = [x for x in toks(r['name']) if len(x) > 1]
            if len(t_) >= 2:
                seen_names[tuple(t_)].add(r['person'])
    n['student_same_name_other_labs_unmerged'] = sum(len(v) > 1 for v in seen_names.values())
    n['pis_with_students'] = sum(bool(stu[p['pi']]) for p in pis); n['students'] = len({s for v in stu.values() for s in v}); n['lab_student_pairs'] = sum(len(v) for v in stu.values())
    ctx.stu, ctx.self_listed = stu, self_listed


def drop_weak(ctx, sp):
    """R-STU-02, R-STU-09, R-STU-10: a student none of the lab's papers links whose every relation is weak (a reader or
    program heading, a program-wide academic adviser, a quote naming another adviser, or the student's own roster entry
    naming another) leaves the lab; the dropped pairs go to the report (ctx.weak_dropped)."""
    pis, stu, n = ctx.pis, ctx.stu, ctx.n
    # Program advising and readers (owner 2026-10-28): a student whose only tie to the lab is a "Doctoral (Program)" or
    # "Reader" listing stays only when they co-authored one of the lab's papers; the dropped pairs are kept in the report
    linked = {(x['pi'], x['student']) for x in sp}
    weak_dropped = []
    for p in pis:
        for sid, s in list(stu[p['pi']].items()):
            nms_ = [s['name']] + list(s.get('aliases') or [])
            if (p['pi'], sid) not in linked and s['relations'] and all(relation_is_weak(r, nms_) or r.get('weak') == 'program_adviser'
                                                                       or relation_names_other_adviser(r, p.get('names') or [p['pi']])
                                                                       or relation_own_entry_names_other(r, nms_, p.get('names') or [p['pi']])
                                                                       for r in s['relations']):
                why_ = sorted({'program_adviser' if r.get('weak') == 'program_adviser' else 'reader_or_program_heading' if relation_is_weak(r, nms_)
                               else 'quote_names_other_adviser' if relation_names_other_adviser(r, p.get('names') or [p['pi']]) else 'own_roster_entry_names_other'
                               for r in s['relations']})
                n['students_dropped_why:' + '+'.join(why_)] += 1
                weak_dropped.append(dict(pi=p['pi'], student=sid, name=s['name'], why=why_, roles=sorted({advising_label(q.get('quote'), [s['name']] + list(s.get('aliases') or [])) or r.get('role') or '' for r in s['relations'] for q in r.get('sources') or []})))
                del stu[p['pi']][sid]
    n['students_dropped_program_or_reader_only'] = len(weak_dropped)
    ctx.weak_dropped = weak_dropped
