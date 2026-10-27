"""Berkeley gap decisions, worker ladder_b (11 recently hired ladder PIs), 2026-10-21/22.

Allon Wagner, Max Willsey, Matei Zaharia, Serina Chang, Lijie Chen, Sewon Min, Emma Pierson, Henry Corrigan-Gibbs,
Rishabh Iyer, Jason Lee, Amy Pavel.

Students advised at a previous institution (Stanford, Cornell, MIT, Princeton, UT Austin, UW) are listed only when a
source places them at Berkeley (a Berkeley co-advisor, a Berkeley group roster, or the source itself saying UC
Berkeley); the exclusions are spelled out in each PI's notes.
"""
import sys

sys.path.insert(0, "/n/fs/similarity/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-berkeley")
from dhelp import *  # noqa: E402,F401,F403

D = {}


def orcid_person(oid, name):
    """ORCID person.json: '"displayName":"<name>"' (raw JSON)."""
    return Q(f"https://orcid.org/{oid}/person.json", f'"displayName":"{name}"', raw=True)


def orcid_aff(oid, org_value, name):
    """ORCID affiliationGroups.json: the affiliation entry from its organisation name through the record owner's
    sourceName (raw JSON)."""
    return SE(f"https://orcid.org/{oid}/affiliationGroups.json", f'"value":"{org_value}"', f'"sourceName":"{name}"',
              raw=True)


def pubmatch(page, quote, note, **kw):
    return ID("openalex_verified_by_publication_list", Q(page, quote, **kw), note)


# ============================================================================ Allon Wagner
WL = "https://www.allonwagnerlab.org/"
WLP = WL + "people"
WLP24 = WB + "20241203041749id_/https://www.allonwagnerlab.org/people"
WLPUB = WL + "publications"
D["Allon Wagner"] = dict(
    status="pi",
    status_ev=[Q(WLP, "Lab Members Allon Wagner, PhD Principal Investigator")],
    students=[
        ST("Charles Chien", "phd", None, Q(WLP, "Charles Chien PhD Student (CCB) Previously Undergraduate Researcher (CS)"),
           note="Earlier captures: undergraduate researcher (CS) in Dec 2024, 'incoming PhD student (CCB)' in Oct 2025."),
        ST("Eway Cai", "phd", None, Q(WLP, "Eway Cai PhD Student (MCB)")),
        ST("Daniel Lewinsohn", "phd", None, Q(WLP, "Daniel Lewinsohn PhD Student (CCB; Jointly supervised with Nilah Ioannidis)")),
        ST("Tiffany Lam", "phd", None, Q(WLP, "Tiffany Lam PhD Student (CCB)")),
        ST("Ayesha Bajwa", "phd", None, Q(WLP, "Ayesha Bajwa PhD Student (EECS; Jointly supervised with Nilah Ioannidis)")),
        ST("Abrar Rahman Abir", "phd", None, Q(WLP, "Abrar Rahman Abir PhD Student (EECS)")),
        ST("Steven Lazarevsky", "phd", None, Q(WLP, "Steven Lazarevsky PhD Student (MCB)")),
        ST("Sina Booeshaghi", "postdoc", None, Q(WLP, "Sina Booeshaghi, PhD HHMI Hanna H. Gray Postdoctoral Fellow (BioE & CCB; Jointly with Aaron Streets)")),
        ST("Rachel Coombs", "postdoc", None, Q(WLP, "Rachel Coombs Postdoctoral Fellow (MCB; joint with Ellen Robey)")),
        ST("Christopher Rene Zavala", "undergraduate", None, Q(WLP, "Christopher Rene Zavala Undergraduate Researcher (BioE)")),
        ST("Adelina Chau", "undergraduate", None, Q(WLP, "Adelina Chau Undergraduate Researcher (CS)")),
        ST("Cedric Chan", "member", None, Q(WLP, "Cedric Chan Staff Scientist (EECS & MCB) Previously Undergraduate Researcher (EECS & MCB)"),
           note="Undergraduate researcher in the lab (Dec 2024 capture), now staff scientist."),
        ST("Ali Tout", "undergraduate", [2024, 2024], Q(WLP24, "Ali Tout Undergraduate Researcher (CS)"),
           note="Dec 2024 Wayback capture of the lab People page; listed under Alumni by Oct 2025."),
        ST("Alex Zhao", "other", [2024, 2024], Q(WLP24, "Alex Zhao PhD rotation (CCB)"), note="PhD rotation student (Dec 2024 capture)."),
        ST("Martin Alvarez-Kuglen", "other", [2024, 2025], Q(WLP24, "Martin Alvarez-Kuglen PhD rotation (CCB)"),
           note="PhD rotation student (Dec 2024 and Oct 2025 captures)."),
        ST("Claire LeBlanc", "other", [2024, 2024], Q(WLP24, "Alumni Claire LeBlanc PhD rotation (CCB)"), note="Former PhD rotation student (Dec 2024 capture)."),
    ],
    identity=dict(
        orcid=["0000-0001-5095-6009"], openalex=["A5089647811"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5089647811", "Allon Wagner"),
               "OpenAlex author record (59 works, last institution UC Berkeley; carries ORCID 0000-0001-5095-6009)."),
            pubmatch(WLPUB, "Extracting interpretable single-cell metabolic states with graph-guided representation learning biorxiv 2026 D. P. Lewinsohn, N. Dias, A. Chau , Y. Koike , Z. D. Smith, N. M. Ioannidis, A. Wagner",
                     "A5089647811 work W7214213245 (2026) is on the lab's Publications page (with advisees D. P. Lewinsohn and A. Chau). 8 of the id's 47 works dated 2016+ match that page."),
            pubmatch(WLPUB, "The coming era of nudge drugs for cancer Cancer Cell 2025 T. Courau, A. Desai, A. Wagner",
                     "A5089647811 work W4414122966 (2025)."),
            pubmatch(WLPUB, "Metabolic modeling of single Th17 cells reveals regulators of autoimmunity Cell 2021 A. Wagner",
                     "A5089647811 work W3174064560 (2021)."),
            pubmatch(WLPUB, "Revealing the vectors of cellular identity with single-cell genomics Nature Biotechnology 2016 A. Wagner",
                     "A5089647811 work W2555892463 (2016)."),
            ID("orcid_record", orcid_person("0000-0001-5095-6009", "Allon Wagner"), "ORCID record display name."),
            ID("orcid_record", orcid_aff("0000-0001-5095-6009", "University of California, Berkeley", "Allon Wagner"),
               "ORCID record lists employment at University of California, Berkeley (self-asserted by Allon Wagner)."),
        ]),
    appt=[Q(WL, "The Wagner Lab @ UC Berkeley Interested in working with us?")],
    notes=("Assistant Professor (EECS, with MCB and the Center for Computational Biology affiliations); first EECS-CS "
           "listing 2024; earliest Wayback capture of the lab site is April 2024. No explicit start date found. He was "
           "previously a postdoc at Berkeley (Nir Yosef's group), so pre-2024 Berkeley-affiliated works are postdoc-era. "
           "Lab People page (live, Oct 2026) plus the Dec 2024 Wayback capture give 16 members: 7 PhD students, 2 "
           "postdocs, 3 undergraduates, a former undergraduate now staff scientist, and 3 PhD rotation students. The "
           "pipeline's 'adviser_name_unmatched_or_namesake' is the surname collision with David Wagner (EECS). OpenAlex "
           "A5089647811 verified against the lab Publications page; ORCID verified by the ORCID record (Berkeley employment)."),
)

