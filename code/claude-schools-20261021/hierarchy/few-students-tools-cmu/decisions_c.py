"""Worker C decisions (CMU few-students investigation): LTI / HCII / S3D / Heinz / SDS PIs.

Every row cites a capture in few-students-captures.sqlite; build.py resolves and re-verifies the quotes.
"""
from dhelp import Q, SE, ST, WB

D = {}
FS = "https://api.figshare.com/v2/articles/"


def kilthub(article_id, full_name, advisor_value, **kw):
    """KiltHub thesis JSON: span from the author's full_name to the Advisor(s) value (raw JSON text)."""
    return SE(FS + str(article_id), f'"full_name": "{full_name}"', f'"name": "Advisor(s)", "value": "{advisor_value}"',
              raw=True, long=True, **kw)


# ---------------------------------------------------------------------------- Cleotilde Gonzalez (DDMLab)
DDM = "https://www.cmu.edu/dietrich/sds/ddmlab/people/index.html"
DDMP = "https://www.cmu.edu/dietrich/sds/ddmlab/people/past-members.html"
NOW = [None, 2026]


def ddm(name, role, years, q, page=DDMP, must=None, note=None):
    return ST(name, role, years, Q(page, q), must=must, note=note)


D["Cleotilde Gonzalez"] = dict(
    students=[
        # current members (people page, live 2026 capture)
        ddm("Maha Alosaimi", "phd", NOW, "Maha Alosaimi, M.S. PhD Student", page=DDM),
        ddm("Xiaohong Cai", "postdoc", NOW, "Xiaohong Cai, Ph.D. Post-Doctoral Fellow", page=DDM),
        ddm("Grace Roessling", "postdoc", NOW, "Grace Roessling, Ph.D. Post-Doctoral Fellow", page=DDM),
        ddm("Jinfeng Lou", "postdoc", NOW, "Jinfeng Lou, Ph.D. Research Associate Google Scholar Jinfeng Lou is a Carnegie Bosch Postdoctoral Fellow.", page=DDM),
        ddm("Jeffrey Flagg", "member", NOW, "Jeffrey Flagg, M.S. Lab Manager - Research Associate II", page=DDM),
        ddm("Kibo Schaffer", "member", NOW, "Kibo Schaffer Research Programmer", page=DDM),
        ddm("Yuchen Li", "member", NOW, "Yuchen Li, M.S. Research Assistant", page=DDM),
        ddm("Bodhisattva Das", "masters", NOW, "Bodhisattva Das Student Research Assistant Bodhisattva Das is pursuing his Masters Degree in Information Security Policy Management at Carnegie Mellon University", page=DDM),
        ddm("Vlad Miloserdov", "undergraduate", NOW, "Vlad Miloserdov Student Research Assistant Vlad Miloserdov is an undergraduate student at Carnegie Mellon University", page=DDM),
        ddm("Jet Jacobsen", "other", NOW, "Jet Jacobsen Visiting Research Associate", page=DDM),
        ddm("Kent Grass-Valdivia", "masters", NOW, "Kent Grass-Valdivia Student Research Assistant Kent Grass is a Master's student in Public Policy and Management", page=DDM),
        # past post-docs (2016+)
        ddm("Maria Ferreira", "postdoc", [2023, 2025], "Maria Ferreira, Ph.D. April 2023 to December 2025"),
        ddm("Tailia Malloy", "postdoc", [2022, 2025], "Tailia Malloy, Ph.D. December 2022 to July 2025"),
        ddm("Roderick Seow", "postdoc", [2023, 2025], "Roderick Seow, Ph.D. September 2023 to February 2025"),
        ddm("Ngoc Nguyen", "postdoc", [2019, 2023], "Ngoc Nguyen, Ph.D. October 2019 to March 2023"),
        ddm("Baptiste Prebot", "postdoc", [2021, 2023], "Baptiste Prebot, Ph.D. October 2021 to March 2023"),
        ddm("Nhat Phan", "postdoc", [2021, 2022], "Nhat Phan, Ph.D. March 2021 to August 2022"),
        ddm("Palvi Aggarwal", "postdoc", [2018, 2021], "Palvi Aggarwal, Ph.D. September 2018 to August 2021"),
        ddm("Kuldeep Singh", "postdoc", [2019, 2021], "Kuldeep Singh, Ph.D. April 2019 to August 2021"),
        ddm("Farnaz Tehranchi", "postdoc", [2020, 2021], "Farnaz Tehranchi, Ph.D. October 2020 to August 2021"),
        ddm("Hanshu Zhang", "postdoc", [2019, 2020], "Hanshu Zhang, Ph.D. September 2019 to July 2020"),
        ddm("Korosh Mahmoodi", "postdoc", [2018, 2020], "Korosh Mahmoodi, Ph.D. September 2018 to May 2020"),
        ddm("Pegah Fakhari", "postdoc", [2018, 2018], "Pegah Fakhari, Ph.D. February 2018 to December 2018"),
        ddm("Prashanth Rajivan", "postdoc", [2015, 2018], "Prashnanth Rajivan, Ph.D. December 2015 to August 2018",
            must=["Prashnanth Rajivan"], note="Spelled 'Prashnanth' on the past-members page."),
        ddm("Efrat Aharonov", "postdoc", [2016, 2018], "Efrat Aharonov, Ph.D. August 2016 to August 2018"),
        ddm("Jeffrey Chrabaszcz", "postdoc", [2016, 2017], "Jeffrey Chrabaszcz, Ph.D. August 2016 to September 2017"),
        ddm("Michael Yu", "postdoc", [2014, 2017], "Michael Yu, Ph.D. May 2014 to May 2017"),
        # past students & staff (2016+)
        ddm("Marko Morrison", "phd", [2025, 2026], "Marko Morrison May 2025 to August 2026 Marko Morrison is a Ph.D. student in Societal Computing"),
        ddm("Yinuo Du", "phd", [2020, 2025], "Yinuo Du September 2020 to August 2025 Yinuo received her PhD in May 2025"),
        ddm("Erin Bugbee", "phd", [2020, 2025], "Erin Bugbee September 2020 to May 2025 Erin received her PhD in May 2025"),
        ddm("Chase McDonald", "phd", [2020, 2025], "Chase McDonald September 2020 to May 2025 Chase received his PhD in May 2025"),
        ddm("Duncan Wood", "phd", [2023, 2024], "Duncan Wood August 2023 to December 2024 Duncan is a Ph.D. student in the Department of Social and Decision Sciences"),
        ddm("Erin McCormick", "phd", [2015, 2022], "Erin McCormick August 2015 to May 2022 Erin McCormick received her PhD in August 2022"),
        ddm("Aarya Bhave", "other", [2026, 2026], "Aarya Bhave Summer 2026"),
        ddm("Raghav Sharma", "other", [2026, 2026], "Raghav Sharma Summer 2026"),
        ddm("Don Morrison", "member", [2017, 2026], "Don Morrison January 2017 to May 2026 Don worked on software supporting researchers in the DDMLab"),
        ddm("Anu Aggarwal", "member", [2024, 2025], "Anu Aggarwal, M.S. January 2024 to December 2025 After her time as Research Associate"),
        ddm("Selena Zheng", "undergraduate", [2025, 2025], "Selena Zheng June 2025 to August 2025 Selena Zheng is completing her undergraduate degree at New York University",
            note="Visiting summer undergraduate (NYU) hosted in the lab."),
        ddm("Saketh Mudundi", "masters", [2024, 2025], "Saketh Mudundi October 2024 to May 2025 Saketh is a Master's student"),
        ddm("Sophie Ding", "undergraduate", [2024, 2025], "Sophie Ding November 2024 to May 2025 Sophie is an undergrad student"),
        ddm("Arya Mane", "undergraduate", [2024, 2024], "Arya Mane January to December 2024 Arya is completing her undergrad work"),
        ddm("Carlos Botelho", "other", [2022, 2023], "Carlos Botelho July 2022 to July 2023"),
        ddm("Tony Xi", "masters", [2021, 2022], "Tony Xi September 2021 to December 2022 Master student intern Tony Xi studied at the Information Networking Institute"),
        ddm("Wenjia (Jiajia) Hu", "other", [2021, 2022], "Wenjia (Jiajia) Hu September 2021 to May 2022"),
        ddm("Ed Matlack", "other", [2021, 2022], "Ed Matlack October 2021 to May 2022 Ed Matlack was be a visiting scholar"),
        ddm("Miso Demko", "undergraduate", [2021, 2021], "Miso Demko August 2021 to December 2021 Miso Demko was an undergraduate research student"),
        ddm("Aditya Gulati", "other", [2020, 2021], "Aditya Gulati June 2020 to August 2021"),
        ddm("Disha Das", "undergraduate", [2020, 2021], "Disha Das September 2020 to January 2021 Computer Science with a minor in Decision Science."),
        ddm("Alison Butler", "other", [2019, 2020], "Alison Butler September 2019 to May 2020 Alison studying as an MD/PhD student",
            note="MD/PhD student (Pitt/CMU Medical Scientist Training Program) working in the lab."),
        ddm("Peijie He", "undergraduate", [2019, 2020], "Peijie He September 2019 to May 2020 Peijie is majoring in Decision Science"),
        ddm("Max Gamerman", "undergraduate", [2019, 2020], "Max Gamerman September 2019 to May 2020 Max is studying Behavioral Economics, Policy, and Organizations"),
        ddm("Andrew Ye", "undergraduate", [2019, 2020], "Andrew Ye September 2019 to May 2020 Andrew is currently studying Statistics and Machine Learning"),
        ddm("Max Yeh", "undergraduate", [2019, 2020], "Max Yeh September 2019 to May 2020 Max is currently in the department of Social and Decision Sciences pursuing a Bachelor's Degree"),
        ddm("Orsi Kovacs", "other", [2019, 2020], "Orsi Kovacs September 2019 to May 2020"),
        ddm("David Hagmann", "member", [2014, 2018], "David Hagmann, Ph.D. 2014 to 2018"),
        ddm("Cristobal De La Maza Guzman", "member", [2014, 2018], "Cristobal De La Maza Guzman, Ph.D. 2014 to 2018"),
        ddm("Qiao Shen", "undergraduate", [2018, 2018], "Qiao Shen Fall 2018 Qiao is an undergraduate student at Carnegie Mellon University"),
        ddm("Sabina Sloman", "member", [2017, 2018], "Sabina Sloman 2017 to 2018 Sabina is currently pursuing her Ph.D. in the Department of Social and Decision Sciences",
            note="SDS PhD student who worked in the lab 2017-2018; the page does not say Gonzalez was her advisor."),
        ddm("Nalyn Sriwattanakomen", "member", [2016, 2018], "Nalyn Sriwattanakomen 2016 to 2018"),
        ddm("Fei Lua", "member", [2015, 2017], "Fei Lua 2015 to 2017"),
        ddm("Sam Cheyette", "member", [2015, 2016], "Sam Cheyette Fall 2015 to Fall 2016"),
        ddm("Emily Ho", "other", [2017, 2017], "Emily Ho September to December 2017 Emily returned to New York to complete her Ph.D"),
        ddm("German Lenin Dugarte Pena", "other", [2017, 2017], "German Lenin Dugarte Pena September to December 2017"),
        ddm("Melisa E. Chavez Guerrero", "other", [2017, 2017], "Melisa E. Chavez Guerrero February to May 2017"),
        ddm("Jörn von Grabe", "other", [2016, 2016], "Jörn von Grabe, Ph.D. January 2016 to March 2016"),
    ],
    lab_note=("Dynamic Decision Making Laboratory (SDS; Gonzalez is HCII/S3D-affiliated): the lab's People page lists 11 current "
              "members besides the director and its Past Members page dates every post-doc, student and staff member; "
              "66 people overlap 2016-2026."),
    notes=("Sources: cmu.edu/dietrich/sds/ddmlab people/index.html (current) and people/past-members.html (dated tenures). "
           "Members whose tenure ended before 2016 were left out (e.g. post-doc Frederic Moisan, ended Dec 2015). Roles: "
           "post-docs as listed; 'member' for lab staff and CMU students whose page entry does not name Gonzalez as advisor; "
           "'other' for visitors and entries with no stated position. Lab page relation = membership, not advising."),
)

