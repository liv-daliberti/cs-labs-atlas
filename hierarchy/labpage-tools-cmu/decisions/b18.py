from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Heather Miller
HM = "https://heather.miller.am/"
H19 = WB + "20190106152155id_/https://heather.miller.am/"
H21 = WB + "20210225024156id_/https://heather.miller.am/"
H23 = WB + "20230127165729id_/https://heather.miller.am/"
D["Heather Miller"] = dict(
    lab_site=HM,
    people_page=HM,
    people_pages=[HM, H19, H21, H23],
    members=[
        M("Christopher Meiklejohn", "phd", None, HM, q="CMU Team Christopher Meiklejohn , PhD Student"),
        M("Matthew Weidner", "phd", None, HM, q="Matthew Weidner , PhD Student"),
        M("Huairui Qui", "masters", None, HM, q="Huairui Qui , MS Student"),
        M("Ria Pradeep", "undergraduate", None, HM, q="Ria Pradeep , Undergrad"),
        M("Luke Dramko", "undergraduate", None, HM, q="Luke Dramko, Undergraduate/REU Student"),
        M("Kevin Clancy", "phd", None, H19, q="CMU Team Kevin Clancy , PhD Student"),
        M("Zeeshan Lakhani", "phd", None, H19, q="Christopher Meiklejohn , PhD Student Zeeshan Lakhani , PhD Student"),
    ],
    pubs=[],
    notes="PI homepage heather.miller.am 'CMU Team' list, live plus Wayback captures 2019, 2021 and 2023 (2019 adds Clancy and Lakhani; 2021 and 2023 match the live list; the department profile lists Siyuan Chen as advisee but the homepage does not). Publications page parses to 1 entry only (the book), so not added; the PI's full list is not on the site.",
    blocked=[],
)