# ============================================================================ Max Willsey
MW = "https://www.mwillsey.com/"
D["Max Willsey"] = dict(
    status="pi",
    status_ev=[SE(MW, "mwillsey Max Willsey", "I’m an Assistant Professor in EECS at UC Berkeley")],
    students=[
        ST("Russel Arbore", "phd", None, SE(MW, "People I", "Russel Arbore , PhD student")),
        ST("Craig Liu", "phd", None, SE(MW, "People I", "Craig Liu , PhD student")),
        ST("Sarah Morin", "phd", None, SE(MW, "People I", "Sarah Morin , PhD student"),
           note="Also listed as a GSR on the Sky Computing Lab people page."),
        ST("Michael Arntzenius", "postdoc", None, SE(MW, "People I", "Michael Arntzenius , Postdoc")),
        ST("Tyler Hou", "undergraduate", [None, 2026], SE(MW, "People I", "Tyler Hou , ugrad UCB 2026")),
    ],
    identity=dict(
        orcid=["0000-0001-8066-4218"], openalex=["A5048760480"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5048760480", "Max Willsey"),
               "OpenAlex author record (40 works; carries ORCID 0000-0001-8066-4218)."),
            pubmatch(MW, "Finite Functional Programming Michael Arntzenius Max Willsey",
                     "A5048760480 work W7160868806 (2026, with postdoc Michael Arntzenius) is on his homepage paper list; 20 of the id's 35 works dated 2016+ match."),
            pubmatch(MW, "Free Join: Unifying Worst-Case Optimal and Traditional Joins Remy Wang Max Willsey", "A5048760480 work W4381327058 (2023)."),
            pubmatch(MW, "babble: Learning Better Abstractions with E-Graphs and Anti-Unification David Cao Rose Kunkel Chandrakana Nandi Max Willsey",
                     "A5048760480 work W4311248665 (2023)."),
            ID("orcid_record", orcid_person("0000-0001-8066-4218", "Max Willsey"), "ORCID record display name."),
            ID("orcid_record", orcid_aff("0000-0001-8066-4218", "University of California, Berkeley", "Max Willsey"),
               "ORCID employment: University of California, Berkeley, EECS, Assistant Professor, 2024-."),
        ]),
    appt=[Q("https://www.mwillsey.com/cv.html", "Max Willsey [email removed] https://mwillsey.com Blog Google Scholar CV Print Positions Assistant Professor, University of California, Berkeley, 2024–present Postdoctoral Researcher, University of Washington, 2021–2023")],
    notes=("Assistant Professor at Berkeley since 2024 (CV; ORCID 2024-); UW postdoc 2021-2023, so the PhD students and "
           "postdoc on his homepage ('People ... students, including') are Berkeley-era (a postdoc has no PhD advisees). "
           "Tyler Hou is a Berkeley undergraduate ('ugrad UCB 2026'). OpenAlex A5048760480 verified against the homepage "
           "paper list; ORCID verified by the ORCID record."),
)

