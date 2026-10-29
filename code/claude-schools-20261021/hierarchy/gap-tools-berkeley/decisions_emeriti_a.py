"""Berkeley gap decisions, worker emeriti_a (2026-10-21/22): Barsky, M. Blum, Clancy, Fateman, Feldman, Ferrari,
Graham, Harrison, Harvey, Hilfinger, Kahan.

Status sources: the March 2016 EECS CS emeritus listing (Wayback), the Jan 2016 / Nov 2017 / Jul 2019 EECS faculty
listings, each PI's EECS Ph.D. dissertations-by-faculty page (newest entry), EECS profiles (retirement years),
Mathematics Genealogy Project pages (Wayback captures; the live MGP site is offline since 2026-10-20 for a PHP
vulnerability), Barsky Lab pages, EECS technical reports ("Advisors:"), and ICSI AI-group pages (Feldman).
"""
import sys

sys.path.insert(0, "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-berkeley")
from dhelp import *  # noqa: E402,F401,F403

D = {}

EM16 = WB + "20160310213756id_/http://www.eecs.berkeley.edu/Faculty/Lists/CS/emeritus.shtml"
FAC16 = WB + "20160104002312id_/http://www.eecs.berkeley.edu/Faculty/Lists/faculty.shtml"
FAC17 = WB + "20171101140017id_/https://www2.eecs.berkeley.edu/Faculty/Lists/faculty.html"
CS19 = WB + "20190715184029id_/https://www2.eecs.berkeley.edu/Faculty/Lists/CS/faculty.html"
EMNOW = "https://www2.eecs.berkeley.edu/Faculty/Lists/CS/emeritus.html"


def diss_newest(pi):
    """Heading of the PI's EECS dissertations page through its newest (first-listed) entry."""
    return diss_status(pi, min_year=0)


# ============================================================================ Brian A. Barsky (pi)
BL = "https://barskygroup.wixsite.com/home/"
BLPERS = BL + "personnel"
BLPUBS = BL + "publications"
TR20 = "https://www2.eecs.berkeley.edu/Pubs/TechRpts/2020/EECS-2020-181.html"
TR24 = "https://www2.eecs.berkeley.edu/Pubs/TechRpts/2024/EECS-2024-179.html"

