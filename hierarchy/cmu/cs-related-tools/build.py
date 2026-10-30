"""Build the CMU CS-related scope outputs (owner decision 2026-10-22) into a staging directory:
  additions.json        census rows for accepted people (format of census/cmu-additions.json; added 'cs_related_scope_20261022')
  periods.json          {name: {periods: [...]}} reviewed periods for appointments not covering all of 2016-2026
  home_departments.json rows in the format of hierarchy/home-departments.json
  review.json           every candidate's decision, reason and resolved evidence
Inputs: decisions.py (ACCEPT/REJECT), cs-related-tools/people.py (names, home departments, ids, aliases), <work>/rows.json
(listing_rows.py output), <work>/advised.json and <work>/theses.json (theses.py output), census, candidates, the
OpenAlex sweep (streamed, for ORCIDs). Every quote is checked to be an exact substring of the stored text of a capture in
hierarchy/cmu/cs-related-captures.sqlite (captures from other stores are copied in unchanged first).
usage: build.py <work_dir> <stage_dir>"""
import collections, json, re, sqlite3, sys, zlib
from pathlib import Path

HERE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE / 'tools')); sys.path.insert(0, str(HERE / 'hierarchy/cs-related-tools')); sys.path.insert(0, str(Path(__file__).parent))
from pi_hierarchy import Name, toks  # noqa: F401,E402
import csrcap, evidence  # noqa: E402
from people import P  # noqa: E402
import decisions as D  # noqa: E402

WORK, STAGE = Path(sys.argv[1]), Path(sys.argv[2])
STAGE.mkdir(parents=True, exist_ok=True)
STORE = 'hierarchy/cmu/cs-related-captures.sqlite'
TODAY = '2026-10-26'
C = json.load(open(HERE / 'hierarchy/cmu/cs-related-candidates.json'))
ROWS = json.load(open(WORK / 'rows.json'))['rows']
ADV = json.load(open(WORK / 'advised.json'))
THESES = json.load(open(WORK / 'theses.json'))
CENSUS = json.load(open(HERE / 'census/cmu-faculty.json'))
OVR = json.load(open(HERE / 'hierarchy/census-overrides.json')).get('cmu', {})
PEOPLE = {n: dict(dept=d, ids=ids, aliases=al) for n, d, ids, al in P}
FULL = {'ECE': 'Department of Electrical and Computer Engineering', 'MechE': 'Department of Mechanical Engineering',
        'CEE': 'Department of Civil and Environmental Engineering', 'ChemE': 'Department of Chemical Engineering',
        'Tepper': 'Tepper School of Business', 'Heinz': 'Heinz College of Information Systems and Public Policy',
        'Statistics & Data Science': 'Department of Statistics and Data Science', 'Social and Decision Sciences': 'Department of Social and Decision Sciences',
        'Philosophy': 'Department of Philosophy', 'Psychology': 'Department of Psychology', 'Mathematical Sciences': 'Department of Mathematical Sciences',
        'EPP': 'Department of Engineering and Public Policy', 'Architecture': 'School of Architecture', 'Design': 'School of Design',
        'MLD': 'Machine Learning Department', 'HCII': 'Human-Computer Interaction Institute', 'RI': 'Robotics Institute'}
problems = []


# ---------------------------------------------------------------- store helpers
def store_con():
    return sqlite3.connect(f'file:{HERE / STORE}?mode=ro', uri=True)


_MEM = {'max': -1, 'rows': [], 'by': {}}


def _load():
    """In-memory view of the store's 200 captures (newest first), reloaded when rows were added (copies)."""
    con = store_con()
    mx = con.execute('select max(id) from captures').fetchone()[0]
    if mx != _MEM['max']:
        rows = con.execute("select id, url, capture_url, fetched_at, sha256, text, copied_from from captures where status=200 and error is null "
                           "and text is not null and url not like '%robots.txt' order by id desc").fetchall()
        by = {}
        for r in rows:
            for k in (r[1], r[2]):
                if k and k not in by:
                    by[k] = r
        _MEM.update(max=mx, rows=rows, by=by)
    con.close()
    return _MEM


def _cap(r):
    key = r[2] or r[1]
    m = re.search(r'/web/(\d{4})(\d{2})(\d{2})\d*id_/', key)
    obs = f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else r[3][:10]
    return dict(url=key, sha256=r[4], text=r[5], observed=obs, id=r[0], copied_from=r[6])


def cap_of(url):
    """(capture key, sha256, text, observed date) of a stored 200 capture whose url or capture_url is url."""
    r = _load()['by'].get(url)
    return _cap(r) if r else None


