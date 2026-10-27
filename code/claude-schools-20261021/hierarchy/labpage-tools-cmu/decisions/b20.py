from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Jignesh Patel
JP = "https://csd.cmu.edu/people/faculty/jignesh-patel"
D["Jignesh Patel"] = dict(
    lab_site="https://jigneshpatel.org/",
    people_page=JP,
    people_pages=[JP],
    members=[
        M("Drew Ripberger", "phd", None, JP, near="Advisees"),
        M("Sam Arch", "phd", None, JP, near="Advisees"),
    ],
    pubs=[],
    notes="Personal site jigneshpatel.org lists only research summary and selected publications (no group/people page, no full list parsed; selected list has no year-wise page). CSD profile lists two advisees (Drew Ripberger, Sam Arch). Patel joined CMU in 2023 from Wisconsin so Wisconsin students are excluded. Pavlo's page names Yuchen Liang as co-advised with Patel (recorded under Pavlo). No Wayback used (nothing to add; no alumni list exists).",
    blocked=[],
)

# ---------------------------------------------------------------- Deepak Pathak
DP = "https://www.cs.cmu.edu/~dpathak/"
DP22 = WB + "20220412185536id_/https://www.cs.cmu.edu/~dpathak/"
DP24 = WB + "20240119064553id_/https://www.cs.cmu.edu/~dpathak/"
D["Deepak Pathak"] = dict(
    lab_site=DP,
    people_page=DP,
    people_pages=[DP, DP22, DP24],
    members=[
        M("Ananye Agarwal", "phd", None, DP, near="PhD Students"),
        M("Lili Chen", "phd", None, DP, near="PhD Students"),
        M("Alex Li", "phd", None, DP, near="PhD Students"),
        M("Mihir Prabhudesai", "phd", None, DP, near="PhD Students", note="with Katerina Fragkiadaki"),
        M("Kenny Shaw", "phd", None, DP, near="PhD Students"),
        M("Andrew Wang", "phd", None, DP, near="PhD Students", note="with Abhinav Gupta"),
        M("Jianren Wang", "phd", None, DP, near="PhD Students", note="with Abhinav Gupta"),
        M("Jason Liu", "phd", None, DP, near="PhD Students", note="with Ruslan Salakhutdinov"),
        M("Kexin Shi", "phd", None, DP, near="PhD Students"),
        M("Tal Daniel", "postdoc", None, DP, near="Postdoc"),
        M("Jim Yang", "masters", None, DP, near="MS Students"),
        M("Hengkai Pan", "masters", None, DP, near="MS Students"),
        M("Tony Tao", "masters", None, DP, near="MS Students"),
        M("Sandeep Routray", "masters", None, DP, near="MS Students"),
        M("Yulong Li", "masters", None, DP, near="Former Students and PostDocs"),
        M("Haoyu Xiong", "masters", None, DP, near="Former Students and PostDocs"),
        M("Unnat Jain", "postdoc", None, DP, near="Former Students and PostDocs"),
        M("Xingyu Liu", "postdoc", None, DP, near="Former Students and PostDocs"),
        M("Mohan Kumar Srirama", "masters", None, DP, near="Former Students and PostDocs"),
        M("Russell Mendonca", "phd", None, DP, near="Former Students and PostDocs"),
        M("Jayesh Singla", "masters", None, DP, near="Former Students and PostDocs"),
        M("Shikhar Bahl", "phd", None, DP, near="Former Students and PostDocs"),
        M("Alexandre Kirchmeyer", "masters", None, DP, near="Former Students and PostDocs"),
        M("Shagun Uppal", "masters", None, DP, near="Former Students and PostDocs"),
        M("Shivam Duggal", "masters", None, DP, near="Former Students and PostDocs"),
        M("Ellis Brown", "masters", None, DP, near="Former Students and PostDocs"),
        M("Xuxin Cheng", "masters", None, DP, near="Former Students and PostDocs"),
        M("Kevin Gmelin", "masters", None, DP, near="Former Students and PostDocs"),
        M("Aditya Kannan", "undergraduate", None, DP, near="Former Students and PostDocs"),
        M("Zipeng Fu", "masters", None, DP, near="Former Students and PostDocs"),
        M("Wenlong Huang", "undergraduate", None, DP, near="Former Students and PostDocs"),
        M("Hongyu Wen", "undergraduate", None, DP, near="Former Students and PostDocs", note="UGrad intern"),
        M("Boyuan Chen", "undergraduate", None, DP, near="Former Students and PostDocs"),
        M("Aravind Sivakumar", "masters", None, DP, near="Former Students and PostDocs"),
        M("Ankit Ramchandani", "masters", None, DP, near="Former Students and PostDocs"),
        M("Pratyusha Sharma", "undergraduate", None, DP, near="Former Students and PostDocs", note="UGrad intern"),
        M("Dian Chen", "undergraduate", None, DP, near="Former Students and PostDocs"),
    ],
    pubs=[PUB(DP, mode="auto")],
    notes="Group on PI homepage: current PhD/postdoc/MS lists plus 'Former Students and PostDocs'. Checked Wayback 2022 and 2024 captures (2020 capture predates the group, no list); every person on them also appears on the live page. Murtaza Dalal (PhD collaborator, now Tesla) and the 'Affiliates and Collaborators' (Hafner, Hu, Kumar, Mordatch, Rybkin) are external and skipped. Homepage publication list is year-less for older entries and includes awards/talks as anchors; auto mode gives 96 in-window entries.",
    blocked=["https://pathak.io/ (connection error)"],
)

