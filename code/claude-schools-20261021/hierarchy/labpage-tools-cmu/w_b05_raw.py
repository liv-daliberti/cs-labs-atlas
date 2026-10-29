"""b05 helper: print src/href/data-file references from a stored capture's raw HTML (no fetching)."""
import re
import sys
sys.path.insert(0, "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/labpage-tools-cmu")
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