def _like(pat, s):
    return bool(s) and re.fullmatch(re.escape(pat).replace('%', '.*').replace('_', '.'), s, re.S) is not None


def page_quote(url_like, rx):
    """Exact quote (regex match) from the newest stored page whose url/capture_url matches url_like (SQL LIKE pattern)."""
    crx = re.compile(rx)
    for r in _load()['rows']:
        if url_like != '%' and not (_like(url_like, r[1]) or _like(url_like, r[2] or '')):
            continue
        m = crx.search(r[5])
        if m:
            c = _cap(r)
            return dict(url=c['url'], sha256=c['sha256'], quote=m.group(0), observed=c['observed'], store=f"{STORE}#{c['id']}")
    return None


LSTORE = sqlite3.connect(f"file:{HERE / 'listings/cmu/captures.sqlite'}?mode=ro", uri=True)
LTEXTS = []


def listing_quote(rx):
    """A quote matching rx from a listings-sweep capture or this review's store (listings capture copied into the store)."""
    q = page_quote('%', rx)
    if q:
        return q
    if not LTEXTS:
        for cap, raw, ct in LSTORE.execute('select capture_url, raw_zlib, content_type from captures where http_status=200 and raw_zlib is not null'):
            try:
                LTEXTS.append((cap, csrcap.to_text(zlib.decompress(raw), ct or 'text/html')))
            except Exception:
                continue
    for cap, t in LTEXTS:
        if re.search(rx, t):
            evidence.copy_listing(cap)
            c = cap_of(cap)
            m = re.search(rx, c['text']) if c else None
            if m:
                return dict(url=c['url'], sha256=c['sha256'], quote=m.group(0), observed=c['observed'], store=f"{STORE}#{c['id']}",
                            capture_copied_from='listings/cmu/captures.sqlite')
    return None


def row_source(r):
    """A listing row (rows.json) as a source whose quote is an exact substring of the stored capture text, or None."""
    cu = r['capture_url']
    if r.get('capture_store') == 'listings/cmu/captures.sqlite':
        hit = LSTORE.execute('select capture_url from captures where sha256=? and http_status=200 limit 1', (r['sha256'],)).fetchone()
        if not hit:
            return None
        cu = hit[0]  # the sweep's own key for these bytes (listing_rows rebuilds the URL from final_url)
        evidence.copy_listing(cu)
    c = cap_of(cu)
    if not c:
        return None
    t, q = c['text'], r['quote']
    if q not in t:
        q2 = re.sub(r'\s+', ' ', q).strip()
        m = re.search(r'\s*'.join(re.escape(ch) for ch in re.sub(r'\s+', '', q)), t) if not q2 in t else None
        if q2 in t:
            q = q2
        elif m:  # same characters, different spacing in this text view (" ; " vs "; "): cite the stored span
            q = m.group(0)
        else:  # cut name .. rank from the stored text
            nm, rk = r.get('name_as_written') or '', (r.get('rank_as_listed') or '').strip()
            i = t.find(nm) if nm else -1
            j = t.find(rk[:60], i) if i >= 0 and rk else -1
            if i < 0 or j < 0 or j - i > 250:
                return None
            q = t[i:j + len(rk[:60])]
    s = dict(url=c['url'], sha256=c['sha256'], quote=q, observed=r['observed_on'], kind='dept_listing:' + r['department'], rank=r.get('rank_as_listed'),
             emeritus=bool(r.get('emeritus')), store=f"{STORE}#{c['id']}")
    if c.get('copied_from'):
        s['capture_copied_from'] = c['copied_from']
    return s


# ---------------------------------------------------------------- thesis helpers
def thesis_quote(rec, adviser_raw=None):
    """(student quote, adviser quote) from a stored thesis capture (copied from hierarchy/cmu/thesis-captures.sqlite)."""
    evidence.copy_thesis(rec['url'])
    c = cap_of(rec['url'])
    if not c:
        return None, None, None
    t = c['text']
    if rec['src'] == 'kilthub' if 'src' in rec else rec['source'] == 'kilthub':
        qs = '"full_name": %s' % json.dumps(rec['student'], ensure_ascii=False)
        if qs not in t:
            qs = '"full_name": %s' % json.dumps(rec['student'])
        vals = rec.get('adviser_values') or []
        qa = None
        for v in vals:
            for cand in ('"name": "Advisor(s)", "value": %s' % json.dumps(v, ensure_ascii=False), '"name": "Advisor(s)", "value": %s' % json.dumps(v)):
                cand = re.sub(r'\s+', ' ', cand)
                if cand in t:
                    qa = cand
        return c, (qs if qs in t else None), qa
    # SCS reports archive abstract page: student .. adviser mark
    i = t.find(rec['student'])
    adv = adviser_raw or ''
    m = re.search(re.escape(adv) + r'\s*\((?:Co-?\s?)?(?:[Cc]hair|[Aa]dvis[eo]r)[^)]*\)', t) if adv else None
    if i >= 0 and m and 0 < m.end() - i < 2500:
        return c, rec['student'], t[m.start():m.end()]
    return c, (rec['student'] if i >= 0 else None), None


