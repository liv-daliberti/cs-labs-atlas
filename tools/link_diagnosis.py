"""Why a lab's student has no linked lab paper (chain check 4): each open student checked against the school's own
OpenAlex sweep (every school-affiliated work 2016-2026, hierarchy/<school>/openalex-sweep.sqlite), offline.

A student's works: sweep authorships that list the school, whose raw name has the student's family name and a
compatible given name (the same first given name, or its initial when the byline gives only an initial), dated from a
year before their recorded advising to three years after it. Then:
  link_missed            one of those works IS a lab paper of this PI: the matcher missed the student's name form
  paper_not_lab_paper    a work with the PI on the byline (the PI's reviewed or anchored OpenAlex id) that is not one
                         of the lab's papers: a gap in the lab's paper list
  with_pi_outside_appointment  every such work with the PI falls outside the PI's evidenced appointment at the school
                         (no reviewed period and no same-year listing covers its date) or is not a paper (dataset,
                         abstract, erratum): the builder's rules exclude it, a reason, not a gap
  with_pi_at_other_institution  every such work is excluded as above or, for at least one of them, the PI's own
                         authorship names another institution and not the school, and the paper's first page
                         (pi-works.sqlite) does not tie the school to the PI (2026-10-29): written before the PI's
                         appointment, after it, or on leave elsewhere (Berg-Kirkpatrick at UCSD, Mankoff and Dey at UW,
                         Ghassemi at Toronto); the lab-paper rule (a) excludes it, a reason, not a gap
  publishes_without_pi   school works in their years, none with this PI (other advisers, co-advised, other groups);
                         the census PIs on those bylines are listed
  linked_in_coadviser_lab  (R-D2, 2026-10-29) as publishes_without_pi, but the same student record (id or merged id) is linked
                         in another lab whose PI is on those works: co-advised, the link sits in that lab
  same_name_record_linked_in_other_lab  (R-D2) a same-name record of another lab is linked there and that PI is on the works;
                         never merged (R-HIER-03), a candidate for review
A student's works count only on an authorship that lists the school (R-D1, 2026-10-29), not non-papers, dissertations or
abstracts, and an initial-only byline only when its author id also carries the student's full given name.
  no_school_work         no school-affiliated work under their name in their years
  ambiguous_name         the name matches 4+ distinct OpenAlex authors at the school in those years and none of the
                         first two cases holds: the evidence cannot tell them apart
The first two are work to do; the others are reasons. Evidence: OpenAlex work ids and titles.
-> hierarchy/<school>/link-diagnosis.json {summary, students: {"<pi> | <student id>": {category, works, pis_seen}}}
usage: link_diagnosis.py <school> ...
"""
import collections, gzip, json, re, sqlite3, sys, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from pi_hierarchy import sweep_works, contains, same_year, NOT_PAPERS, TODAY, INST, AFF  # noqa: E402

import atlas_paths as P  # noqa: E402  (every path in one place)
HERE = P.WORK; H = P.HIERARCHY   # tests point H at a flat fixture tree; hfile follows the layout for the live one
SCHOOL_IDS = {}  # filled from the PIs' lab papers: the institution ids their school authorships carry


