from dhelp import M, PUB, WB
D = {}

TM = "https://augmented-design-capability-studio.github.io/team.html"
D["Nikolas Martelaro"] = dict(
    lab_site="https://augmented-design-capability-studio.github.io/",
    people_page=TM,
    people_pages=[TM],
    members=[
        M("Alice Tang", "phd", None, TM, near="Current Members"),
        M("David Chuan-En Lin", "phd", None, TM, near="Current Members"),
        M("Frederic Gmeiner", "phd", None, TM, near="Current Members"),
        M("Howard Han", "phd", None, TM, near="Current Members"),
        M("Howie Wang", "phd", None, TM, near="Current Members"),
        M("Zeda Xu", "phd", None, TM, near="Current Members"),
        M("Chengyi Shen", "visitor", [2025, 2025], TM, near="Alumni"),
    ],
    pubs=[PUB("https://augmented-design-capability-studio.github.io/publications.html", mode="anchor")],
    notes="Lab = Augmented Design Capability Studio (live team page, 6 current + 1 alumnus). Wayback in shared back-off, so no older team captures were read. nikmartelaro.com is the PI homepage with no student list. Publications page parsed by anchor mode; a few non-paper anchors (site footer) show as missing and should be ignored.",
    blocked=[],
)

LM = "https://www.cmu.edu/cbd/people/lugo-martinez.html"
D["Jose Lugo-Martinez"] = dict(
    lab_site="https://www.andrew.cmu.edu/user/jlugomar/",
    people_page=LM,
    people_pages=[LM],
    members=[
        M("Kanupriya Anand", "masters", None, LM, near="Lab Members"),
        M("Sina Barazandeh", "phd", None, LM, near="Lab Members"),
        M("Peiran Jiang", "phd", None, LM, near="Lab Members"),
        M("Young Je Lee", "phd", None, LM, near="Lab Members"),
        M("Seoyoon Moon", "phd", None, LM, near="Lab Members"),
        M("Aaron Rosen", "phd", None, LM, near="Lab Members", note="co-advised by Jishnu Das"),
        M("Weifeng (William) Wu", "member", None, LM, near="Lab Members", note="role not stated on page"),
        M("Hongliang (Varian) Zhou", "masters", None, LM, near="Lab Members", note="MSCB student"),
    ],
    pubs=[PUB("https://www.andrew.cmu.edu/user/jlugomar/publications.html", mode="auto")],
    notes="Lab members listed on the CBD department profile page (live); homepage andrew.cmu.edu/user/jlugomar has no people list (last updated 2020). Wayback in shared back-off, no alumni captures read.",
    blocked=[],
)

SH = "https://shredlabcmu.github.io/current-members/"
D["Melisa Orta Martinez"] = dict(
    lab_site="https://shredlabcmu.github.io/",
    people_page=SH,
    people_pages=[SH],
    members=[
        M("Peter Roberts", "postdoc", None, SH, near="Postdoctors"),
        M("Annika Srinivasan", "phd", None, SH, near="Graduate Students"),
        M("Guadalupe Bernal", "phd", None, SH, near="Graduate Students"),
        M("Iqui Balam Heredia Marin", "phd", None, SH, near="Graduate Students"),
        M("Nathan Zimmerer", "phd", None, SH, near="Graduate Students"),
        M("Ricardo Salazar Ordonez", "phd", None, SH, near="Graduate Students"),
        M("Donggu Lee (Ben)", "masters", None, SH, near="Graduate Students"),
        M("Hanming Zhang", "masters", None, SH, near="Graduate Students"),
        M("Kiran Marques", "masters", None, SH, near="Graduate Students"),
        M("Woongseok Han (Michael)", "masters", None, SH, near="Graduate Alumni"),
        M("Miles Mufuka Martin", "other", None, SH, near="Graduate Alumni", note="Robotics Institute Pathways Fellow"),
        M("Samantha Speer", "phd", [None, 2025], SH, near="Graduate Alumni", note="PhD defense Dec 2025 per lab news"),
        M("Sarah Costrell", "phd", [None, 2025], SH, near="Graduate Alumni", note="PhD defense Dec 2025 per lab news"),
        M("Sidney Nimako", "masters", None, SH, near="Graduate Alumni"),
        M("William Scott", "masters", None, SH, near="Graduate Alumni"),
        M("Alejandro Gonzalez Escamilla", "undergraduate", None, SH, near="Visitors & Interns"),
        M("Emi Alvarez Perez", "undergraduate", None, SH, near="Visitors & Interns"),
        M("Juan Robles", "undergraduate", None, SH, near="Visitors & Interns"),
        M("Athan Ferber", "undergraduate", None, SH, near="Visitors & Interns"),
        M("Sam Garcia", "undergraduate", None, SH, near="Visitors & Interns"),
        M("Daniela Diego", "undergraduate", None, SH, near="Previous Visitors & Interns"),
        M("Arlene Reyes", "undergraduate", None, SH, near="Previous Visitors & Interns"),
        M("Isaac Osei", "undergraduate", None, SH, near="Previous Visitors & Interns"),
        M("Jesus Guerrero", "undergraduate", None, SH, near="Previous Visitors & Interns"),
        M("Junee Omana", "undergraduate", None, SH, near="Previous Visitors & Interns"),
        M("Olivia Sobek", "undergraduate", None, SH, near="Previous Visitors & Interns"),
        M("Charlotte Betz", "undergraduate", None, SH, near="Previous Visitors & Interns"),
    ],
    pubs=[PUB("https://shredlabcmu.github.io/publications/", mode="auto")],
    notes="SHRED Lab site live. Undated alumni/previous-interns are recorded since lab was founded at CMU ~2019-2020 (Hapkit-era papers 2020). Single-name intern 'Ana' skipped. Wayback in shared back-off; no captures read. Publications auto mode mixes some abstract sentences as titles.",
    blocked=[],
)

