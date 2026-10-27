from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Umut Acar
UA = "https://www.umut-acar.org"
UA17 = WB + "20170110094507id_/http://www.umut-acar.org:80/"
UA20 = WB + "20200126103403id_/http://www.umut-acar.org:80/"
UA23 = WB + "20230104064529id_/https://www.umut-acar.org/"
D["Umut Acar"] = dict(
    lab_site="https://www.umut-acar.org",
    people_page=UA,
    people_pages=[UA, UA17, UA20, UA23],
    members=[
        M("Pengyu Liu", "phd", None, UA, q="Research Group Pengyu Liu , PhD student"),
        M("Colin McDonald", "phd", None, UA, q="Colin McDonald , PhD student"),
        M("Mike Rainey", "staff", None, UA, q="Mike Rainey , Research scientist"),
        M("Mingkuan Xu", "phd", None, UA, q="Mingkuan Xu , PhD student ( Now: Citadel )"),
        M("Jatin Arora", "phd", [None, 2024], UA, q="Jatin Arora , PhD 2024"),
        M("Sam Westrick", "phd", [None, 2022], UA, q="Sam Westrick , PhD 2022",
          note="also listed as Post Doc in the 2023 capture"),
        M("Yue Yao", "masters", [None, 2020], UA, q="Yue Yao, M.S. 2020"),
        M("Yifan Qiao", "undergraduate", [None, 2019], UA, q="Yifan Qiao , Undergraduate 2019"),
        M("Rohan Yadav", "undergraduate", [None, 2019], UA, q="Rohan Yadav B.S. 2019"),
        M("Vijay Ramamurthy", "undergraduate", [None, 2019], UA, q="Vijay Ramamurthy B.S. 2019"),
        M("Stefan Muller", "phd", [None, 2018], UA, q="Stefan Muller Ph.D. 2018"),
        M("Ram Raghunathan", "masters", [None, 2017], UA, q="Ram Raghunathan M.A. 2017",
          note="listed as Ph.D. student in the 2017 capture; left with M.A. 2017"),
        M("Adrien Guatto", "postdoc", [2016, 2017], UA, q="Adrien Guatto Post-doc 2016-17",
          note="page does not state the institution; Acar also held an Inria Paris appointment then"),
        M("Daniel Anderson", "phd", None, UA20, q="Daniel Anderson, PhD (ongoing)",
          note="2020 capture only"),
        M("Matei Budiu", "undergraduate", None, UA23, q="Matei Budiu, B.S. student"),
        M("Puhua Cheng", "undergraduate", None, UA23, q="Puhua Cheng, B.S. student"),
    ],
    pubs=[PUB("https://www.umut-acar.org/publications", mode="anchor")],
    notes=("cs.cmu.edu/~umut points to umut-acar.org (Google Sites); members from the live 'Research Group'/"
           "'Alumni' section plus 2017/2020/2023 captures. Skipped: alumni ending before 2016 (Bhatotia 2015, "
           "Chargueraud, Dunfield, Hammer, Rainey-as-postdoc 2010-12, Sumer, Turkoglu, Ley-Wild, Morgenstern); "
           "Yan Chen (Ph.D. ABD 2015, MPI-SWS per 2017 capture) and Filip Sieczkowski (post-doc 2014-16 at "
           "Inria Paris per 2017 capture) are not CMU."),
    blocked=[],
)

# ---------------------------------------------------------------- Henny Admoni
HA = "https://harp.ri.cmu.edu/members"
HA18 = WB + "20180129025539id_/http://harp.ri.cmu.edu:80/members/"
HA21 = WB + "20210417032723id_/http://harp.ri.cmu.edu/members/"
HA24 = WB + "20240227031426id_/https://harp.ri.cmu.edu/members/"
_ha_ug_cur = ["Yudh Shukla", "Deanna Paukstitus", "David Yi", "Lily Qin", "Geoffrey Sun"]
_ha_ug_alum = ["Annika Srinivasan", "William Montague", "Rithika Narayan", "Ellen Lee", "Shenai Chan",
               "Ethan Villalovoz", "Preethi Krishnamoorthy", "Ivy He", "Ana Runova", "Gustavo Silvera",
               "Karen Zhang", "George Yu", "Jared Santa Maria", "Michael Huang", "Carolyn Youstra",
               "Vignesh Rajmohan", "Minji Kim", "Samuel Leong", "Meghna Behari", "Roman Kaufman",
               "Siddharth Girdhar"]
