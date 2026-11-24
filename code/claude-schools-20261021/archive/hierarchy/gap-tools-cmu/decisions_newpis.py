"""Decisions for the two CMU PIs added after the yearly-listing completeness check (2026-10-22): Yuanzhi Li, Charles Kemp.

Same spec conventions as decisions.py (Q = exact quote, SE = start/end markers, ST = student, ID = identity evidence);
append_newpis.py resolves them against hierarchy/cmu/gap-captures.sqlite and appends one row per PI to gap-evidence.json.
"""
from decisions import Q, SE, ST, ID, WB  # noqa: F401

D = {}

# ------------------------------------------------------------------------------------------------ Yuanzhi Li (MLD)
MLD_PHD = "https://www.ml.cmu.edu/people/phd-students.html"
MLD_PHD_2022 = WB + "20220528094210id_/" + MLD_PHD
MLD_PHD_2023 = WB + "20231206001655id_/" + MLD_PHD
YL_HP = WB + "20220814161716id_/https://www.andrew.cmu.edu/user/yuanzhil/"
TYE_THESIS = "https://ml.cmu.edu/research/phd-dissertation-pdfs/tye2_phd_ml_2025.pdf"
ZW_THESIS = "https://ml.cmu.edu/research/phd-dissertation-pdfs/zixinw_ml_phd_thesis_2026.pdf"
MLD_CORE_2019 = WB + "20190920145845id_/https://www.ml.cmu.edu/people/core-faculty.html"
MLD_CORE_2024 = WB + "20240409190911id_/https://www.ml.cmu.edu/people/core-faculty.html"
OA_YL = "https://api.openalex.org/authors/A5101879892"

