from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Christopher Timperley
CT = "https://chris.timperley.info/"
D["Christopher Timperley"] = dict(
    lab_site=CT,
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[PUB(CT + "publications/", mode="auto")],
    notes="Personal site chris.timperley.info (Home, Publications, Teaching, CV) has no students/members/group page; RI profile URL 404s and the RI search API returns only a seminar event. Home page only lists selected publications. No alumni captures read because there is no people section to capture. Publications page parses cleanly (39 entries, 10 missing from lab papers, titles and years correct).",
    blocked=[],
)

# ---------------------------------------------------------------- Ben Titzer
W25 = WB + "20250622171400id_/https://www.cs.cmu.edu/wrc/meet-our-team"
D["Ben Titzer"] = dict(
    lab_site="https://www.cs.cmu.edu/wrc/",
    people_page="https://www.cs.cmu.edu/wrc/meet-our-team",
    people_pages=[W25],
    members=[
        M("Yash Anand", "masters", None, W25, q="Yash Anand MSE Candidate, Software Engineering"),
        M("Jay Bosamiya", "phd", None, W25, q="Jay Bosamiya Ph.D. Candidate, Computer Science", note="WRC student researcher; center page does not name advisors"),
        M("Siyuan Chen", "phd", None, W25, q="Siyuan Chen Ph.D. Candidate, Computer Science", note="WRC student researcher; center page does not name advisors"),
        M("Elizabeth Gilbert", "phd", None, W25, q="Elizabeth Gilbert Ph.D. Candidate, Software Engineering"),
        M("Alexa Halim", "undergraduate", [2023, 2023], W25, q="Alexa Halim REU Student 2023"),
        M("I-Jen Hsiao", "masters", [None, 2022], W25, q="I-Jen Hsiao (MS 2022) Research Assistant"),
        M("Yuqiao Hu", "undergraduate", None, W25, q="Yuqiao Hu Undergraduate Research Assistant"),
        M("Tianshu Huang", "phd", None, W25, q="Tianshu Huang Ph.D. Candidate, Electrical & Computer Engineering", note="co-author with Titzer and Anthony Rowe"),
        M("John Pluchino", "undergraduate", [2022, 2022], W25, q="John Pluchino REU Student 2022"),
        M("Arjun Ramesh", "phd", None, W25, q="Arjun Ramesh Ph.D. Candidate, Electrical & Computer Engineering", note="co-author with Titzer and Anthony Rowe"),
        M("Kazuyuki Takayama", "masters", None, W25, q="Kazuyuki Takayama MSE Candidate, Software Engineering"),
        M("Bradley Wei Jie Teo", "undergraduate", None, W25, q="Bradley Wei Jie Teo Undergraduate Research Assistant"),
        M("Carly Venenciano", "undergraduate", [2023, 2023], W25, q="Carly Venenciano REU Student 2023"),
        M("Yunqing (Tibbers) Yu", "undergraduate", None, W25, q="Yunqing (Tibbers) Yu Undergraduate Research Assistant"),
        M("Haoyu Zhang", "masters", None, W25, q="Haoyu Zhang M.S. Candidate Information Networking Institute"),
        M("Yuxin (Vincy) Zheng", "undergraduate", None, W25, q="Yuxin (Vincy) Zheng Undergraduate Research Assistant"),
    ],
    pubs=[],
    notes="Titzer has no personal lab site; his S3D profile lists no site. He directs the WebAssembly Research Center (cs.cmu.edu/wrc); its Meet Our Team page loads names with JavaScript so the live fetch shows only section headings, and the 2025-06 Wayback capture has the full list (Student Researchers - Past & Present, 16 students, not grouped by PI so all are recorded; Bosamiya and Chen are likely advised by others, flagged in notes). Affiliated faculty skipped: Heather Miller (WRC co-director), Fraser Brown, Phillip Gibbons, Limin Jia, Claire Le Goues, Brandon Lucia, Dominik Moritz, Bryan Parno, Anthony Rowe, Vyas Sekar. 2024-06 capture exists but was not needed. No publications page (WRC research page lists projects/talks, not a paper list).",
    blocked=[],
)

# ---------------- Matthew O'Toole (duplicate row of b19)
IMG = "https://imaging.cs.cmu.edu/team/"
IMGPUB = "https://imaging.cs.cmu.edu/publications/"
IMG19 = WB + "20191013095347id_/http://imaging.cs.cmu.edu:80/team/"
IMG21 = WB + "20210301003205id_/https://imaging.cs.cmu.edu/team/"

