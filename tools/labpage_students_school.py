"""Students from a protocol school's lab member pages (protocol stage 6, source 3), into the builder's lab-page evidence
format (hierarchy/<key>/labpage-evidence.json, read by pi_hierarchy.py like Berkeley's and EPFL's).

pages    each PI's homepage pages (tools/periods_school.py fetched them) and, one level down, the links on them whose
         text or path says people / students / group / members / team (at most 3 per PI, same site or the PI's lab
         site). Fetching follows the charter: hosts whose `host_use` is live are fetched live (robots honoured,
         challenges detected and the host then blocked); every other host, and every challenged one, is read only from
         existing Wayback id_ captures (the nearest 2026 capture and the nearest one to the PI's first listed year).
         No source the charter marks `none` (Deep Blue, news.umich.edu, record.umich.edu) is ever used.
names    hierarchy/labpage-tools-epfl-berkeley/lpdom.member_candidates (sectioned name lines under role headings).
         Kept: a role of phd, postdoc or visiting (R-STU-17) (lpdom.role_of over the heading path and the line), a plausible person name
         that is not the PI. Alumni headings (former, graduated, alumni) give role phd_alumnus / postdoc_alumnus.
years    a year or range on the line (lpdom.years_in), else the page's capture year (current members; years_basis
         capture_date)
quote    the page's own whitespace-collapsed text from the section heading through the student's name (verbatim, at
         most 600 characters; a candidate without such a stretch is dropped)
filters  plausible person names only (lpdom.plausible_person: no paper titles or topics), 2-4 tokens; alumni only from
         an alumni section and only with a stated year (a graduate without a year cannot be placed); nothing whose years
         end before 2016
alumni   a role heading under an alumni marker in the page text ('Alumni', 'Former Students', ...; no 'Current' marker
         between) is an alumni section even when the marker is not a heading element (alumni_in_text)
previous a student whom the same PI's lab at a released school already holds (the PI matched by a shared DBLP pid or
school  ORCID) is that school's student, and is dropped here unless the page states a start year in or after the PI's
         first listing at this school (previous_school_students; Stella Yu's Berkeley advisees)
status   automatic and unreviewed (auto: true); stage 9's accuracy sample measures it
-> hierarchy/<key>/labpage-evidence.json, hierarchy/<key>/labpage-students-report.json
defenses (protocol stage 6, source 2) department dissertation-defense announcements, read only from Wayback captures of
         the department hosts' /event/ pages whose URL says defense or dissertation (CDX filter). An announcement
         names the candidate ('<Student>PhD Candidate', 'PhD Defense: <Student>') and, on the EECS sites, a
         'Faculty Host <PI>' (the defense chair). The student's quote is the announcement head through the candidate's
         name; host_quote is the 'Faculty Host' line (same page, same sha256). Only hosts that are census PIs count.
         -> hierarchy/<key>/defense-evidence.json, merged into labpage-evidence.json by extract (role phd_alumnus,
         years = the defense year)
directory (protocol stage 6) program PhD directories ([students].directories) list students with their own websites;
         a student's page that names the school, says PhD and puts an adviser phrase directly before a PI's full name
         ties the student to that PI (directory(); -> directory-evidence.json, merged by extract)
undated  (R-STU-14) undated members of a lab page's PhD heading, set aside by the lab-page audit, count in the year of the capture showing them
surname  (R-STU-15) surname-only adviser lists ('PhD Research Advisor: Brei') resolve to the one faculty member of that department listed that year
usage: labpage_students_school.py links|defenses|directory|undated|surname|extract <key>
"""
import collections, json, re, sys, urllib.parse, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I leaves the script's directory off sys.path (docs/CONTRIBUTING.md, Imports and sys.path)
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
import census_overrides as CO  # noqa: E402
import student_decisions as SD  # noqa: E402
import visiting as V  # noqa: E402
import school_web as W  # noqa: E402
import periods_school as PS  # noqa: E402
from pi_hierarchy import Name, toks  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hierarchy' / 'labpage-tools-epfl-berkeley'))  # this checkout's toolkit (Georgia Tech friction 29)
import lpdom  # noqa: E402

PEOPLE = re.compile(r'\b(people|students|group|members|team|lab|advisees?|alumni|former|ph\.?d|doctoral|supervis\w*|mentees?|researchers)\b', re.I)
SKIP = re.compile(r'mailto:|\.pdf$|calendar|publication|paper|teaching|course|news|blog|cv|resume|twitter|linkedin|github\.com|scholar\.google', re.I)
ALUM = lpdom.ALUMNI_RX


def stored_pages(c, url):
    """(page url as cited, sha256, html, observed year) of every stored copy of a URL (live, then Wayback captures)."""
    out = []
    r = c.execute('select status, sha256, raw_zlib, fetched_at from live where url=?', (url,)).fetchone()
    if r and r[0] == 200 and r[2]:
        out.append((url, r[1], zlib.decompress(r[2]).decode('utf-8', 'replace'), int(r[3][:4])))
    for cap, sha, raw, ts in c.execute('select capture_url, sha256, raw_zlib, wayback_timestamp from captures where page_url=? and http_status=200', (url,)):
        if raw:
            out.append((cap, sha, W.body(raw).decode('utf-8', 'replace'), int(str(ts)[:4])))
    return out


def fetch(key, c, url, first):
    host = urllib.parse.urlsplit(url).netloc.lower()
    if S.host_use(key, host) == 'live' and host not in W._blocked:
        res = W.live(c, url)
        if res and res[0] == 200:
            return
    try:
        rows = W.cdx_rows(c, re.sub(r'^https?://', '', url), collapse='timestamp:6')
        if not rows:
            return
        picks = {min(rows, key=lambda r: abs(int(r['timestamp'][:6]) - 202607))['timestamp'],
                 min(rows, key=lambda r: abs(int(r['timestamp'][:6]) - (first * 100 + 7)))['timestamp']}
        for r in rows:
            if r['timestamp'] in picks:
                W.capture(c, r['timestamp'], r['original'], url, 'labpage')
    except RuntimeError as e:   # the shared Wayback clock is cooling down after a 429: the page stays pending, never retried here
        if 'cooling down' not in str(e):
            raise
        print('wayback_cooling_pending', url, flush=True)


def people_links(html, base):
    out = []
    for m in re.finditer(r'<a\s[^>]*href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', html, re.S | re.I):
        href, text = m.group(1), re.sub(r'<[^>]+>', ' ', m.group(2))
        try:
            u = urllib.parse.urljoin(base, href)
        except ValueError:   # a malformed href ('http://[x', an IPv6-looking typo) is no link
            continue
        orig = re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', u)
        if SKIP.search(orig) or not orig.startswith('http'):
            continue
        try:
            path = urllib.parse.urlsplit(orig).path
        except ValueError:
            continue
        if PEOPLE.search(' '.join(text.split())[:60]) or PEOPLE.search(path):
            out.append(orig)
    return list(dict.fromkeys(out))


def in_own_space(url, pi, dept_hosts):
    """A people link followed from a PI's page counts only when it is in the PI's own space: a host that is not a department's, or a department path with
    `~user` or the PI's family name. (The broader people-link words had followed 'phd' links from every CS profile page to the department's
    graduate-student-leadership page and given 24 PIs the same 14 'students': UChicago friction 66.)"""
    sp = urllib.parse.urlsplit(url)
    host = sp.netloc.lower().split(':')[0]
    if not any(host == h or host.endswith('.' + h) for h in dept_hosts):
        return True
    fam = re.sub(r'[^a-z]', '', (pi.split() or [''])[-1].lower())
    return '/~' in sp.path or (len(fam) > 2 and fam in sp.path.lower())


