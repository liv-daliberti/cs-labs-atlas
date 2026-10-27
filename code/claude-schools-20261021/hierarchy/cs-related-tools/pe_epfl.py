"""EPFL CS-related scope review (owner decision 2026-10-22) over hierarchy/epfl/cs-related-candidates.json (DBLP-based list).

Decisions are the DEC table below (one entry per candidate name). Evidence is assembled from:
  faculty lists   school/institute faculty-list captures (listings/epfl/captures.sqlite, and Wayback/live lists in
                  hierarchy/cs-related-captures-epfl.sqlite), 'Name Rank' entries read by epfl_listtext.valid_quotes
                  (pe_index.py -> ep_listrows.json); emeritus entries are never appointment years
  PhD advising    Infoscience thesis records (hierarchy/epfl/thesis-captures.sqlite via thesis-tools/records.py): the
                  adviser field, first-listed adviser = thesis director
  profiles        live people.epfl.ch profiles (position, unit, breadcrumb), fetched into the review store
Every capture cited is copied unchanged (fetched_at, sha256, bytes) or fetched into hierarchy/epfl/cs-related-captures.sqlite
and every quote is checked as an exact substring of that store's text view before it is written.
-> <out>/epfl-additions-new.json, epfl-periods.json, epfl-home-departments.json, epfl-review.json  (merged by pe_merge.py)
usage: pe_epfl.py <work_dir>    (work_dir holds pe_index.py output)
"""
import collections, json, re, sqlite3, sys, unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pecap  # noqa: E402
import helpers  # noqa: E402

HERE = pecap.HERE
W = Path(sys.argv[1])
pecap.use('epfl')
STORE = 'hierarchy/epfl/cs-related-captures.sqlite'
LEFT = HERE / 'hierarchy/cs-related-captures-epfl.sqlite'
LST = HERE / 'listings/epfl/captures.sqlite'
THESIS = HERE / 'hierarchy/epfl/thesis-captures.sqlite'
ADDED = 'cs_related_scope_20261022'
problems = []

C = json.load(open(HERE / 'hierarchy/epfl/cs-related-candidates.json'))
LR = json.load(open(W / 'ep_listrows.json'))
TI = json.load(open(W / 'epfl-thesis-index.json'))


