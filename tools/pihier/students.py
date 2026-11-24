"""Students: who a PI lab's students are, one record per student and lab, and the weak relations that do not keep one.
R-HIER-03 (no merges across labs), R-HIER-04 (the PI is not their own student), R-STU-01 (sources), R-STU-02 (program
advising and readers), R-STU-03 (adviser names), R-STU-04 (reviewed corrections), R-STU-05 (doubled tokens), R-STU-06
(hyphen halves), R-STU-07 (a PI's person id is never a student), R-STU-08 (re-captured evidence), R-STU-09 (program-wide
advisers), R-STU-10 (the student's own roster entry), R-STU-11 (a basis record's advisor field), R-STU-17 (visiting students), R-STU-18 (evidence-confirmed roster pairs)."""
import collections, hashlib, json, re, unicodedata
from pathlib import Path
from urllib.parse import urlsplit

import atlas_paths as P  # data paths (DATA_FILES)
import student_decisions as SD  # reviewed per-person decisions (R-STU-17 `visiting`)

from .common import TODAY, WINDOW_START, accepted_additions, as_years, best_sources, read, source_year
from .names import CJK, Name, _fold, clean_person_name, dedupe_tokens, full_pair, names_full_form, nick_ok, initials_optional, same_student, surname_typo, toks

# Researched student evidence files, hierarchy/<school>/<file>, each a list of {pi, students: [{name, quote, sha256, url,
# ...}]}. EXTENSION POINT for a new reviewed student source. The lab-page additions (labpage-additions.json `students`)
# come in through common.accepted_additions, gated by labpage-acceptance.json (2026-10-31).
RESEARCHED_FILES = ['few-students-evidence.json', 'undated-capture-evidence.json', 'surname-adviser-evidence.json', 'thesis-evidence.json', 'labpage-evidence.json', 'thesis-held-years-evidence.json', 'roster-evidence.json', 'defense-adviser-evidence.json', 'thesis-committee-chair-evidence.json', 'department-directory-evidence.json', 'group-source-evidence.json']


def researched_sources(row):
    """Keep the separate, reviewed source fragments supporting one relationship."""
    url = row.get('capture_url') or row['url']
    sources = [dict(url=url, sha256=row['sha256'], quote=row['quote'])]
    if row.get('host_quote'):
        sources.append(dict(url=url, sha256=row['sha256'], quote=row['host_quote']))
    extras = row.get('corroborating_sources', [])
    if not isinstance(extras, list):
        raise ValueError('invalid reviewed corroborating sources')
    for source in extras:
        if not isinstance(source, dict):
            raise ValueError('invalid reviewed corroborating source')
        source_url = source.get('capture_url') or source.get('url')
        digest, quote = source.get('sha256'), source.get('quote')
        parsed = urlsplit(source_url) if isinstance(source_url, str) else None
        if not (parsed and parsed.scheme in {'http', 'https'} and parsed.hostname
                and isinstance(digest, str) and re.fullmatch(r'[a-fA-F0-9]{64}', digest)
                and isinstance(quote, str) and quote.strip()):
            raise ValueError('invalid reviewed corroborating source')
        fragment = dict(url=source_url, sha256=digest, quote=quote)
        if fragment not in sources:
            sources.append(fragment)
    return sources

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
PIPE_ADVISER_FIELD = re.compile(r"(?:^|\|)\s*advis[oe]rs?(?:\(s\))?\s*:\s*([^|\n]+)", re.I)


def named_advisers(quote):
    """Keep all names in a pipe-delimited adviser field, but no later metadata.

    Repository evidence uses semicolons between co-advisers, e.g. ``Creators
    Zhang, Jiawei | Advisor: Li, Bo; Zhang, Ce | Published 2026``. A semicolon
    before another labelled field remains a boundary. Unstructured quotes keep
    the conservative existing parser.
    """
    fields = PIPE_ADVISER_FIELD.findall(quote) if '|' in quote else []
    if fields:
        return ' '.join(re.split(r';\s*[\w ()-]{1,40}:', field, maxsplit=1)[0] for field in fields)
    return ' '.join((m.group(1) or m.group(2) or '') for m in ADVISER_NAMED.finditer(quote))


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
        named = named_advisers(q)
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
    p = P.data('relation-evidence.json', school, root=Path(here))
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
                        q['original_sha256'] = q['sha256'].split(',') if ',' in q['sha256'] else q['sha256']  # several captures: a list
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
    # Stanford's final advisee section can lead straight into publications: the 2026-11-09 Greg Zaharchuk
    # profile names Ashwin Kumar before "All Publications", which is not part of the student's name.
    m = re.search(r'Doctoral Dissertation (?:Co-)?Advisor \(AC\)\s+(.+?)(?=\s+(?:Doctoral|Postdoctoral|Master|Undergraduate|Reader|Orals|Current|(?:All |Selected )?Publications\b)|\s*$)', q)
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