def targets_pages(key):
    """{pi: [urls]}: the homepages plus their stored people links (computed from stored pages only)."""
    c = W.con(key); out = {}
    dept_hosts = {h['host'].lower() for h in S.get(key).get('hosts') or [] if h.get('host', '').endswith(('uchicago.edu', 'ttic.edu', 'chicagobooth.edu'))}
    for t in PS.targets(key):
        urls = list(t['urls'])
        for u in t['urls']:
            for cited, sha, h, y in stored_pages(c, u):
                urls += [x for x in people_links(h, re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', cited) if 'web.archive.org' in cited else cited) if in_own_space(x, t['name'], dept_hosts)]
        out[t['name']] = (t, list(dict.fromkeys(urls))[:8 + len(t['urls'])])
    return out


def links(key):
    c = W.con(key); n = collections.Counter()
    for pi, (t, urls) in targets_pages(key).items():
        for u in urls[len(t['urls']):]:
            if not stored_pages(c, u):
                fetch(key, c, u, t['first']); n['fetched'] += 1
        print(json.dumps(dict(pi=pi, pages=len(urls))), flush=True)
    print(json.dumps(dict(n)))


DEFENSE_HOSTS = ['cse.engin.umich.edu/event/', 'ece.engin.umich.edu/event/']  # TODO(debt): move to the charter ([students].defense_event_prefixes)


def defenses(key):
    c = W.con(key); out, n = [], collections.Counter()
    pfx = S.field(S.get(key), 'students.defense_event_prefixes') or DEFENSE_HOSTS
    for host in pfx:
        p = {'url': host, 'matchType': 'prefix', 'from': '2016', 'to': '2026', 'output': 'json', 'fl': 'timestamp,original,statuscode',
             'filter': 'original:.*(defense|dissertation).*', 'collapse': 'urlkey', 'limit': '20000'}
        for r in W.wb.cdx(p, c) or []:
            if r.get('statuscode') != '200' or 'google.com' in r['original']:
                continue
            cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], r['original'], 'defense')
            n[f'capture_{st}'] += 1
            if st != 200:
                continue
            t = W.flat(b)
            k = next((i_ for i_, x in enumerate(b) if x[0].startswith('h') and x[1].strip() == 'Dissertation Defense'), None)
            if k is None or k + 2 >= len(b):
                n['not_a_defense'] += 1; continue
            title, spk = b[k + 1][1], b[k + 2][1]
            name = None
            if 'PhD Candidate' in spk:
                name = spk[:spk.find('PhD Candidate')]
            elif re.search(r'Defense:\s*', title) and len(title.split(':', 1)[1].split()) <= 4:
                name = title.split(':', 1)[1]
            elif re.search(r'\s(?:Final|PhD|Ph\.D\.)?\s*Defense$', title):
                name = re.sub(r'\s*(?:Final|PhD|Ph\.D\.)?\s*Defense$', '', title)
            name = ' '.join((name or '').split())
            hk = next((i_ for i_, x in enumerate(b) if x[0].startswith('h') and x[1].strip() == 'Faculty Host'), None)
            host = None
            if hk is not None and hk + 1 < len(b):
                hm = re.match(r'(.+?)(?=Professor|Associate|Assistant|Research|Lecturer|University|$)', b[hk + 1][1])
                host = ' '.join(hm.group(1).split()) if hm else None
            w = re.search(r'WHEN:\s*(?:\w+,\s*)?\w+\s+\d{1,2},\s*((?:19|20)\d\d)', t)
            if not (name and 2 <= len(name.split()) <= 4 and host and w):
                n['no_candidate_or_host'] += 1; continue
            qi = t.find('Dissertation Defense ' + title); qj = t.find(name, qi)
            if qi < 0 or qj < 0 or qj - qi > 600:
                n['no_quote'] += 1; continue
            hq = t.find('Faculty Host ' + host)
            out.append(dict(student=name, host=host, year=int(w.group(1)), url=r['original'], capture_url=cap, sha256=sha,
                            quote=t[qi:qj + len(name)], host_quote=t[hq:hq + len('Faculty Host ' + host)] if hq >= 0 else 'Faculty Host ' + host))
            n['defenses'] += 1
    P.data_w('defense-evidence.json', key).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(n)))


ALUM_MARK = re.compile(r"\b(?:Alumni|Alumnae|Former (?:Students|Members|Advisees|Lab Members|Ph\.?\s?D\.? Students|Postdocs)|"
                       r"Past (?:Students|Members|Advisees|Lab Members)|Graduated (?:Students|Ph\.?\s?D\.?s?))\b")
CURRENT_MARK = re.compile(r"\bCurrent\b")


def alumni_in_text(flat, i, j):
    """The page text says the name at j sits in an alumni part: an alumni marker ('Alumni', 'Former Students', ...)
    stands before the section heading at i (or between it and the name), with no 'Current' marker after it and before
    the name. Learned 2026-10-30 (Stella Yu): an 'Alumni' line that is not a heading element leaves the role headings
    under it ('Alumni Ph.D. Students Zhongqi Miao : ...', 'Postdocs : Dong-Jin Kim') looking current."""
    last = None
    for m in ALUM_MARK.finditer(flat, 0, j):
        last = m
    if not last:
        return None
    if CURRENT_MARK.search(flat, last.end(), j):
        return None
    return last.start()


def previous_school_students(key):
    """{PI name at this school: (released school, [Name of a student of the same PI there])}. The same PI is a released
    school's PI with a shared DBLP pid or ORCID (census, additions, census-overrides). Learned 2026-10-30: Stella Yu's
    Michigan homepage lists her Berkeley advisees; Berkeley's package already holds them under her Berkeley lab."""
    ov = CO.section(key)
    ids = {}
    cf = json.loads((P.data('census-faculty.json', key)).read_text())   # a list (CMU) or {'faculty': [...]} (the other schools)
    for x in (cf if isinstance(cf, list) else cf.get('faculty', [])) + \
            (json.loads((P.data('census-additions.json', key)).read_text()) if (P.data('census-additions.json', key)).exists() else []):
        o = ov.get(x['name']) or {}
        dl = lambda v: [v] if isinstance(v, str) else list(v or [])
        ids[x['name']] = {('dblp', d) for d in dl(o.get('dblp')) or dl(x.get('dblp'))} | {('orcid', q) for q in dl(x.get('orcid')) + dl(o.get('orcid'))}
    out = {}
    for s in S.released():
        if s == key:   # a school is not its own previous school (Michigan 2026-11-05: once its package existed, every wired lab-page student was dropped as 'already held')
            continue
        pf, sf = P.data('pis.json', s), P.data('students.json', s)
        if not (pf.exists() and sf.exists()):
            continue
        st = json.loads(sf.read_text())
        for p in json.loads(pf.read_text()):
            pid = {('dblp', d) for d in p.get('dblp') or []} | {('orcid', q) for q in p.get('orcid') or []}
            for name, mine in ids.items():
                if mine & pid and Name([name]).match(p['pi']) and st.get(p['pi']):
                    out[name] = (s, [Name([r['name']]) for r in st[p['pi']] if r.get('name')])
    return out


GRID = re.compile(r"<p class=['\"]eecs-people-grid-name['\"][^>]*>(.*?)</p>\s*(?:<a href=['\"]([^'\"]+)['\"][^>]*class=['\"]eecs_people_grid_url['\"][^>]*>)?", re.S | re.I)
ADVISED = re.compile(r"(?:\b(?:co-)?advised\s+by|\bsupervised\s+by|under\s+the\s+(?:supervision|guidance|direction)\s+of|\bmy\s+(?:research\s+)?(?:advisors?|supervisors?)\s+(?:is|are|:)|"
                     r"\b(?:Ph\.?\s?D\.?\s+)?(?:advisors?|supervisors?)\s*:)\s*(?:(?:Prof(?:essor)?\.?|Dr\.?)\s+)?$", re.I)
PHD = re.compile(r"Ph\.?\s?D\.?|doctoral", re.I)


LABEL_PREFIX = re.compile(r'^(?:(?:Research|PhD|Ph\.D\.?|Doctoral|Graduate|Pre-?Doctoral)\s+Fellowship|Fellowship|Student Alumni|Alumni|Microsoft|Google|Caltech|Meta|Facebook|Amazon|Apple|IBM|Intel|NSF|Structured Prediction)\s+(?=[A-Z][\w.\'-]+\s+[A-Z])')
NOT_STUDENT_HEAD = re.compile(r'^\W*(?:hiring|open positions?|openings?|join us|we are hiring|job openings|visitors?|collaborators?)\b', re.I)


def clean_student_name(name):
    """A name the page runs together with the label or employer that precedes it ('Research Fellowship Lingyu Gao', 'Microsoft Taehwan Kim', 'Structured
    Prediction Shubhendu Trivedi'): the label is dropped while at least two name tokens remain (UChicago friction 55)."""
    n = ' '.join(str(name or '').split())
    for _ in range(3):
        m = LABEL_PREFIX.match(n)
        if not m:
            break
        n = n[m.end():]
    return n


def is_department_roster(flat, faculty, n=15):
    """True when a page names `n` or more distinct faculty of the atlas (folded full names): a department or program people page, whose students are
    the department's, not any one PI's (the Mathematics people page had given every Mathematics PI 170 graduate students; extract also skips a page with 60 or more candidate names)."""
    low = ' ' + ' '.join(toks(flat)) + ' '
    return sum(1 for f in faculty if f and (' ' + f + ' ') in low) >= n


def all_faculty_names():
    """Folded names of every PI of every school's built pis.json: a person who is faculty somewhere in the atlas is not a student on a lab page."""
    out = set()
    for k in S.keys():
        f = P.data('pis.json', k)
        if Path(f).exists():
            for p_ in json.load(open(f)):
                out |= {' '.join(toks(n)) for n in [p_['pi']] + list(p_.get('names') or []) if len(toks(n)) >= 2}
    return out


def directory_entries(key):
    """{student name: dict(years, website, evidence)} from every stored capture of the charter's
    [students].directories (program PhD directories: name and an optional website, no adviser; contact data never kept)."""
    c = W.con(key); out = {}
    for d in S.field(S.get(key), 'students.directories') or []:
        for r in W.cdx_rows(c, d, collapse='timestamp:4'):
            cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], d, 'student-directory')
            if st != 200:
                continue
            h = W.raw_html(c, cap); flat = W.flat(b); y = int(r['timestamp'][:4])
            for m in GRID.finditer(h):
                nm = ' '.join(__import__('html').unescape(re.sub(r'<[^>]+>', ' ', m.group(1))).split())
                if not (2 <= len(nm.split()) <= 5) or nm not in flat:
                    continue
                e = out.setdefault(nm, dict(years=set(), websites=[], evidence=[]))
                e['years'].add(y)
                if m.group(2) and m.group(2).startswith('http') and m.group(2) not in e['websites']:
                    e['websites'].append(m.group(2))
                if len(e['evidence']) < 2:
                    e['evidence'].append(dict(url=cap, sha256=sha, quote=nm, observed=r['timestamp'][:8], directory=d))
    return out


