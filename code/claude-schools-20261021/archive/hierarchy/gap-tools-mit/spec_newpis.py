"""Researched facts for the four MIT EECS (AI+D) PIs added after the yearly-listing completeness check (2026-10-22):
Sangeeta Bhatia, George Verghese, Sanjoy Mitter, Priya Donti. Same conventions as spec_mit.py (each fact names its stored
source and the regex that finds its verbatim quote); append_newpis.py appends the rows to hierarchy/mit/gap-evidence.json.
"""
import re
from urllib.parse import urlencode

from evlib import ev, student as S, idev, appt, dspace_student as DS

WB = "https://web.archive.org/web/"
OA = "https://api.openalex.org/"
DSPACE_Q = "dc.contributor.advisor:(Bhatia OR Verghese OR Mitter OR Donti)"
# the stored DSpace@MIT discover search (same URL builder as dspace_search.url_for; 15 theses, 2016-2026)
DSPACE = "https://dspace.mit.edu/server/api/discover/search/objects?" + urlencode(
    {"query": DSPACE_Q, "dsoType": "ITEM", "size": 100, "page": 0, "f.dateIssued": "[2016 TO 2026],equals",
     "sort": "dc.date.issued,ASC"})
LISTING_2023 = WB + "20230408143314id_/https://www.eecs.mit.edu/role/faculty/"


def oa_author(aid):
    return OA + "authors/" + aid


def oa_rx(aid, display):
    return '"id":"https://openalex\\.org/' + aid + '".{0,400}?"display_name":"' + display + '"'


SPEC, EXTRA = {}, {}