# ---------------------------------------------------------------- Louis-Philippe Morency
MC = "https://multicomp.cs.cmu.edu/people/"
M20 = WB + "20200930044620id_/http://multicomp.cs.cmu.edu/people/"
M23 = WB + "20230128055239id_/http://multicomp.cs.cmu.edu/people/"
D["Louis-Philippe Morency"] = dict(
    lab_site="https://multicomp.cs.cmu.edu/",
    people_page=MC,
    people_pages=[MC, M20, M23],
    members=[
        M('Gaoussou Youssouf Kebe', 'phd', [2020, None], MC, q='Gaoussou Youssouf Kebe Gaoussou Youssouf Kebe Personal Website Google Scholar Youssouf Kebe'),
        M('Leena Mathur', 'phd', None, MC, q='Leena Mathur Leena Mathur Personal Website Google Scholar Leena Mathur is a PhD'),
        M('Alex Wilf', 'phd', None, MC, q='Alex Wilf Alex Wilf Personal Website Google Scholar Alex Wilf is a doctoral'),
        M('Martin Q. Ma', 'phd', None, MC, q='Martin Q. Ma Martin Q. Ma Personal Website Google Scholar LinkedIn Martin Q. Ma'),
        M('Paul Pu Liang', 'phd', None, MC, q='Paul Pu Liang Paul Pu Liang Personal Website Google Scholar Paul is Ph.D. student'),
        M('Victoria Lin', 'phd', None, MC, q='Victoria Lin Victoria Lin Google Scholar LinkedIn Victoria is a Ph.D. student in'),
        M('Torsten Wörtwein', 'phd', None, MC, q='Torsten Wörtwein Torsten Wörtwein Personal Website Google Scholar LinkedIn Torsten'),
        M('Alexandria Vail', 'phd', None, MC, q='Alexandria Vail Alexandria Vail Personal Website Alexandria K. Vail is a Ph.D.'),
        M('Santiago Benoit', 'masters', None, MC, q='Santiago Benoit Santiago Benoit LinkedIn Santiago Benoit is an MS student in LTI who'),
        M('Bhaavanaa Thumu', 'masters', None, MC, q='Bhaavanaa Thumu Personal Website Bhaavanaa Thumu is a MS student pursuing a Master’s'),
        M('Nihal Jain', 'masters', None, MC, q='Nihal Jain Personal Website Nihal Jain is a Master’s in Machine Learning'),
        M('Sheryl Mathew', 'undergraduate', None, MC, q='Sheryl Mathew Sheryl Mathew is an undergraduate computer science student at CMU.'),
        M('Michal Muszynski', 'postdoc', None, M20, q='Michal Muszynski Michal Muszynski Personal Website Google Scholar Michal Muszynski is'),
        M('Chaitanya Ahuja', 'phd', None, M20, q='Chaitanya Ahuja Chaitanya Ahuja Personal Website Chaitanya Ahuja is a doctoral'),
        M('Volkan Cirik', 'phd', None, M20, q='Volkan Cirik Volkan Cirik Personal Website Volkan is a doctoral student in'),
        M('Yao-Hung Hubert Tsai', 'phd', None, M20, q='Yao-Hung Hubert Tsai Yao-Hung Hubert Tsai Personal Website Google Scholar Hubert is a'),
        M('Amir Zadeh', 'phd', None, M20, q='Amir Zadeh Amir Zadeh Personal Website Amir Zadeh is an Artificial Intelligence'),
        M('Ryo Ishii', 'visitor', None, M20, q='Ryo Ishii Ryo Ishii Personal Website Google Scholar LinkedIn Ryo Ishii is a'),
        M('Nicki Siverling', 'staff', None, M20, q='Nicki Siverling Nicki Siverling Nicki is the MultiComp Lab’s Coordinator. She has 12'),
        M('Atabak Ashfaq', 'masters', None, M20, q='Atabak Ashfaq LinkedIn Atabak Ashfaq is a first-year Masters student at the'),
        M('Sharath Rao', 'masters', None, M20, q='Sharath Rao LinkedIn Sharath is a second-year master’s student in the Electrical'),
        M('Peter Wu', 'masters', None, M20, q='Peter Wu Personal Website Google Scholar LinkedIn Peter is a Masters student'),
        M('Jianing “Jed” Yang', 'masters', None, M20, q='Jianing “Jed” Yang Personal Website Jianing “Jed” Yang is a second-year Master’s'),
        M('Shreya Bali', 'undergraduate', None, M20, q='Shreya Bali Shreya is a senior in the Carnegie Mellon School of Computer'),
        M('Katrina Jiao', 'undergraduate', None, M20, q='Katrina Jiao Katrina is an undergraduate student in Computer Science. Her'),
        M('Dong Won Lee', 'undergraduate', None, M20, q='Dong Won Lee Don is a undergraduate student in Carnegie Mellon University'),
        M('Azaan Rehman', 'undergraduate', None, M20, q='Azaan Rehman Azaan is in his senior year as a Computer Science Undergraduate. His'),
        M('Yiwei Lyu', 'masters', None, M23, q='Yiwei Lyu Yiwei Lyu Google Scholar Yiwei Lyu is a Master’s student in Machine'),
        M('Taylor Gautreaux', 'staff', None, M23, q='Taylor Gautreaux Taylor Gautreaux Taylor is a research associate in the MultiComp'),
        M('Yinghuan Zhang', 'masters', None, M23, q='Yinghuan Zhang Yinghuan is a graduate student in Master of Information Technology'),
        M('Sanika Natu', 'masters', None, M23, q='Sanika Natu Sanika Natu is a Master’s student in the School of Computer Science'),
        M('Yuxin Xiao', 'masters', None, M23, q='Yuxin Xiao Personal Website Yuxin Xiao is a Machine Learning Master student at'),
        M('Blake Martin', 'masters', None, M23, q='Blake Martin Personal Website Blake is a master’s student in Machine Learning.'),
        M('Pratik Joshi', 'masters', None, M23, q='Pratik Joshi Personal Website Google Scholar Pratik Joshi is a Master’s student'),
        M('Catherine Cheng', 'masters', None, M23, q='Catherine Cheng Catherine Cheng is a Master’s student in Machine Learning'),
        M('Aneesha Sampath', 'undergraduate', None, M23, q='Aneesha Sampath Aneesha is an undergraduate student at Carnegie Mellon University'),
        M('Shuyu Zhang', 'undergraduate', None, M23, q='Shuyu Zhang Shuyu Zhang is an undergraduate in the BXA program studying computer'),
        M('Edward Garemo', 'undergraduate', None, M23, q='Edward Garemo Edward Garemo is an undergraduate student in SCS studying computer'),
        M('Evan Zhang', 'undergraduate', None, M23, q='Evan Zhang Hi, I’m Evan! I’m currently a freshman in SCS and plan on'),
        M('Arvin Wu', 'undergraduate', None, M23, q='Arvin Wu Arvin is an undergraduate computer science student at CMU. He is'),
    ],
    pubs=[PUB("https://multicomp.cs.cmu.edu/publications/", mode="auto")],
    notes="Live people page plus 2020 and 2023 Wayback captures of /people/. The live 'Previous Members' page (people/previous-members/) lists ~35 undated alumni; only those also seen as current in the 2020/2023 captures are recorded. Undated and not seen in a capture (skipped): Jeffrey Girard, Elif Bozkurt, Tadas Baltrusaitis (postdocs), Vasu Sharma, Hongliang Yu, Muqiao Yang, TJ Ma, Tejas Srinivasan, Zeeshan Ashraf, Chengfeng Mao, Qingtao Hu, Anirudha Rayasam, Navya Yarrabelly. Earliest Wayback capture of the people page is 2020, so 2016-2019 members rest on the previous-members list only.",
    blocked=[],
)

