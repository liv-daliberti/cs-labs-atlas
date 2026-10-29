from dhelp import M, PUB, WB

D = {}

# ---------------------------------------------------------------- Aditi Raghunathan
AR_PEOPLE = "https://ar-forum.github.io/scripts/people.js"
AR_HOME23 = WB + "20230105152221id_/https://www.cs.cmu.edu/~aditirag/"
AR_HOME24 = WB + "20240205032222id_/https://www.cs.cmu.edu/~aditirag/"
def _ar(name, role, sec, note=None, years=None):
    if sec == "alumni":
        sec = "alumni: ["
    en = 'name:"%s"' % name if name == "Catherine Li" else 'name: "%s"' % name
    return M(name, role, years, AR_PEOPLE, s=sec, e=en, raw=True, note=note)
D["Aditi Raghunathan"] = dict(
    lab_site="https://ar-forum.github.io/",
    people_page=AR_PEOPLE,
    people_pages=[AR_PEOPLE, AR_HOME23],
    members=[
        _ar("Jacob Springer", "phd", "phdAdvisees"),
        _ar("Gaurav Ghosal", "phd", "phdAdvisees"),
        _ar("Chen Wu", "phd", "phdAdvisees"),
        _ar("Ziqian Zhong", "phd", "phdAdvisees"),
        _ar("Jingchu Gai", "phd", "phdAdvisees", note="co-advised with Andrej Risteski"),
        _ar("Lawrence Feng", "member", "extendedGroup", note="Extended group"),
        _ar("Shashwat Saxena", "member", "extendedGroup", note="Extended group"),
        _ar("Ishaan Watts", "member", "extendedGroup", note="Extended group"),
        _ar("Bryan Wang", "member", "extendedGroup", note="Extended group"),
        _ar("Catherine Li", "member", "extendedGroup", note="Extended group"),
        _ar("Sophia Sandholm", "member", "extendedGroup", note="Extended group"),
        _ar("Olina Mukherjee", "member", "extendedGroup", note="Extended group"),
        _ar("Christina Baek", "phd", "alumni", note="alumna: PhD at CMU, co-advised by Zico Kolter; also on the 2023 homepage as PhD student"),
        _ar("Sachin Goyal", "phd", "alumni", note="alumnus: PhD at CMU, advised by Zico Kolter"),
        _ar("Pratyush Maini", "phd", "alumni", note="alumnus: PhD at CMU, advised by Zico Kolter"),
        _ar("Taeyoun Kim", "masters", "alumni", note="alumnus: Masters at CMU"),
        _ar("Charles Ding", "undergraduate", "alumni", note="alumnus: Undergrad at CMU"),
        _ar("Suhas Kotha", "undergraduate", "alumni", note="alumnus: Undergrad at CMU"),
        _ar("Janet Hsieh", "undergraduate", "alumni", note="alumna: Undergrad at CMU, co-advised by Nihar Shah"),
        _ar("Aman Mehra", "masters", "alumni", note="alumnus: Masters at CMU"),
    ],
    pubs=[PUB(AR_HOME24, mode="auto", note="homepage 2024 capture lists Preprints + Publications; live homepage no longer lists papers")],
    notes="Group site ar-forum.github.io (A|Raghunathan Lab / FORUM) renders people from scripts/people.js (JS data, quoted raw). Recorded PhD advisees, extended group (7, role not stated -> member) and alumni who were at CMU (prevPosition CMU undergrad/masters/PhD; the alumni list is the CMU group, PI joined CMU 2021-22). Skipped as not-at-CMU: Tanishq Kumar (Harvard undergrad -> Stanford PhD), Erik Jones (Stanford undergrad -> Berkeley PhD) and Xingyu Dang (tagged 'collaborator'). Alumni carry no years. The new site has no Wayback captures of people.js; homepage 2023 capture lists PhD students Jacob Springer and Christina Baek only (already recorded). Publications: live homepage shows no paper list, so used the 2024 Wayback homepage capture (44 entries; 2025 capture could not be read because Wayback was in back-off).",
    blocked=[],
)