# ---------------------------------------------------------------- Andrew Pavlo
AP = "https://www.cs.cmu.edu/~pavlo/"
AP19 = WB + "20190102093527id_/http://www.cs.cmu.edu/~pavlo/"
AP21 = WB + "20210126175801id_/https://www.cs.cmu.edu/~pavlo/"
D["Andrew Pavlo"] = dict(
    lab_site=AP,
    people_page=AP,
    people_pages=[AP, AP19, AP21],
    members=[
        M("Sam Arch", "phd", None, AP, near="Current:", note="with Todd Mowry"),
        M("Yuchen Liang", "phd", None, AP, near="Current:", note="with Jignesh Patel"),
        M("Dana Van Aken", "phd", None, AP19, near="Students:", note="with Geoff Gordon; current in 2019 and 2021 captures"),
        M("Huanchen Zhang", "phd", None, AP19, near="Students:", note="with Dave Andersen and Michael Kaminsky"),
        M("Lin Ma", "phd", None, AP19, near="Students:"),
        M("Prashanth Menon", "phd", None, AP19, near="Students:", note="with Todd Mowry"),
        M("Joy Arulraj", "phd", None, AP19, near="Graduated:", note="graduated before the 2019 capture"),
        M("Matt Butrovich", "phd", None, AP21, near="Current:"),
        M("Wan Shen Lim", "phd", None, AP21, near="Current:"),
        M("William Zhang", "phd", None, AP, near="Graduated:", note="listed after Butrovich and Lim who were current in 2021, so a later student"),
    ],
    pubs=[PUB(AP + "publications.html", mode="anchor")],
    notes="Students list on homepage; used live plus Wayback 2019 and 2021 captures (2017 capture refused by wayback-backoff). Xiangyao Yu (with Srini Devadas, MIT) and Lianghong Xu (with Greg Ganger, pre-2016) skipped as other labs / out of window. Pavlo is currently at ClickHouse Labs. Publications page parsed in anchor mode (59 entries, 44 in window).",
    blocked=[],
)

# ---------------------------------------------------------------- Richard Peng
RP = "https://www.cs.cmu.edu/~yangp/"
RPC = "https://csd.cmu.edu/people/faculty/richard-peng"
D["Richard Peng"] = dict(
    lab_site=RP,
    people_page=RP,
    people_pages=[RP, RPC],
    members=[
        M("Junzhao Yang", "phd", [2024, None], RP, q="Junzhao Yang, Ph.D. Fall 2024 - present @ CMU."),
        M("Alicia Stepin", "phd", [2024, None], RP, q="Alicia Stepin, Ph.D. Fall 2024 - present @ CMU."),
        M("Hoai-An Nguyen", "phd", None, RPC, near="Advisees"),
    ],
    pubs=[],
    notes="Homepage lists current CMU PhD students (Junzhao Yang, Alicia Stepin) and a Former list of six students whose dates are all at Georgia Tech/Waterloo (Jingbang Chen, Li Chen, Yu Gao, Saurabh Sawlani, David Durfee, Peng Zhang), skipped because Peng joined CMU only in 2023. Hoai-An Nguyen is a third advisee on the CSD profile. No publications page (DBLP link only, off limits). No Wayback needed.",
    blocked=[],
)

