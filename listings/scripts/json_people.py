"""JSON listing endpoints -> text blocks (deterministic, used by extract.blocks and verify.py).

Used for script-rendered listings whose data endpoint Wayback captured, e.g. the 2016-2017 MIT CSAIL
PI list (www.csail.mit.edu/biographies/PI/biolist.php is an Exhibit page fed by
/csaildirectoryoutput/pi, JSON {"items": [{"label": name, "position": title, ...}]}).
Each person record becomes one block with the display name, then one block per title-like field.
The CMU SCS directory API (www.cs.cmu.edu/directory/api/v1/all.json, 2025-2026 captures) records become
a name block and one 'affiliation | titles | departments' block. MIT CSAIL's people Solr index (2022-2026,
the data behind csail.mit.edu/people) records become a name block and one 'title (role group)' block.
"""
import html
import json
import re

NAME_KEYS = ["label", "displayName", "display_name", "fullName", "full_name", "name"]
TITLE_KEYS = ["position", "positions", "title", "titles", "job_title", "jobTitle", "rank", "appointment", "role", "roles"]


def _records(o, out):
    if isinstance(o, dict):
        if any(isinstance(o.get(k), str) for k in NAME_KEYS) or (isinstance(o.get("n"), str) and "sn" in o) or \
                (isinstance(o.get("ss_title"), str) and ("ss_field_title" in o or "ss_name" in o)):
            out.append(o)
            return
        for v in o.values():
            _records(v, out)
    elif isinstance(o, list):
        for v in o:
            _records(v, out)


def blocks(body):
    txt = body.decode("utf-8", "replace")
    try:
        data = json.loads(txt)
    except Exception:
        try:  # Exhibit JSON tolerates trailing commas ('},\n  ]')
            data = json.loads(re.sub(r",\s*([\]}])", r"\1", txt))
        except Exception:
            return []
    recs = []
    _records(data, recs)
    out = []
    for r in recs:
        if isinstance(r.get("n"), str) and "sn" in r:
            # CMU SCS directory API (www.cs.cmu.edu/directory/api/v1/all.json): n, aff, titl[], dept[]
            name = " ".join(r["n"].split())
            if not name:
                continue
            titl = [" ".join(html.unescape(x).split()) for x in (r.get("titl") or []) if isinstance(x, str)]
            dept = [" ".join(html.unescape(x).split()) for x in (r.get("dept") or []) if isinstance(x, str)]
            out.append(["b", name])
            out.append(["b", " | ".join([r.get("aff") or ""] + ["; ".join(titl), "; ".join(dept)])])
            continue
        if isinstance(r.get("ss_title"), str) and ("ss_field_title" in r or "ss_name" in r):
            # MIT CSAIL people Solr index (csail.mit.edu/api-proxy/angular-solr?_api_proxy_uri=people...):
            # ss_title = name, ss_field_title = title, ss_name = CSAIL role group (Core/Dual, Emeritus, ...)
            name = " ".join(r["ss_title"].split())
            if not name:
                continue
            out.append(["b", name])
            t = " ".join((r.get("ss_field_title") or "").split())
            g = " ".join((r.get("ss_name") or "").split())
            line = (t + (f" ({g})" if g else "")) if t else (f"({g})" if g else "")
            if line:
                out.append(["b", line])
            continue
        nk = next((k for k in NAME_KEYS if isinstance(r.get(k), str)), None)
        if nk is None:
            continue
        name = " ".join(r[nk].split())
        if not name:
            continue
        out.append(["b", name])
        for k in TITLE_KEYS:
            if k == nk or k not in r:
                continue
            v = r[k]
            vals = [v] if isinstance(v, str) else [x for x in v if isinstance(x, str)] if isinstance(v, list) else []
            for x in vals:
                x = " ".join(x.split())
                if x and x.lower() != "unknown":
                    out.append(["b", x])
    return out