_ha_riss_alum = ["Nyomi Morris", "Narit Trikasemsak", "Ellie Mamantov", "Kathleen Medill", "Nadia AlMutlak"]
D["Henny Admoni"] = dict(
    lab_site="https://harp.ri.cmu.edu/",
    people_page=HA,
    people_pages=[HA, HA18, HA21, HA24],
    members=[
        M("Pragathi Praveena", "postdoc", None, HA, near="Postdoctoral Scholars"),
        M("Michelle Zhao", "phd", None, HA, near="PhD Students", note="defended June 2026 per lab news"),
        M("Zulekha Karachiwalla", "phd", None, HA, near="PhD Students"),
        M("Patrick Callaghan", "phd", None, HA, near="PhD Students"),
        M("Pranay Gupta", "phd", None, HA, near="PhD Students", note="Master's student in the 2024 capture"),
        M("Cailyn Smith", "phd", None, HA, near="PhD Students"),
        M("Audrey Lee", "phd", None, HA, near="PhD Students"),
        M("Jack Mirenzi", "masters", None, HA, near="Master’s Students"),
        M("Juan Ortega", "masters", None, HA, near="Master’s Students"),
    ] + [M(n, "undergraduate", None, HA, near="Undergraduate students") for n in _ha_ug_cur] + [
        M("Arlene Reyes", "undergraduate", [2026, None], HA, near="Undergraduate students",
          note="RISS summer scholar 2026 per lab news"),
        M("Evelyn Moncayo", "undergraduate", [2026, None], HA, near="Undergraduate students",
          note="RISS summer scholar 2026 per lab news"),
        M("Suresh Kumaar Jayaraman", "postdoc", None, HA, near="Postdoctoral Scholars",
          note="alumni; current postdoc in 2024 capture"),
        M("Tesca Fitzgerald", "postdoc", None, HA, near="Postdoctoral Scholars",
          note="alumni; current postdoc in 2021 capture; now Yale faculty"),
        M("Reuben Aronson", "phd", None, HA, near="PhD Students", note="alumni; current PhD in 2018 capture"),
        M("Stephanie Valencia-Valencia", "phd", None, HA, near="PhD Students", note="alumni; now UMD faculty"),
        M("Pallavi Koppol", "phd", None, HA, near="PhD Students", note="alumni"),
        M("Abhijat Biswas", "phd", None, HA, near="PhD Students", note="alumni; MSR student in 2018 capture"),
        M("Mike Lee", "phd", None, HA, near="PhD Students", note="alumni"),
        M("Ada Taylor", "phd", None, HA, near="PhD Students", note="alumni"),
        M("Ben Newman", "phd", None, HA, near="PhD Students", note="alumni"),
        M("Maggie Collier", "phd", None, HA, near="Master’s Students",
          note="PhD student in 2021/2024 captures; live page lists her under alumni Master's"),
        M("Shreeya Khurana", "masters", None, HA, near="Master’s Students", note="alumni (MLD)"),
        M("Yaxin Hu", "masters", None, HA, near="Master’s Students", note="alumni (Computational Design)"),
        M("Sarthak Ahuja", "masters", None, HA, near="Master’s Students", note="alumni (MSR)"),
        M("Calvin Qiao", "masters", None, HA, near="Master’s Students", note="alumni (Mechanical Engineering)"),
        M("Karsh Tharyani", "masters", None, HA, near="Master’s Students", note="alumni (MRSD); current 2018"),
        M("I-Chen Jwo", "masters", None, HA, near="Master’s Students", note="alumni (MRSD); current 2018"),
        M("Ting-Che Lin", "masters", None, HA, near="Master’s Students", note="alumni (MRSD); current 2018"),
        M("Jiahong Ouyang", "masters", None, HA, near="Master’s Students", note="alumni (MRSD); current 2018"),
        M("Yang Yang", "masters", None, HA, near="Master’s Students", note="alumni (MRSD); current 2018"),
    ] + [M(n, "undergraduate", None, HA, near="Undergraduate Students", note="alumni") for n in _ha_ug_alum] + [
        M(n, "undergraduate", None, HA, near="Undergraduate Students", note="alumni; RISS summer scholar")
        for n in _ha_riss_alum] + [
        M("Ayaka Matsumoto", "visitor", None, HA, near="Visting Students", note="visiting student (alumni)"),
        M("Juan Pablo Vasconez", "visitor", None, HA, near="Visting Students", note="visiting student (alumni)"),
    ],
    pubs=[PUB("https://harp.ri.cmu.edu/publications", mode="auto")],
    notes=("HARP Lab site (harp.ri.cmu.edu -> harplab.github.io). Live Members page lists current members and a "
           "complete alumni section; 2018/2021/2024 captures add nobody new (all listed people reappear on the live "
           "page). Lab founded ~2017-18, so every listed person is in window. Collaborators Aaron Steinfeld, "
           "Kris Kitani, Laura Herlant (faculty/external) skipped."),
    blocked=[],
)