# ---------------------------------------------------------------- Adam Perer
DIG = "https://dig.cmu.edu/team"
D["Adam Perer"] = dict(
    lab_site="https://dig.cmu.edu/",
    people_page=DIG,
    people_pages=[DIG],
    members=[
        M("Arpit Mathur", "phd", [2026, None], DIG, q="Arpit Mathur (PhD Student)"),
        M("Eric Mason", "phd", [2026, None], DIG, q="Eric Mason (PhD Student)"),
        M("Hwei-Shin Harriman", "phd", [2026, None], DIG, q="Hwei-Shin Harriman (PhD Student)"),
        M("Péter Ferenc Gyarmati", "phd", [2026, None], DIG, q="Péter Ferenc Gyarmati (Affiliated PhD Student)"),
        M("Esther Suh", "masters", [2026, None], DIG, q="Esther Suh (Masters Student)"),
        M("Maggie Chen", "undergraduate", [2026, None], DIG, q="Maggie Chen (Undergraduate Student)"),
        M("Udhirna Krishnamurthy", "undergraduate", [2026, None], DIG, q="Udhirna Krishnamurthy (Undergraduate Student)"),
        M("Yuvvan Talreja", "undergraduate", [2026, None], DIG, q="Yuvvan Talreja (Undergraduate Student)"),
        M("Ziyong Ma", "undergraduate", [2026, None], DIG, q="Ziyong Ma (Undergraduate Student)"),
        M("Scott Davidoff", "visitor", [2026, None], DIG, q="Scott Davidoff (Visiting Researcher)"),
        M("Seokweon Jung", "visitor", [2026, None], DIG, q="Seokweon Jung (Visiting Researcher)"),
        M("Katelyn Morrison", "phd", [None, 2026], DIG, near="PhD Alumni"),
        M("Frank Elavsky", "phd", [None, 2026], DIG, near="PhD Alumni"),
        M("Will Epperson", "phd", [None, 2025], DIG, near="PhD Alumni"),
        M("Venkat Sivaraman", "phd", [None, 2025], DIG, near="PhD Alumni"),
        M("Ángel Alexander Cabrera", "phd", [None, 2024], DIG, near="PhD Alumni"),
        M("Pranav Manjunath", "member", [None, 2026], DIG, q="Pranav Manjunath (2026)"),
        M("Kyungjin (James) Kim", "member", [None, 2026], DIG, q="Kyungjin (James) Kim (2026)"),
        M("Daesung Kim", "member", [None, 2026], DIG, q="Daesung Kim (2026)"),
        M("Youli Chang", "member", [None, 2025], DIG, q="Youli Chang (2025)"),
        M("Unn Seo (Grace) Park", "member", [None, 2025], DIG, q="Unn Seo (Grace) Park (2025)"),
        M("Rui Sheng", "member", [None, 2025], DIG, q="Rui Sheng (2025)"),
        M("Rohit Chennamsetti", "member", [None, 2025], DIG, q="Rohit Chennamsetti (2025)"),
        M("Jessica Tong", "member", [None, 2025], DIG, q="Jessica Tong (2025)"),
        M("Eli Slothower", "member", [None, 2025], DIG, q="Eli Slothower (2025)"),
        M("Aidan Bradshaw", "member", [None, 2025], DIG, q="Aidan Bradshaw (2025)"),
        M("Zexuan (Zx) Li", "member", [None, 2024], DIG, q="Zexuan (Zx) Li (2024)"),
        M("Yuxiang Huang", "member", [None, 2024], DIG, q="Yuxiang Huang (2024)"),
        M("Yanwei Huang", "member", [None, 2024], DIG, q="Yanwei Huang (2024)"),
        M("Yanna Lin", "member", [None, 2024], DIG, q="Yanna Lin (2024)"),
        M("Violet Turri", "member", [None, 2024], DIG, q="Violet Turri (2024)"),
        M("Tom Wartmann", "member", [None, 2024], DIG, q="Tom Wartmann (2024)"),
        M("Qianou (Christina) Ma", "member", [None, 2024], DIG, q="Qianou (Christina) Ma (2024)"),
        M("Maggie Cai", "member", [None, 2024], DIG, q="Maggie Cai (2024)"),
        M("Katie Robinson", "member", [None, 2024], DIG, q="Katie Robinson (2024)"),
        M("Jordan Wheeler", "member", [None, 2024], DIG, q="Jordan Wheeler (2024)"),
        M("Erica Fu", "member", [None, 2024], DIG, q="Erica Fu (2024)"),
        M("Eli Kranjec", "member", [None, 2024], DIG, q="Eli Kranjec (2024)"),
        M("Donald Bertucci", "member", [None, 2024], DIG, q="Donald Bertucci (2024)"),
        M("Chloe Yan", "member", [None, 2024], DIG, q="Chloe Yan (2024)"),
        M("Zaynab A.", "member", [None, 2023], DIG, q="Zaynab A. (2023)"),
        M("Yejun (Ariel) Kwak", "member", [None, 2023], DIG, q="Yejun (Ariel) Kwak (2023)"),
        M("Vaishnavi Gorantla", "member", [None, 2023], DIG, q="Vaishnavi Gorantla (2023)"),
        M("Tianqi (Andy) Wu", "member", [None, 2023], DIG, q="Tianqi (Andy) Wu (2023)"),
        M("Syeda Sheherbano Rizvi", "member", [None, 2023], DIG, q="Syeda Sheherbano Rizvi (2023)"),
        M("Rohit Chougule", "member", [None, 2023], DIG, q="Rohit Chougule (2023)"),
        M("Michelle Feng", "member", [None, 2023], DIG, q="Michelle Feng (2023)"),
        M("Laura Wei", "member", [None, 2023], DIG, q="Laura Wei (2023)"),
        M("Lan Lyu", "member", [None, 2023], DIG, q="Lan Lyu (2023)"),
        M("Karim Benharrak", "member", [None, 2023], DIG, q="Karim Benharrak (2023)"),
        M("Crystal Li", "member", [None, 2023], DIG, q="Crystal Li (2023)"),
        M("Bruce Li", "member", [None, 2023], DIG, q="Bruce Li (2023)"),
        M("Yuzhe (Bryan) Lu", "member", [None, 2022], DIG, q="Yuzhe (Bryan) Lu (2022)"),
        M("Rithika Narayan", "member", [None, 2022], DIG, q="Rithika Narayan (2022)"),
        M("Mayank Jain", "member", [None, 2022], DIG, q="Mayank Jain (2022)"),
        M("Lukas Hermann", "member", [None, 2022], DIG, q="Lukas Hermann (2022)"),
        M("Kazi Jawad", "member", [None, 2022], DIG, q="Kazi Jawad (2022)"),
        M("Kan Sun", "member", [None, 2022], DIG, q="Kan Sun (2022)"),
        M("Francisco Maria Calisto", "member", [None, 2022], DIG, q="Francisco Maria Calisto (2022)"),
        M("Donghoon Shin", "member", [None, 2022], DIG, q="Donghoon Shin (2022)"),
        M("Carol (Xinyi) Zheng", "member", [None, 2022], DIG, q="Carol (Xinyi) Zheng (2022)"),
        M("Amanda Li", "member", [None, 2022], DIG, q="Amanda Li (2022)"),
        M("Ziyang Guo", "member", [None, 2021], DIG, q="Ziyang Guo (2021)"),
        M("Zhendong (Mike) Yuan", "member", [None, 2021], DIG, q="Zhendong (Mike) Yuan (2021)"),
        M("Yiwei Wu", "member", [None, 2021], DIG, q="Yiwei Wu (2021)"),
        M("Sachin Grover", "member", [None, 2021], DIG, q="Sachin Grover (2021)"),
        M("Nathan Jen", "member", [None, 2021], DIG, q="Nathan Jen (2021)"),
        M("Monica Chang", "member", [None, 2021], DIG, q="Monica Chang (2021)"),
        M("Marius Hogräfer", "member", [None, 2021], DIG, q="Marius Hogräfer (2021)"),
        M("Leijie Wang", "member", [None, 2021], DIG, q="Leijie Wang (2021)"),
        M("Zhirou (Jenny) Xin", "member", [None, 2021], DIG, q="Zhirou (Jenny) Xin (2021)"),
        M("Canzhou Qu", "member", [None, 2021], DIG, q="Canzhou Qu (2021)"),
        M("Andy Wilbourn", "member", [None, 2021], DIG, q="Andy Wilbourn (2021)"),
        M("Aditi Dhabalia", "member", [None, 2021], DIG, q="Aditi Dhabalia (2021)"),
        M("Abraham Druck", "member", [None, 2021], DIG, q="Abraham Druck (2021)"),
        M("Sujun Cheng", "member", [None, 2020], DIG, q="Sujun Cheng (2020)"),
        M("Shreya Manjunath", "member", [None, 2020], DIG, q="Shreya Manjunath (2020)"),
        M("Mia Manavalan", "member", [None, 2020], DIG, q="Mia Manavalan (2020)"),
        M("Jiachen (Lilian) Gong", "member", [None, 2020], DIG, q="Jiachen (Lilian) Gong (2020)"),
        M("Leila Huang", "member", [None, 2020], DIG, q="Leila Huang (2020)"),
        M("Laura Beth Fulton", "member", [None, 2020], DIG, q="Laura Beth Fulton (2020)"),
        M("Justine Cho", "member", [None, 2020], DIG, q="Justine Cho (2020)"),
        M("Ja Young Lee", "member", [None, 2019], DIG, q="Ja Young Lee (2019)"),
        M("Qian Wang", "member", [None, 2019], DIG, q="Qian Wang (2019)"),
        M("Olivia Zhang", "member", [None, 2019], DIG, q="Olivia Zhang (2019)"),
    ],
    pubs=[PUB("https://dig.cmu.edu/publications", mode="css:.publication", title_css="h3, h2, h4, .title")],
    notes="Perer co-leads the CMU Data Interaction Group (DIG) with Dominik Moritz; the team page is not split by PI so all members are recorded (current plus PhD Alumni plus Past Members with end years 2019-2026). Faculty Perer and Moritz, and Sherry Tongshuang Wu (now faculty) and Hendrik Strobelt (IBM collaborator, past member 2021) were skipped. Past-members entries give only a last year. Publication page is the DIG list and also includes Moritz's papers; css:.publication gives 145 entries. perer.org shows selected papers only (not added).",
    blocked=[],
)

