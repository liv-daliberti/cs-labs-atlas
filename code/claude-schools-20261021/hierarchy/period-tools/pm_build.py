"""Build proposals/princeton.json and proposals/mit.json for the 2026-10-26 appointment-period review.
Every new evidence item is built with pcap.ev (the quote is verified against the stored capture); kept existing
evidence items are copied from hierarchy/<school>/pis.json unchanged."""
import json, sys
sys.path.insert(0, '/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy/period-tools')
import pcap

H = '/n/fs/resemble/maxent-grpo/.research-sweeps/claude-schools-20261021/hierarchy'
TODAY = '2026-10-26'
WB = 'https://web.archive.org/web/'
import unicodedata


def ev(url, quote, kind, observed, note=None):
    """pcap.ev, retrying with the quote in NFD/NFC form (some captures store decomposed accents)."""
    for q in (quote, unicodedata.normalize('NFD', quote), unicodedata.normalize('NFC', quote)):
        if pcap.quote_ok(url, ' '.join(q.split())):
            return pcap.ev(url, q, kind, observed, note)
    return pcap.ev(url, quote, kind, observed, note)

# Wayback captures and live pages used below
NEWS_2018_10 = WB + '20260610035807id_/https://www.princeton.edu/news/2018/10/12/board-approves-22-faculty-appointments'
NEWS_2018_07 = WB + '20250616132319id_/https://www.princeton.edu/news/2018/07/02/board-approves-11-faculty-appointments'
NEWS_2019_01 = WB + '20260512025556id_/https://www.princeton.edu/news/2019/01/31/trustees-approve-two-faculty-appointments'
NEWS_2017_06_29 = WB + '20260120034319id_/https://www.princeton.edu/news/2017/06/29/board-trustees-approves-18-faculty-appointments'
NEWS_2017_05 = WB + '20260515225422id_/https://www.princeton.edu/news/2017/05/09/board-trustees-approves-14-faculty-appointments'
NEWS_2014_10 = WB + '20260505181846id_/https://www.princeton.edu/news/2014/10/08/board-approves-20-appointments-princeton-faculty'
NEWS_2020_05 = WB + '20251212134646id_/https://www.princeton.edu/news/2020/05/26/four-faculty-members-honored-excellence-mentoring-graduate-students'
RESIGN_2017_06 = WB + '20260609061203id_/https://www.princeton.edu/news/2017/06/30/faculty-members-submit-resignations'
RESIGN_2017_09 = WB + '20260511120120id_/https://www.princeton.edu/news/2017/09/29/faculty-members-submit-resignations'
RESIGN_2020_06 = WB + '20260418140634id_/https://www.princeton.edu/news/2020/06/16/faculty-members-submit-resignations'
EMERITUS_2023 = WB + '20260315052028id_/https://www.princeton.edu/news/2023/08/16/thirteen-faculty-members-transfer-emeritus-status'
CBE_KEV = WB + '20260107120744id_/https://cbe.princeton.edu/news/kevrekidis-retire-and-move-johns-hopkins-university'
WIKI_KEV = 'https://en.wikipedia.org/wiki/Yannis_Kevrekidis'
WIKI_COHEN = 'https://en.wikipedia.org/wiki/Jonathan_D._Cohen'
WIKI_YARIV = 'https://en.wikipedia.org/wiki/Leeat_Yariv'
WIKI_CATTANEO = 'https://en.wikipedia.org/wiki/Matias_D._Cattaneo'
WIKI_SONER = 'https://en.wikipedia.org/wiki/Halil_Mete_Soner'
FLINN = 'https://www.flinn.org/scholar-alum-receives-national-accolades-for-neuroscience-research/'
TOETT_BIO = WB + '20260102035915id_/https://toettcherlab.scholar.princeton.edu/bio'
EEB_FEST = WB + '20250715010938id_/https://eeb.princeton.edu/news/festschrift-honoring-daniel-rubensteins-43-years-service-eeb'
DOF_RUB = WB + '20241217093645id_/https://dof.princeton.edu/people/daniel-rubenstein'
YARIV_CV = WB + '20221007215649id_/http://www.leeatyariv.com/cv.htm'
YARIV_HOME = WB + '20180417172200id_/http://www.leeatyariv.com/'
YALE_NTB = 'https://medicine.yale.edu/profile/nicholas-turk-browne'
WTI_NTB = 'https://wti.yale.edu/index.php/profile/nick-turk-browne'
ENG_TANGPI = WB + '20260512221747id_/https://engineering.princeton.edu/news/2022/02/25/mathematician-casts-new-models-of-uncertainty-for-a-changing-world'
NU_RACZ = 'https://mccormick.northwestern.edu/computer-science/news-events/news/articles/2022/northwestern-cs-welcomes-new-tenure-track-faculty-members.html'
RACZ_HOME = 'https://racz.statistics.northwestern.edu/'
RACZ_TEACH = 'https://racz.statistics.northwestern.edu/teaching.html'
MULVEY_2000 = WB + '20000816051705id_/http://www.princeton.edu:80/~mulvey/'
MULVEY_2026 = WB + '20260226073937id_/https://orfe.princeton.edu/people/john-mulvey'
SIRCAR_2001 = WB + '20010213221605id_/http://www.princeton.edu:80/~sircar/'
SIRCAR_2026 = WB + '20260124143524id_/https://orfe.princeton.edu/people/ronnie-sircar'
CS_LEVY = 'https://www.cs.princeton.edu/people/profile/aalevy'
CS_LIST_2025 = WB + '20250123195629id_/https://www.cs.princeton.edu/people/faculty'
ORFE_2026 = WB + '20260208113232id_/https://orfe.princeton.edu/people/faculty'
PSYCH_2026 = WB + '20260331160752id_/https://psych.princeton.edu/people/faculty'
PSYCH_ASSOC_2026 = WB + '20260331160756id_/https://psych.princeton.edu/people/associated-faculty'
LSI_2026 = WB + '20260317022857id_/https://lsi.princeton.edu/people/associated-faculty'
DP_VERDU = WB + '20260817131713id_/http://www.dailyprincetonian.com/article/2018/09/verdu-dismissed'
PAW_VERDU = WB + '20251114093445id_/https://paw.princeton.edu/article/professor-dismissed-misconduct-penalty-toughened'
PAW_GOLD = WB + '20260420224835id_/https://paw.princeton.edu/article/engineering-dean-goldsmith-leaving-presidency-stony-brook'
GLI_GOLD = 'https://greaterlongisland.com/renowned-engineer-andrea-goldsmith-to-lead-stony-brook-university/'
SBU_GOLD = 'https://www.stonybrook.edu/pres/about/bio.html'
CUFF_BIO = WB + '20240918054623id_/http://www.princeton.edu:80/~cuff/bio.html'
ABBE_BIO = WB + '20260609153505id_/https://web.math.princeton.edu/~eabbe/bio.html'

