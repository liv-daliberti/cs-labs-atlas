"""Berkeley gap decisions, worker 'departed' (2026-10-21/22): ladder PIs whose EECS listing ends early or who hold
non-standard posts -- Trevisan, Tygar, Necula, Franklin, Ramamoorthi, Abebe, L. Blum, Chayes.
"""
import sys

sys.path.insert(0, "/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/gap-tools-berkeley")
from dhelp import *  # noqa: E402,F401,F403

D = {}
TR = "https://www2.eecs.berkeley.edu/Pubs/TechRpts/"

# ============================================================================ Luca Trevisan
LT16 = WB + "20161209152023id_/https://people.eecs.berkeley.edu/~luca/"
LT18 = WB + "20180927213920id_/http://people.eecs.berkeley.edu:80/~luca/"
LT19 = WB + "20190910054106id_/http://people.eecs.berkeley.edu:80/~luca/"
LTPUB = WB + "20200929012714id_/https://people.eecs.berkeley.edu/~luca/pubs/by-year.html"
LT_STUD = "people current students Pasin Manurangsi Theo McKenzie Jess Banks Frank Ban"
LT_ORCID_AFF = "https://orcid.org/0000-0002-6982-8530/affiliationGroups.json"
D["Luca Trevisan"] = dict(
    status="pi",
    status_ev=[diss_status("Luca Trevisan"),
               Q(LT18, "Luca Trevisan I am a professor of Electrical Engineering and Computer Sciences and of Mathematics at U.C. Berkeley")],
    students=[
        ST("Pasin Manurangsi", "phd", [None, 2019],
           SE(diss_page_url("Luca Trevisan"), "Ph.D. Dissertations - Luca Trevisan", "Pasin Manurangsi [2019]"),
           note="EECS dissertation 2019; also 'current students' on his homepage in 2016-2018"),
        ST("Theo McKenzie", "phd", [2018, 2018], Q(LT18, LT_STUD), note="'current students' on his homepage (2018-09 capture)"),
        ST("Jess Banks", "phd", [2018, 2018], Q(LT18, LT_STUD), note="'current students' on his homepage (2018-09 capture)"),
        ST("Frank Ban", "phd", [2018, 2018], Q(LT18, LT_STUD), note="'current students' on his homepage (2018-09 capture)"),
    ],
    identity=dict(
        orcid=["0000-0002-6982-8530"], openalex=["A5057752375"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5057752375", "Luca Trevisan"),
               "OpenAlex author A5057752375 (310 works; ORCID 0000-0002-6982-8530; affiliations UC Berkeley 2001-2021, Bocconi 2018-2026)."),
            ID("openalex_verified_by_publication_list",
               Q(LTPUB, "Pasin Manurangsi, Danupon Nanongkai, Luca Trevisan From Gap-ETH to FPT-Inapproximability: Clique, Dominating S"),
               "W2749816968 (2017) of A5057752375 is on his own papers-by-year page; 15 of its 2016+ titles match that page."),
            ID("openalex_verified_by_publication_list",
               Q(LTPUB, "Nikhil Bansal, Ola Svensson and Luca Trevisan New Notions and Constructions of Sparsification for Graphs and Hypergraphs"),
               "W2943467511 (2019) of A5057752375."),
            ID("openalex_verified_by_publication_list",
               Q(LTPUB, "Francesco Pasquale, and Luca Trevisan Finding a Bounded-Degree Expander Inside a Dense One"),
               "W2997284836 (2020) of A5057752375."),
            ID("orcid_record",
               Q("https://orcid.org/0000-0002-6982-8530/person.json", '"displayName":"Luca Trevisan"', raw=True),
               "ORCID 0000-0002-6982-8530 record name; the same id is on OpenAlex A5057752375."),
            ID("orcid_record",
               SE(LT_ORCID_AFF, '"affiliationName":{"errors":[],"value":"U.C. Berkeley"', '"sourceName":"Luca Trevisan"', raw=True),
               "ORCID employment entry (self-asserted by Luca Trevisan): U.C. Berkeley, EECS, Professor, start 2014-07-01."),
        ]),
    appt=[Q(LT18, "Luca Trevisan I am a professor of Electrical Engineering and Computer Sciences and of Mathematics at U.C. Berkeley"),
          Q(LT19, "Luca Trevisan Luca Trevisan Professor Department of Decision Sciences Bocconi University"),
          Q(PROF + "trevisan.html", "Luca Trevisan passed away on June 19, 2024.")],
    notes=("At Berkeley EECS (and Mathematics) from July 2014 (ORCID employment entry) until 2019, when he moved to "
           "Bocconi (homepage by 2019-09 points to Bocconi); died June 19, 2024 (EECS profile). Students 2016-2019: "
           "Pasin Manurangsi (EECS PhD 2019, chaired) and the three other 'current students' on his 2018 homepage (Theo "
           "McKenzie and Jess Banks were Mathematics PhD students; Frank Ban EECS). Postdoc Ali Sinop (2014-2015) is before "
           "the window. The pipeline's 'no_advising_records' missed the live dissertations page entry for Manurangsi."),
)

