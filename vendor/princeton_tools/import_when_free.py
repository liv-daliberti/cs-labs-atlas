# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015/tools/import_when_free.py (sha256 b9c8c3b90de9d68f7bd2f8ffefa5578e11da05a6bc28dc917613554846bcd3ff); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Import staged packages into the full-text catalog at the first safe moment.

Safe = the supervisor (possibly on another host) reports a non-collecting phase or a stopped
status, AND .collector.lock can be taken without blocking. Checks once a minute; imports each
package once (receipts in import_when_free.log); exits when all are imported.
Usage: python tools/import_when_free.py cs_pi_works [more tool modules with import_catalog()]
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import fcntl, importlib, json, sys, time
from datetime import datetime, timezone
from pathlib import Path

STAGE = P.SWEEPS / 'claude-princeton-20261015'  # vendored: the data root (was Path(__file__).resolve().parents[1])
FULLTEXT = P.STORES / 'princeton'
SAFE_PHASES = {'verifying', 'exporting_atlas', 'exporting_focus', 'exporting_cs', 'exporting_page2', 'complete'}
SAFE_STATUS = {'interrupted', 'failed', 'collection_pass_complete'}
sys.path.insert(0, str(Path(__file__).resolve().parent))


def log(**kw):
    with open(STAGE / 'import_when_free.log', 'a') as f:
        f.write(json.dumps(dict(at=datetime.now(timezone.utc).isoformat(), **kw)) + '\n')


def main(modules):
    pending = list(modules)
    while pending:
        try:
            state = json.loads((FULLTEXT / 'run-state.json').read_text())
        except Exception:
            state = {}
        safe = state.get('phase') in SAFE_PHASES or state.get('status') in SAFE_STATUS
        if safe:
            with (FULLTEXT / '.collector.lock').open('a') as probe:
                try:
                    fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(probe, fcntl.LOCK_UN)
                    free = True
                except BlockingIOError:
                    free = False
            if free:
                for name in list(pending):
                    try:
                        importlib.import_module(name).import_catalog()
                        log(imported=name, phase=state.get('phase'), status=state.get('status'))
                        pending.remove(name)
                    except BlockingIOError:
                        log(retry=name, reason='lock taken during import attempt'); break
                    except Exception as e:
                        log(error=name, detail=str(e)[:300]); pending.remove(name)
        time.sleep(60)
    log(done=True)


if __name__ == '__main__':
    main(sys.argv[1:])