# (quote start, quote end, [(student name, role)], note) -- 2016+ student reports on the Barsky Lab publications page
_BL_REPORTS = [
    ("Wu, Zehao (Peter) (2016)", "Master's Research Project Report, May 2016.", [("Zehao Wu", "masters")], "MS research project report, May 2016"),
    ("Ding, Charles (2017)", "Master's Research Project Report, May 2017.", [("Charles Ding", "masters")], "MS research project report, May 2017"),
    ("Claver, Vivek (2017)", "M.Eng. Capstone Report, May 2017.", [("Vivek Claver", "masters")], "M.Eng. capstone, May 2017"),
    ("Teng, Sijia (Scarlett) (2017)", "M.Eng., Capstone Report, May 2017.", [("Sijia Teng", "masters")], "M.Eng. capstone, May 2017"),
    ("Zeng, Jia (Sophie) (2017)", "M.Eng., Capstone Report, May 2017.", [("Jia Zeng", "masters")], "M.Eng. capstone, May 2017"),
    ("Cui, Zhaoxiong (Leo);", "M.Eng., Capstone Report, May 2019.",
     [("Zhaoxiong Cui", "masters"), ("Hanfei Ren", "masters"), ("Siqi Wang", "masters")], "M.Eng. capstone, May 2019"),
    ("Di, Weiwen and", "M.Eng., Capstone Report, May 2019.", [("Weiwen Di", "masters"), ("Ken Kobayashi", "masters")], "M.Eng. capstone, May 2019"),
    ("Lin, Zhaoyan and", "M.Eng., Capstone Report, May 2019.", [("Zhaoyan Lin", "masters"), ("Echo Gu", "masters")], "M.Eng. capstone, May 2019"),
    ("Zhen, Yirong (2019)", "Master's Thesis, May 2019.", [("Yirong Zhen", "masters")], "Master's thesis, May 2019"),
    ("Al-Kazily, Tarkan;", "M.Eng., Capstone Report, May 2020.",
     [("Tarkan Al-Kazily", "masters"), ("Melody Mao", "masters"), ("Eric Liu", "masters"), ("Chun-Ning Tsao", "masters"),
      ("Wei-Chun Hwang", "masters"), ("Eric Ying", "masters")], "M.Eng. capstone, May 2020"),
    ("Baker, Toby;", "M.Eng., Capstone Report, May 2020.",
     [("Toby Baker", "masters"), ("Weihao Dong", "masters"), ("Xun Lin", "masters"), ("Ayusman Saha", "masters"),
      ("Fangping Shi", "masters")], "M.Eng. capstone, May 2020"),
    ("Ding, Yizhen;", "M.Eng., Capstone Report, May 2020.",
     [("Yizhen Ding", "masters"), ("Sundi Xiao", "masters"), ("Xiaoyu Yang", "masters"), ("Yaying Zhao", "masters"),
      ("Zhuoming Zhang", "masters")], "M.Eng. capstone, May 2020"),
    ("Qi, Michael (2021)", "Master's Research Project Report, May 2021.", [("Michael Qi", "masters")], "MS research project report, May 2021"),
    ("Qing, Lisa;", "M.Eng., Capstone Report, May 2021.",
     [("Lisa Qing", "masters"), ("Xianlin Shao", "masters"), ("Xuewei Wang", "masters"), ("Sharon Su Yen Lee", "other")],
     "M.Eng. capstone, May 2021 (the personnel page lists Sharon Su Yen Lee as an undergraduate)"),
    ("Wu, Shiqi (Sophie);", "M.Eng., Capstone Report, May 2021.",
     [("Shiqi Wu", "masters"), ("Sihao Chen", "masters"), ("Weili Liu", "masters"), ("Yiyang Cai", "masters"),
      ("Yizhou Wang", "masters"), ("Xuantong Liu", "masters")], "M.Eng. capstone, May 2021"),
    ("Chen, Chin-An (Daniel);", "M.Eng., Capstone Report, May 2022.",
     [("Chin-An Chen", "masters"), ("Vincent Lieng", "masters"), ("Ya-Sin Luo", "masters"), ("Zi-Chao Lin", "masters")],
     "M.Eng. capstone, May 2022"),
    ("Defauw, Maxime;", "M.Eng., Capstone Report, May 2022.",
     [("Maxime Defauw", "masters"), ("Yao Huang", "masters"), ("Hau-En Ke", "masters"), ("Kuan-Yu Lung", "masters"),
      ("Sagar Patel", "masters"), ("Yucheng Wang", "masters")], "M.Eng. capstone, May 2022"),
    ("Guo, Kexin;", "M.Eng., Capstone Report, May 2022.",
     [("Kexin Guo", "masters"), ("Weiyu Feng", "masters"), ("Hanqi Zhang", "masters"), ("Tucker Cullen", "masters")],
     "M.Eng. capstone, May 2022"),
    ("Hajela, Rohan (2022)", "Master's Research Project Report, May 2022.", [("Rohan Hajela", "masters")], "MS research project report, May 2022"),
    ("Hu, Fang;", "M.Eng., Capstone Report, May 2022.",
     [("Fang Hu", "masters"), ("Xinying Hu", "masters"), ("Yang Huang", "masters"), ("Guanghan Pan", "masters"),
      ("Juntao Peng", "masters")], "M.Eng. capstone, May 2022"),
    ("Huang, Ke (Kenny);", "M.Eng., Capstone Report, May 2022.",
     [("Ke Huang", "masters"), ("Siqi Jiang", "masters"), ("Zhibo Fan", "masters"), ("Zhengmin Zhang", "masters")],
     "M.Eng. capstone, May 2022"),
    ("Li, Shuwei (Waller);", "M.Eng., Capstone Report, May 2022.",
     [("Shuwei Li", "masters"), ("Haohua Lyu", "masters"), ("Kaiwen Yu", "masters"), ("Siyu Zhang", "masters")],
     "M.Eng. capstone, May 2022"),
    ("Nguyen, Quy Hoang;", "M.Eng., Capstone Report, May 2022.",
     [("Quy Hoang Nguyen", "masters"), ("Yiqing Tao", "masters"), ("Jordan Wong", "masters"), ("Kanglan Tang", "masters"),
      ("Yaowei Ma", "masters")], "M.Eng. capstone, May 2022"),
    ("Ouyang, Patricia (2022)", "Master's Research Project Report, May 2022.", [("Patricia Ouyang", "masters")], "MS research project report, May 2022"),
    ("Parande, Anmol (2022)", "Master's Research Project Report, May 2022.", [("Anmol Parande", "masters")], "MS research project report, May 2022"),
    ("Wang, Jinghan;", "M.Eng., Capstone Report, May 2022.",
     [("Jinghan Wang", "masters"), ("Simon N. Heimowitz", "masters"), ("Yao Cheng Yee", "masters")], "M.Eng. capstone, May 2022"),
    ("Xu, Shiyun (Jimmy) (2022)", "Master's Research Project Report, May 2022.", [("Shiyun Xu", "masters")], "MS research project report, May 2022"),
]


