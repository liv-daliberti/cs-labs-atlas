"""Edit decisions.json: setdec.py PI URL[@mode] [URL...] | setdec.py PI --none REASON | setdec.py PI --notes TEXT"""
import json
import os
import sys
import tempfile

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), "decisions.json")
d = json.load(open(P)) if os.path.exists(P) else {}
a = sys.argv[1:]
pi = a[0]
if a[1] == "--none":
    d[pi] = {"none": a[2]}
elif a[1] == "--notes":
    d.setdefault(pi, {})["notes"] = a[2]
elif a[1] == "--del":
    d.pop(pi, None)
else:
    pages = []
    for x in a[1:]:
        if x.startswith("{"):
            pages.append(json.loads(x))
        elif "@" in x.rsplit("/", 1)[-1]:
            u, m = x.rsplit("@", 1)
            pages.append({"url": u, "mode": m})
        else:
            pages.append({"url": x, "mode": "auto"})
    old = d.get(pi, {})
    d[pi] = {"pages": pages, **({"notes": old["notes"]} if old.get("notes") else {})}
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(P))
with os.fdopen(fd, "w") as f:
    json.dump(d, f, ensure_ascii=False, indent=1, sort_keys=True)
os.chmod(tmp, 0o644)
os.replace(tmp, P)
print(pi, json.dumps(d.get(pi))[:300])