# ---------------------------------------------------------------- Deva Ramanan
DR = "http://www.cs.cmu.edu/~deva/"
D["Deva Ramanan"] = dict(
    lab_site=DR,
    people_page=DR,
    people_pages=[DR],
    members=[
        M("Sally (Chuhan) Chen", "phd", None, DR, near="Current group members", note="joint with Matt O'Toole"),
        M("Gautam Gare", "phd", None, DR, near="Current group members", note="joint with John Galeotti"),
        M("Jay Karhade", "phd", None, DR, near="Current group members", note="joint with Sebastian Scherer"),
        M("Nikhil Keetha", "phd", None, DR, near="Current group members", note="joint with Sebastian Scherer"),
        M("Ava Pun", "phd", None, DR, near="Current group members", note="joint with Jun-Yan Zhu"),
        M("Khiem Vuong", "phd", None, DR, near="Current group members", note="joint with Srinivas Narashiman"),
        M("Jacob Yeung", "phd", None, DR, near="Current group members", note="joint with Mike Tarr"),
        M("Zhiqiu Lin", "phd", [None, 2026], DR, q="Zhiqiu Lin Scalable Oversight Across Generative Visual AI: Toward Visual Storytelling for Everyone , 2026, Moodio", note="alumni list: thesis/graduation year 2026"),
        M("Neehar Peri", "phd", [None, 2026], DR, q="Neehar Peri Towards Scalable Open-World 3D Perception , 2026, Caltech", note="alumni list: thesis/graduation year 2026"),
        M("Erica Weng", "phd", [None, 2026], DR, q="Erica Weng A Layered Foundation for Reliable Trajectory Forecasting , 2026, Motional", note="alumni list: thesis/graduation year 2026"),
        M("Tarasha Khurana", "phd", [None, 2025], DR, q="Tarasha Khurana Towards 4D Perception with Foundational Priors , 2025, Tesla", note="alumni list: thesis/graduation year 2025"),
        M("Kangle Deng", "phd", [None, 2025], DR, q="Kangle Deng Learning to Create 3D Content: Geometry, Appearance, and Physics , 2025, Roblox", note="alumni list: thesis/graduation year 2025"),
        M("Nate Chodosh", "phd", [None, 2024], DR, q="Nate Chodosh Analysis by Synthesis for Modern Computer Vision , 2024, Villanova", note="alumni list: thesis/graduation year 2024"),
        M("Jason Zhang", "phd", [None, 2024], DR, q="Jason Zhang Sparse View 3D in the Wild , 2024, Google", note="alumni list: thesis/graduation year 2024"),
        M("Haithem Turki", "phd", [None, 2024], DR, q="Haithem Turki Towards City-Scale Neural Rendering , 2024, Nvidia", note="alumni list: thesis/graduation year 2024"),
        M("Gengshan Yang", "phd", [None, 2023], DR, q="Gengshan Yang Building 4D Models of Objects and Scenes from Monocular Videos , 2023, Meta", note="alumni list: thesis/graduation year 2023"),
        M("Martin Li", "phd", [None, 2022], DR, q="Martin Li Resource-Constrained Learning and Inference for Visual Perception , 2022, OpenAI", note="alumni list: thesis/graduation year 2022"),
        M("Peiyun Hu", "phd", [None, 2021], DR, q="Peiyun Hu Robust and Scalable Perception for Autonomy , 2021, Apple", note="alumni list: thesis/graduation year 2021"),
        M("Ravi Mullapudi", "phd", [None, 2021], DR, q="Ravi Mullapudi Dynamic Model Specialization for Efficient Inference, Training, and Supervision , 2021, OpenAI", note="alumni list: thesis/graduation year 2021"),
        M("Achal Dave", "phd", [None, 2021], DR, q="Achal Dave Open-World Object Detection and Tracking , 2021, Anthropic", note="alumni list: thesis/graduation year 2021"),
        M("Aayush Bansal", "phd", [None, 2020], DR, q="Aayush Bansal Unsupervised Learning of the 4D Audio-Visual World , 2020, Facebook Reality Labs", note="alumni list: thesis/graduation year 2020"),
        M("Rohit Girdhar", "phd", [None, 2019], DR, q="Rohit Girdhar Learning to Understand People via Local, Global, and Temporal Reasoning , 2019, Facebook AI", note="alumni list: thesis/graduation year 2019"),
        M("Phuc Nguyen", "phd", [None, 2018], DR, q="Phuc Nguyen Visual Recognition with Limited Annotations , 2018, Google", note="alumni list: thesis/graduation year 2018"),
        M("James Supancic", "phd", [None, 2017], DR, q="James Supancic Long-Term Tracking by Decision-Making , 2017, Blizzard", note="alumni list: thesis/graduation year 2017"),
        M("Zihan Wang", "masters", [None, 2026], DR, q="Zihan Wang Learning Humanoid Robots from Real2Sim2Real , 2026, Berkeley.", note="alumni list: thesis/graduation year 2026"),
        M("Kaihua Chen", "masters", [None, 2026], DR, q="Kaihua Chen 4D Understanding with Video Diffusion , 2026, Oxford.", note="alumni list: thesis/graduation year 2026"),
        M("Jeff Tan", "masters", [None, 2025], DR, q="Jeff Tan Differentiable 3D Reconstruction , 2025, Stanford.", note="alumni list: thesis/graduation year 2025"),
        M("Anish Madan", "masters", [None, 2024], DR, q="Anish Madan Automating Annotation Pipelines by Leveraging Multi-Modal Data , 2024, Skild.ai", note="alumni list: thesis/graduation year 2024"),
        M("Andrew Saba", "masters", [None, 2023], DR, q="Andrew Saba Development and Testing of a Software Stack for An Autonomous Racing Vehicle , 2023, Meta", note="alumni list: thesis/graduation year 2023"),
        M("Chonghyuk Song", "masters", [None, 2023], DR, q="Chonghyuk Song Total-Recon: Deformable Scene Reconstruction for Emboided View Synthesis , 2023, MIT", note="alumni list: thesis/graduation year 2023"),
        M("Chittesh Thavamani", "masters", [None, 2022], DR, q="Chittesh Thavamani Foveated Attention for Neural Nets , 2022, Nuro", note="alumni list: thesis/graduation year 2022"),
        M("Sean Cha", "masters", [None, 2020], DR, q="Sean Cha Retrieval-based Novel Activity Detection in Untrimmed Videos , 2020, Nvidia", note="alumni list: thesis/graduation year 2020"),
        M("Krishna Uppala", "masters", [None, 2020], DR, q="Krishna Uppala Exemplar-Free Video Retrieval , 2020, Apple", note="alumni list: thesis/graduation year 2020"),
        M("Aaron Huang", "masters", [None, 2020], DR, q="Aaron Huang End-to-End Methods for Autonomous Driving in Simulation , 2020, Zoox", note="alumni list: thesis/graduation year 2020"),
        M("Haochen Wang", "masters", [None, 2020], DR, q="Haochen Wang Audiovisual Ontology and Robust Representations via Cross-Modal Fusion , 2020, TTI-Chicago", note="alumni list: thesis/graduation year 2020"),
        M("Jessica Lee", "masters", [None, 2020], DR, q="Jessica Lee MetaPix: Few Shot Video Retargeting , 2020, UC Berkeley", note="alumni list: thesis/graduation year 2020"),
        M("William Qi", "masters", [None, 2020], DR, q="William Qi Representation Learning for Safe Autonomous Movement , 2020, Argo AI", note="alumni list: thesis/graduation year 2020"),
        M("Siva Mynepalli", "masters", [None, 2019], DR, q="Siva Mynepalli Recognizing Tiny Faces , 2019, Nimble Robotics", note="alumni list: thesis/graduation year 2019"),
        M("Ishan Nigam", "masters", [None, 2019], DR, q="Ishan Nigam Learning with Auxillary Supervision , 2019, UT Austin", note="alumni list: thesis/graduation year 2019"),
        M("Vivek Krishnan", "masters", [None, 2016], DR, q="Vivek Krishnan Tinkering under the Hood: Interactive Zero-Shot Learning with Net Surgery , 2016, Microsoft", note="alumni list: thesis/graduation year 2016"),
    ],
    pubs=[PUB("http://www.cs.cmu.edu/~deva/pubs.html", mode="auto")],
    notes="PI homepage lists current PhD students (7, several joint with other faculty) and dated alumni lists (PhD and Masters/undergraduate with thesis year and destination). Recorded current students and alumni with thesis year >= 2016. Skipped as before 2016: PhD alumni Mohsen Hejrati 2015, Dennis Park 2014, Xiangxin Zhu 2014, Yi Yang 2013, Chaitanya Desai 2012, Hamed Pirsiavash 2012; Masters Carl Vondrick 2011, Goutham Patnaik 2009. Nine undated alumni postdocs/visitors skipped (Arun Vasudevan, Jenny Seidenschwarz, Aljosa Osep, Jonathon Luiten, Pavel Tokmakov, Shu Kong, Chen Huang, Olga Russakovsky, Gregory Rogez). Page is dated through 2026 so no Wayback needed. Named co-advisors (Matt O'Toole, John Galeotti, Sebastian Scherer, Jun-Yan Zhu, Srinivas Narasimhan, Mike Tarr) are other faculty. Several held students (Mehar Khurana, Manu Gaur, Qi Wu, Zixin Guo, Lucky Kant Nayak) are not on the homepage.",
    blocked=[],
)