# ---------------------------------------------------------------------------- Sherry Tongshuang Wu (WInE Lab)
WG = "https://www.cs.cmu.edu/~sherryw/group.html"
D["Sherry Tongshuang Wu"] = dict(
    students=[
        ST("Simret Araya Gebreegziabher", "postdoc", NOW, Q(WG, "Simret Araya Gebreegziabher (Postdoc) , co-advisor: Bob Kraut, Haiyi Zhu, Yi-Chia Wang")),
        ST("Jieun Kim", "postdoc", NOW, Q(WG, "Jieun Kim (Postdoc) , co-advisor: Bob Kraut, Haiyi Zhu, Yi-Chia Wang")),
        ST("Vijay Viswanathan", "phd", NOW, Q(WG, "Vijay Viswanathan (PhD) , co-advisor: Graham Neubig"),
           note="Also on her HCII profile Advisees: 'Vijay Viswanathan (LTI)'."),
        ST("Qianou (Christina) Ma", "phd", NOW, Q(WG, "Christina Ma (PhD) , co-advisor: Ken Koedinger"), must=["Christina Ma"]),
        ST("Xinran Zhao", "phd", NOW, Q(WG, "Xinran Zhao (PhD) Information Seeking for Complex Tasks"),
           note="Also on her HCII profile Advisees: 'Xinran Zhao (LTI)'."),
        ST("Jessie Mindel", "phd", NOW, Q(WG, "Jessie Mindel (PhD) AI-Mediated Communication")),
        ST("Zheyuan Zhang", "phd", NOW, Q(WG, "Zheyuan Zhang (PhD) Human-Agent Interaction")),
        ST("Eunsu Kim", "phd", NOW, Q(WG, "Eunsu Kim (PhD) AI Contributions to Human Tasks.")),
        ST("Keyu He", "masters", NOW, Q(WG, "Keyu He (Master) Eval of Human Prompt Ability")),
        ST("Pengcheng Jing", "masters", NOW, Q(WG, "Pengcheng Jing (Master) Tacit Knowledge in Agents")),
        ST("Jiasi Wang", "undergraduate", NOW, Q(WG, "Jiasi Wang (Undergrad) User Simulator Behavior Analysis")),
        ST("Yuan Tian", "other", NOW, Q(WG, "Yuan Tian (Visit) AI for Data Analysis"), note="Visitor."),
        ST("Seungyeon (Lily) Back", "other", NOW, Q(WG, "Seungyeon (Lily) Back (Visit) UX for Writing with Agents"), note="Visitor."),
        ST("Chenyang Yang", "phd", None, Q(WG, "Alumni Chenyang Yang (PhD, co-advisor: Christian"),
           note="Co-advised with Christian Kaestner (S3D); also on her HCII profile Advisees: 'Chenyang Yang (S3D)'."),
        ST("Yiyang (Diana) Wang", "masters", None, Q(WG, "Yiyang (Diana) Wang (Master) End-User Prompt Disambiguation.")),
        ST("Yuanchen (Sophie) Bai", "masters", None, Q(WG, "Yuanchen (Sophie) Bai (Master) NLP dataset characterization")),
        ST("Raoyi (Cathy) Huang", "masters", None, Q(WG, "Raoyi (Cathy) Huang (Master) NLP dataset characterization.")),
        ST("Atharva Naik", "masters", None, Q(WG, "Atharva Naik (Master) LLM in CS education.")),
        ST("Jushaan Kalra", "masters", None, Q(WG, "Jushaan Kalra (Master) Multi-domain Retrieval.")),
        ST("Yilin Zhang", "masters", None, Q(WG, "Yilin Zhang (Master) Code Retrieval with AST.")),
        ST("Callum Zhao", "masters", None, Q(WG, "Callum Zhao (Master) Build Effective Agentic Skills")),
        ST("Cassandra Shi", "undergraduate", None, Q(WG, "Cassandra Shi (Undergrad) Requirement-driven LLMs.")),
        ST("Cheng Qian", "other", None, Q(WG, "Cheng Qian (Visit) LLM hullucination."), note="Visitor; now a PhD student at UIUC."),
    ],
    lab_note=("WInE Lab (HCII, with LTI affiliation), founded 2022: group page lists 13 current members (2 post-docs, 6 PhD, "
              "2 master's, 1 undergraduate, 2 visitors) and 10 alumni."),
    notes=("Source: www.cs.cmu.edu/~sherryw/group.html ('Current Members' / 'Alumni'). Her HCII profile Advisees list "
           "(Qianou (Christina) Ma, Jessie Mindel, Vijay Viswanathan, Chenyang Yang, Xinran Zhao) agrees. Alumni have no "
           "dates; all fall in her CMU tenure (2022-)."),
)