# ============================================================================ Matei Zaharia
MZ = "https://people.eecs.berkeley.edu/~matei/"
MZ23 = WB + "20231222032031id_/https://people.eecs.berkeley.edu/~matei/"
SKY = "https://sky.cs.berkeley.edu/people/"
_mz_head = "PhD Students and Postdocs"


def mz(name, end, role="phd", note=None):
    return ST(name, role, None, SE(MZ, _mz_head, end), note=note)


D["Matei Zaharia"] = dict(
    status="pi",
    status_ev=[Q(MZ, "Matei Zaharia's Homepage Matei Zaharia Associate Professor of EECS, UC Berkeley")],
    students=[
        mz("Dev Bali", "Dev Bali (with Scott Shenker )", note="Co-advised with Scott Shenker; Sky Lab GSR and NetSys PhD student."),
        mz("Jared Quincy Davis", "Jared Quincy Davis (with Jure Leskovec )",
           note="Co-advisor Jure Leskovec is Stanford faculty; listed as a GSR ('Jared Davis') on the Berkeley Sky Computing Lab people page, which places him at Berkeley."),
        mz("Jiwon Park", "Jiwon Park", note="Sky Computing Lab GSR."),
        mz("Karim Elmaaroufi", "Karim Elmaaroufi (with Sanjit Seshia )", note="Co-advised with Sanjit Seshia (Berkeley); Sky Lab GSR."),
        mz("Lakshya Agarwal", "Lakshya Agarwal (with Dan Klein )", note="Co-advised with Dan Klein (Berkeley); Sky Lab lists 'Lakshya A Agrawal' (GSR)."),
        mz("Liana Patel", "Liana Patel (with Carlos Guestrin )",
           note="Co-advisor Carlos Guestrin is Stanford faculty; listed as a GSR on the Berkeley Sky Computing Lab people page."),
        mz("Melissa Pan", "Melissa Pan", note="Sky Computing Lab GSR."),
        mz("Negar Arabzadeh", "Negar Arabzadeh", role="postdoc", note="Sky Computing Lab postdoc."),
        mz("Parth Asawa", "Parth Asawa", note="Sky Computing Lab GSR."),
        mz("Shangyin Tan", "Shangyin Tan (with Koushik Sen )", note="Co-advised with Koushik Sen (Berkeley); Sky Lab GSR."),
        mz("Soujanya Ponnapalli", "Soujanya Ponnapalli (with Natacha Crooks )", role="postdoc",
           note="Co-advised with Natacha Crooks (Berkeley); the Sky Lab people page lists her as a postdoc."),
        mz("Tyler Griggs", "Tyler Griggs (with Ion Stoica )", note="Co-advised with Ion Stoica (Berkeley); Sky Lab GSR."),
        mz("Wenjie Ma", "Wenjie Ma (with Sewon Min )", note="Co-advised with Sewon Min (her CV: Ph.D. student advising since 01/2025)."),
        mz("Yichuan Wang", "Yichuan Wang (with Joey Gonzalez )", note="Co-advised with Joey Gonzalez (Berkeley); Sky Lab GSR."),
    ],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[SE(MZ23, "Matei Zaharia Interests Teaching Publications Awards Matei Zaharia", "I’m an associate professor at UC Berkeley (previously Stanford)")],
    notes=("Students only (paper side already anchored, 69 in-appointment lab papers). Moved from Stanford to Berkeley in "
           "2023: the Dec 2023 Wayback capture of his Berkeley homepage reads 'associate professor at UC Berkeley "
           "(previously Stanford)'; first EECS-CS listing 2024. Current 'PhD Students and Postdocs' list on his homepage, "
           "each placed at Berkeley by a Berkeley co-advisor and/or the Sky Computing Lab people page (GSR/postdoc). "
           "Excluded: Donghyun Lee (on the current list but no Berkeley placement found), and the whole 'Past PhD Students "
           "and Postdocs' list (Stanford-era: Bailis/Hanrahan/Aiken/Potts/Zou co-advisees)."),
)

