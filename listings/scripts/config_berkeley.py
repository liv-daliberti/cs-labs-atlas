"""Berkeley EECS faculty listing slots -> URL eras (YYYYMMDD inclusive).

Each slot is one logical listing. Its URLs are tried in priority order within their era; per half-year the
first URL with a usable capture wins. CDX `url` matching ignores the www/www2 host prefix.
The .shtml lists (2016) were replaced by .html lists in 2019; Wayback holds no CS-specific list for
2017-2018, so the all-EECS lists are captured too. www.eecs.berkeley.edu/people/faculty was checked and
is a landing page (links to these lists, award captions), not a listing, so it is not used.
"""
D = "20160101", "20261231"
B = "www2.eecs.berkeley.edu/Faculty/Lists/"

SLOTS = [
    {"dept": "EECS", "slot": "EECS CS current faculty", "kind": "main", "urls": [
        (B + "CS/list.shtml", *D),
        (B + "CS/faculty.html", *D),
        (B + "CS/", *D),
        (B + "CS/list.html", *D),
    ]},
    {"dept": "EECS", "slot": "EECS current faculty (all EECS)", "kind": "main", "urls": [
        (B + "list.shtml", *D),
        (B + "faculty.html", *D),
        (B + "list.html", *D),
        (B + "faculty.shtml", *D),
    ]},
    {"dept": "EECS", "slot": "EECS CS faculty emeriti", "kind": "emeritus", "urls": [
        (B + "CS/emeritus.shtml", *D),
        (B + "CS/emeritus.html", *D),
    ]},
    {"dept": "EECS", "slot": "EECS faculty emeriti (all EECS)", "kind": "emeritus", "urls": [
        (B + "emeritus.shtml", *D),
        (B + "emeritus.html", *D),
    ]},
    {"dept": "EECS", "slot": "EECS CS visiting faculty", "kind": "visiting", "untitled_ok": True,
     # 2016 .shtml entries carry no title: the page heading ('CS Spring 2016 Visiting Faculty') is the listing
     "regions": [{"url": r"\.shtml$", "start": r"^h1:(CS |EECS )?(Spring |Fall |Summer )?(\d{4} )?Visiting Faculty$"}],
     "urls": [
        (B + "CS/visiting.shtml", *D),
        (B + "CS/visiting.html", *D),
        (B + "visiting.shtml", *D),
        (B + "visiting.html", *D),
    ]},
    {"dept": "EECS", "slot": "EECS teaching faculty", "kind": "sub", "urls": [
        (B + "teaching.html", *D),
    ]},
    {"dept": "EECS", "slot": "EECS new faculty", "kind": "sub", "urls": [
        (B + "CS/new.html", *D),
        (B + "new.html", *D),
    ]},
]

DEPT_CODES = {"EECS": ["EECS"]}


def relevant_slots(pi, slot_name, slot):
    return True