HASHED = re.compile(r'^[0-9a-f]{64}(?:,[0-9a-f]{64})*$')


def drop_hashless_sources(stu, n):
    """R-STU-12 (2026-10-31, coordinator; validation findings): a relation source without a sha256 is no evidence and
    leaves the relation (CMU's site collection cited 2,260 bare URLs that the R-STU-08 re-capture could not quote); a
    relation left with no source, and a student left with no relation, leave the lab. Runs after the re-captured
    evidence is applied. Returns the dropped students [{pi, student, name}] for the report."""
    dropped = []
    for pi, S in stu.items():
        for sid, r in list(S.items()):
            rels = []
            for rel in r['relations']:
                srcs = rel.get('sources') or []
                kept = [q for q in srcs if HASHED.match(str(q.get('sha256') or ''))]
                if len(kept) < len(srcs):
                    n['relation_sources_dropped_hashless'] += len(srcs) - len(kept)
                    if not kept:
                        n['relations_dropped_no_hashed_source'] += 1
                        continue
                    rel = dict(rel, sources=kept)
                rels.append(rel)
            if r['relations'] and not rels:
                del S[sid]
                dropped.append(dict(pi=pi, student=sid, name=r['name']))
                n['students_dropped_no_hashed_source'] += 1
            else:
                r['relations'] = rels
    return dropped


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
            if t_:
                by_name[t_[-1]].append(person)
    return by_name


def renamed_pis(pis, school=None, here=None):
    """{census name: built name} of PIs a reviewed display_name renamed (R-PAP-34): reviewed and researched files that key a person by the census
    placeholder ('Y Z') still reach the PI built as 'Yang Zhang'. With a school, the spelling a reviewed census-name-aliases pair merged away
    ('Polo Chau' -> 'Duen Horng "Polo" Chau', Georgia Tech 2026-11-18) maps to the built PI too, so students, advisees and papers keyed by the older
    spelling in reviewed files are not dropped by the merge."""
    out = {p['censusName']: p['pi'] for p in pis if p.get('censusName')}
    if school:
        out.update(merged_alias_spellings(school, pis, here))
    return out


def merged_alias_spellings(school, pis, here=None):
    """{merged-away spelling: built PI name} from hierarchy/<school>/reviewed/census-name-aliases.json (explicit, source-backed pairs only)."""
    f = P.data('census-name-aliases.json', school, root=here) if here is not None else P.data('census-name-aliases.json', school)
    if not Path(f).exists():
        return {}
    built = {p['pi'] for p in pis}
    out = {}
    review = read(f) or {}
    for row in review.get('rows') or []:
        a, b = row.get('name_a'), row.get('name_b')
        if a in built and b not in built:
            out[b] = a
        elif b in built and a not in built:
            out[a] = b
    # Native PI merges are validated against the eligible census and original
    # source evidence before student ingestion. Their historical spellings still
    # key accepted student and publication files; retain those relationships.
    for row in review.get('native_pi_merges') or []:
        canonical = row['canonical']
        if canonical not in built:
            continue
        for alias in row['aliases']:
            if alias in built or (alias in out and out[alias] != canonical):
                raise ValueError('Conflicting source-reviewed native PI alias: ' + alias)
            out[alias] = canonical
    return out