# MIT
MIT_NEWS_2025 = 'https://news.mit.edu/2025/mit-schwarzman-college-computing-welcomes-new-faculty-1017'
NIGAM_BIO = 'https://people.csail.mit.edu/rachit/full-bio'
KH_2025_05 = WB + '20250506181245id_/https://omarkhattab.com/'
KH_2025_07 = WB + '20250703122926id_/https://omarkhattab.com/'
KH_LIVE = 'https://omarkhattab.com/'
JB_2026_04 = WB + '20260410155545id_/https://jasbrooks.net/'
JB_LIVE = 'https://jasbrooks.net/'
EECS_JB = 'https://www.eecs.mit.edu/people/jas-brooks/'
CSAIL_2026 = (WB + '20260917151324id_/https://www.csail.mit.edu/api-proxy/angular-solr?_api_proxy_uri=people&q=*%3A*&rows=216&start=0'
              '&fq%5B%5D=ss_name%3A%22Principal%20Investigators%22%20OR%20ss_name%3A%22Researchers%22%20OR%20ss_name%3A%22Principal'
              '%20Investigators%22%20OR%20ss_name%3A%22Core%2FDual%22%20OR%20ss_name%3A%22Associates%22%20OR%20ss_name%3A%22Emeritus%22')
STEALTH_2016 = WB + '20160825213412id_/http://stealth.csail.mit.edu/people.html'
STEALTH_2018 = WB + '20180116182216id_/http://groups.csail.mit.edu/EVO-DesignOpt/STEALTHCSec/people.html'
CSAIL_HEMBERG_2018 = WB + '20180406140116id_/https://www.csail.mit.edu/person/erik-hemberg'
ALFA_2019 = WB + '20190223075609id_/https://alfagroup.csail.mit.edu/people'

P = {p['pi']: p for p in json.load(open(f'{H}/princeton/pis.json'))}


def existing(pi, pid):
    for per in P[pi]['periods']:
        if per['id'] == pid:
            return per
    raise KeyError(pid)


def keep(pi, pid, url_sub):
    """An evidence item of an existing period, unchanged."""
    return [e for e in existing(pi, pid)['evidence'] if url_sub in e['url']]


def period(start, end, asof, prec, evidence, note, end_prec=None):
    d = dict(start=start, end=end, asof=asof, datePrecision=prec, evidence=evidence, note=note)
    if end_prec:
        d['endPrecision'] = end_prec
    return d


def entry(pi, pid, verdict, per=None, departure=None, why=None, extra=None):
    e = {'pi': pi, 'existing_period_id': pid, 'verdict': verdict, 'period': per, 'departure': departure, 'why': why}
    if extra:
        e['departure_evidence'] = extra
    return e


princeton = []

