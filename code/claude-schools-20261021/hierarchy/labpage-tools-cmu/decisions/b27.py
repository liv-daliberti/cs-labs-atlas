from dhelp import M, PUB, WB  # noqa: F401  (kept: a project module; possibly a re-export or a side effect)
D = {}

# ---- Wenshan Wang ----
_WW = "https://www.ri.cmu.edu/ri-faculty/wenshan-wang/"
D["Wenshan Wang"] = dict(
    lab_site="https://www.ri.cmu.edu/robotics-groups/air-lab/",
    people_page=_WW,
    people_pages=[_WW],
    members=[
        M("Parv Maheshwari", "phd", None, _WW, near="current phd students"),
        M("Matthew Sivaprakasam", "phd", None, _WW, near="current phd students"),
        M("Yuchen Zhang", "phd", None, _WW, near="current phd students"),
        M("Ryan Ardalan", "masters", None, _WW, near="current masters students"),
        M("Avigyan Bhattacharya", "masters", None, _WW, near="current masters students"),
        M("Anthony Brogni", "masters", None, _WW, near="current masters students"),
        M("Jiting Cai", "masters", None, _WW, near="current masters students"),
        M("Trevor Chartier", "masters", None, _WW, near="current masters students"),
        M("Geethika Hemkumar", "masters", None, _WW, near="current masters students"),
        M("Joon Kwon", "masters", None, _WW, near="current masters students"),
        M("Winston Marveldoss", "masters", None, _WW, near="current masters students"),
        M("Hang Xu", "masters", None, _WW, near="current masters students"),
        M("Sejun Ahn", "member", None, _WW, near="current affiliates"),
        M("Sunhwi Kim", "member", None, _WW, near="current affiliates"),
        M("Ruogu Li", "member", None, _WW, near="current affiliates"),
        M("Mayuri Murugan", "member", None, _WW, near="current affiliates"),
        M("Micah Nye", "masters", None, _WW, near="past masters students", note="also listed under current affiliates"),
        M("Yilun Wu", "member", None, _WW, near="current affiliates"),
        M("Guofei Chen", "masters", None, _WW, near="past masters students", note="undated; PI joined CMU 2017 so past MS students are in window"),
        M("Pujith Kachana", "masters", None, _WW, near="past masters students", note="undated; PI joined CMU 2017"),
        M("Nicholas Leone", "masters", None, _WW, near="past masters students", note="undated; PI joined CMU 2017"),
        M("Shubhra Aich", "masters", None, _WW, near="past masters students", note="undated; PI joined CMU 2017"),
        M("Nader Zantout", "masters", None, _WW, near="past masters students", note="undated; PI joined CMU 2017"),
    ],
    pubs=[PUB("http://www.wangwenshan.com/", mode="li")],
    notes="Wang is a Systems Scientist at RI (postdoc 2017-19, project scientist 2019-) in the AirLab (Scherer head); the RI "
          "profile lists her own current PhD/MS students, affiliates and past MS students (no years given; all at CMU because she "
          "joined CMU in 2017). The AirLab RI page and external site (theairlab.org team 404) list Scherer's group, not hers, so only "
          "her profile was used. Wayback not used (backoff active; no dated people captures needed since profile is complete). "
          "Homepage publications list covers 2015-2019 only; li mode gives a few non-paper entries (project titles).",
    blocked=[],
)

# ---- Shinji Watanabe ----
_WV = "https://www.wavlab.org/members/"
_wv = []
def _cur(name, role, near, note=None):
    if near == "PhD Students" and name != "Jinchuan Tian":
        # heading is >1500 chars before the name (per-member publication lists in between)
        _wv.append(M(name, role, None, _WV, q=name + " ", near=None,
                     note=(note + "; " if note else "") + "listed under the PhD Students heading of the current members page"))
    else:
        _wv.append(M(name, role, None, _WV, near=near, note=note))