D["Matthew O'Toole"] = dict(
    lab_site="https://imaging.cs.cmu.edu/",
    people_page=IMG,
    people_pages=[IMG, IMG19, IMG21],
    members=[
        M('Mani Ramanagopal', 'postdoc', None, IMG, q='Mani Ramanagopal PostDoc'),
        M('Mian Wei', 'postdoc', None, IMG, q='Mian Wei PostDoc'),
        M('Anurag Ghosh', 'phd', None, IMG, q='Anurag Ghosh PhD Student'),
        M('Gaurav Parmar', 'phd', None, IMG, q='Gaurav Parmar PhD Student'),
        M('Haejoon Lee', 'phd', None, IMG, q='Haejoon Lee PhD Student'),
        M('Khiem Vuong', 'phd', None, IMG, q='Khiem Vuong PhD Student'),
        M('Sagnik Ghosh', 'phd', None, IMG, q='Sagnik Ghosh PhD Student'),
        M('Sally Chen', 'phd', None, IMG, q='Sally Chen PhD Student'),
        M('Shen Zheng', 'phd', None, IMG, q='Shen Zheng PhD Student'),
        M('Sreekar Ranganathan', 'phd', None, IMG, q='Sreekar Ranganathan PhD Student'),
        M('Sriram Narayanan', 'phd', None, IMG, q='Sriram Narayanan PhD Student'),
        M('Tanli Su', 'phd', None, IMG, q='Tanli Su PhD Student'),
        M('Yingsi Qin', 'phd', None, IMG, q='Yingsi Qin PhD Student'),
        M('Bharath Hegde', 'masters', None, IMG, q='Bharath Hegde MS Student'),
        M('Shengxi Wu', 'masters', None, IMG, q='Shengxi Wu MS Student'),
        M('Hyojae Park', 'undergraduate', None, IMG, q='Hyojae Park Undergraduate Student'),
        M('Qirui Da', 'undergraduate', None, IMG, q='Qirui Da Undergraduate Student'),
        M('Akihiko Oharazawa', 'visitor', None, IMG, q='Akihiko Oharazawa Visitor'),
        M('Takahiro Kushida', 'visitor', None, IMG, q='Takahiro Kushida Visitor'),
        M('Zeqing Leo Yuan', 'masters', None, IMG, q='Zeqing Leo Yuan Alumni MS Student', note='undated alumnus on the shared team page; included because already held for this PI'),
        M('Mayank Mishra', 'masters', None, IMG, q='Mayank Mishra Alumni MS Student', note='undated alumnus on the shared team page; included because already held for this PI'),
        M('Chao Liu', 'phd', None, IMG, q='Chao Liu Alumni PhD Student', note='undated alumnus on the shared team page; included because already held for this PI'),
        M('Minh Vo', 'phd', None, IMG, q='Minh Vo Alumni PhD Student', note='undated alumnus on the shared team page; included because already held for this PI'),
        M('Tiancheng Zhi', 'phd', None, IMG, q='Tiancheng Zhi Alumni PhD Student', note='undated alumnus on the shared team page; included because already held for this PI'),
        M('Shumian Xin', 'phd', None, IMG, q='Shumian Xin Alumni PhD Student', note='undated alumnus on the shared team page; included because already held for this PI'),
        M('Joe Bartels', 'postdoc', None, IMG, q='Joe Bartels Alumni PostDoc', note='undated alumnus on the shared team page; included because already held for this PI'),
        M('Anqi Yang', 'phd', None, IMG, q='Anqi Yang Alumni PhD Student', note='undated alumnus on the shared team page; included because already held for this PI'),
        M('Dinesh Reddy', 'phd', None, IMG, q='Dinesh Reddy Alumni PhD Student', note='undated alumnus on the shared team page; included because already held for this PI'),
        M('Adithya Pediredla', 'postdoc', None, IMG19, q='Adithya Pediredla PostDoc', note='listed as current on the 2019 capture'),
        M('Mark Sheinin', 'postdoc', None, IMG19, q='Mark Sheinin PostDoc', note='listed as current on the 2019 capture'),
        M('Vijay Rengarajan', 'postdoc', None, IMG19, q='Vijay Rengarajan PostDoc', note='listed as current on the 2019 capture'),
        M('Alankar Kotwal', 'phd', None, IMG19, q='Alankar Kotwal PhD Student', note='listed as current on the 2019 capture'),
        M('Arjun Teh', 'phd', None, IMG19, q='Arjun Teh PhD Student', note='listed as current on the 2019 capture'),
        M('Bakari Hassan', 'phd', None, IMG19, q='Bakari Hassan PhD Student', note='listed as current on the 2019 capture'),
        M('Byeongjoo Ahn', 'phd', None, IMG19, q='Byeongjoo Ahn PhD Student', note='listed as current on the 2019 capture'),
        M('Chengqian (Bruce) Che', 'phd', None, IMG19, q='Chengqian (Bruce) Che PhD Student', note='listed as current on the 2019 capture'),
        M('Michael De Zeeuw', 'phd', None, IMG19, q='Michael De Zeeuw PhD Student', note='listed as current on the 2019 capture'),
        M('Rick Chang', 'phd', None, IMG19, q='Rick Chang PhD Student', note='listed as current on the 2019 capture'),
        M('Vishwanath Saragadam', 'phd', None, IMG19, q='Vishwanath Saragadam PhD Student', note='listed as current on the 2019 capture'),
        M('Wei-Yu Chen', 'phd', None, IMG19, q='Wei-Yu Chen PhD Student', note='listed as current on the 2019 capture'),
        M('Yi Hua', 'phd', None, IMG19, q='Yi Hua PhD Student', note='listed as current on the 2019 capture'),
        M('Bhargav Ghanekar', 'masters', None, IMG19, q='Bhargav Ghanekar MS Student', note='listed as current on the 2019 capture'),
        M('Roshan Sharma', 'masters', None, IMG19, q='Roshan Sharma MS Student', note='listed as current on the 2019 capture'),
        M('Jiatian (Caroline) Sun', 'undergraduate', None, IMG19, q='Jiatian (Caroline) Sun Undergraduate Student', note='listed as current on the 2019 capture'),
        M('Bailey Miller', 'phd', None, IMG21, q='Bailey Miller PhD Student', note='listed on the 2021 capture'),
        M('Benjamin Attal', 'phd', None, IMG21, q='Benjamin Attal PhD Student', note='listed on the 2021 capture'),
        M('Dorian Chan', 'phd', None, IMG21, q='Dorian Chan PhD Student', note='listed on the 2021 capture'),
        M('Leron Julian', 'phd', None, IMG21, q='Leron Julian PhD Student', note='listed on the 2021 capture'),
        M('Shirsendu Halder', 'masters', None, IMG21, q='Shirsendu Halder MS Student', note='listed on the 2021 capture'),
        M('Po Ryan', 'undergraduate', None, IMG21, q='Po Ryan Undergraduate Student', note='listed on the 2021 capture'),
        M('Vaishnavi Mantha', 'undergraduate', None, IMG21, q='Vaishnavi Mantha Undergraduate Student', note='listed on the 2021 capture'),
        M('Sai Praveen Bangaru', 'masters', None, IMG21, q='Sai Praveen Bangaru Alumni Student', note='listed on the 2021 capture'),
    ],
    pubs=[PUB(IMGPUB, mode="auto")],
    notes='Straight-apostrophe duplicate input row of Matthew O’Toole (same person, same decisions as batch b19). Own homepage has publications but no people list; members from the shared Imaging @ CMU team page (not grouped by PI, so recorded for Narasimhan too). Live alumni list (about 45 names) has no dates; recorded the alumni already held plus everyone listed as current on the 2019 and 2021 Wayback captures (John Galeotti is faculty, skipped); remaining undated alumni (about 20, e.g. Steven Lee, Guanzhou Ji, Neham Jain, Yash Belhe, Ethan Tseng) skipped. Publications page lists only ~11 recent papers.',
    blocked=[],
)