def external_member_id(school, pi, name, source_record_key=None, *, lab_scoped=False):
    """Retain legacy Latin IDs; unromanized names need a nonempty, lab-scoped identity (R-HIER-03)."""
    slug = re.sub('[^a-z0-9]+', '-', name.lower()).strip('-')
    if not slug or CJK.search(name):
        key = json.dumps([pi, unicodedata.normalize('NFKC', name).strip()], ensure_ascii=False)
        slug = 'name-' + hashlib.sha256(key.encode()).hexdigest()[:24]
    if source_record_key is not None:
        if not isinstance(source_record_key, str) or not source_record_key.strip():
            raise ValueError('source_record_key must be a nonempty string')
        key = json.dumps([pi, source_record_key], ensure_ascii=False)
        slug += '-source-' + hashlib.sha256(key.encode()).hexdigest()[:20]
    if type(lab_scoped) is not bool or (lab_scoped and source_record_key is not None):
        raise ValueError('lab_scoped_identity must be boolean and separate from unresolved source_record_key')
    if lab_scoped:
        key = json.dumps([school, pi, unicodedata.normalize('NFKC', name).strip()], ensure_ascii=False)
        slug += '-lab-' + hashlib.sha256(key.encode()).hexdigest()[:20]
    return f'ext:{school}:{slug}'


def compatible_source_records(a, b):
    """Explicit unresolved source records cannot be consolidated by name alone."""
    ka, kb = a.get('sourceRecordKey'), b.get('sourceRecordKey')
    return ka == kb if ka is not None or kb is not None else True


def researched_relation_type(role, withheld=False):
    """Only explicit student/degree roles imply advising; other lab roles remain memberships."""
    student_roles = {'student', 'phd', 'doctoral', 'masters', 'master', 'ms', 'msc', 'mphil', 'meng', 'undergraduate', 'undergrad', 'graduate', 'alumni', 'alumnus'}
    return 'researched_advising' if not withheld and (role is None or role in student_roles) else 'researched_membership'


def reviewed_additional_sources(row):
    """Keep separately captured identity/date evidence alongside the primary claim."""
    sources = row.get('additional_sources', [])
    if not isinstance(sources, list):
        raise ValueError('additional_sources must be a list of hashed source records')
    for source in sources:
        if (not isinstance(source, dict) or not isinstance(source.get('url'), str)
                or not source['url'].startswith(('http://', 'https://'))
                or not isinstance(source.get('sha256'), str)
                or not re.fullmatch(r'[0-9a-f]{64}', source['sha256'])
                or not isinstance(source.get('quote'), str) or not source['quote'].strip()):
            raise ValueError('additional source needs url, SHA-256 and a quoted statement')
    return [dict(source) for source in sources]


def reviewed_relationship_type(row, role, withheld=False):
    """An explicit reviewed membership keeps its degree role without asserting PI advising.

    Omitted selectors retain the legacy role-based behavior. A present selector must be one of the
    two documented values; an advising selector cannot override visitor/nonstudent/withheld-role guards.
    """
    inferred = researched_relation_type(role, withheld)
    if 'relationship' not in row:
        return inferred
    relationship = row['relationship']
    if relationship == 'membership':
        return 'researched_membership'
    if relationship == 'advising' and inferred == 'researched_advising':
        return inferred
    raise ValueError(f"invalid reviewed relationship {relationship!r} for role {role!r}")


def unresolved_roster_observations(group):
    """Source observations remain visible without becoming people, memberships or links.

    A researched-evidence group may explicitly list ``unresolved_students``.
    These records require a reason and a hashed quote, and have no accepted
    identity or relationship years. They are carried only on the PI record.
    """
    if not group or 'unresolved_students' not in group:
        return []
    rows = group['unresolved_students']
    if not isinstance(rows, list):
        raise ValueError('unresolved_students must be a list of source observations')
    result = []
    for row in rows:
        if not isinstance(row, dict) or any(not isinstance(row.get(k), str) or not row[k].strip()
                                          for k in ('name', 'reason', 'url', 'sha256', 'quote')):
            raise ValueError('unresolved roster observation requires name, reason, url, sha256 and quote')
        if not re.fullmatch(r'[0-9a-f]{64}', row['sha256']) or not re.match(r'^https?://[^/\s]+', row['url']):
            raise ValueError('unresolved roster observation requires a SHA-256 and HTTP source URL')
        if row.get('status', 'unresolved') != 'unresolved' or any(row.get(k) for k in
                ('person', 'personId', 'personIds', 'student', 'years', 'relationship', 'work', 'works')):
            raise ValueError('unresolved roster observation cannot assert an accepted identity, dates or relationship')
        observed = dict(name=row['name'], reason=row['reason'], url=row['url'], sha256=row['sha256'],
                        quote=row['quote'], status='unresolved')
        for key in ('source_record_id', 'captured', 'section', 'source_name'):
            if key in row:
                if not isinstance(row[key], str) or not row[key].strip():
                    raise ValueError('unresolved roster observation has invalid ' + key)
                observed[key] = row[key]
        result.append(observed)
    return result


