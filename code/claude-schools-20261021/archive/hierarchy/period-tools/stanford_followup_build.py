"""Stanford follow-up appointment-period review (gap 2, 2026-10-27): sourced START dates (and bridged middle gaps / ends) for
Stanford PIs whose lab papers were rejected as outside_appointment_<YEAR> in hierarchy/stanford/pis.json.
Writes hierarchy/period-tools/proposals/stanford-followup.json (merged by the coordinator with merge_overrides.py).

Conventions
- Every evidence item is built by pcap.ev: the quote is verified against the capture stored in hierarchy/period-captures.sqlite.
  Dated department-listing / Profiles rows are copied unchanged into that store first, from listings/stanford/captures.sqlite
  or from the Stanford base sweep's store (claude-stanford-20261027/raw/captures.sqlite, tables captures/live; sha256 re-checked).
- A sourced start before the 2016-2026 window opens the period at 2016-01-01 (day precision; the real start year is stated in the
  note). A bare year '2016' would not do: pi_hierarchy.contains() needs every possible publication date inside the period, so a
  year-precision start excludes the papers of the start year itself.
- An existing override period that is replaced keeps all its evidence items (existing_period_id set to its id).
- 'no_change' entries carry the sourced reason why the rejected papers stay outside.
usage: /usr/local/anaconda3/2024.02/bin/python -I stanford_followup_build.py
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json, re, sqlite3, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pcap  # noqa: E402
import mpcap  # noqa: E402  (imported by pcap; DB already points at period-captures.sqlite)

ROOT = HERE.parents[1]
BASE = str(P.SWEEPS / 'claude-stanford-20261027/raw/captures.sqlite')
OVR = json.load(open(ROOT / 'hierarchy/census-overrides.json')).get('stanford', {})
PIS = {p['pi']: p for p in json.load(open(ROOT / 'hierarchy/stanford/pis.json'))}
WB = 'https://web.archive.org/web/'
PROF = 'https://profiles.stanford.edu/'
WIKI = 'https://en.wikipedia.org/wiki/'
TODAY = '2026-10-27'
OPEN = '2016-01-01'


def _store(url):
    """Make sure url is in the period store: copy it unchanged from a sister store when it is not there yet."""
    if pcap.cached(url):
        return
    try:
        pcap.copy_listing('stanford', url); return
    except (KeyError, ValueError):
        pass
    s = sqlite3.connect(f'file:{BASE}?mode=ro', uri=True)
    hit = s.execute('select 1 from captures where capture_url=?', (url,)).fetchone()
    live = s.execute('select 1 from live where url=? and status=200', (url,)).fetchone()
    s.close()
    if hit:
        mpcap.copy(BASE, url, 'select fetched_at, sha256, raw_zlib from captures where capture_url=?', (url,),
                   'claude-stanford-20261027/raw/captures.sqlite (captures)')
    elif live:
        mpcap.copy(BASE, url, 'select fetched_at, sha256, raw_zlib from live where url=?', (url,),
                   'claude-stanford-20261027/raw/captures.sqlite (live)')


def ev(url, quote, kind, observed, note=None):
    _store(url)
    return pcap.ev(url, quote, kind, observed, note)


def wb_date(url):
    m = re.search(r'/web/(\d{4})(\d{2})(\d{2})', url)
    return f'{m[1]}-{m[2]}-{m[3]}' if m else None


def cap(url, quote, kind='stanford_profiles_capture', note=None):
    """Evidence from a dated Wayback capture (observed = capture date)."""
    return ev(url, quote, kind, wb_date(url), note)


def live(url, quote, kind='stanford_profiles', note=None):
    return ev(url, quote, kind, TODAY, note)


def listing(pi, year):
    """Evidence item from the PI's dated listing row of `year` (hierarchy/stanford/pis.json)."""
    l = next(x for x in PIS[pi]['listings'] if x['year'] == year)
    _store(l['url'])
    toks = l['quote'].split()
    # the store's text view can render a row's trailing cells differently (e.g. obfuscated e-mail ids spelled letter by letter):
    # keep the longest leading part of the listing row's quote that the stored text shows verbatim (at least name + one cell)
    q = next((' '.join(toks[:k]) for k in range(len(toks), 1, -1) if pcap.quote_ok(l['url'], ' '.join(toks[:k]))), l['quote'])
    return ev(l['url'], q, l.get('kind') or 'dept_listing', wb_date(l['url']) or TODAY)


def existing(pi):
    ps = (OVR.get(pi) or {}).get('periods') or []
    assert len(ps) <= 1, (pi, 'more than one override period: pick the one to replace explicitly')
    return ps[0] if ps else None


def period(pi, start, end, asof, prec, evidence, note, endPrecision=None):
    ex = existing(pi)
    items = [e for e in evidence if e]
    seen = {(e['url'], e['quote']) for e in items}
    if ex:
        items += [e for e in ex['evidence'] if (e['url'], e.get('quote')) not in seen]
    p = dict(start=start, end=end, asof=asof, datePrecision=prec, evidence=items, note=note)
    if endPrecision:
        p['endPrecision'] = endPrecision
    return dict(pi=pi, existing_period_id=ex['id'] if ex else None, verdict='period', period=p, departure=None,
                reason=note, old=dict(start=ex['start'], end=ex['end'], asof=ex.get('asof')) if ex else None)


def no_change(pi, why, evidence=()):
    return dict(pi=pi, existing_period_id=None, verdict='no_change', period=None, departure=None, reason=why, why=why,
                evidence=[e for e in evidence if e])