# Amit Levy: site period princeton_faculty_period_44 has start null, end 2025
princeton.append(entry('Amit Levy', 'princeton_faculty_period_44', 'period', period(
    '2018', '2025', None, 'year',
    [ev(NEWS_2018_10, 'Amit Levy , in computer science , joined the faculty this fall. He comes to Princeton from the Stanford Information Networks Group.',
        'appointment_announcement', '2026-06-10', 'Princeton Office of Communications, Oct. 12, 2018 (Board approves 22 faculty appointments)'),
     ev(CS_LEVY, 'Amit Levy is a Visiting Research Scholar. He was an assistant professor of computer science at Princeton until 2025.',
        'faculty_end_statement', TODAY, 'live CS profile, headed "Amit Levy (on leave)"'),
     ev(CS_LIST_2025, 'Amit Levy Assistant Professor', 'dept_listing:Computer Science', '2025-01-23', 'last dated listing as assistant professor')],
    'Start: the trustees announcement of Oct. 12, 2018 says he joined the faculty in fall 2018 (no month given, so year precision). '
    'End: the department profile states he was an assistant professor until 2025 and is now a Visiting Research Scholar (a visiting role, '
    'not a faculty appointment); 2026 papers stay outside. The end is year-only: no resignation notice with an effective date was found.'),
    departure='Assistant professorship ended in 2025 (CS profile: "assistant professor of computer science at Princeton until 2025"; now Visiting Research Scholar, profile marked on leave).'))

# Sergio Verdu: genuine departure (dismissed 2018-09-24)
princeton.append(entry('Sergio Verdú', None, 'no_change', departure='Dismissed from the Princeton faculty as of 2018-09-24 (trustees approved Sept. 22, 2018).',
    why='Rejected 2019 papers postdate the dismissal; listings already cover 2016-2018. Nothing to add.',
    extra=[ev(DP_VERDU, "professor Sergio Verdú was dismissed from the faculty as of Sept. 24 following a University investigation",
              'departure_announcement', '2026-08-17', 'Daily Princetonian, Sept. 29, 2018'),
           ev(PAW_VERDU, 'Electrical engineering professor Sergio Verdú, a faculty member for 34 years, was dismissed from the faculty as of Sept. 24',
              'departure_announcement', '2025-11-14', 'Princeton Alumni Weekly, Oct. 12, 2018')]))

# Emmanuel Abbe: resigned effective 2020-09-01 for EPFL
princeton.append(entry('Emmanuel Abbe', None, 'no_change', departure='Resigned from Princeton effective 2020-09-01 to accept a position at EPFL.',
    why='Rejected 2021 paper postdates the resignation; listings cover 2016-2020. Nothing to add.',
    extra=[ev(RESIGN_2020_06, 'Emmanuel Abbe, associate professor of electrical engineering and applied and computational mathematics, to accept a position at École Polytechnique Fédérale de Lausanne (effective Sept. 1, 2020)',
              'departure_announcement', '2026-04-18', 'Princeton Office of Communications, June 16, 2020'),
           ev(ABBE_BIO, 'He joined Princeton University as an assistant professor in 2012 and became associate professor in 2016',
              'faculty_start_statement', '2026-06-09')]))

# Andrea Goldsmith: left to be president of Stony Brook, 2025-08-01
princeton.append(entry('Andrea Goldsmith', None, 'no_change', departure='Left Princeton to become president of Stony Brook University, effective 2025-08-01.',
    why='Rejected 2026 papers postdate her departure; listings cover 2020-2025. Nothing to add.',
    extra=[ev(PAW_GOLD, 'Engineering dean Andrea Goldsmith will leave Princeton to become the president of Stony Brook University. The State University of New York Board of Trustees announced her appointment on Feb. 19, and Goldsmith will begin her new role on Aug. 1.',
              'departure_announcement', '2026-04-20', 'Princeton Alumni Weekly, 2025'),
           ev(GLI_GOLD, 'The State University of New York (SUNY) Board of Trustees unanimously approved the appointment of Goldsmith, who will take the helm on Aug. 1.',
              'departure_announcement', TODAY),
           ev(SBU_GOLD, 'She served as dean of engineering and applied science at Princeton University for five years',
              'new_employer_profile', TODAY, 'Stony Brook presidential bio')]))

# Paul Cuff: resigned effective 2017-09-01 for Renaissance Technologies
princeton.append(entry('Paul Cuff', None, 'no_change', departure='Resigned effective 2017-09-01 to join Renaissance Technologies.',
    why='Rejected 2018, 2019 and 2023 papers postdate the resignation; listings cover 2016-2017. Nothing to add.',
    extra=[ev(RESIGN_2017_09, 'Paul Cuff , assistant professor of electrical engineering, to accept a position at Renaissance Technologies, effective Sept. 1.',
              'departure_announcement', '2026-05-11', 'Princeton Office of Communications, Sept. 29, 2017'),
           ev(CUFF_BIO, 'I joined the faculty at Princeton University in September of 2009.', 'faculty_start_statement', '2024-09-18'),
           ev(CUFF_BIO, 'In September of 2017, I left Princeton to join the general research group at Renaissance Technologies.',
              'departure_statement', '2024-09-18')]))