# ============================================================================ Doug Tygar
DT = WB + "20160604175843id_/http://people.eecs.berkeley.edu/~tygar/"
DTP = WB + "20160718121041id_/http://people.eecs.berkeley.edu:80/~tygar/publications.htm"
D["Doug Tygar"] = dict(
    status="pi",
    status_ev=[diss_status("Doug Tygar")],
    students=diss_students("Doug Tygar"),
    identity=dict(
        orcid=[], openalex=["A5113907559"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5113907559", "J. D. Tygar"),
               "OpenAlex author A5113907559 'J. D. Tygar' (187 works, last institution UC Berkeley, no ORCID)."),
            ID("openalex_verified_by_publication_list",
               Q(DTP, "Adversarial Machine Learning: Computer Security and Statistical Machine Learning. A. Joseph, B. Nelson, B. Rubinstein, J. D. Tygar."),
               "W4211122380 (2019, Cambridge UP book, UC Berkeley affiliation) of A5113907559 is on his own publications page (listed there as forthcoming)."),
            ID("openalex_verified_by_publication_list",
               Q(DTP, "When are Best Fit and First Fit Optimal? C. McGeoch and J. D. Tygar"),
               "W769452160 of A5113907559 (OpenAlex year 2018: a repository deposit of a 1987 CMU report)."),
            ID("openalex_verified_by_publication_list",
               Q(DTP, "The TESLA broadcast authentication protocol .\x94 A. Perrig, R. Canneti, J. D. Tygar"),
               "W2110081058 of A5113907559 (OpenAlex year 2018, UC Berkeley affiliation; originally CryptoBytes 2002)."),
            ID("openalex_verified_by_publication_list",
               Q(DTP, "Dyad: A system for using physically secure coprocessors .\x94 J. D. Tygar and B. Yee"),
               "W1555250994 of A5113907559 (OpenAlex year 2018; a deposited CMU-era paper)."),
        ]),
    appt=[Q(DT, "Doug Tygar Professor of Computer Science , UC Berkeley Professor of Information Management , UC Berkeley"),
          Q(PROF + "tygar.html", "Doug Tygar passed away on January 16, 2020.")],
    notes=("Professor of CS and of Information Management at Berkeley until his death on January 16, 2020 (EECS profile). "
           "Chaired the EECS dissertations of Alex Kantchelian (2016) and David Fifield (2017); Bradley Miller (2015) is just "
           "before the window. Identity caveat: his own publication list was last updated in 2013, so only one genuinely "
           "post-2016 work can be matched (the 2019 Adversarial Machine Learning book); the other three matches are legacy "
           "papers that OpenAlex dates 2018 (repository deposits). A5113907559 is unambiguous (J. D. Tygar, UC Berkeley), "
           "and his 2016-2019 Berkeley papers are co-authored with these advisees (e.g. W2464629196 'Reviewer Integration "
           "and Performance Measurement for Malware Detection', 2016, with Kantchelian), so the advisee-coauthor rule also "
           "anchors it. A second, smaller OpenAlex profile A5067640470 'Doug Tygar' (35 works; 2016-2018 Berkeley papers on "
           "adversarial ML and employee security behaviour) is probably the same person but could not be checked against "
           "his own list; not adopted."),
)