STUDENT_BLOCK = re.compile(r"<p>\s*<strong>([^<]{3,80})</strong>\s*<br\s*/?>(.*?)</p>|<h3[^>]*media-heading[^>]*>([^<]{3,80})</h3>\s*<p>(.*?)</p>"
                           r"|<h4[^>]*wp-block-heading[^>]*>([^<]{3,80})</h4>\s*<p[^>]*>(.*?)</p>", re.S | re.I)   # UW Allen 'Outgoing Ph.D.s' (2026-11-23)
# UW ECE PhD directory card (2026-11-23): <span class="stafftemplate--name">Name</span> ... <span ...mailing...>Adviser: PI<br /> (plain text;
# the card's email is never read)
STAFF_BLOCK = re.compile(r'<span class="stafftemplate--name">([^<]{3,80})</span>(.*?)</div>', re.S | re.I)
ADVISER_PLAIN = re.compile(r'>\s*(?:Co-)?Advis[eo]rs?(?:\(s\))?:\s*([^<]{3,200}?)\s*(?:<br|</span>)', re.S | re.I)
ADVISER_LINE = re.compile(r"<strong>\s*(?:Co-)?Advis[eo]rs?(?:\(s\))?:?\s*</strong>:?(?:&nbsp;|\s)*(.*?)(?:<br|$)", re.S | re.I)


def adviser_directory_entries(key):
    """[(student, adviser text, capture url, sha256, observed, directory url, flat text)] from every stored capture of the charter's
    [students].adviser_directories: student lists that name each student's adviser themselves (TTIC /students/ and /student-alumni/:
    `<strong>Name</strong> ... <strong>Advisor:</strong> X`). No contact data is read."""
    import html as H
    import time as _t
    c = W.con(key); out = []
    for d in S.field(S.get(key), 'students.adviser_directories') or []:
        pages = []
        live = isinstance(d, dict) and bool(d.get('live'))   # opt-in per entry ({url, live = true}); a bare URL string stays archive-only
        d = d['url'] if isinstance(d, dict) else d
        url = d if d.startswith('http') else 'https://' + d
        if live and S.host_use(key, url.split('/')[2]) == 'live':   # the live page of a live charter host (robots honoured by W.live), dated today
            res = W.live(c, url)
            if res and res[0] == 200:
                row = c.execute('select raw_zlib from live where url=?', (url,)).fetchone()
                pages.append((url, res[1], _t.strftime('%Y%m%d%H%M%S'), W.wb.text(W.body(row[0])) if row and row[0] else '', W.flat(res[2])))
        try:
            rows = W.cdx_rows(c, d, collapse='timestamp:4')
        except RuntimeError as e:   # the shared Wayback cooldown: the archived years come on a later run
            print(json.dumps(dict(adviser_directory=d, wayback_deferred=str(e)[:80])), file=sys.stderr); rows = []
        for r in rows:
            try:
                cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], d, 'student-directory')
            except RuntimeError as e:
                print(json.dumps(dict(adviser_directory=d, wayback_deferred=str(e)[:80])), file=sys.stderr); break
            if st == 200:
                pages.append((cap, sha, r['timestamp'], W.raw_html(c, cap), W.flat(b)))
        for cap, sha, ts, h, flat in pages:
            r = dict(timestamp=ts)
            for m in STAFF_BLOCK.finditer(h):
                a = ADVISER_PLAIN.search(m.group(2))
                nm = ' '.join(H.unescape(m.group(1)).split())
                adv = ' '.join(H.unescape(a.group(1)).split()) if a else ''
                if adv and 2 <= len(nm.split()) <= 5 and nm in flat:
                    out.append((nm, adv, cap, sha, r['timestamp'], d, flat))
            for m in STUDENT_BLOCK.finditer(h):
                a = ADVISER_LINE.search(m.group(2) or m.group(4) or m.group(6) or '')
                if not a:
                    continue
                nm = ' '.join(H.unescape(m.group(1) or m.group(3) or m.group(5)).split())
                adv = ' '.join(H.unescape(re.sub(r'<[^>]+>', ' ', a.group(1))).split())
                if 2 <= len(nm.split()) <= 5 and nm in flat and adv:
                    out.append((nm, adv, cap, sha, r['timestamp'], d, flat))
    return out


def nickname_forms(forms):
    """'Steve Seitz' for the census's 'Steven Seitz' (UW Allen 'Outgoing Ph.D.s', 2026-11-23: an adviser line prints the short given name).
    For every two-token form 'Given Family', the forms 'Nick Family' where the reviewed nickname tables (hierarchy/nicknames names.csv and
    extras.csv, read in their own direction: name1 has_nickname name2, plus pihier.names.NICK) give Nick as a SHORTER nickname of Given
    ('Michael' -> 'Mike'; never 'Michael' -> 'Miguel' or 'Steven' -> 'Stephen'). A nickname form is kept only when it belongs to exactly one PI
    and is no PI's own form, so it can never move a relation from one PI to another; the quote still carries the page's own spelling.
    -> [(pi, form)]"""
    import csv
    from pihier import names as N
    short = collections.defaultdict(set)
    for nk, full in N.NICK.items():
        short[full].add(nk)
    for fn in ('names.csv', 'extras.csv'):
        fp = P.data('nicknames') / fn
        if fp.exists():
            with open(fp) as fh:
                for r in csv.DictReader(fh):
                    if r.get('relationship') == 'has_nickname' and r.get('name1') and r.get('name2'):
                        short[r['name1'].strip().lower()].add(r['name2'].strip().lower())
    own = {f for _, f in forms}
    cand = collections.defaultdict(set)
    for pi, f in forms:
        t = f.split()
        if len(t) != 2 or not t[0].isalpha():
            continue
        for nk in short.get(t[0].lower(), ()):
            if 2 <= len(nk) < len(t[0]) and nk.isalpha():
                cand[f'{nk.capitalize()} {t[1]}'].add(pi)
    return [(next(iter(p)), f) for f, p in cand.items() if len(p) == 1 and f not in own]


def outgoing_directory_role(flat, name):
    """An explicitly separated outgoing-postdoc block is not a PhD roster.

    The combined page title is not a degree cue. Only a specific outgoing
    section before this person's own card supplies a role.
    """
    pos = flat.find(name)
    if pos < 0:
        return None
    headings = list(re.finditer(r'\bOutgoing\s+(Postdocs|Postdoctoral\s+Scholars|Ph\.?\s*D\.?s?)(?![.\w]|\s*(?:&|and)\s*Post)', flat[:pos], re.I))
    if not headings:
        return None
    return 'postdoc' if headings[-1].group(1).lower().startswith('post') else 'phd'


def adviser_directory(key, forms):
    """Student-adviser relations from adviser_directory_entries: an adviser text that holds a PI's full-name form (forms = [(pi, form)])
    gives one relation per (student, PI); years = the years of the captures that list the pair; the quote runs from the student's name
    through the adviser's name in the capture text (verbatim). -> rows of directory-evidence.json."""
    by = {}
    for nm, adv, cap, sha, ts, d, flat in adviser_directory_entries(key):
        for pi, f in forms:
            if re.search(re.escape(f) + r'(?![\w-])', adv):
                i = flat.find(nm)
                j = flat.find(f, i) if i >= 0 else -1
                if i < 0 or j < 0 or j - i > 500:
                    continue
                role = outgoing_directory_role(flat, nm)
                e = by.setdefault((nm, pi, role), dict(years=set(), first=None))
                e['years'].add(int(ts[:4]))
                if not e['first'] or ts < e['first'][0]:
                    e['first'] = (ts, cap, sha, d, flat[i:j + len(f)])
    rows = []
    for (nm, pi, role), e in sorted(by.items(), key=lambda x: str(x[0])):
        ts, cap, sha, d, q = e['first']
        rows.append(dict(student=nm, pi=pi, years=[min(e['years']), max(e['years'])], url=re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', cap), capture_url=cap if 'web.archive.org' in cap else None,
                         sha256=sha, quote=q, directory_evidence=[dict(url=cap, sha256=sha, quote=nm, observed=ts[:8], directory=d)],
                         section='adviser-bearing student list (' + d + ')', years_basis='directory_years'))
        if role:
            rows[-1]['role'] = role
    return rows