_cur("Samuele Cornell", "postdoc", "Post-Doc")
_cur("Jinchuan Tian", "phd", "PhD Students")
_cur("William Chen", "phd", "PhD Students")
_cur("Shikhar Bharadwaj", "phd", "PhD Students", "co-supervising")
_cur("Chien-yu Huang", "phd", "PhD Students")
_cur("Jaeyeon Kim", "phd", "PhD Students", "co-supervising")
_cur("Sichen Jin", "phd", "PhD Students")
_cur("Masao Someki", "phd", "PhD Students")
_cur("Chin-Jou Li", "phd", "PhD Students", "co-supervising")
_cur("Ting (Justin) Jiang", "phd", "PhD Students")
_cur("Haeri Kim", "phd", "PhD Students", "co-supervising")
_cur("Haoran Wang", "masters", "Master Students")
_cur("Kuang-Da Wang", "visitor", "Visitors")
_cur("Jee-weon Jung", "other", "Industrial Collaborators", "listed as industrial collaborator; also postdoc 2023-24 per alumni list")
# alumni entries: (line text, name, role, years, section)
_al = [
 ("2024. 02 - 2025. 05: Hye-jin Shim (CMU)", "Hye-jin Shim", "postdoc", [2024, 2025], "Post-Docs"),
 ("2023. 03 - 2024. 09: Jeeweon Jung (CMU)", "Jeeweon Jung", "postdoc", [2023, 2024], "Post-Docs"),
 ("2022. 03 - 2024. 08: Soumi Maiti (CMU)", "Soumi Maiti", "postdoc", [2022, 2024], "Post-Docs"),
 ("2021. 09 - 2024. 07: Zhong-Qiu Wang (CMU)", "Zhong-Qiu Wang", "postdoc", [2021, 2024], "Post-Docs"),
 ("2021. 09 - 2026. 04: Brian Yan (CMU)", "Brian Yan", "phd", [2021, 2026], "PhD"),
 ("2022. 05 - 2026. 03: Li-Wei Chen (CMU, co-supervising)", "Li-Wei Chen", "phd", [2022, 2026], "PhD"),
 ("2020. 08 - 2026. 03: Siddhant Arora (CMU)", "Siddhant Arora", "phd", [2020, 2026], "PhD"),
 ("2019. 09 - 2025. 12: Jiatong Shi (CMU)", "Jiatong Shi", "phd", [2019, 2025], "PhD"),
 ("2020. 09 - 2025. 04: Yifan Peng (CMU)", "Yifan Peng", "phd", [2020, 2025], "PhD"),
 ("2019. 09 - 2024. 05: Xuankai Chang (CMU)", "Xuankai Chang", "phd", [2019, 2024], "PhD"),
 ("2021. 09 - 2024. 05: Muqiao Yang (CMU, co-supervisor)", "Muqiao Yang", "phd", [2021, 2024], "PhD"),
 ("2021. 01 - 2023. 06: Xinjian Li (CMU, co-supervisor)", "Xinjian Li", "phd", [2021, 2023], "PhD"),
 ("2020. 09 - 2023. 06: Jessica Huynh (CMU, co-supervisor)", "Jessica Huynh", "phd", [2020, 2023], "PhD"),
 ("2020. 09 - 2022. 08: Siddharth Dalmia (CMU, co-supervisor)", "Siddharth Dalmia", "phd", [2020, 2022], "PhD"),
 ("2024. 08 - 2026. 05: Chyi-Jiunn Lin (CMU)", "Chyi-Jiunn Lin", "masters", [2024, 2026], "MS & Undergraduate"),
 ("2023. 05 - 2025. 05: Kwanghee Choi (CMU)", "Kwanghee Choi", "masters", [2023, 2025], "MS & Undergraduate"),
 ("2022. 09 - 2024. 05: Shih-Lun Wu (CMU)", "Shih-Lun Wu", "masters", [2022, 2024], "MS & Undergraduate"),
 ("2021. 09 - 2023. 05: Dan Berrebbi (CMU)", "Dan Berrebbi", "masters", [2021, 2023], "MS & Undergraduate"),
 ("2021. 09 - 2022. 12: Dorsa Zeinali (CMU)", "Dorsa Zeinali", "masters", [2021, 2022], "MS & Undergraduate"),
 ("2021. 09 - 2022. 12: Karthik Ganesan (MIIS directed study, CMU)", "Karthik Ganesan", "masters", [2021, 2022], "MS & Undergraduate"),
 ("2021. 01 - 2022. 08: Chaitanya Narisetty (CMU)", "Chaitanya Narisetty", "masters", [2021, 2022], "MS & Undergraduate"),
 ("2021. 01 - 2022. 08: Peter Wu (CMU, co-supervisor)", "Peter Wu", "masters", [2021, 2022], "MS & Undergraduate"),
 ("2021. 09 - 2022. 08: Sujay Suresh Kumar (MIIS directed study, CMU)", "Sujay Suresh Kumar", "masters", [2021, 2022], "MS & Undergraduate"),
 ("2021. 09 - 2022. 08: Debayan Ghosh (CMU)", "Debayan Ghosh", "masters", [2021, 2022], "MS & Undergraduate"),
 ("2023. 09 -- 2024. 06: Karen Livescu (TTIC)", "Karen Livescu", "visitor", [2023, 2024], "Visting Faculty"),
]
for _q, _n, _r, _y, _s in _al:
    _wv.append(M(_n, _r, _y, _WV, q=_q, near=None))
