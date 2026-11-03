"""Check a protocol school's stage gates (docs/ADDING-A-SCHOOL.md) from the files the stages wrote, before the school is
wired into pi_hierarchy.py / chain_audit.py. Prints one JSON line per stage and the items that fail.

  1 sources   every department of the charter has an ok listing capture in every window year (listings/<key>/coverage.json);
              a missing year must carry a plan reason
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
  5 identity  every PI has an anchor: a DBLP id, an ORCID or a reviewed OpenAlex id (census, additions, census-overrides)
  0 charter   school_config check passes and every host of the charter is consistent (hosts.json)
  6 students  the lab-page students acceptance is accepted, and the chain audit's students and one_person checks are explained
  7 papers    the lab-page papers acceptance is accepted, and the chain audit's papers and links checks are explained
  8 texts     copies are measured (local share >= 85% of lab papers), the chain audit's copies check is explained, and the ledger exists
  9 accuracy  accuracy/summary-<key>.json: lab precision >= .95, student-link precision >= .97, lab coverage >= .90, on the current build
 10 release   the charter says released and the newest release counts the school
A gate a hand decision waives is recorded in hierarchy/<key>/reviewed/gate-exceptions.json ({"6": {"reason", "by", "decided"}}): it
reports `waived`, with the reason, and the open items stay listed. Michigan shipped that way (stages 6-9, owner, 2026-11-02).

`--run` makes the stage run itself up to its first review step (ROADMAP #39): it runs the stage's mechanical steps in order (local
ones here, heavy ones as one Slurm pipeline of afterok stages, `--submit`), skips a step whose output exists (`--force` re-runs), stops
at a failed step or a hand step and prints what to review, then evaluates the gate and writes hierarchy/<key>/reports/stage-<n>-gate.json.
It refuses a released school: this command never writes released data. A step that writes a shared file runs only with `--allow-shared`.

usage: stage_gate.py <key> [stage ...] [--run [--dry-run] [--submit] [--force] [--allow-shared]] [--json]
"""
import collections, json, re, sys
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402