# ---------------------------------------------------------------- Andreas Robert Pfenning
PL = "http://www.pfenninglab.org/personnel/"
PL18 = WB + "20180109073308id_/http://www.pfenninglab.org:80/personnel/"
PL23 = WB + "20230203034229id_/http://www.pfenninglab.org/personnel/"
D["Andreas Robert Pfenning"] = dict(
    lab_site="http://www.pfenninglab.org/",
    people_page=PL,
    people_pages=[PL, PL18, PL23],
    members=[
        M("Ghada Abdelhady", "phd", None, PL, near="PhD Student"),
        M("Ziheng (Calvin) Chen", "phd", None, PL, near="PhD Student"),
        M("Rajee Ganesan", "phd", None, PL, near="PhD Student"),
        M("Mike Leone", "phd", None, PL, near="PhD Graduate", note="PhD (CPCB), listed on the 2022+ personnel page, now in MD/PhD at Pitt"),
        M("Chaitanya Srinivasan", "phd", None, PL, near="PhD Student"),
        M("Yaxuan Liu", "undergraduate", None, PL, near="Undergraduate Researcher"),
        M("Emmett Meyers", "undergraduate", None, PL, near="Undergraduate Researcher"),
        M("Andrew Wang", "undergraduate", None, PL, near="Undergraduate Researcher"),
        M("Ashley Brown", "staff", None, PL, near="Project Scientist/Engineer"),
        M("Lahari Gadey", "staff", None, PL, near="Research Associate / Lab Manager"),
        M("Robert van de Weerd", "staff", None, PL, near="Project Scientist"),
        M("Heather Sestili", "staff", None, PL, near="Research Programmer"),
        M("Vijay Cherupally", "staff", [2022, None], PL, near="Research Associate", note="graduated Pitt April 2022, then Research Associate"),
        M("Morgan Wirthlin", "postdoc", None, PL18, near="Postdoctoral Scholar", note="current on 2018 capture"),
        M("Easwaran Ramamurthy", "phd", None, PL18, near="PhD Student", note="current on 2018 capture"),
        M("Irene Kaplow", "postdoc", None, PL18, near="Postdoctoral Scholar", note="current on 2018 and 2023 captures; now CMU faculty"),
        M("Alyssa Lawler", "phd", None, PL18, near="PhD Student", note="current on 2018 capture"),
        M("Siddharth Annaldasula", "undergraduate", None, PL18, near="Undergraduate Researcher", note="current on 2018 capture"),
        M("Amanda Kowalczyk", "phd", None, PL23, near="PhD Student", note="current on 2023 capture"),
        M("BaDoi Phan", "phd", None, PL23, near="PhD Student", note="current on 2023 capture"),
        M("Cathy Su", "phd", None, PL23, near="PhD Student", note="current on 2023 capture"),
        M("Yixiao (Amy) Zhu", "masters", None, PL23, near="Master's Student", note="current on 2023 capture; live alumni list writes Amy (Yixiao) Zhu"),
        M("Ruby Redlich", "undergraduate", None, PL23, near="Undergraduate Researcher", note="current on 2023 capture"),
        M("John Apostolides", "member", None, PL23, near="Neurogenomics Laboratory Alumni", note="alumni already listed on the 2018 capture"),
        M("Laura Gunsalus", "member", None, PL23, near="Neurogenomics Laboratory Alumni", note="alumni already listed on the 2018 capture"),
        M("Tae Yoon (Tyler) Park", "member", None, PL23, near="Neurogenomics Laboratory Alumni", note="alumni already listed on the 2018 capture"),
        M("Christine Xu", "member", None, PL23, near="Neurogenomics Laboratory Alumni", note="alumni already listed on the 2018 capture"),
        M("Yeonju Kim", "member", None, PL23, near="Neurogenomics Laboratory Alumni", note="alumni on 2023 capture"),
        M("Michael Kleyman", "member", None, PL23, near="Neurogenomics Laboratory Alumni", note="alumni on 2023 capture"),
        M("Deepika Yeramosu", "member", None, PL23, near="Neurogenomics Laboratory Alumni", note="alumni on 2023 capture"),
    ],
    pubs=[PUB("http://www.pfenninglab.org/publications/", mode="auto")],
    notes="Live personnel page plus Wayback 2018 and 2023 captures (2020 and 2022 captures are identical to 2018). The live Alumni list is undated; kept only alumni seen as current or already alumni on a 2016+ capture. Skipped undated live-only alumni: Grant Fox, Madison Stulir, Riya Podder, Spencer Gibson, Sumitra Lele, Yuxuan Shen, Rajee Ganesan is current on live page (kept).",
    blocked=[],
)

