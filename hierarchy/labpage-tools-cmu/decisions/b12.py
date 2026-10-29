from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Ralph Hollis
HL = "http://www.msl.ri.cmu.edu/people/"
HLRI = "https://www.ri.cmu.edu/ri-faculty/ralph-hollis/"
D["Ralph Hollis"] = dict(
    lab_site="http://www.msl.ri.cmu.edu/",
    people_page=HL,
    people_pages=[HL, HLRI],
    members=[
        M("Roberto Shu", "phd", None, HL, near="Graduate Students"),
        M("Shreyas Srivatchan", "masters", None, HL, near="Graduate Students",
          note="listed under Graduate Students (Robotics)"),
        M("Ryan Lucht", "undergraduate", None, HL, near="Undergraduate Students"),
        M("Michael Shomin", "phd", [None, 2016], HL, q="Michael Shomin, Ph.D., Robotics, 2016"),
        M("Greg Seyfarth", "masters", [None, 2016], HL, q="Greg Seyfarth, M.S., Robotics, 2016"),
    ],
    pubs=[],
    notes=("MSL site www.msl.ri.cmu.edu (last-updated stamp 2006 but the people page is maintained: lists Hollis as "
           "Professor Emeritus, grad students Shu and Srivatchan, undergrad Lucht, graduates Shomin PhD 2016 and "
           "Seyfarth MS 2016). RI profile past-student lists are undated (past PhD: Berkelman, Butler, Nagarajan, "
           "Quaid, Shomin, Shu, Unger; past masters: Dai, DeLuca, Fries, Liu, Mampetta, Mondal, Schearer, Schlender, "
           "Seyfarth, Srivatchan, Tappeiner, Varadharajan); undated alumni not seen as current in 2016+ were skipped "
           "(Jimmy Dai, Xiaohan Liu, Sayan Mondal are already held but have no 2016+ evidence on these pages). "
           "Pre-2016 MSL graduates (Bhatia 2014, Vaidya 2014, Nagarajan 2012, etc.) skipped. Associated faculty "
           "Kantor, Klatzky, Forlizzi not members. Publications page parses (134 entries) but only 1 in-window "
           "paper, already held, so no PUB added."),
    blocked=[],
)

# ---------------------------------------------------------------- Ken Holstein
CO = "https://www.thecoalalab.com/"
HC = "https://hcii.cmu.edu/people/ken-holstein"
_ks = dict(
    lab_site="https://www.thecoalalab.com/",
    people_page=CO,
    people_pages=[CO, HC],
    members=[
        M("Tzu-Sheng Kuo", "phd", None, CO, q="Tzu-Sheng Kuo PhD Researcher @ CMU",
          note="HCII advisee; co-advised with Haiyi Zhu"),
        M("Alicia DeVrio", "phd", [None, 2026], CO, near="CoALA Alums"),
        M("Luke Guerdan", "phd", [None, 2026], CO, near="CoALA Alums"),
        M("Frederic Gmeiner", "phd", [None, 2026], CO, near="CoALA Alums"),
        M("Anna Kawakami", "phd", [None, 2026], CO, near="CoALA Alums"),
        M("Wesley Hanwen Deng", "phd", [None, 2026], CO, near="CoALA Alums"),
        M("Charvi Rastogi", "phd", [None, 2023], CO, near="CoALA Alums"),
        M("Devansh Saxena", "postdoc", [None, 2025], CO, near="CoALA Alums"),
        M("LuEttaMae Lawrence", "postdoc", [None, 2021], CO, near="CoALA Alums"),
        M("Alex Ahmed", "postdoc", [None, 2021], CO, near="CoALA Alums"),
    ],
    pubs=[],
    notes=("Holstein is moving the CoALA Lab to EPFL (site header 'EPFL CoALA Lab'; lab director). Live CoALA "
           "people page lists current EPFL members (Rotter, Stec, Chavigny, Wang, Sotnikova, Zhang, Badr; not CMU, "
           "skipped) and CMU alumni with 'CMU PhD/Postdoc' year tags, which were recorded. Only Tzu-Sheng Kuo is "
           "still at CMU. HCII profile Advisees lists only Kuo. Wayback captures of the lab site could not be read "
           "(wayback back-off). Publications: SSRN link robots-disallowed, no lab publications page."),
    blocked=["https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4884604 (robots-disallowed)"],
)
D["Ken Holstein"] = dict(_ks)
D["Kenneth J Holstein"] = dict(_ks)