def adviser_heading_entries(html):
    """Read named heading cards without borrowing the next student's adviser.

    Historical directories use spans within h3 names and separate div fields;
    newer directories use h4 names followed by a paragraph with line breaks.
    Both layouts bind the explicit adviser field to the preceding name only.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    label = re.compile(r'((?:Co-)?Advis[eo]rs?(?:\(s\))?\s*:)\s*(.*)', re.I)
    for heading in soup.find_all(['h3', 'h4']):
        name = ' '.join(heading.get_text(' ', strip=True).split())
        for sibling in heading.next_siblings:
            if getattr(sibling, 'name', None) in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                break
            if getattr(sibling, 'find', None) and not isinstance(sibling, str) and sibling.find(re.compile(r'^h[1-6]$')):
                break
            fragment = BeautifulSoup(str(sibling), 'html.parser')
            for br in fragment.find_all('br'):
                br.replace_with('\n')
            for line in fragment.get_text(' ', strip=False).split('\n'):
                line = re.sub(r'\s+([,;])', r'\1', ' '.join(line.split()))
                match = label.search(line)
                if match:
                    adviser = re.split(r'\s+(?:Research Interests?|Research Areas?|Email|Office|Website)\s*:', match[2], maxsplit=1, flags=re.I)[0].strip()
                    if adviser:
                        yield name, adviser, match[1] + ' ' + adviser
                    break
            else:
                continue
            break


def adviser_h4_lists(key, forms):
    """PhD lists with h3/h4 name cards and explicit adviser fields (charter `[students].adviser_h4_lists`).
    Pages read: the stored live page (a live host: the year of its fetch) and the Wayback captures the CDX lists (one per year; a cooling Wayback clock leaves
    them pending, never retried). A PI named in the adviser text by a full-name form gets the student, once per PI (a co-advised student is under each);
    years = the years of the pages that list the pair. The quote is the student's name; host_quote is the adviser line, both verbatim in the page text;
    the entry's e-mail and links are never read into the evidence."""
    c = W.con(key); by = {}
    pi_names = {pi: Name([pi]) for pi, _ in forms}
    for d in S.field(S.get(key), 'students.adviser_h4_lists') or []:
        pages = []
        url = 'https://' + d
        row = c.execute('select fetched_at from live where url=? and status=200', (url,)).fetchone()
        if row is None and S.host_use(key, urllib.parse.urlsplit(url).netloc.lower()) == 'live':
            W.live(c, url)
            row = c.execute('select fetched_at from live where url=? and status=200', (url,)).fetchone()
        if row:
            pages.append((url, int(row[0][:4]), W.live_html(c, url), c.execute('select sha256 from live where url=?', (url,)).fetchone()[0], W.flat(W.live(c, url)[2]), row[0][:10]))
        try:
            for r in W.cdx_rows(c, d, collapse='timestamp:4'):
                cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], d, 'student-directory')
                if st == 200:
                    pages.append((cap, int(r['timestamp'][:4]), W.raw_html(c, cap), sha, W.flat(b), r['timestamp'][:8]))
        except RuntimeError as e:
            if 'cooling down' not in str(e):
                raise
            print('wayback_cooling_pending', d, flush=True)
        for cap, y, h, sha, flat, obs in pages:
            for nm, adv, hq in adviser_heading_entries(h):
                if not (2 <= len(nm.split()) <= 5 and nm in flat and hq in flat and adv):
                    continue
                hit = {pi for pi, f in forms if re.search(r'(?<![\w-])' + re.escape(f) + r'(?![\w-])', adv)}
                for tok_ in re.split(r'\s*(?:,|;|\band\b|&)\s*', adv):   # 'Greg Hager' is Gregory D. Hager, 'Anqi “Angie” Liu' is Anqi Liu: the PI whose Name matches the one adviser token
                    tok_ = re.sub(r'[“"”][^“"”]*[“"”]', ' ', tok_).strip()
                    if len(tok_.split()) >= 2:
                        m_ = [pi for pi, N_ in pi_names.items() if N_.match(tok_)]
                        if len(m_) == 1:
                            hit.add(m_[0])
                for pi in sorted(hit):
                    e = by.setdefault((nm, pi), dict(years=set(), first=None))
                    e['years'].add(y)
                    if not e['first'] or obs < e['first'][0]:
                        e['first'] = (obs, cap, sha, d, hq)
    rows = []
    for (nm, pi), e in sorted(by.items()):
        obs, cap, sha, d, hq = e['first']
        rows.append(dict(student=nm, pi=pi, years=[min(e['years']), max(e['years'])], url=re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', cap),
                         capture_url=cap if 'web.archive.org' in cap else None, sha256=sha, quote=nm, host_quote=hq,
                         directory_evidence=[dict(url=cap, sha256=sha, quote=nm, observed=obs, directory=d)],
                         section='adviser-bearing student list (' + d + ')', years_basis='directory_years'))
    return rows


ROBOT_ENTRY = re.compile(r"([A-Z][\w.'\u2019-]+(?: [A-Z][\w.'\u2019-]+){1,2}) (PhD Student|PhD Candidate)\b(.*?)(?= Research Interests?\b|$)")
ROBOT_TAGS = {'Learning', 'Vision', 'Controls', 'Control', 'Robots', 'Interaction', 'Exoskeleton', 'Navigation', 'Perception', 'Optimization', 'Machines', 'Planning', 'Sensing', 'Design', 'Manipulation', 'Medical', 'Human', 'Autonomous', 'Systems', 'Mechatronics', 'Biomechanics', 'Haptics', 'Prosthetics'}
ADV_LABEL = re.compile(r"\bAdvisors?\b\s*(.*)$")


def adviser_flat_lists(key, forms):
    """Student lists whose page text gives `<Name> PhD Student ... Advisor <PI> Research Interests` per entry (Michigan Robotics /people/students/,
    charter `[students].adviser_flat_lists`). PhD entries only (an MS entry is no student relation); the adviser text is the entry's own text up to
    'Research Interests', and a PI is named in it by a full-name form. Years = the years of the captures that list the pair; the quote runs from
    the student's name through the adviser's name (verbatim)."""
    c = W.con(key); by = {}
    for d in S.field(S.get(key), 'students.adviser_flat_lists') or []:
        for r in W.cdx_rows(c, d, collapse='timestamp:4'):
            cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], d, 'student-directory')
            if st != 200:
                continue
            flat = W.flat(b)
            for m in ROBOT_ENTRY.finditer(flat):
                a = ADV_LABEL.search(m.group(3))
                if not a:
                    continue
                nm, adv = m.group(1), a.group(1)
                while len(nm.split()) > 2 and nm.split()[0] in ROBOT_TAGS or nm.split()[0] in ('Robotics', 'Institute', 'Alumni'):
                    nm = nm.split(' ', 1)[1]  # the research-area tag that precedes each entry on the page
                if len(nm.split()) < 2:
                    continue
                for pi, f in forms:
                    mm = re.search(re.escape(f) + r'(?![\w-])', adv)
                    if mm:
                        e = by.setdefault((nm, pi), dict(years=set(), first=None))
                        e['years'].add(int(r['timestamp'][:4]))
                        if not e['first'] or r['timestamp'] < e['first'][0]:
                            q = flat[m.start():m.start(3) + a.start(1) + mm.end()]
                            e['first'] = (r['timestamp'], cap, sha, d, q)
    rows = []
    for (nm, pi), e in sorted(by.items()):
        ts, cap, sha, d, q = e['first']
        rows.append(dict(student=nm, pi=pi, years=[min(e['years']), max(e['years'])], url=re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', cap),
                         capture_url=cap if 'web.archive.org' in cap else None, sha256=sha, quote=q[:600],
                         directory_evidence=[dict(url=cap, sha256=sha, quote=nm, observed=ts[:8], directory=d)],
                         section='adviser-bearing student list (' + d + ')', years_basis='directory_years'))
    return rows


ALUMNI_ENTRY = re.compile(r"([A-Z][\w.'\u2019-]+(?: [A-Z][\w.'\u2019-]+){1,3}) Ph\.?D\.? - (20\d\d) Advisors? - (.*?)(?= Research Interests| Employment| Thesis| After graduating|$)")


def adviser_alumni(key, forms):
    """PhD alumni lists that give the graduation year and the adviser in each student's block (`<h3 class="media-heading">Name</h3><p>PhD - 2025<br />
    Advisors - A and B ...`, or the 2017 `<p><strong>Name</strong><br />` markup: TTIC /student-alumni/, charter `[students].adviser_alumni`). The name is
    the block's own heading (the flat text runs one student's employer and thesis into the next name: 'Microsoft Taehwan Kim', friction 55). A PI named
    in the adviser text gets the student with years [None, graduation year]; graduations before 2016 are not read. The quote runs from the name
    through the adviser text of the capture's own text."""
    import html as H
    c = W.con(key); by = {}
    for d in S.field(S.get(key), 'students.adviser_alumni') or []:
        for r in W.cdx_rows(c, d, collapse='timestamp:4'):
            cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], d, 'student-directory')
            if st != 200:
                continue
            h = W.raw_html(c, cap); flat = W.flat(b)
            for m in STUDENT_BLOCK.finditer(h):
                nm = ' '.join(H.unescape(m.group(1) or m.group(3) or '').split())
                body = ' '.join(H.unescape(re.sub(r'<[^>]+>', ' ', m.group(2) or m.group(4) or '')).split())
                y = re.search(r'Ph\.?D\.?\s*-\s*(20\d\d)', body)
                a = re.search(r'Advisors?\s*[-:]\s*(.*?)(?=Research Interests|Employment|Thesis|After graduating|Honors|$)', body)
                if not (y and a and 2 <= len(nm.split()) <= 5) or int(y.group(1)) < 2016:
                    continue
                for pi, f in forms:
                    if re.search(re.escape(f) + r'(?![\w-])', a.group(1)) and (nm, pi) not in by:
                        i = flat.find(nm); k = flat.find(f, i) if i >= 0 else -1
                        if i < 0 or k < 0 or k - i > 400:
                            continue
                        by[(nm, pi)] = dict(student=nm, pi=pi, years=[None, int(y.group(1))], url=re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', cap),
                                            capture_url=cap if 'web.archive.org' in cap else None, sha256=sha, quote=flat[i:k + len(f)].strip(),
                                            directory_evidence=[dict(url=cap, sha256=sha, quote=nm, observed=r['timestamp'][:8], directory=d)],
                                            section='adviser-bearing alumni list (' + d + ')', years_basis='graduation_year')
    return list(by.values())