# ---------------------------------------------------------------- David R. Mortensen
CL = "https://changelinglab.github.io/people/"
C24 = WB + "20240922022730id_/https://changelinglab.github.io/people/"
C25 = WB + "20250512144312id_/https://changelinglab.github.io/people/"
D["David R. Mortensen"] = dict(
    lab_site="https://changelinglab.github.io/",
    people_page=CL,
    people_pages=[CL, C24, C25],
    members=[
        M('Shikhar Bharadwaj', 'phd', None, CL, q='Shikhar Bharadwaj PhD Student Shikhar Bharadwaj is a third year'),
        M('Chin-Jou Li', 'phd', None, CL, q='Chin-Jou Li PhD Student Chin-Jou Li is a first year LTI PhD'),
        M('Atharva Naik', 'phd', None, CL, q='Atharva Naik PhD Student Atharva Naik is a PhD student'),
        M('John Ternullo', 'masters', None, CL, q='John Ternullo 5LT Student John Ternullo is a student in the Fifth Year'),
        M('Thomas Pei', 'masters', None, CL, q="Thomas Pei Master's Student Thomas Pei is a first-year Data Science"),
        M('Ivan Zhang', 'undergraduate', None, CL, q='Ivan Zhang SCS Undergrad Ivan Zhang is an undergraduate student in'),
        M('Daniel Xu', 'undergraduate', None, CL, q='Daniel Xu Linguistics Undergrad Daniel (Chengmin) Xu is an'),
        M('Eugene Hwang', 'undergraduate', None, CL, q='Eugene Hwang Information Systems Undergrad Eugene Hwang is a sophomore'),
        M('Rithvik Senthil', 'masters', [2025, 2025], CL, q='Rithvik Senthil 2025 MCDS alumni, LTI Based out of Seattle,'),
        M('Brendon Boldt', 'phd', None, C24, q='Brendon Boldt PhD Student office number 5000 Forbes Ave Pittsburgh, PA'),
        M('Kwanghee Choi', 'masters', None, C24, q="Kwanghee Choi Master's Student (joint with WAVLab) Kwanghee Choi is a"),
        M('Liang (Leon) Lu', 'undergraduate', None, C24, q='Liang (Leon) Lu Undergraduate Student Leon (or Liang) Lu is an'),
        M('Kalvin Chang', 'visitor', None, C24, q='Kalvin Chang Visitor (joint with WAVLab) Kalvin Chang worked with David'),
        M('Eunjung Yeo', 'visitor', None, C24, q='Eunjung Yeo Visitor Eunjung Yeo recently completed her Ph.D. in'),
        M('Haeji Jung', 'visitor', None, C24, q='Haeji Jung Visitor Haeji Jung earned her Master’s degree in Computer'),
        M('Ting Chen', 'undergraduate', None, C25, q='Ting Chen Undergraduate Student Ting Chen is an undergraduate in'),
    ],
    pubs=[PUB("https://changelinglab.github.io/publications/", mode="auto")],
    notes="ChangeLing Lab people page (live). Its Alumni section (2 PhD, 13 MS/undergrad, visitors) is undated and the only captures are 2024-2026, and those not seen as current there are skipped; 2024 and 2025 captures add Boldt, Choi, L. Lu, K. Chang, Yeo, Jung, T. Chen (Maria Ryskina, K. Zhang, N. Anderson, X. Zhang, C. Cui, Y. Kim, Y. Feng, A. Cai, K. Xu, L. Lu, T. Chen, N. Robinson). Collaborators (Weissweiler, Yeo, Jung, Kim) and remote collaborator Sadhana Panthi are external, skipped.",
    blocked=[],
)

# ---------------------------------------------------------------- Todd Mowry
TM = "https://www.toddcmowry.org/new-page-1"
T19 = WB + "20190721105352id_/https://www.toddcmowry.org/new-page-1"
D["Todd Mowry"] = dict(
    lab_site="https://www.toddcmowry.org/",
    people_page=TM,
    people_pages=[TM, "https://www.toddcmowry.org/new-page-1-2", T19],
    members=[
        M("PRATIK FEGADE", "phd", None, TM, s="Ph.D. Students: Current", e="PRATIK FEGADE"),
        M("SAM ARCH", "phd", None, TM, s="Ph.D. Students: Current", e="SAM ARCH"),
        M("HONGYI JIN", "phd", None, TM, s="Ph.D. Students: Current", e="HONGYI JIN"),
        M("ZIQI WANG", "phd", None, TM, s="Ph.D. Students: Current", e="ZIQI WANG"),
        M("RUIHANG LAI", "phd", None, TM, s="Ph.D. Students: Current", e="RUIHANG LAI"),
        M("PATRICK COPPOCK", "phd", None, TM, s="Ph.D. Students: Current", e="PATRICK COPPOCK"),
        M("Chris Fallin", "phd", None, T19, s="Current Ph.D. students", e="Chris Fallin"),
        M("Prashanth Menon", "phd", None, T19, s="Current Ph.D. students", e="Prashanth Menon"),
        M("Dominic Chen", "phd", None, T19, s="Current Ph.D. students", e="Dominic Chen"),
    ],
    pubs=[PUB("https://www.toddcmowry.org/publications-1", mode="auto")],
    notes="Live Current PhD Students page (6 students; 5 more from the 2019 capture). The Alumni page (14 PhDs with thesis titles, no years) is undated, so alumni are skipped; one Wayback capture of the Current page (2019-07) adds Fallin, Menon and Chen; a 2022 capture lists only Menon, Fegade, Wang (not re-recorded). Publications page parses 75 entries (6 in window), many selected only.",
    blocked=[],
)

