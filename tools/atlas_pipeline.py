"""`atlas pipeline <name>`: the mechanical chains as Slurm pipelines with dependencies (ROADMAP #34, 2026-11-01).

An agent used to submit a job, poll it, recount coverage, restamp acceptance files, rebuild the ledger and the copies by hand, one command after another.
A pipeline submits every stage at once, each `--dependency=afterok:` the one before, so nothing is polled and nothing is typed between the stages; the agent
reads the result and judges. A stage is one job, or an array with one task per school.

  atlas pipeline --list
  atlas pipeline copies   [SCHOOLS="a b"] [--test-only] [--wait]   lab_paper_copies per school (array) -> unavailability ledger -> coverage recount -> collectors status
  atlas pipeline labpage  [SCHOOLS="a b"] [--test-only] [--wait]   lab-page audit per school (array) -> restamp the acceptance files -> the audit summary
  atlas pipeline reader   [--test-only] [--wait]                   the reader export (licence -> host or link) after fresh copies
  atlas pipeline status [<run dir>]                                states of a run's jobs (one sacct call)

Each run writes <scratch>/pipeline-<name>-<time>/jobs.json (stage -> job id). Every stage runs from a code snapshot of main's HEAD at submit time
(hierarchy/pipeline-stage.slurm). The commands live in PIPELINES below: a new chain is a new entry, not a new script. The judgement steps (the hand checks of
the lab-page rounds, the diagnosis of a failed stage) are not here and never will be.
"""
import argparse, datetime, json, os, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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
    'reader': [
        ('reader', 'once', 'PY $TOOLS/reader_export.py {schools} --site-local-papers "$CS_ATLAS_SITE/atlas/data/local-papers.json"', 'project', 2, '40G', '03:00:00'),
    ],
}


def schools_arg(env=None):
    env = os.environ if env is None else env
    return (env.get('SCHOOLS') or env.get('CS_ATLAS_SCHOOLS') or ' '.join(P.SCHOOL_IDS)).split()


def plan(name, schools):
    """The sbatch argument lists of a pipeline, in order: [(stage, [args])] (dependencies are added at submit time)."""
    if name not in PIPELINES:
        raise SystemExit(f'unknown pipeline {name!r}; atlas pipeline --list')
    out = []
    for stage, kind, cmd, py, cpus, mem, tm in PIPELINES[name]:
        args = [f'--job-name=cs-{name}-{stage}', f'--cpus-per-task={cpus}', f'--mem={mem}', f'--time={tm}',
                f'--output={CODE}/hierarchy/logs/pipeline-{name}-{stage}-%A' + ('_%a' if kind == 'school' else '') + '.out']
        if kind == 'school':
            args.append(f'--array=0-{len(schools) - 1}')
        out.append((stage, args, dict(PIPE_STAGE=stage, PIPE_PY=py, SCHOOL_LIST=' '.join(schools)), cmd))
    return out


def submit(name, schools, run=subprocess.run, test_only=False, commit=None):
    """Submit every stage with afterok dependencies; returns {stage: job id}. With test_only only the first stage is checked (a dependency needs a real id)."""
    commit = commit or subprocess.run(['git', '-C', str(P.CODE), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    jobs, prev = {}, None
    for stage, args, env, cmd in plan(name, schools):
        argv = ['sbatch', '--parsable'] + (['--test-only'] if test_only else []) + args
        if prev:
            argv.append(f'--dependency=afterok:{prev}')
        # the command contains spaces and quotes: everything travels in the environment (--export=ALL), not in a comma list
        e = dict(os.environ, PIPE_CMD=cmd, CS_ATLAS_SNAPSHOT_COMMIT=commit, **env)
        argv += ['--export=ALL', str(CODE / 'hierarchy' / 'pipeline-stage.slurm')]
        r = run(argv, capture_output=True, text=True, env=e, cwd=str(CODE))
        if r.returncode:
            raise SystemExit(f'sbatch failed for stage {stage}: {r.stderr.strip()[:300]}')
        if test_only:
            print(f'{stage}: {(r.stderr or r.stdout).strip()}')
            return jobs
        prev = r.stdout.strip().split(';')[0]
        jobs[stage] = prev
    return jobs


def main(argv=None, run=subprocess.run):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('name', nargs='?'); ap.add_argument('rest', nargs='*')
    ap.add_argument('--list', action='store_true'); ap.add_argument('--test-only', action='store_true'); ap.add_argument('--wait', action='store_true')
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
        return 0
    env = dict(os.environ)
    for x in a.rest:
        if '=' in x:
            k, v = x.split('=', 1)
            env[k] = v
    schools = schools_arg(env)
    jobs = submit(a.name, schools, run=run, test_only=a.test_only)
    if a.test_only:
        return 0
    d = Path(P.SCRATCH) / f"pipeline-{a.name}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    d.mkdir(parents=True, exist_ok=True)
    (d / 'jobs.json').write_text(json.dumps(dict(pipeline=a.name, schools=schools, jobs=jobs), indent=1))
    print(f'pipeline {a.name}: ' + ' -> '.join(f'{s} {j}' for s, j in jobs.items()) + f'; run dir {d}')
    if a.wait:
        last = list(jobs.values())[-1]
        run(['scontrol', 'wait_job', last])   # one blocking call, no polling
        print(run(['sacct', '-j', ','.join(jobs.values()), '-X', '-n', '-o', 'JobID,JobName,State,Elapsed,ExitCode'], capture_output=True, text=True).stdout)
    return 0


if __name__ == '__main__':
    sys.exit(main())