# ============================================================================ Serina Chang
SC = "https://serinachang5.github.io/"
SCV = SC + "assets/files/CV.pdf"
_sc_head = "Advising as Faculty, UC Berkeley"
D["Serina Chang"] = dict(
    status="pi",
    status_ev=[Q(SC, "Serina Chang I am an Assistant Professor at UC Berkeley, jointly appointed in EECS and Computational Precision Health")],
    students=[
        ST("Jessie Zixin Li", "phd", [2026, None], SE(SCV, _sc_head, "Jessie (Zixin) Li, UCSF-UC Berkeley Computational Precision Health Program"), must=["Li"],
           note="CV dates column, in order: 2026-present 2024-present 2026-present 2026-present."),
        ST("Joseph Suh", "phd", [2024, None], SE(SCV, _sc_head, "Joseph Suh, UC Berkeley EECS (co-advised with John Canny)")),
        ST("Kelly (Yu Ying) Chiu", "phd", [2026, None], SE(SCV, _sc_head, "Kelly (Yu Ying) Chiu, UC Berkeley EECS (co-advised with Stuart Russell)")),
        ST("Zhining Zhang", "phd", [2026, None], SE(SCV, _sc_head, "Zhining Zhang, UC Berkeley EECS")),
        ST("Bill (Wang) Zhu", "postdoc", [2026, None], SE(SCV, _sc_head, "Postdoc: Bill (Wang) Zhu, UC Berkeley")),
        ST("Ayush Raj", "undergraduate", [2025, None], SE(SCV, _sc_head, "Ayush Raj, UC Berkeley")),
        ST("David Zhai Yang", "undergraduate", [2025, None], SE(SCV, _sc_head, "David Zhai Yang, UC Berkeley")),
        ST("Murari Ganesan", "undergraduate", [2025, 2026], SE(SCV, _sc_head, "Murari Ganesan, UC Berkeley")),
        ST("Erfan Jahanparast", "undergraduate", [2024, 2026], SE(SCV, _sc_head, "Erfan Jahanparast, UC Berkeley")),
        ST("Steven Luo", "undergraduate", [2025, 2026], SE(SCV, _sc_head, "Steven Luo, UC Berkeley")),
        ST("Jonathan Ngai", "undergraduate", [2025, 2026], SE(SCV, "Undergraduate: Ayush Raj, UC Berkeley", "Jonathan Ngai, UC Berkeley")),
        ST("Zhiqing Hong", "other", [2025, 2025], Q(SCV, "Zhiqing Hong, UC Berkeley visiting student, PhD student at Rutgers University"),
           note="Visiting student (Jul-Dec 2025 per the CV dates column)."),
        ST("Enock Niyonkuru", "other", [2025, 2026], Q(SCV, "Visiting students: Enock Niyonkuru, PhD student in UCSF BMI, rotation"),
           note="UCSF BMI PhD rotation student (Dec 2025-Mar 2026 per the CV dates column)."),
    ],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[SE(SCV, "Serina Chang [email removed]", "2025-present Assistant Professor, Department of Electrical Engineering and Computer Sciences (50%)")],
    notes=("Students only (15 in-appointment lab papers already). Assistant Professor since 2025 (EECS 50% / UCSF-UC Berkeley "
           "Computational Precision Health 50%); Stanford PhD 2024, MSR postdoc 2024-2025. Her CV section 'Advising as "
           "Faculty, UC Berkeley' lists 4 PhD students, 1 postdoc, 6 undergraduates and 2 visiting students; the separate "
           "'Research mentees during PhD, Stanford University' block is excluded. Years come from the CV's dates column, "
           "which pdftotext emits after the names, in the same order. The homepage 'Group' section repeats the PhD and "
           "postdoc names. The pipeline's 'adviser_name_unmatched_or_namesake' is the common surname Chang."),
)

# ============================================================================ Lijie Chen
LC = "https://chen-lijie.github.io"
LCV = "https://chen-lijie.github.io/documents/CV.pdf"
LCP = "https://chen-lijie.github.io/papersYear.html"
D["Lijie Chen"] = dict(
    status="not_pi_in_window",
    status_ev=[SE(LCV, "Lijie Chen Curriculum Vitae", "Miller Postdoctoral Fellow, hosted by Avishay Tal and Umesh Vazirani")],
    students=[],
    identity=dict(
        orcid=[], openalex=["A5100611490"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5100611490", "Lijie Chen"),
               "OpenAlex author record (107 works, last institution UC Berkeley). Its ORCID 0000-0002-6084-4729 is not recorded "
               "here: the ORCID record lists only MIT (PhD student), and his pages do not link it."),
            pubmatch(LCP, "Polynomial-Time Pseudodeterministic Construction of Primes [eccc] [my slides] Lijie Chen",
                     "A5100611490 works W4390098057 (2023) / W7138862885 (2026) are on his 'Publications (by Years)' page; 52 of the id's 92 works dated 2016+ match."),
            pubmatch(LCP, "New Algebrization Barriers to Circuit Lower Bounds via Communication Complexity of Missing-String [eccc] Lijie Chen",
                     "A5100611490 work W7125512998 (2026)."),
            pubmatch(LCP, "Symmetric Exponential Time Requires Near-Maximum Circuit Size [eccc] [arxiv] [Hanlin's talk at IAS] [my slides] Lijie Chen",
                     "A5100611490 work W4399522735 (2024)."),
            pubmatch(LCP, "Hardness Magnification for all Sparse NP Languages [eccc] Lijie Chen", "A5100611490 work W2971710618 (2019)."),
        ]),
    appt=[Q(LC, "Lijie Chen I am an Assistant Professor at the Department of Electrical Engineering and Computer Sciences at UC Berkeley.")],
    notes=("NEW FACULTY WITHOUT A STATED ADVISEE (not one of the standard not_pi categories): Assistant Professor since "
           "2025 (CV: '2025–Now ... Assistant Professor'; Miller Postdoctoral Fellow at Berkeley 2022–2025, hosted by Avishay "
           "Tal and Umesh Vazirani). No student, postdoc or mentee is named on his homepage, CV (last updated July 2025), "
           "publication pages or the EECS dissertations page (404); the Berkeley theory-group people page lists students "
           "without advisers; his only EECS tech report (EECS-2026-11, LatentQA) names Jacob Steinhardt as advisor. Re-check "
           "once his first PhD cohort appears. OpenAlex A5100611490 verified (52 title matches); its Berkeley works from "
           "2022-2025 are Miller-postdoc era. Namesake caution: 'Lijie Chen' is common, but every 2022+ work on this id is "
           "complexity theory / AI-theory consistent with him."),
)

