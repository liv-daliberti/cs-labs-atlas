"""Follow-up appointment-period review (2026-10-27): sourced START dates for core PIs whose dated listings begin after
they had joined (and ends where they left).  Writes hierarchy/period-tools/proposals/<school>-followup.json.

Every new evidence item is built by pcap.ev (quote verified against the capture stored in hierarchy/period-captures.sqlite).
Listing rows are copied unchanged from listings/<school>/captures.sqlite (sha256 re-checked) before their quote is verified;
a listing row that cannot be copied or whose quote the stored text cannot show is left out of the evidence.
Existing override periods that are replaced keep their evidence items.
usage: python3 -I followup_build.py <school> [<school> ...]
"""
import json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pcap  # noqa: E402

ROOT = HERE.parents[1]
OVR = json.load(open(ROOT / 'hierarchy/census-overrides.json'))
WB = 'https://web.archive.org/web/'
TODAY = '2026-10-27'


def ev(url, quote, kind, observed, note=None):
    return pcap.ev(url, quote, kind, observed, note)


def pis(school):
    return {p['pi']: p for p in json.load(open(ROOT / f'hierarchy/{school}/pis.json'))}


def listing(school, pi, year, kind=None):
    """Evidence item from the PI's dated listing row of `year` (hierarchy/<school>/pis.json)."""
    l = next(x for x in pis(school)[pi]['listings'] if x['year'] == year)
    obs = (re.search(r'/web/(\d{8})', l['url']) or [None, None])[1]
    obs = f'{obs[:4]}-{obs[4:6]}-{obs[6:]}' if obs else None
    k = kind or l.get('kind') or 'dept_listing'
    try:
        if 'web.archive.org' in l['url'] and not pcap.cached(l['url']):
            pcap.copy_listing(school, l['url'])
        return ev(l['url'], l['quote'], k, obs)
    except (ValueError, KeyError) as e:  # not storable/verifiable in period-captures.sqlite: left out of the evidence
        print('  skip listing', pi, year, str(e)[:90])
        return None


def existing(school, pi):
    ps = (OVR.get(school, {}).get(pi) or {}).get('periods') or []
    return ps[0] if ps else None


def period(school, pi, start, end, asof, prec, evidence, note, endPrecision=None):
    ex = existing(school, pi)
    items = [e for e in evidence if e]
    seen = {(e['url'], e['quote']) for e in items}
    if ex:
        items += [e for e in ex['evidence'] if (e['url'], e['quote']) not in seen]
    p = dict(start=start, end=end, asof=asof, datePrecision=prec, evidence=items, note=note)
    if endPrecision:
        p['endPrecision'] = endPrecision
    return dict(pi=pi, existing_period_id=ex['id'] if ex else None, verdict='period', period=p, departure=None)


def no_change(pi, why, evidence=()):
    return dict(pi=pi, existing_period_id=None, verdict='no_change', period=None, departure=None, why=why, evidence=list(evidence))


def prof(slug):
    return f'https://people.epfl.ch/{slug}?lang=en'


B = {}