def best_phd(aids):
    hits = [h for a in aids for h in ADV.get(a, {}).get('hits', []) if h['role'] == 'phd' and 2016 <= h['year'] <= 2026]
    seen, out = set(), []
    for h in hits:
        if h['url'] not in seen:
            seen.add(h['url']); out.append(h)
    # prefer KiltHub, sole adviser, latest year
    return sorted(out, key=lambda h: (h['src'] != 'kilthub', h['n_adv'], -h['year'])), out


# ---------------------------------------------------------------- per-person manual evidence
# PI bases from pages (stated PhD advising on a dated page, or a lab the person heads alone)
PAGE_PI = {
    'Rema Padman': ('advises_phd', '%andrew.cmu.edu/user/georgech/supervision.html', r'Chloe Huang, incoming PhD student \(co-advised by Rema Padman\)',
                    'George Chen\'s supervision page names a PhD student co-advised by Rema Padman.'),
    'Michael D. Smith': ('advises_phd', '%andrew.cmu.edu/user/georgech/supervision.html', r'Helen S\. Zeng \(PhD 2024; advised with Mike Smith \(chair\) and Brett Danaher\)',
                         'George Chen\'s supervision page names CMU PhDs chaired by Mike Smith (2020, 2024).'),
    'Jeremy C. Weiss': ('advises_phd', '%andrew.cmu.edu/user/georgech/supervision.html', r'PhD student \(co-advised by Jeremy Weiss and Zack Lipton\)',
                        'George Chen\'s supervision page names a CMU PhD student co-advised by Jeremy Weiss.'),
    'George H. Chen': ('advises_phd', '%andrew.cmu.edu/user/georgech/supervision.html', r'Current Research Supervision Shurui Cao , PhD student \(co-advised by Rayid Ghani\)',
                       'His supervision page lists current and past PhD students.'),
    'Shixiang Zhu': ('advises_phd', '%andrew.cmu.edu/user/shixianz/adv.html', r'Ph\.D\. Students Wenbin Zhou , Ph\.D\. student \(2023 - present\)', 'His advising page lists PhD students.'),
    'Yorie Nakahira': ('advises_phd', '%cmu.edu/ece/learning-control/people/index.html', r'Faculties Yorie Nakahira Ph\.D\. Students Zhuoyuan Wang',
                       'Control & Learning Group people page: faculty Yorie Nakahira, then her PhD students.'),
    'Guannan Qu': ('advises_phd', '%guannanqu.com/people/%', r'People Current members PhD Students Alex DeWeese PhD Student · Fall 2022', 'His group page lists PhD students since Fall 2022.'),
    'Beidi Chen': ('lab_head', '%keroro824.github.io/lab-page/%', r'Beidi Chen Assistant Professor, Carnegie Mellon University', 'InfiniAI Lab page: the lab of Assistant Professor Beidi Chen.'),
    'Daniel Yurovsky': ('advises_phd', '%psychology/directory/graduate-students%', r'Advisor: Daniel Yurovsky', 'Psychology graduate-student roster names him as adviser.'),
}
# rows whose listing is not a CMU appointment although the text gives no other-university marker in the cut title
DROP_ROWS = {('Douglas Sicker', 2026, 'EPP'): 'the 2026 EPP page lists him as Senior Associate Dean for Computing Initiatives, College of Engineering, Design and Computing, University of Colorado Denver'}
TITLE = {'Marvin A. Sirbu': 'Professor of Engineering and Public Policy; Electrical and Computer Engineering and Joint Appointment at Tepper School of Business','John Hooker': 'Professor of Operations Research', 'Rema Padman': 'Trustees Professor of Management Science and Healthcare Informatics',
         'George H. Chen': 'Assistant Professor of Information Systems', 'Shixiang Zhu': 'Assistant Professor of Data Analytics',
         'Pedro Ferreira': 'Professor of Information Systems (Joint appointment with Engineering and Public Policy)',
         'Michael D. Smith': 'Professor of Information Technology and Public Policy', 'Simon DeDeo': 'Professor, Social and Decision Sciences'}
