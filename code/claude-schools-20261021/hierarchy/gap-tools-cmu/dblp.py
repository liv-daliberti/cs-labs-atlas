"""DBLP helper: author search API and pid XML (one request per 5 s; never sparql).

usage: dblp.py search "<name>" ["<name>" ...]
       dblp.py pid 12/345 [--from 2016]
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import quote

sys.path.insert(0, "/n/fs/resemble/cs-atlas/work/hierarchy/gap-tools-cmu")
import capstore  # noqa: E402

cmd = sys.argv[1]
if cmd == "search":
    for name in sys.argv[2:]:
        u = "https://dblp.org/search/author/api?q=" + quote(name) + "&format=json&h=30"
        r = capstore.fetch(u, check_robots=False)
        print("##", name, r.get("status"), (r.get("sha256") or "")[:16], r.get("error"))
        try:
            j = json.loads(r["content"])
            hits = (j.get("result", {}).get("hits", {}) or {}).get("hit", []) or []
            for h in hits:
                info = h.get("info", {})
                notes = info.get("notes", {}).get("note") if info.get("notes") else None
                print("   ", info.get("author"), "|", info.get("url"), "|", json.dumps(notes)[:200])
        except Exception as e:
            print("   parse error", e, r.get("content", b"")[:200])
elif cmd == "pid":
    pid = sys.argv[2]
    frm = int(sys.argv[4]) if len(sys.argv) > 4 else 2016
    u = f"https://dblp.org/pid/{pid}.xml"
    r = capstore.fetch(u, check_robots=False)
    print("##", pid, r.get("status"), r.get("sha256"), r.get("final_url"), r.get("error"))
    try:
        root = ET.fromstring(r["content"])
        print("name:", root.get("name"), "n:", root.get("n"))
        person = root.find("person")
        if person is not None:
            for ch in person:
                print("  person.", ch.tag, ch.attrib, (ch.text or "")[:120])
        cnt = 0
        for rec in root.findall("r"):
            pub = list(rec)[0]
            y = int(pub.findtext("year") or 0)
            if y >= frm:
                cnt += 1
                if cnt <= 12:
                    print("  ", y, (pub.findtext("title") or "")[:100], "|", [e.text for e in pub.findall("ee")][:1])
        print("  works >=", frm, ":", cnt)
    except Exception as e:
        print("  parse error", e, r.get("content", b"")[:300])
