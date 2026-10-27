from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Martial Hebert
MHR = "https://www.ri.cmu.edu/ri-faculty/martial-hebert/"
MHR20 = WB + "20200827194032id_/https://www.ri.cmu.edu/ri-faculty/martial-hebert/"
MHR23 = WB + "20230104071820id_/https://www.ri.cmu.edu/ri-faculty/martial-hebert/"
MHN = "https://www.ri.cmu.edu/robotics-groups/navlab/"
D["Martial Hebert"] = dict(
    lab_site="https://www.ri.cmu.edu/robotics-groups/navlab/",
    people_page=MHR,
    people_pages=[MHR, MHR20, MHR23, MHN],
    members=[
        M("Anurag Bagchi", "phd", None, MHR, near="current affiliates", note="Navlab page: 'current student'; also past masters student"),
        M("Anurag Ghosh", "phd", None, MHR, near="current affiliates", note="current affiliate on live and Jan 2023 captures; Navlab 'current student'"),
        M("Christoph Mertz", "staff", None, MHR, near="current affiliates", note="Navlab research staff/head; affiliate on 2020, 2023, live"),
        M("Tiancheng Zhi", "phd", None, MHR, near="current affiliates", note="affiliate on 2020, 2023 and live"),
        M("Nadine Chang", "phd", None, MHR20, near="current phd students"),
        M("Allison Del Giorno", "phd", None, MHR20, near="current phd students"),
        M("Leonid Keselman", "phd", None, MHR20, near="current phd students", note="also current on Jan 2023 capture"),
        M("Brian E. Okorn", "phd", None, MHR20, near="current phd students"),
        M("Zhipeng Bao", "masters", None, MHR20, near="current masters students", note="current masters on Aug 2020 capture; current PhD on Jan 2023 capture; past PhD on live page"),
        M("John Kozar", "member", None, MHR20, near="current affiliates", note="affiliate on Aug 2020 capture"),
        M("Patti Rote", "member", None, MHR20, near="current affiliates", note="affiliate on 2020 and 2023 captures"),
        M("Xinhe Zhang", "member", None, MHR20, near="current affiliates", note="affiliate on Aug 2020 capture"),
        M("Philip Neugebauer", "member", None, MHR23, near="current affiliates", note="affiliate on Jan 2023 capture"),
        M("Luis Ernesto Navarro-Serment", "staff", None, MHN, near="current staff", note="Navlab current staff (senior systems scientist)"),
    ],
    pubs=[],
    notes=("Hebert (Dean of SCS; RI) has no group site beyond the RI Navlab group page and his RI profile "
           "('Students/Affiliates' tab). Used the live profile and captures of Aug 2020 and Jan 2023 (the Jan 2017 "
           "capture has no student list). Past PhD (35) and past masters (26) lists on the live profile are undated, so "
           "alumni not seen as current in a 2016+ capture were skipped (e.g. Fouhey, Misra, Walker, Wang, Venkatraman, "
           "Daftry, Girdhar, Dwibedi, Laddha, Wentao Yuan, etc., many already held from papers). Skipped faculty: Aaron "
           "Steinfeld (Navlab current staff, faculty). Pubs: RI profile shows 388 publications as embedded data that no "
           "pubx mode parses; Hebert's homepage is only a redirect notice, so no PUB added."),
    blocked=[],
)