# ---------------------------------------------------------------- Aaditya Ramdas
RG = "http://web.stanford.edu/~aramdas/group.html"
RH = "http://web.stanford.edu/~aramdas/"
D["Aaditya Ramdas"] = dict(
    lab_site=RH,
    people_page=RG,
    people_pages=[RG],
    members=[
        M("James Leiner", "phd", None, RG, near="Post-proposal PhD students"),
        M("Hongjian Wang", "phd", None, RG, near="Post-proposal PhD students"),
        M("Diego Martinez-Taboada", "phd", None, RG, near="Post-proposal PhD students"),
        M("Ben Chugg", "phd", None, RG, near="Post-proposal PhD students"),
        M("Michael Wieck-Sosa", "phd", None, RG, near="Post-proposal PhD students"),
        M("Rohan Hore", "postdoc", None, RG, near="Pre-proposal PhD students and postdocs"),
        M("Hamish Flynn", "postdoc", None, RG, near="Pre-proposal PhD students and postdocs", note="co-hosted with M. Larsson"),
        M("Tomas Gonzalez Lara", "phd", None, RG, near="Pre-proposal PhD students and postdocs", note="with G. Fanti"),
        M("Sanjit Dandapanthula", "phd", None, RG, near="Pre-proposal PhD students and postdocs"),
        M("Ashwin Ram", "phd", None, RG, near="Pre-proposal PhD students and postdocs"),
        M("Leo Andeol", "visitor", [2025, 2025], RG, near="Long Visits", note="PhD student visiting Summer 2025 from Univ. Toulouse"),
        M("Aritra Ghosh", "visitor", [2025, 2025], RG, near="Long Visits", note="MS student visiting Summer 2025 from ISI India"),
        M("Swapnaneel Bhattacharya", "visitor", [2025, 2025], RG, near="Long Visits", note="MS student visiting Summer 2025 from ISI India"),
        M("Matteo Gasparin", "visitor", [2024, 2024], RG, near="Long Visits", note="PhD student visiting Spring+Fall 2024 from Univ. Padua"),
        M("Lasse Fischer", "visitor", [2024, 2024], RG, near="Long Visits", note="PhD student visiting Spring 2024 from Univ. Bremen"),
        M("Aytijhya Saha", "visitor", [2024, 2024], RG, near="Long Visits", note="MS student visiting Summer 2024 from ISI Kolkata"),
        M("Yusuf Sale", "visitor", [2024, 2024], RG, near="Long Visits", note="PhD student visiting Fall 2024 from LMU Munich"),
        M("Parnian Kassraie", "visitor", [2025, 2025], RG, near="Long Visits", note="PhD student visiting Spring 2025 from ETH Zurich"),
        M("Neil (Ziyu) Xu", "phd", [None, 2026], RG, q="Neil (Ziyu) Xu (PhD 2026, StatDS)"),
        M("Zhiyu Zhang", "postdoc", [None, 2025], RG, q="Zhiyu Zhang (postdoc 2025, StatDS)"),
        M("Ojash Neopane", "phd", [None, 2025], RG, q="Ojash Neopane (PhD 2025, MLD, + A. Singh)"),
        M("Shubhada Agrawal", "postdoc", [None, 2024], RG, q="Shubhada Agrawal (postdoc 2024, StatDS)"),
        M("Justin Whitehouse", "phd", [None, 2024], RG, q="Justin Whitehouse (PhD 2024, CSD, + S. Wu)"),
        M("Ian Waudby-Smith", "phd", [None, 2024], RG, q="Ian Waudby-Smith (PhD 2024, StatDS)"),
        M("Shubhanshu Shekhar", "postdoc", [2021, 2024], RG, q="Shubhanshu Shekhar (postdoc 2021-24, StatDS)"),
        M("Chirag Gupta", "phd", [None, 2023], RG, q="Chirag Gupta (PhD 2023, MLD)"),
        M("Sasha Podkopaev", "phd", [None, 2023], RG, q="Sasha Podkopaev (PhD 2023, StatDS+MLD)"),
        M("YJ Choe", "phd", [None, 2023], RG, q="YJ Choe (PhD 2023, StatDS+MLD)"),
        M("Aditya Gangrade", "postdoc", [2022, 2023], RG, q="Aditya Gangrade (postdoc 2022-23, StatDS, + A. Rinaldo)"),
        M("Robin Dunn", "phd", [None, 2021], RG, q="Robin Dunn (PhD 2021, StatDS, + L. Wasserman)"),
        M("Boyan Duan", "phd", [None, 2021], RG, q="Boyan Duan (PhD 2021, StatDS, + L. Wasserman)"),
        M("Jaehyok Shin", "phd", [None, 2020], RG, q="Jaehyok Shin (PhD 2020, StatDS, + A. Rinaldo)"),
        M("Eugene Katsevich", "postdoc", [2019, 2020], RG, q="Eugene Katsevich (postdoc 2019-20, StatDS, + K. Roeder)"),
        M("Asaf Weinstein", "postdoc", [2018, 2019], RG, q="Asaf Weinstein (postdoc 2018-19, StatDS, + M. Gavish)"),
    ],
    pubs=[PUB(RH, mode="auto", note="Stanford homepage of the PI (moved Fall 2026); lists all CMU-era papers")],
    notes="stat.cmu.edu/~aramdas now only says 'Moved to web.stanford.edu/~aramdas' (Ramdas moved permanently to Stanford, Fall 2026). The Stanford group page still lists the CMU group: post-/pre-proposal PhD students, postdocs, long visits (all 2024-2025, recorded as visitors), and 16 graduated mentees with years (all 2018 or later, all recorded). Co-advisors named (M. Larsson, G. Fanti, A. Singh, S. Wu, A. Rinaldo, L. Wasserman, K. Roeder, M. Gavish) are faculty and not recorded. The Pre-proposal list may now include students who moved with the PI to Stanford; they were recorded as listed (page does not say which institution). Pubs: auto mode on the PI homepage (parses bold titles; includes a few award lines as noise). Wayback not used (page gives dated lists).",
    blocked=[],
)