_vis = [
 ("2026. 05 - 2026. 08: Thanapat Trachu (University of Southern California)", "Thanapat Trachu", [2026, 2026]),
 ("2026. 02 - 2026. 07: Dahee Yang (Hanyang University)", "Dahee Yang", [2026, 2026]),
 ("2026. 01 - 2026. 05: Alexander Polok (Brno University of Technology)", "Alexander Polok", [2026, 2026]),
 ("2025. 12 - 2026. 03: Xun Gong (Shanghai Jiao Tong University)", "Xun Gong", [2025, 2026]),
 ("2025. 08 - 2025. 12: Haoran Wang (Shanghai Jiao Tong University)", "Haoran Wang", [2025, 2025]),
 ("2025. 04 - 2025. 12: Bo-Hao Su (National Tsing Hua University)", "Bo-Hao Su", [2025, 2025]),
 ("2025. 05 - 2025. 11: Ji-Hoon Kim (Korea Advanced Institute of Science and Technology)", "Ji-Hoon Kim", [2025, 2025]),
 ("2025. 02 - 2025. 07: Jialu Li (University of Illinois Urbana-Champaign)", "Jialu Li", [2025, 2025]),
 ("2025. 01 - 2025. 04: Pu Wang (KU Leuven)", "Pu Wang", [2025, 2025]),
 ("2024. 08 - 2025. 02: Kalvin Chang (UC Berkeley)", "Kalvin Chang", [2024, 2025]),
 ("2024. 09 - 2025. 02: Holger Severin Bovbjerg (Aalborg University)", "Holger Severin Bovbjerg", [2024, 2025]),
 ("2024. 11 - 2024. 12: Junyi Peng (Brno University of Technology)", "Junyi Peng", [2024, 2024]),
 ("2024. 08 - 2024. 12: Carlos Carvalho (Instituto Superior", "Carlos Carvalho", [2024, 2024]),
 ("2024. 04 - 2024. 12: Shuichiro Shimizu (Kyoto University)", "Shuichiro Shimizu", [2024, 2024]),
 ("2024. 08 - 2024. 11: Shih-Heng Wang (National Taiwan University)", "Shih-Heng Wang", [2024, 2024]),
 ("2024. 08 - 2024. 11: Yoshiaki Bando (National Institute of Advanced Industrial Science and Technology)", "Yoshiaki Bando", [2024, 2024]),
 ("2023. 09 - 2024. 08: Yihan Wu (Renmin University)", "Yihan Wu", [2023, 2024]),
 ("2023. 11 - 2024. 04: Chenda Li (Shanghai Jiaotong University)", "Chenda Li", [2023, 2024]),
 ("2023. 08 - 2024. 03: Roshan Sharma (Carnegie Mellon University)", "Roshan Sharma", [2023, 2024]),
 ("2023. 03 - 2024. 03: Wangyou Zhang (Shanghai Jiaotong University)", "Wangyou Zhang", [2023, 2024]),
 ("2023. 08 - 2023. 10: Minsu Kim (Korea Advanced Institute of Science and Technology)", "Minsu Kim", [2023, 2023]),
 ("2023. 05 - 2023. 08: Kohei Saijo (Waseda University)", "Kohei Saijo", [2023, 2023]),
 ("2022. 10 - 2023. 01: Takaaki Saeki (University of Tokyo)", "Takaaki Saeki", [2022, 2023]),
 ("2021. 12 - 2022. 12: Yosuke Kashiwagi (Sony)", "Yosuke Kashiwagi", [2021, 2022]),
 ("2022. 03 - 2022. 06: Yoshiki Masuyama (Tokyo Metropolitan University)", "Yoshiki Masuyama", [2022, 2022]),
 ("2021. 07 - 2022. 07: Yushi Ueda (Japan Patent Office)", "Yushi Ueda", [2021, 2022]),
 ("2021. 08 - 2021. 12: Yen-Ju Lu (Research Center for Information Technology Innovation, Academia Sinica)", "Yen-Ju Lu", [2021, 2021]),
]
for _q, _n, _y in _vis:
    _wv.append(M(_n, "visitor", _y, _WV, q=_q, near=None))