# Matias D. Cattaneo
princeton.append(entry('Matias D. Cattaneo', None, 'period', period(
    '2019', None, TODAY, 'year',
    [ev(NEWS_2019_01, 'The Princeton University Board of Trustees has approved the appointment of two full professors, effective in summer 2019. Matias Cattaneo , in operations research and financial engineering, will join the faculty from the University of Michigan',
        'appointment_announcement', '2026-05-12', 'Princeton Office of Communications, Jan. 31, 2019'),
     ev(WIKI_CATTANEO, 'From 2008 to 2019, Cattaneo taught at the University of Michigan . He joined Princeton University as a Professor in the Department of Operations Research and Financial Engineering in 2019.',
        'faculty_start_statement', TODAY),
     ev(WIKI_CATTANEO, 'He later moved to the Department of Economics in 2026.', 'faculty_profile', TODAY, 'still a Princeton professor (economics) as of 2026'),
     ev(ORFE_2026, 'Matias Cattaneo Professor', 'dept_listing:Operations Research and Financial Engineering', '2026-02-08')],
    'Start: appointment effective "summer 2019" per the trustees (no month stated), so year precision; 2018 papers predate the appointment, '
    '2019 papers stay unresolved at year precision. Ongoing: ORFE listing Feb 2026; Wikipedia reports a 2026 move to Princeton Economics (same school).')))

# Miklos Racz
princeton.append(entry('Miklos Racz', None, 'period', period(
    '2017-09', '2022-12', None, 'month',
    [ev(NEWS_2017_06_29, 'cz , in operations research and financial engineering , will join the faculty in summer 2017 from his role as postdoctoral researcher with Microsoft Research.',
        'appointment_announcement', '2026-01-20', 'Princeton Office of Communications, June 29, 2017 (name rendered "Mikl ó s R á cz" in the capture)'),
     ev(RACZ_TEACH, 'At Princeton University Fall 2021: ORF 526 (Probability Theory) Course webpage Fall 2020: ORF 526 (Probability Theory) Course webpage Fall 2019: ORF 526 (Probability Theory) Course webpage Fall 2018: ORF 526 (Probability Theory) Course webpage Fall 2017: ORF 526 (Probability Theory)',
        'faculty_teaching_record', TODAY, 'first Princeton course Fall 2017'),
     ev(NU_RACZ, 'Miklos Z. Racz will start in January 2023 as an assistant professor of computer science with a joint appointment in the Department of Statistics and Data Science',
        'departure_announcement', TODAY, 'Northwestern CS news, Sep 14, 2022'),
     ev(NU_RACZ, 'He joins Northwestern from Princeton University, where he served as assistant professor of operations research and financial engineering',
        'departure_announcement', TODAY),
     ev(RACZ_HOME, 'Before joining Northwestern, I was an assistant professor at Princeton University in the ORFE Department', 'departure_statement', TODAY)],
    'Start: trustees say he joined in summer 2017 (no month); 2017-09 is used as a conservative month (he taught ORF 526 in Fall 2017), so '
    'papers from July-August 2017 stay outside. End: Northwestern announced (Sep 2022) that he starts there in January 2023 coming from '
    'Princeton, so the Princeton appointment is taken to end in 2022-12 (no Princeton resignation notice with an effective date was found). '
    '2023 papers are after the departure and stay rejected.', end_prec='month'),
    departure='Left Princeton for Northwestern University (assistant professor of CS and Statistics and Data Science from January 2023).'))

# Jonathan D. Cohen
princeton.append(entry('Jonathan D. Cohen', None, 'period', period(
    '1998', None, '2026-03-31', 'year',
    [ev(WIKI_COHEN, 'He originally joined the faculty of Princeton in 1998 and became the founding director of the Center for the Study of Brain, Mind, and Behavior in 2000.',
        'faculty_start_statement', TODAY),
     ev(PSYCH_2026, 'Jonathan Cohen Robert Bendheim and Lynn Bendheim Thoman Professor in Neuroscience', 'dept_listing:Psychology', '2026-03-31')],
    'Start: joined the Princeton faculty in 1998 (Wikipedia statement). Ongoing: Psychology faculty listing March 2026. The 2016 papers fall inside.')))

# Jonathan W. Pillow
princeton.append(entry('Jonathan W. Pillow', None, 'period', period(
    '2014-09', None, '2026-03-31', 'month',
    [ev(FLINN, 'this month is starting a new position as an assistant professor in the Princeton Neuroscience Institute at Princeton University',
        'appointment_announcement', TODAY, 'Flinn Foundation article dated September 12, 2014'),
     ev(PSYCH_ASSOC_2026, 'Jonathan Pillow Professor Princeton Neuroscience Institute', 'dept_listing:Psychology (associated faculty)', '2026-03-31')],
    'Start: a Flinn Foundation article dated Sept. 12, 2014 says he was starting as assistant professor at PNI that month (Wikipedia: UT Austin 2009-2014). '
    'Ongoing: Psychology associated-faculty listing March 2026.')))