def researched(ctx, stu, by_name):
    """R-STU-01: researched advisees and lab members with a quote and hash (gap-evidence.json and RESEARCHED_FILES); a
    unique collection person of that name takes the record, else an ext:<school>:<name> id."""
    HERE, school, pis, ge, n = ctx.here, ctx.school, ctx.pis, ctx.ge, ctx.n
    ren = renamed_pis(pis, school, HERE)
    ge = {ren.get(k, k): v for k, v in ge.items()}
    fe = collections.defaultdict(lambda: dict(students=[]))  # researched students: thin labs and the thesis hunt
    unresolved = collections.defaultdict(list)
    for pi, group in ge.items():
        unresolved[pi].extend(unresolved_roster_observations(group))
    for fn in RESEARCHED_FILES:
        if P.data(fn, school, root=HERE).exists():
            for r in read(P.data(fn, school, root=HERE)):
                fe[ren.get(r['pi'], r['pi'])]['students'] = list(fe[ren.get(r['pi'], r['pi'])]['students']) + list(r.get('students') or [])
                unresolved[ren.get(r['pi'], r['pi'])].extend(unresolved_roster_observations(r))
    for s_ in accepted_additions(school, 'students', HERE, ctx.n):  # LP-STU-01, accepted (docs/LAB-PAGES.md): one row per student
        fe[ren.get(s_['pi'], s_['pi'])]['students'] = list(fe[ren.get(s_['pi'], s_['pi'])]['students']) + [s_]
    dec_f = P.data('student-decisions.json', school, root=HERE)
    decisions = {ren.get(pi_, pi_): d_ for pi_, d_ in (read(dec_f) if dec_f.exists() else {}).items()}
    visiting_decided = {(pi_, SD.fold(nm_)) for pi_, d_ in decisions.items() for nm_, v_ in d_.items() if v_.get('decision') == 'visiting'}
    for p in pis:  # researched students (gap-evidence.json, few-students-evidence.json): a stated advisee or lab member, with its quote
        if unresolved.get(p['pi']):
            seen = set()
            p['unresolvedRosterObservations'] = []
            for observation in unresolved[p['pi']]:
                key = tuple(observation.get(k) for k in ('name', 'url', 'sha256', 'source_record_id'))
                if key not in seen:
                    p['unresolvedRosterObservations'].append(observation)
                    seen.add(key)
        for s_ in list((ge.get(p['pi']) or {}).get('students') or []) + list((fe.get(p['pi']) or {}).get('students') or []):
            if not (s_.get('name') and s_.get('quote') and s_.get('sha256')):
                continue
            if SD.excluded(decisions, p['pi'], s_['name']):
                n['researched_students_review_excluded'] += 1
                continue
            if re.search(r"['\u2019]s$", s_['name']):
                n['researched_students_possessive_label_dropped'] += 1
                continue
            years_ = as_years(s_.get('years'), n)
            placed = bool(years_) and max(years_) >= WINDOW_START and min(years_) <= int(TODAY[:4])
            if not placed and s_.get('relationship') != 'membership':
                n['researched_students_without_window_year_held'] += 1
                continue
            t_ = toks(s_['name']); nm_ = Name([s_['name']])
            source_key = s_.get('source_record_key')
            lab_scoped = s_.get('lab_scoped_identity', False)
            if type(lab_scoped) is not bool or (lab_scoped and source_key is not None):
                raise ValueError('lab_scoped_identity must be boolean and separate from unresolved source_record_key')
            match_ = [] if source_key is not None or lab_scoped else [q for q in by_name.get(t_[-1] if t_ else '', []) if nm_.match(q['name'])]
            sid = match_[0]['id'] if len(match_) == 1 else external_member_id(school, p['pi'], s_['name'], source_key, lab_scoped=lab_scoped)
            # a lab-page entry whose role the audit withheld (role null, role_basis withheld_*: Berkeley, 2026-11-01) is a plain lab MEMBER, not a
            # student: it may be a postdoc or a visitor. roles ['member'] shows as 'Lab member' on the site (build-cs-hierarchy.py role_label).
            role_ = 'visiting' if (p['pi'], SD.fold(s_['name'])) in visiting_decided else s_.get('role')   # R-STU-17: decided `visiting` in student-decisions.json
            withheld = bool(s_.get('role_basis')) and not role_
            if withheld:
                n['students_role_withheld'] += 1
            if role_ == 'visiting':
                n['students_role_visiting'] += 1
            relation_type = reviewed_relationship_type(s_, role_, withheld)
            r = stu[p['pi']].setdefault(sid, dict(person=sid, name=match_[0]['name'] if len(match_) == 1 else s_['name'],
                                                  roles=['member'] if withheld else [role_ or 'student'], relations=[]))
            r['roles'] = list(dict.fromkeys(r['roles'] + (['member'] if withheld else [role_ or 'student'])))
            if source_key is not None:
                r['sourceRecordKey'] = source_key
            if lab_scoped:
                r['identityScope'] = 'lab'
            aliases = s_.get('reviewed_aliases', [])
            if (not isinstance(aliases, list)
                    or any(not isinstance(alias, str) or not alias.strip() for alias in aliases)):
                raise ValueError('reviewed_aliases must be a list of source-established names')
            alias_sources = reviewed_additional_sources(dict(additional_sources=s_.get('alias_evidence', [])))
            if aliases and not alias_sources:
                raise ValueError('reviewed_aliases require separately hashed alias_evidence')
            if aliases:
                r['aliases'] = list(dict.fromkeys(list(r.get('aliases') or []) + aliases))
            # a visiting student is a lab member, never an adviser relation (R-STU-17): researched_membership, like `member`
            r['relations'].append(dict(type=relation_type, years=years_,
                                       role=role_, **({'role_withheld': True} if withheld else {}),
                                       sources=researched_sources(s_) + reviewed_additional_sources(s_) + alias_sources,
                                       # automatic, unreviewed lab-page students stay marked (Michigan request 6: the accuracy sample stratifies on it)
                                       **({'auto': True} if s_.get('auto') else {})))
            if s_.get('auto'):
                r['auto'] = True