# ============================================================================ Sewon Min
SM = "https://www.sewonmin.com/"
SMV = SM + "assets/CV.pdf"
_sm_phd = "Ph.D. Student Advising"
_sm_pre = "Predoctoral Student Advising"
D["Sewon Min"] = dict(
    status="pi",
    status_ev=[Q(SMV, "Sewon Min Department of Electrical Engineering and Computer Sciences University of California, Berkeley")],
    students=[
        ST("Wenjie Ma", "phd", [2025, None], SE(SMV, _sm_phd, "Wenjie Ma (co-advised with Matei Zaharia)")),
        ST("Prasann Singhal", "phd", [2025, None], SE(SMV, _sm_phd, "Prasann Singhal (co-advised with Jacob Steinhardt")),
        ST("Ryan Wang", "phd", [2025, None], SE(SMV, _sm_phd, "Ryan Wang (supported by NSF Graduate Research Fellowship)")),
        ST("Siddharth Gollapudi", "phd", [2026, None], SE(SMV, _sm_phd, "Siddharth Gollapudi (supported by NSF CISE Graduate Fellowship)")),
        ST("Amanda Bertsch", "other", [2026, 2026], Q(SMV, "Visitor & Intern Advising 05/2026–08/2026 01/2025–06/2025 Amanda Bertsch (UC Berkeley & Ai2)"),
           note="Visitor/intern (UC Berkeley & Ai2), 05/2026-08/2026."),
        ST("Tiansheng Hu", "other", [2026, None], SE(SMV, _sm_pre, "Tiansheng Hu, BS student at NYU Shanghai, visiting UC Berkeley"),
           note="Visiting undergraduate (predoctoral advising, 05/2026-)."),
        ST("Haoxiang Sun", "other", [2026, None], SE(SMV, _sm_pre, "Haoxiang Sun, BS student at Renmin University of China, visiting UC Berkeley"),
           note="Visiting undergraduate (04/2026-)."),
        ST("Rajat Rawat", "undergraduate", [2025, None], SE(SMV, _sm_pre, "Rajat Rawat, BS student at UC Berkeley")),
        ST("Akshay N Anand", "undergraduate", [2025, None], SE(SMV, _sm_pre, "Akshay N Anand, BS student at UC Berkeley")),
        ST("Sanjay Adhikesaven", "undergraduate", [2025, None], SE(SMV, _sm_pre, "Sanjay Adhikesaven, BS student at UC Berkeley")),
        ST("Jinjian Liu", "undergraduate", [2025, 2025], SE(SMV, _sm_pre, "Jinjian Liu, BS student at UC Berkeley")),
    ],
    identity=dict(
        orcid=[], openalex=["A5039158419"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5039158419", "Sewon Min"),
               "OpenAlex author record (119 works; no ORCID; last institutions include UC Berkeley and Ai2)."),
            pubmatch(SMV, "Sewon Min, Matei Zaharia. “RAG over Thinking Traces Can Improve Reasoning Tasks",
                     "A5039158419 work W7160406492 (2026) is in her CV publication list; 60 of the id's 87 works dated 2016+ match."),
            pubmatch(SMV, "Sewon Min. “EMO: Pretraining Mixture of Experts for Emergent Modularity", "A5039158419 work W7160663999 (2026)."),
            pubmatch(SMV, "Sewon Min*, Kalpesh Krishna*, Xinxi Lyu, Mike Lewis, Wen-tau Yih, Pang Wei Koh, Mohit Iyyer, Luke Zettlemoyer, Hannaneh Hajishirzi. “FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation",
                     "A5039158419 work W4389519598 (2023)."),
            pubmatch(SMV, "Sewon Min, Ludwig Schmidt, Noah A. Smith, Mike Lewis. “Measuring and Narrowing the Compositionality Gap in Language Models",
                     "A5039158419 work W4389520103 (2023)."),
        ]),
    appt=[SE(SMV, "Sewon Min Department of Electrical Engineering", "07/2025–Current Assistant Professor, UC Berkeley EECS")],
    pi_must=["Sewon Min"],
    notes=("Assistant Professor since 07/2025 (CV), also Ai2 research scientist; UW PhD 2024. CV 'Advising' section: 4 Ph.D. "
           "students (Wenjie Ma co-advised with Matei Zaharia since 01/2025; Prasann Singhal co-advised with Jacob "
           "Steinhardt), a UC Berkeley & Ai2 visitor, and predoctoral advisees (4 UC Berkeley BS students and 2 visiting "
           "undergraduates). Excluded: UW-era mentees (Michael Duan, Xinxi Lyu, Xinyan Yu, Skyler Hallinan, Jungsoo Park, "
           "Belinda Li) and Ai2 intern Kevin Farhat. Years from the CV dates column (emitted in the same order as names). "
           "OpenAlex A5039158419 verified against the CV publication list."),
)

