"""Student-paper links: a lab student on a lab paper's byline. R-LNK-01 (the link bases), R-LNK-02/02a/02b (the given-name
guard, names.given_conflict), R-LNK-03 (within-lab byline matching), R-LNK-05 (links carry their evidence)."""
import collections, re, unicodedata

from .names import LETTERS, Name, byline_name, clean_person_name, given_conflict, gwords, name_variants, nick_ok, student_on_byline, toks

def near_relation(s, year):
    """The paper's year is within three years of the student's recorded advising or membership (no years: any)."""
    ys = [int(y) for rel in s.get('relations') or [] for y in rel.get('years') or [] if str(y).isdigit()]
    return not ys or not year or min(ys) - 3 <= int(year) <= max(ys) + 3


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


def link_students(ctx):
    """ctx.sp: every (lab paper, lab student) link with its basis, byline and roster source; the guard's samples."""
    rows, stu, pls, n = ctx.rows, ctx.stu, ctx.pls, ctx.n
    sp = []
    # every reading of a student's name: the name, its aliases, and parenthesized forms ('Fatma Imamoglu (Deniz)')
    forms = {sid: [f for f in dict.fromkeys([s['name']] + list(s.get('aliases') or []) + [v_ for x_ in [s['name']] + list(s.get('aliases') or []) for v_ in name_variants(x_)])
                   if '(' not in f] or [s['name']] for v in stu.values() for sid, s in v.items()}
    snm = {sid: [(Name([f]), toks(f)) for f in fs] for sid, fs in forms.items()}

    def on_byline(sid, b):
        return any(student_on_byline(nm_, tk_, b or '') for nm_, tk_ in snm[sid])

    def full_name_on(sid, b):
        """The byline spells the student's first given name and family name out in full (no initials)."""
        t = toks(byline_name(b))
        return len(t) >= 2 and any(len(tk_) >= 2 and len(tk_[0]) > 1 and t[0] == tk_[0] and t[-1] == tk_[-1] for _, tk_ in snm[sid])

    def wide_relation(s, year):
        """Two years before to six after the recorded advising: recorded years are often a single roster observation."""
        ys = [int(y) for rel in s.get('relations') or [] for y in rel.get('years') or [] if str(y).isdigit()]
        return not ys or not year or min(ys) - 2 <= int(year) <= max(ys) + 6
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

    def byline_ok(sid, raw, how, pi=None):
        return how(sid, raw) and not student_given_conflict(sid, raw, pi=pi)
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

    def sw_same(sid, bt):
        return any(f1 == f2 and sw_given(g1, g2) for st in sw_names[sid] for f1, g1 in sw_forms(st, True) for f2, g2 in sw_forms(bt, False))

    for r in rows:
        S = stu.get(r['pi']) or {}
        if not S:
            continue
        done_ = set(); linked_by_collection = {}
        for sid, s in S.items():
            l = next((l for l in pls[sid] if r['work'] and l['work'] == r['work']), None)
            if l:
                done_.add(sid); linked_by_collection[sid] = True
                sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status=l.get('status'), basis='collection_person_link'))
            elif (b_ := next((b for _, bs in r['_bylines'] for b in bs if byline_ok(sid, b, on_byline, r['pi'])), None)) is not None:
                # the student's name on this lab paper's byline, on an authorship that lists the school
                done_.add(sid); sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status='candidate', basis='byline_name_with_school_affiliation', byline=b_))
            elif near_relation(s, r['year']) and (b_ := next((b for bl, _ in r['_bylines'] for b in bl if byline_ok(sid, b, on_byline, r['pi'])), None)) is not None:
                # the PI's own advisee named on the PI's lab paper (an authorship without affiliations, e.g. an ACL
                # Anthology record), within three years of the recorded advising
                done_.add(sid); sp.append(dict(pi=r['pi'], student=sid, name=s['name'], work=r['work'], oa=r['oa'], status='candidate', basis='advisee_name_on_lab_paper_byline', byline=b_))
            elif wide_relation(s, r['year']) and (b_ := next((b for bl, _ in r['_bylines'] for b in bl if byline_ok(sid, b, full_name_on, r['pi'])), None)) is not None:
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
            if len(hits_) == 1 and hits_[0] not in done_ and wide_relation(S[hits_[0]], r['year']) and not student_given_conflict(hits_[0], raw):
                sid = hits_[0]; done_.add(sid)
                sp.append(dict(pi=r['pi'], student=sid, name=S[sid]['name'], work=r['work'], oa=r['oa'], status='candidate', basis='within_lab_byline_match', byline=raw))
    n.update({'link_guard_' + k: v for k, v in guard_n.items()})
    # every byline link carries its evidence (2026-10-29, build-time evidence check): the work, the exact byline string
    # matched, and the student's own roster source (the first relation source with url, sha256 and a verbatim quote)
    for x in sp:
        x['relation_source'] = relation_source(stu[x['pi']].get(x['student']) or {})
    ctx.sp, ctx.guard_samples, ctx.guard_kept_samples = sp, guard_samples, guard_kept_samples