# ---------------------------------------------------------------- Yuvraj Agarwal
YA = "https://www.synergylabs.org/people"
YA16 = WB + "20160313234656id_/http://synergylabs.org/people.html"
YA17 = WB + "20170627121607id_/http://synergylabs.org/people.html"
YA21 = WB + "20210225041625id_/https://www.synergylabs.org/people/"
_ya_alum_ms = ["Saksham Chitkara", "Chen Chen", "Kunal Bhuwalka", "Priyanshi Jain", "Abhijith Anilkumar",
               "Pranav Dheer", "Xingchen Wang"]
D["Yuvraj Agarwal"] = dict(
    lab_site="https://www.synergylabs.org/",
    people_page=YA,
    people_pages=[YA, YA16, YA17, YA21],
    members=[
        M("Haozhe Zhou", "phd", None, YA, near="Graduate Students"),
        M("Ben Weinshel", "phd", None, YA, near="Graduate Students"),
        M("Anupama Sitaraman", "phd", None, YA, near="Graduate Students"),
        M("Swarup Kumar Sahoo", "postdoc", [2016, None], YA, near="Alumni: Visiting Faculty, Researchers, and Postdocs",
          note="2017 capture: (2016-Current) Post Doctoral Associate"),
        M("Shreyas Nagare", "staff", None, YA, near="Alumni: Visiting Faculty, Researchers, and Postdocs",
          note="Research Assistant; listed as current visiting researcher in 2021 capture"),
        M("Anurag Maravi", "staff", None, YA, near="Alumni: Visiting Faculty, Researchers, and Postdocs",
          note="Research Assistant; listed as current visiting researcher in 2021 capture"),
        M("Yuanchun Li", "visitor", None, YA, near="PhD Alumni", note="Visiting PhD Researcher"),
        M("Pardis Emami-Naeini", "phd", None, YA, near="PhD Alumni"),
        M("Aqsa Kashaf", "phd", None, YA, near="PhD Alumni"),
        M("Haojian Jin", "phd", None, YA, near="PhD Alumni"),
        M("Tianshi Li", "phd", None, YA, near="PhD Alumni"),
        M("Han Zhang", "phd", None, YA, near="PhD Alumni"),
        M("Sudershan Boovaraghavan", "phd", [2016, None], YA, near="PhD Alumni",
          note="visiting researcher from 2016 per 2017 capture, then PhD"),
        M("Prasoon Patidar", "phd", None, YA, near="PhD Alumni"),
        M("Nishad Gothoskar", "undergraduate", [2015, None], YA, near="Alumni", note="2015-Current in 2017 capture"),
        M("Kevin Ku", "undergraduate", [2016, 2016], YA17, q="Kevin Ku (2016) Undergraduate Researcher"),
        M("Tarun Karuturi", "masters", [2015, 2016], YA17, q="Tarun Karuturi (2015-2016) Student Researcher MS"),
        M("Joshua Gluck", "phd", None, YA17, q="Joshua Gluck Pursuing a PhD (Societal Computing)",
          note="live page lists him as alumni Master Student Researcher"),
        M("Dohyun Kim", "phd", None, YA17, q="Dohyun Kim Pursuing a PhD (Societal Computing)",
          note="live page lists him as alumni Master Student Researcher"),
    ] + [M(n, "masters", None, YA, near="Master Student Researcher", note="alumni") for n in _ya_alum_ms] + [
        M("Abhijith Ragav", "other", None, YA, near="Research Intern", note="alumni; Research Intern"),
        M("Lisa Dougherty", "staff", None, YA17, q="Administrative Lisa Dougherty Lab Administrative Assistant"),
        M("Akshay Patel", "undergraduate", [2014, None], YA17, q="Akshay Patel (2014 - Current) Undergraduate Researcher"),
        M("Vikram Shanker", "undergraduate", [2015, None], YA17, q="Vikram Shanker (2015-Current) Undergraduate Researcher"),
        M("Brandon Schmuck", "undergraduate", [2014, None], YA17, q="Brandon Schmuck (2014-Current) Undergraduate Researcher"),
        M("David Simon", "undergraduate", [2016, None], YA17, q="David Simon (2016 - Current) Undergraduate Reseacher"),
        M("Abhijit Hota", "masters", [2016, None], YA17, q="Abhijit Hota (2016-Current) Masters Student Researcher"),
        M("Sandeep Rao", "masters", [2015, None], YA17, q="Sandeep Rao (2015-Current) Masters Student Researcher",
          note="under Alumni in 2017 capture; current in Mar 2016 capture"),
        M("Daedeepya Yendluri", "masters", [2015, None], YA16,
          q="Daedeepya Yendluri (2015-Current) Masters Student Researcher", note="current in Mar 2016 capture only"),
    ],
    pubs=[PUB("https://www.synergylabs.org/publications/", mode="anchor")],
    notes=("Synergy Lab (synergylabs.org; CSD profile Website link). Live People page plus 2016/2017 captures of the "
           "old people.html and a 2021 capture. Skipped as previous-institution (UCSD) members not placed at CMU: "
           "Bharathan Balaji (UCSD PhD, ucsd email), Jason Koh (UCSD), Malcolm Hall (2012-2014), Virginia McIlwain "
           "(@UCSD), and the UCSD MS/PhD alumni block (Weng, Lyles, Kuppuswamy, McCullough, Dutta, Chandrashekhar, "
           "Bishop, Wei, Masich, Tang, Rizhen Zhang, Qi Li, Yan Zhang, Xiaoxiao Zhang, Nwokafor). Skipped CMU people "
           "whose stated dates end 2015 (Murali Balakrishnan postdoc 2014-2015, Joseph Chan Joo Keng 2014, June "
           "Young Park 2015, Leanna Pancoast 2015) and Hitachi visitors 2012-13. Faculty collaborators (Gupta, "
           "Singh, Dey, Hong) skipped."),
    blocked=[],
)

