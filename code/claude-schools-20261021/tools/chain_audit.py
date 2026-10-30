"""The owner's seven chain checks for every school (2026-10-28), each item passing, explained, or unexplained.

  0 coverage    every computing-related lab is in: faculty a department lists but the census lacks, and CS-related
                candidates, each need a decision (missing-pi-review, cs-related-review, census-overrides) or a PI record
  1 pi          every lab has a PI: a named PI with a lab unit and a site person record
  2 students    every lab has students, or a reason (few-students-evidence, thesis-evidence, chain-reasons)
  3 papers      every lab has papers, or a reason (zero-paper-review)
  4 links       every student of a lab is linked to at least one of that lab's papers, or a reason
  5 copies      every lab paper has a local copy, or a reason
  6 one_person  same/same-ish names within a lab are one record, or a reason (student-audit within_lab)

Reasons come from the evidence files the research passes wrote, from rules applied to the record itself (a student
whose advising starts in 2025 or later has had no time to publish; the lab has no paper in the student's years; a
missing copy's cause as the stores' access review recorded it: paywall, login, bot challenge, robots.txt, landing page
without a PDF, not found, ... (ACCESS_REASON)), or from hierarchy/chain-reasons.json, the reviewed ledger for everything else:
  {school: {check: {item_key: {"verdict": "explained"|"fix", "reason": "...", "evidence": [...]}}}}
A 'fix' verdict counts as unexplained: it names work still to do.
-> hierarchy/chain-audit.json (counts plus every unexplained item) and hierarchy/CHAIN-AUDIT.md
usage: chain_audit.py [school ...]
"""
import collections, gzip, json, re, sys, unicodedata
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
HERE = P.WORK; H = P.HIERARCHY
SCHOOLS = list(P.SCHOOL_IDS)  # the released schools (schools/<key>.toml); an onboarding school is named on the command line
CHECKS = ['coverage', 'pi', 'students', 'papers', 'links', 'copies', 'one_person']
LOCAL = {'local', 'fulltext_xml', 'downloaded', 'pdf', 'xml'}
# why a lab paper has no local copy, by the cause the stores' access review recorded (2026-10-29; the collector keeps such a
# work at needs_access_review): only 401/403, a login or identity-provider redirect, and a bot challenge are paywalls/logins
ACCESS_REASON = {
    'paywall_or_forbidden': 'only paywalled copies found (HTTP 401/403)',
    'login': 'only login copies found (redirect to a login page or identity provider)',
    'challenge': 'only copies behind a bot challenge found',
    'publisher_landing_no_pdf': 'only a publisher landing page without a PDF link found',
    'robots_disallow': "robots.txt disallows every copy found",
    'robots_unavailable': 'robots.txt could not be read (4xx), so no copy was fetched',
    'embargoed': 'the copy is embargoed (signed store answered 403)',
    'not_found': 'every copy URL is gone (404/410)',
    'integrity_mismatch': 'the copy failed its integrity check',
    'unapproved_redirect': 'the copy URLs redirect to hosts the collector may not follow',
    'landing_no_pdf': 'only landing pages without a PDF found',
    'not_pdf': 'the copy URLs serve no PDF',
    'identity_mismatch': 'the only PDFs found are another paper (identity mismatch)',
    'tls_error': 'TLS errors on every copy host',
    'too_large': 'the copy is larger than the store accepts',
    'policy_skip': 'skipped by the collection policy',
    'transient_on_challenge_or_publisher_host': 'transient failures on a challenge or publisher host (not retried)',
    'transient_exhausted': 'transient failures; retries exhausted',
    'transient': 'transient failures; requeued for another try',
    'no_attempts': 'no copy URL was ever tried',
    'other': 'no copy fetched (unclassified failure)',
}