def words(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    if ',' in s:  # 'Li, Yu-Jhe'
        a, b = s.split(',', 1); s = f'{b} {a}'
    return [w for w in re.split(r'[^a-z]+', s) if w]


def first_given(s):
    """The first given name as written, hyphen parts joined: 'Po-Ta Chen' -> 'pota', 'Chen, Po-Hsuan' -> 'pohsuan'."""
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    if ',' in s:
        a, b = s.split(',', 1); s = f'{b} {a}'
    w = [re.sub(r'[^a-z]', '', t) for t in re.split(r'[\s.]+', s)]
    w = [t for t in w if t]
    return w[0] if w else ''


def compatible(student, raw):
    """Same family name; the first given name equal, or an initial standing for it (either side). Hyphenated given names
    count whole (2026-10-29, the builder's given-name guard): 'Po-Ta Chen' is not 'Po-Hsuan Chen', 'Yi-Chia Wang' is
    not 'Yi Wang'."""
    s, r = words(student), words(raw)
    if len(s) < 2 or len(r) < 2 or s[-1] != r[-1]:
        return False
    fa, fb = first_given(student), first_given(raw)
    if len(fa) > 1 and len(fb) > 1 and fa != fb and ('-' in student.split(',')[-1] or '-' in raw.split(',')[-1]):
        return False
    a, b = s[0], r[0]
    if a == b or ''.join(s[:-1]) == ''.join(r[:-1]):
        return True
    return (len(a) == 1 or len(b) == 1) and a[0] == b[0]


def name_key(s):
    return ' '.join(words(s))


def run(school):
    A = {x['school']: x for x in json.loads((P.hfile(H, 'chain-audit.json')).read_text())['schools']}[school]
    pis = {p['pi']: p for p in json.loads((P.hfile(H, 'pis.json', school)).read_text())}
    pi_ids = {k: set(p.get('reviewedOpenAlex') or []) | set(p.get('oaAuthorIds') or []) for k, p in pis.items()}
    id_to_pi = collections.defaultdict(set)
    for k, ids in pi_ids.items():
        for a in ids:
            id_to_pi[a].add(k)
    lab = collections.defaultdict(set)
    for l in gzip.open(P.hfile(H, 'lab_papers.jsonl.gz', school), 'rt'):
        r = json.loads(l)
        for o in [r.get('oa')] + [e.get('oa') for e in r.get('editions') or []]:
            if o:
                lab[r['pi']].add(o)
    open_items = A['checks']['links']['unexplained']
    # the labs where each student record (by id, merged ids included) and each name has a student-paper link (R-D2)
    stu_ = json.loads((P.hfile(H, 'students.json', school)).read_text())
    merged_of = {(pi_, r['person']): list(r.get('merged') or []) for pi_, rs in stu_.items() for r in rs}
    linked_pairs = {(json.loads(l)['pi'], json.loads(l)['student']) for l in gzip.open(P.hfile(H, 'student_papers.jsonl.gz', school), 'rt')}
    linked_labs, linked_by_name = collections.defaultdict(set), collections.defaultdict(set)
    for pi_, rs in stu_.items():
        for r in rs:
            if (pi_, r['person']) in linked_pairs:
                for i in [r['person']] + list(r.get('merged') or []):
                    linked_labs[i].add(pi_)
                linked_by_name[name_key(r['name'])].add(pi_)
    fams = {words(x['student'])[-1] for x in open_items if words(x['student'])}
    inst, aff = 'https://openalex.org/' + INST[school], re.compile(AFF[school], re.I)
    pw = P.hfile(H, 'pi-works.sqlite', school)
    tied = {r[0] for r in sqlite3.connect(f'file:{pw}?mode=ro', uri=True).execute('select work from pages where school_named=1')} if pw.exists() else set()

    def where(a):
        """'school' when the authorship names the school, 'elsewhere' when it names only other institutions, else 'none'."""
        if any(inst == i.get('id') or inst in (i.get('lineage') or []) for i in a.get('institutions') or []) or any(aff.search(z) for z in a.get('raw_affiliation_strings') or []):
            return 'school'
        return 'elsewhere' if a.get('institutions') else 'none'
    # index the sweep's school-affiliated authorships by family name (only the families we need)
    idx = collections.defaultdict(list)
    for w in sweep_works(school):
        y = w.get('publication_year')
        auth = w.get('authorships') or []
        ids_on = {(a.get('author') or {}).get('id') for a in auth}
        pi_where = {}
        for a in auth:
            for k_ in id_to_pi.get((a.get('author') or {}).get('id'), ()):
                pi_where.setdefault(k_, where(a))
        for a in auth:
            raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name')
            ww = words(raw)
            if not ww or ww[-1] not in fams:
                continue
            if where(a) != 'school':  # R-D1 (2026-10-29): the student's own authorship lists the school, not merely some institution
                continue
            idx[ww[-1]].append(dict(work=w['id'], title=(w.get('title') or '')[:120], year=y, raw=raw, type=w.get('type'),
                                    date=w.get('publication_date') or str(y or ''), aid=(a.get('author') or {}).get('id'), coauthor_ids=ids_on,
                                    co_raw=[b.get('raw_author_name') or '' for b in auth if b is not a],
                                    pi_where=pi_where, tied=w['id'] in tied))
    out, summary = {}, collections.Counter()
    lab_students = {pi_: [r['name'] for r in rs] for pi_, rs in stu_.items()}
    for x in open_items:
        resolved = None
        ys = x.get('years')
        lo, hi = (ys[0] - 1, ys[1] + 3) if ys else (2016, 2026)
        fam = (words(x['student']) or [''])[-1]
        cand_all = [c for c in idx.get(fam, []) if c['year'] and lo <= c['year'] <= hi and compatible(x['student'], c['raw'])]
        # R-D1 (2026-10-29, link-gap sample): non-papers, dissertations and abstracts do not show where a student publishes,
        # and an initial-only byline ('Q. Yu' at Max Planck) counts only when its author id also carries a full given name
        # of the student
        full_aids = {c['aid'] for c in cand_all if len(first_given(c['raw'])) > 1}
        cand = [c for c in cand_all if c.get('type') not in NOT_PAPERS | {'dissertation', 'conference-abstract'}
                and (len(first_given(c['raw'])) > 1 or c['aid'] in full_aids)]
        pi = x['pi']
        mine = [c for c in cand if c['work'] in lab[pi]]
        with_pi = [c for c in cand_all if c['coauthor_ids'] & pi_ids.get(pi, set()) and c['work'] not in lab[pi]]
        authors = {c['aid'] for c in cand if c['aid']}
        def excluded(c):  # why the builder rightly left a work with the PI out of the lab's papers, or None
            if c.get('type') in NOT_PAPERS or c.get('type') in ('conference-abstract',):
                return 'not_a_paper'
            if c['pi_where'].get(pi) == 'elsewhere' and not c['tied']:
                return 'pi_affiliated_elsewhere'
            p = pis.get(pi) or {}
            if any(contains(q.get('start'), q.get('end'), c['date'], q.get('asof') or TODAY) == 'supported' for q in p.get('periods') or []):
                return None
            return None if any(l.get('year') == same_year(c['date']) for l in p.get('listings') or []) else 'outside_appointment'
        if mine:
            cat = 'link_missed'
        elif with_pi and all(excluded(c) for c in with_pi):
            cat = 'with_pi_at_other_institution' if any(excluded(c) == 'pi_affiliated_elsewhere' for c in with_pi) else 'with_pi_outside_appointment'
        elif with_pi:
            cat = 'paper_not_lab_paper'
        elif not cand:
            cat = 'no_school_work'
        elif len(authors) >= 4:
            cat = 'ambiguous_name'
            # (2026-10-29, link-gap sample B4) exactly one of the author ids shares a school byline with another student of
            # this lab written with a full given name: that author is the student (the lab-mate tie is evidence, the name
            # alone is not); the student then publishes at the school without this PI
            mates = [m for m in lab_students.get(pi, ()) if m != x['student'] and len(first_given(m)) > 1]
            tied_ = {c['aid'] for c in cand if c['aid'] and any(len(first_given(r)) > 1 and words(r)[-1:] == words(m)[-1:]
                                                                 and first_given(r) == first_given(m) for m in mates for r in c['co_raw'])}
            if len(tied_) == 1:
                cat = 'publishes_without_pi'; resolved = dict(by='labmate_coauthor', author=next(iter(tied_)))
        else:
            cat = 'publishes_without_pi'
            # R-D2 (2026-10-29, link-gap sample): the same student record (its id or a merged id) is linked in another lab
            # whose PI is on these school works: co-advised, and the link sits in that lab. A same-name record of another
            # lab is reported apart and never merged (R-HIER-03; tools/student_audit.py across_labs)
            on_works = {p for c in cand for a in c['coauthor_ids'] for p in id_to_pi.get(a, ()) if p != pi}
            ids_ = {x.get('id')} | set(merged_of.get((pi, x.get('id')), ()))
            if any(p in on_works for i in ids_ for p in linked_labs.get(i, ())):
                cat = 'linked_in_coadviser_lab'
            elif any(p in on_works for p in linked_by_name.get(name_key(x['student']), ()) if p != pi):
                cat = 'same_name_record_linked_in_other_lab'
        with_pi = [dict(c, excluded=excluded(c)) for c in with_pi] if with_pi else with_pi
        seen = collections.Counter(p for c in cand for a in c['coauthor_ids'] for p in id_to_pi.get(a, ()) if p != pi)
        ev = (mine or with_pi or cand)[:5]
        out[f"{pi} | {x.get('id')}"] = dict(pi=pi, student=x['student'], id=x.get('id'), roles=x.get('roles'), years=ys, category=cat,
                                            works=[dict(oa=c['work'], year=c['year'], title=c['title'], byline_name=c['raw'], type=c.get('type'), excluded=c.get('excluded'),
                                                        pi_affiliation=c.get('pi_where', {}).get(pi)) for c in ev],
                                            n_school_works=len({c['work'] for c in cand}), distinct_author_ids=len(authors),
                                            pis_seen=[p for p, _ in seen.most_common(3)], **({'resolved': resolved} if resolved else {}))
        if resolved:
            summary['ambiguous_resolved_by_' + resolved['by']] += 1
        summary[cat] += 1
    P.hfile_w(H, 'link-diagnosis.json', school).write_text(json.dumps(dict(summary=dict(summary), students=out), indent=1, ensure_ascii=False))
    print(json.dumps(dict(school=school, open=len(open_items), **summary)), flush=True)


if __name__ == '__main__':
    for s in sys.argv[1:]:
        run(s)
