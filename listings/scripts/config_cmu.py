"""CMU School of Computer Science department faculty listing slots -> URL eras (YYYYMMDD inclusive).

Departments use the input's codes: CSD, MLD, LTI, RI, HCII, S3D (ISR before 2022), CBD.
Program pages (Societal Computing, SE PhD), student, postdoc, project-staff and alumni pages are not used
(the 2016 RI site's fcode=4 and fcode=5 lists are postdocs and project staff). LTI's directory filters:
154/1 faculty (two pages), 154/200 adjunct, 154/2728 affiliated, 154/2729 visitors.
The SCS-wide directory's HTML (www.cs.cmu.edu/directory) is script-rendered; its JSON endpoint
(directory/api/v1/all.json, captured 2025-2026) is used per department, counting an entry for a
department only when the record itself names that department.
"""
D = "20160101", "20261231"

SLOTS = [
    # ---------------- CSD ----------------
    {"dept": "CSD", "slot": "CSD faculty", "kind": "main", "split_name_cells": True, "urls": [
        ("csd.cs.cmu.edu/directory/faculty", "20160101", "20191231"),
        ("csd.cmu.edu/directory/faculty", "20190101", "20231231"),
        ("csd.cmu.edu/people/faculty", "20230101", "20261231"),
        ("csd.cs.cmu.edu/people/faculty", "20240101", "20261231"),
    ]},
    {"dept": "CSD", "slot": "CSD faculty, page 2 (2024+ pagination)", "kind": "main", "urls": [
        ("csd.cmu.edu/people/faculty?page=1", *D),
        ("csd.cs.cmu.edu/people/faculty?page=1", *D),
    ]},
    {"dept": "CSD", "slot": "CSD faculty, page 3 (2024+ pagination)", "kind": "main", "urls": [
        ("csd.cmu.edu/people/faculty?page=2", *D),
        ("csd.cs.cmu.edu/people/faculty?page=2", *D),
    ]},
    # gap fill (2018 only): CSD's all-people directory; only entries with a faculty title count
    {"dept": "CSD", "slot": "CSD directory (all people)", "kind": "sub", "strict_title": True, "years": [2018],
     "split_name_cells": True, "years_note": "used only to fill 2018, when no CSD faculty listing was captured",
     "urls": [
        ("csd.cs.cmu.edu/directory/all", "20160101", "20191231"),
        ("csd.cmu.edu/directory/all", "20190101", "20231231"),
    ]},
    {"dept": "CSD", "slot": "CSD emeritus faculty", "kind": "emeritus", "urls": [
        ("csd.cmu.edu/people/emeritus-faculty", *D),
    ]},
    {"dept": "CSD", "slot": "CSD teaching faculty", "kind": "sub", "urls": [
        ("csd.cmu.edu/people/teaching-faculty", *D),
    ]},
    {"dept": "CSD", "slot": "CSD adjunct faculty", "kind": "sub", "urls": [
        ("csd.cmu.edu/people/adjunct-faculty", *D),
    ]},
    # ---------------- MLD ----------------
    {"dept": "MLD", "slot": "MLD core faculty", "kind": "main", "urls": [
        ("ml.cmu.edu/people/core-faculty.html", *D),
    ]},
    {"dept": "MLD", "slot": "MLD affiliated faculty", "kind": "sub", "urls": [
        ("ml.cmu.edu/people/affiliated-faculty.html", *D),
    ]},
    {"dept": "MLD", "slot": "MLD adjunct faculty", "kind": "sub", "urls": [
        ("ml.cmu.edu/people/adjunct-faculty.html", *D),
    ]},
    # ---------------- LTI ----------------
    {"dept": "LTI", "slot": "LTI faculty", "kind": "main", "urls": [
        ("lti.cs.cmu.edu/directory/all/154/1", "20160101", "20241231"),
        ("lti.cmu.edu/people/faculty/index.html", "20230101", "20261231"),
        ("lti.cs.cmu.edu/people/faculty", "20240101", "20261231"),
    ]},
    {"dept": "LTI", "slot": "LTI faculty, page 2", "kind": "main", "urls": [
        ("lti.cs.cmu.edu/directory/all/154/1?page=1", "20160101", "20241231"),
    ]},
    {"dept": "LTI", "slot": "LTI adjunct faculty", "kind": "sub", "urls": [
        ("lti.cs.cmu.edu/directory/all/154/200", *D),
    ]},
    {"dept": "LTI", "slot": "LTI affiliated faculty", "kind": "sub", "urls": [
        ("lti.cs.cmu.edu/directory/all/154/2728", *D),
    ]},
    {"dept": "LTI", "slot": "LTI visitors", "kind": "visiting", "urls": [
        ("lti.cs.cmu.edu/directory/all/154/2729", *D),
    ]},
    # ---------------- RI ----------------
    {"dept": "RI", "slot": "RI faculty", "kind": "main", "urls": [
        ("ri.cmu.edu/ri_people.html?fcode=1&menu_id=251&distype=detail&dis_type=detail&list_type=current&selected_letter=AZ", "20160101", "20171231"),
        ("ri.cmu.edu/people/faculty/", "20170101", "20261231"),
    ]},
    {"dept": "RI", "slot": "RI faculty, page 2", "kind": "main", "urls": [
        ("ri.cmu.edu/people/faculty/page/2/", *D),
    ]},
    {"dept": "RI", "slot": "RI faculty, page 3", "kind": "main", "urls": [
        ("ri.cmu.edu/people/faculty/page/3/", *D),
    ]},
    {"dept": "RI", "slot": "RI special faculty", "kind": "sub", "urls": [
        ("ri.cmu.edu/ri_people.html?fcode=3&menu_id=253&distype=detail&dis_type=detail&list_type=current&selected_letter=AZ", "20160101", "20171231"),
        ("ri.cmu.edu/people/special-faculty/", "20170101", "20261231"),
    ]},
    {"dept": "RI", "slot": "RI affiliated faculty", "kind": "sub", "urls": [
        ("ri.cmu.edu/ri_people.html?fcode=2&menu_id=252&distype=detail&dis_type=detail&list_type=current&selected_letter=AZ", "20160101", "20171231"),
        ("ri.cmu.edu/people/affiliated-faculty/", "20170101", "20261231"),
    ]},
    # ---------------- HCII ----------------
    # HCII entries: name heading, title line; some entries carry no title. Untitled entries count only
    # when the name is a heading after the page's h1 (the 'Name of Person' filter drop-down is plain text).
    {"dept": "HCII", "slot": "HCII faculty", "kind": "main", "untitled_ok": "heading",
     "regions": [{"start": r"^h1:Faculty$"}], "urls": [
        ("hcii.cmu.edu/people/faculty", *D),
    ]},
    {"dept": "HCII", "slot": "HCII affiliated faculty", "kind": "sub", "untitled_ok": "heading",
     "regions": [{"start": r"^h1:Affiliated Faculty$"}], "urls": [
        ("hcii.cmu.edu/people/affiliated-faculty", *D),
    ]},
    {"dept": "HCII", "slot": "HCII adjunct faculty", "kind": "sub", "untitled_ok": "heading",
     "regions": [{"start": r"^h1:Adjunct Faculty$"}], "urls": [
        ("hcii.cmu.edu/people/adjunct-faculty", *D),
    ]},
    {"dept": "HCII", "slot": "HCII special faculty", "kind": "sub", "urls": [
        ("hcii.cmu.edu/people/special-faculty", *D),
        ("hcii.cmu.edu/people/special-faculty-and-postdocs", *D),
    ]},
    # ---------------- S3D (ISR before 2022) ----------------
    # the faculty index lists 'Dr. Name' headings + 'Read full bio' under h1 sections (Core Faculty, ...)
    {"dept": "S3D", "slot": "S3D/ISR faculty index", "kind": "main", "untitled_ok": "heading",
     "regions": [{"start": r"^h1:Core Faculty$", "end": r"^h1:Post ?[Dd]ocs"}], "urls": [
        ("isri.cmu.edu/people/faculty-index.html", "20160101", "20221231"),
        ("s3d.cmu.edu/people/faculty-index.html", "20220101", "20261231"),
    ]},
    {"dept": "S3D", "slot": "S3D/ISR core faculty", "kind": "main", "urls": [
        ("isri.cmu.edu/people/core-faculty.html", *D),
        ("s3d.cmu.edu/people/core-faculty.html", *D),
    ]},
    {"dept": "S3D", "slot": "S3D/ISR affiliated faculty", "kind": "sub", "urls": [
        ("isri.cmu.edu/people/affiliated-faculty.html", *D),
        ("s3d.cmu.edu/people/affiliated-faculty.html", *D),
    ]},
    {"dept": "S3D", "slot": "S3D/ISR other faculty", "kind": "sub", "urls": [
        ("isri.cmu.edu/people/other-faculty.html", *D),
        ("s3d.cmu.edu/people/other-faculty.html", *D),
    ]},
    # ---------------- CBD ----------------
    {"dept": "CBD", "slot": "CBD voting faculty", "kind": "main", "urls": [
        ("www.cbd.cmu.edu/directory/faculty/voting-faculty/", "20160101", "20211231"),
        ("cbd.cmu.edu/people/voting-faculty.html", "20210101", "20261231"),
        ("www.cmu.edu/cbd/people/voting-faculty.html", "20250101", "20261231"),
    ]},
    {"dept": "CBD", "slot": "CBD faculty directory (all)", "kind": "main", "urls": [
        ("www.cbd.cmu.edu/directory/faculty/", *D),
    ]},
    {"dept": "CBD", "slot": "CBD affiliated faculty", "kind": "sub", "urls": [
        ("www.cbd.cmu.edu/directory/faculty/affiliated-faculty/", "20160101", "20211231"),
        ("cbd.cmu.edu/people/affiliated-faculty.html", "20210101", "20261231"),
        ("www.cmu.edu/cbd/people/affiliated-faculty.html", "20250101", "20261231"),
    ]},
    {"dept": "CBD", "slot": "CBD adjunct faculty", "kind": "sub", "urls": [
        ("www.cbd.cmu.edu/directory/faculty/adjunct-faculty/", "20160101", "20211231"),
        ("cbd.cmu.edu/people/adjunct-faculty.html", "20210101", "20261231"),
        ("www.cmu.edu/cbd/people/adjunct-faculty.html", "20250101", "20261231"),
    ]},
    {"dept": "CBD", "slot": "CBD visiting faculty", "kind": "visiting", "urls": [
        ("www.cbd.cmu.edu/directory/faculty/visiting-faculty/", "20160101", "20211231"),
        ("cbd.cmu.edu/people/visiting-faculty.html", "20210101", "20261231"),
        ("www.cmu.edu/cbd/people/visiting-faculty.html", "20250101", "20261231"),
    ]},
]

