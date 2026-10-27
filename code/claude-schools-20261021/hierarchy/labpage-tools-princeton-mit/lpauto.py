"""Turn a reviewed lab plan into member rows (used by dec_<school>_main.py).

A plan entry (plan_<school>.py, P[pi]) names the lab's people pages (live URLs, Wayback id_ URLs or sha256s), the
Wayback history to use, and the reviewer's corrections; autom.extract proposes the rows, and every row is built with
lpev.M (exact-quote and name checks). Keys:
  site, people=[src...] (also auto-extracted unless `auto` or `rows` is given), auto=[src...] (pages to auto-extract),
  rows=[manual lpev.M rows, e.g. from R()/RS()], wb=[live people URL whose Wayback captures (wb_<school>.json) are read], pubs=[Pubs/P...],
  drop=[names], keep=[flagged names to keep], roles={name: role}, years={name: [a, b]}, drop_heads=regex,
  only_heads=regex, alumni_pages=[src: every row from it is an alumni row], span={src or '*' (all Wayback captures): (start text, end text)}, alumni_ok=bool (undated alumni count: the lab has only ever been at this school),
  wb_from=year (ignore captures before), extra=[M rows], notes=str, other_pages=[...]
Rules applied here: rows autom flags (excluded-heading, faculty-desc, pre-2016, is-a-PI) are dropped unless kept;
rows from an alumni-type section without stated years count only when alumni_ok, or when the same person is seen in
a non-alumni section of a 2016+ capture.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import autom  # noqa: E402
import lpev  # noqa: E402
import names  # noqa: E402

T = os.path.dirname(os.path.abspath(__file__))
_wb = {}


def wb_captures(school, url):
    if school not in _wb:
        import glob
        _wb[school] = {}
        for p in sorted(glob.glob(f"{T}/wb_{school}*.json")):
            _wb[school].update(json.load(open(p)))
    return _wb[school].get(url, [])


def _same(a, b):
    return names.match_one(a, b) is not None


_start = None


def pi_start(school, pi):
    global _start
    if _start is None:
        p = f"{T}/pi_start.json"
        _start = json.load(open(p)) if os.path.exists(p) else {}
    return _start.get(f"{school}|{pi}")


def wb_from(school, pi, plan):
    """Earliest Wayback year used: the plan's wb_from, else max(2016, the PI's first year at the school)."""
    if plan.get("wb_from"):
        return plan["wb_from"]
    return max(2016, pi_start(school, pi) or 2016)


def rows_for(school, pi, held, plan):
    drop = [names.fold(x) for x in plan.get("drop", [])]
    keep = [names.fold(x) for x in plan.get("keep", [])]
    roles = {names.fold(k): v for k, v in plan.get("roles", {}).items()}
    yrs = {names.fold(k): v for k, v in plan.get("years", {}).items()}
    drop_heads = re.compile(plan["drop_heads"], re.I) if plan.get("drop_heads") else None
    only_heads = re.compile(plan["only_heads"], re.I) if plan.get("only_heads") else None
    srcs = [(s, False) for s in plan.get("auto", plan.get("people", []) if "rows" not in plan else [])]
    for u in plan.get("wb", []):
        for c in wb_captures(school, u):
            y = int(re.search(r"/web/(\d{4})", c).group(1))
            if wb_from(school, pi, plan) <= y <= plan.get("wb_to", 2026):
                srcs.append((c, True))
    cands = []
    for src, is_cap in srcs:
        spans = plan.get("span", {})
        orig = None
        if is_cap:
            m_ = lpev.lpcap.WAYBACK_RX.match(src)
            orig = m_.group(2) if m_ else None
        sp = spans.get(src) or (spans.get(orig) or spans.get(orig.replace("http://", "https://")) or spans.get("*")
                                if is_cap and orig else None)
        try:
            ext = autom.extract(school, src, pi, held, span=sp)
        except ValueError:
            if is_cap:  # an older capture without the section
                continue
            raise
        for x in ext:
            fn = names.fold(x["name"])
            if fn in drop or any(_same(x["name"], d) for d in plan.get("drop", [])):
                continue
            flagged = [f for f in x["flags"] if f != "weak-quote"]
            if flagged and fn not in keep:
                if os.environ.get("LP_SHOW_DROPPED"):
                    print(f"      (dropped {x['name']!r}: {','.join(flagged)}; {x['head']}; {x['desc'][:50]!r})")
                continue
            if drop_heads and x["head"] and drop_heads.search(x["head"]):
                continue
            if plan.get("drop_desc") and re.search(plan["drop_desc"], x["desc"][:80]):
                continue
            if only_heads and not (x["head"] and only_heads.search(x["head"])):
                continue
            if is_cap and not (x["head"] and autom.HEADWORD.search(x["head"])):
                continue  # Wayback rows count only under a people heading (captures are not reviewed one by one)
            x["is_cap"] = is_cap
            x["alumni_sec"] = bool(x.get("alumni") or (x["head"] and autom.ALUMNI_RX.search(x["head"]))
                                   or src in plan.get("alumni_pages", ()) or (orig is not None and (
                                       orig in plan.get("alumni_pages", ()) or orig.replace("http://", "https://") in
                                       plan.get("alumni_pages", ()) or any(orig in a for a in plan.get("alumni_pages", ())))))
            cands.append(x)
    out = []
    for x in cands:
        fn = names.fold(x["name"])
        role = roles.get(fn, x["role"])
        years = yrs.get(fn, x["years"])
        if plan.get("min_last_year") and years and years[1] is not None and years[1] < plan["min_last_year"]:
            continue  # stated dates end before the PI's time at the school
        if plan.get("require_years") and not years and fn not in keep:
            continue  # page lists members of all eras without context: only dated rows can be placed in 2016-2026
        if x["alumni_sec"] and not years and not plan.get("alumni_ok"):
            seen_current = any(c["is_cap"] and not c["alumni_sec"] and _same(c["name"], x["name"]) for c in cands)
            if not seen_current and fn not in keep:
                if os.environ.get("LP_SHOW_DROPPED"):
                    print(f"      (dropped {x['name']!r}: undated alumni; {x['head']})")
                continue
        note = f"{x['qkind']}; section: {x['head']}" if x["head"] else x["qkind"]
        out.append(lpev.M(school, x["name"], role, years, x["capture_url"] or x["sha256"], quote=x["quote"], note=note))
    manual = list(plan.get("rows", [])) + list(plan.get("extra", []))
    if plan.get("min_last_year"):
        ml = plan["min_last_year"]
        manual = [r for r in manual if (r.get("years") and (r["years"][1] or r["years"][0] or 9999) >= ml)
                  or (not r.get("years") and not plan.get("drop_undated_rows"))]
    return manual[:len(plan.get("rows", []))] + out + manual[len(plan.get("rows", [])):] if False else manual + out


def R(school, src, rows, note=None):
    """Manual rows from one page: rows = [(name, role, years, quote), ...]; quote '' means 'the name itself'."""
    out = []
    for name, role, years, quote in rows:
        out.append(lpev.M(school, name, role, years, src, quote=quote or name, note=note))
    return out


def RS(school, src, role, heading, names_, years=None, note=None, after=None):
    """Manual rows for several names under one heading (quote = heading..name)."""
    return lpev.MS(school, src, role, names_, heading, years=years, note=note, after=after)


def _role_of(text):
    r, _ = autom._role(text or "", external_ok=False)
    return r or "member"


def js_members(school, src, name_key="name", title_key="title", cat_key="category", drop=(), roles=None, note=None,
               skip_cats=r"(?i)faculty|collaborator|director|principal investigator"):
    """Rows from a JS bundle / JSON-ish data file listing members as {"name":"X", ..., "title":"Y"} objects (e.g. a
    React site's people data). Quote = the raw text from '"name":"X"' through the title value; the role comes from the
    title, else from the enclosing "category"."""
    import re as _re
    r, vs = lpev.cap(school, src)
    raw = vs.get("raw", "")
    out = []
    pat = _re.compile(r'"%s"\s*:\s*"([^"]{3,60})"(?:(?!"%s"\s*:).){0,400}?"%s"\s*:\s*"([^"]{1,80})"' %
                      (_re.escape(name_key), _re.escape(name_key), _re.escape(title_key)))
    seen = set()
    for m in pat.finditer(raw):
        nm, title = m.group(1), m.group(2)
        if nm in drop or nm in seen or not autom.namey(nm):
            continue
        cats = list(_re.finditer(r'"%s"\s*:\s*"([^"]{1,80})"' % _re.escape(cat_key), raw[:m.start()]))
        cat = cats[-1].group(1) if cats else ""
        if _re.search(skip_cats, cat) or _re.search(skip_cats, title):
            continue
        seen.add(nm)
        role = (roles or {}).get(nm) or (_role_of(title) if _role_of(title) != "member" else _role_of(cat))
        out.append(lpev.M(school, nm, role, None, src, quote=m.group(0), note=note or f"category '{cat}', title '{title}'"))
    return out


def sqs_members(school, src, include=None, drop=(), roles=None, years=None, note=None):
    """Rows from a Squarespace page whose people blocks are stored as HTML-escaped JSON items
    '&quot;title&quot;: &quot;NAME&quot;, &quot;description&quot;: &quot;...'. Quote = the raw item text from the title
    through the first 160 characters of its description."""
    import html as _html
    import re as _re
    r, vs = lpev.cap(school, src)
    raw = vs.get("raw", "")
    out, seen = [], set()
    for m in _re.finditer(r"&quot;title&quot;: &quot;([^&]{3,60})&quot;, &quot;description&quot;: &quot;((?:(?!&quot;, &quot;).){0,400})", raw):
        nm = m.group(1).strip()
        if nm in seen or nm in drop or (include is not None and nm not in include) or not autom.namey(nm):
            continue
        seen.add(nm)
        desc = _re.sub(r"<[^>]+>", " ", _html.unescape(m.group(2).replace("\\/", "/")))
        q = m.group(0)[: m.group(0).find(m.group(2)) + min(len(m.group(2)), 160)]
        role = (roles or {}).get(nm)
        if not role:
            if _re.search(r"(?i)completed (his|her|their) ph\.?d|started (his|her|their) ph\.?d at (princeton|mit)|ph\.?d (student|candidate)", desc):
                role = "phd"
            elif _re.search(r"(?i)received (his|her|their) master|m\.eng|master'?s student", desc):
                role = "masters"
            elif _re.search(r"(?i)graduated from (princeton|mit)|undergrad|senior thesis|class of", desc):
                role = "undergraduate"
            elif _re.search(r"(?i)visiting|postdoc", desc):
                role = "other" if _re.search(r"(?i)visiting", desc) else "postdoc"
            else:
                role = _role_of(desc)
        nm = _re.sub(r",\s*(M\.?Eng\.?|M\.?S\.?|Ph\.?D\.?|B\.?S\.?E?\.?)$", "", nm)
        out.append(lpev.M(school, nm, role, (years or {}).get(nm), src, quote=q,
                          note=note or f"Squarespace people item: {lpev.lpcap.collapse(desc)[:120]}"))
    return out


def rx_members(school, src, pattern, role_map=None, default_role="member", note=None, drop=(), view="html", span=None):
    """Rows from a page whose members follow a regular textual pattern (e.g. a table 'Last, First Position 2019-2023').
    pattern needs named groups: name (as written), and optionally role, y1, y2. Quote = the whole match."""
    import re as _re
    r, vs = lpev.cap(school, src)
    t = vs.get(view) or vs.get("html_p") or vs.get("html") or vs.get("raw") or ""
    if span:
        a = t.find(span[0])
        b = t.find(span[1], a + 1) if span[1] else -1
        t = t[a: b if b > a else len(t)]
    out, seen = [], set()
    for m in _re.finditer(pattern, t):
        nm = m.group("name").strip()
        if nm in seen or nm in drop:
            continue
        seen.add(nm)
        gd = m.groupdict()
        rt = (gd.get("role") or "").strip()
        role = (role_map or {}).get(rt) or (_role_of(rt) if rt else default_role)
        y1 = int(gd["y1"]) if gd.get("y1") else None
        y2 = int(gd["y2"]) if gd.get("y2") else y1
        out.append(lpev.M(school, nm, role, [y1, y2] if y1 else None, src, quote=m.group(0).strip(), note=note or (rt or None)))
    return out


def table_members(school, src, name_col=0, role_col=1, years_col=2, ncols=3, role_map=None, note=None, drop=(),
                  skip_rx=None):
    """Rows from an HTML table of members (one <tr> per person). Quote = the first `ncols` cells of the row joined by
    single spaces (whitespace-collapsed), which must be an exact substring of the page text."""
    import re as _re
    from bs4 import BeautifulSoup
    r, vs = lpev.cap(school, src)
    t = vs.get("html") or ""
    soup = BeautifulSoup(lpev.lpcap.decode(r["content"]), "lxml")
    out, seen = [], set()
    for tr in soup.find_all("tr"):
        cells = [lpev.lpcap.collapse(td.get_text(" ")) for td in tr.find_all(["td", "th"])]
        if len(cells) <= max(name_col, role_col):
            continue
        nm = cells[name_col]
        if not nm or nm in seen or nm in drop or (skip_rx and _re.search(skip_rx, " ".join(cells))):
            continue
        if not autom.namey(names_display(nm)):
            continue
        q = " ".join(c for c in cells[:ncols] if c)
        if q not in t:
            q = nm
        rt = cells[role_col] if role_col is not None else ""
        role = (role_map or {}).get(rt) or (_role_of(rt) if rt else "member")
        years = None
        if years_col is not None and len(cells) > years_col:
            ys = _re.findall(r"(?:19|20)\d\d", cells[years_col])
            if ys:
                years = [int(ys[0]), int(ys[-1]) if len(ys) > 1 else int(ys[0])]
        seen.add(nm)
        out.append(lpev.M(school, nm, role, years, src, quote=q, note=note or rt or None))
    return out


def names_display(n):
    """'Last, First' -> 'First Last' for the name-likeness test only."""
    if "," in n:
        a, b = n.split(",", 1)
        return f"{b.strip()} {a.strip()}"
    return n