# ---------------------------------------------------------------- Tom Mitchell
TS = "https://www.cs.cmu.edu/~tom/TomMitchell_PhDstudents.htm"
D["Tom Mitchell"] = dict(
    lab_site="https://www.cs.cmu.edu/~tom/",
    people_page=TS,
    people_pages=[TS],
    members=[
        M("Yue Wu", "phd", None, TS, q="Current PhD Students: Yue Wu Machine Learning Department"),
        M("Robin Schmucker", "phd", [None, 2024], TS, q="Robin Schmucker, 2024"),
        M("Abulhair Saparov", "phd", [None, 2022], TS, q="Abulhair Saparov, 2022"),
        M("Otilia Strecu", "phd", [None, 2021], TS, q="Otilia Strecu, 2021"),
        M("Mariya Toneva", "phd", [None, 2021], TS, q="Mariya Toneva, 2021"),
        M("Anthony Platanios", "phd", [None, 2020], TS, q="Anthony Platanios, 2020"),
        M("Dan Schwartz", "phd", [None, 2020], TS, q="Dan Schwartz, 2020"),
        M("Nicole Rafidi", "phd", [None, 2018], TS, q="Nicole Rafidi, 2018"),
        M("Shashank Srivastava", "phd", [None, 2018], TS, q="Shashank Srivastava, 2018"),
        M("Derry Wijaya", "phd", [None, 2016], TS, q="Derry Wijaya, 2016"),
    ],
    pubs=[PUB("https://www.cs.cmu.edu/~tom/publications.html", mode="auto")],
    notes="Students page lists former PhDs with defense years; recorded those 2016+ (2015 and earlier skipped: Wehbe, Krishnamurthy, Fyshe, Gardner and older). Former postdocs/visitors list is undated (Jat, Labutov, Yang, Nakashole, Azaria, Talukdar, Ritter, Settles...) so skipped. Stanford Digital Economy Lab is a separate visiting affiliation.",
    blocked=[],
)
# ---------------------------------------------------------------- Onur Mutlu
SA = "https://safari.ethz.ch/safari-alumni/"
D["Onur Mutlu"] = dict(
    lab_site="https://safari.ethz.ch/",
    people_page=SA,
    people_pages=[SA, "https://safari.ethz.ch/group-members/"],
    members=[
        M('Amirali Boroumand', 'phd', [None, 2020], SA, q='Amirali Boroumand , December 2020 (defended 17 November 2020)'),
        M('Jeremie Kim', 'phd', [None, 2020], SA, q='Jeremie Kim , August 2020 (defended 13 July 2020)'),
        M('Nandita Vijaykumar', 'phd', [None, 2019], SA, q='Nandita Vijaykumar , December 2019 (defended 11 October 2019)'),
        M('Kevin Hsieh', 'phd', [None, 2019], SA, q='Kevin Hsieh , October 2019 (defended 5 September 2019)'),
        M('Justin Meza', 'phd', [None, 2019], SA, q='Justin Meza , May 2019 (defended December 2018). Thesis'),
        M('Yixin Luo', 'phd', [None, 2018], SA, q='Yixin Luo , May 2018 (defended February 2018). Thesis'),
        M('Kevin Chang', 'phd', [None, 2017], SA, q='Kevin Chang , May 2017 (defended May 2017). Thesis'),
        M('Rachata Ausavarungnirun', 'phd', [None, 2019], SA, q='Rachata Ausavarungnirun , May 2017 (defended May 2017). Thesis'),
        M('Gennady Pekhimenko', 'phd', [None, 2016], SA, q='Gennady Pekhimenko , August 2016 (defended July 2016). Thesis'),
        M('Vivek Seshadri', 'phd', [None, 2016], SA, q='Vivek Seshadri , May 2016 (defended April 2016). Thesis'),
        M('Donghyuk Lee', 'phd', [None, 2016], SA, q='Donghyuk Lee , May 2016 (defended December 2015). Thesis'),
        M('Abhijith Kashyap', 'masters', [None, 2016], SA, q='Abhijith Kashyap: M.S. ECE, May 2016. Jamie Liu: M.S.'),
        M("Saugata Ghose", "postdoc", [2014, 2021], SA, q="Post-Doc Alumni Samira Khan , September 2015. Currently Assistant Professor at the University of Virginia. [ Job Talk Slides (pptx) (pdf) ] Saugata Ghose"),
    ],
    pubs=[PUB("https://people.inf.ethz.ch/omutlu/projects.htm", mode="auto")],
    notes="Onur Mutlu moved to ETH Zurich (SAFARI). The SAFARI alumni page (live) has a 'SAFARI at CMU Alumni' section and dated PhD defenses; recorded only CMU-placed people with 2016+ end dates: CMU PhD alumni defended 2016-2020 (Boroumand, Kim, Vijaykumar, Hsieh, Meza, Luo, Chang, Ausavarungnirun, Pekhimenko co-advised with Mowry, Seshadri, Lee), master's Kashyap (2016), postdoc Ghose (CMU 2014-2021). Skipped: Samira Khan (postdoc until 2015), Yoongu Kim and Lavanya Subramanian (2015), all ETH students, visitors and interns (2017+ listings are ETH). Current members page not read (ETH-only). Publications page is the PI's whole list (ETH + CMU), 525 entries.",
    blocked=[],
)