LAB_NAME = {'Beidi Chen': 'InfiniAI Lab'}
# Dated appointment evidence besides listing rows: (url LIKE, regex, start, end) -- start/end strings, None when not stated
EXTRA = {
    'Benjamin Moseley': [('%profiles/moseley-benjamin.html', r'Carnegie Bosch Assistant Professor of Operations Research Carnegie Mellon University, Tepper School of Business, Pittsburgh, United States 1 Sep 2018 - 1 Jan 2020', '2018-09', None)],
    'Anita Williams Woolley': [('%profiles/williams-woolley-anita.html', r'Associate Professor of Organizational Behavior and Theory \(untenured\) Carnegie Mellon University, Pittsburgh, United States Jul 2015 - Jun 2017', '2015-07', None)],
    'Willem-Jan van Hoeve': [('%profiles/van-hoeve-willem-jan.html', r'Carnegie Bosch Associate Professor of Operations Research Carnegie Mellon University, Tepper School of Business, Pittsburgh, United States 1 Jan 2016 - 1 Jan 2019', '2016-01', None)],
    'Fatma Kılınç-Karzan': [('%profiles/kilinc-karzan-fatma.html', r'Assistant Professor of Operations Research Carnegie Mellon University, Tepper School of Business, Pittsburgh, United States Sep 2011 - Jun 2016', '2011-09', None)],
    'Javier Peña': [('%profiles/pena-javier.html', r'Professor of Operations Research Carnegie Mellon University - Tepper School of Business, Pittsburgh, Pennsylvania, United States Jul 2011 - present', '2011-07', None)],
    'Sridhar Tayur': [('%profiles/tayur-sridhar.html', r'University Professor, Ford Distinguished Research Chair Carnegie Mellon University, Tepper School of Business, Pittsburgh, United States 1 Jul 1998 - present', '1998-07', None)],
    'Kannan Srinivasan': [('%profiles/srinivasan-kannan.html', r'H\.J\. Heinz II Professor of Management, Marketing and Business Technology at Tepper School of Business since 1999', '1999', None)],
    'Soo-Haeng Cho': [('%profiles/cho-soo-haeng.html', r'Cho has been a faculty member at the Tepper School of Business, Carnegie Mellon University since 2008', '2008', None)],
    'Ali Shourideh': [('%profiles/shourideh-ali.html', r'Assistant Professor of Economics Carnegie Mellon University, Tepper School of Business, Pittsburgh, United States 1 Jul 2016 - Jul 2020', '2016-07', None)],
    'Ariel Zetlin-Jones': [('%profiles/zetlin-jones-ariel.html', r'Assistant Professor of Economics Carnegie Mellon University, Tepper School of Business,, Pittsburgh, United States 2012 - 2018', '2012', None)],
    'Param Vir Singh': [('%profiles/singh-param.html', r'Courtesy Appointment as Professor Carnegie Mellon University, Heinz College, Pittsburgh, United States 2013 - present', '2013', None),
                        ('%profiles/singh-param.html', r'Carnegie Bosch Professor of Business Technologies and Marketing Carnegie Mellon University, Tepper School of Business, Pittsburgh, United States 1 Jul 2019 - present', None, None)],
    'John Hooker': [('%20191111054517id_%operations-research%', r'featuring John Hooker , Professor of Operations Research', None, None)],
    'Alan Scheller-Wolf': [('%20191111054456id_%operations-management%', r'featuring Alan Scheller-Wolf , Richard M\. Cyert Professor of Operations Management', None, None)],
    'Rema Padman': [('%20190504070838id_%padman-rema%', r'Rema Padman Professor of Management Science and Healthcare Informatics', None, None),
                    ('%20210615062016id_%padman-rema%', r'Rema Padman Trustees Professor of Management Science and Healthcare Informatics', None, None),
                    ('https://www.heinz.cmu.edu/faculty-research/profiles/padman-rema', r'Rema Padman Trustees Professor of Management Science and Healthcare Informatics', None, None)],
    'Michael D. Smith': [('%20200920023156id_%smith-michaeld%', r'Michael D\. Smith Professor of Information Technology and [^,]{0,40}', None, None),
                         ('%20210623211521id_%smith-michaeld%', r'Michael D\. Smith Professor of Information Technology and [^,]{0,40}', None, None),
                         ('https://www.heinz.cmu.edu/faculty-research/profiles/smith-michaeld', r'Michael D\. Smith Professor of Information Technology and Public Policy', None, None)],
    'Pedro Ferreira': [('%20190414085155id_%ferreira-pedro%', r'Pedro Ferreira [A-Z][^.]{0,90}', None, None),
                       ('%20210515114530id_%ferreira-pedro%', r'Pedro Ferreira [A-Z][^.]{0,90}', None, None),
                       ('https://www.heinz.cmu.edu/faculty-research/profiles/ferreira-pedro', r'Pedro Ferreira Professor of Information Systems \(Joint appointment with Engineering and Public Policy\)', None, None)],
    'Alexandra Chouldechova': [('%20191213074219id_%chouldechova%', r'Alexandra Chouldechova [A-Z][^.]{0,90}', None, None),
                               ('%20210515105222id_%chouldechova%', r'Alexandra Chouldechova [A-Z][^.]{0,90}', None, None)],
    'Shixiang Zhu': [('%20220812180501id_%zhu-shixiang%', r'Shixiang \(Woody\) Zhu is an assistant professor of data analytics at Heinz College', None, None),
                     ('https://www.heinz.cmu.edu/faculty-research/profiles/zhu-shixiang', r'Shixiang \(Woody\) Zhu is an assistant professor of data analytics at Heinz College', None, None)],
    'Simon DeDeo': [('https://www.cmu.edu/dietrich/sds/people/faculty/simon-dedeo.html', r'Simon DeDeo is a professor in Social and Decision Sciences at Carnegie Mellon University', None, None)],
    'Matteo Pozzi': [('%20160121081334id_%cee/people/faculty%', r"Hae Young Noh Irving Oppenheim, P\.E\. Matteo Pozzi", None, None), ('%20170420225926id_%cee/people/faculty%', r"Hae Young Noh Irving Oppenheim, P\.E\. Matteo Pozzi", None, None)],
    'Burcu Akinci': [('%20160121081334id_%cee/people/faculty%', r"CEE Faculty Amit Acharya Peter Adams Burcu Akinci", None, None), ('%20170420225926id_%cee/people/faculty%', r"CEE Faculty Amit Acharya Peter Adams Burcu Akinci", None, None)],
    'Mario Bergés': [('%20160121081334id_%cee/people/faculty%', r"CEE Faculty Amit Acharya Peter Adams Burcu Akinci Mario Berges", None, None), ('%20170420225926id_%cee/people/faculty%', r"CEE Faculty Amit Acharya Peter Adams Burcu Akinci Mario Berges", None, None)],
    'Hae Young Noh': [('%20160121081334id_%cee/people/faculty%', r"Meagan S\. Mauter Hae Young Noh", None, None), ('%20170420225926id_%cee/people/faculty%', r"Meagan S\. Mauter Hae Young Noh", None, None)],
    'Daragh Byrne': [('https://www.architecture.cmu.edu/profiles/daragh-byrne', r"His teaching has been recognized by CMU with a Teaching Innovation Award \(2017\)", '2017', None)],
    'Beidi Chen': [('%andrew.cmu.edu/user/beidic/%', r'I am starting as an Assistant Professor of Electrical and Computer Engineering at Carnegie Mellon University in Fall 2023', '2023-08', None)],
}
OTHER_UNIV = re.compile(r'Stanford|University of (?!Pittsburgh)|Colorado|Hong Kong|Washington University|UT Austin')
EXCLUDE_TITLE = re.compile(r'Adjunct|Visiting|Special Faculty|Special Professor|Consulting|Systems Scientist|Research Scientist|Post-?doc|Lecturer|Instructor', re.I)


