"""EPFL IC (School of Computer and Communication Sciences) faculty listing slots.

2016-2019: ic.epfl.ch/professors ('Professors and Senior Scientists': names under section headings
Professors / Courtesy Appointments / Senior Scientists / External adjunct Professors / Honorary
Professors, with no per-person title; a verified region makes those untitled entries count); the
French page ic.epfl.ch/professeurs (Professeurs et MER) fills years the English page lacks (2018).
2019-2026: www.epfl.ch/schools/ic/about/faculty-members/ (name, title, e-mail; sections Professors /
External adjunct Professors / Emeritus Professors / Senior Scientists / visiting); some entries,
e.g. emeriti, carry no title, so the listing region (h1 'Professors' to h3 'News') is verified too.
EDIC thesis-director pages are a doctoral-program list, not a faculty listing, and are not used.
"""
SLOTS = [
    {"dept": "IC", "slot": "IC professors and senior scientists", "kind": "main", "untitled_ok": True,
     "regions": [
        # 2016-2019 English / French pages: from the h1 to the sidebar that follows the Honorary list
        {"url": r"ic\.epfl\.ch/(professors|professeurs)",
         "start": r"^h1:(Professors and Senior Scientists|Professeurs et MER|Professeurs et collaborateurs scientifiques)$",
         "end": r"^b:(Deanship|D[ée]canat|Management Committee|Comit[ée] de direction|Professeurs invit[ée]s|Visiting Professors)$|^h4:Wiki"},
        # 2019-2026 page: from the h1 'Professors' to the h3 'News' that follows the listing
        {"url": r"epfl\.ch/schools/ic/about/faculty-members", "start": r"^h1:Professors$", "end": r"^h[1-3]:News$"},
     ],
     "urls": [
        ("ic.epfl.ch/professors", "20160101", "20191231"),
        ("ic.epfl.ch/professeurs", "20160101", "20191231"),  # French version; the only 2018 capture
        ("www.epfl.ch/schools/ic/about/faculty-members/", "20190101", "20261231"),
    ]},
]

# ---------------- home schools outside IC (gap fill, all years) ----------------
# Rows from these carry listing = "home department faculty list" and need a faculty title in the entry.
H = "home department faculty list"
D = "20160101", "20261231"
W = "www.epfl.ch/schools/"
SLOTS += [
    {"dept": "STI", "slot": "STI faculty (home school)", "kind": "main", "listing_label": H, "urls": [
        ("sti.epfl.ch/faculty", "20160101", "20181231"),
        ("sti.epfl.ch/faculte", "20160101", "20181231"),
        ("sti.epfl.ch/faculty-members", "20230101", "20261231"),
        ("sti.epfl.ch/fr/corps-professoral", "20230101", "20261231"),
    ]},
    {"dept": "STI", "slot": "STI-IEM faculty (home institute)", "kind": "sub", "listing_label": H, "urls": [
        ("sti.epfl.ch/iem/faculty-members", *D)]},
    {"dept": "STI", "slot": "STI-IGM faculty (home institute)", "kind": "sub", "listing_label": H, "urls": [
        ("sti.epfl.ch/igm/faculty-members", *D)]},
    {"dept": "STI", "slot": "STI emeriti (home school)", "kind": "emeritus", "listing_label": H, "urls": [
        ("sti.epfl.ch/emeriti-professors", *D)]},
    {"dept": "ENAC", "slot": "ENAC professors (home school)", "kind": "main", "listing_label": H, "urls": [
        ("enac.epfl.ch/en/enac-professors", "20160101", "20181231"),
        ("enac.epfl.ch/professeurs_et_mer", "20160101", "20181231"),
        ("enac.epfl.ch/faculty", "20160101", "20181231"),
        (W + "enac/about/organization/professors-and-senior-scientists/full-professors", "20190101", "20261231"),
    ]},
    {"dept": "ENAC", "slot": "ENAC associate professors (home school)", "kind": "sub", "listing_label": H, "urls": [
        (W + "enac/about/organization/professors-and-senior-scientists/associate-professor", *D)]},
    {"dept": "ENAC", "slot": "ENAC tenure-track professors (home school)", "kind": "sub", "listing_label": H, "urls": [
        (W + "enac/about/organization/professors-and-senior-scientists/tenure-track-assistant-professor", *D)]},
    {"dept": "ENAC", "slot": "ENAC adjunct professors (home school)", "kind": "sub", "listing_label": H, "urls": [
        (W + "enac/about/organization/professors-and-senior-scientists/adjunct-professors", *D)]},
    {"dept": "ENAC", "slot": "ENAC professors and senior scientists (home school)", "kind": "sub", "listing_label": H, "urls": [
        (W + "enac/about/organization/professors-and-senior-scientists", *D)]},
    {"dept": "SB", "slot": "SB faculty (home school)", "kind": "main", "listing_label": H, "urls": [
        (W + "sb/about/faculty", *D),
        (W + "sb/fr/a-propos-de-la-sb/professeurs", *D),
    ]},
    {"dept": "SB", "slot": "SB emeritus professors (home school)", "kind": "emeritus", "listing_label": H, "urls": [
        (W + "sb/about/emeritus-professors", *D)]},
    {"dept": "SV", "slot": "SV professors (home school)", "kind": "main", "listing_label": H, "urls": [
        ("sv.epfl.ch/faculty", "20160101", "20181231"),
        ("sv.epfl.ch/professeurs", "20160101", "20191231"),
        (W + "sv/school-of-life-sciences/professors", "20190101", "20261231"),
        (W + "sv/fr/science-de-la-vie/professeurs-de-la-faculte", "20190101", "20261231"),
    ]},
    {"dept": "CDM", "slot": "CDM faculty (home college)", "kind": "main", "listing_label": H, "urls": [
        (W + "cdm/college-of-management-of-technology/faculty", *D),
        (W + "cdm/fr/college-du-management-dela-technologie/professeurs", *D),
    ]},
    {"dept": "CDM", "slot": "CDM-SFI faculty (home institute)", "kind": "sub", "listing_label": H, "urls": [
        (W + "cdm/college-of-management-of-technology/swiss-finance-institute/faculty-members", *D)]},
    {"dept": "CDM", "slot": "CDM-MTEI faculty (home institute)", "kind": "sub", "listing_label": H, "urls": [
        (W + "cdm/college-of-management-of-technology/management-of-technology-institute/faculty-members", *D)]},
]

DEPT_CODES = {}


def relevant_slots(pi, slot_name, slot):
    return True