# ---------------------------------------------------------------- Hoda Heidari
HH = "http://www.cs.cmu.edu/~hheidari/"
HH23 = WB + "20230204031103id_/http://www.cs.cmu.edu/~hheidari/"
HHN = "I currently advise the following excellent doctoral students and postdocs"
D["Hoda Heidari"] = dict(
    lab_site="http://www.cs.cmu.edu/~hheidari/",
    people_page=HH,
    people_pages=[HH, HH23],
    members=[
        M("Cyrus Cousins", "postdoc", None, HH, near=HHN, note="co-supervised with Jana Schaich Borg, Conitzer, Sinnott-Armstrong"),
        M("Michael Feffer", "phd", None, HH, near=HHN, note="co-advised with Zack Lipton"),
        M("Samsara Foubert", "phd", None, HH, near=HHN, note="co-advised with Aarti Singh"),
        M("Nari Johnson", "phd", None, HH, near=HHN),
        M("Vijay Keswani", "postdoc", None, HH, near=HHN, note="co-supervised with Jana Schaich Borg et al. (Duke); listed among doctoral students and postdocs"),
        M("Rachel Kim", "phd", None, HH, near=HHN, note="co-advised with Rayid Ghani"),
        M("Blaine Kuehnert", "phd", None, HH, near=HHN),
        M("Megan Li", "phd", None, HH, near=HHN, note="co-advised with Lorrie Cranor"),
        M("Tori Qiu", "phd", None, HH, near=HHN),
        M("Anusha Sinha", "member", None, HH, near=HHN, note="co-advised with Steven Wu; doctoral student or postdoc (page does not say)"),
        M("Ningjing Tang", "phd", None, HH, near=HHN, note="co-advised with Hong Shen"),
        M("Kimberly Truong", "phd", None, HH, near=HHN, note="co-advised with Steven Wu"),
        M("Rebecca Yu", "phd", None, HH23, q="I currently advise the following doctoral students: Michael Feffer (co-advised with Zack Lipton), Rebecca Yu",
          note="current doctoral student on the Jan/Feb 2023 capture; not on the live team list"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~hheidari/", mode="auto")],
    notes=("Heidari (joined CMU 2020) has no separate group site; the homepage 'Team' section lists current "
           "doctoral students and postdocs only (alphabetical, undated). Captures of Apr 2021 (no advisee list) and Jan 2023 (two doctoral students) were read; "
           "the 2023 one adds Rebecca Yu. Pubs: homepage list in auto mode (anchor titles; a few non-paper links such as "
           "'Carnegie Mellon University' and 'Google Scholar profile' parse as entries)."),
    blocked=[],
)

# ---------------------------------------------------------------- David Held
DH = "https://r-pad.github.io/members/"
D["David Held"] = dict(
    lab_site="https://r-pad.github.io/",
    people_page=DH,
    people_pages=[DH, WB + "20210127030553id_/https://r-pad.github.io/members/"],
    members=[
        M("Tal Daniel", "postdoc", None, DH, near="Post-Doc", note="co-hosted with Deepak Pathak"),
        M("Ying Yuan", "phd", None, DH, near="PhD Students"),
        M("Amber Li", "phd", None, DH, near="PhD Students"),
        M("Sriram Krishna", "phd", None, DH, near="PhD Students", note="co-advised with Shubham Tulsiani; earlier MSR"),
        M("Pratik Bhowal", "masters", None, DH, q="Pratik Bhowal (MSR)"),
        M("Vera Xiao", "masters", None, DH, q="Vera Xiao (MSR)"),
        M("Yinong He", "masters", None, DH, q="Yinong He (MSR)"),
        M("Madhavan Iyengar", "masters", None, DH, q="Madhavan Iyengar (MSR)"),
        M("Liyuan Geng", "masters", None, DH, q="Liyuan Geng (MSR)"),
        M("Haotian Zhan", "masters", None, DH, q="Haotian Zhan (MSR)"),
        M("Jianglan Wei", "masters", None, DH, q="Jianglan Wei (MSR)"),
        M("Robert Chu", "masters", None, DH, q="Robert Chu (MSR)"),
        M("Fiona Liu", "masters", None, DH, q="Fiona Liu (MSR)"),
        M("Ellina Zhang", "masters", None, DH, q="Ellina Zhang (MSR)", note="held as Ellina Ruiya Zhang"),
        M("Xinyu Liu", "masters", None, DH, q="Xinyu Liu (MSCV)"),
        M("Junwen Miao", "masters", None, DH, q="Junwen Miao (MSML)"),
        M("Sam Ethan Mathew", "undergraduate", None, DH, near="Undergraduate Students"),
        M("Theyanesh Eswaramoorthy Rajahkrishnan", "visitor", None, DH, near="Visiting Students"),
        M("Bu He", "visitor", None, DH, near="Visiting Students"),
        M("Daichi Yashima", "visitor", None, DH, near="Visiting Students"),
        M("Daniel Seita", "postdoc", None, DH, near="Post-Doc alumni"),
        M("Yufei Wang", "phd", None, DH, q="Yufei Wang (co-advised with Zackory Erickson)", note="PhD alumnus; also MSCS alumnus (same name)"),
        M("Ben Eisner", "phd", None, DH, near="PhD alumni"),
        M("Wenxuan Zhou", "phd", None, DH, near="PhD alumni"),
        M("Thomas Weng", "phd", None, DH, near="PhD alumni"),
        M("Brian Okorn", "phd", None, DH, q="Brian Okorn (co-advised with Martial Hebert)"),
        M("Xingyu Lin", "phd", None, DH, near="PhD alumni"),
        M("Siddharth Ancha", "phd", None, DH, q="Siddharth Ancha (co-advised with Srinivasa Narasimhan)"),
        M("Yishu Li", "masters", None, DH, q="Yishu Li (MSR)"),
        M("Kallol Saha", "masters", None, DH, q="Kallol Saha (MSR)"),
        M("Divyam Goel", "masters", None, DH, q="Divyam Goel (MSR)"),
        M("Mino Nakura", "masters", None, DH, q="Mino Nakura (MSR)"),
        M("Kyutae Sim", "masters", None, DH, q="Kyutae Sim (MSR)"),
        M("Alexis Hao", "masters", None, DH, q="Alexis Hao (MSR)"),
        M("Lyuxing He", "masters", None, DH, q="Lyuxing He (MSAI)"),
        M("Eric Cai", "masters", None, DH, q="Eric Cai (MSR)"),
        M("Octavian Donca", "masters", None, DH, q="Octavian Donca (MSR)"),
        M("Pranay Gupta", "masters", None, DH, q="Pranay Gupta (MSR)"),
        M("Zhanyi Sun", "masters", None, DH, q="Zhanyi Sun (MSR)"),
        M("Bowen Jiang", "masters", None, DH, q="Bowen Jiang (MSR)"),
        M("Mansi Agarwal", "masters", None, DH, q="Mansi Agarwal (MSR)"),
        M("Sashank Tirumala", "masters", None, DH, q="Sashank Tirumala (MSR)"),
        M("Fan Yang", "masters", None, DH, q="Fan Yang (MSR)"),
        M("Sarthak Shetty", "masters", None, DH, q="Sarthak Shetty (MSME)"),
        M("Chuer Pan", "masters", None, DH, q="Chuer Pan (MSR)"),
        M("Haolun (Harry) Zhang", "masters", None, DH, q="Haolun (Harry) Zhang (MSR)"),
        M("Carl Qi", "masters", None, DH, q="Carl Qi (MSML)"),
        M("Gaurav Pathak", "masters", None, DH, q="Gaurav Pathak (MSR)"),
        M("Zixuan Huang", "masters", None, DH, q="Zixuan Huang (MSR)"),
        M("Harshit Sikchi", "masters", None, DH, q="Harshit Sikchi (MSCS)"),
        M("Sujay Bajrachaya", "masters", None, DH, q="Sujay Bajrachaya (MSR)"),
        M("Qiao Gu", "masters", None, DH, q="Qiao Gu (MSR)"),
        M("Gautham Narayan Narasimhan", "masters", None, DH, q="Gautham Narayan Narasimhan (MSME)"),
        M("Jianing (Aurora) Qian", "masters", None, DH, q="Jianing (Aurora) Qian (MSR)"),
        M("Junyu (Jenny) Nan", "masters", None, DH, q="Junyu (Jenny) Nan (MSR)"),
        M("Mengyun (Olivia) Xu", "masters", None, DH, q="Mengyun (Olivia) Xu (MSCS)"),
        M("Edward Ahn", "masters", None, DH, q="Edward Ahn (MSR)"),
        M("Jenny Wang", "masters", None, DH, near="Master's students (Research Master's)", note="listed without degree code; Walt Disney Imagineering after"),
        M("Bharath Hegde", "visitor", None, DH, near="Visiting Reseachers"),
        M("Himangi Mittal", "visitor", None, DH, near="Visiting Reseachers"),
        M("Jianren Wang", "visitor", None, DH, near="Visiting Reseachers"),
        M("Ziyu Wang", "visitor", None, DH, near="Visiting Reseachers"),
        M("Lifan Yu", "masters", None, DH, q="Lifan Yu (MSCV)", note="capstone project master's student"),
        M("Haoyue Liu", "masters", None, DH, q="Haoyue Liu (MSCV)", note="capstone project master's student"),
        M("Yi Gu", "masters", None, DH, q="Yi Gu (MRSD)", note="capstone project master's student"),
        M("Arpit Jangid", "masters", None, DH, q="Arpit Jangid (MSCV)", note="capstone project master's student"),
        M("Ji Liu", "masters", None, DH, q="Ji Liu (MSCV)", note="capstone project master's student"),
        M("Zhenli Zhang", "masters", None, DH, q="Zhenli Zhang (MSCV)", note="capstone project master's student"),
        M("Xiaochen Han", "masters", None, DH, q="Xiaochen Han (MSCV)", note="capstone project master's student"),
        M("Tanay Sharma", "masters", None, DH, q="Tanay Sharma (MSCV)", note="capstone project master's student"),
        M("Jacinto Suner", "undergraduate", None, DH, near="Undergraduate students"),
        M("TJ Vitchutripop", "undergraduate", None, DH, near="Undergraduate students"),
        M("Angela Rodriguez-Izquierdo", "undergraduate", None, DH, near="Undergraduate students"),
        M("Rashmi Anil", "undergraduate", None, DH, near="Undergraduate students"),
        M("Patrick Liu", "undergraduate", None, DH, near="Undergraduate students"),
        M("Jake Olkin", "undergraduate", None, DH, near="Undergraduate students"),
        M("Edward Li", "undergraduate", None, DH, near="Undergraduate students"),
        M("Wen Hui Leng", "undergraduate", None, DH, near="Undergraduate students"),
        M("Yiming Fang", "undergraduate", None, DH, near="Undergraduate students"),
        M("Alex Jimenez Sanso", "undergraduate", None, DH, near="Undergraduate students"),
        M("Daniel Guo", "undergraduate", None, DH, near="Undergraduate students"),
        M("Sreyas Venkataraman", "other", None, DH, near="Interns", note="intern"),
        M("Chialiang Kuo", "other", None, DH, near="Interns", note="intern"),
        M("Gunjan Sethi", "other", None, DH, near="Interns", note="intern"),
        M("Khush Agrawal", "other", None, DH, near="Interns", note="intern"),
        M("Pengsheng Guo", "other", None, DH, near="Interns", note="intern"),
        M("Wen-Hsuan Chu", "other", None, DH, near="Interns", note="intern"),
        M("Akshay Dharmavaram", "other", None, DH, near="Interns", note="intern"),
        M("Yifan Qiao", "other", None, DH, near="Interns", note="intern"),
        M("Tiancheng Jin", "other", None, DH, near="Interns", note="intern"),
        M("Stephanie Milani", "other", None, DH, near="Interns", note="intern"),
        M("Shubham Sahoo", "other", None, DH, near="Interns", note="intern"),
        M("Rohan Chacko", "other", None, DH, near="Interns", note="intern"),
        M("Yimin Tang", "other", None, DH, near="Interns", note="intern"),
        M("Ziwen (Leo) Zhuang", "other", None, DH, near="Interns", note="intern"),
        M("Zhaoyuan (Andy) Fang", "other", None, DH, near="Interns", note="intern"),
        M("Yujie Lu", "other", None, DH, near="Interns", note="intern"),
        M("Amith Pallankize", "other", None, DH, near="Interns", note="intern"),
    ],
    pubs=[PUB("https://r-pad.github.io/publications/", mode="bibtex")],
    notes=("RPAD (Robots Perceiving And Doing) lab members page lists current members and complete alumni lists by "
           "category (post-doc, PhD, research master's, capstone master's, visiting researchers, undergraduates, "
           "interns). Held started at CMU in 2016, so all alumni entries are placed in the window although the page "
           "gives no dates. "
           "Skipped: faculty collaborators (Pathak, Tulsiani, Erickson are co-advisors only). Pubs: the publications "
           "page embeds a BibTeX entry per paper, parsed in bibtex mode (76 entries)."),
    blocked=[],
)

# ---------------------------------------------------------------- Maggie Henderson
MG = "https://www.hendersonneurolab.com/people/"
D["Maggie Henderson"] = dict(
    lab_site="https://www.hendersonneurolab.com/",
    people_page=MG,
    people_pages=[MG],
    members=[
        M("Tamar Japaridze", "phd", None, MG, near="Ph.D Students", note="Ph.D program in Cognitive Neuroscience"),
        M("Yuhan Shi", "phd", None, MG, near="Ph.D Students", note="co-supervised with Susanne Ferber"),
        M("Junru Zhao", "phd", None, MG, near="Ph.D Students"),
        M("William Friebel", "phd", None, MG, near="Ph.D Rotation Students", note="PhD rotation student (Neural Computation); also alumnus of the 2025 uPNC summer program"),
        M("Achin Parashar", "masters", None, MG, near="M.S. Students", note="M.S. in Neural Technologies (MiNT)"),
        M("Stephanie Lu", "undergraduate", None, MG, near="Undergraduate Students"),
        M("Ahana Dey", "undergraduate", None, MG, near="Undergraduate Students"),
        M("Iishaan Inabathini", "undergraduate", None, MG, near="Undergraduate Students"),
        M("Rae Gedangoni", "undergraduate", [2026, 2026], MG, near="Lab Alumni", note="uPNC summer program (Vassar/Dartmouth)"),
        M("Ziyu Li", "masters", [2025, 2026], MG, near="Lab Alumni", note="M.S. in Computational Biology"),
        M("Lucas Piper", "visitor", [2025, 2025], MG, near="Lab Alumni", note="visiting M.S. student, CMU-Portugal program (INESC-ID, IST Lisbon)"),
        M("Dylan Diaz", "undergraduate", [2025, 2025], MG, near="Lab Alumni", note="uPNC summer program (CSU San Bernardino)"),
        M("Gaurika Sawhney", "undergraduate", [2022, 2025], MG, near="Lab Alumni"),
        M("Evren Konuk", "undergraduate", [2024, 2025], MG, near="Lab Alumni"),
        M("Omisa Jinsi", "undergraduate", [2021, 2022], MG, near="Lab Alumni"),
    ],
    pubs=[PUB("https://www.hendersonneurolab.com/publications/", mode="block")],
    notes=("Henderson Lab site (hendersonneurolab.com) People page lists PI, PhD, rotation, MS, undergraduate "
           "members and dated lab alumni; Henderson is in Psychology/Neuroscience Institute, affiliated with MLD, "
           "and joined CMU in 2023, so alumni are all in window. Pubs: block mode gives titles after the author "
           "list (some entries are venues or press links)."),
    blocked=[],
)

# ---------------------------------------------------------------- Lauren Herckis
HK = "https://lauher29.dreamhosters.com/teaching/"
D["Lauren Herckis"] = dict(
    lab_site="https://lauher29.dreamhosters.com/",
    people_page=HK,
    people_pages=[HK],
    members=[
        M("Laura Delince Ceballos", "member", [2023, 2023], HK, s="Advisees", e="Laura Delince Ceballos", note="advisee listed under 2023"),
        M("Qiaoqiao Ma", "member", [2023, 2023], HK, s="Advisees", e="Qiaoqiao Ma", note="advisee listed under 2023"),
        M("Manvi Teki", "member", [2023, 2023], HK, s="Advisees", e="Manvi Teki", note="advisee listed under 2023"),
        M("Yue Wang", "member", [2023, 2023], HK, s="Advisees", e="Yue Wang", note="advisee listed under 2023"),
        M("Prithika Acharya", "member", [2022, 2022], HK, s="Advisees", e="Prithika Acharya", note="advisee listed under 2022"),
        M("Tyree Cowell", "member", [2022, 2022], HK, s="Advisees", e="Tyree Cowell", note="advisee listed under 2022"),
        M("Xinlu Gou", "member", [2022, 2022], HK, s="Advisees", e="Xinlu Gou", note="advisee listed under 2022"),
        M("Irene Kang", "member", [2022, 2022], HK, s="Advisees", e="Irene Kang", note="advisee listed under 2022"),
        M("Xiaohan Liu", "member", [2022, 2022], HK, s="Advisees", e="Xiaohan Liu", note="advisee listed under 2022"),
        M("Juhye Pak", "member", [2022, 2022], HK, s="Advisees", e="Juhye Pak", note="advisee listed under 2022"),
        M("Zhijin Wu", "member", [2022, 2022], HK, s="Advisees", e="Zhijin Wu", note="advisee listed under 2022"),
        M("Qianou Ma", "member", [2021, 2021], HK, s="Advisees", e="Qianou Ma", note="advisee listed under 2021"),
        M("Lea Cody", "member", [None, 2020], HK, s="Advisees", e="Lea Cody", note="advisee listed under '2020 and Prior'"),
        M("Vivian Qiu", "member", [None, 2020], HK, s="Advisees", e="Vivian Qiu", note="advisee listed under '2020 and Prior'"),
        M("Vera Schulz", "member", [None, 2020], HK, s="Advisees", e="Vera Schulz", note="advisee listed under '2020 and Prior'"),
        M("Elaine Zhu", "member", [None, 2020], HK, s="Advisees", e="Elaine Zhu", note="advisee listed under '2020 and Prior'"),
    ],
    pubs=[PUB("https://lauher29.dreamhosters.com/selected-publications-and-conference-presentations/", mode="auto")],
    notes=("Herckis runs the Culture Lab (HCII/Simon Initiative/University Libraries); her site (lauher29.dreamhosters.com, "
           "formerly laurenherckis.com) has no members page, only an 'Advisees' line on Teaching and Advising listing "
           "students by year (2023, 2022, 2021, '2020 and Prior'). Roles are not stated (recorded as member). "
           "Wayback captures of the old domain (2018-2023) were not used: the advisee line on the live page already "
           "spans all years. Pubs: selected publications and conference presentations page in auto mode "
           "(mixed titles; some conference talks)."),
    blocked=[],
)

# ---------------------------------------------------------------- Marijn Heule
MU = "https://www.cs.cmu.edu/~mheule/"
MUC = "https://csd.cmu.edu/people/faculty/marijn-heule"
MU22 = WB + "20220101121621id_/https://www.cs.cmu.edu/~mheule/"
D["Marijn Heule"] = dict(
    lab_site="https://www.cs.cmu.edu/~mheule/",
    people_page=MU,
    people_pages=[MU, MUC, MU22],
    members=[
        M("Bernardo Subercaseaux", "phd", None, MU, near="Team"),
        M("Cayden Codel", "phd", None, MU, near="Team", note="together with Jeremy Avigad"),
        M("Amar Shah", "phd", None, MU, near="Team", note="together with Bryan Parno"),
        M("Benjamin Przybocki", "phd", None, MU, near="Team"),
        M("Zach Battleman", "phd", None, MU, near="Team", note="together with Randy Bryant"),
        M("Emre Yolcu", "phd", None, MU, near="Former PhD students:"),
        M("Joseph Reeves", "phd", None, MU, near="Former PhD students:"),
        M("Evan Lohn", "phd", None, MU22, near="Team", note="together with Jeremy Avigad; Jan 2022 capture"),
        M("Lilian Liu", "undergraduate", None, MU22, near="Team", note="Jan 2022 capture"),
    ],
    pubs=[PUB("https://www.cs.cmu.edu/~mheule/", mode="auto")],
    notes=("Heule joined CMU in 2017 (from UT Austin, Research Assistant Professor 2017-2019). Homepage 'Team' lists "
           "5 current PhD students and 2 undated former PhD students (Yolcu, Reeves); the CSD profile 'Advisees' repeats "
           "the five current. The homepage also carries the full publication list (auto mode, bold titles; some "
           "course and media links parse as entries). James Gallicchio (MS, co-advised) appears only on Avigad's page. Jan 2022 capture adds Evan Lohn and Lilian Liu; the 2019, 2020 and 2024 captures show no Team section."),
    blocked=[],
)

# ---------------------------------------------------------------- Jan Hoffmann
JH = "http://www.cs.cmu.edu/~janh/team/"
JH19 = WB + "20190917031824id_/https://www.cs.cmu.edu/~janh/team/"
JH23 = WB + "20230104064534id_/https://www.cs.cmu.edu/~janh/team/"
JHC = "Current Group Members"
JHF = "Former Group Members"
D["Jan Hoffmann"] = dict(
    lab_site="http://www.cs.cmu.edu/~janh/",
    people_page=JH,
    people_pages=[JH, JH19, JH23],
    members=[
        M("Arnav Sabharwal", "undergraduate", None, JH, near=JHC, note="BSc student"),
        M("Ethan Chu", "phd", None, JH, near=JHC),
        M("Nathan Glover", "phd", None, JH, near=JHC),
        M("Ankush Das", "phd", None, JH19, near=JHC, note="current PhD student in 2019; since 2024 Assistant Professor at Boston University"),
        M("David Kahn", "phd", None, JH19, near=JHC, note="current in 2019 and 2023; since 2024 Assistant Professor at Denison"),
        M("Di Wang", "phd", None, JH19, near=JHC, note="current in 2019 and 2023; since 2022 Assistant Professor at Peking University"),
        M("Stefan Muller", "postdoc", None, JH19, near=JHC, note="postdoc current in 2019; since 2020 Assistant Professor at Illinois Tech"),
        M("Jessie Grosen", "phd", None, JH23, near=JHC, note="current PhD student on 2023 capture"),
        M("Long Pham", "phd", None, JH23, near=JHC, note="since 2025 Research Scientist at Oracle Labs"),
        M("Myra Dotzel", "phd", None, JH23, near=JHC, note="since 2022 PhD student advised by Limin Jia"),
        M("Runming Li", "undergraduate", None, JH23, near=JHC, note="BSc student; since 2024 PhD student at CMU"),
        M("Yiyang Guo", "masters", None, JH23, near=JHC, note="MSc student; since 2023 software engineer at Apple"),
        M("Lauren Sands", "masters", None, JH, near=JHF, note="MSc student; since 2025 Visiting Instructor at CMU"),
        M("Benjamin Lichtman", "undergraduate", None, JH19, near=JHF, note="BS student; since 2017 software engineer at Microsoft"),
        M("Biyuan Ding", "masters", None, JH19, near=JHF, note="MSCS student, listed as former member in 2019"),
        M("Chan Ngo", "postdoc", None, JH19, near=JHF, note="postdoc; since 2018 Senior Research Engineer at Aptiv"),
        M("Charles Yuan", "undergraduate", None, JH19, near=JHF, note="BS student; since 2019/2020 elsewhere"),
        M("Nicholas Roberts", "undergraduate", None, JH19, near=JHF, note="BS student; since 2019 Jane Street"),
        M("Prachi Laud", "undergraduate", None, JH19, near=JHF, note="BS student; since 2019 Facebook"),
        M("Yue Niu", "undergraduate", None, JH19, near=JHF, note="BS student; since 2018 PhD student at CMU"),
        M("Brandon Wu", "undergraduate", None, JH23, near=JHF, note="BS student; new former member between 2019 and 2023"),
        M("Ishani Santurkar", "undergraduate", None, JH23, near=JHF, note="BS student; new former member between 2019 and 2023"),
        M("Mohamed Lotfi", "undergraduate", None, JH23, near=JHF, note="BS student; new former member between 2019 and 2023"),
        M("Stephen McIntosh", "undergraduate", None, JH23, near=JHF, note="BS student; new former member between 2019 and 2023"),
        M("Vanshika Chowdhary", "undergraduate", None, JH23, near=JHF, note="BS student; new former member between 2019 and 2023"),
        M("Yinglan Chen", "undergraduate", None, JH23, near=JHF, note="BS student; since 2020 site reliability engineer at Google"),
        M("Zhongyi Cao", "undergraduate", None, JH, q="Zhongyi Cao (BSc Student); following position: Software Engeneer at Meta", note="BSc student; added to former members after the 2023 capture"),
        M("Ziqi Liu", "undergraduate", None, JH, q="Ziqi Liu (BSc Student); following position:", note="BSc student; added to former members after the 2023 capture"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~janh/publications/", mode="auto")],
    notes=("Hoffmann's team page lists current members and undated former members with 'following position' notes. "
           "Used live page and captures Sept 2019 and Jan 2023 to decide who was current when. Skipped Quentin "
           "Carbonneaux (PhD student at Yale with Zhong Shao, not placed at CMU). 2016-2018 captures of the team page "
           "were not read (cdx lists captures only from 2019 for /team/)."),
    blocked=[],
)

# ---------------------------------------------------------------- Vincent Josua Hellendoorn
D["Vincent Josua Hellendoorn"] = dict(
    lab_site="https://vhellendoorn.github.io/index.html",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes=("Hellendoorn (S3D, CMU since 2021; now on leave at Google DeepMind) has a GitHub Pages homepage with research "
           "blurbs and contact only: no students, people or publications page (people/publications/students.html all "
           "404). Captures of Oct 2022 and Feb 2024 of the homepage also list no students. The S3D faculty URL guess "
           "404s and a web search found no lab roster. Homepage links to PDFs of selected papers only."),
    blocked=[],
)

# ---------------------------------------------------------------- James D Herbsleb
HP = "https://herbsleb.org/web-people/people.shtml"
HV = "https://herbsleb.org/current-vita.pdf"
CC = "Committee Chair or Co-chair"
PA = "Postdocs Advised"
D["James D Herbsleb"] = dict(
    lab_site="https://herbsleb.org/",
    people_page=HP,
    people_pages=[HP, HV, WB + "20160209131645id_/http://herbsleb.org:80/web-people/people.shtml"],
    members=[
        M("Ben Towne", "phd", None, HP, near="Current Graduate Students", note="Societal Computing PhD; live page list (frozen ~2016)"),
        M("Jason Tsay", "phd", None, HP, near="Current Graduate Students", note="SE PhD"),
        M("Arun Kalyanasundaram", "phd", None, HP, near="Current Graduate Students", note="Societal Computing PhD"),
        M("Erik Trainer", "postdoc", None, HP, near="Postdoctoral Fellows"),
        M("Chris Bogart", "postdoc", None, HP, near="Postdoctoral Fellows"),
        M("Hongbo Fang", "phd", None, HV, s=CC, e="Hongbo Fang", note="dissertation chair/co-chair with Bogdan Vasilescu (CV, undated)"),
        M("Marat Valiev", "phd", None, HV, s=CC, e="Marat Valiev", note="dissertation chair/co-chair with Bogdan Vasilescu (CV, undated)"),
        M("David Widder", "phd", None, HV, s=CC, e="David Widder", note="with Laura Dabbish (CV, undated)"),
        M("Alexander Nolte", "postdoc", None, HV, s=PA, e="Alexander Nolte", note="CV postdocs advised (undated)"),
        M("Ei Pa Pa Pe-Than", "postdoc", None, HV, s=PA, e="Ei Pa Pa Pe-Than", note="CV postdocs advised (undated)"),
        M("Anna Filippova", "postdoc", None, HV, s=PA, e="Anna Filippova", note="CV postdocs advised (undated)"),
    ],
    pubs=[PUB("https://herbsleb.org/web-pubs/papers.shtml", mode="auto")],
    notes=("herbsleb.org is a frozen ISR-era site (captures of Feb 2016, May 2020 and Apr 2024 of the People page are identical to the live one) (copyright 2006-2018); its People page lists three current graduate "
           "students and two postdocs plus a few alumni, all pre-2016 or undated. The CV (current-vita.pdf) lists "
           "dissertation chair/co-chair students and postdocs advised without dates; those with 2016+ activity are "
           "recorded undated. Skipped as pre-2016 or undated: Chalalai Chaihirunkarn, Uri Dekel (2010), Marcelo Cataldo "
           "(2007), Patrick Wagstrom (2009), Claudia Mueller-Birn, Anita Sarma, James Howison (former postdocs). Pubs: the "
           "papers page is a stale 2014-era list (selected papers, almost all before 2016), auto mode yields few entries."),
    blocked=[],
)

# ---------------------------------------------------------------- Jessica Hodgins
JK = "https://www.ri.cmu.edu/ri-faculty/jessica-k-hodgins/"
JK20 = WB + "20200827194445id_/https://www.ri.cmu.edu/ri-faculty/jessica-k-hodgins/"
JK22 = WB + "20220226184707id_/https://www.ri.cmu.edu/ri-faculty/jessica-k-hodgins/"
D["Jessica Hodgins"] = dict(
    lab_site="https://www.ri.cmu.edu/robotics-groups/computer-graphics-lab/",
    people_page=JK,
    people_pages=[JK, JK20, JK22],
    members=[
        M("Yuyao Shi", "phd", None, JK, near="current phd students"),
        M("Jiashun Wang", "phd", None, JK, near="current phd students"),
        M("Emily Kim", "phd", None, JK20, near="current phd students", note="current PhD on 2020 and 2022 captures; past PhD on live page"),
        M("Donglai Xiang", "phd", None, JK20, near="current phd students", note="current on 2020 and 2022 captures; affiliate then past PhD on live page"),
        M("Stanislav Panev", "staff", None, JK, near="current affiliates", note="affiliate on 2022 capture and live page"),
        M("Justin C. Macey", "member", None, JK, near="current affiliates", note="affiliate on 2020, 2022 and live"),
        M("Ziyan Wang", "member", None, JK, near="current affiliates", note="affiliate on 2020, 2022 and live"),
        M("Melanie Danver", "member", None, JK20, near="current affiliates", note="affiliate on 2020 and 2022 captures"),
        M("David Morales", "member", None, JK20, near="current affiliates", note="affiliate on 2020 capture"),
        M("Andrew Whitford", "member", None, JK20, near="current affiliates", note="affiliate on 2020 capture"),
        M("Eric Yu", "member", None, JK20, near="current affiliates", note="affiliate on 2020 capture"),
        M("Yanzhe Yang", "member", None, JK22, near="current affiliates", note="affiliate on 2022 capture"),
    ],
    pubs=[],
    notes=("Hodgins's own homepage (cs.cmu.edu/~jkh) is a frozen early-2000s page with no students. Members come "
           "from her RI profile 'Students/Affiliates' tab (live page and captures of Aug 2020 and Feb 2022; the 2018 "
           "capture has no list). Past PhD (Anderson, Chai, Jain, Trutoiu, Ada Zhang) and past masters (FunShing Sin) "
           "are undated and not seen as current in a 2016+ capture, so skipped. Hodgins also appears as staff of the "
           "Human Sensing Lab (De la Torre's group; its member list not taken). RI Graphics Lab page is multi-PI "
           "news only. Pubs: RI profile lists 137 publications as embedded data that no pubx mode parses; no other "
           "publication page found."),
    blocked=[],
)

# ---------------------------------------------------------------- Veronica Hinman
HN = "https://labs.bio.cmu.edu/hinman/people/"
HN19 = WB + "20190823020419id_/https://labs.bio.cmu.edu/hinman/people/"
HN21 = WB + "20210730151820id_/https://labs.bio.cmu.edu/hinman/people/"
D["Veronica Hinman"] = dict(
    lab_site="https://labs.bio.cmu.edu/hinman/",
    people_page=HN,
    people_pages=[HN, HN19, HN21],
    members=[
        M("Katherine Buckley", "postdoc", [None, 2019], HN, near="Postdocs:", note="alumni entry '2019. Assistant Professor, Auburn University'"),
        M("Minyan (Mia) Zhang", "phd", [None, 2019], HN, near="Grad Students:"),
        M("Rene Francolini", "masters", [None, 2016], HN, near="Grad Students:", note="Masters in Computational Biology, 2016"),
        M("Siyao Wang", "undergraduate", [None, 2019], HN, near="Undergrads:", note="honors research"),
        M("Njairé Mckoy", "undergraduate", [None, 2017], HN, near="Undergrads:"),
        M("Katherine Huang", "undergraduate", [None, 2017], HN, near="Undergrads:", note="honors research"),
        M("Gregory Cary", "postdoc", None, HN19, q="Dr. Gregory Cary Postdoctoral Associate", note="manages Echinobase; Aug 2019 capture"),
        M("William Hatleberg", "postdoc", None, HN19, q="Dr. William Hatleberg Postdoctoral Researcher", note="Aug 2019 capture"),
        M("Andrew Wolff", "phd", None, HN19, q="Andrew Wolff (and Pumpkin) Ph.D. candidate", note="Aug 2019 capture"),
        M("Annie Meyer", "phd", None, HN19, q="Annie Meyer (and Monty) Ph.D. candidate", note="Aug 2019 capture"),
        M("Olga Zueva", "staff", None, HN19, q="Olga Zueva Research Assistant", note="Aug 2019 capture"),
        M("Joe Pattinato", "staff", None, HN19, q="Joe Pattinato Research Assistant", note="Aug 2019 capture"),
        M("Carolyn Ku", "undergraduate", None, HN19, q="Carolyn Ku Undergraduate Researcher", note="Aug 2019 capture"),
        M("Grace Wolczanski", "undergraduate", None, HN19, q="Grace Wolczanski Undergraduate Researcher", note="Aug 2019 capture"),
        M("Madison Dodds", "undergraduate", None, HN19, q="Madison Dodds Undergraduate Researcher", note="Aug 2019 capture"),
        M("Stephanie Blackwood", "undergraduate", None, HN19, q="Stephanie Blackwood Undergraduate Researcher", note="Aug 2019 capture"),
        M("Noah Lee", "undergraduate", None, HN19, q="Noah Lee Undergraduate Researcher", note="Aug 2019 capture; developing the Echinobase Ortholog Project"),
    ],
    pubs=[],
    notes=("Hinman Lab site (labs.bio.cmu.edu/hinman) People page: the current-member cards are unfilled template "
           "placeholders ('First Last / Title') on the live page and the Jul 2021 capture, so only the 'Lab Alumni' lists carry names there; the Aug 2019 capture lists the full current group (postdocs, PhD candidates, research assistants, undergraduates), which is where most members come from. In window: "
           "Buckley (postdoc 2019), M. Zhang (PhD 2019), Francolini (MS 2016), undergraduates Siyao Wang (2019), Mckoy "
           "and K. Huang (2017). Skipped as pre-2016 or undated: Cheatle Jarvela (PhD 2015), Ray, McCauley, Kadri, Yankura, "
           "Hughes, Lewis (2012-2013), Nikkita Mishra (undated), Annette Ko (2015) and earlier undergraduates, and all "
           "REU students (2008-2011). Pubs: the lab publications page only links to PubMed/Google Scholar (no parsable list)."),
    blocked=[],
)

# ---------------------------------------------------------------- Hanan Hibshi
D["Hanan Hibshi"] = dict(
    lab_site="http://www.cs.cmu.edu/~hhibshi/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[PUB("http://www.cs.cmu.edu/~hhibshi/publications.html", mode="auto")],
    notes=("Hibshi (INI Assistant Teaching Professor; PhD Societal Computing 2018) has a personal homepage with "
           "about/research/teaching/news and a publications page, but no students, group or advisee section on the "
           "live page or on captures of Apr 2017 and May 2021. No lab site found. Pubs: publications.html in auto "
           "mode (bold titles, 2016-2018 papers mostly)."),
    blocked=[],
)