def paged_flat(c, cap, r, url):
    """The text of the other pages of a paged roster capture (`?page=N`, A-Z letters), each page's capture nearest in time within the same calendar year (Georgia Tech:
    the College of Computing PhD-student lists show 12 per page, so page 0 alone names a fifth of the students). '' when the capture is not paged."""
    import listing_formats as LF
    h = W.raw_html(c, cap)
    if not LF.is_paged(h):
        return ''
    out, ts0 = [], r['timestamp']
    for _, u in (LF.page_links(h, r['original']) or LF.letter_links(h, r['original'])).items():
        rows = [x for x in W.cdx_rows(c, re.sub(r'^https?://', '', u), frm=ts0[:4], to=ts0[:4], collapse=None) if x['timestamp'].startswith(ts0[:4])]
        if not rows:
            continue
        x = min(rows, key=lambda z: abs(int(z['timestamp'][:8]) - int(ts0[:8])))
        pc, st, _, pb = W.capture(c, x['timestamp'], x['original'], url, 'student-roster')
        if st == 200:
            out.append(W.flat(pb))
    return ' '.join(out)


AREA_PREFIX = re.compile(r'^(?:(?:Accounting|Finance|Marketing|Economics|Operations Management|Management Science|Econometrics (?:&|and) Statistics|Behavioral Science|Quantitative Marketing|Strategy|Entrepreneurship|Macroeconomics|Candidates)\s+)+')
CHAIR_RX = re.compile(r"([A-Z][\w.'\u2019-]+(?: (?:[A-Z][\w.'\u2019-]+|de|van|von|da))+)\s*\((?:Co-?)?[Cc]hair\b")


def defense_lists(key, forms, first_year):
    """Dissertation proposal/defense lists that name each student's committee chair (Booth `/phd/proposals-defenses`: a table of proposal or defense,
    student and area, date, committee with '(Chair)' / '(Co-chair)'; `/phd/job-market-candidates`: 'Dissertation Committee: A (Chair), ...'). A PI named
    as chair or co-chair gets the student: a proposal gives [year, year], a defense [None, year]; a row dated before the PI's first listing at the school
    is not read (appointment window). The quote is the student's cell through the committee cell, from the capture text. Charter
    `[students].defense_lists` (every Wayback capture 2016-2026 of each URL; the page keeps the recent years)."""
    import html as H
    c = W.con(key); by = {}
    for d in S.field(S.get(key), 'students.defense_lists') or []:
        for r in W.cdx_rows(c, d, collapse='timestamp:4'):
            cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], d, 'student-directory')
            if st != 200:
                continue
            h = W.raw_html(c, cap); flat = W.flat(b)
            items = []
            for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S | re.I):
                tds = [' '.join(H.unescape(re.sub(r'<[^>]+>', ' ', x)).split()) for x in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S | re.I)]
                if len(tds) == 4 and re.match(r'(Proposal|Defense)', tds[0]):
                    nm = re.sub(r'\s*\([^()]*\)\s*$', '', tds[1]).strip()   # only the trailing (area): 'Zi (Elaine) Ling (Management Science)' keeps 'Zi (Elaine) Ling'
                    y = re.search(r'(20[12]\d)', tds[2])
                    items.append((nm, 'defense' if tds[0].startswith('Defense') else 'proposal', int(y.group(1)) if y else None, tds[3], tds[1]))
            for m in re.finditer(r'([A-Z][\w.\'\u2019-]+(?: [A-Z][\w.\'\u2019-]+){1,3}) Job Market Paper:.*?Dissertation Committee: (.*?)(?: Research Interests|$)', flat):
                if len(AREA_PREFIX.sub('', m.group(1)).split()) > 3:
                    continue   # two candidates run together ('Zhouyu Shen Boxin Zhao'): round 12; the proposals/defenses list names the student anyway
                items.append((AREA_PREFIX.sub('', m.group(1)), 'jobmarket', int(r['timestamp'][:4]), m.group(2), AREA_PREFIX.sub('', m.group(1))))
            for nm, kind, y, com, cell in items:
                chairs = [x.group(1) for x in CHAIR_RX.finditer(com)]
                for pi, f in forms:
                    if any(re.fullmatch(re.escape(f), ch) or ch.endswith(f) or f.endswith(ch) for ch in chairs) and y and y >= first_year.get(pi, 2016) and y >= 2016:
                        i = flat.find(nm); k = flat.find(f, i) if i >= 0 else -1
                        if i < 0 or k < 0 or k - i > 700:
                            continue
                        yrs = [None, y] if kind == 'defense' else [y, y]
                        e = by.setdefault((nm, pi), dict(years=yrs, first=(r['timestamp'], cap, sha, d, flat[i:k + len(f) + 25], kind)))
                        a, z = e['years']
                        e['years'] = [None if (a is None or yrs[0] is None) else min(a, yrs[0]), max(z, yrs[1])]
    rows = []
    for (nm, pi), e in sorted(by.items()):
        ts, cap, sha, d, q, kind = e['first']
        rows.append(dict(student=nm, pi=pi, years=e['years'], url=re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', cap), capture_url=cap if 'web.archive.org' in cap else None,
                         sha256=sha, quote=q.strip(), directory_evidence=[dict(url=cap, sha256=sha, quote=nm, observed=ts[:8], directory=d, kind=kind)],
                         section='dissertation committee chair (' + d + ')', years_basis='defense_list'))
    return rows


def roster_coauthor_students(key, forms):
    """R-STU-33 supersedes roster/coauthor inference: no adviser, no PI row.

    A shared program roster and coauthored papers do not identify a supervisor,
    even when the PI is last author or there are several papers. Keep this
    compatibility entry point inert; per-row adviser directories and explicit
    student-owned advising statements remain the admission routes.
    """
    return []


def directory(key):
    """Students from the program directories' student websites (protocol stage 6, learned 2026-10-30 at Michigan): the
    student's own page, fetched like a lab page (live where robots and the charter allow, else Wayback), counts when it
    names the school, says PhD, and an adviser phrase ('advised by', 'under the supervision of', 'my advisor is',
    'Advisor:') stands directly before a PI's full-name form (R-STU-03; 'working with' does not count). The quote runs
    from the PhD mention (or the sentence start) to the PI's name; years are the directory years that list the student.
    -> hierarchy/<key>/directory-evidence.json, merged into labpage-evidence.json by extract."""
    c = W.con(key); rx = S.aff_rx(key); n = collections.Counter(); out = []
    pis = [(t['name'], [t['name']] + list(t.get('aliases') or [])) for t in PS.targets(key)]
    cf = json.loads((P.data('census-faculty.json', key)).read_text())   # a list (CMU) or {'faculty': [...]}
    cen = {x['name']: x for x in (cf if isinstance(cf, list) else cf.get('faculty', []))}
    add = {x['name']: x for x in json.loads((P.data('census-additions.json', key)).read_text())} if (P.data('census-additions.json', key)).exists() else {}
    forms = []
    for pi, _ in pis:
        x = cen.get(pi) or add.get(pi) or {}
        for f in [pi] + list(x.get('aliases') or []):
            f = re.sub(r'\s*\([^)]*\)\s*', ' ', f).strip()
            if len(f.split()) >= 2:
                forms.append((pi, f))
                t = f.split()
                if len(t) >= 3:  # 'Elliott J. Rouse' is also 'Elliott Rouse' (an initial between given and family name)
                    forms.append((pi, f'{t[0]} {t[-1]}'))
                fold = ''.join(ch for ch in __import__('unicodedata').normalize('NFD', f) if not __import__('unicodedata').combining(ch))
                if fold != f:
                    forms.append((pi, fold))
    forms = sorted(set(forms) | set(nickname_forms(forms)), key=lambda x: -len(x[1]))
    ents = directory_entries(key)
    n['directory_students'] = len(ents); n['with_website'] = sum(1 for e in ents.values() if e['websites'])
    for name, e in ents.items():
        for u in e['websites'][:1]:
            fetch(key, c, u, min(e['years']))
            for cited, sha, h, year in stored_pages(c, u):
                flat = ' '.join(__import__('html').unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style)\b.*?</\1>', ' ', h, flags=re.S | re.I))).split())
                if not rx.search(flat) or not PHD.search(flat):
                    n['page_without_school_or_phd'] += 1; continue
                got = set()
                for pi, f in forms:
                    if pi in got:
                        continue
                    for m in re.finditer(re.escape(f) + r'(?![\w-])', flat):
                        pre = flat[max(0, m.start() - 90):m.start()]
                        a = ADVISED.search(pre)
                        if not a:
                            continue
                        k0 = m.start() - len(pre) + a.start()
                        ph = [p_.start() for p_ in PHD.finditer(flat, max(0, k0 - 300), k0)]
                        k = ph[-1] if ph else max(flat.rfind('. ', 0, k0) + 2, k0 - 200, 0)
                        out.append(dict(student=name, pi=pi, years=[min(e['years']), max(e['years'])], url=re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', cited),
                                        capture_url=cited if 'web.archive.org' in cited else None, sha256=sha, quote=flat[k:m.end()], directory_evidence=e['evidence']))
                        got.add(pi); n['relations'] += 1
                        break
                if got:
                    break
    out += adviser_directory(key, forms)
    out += adviser_alumni(key, forms)
    out += defense_lists(key, forms, {t['name']: t['first'] for t in PS.targets(key)})
    out += adviser_flat_lists(key, forms)
    out += adviser_h4_lists(key, forms)
    out += roster_coauthor_students(key, forms)
    n['adviser_directory_relations'] = sum(1 for r in out if str(r.get('section')).startswith('adviser'))   # adviser-bearing lists (current and alumni)
    n['roster_coauthor_relations'] = sum(1 for r in out if str(r.get('section')).startswith('PhD roster'))
    P.data_w('directory-evidence.json', key).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(n, students_with_adviser=len({r['student'] for r in out}), labs=len({r['pi'] for r in out}))))


