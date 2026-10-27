"""Reviewed decisions for every candidate of the CS-related scope (2026-10-22). Keys are the names as the candidate
sources write them. Values: (decision, code, reason, evidence specs). Evidence specs are resolved by build_review.py:
  ('kilthub_author', student)          the person's own CMU dissertation on KiltHub (figshare API record)
  ('ra_author', url)                   the person's own SCS tech-report thesis page
  ('census', census name)              the census row's title and its first quoted source (census/cmu-faculty.json)
  ('scsdir', name)                     the person's entry in the captured SCS directory JSON (listings store)
  ('collection', name)                 the site collection's role record for the person and its source
  ('listing', capture_url, regex)      a captured department listing (copied into the review store), exact quote
  ('page', url, regex)                 a captured page (fetched into the review store), exact quote
  ('override', name)                   the reviewed exclusion already in hierarchy/census-overrides.json
  ('pi', name)                         already a PI in hierarchy/cmu/pis.json
  ('qualified', name)                  qualified; see census/cmu-additions.json
  ('searched', text)                   what was searched without finding a basis
"""
Q = 'qualified'
R = 'rejected'
ECE16 = 'https://web.archive.org/web/20160402213820id_/http://www.ece.cmu.edu/directory/department/faculty/index.html'
ECE26 = 'https://web.archive.org/web/20260908154128id_/https://www.ece.cmu.edu/directory/faculty.html'
ECEC26 = 'https://web.archive.org/web/20260811153043id_/https://www.ece.cmu.edu/directory/courtesy-faculty.html'
NO_ADV = 'KiltHub dissertations 2016-2026 (hierarchy/cmu/thesis-captures.sqlite, every Advisor(s) field) and SCS thesis committees name no thesis advised by this person'
D = {}


def q(*names):
    for n in names:
        D[n] = (Q, 'qualified', 'faculty outside the SCS departments, PI, CS-related: see census/cmu-additions.json', [('qualified', n)])


q('Jose M. F. Moura', 'Soummya Kar', 'Aswin C. Sankaranarayanan', 'Carlee Joe-Wong', 'Marios Savvides', 'Benjamin Moseley', 'Pulkit Grover',
  'Osman Yagan', 'Sivaraman Balakrishnan', 'Ding Zhao', 'Sarah Bergbreiter', 'Kenji Shimada', 'Ole J. Mengshoel', 'Victoria A. Webster-Wood',
  'Alan Scheller-Wolf', 'Ragunathan Raj Rajkumar', 'B. V. K. Vijaya Kumar', 'Jing Lei', 'Diana Marculescu', 'Willem-Jan van Hoeve', 'Daragh Byrne',
  'Richard M. Stern', 'Ian Lane', 'Asim Smailagic', 'Gérard Cornuéjols', 'Tze Meng Low', 'Alexandra Chouldechova', 'Fatma Kılınç-Karzan',
  'Franz Franchetti', 'James C. Hoe', 'Philip Koopman', 'Xin Li', 'Javier Peña', 'Patrick Tague', 'Rinaldo, Alessandro', 'Pei Zhang', 'David Danks',
  'L. Richard Carley', 'Matey Neykov', 'Kuchibhotla, Arun Kumar', 'Jiashun Jin', 'Radu Marculescu', 'Bruno Sinopoli', 'Priya Narasimhan',
  'George H. Chen', 'Shawn Blanton', 'Bob Iannucci', 'Jeremy C. Weiss', 'Steven H. Collins', 'Jelena Kovacevic', 'John Lehoczky', 'Koushil Sreenath',
  'Molly Wright Steenson', 'John Paul Shen', 'Katherine A. Flanigan', 'Yorie Nakahira', 'Timothy X Brown', 'Ozan K. Tonguz', 'Hyong S. Kim',
  'Vanessa Chen', 'Nicola Secomandi', 'Timothy Brown', 'Fatma Kilinc-Karzan', 'Fatma Kılınç-Karzen', 'Steve Awodey', 'Larry Pileggi',
  'Virgil D. Gligor', 'Guannan Qu', 'Beidi Chen', 'Yongjie Jessica Zhang', 'Douglas J. Weber', 'Levent Burak Kara', 'Amir Barati Farimani',
  'Conrad S. Tucker', 'Mario Bergés', 'Matteo Pozzi', 'Burcu Akinci', 'Hae Young Noh', 'John Hooker', 'Anita Williams Woolley', 'Kathryn Roeder',
  "Edward H. Kennedy", "Max G'Sell", 'Rema Padman', 'Shixiang Zhu', 'Peter Spirtes', 'Alex John London', 'Adam Bjorndahl', 'Clark Glymour',
  'John R. Anderson', 'Laurie M. Heller', 'Alan Frieze', 'Daniel Cardoso Llach')