# ---------------------------------------------------------------- Matthew J Travers
ML = "https://themattlab.org/people/current/"
MA = "https://themattlab.org/people/alumni/"
D["Matthew J Travers"] = dict(
    lab_site="https://themattlab.org/",
    people_page=ML,
    people_pages=[ML, MA],
    members=[
        M("Ralph Boirum", "staff", None, ML, q="Staff/Postdocs Ralph Boirum Engineer"),
        M("Prasanna Sriganesh", "phd", None, ML, q="Graduate Students Prasanna Sriganesh Robotics Ph.D Student"),
        M("Tingrui Zhang", "masters", None, ML, q="Tingrui Zhang ECE Masters Student"),
        M("Dhruv Dange", "masters", None, ML, q="Dhruv Dange Robotics Masters Student"),
        M("Kaushik Chavali", "masters", None, ML, q="Kaushik Chavali Robotics Masters Student"),
        M("Mithun Roy", "undergraduate", None, ML, q="Undergraduates Mithun Roy ECE Student"),
        M("Zongyuan Shen", "postdoc", None, MA, q="Former Postdocs Dr. Zongyuan Shen Postdoctoral Fellow"),
        M("Charles Noren", "phd", [None, 2025], MA, q="Former PhD Students Dr. Charles Noren PhD in Robotics, 2025"),
        M("Burhanuddin Shirose", "phd", None, MA, q="Burhanuddin Shirose PhD in Mech.E.", note="undated alumnus; lab papers 2024-2025 place him at CMU in the window"),
        M("Ryan Darnley", "masters", [None, 2021], MA, q="Former Masters Student Ryan Darnley MS in Robotics, 2021"),
        M("Joshua Spisak", "masters", [None, 2023], MA, q="Joshua Spisak MS in Robotics, 2023"),
        M("Namya Bagree", "masters", [None, 2023], MA, q="Namya Bagree MS in Mech.E., 2023"),
        M("Damanpreet Singh", "masters", [None, 2023], MA, q="Damanpreet Singh MS in Mech.E., 2023"),
        M("Sourojit Saha", "masters", [None, 2023], MA, q="Sourojit Saha MS in Mech.E., 2023"),
        M("Adam Johnson", "masters", [None, 2024], MA, q="Adam Johnson MS ECE, 2024"),
        M("James Maier", "masters", [None, 2024], MA, q="James Maier MS in Robotics, 2024"),
        M("Sahil Chaudhary", "masters", [None, 2025], MA, q="Sahil Chaudhary MS in Mech.E., 2025"),
        M("Rohan Chandrashekar", "masters", [None, 2025], MA, q="Rohan Chandrashekar MS in Mech.E., 2025"),
        M("Anushree Sabnis", "masters", None, MA, q="Anushree Sabnis MS in Mech.E.", note="undated alumna listed on the MattLab alumni page (a 2023-era paper author on this lab's page); included as a lab member"),
        M("Barath Satheeshkumar", "masters", None, MA, q="Barath Satheeshkumar MS in Mech.E.", note="undated alumnus; co-author on the lab's 2025 staircase paper"),
    ],
    pubs=[PUB("https://themattlab.org/publications/", mode="anchor")],
    notes="MattLab site themattlab.org (current members, alumni, publications). Live pages only so far. The alumni page dates most master's alumni; two PhD/MS alumni (Shirose, Sabnis, Satheeshkumar) are undated and kept because they are authors on 2023-2025 lab papers. Travers himself is listed as Lab Director (skipped). Publications page parsed with anchor mode (14 entries, 4 missing from lab papers).",
    blocked=[],
)