# Ileana M. Cristea
princeton.append(entry('Ileana M. Cristea', None, 'period', period(
    '2008', None, '2026-03-17', 'year',
    [ev(NEWS_2020_05, 'Ileana Cristea joined the Princeton faculty in 2008.', 'faculty_start_statement', '2025-12-12', 'Princeton Office of Communications, May 26, 2020'),
     ev(LSI_2026, 'Ileana M. Cristea Henry L. Hillman Professor of Molecular Biology Molecular Biology', 'dept_listing:Lewis-Sigler Institute for Integrative Genomics', '2026-03-17')],
    'Start: joined the Princeton faculty in 2008 (university news statement). Ongoing: LSI associated-faculty listing March 2026.')))

# Jared Toettcher
princeton.append(entry('Jared Toettcher', None, 'period', period(
    '2015', None, '2026-03-17', 'year',
    [ev(NEWS_2014_10, 'Jared Toettcher, in molecular biology, will join the faculty at the end of the fall term from UC-San Francisco, where he has been a postdoctoral fellow since 2009.',
        'appointment_announcement', '2026-05-05', 'Princeton Office of Communications, Oct. 8, 2014'),
     ev(TOETT_BIO, 'Jared Toettcher is an Associate Professor of Molecular Biology at Princeton University.', 'faculty_profile', '2026-01-02'),
     ev(LSI_2026, 'Jared Toettcher Associate Professor of Molecular Biology Molecular Biology', 'dept_listing:Lewis-Sigler Institute for Integrative Genomics', '2026-03-17')],
    'Start: the Oct. 2014 trustees announcement says he would join at the end of the fall term (fall term 2014-15 ends in January 2015), '
    'so 2015 at year precision. Ongoing: lab bio and LSI listing 2026.')))

# Daniel I. Rubenstein
princeton.append(entry('Daniel I. Rubenstein', None, 'period', period(
    '1980', '2023-06-30', None, 'year',
    [ev(EEB_FEST, 'A festschrift in honor of Daniel I. Rubenstein’s 43 years of service in the department of Ecology and Evolutionary Biology was held on October 2-3, 2023 at Princeton University.',
        'faculty_start_lower_bound', '2025-07-15', 'EEB news, Jan. 11, 2024; 43 years of service ending 2023 puts the start at about 1980'),
     ev(DOF_RUB, 'Daniel “Dan” Rubenstein transferred to emeritus status on July 1, 2023.', 'emeritus_transfer', '2024-12-17'),
     ev(EMERITUS_2023, 'Thirteen Princeton University faculty members were transferred to emeritus status in recent action by the Board of Trustees. Transfers are effective July 1, 2023, except where noted.',
        'emeritus_transfer', '2026-03-15', 'Princeton Office of Communications, Aug. 16, 2023'),
     ev(EMERITUS_2023, 'Daniel Rubenstein , the Class of 1877 Professor of Zoology and professor of ecology and evolutionary biology ;',
        'emeritus_transfer', '2026-03-15')],
    'Start: 43 years of departmental service by Oct 2023 (EEB festschrift) puts the start around 1980; any start before 2016 covers the 2016 papers. '
    'End: transferred to emeritus status effective July 1, 2023 (DOF profile and trustees news), so the appointment ends 2023-06-30. '
    'Emeritus years are not appointment years: 2026 papers stay rejected. Note the 2024 and 2025 EEB listings show him as "Emeritus, Senior Scholar".',
    end_prec='day'),
    departure='Transferred to emeritus status effective 2023-07-01.'))

# Leeat Yariv: existing override start 2017 is too early
princeton.append(entry('Leeat Yariv', 'override_period_princeton_leeat_yariv', 'period', period(
    '2018-01', None, TODAY, 'month',
    [ev(NEWS_2017_05, 'Leeat Yariv , in economics , will join the faculty in early 2018 from the California Institute of Technology, where she has taught since 2005. Yariv was a visiting professor at Princeton in 2016',
        'appointment_announcement', '2026-05-15', 'Princeton Office of Communications, May 9, 2017'),
     ev(YARIV_CV, '2017-2018 Princeton University , Department of Economics: Full Professor.', 'faculty_start_statement', '2022-10-07', 'academic year 2017-18'),
     ev(YARIV_CV, 'Fall 2016, 2017 Princeton University , Department of Economics: Visiting Professor.', 'prior_visiting_role', '2022-10-07',
        'fall 2017 was a visiting term, which does not count'),
     ev(YARIV_HOME, 'LEEAT YARIV Professor of Economics Department of Economics Princeton University', 'faculty_profile', '2018-04-17',
        'earliest dated statement of the professorship found'),
     ev(WIKI_YARIV, 'held positions at UCLA and Caltech prior to her move to Princeton in 2017', 'faculty_start_statement', TODAY,
        'kept from the existing period; contradicted on timing by the trustees release and her CV'),
     ev(WIKI_YARIV, 'Leeat Yariv ( Hebrew : ליאת יריב ) is the Uwe E. Reinhardt Professor of Economics at Princeton University', 'faculty_profile', TODAY)],
    'The existing period starts in 2017 on Wikipedia\'s "move to Princeton in 2017". The trustees release (May 2017) says she would join the faculty '
    'in early 2018, and her CV lists fall 2017 as a visiting professorship, with the full professorship in AY 2017-18. Together: the regular '
    'appointment began in early 2018 (spring term). The month is not stated; 2018-01 is used as the start of "early 2018" and the earliest '
    'independent dated statement is her homepage, captured 2018-04-17. The rejected 2017 paper falls in her visiting year and stays rejected. '
    'Ongoing: Wikipedia (fetched 2026-10-26) and the 2026 economics listing.')))