# ---------------------------------------------------------------- Jason Hong
CH = WB + "20190122015053id_/http://cmuchimps.org:80/people"
D["Jason Hong"] = dict(
    lab_site="http://www.cs.cmu.edu/~jasonh/",
    people_page=CH,
    people_pages=[CH],
    members=[
        M("Afsaneh Doryab", "postdoc", None, CH, q="Afsaneh Doryab Postdoctoral Researcher"),
        M("Eiji Hayashi", "phd", None, CH, q="Eiji Hayashi Ph.D. Student"),
        M("Song Luan", "phd", None, CH, q="Song Luan Ph.D. Student"),
        M("Dan Tasse", "phd", None, CH, q="Dan Tasse Ph.D. Student"),
        M("Jason Wiese", "phd", None, CH, q="Jason Wiese Ph.D. Student"),
        M("Michael Villena", "staff", None, CH, q="Michael Villena Research Staff"),
    ],
    pubs=[],
    notes=("CHIMPS Lab site cmuchimps.org is dead (connection error); used the Jan 2019 Wayback capture of /people "
           "(current: Doryab, Hayashi, Luan, Tasse, Wiese, Villena). The 2016, 2017, 2018 captures were listed in "
           "CDX but refused by Wayback (back-off), so students of 2016-2018 and 2020-2026 are not covered. 19 "
           "undated alumni on that page were skipped (e.g. Sauvik Das, already held; Amini, Chau, Lindqvist, "
           "Kywe...). Hong's homepage (emeritus since 2024) has no student list; its publications are Google "
           "Scholar links only (off limits) so no PUB. HCII profile has no advisees."),
    blocked=[],
)

# ---------------------------------------------------------------- Eduard Hovy
D["Eduard Hovy"] = dict(
    lab_site="https://www.cs.cmu.edu/~hovy/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[PUB("https://www.cs.cmu.edu/~hovy/publications.html", mode="auto")],
    notes=("No usable member list: lti.cmu.edu faculty profile has no advisees or lab links; cs.cmu.edu/~hovy is a "
           "frameset with no student page (students/people pages 404); the projects site edvisees.cs.cmu.edu is dead "
           "and its Wayback captures (2017-2019) are empty frames. Wayback back-off limited further attempts. "
           "Publications page (402 entries, bold titles, 15 in-window missing in preview) added."),
    blocked=[],
)

# ---------------------------------------------------------------- Scott E Hudson
D["Scott E Hudson"] = dict(
    lab_site="http://www.cs.cmu.edu/~hudson/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes=("Homepage www.cs.cmu.edu/~hudson/ has a prose PhD Students paragraph (alumni destinations only) and no "
           "names of students; HCII profile lists no advisees and no lab site. No member list or publication page "
           "exists (papers are linked only via ACM DL / Google Scholar, the latter off limits)."),
    blocked=[],
)

# ---------------------------------------------------------------- Jeffrey Ichnowski
IC = "https://www.ri.cmu.edu/ri-faculty/jeffrey-ichnowski/"
_ic = dict(
    lab_site="https://ichnow.ski/",
    people_page=IC,
    people_pages=[IC],
    members=[
        M("Hongyi Chen", "phd", None, IC, near="current phd students"),
        M("Bardienus Duisterhof", "phd", None, IC, near="current phd students"),
        M("Adam Hung", "phd", None, IC, near="current phd students"),
        M("Yuemin Mao", "phd", None, IC, near="current phd students"),
        M("Kalie Ching", "masters", None, IC, near="current masters students"),
        M("Arthur Jakobsson", "masters", None, IC, near="current masters students"),
        M("Romina Mir", "member", None, IC, near="current affiliates"),
        M("Richard Xu", "member", None, IC, near="current affiliates"),
        M("Uksang Yoo", "phd", None, IC, near="past phd students"),
        M("Dingkun Guo", "masters", None, IC, near="past masters students"),
        M("Jeffrey Ke", "masters", None, IC, near="past masters students"),
        M("Yunchao Yao", "masters", None, IC, near="past masters students"),
    ],
    pubs=[PUB("https://ichnow.ski", mode="auto")],
    notes=("No lab website: PI homepage ichnow.ski has no student list; members come from the RI faculty profile "
           "(current PhD/masters/affiliates, past PhD/masters, undated). The PI homepage publication list mixes "
           "Berkeley-era papers; affiliation is left to the other tool. Other search hits (MRSD team G 2026 and MSCV "
           "project students such as Aviral Agrawal) are course-project teams, not recorded."),
    blocked=[],
)
D["Jeff Ichnowski"] = dict(_ic)
D["Jeffrey Ichnowski"] = dict(_ic)

# ---------------------------------------------------------------- Andrew Ilyas
IL = "https://andrewilyas.com/"
D["Andrew Ilyas"] = dict(
    lab_site="https://andrewilyas.com/",
    people_page=IL,
    people_pages=[IL],
    members=[
        M("Jiayun (Jeffrey) Wu", "phd", None, IL, near="Students", note="co-advised with Steven Wu"),
        M("Matan Shtepel", "phd", None, IL, near="Students"),
        M("Tori Qiu", "phd", None, IL, near="Students"),
    ],
    pubs=[PUB("https://andrewilyas.com", mode="auto")],
    notes=("Ilyas joined CMU in January 2026 (per homepage). Homepage 'Students' section lists three students, "
           "role not stated (recorded as phd by default of the section; may be mixed). No separate lab site. "
           "Homepage publications are mostly MIT/Stanford-era work."),
    blocked=[],
)

