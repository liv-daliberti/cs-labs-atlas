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
from urllib.parse import urlsplit

NAME_KEYS = ["label", "displayName", "display_name", "fullName", "full_name", "name"]
TITLE_KEYS = ["position", "positions", "title", "titles", "job_title", "jobTitle", "rank", "appointment", "role", "roles"]


def dpi_teacher_records(data):
    """Validate one complete unfiltered official response; no fixed roster size."""
    if not isinstance(data, dict):
        raise ValueError('DPI response must be an object')
    if type(data.get('totalnum')) is not int or data['totalnum'] < 1:
        raise ValueError('DPI totalnum must be a positive integer')
    if type(data.get('totalpage')) is not int or data['totalpage'] != 1:
        raise ValueError('DPI response must contain the complete single-page roster')
    if type(data.get('pageindex')) is not int or data['pageindex'] not in (0, 1):
        raise ValueError('DPI response has an unrecognized pageindex')
    groups = data.get('teacherData')
    if not isinstance(groups, list) or not groups:
        raise ValueError('DPI teacherData must contain institute groups')
    records, ids, group_names = [], set(), set()
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get('collegeName'), str) or not group['collegeName'].strip():
            raise ValueError('DPI institute group has no literal collegeName')
        if group['collegeName'] in group_names:
            raise ValueError('DPI institute group repeated')
        group_names.add(group['collegeName'])
        if not isinstance(group.get('teacherlist'), list):
            raise ValueError('DPI institute group has no teacherlist')
        for person in group['teacherlist']:
            if not isinstance(person, dict):
                raise ValueError('DPI teacher record must be an object')
            ident = person.get('teacherId')
            if type(ident) is not int or ident < 1 or ident in ids:
                raise ValueError('DPI teacherId missing, invalid or repeated')
            ids.add(ident)
            for field in ('teacherName', 'prorank', 'unit', 'url'):
                if not isinstance(person.get(field), str) or not person[field].strip():
                    raise ValueError(f'DPI teacher record has no literal {field}')
            if isinstance(person.get('name'), str) and person['name'].strip() != person['teacherName'].strip():
                raise ValueError('DPI name and teacherName disagree')
            u = urlsplit(person['url'])
            if u.scheme not in ('http', 'https') or u.hostname != 'faculty.dpi.tsinghua.edu.cn' or not u.path:
                raise ValueError('DPI teacher profile must belong to its declared official host')
            records.append((group['collegeName'], person))
    if len(records) != data['totalnum']:
        raise ValueError('DPI teacher count disagrees with response totalnum')
    return records


def dpi_json_blocks(data):
    """Explicit json_people adapter; displayed values from each same source object."""
    out = []
    for _group, p in dpi_teacher_records(data):
        out.extend([['b', p['teacherName'].strip()], ['b', p['prorank'].strip()], ['b', p['unit'].strip()]])
    return out


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


def _rc_item_blocks(content):
    """SJTU CS directory feed (cs.sjtu.edu.cn/active/ajax_teacher_list.html, 2025-): JSON {tab_html, content}; `content` holds one div.rc-item per institute
    (name in div.tit .name; leaders in div.dt a; teachers in div.name-list a). One block for the institute, then one per person; no rank is printed."""
    from bs4 import BeautifulSoup
    out = []
    for item in BeautifulSoup(content, "html.parser").select("div.rc-item"):
        nm = item.select_one("div.tit .name")
        if nm and nm.get_text(strip=True):
            out.append(["b", " ".join(nm.get_text(" ").split())])
        for a in item.select("div.dt a[href], div.name-list a[href]"):
            name = " ".join(a.get_text(" ").split())
            if name:
                out.append(["b", name])
    return out


def blocks(body):
    txt = body.decode("utf-8", "replace")
    try:
        data = json.loads(txt)
    except Exception:
        try:  # Exhibit JSON tolerates trailing commas ('},\n  ]')
            data = json.loads(re.sub(r",\s*([\]}])", r"\1", txt))
        except Exception:
            return []
    if isinstance(data, dict) and "teacherData" in data:
        return dpi_json_blocks(data)
    if isinstance(data, dict) and isinstance(data.get("content"), str) and "rc-item" in data["content"]:
        return _rc_item_blocks(data["content"])
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