def _report_year(end):
    return int(end.rstrip(".")[-4:])


_barsky_students = [
    ST("Jacob Holesinger", "masters", [2020, 2020],
       Q(TR20, "Advisors: Brian A. Barsky BibTeX citation: @mastersthesis{Holesinger:EECS-2020-181, Author= {Holesinger, Jacob}"),
       note="EECS tech report UCB/EECS-2020-181 (MS report, Sep 2020); also on the Barsky Lab publications page"),
    ST("Shawn Zhao", "masters", [2024, 2024],
       Q(TR24, "Advisors: Brian A. Barsky BibTeX citation: @mastersthesis{Zhao:EECS-2024-179, Author= {Zhao, Shawn and Barsky, Brian A.}"),
       note="EECS tech report UCB/EECS-2024-179 (MS report, Aug 2024); listed as current Graduate Student (M.S.) on the Barsky Lab personnel page"),
]
def _alumni_entry(name):
    """The student's entry under 'Recent Alumni' on the Barsky Lab personnel page (relation: lab member), or None."""
    import re as _re
    import capstore as _cs
    cap = _cs.find_capture(BLPERS)
    if not cap:
        return None, None
    t = _cs.page_text(cap[0])
    alum = t[t.find("Recent Alumni"):]
    parts = name.split()
    m = _re.search(_re.escape(parts[0]) + r"[^,;]{0,30}?" + _re.escape(parts[-1])
                   + r" (?:Graduate|Undergraduate) (?:Student|Researcher)(?:\s*\([^)]*\))?", alum)
    return (m.group(0).strip() if m else None), cap[1]


for _s, _e, _people, _note in _BL_REPORTS:
    _y = _report_year(_e)
    for _name, _role in _people:
        _al, _sha = _alumni_entry(_name)
        _n = "Barsky Lab publications page: " + _note
        if _al:
            _n += (f"; also under 'Recent Alumni' on the Barsky Lab personnel page as '{_al}' "
                   f"(personnel capture sha256 {_sha})")
        _barsky_students.append(ST(_name, _role, [_y, _y], SE(BLPUBS, _s, _e), must=[_name.split()[-1]], note=_n))