def stu(name, *ev):
    D[name] = (R, 'student', 'CMU PhD/master\'s student in the window, not faculty', list(ev) or [('collection', name)])


def pdoc(name, *ev):
    D[name] = (R, 'postdoc', 'postdoctoral researcher at CMU, not faculty', list(ev) or [('collection', name)])


# students (their own CMU theses where KiltHub or the SCS archive has them)
for n, s in [('Xuankai Chang', 'Xuankai Chang'), ('Huy A. Nguyen', 'Huy Anh Nguyen'), ('Yifan Peng', 'Yifan Peng'), ('Isaac Grosof', 'Isaac Grosof'),
             ('Siddharth Dalmia', 'Siddharth Dalmia'), ('Bryan Hooi', 'Bryan Hooi'), ('Gabriele Farina', 'Gabriele Farina'), ('Haohan Wang', 'Haohan Wang'),
             ('Xinjian Li', 'Xinjian Li'), ('Zhiting Hu', 'Zhiting Hu'), ('Rachata Ausavarungnirun', 'Rachata  Ausavarungnirun'), ('Valerie Chen', 'Valerie Chen'),
             ('Tiancheng Zhao', 'Tiancheng Zhao'), ('Shijia Pan', 'Shijia  Pan'), ('Xinlei Chen', 'Xinlei Chen'), ('Yifan Song', 'Yifan Song'),
             ('Iain Cruickshank', 'Iain Cruickshank'), ('David Wajc', 'David Wajc'), ('Vitercik, Ellen', 'Ellen Vitercik'), ('Yuanhao Wei', 'Yuanhao Wei'),
             ('Rudy Zhou', 'Rudy Zhou'), ('Amirbehshad Shahrasbi', 'Amirbehshad Shahrasbi'), ('Alex L. Wang', 'Alex Wang'), ('Ziye Tang', 'Ziye Tang'),
             ('Olha Silina', 'Olha Silina'), ('Ziv Scully', 'Ziv Scully')]:
    stu(n, ('kilthub_author', s))
for n, u in [('Nisarg Shah', 'http://reports-archive.adm.cs.cmu.edu/anon/2016/abstracts/16-121.html'),
             ('Justin Raizes', 'http://reports-archive.adm.cs.cmu.edu/anon/2025/abstracts/25-107.html'),
             ('Yihan Sun', 'http://reports-archive.adm.cs.cmu.edu/anon/2019/abstracts/19-128.html'),
             ('Wang, Ruosong', 'http://reports-archive.adm.cs.cmu.edu/anon/2022/abstracts/22-100.html'),
             ('Goran Zuzic', 'http://reports-archive.adm.cs.cmu.edu/anon/2020/abstracts/20-121.html'),
             ('Charles McGuffey', 'http://reports-archive.adm.cs.cmu.edu/anon/2021/abstracts/21-109.html')]:
    stu(n, ('ra_author', u))
for n in ['Conrad Borchers', 'Paul Pu Liang', 'Lynnette Hui Xian Ng', 'Jiatong Shi', 'Franklin Mingzhe Li', 'Siddhant Arora', 'Xiangrui Zeng', 'Brian Yan',
          'Wesley Hanwen Deng', 'Riku Arakawa', 'Amir Zadeh', 'Jaemarie Solyst', 'Tian, Jinchuan', 'Anagnostides, Ioannis', 'Renfei Zhou', 'Peter Manohar',
          'Junxing Wang', 'Jeff Xu']:
    stu(n)
for n in ['Mo, Shentong', 'Eason Chen', 'Yunze Xiao', 'Sherry Sarkar']:
    D[n] = (R, 'student', 'student author: no faculty listing at CMU in any department; OpenAlex output is first/middle-author student work', [('searched', 'department faculty listings captured for this review (ECE, MechE, CEE, Statistics, Tepper, Heinz, Philosophy, Psychology, Math, Architecture, Design, EPP, BME, Chemistry, Physics, SDS, CMU-Africa) and the SCS listings')])