# ---------------------------------------------------------------- Daphne Ippolito
IP = "https://www.daphnei.com/group"
D["Daphne Ippolito"] = dict(
    lab_site="https://www.daphnei.com/",
    people_page=IP,
    people_pages=[IP],
    members=[
        M("Noam Dahan", "phd", None, IP, near="Current PhD Students"),
        M("Harshita Diddee", "phd", None, IP, near="Current PhD Students"),
        M("Barry Wang", "phd", None, IP, near="Current PhD Students"),
        M("Yiming Zhang", "phd", None, IP, near="Current PhD Students", note="on leave at Anthropic"),
        M("Dani Roytburg", "masters", None, IP, near="Current Masters Students", note="MSML"),
        M("Dishank Jain", "masters", None, IP, near="Current Masters Students", note="MIIS"),
        M("Hamzah Hamad", "masters", None, IP, near="Current Masters Students", note="M5LT"),
        M("Ravindra Telidevara", "masters", None, IP, near="Current Masters Students", note="MIIS"),
        M("Shreya Sridhar", "masters", None, IP, near="Graduated Students", note="MSML, now ML engineer at EvenUp as of 2026"),
        M("Xinyue Liu", "masters", [None, 2025], IP, near="Graduated Students", note="MCDS; started PhD at Stony Brook Fall 2025"),
        M("Vinay Samuel", "undergraduate", [None, 2025], IP, near="Graduated Students", note="BS; started Masters at UMD Fall 2025"),
        M("Janny Mongkolsupawan", "masters", None, IP, near="Graduated Students", note="MSAII"),
    ],
    pubs=[],
    notes=("Group page on daphnei.com read live. Wayback captures of the group page (2024, 2025) could not be read "
           "(wayback back-off), so alumni are only those on the live page. Research page lists topics, no "
           "publication list, so no PUB."),
    blocked=[],
)

# ---------------------------------------------------------------- Olexandr Isayev
IS = "https://groups.chem.cmu.edu/isayev/people/"
IS25 = WB + "20250114050337id_/https://groups.chem.cmu.edu/isayev/people/"
D["Olexandr Isayev"] = dict(
    lab_site="https://groups.chem.cmu.edu/isayev/",
    people_page=IS,
    people_pages=[IS, IS25],
    members=[
        M("Dylan Anstine", "postdoc", None, IS, near="Researchers"),
        M("Liliana Gallegos", "postdoc", None, IS, near="Researchers"),
        M("Hattie Gokcan", "staff", None, IS, near="Researchers", note="Research Associate"),
        M("Bhupalee Kalita", "postdoc", None, IS, near="Researchers"),
        M("Peikun Zheng", "staff", None, IS, near="Researchers", note="Research Associate"),
        M("Tetiana Zubatiuk", "staff", None, IS, near="Researchers", note="Research Associate"),
        M("Polina Avdiunina", "phd", None, IS, near="Graduate Students"),
        M("Ilkwon Cho", "phd", None, IS, near="Graduate Students"),
        M("Runtian Gao", "phd", None, IS, near="Graduate Students"),
        M("Zhen Liu", "phd", None, IS, near="Graduate Students"),
        M("Kamal Singh Nayal", "phd", None, IS, near="Graduate Students"),
        M("Shuhao Zhang", "phd", None, IS, near="Graduate Students"),
    ],
    pubs=[],
    notes=("Team page on groups.chem.cmu.edu/isayev (Chemistry). The page and its publications page carry injected "
           "multilingual spam teasers (ignored). The 2022 and 2024 Wayback captures show an empty Team page "
           "(content loaded dynamically); the Jan 2025 capture matches the live list. Publications page has no "
           "parseable paper list, so no PUB."),
    blocked=[],
)

# ---------------------------------------------------------------- Aayush Jain
AJ = "https://sites.google.com/view/aayushjain/home"
AJ23 = WB + "20230301173507id_/https://sites.google.com/view/aayushjain/home"
D["Aayush Jain"] = dict(
    lab_site=AJ,
    people_page=AJ,
    people_pages=[AJ, AJ23],
    members=[
        M("Georgios Chardouvelis", "phd", None, AJ23, near="Students and Postdocs:",
          note="co-advised with Vipul Goyal; listed on the Mar 2023 capture, absent from later captures"),
        M("Quang Dao", "phd", None, AJ, near="Students:", note="co-advised with Riad Wahby"),
        M("Noah Singer", "phd", None, AJ, near="Students:", note="co-advised with Ryan O'Donnell"),
        M("Sagnik Saha", "phd", None, AJ, near="Students:"),
        M("Nuozhou Sun", "phd", None, AJ, near="Students:"),
        M("Mitali Bafna", "postdoc", [2022, 2023], AJ, near="Postdocs:"),
        M("Rex Fernando", "postdoc", [2022, 2023], AJ, near="Postdocs:"),
    ],
    pubs=[PUB(AJ, mode="li")],
    notes=("Homepage lists students and past postdocs with dates. Read the Mar 2023 and Jun 2025 Wayback captures: 2023 adds Georgios Chardouvelis; the 2025 capture matches the live list minus Nuozhou Sun. Publications list parsed in li mode."),
    blocked=[],
)