PRE = 'Opened at 2016-01-01 (the window start; the appointment began earlier, see the note) so that 2016 papers are covered.'


def build():
    out = []
    # ---------------- genuinely earlier starts (sourced) ----------------
    out.append(period('Tsachy Weissman', OPEN, None, TODAY, 'day', [
        ev(WIKI + 'Tsachy_Weissman', 'Weissman became assistant professor of electrical engineering at Stanford University in 2003.', 'faculty_start_statement', TODAY),
        live(PROF + 'itschak-weissman', 'Itschak Weissman Robert and Barbara Kleist Professor in the School of Engineering Electrical Engineering', note='live Stanford Profiles page (slug itschak-weissman): appointment active as of this date'),
        listing('Tsachy Weissman', 2023)],
        'Start: assistant professor of EE at Stanford from 2003 (Wikipedia; associate 2010, professor 2015); EE faculty listing 2023; '
        'Robert and Barbara Kleist Professor on the live Profiles page (2026-10-27). ' + PRE + ' Ongoing.'))
    out.append(period('Dustin Schroeder', '2016', None, TODAY, 'year', [
        cap(WB + '20170912045049id_/https://earth.stanford.edu/people/dustin-schroeder', 'Assistant Professor, Department of Geophysics, Stanford University (2016 - Present)', 'dept_page_capture:Earth'),
        listing('Dustin Schroeder', 2019), listing('Dustin Schroeder', 2023),
        live(PROF + 'dustin-schroeder', 'Director of Undergraduate Studies, Department of Geophysics (2017 - Present)')],
        'Start: Assistant Professor of Geophysics from 2016 (his Earth-sciences page captured 2017-09-12 lists "Assistant Professor, Department of '
        'Geophysics, Stanford University (2016 - Present)"; no month, so year precision: 2016 papers stay unresolved). Listed 2019 (Profiles) and '
        '2023-2026 (EE, Associate Professor); no evidence of a break 2020-2022 (DUS of Geophysics 2017-present on the live profile). Ongoing.'))
    out.append(period('Martin Fischer', OPEN, None, TODAY, 'day', [
        ev('https://web.stanford.edu/~fischer/background/employment_record.html', '1992 to 1999: Assistant Professor, Department of Civil and Environmental Engineering, Stanford University', 'cv', TODAY),
        listing('Martin Fischer', 2016), listing('Martin Fischer', 2023),
        live(PROF + 'martin-fischer', 'Director, Center for Integrated Facility Engineering - CIFE (2001 - Present)')],
        'Start: Assistant Professor of Civil and Environmental Engineering at Stanford from 1992 (his employment record; acting assistant professor 1991-92 '
        'not counted), Professor of CEE and CIFE director (2001-present) on the live profile. Listed 2016, 2023, 2026; no evidence of a break. ' + PRE + ' Ongoing.'))
    out.append(period('Allison Okamura', OPEN, None, TODAY, 'day', [
        ev(WIKI + 'Allison_Okamura', 'She returned to Stanford University as a faculty member in 2011', 'faculty_start_statement', TODAY),
        listing('Allison Okamura', 2020), listing('Allison Okamura', 2023),
        live(PROF + 'allison-okamura', 'Academic Appointments Professor, Mechanical Engineering')],
        'Start: Stanford faculty member from 2011 (Wikipedia; Johns Hopkins before). Listed every year 2016-2020, 2023, 2026; Professor of ME on the live '
        'profile; no evidence of a break in 2021-2022 or 2024-2025. ' + PRE + ' Ongoing.'))
    out.append(period('David Tse', OPEN, None, TODAY, 'day', [
        ev('https://lidsmag.lids.mit.edu/2017/practical_lessons.html', "after nearly two decades on Berkeley's Electrical Engineering and Computer Sciences faculty, in 2014 he moved a few miles south to Stanford's Department of Electrical Engineering", 'faculty_start_statement', TODAY),
        ev('https://web.stanford.edu/~dntse/bio.html', 'From 1995 to 2014, he was on the faculty of the Department of Electrical Engineering and Computer Sciences in the University of California at Berkeley. He is currently a professor at Stanford University.', 'faculty_bio', TODAY),
        listing('David Tse', 2019),
        live(PROF + 'david-tse', 'Academic Appointments Professor, Electrical Engineering')],
        'Start: moved to Stanford EE in 2014 (MIT LIDS magazine 2017; Berkeley faculty 1995-2014 per his bio). Listed 2019, 2023, 2025, 2026; Professor of EE '
        'on the live profile; no evidence of a break. ' + PRE + ' Ongoing.'))
    out.append(period('Boris Murmann', OPEN, '2023', None, 'day', [
        ev('https://www-ee.eng.hawaii.edu/faculty/profile?usr=121', 'Prior to joining UH, he served as an assistant, associate and full professor in the Department of Electrical Engineering at Stanford University from 2004 to 2023.', 'faculty_start_statement', TODAY),
        ev('https://www-ee.eng.hawaii.edu/faculty/profile?usr=121', 'Dr. Murmann joined the University of Hawaiʻi at Mānoa in 2023.', 'departure', TODAY),
        listing('Boris Murmann', 2016), listing('Boris Murmann', 2019), listing('Boris Murmann', 2023)],
        'Stanford EE faculty 2004-2023 (University of Hawaii profile), joined UH Manoa in 2023. Listed 2016, 2019-2023; no evidence of a break in 2017-2018. '
        + PRE + ' End 2023 at year precision (2023 papers via the same-year listing); 2024 papers stay outside (UH).', endPrecision='year'))
    out.append(period('Benjamin Van Roy', OPEN, None, TODAY, 'day', [
        live(PROF + 'benjamin-van-roy', 'Benjamin Van Roy is a Professor at Stanford University, where he has served on the faculty since 1998.', kind='stanford_profiles_bio'),
        listing('Benjamin Van Roy', 2016), listing('Benjamin Van Roy', 2023)],
        'Start: on the Stanford faculty since 1998 (live profile bio). Listed 2016, 2023, 2025, 2026; no evidence of a break. ' + PRE + ' Ongoing.'))
    out.append(period('Yejin Choi', '2025-01-16', None, TODAY, 'day', [
        ev('https://hai.stanford.edu/news/nvidias-yejin-choi-joins-stanford-hai', 'today announced the appointment of NVIDIA’s Yejin Choi as the Dieter Schwarz Foundation HAI Professor, Professor of Computer Science, and Stanford HAI Senior Fellow.', 'appointment_announcement', '2025-01-16'),
        live(PROF + 'yejin-choi', 'Academic Appointments Professor, Computer Science')],
        'Start: Stanford HAI announced her appointment as Professor of Computer Science on 2025-01-16 (start = announcement date; no earlier start is '
        'claimed). Earlier papers are from the University of Washington / AI2 / NVIDIA and stay outside. Ongoing (live profile).'))
    out.append(period('Ehsan Adeli', '2024-08-11', None, TODAY, 'day', [
        cap(WB + '20240502174354id_/https://profiles.stanford.edu/ehsan-adeli', 'Ehsan Adeli Clinical Assistant Professor, Psychiatry and Behavioral Sciences', note='still clinical-track (not a faculty rank under the review rules) on this date'),
        cap(WB + '20240811132000id_/https://profiles.stanford.edu/ehsan-adeli', 'Ehsan Adeli Assistant Professor (Research) of Psychiatry and Behavioral Sciences (Public Mental Health and Populations Sciences)'),
        live(PROF + 'ehsan-adeli', 'Academic Appointments Assistant Professor-Research, Psychiatry and Behavioral Sciences')],
        'Start is a LOWER BOUND: the first Profiles capture with a research-track professor rank (Assistant Professor (Research), 2024-08-11); the '
        '2024-05-02 capture still shows Clinical Assistant Professor (not counted). 2017-2023 papers and 2024 papers before Aug 11 stay outside '
        '(postdoc/research staff/clinical years). Ongoing.'))
    out.append(period('Mark Musen', OPEN, None, TODAY, 'day', [
        ev(WIKI + 'Mark_Musen', 'Between 1988 and 1995, Musen was an Assistant Professor of Medicine at Stanford University School of Medicine .', 'faculty_start_statement', TODAY),
        ev(WIKI + 'Mark_Musen', 'promoted to Professor of Medicine in 2002.', 'faculty_rank_statement', TODAY),
        live(PROF + 'mark-musen', 'Chief, Division of Computational Medicine (1992 - Present)')],
        'Start: Assistant Professor of Medicine at Stanford from 1988, Professor from 2002 (Wikipedia); Chief of the Division of Computational Medicine '
        '1992-present (live profile). ' + PRE + ' Ongoing.'))
    out.append(period('Jeffrey Hancock', OPEN, None, TODAY, 'day', [
        ev(WIKI + 'Jeffrey_T._Hancock', 'Since 2015, Hancock has been a professor in the Department of Communication at Stanford University.', 'faculty_start_statement', TODAY),
        live(PROF + 'jeffrey-hancock', 'Founding Director, Stanford Social Media Lab (2015 - Present)')],
        'Start: professor of Communication at Stanford since 2015 (Wikipedia; Cornell 2002-2015); founding director of the Stanford Social Media Lab '
        '2015-present (live profile). ' + PRE + ' Ongoing.'))
    out.append(period('H.-S. Philip Wong', OPEN, None, TODAY, 'day', [
        ev(WIKI + 'H.-S._Philip_Wong', 'He joined Stanford University as Professor of Electrical Engineering in September 2004.', 'faculty_start_statement', TODAY)],
        'Start: Professor of EE at Stanford from September 2004 (profile bio, Wikipedia); leave of absence at TSMC 2018-2020 (a leave, not a break). '
        'Re-opened at 2016-01-01 instead of the year-precision 2016, which excluded 2016 papers. Ongoing.'))
    out.append(period('Jeremy Bailenson', OPEN, None, TODAY, 'day', [
        ev(WIKI + 'Virtual_Human_Interaction_Lab', 'It was founded in 2003 by Jeremy Bailenson, associate professor of communication at Stanford University.', 'lab_founding_statement', TODAY),
        live(PROF + 'jeremy-bailenson', "Dean's Award for Distinguished Teaching for First Years of Teaching, Stanford University (2007)"),
        live(PROF + 'jeremy-bailenson', 'Senior Fellow, Woods Institute for the Environment, Stanford University (2013 - Present)')],
        'Start: founded the Virtual Human Interaction Lab at Stanford in 2003 as a Communication faculty member (Wikipedia); Stanford teaching award 2007 '
        'and Woods senior fellow 2013-present (live profile). ' + PRE + ' Ongoing.'))
    out.append(period('Daniel Rubin', OPEN, None, '2024-07-06', 'day', [
        cap(WB + '20150919062125id_/https://profiles.stanford.edu/daniel-rubin', 'Daniel Rubin Associate Professor of Radiology (General Radiology), of Medicine (Biomedical Informatics Research) and, by courtesy, of Ophthalmology'),
        live(PROF + 'daniel-rubin', 'Director, Scholarly Concentration in Informatics and Data Driven Medicine, Stanford School of Medicine (2011 - 2024)')],
        'Start: Associate Professor of Radiology and Medicine on the 2015-09-19 Profiles capture (a lower bound before the window). ' + PRE +
        ' asof unchanged (2024-07-06); emeritus now.'))
    out.append(period('Nigam H. Shah', OPEN, None, TODAY, 'day', [
        ev(WIKI + 'Nigam_Shah', 'Shah began his academic career as a Research Scientist at the Stanford University School of Medicine, and joined the faculty in 2011.', 'faculty_start_statement', TODAY)],
        'Start: joined the Stanford faculty in 2011 (Wikipedia); Assistant Professor on the 2015-09-07 Profiles capture. Re-opened at 2016-01-01 instead of '
        'the year-precision 2016, which excluded 2016 papers. Ongoing.'))
    out.append(period('Mike Cherry', OPEN, None, TODAY, 'day', [
        cap(WB + '20151201192105id_/https://profiles.stanford.edu/j-michael-cherry', 'Mike Cherry Professor (Research) of Genetics'),
        listing('Mike Cherry', 2022)],
        'Start: Professor (Research) of Genetics on the 2015-12-01 Profiles capture (a lower bound before the window; same title 2021 and now, emeritus). '
        'No evidence of a break 2016-2020. ' + PRE))
    out.append(period('Justin Grimmer', '2019-12-08', None, TODAY, 'day', [
        listing('Justin Grimmer', 2019), listing('Justin Grimmer', 2023), listing('Justin Grimmer', 2026)],
        'Bridged from dated listings: Professor of Political Science on Profiles captures 2019-12-08 and 2023-01-30 and on the live profile (2026); no capture '
        'for 2020-2022 or 2024-2025 and no evidence of a break. Start is a LOWER BOUND (the first post-return listing); 2016 and 2018 papers (around his '
        'University of Chicago years) stay outside.'))
    out.append(period('Curtis Langlotz', OPEN, None, TODAY, 'day', [
        live(PROF + 'curtis-langlotz', 'Associate Chair for Information Systems, Department of Radiology (2014 - 2024)'),
        ev('https://healthmanagement.org/c/imaging/post/zoom-on-curtis-p-langlotz-professor-of-radiology-and-biomedical-informatics-stanford-university', 'Zoom On: Curtis P. Langlotz, Professor of Radiology and Biomedical Informatics, Stanford University In Imaging Tue, 16 Feb 2016', 'dated_profile', '2016-02-16')],
        'Start: Associate Chair for Information Systems of Stanford Radiology from 2014 (live profile; Penn faculty before); Professor of Radiology and '
        'Biomedical Informatics at Stanford in a 2016-02-16 interview. ' + PRE + ' Ongoing.'))
    out.append(period('Jacob Fox', OPEN, None, TODAY, 'day', [
        ev(WIKI + 'Jacob_Fox', 'He joined the faculty of Stanford University in 2015.', 'faculty_start_statement', TODAY),
        listing('Jacob Fox', 2018), live(PROF + 'jacob-fox', 'Jacob Fox')],
        'Start: joined the Stanford faculty in 2015 (Wikipedia; MIT 2010-2014). Listed every year 2018-2026. ' + PRE + ' Ongoing.'))
    out.append(period('Geoffrey Sonn', OPEN, None, TODAY, 'day', [
        cap(WB + '20150905230219id_/https://med.stanford.edu/profiles/geoffrey-sonn', 'Geoffrey Sonn Assistant Professor of Urology and, by courtesy, of Radiology at the Stanford University Medical Center', 'cap_profile_capture')],
        'Start: Assistant Professor of Urology on the 2015-09-05 CAP profile capture (a lower bound before the window); same title on the 2019 and 2020 '
        'Profiles captures; no evidence of a break. ' + PRE + ' Ongoing.'))
    out.append(period('Johannes van Benthem', OPEN, None, TODAY, 'day', [
        ev('https://www.ae-info.org/ae/User/Benthem_Johan', '2005 - Full Professor, Philosophy, Stanford University', 'cv', TODAY),
        ev('https://www.ae-info.org/ae/User/Benthem_Johan', '2008 Henry Waldgrave Stuart Professor, named chair, Stanford University', 'cv', TODAY)],
        'Start: Full Professor of Philosophy at Stanford from 2005 (Academia Europaea CV; Bonsall Visiting Professor 1991-2005 not counted), named Henry '
        'Waldgrave Stuart Professor 2008. ' + PRE + ' Ongoing.'))
    out.append(period('Lexing Ying', OPEN, None, TODAY, 'day', [
        ev(WIKI + 'Lexing_Ying', 'Before joining Stanford in 2012, he was a post-doc at California Institute of Technology and a professor at University of Texas, Austin .', 'faculty_start_statement', TODAY)],
        'Start: joined Stanford in 2012 (Wikipedia; UT Austin professor before). ' + PRE + ' Ongoing.'))
    out.append(period('Paul Milgrom', OPEN, None, TODAY, 'day', [
        live(PROF + 'paul-milgrom', 'Professor of Economics, Stanford University (1987 - Present)')],
        'Start: Professor of Economics at Stanford 1987-present (live profile). ' + PRE + ' Ongoing.'))
    out.append(period('Mohammad Akbarpour', '2016-09-10', None, TODAY, 'day', [
        cap(WB + '20160910134711id_/http://www.gsb.stanford.edu/faculty-research/faculty/mohammad-akbarpour', 'Research Fellow, Becker-Friedman Institute, University of Chicago, 2015-16 Assistant Professor, Economics, Stanford GSB, 2016', 'dept_page_capture:GSB'),
        listing('Mohammad Akbarpour', 2019)],
        'Start is a LOWER BOUND: his GSB page captured 2016-09-10 lists "Assistant Professor, Economics, Stanford GSB, 2016" (after a 2015-16 Chicago '
        'fellowship). Listed every year 2019-2026; no evidence of a break. 2016 papers before Sept 10 stay outside. Ongoing.'))
    out.append(period('Bruce Daniel', OPEN, None, TODAY, 'day', [
        cap(WB + '20150905232141id_/https://profiles.stanford.edu/bruce-daniel', 'Bruce Daniel Professor of Radiology (General Radiology) and, by courtesy, of Bioengineering')],
        'Start: Professor of Radiology on the 2015-09-05 Profiles capture (a lower bound before the window); no evidence of a break before the 2018 listing. '
        + PRE + ' Ongoing.'))
    out.append(period('Per Enge', OPEN, '2018-04-22', None, 'day', [
        ev(WIKI + 'Per_K._Enge', 'where he died on 22 April 2018, aged 64.', 'death', TODAY)],
        'Start: Professor on the 2015-06-19 Profiles capture (a lower bound before the window). ' + PRE + ' End: died 22 April 2018 (Wikipedia; Stanford '
        'news 2018-04-26), so 2018 papers before that date are covered; posthumous 2018-2020 papers stay outside.'))
    out.append(period('Jay McClelland', OPEN, None, TODAY, 'day', [
        live(PROF + 'jay-mcclelland', 'Professor, Department of Psychology (2006 - Present)'),
        ev(WIKI + 'James_McClelland_(psychologist)', 'In fall 2006 McClelland moved to Stanford University from Carnegie Mellon University', 'faculty_start_statement', TODAY)],
        'Start: Professor of Psychology at Stanford 2006-present (live profile; moved from CMU in fall 2006, Wikipedia). ' + PRE + ' Ongoing.'))
    out.append(period('Jan Vondrak', '2016', None, TODAY, 'year', [
        live(PROF + 'jan-vondrak', 'Jan Vondrak is a Professor of Mathematics at Stanford University, since 2016.', kind='stanford_profiles_bio')],
        'Start: Professor of Mathematics at Stanford since 2016 (live profile bio; IBM Almaden before). Year precision: the 2016 paper stays unresolved, '
        '2017-2019 papers are covered. Ongoing.'))
    out.append(period('Daniel Schwartz', OPEN, None, TODAY, 'day', [
        live(PROF + 'daniel-schwartz', 'Professor of Education, Stanford Graduate School of Education (2000 - Present)')],
        'Start: Professor of Education at Stanford 2000-present (live profile). ' + PRE + ' Ongoing.'))
    out.append(period('Chris Chafe', OPEN, None, TODAY, 'day', [
        ev('https://ccrma.stanford.edu/~cc/lyon/resume/html.html', '1994 to present: Associate Professor of Music, Stanford University.', 'cv', TODAY),
        live(PROF + 'chris-chafe', 'Director, Center for Computer Research in Music and Acoustics (1996 - Present)')],
        'Start: Associate Professor of Music at Stanford from 1994 (his CCRMA CV, c. 1998; Associate Professor (Research) 1989-1994), director of CCRMA '
        '1996-present and Duca Family Professor now (live profile); no evidence of a break. ' + PRE + ' Ongoing.'))
    out.append(period('Jennifer A McNab', OPEN, None, TODAY, 'day', [
        cap(WB + '20150919073057id_/https://profiles.stanford.edu/jennifer-mcnab', 'Jennifer A McNab Assistant Professor (Research) of Radiology (General Radiology)')],
        'Start: Assistant Professor (Research) of Radiology on the 2015-09-19 Profiles capture (a lower bound before the window). ' + PRE + ' Ongoing.'))
    out.append(period('Art Owen', OPEN, None, TODAY, 'day', [
        ev('https://www.uwaterloo.ca/statistics-and-actuarial-science/events/david-sprott-distinguished-lecture-art-b-owen', 'Art Owen is a professor of statistics at Stanford University, where he has held a faculty position since 1985.', 'faculty_start_statement', TODAY),
        live(PROF + 'art-owen', 'Chair, Department of Statistics, Stanford University (2018 - 2021)')],
        'Start: Stanford statistics faculty since 1985 (University of Waterloo lecture bio, 2014). ' + PRE + ' Ongoing.'))
    out.append(period('Mitchell L. Stevens', OPEN, None, TODAY, 'day', [
        ev('https://ed.stanford.edu/news/stevens-named-director-digital-research-and-planning', 'Mitchell Stevens , associate professor of education, has been appointed to a newly created position', 'dated_news', '2013-04-21')],
        'Start: associate professor of education at Stanford by 2013-04-21 (GSE news; a lower bound before the window). Listed 2019, 2020, 2026; no evidence '
        'of a break. ' + PRE + ' Ongoing.'))
    out.append(period('Julian Nyarko', '2020-01-21', None, TODAY, 'day', [
        ev('https://law.stanford.edu/press/empirical-law-scholar-joins-stanford-law-school-faculty/', 'January 21, 2020 By Stephanie Ashe Subscribe Share on Twitter Share on Facebook This winter, Stanford Law School (SLS) welcomed Julian Nyarko as an assistant professor of law.', 'appointment_announcement', '2020-01-21')],
        'Start is a LOWER BOUND: SLS announced on 2020-01-21 that it welcomed him as assistant professor of law "this winter" (Columbia fellow 2018-). '
        '2016-2019 papers predate the appointment and stay outside. Ongoing.'))
    out.append(period('Mohsen Bayati', OPEN, None, TODAY, 'day', [
        cap(WB + '20140722081658id_/http://www.gsb.stanford.edu/faculty-research/faculty/mohsen-bayati', 'Mohsen Bayati Assistant Professor of Operations, Information and Technology', 'dept_page_capture:GSB')],
        'Start: Assistant Professor of OIT on his GSB page captured 2014-07-22 (a lower bound before the window). ' + PRE + ' Ongoing.'))
    out.append(period('Erica Plambeck', OPEN, None, TODAY, 'day', [
        cap(WB + '20140821063741id_/http://www.gsb.stanford.edu/faculty-research/faculty/erica-plambeck', 'Erica Plambeck Walter Kenneth Kilpatrick Professor of Operations, Information and Technology', 'dept_page_capture:GSB')],
        'Start: Professor of OIT on her GSB page captured 2014-08-21 (a lower bound before the window). ' + PRE + ' Ongoing.'))
    out.append(period('Candace Thille', OPEN, None, TODAY, 'day', [
        live(PROF + 'candace-thille', 'Assistant Professor, Stanford Graduate School of Education (2013 - Present)')],
        'Start: Assistant Professor in the Graduate School of Education 2013-present (live profile administrative appointments; Associate Professor '
        '(Teaching) now). ' + PRE + ' Ongoing.'))
    out.append(period('E.J. Chichilnisky', OPEN, None, TODAY, 'day', [],
        'Start: at Stanford since 2013 as Adler Professor of Neurosurgery and Professor of Ophthalmology (live profile bio, existing evidence). Re-opened at '
        '2016-01-01 instead of the year-precision 2016, which excluded 2016 papers. Ongoing.'))
    out.append(period('Daniel Ho', OPEN, None, TODAY, 'day', [
        cap(WB + '20150906125549id_/https://law.stanford.edu/directory/daniel-e-ho/', 'Daniel E. Ho William Benjamin Scott and Luna M. Scott Professor of Law', 'dept_page_capture:Law')],
        'Start: William Benjamin Scott and Luna M. Scott Professor of Law on the SLS directory captured 2015-09-06 (a lower bound before the window). '
        + PRE + ' Ongoing.'))
    out.append(period('Chris Potts', OPEN, None, TODAY, 'day', [
        ev(WIKI + 'Christopher_Potts', 'In 2009, he joined Stanford University, where he now serves as Chair of the Linguistics Department', 'faculty_start_statement', TODAY),
        listing('Chris Potts', 2017)],
        'Start: joined Stanford Linguistics in 2009 (Wikipedia; UMass Amherst 2003-2009). Listed every year 2017-2026. ' + PRE + ' Ongoing.'))
    out.append(period('Steven Hartley Collins', '2017', None, TODAY, 'year', [
        live(PROF + 'steven-collins', 'In 2017, he joined the faculty of Mechanical Engineering at Stanford University.', kind='stanford_profiles_bio')],
        'Start: joined the Stanford ME faculty in 2017 (live profile bio; CMU before). Year precision: 2017 papers stay unresolved, 2018 papers are covered. '
        'Ongoing.'))
    out.append(period('Kuang Xu', OPEN, None, TODAY, 'day', [
        cap(WB + '20150710212249id_/http://www.gsb.stanford.edu/faculty-research/faculty/kuang-xu', 'Kuang Xu Assistant Professor of Operations, Information and Technology', 'dept_page_capture:GSB')],
        'Start: Assistant Professor of OIT on his GSB page captured 2015-07-10 (a lower bound before the window). ' + PRE + ' Ongoing.'))
    out.append(period('Jonathan Berger', OPEN, None, TODAY, 'day', [
        ev('https://ccrma.stanford.edu/~brg/bio.html', 'Berger is The Denning Family Provostial Professor at Stanford', 'faculty_bio', '2009-05-16', 'bio page last updated 5-16-09'),
        live(PROF + 'jonathan-berger', 'Jonathan Berger is the Denning Family Provostial Professor in Music at Stanford University')],
        'Start: Denning Family Provostial Professor at Stanford by 2009-05-16 (his CCRMA bio, a lower bound before the window); same chair on the 2019, 2020 '
        'and live profiles; no evidence of a break. ' + PRE + ' Ongoing.'))
    out.append(period('Johan Ugander', OPEN, '2025', None, 'day', [],
        'Start: Assistant Professor on his MS&E page captured 2015-11-09 (existing evidence; a lower bound before the window). Re-opened at 2016-01-01 '
        'instead of the year-precision 2016, which excluded 2016 papers. End 2025 unchanged.', endPrecision='year'))
    out.append(period('Bernd Girod', OPEN, None, TODAY, 'day', [
        live(PROF + 'bernd-girod', 'Before joining Stanford in 1999, he was a Chaired Professor in the Electrical Engineering Department of the University of Erlangen-Nuremberg.', kind='stanford_profiles_bio'),
        listing('Bernd Girod', 2016), listing('Bernd Girod', 2019)],
        'Start: joined Stanford in 1999 (live profile bio). Listed 2016, 2019-2023, 2026; no evidence of a break in 2017-2018. ' + PRE + ' Ongoing.'))
    out.append(period('Gabriel Y. Weintraub', '2016-07-11', None, '2025-01-02', 'day', [],
        'Start is a LOWER BOUND: his GSB page captured 2016-07-11 lists "Associate Professor, Operations, Information & Technology, Stanford University, '
        '2016 - present" (existing evidence; Columbia before). Day precision from the capture date replaces the year-precision 2016, so 2016 papers after '
        'July 11 are covered. asof unchanged.'))
    out.append(period('Kay Giesecke', OPEN, None, TODAY, 'day', [
        live(PROF + 'kay-giesecke', 'He has been on the Stanford faculty since 2005', kind='stanford_profiles_bio')],
        'Start: on the Stanford faculty since 2005 (MS&E page and live profile bio). Re-opened at 2016-01-01 instead of the year-precision 2016, which '
        'excluded 2016 papers. Ongoing.'))
    out.append(period('Daniela Saban', OPEN, None, TODAY, 'day', [],
        'Start: GSB assistant professor from 2015 (her CV, existing evidence). Re-opened at 2016-01-01 instead of the year-precision 2016, which excluded '
        '2016 papers. Ongoing.'))
    # ---------------- bridged middle gaps ----------------
    out.append(period('Andrea Montanari', wb_date(next(l['url'] for l in PIS['Andrea Montanari']['listings'] if l['year'] == 2016)), None, TODAY, 'day', [
        listing('Andrea Montanari', 2016), listing('Andrea Montanari', 2019), listing('Andrea Montanari', 2023),
        live(PROF + 'andrea-montanari', 'Academic Appointments Professor, Statistics Professor, Mathematics')],
        'Bridged from dated faculty listings: listed as Professor in 2016 (EE), 2019-2023 and 2026 (Profiles); no listing or profile capture exists for '
        '2017-2018 or 2024-2025 and no evidence of a break. Start is a LOWER BOUND (the first dated listing in the window); ongoing (live profile).'))
    # ---------------- no change (papers predate / postdate the appointment, or no source) ----------------
    out.append(no_change('Jason Alan Fries', 'Rejected 2016-2025 papers predate the faculty appointment: Research Engineer (Med/BMIR) on Profiles captures '
        'through 2025-08-05, Assistant Professor by 2025-12-16.', [
        cap(WB + '20250805022643id_/https://profiles.stanford.edu/jason-fries', 'Jason Fries Research Engineer, Med/BMIR'),
        cap(WB + '20251216130513id_/https://profiles.stanford.edu/jason-fries', 'Jason Alan Fries Assistant Professor of Biomedical Data Science and of Medicine (BMIR)')]))
    out.append(no_change('Juan Carlos Niebles', 'Rejected 2016-2018 papers predate any professor rank: the 2019-03-22 Profiles capture still shows Sr Research '
        'Engineer (research staff; Universidad del Norte faculty before). Existing period unchanged.'))
    out.append(no_change('Todd Walter', 'Rejected 2016-2019 papers: research staff then - the GPS Lab page captured 2019-08-22 gives "Sr Research Engineer"; '
        'Professor (Research) first on the 2020-06-09 Profiles capture (existing period start 2020 stands).', [
        cap(WB + '20190822074710id_/https://gps.stanford.edu/people/todd-walter', 'Todd Walter Todd Walter Sr Research Engineer, Aeronautics and Astronautics', 'dept_page_capture:GPS Lab')]))
    out.append(no_change('Nicholas Haber', 'Rejected 2016-2019 papers are from his Stanford postdoc (Postdoctoral Fellow, Stanford University 2014-2019 on the '
        'live profile; Postdoctoral Research Fellow on the 2015 and 2018 Profiles captures); assistant professor of education from the 2020 listing.', [
        live(PROF + 'nicholas-haber', 'Postdoctoral Fellow, Stanford University (2014 - 2019)'),
        cap(WB + '20181205022105id_/https://profiles.stanford.edu/nicholas-haber', 'Nicholas Haber Postdoctoral Research Fellow, Systems Medicine')]))
    out.append(no_change('Kilian M. Pohl', 'Unresolved: Consulting Assistant Professor on the 2015-10-16 Profiles capture (consulting titles are not faculty); '
        'Associate Professor (Research) first on 2020-10-01; no capture or statement for 2016-2019.', [
        cap(WB + '20151016185323id_/https://profiles.stanford.edu/kilian-pohl', 'Kilian Pohl Consulting Assistant Professor, Psychiatry and Behavioral Sciences')]))
    out.append(no_change('Jiajun Wu', 'Rejected 2016-2019 papers are from his MIT PhD / Google years (live profile: "Before joining Stanford, he was a Visiting '
        'Faculty Researcher at Google Research"); assistant professor from the 2020 listing.', [
        live(PROF + 'jiajun-wu', 'Before joining Stanford, he was a Visiting Faculty Researcher at Google Research.', kind='stanford_profiles_bio')]))
    out.append(no_change('Serena Yeung-Levy', 'Rejected 2016-2018 papers are from her Stanford PhD (2018) and Harvard postdoc (2019) (live profile); faculty '
        'from the 2019 listing.', [live(PROF + 'serena-yeung', 'Postdoctoral Fellow, Harvard University (2019) Ph.D., Stanford University (2018)')]))
    out.append(no_change('Renyuan Xu', 'Rejected 2019-2024 papers are from USC (2021-2024), NYU (2024-2025) and earlier (live profile); Stanford from 2025.', [
        live(PROF + 'renyuan-xu', 'Prior to joining Stanford, she held positions at New York University (2024-2025) and the University of Southern California (2021–2024)', kind='stanford_profiles_bio')]))
    out.append(no_change('Tijana Zrnic', 'Rejected 2024-2025 papers are from her Stanford postdoc: Postdoctoral Scholar on Profiles captures through 2025-05-03; '
        'Statistics announced on 2025-12-19 that she returns as Assistant Professor in January (2026).', [
        cap(WB + '20250503124922id_/https://profiles.stanford.edu/tijana-zrnic', 'Tijana Zrnic Postdoctoral Scholar, Statistics'),
        ev('https://statistics.stanford.edu/news/tijana-zrnic-returns-assistant-professor-january', 'Tijana Zrnic returns as Assistant Professor in January December 19, 2025', 'appointment_announcement', '2025-12-19')]))
    out.append(no_change('Victor R. Lee', 'Rejected 2019 papers: Associate Professor at Utah State 2015-2019 (live profile), Stanford from the 2020 listing; '
        'no month for the move, so 2019 stays unresolved.', [live(PROF + 'victorlee', 'Associate Professor, Department of Instructional Technology & Learning Sciences,, Utah State University, Logan (2015 - 2019)')]))
    out.append(no_change('Emily Fox', 'Rejected 2018 paper is from her Apple / University of Washington years (live profile: "From 2018-2021, Emily led the '
        'Health AI team at Apple"); Stanford from the 2021 listing.', [
        live(PROF + '248640', 'From 2018-2021, Emily led the Health AI team at Apple, where she was a Distinguished Engineer.', kind='stanford_profiles_bio')]))
    out.append(no_change('Barbara Elizabeth Engelhardt', 'Rejected 2021-2022 papers are from Princeton (faculty 2014-2022, live profile); Stanford from the 2023 listing.', [
        live(PROF + 'barbara-engelhardt', 'an Assistant, Associate, and then Full Professor at Princeton University in Computer Science from 2014-2022', kind='stanford_profiles_bio')]))
    for pi, why in [
        ('Tatsunori Hashimoto', 'Pre-faculty years (PhD/postdoc 2018-2020); first faculty listing 2021. No dated start was fetched, so 2020 stays unresolved.'),
        ('Sanmi Koyejo', 'Rejected 2016-2017 papers are from his pre-Stanford years (UIUC faculty); Stanford faculty from the 2022 listing. Not re-sourced here.'),
        ('Zachary Manchester', 'Departure: existing period ends 2020 (last dated Aero/Astro capture); 2021-2022 papers are from Carnegie Mellon. Not re-sourced here.'),
        ('Virginia Williams', 'Departure: only a 2016 Stanford listing; 2017+ papers are from MIT. Not re-sourced here.'),
        ('Ryan Williams', 'Departure: only a 2016 Stanford listing; 2017+ papers are from MIT. Not re-sourced here.'),
        ('Tim Roughgarden', 'Departure: listed 2016-2018; 2019-2020 papers are from Columbia. Not re-sourced here.'),
        ('Matei Zaharia', 'Departure: listed 2016-2023; 2024 papers are from UC Berkeley. Not re-sourced here.'),
        ('Fuhito Kojima', 'Departure: existing period 2016-2020 (last dated evidence 2020-04-26); 2022-2025 papers are from the University of Tokyo. Not re-sourced here.'),
        ('Ingmar Riedel-Kruse', 'Departure: existing period 2016-2019 (absent from the 2020 Bioengineering listing); 2020-2022 papers are from Arizona. Not re-sourced here.')]:
        out.append(no_change(pi, why))
    return out