# ---------------------------------------------------------------------------- Lauren Herckis (Culture Lab)
HCV = "https://lauher29.dreamhosters.com/wp-content/uploads/2023/07/Herckis-CV-07-2023.pdf"
METALS = "Masters of Educational Technology and Applied Learning Science"


def hcv(name, role, years, q, note=None, must=None):
    return ST(name, role, years, Q(HCV, q), note=note, must=must)


AMB = "CV lists this entry under the 2021-2022/2018/2016 date block; exact year not separable from the PDF text."
D["Lauren Herckis"] = dict(
    students=[
        hcv("Yue Wang", "masters", [2022, 2023], f"Yue Wang, {METALS}, Independent study: AI-Augmented Learning in Community Colleges"),
        hcv("Manvi Teki", "masters", [2022, 2023], f"Manvi Teki, {METALS}, Independent study: AI-Augmented Learning in Community Colleges"),
        hcv("Qiaoqiao Ma", "masters", [2022, 2023], f"Qiaoqiao Ma, {METALS}, Independent study: AI-Augmented Learning in Community Colleges"),
        hcv("Laura Delince Ceballos", "masters", [2022, 2023], f"Laura Delince Ceballos, {METALS}, Research Assistant: Digitalization of Higher Education"),
        hcv("Marsha Kerman", "masters", [2022, 2023], "Marsha Kerman, METALS student advisee"),
        hcv("Qinglin Feng", "masters", [2022, 2023], "Qinglin Feng, METALS student advisee"),
        hcv("Jitian Liao", "masters", [2022, 2023], "Jitian Liao, METALS student advisee"),
        hcv("Winter Clark", "masters", [2022, 2022], f"Winter Clark, {METALS}, Evidence-based Educational Design Mentor"),
        hcv("Xinzhu Wang", "masters", [2022, 2022], f"Xinzhu Wang, {METALS}, Evidence-based Educational Design Mentor"),
        hcv("Tyree Cowell", "masters", [2022, 2022], f"Tyree Cowell, {METALS}, Research Assistant: Adoption of Adaptive Learning Technologies"),
        hcv("Prithika Acharya", "masters", None, f"Prithika Acharya, {METALS}, Independent Study: Digitalization of Higher Education", note=AMB),
        hcv("Xinlu Gou", "masters", None, "Xinlu Gou, METALS student advisee", note=AMB),
        hcv("Rhea Li", "masters", None, "Rhea Li, METALS student advisee", note=AMB),
        hcv("Ziwen Zheng", "masters", None, "Ziwen Zheng, METALS student advisee", note=AMB),
        hcv("Yangling Zhang", "masters", None, "Yangling Zhang, METALS student advisee", note=AMB),
        hcv("Swarnakshi Kapil", "masters", None, f"Swarnakshi Kapil, {METALS}, Independent Study: Traversing Virtual-Physical Spaces", note=AMB),
        hcv("Zhijin Wu", "undergraduate", [2023, 2023], "2023 Zhijin Wu, Information Systems, Independent study: AI-enabled recommendation systems"),
        hcv("Juhye Pak", "undergraduate", [2023, 2023], "Juhye Pak, Information Systems and Statistics and Machine Learning: Independent study: XR-enabled pedagogy"),
        hcv("Xiaohan Liu", "undergraduate", [2022, 2022], "2022 Xiaohan Liu, Statistics and Data Science, Independent study: Adoption of Adaptive Learning Technologies"),
        hcv("Irene Kang", "undergraduate", [2022, 2022], "Irene Kang, Psychology Department, Independent study: Adoption of Adaptive Learning Technologies"),
        hcv("Qianou (Christina) Ma", "undergraduate", [2021, 2022], "2021-2022 Qianou Ma, Psychology Department, Independent study: Immersive Media in Undergraduate Education",
            must=["Qianou Ma"], note="Same person as Sherry Wu's PhD student Qianou (Christina) Ma."),
        hcv("Vera Schulz", "undergraduate", [2018, 2018], "2018 Vera Schulz, History Department, Independent study: Implementation of Innovative Ed Tech"),
        hcv("Elaine Zhu", "undergraduate", [2018, 2018], "2018 Elaine Zhu, History Department, Independent study: Humanities and Communication for Understanding Hybrid Virtual-Physical Homes"),
        hcv("Vivian Qiu", "undergraduate", [2017, 2017], "2017 Vivian Qiu, School of Design, Independent Study: Methods of Mourning"),
        hcv("Lea Cody", "undergraduate", [2017, 2017], "2017 Lea Cody, School of Design, Independent Study: Mourning Objects"),
        hcv("Zain Islam-Hashmi", "undergraduate", [2018, 2019], "Senior Thesis Committee Advising 2018-2019 Zain Islam-Hashmi, Architecture: Earthworks Construction in Pittsburgh"),
    ],
    lab_note=("No people page; her CV (07/2023) names the 'Culture Lab' (lab group supervision 2019-2023) and lists "
              "16 METALS master's advisees/independent-study students and 10 CMU undergraduate research mentees 2016-2023."),
    notes=("Source: Herckis CV (lauher29.dreamhosters.com, July 2023), sections 'Supervision, Advising, and Mentoring of "
           "Graduate Students', 'Mentoring and Supervision of Undergraduate Students' and 'Senior Thesis Committee Advising'. "
           "Left out: graduate teaching assistants (teaching, not research advising), field-school preparation mentees "
           "(Maria Barr, Gwen Luvara, Laura Lodewyk) and Jessica Walker (University of Pittsburgh, external mentor). "
           "HCII profile lists only Rotem Guttman."),
)

