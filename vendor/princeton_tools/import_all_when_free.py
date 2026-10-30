# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015/tools/import_all_when_free.py (sha256 7ab7047a8e45ca07edd7bb31d53300da9e7c7b80d7ef6eb03f38835fa041b0c1); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Import every staged Princeton CS package into the full-text catalog, in dependency order, at the first
safe moment (supervisor in a non-collecting phase or stopped, and .collector.lock free). Polls every 10 s so
a short export window is not missed; one process, so the imports do not compete for the lock. Packages already
imported (catalog receipt) are skipped; a package that is not built yet is waited for.
Log: import_when_free.log.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import fcntl, importlib, json, sqlite3, sys, time
from datetime import datetime, timezone
from pathlib import Path

STAGE = P.SWEEPS / 'claude-princeton-20261015'  # vendored: the data root (was Path(__file__).resolve().parents[1])
FULLTEXT = P.STORES / 'princeton'
DISC = FULLTEXT / 'discovery'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from import_when_free import SAFE_PHASES, log
SAFE_STATUS = {'interrupted', 'collection_pass_complete'}  # not 'failed': a crashed collector may leave a hot journal

STEPS = [  # (module, package directory)
    ('cs_pi_works', 'claude-cs-pi-works-20261015'),
    ('cs_complete', 'claude-cs-complete-20261016'),
    ('cs_open_copies', 'claude-cs-open-copies-20261016'),
    ('cs_structure_catalog', 'claude-cs-structure-20261016'),
    ('cs_open_copies', 'claude-cs-open-copies-dblparxiv-20261016'),
    ('cs_open_copies', 'claude-cs-open-copies-venues-20261016'),
    ('cs_open_copies', 'claude-cs-open-copies-structure-20261016'),
]


def imported(package):
    db = sqlite3.connect(f'file:{FULLTEXT}/catalog.sqlite?mode=ro', uri=True, timeout=120)
    return db.execute('SELECT 1 FROM receipts WHERE key=?', ('discovery:' + str(DISC / package),)).fetchone() is not None


def run(module, package):
    """Import in a child process: any connection or lock dies with it (a leaked lock once blocked the catalog
    for 12 hours). BlockingIOError in the child means retry later."""
    import subprocess
    code = (f"import sys; sys.path.insert(0, {str(Path(__file__).resolve().parent)!r}); import {module} as m; from pathlib import Path; "
            f"m.PACKAGE = Path({str(DISC / package)!r}) if hasattr(m, 'PACKAGE') else None; "
            + ("m.EVID = m.PACKAGE / 'evidence'; " if module == 'cs_open_copies' else '') + "m.import_catalog()")
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        if 'BlockingIOError' in r.stderr or 'database is locked' in r.stderr:
            raise BlockingIOError(r.stderr.strip().splitlines()[-1][:200])
        raise RuntimeError(r.stderr.strip()[-300:])


def main():
    steps = [tuple(a.split(':')) if ':' in a else ('cs_open_copies', a) for a in sys.argv[1:]] or STEPS  # [module:]package on the command line
    pending = [s for s in steps if not imported(s[1])]
    deadline = time.time() + 36 * 3600
    while pending and time.time() < deadline:
        try:
            state = json.loads((FULLTEXT / 'run-state.json').read_text())
        except Exception:
            state = {}
        if state.get('phase') in SAFE_PHASES or state.get('status') in SAFE_STATUS:
            for module, package in list(pending):
                if not (DISC / package / 'summary.json').exists():
                    break  # not built yet: later packages depend on the order
                try:
                    run(module, package)
                    log(imported=package, phase=state.get('phase'), status=state.get('status'))
                    pending.remove((module, package))
                except BlockingIOError as e:
                    log(retry=package, reason=str(e)[:200]); break
                except Exception as e:
                    log(error=package, detail=str(e)[:300]); pending.remove((module, package))
        time.sleep(10)
    log(all_done=not pending, still_pending=[p for _, p in pending])


if __name__ == '__main__':
    main()
