"""atlas <command>: one entry point over the existing tools (a thin dispatcher; every command runs a script that also
works on its own). Run it from the env (`atlas ...` once the repo is installed into env/atlas, see docs/ENVIRONMENT.md)
or from any checkout with bin/atlas, which runs that checkout's tools.

Python tools run on the interpreter running atlas (env/atlas); the download loop runs on COLLECTOR_PY (atlas_paths).
Paths come from tools/atlas_paths.py as usual (CS_ATLAS_* overrides pass through). `atlas help` lists the commands.
"""
import os
import shlex
import subprocess
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]   # the checkout this dispatcher belongs to

# name: (kind, target, summary). kind: py = a Python script under CODE, sh = a shell script, each = run a py script once
# per school argument, special = handled below.
COMMANDS = {
    'build':      ('each', 'tools/pi_hierarchy.py', 'build packages: atlas build <school> [...]'),
    'rebuild':    ('sh', 'hierarchy/rebuild.sh', 'the full rebuild (STAGES=..., SCHOOLS=... in the environment)'),
    'ids':        ('py', 'tools/atlas_ids.py', 'stable atlas ids into the packages'),
    'copies':     ('py', 'tools/lab_paper_copies.py', 'copies.json from the stores: atlas copies <school> [...]'),
    'ledger':     ('py', 'fulltext-push/unavailable_ledger.py', 'the unavailability ledger: atlas ledger <school> [...]'),
    'audit':      ('py', 'tools/chain_audit.py', 'the chain audit'),
    'evidence':   ('py', 'tools/evidence_check.py', 'the build-time evidence check'),
    'validate':   ('py', 'tools/validate.py', 'data files against schemas/: atlas validate [school ...] [--shared --reviewed --tree --export]'),
    'regression': ('py', 'tools/build_regression.py', 'build regression: snapshot | check --before <counts.json>'),
    'release':    ('py', 'tools/make_release.py', 'cut a release (refuses on uncommitted code or failed stages)'),
    'tree':       ('py', 'tools/organize_tree.py', 'the organized school/lab/paper tree from a release'),
    'export':     ('py', 'tools/export_release.py', 'the GitHub export: atlas export <repo dir> [--skip-atlas]'),
    'sweep':      ('py', 'tools/sweep_school.py', 'a school\'s OpenAlex sweep + sweep check: atlas sweep <school> [--daily] [--print]'),
    'stage-gate': ('py', 'tools/stage_gate.py', 'a protocol school\'s stage gates: atlas stage-gate <school> [stage ...]'),
    'charters':   ('py', 'tools/school_config.py --check', 'validate every school charter (schools/*.toml)'),
    'collect':    ('special', 'fulltext-push/lab_first_loop.py', 'the lab-first download loop: atlas collect <school> [...]'),
    'test':       ('special', 'pytest', 'the test suite: atlas test [pytest args]; --ci skips tests needing NFS data'),
    'lint':       ('special', 'ruff', 'ruff check (pyproject.toml config): atlas lint [--fix]'),
    'scan':       ('py', 'tools/secret_scan.py', 'secret scan: atlas scan --staged | atlas scan <paths>'),
    'vendor':     ('py', 'tools/vendor_sync.py', 'vendored code: atlas vendor check|sync|list'),
    'paths':      ('py', 'tools/atlas_paths.py', 'every path, or one: atlas paths [NAME]'),
    'relocate':   ('py', 'tools/relocate_project.py', 'the project move (dry run by default)'),
    'submit':     ('special', 'sbatch', 'sbatch with the code pinned: atlas submit [sbatch options] script.slurm (CS_ATLAS_SNAPSHOT_COMMIT = main\'s HEAD now)'),
    'run':        ('special', '', 'any script of this checkout on the project interpreter: atlas run tools/x.py [...]'),
}


def _paths():
    sys.path.insert(0, str(CODE / 'tools'))
    import atlas_paths
    return atlas_paths


def _usage():
    w = max(map(len, COMMANDS))
    lines = ['usage: atlas <command> [args]', '']
    lines += [f'  {k:<{w}}  {v[2]}' for k, v in COMMANDS.items()]
    lines += ['', f'checkout: {CODE}', f'python:   {sys.executable}']
    return '\n'.join(lines)


def _run(argv, cwd=CODE):
    print('+ ' + ' '.join(shlex.quote(str(a)) for a in argv), file=sys.stderr, flush=True)
    return subprocess.call([str(a) for a in argv], cwd=str(cwd))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ('-h', '--help', 'help'):
        print(_usage())
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd not in COMMANDS:
        print(f'atlas: unknown command {cmd!r}\n\n{_usage()}', file=sys.stderr)
        return 2
    kind, target, _ = COMMANDS[cmd]
    py = sys.executable
    if kind == 'py':
        script, *fixed = target.split()
        if not (CODE / script).exists():
            print(f'atlas: {script} is not in this checkout ({CODE})', file=sys.stderr)
            return 2
        return _run([py, '-u', CODE / script, *fixed, *args])
    if kind == 'each':
        if not args:
            print(f'atlas {cmd}: name at least one school', file=sys.stderr)
            return 2
        rc = 0
        for school in args:
            rc = _run([py, '-u', CODE / target, school]) or rc
        return rc
    if kind == 'sh':
        return _run(['bash', CODE / target, *args])
    if cmd == 'submit':  # the job runs the code of THIS commit, whatever lands before it starts (tools/job_code_snapshot.sh)
        r = subprocess.run(['git', '-C', str(_paths().CODE), 'rev-parse', 'HEAD'], capture_output=True, text=True)
        if r.returncode:
            print('atlas submit: cannot read HEAD of ' + str(_paths().CODE), file=sys.stderr)
            return 1
        return _run(['sbatch', f'--export=ALL,CS_ATLAS_SNAPSHOT_COMMIT={r.stdout.strip()}', *args], cwd=os.getcwd())
    if cmd == 'test':
        env_ci = '--ci' in args
        args = [a for a in args if a != '--ci']
        if env_ci:
            os.environ['CS_ATLAS_CI'] = '1'
            args = ['-m', 'not nfs', *args]
        return _run([py, '-m', 'pytest', *args])
    if cmd == 'lint':
        ruff = Path(py).with_name('ruff')
        return _run([ruff if ruff.exists() else 'ruff', 'check', '.', *args])
    if cmd == 'collect':
        if not args:
            print('atlas collect: name a school', file=sys.stderr)
            return 2
        P = _paths()
        # the loop takes <store>/.loop.lock itself: a second copy (or the rinse loop) makes it exit at once
        return _run([P.COLLECTOR_PY, '-I', '-u', CODE / target, *args], cwd=CODE / 'fulltext-push')
    if cmd == 'run':
        if not args:
            print('atlas run: name a script', file=sys.stderr)
            return 2
        return _run([py, '-u', CODE / args[0], *args[1:]])
    return 2


if __name__ == '__main__':
    sys.exit(main())