def keep_row(r, home):
    t = r.get('rank_as_listed') or ''
    if r.get('future_start_note') or EXCLUDE_TITLE.search(t) or OTHER_UNIV.search(t) or OTHER_UNIV.search(r.get('quote') or ''):
        return False
    if 'Courtesy' in t or 'courtesy' in t:  # a courtesy title in another CMU department still shows a CMU appointment; in the home department it does not
        rest = re.sub(r'Courtesy (Professor|Faculty|Appointment)[^;]*', '', t)
        if r['department'] == home and not re.search(r'Professor|Head|Dean', rest):
            return False
    return True


def rank_of(title):
    t = title or ''
    if re.search(r'Research Professor', t):
        return 'research'
    if re.search(r'Teaching|Distinguished Service', t):
        return 'teaching'
    return 'ladder'


# ---------------------------------------------------------------- ORCIDs from the sweep (streamed)
acc_ids = {i for n in set(D.ACCEPT.values()) for i in PEOPLE[n]['ids']}
orcids = collections.defaultdict(collections.Counter)
inst = 'https://openalex.org/I74973139'
con = sqlite3.connect(f"file:{HERE / 'hierarchy/cmu/openalex-sweep.sqlite'}?mode=ro", uri=True)
for (b,) in con.execute('select body from pages'):
    try:
        b = zlib.decompress(b)
    except zlib.error:
        pass
    for w in json.loads(b):
        for a in w.get('authorships') or []:
            au = a.get('author') or {}
            aid = (au.get('id') or '').split('/')[-1]
            if aid in acc_ids and au.get('orcid'):
                orcids[aid][au['orcid'].replace('https://orcid.org/', '')] += 1