# ------------------------------------------------------------------------------------------------ Sangeeta Bhatia
LMRT = "https://lmrt.mit.edu/"
TEAM = "https://www.lmrt.mit.edu/team"
LMRT_PUBS = "https://www.lmrt.mit.edu/publications"
BH_EECS = "https://www.eecs.mit.edu/people/sangeeta-bhatia/"
_cur = "current member on the LMRT 'Meet our team' page (live, fetched 2026-10-22)"
bh_team = [
    ("Sydney Hummel", "phd", r"Sydney Hummel Graduate Student", None),
    ("Daniel Kim", "phd", r"Daniel Kim Graduate Student \(MD/PhD\)", None),
    ("Lucia Castello-Pedrero", "phd", r"Lucia Castello-Pedrero Graduate Student \(HST-MEMP\)", None),
    ("Emma McDougal", "phd", r"Emma McDougal Graduate student \(PhD at MIT in Chemical Engineering, co-advised by Paula Hammond\)", None),
    ("Savan Patel", "phd", r"Savan Patel Graduate Student \(HST-MEMP\)", None),
    ("Arya Rao", "phd", r"Arya Rao Graduate student \(MD-PhD co-advised by Pardis Sabeti\)", "Harvard MD-PhD student (hms.harvard.edu address) co-advised with Pardis Sabeti"),
    ("Ju Yeon Chung", "postdoc", r"Ju Yeon Chung Postdoctoral Researcher", None),
    ("Susanna Elledge", "postdoc", r"Susanna Elledge Postdoctoral researcher", None),
    ("Constantine Tzouanas", "postdoc", r"Constantine Tzouanas Postdoctoral Researcher", None),
    ("Vardhman Kumar", "postdoc", r"Vardhman Kumar Postdoctoral Researcher", None),
    ("Florian Huwyler", "postdoc", r"Florian Huwyler Postdoctoral Researcher", None),
    ("Vanessa Kelley", "postdoc", r"Vanessa Kelley Postdoctoral Researher \(co-advised by Viktor Adalsteinsson\)", "Broad Institute address; co-advised with Viktor Adalsteinsson"),
    ("Kasturi Chakraborty", "postdoc", r"Kasturi Chakraborty Postdoctoral Researcher", None),
    ("Gabrielle Grifno", "postdoc", r"Gabrielle Grifno Postdoctoral Researcher", None),
    ("Tahoura Samad", "postdoc", r"Tahoura Samad Postdoctoral Researcher", None),
    ("TianDuo Wang", "postdoc", r"TianDuo Wang Postdoctoral Researcher", "Broad Institute address"),
    ("Sahil Patel", "other", r"Sahil Patel Clinical Fellow \(co-advised by Viktor Adalsteinsson\)", "clinical fellow (MGH address), co-advised with Viktor Adalsteinsson"),
]
bh_theses = [
    ("Warren, Andrew David", "Andrew David Warren", 2016, "PhD in Biomedical Engineering, Harvard-MIT HST"),
    ("Ramanan, Vyas", "Vyas Ramanan", 2016, "PhD in Biomedical Engineering, Harvard-MIT HST"),
    ("Gural, Nil.", "Nil Gural", 2019, "PhD, Harvard-MIT HST"),
    ("Chhabra, Arnav.", "Arnav Chhabra", 2019, "PhD in Medical Engineering and Medical Physics, HST"),
    ("Buss, Colin G.", "Colin G. Buss", 2020, "PhD, Harvard-MIT HST"),
    ("Kirkpatrick, Jesse D.", "Jesse D. Kirkpatrick", 2020, "PhD in Medical Engineering and Medical Physics, HST"),
    ("Chen, Amanda X.", "Amanda X. Chen", 2021, "PhD, Biological Engineering; co-supervised with Robert S. Langer"),
    ("Anahtar, Melodi N.", "Melodi N. Anahtar", 2022, "PhD"),
    ("Martin Alonso, Maria Carmen", "Maria Carmen Martin Alonso", 2024, "PhD"),
    ("Westerfield, Ashley D.", "Ashley D. Westerfield", 2025, "PhD"),
]
SPEC["Sangeeta Bhatia"] = dict(
    status="pi",
    status_evidence=[ev(LMRT, r"The Laboratory for Multiscale Regenerative Technologies \(LMRT\), led by Sangeeta Bhatia, is dedicated to leveraging miniaturization tools to impact human health\.", "Sangeeta Bhatia"),
                     ev(TEAM, r"Meet our team Sangeeta Bhatia, M\.D\., Ph\.D\. Principal investigator John J\. and Dorothy Wilson Professor of Engineering Director, Laboratory for Multiscale Regenerative Technologies", "Sangeeta Bhatia")],
    students=[S(n, r, None, TEAM, rx, note=_cur + ("; " + extra if extra else "")) for n, r, rx, extra in bh_team]
             + [DS(DSPACE, a, r"Bhatia", "phd", y, dn, note=f"DSpace@MIT thesis, supervisor field names Bhatia ({deg})") for a, dn, y, deg in bh_theses],
    identity=dict(dblp=[], orcid=[], openalex=["A5039958236"],
                  evidence=[idev("openalex_author", oa_author("A5039958236"), oa_rx("A5039958236", "Sangeeta N\\. Bhatia"), "Sangeeta N. Bhatia",
                                 "OpenAlex author record (584 works); 115 of its 2016+ titles are on the LMRT publications page")]
                  + [idev("own_publication_list_match", LMRT_PUBS, rx, "Bhatia", f"OpenAlex {w} (author A5039958236) is on the LMRT publications page")
                     for w, rx in [("W2480697384", r"Bhatia, S\. N\. Journal of Biomolecular Screening \(2016\) Manuscript \(PDF\) Read more → August 4, 2016 August 4, 2016 Synchronized cycles of bacterial lysis for in vivo delivery"),
                                   ("W2970241755", r"Bhatia, F\. J\. Slack Oncotarget \(2019\) Manuscript \( 2019 \) Read more → September 3, 2019 September 2, 2019 Renal clearable catalytic gold nanoclusters for in vivo disease monitoring"),
                                   ("W4220903131", r"Early detection of cancer March 23, 2022 David Crosby, Sangeeta Bhatia")]]),
    appointment_notes=[appt(BH_EECS, r"Sangeeta Bhatia People Faculty Faculty AI\+D Faculty CS Faculty EE Faculty Emeritus Lecturers Leadership Staff Instructors John and Dorothy Wilson Professor of Electrical Engineering and Computer Sciences & Health Sciences and Technology, \[EE and AI\+D\]", "Bhatia"),
                       appt(TEAM, r"Sangeeta N\. Bhatia MD, PhD is an inventor, Massachusetts Institute of Technology professor and biotech entrepreneur", "Bhatia")],
    notes=("Runs the Laboratory for Multiscale Regenerative Technologies (Koch Institute; EECS + IMES/HST). Listed EECS faculty 2016-2026. "
           "Students: 17 current LMRT trainees from the live team page (6 graduate students, 10 postdocs, 1 clinical fellow; staff, "
           "technicians and the research scientist are left out) and 10 dated PhD theses 2016-2025 from DSpace@MIT whose supervisor "
           "field is 'Sangeeta N. Bhatia.' / 'Bhatia, Sangeeta (N.)' (one combined supervisor search, stored, 15 hits for "
           "Bhatia/Verghese/Mitter/Donti). Most of her students are in HST, Biological or Chemical Engineering rather than EECS. "
           "The team page's undated alumni list (e.g. Ava Soleimany Amini, Carmen Martin-Alonso, Ashley Westerfield) is not used "
           "beyond the dated theses. No ORCID is linked from her own pages; OpenAlex reports 0000-0002-1293-2097 (unchecked). "
           "No DBLP profile (biomedical engineer)."),
)
EXTRA["Sangeeta Bhatia"] = dict(status_basis="students_found", needs_after_research=[],
                                pipeline_actions=["accept researched students (LMRT team page; DSpace theses)", "add OpenAlex A5039958236"])