# ---------------------------------------------------------------- Yulia Tsvetkov
TS = "https://tsvetshop.github.io/people.html"
D["Yulia Tsvetkov"] = dict(
    lab_site="https://tsvetshop.github.io/",
    people_page=TS,
    people_pages=[TS],
    members=[
        M("Vidhisha Balachandran", "phd", [None, 2024], TS, q="Vidhisha Balachandran PhD'24 @ CMU"),
        M("Chan Young Park", "phd", [None, 2024], TS, q="Chan Young Park PhD'24 @ CMU"),
        M("Sachin Kumar", "phd", [None, 2023], TS, q="Sachin Kumar PhD '23 @ CMU"),
        M("Anjalie Field", "phd", [None, 2022], TS, q="Anjalie Field PhD '22 @ CMU"),
        M("Zirui Wang", "phd", [None, 2022], TS, q="Zirui Wang PhD '22 @ CMU"),
        M("Nupoor Gandhi", "phd", None, TS, q="Nupoor Gandhi PhD Student, CMU"),
        M("Alissa Ostapenko", "masters", [None, 2022], TS, q="Alissa Ostapenko MLT '22"),
        M("Artidoro Pagnoni", "masters", [None, 2021], TS, q="Artidoro Pagnoni MLT'21"),
        M("Rishabh Joshi", "masters", [None, 2021], TS, q="Rishabh Joshi MLT '21"),
        M("Gayatri Bhat", "masters", [None, 2020], TS, q="Gayatri Bhat MLT '20"),
        M("Yiheng Zhou", "masters", [None, 2019], TS, q="Yiheng Zhou MLT '19"),
        M("Emily Ahn", "masters", [None, 2019], TS, q="Emily Ahn MLT '19"),
    ],
    pubs=[PUB("https://tsvetshop.github.io/publications.html", mode="auto")],
    notes="Tsvetkov moved to the University of Washington in 2021; the group site tsvetshop.github.io lists UW students under People and CMU-era students in the Alumni block. Recorded only alumni marked CMU/MLT (LTI master's) with CMU degree years (12). UW-only members (Ahia, Feng, Ahuja, S. Li, Wang, Nazar, Light, Yao, Theologitis, Cooper, Njoo, Fisher, Lucy Li, Sclar, Han, Mireshghallah, He) skipped, as is Antonio Theophilo (UNICAMP -> Microsoft, no CMU dates). Her UW homepage has no student list. Wayback captures of the older group page not read (see final report).",
    blocked=[],
)