def epfl():
    s, out = 'epfl', []
    out.append(period(s, 'Mario Paolone', '2011', None, TODAY, 'year', [
        ev(prof('mario.paolone'), 'Since 2011, he has been with the Swiss Federal Institute of Technology, Lausanne, Switzerland, where he is a Full Professor and the Chair of the Distributed Electrical Systems Laboratory.', 'faculty_start_statement', TODAY),
        listing(s, 'Mario Paolone', 2019)],
        'Start: with EPFL since 2011, now Full Professor and head of DESL (his live EPFL profile, 2026-10-27; before that assistant professor at Bologna until 2011). Ongoing. Covers the 2016-2018 papers that predate the first dated listing (2019).'))
    out.append(period(s, 'Pascal Frossard', '2003', None, TODAY, 'year', [
        ev('https://www.epfl.ch/labs/lts4/frossard', 'He is the founder and director of the LTS4 laboratory since 2003', 'faculty_start_statement', TODAY),
        ev(prof('pascal.frossard'), 'Pascal Frossard [email removed] +41 21 693 11 11 http://lts4.epfl.ch/frossard vCard Full Professor , Signal Processing Laboratory 4', 'faculty_profile', TODAY, 'live people.epfl.ch profile: appointment active as of this date')],
        'Start: founder and director of the LTS4 laboratory since 2003 (LTS4 lab page; SNSF professorship from 2003, tenure-track assistant professor 2006, associate 2013, full later). Ongoing (Full Professor on the live profile). Covers 2016-2018.'))
    out.append(period(s, 'Volkan Cevher', '2010-05-22', None, TODAY, 'day', [
        ev(WB + '20100522120004id_/http://people.epfl.ch:80/volkan.cevher', 'Volkan Cevher login Tenure-Track Assistant Professor Laboratory for Information and Inference Systems', 'faculty_start_lower_bound', '2010-05-22'),
        ev(WB + '20160120042143id_/http://people.epfl.ch:80/volkan.cevher', 'Postal address EPFL STI IEL LIONS ELE 233', 'dated_profile', '2016-01-20', 'profile still in his lab LIONS (no title shown on this page version)'),
        ev(prof('volkan.cevher'), 'Volkan Cevher [email removed] http://lions.epfl.ch vCard Full Professor , Laboratory for Information and Inference Systems', 'faculty_profile', TODAY, 'live people.epfl.ch profile: appointment active as of this date')],
        'Start is a LOWER BOUND: the earliest capture of his EPFL profile (2010-05-22) already names him Tenure-Track Assistant Professor heading LIONS (his own CV gives 2010, a PDF the store cannot show as text). Same profile in his lab in 2016; Full Professor on the live profile. Ongoing. Covers 2016-2018.'))
    out.append(period(s, 'Olaf Blanke', '2004', None, TODAY, 'year', [
        ev('https://en.wikipedia.org/wiki/Olaf_Blanke', 'He joined the EPFL in 2004 first as an assistant professor and has been full professor in neuroscience at EPFL since 2012.', 'faculty_start_statement', TODAY),
        ev(prof('olaf.blanke'), 'Olaf Blanke [email removed] vCard Full Professor , Foundation Bertarelli Chair in Cognitive Neuroprosthetics', 'faculty_profile', TODAY, 'live people.epfl.ch profile: appointment active as of this date')],
        'Start: joined EPFL in 2004 as assistant professor, full professor since 2012 (Wikipedia). Ongoing (Full Professor on the live profile). Covers 2016-2018.'))
    out.append(period(s, 'Ali H. Sayed', '2017-07-01', None, TODAY, 'day', [
        ev('https://actu.epfl.ch/news/ali-h-sayed-appointed-new-dean-of-the-school-of-en', 'Professors Pierre Vandergheynst and Andreas Mortensen will serve as deans ad interim until Professor Sayed takes up his duties on 1 July 2017.', 'appointment_announcement', TODAY),
        ev(prof('ali.sayed'), 'He served before as Distinguished Professor and Chair of Electrical Engineering at UCLA where he was a faculty member for over two decades during the period 1996-2021.', 'faculty_profile', TODAY, 'live profile; the UCLA appointment overlapped (leave) but his EPFL deanship and lab ran from 2017-07-01'),
        listing(s, 'Ali H. Sayed', 2019)],
        'Start: took up his duties as Dean of STI (with his Adaptive Systems Laboratory) on 1 July 2017 (EPFL news). Ongoing. 2016 and pre-July 2017 papers are UCLA-era and stay outside.'))
    out.append(period(s, 'Damir Filipovic', '2010', None, TODAY, 'year', [
        ev('https://en.wikipedia.org/wiki/Damir_Filipovi%C4%87', 'Since 2010, he has been the Swissquote Chair in Quantitative Finance and director of the Swiss Finance Institute at EPFL .', 'faculty_start_statement', TODAY),
        listing(s, 'Damir Filipovic', 2019)],
        'Start: Swissquote Chair in Quantitative Finance at EPFL since 2010 (Wikipedia; University of Vienna 2007-2010). Ongoing (listed every year 2019-2026). Covers 2016-2018.'))
    out.append(period(s, 'Daniel Gatica-Perez', '2014-10-26', None, TODAY, 'day', [
        ev(WB + '20141026230741id_/http://www.idiap.ch:80/~gatica/', "head, social computing group idiap research institute maitre d'enseignement et de recherche epfl", 'faculty_start_lower_bound', '2014-10-26'),
        ev(WB + '20160314080822id_/http://idiap.ch/~gatica/', 'professeur titulaire school of engineering & college of humanities ecole polytechnique federale de lausanne (epfl)', 'dated_profile', '2016-03-14'),
        listing(s, 'Daniel Gatica-Perez', 2019)],
        "Start is a LOWER BOUND: his own page captured 2014-10-26 already gives him as head of the Idiap Social Computing group and EPFL MER (Senior Scientist, counted as faculty-level in this review); professeur titulaire (adjunct professor) by 2016-03-14; listed every year 2019-2026. Ongoing. Covers 2016-2018."))
    out.append(period(s, 'François Fleuret', '2017-08-01', None, '2024-09-17', 'day', [
        ev(WB + '20170801104103id_/https://people.epfl.ch/francois.fleuret', "François Fleuret Maître d'enseignement et de recherche", 'faculty_start_lower_bound', '2017-08-01'),
        listing(s, 'François Fleuret', 2019), listing(s, 'François Fleuret', 2020)],
        'Start is a LOWER BOUND: his EPFL profile names him MER (Senior Scientist) in LIDIAP on 2017-08-01 (earlier captures 2014-01 show no title); Senior Scientist 2019, Adjunct Professor from 2020. No stated MER start found, so 2016 and Jan-Jul 2017 papers stay outside. Runs to his last dated listing (2024-09-17, asof).'))
    out.append(period(s, 'Francesco Mondada', '2013', None, TODAY, 'year', [
        ev('https://en.wikipedia.org/wiki/Francesco_Mondada', 'In 2013, EPFL appointed Mondada Adjunct Professor of Robotics.', 'faculty_start_statement', TODAY),
        ev(WB + '20181105231303id_/https://people.epfl.ch/francesco.mondada', 'Francesco Mondada Prof. Dr.', 'dated_profile', '2018-11-05'),
        ev(prof('francesco.mondada'), 'Francesco Mondada [email removed] vCard Adjunct Professor , SCI STI FMO1 Group', 'faculty_profile', TODAY, 'live people.epfl.ch profile: appointment active as of this date')],
        'Start: appointed Adjunct Professor of Robotics in 2013 (Wikipedia), the same rank he holds on the live profile and on every IC listing 2021-2026; his 2018-11-05 profile already gives Prof. Dr. Ongoing. Covers 2016-2020.'))
    out.append(period(s, 'Alexandre Alahi', '2017', None, TODAY, 'year', [
        ev(prof('alexandre.alahi'), 'Before joining EPFL in 2017, he spent multiple years at Stanford University as a Post-doc and Research Scientist.', 'faculty_start_statement', TODAY),
        listing(s, 'Alexandre Alahi', 2020)],
        'Start: joined EPFL in 2017 (live profile; no month stated, so year precision: 2017 papers stay unresolved, 2018 papers resolve). Tenure-track assistant professor by the 2020 listing; associate professor now. Ongoing.'))
    out.append(period(s, 'Florent Krzakala', '2020-09', None, TODAY, 'month', [
        ev('https://en.wikipedia.org/wiki/Florent_Krzakala', 'In September 2020, he was appointed Full Professor of Electrical Engineering and of Physics at EPFL , where he founded the laboratoire IdePHICS.', 'faculty_start_statement', TODAY),
        listing(s, 'Florent Krzakala', 2021), listing(s, 'Florent Krzakala', 2026)],
        'Start: Full Professor at EPFL from September 2020, founding IdePHICS (Wikipedia, citing the EPFL SB nomination news of 2020-10-07); ENS Paris before. Ongoing. Papers before September 2020 stay outside.'))
    out.append(period(s, 'Sarah Irene Brutton Kenderdine', '2017', None, TODAY, 'year', [
        ev('https://sarahkenderdine.info/bio-and-cv', 'In 2017, Sarah was appointed professor at the École Polytechnique fédérale de Lausanne (EPFL), Switzerland where she has built the Laboratory for Experimental Museology (eM+)', 'faculty_start_statement', TODAY),
        listing(s, 'Sarah Irene Brutton Kenderdine', 2019), listing(s, 'Sarah Irene Brutton Kenderdine', 2026)],
        'Start: appointed professor at EPFL in 2017, building eM+ (her bio; year precision). Ongoing. Covers 2018.'))
    out.append(no_change('Mathieu Salzmann', 'Left as is per the brief (start 2023 is correct).'))
    out.append(no_change('Marco Mattavelli', 'Unresolved: EPFL profiles of 2015-12 and 2017-08 put him at the head of his own MER unit SCI-STI-MM but show no title; no stated MER start or dated faculty-list capture with a title before 2019 was found. The live profile now gives Invited guest.'))
    return out