# ============================================================================ George Necula
GN16 = WB + "20160716190051id_/http://people.eecs.berkeley.edu/~necula/main.html"
GN19 = WB + "20190724150656id_/https://people.eecs.berkeley.edu/~necula/main.html"
GNCV = WB + "20160716190051id_/http://people.eecs.berkeley.edu/~necula/cv.pdf"
WC = "https://people.eecs.berkeley.edu/~wtchoi/"
GN_ADV = SE(GNCV, "Advising George C. Necula", "Philip Wontae Choi (since 2012).")
D["George Necula"] = dict(
    status="pi",
    status_ev=[GN_ADV,
               SE(WC, "Philip Wontae Choi Wontae Choi I am a Senior Software Engineer", "(advisors: Koushik Sen and George Necula )")],
    students=[
        ST("Wontae Choi", "phd", [2012, 2017],
           SE(WC, "Philip Wontae Choi Wontae Choi I am a Senior Software Engineer", "(advisors: Koushik Sen and George Necula )"),
           note="His own page: Ph.D. EECS UC Berkeley Dec. 2017, advisors Koushik Sen and George Necula; listed as Necula's PhD student 'since 2012' on Necula's 2016 CV"),
        ST("Derrick Coetzee", "phd", [2010, None], GN_ADV,
           note="Listed as a current PhD student ('since 2010') on Necula's CV (Wayback capture 2016-07); no Berkeley dissertation found through 2020"),
        ST("Benjamin Hindman", "phd", [2007, None], GN_ADV,
           note="Listed as a current PhD student ('since 2007') on Necula's 2016 CV; may be stale (no Berkeley dissertation found)"),
    ],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[Q(GN16, "Contact: George Necula, Professor – Electrical Engineering and Computer Science"),
          Q(GN19, "Contact: George Necula, (Retired) Professor – Electrical Engineering and Computer Science Currently, working at Google Switzerland.")],
    notes=("Professor until he retired c. 2016-2017 (homepage 2016-07: 'Professor'; 2019: '(Retired) Professor ... working at "
           "Google Switzerland'); his 2016 CV lists 'Industrial Employment 2016-present YouTube/Google Inc.' alongside the "
           "Berkeley professorship, and he is on the 2016-2017 EECS listings. Status pi because in 2016 he still advised "
           "Berkeley PhD students: Wontae Choi finished Dec. 2017 (co-advised with Koushik Sen), and the CV lists Derrick "
           "Coetzee and Benjamin Hindman as current. The lab was winding down, so few lab papers are expected. Identity: the "
           "only OpenAlex candidate, A5049483484 'George C. Necula' (143 works, no ORCID), has just two works dated 2016+ "
           "(W2303724510 'Minimizing faulty executions of distributed systems', NSDI 2016, which is on his CV; W2795227216 "
           "'DetReduce', ICSE 2018, with advisee Wontae Choi), so the three-work test cannot be met and no id is recorded. "
           "The advisee-coauthor rule (Wontae Choi on DetReduce) is the route by which the pipeline can anchor it."),
)

