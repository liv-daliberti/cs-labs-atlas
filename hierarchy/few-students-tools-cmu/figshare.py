"""Search CMU KiltHub (figshare institution) theses: figshare.py "<query>" [--n 50]
Prints article id, title, published date, url. Then fetch article JSON with f.py https://api.figshare.com/v2/articles/<id>.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json, sys
sys.path.insert(0, str(P.HIERARCHY / 'few-students-tools-cmu'))
import capstore
q = sys.argv[1]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 50
r = capstore.post_json("https://api.figshare.com/v2/articles/search", {"search_for": q, "page_size": n})
print("status", r.get("status"), (r.get("sha256") or "")[:16], r.get("error"))
try:
    for a in json.loads(r["content"]):
        print(a.get("id"), "|", a.get("published_date", "")[:10], "|", (a.get("title") or "")[:100], "|", a.get("url_public_html"))
except Exception as e:
    print("parse error", e, r.get("content", b"")[:300])
