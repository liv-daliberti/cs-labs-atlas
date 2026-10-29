from dhelp import M, PUB, WB
D = {}

WW = "https://www.cs.cmu.edu/~weiwu2/people.html"
D["Wei Wu"] = dict(
    lab_site="https://www.cs.cmu.edu/~weiwu2/",
    people_page=WW,
    people_pages=[WW, WB + "20170226171705id_/http://www.cs.cmu.edu:80/~weiwu2/people.html",
                  WB + "20200117201847id_/http://www.cs.cmu.edu:80/~weiwu2/people.html"],
    members=[
        M("Seojin Bang", "phd", None, WW, near="Current Students"),
        M("Siwei Xie", "masters", None, WW, near="Current Students"),
        M("Xupeng Tong", "masters", None, WW, near="Current Students"),
        M("Micol Marchetti-Bowick", "phd", None, WW, near="Students who are working with me", note="advisor Eric Xing, co-working with Wei Wu"),
        M("Pengtao Xie", "phd", None, WW, near="Students who are working with me", note="advisor Eric Xing, co-working with Wei Wu"),
    ],
    pubs=[],
    notes="Live people page (cs.cmu.edu/~weiwu2/people.html) lists 3 current students plus 2 Xing-advised PhD students working with her; 2017 and 2020 Wayback captures show the identical list, 2024 capture is the same as live. No alumni section, no dedicated publications page (homepage has only a short Selected Publications list). Collaborators (Sally Wenzel, Eric Xing, etc.) are faculty, excluded.",
    blocked=[],
)

