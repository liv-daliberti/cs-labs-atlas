"""Build the lab-page pass outputs from per-lab specs (work/<school>/<slug>.json).

Spec keys (all optional except pi):
  pi, lab_site, people_page, notes
  sources: [{url, auto: true|false, kind: "page"|"epfl_profile", only: [rx], skip: [rx], drop: [names],
             role: {name: role}, years: {name: [a, b]}, alumni: {name: bool}, note: str, section_role: {rx: role},
             keep_roles: [roles]}]
           url is a live URL or a Wayback id_ URL whose capture is stored. auto: candidates from the page's
           sectioned name lines (lpdom.member_candidates); kind epfl_profile: the people.epfl.ch "PhD Students" /
           "Past EPFL PhD Students" blocks.
  members: [{name, role, years?, alumni?, src, quote?, heading?, note?}]   manual rows (quote auto-built from
           heading+name when absent)
  held_as: {page name: held name | null}   force / forbid a students_held match
  merge: {page name: other page name}        same person written two ways
  pubs_pages: [url | {url, mode}]
  excluded: [{name, why}]                    people deliberately left out (pre-school, other faculty...)
Every quote is checked here: exact substring of a whitespace-collapsed text view of the stored capture, containing
every name token. Rows that fail are reported as problems and left out.
"""
import gzip
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lpcap
import lpdom
import lplab
import lpnames

ROLES = {"phd", "postdoc", "masters", "undergraduate", "research_staff", "visitor", "intern", "member", "other"}
DROP_ROLES = {"faculty", "admin"}
MAX_SPAN = 1500
LONG_SPAN = 4000  # last resort: a long but exact heading..name span (big tables)