# ---------------------------------------------------------------- Dominik Moritz
TD = "https://dig.cmu.edu/team"
D["Dominik Moritz"] = dict(
    lab_site="https://dig.cmu.edu/",
    people_page=TD,
    people_pages=[TD],
    members=[
        M('Arpit Mathur', 'phd', None, TD, q='Arpit Mathur (PhD Student) Eric Mason (PhD'),
        M('Eric Mason', 'phd', None, TD, q='Eric Mason (PhD Student) Hwei-Shin Harriman'),
        M('Hwei-Shin Harriman', 'phd', None, TD, q='Hwei-Shin Harriman (PhD Student) Péter Ferenc'),
        M('Péter Ferenc Gyarmati', 'phd', None, TD, q='Péter Ferenc Gyarmati (Affiliated PhD Student) Esther'),
        M('Esther Suh', 'masters', None, TD, q='Esther Suh (Masters Student) Maggie Chen'),
        M('Maggie Chen', 'undergraduate', None, TD, q='Maggie Chen (Undergraduate Student) Udhirna'),
        M('Udhirna Krishnamurthy', 'undergraduate', None, TD, q='Udhirna Krishnamurthy (Undergraduate Student) Yuvvan'),
        M('Yuvvan Talreja', 'undergraduate', None, TD, q='Yuvvan Talreja (Undergraduate Student) Ziyong Ma'),
        M('Ziyong Ma', 'undergraduate', None, TD, q='Ziyong Ma (Undergraduate Student) Scott'),
        M('Scott Davidoff', 'visitor', None, TD, q='Scott Davidoff (Visiting Researcher) Seokweon'),
        M('Seokweon Jung', 'visitor', None, TD, q='Seokweon Jung (Visiting Researcher) PhD Alumni'),
        M('Katelyn Morrison', 'phd', [None, 2026], TD, q='Katelyn Morrison (2026) Frank Elavsky (2026)'),
        M('Frank Elavsky', 'phd', [None, 2026], TD, q='Frank Elavsky (2026) Will Epperson (2025)'),
        M('Will Epperson', 'phd', [None, 2025], TD, q='Will Epperson (2025) Venkat Sivaraman'),
        M('Venkat Sivaraman', 'phd', [None, 2025], TD, q='Venkat Sivaraman (2025) Ángel Alexander'),
        M('Ángel Alexander Cabrera', 'phd', [None, 2024], TD, q='Ángel Alexander Cabrera (2024) Past Members Pranav'),
        M('Pranav Manjunath', 'member', [None, 2026], TD, q='Pranav Manjunath (2026)'),
        M('Kyungjin (James) Kim', 'member', [None, 2026], TD, q='Kyungjin (James) Kim (2026)'),
        M('Daesung Kim', 'member', [None, 2026], TD, q='Daesung Kim (2026)'),
        M('Youli Chang', 'member', [None, 2025], TD, q='Youli Chang (2025)'),
        M('Unn Seo (Grace) Park', 'member', [None, 2025], TD, q='Unn Seo (Grace) Park (2025)'),
        M('Rui Sheng', 'member', [None, 2025], TD, q='Rui Sheng (2025)'),
        M('Rohit Chennamsetti', 'member', [None, 2025], TD, q='Rohit Chennamsetti (2025)'),
        M('Jessica Tong', 'member', [None, 2025], TD, q='Jessica Tong (2025)'),
        M('Eli Slothower', 'member', [None, 2025], TD, q='Eli Slothower (2025)'),
        M('Aidan Bradshaw', 'member', [None, 2025], TD, q='Aidan Bradshaw (2025)'),
        M('Zexuan (Zx) Li', 'member', [None, 2024], TD, q='Zexuan (Zx) Li (2024)'),
        M('Yuxiang Huang', 'member', [None, 2024], TD, q='Yuxiang Huang (2024)'),
        M('Yanwei Huang', 'member', [None, 2024], TD, q='Yanwei Huang (2024)'),
        M('Yanna Lin', 'member', [None, 2024], TD, q='Yanna Lin (2024)'),
        M('Violet Turri', 'member', [None, 2024], TD, q='Violet Turri (2024)'),
        M('Tom Wartmann', 'member', [None, 2024], TD, q='Tom Wartmann (2024)'),
        M('Qianou (Christina) Ma', 'member', [None, 2024], TD, q='Qianou (Christina) Ma (2024)'),
        M('Maggie Cai', 'member', [None, 2024], TD, q='Maggie Cai (2024)'),
        M('Katie Robinson', 'member', [None, 2024], TD, q='Katie Robinson (2024)'),
        M('Jordan Wheeler', 'member', [None, 2024], TD, q='Jordan Wheeler (2024)'),
        M('Erica Fu', 'member', [None, 2024], TD, q='Erica Fu (2024)'),
        M('Eli Kranjec', 'member', [None, 2024], TD, q='Eli Kranjec (2024)'),
        M('Donald Bertucci', 'member', [None, 2024], TD, q='Donald Bertucci (2024)'),
        M('Chloe Yan', 'member', [None, 2024], TD, q='Chloe Yan (2024)'),
        M('Zaynab A.', 'member', [None, 2023], TD, q='Zaynab A. (2023)'),
        M('Yejun (Ariel) Kwak', 'member', [None, 2023], TD, q='Yejun (Ariel) Kwak (2023)'),
        M('Vaishnavi Gorantla', 'member', [None, 2023], TD, q='Vaishnavi Gorantla (2023)'),
        M('Tianqi (Andy) Wu', 'member', [None, 2023], TD, q='Tianqi (Andy) Wu (2023)'),
        M('Syeda Sheherbano Rizvi', 'member', [None, 2023], TD, q='Syeda Sheherbano Rizvi (2023)'),
        M('Rohit Chougule', 'member', [None, 2023], TD, q='Rohit Chougule (2023)'),
        M('Michelle Feng', 'member', [None, 2023], TD, q='Michelle Feng (2023)'),
        M('Laura Wei', 'member', [None, 2023], TD, q='Laura Wei (2023)'),
        M('Lan Lyu', 'member', [None, 2023], TD, q='Lan Lyu (2023)'),
        M('Karim Benharrak', 'member', [None, 2023], TD, q='Karim Benharrak (2023)'),
        M('Crystal Li', 'member', [None, 2023], TD, q='Crystal Li (2023)'),
        M('Bruce Li', 'member', [None, 2023], TD, q='Bruce Li (2023)'),
        M('Yuzhe (Bryan) Lu', 'member', [None, 2022], TD, q='Yuzhe (Bryan) Lu (2022)'),
        M('Rithika Narayan', 'member', [None, 2022], TD, q='Rithika Narayan (2022)'),
        M('Mayank Jain', 'member', [None, 2022], TD, q='Mayank Jain (2022)'),
        M('Lukas Hermann', 'member', [None, 2022], TD, q='Lukas Hermann (2022)'),
        M('Kazi Jawad', 'member', [None, 2022], TD, q='Kazi Jawad (2022)'),
        M('Kan Sun', 'member', [None, 2022], TD, q='Kan Sun (2022)'),
        M('Francisco Maria Calisto', 'member', [None, 2022], TD, q='Francisco Maria Calisto (2022)'),
        M('Donghoon Shin', 'member', [None, 2022], TD, q='Donghoon Shin (2022)'),
        M('Carol (Xinyi) Zheng', 'member', [None, 2022], TD, q='Carol (Xinyi) Zheng (2022)'),
        M('Amanda Li', 'member', [None, 2022], TD, q='Amanda Li (2022)'),
        M('Ziyang Guo', 'member', [None, 2021], TD, q='Ziyang Guo (2021)'),
        M('Zhendong (Mike) Yuan', 'member', [None, 2021], TD, q='Zhendong (Mike) Yuan (2021)'),
        M('Yiwei Wu', 'member', [None, 2021], TD, q='Yiwei Wu (2021)'),
        M('Sachin Grover', 'member', [None, 2021], TD, q='Sachin Grover (2021)'),
        M('Nathan Jen', 'member', [None, 2021], TD, q='Nathan Jen (2021)'),
        M('Monica Chang', 'member', [None, 2021], TD, q='Monica Chang (2021)'),
        M('Marius Hogräfer', 'member', [None, 2021], TD, q='Marius Hogräfer (2021)'),
        M('Leijie Wang', 'member', [None, 2021], TD, q='Leijie Wang (2021)'),
        M('Zhirou (Jenny) Xin', 'member', [None, 2021], TD, q='Zhirou (Jenny) Xin (2021)'),
        M('Canzhou Qu', 'member', [None, 2021], TD, q='Canzhou Qu (2021)'),
        M('Andy Wilbourn', 'member', [None, 2021], TD, q='Andy Wilbourn (2021)'),
        M('Aditi Dhabalia', 'member', [None, 2021], TD, q='Aditi Dhabalia (2021)'),
        M('Abraham Druck', 'member', [None, 2021], TD, q='Abraham Druck (2021)'),
        M('Sujun Cheng', 'member', [None, 2020], TD, q='Sujun Cheng (2020)'),
        M('Shreya Manjunath', 'member', [None, 2020], TD, q='Shreya Manjunath (2020)'),
        M('Mia Manavalan', 'member', [None, 2020], TD, q='Mia Manavalan (2020)'),
        M('Jiachen (Lilian) Gong', 'member', [None, 2020], TD, q='Jiachen (Lilian) Gong (2020)'),
        M('Leila Huang', 'member', [None, 2020], TD, q='Leila Huang (2020)'),
        M('Laura Beth Fulton', 'member', [None, 2020], TD, q='Laura Beth Fulton (2020)'),
        M('Justine Cho', 'member', [None, 2020], TD, q='Justine Cho (2020)'),
        M('Ja Young Lee', 'member', [None, 2019], TD, q='Ja Young Lee (2019)'),
        M('Qian Wang', 'member', [None, 2019], TD, q='Qian Wang (2019)'),
        M('Olivia Zhang', 'member', [None, 2019], TD, q='Olivia Zhang (2019)'),
    ],
    pubs=[PUB("https://dig.cmu.edu/publications", mode="css:div.publication")],
    notes="CMU Data Interaction Group (co-led with Adam Perer; the Team page is not split by PI, so all non-faculty members are recorded). Past Members carry the year they left, recorded as [None, year]. Excluded: PIs Perer and Moritz, Sherry Tongshuang Wu (faculty, 2024), Hendrik Strobelt (external collaborator, 2021). Wayback not needed: the live page covers 2019-2026.",
    blocked=[],
)