# ---------------------------------------------------------------- Alessandro Acquisti
AQ = WB + "20250913222457id_/https://www.heinz.cmu.edu/~acquisti/academic-genealogy.htm"
AQ20 = WB + "20200423004825id_/https://www.heinz.cmu.edu/~acquisti/academic-genealogy.htm"
AQ23 = WB + "20230529010509id_/https://www.heinz.cmu.edu/~acquisti/academic-genealogy.htm"
PX21 = WB + "20210922104203id_/https://peex.heinz.cmu.edu/people/"
D["Alessandro Acquisti"] = dict(
    lab_site="https://www.heinz.cmu.edu/~acquisti/",
    people_page=AQ,
    people_pages=[AQ, AQ20, AQ23, PX21],
    members=[
        M("Eduardo Mustri", "phd", None, AQ, near="Current Students", note="main advisor; current since 2020 capture"),
        M("Jessica Colnago", "phd", None, AQ, near="Current Students", note="co-advisor (SCS)"),
        M("Logan Warberg", "phd", None, AQ, near="Current Students", note="co-advisor (EPP)"),
        M("Ryan Steed", "phd", None, AQ, near="Current Students", note="main advisor"),
        M("Zijun Ding", "phd", None, AQ, near="Current Students", note="main advisor"),
        M("Cristobal Cheyre", "postdoc", None, AQ, near="Post-Doctoral Fellows"),
        M("Jim Graves", "phd", None, PX21, q="Jim Graves is a PhD student in Engineering and Public Policy",
          note="PeeX people page (frozen older content, 2021 capture); genealogy lists him under Former Students; "
               "CV co-authored papers 2016-2019"),
        M("Sonam Samat", "phd", None, PX21, q="Sonam Samat is a PhD student in Public Policy & Management",
          note="PeeX people page (frozen older content, 2021 capture); genealogy lists her under Former Students; "
               "CV co-authored SOUPS papers 2017-2018"),
    ],
    pubs=[PUB(WB + "20251108093114id_/https://www.heinz.cmu.edu/~acquisti/papers.htm", mode="auto")],
    notes=("Live heinz.cmu.edu/~acquisti/ 404s since late 2025/2026; used Wayback. People come from the Academic "
           "Genealogy page (captures 2020/2023/2025; no earlier captures) and the PeeX lab people page "
           "(peex.heinz.cmu.edu/people, content frozen at ~2014: Adjerid, Brandimarte, Gross, Mislavsky, Peer, "
           "Romanosky, Stutzman all left before 2016, skipped). current-students.htm lists no names; CV has no "
           "advising list. Undated Former Students not seen as current in any 2016+ capture skipped (12): Alisa Frik, "
           "Brett Danaher, Eyal Peer, Florian Schaub, Fred Stutzman, Idris Adjerid, Laura Brandimarte, Leslie John, "
           "Li Jiang, Ralph Gross, Sasha Romanosky, Veronica Marotta (Marotta/Frik/Jiang/Schaub may overlap 2016+ "
           "but the site gives no dates)."),
    blocked=[],
)