def add_corroborated(ctx):
    """R-STU-20: lab-page student rows the acceptance gate did not wire, kept when the PI's own byline corroborates them (tools/pihier/
    corroborated.py). Runs after the lab papers are built and before the links; the student then links through the usual bases."""
    from . import corroborated as CO
    school, pis, stu, n = ctx.school, ctx.pis, ctx.stu, ctx.n
    ctx.corroborated = []
    if not n.get('labpage_additions_students_not_wired:not_accepted'):
        return
    papers_by_pi = collections.defaultdict(list)
    for r_ in ctx.rows:
        papers_by_pi[r_['pi']].append(r_)
    existing = {p['pi']: [r_['name'] for r_ in stu[p['pi']].values()] + [a for r_ in stu[p['pi']].values() for a in r_.get('aliases') or []] for p in pis}
    dbs = CO.open_capture_dbs(school, ctx.here)
    rows = CO.corroborated_rows(school, papers_by_pi, existing, dbs, ctx.here, n)
    by_name = people_by_family(ctx.people)
    for s_, works in rows:
        t_ = toks(s_['name']); nm_ = Name([s_['name']])
        match_ = [q for q in by_name.get(t_[-1] if t_ else '', []) if nm_.match(q['name'])]
        sid = match_[0]['id'] if len(match_) == 1 else external_member_id(school, s_['pi'], s_['name'])
        role_ = s_['role']
        r = stu[s_['pi']].setdefault(sid, dict(person=sid, name=match_[0]['name'] if len(match_) == 1 else s_['name'], roles=[role_], relations=[]))
        r['relations'].append(dict(type=researched_relation_type(role_), years=as_years(s_.get('years'), n), role=role_,
                                   sources=[dict(url=s_.get('capture_url') or s_['url'], sha256=s_['sha256'], quote=s_['quote'])], auto=True, corroborated=True))
        r['auto'] = True
        n['labpage_students_corroborated_wired'] += 1
        ctx.corroborated.append(dict(pi=s_['pi'], student=s_['name'], role=role_, role_basis=s_.get('role_basis'), years=s_['years'], works=works[:6], n_works=len(works)))
    # a wired row can be the second spelling of a student the lab holds ('Christophe' beside 'Chris', R-STU-20 rule 4 compares names only): the reviewed
    # same_person verdicts apply again, after the wiring (Stanford Gyurgyik, 2026-11-11)
    n['student_records_merged'] += identity_review(ctx, stu)
    n['pis_with_students'] = sum(bool(stu[p['pi']]) for p in pis); n['students'] = len({x for v in stu.values() for x in v}); n['lab_student_pairs'] = sum(len(v) for v in stu.values())


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
            sid = match_[0]['id'] if len(match_) == 1 else external_member_id(school, p['pi'], sname)
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
            tgt = next((k for k in keep if compatible_source_records(k, r) and (
                        Name([k['name']] + k.get('aliases', [])).match(r['name']) or Name([r['name']]).match(k['name'])
                        or any(same_student(r['name'], q, initials=False) for q in [k['name']] + k.get('aliases', [])))), None)
            if tgt is None:  # R-STU-13: the same, with the initial-only tokens optional; counted apart
                tgt = next((k for k in keep if compatible_source_records(k, r) and any(initials_optional(r['name'], q) for q in [k['name']] + k.get('aliases', []))), None)
                if tgt is not None:
                    n['student_records_merged_initials_optional'] += 1
                    ctx.initials_merges.append(dict(pi=p['pi'], kept=[tgt['person'], tgt['name']], merged=[r['person'], r['name']]))
            if tgt is None:
                keep.append(r)
            else:
                tgt['relations'] += r['relations']; tgt['roles'] = list(dict.fromkeys(list(tgt.get('roles') or []) + list(r.get('roles') or [])))
                tgt.setdefault('aliases', []).append(r['name']); tgt.setdefault('merged', []).append(r['person']); merged_students += 1
        stu[p['pi']] = {r['person']: r for r in keep}
    return merged_students


