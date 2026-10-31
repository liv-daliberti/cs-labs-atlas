"""Per-PI home-department decisions for the 94-row home-department sweep (2026-10-21).

Each decision names the capture (by fetched URL) that carries the evidence and the quote
boundaries (q_start .. q_end, both inclusive, first q_end after q_start).  build_output.py
extracts the exact quote from the stored page text, checks length/name/department tokens,
and fills sha256.  `{sha:URL}` inside a note is replaced with that capture's sha256 prefix.

Fields: school, name, home_department, also, no_academic_department, url, q_start, q_end,
        name_tok (must be in quote unless own_page_sentence), dept_toks (all must be in quote),
        own_page_sentence (quote is an I am/He is/She is sentence on the person's own page),
        status ("accepted" unless "hold"), reason (hold only), note.
"""

EPFL_DECODE = ("EPFL unit codes decoded from EPFL's own pages: school names at https://www.epfl.ch/schools/ "
               "({sha:https://www.epfl.ch/schools/}); institute names/acronyms at https://www.epfl.ch/research/domains/ "
               "({sha:https://www.epfl.ch/research/domains/}). Home = school/institute of the first-listed (lab/chair) "
               "position's directory breadcrumb.")

D = []

def add(**kw):
    kw.setdefault("also", [])
    kw.setdefault("no_academic_department", False)
    kw.setdefault("own_page_sentence", False)
    kw.setdefault("status", "accepted")
    kw.setdefault("note", "")
    D.append(kw)

# ----------------------------------------------------------------------------- CMU
add(school="cmu", name="Marcel Bruchez", home_department="Department of Biological Sciences",
    also=["Department of Chemistry", "Ray and Stephanie Lane Computational Biology Department (affiliated listing)"],
    url="https://www.cmu.edu/cbd/people/marcel-bruchez.html",
    q_start="Marcel Bruchez Marcel Bruchez Professor", q_end="Professor, Chemistry",
    name_tok="Marcel Bruchez", dept_toks=["Biological Sciences"],
    note="Joint Biological Sciences/Chemistry (Mellon College of Science); Biological Sciences listed first on the CBD profile. "
         "The Biological Sciences faculty URL guess 404'd; no MCS profile captured.")
add(school="cmu", name="Steven Michael Chase", home_department="Department of Biomedical Engineering",
    also=["Neuroscience Institute"],
    url="https://www.cmu.edu/bme/People/Faculty/profile/schase.html",
    q_start="Dr. Steven M. Chase Professor", q_end="Carnegie Mellon Neuroscience Institute",
    name_tok="Steven M. Chase", dept_toks=["Biomedical Engineering"],
    note="College of Engineering. Census lists him under RI as affiliated.")
add(school="cmu", name="Tom Costello", home_department="Department of Social and Decision Sciences",
    also=["Human-Computer Interaction Institute (affiliated faculty)"],
    url="https://hcii.cmu.edu/people/tom-costello",
    q_start="Thomas Costello is an Assistant Professor", q_end="at Carnegie Mellon University.",
    name_tok="Thomas Costello", dept_toks=["Social and Decision Sciences"],
    note="Dietrich College. Stated on the HCII affiliated-faculty profile; the guessed SDS profile URL 404'd.")
add(school="cmu", name="Joern Dengjel", home_department="Department of Biology, University of Fribourg (Switzerland)",
    url="https://www.cmu.edu/cbd/people/visiting-faculty.html",
    q_start="Joern Dengjel Visiting Professor", q_end="Department of Biology",
    name_tok="Joern Dengjel", dept_toks=["University of Fribourg", "Department of Biology"],
    note="EXTERNAL: not a CMU appointment. CBD lists him under 'Past Visiting Faculty'; CBD 'is not currently hosting faculty'.")
add(school="cmu", name="Steven Dow", home_department="Human-Computer Interaction Institute",
    url="https://hcii.cmu.edu/news/event/2015/12/hcii-seminar-series-steven-dow",
    q_start="Speaker Steven Dow", q_end="Carnegie Mellon University",
    name_tok="Steven Dow", dept_toks=["Human-Computer Interaction Institute"],
    note="LEFT CMU: core HCII assistant professor 2011-2015 (an SCS department, so not merely affiliated). Since 2016 at UC San Diego, "
         "'Associate Professor of Cognitive Science' per https://css.ucsd.edu/people/profiles/sdow.html ({sha:https://css.ucsd.edu/people/profiles/sdow.html}). "
         "Evidence is a Dec 2015 HCII seminar listing.")
add(school="cmu", name="Dannie Durand", home_department="Department of Biological Sciences",
    url="https://www.cmu.edu/bio/people/faculty/durand.html",
    q_start="Dannie Durand Dannie Durand Associate Professor", q_end="Department of Biological Sciences",
    name_tok="Dannie Durand", dept_toks=["Department of Biological Sciences"],
    note="Mellon College of Science. The CBD profile also says 'Associate Professor, Biological Sciences'.")
add(school="cmu", name="Jonathan Francis", home_department="Carnegie Bosch Institute (CBI)", no_academic_department=True,
    also=["Robotics Institute (courtesy faculty)"],
    url="https://www.ri.cmu.edu/ri-people/jonathan-francis/",
    q_start="Jonathan Francis Jonathan Francis Courtesy Faculty", q_end="Home Department: CBI",
    name_tok="Jonathan Francis", dept_toks=["Home Department: CBI"],
    note="Industry researcher, not CMU faculty: his own site says 'I am a Lead Research Scientist at the Bosch Center for Artificial "
         "Intelligence (BCAI)' and Courtesy Faculty in RI and Robotics Research Program Lead in the Carnegie Bosch Institute "
         "(https://jonfranc.com/ {sha:https://jonfranc.com/}). LTI lists him as a 2022 PhD alumnus.")
add(school="cmu", name="Gabe Gomes", home_department="Department of Chemical Engineering",
    also=["Department of Chemistry", "Machine Learning Department (courtesy)"],
    url="https://www.cheme.engineering.cmu.edu/directory/bios/gomes-gabe.html",
    q_start="Gabe Gomes Assistant Professor, Chemical Engineering", q_end="Departments of Chemistry and Chemical Engineering.",
    name_tok="Gabe Gomes", dept_toks=["Chemical Engineering"],
    note="Joint Chemistry/Chemical Engineering appointment. Chemical Engineering is listed first and hosts the profile; the Chemistry "
         "department people page ({sha:https://www.cmu.edu/chemistry/people/faculty/index.html}) does not list him. College of Engineering.")