# ---------------------------------------------------------------- Steve James Rathje
SR = "https://www.hcii.cmu.edu/people/steve-rathje"
D["Steve James Rathje"] = dict(
    lab_site="https://stevenrathje.com/",
    people_page=SR,
    people_pages=[SR],
    members=[
        M("Kevin Hernandez", "phd", None, SR, near="Advisees"),
        M("Meryl Ye", "phd", None, SR, near="Advisees", note="listed as (S3D)"),
    ],
    pubs=[PUB("https://stevenrathje.com/publication/", mode="auto", note="PI site list; much of it predates CMU (PI joined CMU 2026)")],
    notes="The 'Psychology of Technology Lab' has no site of its own (WebSearch for one found nothing). Personal site stevenrathje.com has no group/people section; HCII profile lists two advisees (Kevin Hernandez, Meryl Ye). Rathje joined CMU in Fall 2026 from NYU (postdoc) so NYU/Cambridge people are out. moralunderstanding.com is a separate center page, not this PI's group. No Wayback used (no people page to look back at).",
    blocked=[],
)

# ---------------------------------------------------------------- R. Ravi
RV = "https://www.contrib.andrew.cmu.edu/~ravi/"
D["R. Ravi"] = dict(
    lab_site=RV,
    people_page=RV,
    people_pages=[RV],
    members=[
        M("Daniel Hathcock", "phd", None, RV, near="Current Ph. D. Students"),
        M("Aidin Niaparast", "phd", None, RV, near="Current Ph. D. Students"),
        M("Siyue Liu", "phd", None, RV, near="Current Ph. D. Students"),
        M("Weizhong Zhang", "phd", None, RV, near="Current Ph. D. Students"),
        M("Mik Zlatin", "postdoc", None, RV, near="Current postdoc"),
        M("Arda Antikacioglu", "phd", [None, 2017], RV, q="Arda Antikacioglu (Ph. D. 2017; First position: WorldQuant LLC)"),
        M("Jennifer Iglesias", "phd", [None, 2017], RV, q="Jennifer Iglesias (Ph. D. 2017; First position: Waymo)"),
        M("Jeremy Karp", "phd", [None, 2017], RV, q="Jeremy Karp (Ph. D. 2017; First position: Lyft)"),
        M("Stelios Despotakis", "phd", [None, 2018], RV, q="Stelios Despotakis (Ph. D. 2018; First position: City University of Hong Kong)"),
        M("Yang Jiao", "phd", [None, 2018], RV, q="Yang Jiao (Ph. D. 2018; First position: Boeing Corp)"),
        M("Arash Haddadan", "phd", [None, 2020], RV, q="Arash Haddadan (Ph. D. 2020; First position: Post-doctoral researcher at UVA Biocomplexity Institute)"),
        M("Da Qi Chen", "phd", [None, 2021], RV, q="Da Qi Chen (Ph. D. 2021; First position: Post-doctoral researcher at UVA Biocomplexity Institute)"),
        M("Oleksandr Rudenko", "phd", [None, 2022], RV, q="Oleksandr Rudenko (Ph. D. 2022; First position: Jane Street Capital)"),
        M("Su Jia", "phd", [None, 2022], RV, q="Su Jia (Ph. D. 2022; First position: Research Assistant Professor at Cornell University)"),
        M("D. Ellis Hershkowtiz", "phd", [None, 2022], RV, q="D. Ellis Hershkowtiz (Ph. D. 2022 - co-advised with Bernard Haeupler; First position: Post-doctoral researcher at ETH Zurich)", note="spelled as on page; co-advised with Bernhard Haeupler"),
        M("Daniel de Roux", "phd", [None, 2024], RV, q="Daniel de Roux (Ph. D. 2024; First position: Google)"),
        M("Thomas Bosman", "visitor", [2018, 2018], RV, q="Thomas Bosman (visiting doctoral student from Vrie University, 2018)"),
    ],
    pubs=[PUB(RV, mode="auto", note="homepage 'Research Papers' section (anchor entries); a few non-paper links parse as noise")],
    notes="Ravi's Tepper homepage (www.contrib.andrew.cmu.edu/~ravi/, updated April 2025) lists current PhD students, current postdoc, dated past PhD students and past visitors. Recorded current people, past PhDs with Ph.D. year >= 2017 and the 2018 visitor. Skipped as before 2016: 13 PhD alumni (1997-2012) plus M.Sc. Afshin Nikzad 2012, and visitors dated 2002-2012 (6). The csd.cmu.edu profile is only an affiliated-faculty stub with publications. No Wayback used (the page gives dated lists). Subhodeep Mitra (held) is not on the page.",
    blocked=[],
)

