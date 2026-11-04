"""`atlas pipeline <name>`: the mechanical chains as Slurm pipelines with dependencies (ROADMAP #34, 2026-11-01).

An agent used to submit a job, poll it, recount coverage, restamp acceptance files, rebuild the ledger and the copies by hand, one command after another.
A pipeline submits every stage at once, each `--dependency=afterok:` the one before, so nothing is polled (`--wait` makes one sacct call per 120 s or more, tools/slurm_wait.py) and nothing is typed between the stages; the agent
reads the result and judges. A stage is one job, or an array with one task per school.

  atlas pipeline --list
  atlas pipeline copies   [SCHOOLS="a b"] [--test-only] [--wait]   lab_paper_copies per school (array) -> unavailability ledger -> coverage recount -> collectors status
  atlas pipeline labpage  [SCHOOLS="a b"] [--test-only] [--wait]   lab-page audit per school (array) -> restamp the acceptance files -> the audit summary
  atlas pipeline onboard-data SCHOOLS=<key> [--from-worktree]   a school being onboarded: DBLP affiliation pass -> sweep from its snapshot extension -> sweep check -> OpenAlex candidates
  atlas pipeline build-audit SCHOOLS=<key> [--from-worktree] [--wait]  builder -> lab-page audit (after the students evidence changed)
  atlas pipeline snapshot-ext OA_DATE=<date> SCHOOLS=<key> [--wait]  the OpenAlex snapshot extension of a new school: 16 filter tasks -> merge
  atlas pipeline reader   [--test-only] [--wait]                   the reader export (licence -> host or link) after fresh copies
  atlas pipeline snapshot-refresh [--dry-run] [--promote] [--date D]   a newer OpenAlex snapshot -> NEW dated store -> per-school count compare (`current` moves only with --promote)
  atlas pipeline <name> ... --only <stage>                         just that stage (repeatable), after a diagnosed failure of one step
  atlas pipeline status [<run dir>]                                states of a run's jobs and the current dependency of each queued one (one sacct call, one squeue call)

Each run writes <scratch>/pipeline-<name>-<time>/jobs.json (stage -> job id). Every stage runs from a code snapshot of main's HEAD at submit time (--from-worktree: this worktree's committed HEAD, for onboarding code not landed yet)
(hierarchy/pipeline-stage.slurm). The commands live in PIPELINES below: a new chain is a new entry, not a new script. The judgement steps (the hand checks of
the lab-page rounds, the diagnosis of a failed stage) are not here and never will be.
"""
import argparse, datetime, json, os, subprocess, sys
from pathlib import Path

import atlas_paths as P  # noqa: E402