D["Shinji Watanabe"] = dict(
    lab_site="https://www.wavlab.org/",
    people_page=_WV,
    people_pages=[_WV],
    members=_wv,
    pubs=[PUB("https://www.wavlab.org/publications/", mode="auto")],
    notes="WAVLab members page (live, 2026) lists current faculty/postdoc/PhD/MS/visitors plus a dated Alumni section (visiting faculty, "
          "postdocs, PhD, MS/undergraduate, visitors). Recorded all CMU-era entries (Watanabe joined CMU 2020-08). Skipped entries marked JHU "
          "(Aswin Shanmugam Subramanian, Matthew Maciejewski, Matthew Wiesner, Tianzi Wang, Zhiqi Wang, Szu-Jui Chen) and visitors dated "
          "before 2020-08 from his JHU years (Pengcheng Guo, Yosuke Higuchi 2019-12/2020-03 stay [also 2022-03/06], Jing Shi, Katsuki Inoue, "
          "Murali Karthick Baskar, Xuankai Chang visitor 2018, Hirofumi Inaguma, Yusuke Fujita, Nelson Yalta Soplin). Yosuke Higuchi's 2022 CMU "
          "stay is not recorded separately as the line also covers a pre-CMU stay. Wayback not used (dated alumni list is complete on live "
          "page).",
    blocked=[],
)

# ---- Leila Wehbe ----
_LW = "https://leilawehbe.com/group/"
_lw = [
    M("James Fodor", "postdoc", None, _LW, near="Current members"),
    M("Subha Nawer Pushpita", "phd", None, _LW, near="Current members"),
    M("Francisco Guedes", "phd", None, _LW, near="Current members", note="University of Lisbon PhD student, CMU-affiliated"),
    M("Jerry Jin", "other", None, _LW, near="Current members", note="rotation student, CSD"),
]
for _n, _r, _t in [
    ("Maggie Henderson", "postdoc", "Postdoc (co-advised with Mike Tarr)"),
    ("Julien Dirani", "postdoc", "Postdoc (co-advised with Brad Mahon)"),
    ("Isil Bilgin", "postdoc", "Postdoc (co-advised with Pierre Bellec"),
    ("Joel Ye", "phd", "PNC PhD student (co-advised with Rob Gaunt)"),
    ("Yuchen Zhou", "phd", "CNBC/Psych PhD student"),
    ("Ruogu Lin", "phd", "CBD PhD student"),
    ("Andrew Luo", "phd", "PNC/MLD PhD student"),
    ("Tara Pirnia", "phd", "PNC/MLD PhD student"),
    ("Aria Wang", "phd", "PNC/MLD PhD student"),
    ("Jennifer Williams", "phd", "CBD PhD student"),
    ("Mariya Toneva", "phd", "MLD PhD student"),
    ("Anand Bollu", "masters", "CS Master's"),
    ("Srinivas Ravishankar", "masters", "MLD Master's"),
    ("Aniketh Reddy", "masters", "MLD Master's"),
    ("Nidhi Jain", "masters", "CS Master's"),
    ("Saaketh Medepalli", "masters", "MLD Master's"),
]:
    _lw.append(M(_n, _r, None, _LW, near="Alumni", note="undated alumnus of the group; PI at CMU since 2016 so tenure with her falls in window"))
D["Leila Wehbe"] = dict(
    lab_site="https://leilawehbe.com/",
    people_page=_LW,
    people_pages=[_LW],
    members=_lw,
    pubs=[PUB("https://leilawehbe.com/publications/", mode="css:article.pcard")],
    notes="Live group page (leilawehbe.com/group; old cs.cmu.edu/~lwehbe redirects here) lists 4 current members and 16 undated alumni "
          "(postdocs, PhD, MS) with current positions; the page also shows Wehbe herself now Associate Professor at Stanford. Undated "
          "alumni recorded because the PI has been at CMU since 2016 (their time with her is in the window); co-advisors (Tarr, Mahon, "
          "Bellec, Gaunt, Nozari, Mitchell) are not recorded.",
    blocked=[],
)

