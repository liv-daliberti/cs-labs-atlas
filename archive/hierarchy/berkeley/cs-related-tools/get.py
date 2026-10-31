"""usage: get.py URL... : polite fetch of each URL into the store; prints status, length, error."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[3] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import sys
sys.path.insert(0, str(P.HIERARCHY / 'berkeley/cs-related-tools'))
import mpcap
for u in sys.argv[1:]:
    try:
        r = mpcap.fetch(u)
        print(r.get('status'), len(r.get('text') or ''), r.get('error'), u, flush=True)
    except Exception as e:
        print('EXC', repr(e)[:200], u, flush=True)
