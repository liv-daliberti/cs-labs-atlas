"""One school's OpenAlex institution sweep and its sanity check, for any charter school (protocol stages 0, 2 and 7;
ROADMAP item 5). Runs tools/oa_sweep.py <key> (resumable; the charter's lineage and related ids) and then
tools/sweep_check.py <key>, appending both to hierarchy/sweep-<key>.log with start/done lines. --daily repeats the pair
after each OpenAlex credit reset (00:00 UTC + 10 min) until the log shows the current year stored.

Replaces the one-school runners hierarchy/michigan/run_sweep.sh, hierarchy/michigan/sweep_daily.sh and
hierarchy/run_stanford_sweep.sh (archive/, docs/SCRIPT-MAP.md). The OpenAlex key is read from
~/.config/cs-atlas/openalex.env into the children's environment and never printed. The shared key has 10k credits a day:
check what is left before a long sweep.

usage: sweep_school.py <key> [--daily] [--floor N] [--print]      (--print: show the commands, run nothing)
"""
import argparse
import datetime
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
import school_config  # noqa: E402

TOOLS = Path(__file__).resolve().parent
KEY_FILE = Path.home() / '.config' / 'cs-atlas' / 'openalex.env'


def env_file(p):
    """KEY=VALUE lines of a shell env file (optional `export`, optional quotes), as a dict; values are never printed."""
    out = {}
    if Path(p).exists():
        for line in Path(p).read_text().splitlines():
            m = re.match(r'\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
            if m and not line.lstrip().startswith('#'):
                out[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return out


def commands(key):
    """The two steps, as (argv, extra env)."""
    return [(['nice', '-n', '10', str(P.PY), '-I', '-u', str(TOOLS / 'oa_sweep.py'), key], {}),
            (['nice', '-n', '10', str(P.PY), '-u', str(TOOLS / 'sweep_check.py'), key], {})]


def complete(log, year=None):
    """The sweep log shows the last year of the window stored (oa_sweep prints one '"year": Y, "works"' line per year)."""
    year = year or datetime.date.today().year
    return Path(log).exists() and f'"year": {year}, "works"' in Path(log).read_text(errors='replace')


def run_once(key, log, floor, show=False):
    env = dict(os.environ, **env_file(KEY_FILE), OPENALEX_FLOOR=str(floor))
    stamp = lambda: datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    rc = 0
    for i, (argv, extra) in enumerate(commands(key)):
        if show:
            print(' '.join(argv)); continue
        with open(log, 'a') as f:
            f.write(f"### {'start' if i == 0 else 'sweep-check'} {stamp()}\n"); f.flush()
            rc_ = subprocess.call(argv, stdout=f, stderr=subprocess.STDOUT, env=dict(env, **extra), cwd=str(P.CODE))
            f.write(f"### {'done' if i == 0 else 'sweep-check'} {stamp()} rc={rc_}\n")
        rc = rc or rc_
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('key')
    ap.add_argument('--daily', action='store_true', help='repeat after each 00:00 UTC credit reset until the window is stored')
    ap.add_argument('--floor', type=int, default=1500, help='OPENALEX_FLOOR: stop when the key has this many credits left')
    ap.add_argument('--print', dest='show', action='store_true', help='print the commands and exit')
    a = ap.parse_args(argv)
    if a.key not in school_config.keys():
        raise SystemExit(f'no charter schools/{a.key}.toml')
    log = P.HIERARCHY / f'sweep-{a.key}.log'
    if a.show or not a.daily:
        return run_once(a.key, log, a.floor, a.show)
    tmp = P.HIERARCHY / a.key / 'tmp'
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / 'sweep_daily.pid').write_text(str(os.getpid()))
    while not complete(log):
        now = time.time()
        time.sleep((now // 86400 + 1) * 86400 + 600 - now)
        run_once(a.key, log, a.floor)
    with open(log, 'a') as f:
        f.write(f'### complete {datetime.datetime.now().astimezone().isoformat(timespec="seconds")}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
