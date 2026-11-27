"""Student-paper links: a lab student on a lab paper's byline. R-LNK-01 (the link bases), R-LNK-02/02a/02b (the given-name
guard, names.given_conflict), R-LNK-03 (within-lab byline matching), R-LNK-05 (links carry their evidence)."""
import collections, re, unicodedata

import atlas_paths as P

from .names import EAST_ASIAN_FAMILY, LETTERS, Name, one_edit, byline_name, clean_person_name, given_conflict, gwords, name_variants, nick_ok, student_on_byline, toks
from .role_cues import VISITING_NOT_STUDENT, VISITING_STUDENT, student_by_entry
from .students import relation_names_other_adviser

# R-STU-19 (2026-11-05, owner: UChicago/Georgia Tech stage-9 samples). Rule A: an initials-only name match ('Y. Zhou') cannot link a student to
# a hyper-authored paper. Over the 2,606 byline links of the nine packages that match on a name the paper does not spell out in full, the
# byline sizes run: 540 with 10+ authors, 147 with 20+, 74 with 30+, 37 with 50+, 11 with 100+; a lab paper's median byline is 5, so 50 is
# far outside the lab-paper range and keeps every collaboration-scale byline out (UChicago: four 'Zhou' initials on a 2,938-author ATLAS
# paper linked to one student). Rule B: the wide-window routes (full-name and within-lab byline matches) need the person to hold a student role and no source quote naming other
# advisers only (Georgia Tech: a research scientist, a visiting researcher and a student of two other advisers entered by full name).
HYPER_AUTHORS = 50
STUDENT_ROLE = re.compile(r'^graduate$|phd|doctoral|master|undergrad|student|alumn|intern')
NON_STUDENT_ROLE = re.compile(r'postdoc|visit|research_?(?:staff|scientist)|scientist|staff|faculty|professor|other')


def initials_only(raw):
    """The byline spells no given name out: every token before the family name is one letter ('Y. Zhou', 'Zhou, Y. H.')."""
    t = toks(byline_name(raw))
    return len(t) >= 2 and all(len(x) == 1 for x in t[:-1])


def hyper_authored(r):
    return len(r.get('byline') or []) >= HYPER_AUTHORS


def student_role_ok(s):
    """R-STU-19 rule B: some role is a student role (phd, masters, undergraduate, graduate, student, alumnus, intern), not only research scientist, visitor, postdoc,
    staff or other. Owner 2026-11-06: (1) a visiting STUDENT counts (role `visiting`, R-STU-17: visiting PhD, master's or undergraduate students; visiting
    scholars, professors, faculty and researchers stay out, also when the entry says so); (2) a `member` row counts when the entry's own words
    (right after the name) or else its heading (the nearest role cue before the name) say student: 'David Deriso (Ph.D. Student, CS)', 'PhD Students: A, B'."""
    roles = [str(x).lower() for x in s.get('roles') or [] if x] or [str(rel.get('role') or '').lower() for rel in s.get('relations') or []]
    if any(STUDENT_ROLE.search(x) and not NON_STUDENT_ROLE.search(x) for x in roles):
        return True
    quotes = [q.get('quote') or '' for rel in s.get('relations') or [] for q in rel.get('sources') or []]
    names = [n for n in [s.get('name')] + list(s.get('aliases') or []) if n]
    def nearest_visiting(q):   # the nearest visiting cue before the name decides: 'Visiting scholar (2019) from Purdue Alvaro X' is a scholar
        best = None
        for n in names:
            j = q.rfind(n)
            if j < 0:
                continue
            # A person's explicit position beats the list heading. Only read
            # an immediate title/experience label or a self-introduced bio's
            # current-position sentence, never an arbitrary later visitor.
            after = q[j + len(n):].lstrip(' ,:;()–—-')
            title = re.match(r'(?:[A-Z][\w.-]*\s+Experience\s+)?', after)
            own = after[title.end():]
            first = re.escape(n.split()[0])
            bio = re.match(first + r"(?:\s+[A-Z][\w’'-]+){0,4}\s+is\s+[^.!?]{0,400}?[.]\s+(?:He|She|They)\s+(?:is|are)\s+currently\s+(?:a\s+)?", after)
            if bio:
                own = after[bio.end():]
            for kind, rx in (('student', VISITING_STUDENT), ('not', VISITING_NOT_STUDENT)):
                if rx.match(own):
                    return kind
            for kind, rx in (('student', VISITING_STUDENT), ('not', VISITING_NOT_STUDENT)):
                for m in rx.finditer(q[:j]):
                    if best is None or m.end() > best[0]:
                        best = (m.end(), kind)
        return best[1] if best else None
    if 'visiting' in roles:
        return not any(nearest_visiting(q) == 'not' for q in quotes)
    if 'visitor' in roles:   # a visitors' list is not a student heading: only a visiting-student cue nearest to the name counts
        return any(nearest_visiting(q) == 'student' for q in quotes)
    if 'member' in roles:
        return any(student_by_entry(q, names) for q in quotes)
    return False