CODE = Path(__file__).resolve().parents[1]
# stage = (name, 'school' | 'once', command, interpreter, cpus, mem, time)   {school}/{schools} are filled by hierarchy/pipeline-stage.slurm
PIPELINES = {
    'copies': [
        ('copies', 'school', 'PY $TOOLS/lab_paper_copies.py {school}', 'project', 2, '16G', '02:00:00'),
        ('ledger', 'once', 'PY $FTP/unavailable_ledger.py {schools}', 'collector', 2, '24G', '04:00:00'),
        ('recount', 'once', 'PY $FTP/coverage_bands.py {schools}', 'collector', 1, '8G', '01:00:00'),
        ('status', 'once', 'PY $FTP/collectors_status.py', 'collector', 1, '4G', '00:30:00'),
    ],
    'labpage': [
        ('audit', 'school', 'PY $TOOLS/labpage_audit.py all {school}', 'project', 2, '16G', '12:00:00'),
        ('restamp', 'once', 'PY $TOOLS/labpage_audit.py restamp {schools}', 'project', 1, '8G', '00:30:00'),
        ('summary', 'once', 'PY $TOOLS/labpage_audit.py summary', 'project', 1, '8G', '00:30:00'),
    ],
    # a school being onboarded (docs/ADDING-A-SCHOOL.md stage 2): SCHOOLS="<key>". The sweep comes from the school's snapshot extension (stage 0), so the
    # extension merge must have finished; the DBLP pass and the OpenAlex candidate rule need no API credit.
    'onboard-data': [
        ('dblp', 'school', 'PY $TOOLS/dblp_affiliated.py {school} --pubs', 'project', 2, '16G', '03:00:00'),
        ('sweep', 'school', 'PY $TOOLS/sweep_from_snapshot.py {school} --replace', 'project', 2, '24G', '02:00:00'),
        ('sweepcheck', 'school', 'PY $TOOLS/sweep_check.py {school}', 'project', 2, '24G', '01:00:00'),
        ('candidates', 'school', 'PY $TOOLS/cs_related_candidates.py --no-venues --stats --out cs-related-candidates-openalex.json {school}', 'project', 2, '24G', '02:00:00'),
    ],
    # a school being onboarded, after its labpage evidence or census changed: the builder, then the lab-page audit (offline) that proposes additions from it
    'build-audit': [
        ('build', 'school', 'PY $TOOLS/pi_hierarchy.py {school}', 'project', 3, '40G', '02:00:00'),
        ('audit', 'school', 'PY $TOOLS/labpage_audit.py audit {school}', 'project', 2, '16G', '02:00:00'),
    ],
    # lab-page discovery for some PIs only (LABPI_ARGS='--pi "Name One" "Name Two"'), then the students from their pages and the rebuild
    'labpage-some': [
        ('discover', 'school', 'PY $TOOLS/labpage_audit.py discover {school} --redo $LABPI_ARGS', 'project', 2, '16G', '04:00:00'),
        ('links', 'school', 'PY $TOOLS/labpage_students_school.py links {school}', 'collector', 2, '16G', '06:00:00'),
        ('extract', 'school', 'PY $TOOLS/labpage_students_school.py extract {school}', 'collector', 2, '16G', '02:00:00'),
        ('build', 'school', 'PY $TOOLS/pi_hierarchy.py {school}', 'project', 3, '40G', '02:00:00'),
        ('audit', 'school', 'PY $TOOLS/labpage_audit.py audit {school}', 'project', 2, '16G', '02:00:00'),
    ],
    # the lab-page papers: resolve the listed titles (sweep, pi-works, arXiv, proceedings; no OpenAlex key in this job, so no title-search credit), then the audit
    'labpage-papers': [
        ('recover', 'school', 'PY $TOOLS/labpage_audit.py recover {school}', 'project', 2, '16G', '12:00:00'),
        ('audit', 'school', 'PY $TOOLS/labpage_audit.py audit {school}', 'project', 2, '16G', '02:00:00'),
    ],
    # the PI homepage dive (stage 6, owner 2026-11-04): fetch every target page incl. reviewed extra-lab-pages.json (live where the host allows, else Wayback), follow their
    # people links, extract students under the standard rules -> labpage-evidence.json
    'homepage-dive': [
        ('fetch', 'school', 'PY $TOOLS/periods_school.py fetch {school}', 'project', 1, '8G', '12:00:00'),
        ('links', 'school', 'PY $TOOLS/labpage_students_school.py links {school}', 'project', 1, '8G', '12:00:00'),
        ('extract', 'school', 'PY $TOOLS/labpage_students_school.py extract {school}', 'project', 2, '16G', '02:00:00'),
    ],
    # the PIs' own CVs (advised-student sections): cv-evidence.json, merged by the next labpage_students extract
    'cv-students': [
        ('cv', 'school', 'PY $TOOLS/cv_students.py {school}', 'project', 1, '8G', '06:00:00'),
        ('extract', 'school', 'PY $TOOLS/labpage_students_school.py extract {school}', 'project', 2, '16G', '02:00:00'),
    ],
    # students other sources name: Wikidata P185 (tools/wikidata_students.py; robots allow only Special:EntityData) -> wikidata-evidence.json, merged by extract
    'wikidata-students': [
        ('wikidata', 'school', 'PY $TOOLS/wikidata_students.py {school} --all', 'project', 1, '4G', '06:00:00'),
        ('extract', 'school', 'PY $TOOLS/labpage_students_school.py extract {school}', 'project', 2, '16G', '02:00:00'),
    ],
    # why each student without a linked paper has none (chain check 4): offline over the school's sweep -> link-diagnosis.json
    'link-diagnosis': [
        ('diagnose', 'school', 'PY $TOOLS/link_diagnosis.py {school}', 'project', 2, '24G', '02:00:00'),
    ],
    # the OpenAlex snapshot extension for a school added after the snapshot was built (stage 0): OA_DATE=<snapshot date> SCHOOLS=<key>.
    # 16 filter tasks -> merge (ext-<key>.sqlite beside the main store). `array:16` = 16 tasks of one school ({task} is the task index).
    'snapshot-ext': [
        ('filter', 'array:16', 'PY $TOOLS/oa_snapshot.py filter {task} 16 --date "${OA_DATE:?set OA_DATE to the snapshot date}" --ext {school}', 'project', 1, '8G', '06:00:00'),
        ('merge', 'once', 'PY $TOOLS/oa_snapshot.py merge --date "${OA_DATE:?set OA_DATE}" --of 16 --ext {schools}', 'project', 1, '16G', '02:00:00'),
    ],
    'reader': [
        ('reader', 'once', 'PY $TOOLS/reader_export.py {schools} --site-local-papers "$CS_ATLAS_SITE/atlas/data/local-papers.json" --site-reader-objects "$CS_ATLAS_SITE/atlas/data/reader-objects.json"', 'project', 2, '40G', '03:00:00'),
    ],
}