RM = "https://www.cs.cmu.edu/~rubenm"
D["Ruben Martins"] = dict(
    lab_site="https://www.cs.cmu.edu/~rubenm/",
    people_page=RM,
    people_pages=[RM],
    members=[
        M("Alvaro Silva", "phd", None, RM, near="PhD Students"),
        M("Ricardo Brancas", "phd", None, RM, near="PhD Students"),
        M("Margarida Ferreira", "phd", None, RM, near="PhD Students"),
        M("Aidan Yang", "phd", [None, 2025], RM, near="PhD Students"),
        M("Daniel Ramos", "phd", [None, 2025], RM, near="PhD Students"),
        M("Shirley Yu", "undergraduate", [2024, 2025], RM, near="Undergraduate Students"),
        M("Jose Ferreira", "visitor", [2025, 2025], RM, q="Jose Ferreira (CMU-Portugal Visiting MSc Student, Fall 2025)"),
        M("Max Han", "undergraduate", [2025, 2025], RM, q="Max Han (REUSE, Summer 2025)"),
        M("Martim Afonso", "visitor", [2024, 2024], RM, q="Martim Afonso (CMU-Portugal Visiting MSc Student, Fall 2024)"),
        M("Sophia Kolak", "masters", [2021, 2024], RM, q="Sophia Kolak (S3D, MSc Student, 2021-2024)"),
        M("Joao Sa", "visitor", [2023, 2023], RM, q="Joao Sa (CMU-Portugal Visiting MSc Student, Fall 2023)"),
        M("Aditi Pande", "undergraduate", [2023, 2023], RM, q="Aditi Pande (07-400, Spring 2023)"),
        M("Stephanie Eristoff", "undergraduate", [2023, 2023], RM, q="Stephanie Eristoff (07-400, Spring 2023)"),
        M("Hailie Mitchell", "undergraduate", [2022, 2022], RM, q="Hailie Mitchell (REUSE, Summer 2022)"),
        M("Andreia Pereira", "visitor", [2022, 2022], RM, q="Andreia Pereira (Visiting MSc Student, Spring 2022)"),
        M("Pedro Nunes", "visitor", [2022, 2022], RM, q="Pedro Nunes (Visiting MSc Student, Spring 2022)"),
        M("Joshua Clune", "member", [2019, 2020], RM, q="Joshua Clune (Research Project, 2019-2020)"),
        M("Harutyun Rehanyan", "undergraduate", [2020, 2020], RM, q="Harutyun Rehanyan (REUSE, Summer 2020)"),
        M("Audrey Seo", "undergraduate", [2019, 2019], RM, q="Audrey Seo (REUSE, Summer 2019)"),
        M("Daniel Gibert Llaurado", "visitor", [2019, 2019], RM, q="Daniel Gibert Llaurado (Visiting PhD Student, Fall 2019)"),
        M("Aaron Meyers", "other", [2019, 2019], RM, q="Aaron Meyers (Internship, Summer 2019)"),
        M("Pedro Miguel Orvalho", "visitor", [2019, 2019], RM, q="Pedro Miguel Orvalho (Visiting MSc student, Spring 2019)"),
        M("Rodrigo Bernado", "visitor", [2019, 2019], RM, q="Rodrigo Bernado (Visiting MSc Student, Spring 2019)"),
        M("Yinglan Chen", "undergraduate", [2019, 2019], RM, q="Yinglan Chen (SCS Independent Studies, Spring 2019)"),
        M("Clara Sellke", "undergraduate", [2018, 2018], RM, q="Clara Sellke (SCS Independent Studies, Fall 2018)"),
        M("Naveen Pai", "undergraduate", [2018, 2018], RM, q="Naveen Pai (SCS Independent Studies, Fall 2018)"),
        M("David Chen", "undergraduate", [2018, 2018], RM, q="David Chen (SCS Independent Studies, Fall 2018)"),
        M("Zachary Susag", "undergraduate", [2018, 2018], RM, q="Zachary Susag (REUSE, Summer 2018)"),
        M("Avital Rabinovitch", "other", [2018, 2018], RM, q="Avital Rabinovitch (Internship, Summer 2018)"),
        M("Kaige Liu", "undergraduate", [2018, 2018], RM, q="Kaige Liu (SCS Independent Studies, Spring 2018)"),
        M("Anlun Xu", "undergraduate", [2018, 2018], RM, q="Anlun Xu (SCS Independent Studies, Spring 2018)"),
        M("Tianlei Pan", "undergraduate", [2018, 2018], RM, q="Tianlei Pan (SCS Independent Studies, Spring 2018)"),
        M("Mayank Jai", "undergraduate", [2018, 2018], RM, q="Mayank Jai (SCS Independent Studies, Spring 2018)"),
    ],
    pubs=[PUB(RM, mode="li")],
    notes="PI homepage Students section lists current/graduated PhDs, undergrads and all previous mentored students with terms (2018-2025). Roles for independent-study students approximated as undergraduate (page does not say level). Wayback not needed: page already covers 2018-2026.",
    blocked=[],
)