# ------------------------------------------------------------------------------------------------ George Verghese
CPCI = "https://cpci.mit.edu/people"
CPCI_2016 = WB + "20161018185245id_/http://www.rle.mit.edu:80/cpci/people/"
CPCI_PUBS = "https://cpci.mit.edu/publications/"
RLE = "http://www.rle.mit.edu/verghese"
GV_EECS = "https://www.eecs.mit.edu/people/george-verghese/"
_cpci = ("listed as a current member of the Computational Physiology and Clinical Inference Group (co-led by Verghese and "
         "Thomas Heldt) in the Wayback capture of 2016-10-18 (same list on 2018-01-01); the page does not say which of the two "
         "PIs advises them")
SPEC["George Verghese"] = dict(
    status="pi",
    status_evidence=[ev(CPCI, r"Computational Physiology and Clinical Inference Group Prof\. George Verghese and Prof\. Thomas Heldt", "George Verghese"),
                     ev(RLE, r"George Verghese received his BTech.{0,300}?Since 1979, he has been with the Massachusetts Institute of Technology", "George Verghese")],
    students=[DS(DSPACE, "Mieloszyk, Rebecca Jennie Asher", r"Verghese", "phd", 2016, "Rebecca Jennie Asher Mieloszyk", note="DSpace@MIT PhD thesis (EECS 2016), supervisors 'Thomas Heldt and George C. Verghese.'"),
              DS(DSPACE, "Dunitz, Max (Max H.)", r"Verghese", "masters", 2016, "Max H. Dunitz", note="DSpace@MIT M.Eng. thesis (EECS 2016), supervisors 'Thomas Heldt and George Verghese.'"),
              DS(DSPACE, "Zahray, Lisa(Lisa A.)", r"Verghese", "masters", 2019, "Lisa A. Zahray", note="DSpace@MIT M.Eng. thesis (EECS 2019), supervisors 'Matt Pokress and George Verghese.'"),
              DS(DSPACE, "Jacquot, Grégoire", r"Verghese", "masters", 2021, "Grégoire Jacquot", note="DSpace@MIT S.M. thesis (2021), supervisors Ignacio J. Pérez-Arriaga and George C. Verghese")]
             + [S(n, "member", None, CPCI_2016, rx, note=_cpci) for n, rx in
                [("Kaustav Gopinathan", r"Max Dunitz Kaustav Gopinathan"), ("Abubakar Abid", r"Kaustav Gopinathan Abubakar Abid"),
                 ("Margaret Guo", r"Abubakar Abid Margaret Guo"), ("Thipok (Ben) Rak-amnouyki", r"Margaret Guo Thipok \(Ben\) Rak-amnouyki")]],
    identity=dict(dblp=[], orcid=[], openalex=["A5080571958"],
                  evidence=[idev("openalex_author", oa_author("A5080571958"), oa_rx("A5080571958", "George C\\. Verghese"), "George C. Verghese",
                                 "OpenAlex author record (329 works; 40 dated 2016+)")]
                  + [idev("own_publication_list_match", CPCI_PUBS, rx, "Verghese", f"OpenAlex {w} (author A5080571958) is on his group's (CPCI) publications page")
                     for w, rx in [("W2610570861", r"Verghese GC, Krauss BS, Heldt T\. Model-based estimation of respiratory parameters from capnography, with application to diagnosing obstructive lung disease"),
                                   ("W4361858836", r"Verghese GC, Krauss BS, Heldt T\. Low-order mechanistic models for volumetric and temporal capnography: development, validation, and application"),
                                   ("W2899034855", r"Verghese GC\. An enhanced mechanistic model for capnography, with application to CHF.COPD discrimination")]]),
    appointment_notes=[appt(GV_EECS, r"George Verghese People Faculty Faculty AI\+D Faculty CS Faculty EE Faculty Emeritus Lecturers Leadership Staff Instructors Henry Ellis Warren \(1894\) Professor of Electrical and Biomedical Engineering \(Post-Tenure\), \[EE and AI\+D\]", "Verghese")],
    notes=("At MIT since 1979; Henry Ellis Warren (1894) Professor of Electrical and Biomedical Engineering, now post-tenure; "
           "co-directs the Computational Physiology and Clinical Inference Group (RLE) with Thomas Heldt. Students: four dated "
           "DSpace@MIT theses with Verghese in the supervisor field (PhD 2016, M.Eng. 2016 and 2019, S.M. 2021) plus four "
           "members listed on the 2016 CPCI people page (advising PI not stated). The CPCI page's 'Shamim Nemati Postdoctoral "
           "Associate' entry is stale (the same page lists him as a Harvard postdoc alumnus) and is not used. No ORCID is linked "
           "from his own pages; OpenAlex reports 0000-0002-5930-7694 (unchecked). The pipeline's single advising record is "
           "consistent with these findings; the gap was papers (no person/identity anchor)."),
)
EXTRA["George Verghese"] = dict(status_basis="students_found", needs_after_research=[],
                                pipeline_actions=["add OpenAlex A5080571958", "accept researched students (DSpace theses; CPCI 2016 member list)"])

