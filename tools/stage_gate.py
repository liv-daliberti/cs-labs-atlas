"""Check a protocol school's stage gates (docs/ADDING-A-SCHOOL.md) from the files the stages wrote, before the school is
wired into pi_hierarchy.py / chain_audit.py. Prints one JSON line per stage and the items that fail.

  0 charter   schools/<key>.toml passes school_config.check; hierarchy/<key>/hosts.json (tools/school_hosts.py) has its gate true and
              lists every host of the charter; the OpenAlex snapshot holds the school's primary lineage id (main store or an
              ext-<key>.sqlite extension: tools/oa_snapshot.py filter|merge --ext <key>, docs/OPENALEX-SNAPSHOT.md)
  1 sources   every department of the charter has an ok listing capture in every window year (listings/<key>/coverage.json);
              a missing year must carry a plan reason and, to pass, a reviewed `listing_gaps` entry (year = reason) in the charter's department
  2 census    every CS-related candidate has a decision other than pending_openalex (hierarchy/<key>/cs-related-review.json),
              and every candidate is in the review
  3 pis       every census PI (and addition) has a PI basis with url + sha256 + quote, and an accepted home department
              (hierarchy/<key>/home-departments.json)
  4 periods   every PI has a reviewed period (periods/<key>-faculty-periods.json, census-overrides periods) or listing years
              that run without a gap from their first to their last listed year (a year with papers outside them is
              checked again at stage 7)
  4 also      a span gap passes when census-overrides names it in unproven_years with why_unproven (searched, no
              dated evidence; papers of those years stay outside the appointment)
  2 also      the bulk-pull sanity check passes (tools/sweep_check.py -> hierarchy/<key>/sweep-check.json)
  5 identity  every PI has an anchor: a DBLP id, an ORCID or a reviewed OpenAlex id (census, additions, census-overrides), or a reviewed
              `no_identity` + `why_no_identity` in the overrides (the person is a PI, no papers are attributed); and the anchors yield
              papers: a PI of the built package (pis.json) with verifiedWorks and labPapers both 0 fails unless the overrides record
              `no_papers` + `why_no_papers` (or `no_identity`), or lab-coverage-reasons has a `papers` reason (ROADMAP #43)
  0 charter   school_config check passes and every host of the charter is consistent (hosts.json)
  6 students  the lab-page students acceptance is accepted, and the chain audit's students and one_person checks are explained
  6 also      student recall (tools/student_recall.py; thresholds R1/U/R2/Z in ONE place there): a seeded stratified hand-check record bound to the
              build, strict recall on readable PIs, unverifiable share, PIs without students or a researched reason, estimated whole-school recall
  7 papers    the lab-page papers acceptance is accepted, and the chain audit's papers and links checks are explained
  8 texts     copies are measured (the 85% local share is a target reported as copy_target_met, not a gate), the chain audit's copies check is explained, and the ledger exists
  9 accuracy  accuracy/summary-<key>.json: lab precision >= .95, student-link precision >= .97, lab coverage >= .90, on the current build
 10 release   the charter says released and the newest release counts the school
A gate a hand decision waives is recorded in hierarchy/<key>/reviewed/gate-exceptions.json ({"6": {"reason", "by", "decided"}}): it
reports `waived`, with the reason, and the open items stay listed. Michigan shipped that way (stages 6-9, owner, 2026-11-02).

`--run` makes the stage run itself up to its first review step (ROADMAP #39): it runs the stage's mechanical steps in order (local
ones here, heavy ones as one Slurm pipeline of afterok stages, `--submit`), skips a step whose output exists (`--force` re-runs), stops
at a failed step or a hand step and prints what to review, then evaluates the gate and writes hierarchy/<key>/reports/stage-<n>-gate.json.
It refuses a released school: this command never writes released data. A step that writes a shared file runs only with `--allow-shared`.

usage: stage_gate.py <key> --traps   (every onboarding trap check, tools/onboarding_traps.py)
       stage_gate.py <key> [stage ...] [--run [--dry-run] [--submit] [--from-worktree] [--force] [--allow-shared]] [--json]
"""
import collections, json, re, sys
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import census_overrides as CO  # noqa: E402