# current members on the Barsky Lab personnel page (page live 2026-10-21; first archived 2021-08; Shawn Zhao's
# Aug-2024 MS report shows the current lists date from 2024 or later)
_BL_CURRENT = [
    ('Jiangtian "Joey" Hou Graduate Student (EECS Major)', "Jiangtian Hou", "other"),
    ("Joshua Chen Graduate Student (M.S.)", "Joshua Chen", "masters"),
    ("Saketh Malyala Graduate Student (M.S.)", "Saketh Malyala", "masters"),
    ("Lei Chen Graduate Student (EECS Major)", "Lei Chen", "other"),
    ('Yuqing "Rachel" Liao Graduate Student (EECS Major)', "Yuqing Liao", "other"),
    ('Jinxuan "Alex" Liang Graduate Student (M.S.)', "Jinxuan Liang", "masters"),
    ("Allen Cao Graduate Student (M.S.)", "Allen Cao", "masters"),
    ("Yuanxiu “Christina” Wang Undergraduate Student", "Yuanxiu Wang", "undergraduate"),
    ("Aaron Zheng Undergraduate Student", "Aaron Zheng", "undergraduate"),
    ("Matthew Fogel Undergraduate Student (EECS Major)", "Matthew Fogel", "undergraduate"),
    ("Niall Mandal Undergraduate Student (CS Major)", "Niall Mandal", "undergraduate"),
    ("Yash Vardhan Pansari Undergraduate Student", "Yash Vardhan Pansari", "undergraduate"),
    ("Liheng Lai Undergraduate Student (CS & Stats Major)", "Liheng Lai", "undergraduate"),
    ('Ting-Che "Tim" Lin Undergraduate Student (CS Major; Math Minor)', "Ting-Che Lin", "undergraduate"),
    ("Ishaan Dasgupta Ghose Undergraduate Student", "Ishaan Dasgupta Ghose", "undergraduate"),
    ("Dhruv Kumar Undergraduate Student (CS Major)", "Dhruv Kumar", "undergraduate"),
]
for _q, _name, _role in _BL_CURRENT:
    _barsky_students.append(ST(_name, _role, None, Q(BLPERS, _q), must=[_name.split()[-1]],
                               note="Barsky Lab personnel page, current member ('Graduate Students' / 'Undergraduate Students' "
                                    "sections; 'Graduate Student (EECS Major)' is recorded as role other)"))

D["Brian A. Barsky"] = dict(
    status="pi",
    status_ev=[
        SE(BLPERS, "Faculty Professor Brian A. Barsky Principal Investigator", "Jiangtian \"Joey\" Hou Graduate Student (EECS Major)"),
        Q(TR20, "Advisors: Brian A. Barsky BibTeX citation: @mastersthesis{Holesinger:EECS-2020-181"),
        Q(TR24, "Advisors: Brian A. Barsky BibTeX citation: @mastersthesis{Zhao:EECS-2024-179"),
    ],
    students=_barsky_students,
    identity=dict(orcid=[], openalex=[], evidence=[
        ID("openalex_author_record_no_2016_works", oa_author_quote("A5046623635", "Brian A. Barsky"),
           "OpenAlex A5046623635 is his author record (Berkeley 1982-2015, 196 works) but has 0 works dated 2016 or later "
           "(works filter author.id + from_publication_date:2016-01-01 returned count 0); not anchored because no 2016+ "
           "work can be checked. Raw-author-name searches for 'Brian Barsky' / 'Brian A. Barsky' from 2016 return only "
           "namesakes, and the 2022 arXiv record W4302235174 ('Differentiable Subdivision Surface Fitting') lists only "
           "Tianhao Xie as author."),
    ]),
    appt=[Q(FAC16, "Brian A. Barsky Professor 785 Soda Hall"),
          Q(FAC17, "Brian A. Barsky Professor Emeritus 785 Soda Hall"),
          Q(CS19, "Brian A. Barsky Professor Emeritus , Professor in the Graduate School")],
    notes=("Emeritus since 2016/17 (Jan-2016 listing 'Professor', Nov-2017 'Professor Emeritus'; now Professor of the "
           "Graduate School) but he still runs the Barsky Lab (vision-correcting displays, assistive HCI): its personnel "
           "page lists current graduate and undergraduate members and ~100 'Recent Alumni', and its publications page "
           "dates MS research-project reports and M.Eng. capstone reports 2016-2022. EECS tech reports EECS-2020-181 "
           "(Holesinger) and EECS-2024-179 (Zhao) are MS reports with 'Advisors: Brian A. Barsky'. Last PhD: Fu-Chung "
           "Huang 2013 (EECS dissertations page, MGP). Students recorded: 2 EECS-TR MS students, 77 students named on "
           "dated 2016-2022 lab reports, 15 current members. Alumni on the personnel page without a dated 2016+ report "
           "were not added (the list reaches back to pre-2016 students such as Fu-Chung Huang). PAPERS: OpenAlex has no "
           "2016+ work attributed to Brian A. Barsky at all (his 2016+ output is EECS tech reports, talks, M.Eng. reports "
           "and arXiv preprints whose OpenAlex records omit him), so no identity anchor can produce lab papers; the gap "
           "on the paper side is an OpenAlex coverage gap, not a missing anchor."),
)