# ---------------------------------------------------------------------------- Erik Harpstead
ECV = "http://www.erikharpstead.net/files/Harpstead%20CV.pdf"
YRS = "Year mapped by row order from the CV's separate date column."


def ecv(name, role, years, q, note=YRS, must=None):
    return ST(name, role, years, Q(ECV, q), note=note, must=must)


D["Erik Harpstead"] = dict(
    students=[
        ecv("Max Levine", "phd", [2026, None], "Doctoral and Postdoctoral Supervision Advisor, Max Levine"),
        ecv("Noor Hammad", "phd", [2020, None], "Co-Advisor, Noor Hammad (with Jessica Hammer)",
            note="Co-advised with Jessica Hammer. " + YRS),
        ecv("Collin Wright", "other", [2026, 2026], "Independent Study Mentor, Collin Wright"),
        ecv("Gregory Weber", "undergraduate", [2024, 2024], "REU Mentor, Gregory Weber"),
        ecv("Joseph Fudali", "undergraduate", [2024, 2024], "REU Mentor, Joseph Fudali"),
        ecv("Safiyyah Scott", "other", [2023, 2023], "Independent Study Mentor, Safiyyah Scott"),
        ecv("Marsha Kerman", "masters", [2023, 2023], "Independent Study Mentor, Marsha Kerman",
            note="METALS master's student (Herckis CV). " + YRS),
        ecv("Lanning Zhang", "other", [2023, 2023], "Independent Study Mentor, Lanning Zhang"),
        ecv("Alexander Wang", "other", [2023, 2024], "Independent Study Mentor, Alexander Wang"),
        ecv("Kathryn Minor", "other", [2023, 2023], "Independent Study Mentor, Kathryn Minor"),
        ecv("Adrian Ma", "other", [2020, 2022], "Independent Study Mentor, Adrian Ma"),
        ecv("Elias El Kozah", "other", [2022, 2022], "Independent Study Mentor, Elias El Kozah"),
        ecv("Yiming (Yvonne) Fang", "other", [2022, 2022], "Independent Study Mentor, Yiming (Yvonne) Fang"),
        ecv("Francesca Lamiero", "undergraduate", [2022, 2022], "REU Mentor, Francesca Lamiero"),
        ecv("Qianou (Christina) Ma", "undergraduate", [2021, 2022], "Senior Thesis Advisor, Qianou (Christina) Ma"),
        ecv("Shuyuan Ding", "other", [2020, 2020], "Independent Study Mentor, Shuyuan Ding"),
        ecv("Yuran Ding", "other", [2020, 2020], "Independent Study Mentor, Yuran Ding"),
        ecv("Franklin Guttman", "other", [2020, 2020], "Independent Study Mentor, Franklin Guttman"),
        ecv("Kalpa Anjur", "undergraduate", [2020, 2020], "15-400 Mentor, Kalpa Anjur", note="15-400 is CMU's undergraduate research course. " + YRS),
        ecv("Cayden Codel", "undergraduate", [2020, 2020], "15-400 Mentor, Cayden Codel", note="15-400 is CMU's undergraduate research course. " + YRS),
        ecv("Nadia Susanto", "other", [2020, 2020], "Independent Study Mentor, Nadia Susanto"),
        ecv("Kyle Barron", "other", [2019, 2020], "Independent Study Mentor, Kyle Barron"),
        ecv("Zihuiwen (Daniella) Ye", "undergraduate", [2019, 2020], "REU Mentor, Zihuiwen (Daniella) Ye"),
        ecv("Jingxuan (Nicole) Wang", "other", [2019, 2019], "Independent Study Mentor, Jingxuan (Nicole) Wang"),
        ecv("Simran Jobanputra", "other", [2019, 2019], "Independent Study Mentor, Simran Jobanputra"),
        ecv("Kaitlin McTigue", "other", [2019, 2019], "Independent Study Mentor, Kaitlin McTigue"),
        ecv("Juan Sebastian Rios", "undergraduate", [2018, 2018], "REU Mentor, Juan Sebastian Rios"),
        ecv("Xiaofei Zhou", "other", [2018, 2018], "Project Support, Xiaofei Zhou"),
        ecv("Yeyu Wang", "other", [2018, 2018], "Project Support, Yeyu Wang"),
    ],
    lab_note=("No group page; HCII profile lists 1 advisee (Noor Hammad). His CV (erikharpstead.net, 2026) lists "
              "1 PhD advisee + 1 co-advisee and 27 undergraduate/graduate research mentees 2018-2026."),
    notes=("Source: CV section 'Supervision' (Doctoral and Postdoctoral Supervision; Undergraduate & Graduate Research "
           "Supervision). Roles: REU and 15-400 mentees and the senior thesis = undergraduate; independent-study mentees "
           "whose level the CV does not state = other. Left out: doctoral committee memberships (Daniel Weitekamp; external "
           "Kutub Ghandi, Qiao Zhang) and project-team advising without names. Years come from the CV's date column, "
           "which pdftotext separates from the rows; they were mapped by row order (38 dates for 38 rows). Thesis index: he "
           "co-chairs CMU-HCII-26-114 (Noor Hammad, already held, with Jessica Hammer); note the archive's abstract page "
           "26-114 carries Anna Kawakami's title/name in its header (her thesis is 26-115, chaired by Holstein/Zhu)."),
)