# ---------------- home departments of the CS-related additions (appointment-period review, 2026-10-26) ----------------
# Owner decision 2026-10-22 widened scope to CS-related faculty in any department; these are those PIs' home-department
# faculty lists, in their URL eras (CDX discovery 2026-10-26). Input PIs added for them carry drop_emeritus_rows, so an
# emeritus or visiting entry makes no row (emeritus years are not appointment years).
SLOTS += [
    {"dept": "ME", "slot": "ME faculty", "kind": "main", "urls": [
        ("me.berkeley.edu/people/faculty", "20160101", "20191231"),
        ("me.berkeley.edu/people_type/faculty", "20200101", "20261231"),
        ("me.berkeley.edu/people_type/core", "20200101", "20261231"),
        ("me.berkeley.edu/people", "20200101", "20261231"),
    ]},
    {"dept": "ME", "slot": "ME faculty, page 2", "kind": "main", "urls": [("me.berkeley.edu/people_type/faculty/page/2", *D)]},
    {"dept": "ME", "slot": "ME faculty, page 3", "kind": "main", "urls": [("me.berkeley.edu/people_type/faculty/page/3", *D)]},
    {"dept": "ME", "slot": "ME faculty, page 4", "kind": "main", "urls": [("me.berkeley.edu/people_type/faculty/page/4", *D)]},
    {"dept": "IEOR", "slot": "IEOR faculty", "kind": "main", "urls": [
        ("ieor.berkeley.edu/people/faculty", "20160101", "20181231"),
        ("ieor.berkeley.edu/faculty", "20190101", "20261231"),
        ("ieor.berkeley.edu/people", *D),
    ]},
    {"dept": "Mathematics", "slot": "Mathematics faculty", "kind": "main", "urls": [("math.berkeley.edu/people/faculty", *D)]},
    {"dept": "Statistics", "slot": "Statistics faculty", "kind": "main", "urls": [("statistics.berkeley.edu/people/faculty", *D)]},
    {"dept": "CEE", "slot": "CEE faculty", "kind": "main", "urls": [("ce.berkeley.edu/people/faculty", *D)]},
    {"dept": "Education", "slot": "Education faculty", "kind": "main", "urls": [
        ("gse.berkeley.edu/faculty", "20160101", "20181231"),
        ("gse.berkeley.edu/people/faculty", "20190101", "20221231"),
        ("bse.berkeley.edu/people/faculty", "20220101", "20261231"),
    ]},
    {"dept": "Linguistics", "slot": "Linguistics faculty", "kind": "main", "urls": [("lx.berkeley.edu/people/faculty", *D)]},
    {"dept": "Philosophy", "slot": "Philosophy faculty", "kind": "main", "urls": [("philosophy.berkeley.edu/people/faculty", *D)]},
    {"dept": "ISchool", "slot": "School of Information faculty", "kind": "main", "urls": [
        ("ischool.berkeley.edu/people/faculty", "20160101", "20171231"),
        ("ischool.berkeley.edu/people", *D),
    ]},
    {"dept": "ChemE", "slot": "Chemical and Biomolecular Engineering faculty", "kind": "main", "urls": [
        ("chemistry.berkeley.edu/faculty/cbe-directory", *D)]},
    {"dept": "ESPM", "slot": "ESPM people", "kind": "main", "urls": [("ourenvironment.berkeley.edu/people", *D)]},
    {"dept": "ERG", "slot": "ERG faculty", "kind": "main", "urls": [
        ("erg.berkeley.edu/people-at-erg/faculty", *D),
        ("erg.berkeley.edu/people-at-erg/core-faculty", *D),
    ]},
    {"dept": "Optometry", "slot": "Optometry and Vision Science faculty", "kind": "main", "urls": [
        ("optometry.berkeley.edu/faculty/full-time-faculty", "20160101", "20201231"),
        ("optometry.berkeley.edu/people", *D),
    ]},
    {"dept": "Neuroscience", "slot": "Neuroscience faculty", "kind": "main", "urls": [("neuroscience.berkeley.edu/faculty", *D)]},
    {"dept": "IB", "slot": "Integrative Biology directory", "kind": "main", "urls": [("ib.berkeley.edu/people/directory", *D)]},
    {"dept": "Bioengineering", "slot": "Bioengineering people", "kind": "main", "urls": [("bioeng.berkeley.edu/people", *D)]},
]
DEPT_CODES.update({d: [d] for d in ("ME", "IEOR", "Mathematics", "Statistics", "CEE", "Education", "Linguistics", "Philosophy",
                                    "ISchool", "ChemE", "ESPM", "ERG", "Optometry", "Neuroscience", "IB", "Bioengineering", "Physics")})

# the home-department slots above make no row for emeritus / visiting / 'Professor of the Graduate School' entries
for _s in SLOTS:
    if _s["dept"] != "EECS":
        _s["drop_emeritus"] = True