# ============================================================================ Manuel Blum (not_pi_in_window)
MGPBLUM = WB + "20260228122804id_/https://www.mathgenealogy.org/id.php?id=13373"
D["Manuel Blum"] = dict(
    status="not_pi_in_window",
    status_ev=[
        Q(EM16, "Manuel Blum Professor Emeritus"),
        Q("https://en.wikipedia.org/wiki/Manuel_Blum",
          "Blum worked as a professor of computer science at the University of California, Berkeley until 2001. From 2001 "
          "to 2018, he was the Bruce Nelson Professor of Computer Science at Carnegie Mellon University"),
        diss_newest("Manuel Blum"),
        SE(MGPBLUM, "Shahoumian, Troy University of California, Berkeley 1998", "Manuel Blum has 39 students"),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes=("Berkeley professor until 2001, then CMU (2001-2018); Berkeley Professor Emeritus throughout the window. His "
           "last Berkeley PhD was Troy Shahoumian (1998, EECS dissertations page and MGP); his later students (Hopper "
           "2004, von Ahn 2005, Williams 2007, Blocki/Meeder 2014, Samadi 2015, Singla 2018) were CMU students, outside "
           "Berkeley. No Berkeley advisee 2016-2026 found. Not anchored: the sweep candidate OpenAlex A5102766796 "
           "(ORCID 0000-0002-0982-4845) holds two 2022-23 consciousness papers with Lenore Blum, too few to verify "
           "against a 2016+ publication list (his EECS list ends 2004)."),
)

# ============================================================================ Michael J. Clancy (not_pi_in_window)
D["Michael J. Clancy"] = dict(
    status="not_pi_in_window",
    status_ev=[
        Q(EM16, "Michael J. Clancy Teaching Professor Emeritus"),
        Q(PROF + "clancy.html", "Michael J. Clancy Teaching Professor Emeritus Biography Michael Clancy was an active member "
          "both of the U.S. computer science education community and of the community of researchers into the psychology of programming."),
        Q(WB + "20160613204700id_/http://people.eecs.berkeley.edu:80/~clancy/", "Michael Clancy Mike Clancy Senior Lecturer"),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes=("Teaching faculty (Senior Lecturer / Teaching Professor), emeritus before the window (March-2016 emeritus "
           "listing); no EECS dissertations-by-faculty page exists for him (404) and his EECS publication list ends 2009. "
           "His 2018-2021 papers (Basic Data Structures Inventory, OpenAlex A5103084634, ORCID 0000-0002-6347-8277 in "
           "the sweep) are a multi-institution CS-education collaboration with Porter, Zingaro, Lee, Taylor, Webb and "
           "Nam Liao, not a Berkeley group; no Berkeley advisee found. Identity not anchored (no 2016+ own publication "
           "list to verify against)."),
)

# ============================================================================ Richard J. Fateman (not_pi_in_window)
MGPFATE = WB + "20241112231504id_/https://www.genealogy.math.ndsu.nodak.edu/id.php?id=25263"
D["Richard J. Fateman"] = dict(
    status="not_pi_in_window",
    status_ev=[
        Q(EM16, "Richard J. Fateman Professor Emeritus"),
        diss_newest("Richard J. Fateman"),
        SE(MGPFATE, "Students: Click here to see the students listed in chronological order.",
           "Richard Fateman has 2 students and 2 descendants."),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes=("Professor Emeritus before the window (March-2016 emeritus listing). Last PhD Taku Tokuyasu 2001 (EECS "
           "dissertations page; MGP lists two students, 1982 and 2001). His EECS publication list ends 2002 and the "
           "Berkeley sweep has no 2016+ work under his name. No 2016-2026 advisee found."),
)

# ============================================================================ Jerome A. Feldman (pi, ICSI)
ICSIAI16 = WB + "20160506110310id_/http://www.icsi.berkeley.edu/icsi/groups/ai/members"
ICSIAI17 = WB + "20170827072427id_/http://www.icsi.berkeley.edu/icsi/groups/ai/members"
ICSIAI19 = WB + "20191207174718id_/http://www.icsi.berkeley.edu/icsi/groups/ai/members"
ICSIF16 = WB + "20160821022822id_/http://www.icsi.berkeley.edu/icsi/people/feldman"
ICSIF24 = WB + "20240713093506id_/https://icsi.berkeley.edu/icsi/people/feldman"
ICSIBIB = WB + "20260323230820id_/https://www.icsi.berkeley.edu/icsi/biblio?f[author]=3202"
AIHEAD = "AI Group Members Research Director Professor Jerry Feldman"
D["Jerome A. Feldman"] = dict(
    status="pi",
    status_ev=[
        SE(ICSIAI16, AIHEAD, "Sean Trott"),
        SE(ICSIAI19, AIHEAD, "Research Staff and Students"),
        Q(ICSIBIB, "Doubleday, S. , Trott S. , & Feldman J. (2017). Processing Natural Language About Ongoing Actions in ECG"),
    ],
    students=[
        ST("Sean Trott", "member", [2016, 2016], SE(ICSIAI16, AIHEAD, "Sean Trott"),
           note=("ICSI AI Group 'Research Staff and Students' (May 2016 capture; also listed Oct 2015); co-author with "
                 "Feldman 2016-2017 (ICSI publication list)")),
        ST("Vivek Raghuram", "member", [2016, 2017], SE(ICSIAI17, AIHEAD, "Vivek Raghuram"),
           note=("ICSI AI Group 'Research Staff and Students' (May 2016 and Aug 2017 captures); UC Berkeley affiliation "
                 "on the 2016 GCAI paper with Feldman")),
        ST("Manfred Eppe", "other", [2016, 2016], SE(ICSIAI16, AIHEAD, "Manfred Eppe"),
           note="ICSI AI Group 'Visiting Researchers' (Oct 2015 and May 2016 captures); first author of the 2016 GCAI paper with Feldman"),
    ],
    identity=dict(orcid=["0000-0001-7889-6933"], openalex=["A5106731608"], evidence=[
        ID("openalex_author_record", oa_author_quote("A5106731608", "Jerome A. Feldman"),
           "OpenAlex author record (225 works; affiliations ICSI 1989-2022 and UC Berkeley 1994-2024) carrying ORCID 0000-0001-7889-6933."),
        ID("openalex_verified_by_publication_list",
           Q(ICSIBIB, "Feldman, J. (2019). Language, Stapp, and the Mind/Body/World Problem"),
           "ICSI publication list for author Jerome Feldman (linked from his ICSI profile as \"Jerome Feldman's publications\") "
           "lists OpenAlex W3089087896 (2019) of A5106731608."),
        ID("openalex_verified_by_publication_list",
           Q(ICSIBIB, "Doubleday, S. , Trott S. , & Feldman J. (2017). Processing Natural Language About Ongoing Actions in ECG"),
           "Same list: OpenAlex W2903519024 (2017) of A5106731608."),
        ID("openalex_verified_by_publication_list",
           Q(ICSIBIB, "Eppe, M. , Trott S. , Raghuram V. , Feldman J. , & Janin A. (2016). Application-Independent and "
                      "Integration-Friendly Natural Language Understanding"),
           "Same list: OpenAlex W2613413428 (2018 in OpenAlex) of A5106731608. 4 of its 16 2016+ works match the list."),
        ID("orcid_record", Q("https://orcid.org/0000-0001-7889-6933/person.json", '"displayName":"Jerome Feldman"', raw=True),
           "ORCID record of Jerome Feldman; its employment section (affiliationGroups.json, stored, sha256 "
           "cd9a4ffdd896650b06820612a61041abcfccfab6388ab9964377a447bd9448d5) reads 'University of California Berkeley UC "
           "Data | EECS | Professor | 1988-2015'."),
    ]),
    appt=[Q(EM16, "Jerome A. Feldman Professor Emeritus"),
          SE(ICSIF16, "Jerry Feldman Director, Artificial Intelligence", "Jerome Feldman received his bachelor"),
          SE(ICSIF24, "Jerry Feldman Emeritus Director, Artificial Intelligence", "Jerome Feldman received his bachelor")],
    notes=("Berkeley EECS Professor Emeritus before the window (March-2016 emeritus listing; last EECS PhD Leon Barrett "
           "2010), but through 2020 he was Research Director of the AI Group at ICSI (the Berkeley-affiliated "
           "International Computer Science Institute; 'Emeritus Director' by 2024). The group pages list 'Research Staff "
           "and Students' each year; only members who also co-authored with him 2016-2018 (ICSI publication list) are "
           "recorded: Sean Trott, Vivek Raghuram (UC Berkeley affiliation on the 2016 GCAI paper) and visiting researcher "
           "Manfred Eppe. Other listed members (FrameNet staff Collin Baker and Miriam Petruck, visiting faculty Steven "
           "Bird, and 2016-2020 student names) were not added because no source ties them to Feldman rather than to "
           "another ICSI AI project. CAVEAT: the group is at ICSI, not on campus; if the site counts only campus "
           "advising, Feldman is not_pi_in_window (emeritus before 2016, last PhD 2010). Identity: OpenAlex A5106731608 "
           "verified against the ICSI per-author publication list (4 matching 2016+ works); ORCID 0000-0001-7889-6933 "
           "is on that OpenAlex record and the ORCID record names him with UC Berkeley EECS."),
)

# ============================================================================ Domenico Ferrari (not_pi_in_window)
D["Domenico Ferrari"] = dict(
    status="not_pi_in_window",
    status_ev=[
        Q(EM16, "Domenico Ferrari Professor Emeritus Research Interests: UC Berkeley Unix Project"),
        diss_newest("Domenico Ferrari"),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes=("Professor Emeritus before the window (March-2016 emeritus listing); last EECS PhD Brian D. Whetten 2000; "
           "EECS publication list ends 1994; the Berkeley OpenAlex sweep has no 2016+ work under his name. No 2016-2026 "
           "advisee found. (The English Wikipedia 'Domenico Ferrari' is an 18th-century violinist, a namesake.)"),
)

# ============================================================================ Susan L. Graham (not_pi_in_window)
D["Susan L. Graham"] = dict(
    status="not_pi_in_window",
    status_ev=[
        Q(EM16, "Susan L. Graham Professor Emerita"),
        diss_newest("Susan L. Graham"),
        Q(WB + "20251231102121id_/https://www.mathgenealogy.org/id.php?id=22787",
          "According to our current on-line database, Susan Graham has 28 students and 31 descendants."),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes=("Pehong Chen Distinguished Professor Emerita, emerita before the window (March-2016 listing). Last PhD Marat "
           "Boshernitsan 2006 (EECS dissertations page; the MGP list of 28 students, stored, also ends 2006). Only one "
           "2016+ Berkeley work in the sweep (a 2021 Science letter). No 2016-2026 advisee found."),
)

# ============================================================================ Michael A. Harrison (not_pi_in_window)
D["Michael A. Harrison"] = dict(
    status="not_pi_in_window",
    status_ev=[
        SE(PROF + "harrison.html", "Michael A. Harrison was born in Philadelphia, PA.", "He retired in 1994."),
        Q(EM16, "Michael A. Harrison Professor Emeritus"),
        diss_newest("Michael A. Harrison"),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[Q("https://en.wikipedia.org/wiki/Michael_A._Harrison", "Michael A. Harrison ( 1935 or 1936 – ( 2025-06-07 ) June 7, 2025")],
    notes=("Retired 1994 (EECS profile); last EECS PhD Brian M. Dennis 1998 (MGP's 13 students end 1994). Died 7 June "
           "2025 (Wikipedia). The sweep's 'Michael Harrison' hits are namesakes (Michael I. Harrison, AHRQ; Michael R. "
           "Harrison, UCSF), which is why the pipeline saw adviser-name namesakes. No 2016-2026 advisee."),
)

# ============================================================================ Brian Harvey (not_pi_in_window)
D["Brian Harvey"] = dict(
    status="not_pi_in_window",
    status_ev=[
        Q(EM16, "Brian K. Harvey Teaching Professor Emeritus"),
        Q(PROF + "harvey.html", "Brian Harvey Teaching Professor Emeritus"),
        Q("https://en.wikipedia.org/wiki/Brian_Harvey_(lecturer)",
          "Brian Keith Harvey (born 1949) is a former Lecturer SOE [ clarification needed ] of computer science at University of California, Berkeley"),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes=("Teaching faculty (Senior Lecturer with Security of Employment), emeritus before the window (March-2016 "
           "emeritus listing). His homepage (people.eecs.berkeley.edu/~bh/, stored, sha256 "
           "30b500ff3b63722e55dd1e5c32f748adf711a11a48aa678725d44e1822404f26) says 'I am retired as of July 1, 2013' and "
           "describes teaching-only duties (that sentence is ~900 characters from his name on the page, so it is not "
           "quoted). Snap!/BJC work since 2016 is with Jens Moenig (SAP) and Dan Garcia, not a research group; no EECS "
           "dissertations page exists for him. The sweep's 'Brian Harvey' with ORCID 0000-0002-5902-4862 is a namesake "
           "(forest ecologist, U. Washington)."),
)

# ============================================================================ Paul N. Hilfinger (not_pi_in_window)
D["Paul N. Hilfinger"] = dict(
    status="not_pi_in_window",
    status_ev=[
        Q(FAC16, "Paul N. Hilfinger Teaching Professor"),
        Q(CS19, "Paul N. Hilfinger Teaching Professor"),
        Q(EMNOW, "Paul N. Hilfinger Professor of Teaching Emeritus"),
        diss_newest("Paul N. Hilfinger"),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes=("Teaching Professor throughout 2016-2019 (EECS listings), now Professor of Teaching Emeritus; his last PhD "
           "was Geoffrey Pike in 2002 and his EECS publication list (which carries advised MS reports for other faculty) "
           "ends 2007. His homepage is teaching-only (CS61B, the Berkeley Programming Contest, CPT sign-up). His one "
           "2016+ paper (ChocoPy, 2019) is with Rohan Padhye and Koushik Sen (Sen's student). Teaching faculty with no "
           "research group in the window."),
)

# ============================================================================ William M. Kahan (not_pi_in_window)
MGPKAHAN = WB + "20251220092450id_/https://www.mathgenealogy.org/id.php?id=16049"
D["William M. Kahan"] = dict(
    status="not_pi_in_window",
    status_ev=[
        SE(PROF + "kahan.html", 'William "Velvel" Kahan was born in Canada', "He retired from the University in 2008."),
        Q(EM16, "William M. Kahan Professor Emeritus"),
        SE(MGPKAHAN, "Students: Click here to see the students listed in chronological order.",
           "William Kahan has 7 students and 66 descendants."),
    ],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[],
    notes=("Retired 2008 (EECS profile). MGP lists 7 students, the last Ren-Cang Li (Berkeley 1995); the EECS "
           "dissertations page ends 1989. The only 2016+ Berkeley work under his name is a 2016 precision-tuning paper "
           "with Rubio-Gonzalez, Sen and Demmel's groups (a collaboration). No 2016-2026 advisee."),
)
