"""Worker A helper: search KiltHub theses for a name (item_type 8) and/or fetch article JSONs; print
author / date / department / degree / advisors for each thesis.

usage: a_kilthub.py [--search "QUERY"] [ID ...]
"""
import json
import sys

sys.path.insert(0, "/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/few-students-tools-cmu")
import capstore  # noqa: E402

FS = "https://api.figshare.com/v2/articles/"
args = sys.argv[1:]
ids = []
if "--search" in args:
    i = args.index("--search")
    q = args[i + 1]
    del args[i:i + 2]
    r = capstore.post_json("https://api.figshare.com/v2/articles/search", {"search_for": q, "page_size": 100, "item_type": 8})
    try:
        for a in json.loads(r["content"]):
            if "kilthub" in (a.get("url_public_html") or ""):
                ids.append(str(a["id"]))
    except Exception as e:
        print("search parse error", e)
ids += args
for i in ids:
    r = capstore.fetch(FS + i)
    if r.get("status") != 200:
        print(i, "status", r.get("status"))
        continue
    d = json.loads(r["content"])
    cf = {c["name"]: c["value"] for c in d.get("custom_fields", [])}
    print(i, "|", ", ".join(a["full_name"] for a in d.get("authors", [])), "|", cf.get("Date"), "|",
          cf.get("Thesis Department"), "|", cf.get("Degree Name"), "| ADV:", cf.get("Advisor(s)"), "|", d.get("title", "")[:70])