# ============================================================================ Emma Pierson
EP = "https://people.eecs.berkeley.edu/~emmapierson/"
EPG = EP + "group.html"
EPV = EP + "images/resume.pdf"
D["Emma Pierson"] = dict(
    status="pi",
    status_ev=[SE(EPG, "Emma Pierson Toggle navigation", "Current PhD students and postdocs: Raj Movva (PhD student)")],
    students=[
        ST("Rajiv Movva", "phd", None, SE(SMV, "Ph.D. Quals/Dissertation Committee (UC Berkeley)", "Rajiv Movva (adviser: Emma Pierson)"),
           note="Listed as 'Raj Movva (PhD student)' on Pierson's group page; Sewon Min's CV places him in UC Berkeley quals (2025/2026) with adviser Emma Pierson."),
        ST("Marçal Comajoan Cara", "phd", None, SE(EPG, "Current PhD students and postdocs:", "Marçal Comajoan Cara (PhD student; co-advised with Nilah Ioannidis)"),
           note="Co-advised with Nilah Ioannidis (Berkeley EECS); first appears on the 2026 captures of the group page."),
    ],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[SE(EPV, "Emma Pierson [email removed]", "Andrew H. and Ann R. Tisch Assistant Professor at Cornell Tech (on leave) 2024")],
    notes=("Students only (22 in-appointment lab papers already). CV: Zhang Family Endowed Professor / Assistant Professor of "
           "Computer Science at UC Berkeley 2025- (Cornell Tech on leave 2024-; Cornell Tech assistant professor 2021-2024). "
           "Of her group page's current list only two are placed at Berkeley; excluded as Cornell Tech students/postdocs: "
           "Sidhika Balachandar, Gabriel Agostini and Erica Chiang (each co-advised with Nikhil Garg, Cornell Tech), "
           "and past postdocs Smitha Milli and Harini Suresh. Divya Shanmugam (postdoc) is excluded for lack of a source "
           "placing her at Berkeley."),
)

# ============================================================================ Henry Corrigan-Gibbs
HCG = "https://people.eecs.berkeley.edu/~henrycg/"
HCGA = HCG + "alums/"
HCGPUB = HCG + "pubs/"
HMIT25 = WB + "20251210155336id_/https://people.csail.mit.edu/henrycg/"
SEC = "https://security.cs.berkeley.edu/"
D["Henry Corrigan-Gibbs"] = dict(
    status="pi",
    status_ev=[Q(HCG, "Henry Corrigan-Gibbs about me I am an associate professor in the EECS Department at UC Berkeley.")],
    students=[
        ST("Ryan Lehmkuhl", "phd", None, Q(HCG, "students Current: Shinwon Lee Ryan Lehmkuhl"),
           note="His PhD student since MIT (MIT-era homepage lists him under 'PhD students'); the Berkeley security group page lists him among its grad students, placing him at Berkeley."),
        ST("Shinwon Lee", "member", None, Q(HCG, "students Current: Shinwon Lee"),
           note="Current student on the Berkeley homepage; absent from the MIT-era student list (Dec 2025 capture), so a Berkeley-era student. Degree level not stated."),
        ST("Inès Bichon", "other", [2026, 2026], SE(HCGA, "Henry Corrigan-Gibbs Past students and researchers", "visitors Inès Bichon (Spring 2026)"),
           note="Visitor in Spring 2026, after his January 2026 move to Berkeley."),
    ],
    identity=dict(
        orcid=[], openalex=["A5010212636"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5010212636", "Henry Corrigan-Gibbs"),
               "OpenAlex author record (75 works; only author id for the name). Its ORCID 0009-0006-7577-4512 is not recorded: "
               "the ORCID record has no affiliations and his pages do not link it."),
            pubmatch(HCGPUB, "The Structured Generic-Group Model Henry Corrigan-Gibbs",
                     "A5010212636 work W7160378346 (2026) is on his Research Papers page; 23 of the id's 33 works dated 2016+ match."),
            pubmatch(HCGPUB, "Private Analytics via Streaming, Sketching, and Silently Verifiable Proofs Mayank Rathee, Yuwen Zhang, Henry Corrigan-Gibbs",
                     "A5010212636 work W4402264233 (2024)."),
            pubmatch(HCGPUB, "Single-Server Private Information Retrieval with Sublinear Amortized Time Henry Corrigan-Gibbs",
                     "A5010212636 work W4285201849 (2022)."),
            pubmatch(HCGPUB, "Zero-Knowledge Proofs on Secret-Shared Data via Fully Linear PCPs Dan Boneh, Elette Boyle, Henry Corrigan-Gibbs",
                     "A5010212636 work W2969140724 (2019)."),
        ]),
    appt=[SE(HMIT25, "Henry Corrigan-Gibbs Henry Corrigan- Gibbs", "update: Starting in January 2026, I will be a member of the EECS department at UC Berkeley!"),
          SE("https://people.eecs.berkeley.edu/~henrycg/bio.txt", "Henry Corrigan-Gibbs (he/him) is an associate professor at UC Berkeley", "a faculty member in MIT's EECS Department")],
    notes=("Associate Professor at Berkeley since January 2026 (MIT 2020-2025). Only 2026 papers can be Berkeley lab papers. "
           "Students: Ryan Lehmkuhl (MIT PhD student who appears on the Berkeley security group's grad-student roster), "
           "Shinwon Lee (Berkeley-era) and visitor Inès Bichon. Excluded: Alexandra Henzinger (MIT PhD, now EPFL faculty; "
           "on the Aug 2026 'Current' list) and all MIT-era postdocs/undergraduates on his alums page. Security group roster: "
           f"{SEC}. OpenAlex A5010212636 verified against his Research Papers page."),
)