add(school="cmu", name="Maggie Henderson", home_department="Department of Psychology",
    also=["Neuroscience Institute", "Machine Learning Department (affiliated)"],
    url="https://www.cmu.edu/dietrich/psychology/directory/core-training-faculty/henderson-maggie.html",
    q_start="Department of Psychology › People › Core and Training Faculty › Maggie Henderson", q_end="Machine Learning (Affiliated)",
    name_tok="Maggie Henderson", dept_toks=["Department of Psychology"],
    note="Dietrich College.")
add(school="cmu", name="Kenneth J Holstein", home_department="Human-Computer Interaction Institute",
    url="https://engineering.cmu.edu/directory/bios/holstein-kenneth.html",
    q_start="Kenneth Holstein Assistant Professor, Human-Computer Interaction Institute", q_end="at Carnegie Mellon University",
    name_tok="Kenneth Holstein", dept_toks=["Human-Computer Interaction Institute"],
    note="LEFT CMU (recent): was a core HCII (SCS) assistant professor. His own site now says 'I am an Assistant Professor at EPFL' "
         "(http://kenholstein.com/ -> https://www.thecoalalab.com/kenholstein, {sha:http://kenholstein.com/}), and the live HCII page "
         "lists him only as 'Affiliated Faculty' ({sha:https://hcii.cmu.edu/people/kenneth-holstein}). The CoE directory page quoted is stale.")
add(school="cmu", name="Jeff Ichnowski", home_department="Robotics Institute",
    url="https://www.ri.cmu.edu/ri-faculty/jeffrey-ichnowski/",
    q_start="Jeffrey Ichnowski Jeffrey Ichnowski Assistant Professor", q_end="Home Department: RI",
    name_tok="Jeffrey Ichnowski", dept_toks=["Home Department: RI"],
    note="Core SCS (RI) faculty although the census marks him 'unlisted'. The CoE Manufacturing Futures Institute directory also says "
         "'Assistant Professor, Robotics Institute' ({sha:https://engineering.cmu.edu/mfi/directory/bios/ichnowski-jeffrey.html}).")
add(school="cmu", name="Olexandr Isayev", home_department="Department of Chemistry",
    url="https://www.cmu.edu/chemistry/people/faculty/isayev.html",
    q_start="Department of Chemistry › People › faculty › Olexandr Isayev", q_end="Interdisciplinary Science, Chemistry",
    name_tok="Olexandr Isayev", dept_toks=["Department of Chemistry"],
    note="Mellon College of Science. The CBD profile still says 'Assistant Professor, Chemistry'; Chemistry now titles him Carl and Amy Jones Professor.")
add(school="cmu", name="Aaron M Johnson", home_department="Department of Mechanical Engineering",
    also=["Electrical and Computer Engineering (courtesy)", "Robotics Institute (courtesy)"],
    url="https://meche.engineering.cmu.edu/directory/bios/johnson-aaron.html",
    q_start="Aaron Johnson Professor, Mechanical Engineering", q_end="Robotics Institute",
    name_tok="Aaron Johnson", dept_toks=["Mechanical Engineering"],
    note="College of Engineering.")
add(school="cmu", name="Gauri Joshi", home_department="Department of Electrical and Computer Engineering",
    url="https://www.ece.cmu.edu/directory/bios/joshi-gauri.html",
    q_start="Gauri Joshi Gauri Joshi Professor", q_end="Electrical and Computer Engineering",
    name_tok="Gauri Joshi", dept_toks=["Electrical and Computer Engineering"],
    note="College of Engineering. Census lists her under RI.")
add(school="cmu", name="Inseung Kang", home_department="Department of Mechanical Engineering",
    also=["Robotics Institute (courtesy)"],
    url="https://engineering.cmu.edu/directory/bios/kang-inseung.html",
    q_start="Inseung Kang Assistant Professor, Mechanical Engineering", q_end="Department of Mechanical Engineering.",
    name_tok="Inseung Kang", dept_toks=["Department of Mechanical Engineering"],
    note="College of Engineering.")
add(school="cmu", name="Aisling Kelliher", home_department="School of Design",
    url="https://www.cmu.edu/news/stories/archives/2012/october/oct9_aislingkelliher.html",
    q_start="Aisling Kelliher has joined the full-time faculty", q_end="as an associate professor.",
    name_tok="Aisling Kelliher", dept_toks=["School of Design"],
    note="LEFT CMU: joined the School of Design (College of Fine Arts) in 2012, with an HCII adjunct role; moved to Virginia Tech CS in 2015 "
         "({sha:https://wordpress.cs.vt.edu/csblog/?p=806}); now 'Associate Professor of Cinematic Arts' at USC "
         "({sha:https://cinema.usc.edu/faculty/profile.cfm?id=62323}).")
add(school="cmu", name="Jionghao Lin", home_department="Faculty of Education, The University of Hong Kong",
    also=["Human-Computer Interaction Institute (affiliated assistant professor)"],
    url="https://sites.google.com/site/jiognhaolin/home",
    q_start="Hello! I am currently an Assistant Professor", q_end="University of Hong Kong .",
    name_tok=None, dept_toks=["Faculty of Education"], own_page_sentence=True,
    note="EXTERNAL: not a CMU appointment; a former HCII postdoc. The quote is from his personal Google Sites homepage. The institutional HCII page "
         "says only 'Dr. Jionghao Lin is an Assistant Professor at the University of Hong Kong' "
         "({sha:https://hcii.cmu.edu/people/jionghao-lin}).")
add(school="cmu", name="Carmel S Majidi", home_department="Department of Mechanical Engineering",
    also=["Biomedical Engineering (courtesy)", "Civil and Environmental Engineering (courtesy)",
          "Electrical and Computer Engineering (courtesy)", "Materials Science and Engineering (courtesy)", "Robotics Institute (courtesy)"],
    url="https://meche.engineering.cmu.edu/directory/bios/majidi-carmel.html",
    q_start="Carmel Majidi Clarence H. Adamson Professor", q_end="Robotics Institute",
    name_tok="Carmel Majidi", dept_toks=["Mechanical Engineering"],
    note="College of Engineering.")
add(school="cmu", name="Valentina Nisi", home_department="Instituto Superior Técnico, University of Lisbon",
    also=["Interactive Technologies Institute (LARSyS)", "Human-Computer Interaction Institute (affiliated faculty)"],
    url="https://hcii.cmu.edu/people/valentina-nisi",
    q_start="Valentina Nisi is a Professor at the Instituto Superior Tecnico", q_end="HCI Institute at Carnegie Mellon.",
    name_tok="Valentina Nisi", dept_toks=["Instituto Superior Tecnico"],
    note="EXTERNAL: not a CMU appointment (CMU Portugal affiliate). The page does not name her department within IST.")