def student_link_role_eligible(s):
    """Share the builder's role boundary with audits; unlabelled legacy rows keep their existing treatment."""
    typed = s.get('roles') or any(rel.get('role') for rel in s.get('relations') or [])
    return not typed or student_role_ok(s)


def pi_names_of(ctx, pi):
    """The PI's names for the R-STU-19 adviser test (none known: the test then passes)."""
    pid0 = getattr(ctx, 'pid0', None) or {}
    return (pid0.get(pi) or {}).get('names') or []


def pi_is_adviser(s, pi_names):
    """R-STU-19 rule B: no relation of the student names other advisers only (the student's own roster line)."""
    rels = s.get('relations') or []
    return not (rels and all(relation_names_other_adviser(rel, pi_names) for rel in rels))

def student_relation_years(s):
    """Later dated staff/postdoc episodes do not extend a student's date window."""
    relations = s.get('relations') or []
    if any(rel.get('role') for rel in relations):
        relations = [rel for rel in relations if
                     (not rel.get('role') and student_role_ok(s)) or
                     student_role_ok(dict(s, roles=[rel.get('role') or ''], relations=[rel]))]
    return [int(y) for rel in relations for y in rel.get('years') or [] if str(y).isdigit()]


def near_relation(s, year):
    """The paper's year is within three years of the student's recorded advising or membership (no years: any)."""
    ys = student_relation_years(s)
    return not ys or not year or min(ys) - 3 <= int(year) <= max(ys) + 3


DISSERTATION_BEFORE = 6   # R-LNK-06: a PhD takes up to six years; the dissertation year is the END of the student's years with the lab
MAX_AUTHORS = 15          # R-LNK-06/07: the extensions below never apply to a hyper-authored paper


def vowel_edit(a, b):
    """R-LNK-07: one insertion, deletion, adjacent transposition or vowel-for-vowel substitution ('Aiden'/'Aidan', 'Connor'/'Conor', 'Makena'/
    'Maken'); a consonant substituted for another ('Kavin'/'Navin', 'Anna'/'Anja') makes a different name, not a spelling."""
    if not one_edit(a, b):
        return False
    if len(a) == len(b):
        d = [i for i in range(len(a)) if a[i] != b[i]]
        return len(d) == 2 or (a[d[0]] in 'aeiouy' and b[d[0]] in 'aeiouy')
    return True


def dissertation_only(s):
    """R-LNK-06: every relation of the PhD student is a dissertation record (a DSpace record whose `dc.contributor.advisor` names the
    adviser) and so dates the END of the student's work with the lab: the recorded year is the degree year."""
    rels = s.get('relations') or []
    return bool(rels) and all(any('contributor' in (q.get('quote') or '') and 'advisor' in (q.get('quote') or '') for q in rel.get('sources') or [])
                              and (rel.get('role') or 'phd') == 'phd' for rel in rels)