# ---- Sean Welleck ----
_L3 = "https://cmu-l3.github.io/"
_sw = []
for _n, _r, _h in [
    ("Pranjal Aggarwal", "phd", "members PhD"), ("Weihua Du", "phd", "members PhD"), ("Andre He", "phd", "members PhD"),
    ("Seungone Kim", "phd", "members PhD"), ("Peiyang Song", "phd", "members PhD"), ("Tianran Sun", "phd", "members PhD"),
    ("Zeyu Zheng", "phd", "members PhD"),
    ("Anmol Agarwal", "masters", "MS"), ("Riyaz Ahuja", "masters", "MS"), ("Jiewen Hu", "masters", "MS"),
    ("Qinyue Tan", "masters", "MS"), ("Thomas Zhu", "masters", "MS"),
    ("Tate Rowney", "undergraduate", "Undergrad"),
]:
    _sw.append(M(_n, _r, None, _L3, near=_h))
D["Sean Welleck"] = dict(
    lab_site=_L3,
    people_page=_L3,
    people_pages=[_L3],
    members=_sw,
    pubs=[PUB("https://cmu-l3.github.io/publications/", mode="auto")],
    notes="L3 Lab site (cmu-l3.github.io, same member list as wellecks.com Group section) lists 7 PhD, 5 MS and 1 undergraduate; no alumni "
          "section. Welleck joined CMU in 2024. Co-advisors (Yiming Yang, Daniel Fried, Graham Neubig, Prasad Tetali, Jeremy Avigad) not "
          "recorded. Wayback captures of the L3 page (2024/2025) could not be read (archive.org back-off).",
    blocked=[],
)

# ---- Bryan Wilder ----
_BW = "https://bryanwilder.github.io/group/"
D["Bryan Wilder"] = dict(
    lab_site="https://bryanwilder.github.io/group/",
    people_page=_BW,
    people_pages=[_BW],
    members=[
        M("Ye Won (Emily) Byun", "phd", None, _BW, near="PhD Students"),
        M("Santiago Cortes Gomez", "phd", None, _BW, near="PhD Students"),
        M("Ruiqi Lyu", "phd", None, _BW, near="PhD Students"),
        M("Khurram Yamin", "phd", None, _BW, near="PhD Students"),
        M("Maitreyi Swaroop", "phd", None, _BW, near="PhD Students"),
        M("Kanad Pardeshi", "phd", None, _BW, near="PhD Students"),
        M("Jingjing Tang", "phd", None, _BW, near="PhD Students"),
        M("Aishik Nagar", "phd", None, _BW, near="PhD Students"),
        M("Jianyu Xu", "postdoc", None, _BW, near="Postdoc"),
        M("Vibhhu Sharma", "masters", [None, 2025], _BW, near="Alumni", note="MS 2025 per page"),
        M("Kevin Ren", "undergraduate", [None, 2025], _BW, near="Alumni", note="BS 2025 per page"),
        M("Ananya Joshi", "phd", [None, 2025], _BW, near="Alumni", note="PhD 2025, co-advised with Roni Rosenfeld"),
    ],
    pubs=[PUB("https://bryanwilder.github.io/publications/", mode="auto")],
    notes="Lab for AI and Social Impact group page lists 8 current PhD students, 1 postdoc and 3 dated alumni; all recorded. Wilder joined "
          "CMU in 2021. Co-advisors (Lipton, Rosenfeld, Singh) not recorded. Wayback not needed (alumni dated on live page).",
    blocked=[],
)

# ---- Randi Williams ----
_RW = "https://hcii.cmu.edu/people/randi-williams"
D["Randi Williams"] = dict(
    lab_site="https://randiwilliams.com/",
    people_page=_RW,
    people_pages=[_RW],
    members=[
        M("Leah Teffera", "phd", None, _RW, near="Advisees"),
    ],
    pubs=[],
    notes="Personal site randiwilliams.com is a project portfolio (AI education, Day of AI, MIT Media Lab work) with no group/people page and no "
          "publications list (points to Google Scholar only). The HCII profile lists one advisee, Leah Teffera. Wayback not used.",
    blocked=[],
)