def mit():
    s, out = 'mit', []
    out.append(period(s, 'Dirk Englund', '2013-01', None, TODAY, 'month', [
        ev('https://mtlsites.mit.edu/news/archives/2013/02/englund_is_appo.html', 'Prof. Englund joined the MIT Electrical Engineering and Computer Science Department faculty in January 2013 as Assistant Professor of Electrical Engineering and Computer Science.', 'faculty_start_statement', '2013-02-07'),
        ev('https://en.wikipedia.org/wiki/Dirk_Englund', 'In 2013, he moved to Massachusetts Institute of Technology , where he is currently a Professor of Electrical Engineering and Computer Science.', 'faculty_profile', TODAY),
        listing(s, 'Dirk Englund', 2022), listing(s, 'Dirk Englund', 2026)],
        'Start: joined MIT EECS as assistant professor in January 2013 (MTL news, 2013-02-07); Columbia 2010-2013 before. Ongoing (EECS Professor, 2026 listing). Covers 2016-2021.'))
    out.append(period(s, 'William D. Oliver', '2015-07', None, TODAY, 'month', [
        ev('https://www.rle.mit.edu/professor-william-d-oliver-appointed-lincoln-laboratory-fellow/', 'Will was appointed a Professor of the Practice in the MIT Physics Department in July 2015.', 'faculty_start_statement', TODAY),
        listing(s, 'William D. Oliver', 2022), listing(s, 'William D. Oliver', 2026)],
        'Start: Professor of the Practice in MIT Physics from July 2015 (RLE news), leading the EQuS group (also Lincoln Laboratory staff until 2023); EECS/Physics professor later. Professor of the Practice is counted as a faculty appointment here, as for Kent Larson. Ongoing. Covers 2016-2021.'))
    out.append(period(s, 'Connor Wilson Coley', '2020-07', None, TODAY, 'month', [
        ev('https://alum.mit.edu/node/97802', 'as of July 2020, he is an assistant professor in the Department of Chemical Engineering.', 'faculty_start_statement', '2020-07-20'),
        listing(s, 'Connor Wilson Coley', 2026)],
        'Start corrected from 2021 (first catalog listing) to July 2020 (MIT alumni article of 2020-07-20). 2017-2019 papers are from his PhD/postdoc and stay outside. Ongoing.'))
    out.append(period(s, 'Neil Thompson', '2019', None, TODAY, 'year', [
        ev('https://futuretech.mit.edu/team/neil-thompson', 'Since founding MIT FutureTech in 2019', 'faculty_start_statement', TODAY),
        ev('https://futuretech.mit.edu/team/neil-thompson', 'Principal Research Scientist at MIT’s Computer Science and Artificial Intelligence Lab (CSAIL)', 'faculty_profile', TODAY, 'live FutureTech page: appointment active as of this date'),
        listing(s, 'Neil Thompson', 2019)],
        'Research-scientist PI (his census basis): CSAIL Research Scientist from the 2019 listing, founder/director of FutureTech since 2019, Principal Research Scientist now. Year precision (2019 is covered by the 2019 listing). Ongoing. Covers 2020-2025. His 2016-2017 Sloan years are not covered (no dated source captured).'))
    out.append(period(s, 'Justin Reich', '2017', None, TODAY, 'year', [
        ev(WB + '20190919073023id_/https://cmsw.mit.edu/medias-res-2017/', 'Assistant Professor Justin Reich and Professor Eric Klopfer both join us after time formally based in another MIT unit', 'appointment_announcement', '2019-09-19', 'CMS/W 2017 newsletter (Medias Res 2017) welcoming new faculty for 2017-18; captured 2019'),
        listing(s, 'Justin Reich', 2019), listing(s, 'Justin Reich', 2026)],
        'Start corrected from 2019 to 2017: the CMS/W 2017 newsletter welcomes Assistant Professor Justin Reich (previously research staff in another MIT unit). No month stated, so year precision: 2018 papers resolve, 2016-2017 stay outside. Ongoing.'))
    out.append(period(s, 'Luca Carlone', '2018-01', None, TODAY, 'month', [
        ev('https://www.mit.edu/~lids/news-and-events/news/luca-carlone-join-mit-faculty-be-part-lids-principal-investigator.html', 'Luca Carlone, currently a Research Scientist at LIDS, will be joining the MIT department of Aeronautics and Astronautics, as an Assistant Professor', 'appointment_announcement', '2017-06-01'),
        ev('https://lucacarlone.mit.edu/mit-appointment/', 'I’ll start as Assistant Professor in the Department of Aeronautics and Astronautics at MIT this Fall!', 'appointment_announcement', '2017-07-29'),
        listing(s, 'Luca Carlone', 2019)],
        'Start corrected from 2019 to 2018-01: the LIDS announcement of 2017-06-01 gives the official assistant-professor appointment from January 2018 (his own post of 2017-07-29 says fall 2017; the later, official date is used). 2016-2017 papers are from his LIDS research-scientist years and stay outside. Ongoing.'))
    out.append(period(s, 'Ali Jadbabaie', '2016-07', None, TODAY, 'month', [
        ev('https://engineering.mit.edu/people/ali-jadbabaie-2', 'Ali Jadbabaie joined the MIT faculty as a full professor with dual appointments in the Department of Civil and Environmental Engineering and the Institute for Data, Systems, and Society in July 2016.', 'faculty_start_statement', TODAY)],
        'Start corrected from 2017 to July 2016 (MIT School of Engineering profile; interim SSRC director while still at Penn from 2014). Papers before July 2016 stay outside. Ongoing.'))
    out.append(period(s, 'Elchanan Mossel', '2016-07', None, TODAY, 'month', [
        ev('https://math.mit.edu/directory/profile.html?pid=1844', 'Mossel joined the faculty of the MIT Mathematics Department as a full professor in July 2016', 'faculty_start_statement', TODAY)],
        'Start corrected from 2017 to July 2016 (MIT Mathematics directory; Wharton leave 2014-2016 before). Papers before July 2016 stay outside. Ongoing.'))
    out.append(period(s, 'Alexander Rakhlin', '2018-01-15', None, TODAY, 'day', [
        ev('https://www.mit.edu/~lids/news-and-events/news/prof-alexander-sasha-rakhlin-join-mit-faculty-and-lids-principal-investigator.html', 'will be joining the MIT faculty through the Institute for Data, Systems, and Society (IDSS) and the Department of Brain and Cognitive Sciences (BCS), beginning January 15, 2018.', 'appointment_announcement', '2018-01-02')],
        'Start corrected from 2019 to 2018-01-15 (LIDS announcement of 2018-01-02; visiting professor before, Penn until 2018-01). 2017 papers stay outside. Ongoing.'))
    out.append(period(s, 'Fadel Adib', '2017-01-27', None, TODAY, 'day', [
        ev('https://news.mit.edu/2017/fadel-adib-joins-media-lab-faculty-0127', 'Fadel Adib has joined the Media Lab faculty to head the new research group Signal Kinetics.', 'appointment_announcement', '2017-01-27'),
        listing(s, 'Fadel Adib', 2019), listing(s, 'Fadel Adib', 2026)],
        'Start is a LOWER BOUND: MIT News of 2017-01-27 reports he has joined the Media Lab faculty (assistant professor) heading Signal Kinetics; exact start not stated. 2016 papers (PhD) stay outside. Ongoing.'))
    for pi, why in [
        ('Suvrit Sra', 'Rejected 2016-2017 papers are from his LIDS principal-research-scientist years; the EECS faculty listing starts 2018 (assistant professor), so no faculty start before 2018 is supported.'),
        ('Roger Mark', 'Unresolved/departure: last dated listing as active faculty is 2019; he was Professor Emeritus of IMES and EECS (PhysioNet notice, 2026-07-16); no source dates the emeritus transfer, so 2020-2026 stay outside.'),
        ('Vincent Sitzmann', 'Faculty start 2022-07 stands: rejected 2021 and early-2022 papers are from his MIT postdoc.'),
        ('Marzyeh Ghassemi', 'Faculty start 2021-07 stands: 2016-2020 papers are from her MIT PhD/postdoc and Toronto faculty years.'),
        ('Mohsen Ghaffari', 'Faculty start 2022-04 stands: 2016-2020 papers are from his MIT PhD and ETH Zurich faculty years.'),
        ('Anand V Natarajan', 'Faculty start 2020-09 stands: 2016-2019 papers are from his MIT PhD and Caltech postdoc.'),
        ('Roger Levy', 'Joined BCS in 2016 (MIT Faculty Newsletter) but no month found; a year-only start cannot admit any 2016 paper, so the existing start (2017) is kept.')]:
        out.append(no_change(pi, why))
    return out