add(school="cmu", name="Nuno Nunes", home_department="Instituto Superior Técnico, University of Lisbon",
    also=["Interactive Technologies Institute (president)", "Human-Computer Interaction Institute (affiliated faculty)"],
    url="https://hcii.cmu.edu/people/nuno-nunes",
    q_start="Nuno Jardim Nunes is a Professor of HCI", q_end="Interactive Technologies Institute",
    name_tok="Nuno Jardim Nunes", dept_toks=["Técnico"],
    note="EXTERNAL: not a CMU appointment (CMU Portugal affiliate). The page does not name his department within IST.")
add(school="cmu", name="Nikol Elisabet Rummel",
    home_department="Institut für Erziehungswissenschaft (Pädagogische Psychologie und Bildungstechnologie), Fakultät für Philosophie und Erziehungswissenschaft, Ruhr-Universität Bochum",
    also=["CAIS (Center for Advanced Internet Studies) research professorship"],
    url="https://www.pe.ruhr-uni-bochum.de/erziehungswissenschaft/pp/team/rummel.html.de",
    q_start="Pädagogische Psychologie und Bildungstechnologie » Team Prof. Dr. Nikol Rummel", q_end="Institut für Erziehungswissenschaft",
    name_tok="Nikol Rummel", dept_toks=["Institut für Erziehungswissenschaft"],
    note="EXTERNAL: not a CMU appointment. Her HCII page lists her only as 'Affiliated Faculty' ({sha:https://hcii.cmu.edu/people/nikol-rummel}). "
         "Bochum shows her as 'Univ.-Prof. on leave 2022-2027, CAIS Research Professor'.")
add(school="cmu", name="Michael Tarr", home_department="Department of Psychology",
    also=["Neuroscience Institute", "Machine Learning Department (affiliated)", "Robotics Institute (affiliated)"],
    url="https://www.cmu.edu/dietrich/psychology/directory/core-training-faculty/tarr-michael.html",
    q_start="Michael J Tarr Michael J Tarr", q_end="Robotics Institute (Affiliated)",
    name_tok="Michael J Tarr", dept_toks=["Department of Psychology"],
    note="Dietrich College; department head since 2014.")
add(school="cmu", name="Benjamin Titzer", home_department="Software and Societal Systems Department",
    url="https://s3d.cmu.edu/people/core-faculty/titzer-ben.html",
    q_start="Software and Societal Systems Department › People › core-faculty › Ben Titzer", q_end="Principal Researcher, Software and Societal Systems",
    name_tok="Ben Titzer", dept_toks=["Software and Societal Systems"],
    note="Core SCS (S3D core-faculty listing) although the census marks him 'unlisted'. The page title is Principal Researcher; the census says "
         "Associate Research Professor.")
add(school="cmu", name="Alex Waibel", home_department="Language Technologies Institute",
    url="https://lti.cmu.edu/people/faculty/waibel-alexander.html",
    q_start="Language Technologies Institute › People › Faculty › Alexander Waibel", q_end="Professor (On Leave), Language Technologies Institute",
    name_tok="Alexander Waibel", dept_toks=["Language Technologies Institute"],
    note="Core SCS (LTI) professor, currently on leave; also a professor at Karlsruhe Institute of Technology. The census places him "
         "'unlisted' under MLD.")
add(school="cmu", name="Steven Xia", home_department=None, status="hold",
    reason="No CMU page names a department for him. He is absent from the S3D faculty index "
           "({sha:https://s3d.cmu.edu/people/faculty-index.html}) and the guessed S3D profile URLs 404. His own homepage (today) still "
           "describes a UIUC PhD student, so this is probably an incoming hire whose pages are not yet up.",
    url="https://steven.cs.illinois.edu/",
    q_start="I am a final year Computer Science PhD student", q_end="advised by Lingming Zhang",
    name_tok=None, dept_toks=[], own_page_sentence=True,
    note="Assumed to be Chunqiu Steven Xia (UIUC, LLM agents for software engineering; 2026 faculty-candidate talks). Census: S3D, Assistant Professor.")
add(school="cmu", name="Byron Yu", home_department="Department of Electrical and Computer Engineering",
    also=["Department of Biomedical Engineering"],
    url="https://www.ece.cmu.edu/directory/bios/yu-byron.html",
    q_start="Byron Yu Byron Yu Professor", q_end="Biomedical Engineering",
    name_tok="Byron Yu", dept_toks=["Electrical and Computer Engineering"],
    note="Joint ECE/BME, College of Engineering; ECE is listed first and hosts the profile.")
add(school="cmu", name="Andrea Zanette", home_department="Department of Electrical and Computer Engineering",
    url="https://engineering.cmu.edu/directory/bios/zanette-andrea.html",
    q_start="Andrea Zanette Assistant Professor", q_end="Electrical and Computer Engineering",
    name_tok="Andrea Zanette", dept_toks=["Electrical and Computer Engineering"],
    note="College of Engineering.")
add(school="cmu", name="Natasa Miskov-Zivanov", home_department="Computer Science Department",
    url="https://web.archive.org/web/20150930044621id_/https://www.csd.cs.cmu.edu/people/adjunct-faculty/natasa-miskov-zivanov",
    q_start="Department(s): Computer Science Department", q_end="Senior Researcher",
    name_tok="Natasa Miskov-Zivanov", dept_toks=["Computer Science Department"],
    note="LEFT CMU: research staff ('Senior Researcher') in CSD per a 2015 capture; the live CSD page 404s. She is now at the University of "
         "Pittsburgh: her lab page lists her as Associate Professor with ECE students ({sha:https://nmzlab.pitt.edu/people}).")

# ----------------------------------------------------------------------------- MIT
CSAIL = "Computer Science and Artificial Intelligence Laboratory (CSAIL)"
add(school="mit", name="Ted Adelson", home_department="Department of Brain and Cognitive Sciences",
    also=["Computer Science and Artificial Intelligence Laboratory (investigator)"],
    url="https://bcs.mit.edu/directory/edward-adelson",
    q_start="Edward H Adelson Adelson Edward H Ph.D.", q_end="Faculty Appointment Primary",
    name_tok="Edward H Adelson", dept_toks=["Brain & Cognitive Sciences"],
    note="School of Science. BCS marks the appointment 'Primary'.")