MR = "https://www.ri.cmu.edu/ri-faculty/matthew-t-mason/"
D["Matthew Mason"] = dict(
    lab_site="https://www.ri.cmu.edu/ri-faculty/matthew-t-mason/",
    people_page=MR,
    people_pages=[MR],
    members=[
        M("Yuemin Mao", "member", None, MR, near="current affiliates", note="current affiliate on RI faculty page"),
        M("Ankit Bhatia", "phd", None, MR, near="past phd students", note="undated on page; held PhD student, DDHand lead per page text"),
        M("Yifan Hou", "phd", None, MR, near="past phd students", note="undated; page credits his hybrid force-velocity control work 2018-2020"),
        M("Eric Huang", "phd", None, MR, near="past phd students", note="undated; contact-mode enumeration IJRR work"),
        M("Robert Paolini", "phd", None, MR, near="past phd students", note="undated; webmaster of MLab pages"),
        M("Jiaji Zhou", "phd", None, MR, near="past phd students", note="undated; ICRA 2016 best conference paper"),
        M("Xianyi Cheng", "masters", None, MR, near="past masters students", note="listed under past masters; page text says she led 2021-22 dexterous manipulation planning"),
        M("Anne Holladay", "masters", None, MR, near="past masters students"),
        M("Gilwoo Lee", "masters", None, MR, near="past masters students"),
        M("Pragna Mannam", "masters", None, MR, near="past masters students"),
    ],
    pubs=[],
    notes="Live ~mason homepage returns 403 and carries no student list anyway (Wayback 2023 capture has research/video links only); MLab people page was last updated 2011. Only source is the RI faculty page: 1 current affiliate, 15 past PhD and 5 past masters students, all undated. Recorded the 5 PhD + 4 masters corroborated by 2016+ work (page text or held rows) plus Yuemin Mao; skipped 10 undated past PhDs who graduated well before 2016 (Akella, Balasubramanian, Balkcom, Degani, W. Huang, Knepper, Lynch, Rodriguez, Srinivasa, Zeglin) and Marc Boehlen. Publications: RI page lists 162 but is a dynamic list, no page added.",
    blocked=["https://www.cs.cmu.edu/~mason/ (HTTP 403 live)"],
)

