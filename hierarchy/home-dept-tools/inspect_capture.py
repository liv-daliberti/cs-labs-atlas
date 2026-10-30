"""Print windows of the whitespace-collapsed text of the latest 200 capture of URL around REGEX.
usage: inspect_capture.py URL REGEX [WIDTH]
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import re, sys, zlib
sys.path.insert(0, str(P.HIERARCHY / 'home-dept-tools'))
import capstore
url, rx = sys.argv[1], sys.argv[2]
w = int(sys.argv[3]) if len(sys.argv) > 3 else 300
con = capstore.connect()
row = con.execute("SELECT content, sha256 FROM captures WHERE (url=? OR final_url=?) AND content IS NOT NULL ORDER BY (status=200) DESC, id DESC LIMIT 1", (url, url)).fetchone()
if not row:
    print("NO CAPTURE", url); sys.exit()
t = capstore.page_text(zlib.decompress(row[0]))
print("##", url, row[1][:12], "len", len(t))
n = 0
for m in re.finditer(rx, t, flags=re.I):
    print("  >>", t[max(0, m.start() - w):m.end() + w])
    n += 1
    if n >= 6: break
if n == 0:
    print("  (no match) head:", t[:w*2])