# ============================================================================ Michael Franklin
MF16 = WB + "20160425041548id_/http://www.cs.berkeley.edu:80/~franklin/"
MFP = WB + "20160725084109id_/http://www.eecs.berkeley.edu:80/Faculty/Homepages/franklin.html"
CHI = "https://uchi-db.github.io/chidatasite/publications.html"
D["Michael Franklin"] = dict(
    status="pi",
    status_ev=[Q(TR + "2016/EECS-2016-200.html", "Advisors: Michael Franklin BibTeX citation: @phdthesis{Sparks:EECS-2016-200, Author= {Sparks, Evan}"),
               Q(MF16, "Michael J. Franklin Thomas M. Siebel Professor of Computer Science UC Berkeley Home Research Publications Talks Teaching Background Welcome I am a Professor of Computer Science at UC Berkeley")],
    students=[
        ST("Evan Sparks", "phd", [None, 2016],
           Q(TR + "2016/EECS-2016-200.html", "Advisors: Michael Franklin BibTeX citation: @phdthesis{Sparks:EECS-2016-200, Author= {Sparks, Evan}"),
           note="EECS PhD dissertation 2016 (EECS-2016-200), advisor Michael Franklin"),
        ST("Daniel Haas", "phd", [None, 2017],
           Q(TR + "2017/EECS-2017-134.html", "Advisors: Michael Franklin and Ken Goldberg BibTeX citation: @phdthesis{Haas:EECS-2017-134, Author= {Haas, Daniel}"),
           note="EECS PhD dissertation 2017 (co-advised with Ken Goldberg); also his 2016 MS report EECS-2016-10 names Franklin as sole advisor"),
    ],
    identity=dict(
        orcid=[], openalex=["A5102019638"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5102019638", "Michael J. M. Franklin"),
               "OpenAlex A5102019638 (295 works). CAUTION: a merged profile -- besides the database researcher it holds works "
               "of an Australian ecologist 'Michael J. M. Franklin' (Western Sydney / Wollongong), whose name it displays; its "
               "ORCID 0000-0003-3332-8574 is not adopted."),
            ID("openalex_verified_by_publication_list",
               Q(CHI, "Ernest: Efficient Performance Prediction for Large-Scale Advanced Analytics. Shivaram Venkataraman, Zongheng Yang, Michael J. Franklin"),
               "W2309679942 (2016, NSDI, Berkeley AMPLab) of A5102019638 is on the publication list of ChiData, his UChicago data "
               "group; 30 of the id's 2016+ titles match that list."),
            ID("openalex_verified_by_publication_list",
               Q(CHI, "KeystoneML: Optimizing Pipelines for Large-Scale Advanced Analytics. Evan R. Sparks, Shivaram Venkataraman, Tomer Kaftan, Michael J. Franklin"),
               "W2547386789 (2017, ICDE; with advisee Evan Sparks) of A5102019638."),
            ID("openalex_verified_by_publication_list",
               Q(CHI, "Data Market Platforms: Trading Data Assets to Solve Data Problems. Raul Castro Fernandez, Pranav Subramaniam, Michael J. Franklin"),
               "W3081749234 (2020) of A5102019638."),
            ID("openalex_verified_by_publication_list",
               Q(CHI, "Volume Under the Surface: A New Accuracy Evaluation Measure for Time-Series Anomaly Detection. John Paparrizos, Paul Boniol, Themis Palpanas, Ruey Tsay, Aaron J. Elmore, Michael J. Franklin"),
               "W4312750676 (2022) of A5102019638."),
        ]),
    appt=[Q(MF16, "Michael J. Franklin Thomas M. Siebel Professor of Computer Science UC Berkeley Home Research Publications Talks Teaching Background Welcome I am a Professor of Computer Science at UC Berkeley"),
          SE(MFP, "Professor Franklin is an Adjunct Professor of Computer Science at UC Berkeley", "Chair of Computer Science at the University of Chicago"),
          Q("https://cs.uchicago.edu/people/michael-franklin/", "Michael Franklin is the Morton D. Hull Distinguished Service Professor of Computer Science at the University of Chicago")],
    notes=("Berkeley professor (AMPLab director) into 2016: homepage 2016-04 'I am a Professor of Computer Science at UC "
           "Berkeley'; by 2016-07 the EECS profile calls him an Adjunct Professor at Berkeley and Professor and Chair of CS at "
           "the University of Chicago. Status pi because his Berkeley PhD students finished in the window under him: Evan "
           "Sparks (2016, sole advisor) and Daniel Haas (MS 2016 sole advisor; PhD 2017 with Ken Goldberg). Lab papers are "
           "2016-2017 AMPLab work. OpenAlex: the only Berkeley-bearing profile, A5102019638, is contaminated by an ecologist "
           "namesake (and A5090643027 mixes a Montana microbiologist with a few of his UChicago papers); the Berkeley-"
           "affiliation requirement keeps the namesake works out of lab papers, but the profile should not be used without "
           "it. No own publication list exists on his pages (his Berkeley pubs page deferred to Google Scholar), so the ChiData "
           "group list, which carries his Berkeley-era AMPLab papers, was used."),
)