# ---------------------------------------------------------------- Niloofar Mireshghallah
LL = "https://mireshghallah.github.io/looni-lab.html"
D["Niloofar Mireshghallah"] = dict(
    lab_site="https://mireshghallah.github.io/looni-lab.html",
    people_page=LL,
    people_pages=[LL, "https://lti.cmu.edu/people/faculty/mireshghallah-niloofar.html"],
    members=[
        M("Bill Watson", "phd", None, LL, s="PhD students", e="Bill Watson"),
        M("Xiaoyu (Nicholas) Wu", "phd", None, LL, s="PhD students", e="Xiaoyu (Nicholas) Wu"),
        M("Renfei Zhang", "phd", None, LL, s="PhD students", e="Renfei Zhang"),
        M("Kevin Han", "phd", None, LL, s="PhD students", e="Kevin Han"),
        M("Bhuvan Chandra Koduru", "masters", None, LL, s="Master's students", e="Bhuvan Chandra Koduru"),
        M("Medha Hira", "masters", None, LL, s="Master's students", e="Medha Hira"),
        M("Prachi Goyal", "masters", None, LL, s="Master's students", e="Prachi Goyal"),
        M("Nikitha Srikanth", "masters", None, LL, s="Master's students", e="Nikitha Srikanth"),
        M("Abhav Mehrotra", "masters", None, LL, s="Master's students", e="Abhav Mehrotra"),
        M("Karen Zhang", "masters", None, LL, s="Master's students", e="Karen Zhang"),
        M("Mohith Rajesh", "masters", None, LL, s="Master's students", e="Mohith Rajesh"),
        M("Prince Jha", "visitor", None, LL, s="Visiting & Collaborators", e="Prince Jha", note="listed under Visiting & Collaborators; may be external"),
        M("Anthony Hughes", "visitor", None, LL, s="Visiting & Collaborators", e="Anthony Hughes", note="listed under Visiting & Collaborators; may be external"),
        M("Suresh Raghu", "visitor", None, LL, s="Visiting & Collaborators", e="Suresh Raghu", note="listed under Visiting & Collaborators; may be external"),
    ],
    pubs=[PUB("https://mireshghallah.github.io/", mode="auto")],
    notes="Looni Lab page (Members section, Fall 2026) on the PI homepage. LTI profile says she begins as assistant professor Fall 2027 (incoming), only advisee William Watson there. No earlier captures; the lab is new. Collaborators (Sahar Abdelnabi etc.) external. Publications list is a selected list on the homepage.",
    blocked=[],
)

