"""KiltHub thesis search via the figshare API (item_type 8 = thesis). usage: b_fs.py "<query>" [n]"""
import json, sys
sys.path.insert(0, "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/few-students-tools-cmu")
import capstore
q = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
r = capstore.post_json("https://api.figshare.com/v2/articles/search", {"search_for": q, "page_size": n, "item_type": 8})
print("##", q, "status", r.get("status"), r.get("error"))
try:
    for a in json.loads(r["content"]):
        print(" ", a.get("id"), "|", (a.get("published_date") or "")[:10], "|", (a.get("title") or "")[:90])
except Exception as e:
    print("parse error", e)
