"""Wait for Slurm jobs without polling the controller (ROADMAP #35).

The controller rate-limits every user's RPCs (docs/CONTRIBUTING.md; /etc/claude-code/CLAUDE.md): a status loop gets rejected. Jobs chain by
`--dependency=afterok:` and by their output files; when a command has to block until a chain ends (`atlas pipeline --wait`, `atlas release --wait`)
it does it here: ONE `sacct -j <ids> -X` call, then a sleep of at least 120 s, repeated until every job has ended or one of them failed (a job that
failed leaves its afterok dependants pending forever, so there is nothing left to wait for). An `sacct` error backs the interval off (x2, to 15 min)
instead of retrying faster. `scontrol wait_job` is not used: it polls the controller every few seconds itself.
"""
import subprocess
import sys
import time

MIN_INTERVAL = 120
MAX_BACKOFF = 900
ENDED_OK = {'COMPLETED'}
ENDED_BAD = {'FAILED', 'CANCELLED', 'TIMEOUT', 'OUT_OF_MEMORY', 'NODE_FAIL', 'PREEMPTED', 'BOOT_FAIL', 'DEADLINE'}


def states(ids, run=subprocess.run):
    """{job id: (name, state, exit code)} from one sacct call (array tasks appear as <id>_<n>); raises OSError when sacct fails."""
    r = run(['sacct', '-j', ','.join(map(str, ids)), '-X', '-n', '-P', '-o', 'JobID,JobName,State,ExitCode'], capture_output=True, text=True)
    if r.returncode:
        raise OSError((r.stderr or 'sacct failed').strip()[:200])
    out = {}
    for line in (r.stdout or '').splitlines():
        f = line.split('|')
        if len(f) >= 4:
            out[f[0]] = (f[1], f[2].split()[0], f[3])   # 'CANCELLED by 123' -> CANCELLED
    return out


def verdict(st, ids):
    """'running' | 'ok' | 'failed' from a states() result. A job missing from the accounting yet (just submitted) is still running."""
    if any(s in ENDED_BAD for _, s, _ in st.values()):
        return 'failed'
    if all(any(k == str(i) or k.startswith(f'{i}_') for k in st) for i in ids) and all(s in ENDED_OK for _, s, _ in st.values()):
        return 'ok'
    return 'running'


def wait(ids, interval=MIN_INTERVAL, run=subprocess.run, sleep=time.sleep, out=sys.stdout):
    """Block until the jobs have ended. -> (verdict, states). The interval is never below MIN_INTERVAL."""
    ids = [str(i) for i in ids]
    gap = max(int(interval), MIN_INTERVAL)
    cur = gap
    while True:
        try:
            st = states(ids, run=run)
            cur = gap
        except OSError as e:
            print(f'slurm_wait: {e}; backing off', file=out, flush=True)
            cur = min(cur * 2, MAX_BACKOFF)
            sleep(cur)
            continue
        v = verdict(st, ids)
        if v != 'running':
            return v, st
        sleep(cur)


def table(st):
    return '\n'.join(f'{k:>14} {n:<24} {s:<14} {e}' for k, (n, s, e) in sorted(st.items()))