XS = "https://sailing-lab.github.io/people/"
XH17 = WB + "20170101230911id_/http://www.cs.cmu.edu/~epxing/"
D["Eric Xing"] = dict(
    lab_site="https://sailing-lab.github.io/",
    people_page=XS,
    people_pages=[XS, XH17],
    members=[
        M("Aviv Bick", "phd", None, XS, near="Current (CMU)"),
        M("Mingkai Deng", "phd", None, XS, near="Current (CMU)"),
        M("Caleb Ellington", "phd", None, XS, near="Current (CMU)"),
        M("Han Guo", "phd", None, XS, near="Current (CMU)"),
        M("Jinyu Hou", "phd", None, XS, near="Current (CMU)"),
        M("Lingjing Kong", "phd", None, XS, near="Current (CMU)"),
        M("Lara Sá Neves", "phd", None, XS, near="Current (CMU)"),
        M("Sazan Mahbub", "phd", None, XS, near="Current (CMU)"),
        M("Nicholas Ho", "phd", None, XS, near="Current (CMU)"),
        M("Bowen Tan", "phd", None, XS, near="Current (CMU)"),
        M("Yonghao Zhuang", "phd", None, XS, near="Current (CMU)"),
        M("Maruan Al-Shedivat", "phd", [None, 2021], XH17, near="Current Students and Postdocs:", note="listed current Jan 2017; defended Sep 2021 per sailing-lab news"),
        M("Abutalib Aghayev", "phd", None, XH17, near="Current Students and Postdocs:"),
        M("Kumar Avinava Dubey", "postdoc", None, XH17, near="Current Students and Postdocs:"),
        M("Wei Dai", "phd", None, XH17, near="Current Students and Postdocs:"),
        M("Zhiting Hu", "postdoc", None, XH17, near="Current Students and Postdocs:"),
        M("Jin Kyu Kim", "phd", None, XH17, near="Current Students and Postdocs:"),
        M("Lisa Lee", "phd", [None, 2021], XH17, near="Current Students and Postdocs:", note="listed current Jan 2017; defended Sep 2021 per sailing-lab news"),
        M("Ben Lengerich", "phd", [None, 2024], XH17, near="Current Students and Postdocs:", note="defended Oct 2024 per sailing-lab news"),
        M("Xiaodan Liang", "postdoc", None, XH17, near="Current Students and Postdocs:"),
        M("Micol Marchetti-Bowick", "phd", None, XH17, near="Current Students and Postdocs:"),
        M("Willie Neiswanger", "phd", None, XH17, near="Current Students and Postdocs:"),
        M("Aurick Qiao", "phd", [None, 2021], XH17, near="Current Students and Postdocs:", note="defended Sep 2021 per sailing-lab news"),
        M("Mrinmaya Sachan", "phd", None, XH17, near="Current Students and Postdocs:"),
        M("Haohan Wang", "phd", None, XH17, near="Current Students and Postdocs:"),
        M("Jinliang Wei", "phd", None, XH17, near="Current Students and Postdocs:"),
        M("Pengtao Xie", "phd", None, XH17, near="Current Students and Postdocs:"),
        M("Hao Zhang", "phd", None, XH17, near="Current Students and Postdocs:"),
        M("Xun Zheng", "phd", None, XH17, near="Current Students and Postdocs:"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~epxing/publications-2026.html", mode="auto"),
          PUB("https://sailing-lab.github.io/publications/", mode="auto")],
    notes="Live homepage and Sailing Lab people page (current CMU vs MBZUAI students; MBZUAI students skipped). Alumni lists on both are undated (about 55 undated alumni skipped, many of whom were at CMU 2016+; only those seen as current on 2017+ captures recorded). Jan 2017 homepage capture gives the 18 current students/postdocs. Faculty alumni (Seyoung Kim, Steve Hanneke) excluded.",
    blocked=[],
)


CXT = "https://www.cs.cmu.edu/~cxcscmu/team/"
D["Chenyan Xiong"] = dict(
    lab_site="https://www.cs.cmu.edu/~cxcscmu/",
    people_page=CXT,
    people_pages=[CXT],
    members=[
        M("Cathy Jiao", "phd", None, CXT, near="PhD Students"),
        M("Gabriel Moreira", "phd", None, CXT, near="PhD Students"),
        M("Hao Kang", "phd", None, CXT, near="PhD Students"),
        M("João Miguel Coelho", "phd", None, CXT, near="PhD Students"),
        M("Liwen Sun", "phd", None, CXT, near="PhD Students"),
        M("Shanshan Zhong", "phd", None, CXT, near="PhD Students"),
        M("Xiaochuan Li", "phd", None, CXT, near="PhD Students"),
        M("Yiyang Du", "phd", None, CXT, near="PhD Students"),
        M("Young Jin Ahn", "phd", None, CXT, near="PhD Students"),
        M("Zichun Yu", "phd", None, CXT, near="PhD Students"),
        M("Ethan Chiu", "masters", None, CXT, near="Masters Students"),
        M("Haozhan Tang", "masters", None, CXT, near="Masters Students"),
        M("Jerry Yan", "masters", None, CXT, near="Masters Students"),
        M("Lihan Feng", "masters", None, CXT, near="Masters Students"),
        M("Nihar Atri", "masters", None, CXT, near="Masters Students"),
        M("Sai Gopal", "masters", None, CXT, near="Masters Students"),
        M("Shlok Sanghvi", "masters", None, CXT, near="Masters Students"),
        M("Tianshi Ming", "masters", None, CXT, near="Masters Students"),
        M("Vishal Khot", "masters", None, CXT, near="Masters Students"),
        M("Wentao Wei", "masters", None, CXT, near="Masters Students"),
        M("Yi Lu", "masters", None, CXT, near="Masters Students"),
        M("Yuntian Shen", "masters", None, CXT, near="Masters Students"),
        M("Yuteng Zhang", "masters", None, CXT, near="Masters Students"),
        M("Yuyi Ao", "masters", None, CXT, near="Masters Students"),
        M("Zhanqiu Guo", "masters", None, CXT, near="Masters Students"),
        M("Zhiyun Zhang", "masters", None, CXT, near="Masters Students"),
        M("Aarush Agarwal", "undergraduate", None, CXT, near="Undergraduate Students"),
        M("Tony Li", "undergraduate", None, CXT, near="Undergraduate Students"),
        M("Meng Chu", "visitor", None, CXT, near="Visiting Students"),
        M("Zhihan Zhang", "staff", None, CXT, near="Staff"),
        M("Jiahe Jin", "visitor", None, CXT, near="Alumni", note="alumni entry; group site only exists since 2023 (PI joined LTI 2023)"),
        M("Shi Yu", "visitor", None, CXT, near="Alumni", note="alumni entry; group site only exists since 2023 (PI joined LTI 2023)"),
        M("Tevin Wang", "undergraduate", None, CXT, near="Alumni", note="alumni entry; group site only exists since 2023 (PI joined LTI 2023)"),
    ],
    pubs=[PUB("https://www.cs.cmu.edu/~cx/publications/index.html", mode="auto")],
    notes="Group site cs.cmu.edu/~cxcscmu/team lists 10 PhD, 16 MS, 2 undergrad, 1 visiting, 1 staff and 3 alumni (alumni undated; recorded because the group site dates from 2023 when the PI joined CMU LTI as associate professor; he was at CMU LTI as research faculty earlier, no earlier group page found live). Research page (cxcscmu/research) has 14 recent papers, nearly all matched; personal publications page added. Older Wayback captures of the people pages not read (Wayback backoff at time of run).",
    blocked=[],
)


XG = "https://xulabs.github.io/group/"
D["Min Xu"] = dict(
    lab_site="https://xulabs.github.io/",
    people_page=XG,
    people_pages=[XG],
    members=[
        M("Xingjian Li", "postdoc", None, XG, near="Postdoctoral associates"),
        M("Xiaolong Wu", "postdoc", None, XG, near="Postdoctoral associates"),
        M("Yuanhao Wang", "postdoc", None, XG, near="Postdoctoral associates"),
        M("Seonghui Min", "phd", None, XG, near="PhD students"),
        M("Yang Liu", "postdoc", [2026, 2026], XG, q="Yang Liu (2026, Former Postdoctoral Associate, CMU)"),
        M("Mostofa Rafid Uddin", "phd", [2021, 2026], XG, q="Mostofa Rafid Uddin (2021-2026, Former PhD Student, CPCB, CBD, CMU."),
        M("Xueying Zhan", "postdoc", [2023, 2025], XG, q="Xueying Zhan (2023-2025, Former Postdoctoral Associate, CMU)"),
        M("Zhengzhe Liu", "postdoc", [2024, 2024], XG, q="Zhengzhe Liu (2024, Former Postdoctoral Associate, CMU."),
        M("Jingru Yang", "postdoc", [2024, 2024], XG, q="Jingru Yang (2024, Former Postdoctoral Associate, CMU."),
        M("Ali Dabouei", "postdoc", [2022, 2024], XG, q="Ali Dabouei (2022-2024. Former Postdoctoral Associate, CMU."),
        M("Xiangrui Zeng", "phd", [2017, 2022], XG, q="Xiangrui Zeng (2017-2022. Former PhD Student. CPCB, CBD, CMU."),
        M("Xuqian Tan", "masters", [2020, 2022], XG, q="Xuqian Tan (2020-2022. MSCB, CBD, CMU."),
        M("Gregory Howe", "masters", [2020, 2021], XG, q="Gregory Howe (2020-2021. MSML, MLD, CMU."),
        M("Sima Behpour", "postdoc", [2020, 2021], XG, q="Sima Behpour (2020-2021. Former Postdoctoral Associate, CMU."),
        M("Xiaoyu Zhu", "masters", [2020, 2021], XG, q="Xiaoyu Zhu (2020-2021. MSAII, LTI, CMU."),
        M("Xindi Wu", "masters", [2018, 2022], XG, q="Xindi Wu (2018-2022. MSCV, RI, CMU."),
        M("Yuchen Zeng", "other", [2019, 2020], XG, q="Yuchen Zeng (2019-2020. Intern, CBD, CMU."),
        M("Xuefeng Du", "other", [2018, 2021], XG, q="Xuefeng Du (2018-2021. Intern, CBD, CMU."),
        M("Kai Wen Wang", "undergraduate", [2017, 2019], XG, q="Kai Wen Wang (2017-2019. ECE, CS, CMU."),
        M("Yixiu Zhao", "member", [2017, 2018], XG, q="Yixiu Zhao (2017-2018. CSD, CMU."),
        M("Bo Zhou", "masters", [2017, 2019], XG, q="Bo Zhou (2017-2019. MSCV, RI, CMU."),
        M("Chang Liu", "member", [2017, 2018], XG, q="Chang Liu (2017-2018. ECE, CMU."),
    ],
    pubs=[PUB("https://xulabs.github.io/publication/", mode="auto")],
    notes="Input lab_url (Wharton ~minx) is a different Min Xu; the CMU Computational Biology Min Xu lab site is xulabs.github.io (linked from cbd.cmu.edu/people/xu.html). Group page lists 3 postdocs, 1 PhD student and 19 dated alumni; Muhammad Hamza Sharif and Hussam Osama Azzuni (master's, MBZUAI) skipped as not at CMU. Group page is dated per entry so no Wayback captures were needed; no undated alumni.",
    blocked=[],
)


MMP1 = "https://morphingmatter.org/member?category=Ended"
MMP2 = "https://morphingmatter.org/member?offset=1654027440481&category=Ended"
MMP3 = "https://morphingmatter.org/member?offset=1559328060643&category=Ended"
MMC = "https://morphingmatter.org/people"
D["Lining Yao"] = dict(
    lab_site="https://morphingmatter.org/",
    people_page=MMP1,
    people_pages=[MMC, MMP1, MMP2, MMP3],
    members=[
        M("Stella Shen", "phd", [2021, None], MMC, q="Stella Shen Started September 1, 2021 Computational Design Ph.D.", note="started Sept 2021, before the lab moved to Berkeley"),
        M("Harshika Jain", "other", [2020, None], MMC, q="Harshika Jain Started May 1, 2020 Design CMU Research Affiliate", note="CMU research affiliate listed under Collaborators"),
        M("Qiuyu Lu", "postdoc", [None, 2025], MMP1, q="Qiuyu Lu HCI & ME Postdoc", note="andrew.cmu.edu email on member page"),
        M("Lea Albaugh", "phd", [None, 2024], MMP1, q="Lea Albaugh Human Computer Interaction Ph.D. Student"),
        M("Humphrey Yang", "phd", [None, 2024], MMP1, q="Humphrey Yang Human Computer Interaction Ph.D. Student"),
        M("Ke Zhong", "phd", [None, 2024], MMP1, q="Ke Zhong Material Science and Engineering Ph.D. Student", note="CMU MSE PhD per member page"),
        M("Tucker Rae-Grant", "staff", [None, 2023], MMP1, q="Tucker Rae-Grant Manufacturing and Design Research Associate", note="HCII CMU research associate"),
        M("Yibo Fu", "staff", [None, 2023], MMP1, q="Yibo Fu Design and Engineering Research Associate"),
        M("Di Wu", "masters", [None, 2023], MMP1, q="Di Wu Architecture and HCI Master", note="CMU SoA master per member page"),
        M("Melinda Chen", "undergraduate", [None, 2023], MMP1, q="Melinda Chen Materials Science and Engineering Undergrad"),
        M("Haiqing Xu", "visitor", [None, 2023], MMP1, q="Haiqing Xu Human-Computer Interaction Tsinghua University", note="visiting student from Tsinghua"),
        M("Sunniva Liu", "undergraduate", [None, 2023], MMP1, q="Sunniva Liu Psychology and HCI Undergrad"),
        M("Mengtian Gan", "masters", [None, 2023], MMP1, q="Mengtian Gan Materials Science and Engineering Master"),
        M("Tate Johnson", "undergraduate", [None, 2023], MMP1, q="Tate Johnson Industrial Design Undergrad"),
        M("Yuran Ding", "undergraduate", [None, 2023], MMP1, q="Yuran Ding Psychology and HCI Undergrad"),
        M("Malika Khurana", "masters", [None, 2022], MMP1, q="Malika Khurana Computational Design Master"),
        M("Reece Whatmore", "undergraduate", [None, 2022], MMP2, q="Reece Whatmore Materials Science and Engineering Undergrad"),
        M("Cathy Fang", "undergraduate", [None, 2021], MMP2, q="Cathy Fang Mechanical Engineering ‘20 Undergrad"),
        M("Danli Luo", "staff", [None, 2021], MMP2, q="Danli Luo Material Science and Engineering Research Associate"),
        M("Maria Vlachostergiou", "masters", [None, 2021], MMP2, q="Maria Vlachostergiou Computational Design Master"),
        M("Michael Vinciguerra", "phd", [None, 2020], MMP2, q="Michael Vinciguerra Mechanical Engineering Ph.D. Student"),
        M("Guanyun Wang", "postdoc", [None, 2020], MMP2, q="Guanyun Wang Design and Manufacturing Postdoc"),
        M("Olaitan Adisa", "masters", [None, 2020], MMP2, q="Olaitan Adisa Information Tech Master"),
        M("Matthew McGehee", "undergraduate", [None, 2020], MMP2, q="Matthew McGehee Design Undergrad"),
        M("Yi-Chin Lee", "masters", [None, 2020], MMP2, q="Yi-Chin Lee Computational Design Master"),
        M("Rachel Sneeringer", "member", [None, 2020], MMP2, q="Rachel Sneeringer Mechanical Engineering"),
        M("Sijia Wang", "masters", [None, 2020], MMP2, q="Sijia Wang Integrated Design Master"),
        M("Koya Narumi", "phd", [None, 2019], MMP2, q="Koya Narumi Electrical Engineering PhD", note="listed PhD; later assistant professor at U of Tokyo (likely visiting)"),
        M("Ye Tao", "postdoc", [None, 2019], MMP2, q="Ye Tao Design and Manufacturing Postdoc"),
        M("Jack Forman", "undergraduate", [None, 2019], MMP2, q="Jack Forman Material Science and Engineering Undergrad"),
        M("Jasio Santillan", "masters", [None, 2019], MMP2, q="Jasio Santillan Material Science and Engineering Master"),
        M("Jenny Hu", "undergraduate", [None, 2019], MMP2, q="Jenny Hu Design Undergrad"),
        M("Taylor Tabb", "masters", [None, 2019], MMP2, q="Taylor Tabb Mechanical Engineering Master"),
        M("Zeyu Yan", "masters", [None, 2019], MMP2, q="Zeyu Yan Mechanical Engineering Master"),
        M("Kuanren Qian", "member", [None, 2019], MMP2, q="Kuanren Qian Mechanical Engineering"),
        M("Fang Qin", "member", [None, 2019], MMP2, q="Fang Qin Electrical Engineering"),
        M("Mohan Yeh", "masters", [None, 2019], MMP3, q="Mohan Yeh Costume Design Master"),
        M("Ozguc Bertug Capunaman", "masters", [None, 2019], MMP3, q="Ozguc Bertug Capunaman Computational Design Master"),
        M("Adrian Galvin", "masters", [None, 2019], MMP3, q="Adrian Galvin Design Master"),
        M("Jianzhe Gu", "phd", None, MMP3, q="Jianzhe Gu Human Computer Interaction Ph.D. Student", note="page shows ended 9/1/18; years left unset"),
        M("Jianxun Cui", "other", [None, 2018], MMP3, q="Jianxun Cui Mechanical Engineering Research Affiliate", note="research affiliate"),
        M("Tingyu Cheng", "other", [None, 2018], MMP3, q="Tingyu Cheng Civil Engineering Research Affiliate", note="research affiliate"),
        M("Youngwook Do", "masters", [None, 2018], MMP3, q="Youngwook Do Electrical Engineering Master"),
        M("Catherine Mondoa", "undergraduate", [None, 2018], MMP3, q="Catherine Mondoa Material Science and Engineering Undergrad"),
        M("Ty Van de Zande", "undergraduate", [None, 2018], MMP3, q="Ty Van de Zande Design Undergrad"),
        M("Melodie Yashar", "masters", [None, 2018], MMP3, q="Melodie Yashar MHCI Master"),
        M("Byoungkwon An", "masters", [None, 2017], MMP3, q="Byoungkwon An CS Master"),
        M("Hieu Pham", "undergraduate", [None, 2017], MMP3, q="Hieu Pham Design Undergrad"),
    ],
    pubs=[PUB("https://morphingmatter.org/publications", mode="anchor")],
    notes="Lining Yao moved to UC Berkeley; morphingmatter.org (Squarespace, Berkeley branded) gives per-person Started/Ended dates. Recorded only members whose dates place them in the CMU period (ended 2023 or earlier, plus the CMU-affiliated PhD students/postdoc Lea Albaugh, Humphrey Yang, Ke Zhong, Qiuyu Lu who ended 2024-25, and Stella Shen/Harshika Jain who started 2020-21). Skipped as Berkeley-era: current members who started 2024+ (Haitao Qing, Woorim Choi, Atulit Dasaratha, Ming, Semina Yi, Tianyu Yu, Mako Miyatake, Marco Freschi, Yunosuke Nakamura, Christy Huang, Sean Barbieri, Jeremy Chen), collaborators Dinesh Patel, Shuhong Wang (2023, uncertain), Alisha Collins, and Berkeley visitors/postdocs (David Jourdan, Hajun Lee, Anna Matsumoto, Yuxuan Sun, Yuecheng Peng, Yue Yang). Old CMU-hosted site morphingmatter.cs.cmu.edu not read (see final report).",
    blocked=[],
)


BP = "http://users.ece.cmu.edu/~byronyu/people.html"
D["Byron Yu"] = dict(
    lab_site="http://users.ece.cmu.edu/~byronyu/index.html",
    people_page=BP,
    people_pages=[BP],
    members=[
        M("Noga Larry", "postdoc", None, BP, near="Postdocs"),
        M("Asma Motiwala", "postdoc", None, BP, near="Postdocs"),
        M("Joana Soldado Magraner", "postdoc", None, BP, near="Postdocs"),
        M("Noah Freedman", "phd", None, BP, near="PhD Students"),
        M("Chris Ki", "phd", None, BP, near="PhD Students"),
        M("Megan McDonnell", "phd", None, BP, near="PhD Students"),
        M("Yuki Minai", "phd", None, BP, near="PhD Students"),
        M("Will Noll", "phd", None, BP, near="PhD Students"),
        M("Felix Pei", "phd", None, BP, near="PhD Students"),
        M("Evren Gokcen", "postdoc", [2023, 2025], BP, q="Evren Gokcen (2023-2025; co-advised"),
        M("Elizabeth Spencer", "postdoc", [2021, 2023], BP, q="Elizabeth Spencer (2021-2023; co-advised"),
        M("Emilio Salazar-Gatzimas", "postdoc", [2019, 2022], BP, q="Emilio Salazar-Gatzimas (2019-2022; co-advised"),
        M("Joao Semedo", "postdoc", [2018, 2020], BP, q="Joao Semedo (2018-2020; co-advised"),
        M("Alan Degenhart", "postdoc", [2014, 2020], BP, q="Alan Degenhart (2014-2020; co-advised"),
        M("William Bishop", "postdoc", [2015, 2018], BP, q="William Bishop (2015-2018; next position"),
        M("Adam Snyder", "postdoc", [2015, 2018], BP, q="Adam Snyder (2015-2018, co-advised"),
        M("Matthew Golub", "postdoc", [2015, 2017], BP, q="Matthew Golub (2015-2017, co-advised"),
        M("Shenghao Wu", "phd", [2018, 2023], BP, q="Shenghao Wu (CMU PNC & ML, 2018-2023"),
        M("Tze Hui Koh", "phd", [2017, 2023], BP, q="Tze Hui Koh (CMU BME, 2017-2023"),
        M("Hillary Wehry", "phd", [2017, 2023], BP, q="Hillary Wehry (CMU PNC, 2017-2023"),
        M("Darby Losey", "phd", [2017, 2023], BP, q="Darby Losey (CMU PNC & ML, 2017-2023"),
        M("Evren Gokcen", "phd", [2017, 2023], BP, q="Evren Gokcen (CMU ECE, 2017-2023"),
        M("Akash Umakantha", "phd", [2015, 2021], BP, q="Akash Umakantha (CMU PNC & ML, 2015-2021"),
        M("Jay Hennig", "phd", [2015, 2021], BP, q="Jay Hennig (CMU PNC & ML, 2015-2021"),
        M("Ryan Williamson", "phd", [2015, 2020], BP, q="Ryan Williamson (CMU PNC & ML, 2015-2020"),
        M("Joao Semedo", "phd", [2012, 2018], BP, q="Joao Semedo (CMU ECE, 2012-2018"),
        M("Benjamin Cowley", "phd", [2012, 2018], BP, q="Benjamin Cowley (CMU ML, 2012-2018"),
        M("Suhas Ganesh", "masters", [2018, 2019], BP, q="Suhas Ganesh (CMU ECE, 2018-2019"),
        M("Rudina Morina", "masters", [2016, 2017], BP, q="Rudina Morina (CMU ECE, 2016-2017"),
        M("Ranjani Srinivasan", "masters", [2015, 2017], BP, q="Ranjani Srinivasan (CMU BME, 2015-2017"),
        M("Zoe Wu", "undergraduate", [2025, 2025], BP, q="Zoe Wu (uPNC summer student, 2025)"),
        M("Jonathan Gould", "undergraduate", [2021, 2021], BP, q="Jonathan Gould (uPNC summer student, 2021)"),
        M("Alix MacKlin", "undergraduate", [2016, 2016], BP, q="Alix MacKlin (uPNC summer student, 2016)"),
        M("Sean Bittner", "undergraduate", [2015, 2016], BP, q="Sean Bittner (ECE undergraduate, uPNC year-long fellowship, 2015-2016"),
    ],
    pubs=[PUB("http://users.ece.cmu.edu/~byronyu/pubs.shtml", mode="auto")],
    notes="Lab people page gives current postdocs/PhD students and a fully dated alumni list (postdocs, PhD, masters, undergraduates); only entries overlapping 2016-2026 recorded. Skipped as ended before 2016: William Bishop PhD (2011-2015), Matthew Golub PhD (2010-2015), Patrick Sadtler, Karthik Lakshmanan, Peter Lund, Yuanning Li, and undergraduates 2010-2014. Collaborators section lists other labs' people (Pitt, Einstein, etc.) and was not recorded. Page footer is 2013 but the content is current through 2025.",
    blocked=[],
)

YG = "https://yunwilliamyu.net/content/pages/research-group.html"
YC = "https://www.cmu.edu/cbd/people/yu.html"
D["Yun William Yu"] = dict(
    lab_site="https://yunwilliamyu.net/",
    people_page=YG,
    people_pages=[YG, YC],
    members=[
        M("Molly Borowiak", "phd", None, YG, near="Current group members"),
        M("Aidan Zhang", "phd", None, YG, near="Current group members"),
        M("Spencer Gibson", "masters", None, YG, near="Current group members"),
        M("Navid Bin Hasan", "phd", None, YC, near="Lab Members"),
        M("Grace Oualline", "undergraduate", None, YG, q="Grace Oualline CMU Double Major in Biology and Computational Biology", note="alumni entry, CMU degree (PI moved to CMU from Toronto)"),
        M("Xiaolei (Brian) Zhang", "masters", None, YG, q="Xiaolei (Brian) Zhang CMU M.S. in Quantitative Biology and Bioinformatics", note="alumni entry, CMU degree"),
    ],
    pubs=[],
    notes="PI moved to CMU from Univ. of Toronto Scarborough; research-group page lists 3 current members, CBD profile adds Navid Bin Hasan, alumni list mixes Toronto students (about 10 skipped: Jim Shaw, Ben Connors, Yeonjoon Choi, Kiran Deol, Andrew Zheng, Siyue Wang, Xinqi Shen, Luke Staniscia, Ziye Tao, Yeji Wi, Abbas Hammoud, all undated and Toronto-degree) with two CMU alumni, which are recorded. Mahmudur Rahman Hera (held) is a Toronto-era person not on page. No publications page on the site (only Google Scholar link, off limits); no Wayback captures read.",
    blocked=[],
)

RW = "https://www.ri.cmu.edu/ri-people/wenzhen-yuan/"
D["Wenzhen Yuan"] = dict(
    lab_site="http://robotouch.ri.cmu.edu/yuanwz/",
    people_page=RW,
    people_pages=[RW],
    members=[
        M("Ruihan Gao", "phd", None, RW, near="current phd students"),
        M("Joe Huang", "phd", None, RW, near="current phd students", note="likely Hung-Jui (Joe) Huang, held under that name"),
        M("Yufan Zhang", "phd", None, RW, near="current phd students"),
        M("Helen Jiang", "phd", None, RW, near="past phd students"),
        M("Achu Wilson", "masters", None, RW, near="current masters students"),
        M("Arpit Agarwal", "phd", None, RW, near="past phd students"),
        M("Yichen Li", "masters", None, RW, near="past masters students"),
        M("Zilin Si", "masters", None, RW, near="past masters students"),
    ],
    pubs=[],
    notes="PI moved to UIUC; the RI profile (ri.cmu.edu/ri-people/wenzhen-yuan) still lists her CMU students/affiliates (undated). The old lab site robotouch.ri.cmu.edu no longer resolves. RI profile lists 27 publications as links only (no parseable titles/years), so no pubs page added.",
    blocked=[],
)

AZ = "https://azanette.com/"
AZC = "Current PhD Students and Close Collaborators"
AZF = "Former Students and Collaborators"
D["Andrea Zanette"] = dict(
    lab_site="https://azanette.com/",
    people_page=AZ,
    people_pages=[AZ],
    members=[
        M("Yuda Song", "phd", None, AZ, near=AZC, note="primary advisors Aarti Singh and J. Andrew Bagnell; close collaborator"),
        M("Fahim Tajwar", "phd", None, AZ, near=AZC, note="primary advisors Salakhutdinov and Schneider; close collaborator"),
        M("Tong Yang", "phd", None, AZ, near=AZC, note="primary advisor Yuejie Chi; close collaborator"),
        M("Daman Arora", "phd", None, AZ, near=AZC),
        M("Zhaoyi Zhou", "phd", None, AZ, near=AZC),
        M("Andy Zhou", "phd", None, AZ, near=AZC, note="on leave"),
        M("Guanning Zeng", "phd", None, AZ, near=AZC),
        M("Gokul Swamy", "phd", None, AZ, near=AZF, note="CMU Robotics PhD, collaborator"),
        M("Anmol Agarwal", "masters", None, AZ, near=AZF),
        M("Hanshi Sun", "masters", None, AZ, near=AZF),
    ],
    pubs=[],
    notes="PI joined CMU ECE in Fall 2024 (postdoc at Berkeley before). Home page lists current students/close collaborators and former students; interns (Haolun Li, Yueer Zhou, Hyunho Kook, Sheikh Shafayat, Huitao Yang, Jiahao Shi; the page says interns are remote) and non-CMU collaborators (Ming Yin Princeton postdoc, Ruiqi Zhang and Yifei Zhou Berkeley PhDs) skipped. Papers are listed inline on the home page with arXiv links only; pubs preview parsed award lines, not titles, so no pubs page added.",
    blocked=[],
)

HZ = "https://www.cs.cmu.edu/~hzhang/"
D["Hui Zhang"] = dict(
    lab_site="https://www.cs.cmu.edu/~hzhang/",
    people_page=HZ,
    people_pages=[HZ],
    members=[
        M("Junchen Jiang", "phd", None, HZ, near="Current Students"),
    ],
    pubs=[],
    notes="Homepage is a static page (page content dates from about 2012-2015): lists Junchen Jiang as the only current student and about 19 undated former students/postdocs (Ion Stoica, Eugene Ng, Yanghua Chu, Vyas Sekar, etc.), all skipped under the undated-alumni rule. recentpublication.html parses to 19 undated, pre-2016 papers (in_window=0), so no pubs page added. Wayback captures not read (see final report).",
    blocked=[],
)

ZL = "https://www.ri.cmu.edu/robotics-groups/zhang-lab/"
ZF = "https://www.ri.cmu.edu/ri-faculty/ji-zhang/"
D["Ji Zhang"] = dict(
    lab_site="https://frc.ri.cmu.edu/~zhangji/",
    people_page=ZL,
    people_pages=[ZL, ZF],
    members=[
        M("Chao Cao", "phd", None, ZF, near="current phd students"),
        M("Zhixuan Liu", "phd", None, ZF, near="current phd students"),
        M("Chih-Hao Chou", "masters", None, ZF, near="current masters students"),
        M("Shreedhar Jangam", "masters", None, ZF, near="current masters students"),
        M("Muqing Jiang", "masters", None, ZF, near="current masters students"),
        M("Steven Liu", "masters", None, ZF, near="current masters students"),
        M("Zihan Liu", "masters", None, ZF, near="current masters students"),
        M("Hang Xu", "masters", None, ZF, near="current masters students"),
        M("Yuxin Cai", "staff", None, ZL, near="current staff", note="listed under current affiliates on the RI faculty profile"),
        M("Yifan Lin", "staff", None, ZL, near="current staff", note="listed under current affiliates on the RI faculty profile"),
        M("Pranav Saxena", "staff", None, ZL, near="current staff", note="listed under current affiliates on the RI faculty profile"),
        M("Jingfan Tang", "staff", None, ZL, near="current staff", note="listed under current affiliates on the RI faculty profile"),
        M("Guofei Chen", "masters", None, ZF, near="past masters students"),
        M("Pujith Kachana", "masters", None, ZF, near="past masters students"),
        M("Terry Li", "masters", None, ZF, near="past masters students"),
        M("Xinjie Yao", "masters", None, ZF, near="past masters students"),
        M("Nader Zantout", "masters", None, ZF, near="past masters students"),
    ],
    pubs=[],
    notes="No standalone lab site: RI Zhang Lab page (members) and RI faculty profile (students/affiliates, current and past masters), plus the PI's FRC homepage (frc.ri.cmu.edu/~zhangji) which has only selected publications and no student list. Haokun Zhu (held) is not on any page. Selected-publications parse gave award lines as titles, not usable; only one real paper (JFR 2018 Laser-visual-inertial odometry) was missing, so no pubs page added.",
    blocked=[],
)

# ---- Yiming Yang ----
D["Yiming Yang"] = dict(
    lab_site="https://yimingyang2026.github.io/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[PUB("https://www.cs.cmu.edu/~yiming/publications.html", mode="auto")],
    notes="PI homepage (cs.cmu.edu/~yiming now redirects to yimingyang2026.github.io) lists research areas and teaching only; no student/group "
          "section. A Wayback 2020 capture of the old homepage has the same layout (no students), and the CSD directory profile lists "
          "department and research area only, so no members recorded. Selected-publications page (2020s, class-title parse, ~147 entries, "
          "11 missing from lab papers) added in auto mode.",
    blocked=[],
)