D["Yuanzhi Li"] = dict(
    status="pi",
    status_ev=[
        Q(MLD_PHD_2023, "Tian Ye Tsinghua University B.E. in Computer Science Advisor: Yuanzhi Li"),
        Q(MLD_PHD_2023, "Zixin Wen University of International Business and Economics in China B.A. in Financial Mathematics Advisors: Yuanzhi Li & Yuejie Chi"),
        Q(ZW_THESIS, "Yuanzhi Li for shaping my research taste, teaching me its foundations, and providing me the opportunity to work in the field of deep learning."),
    ],
    students=[
        ST("Zixin Wen", "phd", [2022, 2023],
           Q(MLD_PHD_2022, "Zixin Wen University of International Business and Economics in China B.A. in Financial Mathematics Advisors: Yuanzhi Li & Yuejie Chi"),
           note=("MLD PhD student list: 'Advisor: TBD' in the 2021-09-28 capture; 'Advisors: Yuanzhi Li & Yuejie Chi' in the "
                 "2022-05-28, 2022-12-08, 2023-05-30 and 2023-12-06 captures; 'Advisors: Yuejie Chi & Aarti Singh' from the "
                 "2024-02-23 capture on. PhD in Machine Learning 2026 (CMU-ML-26-111, co-chairs Singh and Chi); the thesis "
                 "acknowledges Yuanzhi Li for 'shaping my research taste'.")),
        ST("Tian Ye", "phd", [2022, 2023],
           Q(MLD_PHD_2022, "Tian Ye Tsinghua University B.E. in Computer Science Advisor: Yuanzhi Li"),
           note=("Same MLD captures: 'Advisor: Yuanzhi Li' 2022-05-28 through 2023-12-06; 'Advisor: Bhiksha Ramakrishan' from "
                 "2024-02-23. PhD in Machine Learning 2025 (CMU-ML-25-111); Yuanzhi Li sits on the thesis committee with "
                 "affiliation 'Meta'.")),
    ],
    identity=dict(dblp=["https://dblp.org/pid/73/3628"], orcid=[], openalex=["A5101879892"], evidence=[
        ID("openalex_author", SE(OA_YL, '"id":"https://openalex.org/A5101879892"', '"display_name":"Yuanzhi Li"', raw=True),
           "OpenAlex author record (163 works). Its affiliation history also lists MBZUAI 2024-2026, Rutgers 2025 and HKU 2023, "
           "so the profile may merge namesakes; accept works by title match or CMU/Microsoft/Princeton affiliation."),
        ID("openalex_verified", SE(YL_HP, "Yuanzhi Li I'm a Assistant Professor", "A Convergence Theory for Deep Learning via Over-Parameterization", long=True),
           "W2899748887 (author A5101879892) is the first paper on his CMU homepage list (Wayback 2022-08-14); 29 title matches in total."),
        ID("openalex_verified", SE(YL_HP, "Yuanzhi Li I'm a Assistant Professor", "Learning and Generalization in Overparameterized Neural Networks, Going Beyond Two Layers", long=True),
           "W2900103278 (author A5101879892), second paper on the same list."),
        ID("openalex_verified", SE(YL_HP, "Yuanzhi Li I'm a Assistant Professor", "On the Convergence Rate of Training Recurrent Neural Networks", long=True),
           "W2898324627 (author A5101879892), third paper on the same list."),
    ]),
    appt=[
        Q(MLD_CORE_2019, "Yuanzhi Li Assistant Professor, Machine Learning, School of Computer Science"),
        SE(YL_HP, "Yuanzhi Li I'm a Assistant Professor in the Machine Learning Department at CMU.", "(20180-2019)."),
        Q(MLD_CORE_2024, "Yuanzhi Li Assistant Professor, Machine Learning, School of Computer Science"),
        SE(TYE_THESIS, "Thesis Committee Bhiksha Raj, Chair", "Yuanzhi Li Meta"),
    ],
    notes=("Assistant Professor in MLD from 2019 (postdoc at Stanford 2018-2019 per his homepage); listed on the MLD core-faculty "
           "page 2019 through the 2024-04-09 capture. His two MLD PhD students (Zixin Wen, Tian Ye) were reassigned to other "
           "advisers between the 2023-12-06 and 2024-02-23 captures of the MLD PhD list, and by July 2025 he sits on Tian Ye's "
           "committee with affiliation Meta: he left CMU around the start of 2024. The pipeline's 'adviser_name_unmatched' cause "
           "is because the advising is only visible in archived MLD PhD-list captures (the live list is JS-rendered from "
           "phd-students-index.v1.json and alumni-phd-index.v1.json, which now carry the later advisers). No other advisee found: "
           "SCS theses index (CS/ML 2016-2020/ISR series) has no chair 'Yuanzhi'; KiltHub search 'Yuanzhi Li' returned no "
           "thesis with him as adviser. His homepage links no ORCID; OpenAlex reports ORCID 0000-0002-4604-0468 (not "
           "checked against his own page)."),
)

# ------------------------------------------------------------------------------------------------ Charles Kemp (Psychology; MLD affiliated)
KEMP_2016 = WB + "20160418163247id_/http://www.psy.cmu.edu/~ckemp/"
KEMP_2017 = WB + "20170717183205id_/http://www.psy.cmu.edu:80/~ckemp/"
KEMP_2018_06 = WB + "20180607161007id_/http://www.psy.cmu.edu:80/~ckemp/"
KEMP_2018_10 = WB + "20181010224210id_/http://www.psy.cmu.edu:80/~ckemp/"
KEMP_NOW = "http://www.charleskemp.com/"
MLD_AFF_2018 = WB + "20180314012330id_/http://www.ml.cmu.edu:80/people/affiliated-faculty.html"
OA_CK = "https://api.openalex.org/authors/A5080087902"