def relation_source(student):
    """The student's roster evidence for a link: the first relation source with url, sha256 and quote (with the relation's
    type), else the first source at all (the evidence check reports it), else None."""
    srcs = [(rel.get('type'), q) for rel in student.get('relations') or [] for q in rel.get('sources') or []]
    full = [(t, q) for t, q in srcs if q.get('url') and q.get('sha256') and q.get('quote')]
    # a quote that names the PI or the lab first; a re-captured student-only quote (names_pi false, R-STU-08) after it
    best = next(((t, q) for t, q in full if q.get('names_pi') is not False), None) or next(iter(full), None) or (srcs[0] if srcs else None)
    if not best:
        return None
    out = dict(relation=best[0], url=best[1].get('url'), sha256=best[1].get('sha256'), quote=best[1].get('quote'))
    if best[1].get('names_pi') is False:
        out['names_pi'] = False
    if best[1].get('capture_url'):
        out['capture_url'] = best[1]['capture_url']
    return out


def exclude_links(sp, doc):
    """Reviewed per-link exclusions (student-link-exclusions.json, version 1): each {pi, student (the member's name), oa, why, evidence}
    removes that one candidate student-paper link and nothing else (the lab paper and the other links stay). Returns (kept, excluded, unmatched).
    The link stays visible in the review file, never deleted from evidence."""
    want = {}
    for e in (doc or {}).get('exclusions') or []:
        if not all(isinstance(e.get(k), str) and e[k].strip() for k in ('pi', 'student', 'oa', 'why')):
            raise ValueError('student link exclusion needs pi, student, oa and why')
        want[(e['pi'], e['student'], e['oa'])] = False
    kept = []
    for x in sp:
        k = (x['pi'], x['name'], x['oa'])
        if k in want:
            want[k] = True
        else:
            kept.append(x)
    return kept, sum(want.values()), sum(not v for v in want.values())