con.close()

# ---------------------------------------------------------------- accepted people
cand_by_id = {c['author'].split('/')[-1]: (i, c) for i, c in enumerate(C)}
rows_by = collections.defaultdict(list)
for r in ROWS:
    rows_by[r['pi']].append(r)
additions, periods, homes, acc_info = [], {}, [], {}
for name in sorted(set(D.ACCEPT.values()), key=lambda n: list(PEOPLE).index(n)):
    pp = PEOPLE[name]; home = pp['dept']
    cands = [cand_by_id[a] for a in pp['ids'] if a in cand_by_id]
    # listing sources: one per year, home department first
    srcs, emer, other = {}, {}, []
    for r in sorted(rows_by.get(name, []), key=lambda r: (r['department'] != home, r['observed_on'])):
        s = row_source(r)
        if not s:
            problems.append((name, 'row quote not in stored capture', r['capture_url'], r['quote'][:80])); continue
        if re.search(r'Emerit', r.get('rank_as_listed') or ''):
            emer.setdefault(r['year'], s); continue
        if (name, r['year'], r['department']) in DROP_ROWS or not keep_row(r, home):
            other.append((r['year'], s)); continue
        srcs.setdefault(r['year'], s)
    extra_ev = []
    for url_like, rx, st, en in EXTRA.get(name, []):
        q = page_quote(url_like, rx)
        if not q:
            problems.append((name, 'extra evidence not found', url_like, rx[:60])); continue
        q.update(kind='dated_profile:' + home); extra_ev.append((q, st, en))
        y = int(q['observed'][:4])
        srcs.setdefault(y, q)
    if emer:  # years from the first emeritus listing on are retirement, whatever other lists still show
        cut = min(emer)
        srcs = {y: s for y, s in srcs.items() if y < cut}
    years = sorted(y for y in srcs if 2016 <= y <= 2026)
    if not years:
        problems.append((name, 'no dated faculty evidence')); continue
    sources = [srcs[y] for y in sorted(srcs)]
    latest = srcs[years[-1]]
    ranked_src = [s for s in sources if s.get('rank') and 'Professor' in s['rank'] and s['kind'] == 'dept_listing:' + home] or \
                 [s for s in sources if s.get('rank') and 'Professor' in s['rank']] or [s for s in sources if s.get('rank')]
    title = TITLE.get(name) or (ranked_src[-1]['rank'].strip() if ranked_src else latest['quote'])
    # PI basis
    pb = None
    if name in PAGE_PI:
        kind, ul, rx, note = PAGE_PI[name]
        q = page_quote(ul, rx)
        if q:
            pb = dict(kind=kind, url=q['url'], sha256=q['sha256'], quote=q['quote'], observed=q['observed'], store=q['store'], note=note)
    ranked, allphd = best_phd(pp['ids'])
    if pb is None:
        for h in ranked:
            rec = dict(h, source=h['src'])
            c, qs, qa = thesis_quote(rec, h['adv'])
            if c and qa:
                pb = dict(kind='advises_phd', url=c['url'], sha256=c['sha256'], quote=qa, quote_student=qs, observed=c['observed'], store=f"{STORE}#{c['id']}",
                          capture_copied_from='hierarchy/cmu/thesis-captures.sqlite',
                          note=(f"Named adviser ({h['adv']}) of {len(allphd)} CMU PhD thesis record(s) {min(x['year'] for x in allphd)}-{max(x['year'] for x in allphd)} "
                                f"(KiltHub / SCS reports archive); quoted: {h['student']} ({h['year']}, {h['dept']}), \"{h['title'][:120]}\"."),
                          record=dict(student=h['student'], year=h['year'], dept=h['dept'], advisers=h['advisers'], source=h['src']))
                break
    if pb is None:
        problems.append((name, 'no PI basis resolved')); continue
    # period
    ext_start = [st for _, st, _ in extra_ev if st]
    start = min(ext_start) if ext_start else str(years[0])
    ongoing = years[-1] >= 2025
    per = None
    if not (years[0] == 2016 and ongoing):  # the dated listings alone do not span the window
        ev = []
        st_ev = next((q for q, st, _ in extra_ev if st == start), None) or srcs[years[0]]
        ev.append(st_ev)
        if ongoing:
            end, asof = None, latest['observed']
            if latest is not st_ev:
                ev.append(latest)
        else:
            end, asof = str(years[-1]), None
            if latest is not st_ev:
                ev.append(latest)
            nxt = sorted([(y, s) for y, s in list(emer.items()) + other if y > years[-1]], key=lambda x: x[0])
            if nxt:
                ev.append(nxt[0][1])  # the first later listing shows the changed status (emeritus / adjunct / courtesy)
        per = dict(id='override_period_cmu_' + re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_'), start=start, end=end, asof=asof,
                   evidence=[dict(url=e['url'], sha256=e['sha256'], quote=e['quote']) for e in ev])
        periods[name] = dict(periods=[per])
    # identity
    orc = collections.Counter()
    for a in pp['ids']:
        orc.update(orcids.get(a, {}))
    orcid = [o for o, n in orc.most_common() if n >= 2][:2]
    ident = '; '.join(f"OpenAlex {a} carries the name ({', '.join(c['names'][:3])}) on {c['works']} CMU-affiliated works 2016-2026, {c['dblp_works']} of them DBLP-indexed "
                      f"(last author on {round(100 * c['last_author_share'])}%; top venues: {', '.join(v for v in c['top_venues'][:3] if v)})"
                      for a, (i, c) in zip([x for x in pp['ids'] if x in cand_by_id], cands))
    if orcid:
        ident += '; ORCID ' + ', '.join(orcid) + ' on those author records'
    ident += '.'
    row = dict(name=name, aliases=[a for a in dict.fromkeys(pp['aliases'] + [n for _, c in cands for n in c['names']]) if a != name][:12],
               collection_person_id=None, profile_url=None, dblp=[], openalex=['https://openalex.org/' + a for a in pp['ids']], orcid=orcid,
               identity_note=ident, rank=rank_of(title), title_as_listed=title, departments=[home], years_listed=years,
               sources=[{k: v for k, v in s.items()} for s in sources], is_pi=True, pi_basis=pb, lab_units=[], added='cs_related_scope_20261022',
               cs_related=dict(basis='hierarchy/cmu/cs-related-candidates.json (DBLP-based)', school_works=sum(c['works'] for _, c in cands),
                               dblp_works=sum(c['dblp_works'] for _, c in cands), candidates=[i for i, _ in cands]))
    if name in LAB_NAME:
        row['lab_name'] = LAB_NAME[name]
    additions.append(row)
    hev = next((s for s in sources if s['kind'].endswith(':' + home) or s['kind'] == 'dept_listing:' + home), sources[-1])
    also = sorted({s['kind'].split(':', 1)[1] for s in sources} - {home})
    homes.append(dict(school='cmu', name=name, home_department=FULL[home], also=[FULL.get(a, a) for a in also], status='accepted',
                      evidence=dict(url=hev['url'], sha256=hev['sha256'], quote=hev['quote']),
                      note=f"CS-related scope review 2026-10-22 (DBLP-based candidates). Home department from the dated department listing/profile quoted; "
                           f"faculty years listed {years[0]}-{years[-1]}" + ('' if not per else f"; reviewed period {per['start']}-{per['end'] or 'present'}") + '.'))
    acc_info[name] = dict(years=years, period=per, pi_kind=pb['kind'], title=title)