# ------------------------------------------------------------------------------------------------ Sanjoy Mitter
MITTER_HP = WB + "20210509231922id_/https://web.mit.edu/mitter/www/"
MITTER_THESES = WB + "20200928172730id_/https://web.mit.edu/mitter/www/Mitter_Theses.html"
MITTER_PUBS = WB + "20180221083538id_/http://www.mit.edu:80/~mitter/mitter-pubs.html"
SPEC["Sanjoy Mitter"] = dict(
    status="not_pi_in_window",
    status_evidence=[ev(MITTER_THESES, r"Theses Supervised by Sanjoy K\. Mitter lastname firstname whereabouts thesistype year school Agarwal Mukul PhD 2012 MIT", "Sanjoy K. Mitter"),
                     ev(MITTER_HP, r"Sanjoy K\. Mitter Professor of Electrical Engineering Massachusetts Institute of Technology Laboratory for Information and Decision Systems", "Sanjoy K. Mitter")],
    students=[],
    identity=dict(dblp=[], orcid=[], openalex=["A5091119091"],
                  evidence=[idev("openalex_author", oa_author("A5091119091"), oa_rx("A5091119091", "Sanjoy K\\. Mitter"), "Sanjoy K. Mitter",
                                 "OpenAlex author record (375 works); 108 of its titles are on his own 'Books & Journal Publications' list")]
                  + [idev("own_publication_list_match", MITTER_PUBS, rx, "Mitter", f"OpenAlex {w} (author A5091119091) is on his own publication list (Wayback 2018-02-21)")
                     for w, rx in [("W1593775104", r"Mitter, S\.K\., Narayanan, H\. Testing the Manifold Hypothesis"),
                                   ("W2156216606", r"Mitter, S\.K\. Control under Communication Constraints"),
                                   ("W2155024125", r"Mitter, S\.K\. Stabilization of Linear Systems with Limited Information")]]),
    appointment_notes=[appt(LISTING_2023, r"Sanjoy Mitter Professor of EE \(Post-Tenure\), \[AI\+D and EE\]", "Mitter")],
    notes=("Professor of Electrical Engineering (post-tenure by 2023; b. 1933), LIDS. His own 'Theses Supervised' list (Wayback "
           "2020-09-28) ends in 2012 (latest entries: Mukul Agarwal PhD 2012, Mesrob Ohannessian PhD 2012); the DSpace@MIT "
           "supervisor search 2016-2026 (stored; query includes 'Mitter') returns no thesis supervised by him; his LIDS "
           "profile now redirects to the LIDS people index. No group page or in-window student was found, so he is judged not "
           "a PI in 2016-2026 (EECS listings carry him through 2023). Identity: OpenAlex A5091119091 matches 108 titles on "
           "his own publication list; OpenAlex reports ORCID 0000-0002-8619-1295, not linked from his own pages (unchecked)."),
)
EXTRA["Sanjoy Mitter"] = dict(status_basis="no_supervision_found_in_window (post-tenure; last supervised thesis 2012)", needs_after_research=[],
                              pipeline_actions=["exclude (owner may prefer to keep and mark as no-group)", "add OpenAlex A5091119091 if papers are still wanted"])

