"""Thesis-style records from the PIs' own pages listed in lab_sources.SOURCES (MIT, CMU, EPFL, Princeton; 2026-10-27).

Every record has the records.py shape {school, source, id, url, capture_url, sha256, student, author_raw, advisers=[PI],
year, years=[y0, y1], role, degree, dept, cs, title, q}; build.py treats it like a thesis whose adviser is the PI. q()
returns the shortest stretch of the stored page text from a PI family-name occurrence to the student's anchor (or the
reverse), at most the source's qmax characters, or raises ValueError (reported by build.py under quote_failures).
Reads hierarchy/<school>/thesis-captures.sqlite only (read-only).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import names  # noqa: E402
import records  # noqa: E402


def records_for(school):
    import lab_sources as ls
    pis = {p["pi"]: p for p in json.load(open(f"{names.ROOT}/{school}/pis.json"))}
    out = []
    for src in ls.SOURCES.get(school, []):
        pi = src["pi"]
        if pi not in pis:
            raise SystemExit(f"lab_sources: {pi} not in {school}/pis.json")
        pnames = list(dict.fromkeys([pi] + list(pis[pi].get("names") or []) + names.ALIASES.get(school, {}).get(pi, [])))
        qmax = src.get("qmax") or ls.QMAX
        # 'adviser' (optional): the PI's name form that names.PIIndex resolves to this PI, when the 'pi' string itself
        # resolves to another entry (Stanford 2026-10-27: 'H.-S. Philip Wong' is grouped with 'S Simon Wong'; 'Hon-Sum Philip
        # Wong' is not)
        caps = {}
        for u in src["captures"]:
            c = records._capture(school, u)
            if c:
                caps[u] = c
        for e in src.get("entries") or []:
            student, role, y0, y1 = e[:4]
            anchor = e[4] if len(e) > 4 and e[4] else student
            u = e[5] if len(e) > 5 else src["captures"][0]
            if u not in caps:
                continue
            url, cap, sha, ct, content, ycap = caps[u]
            view = records.View(content, ct, sha)
            tv = view.views()
            text = tv.get("pdf") or tv.get("html") or tv.get("raw") or ""
            qq = records.pi_window(text, records.collapse(anchor), pnames, qmax)
            if qq is None:
                def q(adv_raw, anchor=anchor, qmax=qmax):
                    raise ValueError(f"no PI-to-student window <= {qmax} chars for '{anchor}'")
            else:
                def q(adv_raw, view=view, qq=qq):
                    return view.check(qq)
            y0, y1 = max(y0, records.Y0), min(y1, records.Y1)
            out.append(records.rec(school=school, source=src["kind"], id=f"{(cap or url)[-60:]}:{student}", url=url, capture_url=cap,
                                   sha256=sha, student=student, author_raw=student, advisers=[src.get("adviser") or pi], year=y1, years=[y0, y1],
                                   role=role, degree=f"listed on {src['kind']} ({ycap} capture)",
                                   dept="; ".join(pis[pi].get("departments") or [])[:80], cs=False,
                                   title=(src.get("title") or "")[:200], q=q))
    return out
