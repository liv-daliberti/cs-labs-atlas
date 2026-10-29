"""Source spec for the zero-students pass (2026-10-27) at MIT, CMU, EPFL and Princeton: PIs whose advisees no thesis
catalogue names (they joined recently, their students have not graduated, or their department deposits no theses).
Read by harvest_lab_sources.py (what to store) and records_labs.records() (how each stored page becomes records).
Berkeley's equivalent is berkeley_depts.LAB_SOURCES (not read here).

SOURCES[school]: the PIs' own pages (lab / group rosters, PI profiles, departmental directories), curated by reading each
stored page. Each source:
  pi        the PI as in hierarchy/<school>/pis.json
  kind      lab-roster | pi-profile | dept-directory | colleague-page (the record's source tag)
  title     what the page is
  captures  stored URLs (a live URL, or a Wayback id_ URL); the first is the default capture of 'entries'
  entries   (student as named, role, y0, y1[, anchor[, capture]]): one record per row. anchor = the exact
            (whitespace-collapsed) page text naming the student (default: the name). Years: the start year the page
            gives ('PhD Student · Fall 2022') through the capture year, or the stated degree year; otherwise the capture
            year (a current-member list says nothing about earlier years).
  qmax      quote limit for this source (default QMAX): pages that name the PI only in a heading need a longer one
  note      what the page is and what was left out.
A quote is the shortest stretch of the stored text that runs from a PI family-name occurrence to the student's anchor (or
from the anchor to the next PI family-name occurrence), at most qmax characters.
"""

QMAX = 2000