# Ioannis G. Kevrekidis: fix null start; keep the 2017 end (retired July 1, 2017, moved to JHU)
kpid = 'override_period_princeton_ioannis_g_kevrekidis'
princeton.append(entry('Ioannis G. Kevrekidis', kpid, 'period', period(
    '1986', '2017-06-30', None, 'year',
    [ev(WIKI_KEV, 'Kevrekidis joined Princeton University in 1986 as an assistant professor of engineering.', 'faculty_start_statement', TODAY),
     ev(CBE_KEV, "Professor Kevrekidis joined Princeton's chemical engineering faculty in 1986.", 'faculty_start_statement', '2026-01-07'),
     ev(CBE_KEV, 'Professor Yannis Kevrekidis will retire from the University effective July 1, 2017, with the titles of Pomeroy and Betty Perry Smith Professor in Engineering, Emeritus',
        'emeritus_transfer', '2026-01-07', 'CBE news, June 13, 2017'),
     ev(CBE_KEV, 'Following his retirement from Princeton, Yannis will be moving to a Bloomberg Distinguished Professorship at Johns Hopkins University.',
        'departure_announcement', '2026-01-07'),
     ev(WIKI_KEV, 'In 2007, he became the Pomeroy and Betty Perry Smith Professor of Engineering, a position which he held until 2017.', 'faculty_end_statement', TODAY)]
    + keep('Ioannis G. Kevrekidis', kpid, 'web.archive.org'),
    'Start: joined Princeton in 1986 (Wikipedia; CBE department news). End kept: retired from Princeton effective July 1, 2017 and moved to '
    'Johns Hopkins, so the appointment ends 2017-06-30; 2018-2022 papers stay rejected.', end_prec='day'),
    departure='Retired from Princeton effective 2017-07-01 (emeritus) and moved to a Bloomberg Distinguished Professorship at Johns Hopkins University.'))

# John M. Mulvey
princeton.append(entry('John M. Mulvey', None, 'period', period(
    '1978', None, '2026-02-26', 'year',
    [ev(MULVEY_2000, 'Princeton University 1978 to 1986 Assistant Professor', 'faculty_start_statement', '2000-08-16', 'own homepage, professional experience section'),
     ev(MULVEY_2026, 'John Mulvey Position Professor', 'faculty_profile', '2026-02-26'),
     ev(ORFE_2026, 'John Mulvey Professor', 'dept_listing:Operations Research and Financial Engineering', '2026-02-08')],
    'Start: his homepage (captured 2000) gives his Princeton career as assistant professor from 1978 (later associate professor) and professor from 1986. Ongoing: ORFE '
    'profile and listing 2026. The 2018-2019 gap was only a gap in listing captures.')))

# H. Mete Soner: existing start 2019 is right; month not stated
princeton.append(entry('H. Mete Soner', 'override_period_princeton_h_mete_soner', 'no_change',
    why='Existing start 2019 is correct: the trustees announced (Oct 2018) that he would join in summer 2019 from ETH Zurich, where he was '
        'professor 2009-2019. No source gives the month, so 2019 papers stay unresolved at year precision and 2018 papers predate the '
        'appointment. (Wikipedia also notes an earlier two-year Princeton professorship around 2000, outside the study window.)',
    extra=[ev(NEWS_2018_10, 'Halil Mete Soner , in operations research and financial engineering , will join the faculty in summer 2019 from ETH Zürich, where he has been a professor since 2009.',
              'appointment_announcement', '2026-06-10', 'Princeton Office of Communications, Oct. 12, 2018'),
           ev(ORFE_2026, 'Mete Soner Department Chair Norman John Sollenberger Professor', 'dept_listing:Operations Research and Financial Engineering', '2026-02-08')]))