# --- R-STU-14 capture-year dating, R-STU-15 surname-only advisers (owner 2026-11-03) ------------------------------------------------------------

def capture_year(url, fallback=None):
    """The year of the Wayback capture a URL names (/web/YYYYMMDDhhmmss...), else the fallback (a live fetch's year)."""
    m = re.search(r'/web/(\d{4})\d{0,10}', url or '')
    return int(m.group(1)) if m else fallback


STUDENT_HEAD = re.compile(r'^\W*(?:current\s+)?(?:ph\.?\s?d\.?|doctoral|graduate|grad\b|students?|members?|team|people|research(?:ers| group)|lab members)', re.I)
NOT_A_LIST = re.compile(r'\b(?:publications?|papers?|arXiv|conference|journal|proceedings|et al|professor|postdoc\w*|alumni|former|past|collaborat\w+|coauthors?|talks?|news|teaching|courses?)\b|@|\bwith\b|[;]', re.I)
NAME_PARTICLES = {'de', 'van', 'von', 'der', 'da', 'di', 'del', 'la', 'le', 'bin', 'al', 'dos', 'du', 'den'}


def member_list_quote_ok(quote, name):
    """R-STU-14: the verbatim quote must be a heading followed by a plain list of names up to this one: it opens with a student / people heading, holds no
    publication, title, collaborator or e-mail cue and no more than two lowercase words before the name (a list of paper titles, a citation byline or a
    sentence is not a member list)."""
    i = quote.find(name)
    if i <= 0 or not STUDENT_HEAD.search(quote) or '(' in name or '@' in name:
        return False
    pre = quote[:i]
    if NOT_A_LIST.search(pre) or ':' in pre.replace('Students :', '').replace('Students:', '')[:0]:
        return False
    low = [w for w in re.findall(r"[^\W\d_][\w'-]*", pre) if w[0].islower() and w.lower() not in NAME_PARTICLES]
    return len(low) <= 2


def undated_capture_rows(records, page_head=None):
    """R-STU-14: from lab-page audit records (labpage-audit.jsonl.gz) the members the audit set aside as `undated_cannot_place`: an undated entry under a
    PhD-student heading of a lab page. Such a member is that lab's student in the year of the capture (Wayback, or live) that shows them, never earlier or
    later; the same person on captures of several years gets the span of those capture years. Not kept: a member under an alumni / past / former heading
    (the capture year is not a membership year), any role but `phd` or `visiting` (R-STU-17), a name without a verbatim quote and a sha256, a PI whose family name is one letter (a placeholder
    row), a page that does not name the PI within its first 400 characters (`page_head(sha256)` -> that text; a centre or group page that lists the PI among
    several leads does not make the PI the members' adviser). -> [{pi, student, years, ...}]."""
    by = {}
    for r in records:
        fb = int(str(r.get('audited_at') or '0')[:4]) or None
        if len(r['pi'].split()[-1].strip('.')) < 2:
            continue
        for x in (r.get('students') or {}).get('missing_from_build') or []:
            if x.get('reason_code') != 'undated_cannot_place' or x.get('role') not in ('phd', 'visiting'):
                continue
            if ALUM.search(x.get('section') or '') or ALUM.search((x.get('quote') or '')[:200]) or not (x.get('quote') and x.get('sha256') and x.get('url')) \
                    or not member_list_quote_ok(x['quote'], x['name']):
                continue
            y = capture_year(x['url'], fb)
            if not y or not 2016 <= y <= 2026:
                continue
            if page_head is not None and r['pi'].split()[-1].lower() not in (page_head(x['sha256']) or '').lower():
                continue
            k = (r['pi'], ' '.join(toks(x['name'])))
            e = by.setdefault(k, dict(pi=r['pi'], student=x['name'], years=set(), first=None))
            e['years'].add(y)
            if not e['first'] or y < e['first'][0]:
                e['first'] = (y, x)
    rows = []
    for (pi, _), e in sorted(by.items()):
        y, x = e['first']
        rows.append(dict(pi=pi, student=e['student'], years=[min(e['years']), max(e['years'])], years_basis='capture_date', role=x.get('role') or 'phd', section=x.get('section'),
                         url=re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', x['url']), capture_url=x['url'] if 'web.archive.org' in x['url'] else None,
                         sha256=x['sha256'], quote=x['quote'], auto=True))
    return rows


def undated_capture(key):
    """R-STU-14 for a school: `labpage_students_school.py undated <key>` -> hierarchy/<key>/reviewed/undated-capture-evidence.json (a RESEARCHED_FILES file)."""
    import gzip
    recs = [json.loads(line) for line in gzip.open(P.data('labpage-audit.jsonl.gz', key), 'rt')]
    import html as H
    import sqlite3
    import zlib
    dbs = [sqlite3.connect(f"file:{P.data(n, key)}?mode=ro", uri=True) for n in ('labpage-audit-captures.sqlite', 'labpage-captures.sqlite') if P.data(n, key).exists()]

    def head(sha):
        for c_ in dbs:
            r_ = c_.execute('select content from captures where sha256=? and content is not null limit 1', (sha,)).fetchone()
            if r_:
                b = r_[0]
                try:
                    b = zlib.decompress(b)
                except Exception:  # noqa: BLE001 (stored uncompressed)
                    pass
                t = b.decode('utf-8', 'replace') if isinstance(b, bytes) else b
                t = re.sub(r'<(script|style)\b.*?</\1>', ' ', t, flags=re.S | re.I)
                return ' '.join(H.unescape(re.sub(r'<[^>]+>', ' ', t)).split())[:400]
        return None
    rows = undated_capture_rows(recs, head)
    by = collections.OrderedDict()
    for r in rows:
        by.setdefault(r['pi'], []).append({k: v for k, v in r.items() if k not in ('pi', 'student')} | dict(name=r['student'], alumni=False))
    out = [dict(pi=pi, lab_site=None, people_page=None, students=ss) for pi, ss in by.items()]
    P.data_w('undated-capture-evidence.json', key).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(relations=len(rows), labs=len(out))))


SURNAME_ENTRY = re.compile(r"(?P<name>[A-Z][^\s,]*(?: [A-Z][^\s,]*){1,3}) (?P<uid>[a-z][a-z0-9]{2,9}) (?P<prog>PhD|MSE|MS)\b"
                           r"(?: Research Advis[eo]rs?:? (?P<adv>(?:[A-Z][^\s,]*, )*[A-Z][^\s,]*))?")


def surname_entries(flat):
    """R-STU-15: [(student, program, [adviser surnames], quote)] of a student list that names each PhD student's adviser by surname only
    ('<First Last> <uniqname> PhD Research Advisor: Brei, Luntz'): the adviser list is the comma-joined surnames, which ends at the first
    one without a trailing comma. PhD entries with an adviser only."""
    i = flat.find("Advisor's Last Name")
    t = flat[i + len("Advisor's Last Name"):] if i >= 0 else flat
    out = []
    for m in SURNAME_ENTRY.finditer(t):
        if m.group('prog') == 'PhD' and m.group('adv'):
            out.append((m.group('name'), 'PhD', [a.strip(' ,') for a in m.group('adv').split(', ')], t[m.start():m.end()]))
    return out