# ---------------------------------------------------------------- Leman Akoglu
LK = "https://www.andrew.cmu.edu/user/lakoglu/research.html"
LK18 = WB + "20180105060705id_/http://www.andrew.cmu.edu:80/user/lakoglu/research.html"
LK22 = WB + "20220506111124id_/https://www.andrew.cmu.edu/user/lakoglu/research.html"
DL21 = WB + "20210515090416id_/https://datalab.heinz.cmu.edu/people/"
D["Leman Akoglu"] = dict(
    lab_site="https://www.andrew.cmu.edu/user/lakoglu/",
    people_page=LK,
    people_pages=[LK, LK18, LK22, DL21],
    members=[
        M("Haomin Wen", "postdoc", [2024, None], LK, q="Haomin Wen , Post-doc (May 2024 - )"),
        M("Shurui Cao", "phd", [2023, None], LK, q="Shurui Cao , PhD student (co-advisor, F 2023 - )"),
        M("Xueying Ding", "phd", [2021, None], LK, q="Xueying Ding , PhD student (advisor, F 2021 - )"),
        M("Lingxiao Zhao", "phd", [2017, None], LK, q="Lingxiao Zhao , PhD student (advisor, F 2018 - )",
          note="MS student (ECE/SCS) F 2017 - S 2018 before the PhD"),
        M("Konstantinos Sotiropoulos", "postdoc", [2023, 2023], LK,
          q="Konstantinos Sotiropoulos , Post-doc (Jul 2023 - Dec 2023)"),
        M("Yue Zhao", "phd", [2019, 2023], LK, q="Yue Zhao , PhD student (advisor, F 2019 - 2023)"),
        M("Shubhranshu Shekhar", "phd", [2017, 2023], LK, q="Shubhranshu Shekhar , PhD student (advisor, F 2017 - 2023)"),
        M("Saurabh Sawlani", "postdoc", [2020, 2021], LK, q="Saurabh Sawlani , Post-doc (Jul 2020 - Aug 2021)"),
        M("Dimitris Berberidis", "postdoc", [2019, 2020], LK, q="Dimitris Berberidis , Post-doc (Jul 2019 - Jul 2020)"),
        M("Hung Nguyen", "postdoc", [2018, 2019], LK, q="Hung Nguyen , Post-doc (Aug 2018 - Aug 2019)"),
        M("Xuejian Wang", "phd", [2018, 2019], LK, q="Xuejian Wang , PhD student (advisor, F 2018 - F 2019)"),
        M("Sachin Grover", "phd", [2018, 2019], LK, q="Sachin Grover, PhD student (advisor, F 2018 - F 2019)"),
        M("Jing Mao", "masters", [2019, 2019], LK, q="Jing Mao , MS student, ECE (research advisor, Summer 2019)"),
        M("Tuan Le", "postdoc", [2017, 2018], LK, q="Tuan Le , Post-doc (F 2017 - F 2018)"),
        M("Meghanath Macha", "phd", [2016, 2018], LK, q="Meghanath Macha , PhD student (advisor, F 2016 - F 2018)"),
        M("Hemank Lamba", "phd", [2017, 2018], LK, q="Hemank Lamba , PhD student (advisor, F 2017 - S 2018)",
          note="co-advisor per 2018 capture"),
        M("Emaad Ahmed Manzoor", "phd", [2016, 2018], LK,
          q="Emaad Ahmed Manzoor , PhD student (advisor, F 2016 - S 2018)",
          note="followed her from Stony Brook (2015-2016); DATA Lab page: PhD, CMU"),
        M("Xuan Wu", "masters", [2017, 2018], LK, q="Xuan Wu, MS student, SCS (research advisor, S 2017 - S 2018)"),
        M("Abhinav Maurya", "phd", [2017, 2017], LK, q="Abhinav Maurya , PhD student (Summer 2017)",
          note="student collaborator, not her advisee"),
        M("Runshan Fu", "phd", [2017, 2017], LK, q="Runshan Fu , PhD student (S 2017)",
          note="student collaborator, not her advisee"),
    ],
    pubs=[PUB("https://www.andrew.cmu.edu/user/lakoglu/pubs.html", mode="auto")],
    notes=("Homepage research.html 'Student collaborators' section lists CMU students/postdocs with dates (she moved "
           "to CMU Heinz Aug 2016); 2018/2022 captures add nobody. DATA Lab site (datalab.heinz.cmu.edu, dead live; "
           "Wayback people page frozen ~2019) adds no CMU names. Stony Brook students (Rayana, Rezaei, Ye, Chan, "
           "Perozzi, Baig, Han, Kwon, Mishra, Lakshminarayanan, Pudipeddi, Bhat, Kulkarni, Gao, Park, Dai) skipped. "
           "Held Meng-Chieh Lee is not on her pages (co-author only)."),
    blocked=[],
)

