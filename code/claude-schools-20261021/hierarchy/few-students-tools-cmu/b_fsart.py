"""Fetch figshare article JSON(s) and print author, date, degree, department, advisors. usage: b_fsart.py ID..."""
import json, sys
sys.path.insert(0, "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/few-students-tools-cmu")
import capstore
for i in sys.argv[1:]:
    r = capstore.fetch("https://api.figshare.com/v2/articles/" + i)
    try:
        d = json.loads(r["content"])
    except Exception as e:
        print(i, "ERR", r.get("status"), e); continue
    cf = {c["name"]: c["value"] for c in d.get("custom_fields", [])}
    print(i, "|", [a["full_name"] for a in d.get("authors", [])], "|", cf.get("Date"), "|", cf.get("Degree Type"), "|",
          cf.get("Thesis Department"), "|", "ADV:", cf.get("Advisor(s)"), "|", d.get("title", "")[:70], "| inst", d.get("institution_id") if "institution_id" in d else "")