# ---------------------------------------------------------------- review
def resolve(spec, cand):
    k = spec[0]
    if k == 'thesis':
        nm = Name([spec[1]])
        recs = [r for r in THESES if nm.match(r['student'])]
        for r in sorted(recs, key=lambda r: r['source'] != 'kilthub'):
            evidence.copy_thesis(r['url'])
            c = cap_of(r['url'])
            if not c:
                continue
            q = re.sub(r'\s+', ' ', '"full_name": %s' % json.dumps(r['student'], ensure_ascii=False) if r['source'] == 'kilthub' else r['student'])
            if q not in c['text']:
                q = re.sub(r'\s+', ' ', '"full_name": %s' % json.dumps(r['student']))
            if q in c['text']:
                return dict(url=c['url'], sha256=c['sha256'], quote=q, observed=c['observed'], kind='own_thesis',
                            note=f"{r['student']}: CMU {r['role']} thesis {r['year']} ({r['dept']}), \"{r['title'][:100]}\"")
        return dict(kind='own_thesis', note=f'no stored thesis record found for {spec[1]}', unresolved_evidence=True)
    if k == 'thesis_url':
        evidence.copy_thesis(spec[1])
        q = page_quote(spec[1], spec[2])
        return dict(q, kind='own_thesis') if q else dict(kind='own_thesis', note='pattern not found: ' + spec[2], unresolved_evidence=True)
    if k == 'listing':
        q = listing_quote(spec[1])
        return dict(q, kind='listing') if q else dict(kind='listing', note='pattern not found: ' + spec[1], unresolved_evidence=True)
    if k == 'page':
        q = page_quote(spec[1], spec[2])
        return dict(q, kind='page') if q else dict(kind='page', note='pattern not found: ' + spec[2], unresolved_evidence=True)
    if k == 'census':
        f = next((f for f in CENSUS if f['name'] == spec[1]), None)
        if not f:
            return dict(kind='census', note='no census row ' + spec[1], unresolved_evidence=True)
        s = (f.get('sources') or [{}])[0]
        return dict(kind='census', url=s.get('url'), sha256=s.get('sha256'), quote=s.get('quote'), note=f"census/cmu-faculty.json: {f['name']}, "
                    f"\"{f.get('title_as_listed')}\" ({', '.join(f.get('departments') or [])}), rank {f.get('rank')}, listed {(f.get('years_listed') or ['-'])[0]}-{(f.get('years_listed') or ['-'])[-1]}", source='census/cmu-faculty.json')
    if k == 'override':
        o = OVR.get(spec[1])
        if o:
            e = o.get('evidence') or {}
            return dict(kind='reviewed_exclusion', url=e.get('url'), sha256=e.get('sha256'), quote=e.get('quote'), note=(o.get('why') or '')[:300], source='hierarchy/census-overrides.json')
        rep = json.load(open(HERE / 'hierarchy/cmu/report.json'))
        x = next((e for e in rep.get('excluded', []) if e['pi'] == spec[1]), None)
        return dict(kind='reviewed_exclusion', note=(x or {}).get('why', 'see hierarchy/cmu/gap-evidence.json')[:400], source='hierarchy/cmu/report.json (excluded) / gap-evidence.json')
    if k == 'advised':
        hits = [h for h in ADV.get(cand['author'].split('/')[-1], {}).get('hits', []) if h['role'] == 'phd']
        return dict(kind='advised_theses', note=spec[1], records=[dict(student=h['student'], year=h['year'], dept=h['dept'], adviser=h['adv'], url=h['url']) for h in hits[:6]])
    if k == 'searched':
        return dict(kind='searched', note=spec[1])
    raise ValueError(spec)


