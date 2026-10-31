"""Build hierarchy/period-tools/proposals/epfl.json (EPFL appointment-period review, 2026-10-26).

Every new evidence item comes from pcap.ev (quote verified against the capture stored in hierarchy/period-captures.sqlite);
existing reviewed evidence items are carried over unchanged from hierarchy/census-overrides.json.
Run: /usr/local/anaconda3/2024.02/bin/python -I hierarchy/period-tools/epfl_build.py
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import epfl_util as U  # noqa: E402

pcap = U.pcap
ROOT = HERE.parents[1]
TARGETS = [t['pi'] for t in json.load(open(ROOT / 'hierarchy/period-targets-20261026.json'))['epfl']]
OVR = json.load(open(ROOT / 'hierarchy/census-overrides.json'))['epfl']
WB = 'https://web.archive.org/web/'
STI1570 = {y: f'{WB}{ts}id_/http://sti.epfl.ch:80/page-1570-en.html' for y, ts in
           [(2011, '20111003214241'), (2015, '20150119035901'), (2016, '20160302010136')]}
STI1613_2011 = f'{WB}20111002025352id_/http://sti.epfl.ch:80/page-1613-en.html'
SB2012 = f'{WB}20120126063856id_/http://sb.epfl.ch:80/faculty'
SB2014 = f'{WB}20140220093534id_/http://sb.epfl.ch:80/faculty'
SB2015 = f'{WB}20150417101756id_/http://sb.epfl.ch:80/faculty'
MATHARCH = 'https://www.epfl.ch/schools/sb/research/math/archive/curriculum-vitae-des-professeurs-de-mathematiques-passes/'
LIVE = '2026-10-23'  # people.epfl.ch profiles captured 2026-10-23 (copied from the CS-related store)


def prof(slug):
    return f'https://people.epfl.ch/{slug}?lang=en'


def ev(url, quote, kind, observed, note=None):
    return pcap.ev(url, quote, kind, observed, note)


def live(slug, quote, observed=LIVE):
    U.prof(slug)
    return ev(prof(slug), quote, 'faculty_profile', observed, 'live people.epfl.ch profile: appointment active as of this date')


def existing(pi):
    ps = (OVR.get(pi) or {}).get('periods') or []
    return ps[0] if ps else None


def period(pi, start, end, asof, prec, evidence, note, keep_existing=True, drop_kinds=()):
    ex = existing(pi)
    items = []
    if ex and keep_existing:
        items += [e for e in ex['evidence'] if e['kind'] not in drop_kinds]
    seen = {(e['url'], e['quote']) for e in items}
    items += [e for e in evidence if (e['url'], e['quote']) not in seen]
    return dict(start=start, end=end, asof=asof, datePrecision=prec, evidence=items, note=note)


P = {}  # pi -> dict(verdict, period, departure, why)
for _s in ['dimitris.kiritsis', 'christian.enz', 'kamiar.aminian', 'dominique.bonvin', 'hannes.bleuler', 'daniel.kuhn', 'ralf.seifert']:
    U.prof(_s)
U.copy_any(STI1570[2016])

# ---------------- new periods for PIs who had none ----------------
P['Eduardo Moraud'] = dict(verdict='period', departure=None, period=period(
    'Eduardo Moraud', '2026-01', None, '2026-10-26', 'month',
    [ev(prof('eduardo.moraud'), 'He joined Neuro-X at EPFL in January 2026.', 'faculty_start_statement', '2026-10-26'),
     ev(prof('eduardo.moraud'), 'Eduardo Moraud eduardo.moraud@epfl.ch vCard Tenure Track Assistant Professor', 'faculty_profile', '2026-10-26')],
    'Start stated on his EPFL profile (joined Neuro-X at EPFL in January 2026; before that a junior PI at CHUV). Ongoing: live profile '
    '2026-10-26 lists him as Tenure Track Assistant Professor. Papers 2016-2025 predate the appointment and stay outside.'))

P['Joseph Sifakis'] = dict(verdict='period', departure='Left EPFL in 2016 (full professor 2011-2016); since 2016 Research Director emeritus at Verimag, Grenoble.',
    period=period('Joseph Sifakis', '2011', '2016', None, 'year',
    [ev('https://actu.epfl.ch/news/epfl-appoints-new-professors-3/', 'Joseph Sifakis has been appointed as Full Professor of Computing and Communications systems at the School of Computer and Communication Sciences (IC)', 'nomination_announcement', '2011-09-30', 'EPFL news 30.09.11: ETH Board nomination'),
     ev('https://en.wikipedia.org/wiki/Joseph_Sifakis', 'has been a full professor [ 7 ] and the Director of the «Rigorous System Design Laboratory » at the School of Computer and Communication Sciences of EPFL (2011–2016)', 'faculty_start_statement', '2026-10-26'),
     ev('https://www.sustech.edu.cn/en/faculties/joseph-sifakis.html', '2011-2016, EPFL, Professor ◆ 2016-present, VERIMAG laboratory, Research Director emeritus', 'departure_announcement', '2026-10-26', 'SUSTech faculty CV')],
    'ETH Board nomination announced 2011-09-30 (effective date not stated, so year precision); CVs give the EPFL professorship as 2011-2016, '
    'consistent with the IC faculty page listing him in 2016-01 but not in 2016-12. 2017 papers are after the departure.'))

P['Sandro Carrara'] = dict(verdict='period', departure=None, period=period(
    'Sandro Carrara', '2015-01-19', None, LIVE, 'day',
    [ev(STI1570[2015], 'CARRARA Sandro Senior Scientist', 'faculty_start_lower_bound', '2015-01-19', 'earliest STI (SEL) faculty-list capture naming him; absent from the 2014-01-27 capture'),
     live('sandro.carrara', 'Sandro Carrara sandro.carrara@epfl.ch https://www.epfl.ch/labs/bci/ vCard Nationality: Swiss and Italian Adjunct Professor')],
    'No stated start found (Wikipedia says he joined EPFL in 2007 but not in what role). Start is a LOWER BOUND: the earliest dated STI '
    'faculty-list capture naming him as Senior Scientist (MER), 2015-01-19. Ongoing (Adjunct Professor on the live 2026 profile). Covers the 2019 listing gap.'))

P['Denis Gillet'] = dict(verdict='period', departure=None, period=period(
    'Denis Gillet', '2011-10-03', None, LIVE, 'day',
    [ev(STI1570[2011], 'GILLET Denis Senior Scientist denis.gillet@epfl.ch', 'faculty_start_lower_bound', '2011-10-03', 'STI (SEL) faculty-list capture'),
     live('denis.gillet', "He is currently Maître d'enseignement et de recherche at the EPFL School of Engineering")],
    'Start is a LOWER BOUND (no stated MER start found): STI faculty list of 2011-10-03 names him as Senior Scientist (MER). Ongoing per the '
    'live 2026 profile. Covers the 2019 listing gap.'))

P['Dimitri Van De Ville'] = dict(verdict='period', departure=None, period=period(
    'Dimitri Van De Ville', '2015', None, LIVE, 'year',
    [ev('https://cibm.ch/?p=7228', 'In 2009, he received a Swiss National Science Foundation professorship. He subsequently became Associate Professor (2015) and Full Professor (2024) at EPFL', 'faculty_start_statement', '2026-10-26', 'CIBM bio'),
     live('dimitri.vandeville', 'Dimitri Van De Ville dimitri.vandeville@epfl.ch http://miplab.epfl.ch/ vCard Nationality: belgo-suisse Full Professor')],
    'Start = tenured Associate Professor at EPFL in 2015 (CIBM bio); he already held an SNSF professorship from 2009 (joint EPFL/UNIGE '
    'tenure-track per his lab page, not captured), so 2015 is conservative. Ongoing (Full Professor, live 2026 profile). Covers 2016 and 2018.'))

P['Daniel Kuhn'] = dict(verdict='period', departure=None, period=period(
    'Daniel Kuhn', '2013', None, LIVE, 'year',
    [ev('https://actu.epfl.ch/news/seven-professors-nominated/', 'Dr Daniel Kuhn currently Senior Lecturer at Imperial College London was appointed as Associate Professor of Operations Research at the College of Management of Technology (CDM)', 'nomination_announcement', '2013-05-24', 'EPFL news 24.05.13'),
     ev(prof('daniel.kuhn'), 'Before joining EPFL, Daniel Kuhn was a faculty member in the Department of Computing at Imperial College London (2007-2013)', 'faculty_profile', LIVE),
     live('daniel.kuhn', 'Daniel Kuhn daniel.kuhn@epfl.ch https://www.epfl.ch/labs/rao/ vCard Nationality: Swiss Full Professor')],
    'ETH Board appointment announced 2013-05-24; profile gives Imperial 2007-2013 before EPFL, so start 2013 (year). Ongoing.'))

P['Alexandre Schmid'] = dict(verdict='period', departure=None, period=period(
    'Alexandre Schmid', '2011', None, LIVE, 'year',
    [ev('https://memento.epfl.ch/event/iem-seminar-series-unconventional-microelectronic/', 'Since 2011, he has been a ‘‘Maître d’Enseignement et de Recherche’’ (MER) Faculty Member of EPFL', 'faculty_start_statement', '2025-10-22', 'EPFL seminar bio (event 22.10.2025)'),
     ev(STI1570[2011], 'SCHMID Alexandre Senior Scientist alexandre.schmid@epfl.ch', 'dept_listing:STI/SEL', '2011-10-03'),
     live('alexandre.schmid', 'Adjunct Professor , SEL - Teaching')],
    'MER since 2011 (stated); listed as Senior Scientist on the STI faculty list in 2011-10. Ongoing (Adjunct Professor, live 2026 profile). Covers 2019, 2021, 2022.'))

P['Daniel Kressner'] = dict(verdict='period', departure=None, period=period(
    'Daniel Kressner', '2011', None, LIVE, 'year',
    [ev('https://actu.epfl.ch/news/eight-professors-appointed-at-epfl/', 'Daniel Kressner has been appointed as tenure track assistant professor of mathematics. He will perform his research work at the MATHICSE institut', 'nomination_announcement', '2011-03-04', 'EPFL news 04.03.11'),
     ev(SB2012, 'Kressner Daniel', 'dept_listing:SB faculty', '2012-01-26'),
     live('daniel.kressner', 'Daniel Kressner daniel.kressner@epfl.ch http://anchp.epfl.ch vCard Full Professor')],
    'ETH Board appointment announced 2011-03-04 (effective date not stated; year precision); on the SB faculty list by 2012-01. Ongoing.'))

P['Nikolas Geroliminis'] = dict(verdict='period', departure=None, period=period(
    'Nikolas Geroliminis', '2009', None, LIVE, 'year',
    [ev('https://actu.epfl.ch/news/nikolas-geroliminis-appointed-tenure-track-assis-2/', 'At its meeting on July 8-9 2009, the Board of the Swiss Federal Institutes of Technology appointed Nikolas Geroliminis a tenure-track assistant professor of transportation engineering', 'nomination_announcement', '2009-07-22', 'EPFL news 22.07.09'),
     live('nikolas.geroliminis', 'Prof. Nikolas Geroliminis is a Full Professor at EPFL and the head of the Urban Transport Systems Laboratory (LUTS)')],
    'ETH Board appointment of July 2009 (effective date not stated; year precision). Ongoing. Covers the 2018 listing gap.'))

P['Jean-Marc Odobez'] = dict(verdict='period', departure=None, period=period(
    'Jean-Marc Odobez', '2016', None, LIVE, 'year',
    [ev(STI1570[2016], 'ODOBEZ Jean-Marc Senior Scientist', 'faculty_start_lower_bound', '2016-03-02', 'earliest dated STI faculty-list capture naming him; absent from the 2015-01-19 capture'),
     ev(f'{WB}20170703194346id_/http://www.idiap.ch/en/allnews/three-idiap-seniors-researchers-awarded', 'three of its senior researchers ( Daniel Gatica-Perez , Jean-Marc Odobez and Francois Fleuret ) have been awarded an academic title (MER, Maître d’Enseignement et de Recherche) from EPFL', 'faculty_profile', '2017-07-03', 'undated Idiap news item (capture date only)'),
     live('jean-marc.odobez', 'Jean-Marc Odobez jean-marc.odobez@epfl.ch +41 27 721 77 26 vCard Senior Scientist')],
    'Start is a LOWER BOUND: MER title date not found (Idiap news item undated); first dated STI faculty-list capture naming him is 2016-03-02. '
    'Ongoing. Covers the 2019 listing gap.'))

P['Alireza Karimi'] = dict(verdict='period', departure=None, period=period(
    'Alireza Karimi', '2011-10-02', None, LIVE, 'day',
    [ev(STI1613_2011, 'KARIMI Alireza Senior Scientist alireza.karimi@epfl.ch', 'faculty_start_lower_bound', '2011-10-02', 'STI (IGM) faculty-list capture'),
     live('alireza.karimi', 'He is currently Professor of Automatic Control and the Head of the Data-Driven Modelling and Control Group within the Institute of Mechanical Engineering of EPFL')],
    'Start is a LOWER BOUND (no stated start found): STI IGM faculty list 2011-10-02 names him as Senior Scientist (MER). Ongoing (Adjunct Professor). Covers 2019.'))

P['Henry Markram'] = dict(verdict='period', departure=None, period=period(
    'Henry Markram', '2002', None, LIVE, 'year',
    [ev('https://www.epfl.ch/labs/markram-lab/?p=98', 'He moved to EPFL in 2002 as a full professor and founder/director of the Brain Mind Institute.', 'faculty_start_statement', '2026-10-26', 'LNMC lab page bio'),
     live('henry.markram', 'Henry Markram henry.markram@epfl.ch vCard Full Professor')],
    'Full professor at EPFL since 2002 (stated). Ongoing.'))

P['Fabio Nobile'] = dict(verdict='period', departure=None, period=period(
    'Fabio Nobile', '2011', None, LIVE, 'year',
    [ev('https://actu.epfl.ch/news/four-professors-appointed-at-epfl/', 'Fabio Nobile has been appointed Associate Professor of Mathematics at the School of Basic Sciences (FSB)', 'nomination_announcement', '2011-05-20', 'EPFL news 20.05.11'),
     ev(SB2012, 'Nobile Fabio', 'dept_listing:SB faculty', '2012-01-26'),
     live('fabio.nobile', 'Fabio Nobile fabio.nobile@epfl.ch http://csqi.epfl.ch vCard Full Professor')],
    'ETH Board appointment announced 2011-05-20 (effective date not stated; year precision). Ongoing.'))

P['Thomas A. Weber'] = dict(verdict='period', departure=None, period=period(
    'Thomas A. Weber', '2011', None, LIVE, 'year',
    [ev('https://actu.epfl.ch/news/meet-a-professor-thomas-a-weber/', 'When the opportunity arose to come to EPFL in 2011, having spent more than a decade in the United States, I was eager to return to Europe', 'faculty_start_statement', '2019-05-01', 'EPFL interview 01.05.19'),
     live('thomas.weber', 'Thomas Weber thomas.weber@epfl.ch http://oes.epfl.ch vCard Full Professor')],
    'Came to EPFL (Chair of Operations, Economics and Strategy) in 2011 (stated in his own interview). Ongoing.'))

P['Mahmut Selman Sakar'] = dict(verdict='period', departure=None, period=period(
    'Mahmut Selman Sakar', '2016-07-05', None, LIVE, 'day',
    [ev(f'{WB}20160705190622id_/http://microbs.epfl.ch:80/', 'Mahmut Selman Sakar, Ph.D. Assistant Professor Institute of Mechanical Engineering', 'faculty_start_lower_bound', '2016-07-05', 'MICROBS lab homepage capture (page footer: Updated 03.06.2016); earliest capture of the lab site'),
     ev('https://actu.epfl.ch/news/appointment-of-sti-professors/', 'Mahmut Selman Sakar, currently Tenure Track Assistant Professor at EPFL, as Associate Professor of Mechanical Engineering', 'faculty_profile', '2023-05-26', 'promotion 2023'),
     live('selman.sakar', 'Selman Sakar selman.sakar@epfl.ch vCard Associate Professor')],
    'Start corrected from 2017 (first STI list) to a LOWER BOUND of 2016-07-05: the earliest capture of his lab site already names him '
    'Assistant Professor (tenure track) of the Institute of Mechanical Engineering. Ongoing.'))

P['Ralf W. Seifert'] = dict(verdict='period', departure=None, period=period(
    'Ralf W. Seifert', '2003', None, LIVE, 'year',
    [ev(prof('ralf.seifert'), 'Ralf W. Seifert is Professor of Technology & Operations Management (TOM) at the College of Management of Technology (CDM) at Ecole Polytechnique Fédérale de Lausanne (EPFL) since 2003', 'faculty_start_statement', LIVE),
     live('ralf.seifert', 'Ralf Seifert ralf.seifert@epfl.ch http://tom.epfl.ch vCard Nationality: German and Swiss Full Professor')],
    'Professor at EPFL since 2003 (stated on profile; held jointly with IMD). Ongoing.'))

P['Simone Deparis'] = dict(verdict='period', departure=None, period=period(
    'Simone Deparis', '2006', None, LIVE, 'year',
    [ev('https://www.edx.org/bio/simone-deparis', 'Maitre d’Enseignement et de Recherche, à l’EPFL depuis 2006.', 'faculty_start_statement', '2026-10-26', 'edX instructor bio (undated; read as MER at EPFL since 2006)'),
     ev('https://actu.epfl.ch/news/appointment-of-four-adjunct-professors-at-sb/', 'At its meeting of 12-13 December 2018, the ETH Board has awarded the title of adjunct professor to four researchers of the School of Basic Sciences (SB). Simone Deparis', 'nomination_announcement', '2018-12-14', 'adjunct professor title Dec 2018'),
     live('simone.deparis', 'Simone Deparis simone.deparis@epfl.ch https://www.epfl.ch/labs/sci-sb-sd/professor-simone-deparis/ vCard Adjunct Professor')],
    'MER at EPFL since 2006 per his edX bio (the sentence could also be read as "at EPFL since 2006"; he was an MIT postdoc 2004-2006); '
    'adjunct professor title from the ETH Board in Dec 2018. If only the adjunct title is accepted, start would be 2018-12 and 2016-2018 stay outside. Ongoing.'))

P['Annalisa Buffa'] = dict(verdict='period', departure=None, period=period(
    'Annalisa Buffa', '2016', None, LIVE, 'year',
    [ev('https://academie-sciences.fr/en/annalisa-buffa', 'Annalisa Buffa has been a professor of mathematics at the École Polytechnique Fédérale de Lausanne (EPFL) since 2016.', 'faculty_start_statement', '2026-10-26', 'Académie des sciences biography'),
     live('annalisa.buffa', 'Annalisa Buffa annalisa.buffa@epfl.ch vCard Full Professor')],
    'Professor at EPFL since 2016 (stated). Her CV (PDF, not text-capturable) gives 09/2016, so 2016 papers stay unresolved at year precision. Ongoing.'))

P['Marco Picasso'] = dict(verdict='period', departure=None, period=period(
    'Marco Picasso', '2012-01-26', None, LIVE, 'day',
    [ev(SB2012, 'Picasso Marco Chair of Numerical Analysis and Simulation (ASN) Mathematics', 'faculty_start_lower_bound', '2012-01-26', 'SB "Faculty Members" list (no titles); he is also listed there in 2013, 2014 and 2015'),
     ev(SB2015, 'Picasso Marco Picasso Group (GR-PI) Mathematics', 'dept_listing:SB faculty', '2015-04-17'),
     live('marco.picasso', 'Marco Picasso marco.picasso@epfl.ch vCard Adjunct Professor')],
    'Start is a LOWER BOUND: no stated start found (CV is a PDF); the School of Basic Sciences "Faculty Members" list names him from the '
    'earliest capture checked (2012-01-26; the list carries no titles). Ongoing (Adjunct Professor).'))

P['Sean L. Hill'] = dict(verdict='period', departure=None, period=period(
    'Sean L. Hill', '2018-12-15', None, LIVE, 'day',
    [ev(f'{WB}20181215122700id_/http://people.epfl.ch/sean.hill?lang=en', 'Sean Hill Edit profile Adjunct Professor sean.hill@epfl.ch', 'faculty_start_lower_bound', '2018-12-15', 'earliest people.epfl.ch capture showing a title; 2013-2017 captures are the old format without titles'),
     live('sean.hill', 'Sean Hill sean.hill@epfl.ch https://www.epfl.ch/labs/gr-hill/ vCard Adjunct Professor')],
    'Start is a LOWER BOUND (adjunct title date not found). Ongoing: listed as Adjunct Professor in 2026 (concurrently director of the '
    'Krembil Centre at CAMH, Toronto). 2016-2018 papers (3) stay outside unless an earlier title is found.'))

# ---------------- corrected periods (existing reviewed period, start null or too late) ----------------
P['Dimitris Kiritsis'] = dict(verdict='period', departure='Professor Emeritus by 2026 (retirement date not found; last dated active listing as Adjunct Professor 2023-04-07).',
    period=period('Dimitris Kiritsis', '2011-10-02', '2023', None, 'day',
    [ev(STI1613_2011, 'KIRITSIS Dimitris Senior Scientist dimitris.kiritsis@epfl.ch', 'faculty_start_lower_bound', '2011-10-02', 'STI (IGM) faculty-list capture'),
     ev(f'{WB}20230325144559id_/http://people.epfl.ch/dimitris.kiritsis?lang=en', 'Dimitrios Kyritsis Edit profile Adjunct Professor', 'faculty_profile', '2023-03-25'),
     ev(prof('dimitris.kiritsis'), 'Professor Emeritus , Honorary Professors STI', 'emeritus_listing', LIVE)],
    'Start is a LOWER BOUND: STI IGM faculty list 2011-10-02 names him as Senior Scientist (MER); later Adjunct Professor. End kept at the '
    'last dated faculty listing year (2023); he is Professor Emeritus on the live profile, retirement date not found. Year-only end.'))

P['Yusuf Leblebici'] = dict(verdict='period', departure='Appointed President of Sabancı University (announced 2018-11-09, taking office during 2019); last dated EPFL faculty listing 2020-12; no EPFL end date found.',
    period=period('Yusuf Leblebici', '2002', '2020', None, 'year',
    [ev('https://actu.epfl.ch/news/yusuf-leblebici-appointed-president-of-sabanc-univ/', 'An Istanbul native, Leblebici joined EPFL in 2002 where he set up the Microelectronic Systems Laboratory (LSM).', 'faculty_start_statement', '2018-11-09', 'EPFL news 09.11.18'),
     ev('https://actu.epfl.ch/news/yusuf-leblebici-appointed-president-of-sabanc-univ/', 'Sabancı University announced this week that EPFL professor Yusuf Leblebici will become its new president, taking office in 2019.', 'departure_announcement', '2018-11-09'),
     ev(STI1570[2011], 'LEBLEBICI Yusuf Full Professor', 'dept_listing:STI/SEL', '2011-10-03')],
    'Start 2002 (stated). End kept at the last dated faculty listing (Full Professor, 2020-12-05): he became Sabancı president in 2019 '
    'but stayed listed as EPFL full professor through 2020; no source dates the end of the EPFL appointment, so it is not extended.'))

P['Christian Enz'] = dict(verdict='period', departure='Retired 2023: Professor Emeritus on his EPFL profile by 2023-09-27 (last listed active 2023-03-30).',
    period=period('Christian Enz', '2013', '2023', None, 'year',
    [ev(prof('christian.enz'), 'He joined the EPFL as full professor in 2013', 'faculty_start_statement', LIVE),
     ev(f'{WB}20230927190432id_/http://people.epfl.ch/christian.enz?lang=en', 'Christian Enz Edit profile Professor Emeritus', 'emeritus_listing', '2023-09-27'),
     ev(STI1570[2011], 'ENZ Christian Adjunct Professor', 'dept_listing:STI/SEL', '2011-10-03', 'adjunct professor while at CSEM, before the 2013 full professorship')],
    'Start: full professor at EPFL in 2013 (stated; he was also an adjunct professor while at CSEM, listed 2011). End: emeritus by '
    '2023-09-27, last active listing 2023-03-30, so end stays 2023; 2024-2025 papers are after retirement.'))

P['Catherine Dehollain'] = dict(verdict='period', departure='Retired (Honorary Professors STI) by 2022-03-05; last active listing as Adjunct Professor 2021-04-13.',
    period=period('Catherine Dehollain', '2011-10-03', '2021', None, 'day',
    [ev(STI1570[2011], 'DEHOLLAIN Catherine Senior Scientist catherine.dehollain@epfl.ch', 'faculty_start_lower_bound', '2011-10-03', 'STI (SEL) faculty-list capture'),
     ev(f'{WB}20220305234659id_/http://people.epfl.ch/catherine.dehollain?lang=en', 'Honorary Professors STI EPFL STI-DO BM 4101', 'emeritus_listing', '2022-03-05')],
    'Start is a LOWER BOUND (her profile says she has led the RFIC group since 1995 but gives no title date): STI list 2011-10-03 names '
    'her Senior Scientist (MER); later Adjunct Professor. End 2021 kept: she is under Honorary Professors STI by 2022-03-05.'))

P['Jan S. Hesthaven'] = dict(verdict='period', departure='Left EPFL to become President of KIT, taking office 2024-10-01 (EPFL Provost 2021-2024).',
    period=period('Jan S. Hesthaven', '2013-07', '2024-09', None, 'month',
    [ev('https://actu.epfl.ch/news/a-new-professor-and-two-faculty-promotions-4/', 'Prof. Jan Hesthaven has been appointed Full Professor as of July 1st 2013', 'faculty_start_statement', '2013-06-07', 'EPFL news 07.06.13'),
     ev('https://www.kit.edu/eb/president.php', 'On October 1, 2024, Jan S. Hesthaven took office as President of KIT.', 'departure_announcement', '2026-10-26'),
     ev('https://www.kit.edu/eb/president.php', 'From 2013, Hesthaven had been Professor of Mathematics of the École Polytechnique Fédérale de Lausanne (EPFL) in Switzerland, and from 2021 to 2024, Provost and Vice President for Academic Affairs of EPFL.', 'faculty_profile', '2026-10-26')],
    'Full professor from 2013-07-01 (stated). End 2024-09: he took office as KIT President on 2024-10-01; the 2025 EPFL emeritus '
    'listing is not an appointment year. Month precision (start is exact to the day).'))

P['János Pach'] = dict(verdict='period', departure='Retired 2019 (EPFL math archive: arrivée 2008, retraite 2019); emeritus listing by 2019-10-16.',
    period=period('János Pach', '2008', '2019', None, 'year',
    [ev(MATHARCH, 'Prof. Janos Pach (arrivée 2008, retraite 2019)', 'faculty_start_statement', '2026-10-26', 'EPFL mathematics archive of former professors'),
     ev(SB2012, 'Pach János Chair of Combinatorial Geometry', 'dept_listing:SB faculty', '2012-01-26')],
    'Arrival 2008 and retirement 2019 per the EPFL mathematics archive; end 2019 matches the last faculty listing (2019-03-10) and the '
    'emeritus listing of 2019-10-16. 2020+ papers are after retirement.'))

P['Mohamed Bouri'] = dict(verdict='period', departure=None, period=period(
    'Mohamed Bouri', '2023-12-26', None, LIVE, 'day',
    [ev(f'{WB}20231226222347id_/http://people.epfl.ch/mohamed.bouri?lang=fr', 'Mohamed Bouri Edit profile Senior Scientist mohamed.bouri@epfl.ch', 'faculty_start_lower_bound', '2023-12-26', 'first capture with the Senior Scientist (MER) title'),
     ev(f'{WB}20231015062051id_/http://people.epfl.ch/mohamed.bouri?lang=en', 'Mohamed Bouri Edit profile Scientist mohamed.bouri@epfl.ch', 'faculty_profile', '2023-10-15', 'previous capture: still Scientist (not faculty-level)'),
     ev(f'{WB}20190818154803id_/http://people.epfl.ch/mohamed.bouri?lang=en', 'Mohamed Bouri Edit profile Lecturer mohamed.bouri@epfl.ch', 'faculty_profile', '2019-08-18', 'Lecturer/Scientist only in 2019-2023'),
     live('mohamed.bouri', 'Senior Scientist , SMT - Teaching')],
    'Start corrected from 2024 to 2023-12-26: his profile shows Scientist (not faculty-level) through 2023-10-15 and Senior Scientist (MER) '
    'from 2023-12-26, so the MER appointment began between those captures; the later date is used. Before that he was Lecturer/Scientist '
    '(with EPFL since 1997), so 2016-2023 papers correctly stay outside. Ongoing.'))

P['Kamiar Aminian'] = dict(verdict='period', departure='Retired between 2023-12-26 (still Adjunct Professor) and 2024-02-29 (Professor Emeritus).',
    period=period('Kamiar Aminian', '2007', '2023-12', None, 'month',
    [ev(prof('kamiar.aminian'), 'Since 2007, he has held the position of "Professor titulaire" at EPFL\'s Institute of Bioengineering', 'faculty_start_statement', LIVE),
     ev(f'{WB}20231226224902id_/http://people.epfl.ch/kamiar.aminian?lang=en', 'Kamiar Aminian Edit profile Adjunct Professor', 'faculty_profile', '2023-12-26', 'last capture with an active title'),
     ev(f'{WB}20240229091210id_/http://people.epfl.ch/kamiar.aminian?lang=en', 'Kamiar Aminian Edit profile Professor Emeritus', 'emeritus_listing', '2024-02-29')],
    'Start: professeur titulaire (adjunct professor) since 2007 (stated; he founded LMAM in 2002). End corrected from 2024 to 2023-12: the '
    'existing end rested on a 2024 listing that already shows him as Professor Emeritus; his profile is Adjunct Professor on 2023-12-26 and '
    'Professor Emeritus on 2024-02-29 (likely end-of-January retirement, not proven, so not extended into 2024). The existing '
    '"last_dated_faculty_listing" item (an emeritus listing) is dropped; its emeritus_listing twin is kept.', drop_kinds=('last_dated_faculty_listing',)))

P['Dominique Bonvin'] = dict(verdict='period', departure='Retired; Professeur honoraire on his EPFL profile by 2019-03-07 (last listed Full Professor 2017-05-02).',
    period=period('Dominique Bonvin', '1989', '2017', None, 'year',
    [ev(prof('dominique.bonvin'), 'He joined the EPFL in 1989, where his current research interests include modeling, control and optimization of dynamic systems.', 'faculty_start_statement', LIVE),
     ev(STI1613_2011, 'BONVIN Dominique Full Professor', 'dept_listing:STI/IGM', '2011-10-02'),
     ev(f'{WB}20190307173443id_/http://people.epfl.ch/dominique.bonvin', 'Professeur honoraire , Professeurs', 'emeritus_listing', '2019-03-07')],
    'Joined EPFL in 1989 (stated; the profile describes him as Professor and lab director). End kept at 2017 (last listing as Full '
    'Professor); honorary (emeritus) by 2019-03; no exact retirement date found.'))

P['Jean-Marc Vesin'] = dict(verdict='period', departure=None, period=period(
    'Jean-Marc Vesin', '2011-10-03', '2022', None, 'day',
    [ev(STI1570[2011], 'VESIN Jean-Marc Senior Scientist jean-marc.vesin@epfl.ch', 'faculty_start_lower_bound', '2011-10-03', 'STI (SEL) faculty-list capture')],
    'Start is a LOWER BOUND (no stated MER start found): STI list 2011-10-03 names him Senior Scientist (MER). End kept at the last dated '
    'listing year (2022); no departure/retirement source found, so 2023-2024 stay outside. Covers the 2019 listing gap.'))

P['Hervé Bourlard'] = dict(verdict='period', departure='EPFL professorship ended by 2021 (last listed 2021-04-13; now Professor Emeritus); retired as Idiap director in March 2023.',
    period=period('Hervé Bourlard', '1997', '2021', None, 'year',
    [ev('https://people.idiap.ch/bourlard/full-biography', 'Since 1997, Hervé Bourlard is also Professor at the Swiss Federal Institute of Technology, Lausanne (EPFL), where he was promoted to the rank of Full Professor in December 2004.', 'faculty_start_statement', '2026-10-26', 'Idiap biography'),
     ev(STI1570[2011], 'BOURLARD Hervé Full Professor', 'dept_listing:STI/SEL', '2011-10-03')],
    'Professor at EPFL since 1997 (stated). End kept at 2021 (last dated listing, Full Professor 2021-04-13); he is Professor Emeritus '
    'now; his Idiap directorship ran to 2023 but that is not the EPFL appointment.'))

P['José del R. Millán'] = dict(verdict='period', departure='Left EPFL for the University of Texas at Austin in 2019.',
    period=period('José del R. Millán', '2009', '2019', None, 'year',
    [ev('https://people.epfl.ch/149175?lang=en', 'Dr. José del R. Millán joined EPFL in 2009 to help establish the Center for Neuroprosthetics. He holds the Defitech Foundation Chair', 'faculty_start_statement', '2026-10-26'),
     ev('https://ece.utexas.edu/news/visionaries-jose-del-r-millan', 'Millán came to The University of Texas at Austin in 2019', 'departure_announcement', '2026-10-26')],
    'Joined EPFL in 2009 as Defitech Foundation Chair (stated). End 2019: moved to UT Austin in 2019 (last EPFL listing 2019-07-30). 2020+ papers are after departure.'))

P['Felix Schürmann'] = dict(verdict='period', departure='Blue Brain Project closed end of 2024; EPFL directory now marks him as no longer at EPFL (date not captured).',
    period=period('Felix Schürmann', '2019-03-07', '2023', None, 'day',
    [ev(f'{WB}20190307134100id_/http://people.epfl.ch/felix.schuermann', 'Felix Schürmann Editer le profil Professeur titulaire', 'faculty_start_lower_bound', '2019-03-07', 'earliest people.epfl.ch capture showing a title; the 2015 capture is the old format without titles'),
     ev('https://memento.epfl.ch/event/computational-brain-science-putting-computational-/', 'Felix Schürmann is adjunct professor at the Ecole polytechnique fédérale de Lausanne (EPFL), co-director of the Blue Brain Project', 'faculty_profile', '2020-04-07')],
    'Start is a LOWER BOUND (adjunct/titulaire title date not found; no title evidence before 2019-03-07). End kept at the last dated '
    'listing year (2023); no source shows the appointment continuing into 2024. 2016-2018 and 2024-2026 stay outside.'))

P['Ian F. C. Smith'] = dict(verdict='period', departure='Professor Emeritus since December 2020.',
    period=period('Ian F. C. Smith', '1999', '2020-11', None, 'month',
    [ev('https://www.epfl.ch/schools/enac/honorary-professors/ph-home/smith-ian-f-c/', 'In 1996, I moved back to the Civil Engineering Department and was nominated “Extraordinary Professor” (!!) in 1999 and “Ordinary Professor” in 2005.', 'faculty_start_statement', '2026-10-26', 'ENAC honorary-professor page (own CV)'),
     ev('https://www.epfl.ch/schools/enac/honorary-professors/ph-home/smith-ian-f-c/', 'As an Emeritus Professor since December 2020', 'retirement_announcement', '2026-10-26')],
    'Professor (extraordinary) from 1999, ordinary 2005 (stated). End 2020-11: emeritus since December 2020. Covers the 2018 listing gap; '
    '2021+ papers are after retirement.'))

P['Rachid Cherkaoui'] = dict(verdict='period', departure='Now Invited guest / Visiting Researcher on his EPFL profile (2026); last dated faculty listing 2024-11-05; end date not found.',
    period=period('Rachid Cherkaoui', '2011-10-03', '2024', None, 'day',
    [ev(STI1570[2011], 'CHERKAOUI Rachid Senior Scientist rachid.cherkaoui@epfl.ch', 'faculty_start_lower_bound', '2011-10-03', 'STI (SEL) faculty-list capture')],
    'Start is a LOWER BOUND (profile says he has led power-systems research at EPFL since 1993, no title date): STI list 2011-10-03 names '
    'him Senior Scientist (MER). End kept at 2024 (last dated listing); he is an invited guest/visiting researcher now. Covers 2019; 2025 stays outside.'))

P['Assyr Abdulle'] = dict(verdict='period', departure='Died 2021-09-01.',
    period=period('Assyr Abdulle', '2009', '2021-09-01', None, 'day',
    [ev(MATHARCH, 'Prof. Assyr Abdulle (arrivée 2009, décès 2021)', 'faculty_start_statement', '2026-10-26', 'EPFL mathematics archive of former professors'),
     ev('https://actu.epfl.ch/news/assyr-abdulle-1971-2021-2/', 'Assyr Abdulle passed away on September 1st, after courageously fighting illness for many years', 'obituary', '2021-09-03', 'EPFL news 03.09.21'),
     ev(SB2012, 'Abdulle Assyr', 'dept_listing:SB faculty', '2012-01-26')],
    'Arrived at EPFL in 2009 (math archive); died 2021-09-01 (EPFL obituary). Start is year-only, end exact. 2022+ papers are posthumous.'))

P['Hannes Bleuler'] = dict(verdict='period', departure='Retired 2019 (honorary lecture 2019-06-12; Professor Emeritus now).',
    period=period('Hannes Bleuler', '1995', '2019', None, 'year',
    [ev(prof('hannes.bleuler'), '1995-present Full Professor at EPFL Lausanne on micro–robotics, biomedical robotics', 'faculty_start_statement', LIVE),
     ev('https://memento.epfl.ch/event/drowned-in-mainstream/', 'Honorary lecture of Prof. Hannes Bleuler: "Drowned in Mainstream"', 'retirement_announcement', '2019-06-12', 'honorary (farewell) lecture'),
     ev(f'{WB}20111003214038id_/http://sti.epfl.ch:80/page-1698-en.html', 'BLEULER Hannes Full Professor', 'dept_listing:STI/IMT', '2011-10-03')],
    'Full professor from 1995 (stated). End kept at 2019: honorary lecture 2019-06-12 and last dated listing 2019-07-30; emeritus now.'))

P['Bernard M. E. Moret'] = dict(verdict='period', departure='Retired at the end of 2016 (LCBB closed).',
    period=period('Bernard M. E. Moret', '2006-06', '2016-12', None, 'month',
    [ev('https://lcbb.epfl.ch/', 'The Laboratory was started in June 2006 by Professor Bernard Moret , as he joined EPFL after working 26 years on the faculty at the University of New Mexico.', 'faculty_start_statement', '2026-10-26'),
     ev('https://lcbb.epfl.ch/', 'The Laboratory closed at end of 2016, as Prof. Moret retired (after 36.5 years as a faculty member).', 'retirement_announcement', '2026-10-26')],
    'Joined EPFL in June 2006 and retired at the end of 2016 (lab site). 2017 and 2023 papers are after retirement.'))

P['Dimitar Jetchev'] = dict(verdict='period', departure='SNSF professorship ended by 2020-08-14 (profile then lists only an Inpher Sàrl affiliation, status outside EPFL); later only lecturer/host roles.',
    period=period('Dimitar Jetchev', '2014-02-20', '2019', None, 'day',
    [ev(SB2014, 'Jetchev Dimitar Jetchev Group (GR-JET) Mathematics', 'faculty_start_lower_bound', '2014-02-20', 'SB "Faculty Members" list (no titles); not on the 2013-03-18 capture'),
     ev(f'{WB}20190308055745id_/http://people.epfl.ch/dimitar.jetchev?lang=en', 'SNSF-funded Professor , Jetchev Group EPFL SB MATH GR-JET', 'faculty_profile', '2019-03-08'),
     ev(f'{WB}20200814151352id_/http://people.epfl.ch/dimitar.jetchev', 'Collaborateur Statut: Hors EPFL Inpher Sàrl', 'departure_announcement', '2020-08-14'),
     ev(f'{WB}20220519160836id_/http://people.epfl.ch/dimitar.jetchev', 'Professeur hôte Statut: Hôte', 'faculty_profile', '2022-05-19', 'host/lecturer only, not a faculty appointment')],
    'Start is a LOWER BOUND: SNSF-professorship start date not found; he first appears with his own group on the SB faculty list on '
    '2014-02-20 (absent 2013-03-18). End kept at 2019 (last listing as SNSF-funded Professor 2019-07-30); by 2020-08 the profile shows '
    'him outside EPFL, and later roles are host professor / lecturer only.'))

P['Pierre-André Farine'] = dict(verdict='period', departure='Retired; Professeur honoraire on his EPFL profile by 2019-07-17 (last listed 2018-01-29).',
    period=period('Pierre-André Farine', '2009-01-01', '2018', None, 'day',
    [ev(f'{WB}20190717210650id_/http://people.epfl.ch/pierre-andre.farine', 'Full professor at EPFL since January 1st, 2009', 'faculty_start_statement', '2019-07-17'),
     ev(f'{WB}20190717210650id_/http://people.epfl.ch/pierre-andre.farine', 'Professeur honoraire , Professeurs honoraires STI', 'emeritus_listing', '2019-07-17')],
    'Full professor at EPFL from 2009-01-01 (stated; IMT Neuchâtel joined EPFL). End kept at 2018 (last dated listing); honorary by 2019-07-17. Year-only end.'))

P['Christopher L. Tucci'] = dict(verdict='period', departure='Left EPFL 2020-04-30 for Imperial College London (Professor from 2020-05-01).',
    period=period('Christopher L. Tucci', '2003-10-01', '2020-04-30', None, 'day',
    [ev('https://www.imperial.ac.uk/people/c.tucci', 'Chair in Corporate Strategy & Innovation École Polytechnique Fédérale de Lausanne, Lausanne, Switzerland 1 Oct 2003 - 30 Apr 2020', 'faculty_start_statement', '2026-10-26', 'Imperial College profile, academic positions'),
     ev('https://www.imperial.ac.uk/people/c.tucci', 'Imperial College London, Management & Entrepreneurship, London, United Kingdom 1 May 2020 - present', 'departure_announcement', '2026-10-26'),
     ev('https://actu.epfl.ch/news/nomination-of-chris-tucci-as-the-new-director-of-4/', 'Since 2003, Christopher Tucci has been a professor of management of technology at EPFL occupying the Chair of Corporate Strategy and Innovation.', 'faculty_profile', '2026-10-26')],
    'EPFL chair 2003-10-01 to 2020-04-30 (his Imperial CV). End EXTENDED from 2019 (last listing) to 2020-04-30 on this evidence; 2020 '
    'papers before May now resolve; 2023 papers are after departure.'))

P['Giancarlo Ferrari-Trecate'] = dict(verdict='period', departure=None, period=period(
    'Giancarlo Ferrari-Trecate', '2016-09', None, LIVE, 'month',
    [ev('https://events.vtools.ieee.org/m/317453', 'Since September 2016 he is Professor at EPFL, Lausanne, Switzerland, and head of the Dependable Control and Decision group (DECODE).', 'faculty_start_statement', '2026-10-26', 'IEEE event bio'),
     ev('https://events.vtools.ieee.org/m/317453', "From 2005 to August 2016, he was Associate Professor at the Dipartimento di Ingegneria Industriale e dell'Informazione of the Universita' degli Studi di Pavia.", 'faculty_profile', '2026-10-26'),
     live('giancarlo.ferraritrecate', 'Giancarlo Ferrari Trecate Il - He/him giancarlo.ferraritrecate@epfl.ch https://www.epfl.ch/labs/decode/ vCard Adjunct Professor')],
    'Start corrected from 2017 (first listing) to 2016-09 (stated; Pavia until August 2016). Ongoing.'))

P['Andrei Popescu-Belis'] = dict(verdict='no_change', departure=None, period=None,
    why='Existing start 2022 (first EDEE listing as Senior Scientist, 2022-06-16) stands: his people.epfl.ch profile shows only "Chargé de '
        'cours" (lecturer) on 2019-07-23 and 2021-02-25, and lecturer-only roles do not count, so the single rejected 2021 paper is correctly outside.',
    why_evidence=[ev(f'{WB}20210225112223id_/http://people.epfl.ch/andrei.popescu-belis', 'Andrei Popescu-Belis Chargé de cours andrei.popescu-belis@epfl.ch Chargé de cours , EDEE - Enseignement', 'faculty_profile', '2021-02-25')])

out = []
for name in TARGETS:
    p = P[name]
    ex = existing(name)
    item = {'pi': name, 'existing_period_id': ex['id'] if ex else None, 'verdict': p['verdict'], 'period': p.get('period'),
            'departure': p.get('departure'), 'why': p.get('why')}
    if p.get('why_evidence'):
        item['why_evidence'] = p['why_evidence']
    out.append(item)
missing = [t for t in TARGETS if t not in P]
assert not missing, missing
(HERE / 'proposals').mkdir(exist_ok=True)
json.dump(out, open(HERE / 'proposals' / 'epfl.json', 'w'), ensure_ascii=False, indent=1)
from collections import Counter
print(Counter(o['verdict'] for o in out), len(out))