def read(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def pis_of(key):
    cen = read(P.data('census-faculty.json', key), {})
    cen = cen.get('faculty', []) if isinstance(cen, dict) else cen   # a composed first-native school keeps a bare list
    add = read(P.data('census-additions.json', key), [])
    return [x for x in cen + add if x.get('is_pi')]


def snapshot_count(key, root=None):
    """Works of the school's primary lineage id in the OpenAlex snapshot (main store and extensions); None when there is no snapshot."""
    import oa_snapshot as O
    try:
        db, d = O.conn(root)
    except FileNotFoundError:
        return None
    i = O.short(S.inst(key))
    return sum(c.execute('select count(*) from work_inst where inst=?', (i,)).fetchone()[0] for c, _ in [(db, d)] + O.exts(root))


def g0(key, root=None):
    bad = list(S.check(key))
    h = read(P.data('hosts.json', key))
    if not h:
        bad.append('hosts: hierarchy/<key>/hosts.json missing (run tools/school_hosts.py <key>)'.replace('<key>', key))
    else:
        done = {x['host']: x for x in h.get('hosts') or []}
        want = {x['host'] for x in S.get(key).get('hosts') or []}
        bad += [f'hosts: {m} is in the charter but not in hosts.json (rerun school_hosts.py)' for m in sorted(want - set(done))]
        bad += [f"hosts: {x['host']}: {', '.join(x['problems'])}" for x in done.values() if not x.get('consistent')]
    n = snapshot_count(key, root)
    if not n:
        bad.append('openalex snapshot: no works of ' + S.inst(key) + ' (extend it: atlas submit tools/oa_snapshot.slurm with OA_EXT=' + key + ')')
    return bad, dict(hosts=len((h or {}).get('hosts') or []), snapshot_works=n)


def g1(key):
    cov = read(P.data('coverage.json', key), {}); lo, hi = S.get(key).get('window')
    bad = []
    for d in S.get(key).get('departments') or []:
        for y in range(lo, hi + 1):
            v = (cov.get(d['code']) or {}).get(str(y)) or {}
            gap = (d.get('listing_gaps') or {}).get(str(y))   # reviewed: searched, no archived listing (reason in the charter)
            if not any(s == 'ok' for s in v.values()) and not gap:
                bad.append(f"{d['code']} {y}: " + ('; '.join(sorted(set(v.values()))) or 'never planned'))
    return bad, dict(departments=len(S.get(key).get('departments') or []), reviewed_gap_years=sum(len(d.get('listing_gaps') or {}) for d in S.get(key).get('departments') or []))


def sweep_gate(key):
    """The bulk-pull sanity check (tools/sweep_check.py -> hierarchy/<key>/sweep-check.json) must exist and pass."""
    sc = read(P.data('sweep-check.json', key))
    if not sc:
        return ['sweep check: hierarchy/<key>/sweep-check.json missing (run tools/sweep_check.py <key>)'.replace('<key>', key)]
    return [f"sweep check: {t['test']} {t.get('year') or ''} {t['why']}".replace('  ', ' ') for t in sc.get('failed') or []] + \
           (['sweep check: status ' + str(sc.get('status'))] if sc.get('status') != 'pass' and not sc.get('failed') else [])


def mixed_author_exclusions(cands, review):
    """Exclude a reviewed mixed author ID from *identity* admission, never by display name alone."""
    by_id = {c.get('author'): c for c in cands if c.get('author')}
    decisions = review.get('decisions') or []
    excluded, bad = set(), []
    for row in review.get('mixed_author_exclusions') or []:
        aid = row.get('author')
        candidate = by_id.get(aid)
        matches = [d for d in decisions if aid in (d.get('openalex') or [])]
        evidence = row.get('evidence') or []
        valid_evidence = bool(evidence) and all(e.get('url') and e.get('quote') and re.fullmatch(r'[0-9a-f]{64}', e.get('sha256') or '')
                                                for e in evidence)
        if (not candidate or len(matches) != 1 or matches[0].get('decision') not in ('not_faculty', 'faculty_no_pi_evidence',
                                                                                     'faculty_not_computing', 'not_faculty_listed')
                or set(row.get('candidate_names') or []) != set(candidate.get('names') or [])
                or len(set(row.get('candidate_names') or [])) < 2 or not row.get('reason') or not valid_evidence):
            bad.append(f'mixed-author exclusion {aid}: missing exact candidate IDs/names, terminal non-PI review or source evidence')
        else:
            excluded.add(aid)
    return excluded, bad


def g2(key):
    cands = read(P.data('cs-related-candidates.json', key))
    if cands is None:  # a missing file read as "no candidates" and passed the gate before the candidates step had run (UChicago friction 23)
        return ['candidates: hierarchy/<key>/cs-related-candidates.json missing (tools/cs_related_school.py candidates <key>)'.replace('<key>', key)] + sweep_gate(key), {}
    rev = read(P.data('cs-related-review.json', key), {}) or {}
    dec = {d['name']: d for d in rev.get('decisions', [])}
    bad = [f"{c['name']}: no decision" for c in cands if c['name'] not in dec and not any(a in dec for a in c.get('aliases') or [])]
    # A display name is not an identity key. Separate DBLP PIDs with the same name
    # must be resolved before the stage can pass; a single name-keyed decision could
    # otherwise hide a second person (VT Dong Li / Lei Zhang / Xi Chen, 2026-11-10).
    excluded, exclusion_bad = mixed_author_exclusions(cands, rev)
    bad += exclusion_bad
    by_name = collections.defaultdict(list)
    for c in cands:
        if c.get('author') not in excluded:
            by_name[c['name']].append(c)
    bad += [f"{name}: {len(rows)} candidate identities share a display name; resolve source IDs before admission"
            for name, rows in by_name.items() if len(rows) > 1]
    bad += [f"{d['name']}: {d['decision']} ({d['reason'][:100]})" for d in dec.values()
            if d['decision'] in ('pending_openalex', 'pending_identity_collision', 'pending_source_coverage')]
    bad += sweep_gate(key)  # the OpenAlex sweep and the DBLP pulls feed the review (owner standard 2026-10-30)
    return bad, dict(candidates=len(cands), **collections.Counter(d['decision'] for d in dec.values()))


def known_homes(key):
    """The home department names a PI may have: the charter's departments, affiliated units and [census].home_units keys. Empty set = nothing to check against."""
    cfg = S.get(key)
    return ({d['name'] for d in cfg.get('departments') or []} | {u['name'] for u in cfg.get('affiliated_units') or []}
            | set((S.field(cfg, 'census.home_units') or {}).keys()))


def website_expected(key, website_doc):
    """The names the website register must cover: every census PI, under the name the package carries (a census alias the register is keyed by
    counts: 'Dan Klein' is the package's 'Daniel Klein'), except a PI the build excluded by review (report.json `excluded`: researched, not a PI of
    the school in the window; the package has no lab for them)."""
    rows = {r['pi'] for r in website_doc.get('labs', [])}
    rep = read(P.data('report.json', key), {})
    excluded = {e.get('pi') for e in (rep.get('excluded') if isinstance(rep, dict) else None) or [] if isinstance(e, dict)}
    out = []
    for x in pis_of(key):
        if x['name'] in excluded and x['name'] not in rows:
            continue
        out.append(x['name'] if x['name'] in rows else next((a for a in x.get('aliases') or [] if a in rows), x['name']))
    return out


def g3(key):
    homes = {r['name']: r for r in read(P.data('home-departments-school.json', key), [])}
    bad = []
    for x in pis_of(key):
        b = x.get('pi_basis') or {}
        if not (b.get('url') and b.get('sha256') and b.get('quote')):
            bad.append(f"{x['name']}: PI basis without url/sha256/quote")
        h = homes.get(x['name'])
        if not h or h.get('status') != 'accepted' or not h.get('home_department'):
            bad.append(f"{x['name']}: no accepted home department")
        elif known_homes(key) and h['home_department'] not in known_homes(key):   # R8: a home must be a department, a searched unit or a charter home_units name
            bad.append(f"{x['name']}: home department {h['home_department']!r} is not a charter department, affiliated unit or [census].home_units name (title text? fix home_units or hold)")
    # a build older than the reviewed inputs that feed the census is stale (Georgia Tech friction 22: a stage-3 chain started by a leftover background
    # command built from the census before the last stage-2 review landed); re-run census-refresh and build with --force
    pis_f = Path(P.data('pis.json', key))
    if pis_f.exists():
        for n in ('cs-related-review.json', 'census-additions.json', 'cs-related-hand.json'):
            f = Path(P.data(n, key))
            if f.exists() and f.stat().st_mtime > pis_f.stat().st_mtime + 1:
                bad.append(f'stale build: pis.json is older than reviewed/{n} (run census-refresh, homes and build again with --force)')
    import lab_websites
    register = Path(P.data('lab-websites.json', key))
    if register.exists():
        website_doc = read(register, {})
        if pis_f.exists() and register.stat().st_mtime + 1 < pis_f.stat().st_mtime:
            bad.append('website register is older than pis.json (refresh lab_websites.py build)')
    elif pis_f.exists() and Path(P.data('labpage-audit.jsonl.gz', key)).exists():
        website_doc = lab_websites.build(key)
    else:
        website_doc = {}
        bad.append(f'lab-page audit: register/audit missing (tools/lab_websites.py build {key}; docs/LAB-PAGES.md)')
    bad += lab_websites.gate(website_doc, website_expected(key, website_doc))
    return bad, dict(pis=len(pis_of(key)), homes=len(homes))


def pi_years(x):
    """The span a PI must be evidenced for: first to last year with a professor rank (ladder or courtesy) when the census
    has ranks per year, else first to last listed year. Learned 2026-10-30: an 'Assistant Research Scientist' row in
    2020 does not open a span for a professorship from 2025 (Ziyou Song); an adjunct year inside a professorship is
    still a listed year (Jason Corso, adjunct in 2021)."""
    rk = x.get('ranks_by_year') or {}
    pr = sorted({int(y) for y, r in rk.items() if {'ladder', 'courtesy'} & set(r if isinstance(r, list) else [r])}) if rk else []
    ys = sorted(set(x.get('years_listed') or []))
    return list(range(pr[0], pr[-1] + 1)) if pr else (list(range(ys[0], ys[-1] + 1)) if ys else [])


def span_gaps(x):
    """Years of pi_years(x) with no listing of any rank."""
    have = set(x.get('years_listed') or [])
    return [y for y in pi_years(x) if y not in have]


def proven_years(key, name):
    """Gap years of a PI that a dated capture of the deep second look (periods_school.py deep) proves with a ladder-title quote."""
    d = read(P.data('deep-gap-evidence.json', key), {}) or {}
    return {int(y) for y in ((d.get(name) or {}).get('evidence') or {})}


def g4(key):
    per = read(P.data('faculty-periods.json', key), [])
    ov = CO.section(key)
    have = {p['name'] for p in per} | {k for k, v in ov.items() if isinstance(v, dict) and v.get('periods')}
    bad, n = [], collections.Counter()
    for x in pis_of(key):
        if x['name'] in have:
            n['period'] += 1; continue
        ys = sorted(set(x.get('years_listed') or []))
        o = ov.get(x['name']) or {}
        gaps = [y for y in span_gaps(x) if y not in proven_years(key, x['name'])]   # years a dated capture proves count as listed
        if ys and gaps and o.get('unproven_years') and o.get('why_unproven') and set(gaps) <= set(o['unproven_years']):
            n['gap_reviewed_unproven'] += 1; continue  # searched, no dated evidence: those years prove nothing (R-PAP-01)
        if ys and not gaps:
            n['contiguous_listings'] += 1; continue
        bad.append(f"{x['name']}: no period, listing years {ys}")
    for p in per:
        for f in ('facultyStart', 'facultyEnd', 'labStart', 'labEnd'):
            v = p.get(f)
            if v is not None and not ISO.match(str(v)):
                bad.append(f"{p['name']}: {f} {v!r} is not an ISO date (2026-10-29), so pi_hierarchy.contains() reads it as unresolved")
    return bad, dict(n)


def g5(key):
    ov = CO.section(key)
    bad, n = [], collections.Counter()
    for x in pis_of(key):
        o = ov.get(x['name']) or {}
        a = [k for k, v in (('dblp', x.get('dblp') or o.get('dblp')), ('orcid', x.get('orcid') or o.get('orcid')),
                            ('openalex', x.get('openalex') or o.get('openalex'))) if v]
        if a:
            n['+'.join(a)] += 1
        elif o.get('no_identity') and o.get('why_no_identity'):   # reviewed: searched ORCID, homepage and CV, nothing attributable; no papers are attributed
            n['reviewed_no_identity'] += 1
        else:
            bad.append(f"{x['name']}: no DBLP id, ORCID or reviewed OpenAlex id")
    gaps = yield_gaps(key)   # an anchor that yields no papers is no anchor (ROADMAP #43)
    bad += [f"{name}: anchors yield 0 papers ({why})" for name, why in (gaps or [])]
    return bad, dict(n, anchors_yield_checked=gaps is not None)


def pi_reasons(key, name):
    """The recorded reasons a PI may have no papers: census-overrides `no_identity` + `why_no_identity`, or `no_papers` +
    `why_no_papers` (a reviewed search that found nothing attributable), or a lab-coverage-reasons `papers` reason."""
    o = CO.section(key).get(name) or {}
    if o.get('no_identity') and o.get('why_no_identity') or o.get('no_papers') and o.get('why_no_papers'):
        return True
    r = (read(P.data('lab-coverage-reasons.json', key), {}) or {}).get(name) or {}
    return bool((r.get('papers') or {}).get('why'))


def yield_gaps(key):
    """[(PI, anchors)] for the PIs of the built package (pis.json) whose anchors yield no papers (verifiedWorks and labPapers both 0)
    and that have no recorded reason (pi_reasons); None when the school has no pis.json yet (nothing to measure). Georgia Tech
    2026-11-04: ten PIs passed stage 5 on a bare DBLP pid that gave no titles and no OpenAlex id."""
    pis = read(P.data('pis.json', key))
    if pis is None:
        return None
    out = []
    for p in pis if isinstance(pis, list) else pis.get('pis', []):
        c = p.get('counts') or {}
        if c.get('verifiedWorks', 0) or c.get('labPapers', 0) or pi_reasons(key, p['pi']):
            continue
        a = [k for k, v in (('DBLP', p.get('dblp')), ('ORCID', p.get('orcid')), ('OpenAlex', p.get('reviewedOpenAlex'))) if v]
        out.append((p['pi'], '+'.join(a) or 'no anchor'))
    return out


ISO = re.compile(r'^\d{4}(-\d{2}(-\d{2})?)?$')
CODE = Path(__file__).resolve().parents[1]
ACCURACY_DIR = CODE / 'accuracy'
COPIES_TARGET = 0.85
ACCURACY_BARS = (('lab_precision_uniform', 0.95), ('student_precision_uniform', 0.97), ('lab_coverage', 0.90))


def audit_open(key, checks):
    """Unexplained items of the chain audit's checks (tools/chain_audit.py), read in-process; never writes chain-audit.json."""
    import chain_audit
    res = chain_audit.audit(key)['checks']
    bad = [f'{c}: {res[c]["n_unexplained"]} unexplained of {res[c]["total"]}' for c in checks if res[c]['n_unexplained']]
    return bad, {c: res[c]['pass'] for c in checks}


def acceptance_gate(key, part):
    a = read(P.data('labpage-acceptance.json', key))
    if not a:
        return [f'lab-page {part} acceptance: labpage-acceptance.json missing (docs/LAB-PAGES.md rounds)']
    r = a.get(part) or {}
    return [] if r.get('accepted') else [f"lab-page {part} acceptance: not accepted ({str(r.get('reason') or r.get('note') or 'no decision')[:160]})"]


def g6(key):
    bad = acceptance_gate(key, 'students')
    b2, n = audit_open(key, ('students', 'one_person'))
    # student RECALL (owner 2026-11-11): the acceptance above measures precision; this asks whether the students are all there (tools/student_recall.py)
    import student_recall as R
    return bad + b2 + R.gate_items(key), dict(n, **R.gate_counts(key))


def g7(key):
    bad = acceptance_gate(key, 'papers')
    b2, n = audit_open(key, ('papers', 'links'))
    return bad + b2, n


def g8(key):
    c = read(P.data('copies.json', key))
    bad = []
    if not c:
        return [f'copies: hierarchy/{key}/copies.json missing (tools/lab_paper_copies.py {key})'], {}
    sm = c.get('summary') or {}
    n, loc = sm.get('lab_papers') or 0, sm.get('local') or 0
    share = loc / n if n else 0
    # the 85% share is a TARGET, not a gate (owner 2026-11-05, after Georgia Tech: ceiling 53.3% under the access rules): the gate needs measured
    # copies and a ledger reason for every paper without one; a shortfall is reported in the counts (target_met), never failed
    if not read(P.data('unavailable-summary.json', key)):
        bad.append(f'ledger: unavailable-summary.json missing (fulltext-push/unavailable_ledger.py {key})')
    return bad, dict(lab_papers=n, local=loc, local_share=round(share, 3), copy_target=COPIES_TARGET, copy_target_met=share >= COPIES_TARGET)


def g9(key):
    d = read(ACCURACY_DIR / f'summary-{key}.json')
    if not d:
        return [f'accuracy: accuracy/summary-{key}.json missing (accuracy/sample.py --school {key}, then the verdicts and summarize.py)'], {}
    bad = []
    for k, bar in ACCURACY_BARS:
        p = (d.get(k) or {}).get('p')
        if p is None or p < bar:
            bad.append(f'accuracy: {k} {p} < {bar}')
    if d.get('files') and d.get('files') != d.get('files_now'):
        bad.append('accuracy: the build changed since the sample was drawn (files != files_now)')
    return bad, dict(n_verdicts=d.get('n_verdicts'))


def g10(key):
    bad = []
    if S.get(key).get('status') != 'released':
        bad.append(f'charter status is {S.get(key).get("status")!r}, not "released"')
    man = read(Path(P.RELEASES) / 'latest' / 'MANIFEST.json') or {}
    if key not in (man.get('counts') or {}):
        bad.append('the newest release does not count this school')
    return bad, {}


GATES = {'0': g0, '1': g1, '2': g2, '3': g3, '4': g4, '5': g5, '6': g6, '7': g7, '8': g8, '9': g9, '10': g10}


def exceptions(key):
    return read(P.data('gate-exceptions.json', key), {}) or {}


def traps_for(key, stage):
    """The known onboarding traps of the stage (tools/onboarding_traps.py): findings, or nothing when the charter is missing."""
    import onboarding_traps as T
    try:
        return T.for_stage(key, stage)
    except KeyError:
        return []


def evaluate(key, stage):
    """Evaluate all findings; scoped exceptions authorize exact reviewed items, never new findings."""
    bad, counts = GATES[str(stage)](key)
    bad = list(bad) + traps_for(key, stage)
    w = exceptions(key).get(str(stage))
    waived, error = [], None
    if bad and w and w.get('reason'):
        if 'allow_items' in w:
            allowed = w['allow_items']
            if not isinstance(allowed, list) or not all(isinstance(x, str) and x for x in allowed):
                error = 'allow_items must be a list of exact gate finding strings'
            elif not isinstance(w.get('owner_quote'), str) or not w['owner_quote'].strip():
                error = 'scoped exceptions require the quoted owner authorization in owner_quote'
            else:
                waived = [x for x in bad if x in set(allowed)]
        elif S.get(key).get('status') == 'onboarding':
            error = 'onboarding exceptions require exact allow_items and owner_quote'
        else:
            waived = list(bad)  # preserve the recorded legacy exceptions of released schools
    unwaived = [x for x in bad if x not in waived]
    gate = 'pass' if not bad else ('waived' if not unwaived else 'fail')
    return dict(stage=int(stage), gate=gate, open=len(bad), items=bad, waiver=(w if gate == 'waived' else None),
                waived_items=waived, unwaived_items=unwaived, **({'exception_error': error} if error else {}), **counts)


# ---- the stages run themselves (ROADMAP #39) -------------------------------------------------------------------------------------
# step = dict(name, kind, cmd, ...). kind: local (run here, argv list) | slurm (one stage of a pipeline: cmd for hierarchy/pipeline-stage.slurm,
# py project|collector, cpus, mem, time) | hand (a review or judgement step: the run stops there and prints `todo`).
# done: data names whose existence means the step ran. shared: the step writes a shared file (needs --allow-shared).
def L(name, script, *args, done=(), shared=False, py='project'):
    return dict(name=name, kind='local', script=script, args=list(args), done=list(done), shared=shared, py=py)


def Q(name, cmd, cpus=2, mem='16G', time='04:00:00', py='project', done=(), shared=False, check=None, check_py=None, newer_than=()):
    return dict(name=name, kind='slurm', cmd=cmd, cpus=cpus, mem=mem, time=time, py=py, done=list(done), shared=shared, check=check, check_py=check_py, newer_than=list(newer_than))


def H(name, todo):
    return dict(name=name, kind='hand', todo=todo)


STEPS = {
    '0': [L('hosts', 'tools/school_hosts.py', '{key}', done=['hosts.json']),
          H('snapshot', 'extend the OpenAlex snapshot for the school (no API credits): OA_DATE=<snapshot date> atlas pipeline snapshot-ext SCHOOLS={key} --from-worktree --wait; the charter must be committed first'),
          H('charter', 'fill schools/{key}.toml (TEMPLATE.toml documents every field), atlas charters, review and commit it')],
    '1': [Q('captures', 'bash $TOOLS/../listings/scripts/run_school.sh {school}', cpus=1, mem='4G', time='12:00:00', check=['listings/scripts/plan_fetch.py', '{key}', '--check']),
          L('rows', 'tools/listing_rows.py', '{key}'),
          H('coverage', 'each department-year without an ok capture needs a plan reason (nocapture, unusable, out_of_scope); fix format drift in tools/listing_formats.py')],
    '2': [L('census', 'tools/census_build.py', '{key}', done=['census-faculty.json']),
          # the school's data from its snapshot extension and the DBLP dump, no API credit (what `atlas pipeline onboard-data` runs; UChicago friction 22):
          Q('dblp', 'PY $TOOLS/dblp_affiliated.py {school} --pubs', cpus=2, mem='16G', time='03:00:00', done=['dblp-affiliated.json']),
          Q('sweep', 'PY $TOOLS/sweep_from_snapshot.py {school} --replace', cpus=2, mem='24G', time='02:00:00', done=['openalex-sweep.sqlite']),
          Q('sweepcheck', 'PY $TOOLS/sweep_check.py {school}', cpus=2, mem='24G', time='01:00:00', done=['sweep-check.json']),
          Q('openalex-candidates', 'PY $TOOLS/cs_related_candidates.py --no-venues --stats --out cs-related-candidates-openalex.json {school}', mem='24G', time='02:00:00', done=['cs-related-candidates-openalex.json']),
          Q('units', 'PY $TOOLS/cs_related_school.py units {school}', cpus=1, mem='4G', time='06:00:00', check=['tools/cs_related_school.py', 'units-check', '{key}'], check_py='project'),   # unit listings by Wayback incl. their pages; done when units-done.json covers the charter's units
          L('candidates', 'tools/cs_related_school.py', 'candidates', '{key}'),
          L('cross-check', 'tools/listed_not_in_census.py', '{key}', done=['listed-not-in-census.json']),
          H('review', 'search the affiliated units (cs_related_school.py units), then decide every candidate (cs_related_school.py review) with its evidence')],
    '3': [L('census-refresh', 'tools/census_build.py', '{key}'),   # the review's additions get their person records only on a re-run (UChicago friction 28)
          L('homes', 'tools/home_departments_school.py', '{key}'),   # school-local file; always re-run (the census changed)
          L('homes-shared', 'tools/home_departments_school.py', '{key}', '--write-shared', shared=True),
          Q('build', 'PY $TOOLS/pi_hierarchy.py {school}', cpus=3, mem='40G', time='02:00:00', done=['pis.json']),   # the lab-page audit reads pis.json (Michigan built at stage 3: UChicago friction 27)
          Q('labpage-discover', 'PY $TOOLS/labpage_audit.py discover {school}', time='12:00:00', done=['labpage-audit-discovery.jsonl']),
          Q('labpage-audit', 'PY $TOOLS/labpage_audit.py audit {school}', cpus=2, mem='16G', time='02:00:00', done=['labpage-audit.jsonl.gz']),   # discover alone writes labpage-audit-discovery.jsonl; the gate reads the audit's file (friction 29)
          H('pi-basis', 'research and teaching faculty need reviewed evidence of a group or advisees (pi-basis-evidence.json)')],
    '4': [Q('periods-fetch', 'PY $TOOLS/periods_school.py fetch {school}', cpus=1, mem='8G', time='08:00:00'),
          Q('periods-extract', 'PY $TOOLS/periods_school.py extract {school}', time='02:00:00'),
          Q('periods-gaps', 'PY $TOOLS/periods_school.py gaps {school}', time='04:00:00'),
          Q('periods-extend', 'PY $TOOLS/periods_school.py extend {school}', time='04:00:00'),
          Q('periods-truncated', 'PY $TOOLS/periods_school.py truncated {school}', time='04:00:00', done=['truncated-title-evidence.json']),
          Q('periods-deep', 'PY $TOOLS/periods_school.py deep {school}', time='10:00:00', done=['deep-gap-evidence.json']),   # the second look at the PIs left open by gaps/extend
          H('holds', 'review periods/<key>-holds.json; a departure the page states is faculty_end_moved evidence; periods use ISO dates')],
    '5': [Q('dblp-ids', 'PY $TOOLS/dblp_ids_school.py {school}', mem='24G', time='01:00:00', done=['dblp-ids.json']),
          Q('homepage-links', 'PY $TOOLS/homepage_links_school.py {school}', time='04:00:00', done=['homepage-identity.json']),
          Q('dblp-dump-persons', 'PY $TOOLS/dblp_dump_persons.py {school}', mem='24G', time='01:00:00', done=['dblp-dump-persons-school.json.gz']),   # school-local: the shared file feeds release builds (friction 43)
          H('openalex-identity', 'first re-run tools/census_build.py <key> (it folds dblp-ids.json into the census; the gate reads the census), then write hierarchy/<key>/openalex-identity-review.json, then tools/oa_identity_school.py <key>; review namesakes and cross-school PIs')],
    '6': [Q('labpage-links', 'PY $TOOLS/labpage_students_school.py links {school}', time='06:00:00', py='collector'),
          Q('labpage-extract', 'PY $TOOLS/labpage_students_school.py extract {school}', time='04:00:00', py='collector'),
          Q('student-directories', 'PY $TOOLS/labpage_students_school.py directory {school}', time='06:00:00', py='collector'),
          H('rounds', 'the lab-page students rounds (docs/LAB-PAGES.md): a fresh sample of 20, its hand check (atlas review-page), a rule fix and a NEW sample on failure, three failed rounds stop the work; record them in labpage-handcheck.json')],
    '7': [Q('pi-works', 'PY $TOOLS/pi_fulltext_affiliation.py works {school} --from-snapshot', mem='24G', time='06:00:00'),
          Q('dblp-recover', 'PY $TOOLS/dblp_recover.py {school}', time='06:00:00'),
          # the lab-page paper pass of a charter school is the audit's own recover + audit (labpage_recover.py needs labpage-pubs.jsonl.gz, which no step produces: UChicago stage 7); no OpenAlex key in the job
          Q('labpage-audit-recover', 'PY $TOOLS/labpage_audit.py recover {school}', time='08:00:00'),
          Q('labpage-audit', 'PY $TOOLS/labpage_audit.py audit {school}', time='02:00:00'),
          Q('build', 'PY $TOOLS/pi_hierarchy.py {school}', cpus=3, mem='40G', time='02:00:00', done=['pis.json'], newer_than=['pi-works.sqlite']),
          Q('link-diagnosis', 'PY $TOOLS/link_diagnosis.py {school}', mem='24G', time='02:00:00', done=['link-diagnosis.json']),
          H('review', 'zero-paper labs need reasons, the links check needs 0 open, the lab-page papers round (a fresh 20, at most 1 error)')],
    '8': [L('add-works', 'fulltext-push/add_works.py', '{key}', py='collector'),
          dict(name='channels', kind='hand', todo='SCHOOL={key} CHANNELS="oa_arxiv openalex proceedings arxiv_title dblp_ee s2 europepmc pmc figshare labpages" atlas submit fulltext-push/school-channels.slurm, then add the school to the downloads array (docs/RUNBOOK.md)'),
          Q('copies', 'PY $TOOLS/lab_paper_copies.py {school}', done=['copies.json']),
          Q('ledger', 'PY $FTP/unavailable_ledger.py {school}', mem='20G', time='06:00:00', py='collector', done=['unavailable-summary.json'])],
    '9': [L('sample', 'accuracy/sample.py', '--school', '{key}'),
          H('verdicts', '105 hand judgments (atlas review-page accuracy/sample-{key}.json), then accuracy/summarize.py; below a threshold add a general rule with a test, never a one-off fix')],
    '10': [H('release', 'status = "released" in the charter, regenerate paths.sh, run the rebuild and the export, hand off to the site (the owner or coordinator decides)')],
}


def expand(s, key):
    return s.replace('{key}', key).replace('{school}', key)


def step_done(key, st, run=None):
    """A step is done when its output files exist, or (`check`: a script of this checkout, run isolated) when the check exits 0 (stage 1's captures:
    `plan_fetch.py <key> --check`, because the file the next step writes, coverage.json, can not be the proof that the captures ran)."""
    if st.get('check'):
        import subprocess
        interp = [sys.executable, '-u'] if st.get('check_py') == 'project' else [P.COLLECTOR_PY, '-I', '-u']   # tools that import their siblings need the project interpreter
        argv = interp + [str(CODE / st['check'][0])] + [expand(a, key) for a in st['check'][1:]]
        return (run or subprocess.run)(argv, cwd=str(CODE), capture_output=True).returncode == 0
    if not (st.get('done') and all(Path(P.data(n, key)).exists() for n in st['done'])):
        return False
    # R12 (Georgia Tech friction 35): a step is stale when an input it reads was rewritten after its output (the build after pi-works)
    ins = [Path(P.data(n, key)) for n in st.get('newer_than') or [] if Path(P.data(n, key)).exists()]
    return not ins or all(Path(P.data(n, key)).stat().st_mtime >= max(i.stat().st_mtime for i in ins) for n in st['done'])


def onboarding_only(key):
    if S.get(key).get('status') != 'onboarding':
        raise SystemExit(f'refused: {key} is {S.get(key).get("status")!r}; stage-gate --run only works on a school that is onboarding (it never writes released data)')


def run_stage(key, stage, dry=False, submit=False, force=False, allow_shared=False, run=None, repo=None):
    """Run a stage's steps up to its first review step. -> (status, log) with status: complete (no hand step left) | review (stopped at a
    hand step) | failed (a step failed) | submitted (Slurm stages are queued; read their output files, then run the stage again)."""
    import subprocess
    run = run or subprocess.run
    log, slurm = [], []
    status = 'complete'
    for st in STEPS[str(stage)]:
        n = st['name']
        if st['kind'] == 'hand':
            if slurm:  # earlier steps are still queued: the judgement needs their output
                log.append(dict(step=n, result='waits for the queued steps'))
                status = 'submitted'
                break
            log.append(dict(step=n, result='review', todo=expand(st['todo'], key)))
            status = 'review'
            break
        if step_done(key, st) and not force:
            log.append(dict(step=n, result='done (output exists)'))
            continue
        if st['shared'] and not allow_shared:
            log.append(dict(step=n, result='skipped: writes a shared file, needs --allow-shared'))
            continue
        if st['kind'] == 'local':
            if slurm and not dry:  # a local step after a queued one reads its output (stage 1: rows need the captures): run it on the next pass
                log.append(dict(step=n, result='waits for the queued steps'))
                status = 'submitted'
                break
            interp = [sys.executable, '-u'] if st['py'] == 'project' else [P.COLLECTOR_PY, '-I', '-u']
            argv = interp + [str(CODE / st['script'])] + [expand(a, key) for a in st['args']]
            if dry:
                log.append(dict(step=n, result='dry run', argv=argv))
                continue
            r = run(argv, cwd=str(CODE))
            log.append(dict(step=n, result='ok' if r.returncode == 0 else f'failed rc={r.returncode}'))
            if r.returncode:
                status = 'failed'
                break
        else:
            slurm.append(st)
            log.append(dict(step=n, result='queued' if submit and not dry else 'slurm (not submitted: pass --submit)', cmd=expand(st['cmd'], key)))
    if slurm and submit and not dry and status in ('complete', 'review', 'submitted'):
        import atlas_pipeline as AP
        stages = [(s['name'], 'school', s['cmd'], s['py'], s['cpus'], s['mem'], s['time']) for s in slurm]
        jobs = AP.submit(f'stage{stage}-{key}', [key], stages=stages, guard_preempt=True, repo=repo)
        log.append(dict(step='slurm', result='submitted', jobs=jobs))
        status = 'submitted'
    elif slurm and status == 'complete':
        status = 'submitted' if submit and not dry else 'review'
    elif slurm and status == 'failed':  # nothing was queued: say so instead of the 'queued' entries above
        for e in log:
            if e.get('result') == 'queued':
                e['result'] = 'not submitted (a step failed)'
    return status, log


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key'); ap.add_argument('stages', nargs='*')
    ap.add_argument('--run', action='store_true'); ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--submit', action='store_true')
    ap.add_argument('--from-worktree', action='store_true', help='Slurm steps run this worktree\'s committed HEAD (a charter not landed on main yet)')
    ap.add_argument('--traps', action='store_true', help='print every known onboarding trap check (tools/onboarding_traps.py) and exit 1 on a finding')
    ap.add_argument('--record', action='store_true', help='evaluate the gates and write stage-<n>-gate.json without running any step (refreshes a stale recorded gate)')
    ap.add_argument('--force', action='store_true'); ap.add_argument('--allow-shared', action='store_true'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    key = a.key
    if a.traps:
        import onboarding_traps as T
        found = T.run(key, T.checks_upto(max(map(int, a.stages)) if a.stages else None))   # only the checks the stage can have work for
        for f in found:
            print(f)
        print(f'{key}: {len(found)} trap finding(s)')
        return 1 if found else 0
    stages = a.stages or list(GATES)
    bad_stage = [s for s in stages if s not in GATES]
    if bad_stage:
        ap.error(f'unknown stage {bad_stage}; stages are {", ".join(GATES)}')
    if a.run:
        onboarding_only(key)
    ok, out = True, []
    for st in stages:
        ran = None
        if a.run:
            status, log = run_stage(key, st, dry=a.dry_run, submit=a.submit, force=a.force, allow_shared=a.allow_shared,
                                    repo=CODE if a.from_worktree and CODE.resolve() != Path(P.CODE).resolve() else None)
            ran = dict(status=status, steps=log)
            for e in log:
                print(f"  step {e['step']}: {e['result']}" + (f" -> {e['todo']}" if e.get('todo') else '') + (f" ({e['cmd']})" if e.get('cmd') else ''))
        res = evaluate(key, st)
        ok &= res['gate'] != 'fail'
        out.append(res)
        shown = {k: v for k, v in res.items() if k not in ('items', 'waiver')}
        print(json.dumps(shown))
        if res['waiver']:
            print('    waived: ' + res['waiver']['reason'])
        for b in res['items'][:int(__import__('os').environ.get('SHOW', 15))]:
            print('   ', b)
        if (a.run or a.record) and not a.dry_run:
            rep = Path(P.HIERARCHY) / key / 'reports'
            rep.mkdir(parents=True, exist_ok=True)
            (rep / f'stage-{st}-gate.json').write_text(json.dumps(dict(school=key, at=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), run=ran, result=res), indent=1) + '\n')
        if ran and (ran['status'] in ('review', 'failed', 'submitted') or res['gate'] == 'fail'):
            print(f"stopped at stage {st}: {ran['status']}")
            break
    if a.json:
        print(json.dumps(out))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