def adviser_column_entries(html):
    """R-STU-15, table form (UW CSE public graduate directory, norfolk.cs.washington.edu/htbin-php/public/grad/, 2026-11-23): a table whose
    header has an 'Advisor' column; each row's first cell is 'Family, Given' and the adviser cell holds comma-separated surnames, a trailing
    '*' marking a temporary adviser (header 'Advisor (* Temp)'), which is never read as an adviser. Only the name and adviser cells are read
    (the office, phone, email and NetID cells never are); the quote is the name cell, ' … ', the adviser cell, as Princeton's directory quotes
    elide the cells between. -> [(student 'Given Family', 'PhD', [surnames], quote)]"""
    import html as H
    cell = lambda s: ' '.join(H.unescape(re.sub(r'<[^>]+>', ' ', s)).split())  # noqa: E731
    out = []; col = None
    for row in re.findall(r'<tr[^>]*>(.*?)</tr>', html or '', re.S | re.I):
        if col is None:
            heads = [cell(x) for x in re.findall(r'<th[^>]*>(.*?)</th>', row, re.S | re.I)]
            col = next((i for i, h in enumerate(heads) if re.match(r'advis[oe]r', h, re.I)), None)
            if col is not None:
                col = (col, len(heads))
            continue
        tds = [cell(x) for x in re.findall(r'<td[^>]*>(.*?)</td>', row, re.S | re.I)]
        if len(tds) != col[1]:
            continue
        nm, adv = tds[0], tds[col[0]]
        m = re.fullmatch(r"([A-Z][\w'’ .-]+),\s+([A-Z][\w'’ .-]+)", nm)
        if not m or not adv:
            continue
        advs = [a.strip() for a in adv.split(',') if a.strip() and not a.strip().endswith('*')]
        if advs:
            out.append((f'{m.group(2)} {m.group(1)}', 'PhD', advs, f'{nm} … {adv}'))
    return out


def resolve_surname(sur, dept, year, listed):
    """R-STU-15: the one faculty member of `dept` listed in `year` with this family name, else None. `listed` = [(pi, family name, dept, year)] from the
    school's dated faculty listings. Zero or several faculty with the surname resolve nothing; a department without a listing for the year resolves nothing."""
    f = lambda s: ''.join(ch for ch in __import__('unicodedata').normalize('NFD', s) if not __import__('unicodedata').combining(ch)).lower()  # noqa: E731
    # 'N. Smith' (UW CSE's directory disambiguates a shared surname with the given initial): the PI's given name must start with it;
    # 'Oveis Gharan' (a compound family name) matches the end of the PI's full name (2026-11-23)
    m = re.fullmatch(r'([A-Z])\.\s*(\S.*)', sur.strip())
    ini, sur = (m.group(1), m.group(2)) if m else (None, sur.strip())
    hit = {pi for pi, fam, d, y in listed if d == dept and y == year and (f(fam) == f(sur) or (' ' in sur and f(pi).endswith(' ' + f(sur))))
           and (ini is None or pi[:1].upper() == ini)}
    return next(iter(hit)) if len(hit) == 1 else None


def surname_advisers(key):
    """R-STU-15 for a school: charter `[students].surname_adviser_lists` = [{url, department}] (Wayback captures); a student whose adviser surname
    resolves (resolve_surname, in the capture's year and the list's department) is that PI's student in the capture years. Quote = the student's own
    entry through the adviser surnames. -> hierarchy/<key>/reviewed/surname-adviser-evidence.json (a RESEARCHED_FILES file)."""
    c = W.con(key)
    listed = []
    for p in json.loads(P.data('pis.json', key).read_text()):
        for ln in p.get('listings') or []:
            if str(ln.get('kind', '')).startswith(('unit_listing:', 'dept_listing:')) and ln.get('year'):   # a department's own listing too (UW CSE, 2026-11-23)
                listed.append((p['pi'], p['pi'].split()[-1], ln['kind'].split(':', 1)[1], int(ln['year'])))
    by = {}; n = collections.Counter()
    for lst in S.field(S.get(key), 'students.surname_adviser_lists') or []:
        for r in W.cdx_rows(c, lst['url'], collapse='timestamp:4'):
            cap, st, sha, b = W.capture(c, r['timestamp'], r['original'], lst['url'], 'student-directory')
            if st != 200:
                continue
            y = int(r['timestamp'][:4])
            ents = adviser_column_entries(W.raw_html(c, cap)) if lst.get('format') == 'adviser_column_table' else surname_entries(W.flat(b))
            for nm, _, advs, q in ents:
                for a in advs:
                    pi = resolve_surname(a, lst['department'], y, listed)
                    n['resolved' if pi else 'skipped'] += 1
                    if not pi:
                        continue
                    e = by.setdefault((nm, pi), dict(years=set(), first=None))
                    e['years'].add(y)
                    if not e['first'] or r['timestamp'] < e['first'][0]:
                        e['first'] = (r['timestamp'], cap, sha, q, lst['url'])
    out = collections.OrderedDict()
    for (nm, pi), e in sorted(by.items()):
        ts, cap, sha, q, lurl = e['first']
        out.setdefault(pi, []).append(dict(name=nm, role='phd', years=[min(e['years']), max(e['years'])], years_basis='directory_years', alumni=False,
                                           section='surname-only adviser list (' + lurl + ')', url=re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', cap),
                                           capture_url=cap if 'web.archive.org' in cap else None, sha256=sha, quote=q[:600], auto=True))
    P.data_w('surname-adviser-evidence.json', key).write_text(json.dumps([dict(pi=pi, lab_site=None, people_page=None, students=ss) for pi, ss in out.items()], indent=1, ensure_ascii=False))
    print(json.dumps(dict(n, relations=sum(len(v) for v in out.values()), labs=len(out))))


GENERIC_STUDENT_HEAD = re.compile(r"^\W*(?:(?:current|former|past|my|our)\s+)?(?:students|student\s+members|advisees|advising|mentees|(?:under)?graduate\s+(?:members|researchers))\W*(?:\(.*\))?\W*$", re.I)


def generic_student_role(role, path):
    """A lab page whose members sit under a plain 'Students' / 'Advisees' / 'Advising' heading names students without a degree level (Qi: 'Students', Hoza:
    'Advising'): the role is 'student' (a member of the lab, R-STU-19 B's student role), not a dropped row. A heading that names a degree or a non-student
    group keeps lpdom's reading (UChicago round 2)."""
    if role is None and path and GENERIC_STUDENT_HEAD.match(path[-1].strip()):
        return 'student'
    return role


def generic_graduate_role(role, path, rest):
    """A graduate-student heading does not choose a doctoral degree."""
    generic = re.compile(r"^\W*(?:(?:current|former|past|my|our)\s+)?(?:graduate|grad)\s+students?\W*$", re.I)
    if role == 'phd' and any(generic.match(head) for head in path):
        last_generic = max(i for i, head in enumerate(path) if generic.match(head))
        if any(re.search(r'ph\.?\s*d|doctoral|doctorate', head, re.I) for head in path[last_generic + 1:]):
            return role
        # The entry can state its own degree; later employment and other
        # people's names in an ancestor heading cannot supply one.
        own = re.match(r"^\s*[,;:(-]*\s*(?:ph\.?\s*d\.?|doctoral|doctorate)\b", rest or '', re.I)
        if not own:
            return 'graduate'
    return role


def mixed_heading_role(role, path, rest):
    """(role, role as written) of a member under a heading that names PhD students AND postdocs ('Alumni (PhDs and Postdocs)'): the entry's own words decide
    when they state it ('Fan Yao (PhD, 2025 ...)', 'Andrzej Kaczmarczyk (postdoc, 2025)'); only an entry that says neither stays 'member' (UChicago round 2, Xu's
    SIGMA alumni: five PhDs and one postdoc were all read as 'member')."""
    if role in ('phd', 'postdoc') and path and re.search(r'ph\.?\s?d|doctoral', path[-1], re.I) and re.search(r'post-?doc', path[-1], re.I):
        r60 = (rest or '')[:60]
        m_phd, m_post = re.search(r'ph\.?\s?d|doctoral', r60, re.I), re.search(r'post-?doc', r60, re.I)
        own = None if not (m_phd or m_post) else 'phd' if (m_phd and (not m_post or m_phd.start() < m_post.start())) else 'postdoc'   # 'Ph.D. 2025, Post Doc @ UIUC': the degree first, the employer after
        if own:
            return own, own
        return 'phd', 'member'   # neither is stated: a member (the heading names both kinds), never dropped as a postdoc
    return role, role