D['Site Li'] = (R, 'student', 'CMU PhD student (Chemistry dissertation 2022), not faculty', [('kilthub_author', 'Site Li')])
D['Yang Zhang'] = (R, 'student', 'CMU HCII PhD (2021 dissertation); the CBD "Yang Zhang" on the SCS directory is project staff; neither is faculty', [('kilthub_author', 'Yang Zhang')])
# postdocs
for n in ['Zhi-Qi Cheng', 'Amy Pavel', 'Antonios Anastasopoulos', 'Pengfei Liu']:
    pdoc(n)
pdoc('Samuele Cornell', ('scsdir', 'Samuele Cornell'))
pdoc('Ashish Gurung', ('scsdir', 'Ashish Gurung'))
pdoc('Wenhe Liu', ('scsdir', 'Wenhe Liu'))
pdoc('Zhou, Samson', ('census', 'Samson Zhou'))
pdoc('Jonathan Mosheiff', ('census', 'Jonathan Mosheiff'))
for n in ['Xiaodan Liang', 'Xiaojun Chang', 'Guangyi Chen', 'Giulio Malavolta', 'Yair Zick', 'Joao Ribeiro', 'Michael Tait']:
    D[n] = (R, 'postdoc', 'short CMU affiliation (postdoctoral period) with no CMU faculty listing in any department', [('searched', 'CMU department faculty listings 2016-2026 captured for this review and the SCS listings')])
D['Spencer Krieger'] = (R, 'postdoc', 'Lane Fellow (CBD postdoctoral fellowship), not a professor rank', [('scsdir', 'Spencer Krieger')])
D['Min Kyung Lee'] = (R, 'postdoc', 'HCII postdoctoral fellow/research scientist, not a CMU professor (now faculty elsewhere)', [('collection', 'Min Kyung Lee')])
# research scientists / staff / not a professor rank
D['Corina S. Păsăreanu'] = (R, 'research_scientist', 'research scientist title (ECE "Senior Research Scientist", CMU Silicon Valley), not a professor rank', [('listing', ECE26, r'Corina Pasareanu Senior Research Scientist|Pasareanu , Corina Senior Research Scientist')])
D['Saugata Ghose'] = (R, 'research_scientist', 'ECE "Systems Scientist" (a research-scientist title), not a professor rank', [('listing', ECE16, r'Ghose , Saugata Systems Scientist')])
D['Ken Mai'] = (R, 'research_scientist', 'ECE "Principal Systems Scientist" throughout 2016-2026 (a research-scientist title, not a professor rank), although he chairs ECE PhD theses', [('listing', ECE26, r'Ken Mai Principal Systems Scientist')])
D['Bradley Schmerl'] = (R, 'research_scientist', 'S3D "Principal Systems Scientist" (research-scientist title; SCS department)', [('census', 'Bradley Schmerl')])
D['Christopher Bogart'] = (R, 'research_scientist', 'S3D "Senior Systems Scientist" (research-scientist title; SCS department)', [('census', 'Christopher Bogart')])
D['Elizabeth J. Carter'] = (R, 'research_scientist', 'RI "Senior Project Scientist" (staff research title)', [('scsdir', 'Elizabeth J Carter')])
D['Jaromir Savelka'] = (R, 'research_scientist', 'CSD "Researcher Associate" (staff research title)', [('scsdir', 'Jaromir Savelka')])
D['Danielle R. Thomas'] = (R, 'research_scientist', 'HCII "Systems Scientist" (research-scientist title)', [('scsdir', 'Danielle Thomas')])
D['Dong Huang'] = (R, 'research_scientist', 'RI/NREC "Senior Project Scientist" (staff research title)', [('scsdir', 'Dong Huang')])
D['Yaqi Xie'] = (R, 'research_scientist', 'RI "Project Scientist" (staff research title)', [('scsdir', 'Yaqi Xie')])
D['Guillaume Marçais'] = (R, 'research_scientist', 'CBD "Senior Systems Scientist" (research-scientist title)', [('census', 'Guillaume Marcais')])
D['Ashiqur R. KhudaBukhsh'] = (R, 'research_scientist', 'CMU PhD alumnus (2017) and LTI project scientist, not a CMU professor', [('collection', 'Ashiqur Rahman KhudaBukhsh')])
D['Stephen Nuske'] = (R, 'research_scientist', 'RI "Systems Scientist" (research-scientist title)', [('census', 'Stephen T. Nuske')])
D['Anthony Tomasic'] = (R, 'research_scientist', 'LTI staff (Associate Director of a program), not a professor rank', [('census', 'Anthony Tomasic')])
D['Maverick Woo'] = (R, 'research_scientist', 'CyLab systems scientist, not a professor rank; the KiltHub theses he advised are master\'s theses', [('searched', 'no professor title on any captured CMU department faculty listing; KiltHub lists him on master\'s theses only')])
D['Heather Burte'] = (R, 'staff', 'CSD staff (Program Manager)', [('scsdir', 'Heather Burte')])
D['Paola A. Buitrago'] = (R, 'staff', 'Pittsburgh Supercomputing Center staff, not CMU faculty', [('searched', 'no CMU department faculty listing names her')])
D['Christoph Mertz'] = (R, 'research_scientist', 'RI "Principal Project Scientist" (staff research title); SCS department', [('census', 'Christoph Mertz')])
D['Paul Scerri'] = (R, 'research_scientist', 'former RI systems scientist; no CMU professor appointment 2016-2026', [('searched', 'no captured CMU faculty listing 2016-2026 names him')])
D['Stephan Vogel'] = (R, 'research_scientist', 'LTI "Research Director" title (a research-staff title; main appointment at QCRI); SCS department', [('census', 'Stephan Vogel')])
D['Mohammad Aazam'] = (R, 'research_scientist', 'CMU-Qatar research staff, not a professor rank found on any listing', [('searched', 'no professor title on captured CMU listings; no stated PhD advising (' + NO_ADV + ')')])
D['Ehab Al-Shaer'] = (R, 'research_scientist', 'listed as "Distinguished Research Fellow" (census); no professor rank and no stated PhD advising found', [('census', 'Ehab Al-Shaer'), ('searched', NO_ADV)])
# SEI and other non-faculty units
for n in ['Grace A. Lewis', 'Forrest Shull', 'Jonathan M. Spring', 'Ipek Ozkaya']:
    D[n] = (R, 'sei_not_faculty', 'Software Engineering Institute technical staff (FFRDC), not a CMU faculty appointment', [('searched', 'no CMU department faculty listing names this person as faculty')])