# ============================================================================ Ravi Ramamoorthi
RR = "https://cseweb.ucsd.edu/~ravir/"
RRP = WB + "20160301030154id_/http://www.eecs.berkeley.edu:80/Faculty/Homepages/ravir.html"
D["Ravi Ramamoorthi"] = dict(
    status="not_pi_in_window",
    status_ev=[SE(RR, "Ravi Ramamoorthi Ronald L. Graham Professor of Computer Science", "moving from UC Berkeley.")],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[Q(RRP, "Ravi Ramamoorthi joined the faculty of the Electrical Engineering and Computer Sciences Department at UC Berkeley in January 2009."),
          Q(TR + "2017/EECS-2017-50.html", "Advisors: Ravi Ramamoorthi and Alexei (Alyosha) Efros BibTeX citation: @phdthesis{Wang:EECS-2017-50, Author= {Wang, Ting-Chun}")],
    notes=("Left Berkeley before the window: his UCSD homepage says he started at UCSD on July 1, 2014, moving from UC "
           "Berkeley (Berkeley faculty from January 2009). The 2016 EECS listing and the Feb-2016 EECS profile capture are "
           "stale. Edge case decided: he co-advised one Berkeley PhD student into the window -- Ting-Chun Wang (EECS PhD "
           "2017, advisors Ramamoorthi and Alexei Efros) -- but supervised him from UCSD; Ramamoorthi's 2016-2017 papers with "
           "Wang carry UCSD, not Berkeley (OpenAlex candidate A5034754633 has 0 Berkeley-affiliated authorships in the "
           "Berkeley sweep), so no Berkeley lab of his exists in 2016-2026 and Wang belongs with Efros's lab. Identity not "
           "recorded: A5034754633 (ORCID 0000-0003-3993-5789) matches 144 titles on his UCSD homepage, but that page omits "
           "author names, so no quote carries his name."),
)