# ------------------------------------------------------------------------------------------------ Priya Donti
PD = "https://priyadonti.com/"
PD_GROUP = "https://priyadonti.com/group"
PD_PUBS = "https://priyadonti.com/publications"
PD_EECS = "https://www.eecs.mit.edu/people/priya-donti/"
_pdcur = "current member on her 'Research Group' page (live, fetched 2026-10-22)"
pd_current = [("Alvaro Carbonero", "phd"), ("Ana Rivera", "phd"), ("Anvita Bhagavathula", "phd"), ("Hoang Nguyen", "phd"),
              ("James Chen", "phd"), ("Khai Nguyen", "phd"), ("Lara Booth", "phd"),
              ("Betsegaw Wosoro", "undergraduate"), ("Maria Chzhen", "undergraduate"), ("Ojas Sanghi", "undergraduate")]
pd_past = [("Adeoluwa Adekanmbi", "undergraduate", [2024, 2025], r"Adeoluwa Adekanmbi \(undergrad, 2024-25\)", None),
           ("Alicia Li", "undergraduate", [2024, 2024], r"Alicia Li \(undergrad, 2024\)", None),
           ("Arsam Aryandoust", "postdoc", [2023, 2025], r"Arsam Aryandoust \(postdoc, 2023-25\)", None),
           ("Cameron Cowperthwaite", "undergraduate", [2024, 2024], r"Cameron Cowperthwaite \(undergrad, 2024\)", None),
           ("Chiara Fusar Bassini", "other", [2025, 2025], r"Chiara Fusar Bassini \(visiting Ph\.D\. student, 2025\)", "visiting PhD student"),
           ("Enrico Marchesini", "postdoc", [2023, 2025], r"Enrico Marchesini \(postdoc, 2023-25\)", None),
           ("Haley Nakamura", "masters", [2024, 2025], r"Haley Nakamura \(MEng, 2024-25\)", None),
           ("Maria Alder", "undergraduate", [2023, 2025], r"Maria Alder \(undergrad, 2023-25\)", None),
           ("Petros Ellinas", "other", [2025, 2026], r"Petros Ellinas \(visiting Ph\.D\. student, 2025-26\)", "visiting PhD student"),
           ("Shiva Madadkhani", "other", [2025, 2025], r"Shiva Madadkhani \(visiting Ph\.D\. student, 2025\)", "visiting PhD student")]