# ---------------------------------------------------------------- Shubham Tulsiani
SHT = "https://shubhtuls.github.io/"
D["Shubham Tulsiani"] = dict(
    lab_site=SHT,
    people_page=SHT,
    people_pages=[SHT],
    members=[
        M("Hanzhe Hu", "phd", None, SHT, near="PhD Students"),
        M("Himangi Mittal", "phd", None, SHT, near="PhD Students"),
        M("Qitao Zhao", "phd", None, SHT, near="PhD Students"),
        M("Yehonathan Litman", "phd", None, SHT, near="PhD Students", note="co-advised with Fernando De la Torre"),
        M("Yuxuan Kuang", "phd", None, SHT, near="PhD Students", note="co-advised with Katerina Fragkiadaki"),
        M("Clara Cong", "masters", None, SHT, near="MS Students"),
        M("Lucas Wu", "masters", None, SHT, near="MS Students"),
        M("Minsik Jeon", "masters", None, SHT, near="MS Students"),
        M("Soumojit Bhattacharya", "masters", None, SHT, near="MS Students"),
        M("Sungjae Park", "masters", None, SHT, near="MS Students"),
        M("Jason Zhang", "phd", [None, 2024], SHT, q="Alumni PhD : Jason Zhang (co-advised with Deva Ramanan), Sparse-view 3D in the Wild, 2024."),
        M("Yufei Ye", "phd", [None, 2024], SHT, q="Yufei Ye (co-advised with Abhinav Gupta), Learning to Perceive and Predict Everyday Interactions, 2024."),
        M("Homanga Bharadhwaj", "phd", [None, 2025], SHT, q="Homanga Bharadhwaj (co-advised with Abhinav Gupta), Watch, Predict, Act: Robot Learning meets Web Videos, 2025."),
        M("Yanbo Xu", "masters", None, SHT, q="MSR : Yanbo Xu . PhD at Princeton", note="undated MSR alumnus; PI joined CMU 2021 straight from industry, so alumni are CMU RI master's students"),
        M("Bharath Raj", "masters", None, SHT, q="Bharath Raj . PhD at Cornell", note="undated MSR alumnus"),
        M("Zhizhuo (Z) Zhou", "masters", None, SHT, q="Zhizhuo (Z) Zhou . PhD at Stanford", note="undated MSR alumnus"),
        M("Rena Ju", "masters", None, SHT, q="MSCV : Rena Ju , Poorvi Hebbar", note="undated MSCV alumna"),
        M("Poorvi Hebbar", "masters", None, SHT, q="Poorvi Hebbar , Naveen Venkat", note="undated MSCV alumna"),
        M("Naveen Venkat", "masters", None, SHT, q="Naveen Venkat , Mayank Agarwal", note="undated MSCV alumnus"),
        M("Mayank Agarwal", "masters", None, SHT, q="Mayank Agarwal , Yen-Chi Cheng", note="undated MSCV alumnus"),
        M("Yen-Chi Cheng", "masters", None, SHT, q="Yen-Chi Cheng , Paritosh Mittal", note="undated MSCV alumnus"),
        M("Paritosh Mittal", "masters", None, SHT, q="Paritosh Mittal Undergraduate : Amy Lin", note="undated MSCV alumnus"),
        M("Amy Lin", "undergraduate", None, SHT, q="Undergraduate : Amy Lin", note="undated undergraduate alumna"),
    ],
    pubs=[PUB(SHT, mode="auto")],
    notes="Group info lives on the PI homepage shubhtuls.github.io (Research Group section: PhD, MS, alumni). No separate lab site (RI profile links only to this homepage). Tulsiani joined CMU in 2021 (previously at FAIR, no prior academic group), so undated alumni of CMU RI programs (MSR/MSCV) and an undergraduate are recorded as members; flagged as undated in notes. Publications are on the same page (77 entries parsed, ~2 junk rows from non-paper anchors, 36 not in lab papers).",
    blocked=[],
)