# ---- David Woodruff ----
_DW = "http://www.cs.cmu.edu/~dwoodruf/"
_dw = []
for _n, _r, _note in [
    ("Ainesh Bakshi", "phd", "co-advised with Pravesh Kothari; graduated"),
    ("Rajesh Jayaram", "phd", "graduated"), ("Praneeth Kacham", "phd", "graduated"), ("Honghao Lin", "phd", "graduated"),
    ("Hoai-An Nguyen", "phd", "co-advised with Yang Liu"), ("Hai Pham", "phd", "co-advised with Barnabas Poczos; graduated"),
    ("Madhusudhan Pittu", "phd", "co-advised with Anupam Gupta; graduated"), ("Kijun Shin", "phd", None),
    ("Shenghao Xie", "phd", None), ("Taisuke Yasuda", "phd", "graduated"),
    ("Hongyang Zhang", "phd", "co-advised with Nina Balcan; graduated"),
    ("William Swartworth", "postdoc", None), ("Samson Zhou", "postdoc", None),
]:
    _dw.append(M(_n, _r, None, _DW, s="My Amazing Students and Postdocs", e=_n, note=("page gives no years; " + _note) if _note else "page gives no years"))
D["David Woodruff"] = dict(
    lab_site=_DW,
    people_page=_DW,
    people_pages=[_DW],
    members=_dw,
    pubs=[],
    notes="PI homepage section 'My Amazing Students and Postdocs' lists 11 students (current and graduated, undated; PI at CMU since 2017) and "
          "2 postdocs; all recorded. The homepage publication list is plain 'VENUE, Title with coauthors' text that none of the pubs modes "
          "parses into titles (previews returned link labels and award notes), so no publications page added. PI is on leave at Google. "
          "Wayback not used.",
    blocked=["https://www.siam.org/conferences/cm/program/accepted-papers/soda24-accepted-papers (bot-challenge; not a lab page)"],
)

# ---- Sherry Tongshuang Wu ----
_SW = "https://www.cs.cmu.edu/~sherryw/group.html"
_swu = []
for _n, _r, _h in [
    ("Simret Araya Gebreegziabher", "postdoc", "Current Members"), ("Jieun Kim", "postdoc", "Current Members"),
    ("Vijay Viswanathan", "phd", "Current Members"), ("Christina Ma", "phd", "Current Members"),
    ("Xinran Zhao", "phd", "Current Members"), ("Jessie Mindel", "phd", "Current Members"),
    ("Zheyuan Zhang", "phd", "Current Members"), ("Eunsu Kim", "phd", "Current Members"),
    ("Keyu He", "masters", "Current Members"), ("Pengcheng Jing", "masters", "Current Members"),
    ("Jiasi Wang", "undergraduate", "Current Members"), ("Yuan Tian", "visitor", "Current Members"),
    ("Seungyeon (Lily) Back", "visitor", "Current Members"),
    ("Chenyang Yang", "phd", "Alumni"), ("Yiyang (Diana) Wang", "masters", "Alumni"),
    ("Yuanchen (Sophie) Bai", "masters", "Alumni"), ("Raoyi (Cathy) Huang", "masters", "Alumni"),
    ("Atharva Naik", "masters", "Alumni"), ("Jushaan Kalra", "masters", "Alumni"), ("Yilin Zhang", "masters", "Alumni"),
    ("Callum Zhao", "masters", "Alumni"), ("Cassandra Shi", "undergraduate", "Alumni"), ("Cheng Qian", "visitor", "Alumni"),
]:
    _swu.append(M(_n, _r, None, _SW, near=_h, note=None if _h == "Current Members" else "undated alumnus; PI at CMU since 2021"))
D["Sherry Tongshuang Wu"] = dict(
    lab_site="https://www.cs.cmu.edu/~sherryw/group.html",
    people_page=_SW,
    people_pages=[_SW],
    members=_swu,
    pubs=[PUB(_SW, mode="css:div.publication")],
    notes="WInE Lab page (group.html on PI's cs.cmu.edu site) lists 13 current members (2 postdocs, 6 PhD, 2 MS, 1 undergrad, 2 visitors) and "
          "10 undated alumni; all recorded (PI joined CMU in 2021). Co-advisors (Kraut, Zhu, Wang, Neubig, Koedinger, Kastner) not recorded. "
          "Wayback captures not read (live page complete).",
    blocked=[],
)