def read(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def pis_of(key):
    cen = read(P.data('census-faculty.json', key), {}).get('faculty', [])
    add = read(P.data('census-additions.json', key), [])
    return [x for x in cen + add if x.get('is_pi')]


def g1(key):
    cov = read(P.data('coverage.json', key), {}); lo, hi = S.get(key).get('window')
    bad = []
    for d in S.get(key).get('departments') or []:
        for y in range(lo, hi + 1):
            v = (cov.get(d['code']) or {}).get(str(y)) or {}
            if not any(s == 'ok' for s in v.values()):
                bad.append(f"{d['code']} {y}: " + ('; '.join(sorted(set(v.values()))) or 'never planned'))
    return bad, dict(departments=len(S.get(key).get('departments') or []))


def sweep_gate(key):
    """The bulk-pull sanity check (tools/sweep_check.py -> hierarchy/<key>/sweep-check.json) must exist and pass."""
    sc = read(P.data('sweep-check.json', key))
    if not sc:
        return ['sweep check: hierarchy/<key>/sweep-check.json missing (run tools/sweep_check.py <key>)'.replace('<key>', key)]
    return [f"sweep check: {t['test']} {t.get('year') or ''} {t['why']}".replace('  ', ' ') for t in sc.get('failed') or []] + \
           (['sweep check: status ' + str(sc.get('status'))] if sc.get('status') != 'pass' and not sc.get('failed') else [])


def g2(key):
    cands = read(P.data('cs-related-candidates.json', key), [])
    rev = read(P.data('cs-related-review.json', key), {}) or {}
    dec = {d['name']: d for d in rev.get('decisions', [])}
    bad = [f"{c['name']}: no decision" for c in cands if c['name'] not in dec and not any(a in dec for a in c.get('aliases') or [])]
    bad += [f"{d['name']}: {d['decision']} ({d['reason'][:100]})" for d in dec.values() if d['decision'] == 'pending_openalex']
    bad += sweep_gate(key)  # the OpenAlex sweep and the DBLP pulls feed the review (owner standard 2026-10-30)
    return bad, dict(candidates=len(cands), **collections.Counter(d['decision'] for d in dec.values()))


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
    if not Path(P.data('labpage-audit.jsonl.gz', key)).exists():
        bad.append(f'lab-page audit: labpage-audit.jsonl.gz missing (tools/labpage_audit.py discover {key}; docs/LAB-PAGES.md)')
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


def g4(key):
    per = read(P.data('faculty-periods.json', key), [])
    ov = (read(P.data('census-overrides.json'), {}) or {}).get(key, {})
    have = {p['name'] for p in per} | {k for k, v in ov.items() if isinstance(v, dict) and v.get('periods')}
    bad, n = [], collections.Counter()
    for x in pis_of(key):
        if x['name'] in have:
            n['period'] += 1; continue
        ys = sorted(set(x.get('years_listed') or []))
        o = ov.get(x['name']) or {}
        gaps = span_gaps(x)
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
    ov = (read(P.data('census-overrides.json'), {}) or {}).get(key, {})
    bad, n = [], collections.Counter()
    for x in pis_of(key):
        o = ov.get(x['name']) or {}
        a = [k for k, v in (('dblp', x.get('dblp') or o.get('dblp')), ('orcid', x.get('orcid') or o.get('orcid')),
                            ('openalex', x.get('openalex') or o.get('openalex'))) if v]
        if a:
            n['+'.join(a)] += 1
        else:
            bad.append(f"{x['name']}: no DBLP id, ORCID or reviewed OpenAlex id")
    return bad, dict(n)


ISO = re.compile(r'^\d{4}(-\d{2}(-\d{2})?)?$')
CODE = Path(__file__).resolve().parents[1]
ACCURACY_DIR = CODE / 'accuracy'
COPIES_TARGET = 0.85
ACCURACY_BARS = (('lab_precision_uniform', 0.95), ('student_precision_uniform', 0.97), ('lab_coverage', 0.90))


def g0(key):
    bad = [f'charter: {p}' for p in S.check(key)]
    hosts = read(P.data('hosts.json', key))
    if hosts is None:
        bad.append(f'hosts: hierarchy/{key}/hosts.json missing (run tools/school_hosts.py {key})')
    else:
        bad += [f"host {h['host']}: " + '; '.join(h.get('problems') or ['inconsistent']) for h in hosts.get('hosts', []) if not h.get('consistent')]
    return bad, dict(hosts=len((hosts or {}).get('hosts', [])))


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
    return bad + b2, n


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
    if share < COPIES_TARGET:
        bad.append(f'copies: local share {share:.3f} < {COPIES_TARGET} ({loc} of {n})')
    if not read(P.data('unavailable-summary.json', key)):
        bad.append(f'ledger: unavailable-summary.json missing (fulltext-push/unavailable_ledger.py {key})')
    return bad, dict(lab_papers=n, local=loc, local_share=round(share, 3))


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


def evaluate(key, stage):
    """-> dict(stage, gate pass|waived|fail, open, counts, items, waiver)."""
    bad, counts = GATES[str(stage)](key)
    w = exceptions(key).get(str(stage))
    gate = 'pass' if not bad else ('waived' if w and w.get('reason') else 'fail')
    return dict(stage=int(stage), gate=gate, open=len(bad), items=bad, waiver=(w if gate == 'waived' else None), **counts)


# ---- the stages run themselves (ROADMAP #39) -------------------------------------------------------------------------------------
# step = dict(name, kind, cmd, ...). kind: local (run here, argv list) | slurm (one stage of a pipeline: cmd for hierarchy/pipeline-stage.slurm,
# py project|collector, cpus, mem, time) | hand (a review or judgement step: the run stops there and prints `todo`).
# done: data names whose existence means the step ran. shared: the step writes a shared file (needs --allow-shared).
def L(name, script, *args, done=(), shared=False, py='project'):
    return dict(name=name, kind='local', script=script, args=list(args), done=list(done), shared=shared, py=py)


def Q(name, cmd, cpus=2, mem='16G', time='04:00:00', py='project', done=(), shared=False):
    return dict(name=name, kind='slurm', cmd=cmd, cpus=cpus, mem=mem, time=time, py=py, done=list(done), shared=shared)


def H(name, todo):
    return dict(name=name, kind='hand', todo=todo)


STEPS = {
    '0': [L('hosts', 'tools/school_hosts.py', '{key}', done=['hosts.json']),
          Q('sweep', 'PY $TOOLS/sweep_school.py {school}', cpus=1, mem='8G', time='1-00:00:00', done=['sweep-check.json']),
          H('charter', 'fill schools/{key}.toml (TEMPLATE.toml documents every field), atlas charters, review and commit it')],
    '1': [Q('captures', 'bash $TOOLS/../listings/scripts/run_school.sh {school}', cpus=1, mem='4G', time='12:00:00', done=['coverage.json']),
          L('rows', 'tools/listing_rows.py', '{key}'),
          H('coverage', 'each department-year without an ok capture needs a plan reason (nocapture, unusable, out_of_scope); fix format drift in tools/listing_formats.py')],
    '2': [L('census', 'tools/census_build.py', '{key}', done=['census-faculty.json']),
          L('candidates', 'tools/cs_related_school.py', 'candidates', '{key}'),
          Q('openalex-candidates', 'PY $TOOLS/cs_related_candidates.py --no-venues --stats --out cs-related-candidates-openalex.json {school}', mem='24G', time='02:00:00'),
          L('cross-check', 'tools/listed_not_in_census.py', '{key}', done=['listed-not-in-census.json']),
          H('review', 'search the affiliated units (cs_related_school.py units), then decide every candidate (cs_related_school.py review) with its evidence')],
    '3': [L('homes', 'tools/home_departments_school.py', '{key}', '--write-shared', shared=True, done=['home-departments-school.json']),
          Q('labpage-discover', 'PY $TOOLS/labpage_audit.py discover {school}', time='12:00:00', done=['labpage-audit.jsonl.gz']),
          H('pi-basis', 'research and teaching faculty need reviewed evidence of a group or advisees (pi-basis-evidence.json)')],
    '4': [Q('periods-fetch', 'PY $TOOLS/periods_school.py fetch {school}', cpus=1, mem='8G', time='08:00:00'),
          Q('periods-extract', 'PY $TOOLS/periods_school.py extract {school}', time='02:00:00'),
          Q('periods-gaps', 'PY $TOOLS/periods_school.py gaps {school}', time='04:00:00'),
          Q('periods-extend', 'PY $TOOLS/periods_school.py extend {school}', time='04:00:00'),
          H('holds', 'review periods/<key>-holds.json; a departure the page states is faculty_end_moved evidence; periods use ISO dates')],
    '5': [Q('dblp-ids', 'PY $TOOLS/dblp_ids_school.py {school}', mem='24G', time='01:00:00'),
          Q('homepage-links', 'PY $TOOLS/homepage_links_school.py {school}', time='04:00:00'),
          H('openalex-identity', 'write hierarchy/<key>/openalex-identity-review.json, then tools/oa_identity_school.py <key>; review namesakes and cross-school PIs'),
          Q('dblp-dump-persons', 'PY $TOOLS/dblp_dump_persons.py', mem='24G', time='01:00:00', shared=True)],
    '6': [Q('labpage-links', 'PY $TOOLS/labpage_students_school.py links {school}', time='06:00:00', py='collector'),
          Q('labpage-extract', 'PY $TOOLS/labpage_students_school.py extract {school}', time='04:00:00', py='collector'),
          Q('student-directories', 'PY $TOOLS/labpage_students_school.py directory {school}', time='06:00:00', py='collector'),
          H('rounds', 'the lab-page students rounds (docs/LAB-PAGES.md): a fresh sample of 20, its hand check (atlas review-page), a rule fix and a NEW sample on failure, three failed rounds stop the work; record them in labpage-handcheck.json')],
    '7': [Q('pi-works', 'PY $TOOLS/pi_fulltext_affiliation.py works {school}', mem='24G', time='06:00:00'),
          Q('dblp-recover', 'PY $TOOLS/dblp_recover.py {school}', time='06:00:00'),
          Q('labpage-recover', 'PY $TOOLS/labpage_recover.py run {school}', time='08:00:00'),
          Q('build', 'PY $TOOLS/pi_hierarchy.py {school}', cpus=3, mem='40G', time='02:00:00', done=['pis.json']),
          H('review', 'zero-paper labs need reasons, the links check needs 0 open, the lab-page papers round (a fresh 20, at most 1 error)')],
    '8': [L('add-works', 'fulltext-push/add_works.py', '{key}', py='collector'),
          dict(name='channels', kind='hand', todo='SCHOOL={key} CHANNELS="oa_arxiv openalex proceedings arxiv_title dblp_ee s2 core europepmc pmc figshare labpages" atlas submit fulltext-push/school-channels.slurm, then add the school to the downloads array (docs/RUNBOOK.md)'),
          Q('copies', 'PY $TOOLS/lab_paper_copies.py {school}', done=['copies.json']),
          Q('ledger', 'PY $FTP/unavailable_ledger.py {school}', mem='20G', time='06:00:00', py='collector', done=['unavailable-summary.json'])],
    '9': [L('sample', 'accuracy/sample.py', '--school', '{key}'),
          H('verdicts', '105 hand judgments (atlas review-page accuracy/sample-{key}.json), then accuracy/summarize.py; below a threshold add a general rule with a test, never a one-off fix')],
    '10': [H('release', 'status = "released" in the charter, regenerate paths.sh, run the rebuild and the export, hand off to the site (the owner or coordinator decides)')],
}


def expand(s, key):
    return s.replace('{key}', key).replace('{school}', key)


def step_done(key, st):
    return bool(st.get('done')) and all(Path(P.data(n, key)).exists() for n in st['done'])


def onboarding_only(key):
    if S.get(key).get('status') != 'onboarding':
        raise SystemExit(f'refused: {key} is {S.get(key).get("status")!r}; stage-gate --run only works on a school that is onboarding (it never writes released data)')


def run_stage(key, stage, dry=False, submit=False, force=False, allow_shared=False, run=None):
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
        jobs = AP.submit(f'stage{stage}-{key}', [key], stages=stages, guard_preempt=True)
        log.append(dict(step='slurm', result='submitted', jobs=jobs))
        status = 'submitted'
    elif slurm and status == 'complete':
        status = 'submitted' if submit and not dry else 'review'
    return status, log


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key'); ap.add_argument('stages', nargs='*')
    ap.add_argument('--run', action='store_true'); ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--submit', action='store_true')
    ap.add_argument('--force', action='store_true'); ap.add_argument('--allow-shared', action='store_true'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    key = a.key
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
            status, log = run_stage(key, st, dry=a.dry_run, submit=a.submit, force=a.force, allow_shared=a.allow_shared)
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
        if a.run and not a.dry_run:
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