def schools_arg(env=None):
    env = os.environ if env is None else env
    return (env.get('SCHOOLS') or env.get('CS_ATLAS_SCHOOLS') or ' '.join(P.SCHOOL_IDS)).split()


def plan(name, schools, stages=None):
    """The sbatch argument lists of a pipeline, in order: [(stage, [args])] (dependencies are added at submit time).
    `stages` replaces the registry's list for an ad-hoc chain (tools/stage_gate.py --run submits a protocol stage's heavy steps so)."""
    if stages is None and name not in PIPELINES:
        raise SystemExit(f'unknown pipeline {name!r}; atlas pipeline --list')
    out = []
    for stage, kind, cmd, py, cpus, mem, tm in (stages if stages is not None else PIPELINES[name]):
        args = [f'--job-name=cs-{name}-{stage}', f'--cpus-per-task={cpus}', f'--mem={mem}', f'--time={tm}',
                f'--output={P.data("logs")}/pipeline-{name}-{stage}-%A' + ('_%a' if kind == 'school' else '') + '.out']
        if kind == 'school':
            args.append(f'--array=0-{len(schools) - 1}')
        elif kind.startswith('array:'):
            args.append(f'--array=0-{int(kind[6:]) - 1}')
        out.append((stage, args, dict(PIPE_STAGE=stage, PIPE_PY=py, SCHOOL_LIST=' '.join(schools), PIPE_KIND=kind), cmd))
    return out