def _bounds(v):
    import calendar
    v = str(v or '')
    if re.fullmatch(r'\d{4}', v):
        return v + '-01-01', v + '-12-31'
    if re.fullmatch(r'\d{4}-\d{2}', v):
        y, m = map(int, v.split('-')); return v + '-01', v + '-%02d' % calendar.monthrange(y, m)[1]
    return v, v


def recovers(e):
    """Rejected papers (pis.json funnel outside_appointment_<YEAR>) whose whole year the proposed period covers, and those in
    years it covers only partly (an upper bound for the boundary years)."""
    o = {int(k[-4:]): v for k, v in PIS[e['pi']]['funnel'].items() if k.startswith('outside_appointment_')}
    if e['verdict'] != 'period':
        return dict(rejected=sum(o.values()), full=0, partial=0)
    p = e['period']; sb = _bounds(p['start']); eb = _bounds(p['end'] or p['asof'])
    inside = lambda y: f'{y}-01-01' >= sb[1] and f'{y}-12-31' <= min(eb[0], TODAY)
    return dict(rejected=sum(o.values()), full=sum(v for y, v in o.items() if inside(y)),
                partial=sum(v for y, v in o.items() if not inside(y) and f'{y}-12-31' >= sb[1] and f'{y}-01-01' <= eb[0]))


if __name__ == '__main__':
    res = build()
    for e in res:
        e['recovers'] = recovers(e)
    f = HERE / 'proposals/stanford-followup.json'
    json.dump(res, open(f, 'w'), indent=1, ensure_ascii=False)
    print(sum(e['verdict'] == 'period' for e in res), 'periods,', sum(e['verdict'] == 'no_change' for e in res), 'no_change ->', f)