# ---------------------------------------------------------------------------- Akari Asai
AG = "https://akariasai.github.io/group/"
D["Akari Asai"] = dict(
    students=[
        ST("Abhinav Java", "phd", NOW, Q(AG, "Group Students Abhinav Java CMU MLD Ph.D.")),
        ST("Xueqiao Sun", "phd", NOW, Q(AG, "Xueqiao Sun CMU LTI Ph.D. With Graham Neubig"), note="Co-advised with Graham Neubig."),
        ST("Saee Patil", "masters", NOW, Q(AG, "Saee Patil CMU M.S. in Machine Learning")),
        ST("Harry Hu", "undergraduate", NOW, Q(AG, "Harry Hu CMU ECE and CS undergraduate")),
    ],
    lab_note="New lab: CMU LTI assistant professor from 07/2026 (CV); group page lists 4 CMU students (2 PhD, 1 M.S., 1 undergraduate).",
    notes=("Source: akariasai.github.io/group/ 'Students'. Left out: Zhengliang Shi (listed 'CMU LTI Ph.D. From Spring 2027', "
           "outside the window), Zijian (Steven) Chen (AI2 intern, University of Waterloo undergraduate - not CMU) and the "
           "'Close collaborators' (Rulin Shao, Seungone Kim - advised by others). CV start date: 'Employment 07/2026 - "
           "Carnegie Mellon University'."),
)