def norm(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


SCHOOLS = {
    'STI/IEM': 'School of Engineering (STI) — Institute of Electrical and Micro Engineering (IEM)',
    'STI/IEL': 'School of Engineering (STI) — Institute of Electrical Engineering (IEL; merged into IEM in 2023)',
    'STI/IMT': 'School of Engineering (STI) — Institute of Microengineering (IMT; merged into IEM in 2023)',
    'STI/IGM': 'School of Engineering (STI) — Institute of Mechanical Engineering (IGM)',
    'STI/IBI-STI': 'School of Engineering (STI) — Institute of Bioengineering (IBI-STI)',
    'STI/INX-STI': 'School of Engineering (STI) — Neuro-X Institute (INX)',
    'SB/MATH': 'School of Basic Sciences (SB) — Institute of Mathematics (MATH)',
    'ENAC/IIC': 'School of Architecture, Civil and Environmental Engineering (ENAC) — Civil Engineering Institute (IIC)',
    'ENAC/IA': 'School of Architecture, Civil and Environmental Engineering (ENAC) — Institute of Architecture (IA)',
    'CDM/MTEI': 'College of Management of Technology (CDM) — Management of Technology & Entrepreneurship Institute (MTEI)',
    'SV/BMI': 'School of Life Sciences (SV) — Brain Mind Institute (BMI)',
    'IC': 'School of Computer and Communication Sciences (IC)',
}

# ---------------------------------------------------------------------------------------------------------------------
# Accepted. home: department code; adv: adviser strings as written in Infoscience (family, given prefix); start/end:
# reviewed period bounds (None = covers the window); pi: 'phd' (thesis director record), 'lab' (profile/lab page), 'list'
# (EDEE thesis-director list); extra: listing quotes on rank-less lists [(store url, quote, year)].
A = {
 'David Atienza': dict(home='STI/IEM', adv=['Atienza Alonso, David']),
 'Jean-Philippe Thiran': dict(home='STI/IEM', adv=['Thiran, Jean-Philippe']),
 'Michael Unser': dict(home='STI/IEM', adv=['Unser, Micha'], aliases=['Michaël Unser']),
 'Aude Billard': dict(home='STI/IEM', adv=['Billard, Aude'], note='Profile breadcrumb STI › IEM › LASA; the STI IGM faculty list 2024-2026 lists her too.'),
 'Colin N. Jones': dict(home='STI/IGM', adv=['Jones, Colin'], aliases=['Colin Jones']),
 'Sandro Carrara': dict(home='STI/IEM', adv=['Carrara, Sandro'], note='IC listed him 2016-2018 among its senior scientists (LSI1); IEM since.'),
 'Dario Floreano': dict(home='STI/IGM', adv=['Floreano, Dario']),
 'Touradj Ebrahimi': dict(home='STI/IEM', adv=['Ebrahimi, Touradj']),
 'Denis Gillet': dict(home='STI/IEM', adv=['Gillet, Denis'], note='MER (Senior Scientist) heading the SCI STI DG group (REACT); thesis director.'),
 'Edoardo Charbon': dict(home='STI/IEM', adv=['Charbon, Edoardo']),
 'Dimitris Kiritsis': dict(home='STI/IGM', adv=['Kyritsis, Dimitrios', 'Kiritsis'], aliases=['Dimitrios Kyritsis'], end='last'),
 'Dimitri Van De Ville': dict(home='STI/INX-STI', adv=['Van De Ville, Dimitri'], note='Joint with the University of Geneva; SV listed him 2016-2017.'),
 'Giancarlo Ferrari-Trecate': dict(home='STI/IGM', adv=['Ferrari Trecate, Giancarlo', 'Ferrari-Trecate, Giancarlo'], aliases=['Giancarlo Ferrari Trecate'], start='first',
                                   note='First on an STI (IGM) faculty list in 2017 (not on the January 2016 capture).'),
 'Josie Hughes': dict(home='STI/IGM', adv=['Hughes, Josephine', 'Hughes, Josie'], start='first'),
 'Yusuf Leblebici': dict(home='STI/IEL', adv=['Leblebici, Yusuf'], end='last'),
 'Christian Enz': dict(home='STI/IMT', adv=['Enz, Christian'], end='last', note='Director of IMT (profile biography); IEM after the 2023 merger until retirement.'),
 'Jamie Paik': dict(home='STI/IGM', adv=['Paik, Jamie']),
 'Daniel Kuhn': dict(home='CDM/MTEI', adv=['Kuhn, Daniel']),
 'Catherine Dehollain': dict(home='STI/IEL', adv=['Dehollain, Catherine'], end='last', note='MER (Adjunct Professor) heading the RFIC group.'),
 'Alexandre Schmid': dict(home='STI/IEM', adv=['Schmid, Alexandre'], note='Head of the SCI STI AXS group; Senior Scientist (MER), Adjunct Professor by 2026.'),
 'Daniel Kressner': dict(home='SB/MATH', adv=['Kressner, Daniel']),
 'Nikolas Geroliminis': dict(home='ENAC/IIC', adv=['Geroliminis, Nikola'], aliases=['Nikolaos Geroliminis']),
 'Jean-Marc Odobez': dict(home='STI/IEM', adv=['Odobez, Jean-Marc'], note='EPFL Senior Scientist (MER) in the LIDIAP unit (Idiap); thesis director of EPFL PhDs.'),
 'Jan S. Hesthaven': dict(home='SB/MATH', adv=['Hesthaven, Jan'], end='last', aliases=['Jan Hesthaven']),
 'Ronan Boulic': dict(home='IC', adv=['Boulic, Ronan'], end='last',
                      extra=[('ic.epfl.ch', 'Ronan Boulic IIG [email removed]', 'IC')],
                      note='IC MER (Senior Scientist) heading the IIG group (VRLAB); IC is a computing school but he was missing from pis.json.'),
 'Drazen Dujic': dict(home='STI/IEM', adv=['Dujic, Drazen']),
 'János Pach': dict(home='SB/MATH', adv=['Pach, J'], end='last', aliases=['Janos Pach']),
 'Mohamed Bouri': dict(home='STI/INX-STI', adv=['Bouri, Mohamed'], start='first', rank=('mer_senior_scientist', 'Senior Scientist'), note='Senior Scientist (MER) heading the SCI STI MB group (REHAssist); first on a dated STI faculty list in 2024, though he directed EPFL PhDs earlier (co-director from 2016).'),
 'Alireza Karimi': dict(home='STI/IGM', adv=['Karimi, Alireza']),
 'Kamiar Aminian': dict(home='STI/IBI-STI', adv=['Aminian, Kamiar'], end='last'),
 'Henry Markram': dict(home='SV/BMI', adv=['Markram, Henry']),
 'Dominique Bonvin': dict(home='STI/IGM', adv=['Bonvin, Dominique'], end='last'),
 'Jean-Marc Vesin': dict(home='STI/IEL', adv=['Vesin, Jean-Marc'], end='last'),
 'Fabio Nobile': dict(home='SB/MATH', adv=['Nobile, Fabio']),
 'Hervé Bourlard': dict(home='STI/IEL', adv=['Bourlard, Herv'], end='last', aliases=['Herve Bourlard']),
 'José del R. Millán': dict(home='STI/IEL', adv=['Millán Ruiz, José', 'Millán-Ruiz, José'], end='last', aliases=['José del R. Millán', 'Jose del R. Millan', 'José del Rocío Millán']),
 'Adrian M. Ionescu': dict(home='STI/IEM', adv=['Ionescu, Mihai Adrian'], aliases=['Mihai Adrian Ionescu', 'Adrian Ionescu']),
 'Maher Kayal': dict(home='STI/IEL', adv=['Kayal, Maher'], end='last'),
 'Felix Schürmann': dict(home='SV/BMI', adv=['Schürmann, Felix'], end='last', aliases=['Felix Schuermann']),
 'Ian F. C. Smith': dict(home='ENAC/IIC', adv=['Smith, Ian'], end='last', aliases=['Ian Smith']),
 'Thomas A. Weber': dict(home='CDM/MTEI', adv=['Weber, Thomas Alois'], aliases=['Thomas Weber']),
 'Rachid Cherkaoui': dict(home='STI/IEL', adv=['Cherkaoui, Sidi-Rachid', 'Cherkaoui, Rachid'], end='last', aliases=['Sidi-Rachid Cherkaoui']),
 'Assyr Abdulle': dict(home='SB/MATH', adv=['Abdulle, Assyr'], end='last'),
 'Mahmut Selman Sakar': dict(home='STI/IGM', adv=['Sakar, Mahmut Selman'], start='first', aliases=['Selman Sakar']),
 'Hannes Bleuler': dict(home='STI/IMT', adv=['Bleuler, Hannes'], end='last'),
 'Ralf W. Seifert': dict(home='CDM/MTEI', adv=['Seifert, Ralf'], aliases=['Ralf Seifert']),
 'Simone Deparis': dict(home='SB/MATH', adv=['Deparis, Simone']),
 'Andrea Cavallaro': dict(home='STI/IEM', adv=[], pi='list', start='first', note='Full Professor from 2023 (also Director of Idiap); no EPFL thesis he directed is recorded yet, but the EDEE thesis-director list names him.'),
 'Annalisa Buffa': dict(home='SB/MATH', adv=['Buffa, Annalisa']),
 'Marco Picasso': dict(home='SB/MATH', adv=['Picasso, Marco'], note='Adjunct Professor (MER) heading the Picasso Group (GR-PI).'),
 'Andrew Sonta': dict(home='ENAC/IIC', adv=[], pi='lab', start='first'),
 'Bernard M. E. Moret': dict(home='IC', adv=['Moret, Bernard'], end=2016, aliases=['Bernard Moret'],
                             extra=[('ic.epfl.ch', 'Bernard Moret LCBB [email removed]', 'IC')], rank=('full_professor', 'Professor'),
                             note='Listed among IC professors in 2016 and among its emeriti from 2017; directed a PhD completed in 2017 (LCBB).'),
 'Dimitar Jetchev': dict(home='SB/MATH', adv=['Jetchev, Dimitar'], end='last', extra=[('research/faculty-members', 'Dimitar Jetchev SNSF-funded Professor', 'EPFL')], rank=('assistant_professor_snsf', 'SNSF-funded Professor'), note='SNSF-funded professor heading GR-JET; now a Host Professor (visitor).'),
 'Andrei Popescu-Belis': dict(home='STI/IEM', adv=['Popescu-Belis, Andrei'], start='first', rank=('mer_senior_scientist', 'Senior Scientist'), note='Professor at HEIG-VD; at EPFL a Senior Scientist on the STI (IEM) faculty list from 2022 and on the EDEE thesis-director list; sole/first director of one PhD (2025), co-director earlier.'),
 'Pierre-André Farine': dict(home='STI/IMT', adv=['Farine, Pierre-Andr'], end='last', aliases=['Pierre-Andre Farine']),
 'Sean L. Hill': dict(home='SV/BMI', adv=['Hill, Sean Lewis'], aliases=['Sean Hill']),
 'Stefana Parascho': dict(home='ENAC/IA', adv=[], pi='lab', start='first'),
 'Christopher L. Tucci': dict(home='CDM/MTEI', adv=['Tucci, Christopher'], end='last', aliases=['Christopher Tucci']),
}
RANKS = [('Professor Emeritus', 'emeritus'), ('Tenure', 'assistant_professor_tenure_track'), ('Associate Professor', 'associate_professor'),
         ('Full Professor', 'full_professor'), ('Professeur ordinaire', 'full_professor'), ('Professeure ordinaire', 'full_professor'),
         ('Adjunct Professor', 'adjunct'), ('Professeur titulaire', 'adjunct'), ('SNSF', 'assistant_professor_snsf'),
         ('Senior Scientist', 'mer_senior_scientist'), ('Lecturer', 'lecturer')]

# Not accepted: decision, summary. 'student' summaries get the thesis author record as evidence; others get the
# profile position (if a live profile exists) and, where they co-directed theses, one co-direction record.
R = {
 'Mathias Soeken': ('not_faculty', 'Research scientist in the LSI lab (now Microsoft); co-directed four LSI PhDs 2019-2022; never on a faculty list. Profile: Lecturer (EDIC teaching).'),
 'Behzad Bozorgtabar': ('not_faculty', 'Research scientist/postdoc (LTS5, then other labs); no faculty list, profile or thesis direction.'),
 'Giovanni Ansaloni': ('not_faculty', 'Research and Teaching Associate in ESL (Atienza); no faculty list or thesis direction.'),
 'Marina Zapater': ('not_faculty', 'Host Professor (visitor) in ESL; her professorship is at HEIG-VD; co-director of two ESL PhDs 2024-2026; on no EPFL faculty list.'),
 'Mirjana Stojilović': ('not_faculty', 'Scientist and Lecturer in Babak Falsafi\'s PARSA lab (decided the same way in the 2026-10-22 missing-PI review); co-directed three PhDs with Falsafi.'),
 'Barbara Bruno': ('not_faculty', 'Postdoc/scientist in CHILI and MOBOTS (co-director of four PhDs 2022-2023); on no EPFL faculty list; now at KIT.'),
 'Yuning Jiang': ('not_faculty', 'Postdoc in LA3 (Jones); profile now Invited guest; no faculty list.'),
 'Wafa Johal': ('not_faculty', 'Postdoc in CHILI 2016-2021; no faculty list or thesis direction.'),
 'Alexandre Levisse': ('not_faculty', 'Scientist in ESL, now Operational Director of the CHIPS centre; no faculty list.'),
 'Stefan Vlaski': ('not_faculty', 'Postdoc in ASL (Sayed) 2019-2023; no faculty list or thesis direction.'),
 'Daniel Thalmann': ('faculty_no_pi_evidence', 'IC Professor Emeritus throughout 2016-2026 (Honorary Professors IC); no EPFL PhD he directed or co-directed in 2016-2026 and no lab of his own in the window (VRLAB closed).'),
 'Dorina Thanou': ('not_faculty', 'Research and Teaching Associate (LTS4); no faculty list or thesis direction.'),
 'Subhadeep Banik': ('not_faculty', 'Postdoc in LASEC 2017-2022; no faculty list or thesis direction.'),
 'Jinzhi Lu': ('not_faculty', 'Postdoc in ICT4SM (Kiritsis) 2020-2024; no faculty list or thesis direction.'),
 'Alexios Balatsoukas-Stimming': ('not_faculty', 'EPFL PhD 2016 (TCL), then postdoc; now at TU Eindhoven, a guest of TCL; co-directed three TCL PhDs; never on an EPFL faculty list.'),
 'Nathanaël Perraudin': ('not_faculty', 'EPFL PhD 2017 (LTS2), then data scientist at the Swiss Data Science Center; no faculty list.'),
 'Loukas, Andreas': ('not_faculty', 'Postdoc/research scientist in LTS2 2017-2021; co-director of one PhD; no faculty list.'),
 'Fernando Perez-Cruz': ('not_faculty', 'Chief Data Scientist of the Swiss Data Science Center (ETH/EPFL); on no EPFL faculty list and no EPFL thesis direction.'),
 'Juan Ramón Troncoso-Pastoriza': ('not_faculty', 'Senior researcher in LDS (Hubaux) 2018-2023; no faculty list or thesis direction.'),
 'Manoel Horta Ribeiro': ('not_faculty', 'EPFL PhD student in DLAB (thesis 2024).', 'student'),
 'Stich, Sebastian U.': ('not_faculty', 'Postdoc/research scientist in MLO 2017-2021 (co-director of one PhD); now faculty at CISPA; no EPFL faculty list.'),
 'Virginia Bordignon': ('not_faculty', 'EPFL PhD student in ASL (thesis 2022), then postdoc.', 'student'),
 'María Jesús Rodríguez-Triana': ('not_faculty', 'Postdoc in REACT (Gillet) 2016-2019; no faculty list or thesis direction.'),
 'Bruno Herbelin': ('not_faculty', 'Scientist in LNCO (Bertarelli Chair in Cognitive Neuroprosthetics); co-directed EPFL PhDs but holds no faculty rank and is on no faculty list.'),
 'Sylvain Calinon': ('not_faculty', 'EPFL Lecturer (LIDIAP unit) whose appointment is at Idiap; on no EPFL faculty list; every one of his ten EPFL PhDs 2018-2026 names another first-listed thesis director, so he is a co-director only.'),
 'Jiancheng Yang': ('not_faculty', 'Postdoc in CVLAB 2022-2026 (EPFL PhD 2025 in LPMAT under another adviser by name match; identity not relied on).'),
 'Miguel Peón-Quirós': ('not_faculty', 'Computer Scientist at the EcoCloud centre; no faculty list.'),
 'Gabriel Girard': ('not_faculty', 'Scientist in LTS5 / CIBM; no faculty list or thesis direction.'),
 'Martijn de Vos': ('not_faculty', 'Scientist in SaCS; no faculty list or thesis direction.'),
 'Thomas A.W. Bolton': ('not_faculty', 'EPFL PhD student in MIPLAB (thesis 2020).', 'student'),
 'Julien Fageot': ('not_faculty', 'EPFL PhD student in LIB (thesis 2017), later Scientist; co-director of one PhD; no faculty list.', 'student'),
 'Maud Ehrmann': ('not_faculty', 'Scientist in the Digital Humanities Laboratory; no faculty list or thesis direction.'),
 'Erick J. Canales-Rodríguez': ('not_faculty', 'Associated scientist in LTS5; no faculty list.'),
 'Ricardo Chavarriaga': ('not_faculty', 'Senior scientist in CNBI (Millán) to 2019; no faculty list or thesis direction.'),
 'Andrey Kupavskii': ('not_faculty', 'Postdoc in DCG (Pach) 2016-2019.'),
 'Werner Van Geit': ('not_faculty', 'Blue Brain Project staff scientist; no faculty list or thesis direction.'),
 'Jonathan Rafael-Patiño': ('not_faculty', 'EPFL PhD student in LTS5 (thesis 2021), then postdoc.', 'student'),
 'Maria Giulia Preti': ('not_faculty', 'Scientist in MIPLAB; no faculty list or thesis direction.'),
 'Matthieu Simeoni': ('not_faculty', 'EPFL PhD student in LCAV (thesis 2020), then data scientist.', 'student'),
 'Xiaochen Zheng': ('not_faculty', 'Postdoc in ICT4SM (Kiritsis) 2019-2024.'),
 'Mirko Marras': ('not_faculty', 'Postdoc at EPFL (ML4ED) 2020-2022; now faculty at Cagliari.'),
 'Meritxell Bach Cuadra': ('not_faculty', 'Head of the CIBM signal-processing section at UNIL/CHUV; co-directed two EPFL LTS5 PhDs (2022) but is on no EPFL faculty list and has no EPFL profile.'),
 'Daniel Keller': ('not_faculty', 'Blue Brain Project section manager; co-directed two BBP PhDs; no faculty list or profile.'),
 'Dominique de Werra': ('faculty_no_pi_evidence', 'SB Professor Emeritus (ROSO) throughout 2016-2026; no EPFL PhD he directed in 2016-2026 and no lab of his own in the window.'),
 'Artur Riazanov': ('not_faculty', 'EPFL PhD student in THL5 (thesis 2026).', 'student'),
 'Vincent Gramoli': ('not_faculty', 'Professor at the University of Sydney; an IC Host Professor (visitor) only.'),
 'Solaiman Shokur': ('not_faculty', 'Scientist in the Bertarelli Chair in Translational Neuroengineering (TNE); co-director of three PhDs 2024-2026; no faculty list.'),
 'Laila El-Hamamsy': ('not_faculty', 'EPFL PhD student (thesis 2023), then postdoc.', 'student'),
 'Johanni Brea': ('not_faculty', 'Scientist in the Computational Neuroscience Laboratory (Gerstner); co-director of one PhD (2026); no faculty list.'),
 'Marc-Oliver Gewaltig': ('not_faculty', 'Blue Brain Project section leader; co-directed BBP PhDs 2017-2023; no faculty list or profile.'),
 'Rouault, Sébastien': ('not_faculty', 'EPFL PhD student in LPD (thesis 2022).', 'student'),
 'Hung-Chi Han': ('not_faculty', 'EPFL PhD student in AQUA (thesis 2024).', 'student'),
 'Assim Boukhayma': ('not_faculty', 'EPFL PhD student in ICLAB (thesis 2016), then scientist; co-director of two ICLAB PhDs; no faculty list.', 'student'),
 'Gianluigi Viscusi': ('not_faculty', 'Senior scientist in the CSI chair (Tucci) 2016-2020; no faculty list or thesis direction.'),
 'Benjamin Wesolowski': ('not_faculty', 'EPFL PhD student in LACAL (thesis 2018).', 'student'),
 'Maria-Alexandra Paun': ('not_faculty', 'Scientist (STI); no faculty list or thesis direction.'),
 'Marwan Abdellah': ('not_faculty', 'EPFL PhD student in the Blue Brain Project (thesis 2017), then BBP scientist.', 'student'),
 'Fiorenzo Artoni': ('not_faculty', 'Postdoc (TNE / CNBI) 2016-2023; no faculty list.'),
 'Fabrizio Sossan': ('not_faculty', 'Scientist in DESL 2016-2019, now professor at HES-SO; EPFL Host Professor (visitor); co-director of two DESL PhDs.'),
 'Adrien Depeursinge': ('not_faculty', 'Professor at HES-SO Valais; on no EPFL faculty list; no EPFL thesis direction.'),
 'Tarnawski, Jakub': ('not_faculty', 'EPFL PhD student in THL2 (thesis 2019).', 'student'),
 'István Tomon': ('not_faculty', 'Postdoc in DCG 2016-2020.'),
 'Delphine Ribes Lemay': ('not_faculty', 'Engineer / head of group at the EPFL+ECAL Lab (a centre); no faculty list.'),
 'Enrico Amico': ('not_faculty', 'Postdoc in MIPLAB 2019-2023.'),
 'Jessica Dehler Zufferey': ('not_faculty', 'Executive director of the Center for Digital Education (CEDE); no faculty list or thesis direction.'),
 'Manuel Vidigueira': ('not_faculty', 'EPFL PhD student in DCL (thesis 2025).', 'student'),
 'Andrea Cavalli': ('faculty_no_pi_evidence', 'Adjunct Professor (professeur titulaire) from 2024 as Director of CECAM, a centre; no EPFL PhD he directed and no lab of his own.'),
 'Philipp Bucher': ('unresolved', 'Heads "Bucher\'s Lab" in the SV (ISREC) research-group lists 2016-2019 and directed one PhD (2020), but no dated list gives him a faculty rank (MER or professor) and he has no live profile.'),
 'Pablo Antolin': ('not_faculty', 'Scientist in MNS (Buffa); co-director of one PhD; no faculty list.'),
 'Amir Zandieh': ('not_faculty', 'EPFL PhD student in THL4 (thesis 2020).', 'student'),
 'Diego Barrettino': ('not_faculty', 'Scientist in the IEL scientists group; co-director of one PhD; no faculty list.'),
 'Dmitry Sokolov': ('not_faculty', 'Postdoc in THL (2023-2026).'),
 'Elda Fischi-Gomez': ('not_faculty', 'Scientist in LTS5 / CIBM; no faculty list.'),
 'Igor Zablotchi': ('not_faculty', 'EPFL PhD student in DCL (2016-2020), then postdoc elsewhere.', 'student'),
 'Dragos-Adrian Seredinschi': ('not_faculty', 'EPFL PhD student in DCL (thesis 2019).', 'student'),
 'E. Lanti': ('not_faculty', 'EPFL PhD student in SPC (thesis 2019), then scientist.', 'student'),
 'Aris Filos-Ratsikas': ('not_faculty', 'Postdoc in LIA 2016-2019.'),
 'Pramod Kumbhar': ('not_faculty', 'Blue Brain Project HPC engineer; no faculty list.'),
 'James King': ('not_faculty', 'Blue Brain Project staff; no faculty list.'),
 'Khan, Mohammad Emtiyaz': ('not_faculty', 'Postdoc/scientist at EPFL 2014-2016; now RIKEN.'),
 'Ibrahim Issa': ('not_faculty', 'Postdoc in LINX (Gastpar) 2018-2019; now at AUB.'),
 'Jiyong Zhang': ('not_faculty', 'Visiting researcher 2018-2021; no faculty list or profile.'),
 'Frank de Zeeuw': ('not_faculty', 'Postdoc in DCG (Pach) 2016-2018.'),
 'Jiahua Xu': ('not_faculty', 'Postdoc/visiting researcher; her faculty appointment is at UCL; no EPFL faculty list.'),
 'Jakab Tardos': ('not_faculty', 'EPFL PhD student in THL4 (thesis 2022).', 'student'),
 'Hamid Behjat': ('not_faculty', 'Postdoc in MIPLAB; profile now Invited guest.'),
 'Badr AlKhamissi': ('not_faculty', 'EPFL PhD student (NeuroAI) 2023-2026.'),
 'Ivo Widmer': ('not_faculty', 'Postdoc/scientist (2016-2018); no faculty list or profile.'),
 'Rafael Vázquez': ('not_faculty', 'Scientist in MNS (Buffa) 2017-2023; co-director of one PhD; no faculty list.'),
 'Emanuele Massaro': ('not_faculty', 'Postdoc/scientist (HERUS) 2017-2022.'),
 'Venzin, Moritz': ('not_faculty', 'EPFL PhD student in DISOPT (thesis 2023).', 'student'),
 'Christoph Strössner': ('not_faculty', 'EPFL PhD student in ANCHP (thesis 2023).', 'student'),
 'Ileana O. Jelescu': ('not_faculty', 'Group leader at CIBM (EPFL) 2017-2021, now at UNIL/CHUV; co-director of one PhD; on no EPFL faculty list.'),
 'Giacomo Rosilho de Souza': ('not_faculty', 'EPFL PhD student in ANMC (thesis 2020).', 'student'),
 'Andrea Zanoni': ('not_faculty', 'EPFL PhD student in CSQI (thesis 2022).', 'student'),
 'Tommaso Vanzan': ('not_faculty', 'Postdoc in CSQI / ANMC 2019-2024.'),
 'Maximilien Dreveton': ('not_faculty', 'Postdoc in INDY; profile now Invited guest.'),
}


# ---------------------------------------------------------------------------------------------------------------------
def store_row(url):
    con = sqlite3.connect(f"file:{HERE / STORE}?mode=ro", uri=True)
    r = con.execute('select id, sha256, text, fetched_at from captures where (url=? or capture_url=?) and status=200 and error is null order by id desc limit 1',
                    (url, url)).fetchone()
    con.close()
    return r


def bring(url, kind):
    """Copy a capture into the review store unchanged (listing sweep store first, then the earlier review store)."""
    if pecap.cached(url):
        return pecap.cached(url)
    if kind == 'listing':
        s = sqlite3.connect(f'file:{LST}?mode=ro', uri=True)
        hit = s.execute('select 1 from captures where capture_url=? and http_status=200 and raw_zlib is not null', (url,)).fetchone()
        s.close()
        if hit:
            return pecap.copy_from(str(LST), url, 'listing')
        return pecap.copy_from(str(LEFT), url, 'mp')
    if kind == 'thesis':
        return pecap.copy_from(str(THESIS), url, 'thesis')
    return pecap.copy_from(str(LEFT), url, 'mp')


def ev(url, quote, what, **kw):
    r = store_row(url)
    if not r or quote not in (r[2] or ''):
        problems.append(f'{what}: quote not in stored capture {url}: {quote[:90]}')
        return None
    return dict(url=url, sha256=r[1], quote=quote, **kw)


def observed_of(url, fallback):
    m = re.search(r'/web/(\d{4})(\d{2})(\d{2})', url)
    return f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else fallback


# profiles in the store (people.epfl.ch/<slug>?lang=en), keyed by folded family name
PROF = {}
con = sqlite3.connect(f"file:{HERE / STORE}?mode=ro", uri=True)
for url, text in con.execute("select url, text from captures where url like 'https://people.epfl.ch/%?lang=en' and status=200 and error is null"):
    m = re.match(r'EPFL - (.+?) Online People Directory', text or '')
    if m:
        PROF[url] = (m.group(1), text)
con.close()


def profile_of(cname, aliases):
    toks = {norm(t) for n in [cname] + list(aliases) for t in re.findall(r"[\w'-]+", n.replace(',', ' ')) if len(t) > 2}
    fam = norm(re.sub(r',.*', '', cname)) if ',' in cname else norm(cname.split()[-1])
    best = None
    for url, (pn, text) in PROF.items():
        pt = {norm(t) for t in re.findall(r"[\w'-]+", pn) if len(t) > 2}
        if fam.replace('-', ' ').split()[-1] in ' '.join(pt).replace('-', ' ').split() and len(pt & toks) >= 2:
            best = (url, pn, text)
    return best


POS_RX = re.compile(r'((?:Tenure Track Assistant |Full |Associate |Adjunct |Assistant |Senior |Research and Teaching |Associated |Computer |Operational |Host |Invited |Group |Engineer/)?'
                    r'(?:Professor|Professor Emeritus|Scientist|scientist|Lecturer|Head of Group|Head|Leader|guest|Guest|Associate|Director|Engineer|Staff) , )')


def position_quote(text):
    """The first position line of a people.epfl.ch profile: 'Rank , Unit name EPFL SCHOOL INST UNIT' (exact substring)."""
    t = text or ''
    i = t.find('vCard ')
    if i < 0:
        return None
    m = POS_RX.search(t, i, i + 400)
    if not m:
        return None
    seg = t[m.start():m.start() + 260]
    m2 = re.match(r'(.*? , .*?EPFL(?: [A-Z][A-Za-z0-9\-]+){1,4})(?=\s)', seg)
    if m2:
        return m2.group(1)
    m3 = re.match(r'(.*? , .*?)(?= \+41| Office :| EPFL ›| Contact EPFL| Website:| Expertise|$)', seg)
    return m3.group(1)[:160] if m3 else None


LABWORD = re.compile(r'(?i)\b(lab|laboratory|laboratoire|group|groupe|chair|chaire|institute|centre|center|unit)\b')


def adviser_rows(adv):
    out = []
    for a in TI['advisers']:
        if a['role'] == 'phd' and 2016 <= (a['year'] or 0) <= 2026 and any(a['adviser'].startswith(p) for p in adv):
            out.append(a)
    return out


def rank_code(r):
    for k, c in RANKS:
        if r and k.lower() in r.lower():
            return c
    return None


cand_by_name = collections.defaultdict(list)
for c in C:
    cand_by_name[c['name']].append(c)

additions, periods, homes, review = [], {}, [], []
for c in C:
    name = c['name']; aid = c['author'].rsplit('/', 1)[-1]
    rows = LR.get(c['author'], {}).get('rows', [])
    if name in A:
        s = A[name]
        if len(cand_by_name[name]) > 1 and c is not cand_by_name[name][0]:
            continue
        aliases = list(dict.fromkeys([n for n in c['names'] if n != name and ',' not in n] + s.get('aliases', [])))
        prof = profile_of(name, aliases + s.get('aliases', []))
        if prof and prof[1] != name and prof[1] not in aliases:
            aliases.append(prof[1])
        # dated faculty-list entries (active ranks only), one per year
        act = [r for r in rows if r['school'] != 'EDEE' and not (r['rank'] and 'Emerit' in r['rank'])
               and (r['rank'] or LABWORD.search(r['quote']))]  # rank-less STI entries must name the person's unit
        emer = [r for r in rows if r['rank'] and 'Emerit' in r['rank']]
        for host, q, xs in s.get('extra', []):
            con = sqlite3.connect(f'file:{LEFT}?mode=ro', uri=True)
            for cid, url, text, fa in con.execute('select id, url, text, fetched_at from captures where url like ? and status=200 and error is null', (f'%{host}%',)):
                if q in (text or ''):
                    i = text.find(q); pre = text[max(0, i - 2500):i]
                    if xs == 'IC' and ('Emerit' in pre[-600:] or re.search(r'Mange RDSG', text[max(0, i - 80):i])):
                        continue  # the emeritus block of the IC page
                    y = int(re.search(r'/web/(\d{4})', url).group(1))
                    act.append(dict(id=cid, url=url, school=xs, year=y, observed=observed_of(url, fa[:10]), quote=q, rank=None))
            con.close()
        fac_years = {r['year'] for r in act}
        act += [dict(r, edee=True) for r in rows if r['school'] == 'EDEE' and r['rank'] and r['year'] not in fac_years]
        by_year = {}
        pref = lambda r: (r['rank'] is not None, r['school'] != 'EPFL', r['observed'])
        for r in act:
            if 2016 <= r['year'] <= 2026 and (r['year'] not in by_year or pref(r) > pref(by_year[r['year']])):
                by_year[r['year']] = r
        sources = []
        for y in sorted(by_year):
            r = by_year[y]
            bring(r['url'], 'listing')
            e = ev(r['url'], r['quote'], f'{name} listing {y}', observed=r['observed'],
                   kind=('phd_program_thesis_directors:EDEE' if r.get('edee') else 'faculty_listing:EPFL' if r['school'] == 'EPFL' else f"dept_listing:{r['school']}"))
            if e:
                if r['rank']:
                    e['rank'] = r['rank']
                e['store'] = STORE
                sources.append(e)
        years = sorted({int(e['observed'][:4]) for e in sources})
        ranked = [r for r in sorted(act, key=lambda r: r['observed']) if r['rank']]
        title = ranked[-1]['rank'] if ranked else None
        if s.get('rank'):
            title = s['rank'][1]
        # PI basis
        arows = adviser_rows(s['adv']) if s['adv'] else []
        direct = sorted([a for a in arows if a['pos'] == 0 and a['quote']], key=lambda a: a['year'])
        pi_basis = None
        if s.get('pi', 'phd') == 'phd':
            pick = direct[-1] if direct else None
            if pick:
                bring(pick['url'], 'thesis')
                e = ev(pick['url'], pick['quote'], f'{name} thesis')
                if e:
                    pi_basis = dict(kind='advises_phd', url=e['url'], sha256=e['sha256'], quote=e['quote'], observed='2026-10-22', store=STORE,
                                    note=(f"First-listed thesis director (Infoscience dc.contributor.advisor) of {len(direct)} EPFL doctoral thesis record(s) "
                                          f"{direct[0]['year']}-{direct[-1]['year']} ({len(arows)} as director or co-director); quoted: {pick['student']} "
                                          f"({pick['year']}, {pick['dept']})."),
                                    record=dict(id=pick['id'], student=pick['student'], year=pick['year'], dept=pick['dept'], title=pick['title']))
        elif s['pi'] == 'list':
            lr = sorted([r for r in rows if r['school'] == 'EDEE'], key=lambda r: r['observed'])
            if lr:
                r = lr[-1]; bring(r['url'], 'listing')
                e = ev(r['url'], r['quote'], f'{name} EDEE list')
                if e:
                    pi_basis = dict(kind='advises_phd', url=e['url'], sha256=e['sha256'], quote=e['quote'], observed=r['observed'], store=STORE,
                                    note=f"Listed as a thesis director of the EPFL doctoral program in Electrical Engineering (EDEE) {lr[0]['year']}-{lr[-1]['year']}.")
        elif s['pi'] == 'lab' and prof:
            if name == 'Andrew Sonta':
                u = 'https://www.epfl.ch/labs/ethos/team/'; bring(u, 'mp')
                e = ev(u, 'Andrew Sonta , Director Andrew directs the ETHOS Lab and is a tenure-track assistant professor of civil engineering.', f'{name} lab')
            else:
                e = ev(prof[0], position_quote(prof[2]) or '', f'{name} lab')
            if e:
                pi_basis = dict(kind='lab_head', url=e['url'], sha256=e['sha256'], quote=e['quote'], observed='2026-10-22', store=STORE)
        if not pi_basis:
            problems.append(f'{name}: no PI basis')
        # home department evidence: live profile position (with unit codes), else the latest listing row
        hq = None
        if prof:
            pq = position_quote(prof[2])
            if pq and not re.search(r'guest|Emeritus|Host|Teaching', pq):
                hq = ev(prof[0], pq, f'{name} profile')
        if not hq and sources:
            inst = [x for x in sources if re.search(r'sti\.epfl\.ch/(iem|igm)/|page-1570|page-1613|page-1698|schools/(sb|cdm|enac|sv|ic)/', x['url'])]
            x = (inst or sources)[-1]
            hq = dict(url=x['url'], sha256=x['sha256'], quote=x['quote'])
        # period
        per = None
        st, en = s.get('start'), s.get('end')
        if st or en:
            evid = []
            if st == 'first' and sources:
                f = sources[0]; st = f['observed'][:4]
                evid.append(dict(url=f['url'], sha256=f['sha256'], quote=f['quote'], observed=f['observed'], kind='first_dated_faculty_listing'))
            if en == 'last' and sources:
                l = sources[-1]; en = l['observed'][:4]
                evid.append(dict(url=l['url'], sha256=l['sha256'], quote=l['quote'], observed=l['observed'], kind='last_dated_faculty_listing'))
                if emer:
                    e0 = sorted(emer, key=lambda r: r['observed'])[0]; bring(e0['url'], 'listing')
                    e = ev(e0['url'], e0['quote'], f'{name} emeritus')
                    if e:
                        evid.append(dict(e, observed=e0['observed'], kind='emeritus_listing'))
            elif isinstance(en, int):
                l = [x for x in sources if int(x['observed'][:4]) == en][-1]
                evid.append(dict(url=l['url'], sha256=l['sha256'], quote=l['quote'], observed=l['observed'], kind='last_dated_faculty_listing'))
                en = str(en)
            if prof and s.get('end'):
                pq = position_quote(prof[2])
                if pq and re.search(r'Emeritus|guest|Host', pq):
                    e = ev(prof[0], pq, f'{name} profile now')
                    if e:
                        evid.append(dict(e, observed='2026-10-22', kind='current_profile'))
            slug = re.sub(r'[^a-z0-9]+', '_', norm(name)).strip('_')
            per = dict(id=f'override_period_epfl_{slug}', start=str(st) if st else None, end=str(en) if en else None, asof=None, datePrecision='year',
                       evidence=evid, note='Reviewed for the CS-related scope (2026-10-22): bounds are the first/last dated faculty-list year at EPFL; emeritus listings are not appointment years.')
            periods[name] = dict(periods=[per])
        orc = helpers.orcids('epfl', [c['author']]) if True else []
        dept = s['home']
        row = dict(name=name, aliases=aliases, collection_person_id=None, profile_url=prof[0].replace('?lang=en', '') if prof else None, dblp=[],
                   openalex=[c['author']], orcid=orc,
                   identity_note=(f"OpenAlex {aid} carries the name ({', '.join(c['names'][:3])}) on {c['works']} EPFL-affiliated works 2016-2026 of the school sweep, "
                                  f"{c['dblp_works']} of them DBLP-indexed ({', '.join(c['top_venues'][:3])}); "
                                  + (f"ORCID {', '.join(orc)} from that author record; " if orc else '')
                                  + "matched to the person by name, EPFL affiliation and field (thesis-director records and faculty lists name the same person)."),
                   rank=(s['rank'][0] if s.get('rank') else rank_code(title)), title_as_listed=title, departments=[dept], years_listed=years, sources=sources,
                   is_pi=True, pi_basis=pi_basis, lab_units=[], added=ADDED,
                   cs_related=dict(basis='hierarchy/epfl/cs-related-candidates.json (DBLP-indexed works)', school_works=c['works'], dblp_works=c['dblp_works'],
                                   cs_share=c['cs_share'], top_venues=c['top_venues'][:5]))
        if s.get('note'):
            row['review_note'] = s['note']
        additions.append(row)
        homes.append(dict(school='epfl', name=name, home_department=SCHOOLS[dept], also=[], no_academic_department=False, status='accepted',
                          evidence=hq, note=(s.get('note') or '') + (' Home = school/institute of the profile position\'s unit (people.epfl.ch breadcrumb).' if prof else
                                                                     ' Home = school/institute of the faculty lists that name the person (no live profile).')))
        review.append(dict(name=name, openalex=[c['author']], decision='accepted', reason='accepted', home_department=SCHOOLS[dept], rank=row['rank'],
                           title_as_listed=title, years_listed=years, pi_basis_kind=(pi_basis or {}).get('kind'),
                           phd_records=dict(director=len(direct), director_or_codirector=len(arows),
                                            years=sorted({a['year'] for a in direct}) or sorted({a['year'] for a in arows})),
                           period=(dict(start=per['start'], end=per['end']) if per else None), summary=s.get('note', ''),
                           evidence=[x for x in [pi_basis and {k: pi_basis[k] for k in ('url', 'sha256', 'quote')}, hq] + sources[:1] + sources[-1:] if x]))
    else:
        if name not in R:
            problems.append(f'no decision for {name}'); continue
        dec, summ, *flag = R[name]
        evid = []
        names = [name] + list(c['names'])
        prof = profile_of(name, c['names'])
        if prof:
            pq = position_quote(prof[2])
            if pq:
                e = ev(prof[0], pq, f'{name} profile')
                if e:
                    evid.append(dict(e, kind='profile_position', observed='2026-10-22'))
        fam = norm(re.sub(r',.*', '', name) if ',' in name else name.split()[-1])
        giv = norm(name.split(',')[1].strip().split()[0] if ',' in name else name.split()[0])
        if flag and flag[0] == 'student':
            fl = re.findall(r'[a-z]+', fam)[-1]; gl = re.findall(r'[a-z]+', giv)[0]
            st = [a for a in TI['authors'] if a['role'] == 'phd' and a['quote'] and fl in re.findall(r'[a-z]+', norm(a['author_raw']))
                  and (gl in re.findall(r'[a-z]+', norm(a['author_raw'])) or (len(gl) == 1 and re.search(r',\s*' + gl, norm(a['author_raw']))))]
            for a in st[:1]:
                bring(a['url'], 'thesis')
                e = ev(a['url'], a['quote'], f'{name} thesis author')
                if e:
                    evid.append(dict(e, kind='phd_thesis_author', record=dict(id=a['id'], year=a['year'], dept=a['dept'], advisers=a['advisers'])))
        else:
            co = [a for a in TI['advisers'] if a['role'] == 'phd' and norm(a['adviser']).startswith(fam) and giv in norm(a['adviser']) and a['quote']]
            for a in co[:1]:
                bring(a['url'], 'thesis')
                e = ev(a['url'], a['quote'], f'{name} co-direction')
                if e:
                    evid.append(dict(e, kind=('thesis_codirector' if a['pos'] > 0 else 'thesis_director'), record=dict(id=a['id'], year=a['year'], dept=a['dept'])))
        if dec == 'faculty_no_pi_evidence':
            em = [r for r in rows if r['rank'] and ('Emerit' in r['rank'] or 'Adjunct' in r['rank'])]
            for r in sorted(em, key=lambda r: r['observed'])[:1]:
                bring(r['url'], 'listing')
                e = ev(r['url'], r['quote'], f'{name} listing')
                if e:
                    evid.append(dict(e, kind=f"dept_listing:{r['school']}", observed=r['observed']))
        if not evid:
            evid.append(dict(kind='absence', note='No 2016-2026 EPFL faculty list (school, institute or EPFL-wide lists in the review stores) names the person, no Infoscience doctoral thesis record 2016-2026 names them as thesis director, and no live people.epfl.ch profile was found.'))
        review.append(dict(name=name, openalex=[c['author']], decision=dec, reason=dec, summary=summ, evidence=evid))

json.dump(additions, open(W / 'epfl-additions-new.json', 'w'), indent=1, ensure_ascii=False)
json.dump(periods, open(W / 'epfl-periods.json', 'w'), indent=1, ensure_ascii=False)
json.dump(homes, open(W / 'epfl-home-departments.json', 'w'), indent=1, ensure_ascii=False)
json.dump(review, open(W / 'epfl-review.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps(dict(accepted=len(additions), periods=len(periods), reviewed=len(review),
                      by_decision=collections.Counter(r['decision'] for r in review), problems=problems), indent=1, ensure_ascii=False))