add(school="mit", name="Andreea Bobu", home_department="Department of Aeronautics and Astronautics",
    url="https://aeroastro.mit.edu/people/andreea-bobu/",
    q_start="Andreea Bobu She/Her", q_end="Professor in Aeronautics and Astronautics",
    name_tok="Andreea Bobu", dept_toks=["Aeronautics and Astronautics"],
    note="School of Engineering. The MIT Catalog lists her as 'Assistant Professor of Aeronautics and Astronautics' "
         "({sha:https://catalog.mit.edu/schools/engineering/aeronautics-astronautics/}).")
add(school="mit", name="Michael Cafarella", home_department=CSAIL, no_academic_department=True,
    url="https://www.csail.mit.edu/person/michael-cafarella",
    q_start="Mike Cafarella is a Principal Research Scientist", q_end="Artificial Intelligence Lab.",
    name_tok="Cafarella", dept_toks=["Computer Science and Artificial Intelligence Lab"],
    note="Research staff. Census title is Senior Research Scientist; the bio says Principal.")
add(school="mit", name="Alan Edelman", home_department="Department of Mathematics",
    also=["Computer Science and Artificial Intelligence Laboratory"],
    url="https://math.mit.edu/directory/profile.html?pid=63",
    q_start="Alan Edelman PhD", q_end="AI Laboratories (CSAIL)",
    name_tok="Alan Edelman", dept_toks=["Department of Mathematics"],
    note="School of Science (applied mathematics).")
add(school="mit", name="Jim Glass", home_department=CSAIL, no_academic_department=True,
    url="https://www.csail.mit.edu/person/jim-glass",
    q_start="James Glass is a Senior Research Scientist", q_end="Artificial Intelligence Laboratory.",
    name_tok="James Glass", dept_toks=["Computer Science and Artificial Intelligence Laboratory"],
    note="Research staff; head of the Spoken Language Systems Group.")
add(school="mit", name="D. Fox Harrell", home_department="Comparative Media Studies/Writing (Comparative Media Studies Program)",
    also=["Computer Science and Artificial Intelligence Laboratory"],
    url="https://web.archive.org/web/20260115030548id_/https://cmsw.mit.edu/profile/fox-harrell/",
    q_start="D. Fox Harrell is Professor", q_end="Laboratory at MIT.",
    name_tok="D. Fox Harrell", dept_toks=["Comparative Media Studies"],
    note="School of Humanities, Arts, and Social Sciences. Wayback capture used because the live cmsw.mit.edu fetch failed TLS verification "
         "(incomplete certificate chain). Joint with CSAIL, not EECS.")
add(school="mit", name="Lalana Kagal", home_department=CSAIL, no_academic_department=True,
    url="https://www.csail.mit.edu/person/lalana-kagal",
    q_start="Lalana Kagal is a Principal Research Scientist", q_end="Artificial Intelligence Lab",
    name_tok="Lalana Kagal", dept_toks=["Computer Science and Artificial Intelligence Lab"], note="Research staff.")
add(school="mit", name="Boris Katz", home_department=CSAIL, no_academic_department=True,
    url="https://www.csail.mit.edu/person/boris-katz",
    q_start="Boris Katz is a Principal Research Scientist", q_end="Artificial Intelligence Laboratory.",
    name_tok="Boris Katz", dept_toks=["Computer Science and Artificial Intelligence Laboratory"],
    note="Research staff; head of the InfoLab Group.")
add(school="mit", name="Jonathan Kelner", home_department="Department of Mathematics",
    also=["Computer Science and Artificial Intelligence Laboratory"],
    url="https://math.mit.edu/directory/profile.html?pid=125",
    q_start="Jonathan Kelner Professor of Applied Mathematics", q_end="as of September, 2018.",
    name_tok="Kelner", dept_toks=["Mathematics"],
    note="MIT Department of Mathematics directory profile; the footer reads 'Massachusetts Institute of Technology Department of Mathematics'.")
add(school="mit", name="Tom Leighton", home_department="Department of Mathematics",
    also=["Computer Science and Artificial Intelligence Laboratory"],
    url="https://math.mit.edu/directory/profile.html?pid=144",
    q_start="Tom Leighton is a Professor of Applied Mathematics", q_end="(currently on leave).",
    name_tok="Tom Leighton", dept_toks=["Mathematics"],
    note="On leave from MIT; CEO of Akamai Technologies per the same page. Department of Mathematics directory profile.")
add(school="mit", name="John Leonard", home_department="Department of Mechanical Engineering",
    also=["Computer Science and Artificial Intelligence Laboratory"],
    url="https://www.csail.mit.edu/person/john-leonard",
    q_start="John J. Leonard is Samuel C. Collins Professor", q_end="Department of Mechanical Engineering.",
    name_tok="John J. Leonard", dept_toks=["Department of Mechanical Engineering"], note="School of Engineering.")
add(school="mit", name="Rachit Nigam", home_department="Department of Electrical Engineering and Computer Science",
    url="https://people.csail.mit.edu/rachit/full-bio",
    q_start="I am starting as an assistant professor", q_end="2025-26 academic year.",
    name_tok=None, dept_toks=["Department of Electrical Engineering and Computer Science"], own_page_sentence=True,
    note="Core EECS faculty (started Jan 2026) whom the census missed. The EECS people page lists him as 'Douglas Ross (1954) Career Development "
         "Professor of Software Technology, Assistant Professor [CS, EE]' ({sha:https://www.eecs.mit.edu/people/rachit-nigam/}).")
add(school="mit", name="Una-May O'Reilly", home_department=CSAIL, no_academic_department=True,
    url="https://alfagroup.csail.mit.edu/people",
    q_start="ALFA Lab @ MIT CSAIL", q_end="Principal Investigator",
    name_tok="Una-May O’Reilly", dept_toks=["MIT CSAIL"],
    note="Research staff; founder and leader of the ALFA group. Census title is Senior Research Scientist.")
add(school="mit", name="Aude Oliva", home_department=CSAIL, no_academic_department=True,
    also=["MIT-IBM Computing Research Lab (MIT director)"],
    url="https://mitibmwatsonailab.mit.edu/people/aude-oliva/",
    q_start="She is also a senior research scientist", q_end="Artificial Intelligence Laboratory (CSAIL)",
    name_tok=None, own_page_sentence=True, dept_toks=["Computer Science and Artificial Intelligence Laboratory"],
    note="Research staff; heads the Computational Perception and Cognition group. The CSAIL person page has no bio text.")