D["Charles Kemp"] = dict(
    status="not_pi_in_window",
    status_ev=[
        SE(KEMP_2018_06, "Charles Kemp I am an Associate Professor at CMU's Department of Psychology .", "In July 2018 I will move to the School of Psychological Sciences at the University of Melbourne."),
        SE(KEMP_2018_10, "Charles Kemp After 10 wonderful years", "I have moved to the School of Psychological Sciences at the University of Melbourne."),
        Q(KEMP_NOW, "Charles Kemp I work at the School of Psychological Sciences at the University of Melbourne."),
    ],
    students=[],
    identity=dict(dblp=["https://dblp.org/pid/78/4319"], orcid=[], openalex=["A5080087902"], evidence=[
        ID("openalex_author", SE(OA_CK, '"id":"https://openalex.org/A5080087902"', '"display_name":"Charles Kemp"', raw=True),
           "OpenAlex author record (255 works; CMU 2008-2018, Melbourne 2018-2026). Its alternative names include 'C. Gratton "
           "Kemp' and 'Charles F. Kemp', so the profile likely merges namesakes: accept works only by title match to his list "
           "or a CMU/Melbourne affiliation."),
        ID("openalex_verified", Q(KEMP_2017, "Regier, T., Carstensen, A. & Kemp C. (2016). Languages support efficient communication about the environment: Words for snow revisited"),
           "W2339609277 (author A5080087902, CMU affiliation) on his CMU homepage list (Wayback 2017-07-17)."),
        ID("openalex_verified", Q(KEMP_2017, "Jern, A., Lucas, C. G., & Kemp, C. (in press). People learn other people's preferences through inverse decision-making"),
           "W2626006336 (2017, CMU affiliation)."),
        ID("openalex_verified", Q(KEMP_2018_10, "Kemp C., Xu Y. & Regier, T. (2018). Semantic typology and efficient communication"),
           "W2622700781 (2018, CMU affiliation)."),
        ID("openalex_verified", Q(KEMP_2018_10, "Navarro, D. J. & Kemp C. (2017). None of the above: A Bayesian account of the detection of novel categories"),
           "W2734810719 (2017, CMU affiliation) on his CMU homepage list (Wayback 2018-10-10)."),
        ID("openalex_verified", Q(KEMP_NOW, "Kemp, C., Regier, T. & Tishby, N. (2018). Efficient compression in color naming and its evolution"),
           "W2882987577 (2018, CMU affiliation) on his current homepage; 65 title matches between A5080087902 and charleskemp.com."),
    ]),
    appt=[
        Q(KEMP_2016, "Charles Kemp Charles Kemp I am an Associate Professor at CMU's Department of Psychology ."),
        Q(MLD_AFF_2018, "Charles Kemp Associate Professor, Psychology, Dietrich College of Humanities and Social Sciences"),
        SE(KEMP_2018_06, "Charles Kemp I am an Associate Professor", "In July 2018 I will move to the School of Psychological Sciences at the University of Melbourne."),
    ],
    notes=("Associate Professor of Psychology (MLD affiliated faculty) until July 2018, then University of Melbourne. No stated "
           "student, postdoc or advisee at CMU in 2016-2018 was found: his CMU homepage (Wayback 2016-04, 2017-07, 2018-02, "
           "2018-06) has no lab or people section; the Psychology graduate-student pages (Wayback 2016-01-23, 2016-11-08, "
           "2017-10-06; the 2017 one gives every student's 'Advisor :') name no Kemp advisee; the MLD PhD-student pages "
           "(2016-07-23, 2017-07-07) list no Kemp advisee; the SCS theses index (622 theses 2016-2026) has no Kemp on any "
           "committee; a KiltHub thesis search for 'Kemp' (171 hits) found none with Kemp as adviser. "
           "His 2016-2018 co-authors are outside CMU in OpenAlex (Regier, Carstensen, Navarro, Zaslavsky, Tishby; Jern at "
           "Rose-Hulman, Lucas at Edinburgh, Yang Xu at Toronto); Caleb Eddy (CogSci 2017 co-author) has no stated role. Judged not a PI in the window: no in-window "
           "group member or advisee is stated anywhere. For papers: OpenAlex re-dates many of his 2007-2012 NIPS/CogSci "
           "papers to 2018 (e.g. 'Bayesian Belief Polarization', 'Learning Causal Schemata'); only genuinely 2016-2018 works "
           "should be attributed to the CMU appointment. No ORCID is linked from his own pages; OpenAlex reports "
           "0000-0001-9683-8737 (unchecked)."),
)