def link_students(ctx):
    """ctx.sp: every (lab paper, lab student) link with its basis, byline and roster source; the guard's samples."""
    rows, stu, pls, n = ctx.rows, ctx.stu, ctx.pls, ctx.n
    sp = []
    # every reading of a student's name: the name, its aliases, and parenthesized forms ('Fatma Imamoglu (Deniz)')
    # one person under two labs (Netzorg: Bin Yu and Anumanchipalli) is one entry: the readings of every lab's record, so a reviewed alias in one lab (Robin)
    # is not lost to the other lab's record of the same person (2026-11-05, round-r2 Berkeley verdict)
    forms = {}
    for v in stu.values():
        for sid, s in v.items():
            fs = [f for f in dict.fromkeys([s['name']] + list(s.get('aliases') or []) + [v_ for x_ in [s['name']] + list(s.get('aliases') or []) for v_ in name_variants(x_)])
                  if '(' not in f] or [s['name']]
            forms[sid] = list(dict.fromkeys(forms.get(sid, []) + fs))
    snm = {sid: [(Name([f]), toks(f)) for f in fs] for sid, fs in forms.items()}

    def on_byline(sid, b):
        return any(student_on_byline(nm_, tk_, b or '') for nm_, tk_ in snm[sid])

    def full_name_on(sid, b):
        """The byline spells the student's first given name and family name out in full (no initials)."""
        t = toks(byline_name(b))
        return len(t) >= 2 and any(len(tk_) >= 2 and len(tk_[0]) > 1 and t[0] == tk_[0] and t[-1] == tk_[-1] for _, tk_ in snm[sid])

    def wide_relation(s, year, full=False, nauthors=0):
        """Two years before to six after the recorded advising: recorded years are often a single roster observation.
        R-LNK-06 (2026-11-05): a PhD student known only from dissertation records is dated by the degree year, the END of the work:
        a full-name byline on a paper of at most MAX_AUTHORS authors counts from DISSERTATION_BEFORE years before it."""
        ys = student_relation_years(s)
        if not ys or not year:
            return True
        before = DISSERTATION_BEFORE if full and 0 < nauthors <= MAX_AUTHORS and dissertation_only(s) else 2
        return min(ys) - before <= int(year) <= max(ys) + 6
    # (2026-10-29, owner) every byline link passes a given-name guard: a byline whose first given name is a full word that
    # differs from every full given-name reading of the student is someone else ('Wei-Ning Chen' had been linked via
    # 'Wei-Chen Chen'). A middle name used as the preferred given name ('Xiang Lisa Li' / 'Lisa Li'), hyphen/space
    # variants ('Hong-Xing Yu' / 'Hongxing Yu'), nickname pairs and an order swap ('Zhang Wei') stay links.
    guard_n = collections.Counter()

    def student_given_conflict(sid, raw, strict=False, pi=None):
        """The given-name guard (module-level given_conflict) for one of this school's students."""
        return given_conflict(forms[sid], raw, strict=strict, pi=pi, recur=recur, lab_names=lab_names)

    recur = collections.Counter()  # (lab, byline name words) -> number of the lab's papers carrying it
    for r_ in rows:
        for key in {' '.join(gwords(b)) for bl, _ in r_['_bylines'] for b in bl}:
            recur[(r_['pi'], key)] += 1
    lab_names = {pi_: {' '.join(gwords(clean_person_name(f))) for sid in S_ for f in forms[sid]} for pi_, S_ in stu.items()}

    def byline_ok(sid, raw, how, pi=None, r=None):
        # Distinct reviewed source profiles may have the same full name. Neither a school
        # affiliation nor a nearby observation year disambiguates their authorship.
        if stu.get(pi, {}).get(sid, {}).get('sourceRecordKey') is not None:
            return False
        return how(sid, raw) and not student_given_conflict(sid, raw, pi=pi) and not (r is not None and hyper_authored(r) and initials_only(raw))
    guard_samples, guard_kept_samples = [], []

    # (2026-10-29, owner) within-lab byline matching (the link_sweep.py measurement as a rule): a byline author who is
    # exactly one student of the lab by family name (the last token, or for a 3+ token student name the second-to-last,
    # a two-part family name the byline cuts: 'Bruno Schmitt Antunes' / 'Bruno Schmitt'; either half of a hyphenated
    # one; letters normalized with LETTERS) and given name (equal, an initial, a nickname pair, or the same letters
    # without hyphens); the order swap only for two-token names; family names of 2+ letters; within two years before to
    # six after the recorded years
    def sw_forms(t, student):
        if len(t) < 2:
            return []
        out = [(t[-1], t[0])]
        if len(t) == 2:
            out.append((t[0], t[1]))
        elif student:
            out.append((t[-2], t[0]))
        if '-' in t[-1]:
            out += [(q, t[0]) for q in t[-1].split('-')]
        return [(f.replace('-', ''), g) for f, g in out if len(f.replace('-', '')) >= 2]

    def sw_toks(x):
        x = unicodedata.normalize('NFKD', byline_name(str(x or '').translate(LETTERS)).replace('\u2013', '-').replace('\u2014', '-'))
        x = re.sub(r'\([^)]*\)', ' ', ''.join(c for c in x if not unicodedata.combining(c)).lower())
        return [t for t in re.split(r"[^a-z\-]+", x.replace("'", '')) if t and t not in ('jr', 'sr', 'ii', 'iii', 'iv', 'phd', 'dr')]

    def sw_given(a, b):
        a2, b2 = a.replace('-', ''), b.replace('-', '')
        return a2 == b2 or nick_ok(a2, b2) or (len(a2) == 1 and b2.startswith(a2)) or (len(b2) == 1 and a2.startswith(b2))

    sw_names = {sid: [sw_toks(clean_person_name(f)) for f in fs] for sid, fs in forms.items()}  # catalogue junk cleaned ('Li,M. Eng.Massachusetts ... Wang')
    sw_index = {}  # per lab: family-name reading -> students
    for pi_, S_ in stu.items():
        ix = collections.defaultdict(set)
        for sid in S_:
            for st in sw_names[sid]:
                for f_, _ in sw_forms(st, True):
                    ix[f_].add(sid)
        sw_index[pi_] = ix

    def sw_variant(sid, bt):
        """R-LNK-07 (2026-11-05): the family name written the same way (read as the family name, never through the order swap, which
        would turn a family-name typo into a match: 'Dor Mintzer' / 'Dor Minzer', 'Swarup Sahoo' / 'Swarun Kumar') and a first given name
        of 5+ letters one vowel substitution, insertion, deletion or transposition apart: a spelling or transliteration variant ('Aiden'/'Aidan', 'Connor'/'Conor').
        Not under an East Asian family name ('Yue'/'Yuan' are different people)."""
        if len(bt) < 2:
            return False
        fam, g2 = bt[-1].replace('-', ''), bt[0].replace('-', '')
        for st in sw_names[sid]:
            if len(st) >= 2 and st[-1].replace('-', '') == fam and fam not in EAST_ASIAN_FAMILY:
                g1 = st[0].replace('-', '')
                if min(len(g1), len(g2)) >= 5 and g1 != g2 and vowel_edit(g1, g2):
                    return True
        return False

    def sw_same(sid, bt):
        return any(f1 == f2 and sw_given(g1, g2) for st in sw_names[sid] for f1, g1 in sw_forms(st, True) for f2, g2 in sw_forms(bt, False))

    for r in rows:
        S = stu.get(r['pi']) or {}
        if not S:
            continue
        done_ = set(); linked_by_collection = {}
        for sid, s in S.items():
            # A nonstudent member may coauthor the PI's paper and have a dated lab
            # membership record, but that does not make this a student link.
            # Keep a separate recorded student role when one exists.
            if not student_link_role_eligible(s):
                continue
            l = next((l for l in pls[sid] if r['work'] and l['work'] == r['work']), None)
            if l:
                done_.add(sid); linked_by_collection[sid] = True
                sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status=l.get('status'), basis='collection_person_link'))
            elif (b_ := next((b for _, bs in r['_bylines'] for b in bs if byline_ok(sid, b, on_byline, r['pi'], r)), None)) is not None:
                # the student's name on this lab paper's byline, on an authorship that lists the school
                done_.add(sid); sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status='candidate', basis='byline_name_with_school_affiliation', byline=b_))
            elif near_relation(s, r['year']) and (b_ := next((b for bl, _ in r['_bylines'] for b in bl if byline_ok(sid, b, on_byline, r['pi'], r)), None)) is not None:
                # the PI's own advisee named on the PI's lab paper (an authorship without affiliations, e.g. an ACL
                # Anthology record), within three years of the recorded advising
                done_.add(sid); sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status='candidate', basis='advisee_name_on_lab_paper_byline', byline=b_))
            elif wide_relation(s, r['year'], True, len(r['byline'])) and student_role_ok(s) and pi_is_adviser(s, pi_names_of(ctx, r['pi'])) \
                    and (b_ := next((b for bl, _ in r['_bylines'] for b in bl if byline_ok(sid, b, full_name_on, r['pi'], r)), None)) is not None:
                # the lab's own student by full name on the lab's own paper, outside the narrow window (2026-10-28:
                # recorded years are often one roster observation; alumni keep publishing with the lab)
                done_.add(sid); sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status='candidate', basis='full_name_on_lab_paper_byline', byline=b_))
        for sid, s in S.items():  # links the guard took away (counted, with a sample, in the report)
            bl_all = [b for bl, _ in r['_bylines'] for b in bl]
            if sid in done_:
                used = [b for b in bl_all if on_byline(sid, b) or full_name_on(sid, b)]
                if not linked_by_collection.get(sid) and used and all(student_given_conflict(sid, b, strict=True) for b in used):
                    guard_n['kept_prefix_or_spelling_variant'] += 1  # the literal guard would have removed it
                    if len(guard_kept_samples) < 40:
                        guard_kept_samples.append(dict(pi=r['pi'], student=s['name'], byline=used[0], oa=r['oa']))
                continue
            unguarded = [b for _, bs in r['_bylines'] for b in bs if on_byline(sid, b)] \
                + ([b for b in bl_all if on_byline(sid, b)] if near_relation(s, r['year']) else []) \
                + ([b for b in bl_all if full_name_on(sid, b)] if wide_relation(s, r['year']) else [])
            if unguarded:
                b0 = unguarded[0]; hy = '-' in byline_name(b0).split(' ')[0] or any('-' in str(f).split(' ')[0] for f in forms[sid])
                guard_n['removed_' + ('hyphenated_given' if hy else 'different_full_given')] += 1
                if len(guard_samples) < 40:
                    guard_samples.append(dict(pi=r['pi'], student=s['name'], byline=b0, oa=r['oa']))
        for raw in dict.fromkeys(b for bl, _ in r['_bylines'] for b in bl):
            bt = sw_toks(raw)
            cand_ = {sid for f2, _ in sw_forms(bt, False) for sid in sw_index.get(r['pi'], {}).get(f2, ())}
            hits_ = [sid for sid in cand_ if sw_same(sid, bt)]
            plain_ = len(hits_) == 1
            if not hits_ and 0 < len(r['byline']) <= MAX_AUTHORS:  # R-LNK-07: no exact reading; a one-edit given-name variant of exactly one student
                hits_ = [sid for sid in cand_ if sw_variant(sid, bt)]
                # never when the student's own spelling is on the same paper (two people), nor for an initial or a second variant of the lab
                if hits_ and any(sw_same(hits_[0], sw_toks(o)) for o in r['byline']):
                    hits_ = []
            if len(hits_) == 1 and hits_[0] not in done_ and wide_relation(S[hits_[0]], r['year']) and not student_given_conflict(hits_[0], raw) \
                    and student_role_ok(S[hits_[0]]) and pi_is_adviser(S[hits_[0]], pi_names_of(ctx, r['pi'])) \
                    and S[hits_[0]].get('sourceRecordKey') is None \
                    and not (hyper_authored(r) and initials_only(raw)):
                sid = hits_[0]; done_.add(sid)
                if not plain_:
                    n['link_within_lab_spelling_variant'] += 1
                sp.append(dict(pi=r['pi'], student=sid, name=S[sid]['name'], work=r['work'], oa=r['oa'], status='candidate', basis='within_lab_byline_match', byline=raw))
    n.update({'link_guard_' + k: v for k, v in guard_n.items()})
    # every byline link carries its evidence (2026-10-29, build-time evidence check): the work, the exact byline string
    # matched, and the student's own roster source (the first relation source with url, sha256 and a verbatim quote)
    for x in sp:
        x['relation_source'] = relation_source(stu[x['pi']].get(x['student']) or {})
    _ex = P.data('student-link-exclusions.json', ctx.school, root=ctx.here)
    if _ex.exists():
        import json as _json
        doc = _json.loads(_ex.read_text())
        if doc.get('version') != 1 or doc.get('school') != ctx.school:
            raise ValueError('student link exclusions must name this school and version 1')
        sp, n_ex, n_un = exclude_links(sp, doc)
        n['student_links_excluded'] += n_ex
        n['student_link_exclusions_unmatched'] += n_un
    ctx.sp, ctx.guard_samples, ctx.guard_kept_samples = sp, guard_samples, guard_kept_samples