# ============================================================================ Rediet Abebe
AB21 = WB + "20211102114244id_/https://www.redietabebe.com/"
AB22 = WB + "20220822173247id_/https://www.redietabebe.com/"
AB23 = WB + "20230609223140id_/https://www.redietabebe.com/"
AB_GROUP = SE(AB22, "Research Group PhD Students: Eve Fleisig", "Liya Mulugeta , & Vyoma Raman")
AB_NOTE22 = "Listed in 'Research Group' on her homepage (Wayback 2022-08)"
D["Rediet Abebe"] = dict(
    status="pi",
    status_ev=[diss_status("Rediet Abebe"),
               Q(AB21, "Rediet Abebe Rediet Abebe Assistant Professor Department of Electrical Engineering and Computer Sciences University of California, Berkeley")],
    students=(
        diss_students("Rediet Abebe")
        + [ST("Angela Jin", "phd", [2022, 2025], AB_GROUP, note=AB_NOTE22 + "; still listed 2023 and 2025"),
           ST("Ezinne Nwankwo", "phd", [2022, 2022], AB_GROUP, note=AB_NOTE22),
           ST("Ricardo Sandoval", "phd", [2022, 2022], AB_GROUP, note=AB_NOTE22),
           ST("Ramon Vilarino", "phd", [2022, 2023], AB_GROUP, note=AB_NOTE22 + "; still listed 2023"),
           ST("Serena Wang", "phd", [2022, 2022], AB_GROUP, note=AB_NOTE22),
           ST("George Obaido", "postdoc", [2022, 2025], AB_GROUP, note=AB_NOTE22 + " as Postdoctoral Fellow; still listed 2023 and 2025"),
           ST("Raysa Benatti", "other", [2022, 2022], AB_GROUP, note=AB_NOTE22 + " as Visiting Scholar"),
           ST("Rodrigo Dornelles", "other", [2022, 2022], AB_GROUP, note=AB_NOTE22 + " as Visiting Scholar"),
           ST("Meryem Essaidi", "other", [2022, 2022], AB_GROUP, note=AB_NOTE22 + " as Visiting Scholar"),
           ST("Tainá Turella C. dos Santos", "other", [2022, 2025], AB_GROUP, note=AB_NOTE22 + " as Visiting Scholar; still listed 2023 and 2025"),
           ST("Mírian Silva", "other", [2022, 2022], AB_GROUP, note=AB_NOTE22 + " as Visiting Scholar"),
           ST("Meareg Hailemariam", "masters", [2022, 2025], Q(AB23, "Graduate Researchers : Meareg Hailemariam (masters student)"),
              note="'(masters student)' in her group (2023 capture); also under MS/BS Students in 2022"),
           ST("Liya Mulugeta", "member", [2022, 2022], AB_GROUP, note=AB_NOTE22 + " under 'MS/B S Students' (degree level not stated)"),
           ST("Vyoma Raman", "member", [2022, 2022], AB_GROUP, note=AB_NOTE22 + " under 'MS/B S Students' (degree level not stated)")]),
    identity=dict(
        orcid=[], openalex=["A5072647467"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5072647467", "Rediet Abebe"),
               "OpenAlex A5072647467 (54 works; ORCID 0000-0002-5487-9108; last institutions MPI-IS / ELLIS Institute Tuebingen)."),
            ID("openalex_verified_by_publication_list",
               Q(AB23, 'Abebe, R., Schaub, M. T., Jadbabaie, A., and Kleinberg, J. "Simplicial Closure and Higher-Order Link Prediction'),
               "W2787887656 (2018) of A5072647467 is in 'All Publications' on her homepage (2023 capture); 19 of its 2016+ titles match."),
            ID("openalex_verified_by_publication_list",
               Q(AB23, 'Abebe, R., Kleinberg, J., Parkes, D., and Tsourakakis, C. E. "Opinion Dynamics with Varying Susceptibility to Persuasion'),
               "W2784592207 (2018) of A5072647467."),
            ID("openalex_verified_by_publication_list",
               Q(AB23, 'Abebe, R . "Difficult Lessons on Social Prediction from Wisconsin Public Schools'),
               "W4411550415 (2025) of A5072647467."),
            ID("openalex_verified_by_publication_list",
               Q(AB23, 'Abebe, R. "Fairness, Equality, and Power in Algorithmic Decision-Making'),
               "W3133953502 (2021) of A5072647467."),
        ]),
    appt=[Q(AB21, "Rediet Abebe Rediet Abebe Assistant Professor Department of Electrical Engineering and Computer Sciences University of California, Berkeley"),
          SE(AB23, "Rediet Abebe Rediet Abebe I am a Junior Fellow", "I am on leave as an assistant professor of computer science at UC Berkeley.")],
    notes=("Assistant Professor at Berkeley EECS from 2021 (homepage 2021-11), also a Harvard Junior Fellow; by 2023 she "
           "describes herself as on leave from Berkeley, and OpenAlex now places her at MPI-IS / ELLIS Institute Tuebingen. "
           "EECS listings stop after 2023, but her Berkeley PhD students graduated under her: Ali Shirali (2025, with Moritz "
           "Hardt) and Eve Fleisig (2026, with Dan Klein), per the EECS dissertations page and tech reports. The 2022 homepage "
           "lists the full group (7 PhD students, a postdoc, 5 visiting scholars, 3 MS/BS students); the domain "
           "redietabebe.com is now hijacked by a spam site, so only Wayback captures were used. ORCID 0000-0002-5487-9108 "
           "(on her OpenAlex record) is not recorded: the ORCID record lists only education and her page does not link it."),
)

# ============================================================================ Lenore Blum
D["Lenore Blum"] = dict(
    status="not_pi_in_window",
    status_ev=[Q(PROF + "lblum.html", "Lenore Blum Former Professor in Residence Biography Lenore Blum is a Professor-in-Residence in EECS at UC Berkeley. She is also the Distinguished Career Professor of Computer Science, Emeritus at Carnegie Mellon University")],
    students=[],
    identity=dict(orcid=[], openalex=[], evidence=[]),
    appt=[Q(PROF + "lblum.html", "Lenore Blum Former Professor in Residence")],
    notes=("Professor-in-Residence (a non-ladder in-residence appointment) in EECS 2021-2023, while Distinguished Career "
           "Professor Emerita at CMU; no group. Her Berkeley-era research is the Conscious Turing Machine work with Manuel "
           "Blum: OpenAlex A5073359845 (ORCID 0000-0003-1541-1294) has 12 works since 2016, all either with Manuel Blum alone, "
           "memorial/history pieces, or a 2026 paper with CMU/MIT co-authors (Haofei Yu, Yining Zhao, Paul Pu Liang), and all "
           "affiliated to CMU, not Berkeley. No EECS dissertations page exists (404), and no source names a Berkeley student, "
           "postdoc or lab member. Identity not recorded: her own homepage (cs.cmu.edu/~lblum) has no 2016+ publication list "
           "and her ORCID record lists no affiliation."),
)