# ---------------------------------------------------------------- Teruko Mitamura
MI = "https://lti.cmu.edu/people/faculty/mitamura-teruko.html"
D["Teruko Mitamura"] = dict(
    lab_site="http://www.cs.cmu.edu/~teruko/",
    people_page=MI,
    people_pages=[MI, "http://www.cs.cmu.edu/~teruko/"],
    members=[
        M("Kimihiro Hasegawa", "phd", None, MI, q="Advisees Kimihiro Hasegawa"),
    ],
    pubs=[],
    notes="Her own homepage www.cs.cmu.edu/~teruko/ has no people or publications list and says it was last updated August 2015; JAVELIN/KANT project pages are external legacy links. The LTI profile lists one current advisee. No lab site exists; project pages not fetched.",
    blocked=[],
)

# ---------------------------------------------------------------- Stefan Mitsch
D["Stefan Mitsch"] = dict(
    lab_site="http://www.cs.cmu.edu/~smitsch/",
    people_page=None,
    people_pages=[],
    members=[],
    pubs=[PUB("http://www.cs.cmu.edu/~smitsch/publications.html", mode="auto")],
    notes="Senior Systems Scientist in the Logical Systems Lab (ls.cs.cmu.edu now redirects to logic.kastel.kit.edu, the lab of Andre Platzer who moved to KIT). His homepage (home, projects, courses, tools) lists no students or group members; searched homepage and projects page. The Logical Systems Lab has no CMU people page to read.",
    blocked=[],
)

# ---------------------------------------------------------------- Hosein Mohimani
W19 = WB + "20190103094805id_/http://mohimanilab.cbd.cmu.edu:80/members/"
W20 = WB + "20200108024834id_/http://mohimanilab.cbd.cmu.edu:80/members/"
W23 = WB + "20231001063925id_/http://mohimanilab.cbd.cmu.edu/members/"
D["Hosein Mohimani"] = dict(
    lab_site="http://mohimanilab.cbd.cmu.edu/",
    people_page=W23,
    people_pages=[W19, W20, W23],
    members=[
        M('Arash Gholami Davoodi', 'postdoc', [2018, 2021], W19, q='Arash Gholami Davoodi Postdoctoral Scholar Lane Fellow (9/2018 -) of'),
        M('Liu Cao', 'phd', None, W19, q='Liu Cao Graduate Student Ph.D. Candidate of Computational Biology'),
        M('Egor Scherbin', 'visitor', [None, 2019], W19, q='Egor Scherbin Undergraduate Researcher Bioinformatics, Graduation Year', note='undergraduate at HSE St Petersburg, apparently remote'),
        M('Mihir Mongia', 'phd', None, W20, q='Mihir Mongia Graduate Student Ph.D. Candidate of Computational Biology'),
        M('Anubhav Baweja', 'undergraduate', None, W20, q='Anubhav Baweja Undergraduate Student Bachelor’s of Science in'),
        M('Bahar Behsaz', 'staff', [2021, None], W23, q='Bahar Behsaz Project Scientist (01/2021-) Computational Biology School'),
        M('Mohsen Ferdosi', 'phd', None, W23, q='Mohsen Ferdosi Graduate Student Ph.D. Candidate of Computational Biology'),
        M('Mustafa Guler', 'phd', None, W23, q='Mustafa Guler Graduate Student Ph.D. Candidate of Computational Biology'),
        M('Donghui Yan', 'phd', None, W23, q='Donghui Yan Graduate Student Ph.D. Candidate of Computational Biology'),
        M('Chengze Shen', 'masters', None, W23, q='Chengze Shen Graduate Student M.S. in Computational Biology at Carnegie'),
        M('Yi-Yuan Lee', 'masters', None, W23, q='Yi-Yuan Lee Graduate Student M.S. in Computational Biology at Carnegie'),
        M('Haodong Liu', 'masters', None, W23, q='Haodong Liu Graduate Student M.S. in Computational Biology at Carnegie'),
        M('Romel Baral', 'masters', None, W23, q='Romel Baral Graduate Student M.S. in Computational Biology at Carnegie'),
        M('Neel Mittal', 'masters', None, W23, q='Neel Mittal Graduate Student M.S. in Computational Biology at Carnegie'),
        M('Zeyuan Zuo', 'masters', None, W23, q='Zeyuan Zuo Graduate Student M.S. in Computational Biology at Carnegie'),
        M('Ziyu Zhang', 'undergraduate', None, W23, q='Ziyu Zhang Undergraduate Student Computer Science Carnegie Mellon'),
        M('Aman Malik', 'undergraduate', None, W23, q='Aman Malik Undergraduate Student Biological Sciences Carnegie Mellon'),
        M('Sean Chang', 'undergraduate', None, W23, q='Sean Chang Undergraduate Student School of Computer Science Carnegie'),
        M('Yucheng Dai', 'undergraduate', None, W23, q='Yucheng Dai Undergraduate Student Computer Science Carnegie Mellon'),
    ],
    pubs=[PUB(WB + "20260416145831id_/http://mohimanilab.cbd.cmu.edu/publications/", mode="auto")],
    notes="Lab site is dead live (connection refused; PI moved to UCLA); used Wayback captures of /members/ from 2019, 2020 and 2023 (three-capture limit used; 2024-2026 captures not read, so later arrivals may be missing). Excluded: Andres Mauricio Caraballo (postdoc at UC San Diego, jointly mentored). Egor Scherbin is a remote undergraduate at HSE St Petersburg, recorded as visitor.",
    blocked=[],
)