SPEC["Priya Donti"] = dict(
    status="pi",
    status_evidence=[ev(PD_GROUP, r"Research Group - Priya L\. Donti .{0,120}?Research Group Current Members Alvaro Carbonero \(Ph\.D\. student\)", "Priya L. Donti"),
                     ev(PD, r"Priya L\. Donti Assistant Professor, MIT EECS and LIDS Co-founder and Chair, Climate Change AI", "Priya L. Donti")],
    students=[S(n, r, None, PD_GROUP, re.escape(n) + r" \((?:Ph\.D\. student|undergrad)\)", note=_pdcur) for n, r in pd_current]
             + [S(n, r, y, PD_GROUP, rx, note="past member with years on her 'Research Group' page" + ("; " + x if x else "")) for n, r, y, rx, x in pd_past]
             + [DS(DSPACE, "Ramirez Sanchez, Edgar", r"Donti", "masters", 2024, "Edgar Ramirez Sanchez", note="DSpace@MIT S.M. thesis (2024-05), supervisors Cathy Wu and Priya L. Donti")],
    identity=dict(dblp=[], orcid=[], openalex=["A5075620331"],
                  evidence=[idev("openalex_author", oa_author("A5075620331"), oa_rx("A5075620331", "Priya L\\. Donti"), "Priya L. Donti",
                                 "OpenAlex author record (48 works); 21 of its 2016+ titles are on her own publications page")]
                  + [idev("own_publication_list_match", PD_PUBS, rx, "Priya L. Donti", f"OpenAlex {w} (author A5075620331) is on her own publications page")
                     for w, rx in [("W4210916416", r"Tackling Climate Change with Machine Learning David Rolnick, Priya L\. Donti"),
                                   ("W3187503080", r"Machine Learning for Sustainable Energy Systems Priya L\. Donti"),
                                   ("W2996221078", r"Matrix Completion for Low-Observability Voltage Estimation Priya L\. Donti")]]),
    appointment_notes=[appt(PD_EECS, r"Priya Donti People Faculty Faculty AI\+D Faculty CS Faculty EE Faculty Emeritus Lecturers Leadership Staff Instructors Assistant Professor, \[EE, AI\+D\]", "Donti")],
    notes=("Assistant Professor in EECS and LIDS since 2023 (EECS listings 2023-2026; previously Cornell Tech postdoc, CMU PhD). "
           "Students: 10 current group members and 10 dated past members (2023-2026) from her 'Research Group' page, plus one "
           "DSpace@MIT S.M. thesis (2024, co-supervised with Cathy Wu). Past members dated before her MIT appointment are left "
           "out (Amy Wang 2019-21, Marissa Liu 2020-21, Neeraj Vijay Bedmutha MSc 2020-21, Tom Wright 2021-22), as is "
           "'Chotiya Mahittigul (MSc, 2023)' (an MSc is not an MIT degree, so the mentoring was probably elsewhere). No ORCID is "
           "linked from her own pages; OpenAlex reports 0000-0002-8503-7464 (unchecked). DBLP not consulted (off limits)."),
)
EXTRA["Priya Donti"] = dict(status_basis="students_found", needs_after_research=[],
                            pipeline_actions=["add OpenAlex A5075620331", "accept researched students (group page; DSpace thesis)"])