# ---------------------------------------------------------------------------- Niloofar Mireshghallah (Looni Lab)
LL = "https://mireshghallah.github.io/looni-lab.html"
MS = "Master's students Bhuvan Chandra Koduru"


def lms(name):
    return ST(name, "masters", NOW, SE(LL, "Master's students", name))


D["Niloofar Mireshghallah"] = dict(
    students=[
        ST("William Watson", "phd", NOW, Q(LL, "PhD students Bill Watson (co-advised with Sauvik Das )"), must=["Bill Watson"],
           note="Listed as 'Bill Watson'; co-advised with Sauvik Das."),
        ST("Xiaoyu (Nicholas) Wu", "phd", NOW, Q(LL, "Xiaoyu (Nicholas) Wu (co-advised with Andrew Ilyas and Steven Wu )")),
        ST("Renfei (Alex) Zhang", "phd", NOW, SE(LL, "PhD students Bill Watson", "Renfei Zhang"), must=["Renfei Zhang"]),
        ST("Kevin Han", "phd", NOW, Q(LL, "Kevin Han (co-advised with Amir Barati Farimani )")),
        lms("Bhuvan Chandra Koduru"),
        lms("Medha Hira"),
        lms("Prachi Goyal"),
        lms("Nikitha Srikanth"),
        lms("Abhav Mehrotra"),
        lms("Karen Zhang"),
        lms("Mohith Rajesh"),
    ],
    lab_note=("New lab (Looni Lab), started 2026: lab page ('Lab lunch, Fall 2026') lists 4 PhD and 7 master's students; "
              "joint LTI/EPP appointment."),
    notes=("Source: mireshghallah.github.io/looni-lab.html 'Members'. Left out: 'Visiting & Collaborators' (Prince Jha, "
           "Anthony Hughes, Suresh Raghu) - the page does not separate visitors from outside collaborators. Conflict: her "
           "LTI profile says 'Assistant Professor (Beginning Fall 2027)' while her homepage says she is an Assistant "
           "Professor at CMU and the lab page shows a Fall 2026 lab; the LTI profile lists William Watson as advisee."),
)