review = []
for i, c in enumerate(C):
    aid = c['author'].split('/')[-1]
    base = dict(index=i, name=c['name'], openalex=c['author'], works=c['works'], dblp_works=c['dblp_works'], last_author_share=c['last_author_share'], years=c['years'])
    if i in D.ACCEPT:
        n = D.ACCEPT[i]
        if n not in acc_info:
            review.append(dict(base, decision='unresolved', reason='accepted in review but the build could not resolve its evidence', person=n)); continue
        a = acc_info[n]; row = next(r for r in additions if r['name'] == n)
        review.append(dict(base, decision='accepted', person=n, home_department=PEOPLE[n]['dept'], reason=f"{a['title']} ({PEOPLE[n]['dept']}); PI basis {a['pi_kind']}; "
                           f"faculty years listed {a['years'][0]}-{a['years'][-1]}" + (f"; period {a['period']['start']}-{a['period']['end'] or 'present'}" if a['period'] else ''),
                           evidence=[dict(url=row['pi_basis']['url'], sha256=row['pi_basis']['sha256'], quote=row['pi_basis']['quote'], kind='pi_basis:' + row['pi_basis']['kind']),
                                     dict(url=row['sources'][-1]['url'], sha256=row['sources'][-1]['sha256'], quote=row['sources'][-1]['quote'], kind=row['sources'][-1]['kind'])]))
    else:
        dec, reason, specs = D.REJECT[i]
        review.append(dict(base, decision=dec, reason=reason, evidence=[resolve(s, c) for s in specs]))

json.dump(additions, open(STAGE / 'additions.json', 'w'), indent=1, ensure_ascii=False)
json.dump(periods, open(STAGE / 'periods.json', 'w'), indent=1, ensure_ascii=False)
json.dump(homes, open(STAGE / 'home_departments.json', 'w'), indent=1, ensure_ascii=False)
json.dump(review, open(STAGE / 'review.json', 'w'), indent=1, ensure_ascii=False)
json.dump(problems, open(STAGE / 'problems.json', 'w'), indent=1, ensure_ascii=False)
print(json.dumps(dict(accepted=len(additions), periods=len(periods), review=len(review), decisions=collections.Counter(r['decision'] for r in review), problems=len(problems))))