add(school="mit", name="Tomaso Poggio", home_department="Department of Brain and Cognitive Sciences",
    also=["Center for Brains, Minds and Machines (director)", "Computer Science and Artificial Intelligence Laboratory",
          "McGovern Institute for Brain Research"],
    url="https://bcs.mit.edu/directory/tomaso-poggio",
    q_start="Tomaso A. Poggio is the Eugene McDermott Professor", q_end="Department of Brain and Cognitive Sciences",
    name_tok="Tomaso A. Poggio", dept_toks=["Department of Brain and Cognitive Sciences"],
    note="School of Science. The same BCS profile header says 'Faculty Appointment Primary'.")
add(school="mit", name="Nicholas Roy", home_department="Department of Aeronautics and Astronautics",
    also=["Computer Science and Artificial Intelligence Laboratory"],
    url="https://www.csail.mit.edu/person/nicholas-roy",
    q_start="Nicholas Roy is a Professor of Aeronautics and Astronautics", q_end="at MIT",
    name_tok="Nicholas Roy", dept_toks=["Aeronautics and Astronautics"],
    note="School of Engineering. The MIT Catalog lists him as Jerome C. Hunsaker Professor in AeroAstro "
         "({sha:https://catalog.mit.edu/schools/engineering/aeronautics-astronautics/}).")
add(school="mit", name="Stephanie Seneff", home_department=CSAIL, no_academic_department=True,
    url="https://www.csail.mit.edu/person/stephanie-seneff",
    q_start="Stephanie Seneff is a Senior Research Scientist", q_end="Artificial Intelligence Laboratory.",
    name_tok="Stephanie Seneff", dept_toks=["Computer Science and Artificial Intelligence Laboratory"], note="Research staff.")
add(school="mit", name="Julie Shah", home_department="Department of Aeronautics and Astronautics",
    also=["Computer Science and Artificial Intelligence Laboratory"],
    url="https://aeroastro.mit.edu/?p=2615",
    q_start="Julie Shah H.N. Slater Professor", q_end="Aeronautics and Astronautics",
    name_tok="Julie Shah", dept_toks=["Aeronautics and Astronautics"],
    note="School of Engineering; AeroAstro department head since May 2024. The MIT Catalog marks her '(On leave)' "
         "({sha:https://catalog.mit.edu/schools/engineering/aeronautics-astronautics/}).")
add(school="mit", name="Peter Shor", home_department="Department of Mathematics",
    also=["Computer Science and Artificial Intelligence Laboratory"],
    url="https://math.mit.edu/directory/profile.html?pid=247",
    q_start="Peter Shor is Morss Professor of Applied Mathematics", q_end="since 2003.",
    name_tok="Peter Shor", dept_toks=["Mathematics"], note="Department of Mathematics directory profile.")
add(school="mit", name="Howard Shrobe", home_department=CSAIL, no_academic_department=True,
    url="https://people.csail.mit.edu/hes/",
    q_start="I am currently serving as a Program Manager", q_end="Principal Research Scientist MIT CSAIL",
    name_tok=None, dept_toks=["MIT CSAIL"], own_page_sentence=True,
    note="Research staff, currently a DARPA I2O program manager and 'not conducting research on campus'.")
add(school="mit", name="Michael Sipser", home_department="Department of Mathematics",
    also=["Computer Science and Artificial Intelligence Laboratory"],
    url="https://math.mit.edu/directory/profile.html?pid=251",
    q_start="Michael Sipser is a theoretical computer scientist.", q_end="a member of CSAIL",
    name_tok="Michael Sipser", dept_toks=["Mathematics"],
    note="Donner Professor of Mathematics; Dean of Science 2013-2020. His CSAIL page still says 'Chairman of Applied Mathematics'.")
add(school="mit", name="Daniel Weitzner", home_department=CSAIL, no_academic_department=True,
    also=["MIT Internet Policy Research Initiative (founding director)"],
    url="https://www.csail.mit.edu/person/daniel-weitzner",
    q_start="Daniel J. Weitzner holds the 3Com Founders", q_end="Policy Research Initiative",
    name_tok="Daniel J. Weitzner", dept_toks=["CSAIL"],
    note="Research staff. He teaches Internet policy in EECS (same page) but holds no faculty appointment there.")
add(school="mit", name="Brian Williams", home_department="Department of Aeronautics and Astronautics",
    also=["Computer Science and Artificial Intelligence Laboratory"],
    url="https://catalog.mit.edu/schools/engineering/aeronautics-astronautics/",
    q_start="Brian C. Williams, PhD", q_end="Professor of Aeronautics and Astronautics",
    name_tok="Brian C. Williams", dept_toks=["Aeronautics and Astronautics"],
    note="MIT Catalog faculty list for the Department of Aeronautics and Astronautics. His AeroAstro profile lists 'Professor of Aeronautics and "
         "Astronautics, 2007-Present' ({sha:https://aeroastro.mit.edu/people/brian-c-williams/}).")
add(school="mit", name="Joshua Tenenbaum", home_department="Department of Brain and Cognitive Sciences",
    also=["Computer Science and Artificial Intelligence Laboratory (investigator)", "Center for Brains, Minds, and Machines"],
    url="https://bcs.mit.edu/directory/joshua-b-tenenbaum",
    q_start="Joshua B Tenenbaum Tenenbaum Joshua B Ph.D.", q_end="Faculty Appointment Primary",
    name_tok="Joshua B Tenenbaum", dept_toks=["Brain & Cognitive Sciences"],
    note="School of Science. BCS marks the appointment 'Primary'.")
add(school="mit", name="Steve Ward", home_department="Department of Electrical Engineering and Computer Science",
    url="https://www.eecs.mit.edu/people/stephen-ward/",
    q_start="Home People Stephen Ward", q_end="Electrical Engineering & Computer Science Department",
    name_tok="Stephen Ward", dept_toks=["Electrical Engineering & Computer Science Department"],
    note="EMERITUS EECS professor ('Professor of CS and Engineering (Emeritus)' on the EECS people page). EECS core, not another department.")
add(school="mit", name="Adrian Dalca",
    home_department="A.A. Martinos Center for Biomedical Imaging, Massachusetts General Hospital / Harvard Medical School",
    also=["Massachusetts Institute of Technology (CSAIL research affiliate)"],
    url="https://www.mit.edu/~adalca/",
    q_start="Adrian V. Dalca Assistant Professor", q_end="Harvard Medical School",
    name_tok="Adrian V. Dalca", dept_toks=["Martinos Center", "Harvard Medical School"],
    note="EXTERNAL: his primary appointment is HMS/MGH; CSAIL lists him only as a Research Affiliate. The page does not name the HMS "
         "department (radiology).")