D['Scott McMillan'] = (R, 'courtesy_only', 'SEI principal research scientist with an ECE courtesy title only (main appointment outside the academic departments)', [('listing', ECEC26, r'Scott McMillan Courtesy Professor')])
D['Mark Klein'] = (R, 'sei_not_faculty', 'SEI staff; no faculty title', [('census', 'Mark Klein')])
D['Nancy R. Mead'] = (R, 'courtesy_only', 'SEI Fellow with an adjunct professor title (main appointment SEI)', [('census', 'Nancy R Mead')])
D['Rick Kazman'] = (R, 'faculty_elsewhere', 'Professor at the University of Hawaii; CMU affiliation is through the SEI (visiting)', [('searched', 'no CMU department faculty listing names him')])
# faculty elsewhere / courtesy or adjunct only
D['A. Ercument Cicek'] = (R, 'faculty_elsewhere', 'faculty at Bilkent University; CMU CBD listing is adjunct/contingent research faculty', [('census', 'A. Ercument Cicek')])
D['Jeffrey F. Cohn'] = (R, 'faculty_elsewhere', 'Professor of Psychology at the University of Pittsburgh; CMU RI adjunct/courtesy only', [('census', 'Jeffrey Cohn')])
D['Alexander Nolte'] = (R, 'faculty_elsewhere', 'faculty at the University of Tartu; S3D adjunct faculty only', [('census', 'Alexander Nolte')])
D['Rebekka Wohlrab'] = (R, 'faculty_elsewhere', 'S3D postdoc/adjunct; faculty at Chalmers', [('census', 'Rebekka Wohlrab')])
D['Iain Cruickshank'] = (R, 'student', 'CMU PhD (2020) and S3D adjunct assistant professor (US Army officer), not a CMU faculty appointment', [('kilthub_author', 'Iain Cruickshank')])
D['Chieko Asakawa'] = (R, 'courtesy_only', 'IBM Fellow; RI lists her as "Courtesy Faculty" (main appointment IBM)', [('scsdir', 'Chieko Asakawa')])
D['Jionghao Lin'] = (R, 'faculty_elsewhere', 'reviewed earlier: HKU faculty, former HCII postdoc', [('override', 'Jionghao Lin')])
D['Steven P. Dow'] = (R, 'left_before_window', 'reviewed earlier: left CMU for UC San Diego in 2015', [('override', 'Steven Dow')])
D['Steven Dow'] = D['Steven P. Dow']
D['Nikol Rummel'] = (R, 'faculty_elsewhere', 'reviewed earlier: Ruhr-Universitat Bochum; HCII affiliated only', [('override', 'Nikol Elisabet Rummel')])
D['Aisling Kelliher'] = (R, 'left_before_window', 'reviewed earlier: left CMU in 2015', [('override', 'Aisling Kelliher')])
D['Farzaneh Derakhshan'] = (R, 'faculty_elsewhere', 'reviewed earlier: Illinois Tech faculty', [('override', 'Farzaneh Derakhshan')])
D['Alexei A. Efros'] = (R, 'faculty_elsewhere', 'UC Berkeley faculty (left CMU 2013); RI adjunct only', [('census', 'Alexei A. Efros')])
D['Metin Sitti'] = (R, 'faculty_elsewhere', 'director at the Max Planck Institute for Intelligent Systems since 2014; CMU listing is an adjunct/courtesy holdover', [('searched', 'MechE/RI listings')])
for n, why in [('Noah A. Smith', 'University of Washington faculty since 2015; the 2016-2025 CMU theses finished students he began advising at CMU'),
               ('André Martins', 'Instituto Superior Tecnico (Lisbon) faculty; CMU Portugal co-advising'),
               ('Avniel Singh Ghuman', 'University of Pittsburgh faculty (neurosurgery); co-advises CNBC students'),
               ('Francisco S. Melo', 'Instituto Superior Tecnico (Lisbon) faculty; CMU Portugal co-advising'),
               ('Fancisco S. Melo', 'Instituto Superior Tecnico (Lisbon) faculty; CMU Portugal co-advising (spelling variant)'),
               ('Paolo Romano', 'Instituto Superior Tecnico (Lisbon) faculty; CMU Portugal co-advising'),
               ('Abhik Roychoudhury', 'National University of Singapore faculty; external co-adviser'),
               ('Isabel Trancoso', 'Instituto Superior Tecnico (Lisbon) faculty; CMU Portugal co-advising'),
               ('Joao Paulo Neto', 'Instituto Superior Tecnico (Lisbon) faculty; CMU Portugal co-advising'),
               ('João Magalhães', 'NOVA University Lisbon faculty; CMU Portugal co-advising'),
               ('Luísa Coheur', 'Instituto Superior Tecnico (Lisbon) faculty; CMU Portugal co-advising'),
               ('Maria Luısa Torres Ribeiro Marques da Silva Coheur', 'Instituto Superior Tecnico (Lisbon) faculty (Luisa Coheur); CMU Portugal co-advising'),
               ('Mario Zenha-Rela', 'University of Coimbra faculty; CMU Portugal co-advising'),
               ('Nuno Neves', 'University of Lisbon faculty; CMU Portugal co-advising'),
               ('Vasco Manquinho', 'Instituto Superior Tecnico (Lisbon) faculty; CMU Portugal co-advising'),
               ('Sameena Shah', 'J.P. Morgan AI Research; external co-adviser'),
               ('Nizar Habash', 'NYU Abu Dhabi faculty; CMU-Qatar collaborator'),
               ('Maria Chikina', 'University of Pittsburgh faculty; CBD collaborator'),
               ('Yejin Choi', 'University of Washington / Stanford faculty; CMU-affiliated co-authorship only'),
               ('Luke Zettlemoyer', 'University of Washington faculty; CMU-affiliated co-authorship only'),
               ('Yoshimasa Masuda', 'faculty at Keio University; CMU affiliation is an adjunct/visiting role')]:
    D[n] = (R, 'faculty_elsewhere', why, [('searched', 'no CMU department faculty listing 2016-2026 names this person as CMU faculty')])