D["Roy Maxion"] = dict(
    lab_site="http://www.cs.cmu.edu/~maxion/dsl.html",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="Homepage, Dependable Systems Lab page and Recent Publications page searched: none lists students or staff. Publications list has 28 entries, all pre-2016 (no entries in the 2016-2026 window), so no pubs page added.",
    blocked=[],
)

MC = "https://www.cs.cmu.edu/~jmccann/"
D["James McCann"] = dict(
    lab_site="https://textiles.cs.cmu.edu/",
    people_page=MC,
    people_pages=[MC],
    members=[
        M("Angelica Bonilla Fominaya", "phd", None, MC, near="Students"),
        M("Yuichi Hirose", "phd", None, MC, near="Students"),
        M("Gabrielle Ohlson", "phd", None, MC, near="Students"),
        M("Jenny Lin", "phd", None, MC, near="Graduated:"),
        M("Nur Yildirim", "phd", None, MC, near="Graduated:"),
        M('Tianhong "Catherine" Yu', "masters", None, MC, near="Graduated:"),
        M("Vidya Narayanan", "phd", None, MC, near="Graduated:"),
        M("Ruta Desai", "phd", None, MC, near="Graduated:"),
        M("Ticha Sethapakdi", "masters", None, MC, near="Graduated:"),
        M("Evan Shimizu", "phd", None, MC, near="Graduated:"),
    ],
    pubs=[],
    notes="Students list is on the PI homepage (live). Lab site textiles.cs.cmu.edu fails TLS certificate verification, so its people and publications pages could not be fetched; PI joined CMU faculty May 2017 so all listed students are in window. Wayback in shared back-off at the time, no captures read.",
    blocked=["https://textiles.cs.cmu.edu/ (SSL certificate verification error)"],
)

BM = "https://cs.cmu.edu/~bmclaren/mclearnlab/team"
D["Bruce McLaren"] = dict(
    lab_site="https://www.cs.cmu.edu/~bmclaren/mclearnlab/",
    people_page=BM,
    people_pages=[BM],
    members=[
        M("Aditi Haiman", "phd", [2024, None], BM, near="Group Members"),
        M("Marshall An", "phd", [2025, None], BM, near="Group Members"),
        M("Daniel Pollock", "staff", [2023, None], BM, near="Group Members", note="Research Programmer"),
        M("Autumn Qiu", "undergraduate", [2024, None], BM, near="Group Members", note="Research Assistant, CMU B.S. student"),
        M("Angie Chi", "undergraduate", [2025, None], BM, near="Group Members", note="Research Assistant, CMU B.S. student"),
        M("Helen Yu", "other", [2026, None], BM, near="Group Members", note="Research Intern, Pitt/Sichuan student"),
        M("Leah Teffera", "staff", None, BM, near="Associated Members", note="Project Manager, Carnegie Mellon University"),
    ],
    pubs=[],
    notes="McLearn Lab team page (live) lists current members only, no alumni. Skipped external associated members (Esma Kahveci, Alessandro Pagano) and the collaborator list (Goldstein, Savelka, Kultur, Bogart, Krishnan, Sakr, Mayer). Wayback in back-off, no older team captures read. Publications live in per-project accordions on /research (not a flat list), so no pubs page added.",
    blocked=[],
)