def load(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    if p.suffix == '.gz':
        return [json.loads(l) for l in gzip.open(p, 'rt')]
    return json.loads(p.read_text())


def norm(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z ]', ' ', s).split())


def names_in(obj):
    """Every name-like string a decision record carries (name, aliases, names)."""
    out = set()
    if isinstance(obj, dict):
        for k in ('name', 'pi', 'aliases', 'names'):
            v = obj.get(k)
            for x in (v if isinstance(v, list) else [v]):
                if isinstance(x, str) and x:
                    out.add(norm(x))
    return out


def decisions(doc):
    if not doc:
        return []
    d = doc.get('decisions', doc) if isinstance(doc, dict) else doc
    d = d if isinstance(d, list) else [dict(v, name=k) if isinstance(v, dict) else {'name': k} for k, v in d.items()]
    # a decision whose value starts with 'pending' ('pending_openalex') is not a decision yet (Michigan request 3,
    # 2026-10-29; tools/stage_gate.py already reads it so)
    return [x for x in d if not (isinstance(x, dict) and str(x.get('decision') or '').startswith('pending'))]


def revisit_due(ov_school, today):
    """The census-overrides entries of one school whose revisit_after date has come (2026-10-29, owner: best judgement):
    an exclusion with revisit_after (a new arrival with no group or advisee yet) is decided only until that date; after
    it the person is open again for a fresh coverage review. Names normalized (norm)."""
    return {norm(k) for k, v in ov_school.items() if isinstance(v, dict) and v.get('revisit_after') and v['revisit_after'] <= today}


def by_pi(rows):
    out = {}
    for r in rows or []:
        if isinstance(r, dict) and r.get('pi'):
            out.setdefault(norm(r['pi']), []).append(r)
    return out


def years_of(stu):
    ys = []
    for r in stu.get('relations') or []:
        ys += [int(y) for y in r.get('years') or [] if str(y).isdigit()]
    return ys


def audit(school):
    D = H / school
    pis = load(D / 'pis.json', [])
    students = load(D / 'students.json', {})
    lab_papers = load(D / 'lab_papers.jsonl.gz', [])
    links = load(D / 'student_papers.jsonl.gz', [])
    copies = (load(D / 'copies.json', {}) or {}).get('papers', {})
    report = load(D / 'report.json', {}) or {}
    ledger = (load(H / 'chain-reasons.json', {}) or {}).get(school, {})
    zero = (load(H / 'zero-paper-review.json', {}) or {}).get(school, {})
    ov_school = (load(H / 'census-overrides.json', {}) or {}).get(school, {})
    overrides = json.dumps(ov_school)
    # an exclusion with revisit_after (a new arrival with no group or advisee yet) is decided only until that date
    # (2026-10-29, owner: best judgement); after it the person is open again for a fresh coverage review
    today = datetime.now(timezone.utc).date().isoformat()
    due = revisit_due(ov_school, today)
    res = {c: {'total': 0, 'pass': 0, 'explained': collections.Counter(), 'unexplained': []} for c in CHECKS}

    def item(check, key, ok, reason=None, detail=None):
        r = res[check]; r['total'] += 1
        rev = (ledger.get(check) or {}).get(key)
        if ok:
            r['pass'] += 1
        elif rev and rev.get('verdict') == 'explained':
            r['explained']['reviewed: ' + rev.get('reason', '')[:60]] += 1
        elif reason:
            r['explained'][reason] += 1
        else:
            r['unexplained'].append(dict(key=key, **(detail or {}), **({'fix': rev['reason']} if rev else {})))

    pi_names = set()
    for p in pis:
        pi_names |= {norm(p['pi'])} | {norm(n) for n in p.get('names') or []}

    # 0 coverage
    decided = set()
    for f in ('missing-pi-review.json', 'cs-related-review.json'):
        for d in decisions(load(D / f)):
            decided |= names_in(d)
    for x in load(D / 'listed-not-in-census.json', []) or []:
        n = norm(x.get('name'))
        item('coverage', 'listed:' + x.get('name', ''), n in pi_names,
             'decided' if (n in decided or (x.get('name') and x['name'] in overrides)) and n not in due else None,
             {'why': 'revisit due: excluded as a new arrival without a group' if n in due else 'a department lists this person; neither in the census nor decided', 'titles': x.get('titles'),
              'years': x.get('years')})
    for x in load(D / 'cs-related-candidates.json', []) or []:
        ns = names_in(x)
        item('coverage', 'candidate:' + x.get('name', ''), bool(ns & pi_names),
             'decided' if ns & decided and not ns & due else None,
             {'why': 'CS-related candidate without a decision', 'works': x.get('works'), 'cs_share': x.get('cs_share')})
    if not (D / 'listed-not-in-census.json').exists():
        res['coverage']['unexplained'].append({'key': 'listed-not-in-census.json', 'why': 'the department-listing cross-check was never run'})
        res['coverage']['total'] += 1

    # papers per PI, links per (pi, student)
    papers_by_pi = collections.defaultdict(list)
    for r in lab_papers:
        papers_by_pi[norm(r['pi'])].append(r)
    linked = collections.defaultdict(set)
    for r in links:
        linked[norm(r['pi'])].add(r['student'])
    few = by_pi(load(D / 'few-students-evidence.json', []))
    # tools/link_diagnosis.py: each open student checked against the school's OpenAlex sweep
    diag = (load(D / 'link-diagnosis.json', {}) or {}).get('students', {})
    DIAG_REASON = {'no_school_work': 'no school-affiliated work under their name in their years (OpenAlex sweep)',
                   'publishes_without_pi': 'publishes at the school in their years, never with this PI (OpenAlex sweep)',
                   'ambiguous_name': 'name matches 4+ distinct school authors in their years: cannot be told apart',
                   'linked_in_coadviser_lab': "co-advised: linked in the other adviser's lab, whose PI is on their school works (OpenAlex sweep)",
                   'same_name_record_linked_in_other_lab': 'a same-name record in another lab is linked there with that PI (not merged across labs; review)',
                 'with_pi_outside_appointment': "co-wrote with the PI only outside the PI's evidenced appointment at the school, or only non-paper outputs (OpenAlex sweep)",
                 'with_pi_at_other_institution': "co-wrote with the PI only on works where the PI's own authorship names another institution (or outside the appointment, or non-papers) (OpenAlex sweep)"}
    thesis = by_pi(load(D / 'thesis-evidence.json', []))

    for p in pis:
        name, k = p['pi'], norm(p['pi'])
        lab = p.get('lab') or {}
        # 1 pi: the hierarchy builds each PI's own lab, so a lab needs a named PI with a recorded basis (advising, own lab)
        basis = (p.get('piBasis') or {}).get('kind')
        item('pi', name, bool(basis) and basis != 'listed_faculty_missing_from_census', None,
             {'why': 'no PI basis on record' if not basis else 'PI basis is only a department listing (no advising or lab evidence)'})
        # 2 students
        studs = students.get(name) or []
        item('students', name, bool(studs),
             'researched: few-students evidence' if k in few else ('researched: thesis evidence' if k in thesis else None),
             {'why': 'lab has no students'})
        # 3 papers
        z = zero.get(name) or {}
        item('papers', name, bool(papers_by_pi.get(k)),
             'reviewed: ' + z.get('reason', '')[:60] if z.get('verdict') == 'zero_is_right' else None,
             {'why': 'lab has no papers', **({'fix': z['reason']} if z.get('verdict') == 'fix' else {})})
        # 4 links
        pyears = collections.Counter(int(str(r.get('year'))[:4]) for r in papers_by_pi.get(k, []) if str(r.get('year'))[:4].isdigit())
        for s in studs:
            sid = s.get('person') or s.get('id') or s.get('name')
            ys = years_of(s)
            roles = set(s.get('roles') or [])
            reason = None
            if not papers_by_pi.get(k):
                reason = 'lab has no papers (check 3)'
            elif ys and min(ys) >= 2025:
                reason = 'advising starts 2025 or later: no time to publish yet'
            elif ys and not any(pyears.get(y) for y in range(min(ys) - 1, max(ys) + 4)):
                reason = "no lab paper in the student's years"
            elif roles and roles <= {'undergraduate', 'masters', 'visiting', 'intern'}:
                reason = 'non-PhD advisee (' + '/'.join(sorted(roles)) + '): thesis-only is normal'
            dg = diag.get(f'{name} | {sid}') or {}
            if not reason and dg.get('category') in DIAG_REASON:
                reason = DIAG_REASON[dg['category']]
            item('links', f'{name} | {s.get("name")} | {sid}', sid in linked.get(k, set()), reason,
                 {'pi': name, 'student': s.get('name'), 'id': sid, 'diagnosis': dg.get('category'), 'diagnosis_works': (dg.get('works') or [])[:3], 'years': [min(ys), max(ys)] if ys else None,
                  'roles': sorted(roles), 'lab_papers_in_years': sum(pyears.get(y, 0) for y in range(min(ys) - 1, max(ys) + 4)) if ys else None})

    # 5 copies (one paper may sit in several labs: count each work once)
    seen = set()
    for r in lab_papers:
        w = r.get('work') or r.get('oa') or r.get('doi')  # Berkeley's lab papers carry only the OpenAlex id
        if w in seen:
            continue
        seen.add(w)
        c = copies.get(w)
        st = (c or {}).get('status')
        reason = None
        if st == 'needs_access_review':
            # the stores' access review (fulltext-push/review_access.py, catalog table access_review, carried into
            # copies.json by lab_paper_copies.py) names the real cause; a work it has not classified yet says so
            cause = (c or {}).get('access_cause')
            reason = ACCESS_REASON.get(cause) or (f'no copy fetched: {cause}' if cause else 'no copy fetched; the access review has not classified the cause yet')
        item('copies', w, st in LOCAL, reason,
             {'why': 'not in copies.json (copies were computed before this paper became a lab paper)' if c is None
              else f'status {st}', 'cause': (c or {}).get('access_cause'), 'causes': (c or {}).get('access_causes'),
              'pi': r['pi'], 'year': r.get('year'), 'doi': r.get('doi'), 'title': (r.get('title') or '')[:100]})

    # 6 one person per lab
    sa = {x['school']: x for x in load(H / 'student-audit.json', []) or []}.get(school)
    if sa is None:
        res['one_person']['unexplained'].append({'key': 'student-audit.json', 'why': 'student_audit.py has no entry for this school'})
        res['one_person']['total'] += 1
    else:
        pairs = 0
        for x in sa.get('within_lab') or []:
            pairs += 1
            key = f"{x['pi']} | {x['a'][1]} = {x['b'][1]}"
            item('one_person', key, False, None, {'pi': x['pi'], 'a': x['a'], 'b': x['b'], 'why': 'probably one person, two records'})
        n_pairs = sum(len(v) for v in students.values())
        res['one_person']['total'] = n_pairs
        res['one_person']['pass'] = n_pairs - pairs - sum(res['one_person']['explained'].values())

    for r in res.values():
        r['explained'] = dict(r['explained'].most_common())
        r['n_unexplained'] = len(r['unexplained'])
    return {'school': school, 'builtAt': report.get('builtAt'), 'checks': res}


def md(out):
    L = ['# Chain audit: the seven checks per school', '', f"Built {out['at']} by tools/chain_audit.py.", '',
         '| School | ' + ' | '.join(CHECKS) + ' |', '|---|' + '---|' * len(CHECKS)]
    for s in out['schools']:
        cells = []
        for c in CHECKS:
            r = s['checks'][c]
            cells.append(f"{r['pass']}/{r['total']} ok, {sum(r['explained'].values())} why, **{r['n_unexplained']}** open")
        L.append(f"| {s['school']} | " + ' | '.join(cells) + ' |')
    for s in out['schools']:
        L += ['', f"## {s['school']}"]
        for c in CHECKS:
            r = s['checks'][c]
            L.append(f"- **{c}**: {r['pass']} pass of {r['total']}; explained {r['explained'] or '{}'}; open {r['n_unexplained']}")
    return '\n'.join(L) + '\n'


def main(argv):
    schools = argv or SCHOOLS
    prev = {x['school']: x for x in (load(H / 'chain-audit.json', {}) or {}).get('schools', [])}
    for s in schools:
        prev[s] = audit(s)
    out = {'at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'schools': [prev[s] for s in SCHOOLS if s in prev]}
    (H / 'chain-audit.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    (H / 'CHAIN-AUDIT.md').write_text(md(out))
    for s in out['schools']:
        print(s['school'], {c: (s['checks'][c]['pass'], s['checks'][c]['total'], s['checks'][c]['n_unexplained']) for c in CHECKS})


if __name__ == '__main__':
    main(sys.argv[1:])