# ---------------------------------------------------------------- Jonathan Aldrich
JA = "http://www.cs.cmu.edu/~aldrich/aldrich-cv.html"
JA17 = WB + "20170306060500id_/http://www.cs.cmu.edu/~aldrich/aldrich-cv.html"
JA20 = WB + "20200108174136id_/http://www.cs.cmu.edu:80/~aldrich/aldrich-cv.html"
JA23 = WB + "20230520162532id_/http://www.cs.cmu.edu/~aldrich/aldrich-cv.html"
D["Jonathan Aldrich"] = dict(
    lab_site="http://www.cs.cmu.edu/~aldrich/",
    people_page=JA,
    people_pages=[JA, JA17, JA20, JA23],
    members=[
        M("Michael Maass", "phd", [None, 2016], JA, q="Michael Maass (Ph.D. 2016", note="co-advised with William Scherlis"),
        M("Cyrus Omar", "phd", [None, 2017], JA, q="Cyrus Omar (Ph.D. 2017"),
        M("Ligia Nistor", "phd", [None, 2017], JA, q="Ligia Nistor (Ph.D. 2017"),
        M("Darya Melicher", "phd", [None, 2019], JA, q="Darya Melicher (Ph.D. 2019"),
        M("Michael Coblenz", "phd", [None, 2020], JA, q="Michael Coblenz (Ph.D. 2020", note="co-advised with Brad Myers"),
        M("Jenna Wise DiVincenzo", "phd", [None, 2023], JA, q="Jenna Wise DiVincenzo (Ph.D. 2023",
          note="co-advised with Joshua Sunshine"),
        M("Selva Samuel", "phd", [None, 2024], JA, q="Selva Samuel (Ph.D. 2024)"),
        M("Kyle Liang", "phd", None, JA, near="Ph.D. Advisees"),
        M("Luís Gomes", "phd", None, JA, near="Ph.D. Advisees", note="co-advised with Vincent Hellendoorn and Rui Abreu"),
        M("Ian McCormack", "phd", None, JA, near="Ph.D. Advisees", note="co-advised with Joshua Sunshine"),
        M("Catarina Gamboa", "phd", None, JA, near="Ph.D. Advisees", note="co-advised by Alcides Fonseca"),
        M("Hemant Gouni", "phd", None, JA, near="Postdoctoral Advisees"),
        M("Long Nguyen", "phd", None, JA, near="Postdoctoral Advisees"),
        M("Juli O'Connor", "phd", None, JA, near="Postdoctoral Advisees"),
        M("Mikail Khan", "phd", None, JA, near="Postdoctoral Advisees"),
        M("Waqar Ahmad", "phd", None, JA17, near="Ph.D. Advisees", note="co-advised with Christian Kästner; 2017 capture only"),
        M("Katherine Ye", "phd", None, JA20, near="Ph.D. Advisees", note="co-advised with Keenan Crane; 2020 capture only"),
        M("Anlun Xu", "masters", [None, 2020], JA, near="Master's Thesis Advisees"),
        M('Yu Xiang "Billy" Zhu', "masters", [None, 2019], JA, near="Master's Thesis Advisees"),
        M("Johannes Bader", "masters", [None, 2016], JA, near="Master's Thesis Advisees"),
        M("Esther Wang", "undergraduate", [None, 2016], JA, near="Undergraduate Thesis Advisees"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~aldrich/papers/", mode="anchor")],
    notes=("No group/people page; homepage has no student list. Members from the 'Advising' section of the html CV "
           "(live) plus 2017/2020/2023 captures. Skipped: Ph.D. advisees graduating 2009-2015 (Malayeri, Bierhoff, "
           "Abi-Antoun, Beckman, Jaspan, Krishnaswami, LaToza, Stork, Sunshine, Militao (defended Dec 2015)); "
           "postdocs Bocchino, Balzer, Du Li (undated; all listed as 'now at' elsewhere already in the 2017 capture); "
           "master's/undergraduate/independent-study advisees completed 2004-2012."),
    blocked=[],
)

# ---------------------------------------------------------------- Vincent Aleven
VA17 = WB + "20170316161412id_/http://www.cs.cmu.edu:80/~aleven/"
D["Vincent Aleven"] = dict(
    lab_site="http://www.cs.cmu.edu/~aleven/",
    people_page=None,
    people_pages=[VA17],
    members=[
        M("Franceska Xhakaj", "phd", None, VA17, q="HCII PhD student Franceska Xhakaj",
          note="named in homepage news (page last updated Sep 2016; also in 2019 capture)"),
        M("Erik Harpstead", "phd", None, VA17, q="HCII Ph.D. student Erik Harpstead",
          note="named in homepage news (page last updated Sep 2016)"),
        M("Jenny Olsen", "phd", None, VA17, q="HCII Ph.D. student Jenny Olsen",
          note="named in homepage news; Siebel Scholar class of 2017"),
    ],
    pubs=[],
    notes=("Homepage names the 'Creating Adaptive Tutoring Systems (CATS) Lab' but there is no lab site or people "
           "page (HCII profile links only to the homepage; web search found no CATS Lab site). Homepage captures "
           "2016-2026 checked (2017/2019/2021): the only member names are three HCII PhD students in the 2016-era "
           "news section; Martina Rau / Nikol Rummel are external faculty collaborators; Jo Bodnar is the HCII "
           "administrative associate (not recorded). publications.html is a stale 2016 'Selected publications' "
           "page with 4 entries (nothing missing), not added."),
    blocked=[],
)

# ---------------------------------------------------------------- George Amvrosiadis
GA = "https://www.cs.cmu.edu/~gamvrosi/"
GA20 = WB + "20200113124440id_/http://users.ece.cmu.edu:80/~gamvrosi/"
GA23 = WB + "20230117050614id_/http://users.ece.cmu.edu/~gamvrosi/"
D["George Amvrosiadis"] = dict(
    lab_site="https://www.cs.cmu.edu/~gamvrosi/",
    people_page=GA,
    people_pages=[GA, GA20, GA23],
    members=[
        M("Sherman Lim", "phd", None, GA, near="Students"),
        M("Sheng Jiang", "phd", None, GA, near="Students"),
        M("Ziyue Qiu", "phd", None, GA, near="Students", note="with Greg Ganger"),
        M("Nj Mukherjee", "phd", None, GA, near="Students"),
        M("Jekyeom Jeon", "phd", None, GA, near="Students"),
        M("Ankush Jain", "phd", None, GA, near="Students", note="listed since the 2020 capture"),
        M("Hojin Park", "phd", None, GA, near="Past students:", note="with Greg Ganger; now Meta"),
        M("Michael Kuchnik", "phd", None, GA, near="Past students:", note="with Virginia Smith; now Meta FAIR"),
        M("Qing Zheng", "phd", None, GA, near="Past students:", note="with Garth Gibson; now LANL"),
        M("Abutalib Aghayev", "phd", None, GA, near="Past students:", note="now Penn State faculty"),
    ],
    pubs=[PUB("http://users.ece.cmu.edu/~gamvrosi/publications.html", mode="auto")],
    notes=("PI homepage (cs.cmu.edu/~gamvrosi -> users.ece.cmu.edu/~gamvrosi) has a Students / Past students list; "
           "CSD profile links only to the Parallel Data Lab (shared center, not his group page). 2020 and 2023 "
           "captures add nobody new (no capture before 2018). Students are listed without roles; all are PhD "
           "students per their co-advising notes."),
    blocked=[],
)

# ---------------------------------------------------------------- David Andersen
DGA = "http://www.cs.cmu.edu/~dga/"
D["David Andersen"] = dict(
    lab_site=DGA,
    people_page=None,
    people_pages=[DGA + "students.html"],
    members=[],
    pubs=[PUB(DGA + "papers/index.html", mode="auto")],
    notes=("PI homepage (cs.cmu.edu/~dga) lists no group members; students.html is a 'Potential Students' notice "
           "(identical text in live page and the 2017 and 2020 Wayback captures, last updated 2012) with no student "
           "list; CSD profile has no advisee list; the 2016 blog post is unrelated. Group code is on GitHub "
           "(efficient), not a people page. Papers index parsed with auto mode (104 entries, 9 in window, 2 missing)."),
    blocked=[],
)

# ---------------------------------------------------------------- Dimitrios S Apostolopoulos
RIA = "https://www.ri.cmu.edu/ri-faculty/dimitrios-dimi-apostolopoulos/"
D["Dimitrios S Apostolopoulos"] = dict(
    lab_site=None,
    people_page=RIA,
    people_pages=[RIA],
    members=[
        M("Robert J. Engel", "staff", None, RIA, near="current affiliates", note="RI profile current affiliate (NREC)"),
        M("Matthew Glisson", "staff", None, RIA, near="current affiliates", note="RI profile current affiliate (NREC)"),
        M("David Norton", "staff", None, RIA, near="current affiliates", note="RI profile current affiliate (NREC)"),
        M("Stephen Novick", "staff", None, RIA, near="current affiliates", note="RI profile current affiliate (NREC)"),
        M("Greg Paff", "staff", None, RIA, near="current affiliates", note="RI profile current affiliate (NREC)"),
        M("Richard Pantaleo", "staff", None, RIA, near="current affiliates", note="RI profile current affiliate (NREC)"),
        M("Graham Papciak", "staff", None, RIA, near="current affiliates", note="RI profile current affiliate (NREC)"),
        M("Douglas Rakoczy", "staff", None, RIA, near="current affiliates", note="RI profile current affiliate (NREC)"),
        M("Gary Russell", "staff", None, RIA, near="current affiliates", note="RI profile current affiliate (NREC)"),
        M("Stephen D. Scott", "staff", None, RIA, near="current affiliates", note="RI profile current affiliate (NREC)"),
        M("Douglas Soxman", "staff", None, RIA, near="current affiliates", note="RI profile current affiliate (NREC)"),
        M("Hannah D. Lyness", "phd", None, RIA, near="past phd students", note="undated past PhD student on live profile"),
        M("Gregory Colvin", "masters", None, RIA, near="past masters students", note="undated past master's student on live profile"),
    ],
    pubs=[],
    notes=("No lab site: the old ri.cmu.edu/people/apostolopoulos URL 404s; the live RI faculty profile "
           "(ri-faculty/dimitrios-dimi-apostolopoulos) lists 11 'current affiliates' (NREC project staff, role not "
           "stated, recorded as staff), past PhD student Hannah D. Lyness and past master's students Gregory Colvin, "
           "Nick Miller and David D. Wilkinson (all undated; only the two already-held ones recorded, Miller and "
           "Wilkinson skipped as undated alumni). The profile shows 47 publications from the RI database but there "
           "is no separate publications page to parse. Wayback not needed/consulted."),
    blocked=[],
)

# ---------------------------------------------------------------- Akari Asai
AG = "https://akariasai.github.io/group/"
D["Akari Asai"] = dict(
    lab_site="https://akariasai.github.io/",
    people_page=AG,
    people_pages=[AG],
    members=[
        M("Abhinav Java", "phd", None, AG, near="Students"),
        M("Zhengliang Shi", "phd", [2027, None], AG, near="Students", note="CMU LTI PhD from Spring 2027, with Yiming Yang"),
        M("Xueqiao Sun", "phd", None, AG, near="Students", note="with Graham Neubig"),
        M("Zijian (Steven) Chen", "undergraduate", None, AG, near="Students", note="AI2 intern; University of Waterloo undergraduate (not CMU), listed as group student"),
        M("Saee Patil", "masters", None, AG, near="Students"),
        M("Harry Hu", "undergraduate", None, AG, near="Students"),
    ],
    pubs=[PUB("https://akariasai.github.io/publications/", mode="li")],
    notes=("Personal group page lists six students (live only; the page has no Wayback captures per cdx and Wayback "
           "was not needed for a 2025+ group). Close collaborators Rulin Shao (UW) and Seungone Kim (CMU LTI, "
           "advised by Welleck/Neubig) are listed as collaborators, not members, and skipped. Zijian Chen is a "
           "Waterloo undergraduate and Zhengliang Shi starts Spring 2027; both included as stated on the page. "
           "Publications use li mode (the default first-sentence mode extracts abstracts)."),
    blocked=[],
)

# ---------------------------------------------------------------- Chris Atkeson
CS = "https://www.cs.cmu.edu/~cga/students.html"
D["Chris Atkeson"] = dict(
    lab_site="https://www.cs.cmu.edu/~cga/",
    people_page=CS,
    people_pages=[CS],
    members=[
        M("Alisa Allaire", "phd", None, CS, near="Current Students"),
        M("Arkadeep Narayan Chaudhury", "phd", None, CS, near="Current Students"),
        M("Mrinal Verghese", "phd", None, CS, near="Current Students"),
        M("Chiheb Boussema", "phd", None, CS, near="Current Students"),
        M("Sunyu Wang", "phd", None, CS, near="Current Students"),
    ],
    pubs=[PUB("https://www.cs.cmu.edu/~cga/publications.html", mode="auto")],
    notes=("PI homepage links Students page with Current Students (5) and an undated Alumni list; Wayback CDX was "
           "refused (connection refused) so no historical captures could be read. Undated alumni (Akshara Rai, "
           "Siyuan Feng, Xinjilefu, Jiuguang Wang, Joohyung Kim, Scott Niekum, Sid Sanan, Eric Whitman, Ben Stephens, "
           "Chenggang Liu, Martin Stolle, Mike Stilman, etc.) not recorded as they cannot be placed in 2016-2026 from "
           "this page; several are already held. Publications page auto mode finds few dated entries (3 in window, "
           "30 undated)."),
    blocked=[],
)