# ---------------------------------------------------------------- Matthew Johnson-Roberson
MJ = "https://droplab.ri.cmu.edu/people-1"
D["Matthew Johnson-Roberson"] = dict(
    lab_site="https://droplab.ri.cmu.edu/",
    people_page=MJ,
    people_pages=[MJ],
    members=[
        M("Weiming (William) Zhi", "postdoc", None, MJ, near="Post Docs"),
        M("Tianyi Zhang", "phd", None, MJ, near="Graduate Students"),
    ],
    pubs=[],
    notes="DROP Lab site droplab.ri.cmu.edu (live) lists one postdoc (William Zhi), one graduate student (Tianyi Zhang) and seven Lab Alumni (Jie Li, Katherine Skinner, Wonhui Kim, Ming-Yuan Yu, Gideon Billings, Corina Barbalata, Eduardo Iscar Ruland); the alumni are the Michigan-era DROP lab (PI joined CMU in 2022 from UMich; page does not place them at CMU) so they are excluded. Publications page only links to Google Scholar (nothing to parse). The RI faculty profile URL for this PI returns 404 on the RI site.",
    blocked=[],
)

# ---------------------------------------------------------------- Carolyn P Rose
CR = "https://cp3a.github.io/Teledia%20Team/"
_PH = "PhD and Research Masters Students"
_MI = "Masters of Intelligent Information Systems Advisees"
_ST = "Other Group Affiliates and Staff"
D["Carolyn P Rose"] = dict(
    lab_site="https://cp3a.github.io/",
    people_page=CR,
    people_pages=[CR],
    members=[
        M("Luke Breitfeller", "phd", None, CR, near=_PH),
        M("Ritam Dutt", "phd", None, CR, near=_PH),
        M("Yiqing Xie", "phd", None, CR, near=_PH),
        M("Atharva Naik", "phd", None, CR, near=_PH),
        M("Zhen Wu", "phd", None, CR, near=_PH),
        M("Mingqian Zheng", "phd", None, CR, near=_PH, note="co-advised with Maarten Sap"),
        M("Nachiket Kotalwar", "phd", None, CR, near=_PH),
        M("Doni Moon", "phd", None, CR, near=_PH, note="HCII PhD, co-advised with John Stamper"),
        M("Hyun Ryu", "visitor", None, CR, near=_PH, note="Visiting Masters student, co-advised with Sean Welleck"),
        M("Shubham Gandhi", "phd", None, CR, near=_PH, note="also listed under MIIS advisees"),
        M("Dhruv Gupta", "masters", None, CR, near=_MI),
        M("Keer Xu", "masters", None, CR, near=_MI),
        M("Gayathri Ganesh Lakshmy", "masters", None, CR, near=_MI),
        M("Manav Kapadnis", "masters", None, CR, near=_MI),
        M("Dhatchi Kunde Govindarajan", "masters", None, CR, near=_MI),
        M("Lawanya Baghel", "masters", None, CR, near=_MI),
        M("Jill Fain Lehman", "staff", None, CR, near=_ST, note="group affiliate/staff"),
        M("Chas Murray", "staff", None, CR, near=_ST),
        M("Eric Gonzalez", "staff", None, CR, near=_ST),
        M("Vicente Malave", "staff", None, CR, near=_ST),
        M("Annette Han", "staff", None, CR, near=_ST),
        M("Micah San Andres", "staff", None, CR, near=_ST),
    ],
    pubs=[],
    notes="PLACEHOLDER-REVISE",
    blocked=[],
)