# Nicholas B. Turk-Browne: fix null start; keep the 2017 end (resigned effective July 1, 2017 for Yale)
tpid = 'override_period_princeton_nicholas_b_turk_browne'
princeton.append(entry('Nicholas B. Turk-Browne', tpid, 'period', period(
    '2009', '2017-06-30', None, 'year',
    [ev(YALE_NTB, 'then served on the faculty at Princeton University from 2009-2017.', 'faculty_start_statement', TODAY, 'Yale School of Medicine profile'),
     ev(WTI_NTB, 'He started his lab in 2009 at Princeton University before returning to Yale in 2017.', 'faculty_start_statement', TODAY, 'Wu Tsai Institute profile'),
     ev(RESIGN_2017_06, 'Five faculty members have submitted their resignations, effective July 1.', 'departure_announcement', '2026-06-09',
        'Princeton Office of Communications, June 30, 2017'),
     ev(RESIGN_2017_06, 'Nicholas Turk-Browne , professor of psychology, to accept a position at Yale University.', 'departure_announcement', '2026-06-09')]
    + keep('Nicholas B. Turk-Browne', tpid, 'web.archive.org'),
    'Start: on the Princeton faculty from 2009 (Yale profiles; PhD Yale 2009). End kept: resignation to accept a position at Yale effective '
    'July 1, 2017, so the appointment ends 2017-06-30. The 2016 papers fall inside; 2018-2020 papers stay rejected.', end_prec='day'),
    departure='Resigned effective 2017-07-01 to accept a position at Yale University.'))

# Ludovic Tangpi: existing override start 2020 (first listing) is too late
princeton.append(entry('Ludovic Tangpi', 'override_period_princeton_ludovic_tangpi', 'period', period(
    '2018', None, '2026-02-08', 'year',
    [ev(NEWS_2018_07, 'Ludovic Tangpi Ndounkeu , in operations research and financial engineering , will join the faculty in fall 2018.',
        'appointment_announcement', '2025-06-16', 'Princeton Office of Communications, July 2, 2018'),
     ev(ENG_TANGPI, 'Tangpi joined Princeton in 2018 after completing a Ph.D. at Humboldt University of Berlin and a postdoctoral fellowship at the University of Vienna.',
        'faculty_start_statement', '2026-05-12', 'Princeton Engineering news, Feb. 25, 2022'),
     ev(ORFE_2026, 'Ludovic Tangpi Associate Professor Director of Graduate Studies', 'dept_listing:Operations Research and Financial Engineering', '2026-02-08')],
    'The existing start (2020) came from the first dated listing. The trustees (July 2018) say he would join in fall 2018 and Princeton '
    'Engineering states he joined in 2018. No month is stated, so 2019 papers are now covered and 2018 papers stay unresolved at year precision. '
    'Ongoing: ORFE listing Feb 2026.')))

# Ronnie Sircar
princeton.append(entry('Ronnie Sircar', None, 'period', period(
    '2001', None, '2026-02-08', 'year',
    [ev(SIRCAR_2001, 'Ronnie Sircar Operations Research & Financial Engineering Princeton University E-Quad Princeton, NJ 08544.', 'faculty_start_lower_bound', '2001-02-13',
        'own Princeton homepage captured Feb 2001'),
     ev(WB + '20250624220135id_/https://sircar.princeton.edu/short-bio/', 'He received his doctorate from Stanford University, and taught for three years at the University of Michigan in the Department of Mathematics.',
        'faculty_profile', '2025-06-24'),
     ev(SIRCAR_2026, 'Ronnie Sircar Position Eugene Higgins Professor of Operations Research & Financial Engineering', 'faculty_profile', '2026-01-24'),
     ev(ORFE_2026, 'Ronnie Sircar Eugene Higgins Professor of Operations Research & Financial Engineering', 'dept_listing:Operations Research and Financial Engineering', '2026-02-08')],
    'Start is a lower bound: no stated start was found; his Princeton ORFE homepage was captured in Feb 2001 (the bio adds three years at '
    'Michigan before Princeton and a junior-faculty award in 2003). Any start before 2016 covers the 2018 paper. Ongoing: ORFE profile and '
    'listing 2026. The 2018-2019 gap was only a gap in listing captures.')))

# ---------------- MIT ----------------
mit = []
mit.append(entry('Jas Brooks', None, 'period', period(
    '2026-07', None, TODAY, 'month',
    [ev(JB_2026_04, 'Excited to join MIT EECS / CSAIL as an Assistant Professor in July 2026!', 'appointment_announcement', '2026-04-10',
        'own homepage news item dated May 31, 2025'),
     ev(JB_2026_04, 'Jas Brooks is an incoming Assistant Professor at MIT EECS and CSAIL (starting Fall 2026).', 'appointment_announcement', '2026-04-10'),
     ev(JB_LIVE, 'Jas Brooks is an Assistant Professor and KDD Career Development Professor in Communications and Technology at MIT EECS', 'faculty_profile', TODAY)],
    'Start: own homepage (captured April 2026) announces joining MIT EECS/CSAIL as assistant professor in July 2026; still "incoming" in April 2026. '
    'The live page now gives the item as "Fall 2026". 2025 papers (PhD at UChicago, defended March 2025) predate the appointment. '
    'Ongoing: live homepage 2026-10-26.')))