# ---------------------------------------------------------------- Robert F Murphy
A25 = WB + "20250520125020id_/https://murphylab.web.cmu.edu/murphylab_info.html"
A17 = WB + "20170209231129id_/http://murphylab.web.cmu.edu:80/murphylab_info.html"
A20 = WB + "20200126201256id_/http://murphylab.web.cmu.edu:80/murphylab_info.html"
A22 = WB + "20220529081220id_/https://murphylab.web.cmu.edu/murphylab_info.html"
D["Robert F Murphy"] = dict(
    lab_site="https://murphylab.web.cmu.edu/",
    people_page=A25,
    people_pages=[A25, A17, A20, A22],
    members=[
        M('Gary Wilkins', 'phd', None, A25, q='Gary Wilkins, Biological Sciences Ph.D. Program'),
        M('Shiqiu Yu', 'masters', None, A25, q='M.S. Students Shiqiu Yu, Automated Science M.S. Program'),
        M('Ted Zhang', 'staff', None, A25, q='Staff Ted Zhang'),
        M('Jose Lugo-Martinez', 'postdoc', [2017, 2021], A25, q='Jose Lugo-Martinez (2017-2021) Assistant Professor, University'),
        M('Maja Temerinac-Ott', 'postdoc', [2013, 2016], A25, q='Maja Temerinac-Ott (University of Freiburg) (2013-2016)'),
        M('Huangqingbo (Paul) Sun', 'masters', [2021, 2024], A25, q='Huangqingbo (Paul) Sun, M.S., Automated Science, 2021; Ph.D., Computational'),
        M('Haoran Chen', 'phd', [None, 2023], A25, q='Haoran Chen, Ph.D., Computational Biology (2023) Senior'),
        M('Justin Hoffman', 'masters', [None, 2022], A25, q='Justin Hoffman, M.S., Automated Science (2022) Senior'),
        M('Aparna Kumar', 'phd', [None, 2021], A25, q='Aparna Kumar, Ph.D., Computational Biology (2021)'),
        M('Xiongtao Ruan', 'phd', [None, 2019], A25, q='Xiongtao Ruan, Ph.D., Computational Biology (2019)'),
        M('Sun Uk Kim', 'masters', [None, 2018], A25, q='Sun Uk Kim, M.S., Biomedical Engineering (2018)'),
        M('Jingyi Wang', 'masters', [None, 2017], A25, q='Jingyi Wang, M.S., Biomedical Engineering (2017)'),
        M('Timothy Majarian', 'masters', [None, 2017], A25, q='Timothy Majarian, M.S., Computational Biology (2017)'),
        M('Gregory R. Johnson', 'phd', [None, 2016], A25, q='Gregory R. Johnson, Ph.D., Computational Biology (2016)'),
        M('Kelvin Liu', 'phd', None, A17, q='Kelvin Liu, Joint CMU-Pitt Ph.D. program in Computational Biology'),
        M('Ivan Cao-Berg', 'staff', None, A17, q='Staff Ivan Cao-Berg'),
        M('Xin Lu', 'staff', None, A20, q='Staff Ivan Cao-Berg Xin Lu'),
        M('Serena Abraham', 'masters', None, A22, q='M.S. Students Serena Abraham'),
        M('Yashaswini Manjunath', 'masters', None, A22, s='M.S. Students', e='Yashaswini Manjunath'),

    ],
    pubs=[PUB(WB + "20251213043109id_/https://murphylab.web.cmu.edu/murphylab_pubs.html", mode="auto")],
    notes="Live murphylab.web.cmu.edu does not answer; read Wayback captures of murphylab_info.html (People section) from 2017, 2020, 2022 and 2025 (the 2025 one carries the dated Alumni lists). Skipped alumni ending before 2016 (Devin Sullivan 2015, Kangas, Buck, Naik and older) and the 2013-2016 postdoc Temerinac-Ott is kept (overlaps 2016). Collaborator lists on ResearchGate (Glory-Afshar, Cain, Roederer) not on the lab page. Publications page is an old-style list: only 5 in-window entries, all already held.",
    blocked=[],
)

