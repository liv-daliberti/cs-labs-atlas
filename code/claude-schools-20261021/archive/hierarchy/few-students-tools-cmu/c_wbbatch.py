"""Worker C: run a list of Wayback lookups sequentially with back-off; append results to an output file.

usage: c_wbbatch.py OUTFILE LINE...   where LINE is "cdx <url> [prefix] [from=YYYY]" or "get <wayback id_ url> [grep=RX]"
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import re
import sys

sys.path.insert(0, str(P.HIERARCHY / 'few-students-tools-cmu'))
import capstore  # noqa: E402
import c_wb  # noqa: E402

out = open(sys.argv[1], "a")
for line in sys.argv[2:]:
    parts = line.split()
    kw = dict(p.split("=", 1) for p in parts[2:] if "=" in p)
    out.write(f"#### {line}\n")
    if parts[0] == "cdx":
        rows = c_wb.cdx(parts[1], "prefix" in parts, kw.get("from"))
        for ts, o in rows:
            if not re.search(r"\.(jpg|jpeg|png|gif|css|js|ico|woff2?|xml|txt)(\?|$)", o, re.I):
                out.write(f"{ts} {o}\n")
        out.write(f"{len(rows)} captures\n")
    else:
        r = c_wb.fetch_retry(parts[1])
        out.write(str({k: r.get(k) for k in ("url", "capture_url", "status", "sha256", "error")}) + "\n")
        if r.get("content"):
            t = capstore.page_text(r["content"])
            if "grep" in kw:
                for m in list(re.finditer(kw["grep"], t, re.I))[:6]:
                    out.write("  >> " + t[max(0, m.start() - 300):m.end() + 1500] + "\n")
            else:
                out.write(t[:6000] + "\n")
    out.flush()
out.write("DONE\n")