MP = "https://labs.bio.cmu.edu/mcmanus/people/"
MCB = "https://www.cmu.edu/cbd/people/mcmanus.html"
D["C. Joel McManus"] = dict(
    lab_site="https://labs.bio.cmu.edu/mcmanus/",
    people_page=MP,
    people_pages=[MP, MCB],
    members=[
        M("Gemma May", "staff", None, MP, q="Gemma May Gemma is a researcher in the McManus Lab."),
        M("Melisa Tosiano", "phd", None, MP, q="Melisa Tosiano Melisa is a PhD candidate in the McManus lab."),
        M("Kara Delbridge", "member", None, MP, q="Kara Delbridge Kara graduated from the University of Tennessee"),
        M("Lucy Johnson", "other", None, MP, q="Lucy Johnson Lucy is a postbac in the McManus lab."),
        M("Zeqing Jiang", "undergraduate", None, MP, q="Zeqing Jiang Zeqing is an undergraduate in the McManus Lab"),
        M("Claire Dupont", "undergraduate", None, MCB, near="Lab Members"),
        M("Tate Mauzy", "undergraduate", None, MCB, near="Lab Members"),
        M("Derek Wang", "undergraduate", None, MCB, near="Lab Members"),
        M("Salini Konikkat", "postdoc", [2016, 2018], MP, near="Post-Docs"),
        M("Christina Akirtava", "phd", [None, 2023], MP, near="Ph.D Students"),
        M("Yizhu Lin", "phd", [None, 2018], MP, near="Ph.D Students"),
        M("Pieter Spealman", "phd", [None, 2017], MP, near="Ph.D Students"),
        M("Yuning Zheng", "masters", [None, 2025], MP, near="Masters Students"),
        M("Rohan Munoth", "masters", [None, 2025], MP, near="Masters Students"),
        M("Simon Chow", "masters", [None, 2023], MP, near="Masters Students"),
        M("Sanat Mishra", "masters", [None, 2023], MP, near="Masters Students"),
        M("Evan Corden", "masters", [None, 2023], MP, near="Masters Students"),
        M("Saina Mahera", "masters", [None, 2020], MP, near="Masters Students"),
        M("Ayushi Sood", "masters", [None, 2020], MP, near="Masters Students"),
        M("Brendan Wee", "masters", [None, 2019], MP, near="Masters Students"),
        M("Tianqi Tang", "masters", [None, 2018], MP, near="Masters Students"),
        M("Myles Mao", "masters", [None, 2017], MP, near="Masters Students"),
        M("Chaohao Gu", "masters", [None, 2017], MP, near="Masters Students"),
        M("Emma Kulbida", "undergraduate", [None, 2025], MP, near="Undergraduates"),
        M("Cassia Williams-Rogers", "undergraduate", [None, 2023], MP, near="Undergraduates"),
        M("Kiran Mirpuri", "undergraduate", [None, 2021], MP, near="Undergraduates"),
        M("Valerie Collins", "undergraduate", [None, 2020], MP, near="Undergraduates"),
        M("Lauren Nazzaro", "undergraduate", [None, 2019], MP, near="Undergraduates"),
        M("Hunter Kready", "undergraduate", [None, 2019], MP, near="Undergraduates"),
        M("Alexander Muralles", "undergraduate", [None, 2019], MP, near="Undergraduates"),
        M("Laura Parella", "undergraduate", [None, 2016], MP, near="Undergraduates"),
    ],
    pubs=[],
    notes="Lab site people page (live) lists 5 current members plus dated alumni; CBD profile adds 3 undergraduate researchers. Skipped alumni who left before 2016: Easwaran Ramamurthy (M.S. 2015), Alan Shteyman (2014), Tara Tappen (2014), Naveen Chandromahon (2012), Alexis Oguh (B.S. 2014). Publications page parses as journal names rather than titles (anchor mode), so no pubs page added. Wayback in back-off; not needed.",
    blocked=[],
)

D["Florian Metze"] = dict(
    lab_site="http://www.cs.cmu.edu/~fmetze/interACT/Home.html",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[PUB("http://www.cs.cmu.edu/~fmetze/interACT/Publications_files/publications/node1.html", mode="auto")],
    notes="PI homepage (interACT, LTI) has no student/group list and links only course pages; web search found no group roster (he has been on leave at Meta AI since ~2022). Publications node1 page parses well in auto mode (anchor titles, 35 in window).",
    blocked=[],
)

D["Gary Miller"] = dict(
    lab_site="http://www.cs.cmu.edu/~glmiller/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="Homepage lists contact, courses, projects, talks and publications only (last modified 2012), no students. Publications sort_date page parses to '[pdf]' labels and author names rather than titles in every mode (anchor/block/li), so it was not added.",
    blocked=[],
)

D["Nathan Michael"] = dict(
    lab_site="http://nmichael.frc.ri.cmu.edu/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="Lab (RISLab) site nmichael.frc.ri.cmu.edu is dead (connect timeout); PI left CMU for Shield AI and www.ri.cmu.edu/ri-faculty/nathan-michael/ is 404. Live rislab.org/people is now Wennie Tabib's lab (current members + alumni 2023-2026), not Michael's group, so none of it was recorded. Wayback has 5 captures of the old lab homepage (2013-2017, e.g. 20170426010803) and its people page was never read because Wayback stayed in shared back-off (wayback-backoff errors on every attempt); rislab.org/people has no CDX captures. Needs a later Wayback pass for Michael-era members.",
    blocked=[],
)