add(school="mit", name="Erik Hemberg", home_department=CSAIL, no_academic_department=True,
    url="https://www.csail.mit.edu/person/erik-hemberg",
    q_start="Erik Hemberg Research Scientist", q_end="hembergerik@CSAIL.MIT.EDU",
    name_tok="Erik Hemberg", dept_toks=["CSAIL"],
    note="Research staff, co-leader of the ALFA group. The CSAIL directory entry names the lab only through its csail.mit.edu address. "
         "The ALFA page ({sha:https://alfagroup.csail.mit.edu/people}) lists 'Erik Hemberg Co-leader, Research Scientist'.")
add(school="mit", name="Karen Sollins", home_department=CSAIL, no_academic_department=True,
    url="https://groups.csail.mit.edu/ana/People/Sollins.html",
    q_start="Karen Sollins Dr. Karen Sollins", q_end="Advanced Network Architecture Group at CSAIL.",
    name_tok="Karen Sollins", dept_toks=["CSAIL"],
    note="Research staff (Principal Research Scientist, ANA group, per an undated group page). The live CSAIL directory now lists her only as "
         "'Research Affiliate' ({sha:https://www.csail.mit.edu/person/karen-sollins}), probably retired.")
add(school="mit", name="Neil Thompson", home_department=CSAIL, no_academic_department=True,
    also=["MIT Initiative on the Digital Economy (principal investigator)"],
    url="https://www.csail.mit.edu/person/neil-thompson",
    q_start="Neil Thompson is the Director of the FutureTech", q_end="Artificial Intelligence Lab",
    name_tok="Neil Thompson", dept_toks=["Computer Science and Artificial Intelligence Lab"],
    note="Research staff. Formerly an assistant professor at MIT Sloan.")
add(school="mit", name="Judy Brewer", home_department=CSAIL + " — W3C Web Accessibility Initiative", no_academic_department=True,
    url="https://web.archive.org/web/20221130235544id_/https://www.csail.mit.edu/person/judy-brewer",
    q_start="Judy Brewer directs the Web Accessibility Initiative", q_end="part of MIT CSAIL.",
    name_tok="Judy Brewer", dept_toks=["MIT CSAIL"],
    note="LEFT: the live CSAIL page is login-restricted, so a 2022 Wayback capture was used. Per W3C she directed WAI until January 2023 and "
         "'was a Principal Research Scientist at MIT's CSAIL' ({sha:https://www.w3.org/People/Brewer}).")
add(school="mit", name="John Fisher", home_department=CSAIL, no_academic_department=True,
    url="https://sli.csail.mit.edu/people",
    q_start="John W. Fisher III ( fisher@csail.mit.edu )", q_end="Artificial Intelligence Laboratory",
    name_tok="John W. Fisher III", dept_toks=["Computer Science and Artificial Intelligence Laboratory"],
    note="Research staff; runs the Sensing, Learning, and Inference group. The live CSAIL person page is login-restricted "
         "({sha:https://www.csail.mit.edu/person/john-fisher}).")
add(school="mit", name="Michael Goemans", home_department="Department of Mathematics",
    also=["Computer Science and Artificial Intelligence Laboratory (Theory of Computation group)"],
    url="https://math.mit.edu/directory/profile.html?pid=84",
    q_start="Michel Goemans is the RSA Professor of Mathematics", q_end="Department Head of the Mathematics Department",
    name_tok="Michel Goemans", dept_toks=["Mathematics Department"],
    note="The input name 'Michael' is the CSAIL spelling; MIT Mathematics writes 'Michel'. He is the Mathematics department head.")
add(school="mit", name="Jeffrey Jaffe", home_department=CSAIL + " — World Wide Web Consortium (W3C)", no_academic_department=True,
    url="https://web.archive.org/web/20220926215015id_/https://www.csail.mit.edu/person/jeffrey-jaffe",
    q_start="PI Core/Dual Jeffrey Jaffe Principal Research Scientist", q_end="Email jeff@w3.org",
    name_tok="Jeffrey Jaffe", dept_toks=[], status="hold",
    reason="The only institutional statement is a CSAIL directory entry (2022 Wayback, now login-restricted) titling him 'Principal Research "
           "Scientist'. No quote within 300 characters names CSAIL together with his name; W3C's own page omits MIT.",
    note="LEFT: W3C CEO March 2010 - November 2022 ({sha:https://www.w3.org/People/Jeff}). W3C left MIT hosting in 2023.")
add(school="mit", name="Bill Long", home_department=CSAIL, no_academic_department=True,
    url="https://groups.csail.mit.edu/medg/people/wjl/index.html",
    q_start="William J. Long MIT CSAIL", q_end="Clinical Decision Making Group",
    name_tok="William J. Long", dept_toks=["MIT CSAIL"],
    note="Research staff. The group page is old, and the live CSAIL person page is login-restricted "
         "({sha:https://www.csail.mit.edu/person/bill-long}); his current status is unclear.")
add(school="mit", name="Ruth Rosenholtz", home_department="Department of Brain and Cognitive Sciences",
    also=["Computer Science and Artificial Intelligence Laboratory (member)"],
    url="https://web.archive.org/web/20240419114013id_/https://www.csail.mit.edu/person/ruth-rosenholtz",
    q_start="Ruth Rosenholtz is a Principal Research Scientist", q_end="a member of CSAIL.",
    name_tok="Ruth Rosenholtz", dept_toks=["Department of Brain and Cognitive Sciences"],
    note="LEFT: research staff (not faculty) in BCS. Her NVIDIA page says she 'joined NVIDIA Research in 2023' "
         "({sha:https://research.nvidia.com/person/ruth-rosenholtz}). The live CSAIL page is login-restricted, so a 2024 Wayback capture was used.")
add(school="mit", name="F. J. Corbato", home_department="Department of Electrical Engineering and Computer Science",
    url="https://web.archive.org/web/20191016190800id_/https://www.csail.mit.edu/person/f-j-corbato",
    q_start="Fernando J. Corbato, Professor Emeritus", q_end="at M.I.T.",
    name_tok="Fernando J. Corbato", dept_toks=["Department of Electrical Engineering and Computer Science"],
    note="DECEASED: died 12 July 2019 ({sha:https://www.csail.mit.edu/news/fernando-corby-corbato-1926-2019}). Emeritus EECS, so EECS core. "
         "A Wayback capture was used because the live CSAIL page is login-restricted.")