# ---------------------------------------------------------------------------- Hanan Hibshi
D["Hanan Hibshi"] = dict(
    students=[
        ST("Taylor McCampbell", "masters", [None, 2025], kilthub(29089931, "Taylor McCampbell", "Hanan Hibshi"),
           note="KiltHub MS thesis (Information Networking Institute) 2025-05-05, 'Barriers Regarding K-12 Cyber Security Education in the United States'."),
        ST("Vishruti Jignesh Kakkad", "masters", [None, 2023], kilthub(23580210, "Vishruti Jignesh Kakkad", "Hanan Hibshi"),
           note="KiltHub MS thesis (Information Networking Institute) 2023-05-01."),
        ST("Antonio Martorana", "masters", [None, 2022], kilthub(21861597, "Antonio Martorana", "Hanan Hibshi"),
           note="KiltHub MSIT thesis (Information Networking Institute) 2022-05-04, 'Investigating the Experiences of Female CTF Players'."),
    ],
    lab_note="No lab page; INI teaching-track faculty (CyLab core, Societal Computing affiliate). KiltHub holds 3 INI master's theses she advised.",
    notes=("Searched: homepage (www.cs.cmu.edu/~hhibshi/, no student list - mentions 'my students' on the NCAE-C/picoCTF "
           "outreach projects), KiltHub theses mentioning Hibshi (4 found, 3 with Advisor(s) = Hanan Hibshi), reports-archive "
           "thesis committees. Maha Alosaimi is already held."),
)

# ---------------------------------------------------------------------------- Alessandro Acquisti
AQ20 = WB + "20200423004825id_/https://www.heinz.cmu.edu/~acquisti/academic-genealogy.htm"
AQ23 = WB + "20231205110132id_/https://www.heinz.cmu.edu/~acquisti/academic-genealogy.htm"
D["Alessandro Acquisti"] = dict(
    students=[
        ST("Eduardo Mustri", "phd", None, Q(AQ20, "Current Students Eduardo Mustri, Ph.D. Student, Heinz College, Carnegie Mellon University"),
           note="Listed as current student in the 2020-04 and 2023-12 captures (main advisor in 2023)."),
        ST("Logan Warberg", "phd", [None, 2022], Q(AQ20, "Logan Warberg, Ph.D. Student, EPP, Carnegie Mellon University (co-advisor)"),
           note="KiltHub PhD thesis (EPP) 2022-08-10, Advisor(s): Alessandro Acquisti, Douglas Sicker (figshare 22151954)."),
        ST("Zijun Ding", "phd", None, Q(AQ23, "Zijun Ding, Ph.D. Student, Heinz College, Carnegie Mellon University (Main Advisor)"),
           note="Current student in the 2023-12 capture."),
        ST("Ryan Steed", "phd", None, Q(AQ23, "Ryan Steed, Ph.D. Student, Heinz College, Carnegie Mellon University (Main Advisor)")),
        ST("Jessica Colnago", "phd", None, Q(AQ20, "Jessica Colnago, Ph.D. Student, SCS, Carnegie Mellon University (co-advisor)"),
           note="KiltHub PhD thesis (ISR) 2021-09-28, Advisor(s): Lorrie Faith Cranor, Alessandro Acquisti."),
        ST("Cristobal Cheyre", "postdoc", None, Q(AQ20, "Post-Doctoral Fellows Cristobal Cheyre (Carnegie Mellon University)")),
        ST("James Graves", "phd", [None, 2021], kilthub(16679617, "James Graves", "Alessandro Acquisti"),
           note="KiltHub PhD thesis (EPP) 2021-09-20 'Empirical Analyses of Effects and Perceptions of Cybercrime'; listed as 'Jim Graves (EPIC)' among former students."),
    ],
    lab_note=("Privacy Economics Experiments (PeeX) Lab, Heinz College; his homepage (www.heinz.cmu.edu/~acquisti/, now 404) "
              "has an 'Academic Genealogy' page listing 5 current PhD students and 1 post-doc (2023-12 capture)."),
    notes=("Sources: Wayback captures of academic-genealogy.htm (2020-04, 2023-12), KiltHub theses with Advisor(s) Acquisti "
           "(Graves 2021, Warberg 2022, Colnago 2021; Adjerid 2013, Brandimarte 2012, Tsai 2009 are pre-window). The "
           "genealogy 'Former Students' list (Alisa Frik, Veronica Marotta, Sonam Samat, Li Jiang, ...) carries no dates and "
           "no 2016+ source was found for them, so they are not recorded. The PeeX lab people page (peex.heinz.cmu.edu/people/, "
           "2021 and 2024 captures) is stale pre-2016 content (Adjerid/Brandimarte as PhD candidates) and was not used. The "
           "live homepage now returns 404. No SCS (ISR) thesis lists him as chair."),
)

# ---------------------------------------------------------------------------- Alon Lavie
D["Alon Lavie"] = dict(
    students=[],
    lab_note=("No lab; returned to an active LTI faculty role in July 2025 after ten years as adjunct (industry: Amazon, "
              "Unbabel, Phrase). Homepage lists graduated students only."),
    notes=("Homepage www.cs.cmu.edu/~alavie/ 'My Students that have Graduated': in-window are Austin Matthews (PhD 2019, "
           "co-advised with Chris Dyer; already held), Ricardo Rei (PhD 2024, co-advised with Luisa Coheur) and John Mendonca "
           "(PhD 2025, co-advised with Isabel Trancoso). Rei and Mendonca are IST Lisbon / Unbabel-era co-advisees (CMU-Portugal); "
           "no source found that puts them at CMU (not on the LTI dissertation lists or LTI alumni 2024/2025 pages, no KiltHub "
           "thesis), so they are left out. Michael Denkowski (PhD 2015) is pre-window and already held. KiltHub has only "
           "Denkowski's thesis with Advisor Alon Lavie. The SCS thesis index (622 theses 2016-2026) has no committee naming "
           "Lavie, as chair or member. As MSAII director (2025-) he has no listed research advisees yet."),
)

