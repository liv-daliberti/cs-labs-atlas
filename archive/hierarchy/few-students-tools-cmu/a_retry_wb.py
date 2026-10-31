"""Worker A: fetch a few Wayback captures with polite backoff (the archive is refusing connections intermittently).

usage: a_retry_wb.py URL...   (tries each URL up to 5 times, waiting 120 s after a refused connection)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import sys
import time

sys.path.insert(0, str(P.HIERARCHY / 'few-students-tools-cmu'))
import capstore  # noqa: E402

for u in sys.argv[1:]:
    for attempt in range(5):
        r = capstore.fetch(u)
        if r.get("status") is not None:
            break
        print("refused, backing off:", u, flush=True)
        time.sleep(120)
    print("==", u, r.get("status"), flush=True)
    if r.get("status") == 200:
        print(capstore.page_text(r["content"])[:2500], flush=True)