# ============================================================================ Rishabh Iyer
RI = "https://rishabh246.github.io/"
RIP = RI + "publications/"
D["Rishabh Iyer"] = dict(
    status="not_pi_in_window",
    status_ev=[Q(RI, "Rishabh Iyer Assistant Professor UC Berkeley Follow Email LinkedIn Github Google Scholar I am an Assistant Professor in the Electrical Engineering and Computer Sciences department at UC Berkeley . Prior to joining Berkeley, I completed my PhD at EPFL"),
               Q("https://netsys.cs.berkeley.edu/", "The NetSys Lab is directed by faculty members Rishabh Iyer , Sylvia Ratnasamy , and Scott Shenker .")],
    students=[],
    identity=dict(
        orcid=["0009-0008-5599-8636"], openalex=["A5007631563"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5007631563", "Rishabh Iyer"),
               "OpenAlex author record (15 works, EPFL then UC Berkeley; carries ORCID 0009-0008-5599-8636)."),
            pubmatch(RIP, "CrossCheck: Input Validation for WAN Control Systems Alexander Krentsel, Rishabh Iyer",
                     "A5007631563 work W7134224580 (2026) is on his Publications page; all 13 of the id's works dated 2016+ match."),
            pubmatch(RIP, "Rethinking the Cost of Distributed Caches for Datacenter Services Ziming Mao, Jonathan Ellithorpe, Atul Adya, Rishabh Iyer",
                     "A5007631563 work W4416298038 (2025)."),
            pubmatch(RIP, "Achieving Microsecond-Scale Tail Latency Efficiently with Approximate Optimal Scheduling Rishabh Iyer",
                     "A5007631563 work W4387302697 (2023)."),
            ID("orcid_record", orcid_person("0009-0008-5599-8636", "Rishabh Iyer"), "ORCID record display name."),
            ID("orcid_record", orcid_aff("0009-0008-5599-8636", "University of California, Berkeley", "Rishabh Iyer"),
               "ORCID record lists employment at University of California, Berkeley."),
        ]),
    appt=[],
    notes=("NEW FACULTY WITHOUT A STATED ADVISEE (not one of the standard not_pi categories): CV gives Assistant Professor "
           "at UC Berkeley July 2025 - present, after a Berkeley postdoc March 2024 - June 2025 (supervisor Sylvia "
           "Ratnasamy); EPFL PhD 2023. His homepage says he 'will be hiring several PhD students in the upcoming "
           "admissions cycle (2025-26)', i.e. first students arrive Fall 2026. No advisee is named on his homepage, CV, "
           "publications page or the NetSys people page (which lists students without advisers); no EECS dissertations or "
           "publications page exists. OpenAlex A5007631563 verified; a second id A5153658383 (one 2026 Berkeley paper, "
           "'LeapQuant', not on his list) is NOT anchored. Namesake: Rishabh Iyer of UT Dallas (A5000529247, 111 works) is a "
           "different person, which is likely behind the pipeline's 'adviser_name_unmatched_or_namesake'."),
)

# ============================================================================ Jason Lee
JL = "https://jasondlee88.github.io/"
JLG = JL + "group.html"
JLP = JL + "publications.html"
_jl_head = "Group Members Students"
D["Jason Lee"] = dict(
    status="pi",
    status_ev=[Q(JL, "Jason D. Lee Associate Professor, EECS and Statistics .")],
    students=[
        ST("Jongho Park", "phd", None, SE(JLG, _jl_head, "Jongho Park jointly advised with Song Mei."),
           note="Co-advisor Song Mei is Berkeley Statistics/EECS faculty."),
        ST("Hengyu Fu", "phd", None, SE(JLG, _jl_head, "Hengyu Fu jointly advised with Song Mei."), note="Co-advised with Song Mei (Berkeley)."),
        ST("Juno Kim", "phd", None, SE(JLG, _jl_head, "Juno Kim jointly advised with Song Mei."), note="Co-advised with Song Mei (Berkeley)."),
        ST("Druv Pai", "phd", None, SE(JLG, _jl_head, "Druv Pai jointly advised with Yi Ma and Jiantao Jiao."),
           note="Song Mei's group page lists Druv Pai as 'EECS PhD; Advised by Yi Ma and Jiantao Jiao' (Berkeley)."),
        ST("Philip Amortila", "postdoc", None, SE(JLG, _jl_head, "Postdocs Philip Amortila jointly with Peter Bartlett."),
           note="Co-hosted with Peter Bartlett (Berkeley)."),
    ],
    identity=dict(
        orcid=["0000-0003-0064-7800"], openalex=["A5059740024"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5059740024", "Jason D. Lee"),
               "OpenAlex author record 'Jason D. Lee' (245 works; carries ORCID 0000-0003-0064-7800)."),
            pubmatch(JLP, "Sharp Capacity Scaling of Spectral Optimizers in Learning Associative Memory. Juno Kim, Eshaan Nichani, Denny Wu, Alberto Bietti, Jason D. Lee",
                     "A5059740024 work W7143480655 (2026, with advisee Juno Kim) is on his Publications page; 148 of the id's 197 works dated 2016+ match."),
            pubmatch(JLP, "Fine-Tuning Dynamics of In-Context Factual Recall in Transformers. Ruomin Huang, Eshaan Nichani, Jason D. Lee",
                     "A5059740024 work W7162652628 (2026)."),
            pubmatch(JLP, "A Kernelized Stein Discrepancy for Goodness-of-fit Tests and Model Evaluation . Qiang Liu, Jason D. Lee",
                     "A5059740024 work W2441221256 (2016)."),
            ID("orcid_record", orcid_person("0000-0003-0064-7800", "Jason Lee"), "ORCID record display name."),
            ID("orcid_record", orcid_aff("0000-0003-0064-7800", "UC Berkeley", "Jason Lee"),
               "ORCID employment: UC Berkeley, EECS and Statistics, Associate Professor, 2025- (also lists USC 2016-2019 and the 2015-2016 Berkeley postdoc)."),
        ]),
    appt=[SE(JL, "Jason D. Lee Associate Professor, EECS and Statistics", "an associate professor at Princeton.")],
    notes=("Associate Professor of EECS and Statistics since 2025 (CV '2025–current'; ORCID 2025-); previously Princeton "
           "(2019-2025), USC (2016-2019), Berkeley postdoc with Michael Jordan (2015-2016); Simons Institute Senior "
           "Scientist from July 2026. Group page (Sept 2026): Berkeley-placed students are those co-advised with Berkeley "
           "faculty (Song Mei; Yi Ma and Jiantao Jiao) plus postdoc Philip Amortila (with Peter Bartlett). Excluded as "
           "Princeton students: Wenhao Zhan and Eshaan Nichani (Princeton ECE, co-advised with Yuxin Chen per his CV), and "
           "Zixuan Wang and Yunwei Ren (no Berkeley placement found); the CV's 'PhD Supervision'/'Postdoctoral Supervision' "
           "lists are all Princeton. Namesakes: several OpenAlex 'Jason Lee' ids exist; A5059740024 ('Jason D. Lee') is the "
           "verified one (148 title matches)."),
)