# ----------------------------------------------------------------------------- EPFL
def epfl(name, display, home, url, crumb, toks, also=(), note="", q_end=None, **kw):
    add(school="epfl", name=name, home_department=home, also=list(also), url=url,
        q_start=display, q_after="Administrative data", q_end=q_end or crumb,
        name_tok=display, dept_toks=toks, note=(note + " " + EPFL_DECODE).strip(), **kw)

STI_IEM = "School of Engineering (STI) — Institute of Electrical and Micro Engineering (IEM)"
SB_MATH = "School of Basic Sciences (SB) — Institute of Mathematics (MATH)"
ENAC_IIE = "School of Architecture, Civil and Environmental Engineering (ENAC) — Environmental Engineering Institute (IIE)"
ENAC_IIC = "School of Architecture, Civil and Environmental Engineering (ENAC) — Civil Engineering Institute (IIC)"
P = "https://people.epfl.ch/"
epfl("Alcherio Martinoli", "Alcherio Martinoli", ENAC_IIE, P + "alcherio.martinoli", "EPFL ENAC IIE DISAL", ["ENAC", "IIE"],
     also=["School of Engineering (STI) — Section of Microengineering (SMT) teaching", "ENAC — Environmental Sciences and Engineering section (SSIE) teaching"],
     note="Lab DISAL. The quote ends at the unit's postal code string; the breadcrumb 'EPFL › ENAC › IIE › DISAL' follows.")
epfl("Alexandre Alahi", "Alexandre Alahi", ENAC_IIC, P + "alexandre.alahi", "EPFL › ENAC › IIC › VITA", ["ENAC", "IIC"],
     also=["ENAC — Civil Engineering section (SGC) teaching"], note="Lab VITA.")
epfl("Ali H. Sayed", "Ali H. Sayed", STI_IEM, P + "ali.sayed", "EPFL › STI › IEM › ASL", ["STI", "IEM"],
     also=["STI — Electrical Engineering section (SEL) teaching"],
     note="Lab ASL. The address line still uses the older 'STI IEL' code; the hierarchy breadcrumb gives IEM.")
epfl("Andreas Peter Burg", "Andreas Peter Burg", STI_IEM, P + "andreas.burg", "EPFL › STI › IEM › TCL", ["STI", "IEM"],
     also=["STI — Electrical Engineering section (SEL) teaching"], note="Lab TCL. The address line says 'STI IEL'; the breadcrumb says IEM.")
epfl("Andrés Cristi", "Andrés Cristi", "College of Management of Technology (CDM) — Management of Technology & Entrepreneurship Institute (MTEI)",
     P + "andres.cristi", "EPFL › CDM › MTEI › GO", ["CDM", "MTEI"], note="Chair GO (Game Theory and Operations).")
epfl("Auke Ijspeert", "Auke Ijspeert", "School of Engineering (STI) — Institute of Bioengineering (IBI-STI)", P + "auke.ijspeert",
     "EPFL › STI › IBI-STI › BIOROB", ["STI", "IBI-STI"],
     also=["STI — Institute of Mechanical Engineering (IGM) administration", "School of Life Sciences (SV) — SSV teaching"], note="Lab BIOROB.")
epfl("Clément Hongler", "Clément Hongler", SB_MATH, P + "clement.hongler", "EPFL › SB › MATH › CSFT", ["SB", "MATH"],
     note="Chair CSFT.")
epfl("Damir Filipovic", "Damir Filipovic", "College of Management of Technology (CDM) — Swiss Finance Institute (SFI)", P + "damir.filipovic",
     "EPFL › CDM › SFI › CSF", ["CDM", "SFI"], also=["CDM — Financial Engineering section (IF) teaching"], note="Swissquote Chair in Quantitative Finance.")
epfl("Daniel Gatica-Perez", "Daniel Gatica-Perez", STI_IEM, P + "daniel.gatica-perez", "EPFL › STI › IEM › LIDIAP", ["STI", "IEM"],
     also=["School of Computer and Communication Sciences (IC) — Social Computing Group (SCI-IC-DGP, IC › IINFCOM), head of unit",
           "IC — Digital Humanities section (SODH) teaching"],
     note="Adjunct Professor; his first-listed position is in the LIDIAP unit (the EPFL-hosted Idiap link). He also heads an IC unit, SCI-IC-DGP, "
          "so IC is a strong secondary home.")
epfl("Devis Tuia", "Devis Tuia", ENAC_IIE, P + "devis.tuia", "EPFL › ENAC › IIE › ECEO", ["ENAC", "IIE"],
     also=["ENAC — SSIE section director"], note="Lab ECEO (EPFL Valais Wallis, Sion).")
epfl("Florent Krzakala", "Florent Krzakala", STI_IEM, P + "florent.krzakala", "EPFL › STI › IEM › IDEPHICS1", ["STI", "IEM"],
     also=["School of Basic Sciences (SB) — Institute of Physics (IPHYS), IDEPHICS2"],
     note="Joint STI/SB lab (IdePHICS); the STI/IEM unit is listed first.")
epfl("François Fleuret", None, STI_IEM, "https://web.archive.org/web/20241207185408id_/https://people.epfl.ch/francois.fleuret", None,
     ["School of Engineering"], also=["Department of Computer Science, University of Geneva (primary employer)"],
     q_end="Polytechnique Fédérale de Lausanne.",
     note="LEFT / NOT LISTED: the live people.epfl.ch page returns 404 today ({sha:https://people.epfl.ch/francois.fleuret}). A Dec 2024 Wayback "
          "capture shows Adjunct Professor in LIDIAP, 'EPFL > STI > IEM > LIDIAP'. Primary employer: University of Geneva.")
epfl("Friedrich Eisenbrand", "Friedrich Eisenbrand", SB_MATH, P + "friedrich.eisenbrand", "EPFL › SB › MATH › DISOPT", ["SB", "MATH"],
     also=["School of Computer and Communication Sciences (IC) — courtesy appointment (IC deanship)"], note="Chair DISOPT.")
epfl("Frédéric Kaplan", "Frédéric Kaplan", "School of Computer and Communication Sciences (IC) — IINFCOM", P + "frederic.kaplan",
     "EPFL › IC › IINFCOM › DHLAB", ["IC", "IINFCOM"],
     also=["College of Humanities (CDH) — Digital Humanities Institute (DHI): postal unit string", "ENAC — Architecture section (SAR) teaching",
           "IC — Digital Humanities section (SODH) teaching"],
     note="SURPRISE: the directory hierarchy places DHLAB under IC (IC › IINFCOM), so he looks IC-hosted rather than affiliated from another school. "
          "His postal unit string still reads 'EPFL CDH DHI DHLAB' (College of Humanities), which suggests a recent move of DH into IC. IINFCOM is "
          "the same IC unit that hosts core IC labs (e.g. 'EPFL › IC › IINFCOM › DCL' for R. Guerraoui, {sha:https://people.epfl.ch/rachid.guerraoui}); "
          "its long name was not found on a fetched page.")