def extract(key):
    c = W.con(key); ev, rep = [], collections.Counter()
    prev = previous_school_students(key); dropped_prev = []
    first_year = {t['name']: min(t.get('years') or [9999]) for t in PS.targets(key)}
    fac = []  # the school's listed faculty: a co-adviser named in a students list is not a student
    cf = json.loads((P.data('census-faculty.json', key)).read_text())   # a list (CMU) or {'faculty': [...]} (the other schools)
    for x in (cf if isinstance(cf, list) else cf.get('faculty', [])) + \
            (json.loads((P.data('census-additions.json', key)).read_text()) if (P.data('census-additions.json', key)).exists() else []):
        fac.append(Name([x['name']] + list(x.get('aliases') or [])))
    faculty_anywhere = all_faculty_names()
    skip_pages = S.field(S.get(key), 'labpages.skip_pages') or []
    decisions = SD.load(key)
    ef_ = P.data('extra-lab-pages.json', key)
    reviewed_pages = {pi_: [re.sub(r'^https?://(www\.)?', '', x['url']) for x in l_] for pi_, l_ in (json.loads(ef_.read_text()) if ef_.exists() else {}).items()}
    for pi, (t, urls) in targets_pages(key).items():
        N = Name([pi]); studs, seen = [], set()
        for u in urls:
            if any(re.sub(r'^https?://(www\.)?', '', u).rstrip('/') == re.sub(r'^https?://(www\.)?', '', x['url']).rstrip('/') for x in skip_pages):
                rep['reviewed_skipped_page'] += 1; continue   # a page a reviewer judged not to list this lab's members at the school ([labpages].skip_pages, with why)
            for cited, sha, h, year in stored_pages(c, u):
                try:
                    cands, _ = lpdom.member_candidates(h.encode('utf-8', 'replace'), u)
                except Exception:  # noqa: BLE001 (a page lpdom cannot linearise has no candidates)
                    continue
                flat = ' '.join(lpdom.collapse(x) for x in [re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style)\b.*?</\1>', ' ', h, flags=re.S | re.I))])
                flat = ' '.join(__import__('html').unescape(flat).split())
                if is_department_roster(flat, faculty_anywhere) or (len(cands) >= 60 and not any(u.rstrip('/').endswith(e.rstrip('/')) for e in reviewed_pages.get(pi, ()))):   # a reviewed lab page may be long (AxLab's 140 members)
                    rep['department_roster_page_skipped'] += 1; continue   # a department people page names many faculty: not this PI's lab page (UChicago homepage dive)
                for path, name, rest, nxt, idx in cands:
                    name = clean_student_name(name)
                    if SD.excluded(decisions, pi, name):
                        rep['reviewed_decision_dropped'] += 1; continue   # decided not / unclear for this lab (student-decisions.json)
                    vis = V.visiting_role(rest, ' > '.join(path), lambda t: (lpdom.role_of(t), None))   # R-STU-17: student wording required; visiting faculty, scientists, scholars are not
                    if (path and any(NOT_STUDENT_HEAD.match(x) and not (vis and V.says_visiting(x)) for x in path)) or ' '.join(toks(name)) in faculty_anywhere:
                        rep['dropped_hiring_or_faculty'] += 1; continue
                    role = 'visiting' if vis else lpdom.role_of(*(list(reversed(path)) + [rest]))
                    role = generic_student_role(role, path)
                    role = generic_graduate_role(role, path, rest)
                    role, role_out = mixed_heading_role(role, path, rest)
                    if role not in ('phd', 'postdoc', 'visiting', 'student', 'graduate') or not lpdom.looks_like_name(name) or not lpdom.plausible_person(name) \
                            or N.match(name) or len(toks(name)) < 2 or len(toks(name)) > 4 or any(F.match(name) for F in fac):
                        rep['dropped_not_a_student_name'] += 1; continue
                    if role_out == 'postdoc':
                        rep['dropped_postdoc'] += 1; continue   # a postdoc is not a student (R-STU-19 B); mixed 'PhDs and Postdocs' headings now give the entry's own role
                    alum = any(ALUM.search(x) for x in path)  # the section says it, not the person's line ('now Ph.D. student @ ...')
                    head = path[-1] if path else ''
                    j = flat.find(name)
                    i = flat.rfind(head, 0, j) if head and j >= 0 else -1
                    a_at = alumni_in_text(flat, i, j) if j >= 0 else None
                    if a_at is not None and not alum:
                        alum = True; rep['alumni_by_page_text'] += 1
                    ys = lpdom.years_in(rest)
                    if alum and not ys:  # a graduate without a stated year cannot be placed in the window
                        rep['dropped_alumnus_without_year'] += 1; continue
                    years = [y for y in (ys or []) if y] or [year]
                    if max(years) < 2016:
                        rep['dropped_before_window'] += 1; continue
                    if alum and ys and max(years) <= first_year.get(pi, 0) and not re.search(r'chicago|uchicago|ttic', rest, re.I):
                        rep['dropped_alumnus_before_arrival'] += 1; continue   # an alumnus who left in or before the PI's first year here was the PI's student elsewhere (Zhang's ETH PhDs, Tomlin's Berkeley advisees)
                    if j < 0 or i < 0 or j - i > 600:  # the quote must run from the section heading to the name
                        rep['dropped_no_heading_quote'] += 1; continue
                    if a_at is not None and a_at < i and j - a_at <= 600:
                        i = a_at  # the quote shows the alumni marker too
                    q = flat[i:j + len(name)]
                    if pi in prev and any(M.match(name) for M in prev[pi][1]) and not (ys and min(years) >= first_year.get(pi, 0)):
                        rep['dropped_previous_school_student'] += 1
                        dropped_prev.append(dict(pi=pi, student=name, school=prev[pi][0], url=cited)); continue
                    k = (' '.join(toks(name)), role)
                    if k in seen:
                        continue
                    seen.add(k)
                    studs.append(dict(name=name, role=role_out + ('_alumnus' if alum and role_out not in ('member', 'visiting', 'graduate') else ''), years=[min(years), max(years)],
                                      years_basis='stated' if ys else 'capture_date', alumni=alum, section=' › '.join(path)[:200],
                                      url=re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', cited), capture_url=cited if 'web.archive.org' in cited else None,
                                      sha256=sha, quote=q, auto=True))
        if studs:
            ev.append(dict(pi=pi, lab_site=t['urls'][0] if t['urls'] else None, people_page=studs[0]['url'], students=studs))
            rep['labs_with_students'] += 1; rep['students'] += len(studs)
        else:
            rep['labs_without'] += 1
    # a page that yields students for five or more PIs is a department's page, not any one PI's lab page ('current graduate students' linked from every
    # profile gave all JHU labs the same staff member; HJW 2026-11-07): its rows go, unless a reviewer listed it for that PI (extra-lab-pages.json)
    page_pis = collections.defaultdict(set)
    for e in ev:
        for s_ in e['students']:
            page_pis[s_['sha256']].add(e['pi'])
    shared = {h for h, v in page_pis.items() if len(v) >= 5}
    if shared:
        keep = []
        for e in ev:
            ok = [s_ for s_ in e['students'] if s_['sha256'] not in shared or any(s_['url'].rstrip('/').endswith(x.rstrip('/')) for x in reviewed_pages.get(e['pi'], ()))]
            rep['shared_page_students_dropped'] += len(e['students']) - len(ok)
            if ok:
                keep.append(dict(e, students=ok))
        ev = keep
        rep['labs_with_students'] = len(ev); rep['students'] = sum(len(e['students']) for e in ev)
    dfs = json.loads((P.data('defense-evidence.json', key)).read_text()) if (P.data('defense-evidence.json', key)).exists() else []
    by_pi = {e['pi']: e for e in ev}
    pis = {t['name']: Name([t['name']]) for t in PS.targets(key)}
    for d in dfs:
        hit = [pi for pi, N_ in pis.items() if N_.match(d['host'])]
        if len(hit) != 1 or not (2016 <= d['year'] <= 2026):
            rep['defense_host_not_one_pi'] += 1; continue
        e = by_pi.setdefault(hit[0], dict(pi=hit[0], lab_site=None, people_page=None, students=[]))
        if e not in ev:
            ev.append(e)
        e['students'].append(dict(name=d['student'], role='phd_alumnus', years=[d['year'], d['year']], years_basis='defense_date', alumni=True,
                                  section='dissertation defense announcement', url=d['url'], capture_url=d['capture_url'], sha256=d['sha256'],
                                  quote=d['quote'], host_quote=d['host_quote'], auto=True))
        rep['defense_students'] += 1
    dirs = json.loads((P.data('directory-evidence.json', key)).read_text()) if (P.data('directory-evidence.json', key)).exists() else []
    cvf = P.data('cv-evidence.json', key)
    dirs = dirs + (json.loads(cvf.read_text()).get('rows') or [] if cvf.exists() else [])   # students named in the PIs' own CVs (tools/cv_students.py)
    for nm_ in ('wikidata-evidence.json',):   # students other sources name (tools/wikidata_students.py), same row shape
        xf = P.data(nm_, key)
        dirs = dirs + (json.loads(xf.read_text()).get('rows') or [] if xf.exists() else [])
    for d in dirs:
        e = by_pi.setdefault(d['pi'], dict(pi=d['pi'], lab_site=None, people_page=None, students=[]))
        if e not in ev:
            ev.append(e)
        if any(Name([s_['name']]).match(d['student']) for s_ in e['students']):
            rep['directory_student_already_listed'] += 1
        e['students'].append(dict(name=d['student'], role=d.get('role') or 'phd', years=d['years'], years_basis='directory_years', alumni=False,
                                  section=d.get('section') or "student's own page (program PhD directory website)", url=d['url'], capture_url=d['capture_url'],
                                  sha256=d['sha256'], quote=d['quote'], directory_evidence=d['directory_evidence'], auto=True,
                                  **({'host_quote': d['host_quote']} if d.get('host_quote') else {})))
        rep['directory_students'] += 1
    P.data_w('labpage-evidence.json', key).write_text(json.dumps(ev, indent=1, ensure_ascii=False))
    P.data_w('labpage-students-report.json', key).write_text(json.dumps(dict(rep, previous_school_pis={k: v[0] for k, v in prev.items()},
                                                                                 dropped_previous_school=dropped_prev), indent=1))
    print(json.dumps(dict(rep)))


if __name__ == '__main__':
    if sys.argv[1] == 'sources':
        import student_source_discovery
        student_source_discovery.main(sys.argv[2], sys.argv[3:])
    else:
        {'links': links, 'defenses': defenses, 'directory': directory, 'extract': extract, 'undated': undated_capture, 'surname': surname_advisers}[sys.argv[1]](sys.argv[2])