# ---------------------------------------------------------------- Ronald Rosenfeld
RM = "https://www.ml.cmu.edu/people/bio/roni-rosenfeld/"
DT = "https://delphi.cmu.edu/about/team/"
D["Ronald Rosenfeld"] = dict(
    lab_site="https://delphi.cmu.edu/",
    people_page=RM,
    people_pages=[RM, DT],
    members=[
        M("Jingjing Tang", "postdoc", None, RM, near="Current postdocs and students", note="CompBio, epi-forecasting; listed under current postdocs and students (role as postdoc/student not stated)"),
        M("Ruiqi Lyu", "member", None, RM, near="Current postdocs and students", note="CompBio, epi-forecasting; listed under current postdocs and students"),
        M("Brian Clark", "member", None, DT, near="Core Members", note="Delphi core member (CMU-affiliated)"),
        M("Nat DeFries", "member", None, DT, near="Core Members", note="Delphi core member (CMU-affiliated)"),
        M("Erin Franke", "member", None, DT, near="Core Members", note="Delphi core member (CMU-affiliated)"),
        M("Nolan Gormley", "member", None, DT, near="Core Members", note="Delphi core member (CMU-affiliated)"),
        M("Oliver Hannaoui", "member", None, DT, near="Core Members", note="Delphi core member (CMU-affiliated)"),
        M("Minh Le", "member", None, DT, near="Core Members", note="Delphi core member (CMU-affiliated)"),
        M("Terry Ma", "member", None, DT, near="Core Members", note="Delphi core member (CMU-affiliated)"),
        M("Anna Rosengart", "member", None, DT, near="Core Members", note="Delphi core member (CMU-affiliated)"),
        M("Dmitry Shemetov", "member", None, DT, near="Core Members", note="Delphi core member (CMU-affiliated)"),
        M("Jingjing Tang", "phd", None, DT, near="Core Members", note="Delphi core member (CMU-affiliated)"),
        M("David Weber", "member", None, DT, near="Core Members", note="Delphi core member (CMU-affiliated)"),
        M("Christy Melucci", "staff", None, DT, near="Core Members", note="Delphi core member; MLD administrative assistant"),
        M("Tina Townes", "member", None, DT, near="Core Members", note="Delphi core member (CMU)"),
        M("Peter Jhon", "staff", None, DT, q="Peter Jhon CMU/MLD and OVPR Executive Director", note="Delphi executive director"),
        M("Adam Johns", "staff", None, DT, q="Adam Johns CMU/MLD Engineering Manager", note="Delphi engineering manager"),
        M("Addison Hu", "member", [2020, 2021], DT, q="Addison Hu CMU/Stat Core member, March 2020-August 2021", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Amartya Basu", "member", [2020, 2020], DT, q="Amartya Basu CMU/INI Intern, Summer 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Angel (Alex) Cabrera", "member", [2020, 2020], DT, q="Angel (Alex) Cabrera CMU/HCII Core member, March-April 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Zhuoran (Cheryl) Cheng", "member", [2021, 2021], DT, q="Zhuoran (Cheryl) Cheng CMU/ECE Intern, Summer 2021", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Aditya Chindhade", "member", [2022, 2022], DT, q="Aditya Chindhade CMU/Tepper Contributor, March-May 2022", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Eu Jing Chua", "member", [2020, 2021], DT, q="Eu Jing Chua CMU/MLD Intern, Summer 2020; Contributor, September 2020-May 2021", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("David Farrow", "member", [2012, 2020], DT, q="David Farrow Google Founding member, 2012-2016; Core member, March-April 2020; Google Fellow, October-December 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("EJ Fox", "member", [2020, 2020], DT, q="EJ Fox CMU/MLD Contributor, July-September 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Joseph Greene", "member", [2021, 2022], DT, q="Joseph Greene CMU/MLD Core member, September 2021-May 2022", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Shantanu Gupta", "member", [2020, 2020], DT, q="Shantanu Gupta CMU/MLD Contributor, April-May 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("George Haff", "member", [2020, 2026], DT, q="George Haff CMU/CSD Core member, June 2020-April 2026", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Robin Han", "member", [2020, 2020], DT, q="Robin Han CMU/HCII Intern, Summer 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Maria Jahja", "member", [2017, 2022], DT, q="Maria Jahja CMU/Stat Core member, August 2017-June 2022", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Kyungmin Kim", "member", [2021, 2021], DT, q="Kyungmin Kim CMU/CSD Intern, Fall 2021", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Andrew Kuznetsov", "member", [2020, 2020], DT, q="Andrew Kuznetsov CMU/HCII Core member, March-April 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Tara Lakdawala", "member", [2021, 2023], DT, q="Tara Lakdawala CMU/CSD Contributor, June-December 2021, September 2022-May 2023", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Wichada La Motte‑Kerr", "member", [2020, 2022], DT, q="Wichada La Motte‑Kerr CMU/MLD Core member, September 2020-July 2022", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Jenny Lee", "member", [2020, 2020], DT, q="Jenny Lee CMU/HCII Intern, Summer 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Woochan Lee", "member", [2021, 2022], DT, q="Woochan Lee CMU/Stat Contributor, December 2021-May 2022", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Michael Liu", "member", [2020, 2020], DT, q="Michael Liu CMU/HCII Core member, March-April 2020; Contributor, Summer 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Natalia Lombardi de Oliveira", "member", [2020, 2020], DT, q="Natalia Lombardi de Oliveira CMU/Stat Core member, March-May 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Kathryn Mazaitis", "member", [2020, 2023], DT, q="Kathryn Mazaitis CMU/MLD Core member, March 2020-July 2023", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Duane Mengo", "member", [2022, 2022], DT, q="Duane Mengo CMU/MLD Core member, April-September 2022", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Luke Neureiter", "member", [2022, 2023], DT, q="Luke Neureiter CMU/MLD Core member, March 2022-June 2023", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Pratik Patil", "member", [2020, 2020], DT, q="Pratik Patil CMU/Stat Core member, March-May 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Collin Politsch", "member", [2020, 2021], DT, q="Collin Politsch CMU/MLD Core member, August 2020-August 2021", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Aaron Rumack", "member", [2017, 2024], DT, q="Aaron Rumack CMU/MLD Member, August 2017-June 2024", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Wael Al Saeed", "member", [2020, 2020], DT, q="Wael Al Saeed CMU/CSD Intern, Summer 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Anshika Shukla", "member", [2025, 2026], DT, q="Anshika Shukla CMU/Heinz College Core member, May 2025-May 2026", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Venkatesh Sivaraman", "member", [2020, 2020], DT, q="Venkatesh Sivaraman CMU/HCII Summer 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Mashrin Srivastava", "member", [2021, 2022], DT, q="Mashrin Srivastava CMU/MLD Contributor, August 2021-Decmeber 2022", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Qi Xuan Teo", "member", [2021, 2022], DT, q="Qi Xuan Teo CMU/MLD Core member, June 2021-May 2022", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Gabrielle Thivierge", "member", [2023, 2026], DT, q="Gabrielle Thivierge CMU/Stat Core member, April 2023-August 2026", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Ana Karina Van Nortwick", "member", [2020, 2021], DT, q="Ana Karina Van Nortwick CMU/MLD Contributor, October 2020-January 2021", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Kristin Williams", "member", [2020, 2020], DT, q="Kristin Williams CMU/HCII Core member, March-April 2020; Contributor, Summer 2020", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Evan Zhang", "member", [2022, 2022], DT, q="Evan Zhang CMU/CSD Contributor, June-August 2022", note="Delphi past member (CMU-affiliated, dates as listed)"),
        M("Helen Zhou", "member", [2020, 2021], DT, q="Helen Zhou CMU/MLD Core member, April 2020-March 2021", note="Delphi past member (CMU-affiliated, dates as listed)"),
    ],
    pubs=[],
    notes="PLACEHOLDER-REVISE",
    blocked=["https://scholars.cmu.edu/4251-roni-rosenfeld/publications (robots-disallowed)"],
)

# ---------------------------------------------------------------- Bhiksha Raj
BT = "https://cmu-mlsp.github.io/team"
D["Bhiksha Raj"] = dict(
    lab_site="https://cmu-mlsp.github.io/",
    people_page=BT,
    people_pages=[BT],
    members=[
        M("Ahmed Shah", "phd", None, BT, near="PhD Students"),
        M("Joseph Konan", "phd", None, BT, near="PhD Students"),
        M("Xiang Li", "phd", None, BT, near="PhD Students"),
        M("Soham Deshmukh", "phd", None, BT, near="PhD Students"),
        M("Hao Chen", "phd", None, BT, near="PhD Students"),
        M("Massa Baali", "phd", None, BT, near="PhD Students"),
        M("Yizhou Zhao", "phd", None, BT, near="PhD Students"),
        M("Hazim Bukhari", "masters", None, BT, near="MS Students"),
        M("Dareen Alharti", "masters", None, BT, near="MS Students"),
        M("Shuo Han", "masters", None, BT, near="MS Students"),
        M("Sunghwan Baek", "masters", None, BT, near="MS Students"),
        M("Satvik Dixit", "masters", None, BT, near="MS Students"),
        M("Thomas Cantalapiedra", "undergraduate", None, BT, near="Undergraduate Students"),
    ],
    pubs=[PUB("https://cmu-mlsp.github.io/publications", mode="auto")],
    notes="PLACEHOLDER-REVISE",
    blocked=[],
)

# ---------------------------------------------------------------- Pradeep Ravikumar
PC = "http://www.cs.cmu.edu/~pradeepr/content.js"
D["Pradeep Ravikumar"] = dict(
    lab_site="http://www.cs.cmu.edu/~pradeepr/",
    people_page=PC,
    people_pages=[PC],
    members=[
        M("Utkarsh Priyam", "phd", None, PC, s="phd: [", e='name: "Utkarsh Priyam"', raw=True),
        M("Ritabrata Ray", "phd", None, PC, s="phd: [", e='name: "Ritabrata Ray"', raw=True),
        M("Che-Ping Tsai", "phd", None, PC, s="phd: [", e='name: "Che-Ping Tsai"', raw=True),
        M("Rattana Pukdee", "phd", None, PC, s="phd: [", e='name: "Rattana Pukdee"', raw=True, note="joint with Nina Balcan"),
        M("Daniel Jeong", "phd", None, PC, s="phd: [", e='name: "Daniel Jeong"', raw=True, note="joint with Zack Lipton"),
        M("Chandler Squires", "postdoc", None, PC, s="postdocs: [", e='name: "Chandler Squires"', raw=True),
        M("Burak Varici", "postdoc", None, PC, s="postdocs: [", e='name: "Burak Varici"', raw=True),
        M("Omar Chehab", "postdoc", None, PC, s="postdocs: [", e='name: "Omar Chehab"', raw=True),
    ],
    pubs=[],
    notes="PLACEHOLDER-REVISE",
    blocked=[],
)

# ---------------------------------------------------------------- Andrej Risteski
AK = "https://www.andrejristeski.org/"
D["Andrej Risteski"] = dict(
    lab_site=AK,
    people_page=AK,
    people_pages=[AK],
    members=[
        M("Jingchu Gai", "phd", None, AK, near="Current Students", note="co-advised with Aditi Raghunathan"),
        M("Niki Hasrati", "phd", None, AK, near="Current Students"),
        M("Stephen Huan", "phd", None, AK, near="Current Students"),
        M("Yuchen Li", "phd", None, AK, near="Current Students"),
        M("Anna Wei", "phd", None, AK, near="Current Students"),
        M("Tanya Marwah", "phd", [None, 2025], AK, near="Alumni"),
    ],
    pubs=[],
    notes="PLACEHOLDER-REVISE",
    blocked=[],
)

# ---------------------------------------------------------------- Cameron N Riviere
RL = "https://www.ri.cmu.edu/robotics-groups/surgical-mechatronics-laboratory/"
RF = "https://www.ri.cmu.edu/ri-faculty/cameron-riviere/"
D["Cameron N Riviere"] = dict(
    lab_site=RL,
    people_page=RL,
    people_pages=[RL, RF],
    members=[
        M("Basil Fitiane", "staff", None, RL, near="current staff"),
        M("Robert MacLachlan", "staff", None, RL, near="current staff"),
        M("Ailisi Bao", "member", None, RL, near="current student", note="listed as current student (degree level not stated)"),
        M("Arpita Routray", "phd", None, RF, near="current phd students"),
        M("Roger Ho", "member", None, RF, near="current affiliates"),
        M("Pritish Joshi", "member", None, RF, near="current affiliates"),
    ],
    pubs=[],
    notes="PLACEHOLDER-REVISE",
    blocked=[],
)