# ---------------------------------------------------------------- Bogdan Vasilescu
SP_ = "https://cmustrudel.github.io/people/"
D["Bogdan Vasilescu"] = dict(
    lab_site="https://cmustrudel.github.io/",
    people_page=SP_,
    people_pages=[SP_],
    members=[
        M("Thomas Bock", "postdoc", None, SP_, q="Thomas Bock Postdoctoral Researcher"),
        M("Nandini Sharma", "postdoc", None, SP_, q="Nandini Sharma Postdoctoral Researcher"),
        M("Shyam Agarwal", "phd", [2025, None], SP_, q="Shyam Agarwal PhD Societal Computing, 2025 -"),
        M("Hao He", "phd", [2023, None], SP_, q="Hao He PhD Software Engineering, 2023 -"),
        M("Courtney Miller", "phd", [2021, None], SP_, q="Courtney Miller PhD Software Engineering, 2021 -"),
        M("Anita Brown", "undergraduate", [2017, 2017], SP_, q="Anita Brown REU 2017, Bryn Mawr College"),
        M("Hongbo Fang", "phd", [2019, None], SP_, q="Hongbo Fang PhD Societal Computing, 2019-"),
        M("Jacob Hoffman", "undergraduate", [2017, 2017], SP_, q="Jacob Hoffman REU 2017, CMU, CS"),
        M("Hemank Lamba", "phd", [2014, None], SP_, q="Hemank Lamba PhD Societal Computing, 2014-"),
        M("Theresa Lim", "undergraduate", [2021, 2021], SP_, q="Theresa Lim REU 2021, Princeton University"),
        M("Daye Nam", "phd", [2018, None], SP_, q="Daye Nam PhD Software Engineering, 2018-"),
        M("Cassandra Overney", "undergraduate", [2019, 2019], SP_, q="Cassandra Overney REU 2019, Olin College of Engineering"),
        M("Huilian (Sophie) Qiu", "phd", [2017, None], SP_, q="Huilian (Sophie) Qiu PhD Societal Computing, 2017-"),
        M("Naveen Raman", "undergraduate", [2019, 2019], SP_, q="Naveen Raman REU 2019, University of Maryland, College Park"),
        M("Sophie Rosas-Smith", "undergraduate", [2018, 2018], SP_, q="Sophie Rosas-Smith REU 2018, Wellesley College"),
        M("Asher Trockman", "undergraduate", [2017, 2017], SP_, q="Asher Trockman REU 2017, U. of Evansville"),
        M("Marat Valiev", "phd", [2016, None], SP_, q="Marat Valiev PhD Societal Computing, 2016-"),
        M("David Widder", "phd", [2017, None], SP_, q="David Widder PhD Software Engineering, 2017-"),
    ],
    pubs=[PUB("https://cmustrudel.github.io/publications/", mode="bibtex")],
    notes="STRUDEL lab site cmustrudel.github.io (linked from bvasiles.github.io). People page lists current members plus alumni; undated alumni skipped: Raunak Agnihotri, Fabio Calefato, Michelle Cao, Alan Jaffe, Jeremy Lacomis, Yucen (Lily) Li, Alex Nolte, Adithya Raghuraman (8). Affiliated faculty skipped: Jim Herbsleb, Christian Kastner, Narayan Ramasubbu. Publications page has no per-entry year text for the default extractor; bibtex mode gives 108 entries with correct years (11 not in lab papers).",
    blocked=[],
)

# ---------------------------------------------------------------- Manuela Veloso
MV = "https://www.cs.cmu.edu/~mmv/"
D["Manuela Veloso"] = dict(
    lab_site=MV,
    people_page=MV,
    people_pages=[MV],
    members=[
        M("Mengda Xu", "phd", [None, 2025], MV, q="Mengda Xu , Ph.D. Robotics, August 2025", note="co-advised with Shuran Song"),
        M("Kevin Zhang", "phd", [None, 2025], MV, q="Kevin Zhang , Ph.D. Robotics, February 2025", note="co-advised with Oliver Kroemer"),
        M("Ishani Chatterjee", "phd", [None, 2022], MV, q="Ishani Chatterjee , Ph.D. Robotics, September 2022."),
        M("Nicholay Topin", "phd", [None, 2022], MV, q="Nicholay Topin , Ph.D. Machine, July 2022."),
        M("Anahita Mohseni-Kabir", "phd", [None, 2021], MV, q="Anahita Mohseni-Kabir , Ph.D. Robotics, August 2021."),
        M("Max Korein", "phd", [None, 2021], MV, q="Max Korein, , Ph.D. Robotics, August 2021."),
        M("Devin Schwab", "phd", [None, 2020], MV, q="Devin Schwab , Ph.D. Robotics, August 2020."),
        M("Rui Silva", "phd", [None, 2020], MV, q="Rui Silva , Ph.D. Computer Science, August 2020, dual degree, CMU-Portugal Program"),
        M("Kim Baraka", "phd", [None, 2020], MV, q="Kim Baraka , Ph.D. Robotics, August 2020, dual degree, CMU-Portugal Program"),
        M("Philip Cooksey", "phd", [None, 2019], MV, q="Philip Cooksey , Ph.D. Robotics, May 2019."),
        M("Rongye Shi", "phd", [None, 2019], MV, q="Rongye Shi , Ph.D. Electrical and Computer Engineering, May 2019."),
        M("Tiago Pereira", "phd", [None, 2019], MV, q="Tiago Pereira , Ph.D. Electrical and Computer Engineering, May 2019, dual degree, CMU-Portugal Program"),
        M("Vittorio Perera", "phd", [None, 2018], MV, q="Vittorio Perera , Ph.D. Computer Science, August 2018, Amazon."),
        M("Danny Zhu", "phd", [None, 2017], MV, q="Danny Zhu , Ph.D. Computer Science, December 2017, Determined AI."),
        M("Juan Pablo Mendoza", "phd", [None, 2017], MV, q="Juan Pablo Mendoza , Ph.D. Robotics, August 2017, Waymo."),
        M("Richard Wang", "phd", [None, 2016], MV, q="Richard Wang , Ph.D. Computer Science, May 2016, ABB."),
        M("Junyun Tay", "phd", [None, 2016], MV, q="Junyun Tay , Ph.D. Mechanical Engineering, May 2016, dual degree, CMU ME/NTU CoE Program"),
    ],
    pubs=[],
    notes="Veloso has been at J.P. Morgan since July 2018 (Head of JPMorganChase AI Research until March 2026; now Emerita), so members are placed at CMU via her homepage list of past advised PhD students (dated by degree month). Recorded the 17 with degree dates 2016-2025 (CMU 2016-2026); the 'Current PhD Students' heading is empty. Dated before 2016 skipped: Brandao, Samadi, Biswas, Mericli, Coltin and all earlier (about 25). The CORAL site (cs.cmu.edu/~coral) people page is a ~2012 snapshot (Coltin, Biswas, Brandao, Mendoza, Korein, Reddy, Samadi, Tay, Fazli, Licitra) and was not used beyond confirming names already on the homepage. Publications page www.cs.cmu.edu/~mmv/Veloso.html is JavaScript-driven from an unlisted bib source and renders no entries, so no publications page was added.",
    blocked=[],
)