SOURCES = {
    "mit": [
        {"pi": "Pat Pataranutaporn", "kind": "lab-roster",
         "title": "Cyborg Psychology (MIT Media Lab group), People: graduate students and MEng students (2026)",
         "captures": ["https://www.media.mit.edu/groups/cyborg-psychology/people/"],
         "entries": [("Sally Ahmed", "other", 2026, 2026, "Sally Ahmed Graduate Student"),
                     ("Tiffany Wang", "other", 2026, 2026, "Tiffany Wang Graduate Student"),
                     ("Soojin Lee", "other", 2026, 2026, "Soojin Lee Graduate Student"),
                     ("Stanley Huang", "other", 2026, 2026, "Stanley Huang Graduate Student"),
                     ("Chayapatr Archiwaranguprok", "other", 2026, 2026, "Chayapatr Archiwaranguprok Graduate Student"),
                     ("Constanze Albrecht", "other", 2026, 2026, "Constanze Albrecht Graduate Student"),
                     ("Sheer Karny", "other", 2026, 2026, "Sheer Karny Graduate Student"),
                     ("Anthony Baez", "masters", 2026, 2026, "Anthony Baez , MEng Student"),
                     ("Jennifer Ai", "masters", 2026, 2026, "Jennifer Ai, MEng Student")],
         "note": "the group started with his appointment (2025-09); MAS 'Graduate Student' does not say SM or PhD (role "
                 "other); Rachel Poonsiriwong (Harvard GSD), the research affiliate, the administrative assistant and two "
                 "members with no stated role left out"},
    ],
    "cmu": [
        {"pi": "Yorie Nakahira", "kind": "lab-roster", "title": "Control & Learning Group (CMU ECE), People: Ph.D. Students",
         "captures": ["https://www.cmu.edu/ece/learning-control/people/index.html"],
         "entries": [("Zhuoyuan Wang", "phd", 2026, 2026), ("Oren Wright", "phd", 2026, 2026), ("Haoming Jing", "phd", 2026, 2026),
                     ("Ziyi Zhang", "phd", 2026, 2026), ("Xiyu Deng", "phd", 2026, 2026)],
         "note": "'Last updated Summer 2026'; Oren Wright co-advised by Jose Moura, Ziyi Zhang by Guannan Qu"},
        {"pi": "Guannan Qu", "kind": "lab-roster", "title": "Guannan Qu, People: current PhD and master's students (start term)",
         "captures": ["https://www.guannanqu.com/people/"],
         "entries": [("Alex DeWeese", "phd", 2022, 2026, "Alex DeWeese PhD Student · Fall 2022"),
                     ("Ziyi Zhang", "phd", 2022, 2026, "Ziyi Zhang PhD Student · Fall 2022"),
                     ("Chaoyi Pan", "phd", 2023, 2026, "Chaoyi Pan PhD Student · Fall 2023"),
                     ("Zeji Yi", "phd", 2023, 2026, "Zeji Yi PhD Student · Fall 2023"),
                     ("Muhammed Ustaömeroğlu", "phd", 2023, 2026, "Muhammed Ustaömeroğlu PhD Student · Fall 2023"),
                     ("Vidur Sinha", "phd", 2026, 2026, "Vidur Sinha PhD Student · Fall 2026"),
                     ("Nai-Chieh Huang", "phd", 2026, 2026, "Nai-Chieh Huang MLD PhD Student · Fall 2025 (Co-advising since Fall 2026)"),
                     ("Euijin Hong", "masters", 2026, 2026), ("Jivesh Jain", "masters", 2026, 2026)],
         "note": "'Last Updated: 13 Oct 2026'; past master's students (no years) and visitors left out"},
        {"pi": "Michael D. Smith", "kind": "colleague-page",
         "title": "George Chen (CMU Heinz), Supervision: past PhD students advised with Mike Smith",
         "captures": ["https://www.andrew.cmu.edu/user/georgech/supervision.html"],
         "entries": [("Helen S. Zeng", "phd", 2024, 2024, "Helen S. Zeng (PhD 2024; advised with Mike Smith (chair)"),
                     ("Emaad Manzoor", "phd", 2021, 2021, "Emaad Manzoor (PhD 2021; advised with Dokyun Lee (chair) and Mike Smith"),
                     ("Mi Zhou", "phd", 2020, 2020, "Mi Zhou (PhD 2020; advised with Mike Smith (chair)")],
         "note": "Heinz College PhDs: KiltHub holds only 4 Heinz theses 2016-2026, none naming him"},
        {"pi": "Daniel Yurovsky", "kind": "dept-directory",
         "title": "CMU Psychology graduate-student directory (Wayback 2022-05-16): 'Advisor: Daniel Yurovsky'",
         "captures": ["https://web.archive.org/web/20220516223206id_/https://www.cmu.edu/dietrich/psychology/directory/graduate-students/index.html"],
         "entries": [("Megan Waller", "phd", 2022, 2022, "Megan Waller Graduate Student, Psychology"),
                     ("Yuchen Zhou", "phd", 2022, 2022, "Yuchen Zhou Graduate Student, Psychology")],
         "note": "his CMU appointment ran 2020-2022, so the 2022 capture is used, not the live page"},
    ],
    "epfl": [
        {"pi": "Andrea Cavallaro", "kind": "lab-roster",
         "title": "MINTS (Laboratory of Multimodal Intelligent Systems), People: Head / Doctoral Assistants",
         "captures": ["https://www.epfl.ch/labs/mints/people/"],
         "entries": [(n, "phd", 2026, 2026, a) for n, a in [
             ("Darya Baranouskaya", "Baranouskaya, Darya"), ("Mirko Casu", "Casu, Mirko"), ("Lorenzo Cirillo", "Cirillo, Lorenzo"),
             ("Dina El Zein", "El Zein, Dina"), ("Jose Rafael Espinosa Mena", "Espinosa Mena, Jose Rafael"),
             ("Olena Hrynenko", "Hrynenko, Olena"), ("Shashi Kumar", "Kumar, Shashi"), ("Cen Lu", "Lu, Cen"),
             ("Ante Maric", "Maric, Ante"), ("Martin Schonger", "Schonger, Martin"), ("Haruki Shirakami", "Shirakami, Haruki"),
             ("Yung-Chen Tang", "Tang, Yung-Chen"), ("Martina Vincoli", "Vincoli, Martina"), ("Lei Xu", "Xu, Lei")]],
         "note": "Infoscience has no thesis directed by him yet (EPFL since 2023); project students left out"},
        {"pi": "Andrew Sonta", "kind": "pi-profile", "title": "EPFL people page, Teaching & PhD: PhD Students",
         "captures": ["https://people.epfl.ch/andrew.sonta?lang=en"],
         "entries": [(n, "phd", 2026, 2026) for n in ["Philyoung Jeong", "Samuel Jordi", "Shiyu Liu", "Giovanna Pilot",
                                                      "Kanaha Shoji", "Yufei Zhang"]],
         "note": "the same six are 'PhD Student' on the ETHOS team page; Infoscience has no thesis directed by him yet (EPFL since 2022)"},
    ],
    "princeton": [
        {"pi": "Arash Adel", "kind": "lab-roster", "title": "Adel Research Group (Princeton SoA), Team",
         "captures": ["https://www.adelresearchgroup.org/team"],
         "entries": [("Daniel Ruan", "phd", 2026, 2026, "Daniel Ruan Ph.D. Student"),
                     ("Jutang Gao", "phd", 2026, 2026, "Jutang Gao Ph.D. Student"),
                     ("Ava Daniel", "undergraduate", 2026, 2026, "Ava Daniel Senior Thesis Student")],
         "note": "formerly ADR (adeldesignresearch.org, now parked); postdoc, research associate/assistants and the alumni list "
                 "(no years; it mixes his Michigan group) left out"},
        {"pi": "Andrea Goldsmith", "kind": "dept-directory",
         "title": "Princeton ECE people pages (Wayback): advisee profiles 'Adviser(s): Andrea Goldsmith' and her 'Advisee(s)' list",
         "captures": ["https://web.archive.org/web/20210620165734id_/https://ece.princeton.edu/people/dennis-anthony",
                      "https://web.archive.org/web/20211217072831id_/https://ece.princeton.edu/people/andrea-goldsmith",
                      "https://web.archive.org/web/20221222054802id_/https://ece.princeton.edu/people/andrea-goldsmith",
                      "https://web.archive.org/web/20211015152253id_/https://ece.princeton.edu/people/rajarshi-saha"],
         "entries": [("Dennis Anthony", "phd", 2021, 2021, "Dennis Anthony Email Address: [email removed]"),
                     ("Dennis Anthony", "phd", 2021, 2021, "Advisee(s): Dennis Anthony",
                      "https://web.archive.org/web/20211217072831id_/https://ece.princeton.edu/people/andrea-goldsmith"),
                     ("Dennis Anthony", "phd", 2022, 2022, "Advisee(s): Dennis Anthony",
                      "https://web.archive.org/web/20221222054802id_/https://ece.princeton.edu/people/andrea-goldsmith"),
                     ("Rajarshi Saha", "other", 2021, 2021, "Rajarshi Saha Email Address: [email removed]",
                      "https://web.archive.org/web/20211015152253id_/https://ece.princeton.edu/people/rajarshi-saha")],
         "note": "Dennis Anthony: Princeton graduate student (MAE graduate-student page) with adviser Goldsmith; Rajarshi Saha: "
                 "Stanford EE PhD student listed by Princeton ECE with adviser Goldsmith (role other). Her other listed "
                 "advisees 2020-2025 (Anusha Lalitha, Michal Yemini, Mohamed Seif Mohamed, Priyanka Kaswan) are postdocs / "
                 "research scholars and are left out. No 2020-2025 Princeton dissertation or senior thesis in DataSpace names her."},
    ],
}

try:  # Stanford (gap 3, 2026-10-27): Profiles Wayback advisee lists + lab rosters, see lab_sources_stanford.py
    from lab_sources_stanford import SOURCES as _STANFORD; SOURCES["stanford"] = _STANFORD  # noqa: E702
except ImportError:
    pass
