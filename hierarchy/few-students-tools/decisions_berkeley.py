"""Berkeley few-students decisions (25 PIs), 2026-10-21/22.

Sources (all stored in hierarchy/berkeley/few-students-captures.sqlite): EECS dissertations-by-faculty pages, EECS
technical-report pages ("Advisors: <PI>" + @mastersthesis/@phdthesis BibTeX), PI group pages and their Wayback captures,
PI CVs. Every row is built with fsev (exact-substring + all-name-tokens checks).
Excluded on purpose: students a page lists as co-advised at another institution (Pierson's Cornell Tech students
co-advised with Nikhil Garg; Fletcher's UIUC-era students), collaborators/"friends of the family" lists, visiting
students from other universities.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fsev  # noqa: E402

B = "berkeley"
WB = "https://web.archive.org/web/"
DISS = "https://www2.eecs.berkeley.edu/Pubs/Dissertations/Faculty/"
TRP = "https://www2.eecs.berkeley.edu/Pubs/TechRpts/"
D = {}


def diss(slug, pi_on_page):
    return fsev.eecs_dissertations(DISS + slug + ".html", "Ph.D. Dissertations - " + pi_on_page)


def tr(name, rid, pi, role="masters"):
    """EECS tech report EECS-<year>-<n>: quote 'Advisors: ...<PI>... BibTeX citation: @mastersthesis{..., Author= {...}'."""
    y = int(rid.split("-")[0])
    url = f"{TRP}{y}/EECS-{rid}.html"
    pat = (r"Advisors?: [^@]{0,120}?" + re.escape(pi) + r"[^@]{0,80}? BibTeX citation: @(?:masters|phd)thesis\{[^}]*?Author= \{[^}]*\}")
    kind = "Ph.D. dissertation" if role == "phd" else "master's thesis"
    return fsev.S(B, name, role, [y, y], url, pattern=pat, note=f"EECS technical report EECS-{rid} ({kind}, {y}); advisor {pi}")


def L(name, role, years, src, start, end, note=None, max_span=1500, after=None):
    return fsev.S(B, name, role, years, src, start=start, end=end, note=note, max_span=max_span, after=after)


# ============================================================ Jonathan Bachrach
D["Jonathan Bachrach"] = dict(
    students=diss("bachrach", "Jonathan Bachrach") + [tr("Adam Izraelevitz", "2019-168", "Jonathan Bachrach", "phd")],
    lab_note="Bachrach (EECS adjunct/research faculty, Chisel/FIRRTL hardware-construction work in the ASPIRE/ADEPT/BAR labs) has no "
             "group page; his advisees are known from the EECS dissertations-by-faculty page (five Ph.D.s 2017-2021, several "
             "co-advised with Krste Asanovic).",
    notes="EECS profile has no homepage link; TechRpts-by-faculty gives one more confirming source (Izraelevitz). No group page or CV found.")

# ============================================================ Phillip Colella
D["Phillip Colella"] = dict(
    students=diss("colella", "Phillip Colella"),
    lab_note="Colella is a LBNL senior scientist (ANAG) and EECS professor in residence; his Berkeley EECS advising record is one "
             "2018 dissertation (Brian Van Straalen, already held). Small by nature, not a records gap.",
    notes="Searched: EECS dissertations page (only Van Straalen 2016+), EECS tech reports by faculty (no 2016+ entries), EECS "
          "profile (no homepage link). Nothing more found; his group lives at LBNL (staff, not students).")

# ============================================================ John DeNero
D["John DeNero"] = dict(
    students=diss("denero", "John DeNero") + [tr("Sumukh Sridhara", "2017-187", "John DeNero")],
    lab_note="DeNero is a teaching professor (CS 61A/Data 8); his homepage has said 'Currently I am not taking new students' "
             "since at least 2019. Advising record: one Ph.D. (Ibraheem 2022, held) and one master's thesis (2017).",
    notes="Searched denero.org live and Wayback 2017/2019/2021/2023 (no student list), EECS dissertations and tech reports. "
          "A 2023 master's thesis on his TR listing (Brian Yu) names Kurt Keutzer as advisor and was not counted.")

# ============================================================ Hany Farid
HF = "https://farid.berkeley.edu/"  # -> hfarid.org
HFCV = "https://hfarid.org/downloads/cv.pdf"
D["Hany Farid"] = dict(
    students=diss("hfarid", "Hany Farid") + [
        L("Sarah Barrington", "phd", [2026, 2026], HFCV, "C URRENT S TUDENTS", "Sarah Barrington, Ph.D. advisor"),
        L("Josh Bucci", "member", [2026, 2026], HF, "GROUP", "GROUP Sarah Barrington | Josh Bucci",
          note="listed under GROUP on the homepage; role not stated"),
        L("Justin Norman", "phd", [2026, 2026], HFCV, "F ORMER S TUDENTS", "Justin Norman (2026), Ph.D. advisor"),
        L("Sophie Nightingale", "postdoc", [2020, 2020], HFCV, "F ORMER S TUDENTS", "Sophie Nightingale (2020), postdoctoral advisor",
          note="postdoc completed 2020, after Farid moved to Berkeley in 2019"),
        L("Simran Kaur", "undergraduate", [2021, 2021], HFCV, "F ORMER S TUDENTS", "Simran Kaur, (2021), Haas Scholar, (UC Berkeley)"),
        L("Vibhor Sehgal", "masters", [2021, 2021], HF, "ALUMNI", "Vibhor Sehgal (M.S., 2021)", max_span=2500),
        L("Elliott Waissbluth", "masters", [2022, 2022], HF, "ALUMNI", "Elliott Waissbluth (M.S., 2022)", max_span=2500),
    ],
    lab_note="Farid joined Berkeley (I School + EECS) in 2019 from Dartmouth; his homepage GROUP lists two current members and an "
             "ALUMNI list spanning both institutions. Only Berkeley-era entries (completed 2020 or later, or explicitly UC Berkeley) "
             "are counted.",
    notes="Sources: hfarid.org homepage (GROUP, ALUMNI), CV (CURRENT/FORMER STUDENTS), EECS dissertations page. Excluded: "
          "Marc Faddoul (M.S., 2019) and Priyanka Singh (postdoc, 2019), which could be Dartmouth or Berkeley; Matyas Bohacek "
          "(undergraduate advisee, a Stanford student). The 2026 CV also lists a Dartmouth professorship from 2026.")

# ============================================================ Marti Hearst
D["Marti Hearst"] = dict(
    students=diss("hearst", "Marti Hearst"),
    lab_note="Hearst (I School + EECS) has no group page; her EECS-supervised Ph.D.s 2016+ come from the dissertations page "
             "(five, two already held). I School Ph.D. advisees are not on any page found.",
    notes="Searched homepage (live + Wayback 2016/2018/2020/2022), bio page and CV (vitae.pdf, Wayback 2025; no advising "
          "section), EECS tech reports (no 2016+ entries).")

# ============================================================ Nilah Ioannidis
PIERSON_G = "https://people.eecs.berkeley.edu/~emmapierson/group.html"
D["Nilah Ioannidis"] = dict(
    students=diss("nilah", "Nilah Ioannidis") + [
        tr("Arbaaz Muslim", "2023-110", "Nilah Ioannidis"),
        tr("Connie Huang", "2023-83", "Nilah Ioannidis"),
        tr("Parth Baokar", "2022-120", "Nilah Ioannidis"),
        L("Marçal Comajoan Cara", "phd", [2026, 2026], PIERSON_G, "Current PhD students and postdocs",
          "Marçal Comajoan Cara (PhD student; co-advised with Nilah Ioannidis)", note="co-advised with Emma Pierson"),
    ],
    lab_note="Ioannidis (EECS + CCB, at Berkeley since 2019) has no group page that could be found; advisees come from EECS "
             "dissertations (2), EECS master's theses (3) and Emma Pierson's group page (one co-advised Ph.D. student).",
    notes="Her EECS profile's homepage link is a VC-Research expertise page with no people. The CCB people directory lists "
          "students without advisors on its index pages (not crawled further).")

# ============================================================ John D. Kubiatowicz
FPSG = "https://cwfletcher.github.io/fpsg"
D["John D. Kubiatowicz"] = dict(
    students=diss("kubiatowicz", "John D. Kubiatowicz") + [
        tr("Justin Kalloor", "2024-78", "John D. Kubiatowicz"),
        tr("Mathias Weiden", "2023-84", "John D. Kubiatowicz"),
        tr("Hanming Lu", "2022-267", "John D. Kubiatowicz"),
        tr("Nathan Pemberton", "2019-154", "John D. Kubiatowicz"),
        L("Alex Thomas", "phd", [2024, 2026], FPSG, "PhD Hannah Leung", "Alex Thomas (2024-present; co-advised by John Kubiatowicz)",
          note="listed on Christopher Fletcher's group page as co-advised by Kubiatowicz"),
    ],
    lab_note="Kubiatowicz's homepage and resume list no students; his 2016+ advisees come from the EECS dissertations page "
             "(Maas 2017 plus the two held), four master's theses with him as advisor, and one co-advised Ph.D. on Fletcher's page.",
    notes="Resume (resume.pdf) has no advising section. Pemberton's 2019 master's thesis is co-advised with Randy Katz.")

# ============================================================ Jennifer Listgarten
LG = "http://www.jennifer.listgarten.com/group.html"
LG19 = WB + "20190723173536id_/http://jennifer.listgarten.com/group.html"
LG21 = WB + "20210425225821id_/http://www.jennifer.listgarten.com/group.html"
LG22 = WB + "20221127013021id_/http://www.jennifer.listgarten.com/group.html"
LG23 = WB + "20231205214154id_/http://jennifer.listgarten.com/group.html"
LG24 = WB + "20241128200031id_/http://www.jennifer.listgarten.com/group.html"
LG25 = WB + "20251014223627id_/http://jennifer.listgarten.com/group.html"
D["Jennifer Listgarten"] = dict(
    students=diss("listgarten", "Jennifer Listgarten") + [
        tr("Brian Yao", "2022-15", "Jennifer Listgarten"),
        L("Hanlun Jiang", "postdoc", [2023, 2026], LG, "Postdocs", "Postdocs Hanlun Jiang"),
        L("Nico Ayala", "phd", [2025, 2026], LG, "PhD students", "Nico Ayala (PhD student, CCB)"),
        L("James Bowden", "phd", [2023, 2026], LG, "PhD students", "James Bowden (PhD student, EECS co-advised with Sergey Levine)"),
        L("Vincent Chim", "phd", [2024, 2026], LG, "PhD students", "Vincent Chim (PhD student, Chemistry, co-advised with Alanna Schepartz)"),
        L("Ishan Gaur", "phd", [2025, 2026], LG, "PhD students", "Ishan Gaur (PhD student, EECS)"),
        L("Mohammed Ehab", "phd", [2026, 2026], LG, "PhD students", "Mohammed Ehab (PhD student, EECS)"),
        L("Theo Sternlieb", "phd", [2025, 2026], LG, "PhD students", "Theo Sternlieb (PhD student, EECS)"),
        L("Yifan Wang", "undergraduate", [2026, 2026], LG, "Undergraduates", "Yifan Wang (EECS undergraduate)"),
        L("Prastik Mohanraj", "phd", [2025, 2025], LG25, "PhD students", "Prastik Mohanraj (PhD student, BioE)"),
        L("Saket Budhia", "undergraduate", [2025, 2025], LG25, "Undergraduates", "Saket Budhia (EECS+Bioeng undergraduate)"),
        L("Aathreya Kadambi", "undergraduate", [2025, 2025], LG25, "Undergraduates", "Aathreya Kadambi (Math+CS undergraduate)"),
        L("Stephan Allenspach", "postdoc", [2023, 2024], LG24, "Postdocs", "Postdocs Stephan Allenspach"),
        L("Juno Lee", "masters", [2024, 2024], LG24, "PhD students", "Juno Lee (5th year MSc)"),
        L("Suchir Agarwal", "undergraduate", [2024, 2024], LG24, "Undergraduates", "Suchir Agarwal (EECS undergraduate)"),
        L("Tony Jin'Ichi de Leon", "undergraduate", [2024, 2024], LG24, "Undergraduates", "Tony Jin'Ichi de Leon (CS & Chemistry undergraduate)"),
        L("Hunter Nisonoff", "phd", [2021, 2024], LG23, "PhD students", "Hunter Nisonoff (PhD student, CCB, BAIR)"),
        L("Arthur Deng", "undergraduate", [2023, 2023], LG23, "Undergraduates", "Arthur Deng (EECS undergraduate)"),
        L("Inji Park", "undergraduate", [2023, 2023], LG23, "Undergraduates", "Inji Park (Chemistry undergraduate)"),
        L("Renzo Soatto", "undergraduate", [2023, 2023], LG23, "Undergraduates", "Renzo Soatto (EECS undergraduate)"),
        L("Mrunali Manjrekar", "undergraduate", [2022, 2022], LG22, "Core group", "Mrunali Manjrekar (UC Berkeley EECS and Bioengineering junior)"),
        L("David Brookes", "phd", [2019, 2021], LG21, "People", "David Brookes (PhD student, Biophysics, BAIR)"),
        L("Jahnavi Singh", "undergraduate", [2019, 2019], LG19, "People", "Jahnavi Singh (undergraduate, CS & Data Science)"),
        L("Chuck Tang", "undergraduate", [2019, 2019], LG19, "People", "Chuck Tang (undergraduate, EECS)"),
        L("Michael Whitmeyer", "undergraduate", [2019, 2019], LG19, "People", "Michael Whitmeyer (undergraduate, EECS)"),
    ],
    lab_note="ScienceML@Berkeley (Listgarten, at Berkeley since 2017 from Microsoft Research). Group page captured live and in "
             "Wayback 2019, 2021-2025; dissertations page has four 2016+ Ph.D.s. A mid-sized group (about 6-8 Ph.D. students at a time).",
    notes="Years for group-page rows are the captures that list them. 'Friends of the family' (Justin Lubin, Maria Lukarska) and "
          "collaborators are not counted. Junhao (Bear) Xiong is held as Bear Xiong.")

# ============================================================ James O'Brien
D["James O'Brien"] = dict(
    students=diss("obrien", "James O'Brien") + [tr("James Lin", "2019-59", "James O'Brien")],
    lab_note="O'Brien's homepage lists no group; 2016+ advising is one Ph.D. (Bailey 2020, held) and one master's thesis (2019). "
             "He has been mostly in industry (co-founder roles) in recent years.",
    notes="Searched homepage live + Wayback 2016/2022, EECS dissertations and tech reports (a 2023 Ph.D. on his TR listing, Vivek "
          "Nair, names Dawn Song as advisor and was not counted).")

# ============================================================ Aditya Parameswaran
AGP = "https://people.eecs.berkeley.edu/~adityagp/cv.pdf"
AGP_GRAD = "Graduated PhD Students [All students at Berkeley unless indicated otherwise.]"
D["Aditya Parameswaran"] = dict(
    students=diss("adityagp", "Aditya Parameswaran") + [
        tr("Haojun Zhuang", "2026-9", "Aditya Parameswaran"),
        tr("Rachel Lin", "2025-113", "Aditya Parameswaran"),
        tr("Mawil Hasan", "2025-77", "Aditya Parameswaran"),
        tr("Joshua Wu", "2023-167", "Aditya Parameswaran"),
        tr("Todd Yu", "2023-116", "Aditya Parameswaran"),
        tr("Priyam Mohanty", "2022-125", "Aditya Parameswaran"),
        tr("Christopher De Leon", "2022-67", "Aditya Parameswaran"),
        tr("Avinash Arjavalingam", "2021-181", "Aditya Parameswaran"),
        tr("Richard Lin", "2021-107", "Aditya Parameswaran"),
        L("Doris Lee", "phd", [2017, 2021], AGP, "Graduated PhD Students", "⋅ Doris Lee, Title: “Designing Automated Assistants for Visual Data Exploration” 2017—2021",
          note="CV: 'All students at Berkeley unless indicated otherwise' (began at Illinois, moved with him)"),
        L("Devin Petersohn", "phd", [2015, 2021], AGP, "Graduated PhD Students", "⋅ Devin Petersohn, Title: “Dataframe Systems: Theory, Architecture, and Implementation” 2015—2021",
          max_span=2000),
        L("Shreya Shankar", "phd", [2021, 2022], AGP, "PhD Students (Current Advising or Co-advising)", "⋅ Shreya Shankar, 2021—"),
        L("Nithin Chalapathi", "phd", [2021, 2022], AGP, "PhD Students (Current Advising or Co-advising)", "⋅ Nithin Chalapathi, 2021— (Coadvisor: Alvin Cheung)"),
        L("Dixin Tang", "postdoc", [2021, 2022], AGP, "Postdocs (Current or Past)", "Postdocs (Current or Past) ⋅ Dixin Tang, 2021—"),
        L("Kunal Aggarwal", "masters", [2021, 2022], AGP, "MS Thesis Students", "⋅ Kunal Aggarwal, 2021–"),
        L("Nidhi Kakulawaram", "masters", [2020, 2021], AGP, "MS Thesis Students", "⋅ Nidhi Kakulawaram, Title: “Spreadsheet Bubbles: Showing Contextually Relevant Data During Formula Editing”, 2020-21"),
        L("Jerry Song", "masters", [2020, 2021], AGP, "MS Thesis Students", "⋅ Jerry Song, Title: “Understanding and Evaluating the User Data Exploration Experience with Lux”, 2020–21"),
        L("Vincent Truong", "masters", [2020, 2021], AGP, "MS Thesis Students", "⋅ Vincent Truong, Title: “Generalized Partitioning for Dataset Versions in OrpheusDB”, 2020–21"),
        L("Jennifer Momoh", "other", [2020, 2021], AGP, "PhD/MS Students (Informal or Past advising)", "PhD/MS Students (Informal or Past advising) ⋅ Jennifer Momoh, 2020–21",
          note="CV section 'PhD/MS Students (Informal or Past advising)'"),
        L("Thyne Boonmark", "other", [2019, 2021], AGP, "PhD/MS Students (Informal or Past advising)", "Thyne Boonmark, 2019–21",
          note="CV section 'PhD/MS Students (Informal or Past advising)'"),
        L("Eva Wu", "other", [2019, 2021], AGP, "PhD/MS Students (Informal or Past advising)", "Eva Wu, 2019–21",
          note="CV section 'PhD/MS Students (Informal or Past advising)'"),
    ] + [L(n, "undergraduate", [y, 2022], AGP, "Undergraduate Students", f"{n}, {y}–") for n, y in [
        ("Micah Yong", 2020), ("Jonathan Yun", 2021), ("Connor Lien", 2022), ("Lawrence Chen", 2022),
        ("Pragya Kallanagoudar", 2022), ("Christina Fan", 2022), ("Eve Yi", 2022), ("Chris Seo", 2022)]] + [
        L("Murtaza Ali", "undergraduate", [2020, 2021], AGP, "Past students opting for Ph.D. studies", "Murtaza Ali, 2020—21"),
        L("William Ma", "undergraduate", [2019, 2020], AGP, "Past students opting for Ph.D. studies", "William Ma, 2019—20"),
    ],
    lab_note="Parameswaran's data-systems group (EPIC Data Lab; at Berkeley since 2019 from Illinois). The CV (c. 2022) has a full "
             "Mentorship section; EECS master's theses add 2021-2026 M.S. students. Illinois-era students are excluded.",
    notes="CV rows marked 'Illinois:' and undergraduates from before 2019 are not counted. Joshua Wu and Todd Yu appear both as "
          "undergraduates (CV) and master's students (EECS TR); kept once. Nidhi Kakulawaram's EECS TR names Bjorn Hartmann, "
          "but the CV lists her as Parameswaran's M.S. thesis student. The group blog (data-people-group.github.io) lists no people.")

# ============================================================ David A. Patterson
D["David A. Patterson"] = dict(
    students=diss("patterson", "David A. Patterson") + [tr("Henry Cook", "2016-89", "David A. Patterson", "phd")],
    lab_note="Patterson (emeritus since 2016, at Google) last graduated Ph.D.s in 2016-2017 (ASPIRE/ADEPT lab, often co-advised "
             "with Krste Asanovic); the dissertations page gives five, one held.",
    notes="Homepage links only to photos and an alumni page of pre-2016 projects. No later advisees expected.")

# ============================================================ Jonathan Ragan-Kelley
JRK19 = WB + "20191215130853id_/https://people.eecs.berkeley.edu/~jrk/"
D["Jonathan Ragan-Kelley"] = dict(
    students=diss("jrk", "Jonathan Ragan-Kelley") + [
        tr("Vaishaal Shankar", "2018-137", "Jonathan Ragan-Kelley"),
        L("Karima Ma", "member", [2019, 2019], JRK19, "Students", "Students Karl Krauth Karima Ma",
          note="listed under 'Students' on his Berkeley homepage in Dec 2019 (moving to MIT in Jan 2020); degree program not stated"),
    ],
    lab_note="Ragan-Kelley was a Berkeley assistant professor 2017-2019, moving to MIT CSAIL in January 2020. His Berkeley "
             "students: Reinking (held), Krauth and Shankar (both co-advised with Ben Recht), and Karima Ma (2019 page).",
    notes="Alexander Reinking (held) also has a 2020 master's thesis (EECS-2020-40) under him. Later homepage captures list 'Students & Collaborators' mixing MIT and Berkeley people (Gilbert Bernstein postdoc, Yuka "
          "Ikarashi, Tian Jin, Amanda Liu, AJ Root, Tzu-Mao Li); only the 2019 Berkeley-only list is used.")

# ============================================================ Jonathan Shewchuk
D["Jonathan Shewchuk"] = dict(
    students=diss("shewchuk", "Jonathan Shewchuk") + [tr("Sagnik Bhattacharya", "2022-92", "Jonathan Shewchuk")],
    lab_note="Shewchuk is a single-investigator theorist; 2016+ advising is one Ph.D. (Khoury 2020, held) and one master's thesis "
             "(Bhattacharya 2022), whom his homepage calls a 'former UC Berkeley student'.",
    notes="Homepage, dissertations page and tech reports searched; no other advisees named.")

# ============================================================ Doug Tygar
D["Doug Tygar"] = dict(
    students=diss("tygar", "Doug Tygar"),
    lab_note="Tygar's advising ended with Ph.D.s in 2016-2017 (both held); listed only 2016-2019.",
    notes="Homepage (Wayback 2016-2024) has only biography/publications links; research page capture is a 403; EECS tech "
          "reports by faculty have no 2016+ entries. Nothing more found.")

# ============================================================ Jean Walrand
D["Jean Walrand"] = dict(
    students=diss("walrand", "Jean Walrand"),
    lab_note="Walrand (emeritus) has no 2016+ Ph.D. on the dissertations page; the two held students finished in 2015.",
    notes="Homepage people.eecs.berkeley.edu/~wlr is a bare directory index (live 403; Wayback 2024), last updated 2014; EECS "
          "tech reports by faculty have no 2016+ entries. Nothing more found; the held 2015 graduates predate the window.")

# ============================================================ Christian Borgs
D["Christian Borgs"] = dict(
    students=diss("borgs", "Christian Borgs"),
    lab_note="Borgs joined Berkeley EECS/BIDMaP in 2020 from Microsoft Research; one Berkeley Ph.D. (Geng Zhao 2025, held).",
    notes="Homepage and publication list (cv/cpub.pdf) name no advisees; EECS tech reports listing is a 404. Postdocs and "
          "students of the Borgs-Chayes BIDMaP group are not listed on any page found.")

# ============================================================ Jennifer Chayes
D["Jennifer Chayes"] = dict(
    students=[],
    lab_note="Chayes is Dean of the College of Computing, Data Science, and Society (since 2020); she has no EECS dissertations "
             "page (404) and no group page. One held advisee (Shengchao Liu).",
    notes="Searched homepage and CV (July 2022; no advising section), EECS dissertations (404) and tech reports (404). Nothing more found.")

# ============================================================ Nika Haghtalab
NIKA = "https://people.eecs.berkeley.edu/~nika/files/Nika_CV.pdf"
NIKA_PHD = "Research Advising Ph.D. Students"
D["Nika Haghtalab"] = dict(
    students=diss("nika", "Nika Haghtalab") + [
        L("Abhishek Shetty", "phd", [2019, 2024], NIKA, NIKA_PHD, "Abhishek Shetty, EECS."),
        L("Eric Zhao", "phd", [2021, 2024], NIKA, NIKA_PHD, "Eric Zhao, EECS co-advised with Jordan."),
        L("Jessica Dai", "phd", [2022, 2024], NIKA, NIKA_PHD, "Jessica Dai, EECS co-advised with Recht."),
        L("Yuval Dagan", "postdoc", [2023, 2024], NIKA, "Postdoctoral Researchers", "Postdoctoral Researchers Yuval Dagan, FODSI."),
        L("Mingda Qiao", "postdoc", [2023, 2024], NIKA, "Postdoctoral Researchers", "Mingda Qiao, FODSI."),
        L("Paul Goelz", "postdoc", [2024, 2024], NIKA, "Postdoctoral Researchers", "Paul Goelz, FODSI."),
        L("Chara Podimata", "postdoc", [2022, 2023], NIKA, "Postdoctoral Researchers", "Chara Podimata, FODSI."),
        L("Mahsa Derakhshan", "postdoc", [2021, 2022], NIKA, "Postdoctoral Researchers", "Mahsa Derakhshan, FODSI."),
        L("Naveen Durvasula", "undergraduate", [2021, 2023], NIKA, "Undergraduate Research Advising", "Naveen Durvasula, BEng/BBA 2023."),
        L("Korinna Frangias", "undergraduate", [2022, 2023], NIKA, "Undergraduate Research Advising", "Korinna Frangias, BEng 2023."),
    ],
    lab_note="Haghtalab (at Berkeley since 2020, from Cornell) runs a learning-theory/econ group; her CV (c. 2024) lists six "
             "Ph.D. students, six postdocs and two undergraduates.",
    notes="Years come from the CV's date column (listed in the same order as the names). Ellen Vitercik is listed as "
          "'unofficial mentor' and not counted. Alex Wei appears on the dissertations page as Alexander Wei.")

# ============================================================ Stella Yu
SY22 = WB + "20220924001939id_/https://www1.icsi.berkeley.edu/~stellayu/"
SY_GROUP = ["Dr. Iksung Kang", "Dr. Sangryul Jeon", "Ke Wang", "Tony Long Lian", "Peter Ren", "Frank Xudong Wang", "Peter Xinlei Pan",
            "Daniel Chun-Hsiao Yeh", "Peter Jiayun Wang", "Tsung-Wei Ke", "Dr. Dong-Jin Kim", "Dr. Nils-Steffen Worzyk", "Dr. Yunhui Guo",
            "Tejasvi Kothapalli", "Daniel Lin", "Haoran Guo", "Joshua Levine", "Galen Chuang", "Dr. Zhongqi Miao",
            "Dr. Baladitya Yellapragada", "Yifei Xing", "Dr. Yubei Chen", "Dr. Saeed Seyyedi", "Daniel Zeng", "Ke Li", "Runtao Liu",
            "Dr. Sascha Hornauer", "Shuai Liu", "Dr. Jyh-Jing Hwang", "Dr. Rudrasis Chakraborty", "Arian Ranjbar", "Emily Hsiao",
            "Alice Duan", "Lu Yu", "Pengyuan Chen", "Wayne Li", "Lucy Yang", "Dr. Qian Yu", "Jesper Haahr Christensen", "Jianqiao Ni",
            "Michele Winter", "Dr. Caigui Jiang", "Borong Zhang", "Dr. Zhirong Wu", "Dr. Ziwei Liu", "Dr. Matthias Demant",
            "Sebastian Palacio", "Dr. Seyed Ali Amirshahi", "Vinay Ramasesh", "Noah Golmant", "Renee Sweeney", "Riley Edmunds",
            "William Guss", "Asha Anoosheh"]
D["Stella Yu"] = dict(
    students=diss("stellayu", "Stella Yu") + [tr("Haoran Guo", "2022-127", "Stella Yu")] + [
        L(n.replace("Dr. ", ""), "member", None, SY22, "Group", n, max_span=2500, after="Group Dr. Iksung Kang",
          note="ICSI Vision Group list on her homepage (2021-2022 captures): cumulative, newest first, no dates; 'Dr.' marks "
                "postdocs/research scientists") for n in SY_GROUP],
    lab_note="Stella Yu directed the ICSI Vision Group (Berkeley EECS faculty) and moved to the University of Michigan in fall 2022, "
             "keeping a Berkeley adjunct appointment and Berkeley Ph.D. students (dissertations through 2026). Her homepage group "
             "list is cumulative.",
    notes="The group list first appears in the Dec 2021 capture and is undated; members are recorded with years null. The final "
          "four names on the list (Weiyu Zhang, Dimitri Lisin, Christina Pavlopoulou, Elena Bernardis) are known pre-2016 members "
          "and were left out, as was 'Dr. Patrick Virtue' (the same person as dissertation author Pat Virtue). Utkarsh Singhal is held.")

# ============================================================ John Wright
D["John Wright"] = dict(
    students=[],
    lab_note="Wright (quantum computing theory) joined Berkeley in 2022 from UT Austin; the two held students (Angelos Pelecanos, "
             "Laura Lewis) are the only ones his homepage links. A new, small group.",
    notes="Searched homepage (no Students section), EECS dissertations (404) and tech reports (404). Nothing more found.")

# ============================================================ Aditi Krishnapriyan
AK = "https://a1k12.github.io/"
AK23 = WB + "20231209053732id_/https://a1k12.github.io/"
AK24 = WB + "20241109072354id_/https://a1k12.github.io/"
AK25 = WB + "20251012082459id_/https://a1k12.github.io/"
AKH = "advise the following PhD students and postdocs:"
AKNOTE = "listed under 'I am very fortunate to advise the following PhD students and postdocs'; the list does not say which are postdocs"
D["Aditi Krishnapriyan"] = dict(
    students=diss("aditik", "Aditi Krishnapriyan") + [tr("Ishan Amin", "2025-41", "Aditi Krishnapriyan")] + [
        L(n, "member", [y, 2026], AK, AKH, n, note=AKNOTE, after=AKH) for n, y in [
            ("Sanjeev Raja", 2023), ("Nithin Chalapathi", 2023), ("Toby Kreiman", 2023), ("Eric Qu", 2023), ("Yue Jian", 2023),
            ("Yiheng Du", 2024), ("Kai Nelson", 2025), ("Theo Sternlieb", 2026), ("Ivan Kuang", 2026)]] + [
        L("Lucas Aschenbach", "masters", [2026, 2026], AK, "Master’s students", "Master’s students : Ishan Amin Lucas Aschenbach"),
        L("Ritwik Gupta", "postdoc", [2025, 2026], AK, "Former members", "Ritwik Gupta (postdoc)"),
        L("Boyu Qie", "postdoc", [2025, 2026], AK, "Former members", "Boyu Qie (postdoc)"),
        L("Rasmus H⌀egh", "postdoc", [2023, 2025], AK, "Former members", "Rasmus H⌀egh (postdoc)",
          note="Rasmus Høegh; the page writes the ø as ⌀"),
        L("Danny Reidenbach", "masters", [2023, 2023], AK23, "Former members", "Danny Reidenbach (UC Berkeley MS CS)"),
        L("Nick Swenson", "masters", [2023, 2023], AK23, "Former members", "Nick Swenson (UC Berkeley EECS MEng)"),
        L("Divyam Goel", "undergraduate", [2023, 2025], AK23, "Undergraduate students", "Undergraduate students : Yiheng Du Ishan Amin Divyam Goel"),
        L("Tianlang Chen", "undergraduate", [2023, 2023], AK23, "Undergraduate students", "Undergraduate students : Yiheng Du Ishan Amin Divyam Goel Tianlang Chen"),
        L("Ryan Liu", "undergraduate", [2024, 2025], AK24, "Undergraduate students", "Undergraduate students : Ishan Amin Divyam Goel Ryan Liu"),
        L("Christine Zhang", "undergraduate", [2025, 2025], AK25, "Undergraduate students", "Undergraduate students : Divyam Goel Ryan Liu Christine Zhang"),
        L("Elizabeth Weaver", "undergraduate", [2025, 2025], AK25, "Undergraduate students", "Undergraduate students : Divyam Goel Ryan Liu Christine Zhang Elizabeth Weaver"),
    ],
    lab_note="Krishnapriyan (Chemical Engineering + EECS, since 2022) runs an AI-for-science group of about ten Ph.D. "
             "students/postdocs; homepage Group Information captured live and in Wayback 2023-2025.",
    notes="First-listed years come from the earliest capture naming each person. Dami Fasina (visiting Ph.D. student, Yale) is not "
          "counted. Theo Sternlieb is also on Listgarten's page (co-advised).")

# ============================================================ Irene Chen
CT = "https://chenlab.io/team/"
CT23 = WB + "20230927155514id_/https://chenlab.io/team/"
CT25 = WB + "20251016030008id_/http://chenlab.io/team/"
D["Irene Chen"] = dict(
    students=diss("iychen", "Irene Chen") + [
        L("Zhongyuan Liang", "phd", [2023, 2026], CT, "team", "Zhongyuan Liang PhD Student"),
        L("Stanley Hua", "phd", [2025, 2026], CT, "team", "Stanley Hua PhD Student"),
        L("Junayd Lateef", "masters", [2025, 2026], CT, "team", "Junayd Lateef Masters Student"),
        L("Erin Tan", "masters", [2024, 2026], CT, "team", "Erin Tan Masters Student", note="undergraduate researcher in 2024-2025 captures"),
        L("Ricky Zhuang", "masters", [2024, 2026], CT, "team", "Ricky Zhuang Masters Student", note="undergraduate researcher in 2024-2025 captures"),
        L("Neha Simha", "other", [2025, 2026], CT, "team", "Neha Simha Researcher"),
    ] + [L(n, "undergraduate", [y, 2026], CT, "team", f"{n} Undergraduate Researcher") for n, y in [
        ("Sarika Pasumarthy", 2025), ("Anwen Huang", 2025), ("Mira Wagner", 2026), ("Paulina Ai", 2026), ("Aditi Bordia", 2026)]] + [
        L("Li-Ching Chen", "other", [2023, 2025], CT, "alumni", "Li-Ching Chen PhD Rotation Student",
          note="listed as 'PhD Student' on the 2023-2025 team pages, as 'PhD Rotation Student' among alumni in 2026"),
        L("Hongzhou Luan", "other", [2024, 2025], CT, "alumni", "Hongzhou Luan PhD Rotation Student",
          note="listed as 'PhD Student' in 2024-2025, as 'PhD Rotation Student' among alumni in 2026"),
        L("Yuanyuan Gao", "masters", [2025, 2025], CT, "alumni", "Yuanyuan Gao Masters Student"),
    ] + [L(n, "undergraduate", [2024, 2025], CT, "alumni", f"{n} Undergraduate Researcher") for n in [
        "Alyssa Nguyen", "Catherine Chu", "Joon Kim", "Rebecca Dang", "Anthony Tafoya", "Vatsal Ananthula"]],
    lab_note="C.H.E.N. Lab (Irene Chen, Berkeley EECS + UCSF Computational Precision Health, since 2023). Team page captured live "
             "and in Wayback 2023-2025: two Ph.D. students, three master's students, about ten undergraduates.",
    notes="Collaborators (Deb Raji, Jessica Dai, Peter Wu and others) and the visiting ETH master's student are not counted. Haojun "
          "Zhuang's 2026 master's thesis has Irene Chen as co-author but names Parameswaran as advisor (counted there).")

# ============================================================ Christopher Fletcher
FPSG_PHD = "PhD Hannah Leung"
D["Christopher Fletcher"] = dict(
    students=diss("cwfletcher", "Christopher Fletcher") + [
        L("Shashank Anand", "phd", [2024, 2026], FPSG, FPSG_PHD, "Shashank Anand (2024-present; co-advised by Sophia Shao)"),
        L("Yan Zhu", "phd", [2024, 2026], FPSG, FPSG_PHD, "Yan Zhu (2024-present)"),
        L("Kris Dong", "phd", [2024, 2026], FPSG, FPSG_PHD, "Kris Dong (2024-present; co-advised by Sophia Shao)"),
        L("Alex Thomas", "phd", [2024, 2026], FPSG, FPSG_PHD, "Alex Thomas (2024-present; co-advised by John Kubiatowicz)"),
        L("Alan Wang", "phd", [2025, 2026], FPSG, FPSG_PHD, "Alan Wang (2025-present)"),
        L("Nandeeka Nayak", "phd", [2020, 2025], FPSG, "PhD Hadi Asgharimoghaddam",
          "Nandeeka Nayak (2020-present); SURGE Fellow (2020-2025), NSF GRFP Honorable Mention; Berkeley Outstanding Graduate Peer Mentor Award",
          note="began at UIUC; the Berkeley award places her at Berkeley after Fletcher's 2023 move"),
        L("Yingchen Wang", "postdoc", [2024, 2025], FPSG, "Alumni PostDocs", "Yingchen Wang (2024-2025)"),
        L("Flavien Solt", "postdoc", [2024, 2025], FPSG, "Alumni PostDocs", "Flavien Solt (2024-2025)"),
        L("Yongye Zhu", "masters", [2023, 2025], FPSG, "Masters Rohit Agrawal", "Yongye Zhu (2023-2025)"),
        L("Ronit Nagarapu", "masters", [2024, 2026], FPSG, "Masters Rohit Agrawal", "Ronit Nagarapu (2024-2026)"),
        L("Anish Dhanashekar", "masters", [2024, 2026], FPSG, "Masters Rohit Agrawal", "Anish Dhanashekar (2024-2026)"),
        L("Anto Kam", "masters", [2024, 2026], FPSG, "Masters Rohit Agrawal", "Anto Kam (2024-2026)"),
        L("Frederic Wu", "undergraduate", [2024, 2026], FPSG, "Undergraduate Frederic Wu", "Undergraduate Frederic Wu (2024-present)"),
        L("Jaewon Hur", "undergraduate", [2025, 2026], FPSG, "Undergraduate Frederic Wu", "Jaewon Hur (2025-present)"),
        L("Archie Lee", "undergraduate", [2024, 2024], FPSG, "Undergraduate Lucas Hsiung", "Archie Lee (2024)"),
        L("SooHyuk Cho", "undergraduate", [2024, 2025], FPSG, "Undergraduate Lucas Hsiung", "SooHyuk Cho (2024-2025)"),
        L("Wen Cao", "undergraduate", [2025, 2026], FPSG, "Undergraduate Lucas Hsiung", "Wen Cao (2025-2026)"),
        L("Julia Tomaszewska", "undergraduate", [2025, 2026], FPSG, "Undergraduate Lucas Hsiung", "Julia Tomaszewska (2025-2026)"),
    ],
    lab_note="FPSG (Fletcher's group) moved from UIUC to Berkeley in 2023. The group page lists both eras; only members who "
             "started in 2023 or later, or whom the page places at Berkeley, are counted.",
    notes="Excluded as UIUC-era or unplaced: Hannah Leung (co-advised with Talia Ringer, UIUC), Boru Chen (2022-present, no "
          "Berkeley evidence on the page), Rutvik Choudhary and other 2017-2023 alumni, interns/visitors and high-school students.")

# ============================================================ Emma Pierson
D["Emma Pierson"] = dict(
    students=[],
    lab_note="Pierson moved from Cornell Tech to Berkeley in 2024. Her group page lists five current Ph.D. students, but three are "
             "co-advised with Nikhil Garg (Cornell Tech) and so are Cornell students; the two Berkeley students (Raj/Rajiv Movva, "
             "Marçal Comajoan Cara) are already held.",
    notes="Not counted for lack of a source placing them at Berkeley: Sidhika Balachandar, Gabriel Agostini, Erica Chiang (co-advised "
          "with Nikhil Garg), Divya Shanmugam (postdoc), Smitha Milli and Harini Suresh (past postdocs). Her one EECS master's TR "
          "(Michael Wu 2025) names Prabal Dutta as advisor. EECS dissertations page is a 404.")

# ============================================================ Michael Franklin
D["Michael Franklin"] = dict(
    students=[],
    lab_note="Franklin left Berkeley for the University of Chicago in 2016 (listed 2016-2017); his last Berkeley Ph.D.s finished "
             "in 2016-2017 (Evan Sparks, Daniel Haas, both held).",
    notes="The EECS dissertations page is now a 404 (newest Wayback capture July 2016, entries to 2015); the TechRpts faculty listing "
          "is a 404 (Wayback to 2015). The 2016-2018 EECS tech-report indexes show Sparks (advisor Franklin, held), Haas (held) "
          "and Sanjay Krishnan, whose 2018 dissertation names only Ken Goldberg. Nothing more found.")