# ---- Steven Wu ----
_ZW = "https://zstevenwu.com/index.html"
_zw = []
for _n, _r, _h, _note in [
    ("Terrance Liu", "phd", "PhD students", None), ("Jingwu Tang", "phd", "PhD students", "co-advised by Fei Fang"),
    ("Anusha Sinha", "phd", "PhD students", "co-advised by Hoda Heidari"),
    ("Kimberly Truong", "phd", "PhD students", "co-advised by Hoda Heidari"),
    ("Jiahao Zhang", "phd", "PhD students", None), ("Keltin Grimes", "phd", "PhD students", None),
    ("Rui Melo", "phd", "PhD students", None), ("Jiayun Wu", "phd", "PhD students", "co-advised by Andrew Ilyas"),
    ("Yifei Pang", "masters", "Master's Students", "MS; later PhD student at UNC"),
    ("Gokul Swamy", "phd", "Alumni", "undated alumnus; PI at CMU since 2021"),
    ("Luke Guerdan", "phd", "Alumni", "undated alumnus; PI at CMU since 2021"),
    ("Pratiksha Thaker", "postdoc", "Alumni", "undated alumnus (post-doc, now Databricks)"),
    ("Keegan Harris", "phd", "Alumni", "undated alumnus; PI at CMU since 2021"),
    ("Justin Whitehouse", "phd", "Alumni", "undated alumnus (PhD student, now post-doc at Stanford)"),
    ("Shuran Zheng", "postdoc", "Alumni", "undated alumnus (post-doc, now Tsinghua IIIS faculty)"),
    ("Xin Gu", "masters", "Past CMU master's and undergrads", "MS, undated; page says past CMU"),
    ("Ken Ziyu Liu", "masters", "Past CMU master's and undergrads", "MS, undated; page says past CMU"),
    ("Konwoo Kim", "undergraduate", "Past CMU master's and undergrads", "undergrad, undated; page says past CMU"),
    ("Ally Du", "undergraduate", "Past CMU master's and undergrads", "undergrad, undated; page says past CMU"),
    ("Kevin Ren", "undergraduate", "Past CMU master's and undergrads", "undergrad, undated; page says past CMU"),
    ("Xiaoyu Wu", "visitor", "Past visiting and REU students", "visiting master's student from Shanghai Jiaotong U.; undated; recorded because already held for this lab"),
]:
    _zw.append(M(_n, _r, None, _ZW, near=_h, note=_note))
D["Steven Wu"] = dict(
    lab_site="https://zstevenwu.com/",
    people_page=_ZW,
    people_pages=[_ZW],
    members=_zw,
    pubs=[PUB("https://zstevenwu.com/papers.html", mode="css:div.paper", title_css="h5")],
    notes="Group section of the PI homepage lists 8 current PhD students (some co-advised), 1 MS, alumni with current positions (undated), "
          "past CMU MS/undergrads and 'past visiting and REU students' (undated). Wu joined CMU in 2021 after Minnesota: the alumni "
          "Giuseppe Vietri, Hao-Fei Cheng, Daniel Ngo and Logan Stapleton were not recorded (previous-institution students; page does not "
          "place them at CMU). 15 undated visiting/REU students skipped (Xiaoyu Wu recorded as already held). Wayback not used.",
    blocked=[],
)

# ---- David Wettergreen ----
_DWE = "https://www.ri.cmu.edu/ri-faculty/david-wettergreen/"
_RIS = "https://www.ri.cmu.edu/people/students/?wpv_post_search=&wpv_post_advisor=wettergreen"
_dwe = [
    M("Margaret Hansen", "phd", None, _DWE, near="current phd students"),
    M("Tushaar Jain", "phd", None, _DWE, near="current phd students"),
    M("Warren Whittaker", "member", None, _DWE, near="current affiliates"),
    M("Ethan Holand", "masters", None, _RIS, q="Ethan Holand MSR Student", note="listed as current MSR student / graduate research assistant on the RI students page filtered by advisor"),
]
for _n in ["Abigail Breitfeld", "Mark Desnoyer", "Greydon Foil", "Padraig Michael Furlong", "Alberto Candela Garza", "Nathan Otten",
           "Ananya Rao", "Srinivasan Vijayarangan"]:
    _dwe.append(M(_n, "phd", None, _DWE, near="past phd students", note="undated past PhD student on RI profile; recorded because already held from other sources"))