def submit(name, schools, run=subprocess.run, test_only=False, commit=None, stages=None, guard_preempt=False, repo=None):
    """Submit every stage with afterok dependencies; returns {stage: job id}. With test_only only the first stage is checked (a dependency needs a real id).
    guard_preempt: `sbatch --test-only` the first stage first and refuse to submit when it would preempt another job (standing rule).
    repo: a worktree whose HEAD is pinned instead of main's (atlas pipeline --from-worktree)."""
    commit = commit or subprocess.run(['git', '-C', str(repo or P.CODE), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    jobs, prev = {}, None
    steps = plan(name, schools, stages)
    if guard_preempt and not test_only:
        first = steps[0]
        probe = run(['sbatch', '--parsable', '--test-only'] + first[1] + ['--export=ALL', str(CODE / 'hierarchy' / 'pipeline-stage.slurm')],  # route-ok: code that stays in hierarchy/
                    capture_output=True, text=True, env=dict(os.environ, PIPE_CMD=first[3], CS_ATLAS_SNAPSHOT_COMMIT=commit, **first[2], **({'SNAPSHOT_REPO': str(repo)} if repo else {})), cwd=str(CODE))
        if probe.returncode or 'Preempts:' in (probe.stderr or '') + (probe.stdout or ''):
            raise SystemExit(f'not submitted ({first[0]}): ' + ((probe.stderr or probe.stdout or '').strip()[:300] or 'sbatch --test-only failed'))
    for stage, args, env, cmd in steps:
        argv = ['sbatch', '--parsable'] + (['--test-only'] if test_only else []) + args
        if prev:
            argv.append(f'--dependency=afterok:{prev}')
        # the command contains spaces and quotes: everything travels in the environment (--export=ALL), not in a comma list
        e = dict(os.environ, PIPE_CMD=cmd, CS_ATLAS_SNAPSHOT_COMMIT=commit, **env, **({'SNAPSHOT_REPO': str(repo)} if repo else {}))
        argv += ['--export=ALL', str(CODE / 'hierarchy' / 'pipeline-stage.slurm')]  # route-ok: code that stays in hierarchy/
        r = run(argv, capture_output=True, text=True, env=e, cwd=str(CODE))
        if r.returncode:
            raise SystemExit(f'sbatch failed for stage {stage}: {r.stderr.strip()[:300]}')
        if test_only:
            print(f'{stage}: {(r.stderr or r.stdout).strip()}')
            return jobs
        prev = r.stdout.strip().split(';')[0]
        jobs[stage] = prev
    return jobs


def dependency_lines(ids, run=subprocess.run):
    """Each still-queued job's CURRENT dependency, one squeue call (PROTOCOL-FRICTION 18: another session rewired a job's dependency and nothing showed it)."""
    r = run(['squeue', '-h', '-j', ','.join(map(str, ids)), '-o', '%i %T dependency=%E'], capture_output=True, text=True)
    return (r.stdout or '').strip() or '(no queued jobs)'


def main(argv=None, run=subprocess.run):
    args = sys.argv[1:] if argv is None else list(argv)
    if args and args[0] == 'snapshot-refresh':  # the OpenAlex snapshot refresh (ROADMAP #24): its own planner, docs/OPENALEX-SNAPSHOT.md section 14
        import oa_snapshot_refresh
        return oa_snapshot_refresh.main(args[1:] or ['submit'], run=run)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('name', nargs='?'); ap.add_argument('rest', nargs='*')
    ap.add_argument('--list', action='store_true'); ap.add_argument('--test-only', action='store_true'); ap.add_argument('--wait', action='store_true'); ap.add_argument('--from-worktree', action='store_true')
    ap.add_argument('--only', action='append', default=[], help='run only this stage (repeatable), e.g. after a diagnosed failure of one step')
    a = ap.parse_args(argv)
    if a.list or not a.name:
        for n, st in PIPELINES.items():
            print(f"{n:9} " + ' -> '.join(f"{s[0]}{'[per school]' if s[1] == 'school' else ''}" for s in st))
        return 0
    if a.name == 'status':
        d = Path(a.rest[0]) if a.rest else max(Path(P.SCRATCH).glob('pipeline-*'), key=lambda p: p.stat().st_mtime)
        jobs = json.loads((d / 'jobs.json').read_text())['jobs']
        ids = ','.join(jobs.values())
        print(run(['sacct', '-j', ids, '-X', '-n', '-o', 'JobID,JobName,State,Elapsed,ExitCode'], capture_output=True, text=True).stdout)
        print(dependency_lines(list(jobs.values()), run))
        return 0
    env = dict(os.environ)
    for x in a.rest:
        if '=' in x:
            k, v = x.split('=', 1)
            env[k] = v
    schools = schools_arg(env)
    stages = [st for st in PIPELINES.get(a.name, []) if st[0] in a.only] if a.only else None
    if a.only and not stages:
        raise SystemExit(f'--only {a.only}: no such stage in {a.name}; atlas pipeline --list')
    jobs = submit(a.name, schools, run=run, test_only=a.test_only, stages=stages, guard_preempt=True, repo=CODE if a.from_worktree and CODE.resolve() != Path(P.CODE).resolve() else None)
    if a.test_only:
        return 0
    d = Path(P.SCRATCH) / f"pipeline-{a.name}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    d.mkdir(parents=True, exist_ok=True)
    (d / 'jobs.json').write_text(json.dumps(dict(pipeline=a.name, schools=schools, jobs=jobs), indent=1))
    print(f'pipeline {a.name}: ' + ' -> '.join(f'{s} {j}' for s, j in jobs.items()) + f'; run dir {d}')
    if a.wait:
        import slurm_wait
        v, st = slurm_wait.wait(list(jobs.values()), run=run)   # one sacct call per 120 s or more; stops at the first failed job
        print(slurm_wait.table(st))
        print(f'pipeline {a.name}: {v}')
        return 0 if v == 'ok' else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
