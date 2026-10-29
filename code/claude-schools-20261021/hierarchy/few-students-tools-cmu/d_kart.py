"""Fetch KiltHub article JSONs by id and print author, date, department, degree, Advisor(s), title.

usage: d_kart.py ID [ID ...]
"""
import json
import sys

sys.path.insert(0, "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/few-students-tools-cmu")
import capstore  # noqa: E402

for i in sys.argv[1:]:
    rr = capstore.fetch("https://api.figshare.com/v2/articles/%s" % i)
    try:
        d = json.loads(rr["content"])
    except Exception:
        print(i, "fetch failed", rr.get("status"))
        continue
    cf = {c["name"]: c.get("value") for c in d.get("custom_fields", [])}
    authors = ", ".join(x.get("full_name", "") for x in d.get("authors", []))
    print(i, cf.get("Date"), "|", authors, "|", cf.get("Thesis Department"), "|", cf.get("Degree Type"), "| Advisor(s):",
          cf.get("Advisor(s)"), "|", (d.get("title") or "")[:90], flush=True)
