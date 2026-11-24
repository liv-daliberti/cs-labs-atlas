"""Freeze the profile-page targets for one school's gap PI-years.

usage: make_profile_targets.py berkeley
Berkeley: 2018 (no EECS faculty list captured) for every PI listed in 2017 or 2019, via the EECS faculty
homepage www2.eecs.berkeley.edu/Faculty/Homepages/<id>.html; ids are read from the links of the captured
EECS faculty lists (scripts/berkeley_homepage_ids.json).
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), 'tools'))
import atlas_paths as P  # noqa: E402  (every path in one place)


def berkeley():
    cov = json.load(open(P.data("coverage.json", "berkeley")))
    ids = json.load(open(os.path.join(HERE, "berkeley_homepage_ids.json")))
    out = []
    for pi, c in sorted(cov.items()):
        ys = set(c["all_years_listed_any_department"])
        if 2018 in ys or not (2017 in ys or 2019 in ys) or pi not in ids:
            continue
        hid = ids[pi]
        out.append({"pi": pi, "dept": "EECS", "detail": f"EECS faculty homepage {hid}",
                    "cdx": ["eecs.berkeley.edu/Faculty/Homepages/", "2018", "2018"],
                    "match": r"eecs\.berkeley\.edu(:80)?/Faculty/Homepages/" + hid.replace(".", r"\.") + r"$",
                    "years": [2018]})
    return out


def _gap_years(school, pi):
    cov = json.load(open(P.data("coverage.json", school)))
    return [y for y in range(2016, 2027) if y not in set(cov[pi]["all_years_listed_any_department"])]


def epfl():
    """people.epfl.ch/<handle> (EPFL's directory profile, which states the title) for every gap year of the
    PIs homed outside IC (hierarchy/home-departments.json gives the handle) and of IC PIs never listed."""
    home = json.load(open(P.data("home-departments.json")))
    pis = {p["pi"] for p in json.load(open(P.data("listings-input.json", "epfl")))["pis"]}
    out = []
    for h in home:
        if h["school"] != "epfl" or h["name"] not in pis:
            continue
        url = (h.get("evidence") or {}).get("url") or ""
        if "people.epfl.ch/" not in url:
            continue
        handle = url.split("people.epfl.ch/")[1].strip("/")
        ys = [y for y in _gap_years("epfl", h["name"]) if y >= 2019]  # profiles state a title only from 2019
        if not ys:
            continue
        school = h["home_department"].split("(")[-1].split(")")[0] if "(" in h["home_department"] else "EPFL"
        out.append({"pi": h["name"], "dept": school, "detail": f"people.epfl.ch/{handle}",
                    "cdx": [f"people.epfl.ch/{handle}", "2016", "2026"],
                    "match": r"people\.epfl\.ch(:80)?/" + handle.replace(".", r"\.") + r"/?(\?.*)?$",
                    "years": ys})
    # PIs never found on any listing and absent from home-departments.json: guessed first.last handle
    import unicodedata
    have = {t["pi"] for t in out}
    summ = json.load(open(P.data("listings-summary.json", "epfl")))
    for name in summ["pis_never_found"]:
        if name in have or name == "Ken Holstein":  # Ken Holstein is a CMU person (input error)
            continue
        toks = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().replace("'", "").split()
        handle = f"{toks[0]}.{toks[-1]}"
        out.append({"pi": name, "dept": "EPFL", "detail": f"people.epfl.ch/{handle}",
                    "cdx": [f"people.epfl.ch/{handle}", "2016", "2026"],
                    "match": r"people\.epfl\.ch(:80)?/" + handle.replace(".", r"\.") + r"/?(\?.*)?$",
                    "years": list(range(2019, 2027))})
    return out


CMU_PAGES = {  # department profile pages of the CMU PIs the coordinator named (one CDX prefix each)
    "Andre Platzer": [("CSD", "csd.cs.cmu.edu/people/faculty/andre-platzer")],
    "Gauri Joshi": [("ECE", "ece.cmu.edu/directory/department/faculty/j/gauri_joshi_10218.html"),
                    ("ECE", "ece.cmu.edu/directory/bios/joshi-gauri.html")],
    "Onur Mutlu": [("ECE", "ece.cmu.edu/directory/department/faculty/m/onur_mutlu_4195.html"),
                   ("ECE", "ece.cmu.edu/directory/bios/mutlu-onur.html")],
    "Anthony Rowe": [("ECE", "ece.cmu.edu/directory/department/faculty/r/anthony_rowe_964.html"),
                     ("ECE", "ece.cmu.edu/directory/bios/rowe-anthony.html")],
    "Jeremy Avigad": [("Philosophy", "cmu.edu/dietrich/philosophy/people/faculty/jeremy-avigad.html"),
                      ("Philosophy", "cmu.edu/dietrich/philosophy/people/faculty/core-faculty/avigad.html")],
    "Olexandr Isayev": [("Chemistry", "cmu.edu/chemistry/people/faculty/isayev.html")],
    "Carmel S Majidi": [("MechE", "meche.engineering.cmu.edu/directory/bios/majidi-carmel.html"),
                        ("MechE", "cmu.edu/me/people/majidi.html")],
    "Aaron M Johnson": [("MechE", "meche.engineering.cmu.edu/directory/bios/johnson-aaron.html"),
                        ("MechE", "cmu.edu/me/people/johnson.html")],
}


def cmu():
    out = []
    for pi, pages in CMU_PAGES.items():
        ys = _gap_years("cmu", pi)
        if pi == "Andre Platzer":
            ys = [y for y in ys if y <= 2022]  # at KIT from 2022
        if not ys:
            continue
        for dept, url in pages:
            out.append({"pi": pi, "dept": dept, "detail": url, "cdx": [url, "2016", "2026"],
                        "match": re.escape(url.split("/", 1)[1]) + r"/?(\?.*)?$", "years": ys})
    return out


if __name__ == "__main__":
    s = sys.argv[1]
    t = globals()[s]()
    json.dump(t, open(os.path.join(HERE, f"profile_targets_{s}.json"), "w"), indent=1)
    print(s, len(t), "targets")