# SCS-wide directory API (script data behind www.cs.cmu.edu/directory; Wayback holds it for 2025-2026 only).
# One slot per department: an entry counts for a department only when its own record names that department.
API = "www.cs.cmu.edu/directory/api/v1/all.json"
for _d, _rx in [("CSD", r"Computer Science Department"), ("MLD", r"Machine Learning Department"),
                ("LTI", r"Language Technologies Institute"), ("RI", r"Robotics Institute"),
                ("HCII", r"Human-Computer Interaction Institute"),
                ("S3D", r"Software and Societal Systems Department|Institute for Software Research"),
                ("CBD", r"Computational Biology Department")]:
    SLOTS.append({"dept": _d, "slot": f"SCS directory API ({_d} entries)", "kind": "sub", "quote_require": _rx,
                  "urls": [(API, *D)]})

# ---------------- home departments outside SCS (gap fill, all years) ----------------
# Rows from these carry listing = "home department faculty list" and need a faculty title in the entry.
H = "home department faculty list"
SLOTS += [
    {"dept": "ECE", "slot": "ECE faculty (home department)", "kind": "main", "listing_label": H, "urls": [
        ("ece.cmu.edu/directory/department/faculty/index.html", "20160101", "20181231"),
        ("ece.cmu.edu/directory/faculty.html", "20180101", "20261231"),
    ]},
    {"dept": "ECE", "slot": "ECE courtesy faculty (home department)", "kind": "sub", "listing_label": H, "urls": [
        ("ece.cmu.edu/directory/courtesy-faculty.html", *D)]},
    {"dept": "ECE", "slot": "ECE adjunct faculty (home department)", "kind": "sub", "listing_label": H, "urls": [
        ("ece.cmu.edu/directory/adjunct-faculty.html", *D)]},
    {"dept": "MechE", "slot": "MechE faculty (home department)", "kind": "main", "listing_label": H, "urls": [
        ("cmu.edu/me/people/faculty.html", "20160101", "20181231"),
        ("meche.engineering.cmu.edu/directory/index.html", "20190101", "20261231"),
    ]},
    {"dept": "Chemistry", "slot": "Chemistry faculty (home department)", "kind": "main", "listing_label": H, "urls": [
        ("cmu.edu/chemistry/people/faculty/index.html", *D),
        ("cmu.edu/chemistry/people/faculty", *D),
    ]},
    {"dept": "Philosophy", "slot": "Philosophy faculty (home department)", "kind": "main", "listing_label": H, "urls": [
        ("cmu.edu/dietrich/philosophy/people/faculty/index.html", *D),
        ("cmu.edu/dietrich/philosophy/people/faculty/core-faculty/index.html", *D),
        ("cmu.edu/dietrich/philosophy/people/faculty", *D),
    ]},
]

DEPT_CODES = {d: [d] for d in ("CSD", "MLD", "LTI", "RI", "HCII", "S3D", "CBD")}


def relevant_slots(pi, slot_name, slot):
    return slot["dept"] in pi.get("departments", [])

# Appointment-period review, 2026-10-26: the CMU undergraduate catalog's faculty lists (coursecatalog.web.cmu.edu college and
# department pages) were captured into captures.sqlite (plan slots "Catalog faculty list (...)") and tried as yearly slots,
# then withdrawn: the catalog is stale (Fienberg, d. 2016, listed in 2018; Smola, Park listed years after leaving), so a
# catalog capture does not prove its capture year. The slots are deliberately not in SLOTS; their plan rows are ignored.