# ============================================================================ Amy Pavel
AP = "https://amypavel.com/"
APV = AP + "docs/pavel-cv.pdf"
_ap_head = "UNDERGRADUATE AND MASTERS STUDENT ADVISING"
D["Amy Pavel"] = dict(
    status="pi",
    status_ev=[SE(APV, "Amy Pavel 11 PHD STUDENT ADVISING", "Undergraduate Student (Jacobs Design Scholar), UC Berkeley")],
    students=[
        ST("Sampurn (Sam) Bhowmick", "undergraduate", [2026, None],
           SE(APV, _ap_head, "Sampurn (Sam) Bhowmick. “Accessible Robot Communication.” Undergraduate Student (Jacobs Design Scholar), UC Berkeley"),
           must=["Bhowmick"]),
        ST("Brian Chu", "other", [2026, None], SE(APV, _ap_head, "Brian Chu. “Co-Designing Agents for People Experiencing Demand Avoidance.” Post-Bachelor Scholar, UC Berkeley"),
           note="Post-bachelor scholar, January 2026 - present."),
        ST("Anika Bhagavatula", "masters", [2026, None], SE(APV, _ap_head, "Anika Bhagavatula. “Sychophancy in Multimodal Models for Blind People.” Master’s Student, UC Berkeley")),
        ST("Suk Min Huang", "masters", [2026, None], SE(APV, _ap_head, "Suk Min Huang. “Legible Computer Use Agents.” Master’s Student, UC Berkeley")),
    ],
    identity=dict(
        orcid=[], openalex=["A5014816733"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5014816733", "Amy Pavel"),
               "OpenAlex author record (72 works). Its ORCID 0000-0002-3908-4366 is not recorded: the ORCID record has no "
               "affiliations and her pages do not link it."),
            pubmatch(AP, "A11y-CUA Dataset: Characterizing the Accessibility Gap in Computer Use Agents Ananya Gubbi Mohanbabu * , Rosiana Natalie * , Brandon Kim , Anhong Guo , Amy Pavel",
                     "A5014816733 work W7128626332 (2026) is on her homepage publication list; 47 of the id's 59 works dated 2016+ match."),
            pubmatch(AP, "GenAssist: Making Image Generation Accessible Mina Huh , Yi-Hao Peng , Amy Pavel", "A5014816733 work W4387801394 (2023)."),
            pubmatch(AP, "Saliency in VR: How do people explore virtual environments? Vincent Sitzmann , Ana Serrano , Amy Pavel",
                     "A5014816733 work W2561270043 (2018)."),
        ]),
    appt=[Q(APV, "Amy Pavel University of California, Berkeley Assistant Professor Department of Electrical Engineering and Computer Sciences")],
    notes=("Assistant Professor at Berkeley since July 2025 (CV: 'July 2025-Present'); UT Austin Assistant Professor January "
           "2022-June 2025; Berkeley EECS PhD 2019 (her 2016-2018 Berkeley undergraduate mentees predate her PI role and are "
           "excluded). Berkeley advisees from the CV's 'Undergraduate and Masters Student Advising' list: 1 undergraduate, 1 "
           "post-bachelor scholar, 2 master's students. Excluded: all 5 PhD students (Meng Chen, Ananya Gubbi Mohanbabu, "
           "Karim Benharrak, Mina Huh: UT Austin; Yi-Hao Peng: CMU) and the UT Austin masters/undergraduates and "
           "'Recent Alumni' shown on her homepage; KTH visiting master's student Oskar Hokkanen Eriksson (no Berkeley "
           "placement stated). OpenAlex A5014816733 verified against the homepage publication list."),
)