# ---------------------------------------------------------------- Rashmi Korlakai Vinayak
RV = "http://www.cs.cmu.edu/~rvinayak/"
D["Rashmi Korlakai Vinayak"] = dict(
    lab_site=RV,
    people_page=RV,
    people_pages=[RV],
    members=[
        M("Sanjith Athlur", "phd", None, RV, near="Current students"),
        M("Timothy Kim", "phd", None, RV, near="Current students"),
        M("Yixuan Mei", "phd", None, RV, near="Current students"),
        M("Saransh Chopra", "phd", None, RV, near="Current students"),
        M("Meredith Pan", "masters", None, RV, near="Masters students"),
        M("Frank Chen", "masters", None, RV, near="Masters students"),
        M("Bob Chen", "undergraduate", None, RV, near="Undergraduate students"),
        M("Juncheng (Jason) Yang", "phd", None, RV, near="Graduated students", note="graduated; PhD dissertation award 2025"),
        M("Francisco Maturana", "phd", None, RV, q="Francisco Maturana (CMU -> AWS Data Storage team)"),
        M("Michael Rudow", "phd", None, RV, q="Michael Rudow (CMU -> McKinsey)"),
        M("Jack Kosaian", "phd", None, RV, q="Jack Kosaian (CMU -> Nvidia)"),
        M("Saurabh Kadekodi", "phd", [None, 2020], RV, q="Saurabh Kadekodi (co-advised with Greg Ganger) (CMU -> Research Scientist at Google)", note="thesis defended 2020 per news item"),
        M("Justin Zhang", "masters", None, RV, q="Justin Zhang (CMU -> Purdue Ph.D. student)"),
        M("Jiyu Hu", "masters", None, RV, q="Jiyu Hu (CMU -> UIUC Ph.D. student)"),
        M("Kaige Liu", "masters", None, RV, q="Kaige Liu (CMU -> Meta)"),
        M("Abhishek Kumar", "masters", None, RV, q="Abhishek Kumar (CMU)"),
        M("Shaobo Guan", "masters", None, RV, q="Shaobo Guan (CMU)"),
        M("Arvind Sai Krishnan", "masters", None, RV, q="Arvind Sai Krishnan (CMU)"),
        M("Vilas Bhat", "masters", None, RV, q="Vilas Bhat (CMU -> Google)"),
        M("Jiaan Dai", "masters", None, RV, q="Jiaan Dai (CMU)"),
        M("Jiaqi Zuo", "masters", None, RV, q="Jiaqi Zuo (CMU)"),
        M("Jiongtao Ye", "masters", None, RV, q="Jiongtao Ye (CMU)"),
        M("Xuren Zhou", "masters", None, RV, q="Xuren Zhou (CMU)"),
        M("Sai Kiriti Badam", "masters", None, RV, q="Sai Kiriti Badam (CMU)"),
        M("Helen Wang", "undergraduate", None, RV, q="Helen Wang (CMU)"),
        M("Tianyu Zhang", "undergraduate", None, RV, q="Tianyu Zhang (CMU -> CMU 5th year masters)"),
        M("Ian Chiu", "undergraduate", None, RV, q="Ian Chiu (CMU -> Instagram)"),
        M("Eliot Robson", "undergraduate", None, RV, q="Eliot Robson (CMU -> UIUC Ph. D. student)"),
        M("Sanya Agarwarl", "undergraduate", None, RV, q="Sanya Agarwarl (CMU)", note="name spelled thus on the page"),
    ],
    pubs=[PUB(RV, mode="li")],
    notes="TheSys group (Theory + Systems) at www.cs.cmu.edu/~rvinayak/ (the input lab_url is a stale Berkeley homepage that redirects here); the Group section lists current students and graduated students without dates, though every entry is marked (CMU). She joined CMU in 2016 as an assistant professor after her Berkeley PhD, so all CMU-marked students fall inside 2016-2026 and undated graduates are recorded. Skipped as not placed at CMU: Ziming Mao (Yale -> UC Berkeley), Chaitanya Mukka (BITS, India), Weizhong Zhang (Tsinghua -> CMU Tepper PhD); Saransh Chopra and Timothy Kim appear as both current PhD and graduated masters, Justin Zhang as masters and undergraduate (recorded once). PI is currently on leave at Google. Publications are inline on the homepage as quoted titles; auto extraction returned only news-item fragments, but li mode parses 62 entries with correct titles and years (12 not in lab papers).",
    blocked=[],
)

