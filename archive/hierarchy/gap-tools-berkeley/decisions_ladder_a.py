"""Berkeley gap decisions, worker ladder_a (11 active ladder PIs), 2026-10-21/22.

Bamman, Nelson, Shao, Chasins, Crooks, Salehi, Guruswami, Wright, Alaa, Suhr, Yala.
Evidence specs are resolved and re-verified by build.py; see dhelp.py for the helpers.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import sys

sys.path.insert(0, str(P.HIERARCHY / 'gap-tools-berkeley'))
from dhelp import *  # noqa: E402,F401,F403
import capstore  # noqa: E402

D = {}
_txt = {}


def _text(url):
    if url not in _txt:
        r = capstore.find_capture(url)
        _txt[url] = capstore.page_text(r[0]) if r else ""
    return _txt[url]


def hs(url, head, entry, maxspan=650, **kw):
    """Quote spanning a section heading through an entry when short enough, else the entry alone."""
    t = _text(url)
    j = t.find(entry)
    i = t.rfind(head, 0, j) if j >= 0 else -1  # the heading occurrence nearest before the entry
    if i >= 0 and (j + len(entry) - i) <= maxspan:
        if t.find(head) == i:
            return SE(url, head, entry, **kw)
        aft = t[max(0, i - 60):i]
        if aft and t.find(aft) == i - len(aft) and t.find(entry, i + len(head)) == j:
            return SE(url, head, entry, after=aft, **kw)
    return Q(url, entry, **kw)


def orcid_person(oid, name):
    return Q(f"https://orcid.org/{oid}/person.json", f'"displayName":"{name}"', raw=True)


def VER(url, q=None, s=None, e=None, note=""):
    ev = Q(url, q) if q is not None else SE(url, s, e)
    return ID("openalex_verified_by_publication_list", ev, note)


# ============================================================================ David Bamman
BAM26 = WB + "20260308195019id_/https://people.ischool.berkeley.edu/~dbamman/"
BAM19 = WB + "20191119113012id_/http://people.ischool.berkeley.edu/~dbamman/"
BAMG = "I lead an amazing research group:"
MEH = WB + "20260308163604id_/https://www.ischool.berkeley.edu/people/nikita-mehandru"
D["David Bamman"] = dict(
    status="pi",
    status_ev=[SE(BAM26, "Bamman's work is supported by", "I lead an amazing research group: Svenja Guhr , postdoctoral fellow")],
    students=[
        ST("Svenja Guhr", "postdoc", [2025, 2026], hs(BAM26, BAMG, "Svenja Guhr , postdoctoral fellow")),
        ST("Kent Chang", "phd", [2020, 2026], hs(BAM26, BAMG, "Kent Chang , PhD student"),
           note="listed as PhD student in the 2020-2026 captures"),
        ST("Nikita Mehandru", "phd", [2022, 2026], SE(MEH, "Nikita Mehandru PhD Student", "David Bamman Associate Professor"),
           must=["Mehandru", "Bamman"], note="I School profile names advisors Steven Weber and David Bamman; also on Alaa Lab page"),
        ST("Naitian Zhou", "phd", [2022, 2026], hs(BAM26, BAMG, "Naitian Zhou , PhD student")),
        ST("Dan Hickey", "phd", [2024, 2026], hs(BAM26, BAMG, "Dan Hickey , PhD student")),
        ST("Apolline Tardy", "phd", [2025, 2026], hs(BAM26, BAMG, "Apolline Tardy (co-advised with Kimiko Ryokai), PhD student")),
        ST("Mackenzie Cramer", "masters", [2025, 2026], hs(BAM26, BAMG, "Mackenzie Cramer, MIMS student")),
        ST("Lucy Li", "phd", [2019, 2025], hs(BAM26, "Alumni", "Lucy Li , PhD 2025")),
        ST("Sandeep Soni", "postdoc", [2021, 2022], hs(BAM26, "Alumni", "Sandeep Soni , Postdoc")),
        ST("Jon Gillick", "phd", [2019, 2022], hs(BAM26, "Alumni", "Jon Gillick , PhD 2022")),
        ST("Matt Sims", "postdoc", [2019, 2020], hs(BAM26, "Alumni", "Matt Sims, Postdoc")),
        ST("Masha Belyi", "masters", [2019, 2019], hs(BAM19, "Research group", "Masha Belyi, MIMS")),
        ST("Olivia Lewke", "undergraduate", [2019, 2019], hs(BAM19, "Research group", "Olivia Lewke, undergraduate")),
        ST("Anya Mansoor", "undergraduate", [2019, 2019], hs(BAM19, "Research group", "Anya Mansoor, undergraduate")),
        ST("Aubrey Williams", "undergraduate", [2019, 2019], hs(BAM19, "Research group", "Aubrey Williams, undergraduate")),
    ],
    identity=dict(
        orcid=["0009-0003-1171-9408"], openalex=["A5058212934"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5058212934", "David Bamman"),
               "OpenAlex author A5058212934 (121 works; last known UC Berkeley); carries ORCID 0009-0003-1171-9408."),
            VER(BAM26, 'Bamman (2023), "Speak, Memory: An Archaeology of Books Known to ChatGPT/GPT-4',
                note="W4389519044 (2023) of A5058212934; 46 of its 2016+ titles match his homepage list."),
            VER(BAM26, 'Bamman (2021), "Gender and Representation Bias in GPT-3 Generated Stories', note="W3168771811 (2021)."),
            VER(BAM26, 'Bamman (2020), "Measuring Information Propagation in Literary Social Networks', note="W3023297993 (2020)."),
            VER(BAM26, 'Bamman (2019), "Literary Event Detection', note="W2952411148 (2019)."),
            ID("orcid_record", orcid_person("0009-0003-1171-9408", "David Bamman"),
               "ORCID record names David Bamman; its affiliations (affiliationGroups.json, sha256 d2a61a6f34b32d5f...) list "
               "EMPLOYMENT University of California, Berkeley, School of Information, Associate Professor, 2015-."),
        ]),
    appt=[Q(BAM26, "David Bamman is an associate professor in the School of Information at UC Berkeley")],
    notes=("Primary appointment is the School of Information (ORCID employment 2015-); EECS affiliated appointment, BAIR. "
           "His group list and alumni (homepage, Wayback 2019-2026; the live people.ischool.berkeley.edu path is "
           "robots-disallowed for our agent) give 15 Berkeley advisees. The EECS dissertations page is 404 because his PhD "
           "students are I School students. OpenAlex A5058212934 verified (46 title matches)."),
)

# ============================================================================ Jelani Nelson
NEL = "https://people.eecs.berkeley.edu/~minilek/"
NELP = NEL + "publications/"
NELCV = NEL + "cv.pdf"
_nel_diss = diss_students("Jelani Nelson")
D["Jelani Nelson"] = dict(
    status="pi",
    status_ev=[diss_status("Jelani Nelson"),
               SE(NEL, "Jelani Nelson Professor, Department of EECS", "Current postdoc: Ce Jin (Miller Fellow)",
                  must=["Nelson", "Singhal"])],
    students=_nel_diss + [
        ST("Mihir Singhal", "phd", None, SE(NEL, "Jelani Nelson Professor, Department of EECS",
                                            "Current student: Mihir Singhal (co-advised with Venkatesan Guruswami )")),
        ST("Ce Jin", "postdoc", None, SE(NEL, "Current student: Mihir Singhal", "Current postdoc: Ce Jin (Miller Fellow)")),
        ST("Samson Zhou", "postdoc", [2023, 2023], Q(NELCV, "Postdoctoral Fellows April ’23–July ’23 Samson Zhou"),
           note="CV: co-hosted with Vladimir Braverman at Rice University"),
        ST("Shay Golan", "postdoc", [2021, 2022], hs(NELCV, "Postdoctoral Fellows", "Shay Golan October ’21–October ’22")),
        ST("Jan van den Brand", "postdoc", [2021, 2022], hs(NELCV, "Postdoctoral Fellows", "August ’21–May ’22 Jan van den Brand"),
           must=["van den Brand"], note="CV: Simons Fellow"),
        ST("Paris Syminelakis", "postdoc", [2019, 2020], hs(NELCV, "Postdoctoral Fellows", "Paris Syminelakis September ’19–September ’20")),
        ST("Matthew Ding", "undergraduate", [2024, 2024],
           SE(NELCV, "Undergraduate and High School Research Advising Matthew Ding", "UC Berkeley, Class of 2025")),
    ],
    identity=dict(
        orcid=["0000-0001-7370-3733"], openalex=["A5109135732"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5109135732", "Jelani Nelson"),
               "OpenAlex author A5109135732 (143 works; UC Berkeley 2017-2026 in its affiliations)."),
            VER(NELP, "Nelson. Terminal embeddings in sublinear time",
                note="W4214880130 (2022) of A5109135732; 38 of its 2016+ titles match his publications page."),
            VER(NELP, "Nelson, Huacheng Yu . Optimal bounds for approximate counting", note="W3095925971 (2022)."),
            VER(NELP, "Nelson, Yinzhan Xu . Differentially Private All-Pairs Shortest Path Distances: Improved Algorithms and Lower Bounds",
                note="W4316652290 (2023)."),
            VER(NELP, "Nelson, Uri Stemmer . Heavy hitters and the structure of local privacy", note="W2963424903 (2018)."),
            ID("orcid_record", orcid_person("0000-0001-7370-3733", "Jelani Nelson"),
               "ORCID record names Jelani Nelson; affiliationGroups.json (sha256 573092149ee89b5b...) lists EMPLOYMENT "
               "UC Berkeley, EECS, Professor, 2019-."),
        ]),
    appt=[SE(NELCV, "Jelani Nelson Curriculum Vitae",
             "Professor, Department of Electrical Engineering and Computer Sciences, July 2019–present")],
    notes=("EECS Professor since July 2019 (CV); Harvard 2013-2019; EECS chair July 2025-; homepage says currently on leave "
           "at Anthropic. Students: 4 EECS dissertations (2024-2026), current PhD student Mihir Singhal (co-advised with "
           "Guruswami), current Miller postdoc Ce Jin, 4 Berkeley-era CV postdocs (Sep 2019 onward) and one Berkeley "
           "undergraduate. Harvard-era students/postdocs on his pages (Blasiok, Nakos, Zhengyu Wang, Kyng, Luh, Huacheng Yu, "
           "Pachocki, Yi Li) are excluded. OpenAlex A5109135732 verified (38 title matches)."),
)

# ============================================================================ Sophia Shao
SH = "https://people.eecs.berkeley.edu/~ysshao/"
SHT = SH + "students.html"
SHP = SH + "publication.html"
SHCV = SH + "assets/cv/shao-cv.pdf"
SHD = "A DVISING"
TR = "https://www2.eecs.berkeley.edu/Pubs/TechRpts/"
_sh_diss = diss_students("Sophia Shao")
D["Sophia Shao"] = dict(
    status="pi",
    status_ev=[diss_status("Sophia Shao"),
               SE(SH + "index.html", "Yakun Sophia Shao The Class of 1951 Chair", "Associate Professor EECS, UC Berkeley")],
    students=_sh_diss + [
        ST("Man (Amanda) Shi", "postdoc", None, hs(SHT, "PostDoc Researcher", "Man (Amanda) Shi"), must=["Shi"]),
        ST("Vikram Jain", "postdoc", [2023, 2025], hs(SHCV, SHD, "Postdoc Vikram Jain (with Nikolic), 2023"),
           note="team page: now Purdue University (2025)"),
        ST("Yufeng Chi", "phd", [2023, None], hs(SHCV, SHD, "Yufeng Chi (with Nikolic), 2023")),
        ST("Junsun Choi", "phd", [2021, None], hs(SHCV, SHD, "Junsun Choi (with Nikolic), 2021")),
        ST("Kris Dong", "phd", [2023, None], hs(SHCV, SHD, "Kris Dong (with Fletcher), 2023")),
        ST("Prashanth Ganesh", "phd", [2021, None], hs(SHCV, SHD, "Prashanth Ganesh, 2021")),
        ST("Roger Hsiao", "phd", [2021, None], hs(SHCV, SHD, "Roger Hsiao (with Demmel), 2021")),
        ST("Dima Nikiforov", "phd", [2020, None], hs(SHCV, SHD, "Dima Nikiforov (with Nikolic), 2020")),
        ST("Shashank Anand", "phd", None, hs(SHT, "Ph.D. Students", "Shashank Anand")),
        ST("Richard Yan", "phd", None, hs(SHT, "Ph.D. Students", "Richard Yan"),
           note="team page: former M.S./undergraduate researcher (2024), now her Ph.D. student"),
        ST("Chengyi Lux Zhang", "phd", None, hs(SHT, "Ph.D. Students", "Chengyi Lux Zhang"), must=["Zhang"]),
        ST("Jingyi Xu", "masters", [None, 2025], SE(TR + "2025/EECS-2025-190.html", "Advisors: Borivoje Nikolic and Sophia Shao",
                                                   "Author= {Xu, Jingyi")),
        ST("Avinash Nandakumar", "masters", [None, 2022], SE(TR + "2022/EECS-2022-100.html", "Advisors: Sophia Shao",
                                                            "Author= {Nandakumar, Avinash")),
        ST("Zekai Lin", "masters", [2024, 2025], hs(SHCV, "Current Masters Students", "Zekai Lin, 2024")),
        ST("Branden Roberts", "masters", [2024, 2025], hs(SHCV, "Current Masters Students", "Branden Roberts, 2024"),
           note="team page spells 'Brendan Roberts'"),
        ST("Jonathan Wang", "masters", [2024, 2025], hs(SHCV, "Current Masters Students", "Jonathan Wang, 2024")),
        ST("Joshua You", "undergraduate", [2022, None], hs(SHCV, "Current Undergraduate Researchers", "Joshua You, 2022")),
        ST("Agustin N. Coppari Hollmann", "member", [2025, None], hs(SHT, "M.S. and Undergraduate Researchers", "Agustin N. Coppari Hollmann 2025"),
           must=["Hollmann"], note="team page heading 'M.S. and Undergraduate Researchers'"),
        ST("Minh Ngugen", "member", [2023, None], hs(SHT, "M.S. and Undergraduate Researchers", "Minh Ngugen 2023"),
           note="team page heading 'M.S. and Undergraduate Researchers' (spelling as on page)"),
        ST("Leena Elzeiny", "member", [None, 2024], hs(SHT, "Former M.S. and Undergraduate Researchers", "Leena Elzeiny -> SambaNova")),
        ST("Simon Guo", "member", [None, 2023], hs(SHT, "Former M.S. and Undergraduate Researchers", "Simon Guo -> Ph.D. Student at Stanford")),
        ST("Divija Hasteer", "member", [None, 2023], hs(SHT, "Former M.S. and Undergraduate Researchers", "Divija Hasteer -> M.S. Student at Stanford 2023")),
        ST("Kareem Ahmad", "member", [None, 2021], hs(SHT, "Former M.S. and Undergraduate Researchers", "Kareem Ahmad -> Apple 2021")),
        ST("Thomas Norell", "member", [None, 2020], hs(SHT, "Former M.S. and Undergraduate Researchers", "Thomas Norell -> AWS")),
        ST("Patrick Wang", "member", [None, 2020], hs(SHT, "Former M.S. and Undergraduate Researchers", "Patrick Wang -> NVIDIA")),
    ],
    identity=dict(
        orcid=[], openalex=["A5008683881"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5008683881", "Yakun Sophia Shao"),
               "OpenAlex author A5008683881 'Yakun Sophia Shao' (96 works; last known UC Berkeley)."),
            VER(SHP, "Timeloop: A Systematic Approach to DNN Accelerator Evaluation Angshuman Parashar, Priyanka Raina, Yakun Sophia Shao",
                note="W2940862705 (2019) of A5008683881; 29 of its 2016+ titles match her publications page."),
            VER(SHP, "MAGNet: A Modular Accelerator Generator for Neural Networks Rangharajan Venkatesan, Yakun Sophia Shao",
                note="W2997929983 (2019)."),
            VER(SHP, "SNAP: An Efficient Sparse Neural Acceleration Processor for Unstructured Sparse Deep Neural Network Inference Jie-Fang Zhang, Ching-En Lee, Chester Liu, Yakun Sophia Shao",
                note="W3114479342 (2020)."),
            VER(SHP, "Co-Designing Accelerators and SoC Interfaces using gem5-Aladdin Yakun Sophia Shao", note="W4249553981 (2016)."),
        ]),
    appt=[SE(SH + "index.html", "Yakun Sophia Shao The Class of 1951 Chair",
             "I am an Associate Professor at the Electrical Engineering and Computer Sciences department of University of California, Berkeley")],
    pi_must=["Shao"],
    notes=("Byline name is 'Yakun Sophia Shao' (OpenAlex A5008683881); the pipeline's name 'Sophia Shao' misses that byline, "
           "which explains name_hits=7 and no anchor -- add the alias. CV (shao-cv.pdf): Assistant Professor UC Berkeley "
           "2019-2024, Associate Professor 2024- (the CV's name heading is letter-spaced, so not quotable). Small OpenAlex "
           "'Sophia Shao' ids A5109711999 (robotics papers; 1 title match), A5087003952 and A5128232650 (0 matches) are left "
           "unanchored. ORCID 0000-0003-1811-5407 names 'Yakun Sophia Shao' but lists no affiliation, so it is not anchored. "
           "Team-page 'Former Ph.D. Students and Collaborators' Alon Amid, Grace Dinh, Hasan Genc, Qijing (Jenny) Huang and "
           "Jerry Zhao are excluded: her CV names other primary advisors (Asanovic, Demmel, Wawrzynek)."),
)

# ============================================================================ Sarah Chasins
PL = "https://plait-lab.org/"
PLH = "People Sarah E. Chasins Faculty"


def _pl(name, label, role, years=None, note=None, must=None):
    head = "Alums" if label in ("MS", "PhD", "Undergraduate", "Assistant") and name in _PL_ALUMS else PLH
    entry = f"{name} , {label}" if head == "Alums" else f"{name} {label}"
    return ST(name, role, years, hs(PL, head, entry), note=note, must=must)


_PL_ALUMS = {"Laila Walker", "Pragya Kallanagoudar", "Angela Bi", "Xiaorui Liu", "Rolando Garcia", "Jacob Yim",
             "Jeremy Ferguson", "Sora Kanosue", "Lisa Rennels", "Kevin Ye", "Arda Demirci", "Selina Kim",
             "Rajavi Mishra", "Hannah Perlstein", "Rebecca Hicke"}
D["Sarah Chasins"] = dict(
    status="pi",
    status_ev=[diss_status("Sarah Chasins"), Q(PL, "People Sarah E. Chasins Faculty Justin Lubin PhD Candidate")],
    students=diss_students("Sarah Chasins") + [
        _pl("Justin Lubin", "PhD Candidate", "phd"),
        _pl("David Minh-Duy Cao", "PhD Student", "phd", must=["Cao"]),
        _pl("Jay Lee", "PhD Student", "phd"),
        _pl("Marlena Preigh", "PhD Student", "phd"),
        _pl("Eric Rawn", "PhD Student", "phd"),
        _pl("Parker Ziegler", "PhD Student", "phd"),
        _pl("Slim Lim", "PhD Student (on leave)", "phd"),
        _pl("Arfa Momin", "Undergraduate Student", "undergraduate"),
        _pl("Rolando Garcia", "PhD", "phd"),
        _pl("Jacob Yim", "MS", "masters"),
        _pl("Jeremy Ferguson", "MS", "masters"),
        _pl("Sora Kanosue", "MS", "masters"),
        _pl("Lisa Rennels", "MS", "masters"),
        ST("Gabriel Matute", "masters", [None, 2024], SE(TR + "2024/EECS-2024-93.html", "Advisors: Alvin Cheung and Sarah Chasins",
                                                        "Author= {Matute, Gabriel")),
        ST("Dhanya Jayagopal", "masters", [None, 2022], SE(TR + "2022/EECS-2022-59.html", "Advisors: Sarah Chasins",
                                                          "Author= {Jayagopal, Dhanya")),
        _pl("Laila Walker", "Undergraduate", "undergraduate"),
        _pl("Pragya Kallanagoudar", "Undergraduate", "undergraduate"),
        _pl("Angela Bi", "Undergraduate", "undergraduate"),
        _pl("Xiaorui Liu", "Undergraduate", "undergraduate"),
        _pl("Kevin Ye", "Undergraduate", "undergraduate"),
        _pl("Arda Demirci", "Undergraduate", "undergraduate"),
        _pl("Selina Kim", "Undergraduate", "undergraduate"),
        _pl("Rajavi Mishra", "Undergraduate", "undergraduate"),
        _pl("Hannah Perlstein", "Undergraduate", "undergraduate"),
        _pl("Rebecca Hicke", "Undergraduate", "undergraduate"),
    ],
    identity=dict(
        orcid=["0000-0003-0557-3580"], openalex=["A5090728813"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5090728813", "Sarah Chasins"),
               "OpenAlex author A5090728813 (86 works; last known UC Berkeley)."),
            VER("https://schasins.com/papers/", "Pagebreaks: Multi-Cell Scopes in Computational Notebooks Eric Rawn , Sarah E. Chasins",
                note="W4409736320 (2025) of A5090728813; 27 of its 2016+ titles match her papers page."),
            VER("https://schasins.com/papers/", "A Need-Finding Study with Users of Geospatial Data Parker Ziegler , Sarah E. Chasins",
                note="W4366547507 (2023)."),
            VER("https://schasins.com/papers/", "How Statically-Typed Functional Programmers Write Code Justin Lubin , Sarah E. Chasins",
                note="W3206925941 (2021)."),
            VER("https://schasins.com/papers/", "Exploring the Learnability of Program Synthesizers by Novice Programmers Dhanya Jayagopal , Justin Lubin , Sarah E. Chasins",
                note="W4307472488 (2022)."),
            ID("orcid_record", orcid_person("0000-0003-0557-3580", "Sarah Chasins"),
               "ORCID record names Sarah Chasins; affiliationGroups.json (sha256 aef51fc76979accb...) lists EMPLOYMENT "
               "University of California, Berkeley, Electrical Engineering and Computer Sciences (undated)."),
        ]),
    appt=[Q("https://schasins.com/cv/", "Sarah E. Chasins is an Associate Professor at UC Berkeley EECS.")],
    notes=("PLAIT Lab (plait-lab.org) lists 8 current members and 16 alumni; EECS tech reports name her as M.S. advisor "
           "(Matute 2024, Jayagopal 2022; Nigatu's 2023 M.S. report co-advised with Canny) and the EECS dissertations page "
           "has Hellina Hailu Nigatu (2025). Liliana Rojas ('Assistant') is not counted. The pipeline cause "
           "adviser_name_unmatched_or_namesake is probably the 'Sarah E. Chasins' vs 'Sarah Chasins' form. "
           "OpenAlex A5090728813 verified (27 title matches)."),
)

# ============================================================================ Natacha Crooks
NC = "https://nacrooks.github.io/"
NCS = NC + "students/"
NCB = NC + "bibliography/"
NCH = "Research Group I am fortunate to collaborate with the following graduate and undergraduate researchers:"
D["Natacha Crooks"] = dict(
    status="pi",
    status_ev=[SE(NCS, "Natacha Crooks | Research Group", "David Chu (PhD Student, UC Berkeley)")],
    students=[
        ST("Soujanya Ponnapalli", "postdoc", None, hs(NCS, NCH, "Postdoctoral Researchers Soujanya Ponnapalli")),
        ST("David Chu", "phd", None, hs(NCS, NCH, "David Chu (PhD Student, UC Berkeley)")),
        ST("Audrey Cheng", "phd", None, hs(NCS, NCH, "Audrey Cheng (PhD Student, UC Berkeley)")),
        ST("Neil Giridharan", "phd", None, hs(NCS, NCH, "Neil Giridharan (PhD Student, UC Berkeley)"),
           note="also EECS-2026-21 (M.S. report, 'Advisors: Natacha Crooks')"),
        ST("Reginald Frank", "phd", None, hs(NCS, NCH, "Reginald Frank (PhD Student, UC Berkeley)")),
        ST("Shubham Mishra", "phd", None, hs(NCS, NCH, "Shubham Mishra (PhD Student, UC Berkeley)")),
        ST("Micah Murray", "phd", None, hs(NCS, NCH, "Micah Murray (PhD Student, UC Berkeley)")),
        ST("Suyash Gupta", "postdoc", [2022, 2024], hs(NCS, "Alumni", "Suyash Gupta (Postdoc 2022-2024")),
        ST("Chris Liu", "masters", [None, 2024], hs(NCS, "Alumni", "Chris Liu (MS Student 2024")),
        ST("Siddanth Sharma", "masters", [None, 2024], hs(NCS, "Alumni", "Siddanth Sharma (MS Student 2024")),
        ST("Maxime Jacovella", "other", [2023, 2023], hs(NCS, "Alumni", "Maxime Jacovella (Visiting Research Intern Spring 2023"),
           note="visiting research intern"),
        ST("Michael Paper", "other", [2023, 2023], hs(NCS, "Alumni", "Michael Paper (Visiting Masters Student, Spring 2023"),
           note="visiting masters student"),
        ST("Ayoub Saidane", "other", [2023, 2023], hs(NCS, "Alumni", "Ayoub Saidane (Visiting Masters Student, Spring 2023"),
           note="visiting masters student"),
        ST("Timothée Zerbib", "other", [2023, 2024], hs(NCS, "Alumni", "Timothée Zerbib (Visiting Masters Student, Fall 2023, Spring 2024"),
           note="visiting masters student"),
    ],
    identity=dict(
        orcid=[], openalex=["A5043986860"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5043986860", "Natacha Crooks"),
               "OpenAlex author A5043986860 (67 works; last known UC Berkeley); carries ORCID 0000-0002-3567-801X."),
            VER(NCB, "Keep CALM and CRDT on VLDB’23 Shadaj Laddad, Conor Power, Mae Milano, Alvin Cheung, Natacha Crooks",
                note="W4321448357 (2022) of A5043986860; 28 of its 2016+ titles match her publications page."),
            VER(NCB, s="RALF: Accuracy-Aware Scheduling for Feature Store Maintenance", e="Crooks", note="W4391054877 (2023)."),
            VER(NCB, s="Treaty: Secure Distributed Transactions", e="Crooks", note="W4287849790 (2022)."),
            VER(NCB, s="Morty: Scaling Concurrency Control with Re-Execution", e="Crooks", note="W4372267675 (2023)."),
        ]),
    appt=[Q(NC + "cv.pdf", "Natacha Crooks, Matthew Grosvenor, Allen Clement and Steven Hand Relevant Experience UC Berkeley, Assistant Professor Berkeley, USA")],
    notes=("Assistant Professor July 2020 (CV 'UC Berkeley, Assistant Professor ... July 2020 -'), now Associate Professor. "
           "Research-group page: 1 postdoc, 6 Berkeley PhD students, alumni (postdoc Suyash Gupta 2022-2024, 2 MS students, "
           "4 visiting students). Excluded: Florian Suri-Payer (listed as a Cornell PhD student) and Matthew Burke (PhD 2023; "
           "the page does not put him at Berkeley -- he was a Cornell student). ORCID 0000-0002-3567-801X record has no "
           "affiliation, so not anchored. OpenAlex A5043986860 verified (28 title matches)."),
)

# ============================================================================ Niloufar Salehi
NS = "https://niloufar.org/"
NSCV = "https://niloufar.org/wp-content/uploads/2024/01/CV_Jan2024.pdf"
NSM = "Master’s students supervised (with publications)"
NSU = "Undergraduate students supervised (with publications)"
D["Niloufar Salehi"] = dict(
    status="pi",
    status_ev=[diss_status("Niloufar Salehi", heading_name="Nilou Salehi"),
               Q(NS, "Niloufar (Nilou) Salehi is an Associate Professor in the School of Information at UC, Berkeley")],
    students=diss_students("Niloufar Salehi", heading_name="Nilou Salehi") + [
        ST("Sabriya Alam", "phd", None, hs(NS, "PhD students", "Sabriya Alam")),
        ST("Angela Jin", "phd", None, hs(NS, "PhD students", "Angela Jin")),
        ST("Liza Gak", "phd", None, hs(NS, "PhD alumni", "Liza Gak")),
        ST("Tonya Nguyen", "phd", None, hs(NS, "PhD alumni", "Tonya Nguyen")),
        ST("Seyi Olojo", "phd", None, hs(NS, "PhD alumni", "Seyi Olojo"), note="CV: co-advised with Jenna Burrell"),
        ST("Sijia Xiao", "phd", None, hs(NS, "PhD alumni", "Sijia Xiao"), note="CV: co-advised with Coye Cheshire"),
        ST("Liya Mulugeta", "masters", [None, 2023], SE(TR + "2023/EECS-2023-294.html", "Advisors: Niloufar Salehi",
                                                       "Author= {Mulugeta, Liya")),
        ST("Rachel B. Warren", "masters", [None, 2021], hs(NSCV, NSM, "Rachel B. Warren (2021)")),
        ST("Sofia Dewar", "masters", [None, 2020], hs(NSCV, NSM, "Sofia Dewar (2020)")),
        ST("Eva Wu", "masters", [None, 2019], hs(NSCV, NSM, "Eva Wu (2019)")),
        ST("Emily Pederson", "masters", [None, 2019], hs(NSCV, NSM, "Emily Pederson (2019)")),
        ST("Soravis (Sun) Prakkamakul", "masters", [None, 2019], hs(NSCV, NSM, "Soravis (Sun) Prakkamakul (2019)")),
        ST("Qian Yu", "masters", [None, 2019], hs(NSCV, NSM, "Qian Yu (2019)")),
        ST("Darya Kaviani", "undergraduate", [None, 2021], hs(NSCV, NSU, "Darya Kaviani (2021)")),
        ST("Wesley Deng", "undergraduate", [None, 2021], hs(NSCV, NSU, "Wesley Deng (2021)")),
    ],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[SE(NSCV, "Niloufar Salehi Assistant Professor, School of Information",
             "Affiliated appointment at Electrical Engineering and Computer Science (EECS), Feb 2020-present")],
    notes=("Papers were not missing (33 lab papers); only students. Primary appointment School of Information (Assistant "
           "Professor July 2018-, EECS affiliated Feb 2020-, per her Jan 2024 CV; now Associate Professor). She advises "
           "through both the I School and EECS PhD programs, so most advisees are I School students the EECS dissertations "
           "page misses. Sources: homepage PhD students/alumni, CV M.S./undergraduate supervision, EECS dissertation "
           "(Samantha Robertson 2023) and tech report EECS-2023-294 (Mulugeta)."),
)

# ============================================================================ Venkatesan Guruswami
VG = "https://people.eecs.berkeley.edu/~venkatg/"
VGCV = VG + "CV/venkat-CV-web.pdf"
VGH = "Current PhD advisees:"
VGP = "6.2 Postdoctoral mentoring"
D["Venkatesan Guruswami"] = dict(
    status="pi",
    status_ev=[Q(NEL, "Current student: Mihir Singhal (co-advised with Venkatesan Guruswami )"),
               SE(VG, "Venkatesan Guruswami University of California, Berkeley", "Chancellor's Professor , Department of EECS")],
    students=[
        ST("Omar Alrabiah", "phd", None, hs(VG, VGH, "Omar Alrabiah")),
        ST("Louis Golowich", "phd", None, hs(VG, VGH, "Louis Golowich")),
        ST("Yihan Geng", "phd", None, hs(VG, VGH, "Yihan Geng")),
        ST("Meghal Gupta", "phd", None, hs(VG, VGH, "Meghal Gupta")),
        ST("Shilun Li", "phd", None, hs(VG, VGH, "Shilun Li")),
        ST("Xuandi Ren", "phd", None, hs(VG, VGH, "Xuandi Ren")),
        ST("Mihir Singhal", "phd", None, hs(VG, VGH, "Mihir Singhal (co-advised with Jelani Nelson)")),
        ST("Pranav Trivedi", "phd", [None, 2026], Q(VGCV, "At University of California, Berkeley - Pranav Trivedi, May 2026. Dissertation title: Quantum Hierarchical Locally Recoverable Codes")),
        ST("Joshua Brakensiek", "postdoc", [2024, None], hs(VGCV, VGP, "Joshua Brakensiek, Aug 2024-present")),
        ST("Hsin-Po Wang", "postdoc", [2022, 2024], hs(VGCV, VGP, "Hsin-Po Wang, Oct 2022-May 2024")),
        ST("Sai Sandeep", "postdoc", [2022, 2023], hs(VGCV, VGP, "Sai Sandeep, Sep 2022-May 2023")),
        ST("Ray Li", "postdoc", [2022, 2023], hs(VGCV, VGP, "Ray Li, Aug 2022-Aug 2023")),
        ST("Vinayak Kumar", "postdoc", [2026, None], hs(VG, "Current postdocs", "Vinayak Kumar , Aug 2026-")),
        ST("Rachel Zhang", "postdoc", [2026, None], hs(VG, "Current postdocs", "Rachel Zhang , Aug 2026-")),
    ],
    identity=dict(
        orcid=[], openalex=["A5068388812"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5068388812", "Venkatesan Guruswami"),
               "OpenAlex author A5068388812 (646 works; last known UC Berkeley / Simons)."),
            VER(VGCV, "Guruswami and M. Wootters. Repairing Reed-Solomon codes",
                note="W1842188052 (2016) of A5068388812; 112 of its 2016+ titles match his CV (his web bibliography writes "
                     "his name as 'V.G.', so the CV is used)."),
            VER(VGCV, "Guruswami, C. Xing, and C. Yuan. How long can optimal locally repairable codes be", note="W2963890921 (2019)."),
            VER(VGCV, s="V. Guruswami and J. Ha", e="Explicit two-deletion codes with redundancy matching the existential bound",
                note="W3113522538 (2021)."),
            VER(VGCV, "Guruswami. Promise constraint satisfaction: Structure theory and a symmetric boolean dichotomy",
                note="W2776885602 (2018)."),
        ]),
    appt=[SE(VG, "Venkatesan Guruswami University of California, Berkeley", "Director , Simons Institute for the Theory of Computing")],
    notes=("At Berkeley since Jan 2022 (CV: 'University of California, Berkeley Jan 2022-present'; Chancellor's Professor of "
           "EECS, Professor of Mathematics, Simons Institute Director July 2025-). Students: 7 current PhD advisees "
           "(homepage), Pranav Trivedi PhD May 2026 (CV, 'At University of California, Berkeley'), 4 dated Berkeley-era CV "
           "postdocs plus 2 postdocs starting Aug 2026. CMU/UW students and pre-2022 postdocs (incl. Joao Ribeiro Aug "
           "2021-Feb 2023, which straddles the move) are excluded. No EECS dissertations page yet (404). ORCID "
           "0000-0001-7926-3396 record has no affiliation, so not anchored. OpenAlex A5068388812 verified (112 CV matches)."),
)

# ============================================================================ John Wright
JW = "https://people.eecs.berkeley.edu/~jswright/"
D["John Wright"] = dict(
    status="pi",
    status_ev=[Q("https://people.eecs.berkeley.edu/~lllewis/",
                 "I'm a second-year PhD student at UC Berkeley, where I am advised by Umesh Vazirani and John Wright"),
               Q("https://apelecan.github.io/",
                 "fortunate to be co-advised by Prof. Shafi Goldwasser and Prof. John Wright")],
    students=[
        ST("Laura Lewis", "phd", None, SE("https://people.eecs.berkeley.edu/~lllewis/", "Laura Lewis I'm a second-year PhD student",
                                          "advised by Umesh Vazirani and John Wright")),
        ST("Angelos Pelecanos", "phd", None, SE("https://apelecan.github.io/", "Angelos Pelecanos Ph.D. student in Computer Science",
                                                "co-advised by Prof. Shafi Goldwasser and Prof. John Wright")),
    ],
    identity=dict(
        orcid=["0009-0006-4071-3488"], openalex=["A5102755411", "A5144385508"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5102755411", "John Wright"),
               "OpenAlex A5102755411 (4 works 2023-2025, UC Berkeley) carries ORCID 0009-0006-4071-3488."),
            VER(JW, "A one-query lower bound for unitary synthesis and breaking quantum cryptography Alex Lombardi , Fermi Ma , John Wright",
                note="W4399512732 (2024) of A5102755411; all 4 of its works match his homepage."),
            VER(JW, "Haar random codes attain the quantum Hamming bound, approximately Fermi Ma , Xinyu Tan , John Wright",
                note="W4415318129 (2025) of A5102755411."),
            VER(JW, s="The state hidden subgroup problem and an efficient algorithm for locating unentanglement", e="John Wright",
                note="W4411319770 (2025) of A5102755411."),
            VER(JW, s="Unique Games hardness of Quantum Max-Cut, and a conjectured vector-valued Borell", e="John Wright",
                note="W4316652448 (2023) of A5102755411."),
            ID("openalex_author_record", oa_author_quote("A5144385508", "John Wright"),
               "OpenAlex A5144385508 (7 works 2025-2026, UC Berkeley) carries the same ORCID 0009-0006-4071-3488: a split "
               "of the same person."),
            VER(JW, "The Keyl-Werner algorithm is not optimal for spectrum estimation Angelos Pelecanos , Jack Spilecki , Ewin Tang , John Wright",
                note="W7171811238 (2026) of A5144385508."),
            VER(JW, "Are controlled unitaries helpful? Ewin Tang , John Wright", note="W4416548081 (2025) of A5144385508."),
            VER(JW, "Improved lower bounds for QAC 0 Malvika Raj Joshi, Avishay Tal , Francisca Vasconcelos , John Wright",
                note="W4417474187 (2026) of A5144385508 ('Improved Lower Bounds for QAC0')."),
            ID("orcid_record", orcid_person("0009-0006-4071-3488", "John Wright"),
               "ORCID record names John Wright; affiliationGroups.json (sha256 ec7436a9c9c8f129...) lists EMPLOYMENT "
               "University of California, Berkeley, Electrical engineering and computer science, Assistant professor, 2022-."),
        ]),
    appt=[Q(JW, "John Wright Assistant Professor Department of Electrical Engineering and Computer Sciences , University of California, Berkeley")],
    notes=("Assistant Professor since 2022 (ORCID employment 2022-; homepage: before Berkeley at MIT, Caltech and UT Austin). "
           "Two PhD students state him as co-advisor on their own pages. Identity: OpenAlex leaves most of his authorships "
           "UNASSIGNED (author id null, e.g. W1944079109, W4214903668, W4414922337), which is why the sweep shows a '-' "
           "candidate; the two small ids A5102755411 + A5144385508 (shared ORCID) are his. NAMESAKE WARNING: OpenAlex "
           "A5007969144 'John (Charles) Wright' is a different Berkeley EECS person (RISC-V/Chipyard/Gemmini hardware, "
           "2018-2022, ORCID 0000-0001-6363-0462) and must not be attached to this PI. No student found beyond the two; "
           "his EECS dissertations page is 404."),
)

# ============================================================================ Ahmed Alaa
AL = WB + "20260314141428id_/https://alaalab.berkeley.edu/people/"
ALP = WB + "20260314141536id_/https://alaalab.berkeley.edu/publications"
ALH = "People PhD Students"
AL23 = WB + "20230207140602id_/https://ahmedmalaa.github.io/"
D["Ahmed Alaa"] = dict(
    status="pi",
    status_ev=[SE(AL, "People | Alaa Lab", "Alexander Schubert PhD Student (with Ziad Obermeyer)")],
    students=[
        ST("Alexander Schubert", "phd", None, hs(AL, ALH, "Alexander Schubert PhD Student (with Ziad Obermeyer)")),
        ST("Jivat Kaur", "phd", None, hs(AL, ALH, "Jivat Kaur PhD Student (with Michael I. Jordan)")),
        ST("Zhongyuan Liang", "phd", None, hs(AL, ALH, "Zhongyuan Liang PhD Student")),
        ST("Frances Dean", "phd", None, hs(AL, ALH, "Frances Dean PhD Student (with Ziad Obermeyer)")),
        ST("Nikita Mehandru", "phd", None, hs(AL, ALH, "Nikita Mehandru PhD Candidate (with David Bamman)")),
        ST("William Hou", "phd", None, hs(AL, ALH, "William Hou PhD Student (with Geoff Tison)")),
        ST("Jenna Fields", "phd", None, hs(AL, ALH, "Jenna Fields PhD Student")),
        ST("Lars Van der Laan", "other", None, hs(AL, ALH, "Lars Van der Laan Visiting PhD Student"), must=["Laan"],
           note="visiting PhD student from University of Washington"),
        ST("Niloufar Golchini", "other", None, hs(AL, "Predoctoral Researcher", "Niloufar Golchini Predoctoral Researcher"),
           note="predoctoral researcher"),
        ST("Shiladitya Dutta", "other", None, hs(AL, "Predoctoral Researcher", "Shiladitya Dutta Predoctoral Researcher UC Berkeley EECS"),
           note="predoctoral researcher"),
        ST("Ayush Jain", "other", None, hs(AL, "Predoctoral Researcher", "Ayush Jain Predoctoral Researcher"), note="predoctoral researcher (Duke)"),
        ST("Yulu Gan", "other", None, hs(AL, "Predoctoral Researcher", "Yulu Gan Predoctoral Researcher"), note="predoctoral researcher (Peking University)"),
        ST("Hongbo Wei", "undergraduate", None, hs(AL, "Predoctoral Researcher", "Hongbo Wei URAP Student UC Berkeley EECS")),
        ST("Saathvik Selvan", "undergraduate", None, hs(AL, "Predoctoral Researcher", "Saathvik Selvan URAP Student UC Berkeley EECS")),
        ST("Dev Patel", "undergraduate", None, hs(AL, "Predoctoral Researcher", "Dev Patel URAP Student UC Berkeley EECS")),
        ST("Zekai Wang", "undergraduate", None, hs(AL, "Predoctoral Researcher", "Zekai Wang URAP Student Mathematics & Computer Science, UC Berkeley")),
        ST("Keying Kuang", "member", None, hs(AL, "Lab Associates", "Lab Associates Keying Kuang"), note="lab associate"),
        ST("Huong Vu", "member", None, hs(AL, "Lab Associates", "Huong Vu"), note="lab associate"),
        ST("Wenxin Zhang", "member", None, hs(AL, "Lab Associates", "Wenxin Zhang"), note="lab associate"),
        ST("Sungwoo Park", "postdoc", None, hs(AL, "Alumni Post Docs", "Alumni Post Docs Sungwoo Park")),
        ST("Shenghuan Sun", "phd", None, hs(AL, "Alumni Post Docs", "PhD Students Shenghuan Sun"), note="alumni list"),
        ST("Jack Jedlicki", "other", None, hs(AL, "Alumni Post Docs", "Jack Jedlicki"), note="alumni predoctoral researcher"),
    ],
    identity=dict(
        orcid=[], openalex=["A5014596965"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5014596965", "Ahmed M. Alaa"),
               "OpenAlex author A5014596965 'Ahmed M. Alaa' (139 works; UC Berkeley 2022-2026, UCSF)."),
            VER(ALP, s="Evaluating Large Language Models as Agents in the Clinic", e="Ahmed Alaa",
                note="W4393867901 (2024) of A5014596965; 46 of its 2016+ titles match the Alaa Lab publications page."),
            VER(ALP, s="Conformal Time-series Forecasting", e="Ahmed Alaa", note="W3211802876 (2021)."),
            VER(ALP, "Machine learning to guide the use of adjuvant therapies for breast cancer Ahmed Alaa", note="W3114973470 (2021)."),
            VER(ALP, s="How artificial intelligence and machine learning can help healthcare systems respond to COVID-19", e="Ahmed Alaa",
                note="W3111353854 (2020)."),
        ]),
    appt=[Q(AL23, "Ahmed M. Alaa Assistant Professor of Computational Precision Health (UC Berkeley and UCSF)")],
    notes=("Assistant Professor in the Berkeley-UCSF Computational Precision Health program (EECS/Statistics affiliated), "
           "Berkeley since 2022. The homepage on his EECS profile (ahmedmalaa.github.io) is now 404 and its archived "
           "'Lab Members'/'Publications' pages were empty; the lab moved to alaalab.berkeley.edu (live host timed out from "
           "here; Wayback 2026-02/03 captures used). Lab page lists 7 PhD students (most co-advised), 4 predoctoral "
           "researchers, 4 URAP undergraduates, 3 lab associates and alumni. Nikita Mehandru is co-advised with Bamman. "
           "ORCID 0000-0001-9936-7141 record ('ahmed alaa') lists no affiliation, so not anchored. OpenAlex A5014596965 "
           "verified (46 title matches on the lab publications page)."),
)

# ============================================================================ Alane Suhr
NLPM = "http://nlp.cs.berkeley.edu/members.html"
AS = "https://www.alanesuhr.com/pubs.html"
D["Alane Suhr"] = dict(
    status="pi",
    status_ev=[Q(NLPM, "Zineng Tang Advisor: Alane Suhr")],
    students=[
        ST("Zineng Tang", "phd", None, hs(NLPM, "PhD Students", "Zineng Tang Advisor: Alane Suhr")),
        ST("Seun Eisape", "phd", None, hs(NLPM, "PhD Students", "Seun Eisape Advisor: Alane Suhr")),
        ST("Téa Wright", "phd", None, hs(NLPM, "PhD Students", "Téa Wright Advisor: Alane Suhr")),
        ST("Anya Ji", "phd", None, hs(NLPM, "PhD Students", "Anya Ji Advisor: Alane Suhr")),
        ST("Kalvin Chang", "phd", None, hs(NLPM, "PhD Students", "Kalvin Chang Advisor: Alane Suhr")),
    ],
    identity=dict(
        orcid=[], openalex=["A5009625151", "A5048246314"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5009625151", "Alane Suhr"),
               "OpenAlex author A5009625151 (49 works; last known UC Berkeley)."),
            VER(AS, "A corpus for reasoning about natural language grounded in photographs. Alane Suhr",
                note="W2899335602 (2019) of A5009625151; 31 of its 2016+ titles match her publications page."),
            VER(AS, "A corpus of natural language for visual reasoning. Alane Suhr", note="W2741631785 (2017) of A5009625151."),
            VER(AS, "Executing instructions in situated collaborative interactions. Alane Suhr", note="W2971077754 (2019) of A5009625151."),
            ID("openalex_author_record", oa_author_quote("A5048246314", "Alane Suhr"),
               "OpenAlex author A5048246314 (10 works 2024-2025, UC Berkeley): a split of the same person."),
            VER(AS, "Long chain-of-thought reasoning across languages. Josh Barua, Seun Eisape, Kayo Yin, and Alane Suhr",
                note="W4415241223 (2025) of A5048246314; 4 of its titles match her publications page."),
            VER(AS, "DigiRL: Training in-the-wild device-control agents with autonomous reinforcement learning . Hao Bai*, Yifei Zhou*, Mert Cemri, Jiayi Pan, Alane Suhr",
                note="W4415798734 (2024) of A5048246314."),
            VER(AS, s="Fine-tuning large vision-language models as decision-making agents via reinforcement learning", e="Suhr",
                note="W4415795780 (2024) of A5048246314."),
            VER(AS, s="UNcommonsense reasoning: Abductive reasoning about uncommon situations", e="Suhr",
                note="W4401043507 (2024) of A5048246314."),
        ]),
    appt=[Q("http://nlp.cs.berkeley.edu/", "Alane Suhr joined Berkeley NLP as faculty in Summer 2023.")],
    notes=("Assistant Professor since Summer 2023 (Berkeley NLP news); PhD Cornell 2022, then AI2. The Berkeley NLP people "
           "page lists 5 PhD students with 'Advisor: Alane Suhr'. Her homepage has no group list (only first names of "
           "students). Two OpenAlex ids are hers: A5009625151 (main) and A5048246314 (2024-2025 split); A5121253730 "
           "(1 work, Georgia Tech) did not match and is not anchored. No ORCID found. No EECS dissertations page yet (404)."),
)

# ============================================================================ Adam Yala
AY = "https://www.adamyala.org/"
AYM = WB + "20220702175312id_/https://adamyala.csail.mit.edu/"
D["Adam Yala"] = dict(
    status="pi",
    status_ev=[diss_status("Adam Yala")],
    students=diss_students("Adam Yala") + [
        ST("Natalia Harguindeguy", "phd", None, Q(AY, "Natalia Harguindeguy PhD Student")),
        ST("Xinyang Han", "phd", None, Q(AY, "Xinyang Han PhD Student")),
        ST("Kumar Krishna Agrawal", "phd", None, Q(AY, "Kumar Krishna Agrawal PhD Student")),
        ST("Michael Nercessian", "phd", None, Q(AY, "Michael Nercessian PhD Student")),
        ST("Longchao (Joy) Liu", "phd", None, Q(AY, "Longchao (Joy) Liu PhD Student"), must=["Liu"]),
        ST("Curtis Chambers", "phd", None, Q(AY, "Curtis Chambers PhD Student")),
        ST("Yutong Bai", "postdoc", None, Q(AY, "Yutong Bai Post Postdoc")),
    ],
    identity=dict(
        orcid=[], openalex=["A5084801169"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5084801169", "Adam Yala"),
               "OpenAlex author A5084801169 (69 works; last known UCSF / UC Berkeley)."),
            VER(AYM, "Optimizing risk-based breast cancer screening policies with reinforcement learning Adam Yala",
                note="W4226269440 (2022) of A5084801169; 10 of its 2016+ titles match the 2022 capture of his own homepage "
                     "(adamyala.csail.mit.edu, already titled UC Berkeley/UCSF)."),
            VER(AYM, "Multi-Institutional Validation of a Mammography-based Breast Cancer Risk Model Adam Yala", note="W3213232584 (2021)."),
            VER(AYM, "A Deep Learning Mammography-based Model for Improved Breast Cancer Risk Prediction Adam Yala", note="W2944016032 (2019)."),
            VER(AYM, "Using machine learning to parse breast pathology reports Adam Yala", note="W2949479579 (2016)."),
        ]),
    appt=[Q(AYM, "Adam Yala Assistant Professor Computational Precision Health and EECS UC Berkeley and UCSF")],
    notes=("Assistant Professor of Computational Precision Health (Berkeley-UCSF), EECS and Statistics; co-founder/CEO of "
           "Voio. Lab section of adamyala.org lists 7 PhD students and a postdoc (each labelled on the page); EECS "
           "dissertations page has Long Lian (2026), whose 2024 M.S. report EECS-2024-206 also names 'Advisors: Trevor "
           "Darrell and Adam Yala'. His current site links publications only to Google Scholar (not used); the 2022 "
           "capture of his own homepage carries a featured-publications list. ORCID 0000-0001-9576-2590 record has no "
           "affiliation, so not anchored. OpenAlex A5084801169 verified (10 title matches)."),
)