def cmu():
    s, out = 'cmu', []
    out.append(period(s, 'Ryan Tibshirani', '2011', '2022', None, 'year', [
        ev('https://www.stat.berkeley.edu/~ryantibs/', 'From 2011-2022, I was a faculty member in Statistics and Machine Learning at Carnegie Mellon University.', 'faculty_start_statement', TODAY),
        listing(s, 'Ryan Tibshirani', 2016), listing(s, 'Ryan Tibshirani', 2017)],
        'CMU faculty (Statistics and MLD) 2011-2022 per his own page; assistant professor on the 2016-2017 MLD core-faculty lists; moved to UC Berkeley in 2022. Year precision both ends. Covers 2018-2021. His 2022-2025 MLD listings are as Adjunct Faculty (after the move).', endPrecision='year'))
    for pi, why in [
        ('Jason Li', 'Verified and left: rejected 2017-2022 papers are from his CMU PhD and pre-faculty years; CSD assistant professor from the 2023 cohort.'),
        ('Diana Marculescu', 'Departure confirmed (prior review): UT Austin chair from 2019-12-01; 2020-2023 stay outside.'),
        ('Jeyanandh Paramesh', 'Departure confirmed (prior review): regular ECE appointment ended in 2019 (Adjunct by 2019-09-19).'),
        ('Chenyan Xiong', 'Rejected 2018-2022 papers are from his Microsoft Research years; CMU faculty from 2023 (listing). NOTE: his 2016-2017 listings are LTI PhD-student directory rows, not faculty listings.'),
        ('Sauvik Das', 'Rejected 2018 and 2021 papers fall in his Georgia Tech years. NOTE: his 2016-2017 listings are HCII PhD-student rows.'),
        ('Kayvon Fatahalian', 'Rejected 2020-2021 papers are from Stanford (left CMU); his 2022-2024 CSD rows are Adjunct Faculty.'),
        ('Wenshan Wang', 'Unresolved: Postdoctoral Fellow on the 2018-2019 RI lists, Systems Scientist from 2023; no dated source for the move to Systems Scientist (2020-2022) was found.'),
        ('Jonathan Francis', 'Unresolved: 2019-2021 rows are LTI PhD-student listings; he is RI Courtesy Faculty from 2025; no faculty start in 2022-2024 was found.'),
        ('Anthony Stentz', 'Unresolved (2 papers): Research Professor through 2019, Courtesy Faculty from 2025; no source for 2021-2022.'),
        ('George D Stetten', 'Unresolved (1 paper): RI Research Professor 2016-2017, Courtesy Faculty 2025-2026; no 2018 source.')]:
        out.append(no_change(pi, why))
    return out