for _n in ["Joseph Amato", "Kevin Edelson", "Haidar Jamal", "Suhit Kodgule", "Samuel Ong", "Karen Orton", "David Russell",
           "Paloma Sodhi", "Himanshi Yadav", "Zongyi Yang"]:
    _dwe.append(M(_n, "masters", None, _DWE, near="past masters students", note="undated past MS student on RI profile; recorded because already held from other sources"))
D["David Wettergreen"] = dict(
    lab_site="https://sites.google.com/view/david-wettergreen",
    people_page=_DWE,
    people_pages=[_DWE, _RIS],
    members=_dwe,
    pubs=[],
    notes="PI Google Sites page has no members list (links to the RI student filter 'wpv_post_advisor=wettergreen', which currently shows 3 "
          "people). The RI profile lists current PhD students, an affiliate and undated past PhD (13) and MS (23) students; only past students "
          "already held from other sources were recorded, the other undated past students were skipped (many predate 2016: e.g. Fairfield, "
          "Seo, Skonieczny, Stubbs, Thompson, Bartlett, Dunlop, Harris, Kraut, Lee, Luders, Seegmiller, Sigel, Villa, Calderon, Inotsume, "
          "Loret de Mola). Publications page on the Google Site is JavaScript-rendered (no parsable entries).",
    blocked=[],
)

# ---- William Red L Whittaker ----
_WW2 = "https://www.ri.cmu.edu/ri-faculty/william-red-l-whittaker/"
_ww = [
    M("Brady Stump", "masters", None, _WW2, near="current masters students"),
    M("Timothy Angert", "member", None, _WW2, near="current affiliates"),
    M("Lou Chomas", "member", None, _WW2, near="current affiliates"),
    M("Heather Jones", "staff", None, _WW2, near="current affiliates", note="also past PhD student listed on the same profile"),
    M("Tanvi Lad", "member", None, _WW2, near="current affiliates"),
]
for _n, _r, _h in [
    ("Joseph Bartels", "phd", "past phd students"), ("Christopher Cunningham", "phd", "past phd students"),
    ("Eugene Fang", "phd", "past phd students"), ("Paulo Rotband Marchtein Fisch", "phd", "past phd students"),
    ("Nathan Otten", "phd", "past phd students"),
    ("Joseph Amato", "masters", "past masters students"), ("Neal S. Bhasin", "masters", "past masters students"),
    ("Myles Blodnick", "masters", "past masters students"), ("Jack Buffington", "masters", "past masters students"),
    ("Matthew Hanczor", "masters", "past masters students"), ("Haidar Jamal", "masters", "past masters students"),
    ("Nikhil Jog", "masters", "past masters students"), ("Neil Khera", "masters", "past masters students"),
    ("Michael Lee", "masters", "past masters students"),
]:
    _ww.append(M(_n, _r, None, _WW2, near=_h, note="undated past student on RI profile; recorded because already held from other sources"))
D["William Red L Whittaker"] = dict(
    lab_site="https://frc.ri.cmu.edu/~red/",
    people_page=_WW2,
    people_pages=[_WW2],
    members=_ww,
    pubs=[],
    notes="PI page frc.ri.cmu.edu/~red/ ('PhD's Directed', 'Representative Publications') now redirects to the generic RI Field Robotics page "
          "(no data). The RI profile lists 1 current MS student, 4 affiliates and undated past PhD (25) and MS (~35) students; only past "
          "students already held from other sources were recorded, other undated ones skipped (most predate 2016).",
    blocked=[],
)

# ---- Larry A Wasserman ----
D["Larry A Wasserman"] = dict(
    lab_site="https://www.stat.cmu.edu/~larry/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="Homepage (stat.cmu.edu/~larry) has no student/advisee list and no publications list (links only to arXiv search and Google Scholar, "
          "which is off limits); the Statistics and Data Science and MLD faculty profiles carry bio and research areas only. Linked group pages: "
          "the Statistical Machine Learning Theory Group (statml.cs.cmu.edu; live host no longer resolves, Wayback 2025 capture is a weekly reading-group "
          "page for many faculty and students, not Wasserman's own advisees, so not used) and the STAMPS center page (no member list). "
          "Nothing usable for members or publications.",
    blocked=[],
)