# no PhD advising and no own lab found
D['Houda Bouamor'] = (R, 'no_pi_basis', 'CMU-Qatar teaching faculty (information systems); no stated PhD advising and no lab she heads', [('searched', NO_ADV)])
D['Chadi Aoun'] = (R, 'no_pi_basis', 'CMU-Qatar information-systems teaching faculty; no stated PhD advising and no own lab', [('searched', NO_ADV)])
D['Savanid Vatanasakdakul'] = (R, 'no_pi_basis', 'CMU-Qatar associate teaching professor of information systems; no stated PhD advising and no own lab', [('searched', NO_ADV)])
D['Peter J. Jansen'] = (R, 'no_pi_basis', 'no CMU professor listing and no stated PhD advising found', [('searched', NO_ADV)])
D['Daniel Brasier'] = (R, 'no_pi_basis', 'advises a 2025 master\'s thesis only; no CMU professor listing found', [('searched', NO_ADV)])
D['Martin Saint'] = (R, 'no_pi_basis', 'CMU-Africa teaching staff; no stated PhD advising and no own lab; not on the current CMU-Africa faculty directory', [('searched', NO_ADV)])
D['Manoranjan Mohanty'] = (R, 'no_pi_basis', 'CMU-Africa; no stated PhD advising and no own lab; not on the current CMU-Africa faculty directory', [('searched', NO_ADV)])
D['Assane Gueye'] = (R, 'no_pi_basis', 'CMU-Africa teaching faculty; no stated PhD advising and no own lab; not on the current CMU-Africa faculty directory', [('searched', NO_ADV)])
D['David Vernon'] = (R, 'no_pi_basis', 'CMU-Africa ECE teaching faculty; no stated PhD advising and no own lab', [('listing', ECE16, r'Vernon , David Teaching Faculty – ECE'), ('searched', NO_ADV)])
D['Hakan Erdogmus'] = (R, 'no_pi_basis', 'ECE Teaching Professor (Silicon Valley); no stated PhD advising and no own lab', [('listing', ECE26, r'Hakan Erdogmus Teaching Professor'), ('searched', NO_ADV)])
D['Prasenjit Mitra'] = (R, 'no_pi_basis', 'CMU-Africa Research Professor since 2024/25 (PhD advising stated is at Penn State); no CMU PhD advising or CMU lab found', [('page', 'https://www.africa.engineering.cmu.edu/about/contact/directory/bios/mitra-prasenjit.html', r'Prasenjit Mitra Research Professor, CMU-Africa'), ('searched', NO_ADV)])
D['Tridas Mukhopadhyay'] = (R, 'no_pi_basis', 'Tepper professor (information systems); no PhD advising 2016-2026 or own lab found in the captures', [('searched', NO_ADV)])
D['Scheines, Richard'] = (R, 'no_pi_basis', 'Philosophy professor and Dietrich College dean; the only KiltHub dissertation naming him as adviser is from 1996; no 2016-2026 advising or own lab found', [('searched', NO_ADV)])
D['Christian Lebiere'] = (R, 'research_scientist', 'Psychology research faculty (not on the core and training faculty listing); no stated PhD advising', [('searched', 'not on the captured Psychology core/training faculty listing; ' + NO_ADV)])
D['Dina El-Zanfaly'] = (R, 'no_pi_basis', 'School of Design faculty; KiltHub names her only on master\'s theses, and no lab page could be captured (design.cmu.edu profiles are disallowed by robots.txt)', [('searched', NO_ADV)])
D['Matthew S. Smith'] = (R, 'not_cs_related', 'BME/Neuroscience Institute professor; 2 CS-venue works at CMU 2016-2026 (OpenAlex A5023814498), below 5', [('searched', 'hierarchy/cmu/openalex-sweep.sqlite against hierarchy/cs-venues.json')])
D['Inês Azevedo'] = (R, 'not_cs_related', 'EPP professor until 2019; 0 CS-venue works at CMU 2016-2026 (OpenAlex A5009342516)', [('searched', 'hierarchy/cmu/openalex-sweep.sqlite against hierarchy/cs-venues.json')])
D['Jeyanandh Paramesh'] = (R, 'not_cs_related', 'ECE RF/mm-wave integrated-circuit work; his 6 "CS-venue" works are ISSCC/CICC circuit papers (DBLP-indexed 2); not plainly CS-related', [('searched', 'hierarchy/cmu/openalex-sweep.sqlite against hierarchy/cs-venues.json and the DBLP dump index')])
D['Martin Larsson'] = (R, 'not_cs_related', 'Mathematical Sciences (mathematical finance, probability); his 8 "CS-venue" works are statistics/probability journals; not plainly CS-related', [('searched', 'hierarchy/cmu/openalex-sweep.sqlite against hierarchy/cs-venues.json')])
D['Tomasz Tkocz'] = (R, 'no_pi_basis', 'Mathematical Sciences; KiltHub names him only on master\'s theses (2025, 2026); no PhD advising or own lab found', [('searched', NO_ADV)])
D['John R. Miller'] = (R, 'not_cs_related', 'the OpenAlex author (A5015369282) is a namesake (ECE AR-systems student); SDS professor John H. Miller has no CS-venue works matched', [('searched', 'hierarchy/cmu/openalex-sweep.sqlite')])
D['Brian MacWhinney'] = (R, 'no_pi_basis', 'Psychology professor; no captured PhD-advising statement 2016-2026 or lab he heads alone (TalkBank is a project)', [('searched', NO_ADV + '; the Psychology graduate-student roster names no advisee')])
D['Roberta L. Klatzky'] = (R, 'no_pi_basis', 'Psychology professor; captured theses list her as a committee member only, no adviser statement 2016-2026 and no own lab page', [('searched', NO_ADV + '; the Psychology graduate-student roster names no advisee')])
# SCS-home people: outside this review's scope (the SCS census decides their PI status)
SCS = 'home department is an SCS (computing) department; outside this review of non-computing faculty. The SCS census row has is_pi false; PI status is the census\'s to decide'
for n, cn in [('Michael Hilton', 'Michael Edward Hilton'), ('Alexandra Ion', 'Alexandra Ion'), ('Majd Sakr', 'Majd Sakr'), ('Gianni A. Di Caro', 'Gianni Di Caro'),
              ('David Touretzky', 'David Touretzky'), ('Matthew R. Gormley', 'Matt Gormley'), ('Matthew Gormley', 'Matt Gormley'), ('Fernando Diaz', 'Fernando Diaz'),
              ('Jack Mostow', 'Jack Mostow'), ('Zakia Hammal', 'Zakia Hammal'), ('Sanjiv Singh', 'Sanjiv Singh'), ('Christos A. Kapoutsis', 'Christos Kapoutsis'),
              ('Ryan Riley', 'Ryan Riley'), ('Eduardo Feo-Flushing', 'Eduardo Feo Flushing'), ('Khaled A. Harras', 'Khaled Harras'), ('Khaled Harras', 'Khaled Harras'),
              ('Dan DeBlasio', 'Dan DeBlasio'), ('Danny Sleator', 'Danny Sleator'), ('David Sleator', 'Danny Sleator'), ('David Kosbie', 'David Kosbie'),
              ('Mark Stehlik', 'Mark Stehlik'), ('Stephanie Rosenthal', 'Stephanie Rosenthal')]:
    D[n] = (R, 'scs_department_out_of_scope', SCS, [('census', cn)])
D['Yong-Lae Park'] = (R, 'scs_department_out_of_scope', 'RI (SCS) assistant professor until 2016, then Seoul National University; outside this review (and absent from the SCS census)', [('searched', 'RI listings 2016 (listings/cmu/captures.sqlite)')])
D['Amy Pavel'] = (R, 'postdoc', 'LTI/HCII postdoctoral fellow, not CMU faculty', [('collection', 'Amy Pavel')])
# already PIs (thesis-adviser name variants)
D['Fernando De la Torre'] = (R, 'already_pi', 'already a PI (Fernando De La Torre Frade); alias added in the missing-PI review', [('pi', 'Fernando De La Torre Frade')])
D['Barnabá P&oacoute;czos'] = (R, 'already_pi', 'garbled spelling of Barnabás Póczos, already a PI', [('pi', 'Barnabas Poczos')])
D['Brad A, Myers'] = (R, 'already_pi', 'garbled spelling of Brad A. Myers, already a PI', [('pi', 'Brad Myers')])
D['Max Likhavchev'] = (R, 'already_pi', 'misspelling of Maxim Likhachev, already a PI', [('pi', 'Maxim Likhachev')])