def princeton():
    out = []
    for pi, why in [
        ('Pravesh Kothari', 'Rejected 2017-2021 papers are from his Princeton/IAS postdoc (research instructor) and CMU faculty years; Princeton faculty appointment starts January 1, 2024 (CS faculty page 2023).'),
        ('Matias D. Cattaneo', 'Unresolved: trustees give summer 2019 without a day/month and no 2019 ORFE capture was found, so 2019 papers stay at year precision.'),
        ('Huacheng Yu', 'Rejected 2017-2020 papers are from his Harvard postdoc and Princeton associate-research-scholar years (2019-2021); CS faculty from 2021.'),
        ('Nick Feamster', 'Departure confirmed: left for the University of Chicago in 2019 (period ends 2019-06); 2020 and 2022 papers stay outside.'),
        ('Mung Chiang', 'Departure confirmed: Purdue dean from July 2017 (period ends 2017). NOTE: his 2019-2026 ECE rows are under "Visiting Faculty" and currently admit post-departure years.'),
        ('Daniel I. Rubenstein', 'Departure confirmed: emeritus from 2023-07-01; 2026 papers stay outside.')]:
        out.append(no_change(pi, why))
    return out


def berkeley():
    s, out = 'berkeley', []
    out.append(period(s, 'Jan M. Rabaey', '1987', '2019', None, 'year', [
        ev('https://www.janrabaey.com/about', 'in 1987, he joined the faculty of the Electrical Engineering and Computer Science department of the University of California, Berkeley', 'faculty_start_statement', TODAY),
        ev('https://www.janrabaey.com/about', 'He became Professor Emeritus and Professor in the Graduate School in 2019.', 'emeritus_transfer', TODAY),
        listing(s, 'Jan M. Rabaey', 2017)],
        'EECS faculty from 1987; Professor Emeritus and Professor in the Graduate School in 2019 (his bio). Year-precision end 2019: covers 2018 (between the 2017 Professor listing and the 2019 emeritus listing); 2019+ only via same-year listings.', endPrecision='year'))
    out.append(period(s, 'David Bamman', '2015', None, TODAY, 'year', [
        ev('https://www.ischool.berkeley.edu/news/2015/new-professor-david-bamman-scholar-computational-humanities-and-social-sciences', 'is joining the Berkeley School of Information this fall as an assistant professor.', 'appointment_announcement', '2015-09-01'),
        ev('https://www.ischool.berkeley.edu/people/david-bamman', 'David Bamman Associate Professor [email removed]', 'faculty_profile', TODAY, 'live I School profile: appointment active as of this date'),
        listing(s, 'David Bamman', 2019), listing(s, 'David Bamman', 2026)],
        'Start: joined the I School as assistant professor in fall 2015 (I School news, 2015-09-01); EECS lists him (Below The Line) from 2019. Ongoing. Covers 2016-2018.'))
    for pi, why in [
        ('Zuo-Jun Max Shen', 'Departure confirmed: joined HKU in 2021 (Vice-President Research, approved 2020-10-27); 2023-2025 papers stay outside.'),
        ('Jean Walrand', 'Unresolved: Professor on 2017-11-01, Professor Emeritus by 2019-07-15; no source dates the retirement, so 2018 is not bridged.'),
        ('Marta C. González', 'Unresolved: Berkeley start is 2018 on her CV (PDF, not text-capturable) and 2019 on the MIT profile; no dated 2018 Berkeley listing captured.'),
        ('Angjoo Kanazawa', 'Rejected 2017-2019 papers are from her BAIR postdoc years; faculty from the 2020 listing (Berkeley News new-faculty profile 2020-11-30).'),
        ('Shmuel Oren', 'Retirement: Professor of the Graduate School (recalled emeritus) after 2018; 2019-2025 stay outside.')]:
        out.append(no_change(pi, why))
    return out


if __name__ == '__main__':
    for school in sys.argv[1:]:
        res = globals()[school]()
        f = HERE / f'proposals/{school}-followup.json'
        json.dump(res, open(f, 'w'), indent=1, ensure_ascii=False)
        print(school, sum(e['verdict'] == 'period' for e in res), 'periods,', sum(e['verdict'] == 'no_change' for e in res), 'no_change ->', f)