def identity_review(ctx, stu):
    """R-STU-04: hierarchy/student-identity-review.json 'same_person' verdicts merge two records of one lab. Returns the
    number merged."""
    HERE, school = ctx.here, ctx.school
    merged_students = 0
    # reviewed identities (hierarchy/student-identity-review.json, from the same-name research): two records of one lab
    # that are one person merge under the canonical name; 'different_people' verdicts only feed the chain audit
    rev_f = P.data('student-identity-review.json', root=HERE)
    rev = read(rev_f) if rev_f.exists() else []
    for x in rev:
        if x.get('scope') == 'cross_lab' or x.get('school') != school or x.get('verdict') != 'same_person' or x.get('pi') not in stu:
            continue
        S = stu[x['pi']]
        find = lambda i: next((k for k, r in S.items() if k == i or r.get('person') == i or i in (r.get('merged') or [])), None)   # a review may name the record's person id when the dict key is another id (Stanford Gyurgyik, 2026-11-11)
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


def queue_surname_typos(ctx, stu):
    """R-STU-13: two records of one lab with the same given name and family names one edit apart are queued for review
    (ctx.typo_pairs), never merged. Pairs the review file already judged (either verdict) are not queued again."""
    rev_f = P.data('student-identity-review.json', root=ctx.here)
    judged = {frozenset((x['a'][0], x['b'][0])) for x in (read(rev_f) if rev_f.exists() else [])
              if x.get('scope') != 'cross_lab' and x.get('school') == ctx.school and x.get('verdict')}
    for pi, S in stu.items():
        recs = list(S.values())
        for i, a in enumerate(recs):
            for b in recs[i + 1:]:
                if frozenset((a['person'], b['person'])) in judged:
                    continue
                if any(surname_typo(x, y) for x in [a['name']] + list(a.get('aliases') or []) for y in [b['name']] + list(b.get('aliases') or [])):
                    ctx.typo_pairs.append((pi, a['person'], b['person']))
    ctx.n['student_surname_typo_candidates'] = len(ctx.typo_pairs)