# ---------------------------------------------------------------- Riad Wahby
WN = "https://wahby.net/"
QD = "https://quangvdao.github.io/"
D["Riad Wahby"] = dict(
    lab_site=WN,
    people_page=None,
    people_pages=[],
    members=[
        M("Quang Dao", "phd", None, QD, s="Quang Dao Quang Dao PhD Student", e="advised by Aayush Jain and Riad Wahby", note="evidence is the student's own homepage; no group page exists"),
    ],
    pubs=[PUB(WN, mode="auto")],
    notes="wahby.net is a personal page (bio, publications, CV) with no students/group section; his CV lists no advisees and says Assistant Professor in ECE at CMU since September 2022 (previously Stanford PhD, Algorand/NYU). The CSD profile has no site link. Found one CMU PhD student through web search (Quang Dao, advised by Aayush Jain and Riad Wahby, per his own homepage); already held under both advisors. Publications are inline on the home page (55 entries, 26 not in lab papers; class-title extraction gives correct titles and years, 14 undated items are talks/tech reports).",
    blocked=[],
)

# ---------------------------------------------------------------- Alex Waibel
D["Alex Waibel"] = dict(
    lab_site="https://www.cs.cmu.edu/~ahw/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[],
    notes="Homepage cs.cmu.edu/~ahw/ is contact + biography only and points to the Interactive Systems Labs / InterACT sites at KIT (isl.anthropomatik.kit.edu, interact.anthropomatik.kit.edu), which did not answer from this host (connection errors) and describe the Karlsruhe group in any case. The input lab_url (afs path) is robots-disallowed. No CMU InterACT people page was found (cs.cmu.edu/~interact 404; LTI faculty profile URLs 404).",
    blocked=["http://www.cs.cmu.edu/afs/cs.cmu.edu/user/ahw/www/index.html"],
)

# ---------------------------------------------------------------- Weina Wang
WW = "https://www.cs.cmu.edu/~weinaw/group.html"
D["Weina Wang"] = dict(
    lab_site="https://www.cs.cmu.edu/~weinaw/",
    people_page=WW,
    people_pages=[WW],
    members=[
        M("Andreas Kalavas", "phd", None, WW, near="Current PhD students", note="co-advised with Nina Balcan"),
        M("Yige Hong", "phd", None, WW, near="Current PhD students"),
        M("Jalani Williams", "phd", [None, 2024], WW, q="Jalani Williams (PhD, 2024)"),
        M("Tuhinangshu Choudhury", "phd", [None, 2024], WW, q="Tuhinangshu Choudhury (PhD, 2024)"),
        M("Wenxin Ding", "masters", [None, 2021], WW, q="Wenxin Ding (Masters, 2021)"),
    ],
    pubs=[PUB("https://www.cs.cmu.edu/~weinaw/publications.html", mode="auto")],
    notes="Personal site cs.cmu.edu/~weinaw with a Research Group page (2 current PhD students, 3 dated alumni); she joined CMU in Fall 2018, so all fall inside the window. Publications page parses well (49 entries, 12 not in lab papers).",
    blocked=[],
)
