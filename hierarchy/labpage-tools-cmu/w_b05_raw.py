"""b05 helper: print src/href/data-file references from a stored capture's raw HTML (no fetching)."""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import re
import sys
sys.path.insert(0, str(P.HIERARCHY / 'labpage-tools-cmu'))
import capstore  # noqa: E402

url = sys.argv[1]
rx = sys.argv[2] if len(sys.argv) > 2 else r"(src|href)=[\"'][^\"']+"
r = capstore.cached(url)
if not r or not r.get("content"):
    print("not cached")
    sys.exit()
t = capstore._decode(r["content"])
print("len", len(t))
for m in re.finditer(rx, t, flags=re.I):
    print(" ", m.group(0)[:200])