mit.append(entry('Omar Khattab', None, 'period', period(
    '2025-07', None, TODAY, 'month',
    [ev(KH_2025_05, 'I’m a Research Scientist at Databricks. I start in Fall 2025 as an Assistant Professor at MIT EECS.', 'appointment_announcement', '2025-05-06'),
     ev(KH_2025_07, 'I’m an Assistant Professor at MIT EECS and CSAIL.', 'faculty_start_lower_bound', '2025-07-03'),
     ev(MIT_NEWS_2025, 'Omar Khattab is an assistant professor in EECS. He is also a member of CSAIL.', 'appointment_announcement', TODAY,
        'MIT News, Schwarzman College of Computing welcomes new faculty (Oct 2025)'),
     ev(KH_LIVE, 'I\'m an Assistant Professor at MIT EECS and a member of CSAIL', 'faculty_profile', TODAY),
     ev(CSAIL_2026, '"ss_name":"Core/Dual", "ss_field_title":"Assistant Professor", "ss_csail_room_map":"http://default/sites/default/files/resources/maps/8G/G818.gif", "ss_field_room":"32-G818", "ss_title":"Omar Khattab"',
        'dept_listing:CSAIL', '2026-09-17')],
    'Start: his homepage still said Databricks research scientist, starting at MIT in Fall 2025, on 2025-05-06, and said "I\'m an Assistant '
    'Professor at MIT EECS and CSAIL" on 2025-07-03, so the appointment began between those dates (very likely July 1, 2025). 2025-07 is '
    'used, which leaves papers before July 2025 outside. Ongoing: CSAIL directory Sept 2026 and live homepage.')))

mit.append(entry('Rachit Nigam', None, 'period', period(
    '2026-01', None, '2026-09-17', 'month',
    [ev(MIT_NEWS_2025, 'Rachit Nigam will join EECS as an assistant professor in January 2026.', 'appointment_announcement', TODAY,
        'MIT News, Schwarzman College of Computing welcomes new faculty (Oct 2025)'),
     ev(NIGAM_BIO, 'I am starting as an assistant professor in the Department of Electrical Engineering and Computer Science at the Massachusetts Institute of Technology in 2025-26 academic year.',
        'appointment_announcement', TODAY),
     ev(CSAIL_2026, '"ss_name":"Core/Dual", "ss_field_title":"Assistant Professor", "ss_title":"Rachit Nigam"', 'dept_listing:CSAIL', '2026-09-17')],
    'Start: MIT News (Oct 2025) says he joins EECS as assistant professor in January 2026. Earlier he was a visiting scholar at MIT and a '
    'Cornell PhD student, which do not count; the 2024 paper stays rejected. Ongoing: CSAIL directory Sept 2026.')))

mit.append(entry('Erik Hemberg', None, 'period', period(
    '2018-01-16', None, '2026-09-17', 'day',
    [ev(STEALTH_2016, 'Erik Hemberg, PhD is a Post Doctoral researcher in the ALFA group in CSAIL at the Massachusetts Institute of Technology.',
        'prior_role_postdoc', '2016-08-25', 'still a postdoc in Aug 2016; postdoc years do not count'),
     ev(STEALTH_2018, 'Erik Hemberg, PhD is a Research Scientist in the ALFA group in CSAIL at the Massachusetts Institute of Technology.',
        'faculty_start_lower_bound', '2018-01-16', 'earliest dated capture showing the research-scientist appointment'),
     ev(CSAIL_HEMBERG_2018, "Erik Hemberg Research Scientist Contact Me Projects Research Groups Contact Me Email [email removed] Room 32-D540 Last updated Oct 29 '17",
        'faculty_profile', '2018-04-06', 'CSAIL profile, last updated Oct 29 2017'),
     ev(ALFA_2019, 'Erik Hemberg Research Scientist', 'faculty_profile', '2019-02-23', 'ALFA group members page'),
     ev(CSAIL_2026, '"ss_name":"Researchers", "ss_field_title":"Research Scientist", "ss_csail_room_map":"http://default/sites/default/files/resources/maps/5D/D540.gif", "ss_field_room":"32-D540", "ss_title":"Erik Hemberg"',
        'dept_listing:CSAIL', '2026-09-17')],
    'The PI appointment is his CSAIL research-scientist appointment (ALFA co-leader), not the earlier postdoc. No stated start was found: '
    'he was a postdoc on 2016-08-25 and a research scientist by 2018-01-16 (earliest dated capture, used as a lower-bound start). His CSAIL '
    'profile captured April 2018 shows Research Scientist with "Last updated Oct 29 \'17", which suggests the title from late 2017, but that '
    'is not a dated statement of the title, so it is not used. 2016-2017 papers stay outside; 2018-2025 are now covered. Ongoing: CSAIL '
    'directory Sept 2026.')))

for name, rows in (('princeton', princeton), ('mit', mit)):
    with open(f'{H}/period-tools/proposals/{name}.json', 'w') as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
    print(name, len(rows), {v: sum(r['verdict'] == v for r in rows) for v in ('period', 'no_change', 'unresolved')})