# ---------------------------------------------------------------------------- Randi Williams
D["Randi Williams"] = dict(
    students=[],
    lab_note="New lab: HCII assistant research professor since July 2026; HCII profile lists 1 advisee (Leah Teffera, already held).",
    notes=("Searched homepage (randiwilliams.com) and CV: all prior supervision is MIT Media Lab / Day of AI (out of scope). "
           "No other CMU advisee found; no SCS thesis committee (2016-2026 index) or KiltHub thesis names her."),
)

# ---------------------------------------------------------------------------- Steve James Rathje
D["Steve James Rathje"] = dict(
    students=[],
    lab_note=("New lab (Psychology of Technology Lab), HCII assistant professor from 2026; HCII profile lists 2 advisees "
              "(Kevin Hernandez, Meryl Ye (S3D)), both already held."),
    notes=("Searched stevenrathje.com (no members page) and his 2026 CV (no CMU mentees; prior supervision at Cambridge/NYU "
           "is out of scope). No SCS thesis committee (2016-2026 index) or KiltHub thesis names him as advisor."),
)

# ---------------------------------------------------------------------------- Lori Levin (LLab)
LL17 = WB + "20170127213733id_/http://www.cs.cmu.edu:80/afs/cs/project/llab/www/"
LL18 = WB + "20180607164843id_/http://www.cs.cmu.edu:80/afs/cs/project/llab/www/"
LL20 = WB + "20200115111119id_/http://www.cs.cmu.edu:80/afs/cs/project/llab/www/"
LL22 = WB + "20220120100103id_/http://www.cs.cmu.edu/afs/cs/project/llab/www/"
CUR = "Llab is lead by Lori Levin . Current members include:"
D["Lori Levin"] = dict(
    students=[
        ST("Katherine Kairis", "member", [None, 2017], SE(LL17, CUR, "Katherine Kairis")),
        ST("Ke Lin", "member", [None, 2017], SE(LL17, CUR, "Ke Lin")),
        ST("Patrick Littell", "member", [None, 2017], SE(LL17, CUR, "Patrick Littell")),
        ST("Jeffrey Micher", "member", [2017, 2022], SE(LL17, CUR, "Jeffrey Micher"),
           note="Listed as a current LLab member in the 2017-01, 2018-06, 2020-01 and 2022-01 captures."),
        ST("David R. Mortensen", "member", [2017, 2022], SE(LL17, CUR, "David R. Mortensen"),
           note="LTI research faculty colleague listed as an LLab member (2017-2022 captures); a lab member, not an advisee."),
        ST("Jay Park", "member", [2020, 2022], Q(LL20, "Current members include: Lori Levin Jeffrey Micher David R. Mortensen Jay Park"),
           note="Listed in the 2020-01 and 2022-01 captures."),
        ST("Sriharini Pingali", "other", [2017, 2017], Q(LL18, "Linguistics Lab Course and Directed Study Spring 2017 Sriharini Pingali"),
           note="Directed-study student (Linguistics Lab course), Spring 2017; level not stated."),
    ],
    lab_note=("LLab (linguistics lab, www.cs.cmu.edu/afs/cs/project/llab/www/, robots-disallowed live; Wayback captures "
              "2017-2022) lists 'current members' - 7 people besides Levin across captures; no current people page."),
    notes=("Sources: Wayback captures of the LLab page (2017-01, 2018-06, 2020-01, 2022-01). Her homepage (www.cs.cmu.edu/~lsl/, "
           "2020 capture) points to LLab for 'a list of participants'. Her LTI profile lists no advisees. SCS thesis index: "
           "only CMU-CS-18-100 (Jesse Dunietz, co-chair with Jaime Carbonell; already held); other committees naming her are "
           "member-only. LTI dissertation lists 2012-2026 name no Levin-advised thesis; KiltHub search for 'Lori Levin' "
           "returns no theses."),
)

# ---------------------------------------------------------------------------- Christina Harrington
D["Christina Harrington"] = dict(
    students=[],
    lab_note=("Equity and Health Innovations Design Research Lab (named on her HCII profile and homepage) has no people "
              "page found; HCII profile lists 2 advisees (Adinawa Adjagbodjou, Sanika Moharana), both already held."),
    notes=("christinaharrington.me robots.txt disallows all agents (Squarespace 'User-agent: * Disallow: /'), so only Wayback "
           "captures were read: homepage (2025-10) and About (2024-05) carry no student or lab-member list; the linked CV "
           "(/s/HarringtonCV_Updated-Mar2024.pdf) has no Wayback capture. HCII Centers and Labs page does not list the lab. "
           "No SCS thesis committee (2016-2026 index) and no KiltHub thesis names her. She joined CMU HCII in 2021 (from "
           "DePaul); earlier students are out of scope."),
)