def typo_candidate_rows(ctx):
    """The queued pairs in the student-identity-review.json shape with `verdict` empty, and the supporting signals found:
    `shared_source_url` (both records cite the same page), `alias_of_other` (one name is the other's alias, or either
    name is one of the other's aliases) and `shared_paper` (the same lab paper is linked to both; a coauthor pair as
    often as a duplicate, so it is a lead, not a verdict)."""
    papers = collections.defaultdict(set)
    for x in ctx.sp:
        papers[(x['pi'], x['student'])].add(x['work'])
    rows = []
    for pi, ia, ib in ctx.typo_pairs:
        a, b = ctx.stu[pi].get(ia), ctx.stu[pi].get(ib)
        if not a or not b:
            continue
        urls = lambda r: {s.get('url') for rel in r['relations'] for s in rel.get('sources') or [] if s.get('url')}
        sig = []
        if urls(a) & urls(b):
            sig.append(dict(signal='shared_source_url', urls=sorted(urls(a) & urls(b))[:3]))
        if toks(a['name']) in [toks(x) for x in b.get('aliases') or []] or toks(b['name']) in [toks(x) for x in a.get('aliases') or []]:
            sig.append(dict(signal='alias_of_other'))
        if papers[(pi, ia)] & papers[(pi, ib)]:
            sig.append(dict(signal='shared_paper', works=sorted(papers[(pi, ia)] & papers[(pi, ib)])[:3]))
        rows.append(dict(school=ctx.school, pi=pi, a=[ia, a['name']], b=[ib, b['name']], verdict='', canonical_name=None, reason='', evidence=[],
                         signals=sig))
    return rows


def corrections(ctx, stu):
    """R-STU-04: hierarchy/student-corrections.json drops, renames or replaces the evidence of a record."""
    HERE, school, n = ctx.here, ctx.school, ctx.n
    # reviewed record corrections (hierarchy/student-corrections.json): drop a misplaced student from a lab, rename a
    # record keyed to the wrong person (the old name stays an alias), or replace a relation's mis-cut evidence
    corr_f = P.data('student-corrections.json', root=HERE)
    corr = read(corr_f) if corr_f.exists() else []
    def check_preimage(decision, member):
        expected = decision.get('expected_member_sha256')
        if 'expected_member_sha256' not in decision:
            return
        if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise ValueError('student correction needs a valid expected_member_sha256')
        if member is not None:
            actual = hashlib.sha256(json.dumps(member, ensure_ascii=False, sort_keys=True,
                                               separators=(',', ':')).encode()).hexdigest()
            if actual != expected:
                raise ValueError('student correction source preimage changed; review required: '
                                 + str((school, decision.get('pi'), decision['student'])))

    # Validate all applicable guards before any correction, and recheck immediately before use.
    for decision in corr:
        if decision.get('school') == school and 'roles' in decision:
            roles = decision['roles']
            if (decision.get('action') != 'replace_sources' or 'expected_member_sha256' not in decision
                    or not isinstance(roles, list) or not roles
                    or any(not isinstance(role, str) or not role.strip() for role in roles)):
                raise ValueError('student correction roles require guarded replace_sources and a nonempty role list')
        if 'expected_member_sha256' not in decision or decision.get('school') != school:
            continue
        group = stu.get(decision.get('pi')) or {}
        member = next((r for key, r in group.items()
                       if key == decision['student'] or decision['student'] in (r.get('merged') or [])), None)
        check_preimage(decision, member)
    for x in corr:
        S = stu.get(x.get('pi')) if x.get('school') == school else None
        k = next((k for k, r in (S or {}).items() if k == x['student'] or x['student'] in (r.get('merged') or [])), None)
        if not k:
            continue
        r = S[k]
        check_preimage(x, r)
        if x['action'] == 'drop':
            S.pop(k)
        elif x['action'] == 'rename':
            r.setdefault('aliases', []).append(r['name']); r['name'] = x['name']
            r['aliases'].extend(a for a in x.get('aliases') or [] if a not in r['aliases'])   # reviewed extra name forms (a byline form such as 'Panos Tigas')
            if x.get('person'):
                r.setdefault('merged', []).append(k); r['person'] = x['person']; S[x['person']] = S.pop(k)
        elif x['action'] == 'replace_sources':
            r['relations'] = [dict(type=x.get('type', 'researched_advising'), years=x['years'], role=x.get('role'), sources=x['sources'])]
            # Correct an unsupported displayed degree as well as its evidence. The original
            # accepted source remains immutable; an exact preimage guard demands renewed
            # review if another genuine role or source is added to this member.
            if 'roles' in x:
                r['roles'] = list(dict.fromkeys(x['roles']))
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
    queue_surname_typos(ctx, stu)
    n['student_records_merged'] = merged_students
    # re-captured evidence for the site collections' bare-URL relations (R-STU-08, 2026-10-29)
    n.update(apply_relation_evidence(stu, school, HERE))
    ctx.unevidenced = drop_hashless_sources(stu, n)  # R-STU-12
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