def has_name(quote, name):
    q = lpnames.fold(quote)
    toks = [t for t in re.split(r"[^a-z0-9]+", lpnames.fold(re.sub(r"\([^)]*\)", " ", name))) if len(t) > 1]
    return bool(toks) and all(re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", q) for t in toks)


_views = {}


def views_of(school, url):
    if (school, url) not in _views:
        r = lplab.stored(school, url)
        if not r:
            _views[(school, url)] = (None, {})
        else:
            _views[(school, url)] = (r, lpcap.texts(r["content"], r.get("content_type")))
    return _views[(school, url)]


def cap_year(r):
    m = re.search(r"/web/(\d{4})", r.get("capture_url") or "")
    if m:
        return int(m.group(1))
    return int((r.get("fetched_at") or "2026")[:4])


def _ev(r, quote):
    o = {"url": r["url"]}
    if r.get("capture_url"):
        o["capture_url"] = r["capture_url"]
    o["sha256"] = r["sha256"]
    o["quote"] = quote
    return o


def find_quote(views, name, heading=None, rest=None, nxt=None, other_heads=(), other_names=(), role_head=None):
    """Shortest good quote, in order of preference:
    1. heading..name (<= 400 chars, no other heading in between)
    2. name followed by role words from its own line / the card's next line (no other member name in between)
    3. heading..name (<= MAX_SPAN)
    4. role words within 40 chars before the name (no other member name in between)
    Returns None when nothing qualifies (the row is then reported, not guessed)."""
    others = [o for o in other_names if o and o != name and o not in name and name not in o]
    for t in [views.get("html"), views.get("pdf"), views.get("raw")]:
        if not t:
            continue
        occ = [m.start() for m in re.finditer(re.escape(name), t)]
        if not occ:
            continue
        spans = []
        if heading:
            for p in occ:
                h = t.rfind(heading, 0, p)
                if h < 0:
                    continue
                between = t[h + len(heading):p]
                if any(oh and oh != heading and oh in between and oh not in heading for oh in other_heads):
                    continue
                spans.append((p + len(name) - h, t[h:p + len(name)]))
        spans.sort()
        if spans and spans[0][0] <= 400:
            return spans[0][1]
        for p in occ:
            post = t[p + len(name):p + len(name) + 160]
            cut = len(post)
            for o in others:
                j = post.find(o)
                if 0 <= j < cut:
                    cut = j
            m = lpdom.ROLE_RX.search(post[:cut])
            if m:
                return t[p:p + len(name) + m.end()]
        if spans and spans[0][0] <= MAX_SPAN:
            return spans[0][1]
        for p in occ:
            pre = t[max(0, p - 40):p]
            if any(o in pre for o in others):
                continue
            ms = list(lpdom.ROLE_RX.finditer(pre))
            if ms:
                st = max(0, p - 40) + ms[-1].start()
                return t[st:p + len(name)]
        if spans and spans[0][0] <= LONG_SPAN:
            return spans[0][1]
        # the section's role heading (e.g. 'Postdoctoral Researchers') above per-card sub-headings: accept the span when
        # no other role-section heading lies between it and the name
        if role_head and role_head != heading:
            role_others = [oh for oh in other_heads if oh != role_head and oh not in role_head and
                           (lpdom.SECTION_LABEL_RX.search(oh) or lpdom.ROLE_RX.search(oh))]
            best = None
            for p in occ:
                h = t.rfind(role_head, 0, p)
                if h < 0:
                    continue
                between = t[h + len(role_head):p]
                if any(oh in between for oh in role_others):
                    continue
                if p + len(name) - h <= LONG_SPAN and (best is None or p + len(name) - h < len(best)):
                    best = t[h:p + len(name)]
            if best:
                return best
    return None


def section_role(path, rest, nxt, overrides=None):
    if overrides:
        hp = " › ".join(path)
        for rx, role in overrides.items():
            if re.search(rx, hp, re.I):
                return role
    for h in reversed(path):
        r = lpdom.role_of(h)
        if r:
            return r
    return lpdom.role_of(rest) or lpdom.role_of(nxt[:60] if nxt else None) or "member"


NONPEOPLE_RX = (r"publication|papers|preprints?|selected works|talks|news|press|media|teaching|courses?|projects?|"
                r"software|code|datasets?|awards?|honou?rs|service|events?|seminars?|blog|research( areas| interests)?$|"
                r"contact|sponsors?|funding|collaborat|partners|links|bibliograph|in the news|patents?|books?")
UNTIL_RX = re.compile(r"\buntil\s+((?:19|20)\d{2})\b", re.I)


def path_years(path, rest):
    for h in reversed(path):
        m = UNTIL_RX.search(h)
        if m:
            return [None, int(m.group(1))]
        y = lpdom.years_in(h)
        if y and re.fullmatch(r"\s*(?:class of\s*|cohort\s*)?(19|20)\d{2}(\s*[-–]\s*((19|20)\d{2}|present))?\s*", h, re.I):
            return y
    if rest:
        y = lpdom.years_in(rest)
        if y:
            return y
    return None


def is_alumni(path, rest):
    hp = " › ".join(path)
    if lpdom.ALUMNI_RX.search(hp) or UNTIL_RX.search(hp):
        return True
    if rest and re.search(r"\bnow (at|with|a|an)\b|\bmoved to\b|\bgraduated\b|\bformer\b|\bnext:", rest, re.I):
        return True
    return False


def auto_rows(school, row, src, problems):
    url = src["url"]
    r, views = views_of(school, url)
    if not r:
        problems.append(f"source not stored: {url}")
        return []
    base = url if r.get("capture_url") else (r.get("final_url") or url)
    cands, ls = lpdom.member_candidates(r["content"], base)
    heads = {l.text for l in ls if (lpdom.is_heading(l) or (l.level and l.level <= 6)) and
             not lpdom.name_prefix(l.text)[0]}  # person-name card titles are not section headings
    only = [re.compile(x, re.I) for x in src.get("only") or []]
    nonpeople = re.compile(src.get("nonpeople_rx") or NONPEOPLE_RX, re.I)
    skip = [re.compile(x, re.I) for x in src.get("skip") or []]
    drop = {lpnames.fold(x) for x in src.get("drop") or []}
    keep_roles = set(src.get("keep_roles") or [])
    cy = cap_year(r)
    out = []
    for path, name, rest, nxt, i in cands:
        hp = " › ".join(path)
        if only and not any(x.search(hp) for x in only):
            continue
        if any(x.search(hp) for x in skip):
            continue
        # sections that are not member lists (publications, news, talks...) unless a deeper heading names a role
        if any(re.search(r"collaborat|friends of", h, re.I) for h in path):
            continue  # collaborators are not lab members
        ib = max([k for k, h in enumerate(path) if nonpeople.search(h)], default=-1)
        if ib >= 0 and not any(lpdom.SECTION_LABEL_RX.search(h) or lpdom.ROLE_RX.search(h) for h in path[ib + 1:]):
            continue
        if lpnames.fold(name) in drop:
            continue
        if src.get("only_names") and name not in src["only_names"]:
            continue
        if any(lpnames.match_one(name, n) in ("exact", "reordered", "subset") for n in (row.get("names") or [row["pi"]])):
            continue
        if other_pi(school, row, name):
            continue
        if not src.get("no_name_filter") and not lpdom.plausible_person(name) and \
                not lpnames.match_held(name, row.get("students_held") or [])[0] and name not in (src.get("keep") or []):
            continue
        role = (src.get("role") or {}).get(name) or section_role(path, rest, nxt, src.get("section_role"))
        if role in DROP_ROLES and role not in keep_roles:
            continue
        if role not in ROLES:
            role = "other"
        years = (src.get("years") or {}).get(name)
        if years is None:
            years = path_years(path, rest)
        basis = "page" if years else None
        alumni = (src.get("alumni") or {}).get(name)
        if alumni is None and any(re.search(x, hp, re.I) for x in src.get("alumni_sections") or []):
            alumni = True
        if alumni is None and any(re.search(x, hp, re.I) for x in src.get("current_sections") or []):
            alumni = False
        if alumni is None:
            alumni = is_alumni(path, rest)
        if src.get("undated_is_alumni") and years is None and not re.search(r"current|present|\bnow\b", hp, re.I):
            alumni = True  # a stale or historical list: undated names are not evidence of current membership
        if years is None and r.get("capture_url"):
            years = [cy, cy] if not alumni else None
            basis = "capture_date" if years else None
        if years is None and not alumni and not r.get("capture_url"):
            years = [cy, cy]
            basis = "capture_date"
        heading = path[-1] if path else None
        if not in_window({"years": years}):
            out.append({"name": name, "years": years, "out_of_window": True})
            continue
        rh = next((h for h in reversed(path) if lpdom.SECTION_LABEL_RX.search(h) or lpdom.ROLE_RX.search(h)), None)
        q = find_quote(views, name, heading, rest, nxt, heads, [c[1] for c in cands], role_head=rh)
        if not q or not has_name(q, name):
            problems.append(f"no quote for {name!r} on {url}")
            continue
        o = {"name": name, "role": role, "years": years, "years_basis": basis, "alumni": bool(alumni),
             "section": hp or None}
        o.update(_ev(r, lpdom.collapse(q)))
        note = src.get("note")
        if r.get("capture_url") and not note:
            note = f"listed in the {cy} Wayback capture of the page"
        if note:
            o["note"] = note
        out.append(o)
    return out


EPFL_HEADS = [("Past EPFL PhD Students as codirector", "codirector"), ("Past EPFL PhD Students", "past"),
              ("PhD Students", "current")]
EPFL_STOP = (r"(?=\s(?:Past EPFL PhD Students|Courses|Contact EPFL|Teaching & PhD|Awards|Publications|Research|"
             r"Infoscience|Biography|Teaching|Selected publications|Positions|Fields of expertise)\b|$)")


_pis = {}


def other_pi(school, row, name):
    """name is another PI of this school's lab list (faculty listed on shared or centre pages)."""
    if school not in _pis:
        _pis[school] = [(r["pi"], r.get("names") or [r["pi"]]) for r in lplab.rows(school)]
    for pi, names in _pis[school]:
        if pi == row["pi"]:
            continue
        if any(lpnames.match_one(name, n) in ("exact", "reordered") for n in names):
            return True
    return False


def lab_start(school, row):
    """First year the census lists the PI at the school (None when listed from the first observed year, 2016)."""
    names = row.get("names") or [row["pi"]]
    for c in lplab.census(school):
        if any(lpnames.match_one(n, c.get("name", "")) in ("exact", "reordered", "subset") for n in names):
            ys = [y for y in c.get("years_listed") or [] if isinstance(y, int)]
            if ys and min(ys) > 2016:
                return min(ys)
            return None
    return None


def epfl_profile_rows(school, row, src, problems):
    url = src["url"]
    r, views = views_of(school, url)
    if not r:
        problems.append(f"source not stored: {url}")
        return []
    t = views.get("html") or views.get("raw") or ""
    cy = cap_year(r)
    out = []
    drop = {lpnames.fold(x) for x in src.get("drop") or []}
    for m in re.finditer(r"(Past EPFL PhD Students as codirector|Past EPFL PhD Students|(?<!Past EPFL )PhD Students)\s(.*?)"
                         + EPFL_STOP, t):
        head, body = m.group(1), m.group(2)
        kind = dict(EPFL_HEADS)[head]
        start, pos = m.start(1), m.start(2)
        for part in body.split(" , "):
            part = part.strip()
            if not part:
                continue
            i = t.find(part, pos)
            pos = i + len(part)
            ym = re.search(r"\((\d{4})\)\s*$", part)
            name = re.sub(r"\s*\(\d{4}\)\s*$", "", part).strip()
            if lpnames.fold(name) in drop or not lpdom.looks_like_name(name) and len(name.split()) > 6:
                continue
            years = [int(ym.group(1))] * 2 if ym else ([cy, cy] if kind == "current" else None)
            if years is None:
                out.append({"name": name, "years": None, "out_of_window": True})  # undated past thesis
                continue
            quote = t[start:i + len(part)]
            if len(quote) > MAX_SPAN:
                quote = t[max(start, i - 200):i + len(part)]
                if head not in quote:
                    # keep the heading: fall back to a shorter span from the nearest " , " run start
                    quote = t[start:i + len(part)]
            if not has_name(quote, name):
                problems.append(f"profile quote lacks {name!r}")
                continue
            o = {"name": name, "role": "phd", "years": years, "years_basis": "page" if ym else "capture_date",
                 "alumni": kind != "current", "section": head}
            o.update(_ev(r, quote))
            o["note"] = {"current": "current doctoral student listed on the director's EPFL profile",
                         "past": "thesis directed (defence year in parentheses) per the director's EPFL profile",
                         "codirector": "thesis co-directed (defence year in parentheses) per the EPFL profile"}[kind]
            out.append(o)
    return out


def manual_rows(school, row, spec, problems):
    out = []
    for m in spec.get("members") or []:
        name, src = m["name"], m["src"]
        r, views = views_of(school, src)
        if not r:
            problems.append(f"manual {name!r}: source not stored {src}")
            continue
        q = m.get("quote")
        if q:
            q = lpdom.collapse(q)
            if not any(q in v for v in views.values()):
                problems.append(f"manual {name!r}: quote not found: {q[:120]}")
                continue
        else:
            q = find_quote(views, name, m.get("heading"), m.get("rest"), None, ())
            if not q:
                problems.append(f"manual {name!r}: could not build a quote (heading {m.get('heading')!r})")
                continue
            q = lpdom.collapse(q)
        if not has_name(q, name):
            problems.append(f"manual {name!r}: quote lacks the name: {q[:120]}")
            continue
        role = m.get("role") or "member"
        if role not in ROLES:
            problems.append(f"manual {name!r}: bad role {role}")
            role = "other"
        o = {"name": name, "role": role, "years": m.get("years"), "years_basis": "page" if m.get("years") else None,
             "alumni": bool(m.get("alumni")), "section": m.get("heading")}
        o.update(_ev(r, q))
        if m.get("note"):
            o["note"] = m["note"]
        out.append(o)
    return out


ROLE_PRI = ["phd", "postdoc", "masters", "undergraduate", "research_staff", "visitor", "intern", "other", "member"]


def same_person(a, b):
    if lpnames.fold(a) == lpnames.fold(b):
        return True
    m = lpnames.match_one(a, b) or lpnames.match_one(b, a)
    return m in ("exact", "reordered", "subset", "nickname")


def merge_rows(rows, merge_map):
    people = []
    for r in rows:
        nm = merge_map.get(r["name"], r["name"])
        tgt = None
        for p in people:
            if same_person(p["name"], nm) or (merge_map.get(r["name"]) and p["name"] == merge_map[r["name"]]):
                tgt = p
                break
        if tgt is None:
            r = dict(r)
            r["other_sources"] = []
            people.append(r)
            continue
        src = {k: r[k] for k in ("url", "capture_url", "sha256", "quote") if k in r}
        src["name_as_written"] = r["name"]
        src["role"] = r["role"]
        if r.get("years"):
            src["years"] = r["years"]
        tgt["other_sources"].append(src)
        if ROLE_PRI.index(r["role"]) < ROLE_PRI.index(tgt["role"]) and tgt["role"] in ("member", "other"):
            tgt["role"] = r["role"]
        ya, yb = tgt.get("years"), r.get("years")
        if yb:
            if not ya:
                tgt["years"] = yb
            else:
                lo = [x for x in (ya[0], yb[0]) if x]
                hi = [x for x in (ya[1], yb[1]) if x]
                tgt["years"] = [min(lo) if lo else None, max(hi) if hi else None]
        if r["name"] != tgt["name"] and lpnames.fold(r["name"]) != lpnames.fold(tgt["name"]):
            tgt.setdefault("written_also", [])
            if r["name"] not in tgt["written_also"]:
                tgt["written_also"].append(r["name"])
    return people


def in_window(r):
    y = r.get("years")
    if not y:
        return True
    hi = y[1] if y[1] is not None else y[0]
    lo = y[0] if y[0] is not None else y[1]
    if hi is not None and hi < 2016:
        return False
    if lo is not None and lo > 2026:
        return False
    return True


def build_lab(school, row, verbose=False):
    path = lplab.spec_path(school, row)
    problems = []
    out = {"pi": row["pi"], "lab_site": None, "people_page": None, "students": [], "notes": ""}
    if not os.path.exists(path):
        problems.append("no spec")
        out["notes"] = "not reviewed"
        return out, [], problems
    spec = json.load(open(path))
    if spec.get("pi") != row["pi"]:
        problems.append(f"spec pi {spec.get('pi')!r} != {row['pi']!r}")
    out["lab_site"] = spec.get("lab_site")
    out["people_page"] = spec.get("people_page")
    rows = []
    for src in spec.get("sources") or []:
        if src.get("kind") == "epfl_profile":
            rows += epfl_profile_rows(school, row, src, problems)
        elif src.get("auto", True):
            rows += auto_rows(school, row, src, problems)
    rows += manual_rows(school, row, spec, problems)
    excluded = list(spec.get("excluded") or [])
    keep = []
    for r in rows:
        if r.get("out_of_window") or not in_window(r):
            excluded.append({"name": r["name"], "why": (f"years {r['years']} end before 2016" if r.get("years")
                                                        else "undated past thesis on the EPFL profile")})
            continue
        keep.append(r)
    people = merge_rows(keep, spec.get("merge") or {})
    # Undated alumni (no year on any of their rows) need something that places them in 2016-2026:
    #  - an early (<= 2016) capture of the people page (spec before_2016) that does not list them at all: they joined
    #    after it; one that lists them under a former-member heading: they left before the window;
    #  - or a lab that started in 2016 or later (census first listing year).
    early_all, early_alum, early_url = [], [], None
    for b in spec.get("before_2016") or []:
        r, views = views_of(school, b["url"])
        if not r:
            problems.append(f"before_2016 source not stored: {b['url']}")
            continue
        if cap_year(r) > 2016:
            problems.append(f"before_2016 source is not a 2016-or-earlier capture: {b['url']}")
            continue
        early_url = r.get("capture_url") or r["url"]
        cands, _ = lpdom.member_candidates(r["content"], b["url"])
        rx = [re.compile(x, re.I) for x in b.get("sections") or ["alumn|former|past|graduated"]]
        for pth, n, rest, nxt, i in cands:
            early_all.append(n)
            if any(x.search(" › ".join(pth)) for x in rx):
                early_alum.append(n)
    ls = spec.get("lab_start", lab_start(school, row))
    held = row.get("students_held") or []
    kept = []
    for p in people:
        rows_y = [p.get("years")] + [o.get("years") for o in p.get("other_sources", [])]
        undated = not any(y for y in rows_y)
        names = [p["name"]] + p.get("written_also", [])
        is_held = any(lpnames.match_held(n, held)[0] for n in names)
        if undated and p.get("alumni") and not is_held and not spec.get("keep_undated_alumni"):
            if any(same_person(n, e) for n in names for e in early_alum):
                excluded.append({"name": p["name"], "why": f"undated alumni entry; already a former member in {early_url}"})
                continue
            if early_url and not any(same_person(n, e) for n in names for e in early_all):
                p["note"] = ((p.get("note") or "") + f"; undated alumni entry absent from the 2016-or-earlier capture "
                             f"{early_url}, so after it").strip("; ")
            elif not (ls and ls >= 2016):
                excluded.append({"name": p["name"], "why": "undated alumni entry; nothing places them in 2016-2026"})
                continue
            else:
                p["note"] = ((p.get("note") or "") + f"; undated alumni entry of a lab started in {ls}").strip("; ")
        kept.append(p)
    people = kept
    forced = spec.get("held_as") or {}
    for p in people:
        names = [p["name"]] + p.get("written_also", [])
        h, how = None, None
        for n in names:
            if n in forced:
                h, how = forced[n], ("curated" if forced[n] else None)
                if forced[n] and forced[n] not in held:
                    problems.append(f"held_as target {forced[n]!r} not in students_held")
                break
        else:
            for n in names:
                h, how = lpnames.match_held(n, held)
                if h:
                    break
        p["already_held"] = bool(h)
        if h:
            p["held_name"] = h
            p["match"] = how
            al = [n for n in names if lpnames.fold(n) != lpnames.fold(h)]
            # every held alias string of this person
            p["aliases"] = al
        else:
            p["aliases"] = [n for n in p.get("written_also", [])]
            fz = [x for n in names for x in lpnames.fuzzy_held(n, held)]
            if fz:
                p["possible_held"] = sorted(set(fz))
            if how == "ambiguous":
                p["possible_held"] = sorted(set(p.get("possible_held", []) + [x for x in held if lpnames.match_one(p["name"], x)]))
        p.pop("written_also", None)
        if not p["other_sources"]:
            p.pop("other_sources")
    # one row per held person: two page rows matching the same held name are the same person
    seen = {}
    final = []
    for p in people:
        if p["already_held"]:
            k = p["held_name"]
            hit = None
            for f in final:
                if f["already_held"] and (f["held_name"] == k or same_person(f["held_name"], k)):
                    hit = f
                    break
            if hit:
                hit.setdefault("other_sources", []).append({k2: p[k2] for k2 in ("url", "capture_url", "sha256", "quote")
                                                            if k2 in p} | {"name_as_written": p["name"]})
                if p["name"] not in hit["aliases"] and lpnames.fold(p["name"]) != lpnames.fold(hit["held_name"]):
                    hit["aliases"].append(p["name"])
                continue
        final.append(p)
    out["students"] = final
    notes = spec.get("notes") or ""
    seen_x, ex2 = set(), []
    for e in excluded:
        k = lpnames.fold(e["name"])
        if k not in seen_x:
            seen_x.add(k)
            ex2.append(e)
    excluded = ex2
    if excluded:
        notes = (notes + " | Excluded: " + "; ".join(f"{e['name']} ({e['why']})" for e in excluded)).strip(" |")
    pp = spec.get("pubs_pages") or []
    if pp:
        notes = (notes + " | Publications page(s): " + ", ".join(x if isinstance(x, str) else x["url"] for x in pp)).strip(" |")
    out["notes"] = notes
    pubs = build_pubs(school, row, spec, problems)
    return out, pubs, problems


def build_pubs(school, row, spec, problems):
    import lppubs
    res, seen = [], set()
    for x in spec.get("pubs_pages") or []:
        url, mode = (x, "auto") if isinstance(x, str) else (x["url"], x.get("mode", "auto"))
        r, views = views_of(school, url)
        if not r:
            problems.append(f"pubs page not stored: {url}")
            continue
        for e in lppubs.parse(school, row, r, url, mode=mode):
            if not e["in_window"] or e["held"]:
                continue
            k = lpdom.norm_title(e["title"])
            if k in seen:
                continue
            q = e.get("quote")
            if not q or not any(q in v for v in views.values()):
                problems.append(f"pub quote not found: {e['title'][:80]}")
                continue
            if lpdom.norm_title(e["title"]) not in lpdom.norm_title(q):
                problems.append(f"pub quote lacks the title: {e['title'][:80]}")
                continue
            seen.add(k)
            o = {"pi": row["pi"], "title": e["title"], "year": e["year"], "venue": e["venue"], "links": e["links"],
                 "url": r["url"]}
            if r.get("capture_url"):
                o["capture_url"] = r["capture_url"]
            o["sha256"] = r["sha256"]
            o["quote"] = q
            res.append(o)
    return res


def build_all(school):
    ev, pubs, allprob = [], [], {}
    for row in lplab.rows(school):
        o, p, prob = build_lab(school, row)
        ev.append(o)
        pubs += p
        if prob:
            allprob[row["pi"]] = prob
    return ev, pubs, allprob


if __name__ == "__main__":
    school = sys.argv[1]
    write = "--write" in sys.argv
    ev, pubs, prob = build_all(school)
    print(f"{school}: {len(ev)} labs, {sum(len(e['students']) for e in ev)} people, "
          f"{sum(1 for e in ev for s in e['students'] if not s['already_held'])} new, {len(pubs)} missing pubs, "
          f"{len(prob)} labs with problems")
    for k, v in prob.items():
        for x in v[:5]:
            print("  PROBLEM", k, "|", x)
    if write:
        with open(lpcap.data("labpage-evidence.json", school), "w") as f:
            json.dump(ev, f, ensure_ascii=False, indent=1)
        with gzip.open(lpcap.data("labpage-pubs.jsonl.gz", school), "wt") as f:
            for p in pubs:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        print("written")