# ---------------------------------------------------------------- Frank Pfenning
FS = "http://www.cs.cmu.edu/~fp/students.html"
D["Frank Pfenning"] = dict(
    lab_site="http://www.cs.cmu.edu/~fp/",
    people_page=FS,
    people_pages=[FS],
    members=[
        M("Rodrigo Marques", "phd", None, FS, near="Current Ph.D. Students"),
        M("Joanna Boyland", "phd", None, FS, near="Current Ph.D. Students", note="Philosophy"),
        M("Zhibo Chen", "phd", None, FS, near="Current Ph.D. Students"),
        M("Corinthia Aberlé", "phd", None, FS, near="Current Ph.D. Students"),
        M("Sophia Roshal", "phd", None, FS, near="Current Ph.D. Students"),
        M("Luiz de Sá", "phd", None, FS, near="Current Ph.D. Students"),
        M("Zeeshan Lakhani", "phd", None, FS, near="Current Ph.D. Students", note="S3D"),
        M("Siva Somayyajula", "phd", [None, 2024], FS, near="Former Ph.D. Students", note="thesis May 2024"),
        M("Klaas Pruiksma", "phd", [None, 2024], FS, q="Klaas Pruiksma Adjoint Logic with Applications Computer Science Department, May 2024."),
        M("Ryan Kavanagh", "phd", [None, 2021], FS, q="Ryan Kavanagh Communication-Based Semantics for Recursive Session-Typed Processes Computer Science Department, September 2021."),
        M("Ankush Das", "phd", [None, 2021], FS, q="Ankush Das Resource-Aware Session Types for Digital Contracts Computer Science Department, May 2021."),
        M("Farzaneh Derakhshan", "phd", [None, 2021], FS, q="Farzaneh Derakhshan (Dept of Philosophy) Session-Typed Recursive Processes and Circular Proofs Department of Philosophy, May 2021."),
        M("Henry DeYoung", "phd", [None, 2020], FS, q="Henry DeYoung Session-Typed Ordered Logical Specifications Computer Science Department, December 2020."),
        M("Anna Gommerstadt", "phd", [None, 2019], FS, q="Anna Gommerstadt Session-Typed Concurrent Contracts Computer Science Department, September 2019."),
        M("Kristina Sojakova", "phd", [None, 2016], FS, q="Kristina Sojakova Higher Inductive Types as Homotopy-Initial Algebras Computer Science Department, August 2016."),
        M("Flávio Cruz", "phd", [None, 2016], FS, q="Flávio Cruz Linear Logic and Coordination for Parallel Programming , Computer Science Department, March 2016."),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~fp/publications.html", mode="auto")],
    notes="Students & Co-authors page lists current PhD students and former PhD students with thesis dates; the page has empty Current M.S. and B.S. sections and no former M.S./B.S. lists. Former students with thesis before 2016 skipped (Martens 2015, Toninho 2015, Simmons, Lovas, Garg, Reed, Zeilberger, Dunfield, Chaudhuri, Park, Davies, Nanevski, Pientka, Polakow, Penn). Dennis Griffith (UIUC thesis April 2016, co-advised, not at CMU) skipped. Sojakova (Aug 2016) and Cruz (Mar 2016) have thesis dates in 2016 so are counted. No Wayback needed.",
    blocked=[],
)

# ---------------------------------------------------------------- Nancy Pollard
FP = "https://labs.ri.cmu.edu/foamroboticslab/people"
FP23 = WB + "20230205165618id_/https://labs.ri.cmu.edu/foamroboticslab/people/"
FP25 = WB + "20250315212639id_/https://labs.ri.cmu.edu/foamroboticslab/people/"
D["Nancy Pollard"] = dict(
    lab_site="https://labs.ri.cmu.edu/foamroboticslab/",
    people_page=FP,
    people_pages=[FP, FP23, FP25],
    members=[
        M("Capprin James Bass", "phd", None, FP, near="phd students"),
        M("Arjun Lakshmipathy", "phd", None, FP, near="phd students"),
        M("Sunyu Wang", "phd", None, FP, near="phd students"),
        M("Dominik Bauer", "staff", None, FP, near="alumni"),
        M("Cornelia Bauer", "staff", None, FP, near="Staff"),
        M("Jonathan King", "phd", None, FP, near="alumni"),
        M("Pragna Mannam", "phd", None, FP, near="alumni"),
        M("Michelle Guo", "undergraduate", None, FP, near="undergraduate students"),
        M("Chao Li", "undergraduate", None, FP, near="undergraduate students"),
        M("Jiatian Sun", "undergraduate", None, FP, near="undergraduate students"),
        M("Caroline Swanton", "undergraduate", None, FP, near="undergraduate students", note="BSR Student"),
        M("Kai-Hung Chang", "member", None, FP, near="past people", note="research scientist at Autodesk now"),
        M("Christopher Hazard", "member", None, FP, near="past people"),
        M("Daniele Moro", "member", None, FP, near="past people"),
        M("Yuzuko Nakamura", "member", None, FP, near="past people"),
        M("Nippun Sabharwal", "masters", None, FP, near="masters students", note="MSR Student"),
        M("Sayan Mondal", "masters", None, FP25, near="masters students", note="MSR Student / Teaching Assistant"),
        M("Aadarsh Narayan", "visitor", None, FP, near="visitors", note="Courtesy Student"),
        M("Rongxuan Deng", "undergraduate", None, FP, near="non-ri students"),
        M("Tracy Ding", "undergraduate", None, FP, near="non-ri students"),
        M("Maxwell Lee", "undergraduate", None, FP, near="non-ri students"),
        M("Benjamin Liu", "undergraduate", None, FP, near="non-ri students"),
        M("Jason Moroe", "undergraduate", None, FP, near="non-ri students"),
        M("Hyojae Park", "undergraduate", None, FP, near="non-ri students"),
        M("Nikita Sane", "undergraduate", None, FP, near="non-ri students"),
        M("Timothy Wang", "undergraduate", None, FP, near="non-ri students", note="Undergraduate Teaching Assistant"),
        M("Qincheng Xu", "masters", None, FP, near="non-ri students", note="Graduate Research Assistant"),
        M("Ethan Zuo", "undergraduate", None, FP, near="non-ri students"),
        M("Justin C. Macey", "staff", None, FP, near="Staff", note="Research Associate II"),
        M("Yu Xi Lee", "masters", None, FP23, near="non-ri students", note="Graduate Research Assistant"),
    ],
    pubs=[PUB("http://graphics.cs.cmu.edu/nsp/publications.html", mode="auto")],
    notes="Lab site is labs.ri.cmu.edu/foamroboticslab (previously 'Foam Robotics Lab'); PI homepage graphics.cs.cmu.edu/nsp has no student list. People page read live plus Wayback 2023 and 2025 (the earliest capture of the lab site is 2023, so 2016-2022 students are only covered where PI-site publications or the held list show them; old pages of graphics.cs.cmu.edu/nsp carry no student list). The lab-site publications page is JavaScript-only and parses empty; the PI's publications page (105 entries) was added instead. Pollard's other lab members listed as 'Staff' kept once.",
    blocked=[],
)

# ---------------------------------------------------------------- Ariel Procaccia
PP = "https://procaccia.info/people/"
def _pp(n, role, yrs, rolestr):
    return M(n, role, yrs, PP, q=f"{n} {rolestr} Carnegie Mellon University")
D["Ariel Procaccia"] = dict(
    lab_site="https://procaccia.info/",
    people_page=PP,
    people_pages=[PP],
    members=[
        _pp("Gerdus Benadè", "phd", [None, 2019], "PhD in OR, 2019"),
        _pp("Bailey Flanigan", "phd", [None, 2024], "PhD in CS, 2024"),
        _pp("Paul Gölz", "phd", [None, 2022], "PhD in CS, 2022"),
        _pp("Nika Haghtalab", "phd", [None, 2018], "PhD in CS, 2018"),
        _pp("Hadi Hosseini", "postdoc", [2016, 2016], "Postdoc, 2016"),
        _pp("Anson Kahng", "phd", [None, 2021], "PhD in CS, 2021"),
        _pp("David Kurokawa", "phd", [None, 2017], "PhD in CS, 2017"),
        _pp("Simon Mackenzie", "postdoc", [2016, 2018], "Postdoc, 2016-2018"),
        _pp("Swaprava Nath", "postdoc", [2015, 2017], "Postdoc, 2015-2017"),
        _pp("Ritesh Noothigattu", "phd", [None, 2020], "PhD in ML, 2020"),
        _pp("Alex Psomas", "postdoc", [2017, 2019], "Postdoc, 2017-2019"),
        _pp("Nisarg Shah", "phd", [None, 2016], "PhD in CS, 2016"),
        _pp("Yair Zick", "postdoc", [2014, 2016], "Postdoc 2014-2016"),
    ],
    pubs=[PUB("https://procaccia.info/publications/", mode="css:[id^=publication-]")],
    notes="procaccia.info/people lists current Harvard members (skipped) and alumni with institution; only alumni marked Carnegie Mellon University with dates overlapping 2016-2026 recorded. Procaccia left CMU for Harvard in 2018/19. Bailey Flanigan and Kahng/Gölz/Noothigattu have CMU degrees. Publications list covers all years (244 entries, 149 in window).",
    blocked=["https://cmsa.fas.harvard.edu/ (bot-challenge, Harvard center page, not needed)"],
)

# ---------------------------------------------------------------- Andre Platzer
KT = "https://logic.kastel.kit.edu/team/"
SY = "https://symbolaris.com/"
D["Andre Platzer"] = dict(
    lab_site=SY,
    people_page=KT,
    people_pages=[KT, SY],
    members=[
        M("Aditi Kabra", "phd", [None, 2025], SY, q="PhD Defense: Dr. Aditi Kabra defended her PhD thesis on Verified Control Envelope Design: Scaling for Complexity and Automation", note="CMU PhD placed by held records; page does not name the university"),
        M("Jonathan Laurent", "phd", [None, 2025], SY, q="PhD Defense: Dr. Jonathan Laurent defended his PhD thesis on Oracular Programming: A Modular Foundation for Building LLM-Enabled Software", note="CMU PhD placed by held records; page does not name the university"),
        M("Katherine Kosaian", "phd", [None, 2024], SY, q="Award: Dr. Katherine Kosaian received the Bill McCune PhD Award in Automated Reasoning 2024 for her PhD thesis", note="CMU news link on page"),
        M("Long Qian", "member", None, KT, near="External Researchers", note="listed with office at CMU"),
        M("Yong Kiam Tan", "postdoc", None, KT, near="Alumni", note="alumni of the Platzer group; CMU postdoc per held records"),
        M("Rose Bohrer", "phd", None, KT, near="Alumni", note="alumni of the Platzer group; CMU PhD per held records"),
        M("Nathan Fulton", "phd", None, KT, near="Alumni", note="alumni of the Platzer group; CMU PhD per held records"),
    ],
    pubs=[PUB("https://symbolaris.com/pub/index.html", mode="auto")],
    notes="Platzer moved to KIT (2022-23); symbolaris.com now shows KIT and has no people list; Advising section of andre.html is not in the stored text for any capture. KIT team page (logic.kastel.kit.edu/team) gives current KIT researchers (skipped as KIT) and an undated Alumni list; only alumni with CMU evidence kept (Kabra, Laurent, Kosaian from the home page announcements; Qian listed with CMU office; Tan, Bohrer, Fulton are CMU alumni per held records). Stefan Mitsch (CMU research faculty then DePaul) and Enguerrand Prebet, Riccardo Gozzi skipped. Wayback captures of the CSD profile and symbolaris homepage (2017, 2019, 2020) carry no student lists. Publications list parsed in auto mode (184 entries, 97 in window).",
    blocked=[],
)

# ---------------------------------------------------------------- Jürgen Pfeffer
PF16 = WB + "20160103122340id_/http://www.pfeffer.at:80/lab.php"
PF18 = WB + "20180114124023id_/http://pfeffer.at:80/lab.php"
D["Jürgen Pfeffer"] = dict(
    lab_site="http://www.pfeffer.at/",
    people_page=PF16,
    people_pages=[PF16, PF18],
    members=[
        M("Momin M. Malik", "phd", None, PF16, q="Momin M. Malik Ph.D. Student"),
        M("Hemank Lamba", "phd", None, PF16, q="Hemank Lamba Ph.D. Student"),
        M("Gabriel Ferreira", "phd", None, PF16, q="Gabriel Ferreira Ph.D. Student"),
        M("Constantine Nakos", "masters", None, PF16, q="Constantine Nakos Graduate Student", note="listed as Graduate Student"),
        M("Ju-Sung (Juice) Lee", "postdoc", None, PF16, q="Ju-Sung (Juice) Lee Post-Doc Researcher"),
        M("Nikou Günnemann", "staff", None, PF16, q="Nikou Günnemann Research Assistant", note="Research Assistant at CMU in 2016; later PhD student on the TUM team"),
        M("Jamie Lou Hagerty", "staff", None, PF16, q="Jamie Lou Hagerty Administration", note="administrator"),
    ],
    pubs=[],
    notes="pfeffer.at is dead live (404); read Wayback captures of lab.php: Jan 2016 (Team: Malik, Lamba, Ferreira, Nakos, Lee, Günnemann, Hagerty; Pfeffer 'on leave' at CMU ISR) and Jan 2018 ('Team @ CMU' = Malik, Lamba; 'Former Team Member @ CMU' = Lee, Ferreira, Nakos, Günnemann). A third capture (2020) shows only the TUM team. TUM team members (Mahrenbach, Mayer, Schönfeld, Rao, Petz, Mircea, Böhmer, Drechsel, West) skipped as not at CMU. Pfeffer moved to TUM in 2016-2017, so the CMU group is small. Publications page (Wayback publications.php) parses with mostly TUM-era entries and author-name junk titles, so it was not added.",
    blocked=[],
)

# ---------------------------------------------------------------- Barnabas Poczos
D["Barnabas Poczos"] = dict(
    lab_site="http://www.cs.cmu.edu/~bapoczos/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="Homepage (frames: Home, Read me, Biography, CV, Calendar, Publications -> Google Scholar, Teaching, Contact) has no students/group page; students.html, group.html, people.html, team.html all 404. MLD faculty profile URL 404s and the MLD PhD directory returns 500. Wayback (2011-2024 captures of the frameset) carries no member list. Nothing usable; the 20 held students come from other sources. Publications link goes to Google Scholar only (off limits).",
    blocked=["https://www.ml.cmu.edu/people/phd-students/ (HTTP 500)"],
)