# ============================================================================ Jennifer Chayes
JC = "http://jenniferchayes.com/"
SL = "https://chao1224.github.io/"
SL_Q = SE(SL, "Shengchao Liu, Mehmet Furkan Demirel, Yingyu Liang NeurIPS 2019 Spotlight",
          "Advisors: Prof. Jennifer Chayes and Prof. Christian Borgs")
D["Jennifer Chayes"] = dict(
    status="pi",
    status_ev=[SL_Q,
               Q(PROF + "jchayes.html", "Jennifer Chayes is Dean of the College of Computing, Data Science, and Society. She is a Professor of Electrical Engineering and Computer Sciences, Mathematics, Statistics, and Information.")],
    students=[ST("Shengchao Liu", "postdoc", [2023, 2025], SL_Q,
                 note="His homepage: '2023 -- 2025, Postdoc University of California, Berkeley Advisors: Prof. Jennifer Chayes and Prof. Christian Borgs'")],
    identity=dict(
        orcid=["0000-0003-4020-8618"], openalex=["A5038662431"],
        evidence=[
            ID("openalex_author_record", oa_author_quote("A5038662431", "Jennifer Chayes"),
               "OpenAlex A5038662431 (233 works; ORCID 0000-0003-4020-8618; last institution UC Berkeley)."),
            ID("openalex_verified_by_publication_list",
               Q(JC, "Entropy-SGD: biasing gradient descent into wide valleys (P. Chaudhari, A. Choromanska, S. Soatto, Y. LeCun, C. Baldassi, C. Borgs, J.T. Chayes"),
               "W2552194003 (2019) of A5038662431 is in 'Selected Publications' on her homepage; 17 of its 2016+ titles match."),
            ID("openalex_verified_by_publication_list",
               Q(JC, "The disparate equilibria of algorithmic decision-making when individuals invest rationally (L. Liu, A. Wilson, N. Haghtalab, A. Kalai, C. Borgs, and J.T. Chayes"),
               "W2980293941 (2020) of A5038662431."),
            ID("openalex_verified_by_publication_list",
               Q(JC, "A multifactorial model of T Cell expansion and durable clinical benefit in response to a PD-L1 inhibitor (M. Leiserson, V. Syrgkanis, A. Gilson, M. Dudik, S. Gillett, J. Chayes"),
               "W2950472298 (2018) of A5038662431."),
            ID("orcid_record",
               Q("https://orcid.org/0000-0003-4020-8618/person.json",
                 '"content":"Jennifer Chayes is Dean of the College of Computing, Data Science, and Society at UC Berkeley', raw=True),
               "ORCID 0000-0003-4020-8618 biography names her as Dean at UC Berkeley (display name 'J. T. Chayes')."),
        ]),
    appt=[Q(JC, "Prior to joining UC Berkeley in 2020, Chayes worked at Microsoft Research for 23 years.")],
    notes=("Joined Berkeley in 2020 as Associate Provost of the Division (now College) of Computing, Data Science, and "
           "Society and Dean, with professorships in EECS, Mathematics, Statistics and Information. Mostly administrative, "
           "but she co-hosted at least one Berkeley postdoc with Christian Borgs: Shengchao Liu (2023-2025, now CUHK). Her CV "
           "has no student list, no EECS dissertations page exists (404), and Borgs's only listed dissertation (Geng Zhao, "
           "2025) names Jiantao Jiao and Borgs, not Chayes. Other Berkeley co-authors (e.g. EECS student Christian Ikeokwu on "
           "'Disincentivizing Polarization in Social Networks', 2023; Karissa Huang, 2026) have no source stating that she "
           "advised them, so they are not recorded."),
)