epfl("Giuseppe Carleo", "Giuseppe Carleo", "School of Basic Sciences (SB) — Institute of Physics (IPHYS)", P + "giuseppe.carleo",
     "EPFL › SB › IPHYS › CQSL", ["SB", "IPHYS"], also=["STI — SSIQ co-director"], note="Lab CQSL.")
epfl("Laura Grigori", "Laura Grigori", SB_MATH, P + "laura.grigori", "EPFL › SB › MATH › HPNALGS", ["SB", "MATH"], note="Chair HPNALGS.")
epfl("Lénaïc Chizat", "Lénaïc Chizat", SB_MATH, P + "lenaic.chizat", "EPFL SB MATH DOLA", ["SB", "MATH"],
     note="Chair DOLA. The quote ends at the unit's postal code string 'EPFL SB MATH DOLA'; the breadcrumb 'EPFL › SB › MATH › DOLA' follows it.")
epfl("Mahsa Shoaran", "Mahsa Shoaran", STI_IEM, P + "mahsa.shoaran", "EPFL STI IEL INL", ["STI"],
     also=["STI — Neuro-X Institute (INX-STI)"], note="Lab INL (Campus Biotech, Geneva). The quote ends at the postal unit string, which still uses the legacy code 'STI IEL'. The same page's hierarchy breadcrumb, just after the 300-character window, reads 'EPFL › STI › IEM › INL', the source of the IEM placement.")
epfl("Marco Mattavelli", "Marco Mattavelli", STI_IEM, "https://web.archive.org/web/20260316025657id_/https://people.epfl.ch/marco.mattavelli",
     "EPFL › STI › IEM › SCI-STI-MM", ["STI", "IEM"],
     note="Senior Scientist (MER), not a professor. A March 2026 Wayback capture shows group SCI-STI-MM under STI › IEM. The live page now "
          "lists only 'Invited guest, SEL - Teaching' ({sha:https://people.epfl.ch/marco.mattavelli}), probably retired.")
epfl("Mario Paolone", "Mario Paolone", STI_IEM, P + "mario.paolone", "EPFL › STI › IEM › DESL", ["STI", "IEM"],
     also=["EPFL Energy Center (CEN) — chairman of the directorate"], note="Lab DESL.")
epfl("Maryam Kamgarpour", "Maryam Kamgarpour", "School of Engineering (STI) — Institute of Mechanical Engineering (IGM)", P + "maryam.kamgarpour",
     "EPFL › STI › IGM › SYCAMORE", ["STI", "IGM"], also=["STI — Mechanical Engineering section (SGM) teaching"], note="Lab SYCAMORE.")
epfl("Maryna Viazovska", "Maryna Viazovska", SB_MATH, P + "maryna.viazovska", "EPFL › SB › MATH › TN", ["SB", "MATH"],
     note="Chair of Number Theory; also Director of the Institute of Mathematics (MATH).")
epfl("Mats Julius Stensrud", "Mats Julius Stensrud", SB_MATH, P + "mats.stensrud", "EPFL › SB › MATH › BIOSTAT", ["SB", "MATH"],
     note="Chair BIOSTAT.")
epfl("Nicolas Boumal", "Nicolas Boumal", SB_MATH, P + "nicolas.boumal", "EPFL SB SMA-GE", ["SB"],
     note="Chair OPTIM. His first-listed position is the SB mathematics section (SMA, quoted). The second, 'Chair of Continuous Optimization EPFL SB MATH OPTIM' with breadcrumb 'EPFL › SB › MATH › OPTIM', is beyond the 300-character window from his name. The lab page says 'OPTIM is part of the Institute of Mathematics at EPFL' ({sha:https://www.epfl.ch/labs/optim/}).")
epfl("Olaf Blanke", "Olaf Blanke", "School of Life Sciences (SV) — Neuro-X Institute (INX-SV)", P + "olaf.blanke",
     "EPFL › SV › INX-SV › LNCO", ["SV", "INX-SV"],
     note="Lab LNCO (Campus Biotech, Geneva). The postal unit string still reads 'EPFL SV BMI LNCO' (Brain Mind Institute); the breadcrumb "
          "places it in Neuro-X.")
epfl("Olga Fink", "Olga Fink", ENAC_IIC, P + "olga.fink", "EPFL › ENAC › IIC › IMOS", ["ENAC", "IIC"], note="Lab IMOS.")
epfl("Olivier Verscheure", "Olivier Verscheure", "Swiss Data Science Center (SDSC)", P + "olivier.verscheure",
     "EPFL › VPS › SDSC › SDSC-GE", ["SDSC"], no_academic_department=True,
     also=["School of Computer and Communication Sciences (IC) — SSC and SIN sections (adjunct teaching)",
           "School of Engineering (STI) — SEL section (adjunct teaching)"],
     note="Executive Director of the SDSC (a joint EPFL-ETH center under a vice-presidency, VPS), not a school unit. His adjunct professorship is "
          "teaching-only, in IC and STI sections.")
epfl("Pascal Frossard", "Pascal Frossard", STI_IEM, P + "pascal.frossard", "EPFL › STI › IEM › LTS4", ["STI", "IEM"],
     also=["School of Computer and Communication Sciences (IC) — courtesy appointment (IC deanship)", "EPFL AI Center — academic co-director"],
     note="Lab LTS4.")
epfl("Philippe Schwaller", "Philippe Schwaller", "School of Basic Sciences (SB) — Institute of Chemical Sciences and Engineering (ISIC)",
     P + "philippe.schwaller", "EPFL › SB › ISIC › LIAC", ["SB", "ISIC"], note="Lab LIAC.")
epfl("Volkan Cevher", "Volkan Cevher", STI_IEM, P + "volkan.cevher", "EPFL › STI › IEM › LIONS", ["STI", "IEM"],
     also=["STI — Electrical Engineering section (SEL) teaching"], note="Lab LIONS. The address line says 'STI IEL'; the breadcrumb says IEM.")

# Fleuret: own-page "He is ..." sentence (Wayback people page).
for d in D:
    if d["name"] == "François Fleuret":
        d["q_start"] = "He is Full Professor in the department of Computer Science"
        d.pop("q_after", None)
        d["name_tok"] = None
        d["own_page_sentence"] = True
