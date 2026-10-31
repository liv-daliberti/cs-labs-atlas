"""Lab-page audit: for every PI lab of a school, is there a lab page, are all its students and alumni in the build, and
are all its listed papers among the lab's papers? Every gap gets a reason from a fixed vocabulary (docs/LAB-PAGES.md).

One config-driven tool for every school (SCHOOLS below). It reuses the lab-page pass's own fetch and parse code instead
of forking it: the fetcher and capture stores of hierarchy/labpage-tools-princeton-mit (lpcap, lpev), its member
extractor (autom.extract) and publication extractor (pubx.extract), the cross-school name matcher (names.match), and
tools/labpage_recover.py for resolving listed papers to works and judging them under the build's own rule.

steps (each school; `all` runs discover -> recover -> audit)
  discover  network, run on Slurm (hierarchy/labpage-audit.slurm). For every PI lab without a lab-page record (never
            searched), with none found, or whose page was never captured: the department listing -> the PI's school
            profile -> its website/lab links; the DBLP person's homepage URLs (local dump extract); the PI's ORCID
            researcher URLs (pub.orcid.org); earlier homepage finds and the PI's own evidence URLs; then the candidate
            site, its people / alumni / publications links, and up to three Wayback id_ captures (2016-2026) of each
            people or alumni page. For labs already recorded: the ORCID check, and alumni / publications links on the
            stored lab and people pages that were never captured. Every place checked is recorded with its date and
            result -> hierarchy/<school>/labpage-audit-discovery.json; captures -> labpage-audit-captures.sqlite.
  recover   network (OpenAlex, arXiv page 1). Every listed in-window paper that is not a lab paper goes through
            tools/labpage_recover.run in a private shadow tree (hierarchy/<school>/labpage-audit-recover/), so nothing
            the build reads changes: its parse (junk: talks, patents, theses, headings), resolution (sweep, PI works,
            arXiv, OpenAlex) and the build's rule (PI on the byline, appointment, school authorship or page 1) give each
            paper its reason. The accepted ones become proposed additions.
  audit     offline -> hierarchy/<school>/labpage-audit.jsonl.gz (one record per PI lab), labpage-additions.json
            (proposed students and papers, each with evidence and the admitting rule), and the school's summary row.
  summary   hierarchy/labpage-audit-summary.json and hierarchy/LABPAGE-AUDIT.md over the schools audited so far.

Fetching: robots.txt honoured, including groups naming ClaudeBot, anthropic-ai, Claude-Web (AI_AGENTS); at least 3 s
between requests to a host (Wayback 6 s); a bot challenge is stored and never retried, and that host is then read only
from existing Wayback id_ captures; dblp.org, Scholar and eScholarship are never fetched (lpcap.BLOCKED_RX); the
owner's e-mail is never sent. Schools whose charter marks hosts as never-used (Michigan: Deep Blue, news.umich.edu,
record.umich.edu) are read-only here (`read_only`): the audit reads that school's own lab-page outputs.

usage: labpage_audit.py discover|recover|audit|all <school> [--pi NAME ...]
       labpage_audit.py summary
"""
import argparse
import collections
import copy
import datetime
import gzip
import hashlib
import json
import os
import re
import sqlite3
import sys
import unicodedata
import zlib
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

H = P.HIERARCHY
WINDOW = (2016, 2026)
AI_AGENTS = ('ClaudeBot', 'anthropic-ai', 'Claude-Web', 'Claude-User', 'Claude-SearchBot')
HOST_GAP = 3.0
OPENALEX_FLOOR = 6000  # the shared key allows 10,000 credits a day (X-RateLimit-Limit): stop resolving below 6,000 left, ~4k a day at most
WAYBACK_GAP = 6.0
TODAY = datetime.date.today().isoformat()

# ---------------------------------------------------------------- reason vocabularies (docs/LAB-PAGES.md)
LAB_STATUS = ('found', 'none_found', 'not_applicable')
LAB_REASONS = {
    'lab_site': 'a lab or group site (its own site or page, naming a lab/group) exists and was audited',
    'pi_homepage_only_no_lab_site': "no lab site; the PI's own homepage is the lab page and was audited for students and papers",
    'no_web_presence_found': 'no homepage or lab site at the school profile, department listing, DBLP, ORCID, earlier finds or Wayback',
    'profile_only_no_homepage': 'only the department profile page exists (no homepage or lab site linked anywhere)',
    'site_dead_no_wayback': 'the known site no longer answers and Wayback holds no capture',
    'host_blocked_by_robots': "robots.txt disallows the site for our agent or for AI agents by name, and Wayback holds no capture",
    'host_challenge_no_wayback': 'the host serves a bot challenge and Wayback holds no capture',
    'pi_left_school_site_moved': "the PI left the school; the live site is at the new institution and the school-era site is gone",
    'emeritus_or_admin_no_lab': 'emeritus or administrative appointment with no lab site',
    'new_arrival_no_site_yet': 'joined the school recently; no school lab site yet',
    'site_at_other_institution': "the only site found is at another institution (a joint or previous appointment), not this school's lab page",
}
STUDENT_PAGE_STATUS = ('audited', 'no_people_section', 'no_lab_page', 'page_not_captured')
STUDENT_REASONS = {
    'in_build': 'the listed person is a student record of this lab in the build',
    'not_a_student': 'listed under faculty / collaborators / staff, or a PI of the school, or reviewer-excluded as not a member',
    'outside_2016_2026': 'stated years end before 2016',
    'at_previous_school': "stated years end before the PI's appointment at this school (the PI's previous institution)",
    'undated_alumni_cannot_place': 'an undated alumni entry on a page of a lab older than the window: cannot be placed in 2016-2026 at this school',
    'not_in_people_section': 'a name on an archived capture outside any people heading (captures are not reviewed one by one)',
    'name_unresolved': 'a fragment, first name only, or not a person name',
    'merged_under_variant': 'in the build under another spelling of the same name (within this lab)',
    'dropped_by_review': 'in the reviewed corrections (hierarchy/student-corrections.json) as not this lab',
    'shared_page_no_adviser': 'a people page several PIs share (a centre or group listing); the entry does not name this PI as adviser',
    'after_pi_left': "the PI left the school; the entry is undated or dated after the move (another institution's member)",
    'reviewer_excluded': 'the 2026-10-22 lab-page reviewer excluded the name or its section (non-person, collaborator, other lab)',
    'undated_cannot_place': 'the page lists members of every era without dates and the reviewer required dates',
    'evidence_not_in_build': 'in labpage-evidence.json but in no student record of the lab (a build-side loss to check)',
    'genuinely_missing': 'a listed member placeable in 2016-2026 at this school who is not in the build: a gap, proposed as an addition',
}
PAPER_PAGE_STATUS = ('audited', 'no_pubs_page', 'external_index_only', 'no_lab_page', 'page_not_captured', 'page_unparseable')
PAPER_REASONS = {
    'outside_window': 'listed year outside 2016-2026 (or the resolved work is)',
    'undated_entry': 'the entry shows no year and matches no lab paper',
    'not_a_paper': 'a talk, patent, thesis, award, service or news line, or a non-paper record',
    'parse_artifact': 'a heading, venue-only, author-only line or fragment cut out of the page, not an entry',
    'pi_not_author': "the resolved work's byline does not carry the PI (a student-only paper; R-PAP preamble (b))",
    'from_previous_school': "the work dates from before the PI's appointment at this school (R-PAP-01)",
    'outside_appointment': "the work falls outside the PI's reviewed periods and listed years at this school (R-PAP-01)",
    'other_institution_affiliation': "the PI's authorship lists only other institutions (R-PAP preamble (a))",
    'no_school_affiliation_evidence': "the PI's authorship lists no institution and page 1 does not tie the school to the PI",
    'unresolved_metadata': 'no OpenAlex, arXiv or proceedings record matches the listed title',
    'not_yet_resolved': 'the resolution step has not judged this entry yet',
    'genuinely_missing': 'resolves to a work that passes the build rule but is not a lab paper: proposed as an addition',
}

# ---------------------------------------------------------------- schools
PM = 'labpage-tools-princeton-mit'
SCHOOLS = {
    'princeton': dict(family='pm', tools=PM, plan='plan_princeton', dossier='dossier_princeton.json', domain=r'princeton\.edu',
                      extra_stores=['gap-captures.sqlite', 'few-students-captures.sqlite', 'thesis-captures.sqlite',
                                    'cs-related-captures.sqlite']),
    'mit': dict(family='pm', tools=PM, plan='plan_mit', dossier='dossier_mit.json', domain=r'mit\.edu',
                extra_stores=['gap-captures.sqlite', 'few-students-captures.sqlite', 'thesis-captures.sqlite']),
    'cmu': dict(family='cmu', tools='labpage-tools-cmu', domain=r'cmu\.edu'),
    'epfl': dict(family='eb', tools='labpage-tools-epfl-berkeley', domain=r'epfl\.ch'),
    'berkeley': dict(family='eb', tools='labpage-tools-epfl-berkeley', domain=r'berkeley\.edu'),
    'stanford': dict(family='st', tools='labpage-tools-stanford', domain=r'stanford\.edu'),
    'michigan': dict(family='michigan', domain=r'umich\.edu'),
}
SCHOOL_NAMES = dict(princeton=r'Princeton', mit=r'MIT|Massachusetts Institute', cmu=r'CMU|Carnegie Mellon', epfl=r'EPFL|[EÉ]cole Polytechnique',
                    berkeley=r'Berkeley|UCB', stanford=r'Stanford', michigan=r'Michigan|UMich|U-M\b')
DEGREE_AT_RX = re.compile(r"\b(?i:ph\.?\s?d|m\.?s|b\.?s|m\.?eng|msc|bsc)\.?,?\s*(?:19|20)\d\d\s*\(([A-Z][\w&.' -]{1,40})\)")  # 'PhD 2016 (DTU)'
ELSEWHERE_RX = re.compile(r"\b(?i:ph\.?\s?d\.?|graduate|doctoral|master'?s|undergraduate|visiting) (?i:student|candidate)"
                          r"(?: in [\w &,-]{2,60}?)? at (?:the )?([A-Z][\w.&'-]*(?: (?:of )?[A-Z][\w.&'-]*){0,5})")


# ---------------------------------------------------------------- pure helpers (tests/test_labpage_audit.py)
def fold(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = s.replace('ł', 'l').replace('Ł', 'L').replace('ø', 'o').replace('Ø', 'O').replace('ß', 'ss').replace('đ', 'd')
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


def norm_title(s):
    """pi_hierarchy.norm_title: ASCII-folded, lowercase, letters and digits only."""
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)


def ndoi(s):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(s or '').strip(), flags=re.I).lower().rstrip('.)];,')


DOI_RX = re.compile(r'(?:doi\.org/|doi:\s*|/doi/(?:abs/|full/|pdf/)?)(10\.\d{4,9}/[^\s"<>?#]+)', re.I)
ARXIV_RX = re.compile(r'arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})|arxiv[:\s]+(\d{4}\.\d{4,5})|10\.48550/arxiv\.(\d{4}\.\d{4,5})', re.I)


def entry_ids(entry):
    """(DOIs, arXiv ids) an entry links or states."""
    blob = ' '.join([*(entry.get('links') or []), entry.get('quote') or '', entry.get('text') or ''])
    dois = {ndoi(m.group(1)) for m in DOI_RX.finditer(blob)}
    axs = {next(g for g in m.groups() if g) for m in ARXIV_RX.finditer(blob)}
    dois = {d for d in dois if not d.startswith('10.48550/arxiv')}
    return dois, axs


class PaperIndex:
    """A lab's papers (lab_papers.jsonl.gz rows with their editions) by DOI, arXiv id and normalized title.
    match(entry) -> (how, row) | (None, None). Order: DOI, arXiv id, exact title, then the lab-page recovery's held test
    (a held title of 30+ characters inside the citation, or a 30+ character prefix either way)."""

    def __init__(self, rows):
        self.doi, self.ax, self.title = {}, {}, {}
        for r in rows:
            for e in [r] + list(r.get('editions') or []):
                d = ndoi(e.get('doi'))
                if d:
                    m = re.match(r'10\.48550/arxiv\.(\d{4}\.\d{4,5})', d)
                    if m:
                        self.ax.setdefault(m.group(1), r)
                    else:
                        self.doi.setdefault(d, r)
                if e.get('arxiv'):
                    self.ax.setdefault(e['arxiv'], r)
                t = norm_title(e.get('title'))
                if t:
                    self.title.setdefault(t, r)
        self.long = [t for t in self.title if len(t) >= 30]

    def match(self, entry):
        dois, axs = entry_ids(entry)
        for d in dois:
            if d in self.doi:
                return 'doi', self.doi[d]
        for a in axs:
            if a in self.ax:
                return 'arxiv', self.ax[a]
        t = norm_title(entry.get('title'))
        if t and t in self.title:
            return 'title', self.title[t]
        cite = [s for s in (t, norm_title(entry.get('quote'))) if s]
        for h in self.long:
            if any(h in s for s in cite):
                return 'title_in_citation', self.title[h]
            if len(t) >= 30 and (h.startswith(t) or t.startswith(h)):
                return 'title_prefix', self.title[h]
        return None, None


RECOVER_STATUS = {  # tools/labpage_recover.py row status -> paper reason
    'accepted': 'genuinely_missing', 'pi_not_on_byline': 'pi_not_author', 'outside_2016_2026': 'outside_window',
    'other_institution': 'other_institution_affiliation', 'no_school_evidence': 'no_school_affiliation_evidence',
    'unresolved': 'unresolved_metadata', 'candidate': 'not_yet_resolved', 'held': 'matched', 'held_by_resolved_id': 'matched',
}
RECOVER_JUNK = {'thesis': 'not_a_paper', 'talk': 'not_a_paper', 'patent': 'not_a_paper', 'service_award_news': 'not_a_paper',
                'filter_or_heading': 'parse_artifact', 'venue_only': 'parse_artifact', 'author_line': 'parse_artifact',
                'fragment': 'parse_artifact', 'pi_not_in_hierarchy': 'parse_artifact'}


def paper_reason(status, junk_reason, year, pi_start):
    """Reason for a listed in-window paper that is not a lab paper, from the recovery's verdict."""
    if status == 'junk':
        return RECOVER_JUNK.get((junk_reason or '').split(':')[0], 'not_a_paper')
    if status == 'outside_appointment':
        return 'from_previous_school' if (pi_start and year and int(year) < pi_start) else 'outside_appointment'
    return RECOVER_STATUS.get(status, 'not_yet_resolved')


ALUMNI_RX = re.compile(r'\b(alumni|alumnae|alumnus|alumna|former|past|previous|alums?|graduates|graduated|completed|emeriti|moved on)\b', re.I)


def student_reason(cand, pi_start, alumni_ok):
    """Reason a listed name is not admitted by the lab-page rules (None: admissible). cand: flags, years, alumni (bool),
    is_cap (from an archived capture), under_people_heading, single_token, reviewer_drop, seen_current_2016 (the same
    person listed as current on a 2016+ capture)."""
    flags = set(cand.get('flags') or ())
    if cand.get('reviewer_drop') or flags & {'excluded-heading', 'faculty-desc', 'is-a-PI'}:
        return 'not_a_student'
    if cand.get('single_token') or 'not-a-name' in flags:
        return 'name_unresolved'
    ys = cand.get('years') or None
    last = (ys[1] if ys[1] is not None else ys[0]) if ys else None
    if last is not None and last < WINDOW[0]:
        return 'outside_2016_2026'
    if last is not None and pi_start and last < pi_start:
        return 'at_previous_school'
    if cand.get('is_cap') and not cand.get('under_people_heading'):
        return 'not_in_people_section'
    if cand.get('alumni') and not ys and not alumni_ok and not cand.get('seen_current_2016'):
        return 'undated_alumni_cannot_place'
    return None


def is_lab_site(title, url, people_url=None):
    """A lab or group site (vs. the PI's personal homepage): the page title names a lab/group, or the site is its own
    host named as a lab, or its people page is a separate members page."""
    t = fold(title)
    if re.search(r'\b(lab|labs|laboratory|group|research group|team|center|centre)\b', t):
        return True
    host = urlsplit(url or '').hostname or ''
    if re.search(r'lab|group', host.split('.')[0]):
        return True
    if people_url and people_url.rstrip('/') != (url or '').rstrip('/') and \
            re.search(r'/(people|members|team|group|lab-members|our-team)\b', urlsplit(people_url).path, re.I):
        return True
    return False


def pi_quote(text, names):
    """A verbatim stretch of the page text naming the PI (family name), at most 160 characters."""
    for n in names:
        toks_ = [t for t in re.split(r'\s+', str(n).strip()) if t]
        if not toks_:
            continue
        fam = toks_[-1]
        i = fold(text).find(fold(fam))
        if i >= 0:
            a = max(0, i - 60)
            return text[a:i + len(fam) + 60].strip()
    return None


def spread(stamps, k=3):
    """Up to k timestamps spread over the list (first, middle, last)."""
    stamps = sorted(set(stamps))
    if len(stamps) <= k:
        return stamps
    idx = sorted({0, len(stamps) // 2, len(stamps) - 1} if k == 3 else {round(i * (len(stamps) - 1) / (k - 1)) for i in range(k)})
    return [stamps[i] for i in idx]


def read(p):
    p = Path(p)
    if p.suffix == '.gz':
        with gzip.open(p, 'rt', encoding='utf-8') as f:
            if p.name.endswith('.jsonl.gz'):
                return [json.loads(line) for line in f if line.strip()]
            return json.load(f)
    return json.load(open(p, encoding='utf-8'))


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def pi_start_year(p):
    ys = []
    for q in p.get('periods') or []:
        m = re.match(r'(\d{4})', str(q.get('start') or ''))
        if m:
            ys.append(int(m.group(1)))
    if ys:
        return min(ys)
    ls = [l['year'] for l in p.get('listings') or [] if l.get('year')]
    if not ls or min(ls) <= WINDOW[0]:
        return None  # a first listing in 2016 is the window's floor, not an arrival (Leonard, Jha: decades at the school)
    return min(ls)


def pi_left_year(p):
    """The year the PI left: a reviewed period's end, else (no periods) the last listing year when it is before 2025."""
    e = pi_end_year(p)
    if e or p.get('periods'):
        return e
    ls = [l['year'] for l in p.get('listings') or [] if l.get('year')]
    return max(ls) if ls and max(ls) < 2025 else None


def pi_end_year(p):
    ends = []
    for q in p.get('periods') or []:
        if q.get('end') in (None, ''):
            return None
        m = re.match(r'(\d{4})', str(q['end']))
        if m:
            ends.append(int(m.group(1)))
    return max(ends) if ends else None


# ---------------------------------------------------------------- the lab-page toolkit (fetch + parse), patched
class Kit:
    """hierarchy/labpage-tools-princeton-mit loaded for one school: lpcap (fetch + store), lpev (capture lookup and quote
    checks), autom (member extraction), pubx (publication extraction), names (matching). New captures go to
    hierarchy/<school>/labpage-audit-captures.sqlite (LPCAP_LOCAL); reads also cover the school's earlier stores.
    Patched here, not in the toolkit: >= 3 s per host (Wayback 6 s), and robots.txt groups naming AI agents honoured."""

    def __init__(self, school):
        cfg = SCHOOLS[school]
        self.school = school
        self.store = H / school / 'labpage-audit-captures.sqlite'
        os.environ['LPCAP_LOCAL'] = str(self.store)
        extra = [str(H / school / f) for f in cfg.get('extra_stores', [])]
        if (H / school / 'labpage-captures.sqlite').exists():
            extra.append(str(H / school / 'labpage-captures.sqlite'))
        os.environ['LPCAP_EXTRA'] = ':'.join(extra)
        sys.path.insert(0, str(H / PM))
        import lpcap, lpev, autom, pubx, names  # noqa: E401
        self.lpcap, self.lpev, self.autom, self.pubx, self.names = lpcap, lpev, autom, pubx, names
        lpcap.ROOT = pubx.ROOT = str(H)  # the toolkit's own constant predates tools/atlas_paths.py
        for k_ in list(lpcap.DBS) + [school]:
            lpcap.DBS[k_] = str(H / k_ / 'labpage-captures.sqlite')
            lpcap.SISTER[k_] = [p_.replace(str(Path(p_).parents[1]), str(H)) for p_ in lpcap.SISTER.get(k_, [])]
        lpcap.DEFAULT_GAP = max(lpcap.DEFAULT_GAP, HOST_GAP)
        lpcap.LOCKDIR = os.path.join(os.environ.get('TMPDIR') or '/tmp', 'lp-ratelimit')
        owait = lpcap._wait
        lpcap._wait = lambda host: owait(host or '_no-host_')  # a link with no host must not name the lock directory itself
        lpcap.GAPS['web.archive.org'] = WAYBACK_GAP
        lpcap.GAPS['archive.org'] = WAYBACK_GAP
        lpcap.GAPS['api.openalex.org'] = max(lpcap.GAPS.get('api.openalex.org', 0), 1.05)
        orig = lpcap.robots_allowed
        self.robots_log = {}

        def robots_allowed(url, school_):
            ok = orig(url, school_)
            if ok:
                ok = self._ai_allowed(url)
            self.robots_log[urlsplit(url).netloc] = ok
            return ok
        lpcap.robots_allowed = robots_allowed
        con = lpcap.connect(school)  # create the store
        con.close()
        try:  # the school charter's host policy (schools/<key>.toml): 'none' is never fetched, live or Wayback; 'wayback-only'
            import school_config as SC  # hosts are read only from Wayback id_ captures (Michigan: Deep Blue, news, record; umich.edu)
            SC.get(school)
            self.host_use = lambda h: SC.host_use(school, h)
        except Exception:  # noqa: BLE001 (a school without a charter: every host live, robots and challenges still checked)
            self.host_use = lambda h: 'live'
        ofetch = lpcap.fetch

        def fetch(school_, url, **kw):
            use = self.host_use(lpcap.host_of(url) or '')
            if use == 'none':
                return {'url': url, 'capture_url': None, 'status': None, 'error': 'off-limits-host', 'content': b''}
            if use == 'wayback-only' and not lpcap.WAYBACK_RX.match(url) and 'web.archive.org/cdx/' not in url:
                return {'url': url, 'capture_url': None, 'status': None, 'error': 'wayback-only-host', 'content': b''}
            return ofetch(school_, url, **kw)
        lpcap.fetch = fetch
        pis = read(H / school / 'pis.json')  # autom's is-a-PI flag: every PI of the school, not only the 2026-10-22 input
        autom._all_pis[school] = list(dict.fromkeys(n for p_ in pis for n in [p_['pi']] + list(p_.get('names') or [])))

    def _ai_allowed(self, url):
        import urllib.robotparser
        sp = urlsplit(url)
        base = f'{sp.scheme}://{sp.netloc}/robots.txt'
        body, st = '', None
        for path in [str(self.store), self.lpcap.DBS[self.school]]:
            if not os.path.exists(path):
                continue
            c = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=60)
            row = c.execute('SELECT status, content FROM captures WHERE url=? AND capture_url IS NULL AND error IS NULL '
                            'ORDER BY id DESC LIMIT 1', (base,)).fetchone()
            c.close()
            if row:
                st, body = row[0], (zlib.decompress(row[1]).decode('utf-8', 'replace') if row[1] else '')
                break
        if st != 200 or '<html' in body[:500].lower():
            return st not in (401, 403)
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(body.splitlines())
        return all(rp.can_fetch(a, url) for a in AI_AGENTS)

    # fetching
    def get(self, url, wb=True):
        """Live page (robots, pacing, challenge detection), else the newest Wayback id_ capture. -> lpcap result dict."""
        return self.lpcap.get(self.school, url, wb=wb)

    def fetch(self, url, **kw):
        return self.lpcap.fetch(self.school, url, **kw)

    def cdx(self, url, frm=2016, to=2026):
        return self.lpcap.wayback_cdx(self.school, url, frm=frm, to=to)

    def src_of(self, url):
        """The stored copy to read for a URL: the live capture when there is one, else the newest Wayback id_ capture."""
        if not url or self.stored(url)[0]:
            return url
        for path in [str(self.store), self.lpcap.DBS[self.school]] + os.environ.get('LPCAP_EXTRA', '').split(':'):
            if not path or not os.path.exists(path):
                continue
            c = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=60)
            try:
                b = re.sub(r'^https?://', '', url).rstrip('/')
                vs = [f'{sch}://{b}{sl}' for sch in ('http', 'https') for sl in ('', '/')]
                row = c.execute('SELECT capture_url FROM captures WHERE url IN (?,?,?,?) AND capture_url IS NOT NULL AND status=200 '
                                'AND error IS NULL ORDER BY capture_url DESC LIMIT 1', vs).fetchone()
            except sqlite3.OperationalError:
                row = None
            c.close()
            if row:
                return row[0]
        return url

    def import_school_web(self, path, urls):
        """Copy a protocol school's stored pages (tools/school_web.py container: tables live and captures) for these page URLs
        into the audit store, unchanged (their own fetched_at and sha256; copied_from names the container), so the
        extractors read them without fetching again. Bodies Wayback served gzip-encoded are stored decoded."""
        import gzip as gz
        if not os.path.exists(path):
            return 0
        src = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=60)
        dst = self.lpcap.connect(self.school)
        n = 0
        for u in urls:
            if not u:
                continue
            rows = [(u, None, f, st, sha, ct, raw) for f, st, sha, ct, raw in src.execute(
                'select fetched_at, status, sha256, content_type, raw_zlib from live where url=? and status=200', (u,))]
            rows += [(pu, cap, f, st, sha, ct, raw) for pu, cap, f, st, sha, ct, raw in src.execute(
                'select page_url, capture_url, fetched_at, http_status, sha256, content_type, raw_zlib from captures '
                'where (page_url=? or capture_url=?) and http_status=200', (u, u))]
            for url, cap, f, st, sha, ct, raw in rows:
                if not raw or dst.execute('select 1 from captures where url=? and capture_url is ? and sha256=?', (url, cap, sha)).fetchone():
                    continue
                body = zlib.decompress(raw)
                if body[:2] == b'\x1f\x8b':
                    body = gz.decompress(body)
                dst.execute('insert into captures(url,final_url,capture_url,fetched_at,status,sha256,content_type,content,error,copied_from) '
                            'values (?,?,?,?,?,?,?,?,?,?)', (url, cap or url, cap, f, st, sha, ct, zlib.compress(body, 9), None,
                                                             os.path.basename(path)))
                n += 1
        dst.commit()
        dst.close()
        src.close()
        self.lpev._cache.clear()
        return n

    def stored(self, src):
        try:
            return self.lpev.cap(self.school, src)
        except (KeyError, ValueError):
            return None, None


def result_of(r):
    """A fetch result as a check result word."""
    if r.get('error') == 'robots-disallowed':
        return 'robots_disallowed'
    if r.get('error') in ('bot-challenge', 'host-challenged-skip'):
        return 'bot_challenge'
    if r.get('error') == 'off-limits-host':
        return 'off_limits'
    if r.get('error') == 'wayback-only-host':
        return 'wayback_only_host'
    if r.get('status') == 200 and r.get('content'):
        return 'ok_wayback' if r.get('capture_url') else 'ok'
    if r.get('status'):
        return f"http_{r['status']}"
    if r.get('http_status'):
        return f"http_{r['http_status']}"
    return 'unreachable' if r.get('error') else 'no_capture'


# ---------------------------------------------------------------- discovery
SOCIAL = ('linkedin.com', 'twitter.com', 'x.com', 'facebook.com', 'instagram.com', 'youtube.com', 'scholar.google', 'orcid.org',
          'researchgate.net', 'dblp.org', 'dblp.uni-trier.de', 'github.com', 'wikipedia.org', 'bsky.app', 'mastodon', 'academia.edu',
          'semanticscholar.org', 'scopus.com', 'webofscience.com', 'doi.org', 'google.com', 'zoom.us', 'calendly.com', 'wikidata.org',
          'mathgenealogy.org', 'genealogy.math.ndsu', 'zbmath.org', 'ams.org/mathscinet', 'twitter', 'threads.net', 'publons.com',
          'ieeexplore', 'acm.org', 'pubmed', 'ncbi.nlm.nih.gov', 'arxiv.org', 'openreview.net', 'loop.frontiersin', 'mailto:',
          'isni.org', 'viaf.org', 'id.loc.gov', 'd-nb.info', 'catalogue.bnf.fr', 'idref.fr', 'isni.oclc', 'kb.nl', 'nla.gov.au',
          'nii.ac.jp', 'id.ndl.go.jp', 'lccn.loc.gov', 'babelnet', 'ror.org', 'crossref.org', 'mathscinet', 'genealogy.ams.org')
WEBWORD = re.compile(r'\b(web\s*site|website|home\s*page|homepage|web\s*page|webpage|personal page|personal site|lab|laboratory|'
                     r'group|research group|research site|visit)\b', re.I)
PEOPLE_LINK = re.compile(r'^\W*((our|the|lab|group|current)\s+)?(people|members?|team|group members?|lab members?|students?|'
                         r'personnel|researchers|group|lab|research group|who we are|advisees|phd students)\W*$', re.I)
ALUMNI_LINK = re.compile(r'\b(alumni|alumnae|alums|former (members|students|group members|lab members)|past (members|students)|'
                         r'graduated students|previous members)\b', re.I)
PUBS_LINK = re.compile(r'^\W*((selected|recent|all|full|research|our|lab|group)\s+)?(publications?|papers|bibliography|pubs|'
                       r'publication list|list of publications)\W*$', re.I)
STUDENT_HEAD = re.compile(r'\b(students?|advisees?|ph\.?\s?d|postdocs?|group members|lab members|current members|alumni|'
                          r'graduated|mentees|research group|post-?docs?|post-?doctoral|graduates?|undergrad\w*|members|team|people|'
                          r'researchers|visitors|former|current|doctoral|masters?|interns?|staff)\b', re.I)
GENERIC_PAGE_RX = re.compile(r'/(undergraduate|graduate|admissions?|visit|apply|news|events?|students|academics|programs?|'
                             r'giving|calendar|directory|about-us|contact)\b', re.I)
PROFILE_RX = re.compile(r'/(people|faculty|directory|profiles?|person|staff|our-people|bios?)/(profile/|faculty/)?[^/?#]+'
                        r'(/(overview|bio|about|profile|research|publications))?/?$', re.I)
NOT_HOME = re.compile(r'/news/|/events?/|/article|wikipedia|/\d{4}/\d{2}/|people-list|/people/?$|/faculty/?$|/directory|'
                      r'/oai/|dataspace|/courses?/|\.pdf$|cv\.html?$|/cv/?$|resume', re.I)


def family(name):
    t = [x for x in re.split(r'[\s,]+', re.sub(r'\([^)]*\)', ' ', str(name))) if x and not re.fullmatch(r'(jr|sr|ii|iii|iv)\.?', x, re.I)]
    return t[-1] if t else ''


def unwrap(u):
    """A mail-security redirect (Outlook safelinks, urldefense) -> the URL it wraps."""
    from urllib.parse import parse_qs, unquote
    sp = urlsplit(u or '')
    if (sp.hostname or '').endswith('safelinks.protection.outlook.com'):
        v = parse_qs(sp.query).get('url')
        return v[0] if v else u
    m = re.match(r'^https?://urldefense(?:\.proofpoint)?\.com/v3/__(.+?)__', u or '')
    return unquote(m.group(1)) if m else u


def unwayback(u):
    m = re.match(r'^https?://web\.archive\.org/web/\d+(?:id_|if_)?/(.+)$', u or '')
    if not m:
        return u
    v = m.group(1)
    if not re.match(r'^https?://', v):
        v = 'http://' + v.lstrip('/')
    v = re.sub(r':80(?=/)', '', v)
    return v


def social(u):
    """A social, index, authority or publisher URL (never a lab site). Host entries match the host or its subdomains
    ('google.com' is Google itself, not sites.google.com); entries with a path or scheme match as substrings."""
    lu = (u or '').lower()
    h = urlsplit(lu).hostname or ''
    for e in SOCIAL:
        if '/' in e or ':' in e:
            if e in lu:
                return True
        elif e == 'google.com':
            if h in ('google.com', 'www.google.com'):
                return True
        elif re.search(r'\.(com|org|net|app|edu|gov|fr|nl|au|jp|io|de|info|social)$', e):
            if h == e or h.endswith('.' + e):
                return True
        elif e in h:
            return True
    return False


def link_base(row, url):
    """Links in a Wayback id_ capture are relative to the original page, not to web.archive.org."""
    return row.get('url') if row.get('capture_url') else (row.get('final_url') or url)


def is_profile(url, dom):
    h = urlsplit(url or '').hostname or ''
    return bool(re.search(dom, h) and PROFILE_RX.search(urlsplit(url).path or '') and '~' not in (url or ''))


def site_links(kit, row, base):
    try:
        return kit.lpcap.links(row['content'], base)
    except Exception:  # noqa: BLE001 (malformed bytes: no links)
        return []


def classify_links(lks, site_url, domain_rx):
    """people / alumni / pubs links on a site page: same host, or the site's own path, or a sibling on the school domain."""
    out = collections.defaultdict(list)
    sh = urlsplit(site_url).hostname or ''
    sp = urlsplit(site_url).path or '/'
    seg = sp.strip('/').split('/')[0] if sp.strip('/') else ''
    for href, txt in lks:
        h = urlsplit(href).hostname or ''
        if not href.startswith('http') or social(href) or href.rstrip('/') == site_url.rstrip('/'):
            continue
        same = h == sh or (h.endswith('.' + sh.split('.', 1)[-1]) and re.search(domain_rx, h) and re.search(domain_rx, sh))
        if not same:
            continue
        if h == sh and seg and (urlsplit(href).path.strip('/').split('/') or [''])[0] != seg:
            continue  # a personal page on a department host (/~user/...): only links under the same first path segment
        segs = [x for x in sp.split('/') if x]
        if h == sh and len(segs) >= 2 and not (urlsplit(href).path or '/').startswith('/' + '/'.join(segs[:2])):
            continue  # a page two levels deep (/people/pattie/...): never the institution's own /people/ listing
        t = (txt or '').strip()
        path = urlsplit(href).path.lower()
        if ALUMNI_LINK.search(t) or re.search(r'/(alumni|former|past-members|alums)\b', path):
            out['alumni'].append(href)
        elif PUBS_LINK.match(t) or re.search(r'/(publications?|papers|pubs|bibliography)(\.html?|/)?$', path):
            out['pubs'].append(href)
        elif PEOPLE_LINK.match(t) or re.search(r'/(people|members|team|group|students|lab-members|our-team|personnel)(\.html?|/)?$', path):
            out['people'].append(href)
    return {k: list(dict.fromkeys(v)) for k, v in out.items()}


def has_student_section(kit, row):
    try:
        t = kit.lpcap.page_text(row['content'], row.get('content_type'))
    except Exception:  # noqa: BLE001
        return False
    return bool(re.search(r'(current|graduate|ph\.?\s?d\.?|doctoral|former|past)\s+(students|advisees|members)|\bstudents\s*:|'
                          r'\badvisees\b|\bmy (students|group)\b|\bgroup members\b|\bpostdocs?\b', t, re.I))


def discover_lab(kit, school, p, ctx, full=True):
    """Every place checked for one PI lab, the chosen pages and their captures (see the module docstring)."""
    cfg = SCHOOLS[school]
    dom = cfg['domain']
    checks, cands = [], collections.OrderedDict()
    names_ = list(dict.fromkeys([p['pi']] + list(p.get('names') or [])))
    fam = fold(family(p['pi']))
    fam_toks = [fold(t) for t in re.split(r'[\s-]+', family(p['pi'])) if len(t) > 2]

    def add(source, url, res, **kw):
        checks.append(dict(source=source, url=url, at=now(), result=res, **{k: v for k, v in kw.items() if v}))

    def cand(url, source):
        url = unwayback(unwrap(url))
        if url and url.startswith('http') and not social(url) and not re.search(r'\.(pdf|jpg|png|docx?)$', url, re.I) \
                and not is_profile(url, dom):
            cands.setdefault(url, source)

    prior = ctx['prior'].get(p['pi'])
    profiles = []
    if prior:
        for k in ('lab_site', 'people_page'):
            if prior.get(k):
                add('prior_labpage_pass_2026-10-22', prior[k], 'recorded_' + k + ('_is_a_profile' if is_profile(prior[k], dom) else ''))
                if is_profile(prior[k], dom):
                    profiles.append(prior[k])
                cand(prior[k], 'prior_labpage_pass')
        for pg in (ctx['dossier'].get(p['pi']) or {}).get('pages', []):
            add('prior_labpage_pass_2026-10-22', pg.get('capture_url') or pg['url'],
                'ok' if pg.get('status') == 200 else (pg.get('error') or f"http_{pg.get('status')}"), kind=pg.get('kind'),
                sha256=pg.get('sha256'))
    for u in ctx.get('seeds', {}).get(p['pi'], []):
        add('prior_labpage_pass', u, 'recorded_page')
        cand(u, 'earlier_homepage_find')
    if full:
        # 1. department listing -> school profile
        lst = sorted(p.get('listings') or [], key=lambda l: -(l.get('year') or 0))
        seen_l = set()
        for l in lst:
            lu = unwayback(l['url']).replace('http://', 'https://')
            key_ = (urlsplit(lu).hostname, urlsplit(lu).path.rstrip('/'))
            if key_ in seen_l or len(seen_l) >= 2:
                continue
            seen_l.add(key_)
            r = kit.get(lu)
            add('department_listing', lu, result_of(r), capture_url=r.get('capture_url'), sha256=r.get('sha256'))
            if r.get('status') == 200 and r.get('content'):
                base = link_base(r, lu)
                for href, txt in site_links(kit, r, base):
                    if txt and len(txt) < 60 and any(kit.names.match_one(txt, n) for n in names_) and not social(href):
                        profiles.append(unwayback(href))
        for e in [e for q in p.get('periods') or [] for e in q.get('evidence') or []] + [p.get('piBasis') or {}]:
            u = unwayback(e.get('url') or '')
            if re.search(dom, urlsplit(u).hostname or '') and re.search(r'/(people|faculty|profile|directory)/', u) and \
                    fam and fam.replace(' ', '-') in fold(u):
                profiles.append(u)
        for prof in list(dict.fromkeys(profiles))[:3]:
            r = kit.get(prof)
            add('school_profile', prof, result_of(r), capture_url=r.get('capture_url'), sha256=r.get('sha256'))
            if r.get('status') == 200 and r.get('content'):
                ph = urlsplit(prof).hostname
                for href, txt in site_links(kit, r, link_base(r, prof)):
                    hh = urlsplit(href).hostname or ''
                    if social(href) or not href.startswith('http'):
                        continue
                    pth = [x for x in urlsplit(href).path.split('/') if x]
                    named = any(t in fold(href) for t in fam_toks) and len(pth) <= 1  # a site named for the PI, not a deep page
                    if (WEBWORD.search(txt or '') and hh != ph) or (named and hh != ph) or \
                            (re.match(r'^\s*https?://', txt or '') and hh != ph):
                        add('school_profile_link', href, 'listed', anchor=(txt or '')[:80], on=prof)
                        cand(href, 'school_profile_link')
        # 2. DBLP person homepage URLs (the local dump extract; dblp.org itself is never fetched)
        persons = ctx['dblp_persons']
        for pid in p.get('dblp') or []:
            rec = persons.get(pid)
            if rec is None:
                add('dblp_person_url', pid, 'person_not_in_dump_extract')
                continue
            urls = [u for u in rec.get('urls') or [] if not social(u)]
            add('dblp_person_url', pid, 'listed' if urls else 'no_homepage_url', urls=urls or None)
            for u in urls:
                cand(u, 'dblp_person_url')
        if not p.get('dblp'):
            add('dblp_person_url', None, 'no_dblp_person')
        # 3. ORCID researcher URLs: the public record's person.json on orcid.org (pub.orcid.org's robots.txt disallows all)
        for o in (p.get('orcid') or [])[:2]:
            u = f'https://orcid.org/{o}/person.json'
            r = kit.fetch(u, headers={'Accept': 'application/json'})
            urls = []
            if r.get('status') == 200 and r.get('content'):
                try:
                    urls = sorted(set(re.findall(r'"(https?://[^"\s]+)"', json.dumps(json.loads(r['content']).get('publicGroupedResearcherUrls') or {}))))
                except ValueError:
                    pass
            add('orcid_researcher_urls', u, (result_of(r) if r.get('status') != 200 else ('listed' if urls else 'no_urls')),
                sha256=r.get('sha256'), urls=urls or None)
            for x in urls:
                cand(x, 'orcid_researcher_url')
        if not p.get('orcid'):
            add('orcid_researcher_urls', None, 'no_orcid')
        add('openalex_author', (p.get('reviewedOpenAlex') or [None])[0], 'no_homepage_field_in_schema')
        # 4. earlier homepage finds and the PI's own evidence URLs that are homepages
        for u in ctx['homepage_finds'].get(p['pi'], []):
            add('earlier_homepage_find', u, 'listed')
            cand(u, 'earlier_homepage_find')
        for e in [e for q in p.get('periods') or [] for e in q.get('evidence') or []] + [p.get('piBasis') or {}]:
            u = unwayback(e.get('url') or '')
            if u and not NOT_HOME.search(u) and not social(u) and (any(t in fold(u) for t in fam_toks) or re.search(r'lab\.', u)):
                add('pi_evidence_url', u, 'listed')
                cand(u, 'pi_evidence_url')
    # 5. evaluate the candidates (a lab the 2026-10-22 pass recorded keeps its reviewed pages: only other candidates are
    #    evaluated, to catch a missed lab site; its links and Wayback history are scanned by scan_prior)
    recorded = bool(prior and prior.get('lab_site') and not is_profile(prior['lab_site'], dom))
    sites = []
    for u, src in list(cands.items())[:8]:
        if recorded and src == 'prior_labpage_pass':
            continue
        r = kit.get(u)
        res = result_of(r)
        txt = ''
        if r.get('status') == 200 and r.get('content'):
            try:
                txt = kit.lpcap.page_text(r['content'], r.get('content_type'))
            except Exception:  # noqa: BLE001
                txt = ''
        names_pi = bool(fam and fam in fold(txt))
        host = urlsplit(unwayback(r.get('final_url') or u)).hostname or ''
        strong = src in ('school_profile_link', 'dblp_person_url', 'orcid_researcher_url', 'earlier_homepage_find')
        add('candidate_site', u, res if (not txt or names_pi) else ('does_not_name_pi' + ('_kept_strong_source' if strong else '')),
            via=src, capture_url=r.get('capture_url'), sha256=r.get('sha256'),
            final_url=r.get('final_url') if r.get('final_url') and r.get('final_url') != u else None)
        # a frameset or script-built homepage: kept when the school's own profile links it, or DBLP / ORCID name it on the school's domain
        generic = bool(GENERIC_PAGE_RX.search(urlsplit(u).path or '')) or (host.split('.')[0] in ('www', 'grad', 'admissions', 'apply'))
        if txt and (names_pi or (not generic and (src == 'school_profile_link' or (strong and re.search(dom, host))))):
            title = ''
            m = re.search(rb'<title[^>]*>(.*?)</title>', r['content'][:20000], re.I | re.S)
            if m:
                title = kit.lpcap.collapse(kit.lpcap.decode(m.group(1)))
            other_edu = bool(re.search(r'\.edu$|\.ac\.[a-z]{2}$|university|\.edu\.[a-z]{2}$', host)) and not re.search(dom, host)
            sites.append(dict(url=u, row=r, title=title, school_host=bool(re.search(dom, host)), other_school=other_edu, via=src,
                              text=txt, names_pi=names_pi))
    fam_t = fold(family(p['pi']))
    named = any(fam_t and fam_t in fold(x['title']) for x in sites)

    def other_group(x):  # 'Coley Research Group' on Ashia Wilson's profile: another PI's group, when a candidate names her
        m = re.search(r"\b([A-Z][\w'’-]+)(?:'s)? (?:research group|lab|laboratory|group)\b", x['title'] or '', re.I)
        return bool(named and m and fam_t not in fold(x['title']) and fold(m.group(1)) not in ('the', 'research', 'our', 'mit', 'ai', 'ml'))
    sites = [x for x in sites if not other_group(x)] or sites
    rank = lambda s: (not s['school_host'], s['other_school'], not is_lab_site(s['title'], s['url']), not s['names_pi'],
                      len([x for x in urlsplit(s['url']).path.split('/') if x]), s['via'] != 'prior_labpage_pass')
    sites.sort(key=rank)
    chosen = dict(lab_site=None, people_page=None, alumni_page=None, pubs_page=None, kind=None, title=None)
    pages = []
    if recorded:
        chosen['other_candidates'] = [dict(url=s_['url'], via=s_['via'], title=s_['title']) for s_ in sites] or None
        sites = []
    pubs_site = None
    if sites and re.search(r'/(publications?|papers|pubs)(\.html?|/)?$', urlsplit(sites[0]['url']).path, re.I):
        root = [x for x in sites[1:] if urlsplit(x['url']).hostname == urlsplit(sites[0]['url']).hostname]
        if root:  # the publications page was found first: the site is its host's homepage
            pubs_site = sites[0]['url']
            sites = root + [x for x in sites if x not in root]
    if sites:
        s = sites[0]
        chosen.update(lab_site=s['url'], title=s['title'], kind=('lab_site' if is_lab_site(s['title'], s['url']) else 'pi_homepage'),
                      other_school=s['other_school'] or None, capture_url=s['row'].get('capture_url'), sha256=s['row'].get('sha256'),
                      quote=pi_quote(s['text'], names_))
        b_ = link_base(s['row'], s['url'])
        lk = classify_links(site_links(kit, s['row'], b_), b_, dom)
        for k in ('people', 'alumni', 'pubs'):
            for u in sorted(lk.get(k, []), key=lambda x: x.lower().endswith('.pdf'))[:2]:
                r = kit.get(u)
                add(f'{k}_link', u, result_of(r), on=s['url'], capture_url=r.get('capture_url'), sha256=r.get('sha256'))
                if r.get('status') == 200 and r.get('content') and not chosen[f'{k}_page' if k != 'people' else 'people_page']:
                    chosen['people_page' if k == 'people' else f'{k}_page'] = u
                    pages.append((k, u))
        if pubs_site and not chosen['pubs_page']:
            chosen['pubs_page'] = pubs_site
            pages.append(('pubs', pubs_site))
        if not chosen['people_page'] and has_student_section(kit, s['row']):
            chosen['people_page'] = s['url']
            pages.append(('people', s['url']))
        if chosen['people_page'] and kind_lab(chosen, kit):
            chosen['kind'] = 'lab_site'
    # 6. Wayback history of the people and alumni pages (2016-2026, from the PI's first year at the school)
    wb = {}
    first = max(WINDOW[0], pi_start_year(p) or WINDOW[0])
    for k, u in pages:
        if k not in ('people', 'alumni'):
            continue
        rows = kit.cdx(u, frm=first, to=WINDOW[1])
        add('wayback_cdx', u, f'{len(rows)} captures', frm=first)
        caps = []
        for ts in spread([r_[0] for r_ in rows], 3):
            orig = next(r_[1] for r_ in rows if r_[0] == ts)
            cu = kit.lpcap.wayback_id(ts, orig)
            r = kit.fetch(cu, check_robots=False)
            add('wayback_capture', cu, result_of(r), sha256=r.get('sha256'))
            if r.get('status') == 200:
                caps.append(cu)
        wb[u] = caps
    return dict(pi=p['pi'], checked_at=now(), checks=checks, chosen=chosen, sites=[dict(url=s['url'], via=s['via'], title=s['title'],
                school_host=s['school_host'], other_school=s['other_school']) for s in sites], wayback=wb,
                robots={h: ok for h, ok in kit.robots_log.items() if not ok})


def kind_lab(chosen, kit):
    return bool(chosen.get('people_page') and chosen['people_page'].rstrip('/') != (chosen.get('lab_site') or '').rstrip('/')
                and re.search(r'/(people|members|team|group|lab-members|our-team)\b', urlsplit(chosen['people_page']).path, re.I))


def scan_prior(kit, school, p, ctx):
    """Labs the 2026-10-22 pass recorded: alumni and publications links on the stored lab and people pages that the pass
    never captured; capture them (and up to three Wayback captures of each alumni page)."""
    ev = ctx['prior'].get(p['pi']) or {}
    plan = ctx['plan'].get(p['pi']) or {}
    used = set()
    for k in ('people', 'wb', 'auto', 'alumni_pages', 'other_pages'):
        for u in plan.get(k) or []:
            used.add(unwayback(u).rstrip('/'))
    for x in plan.get('pubs') or []:
        if isinstance(x, dict) and x.get('pubs_page'):
            used.add(x['pubs_page'].rstrip('/'))
    for x in ev.get('pubs_pages') or []:
        used.add(x['url'].rstrip('/'))
    checks, found = [], collections.defaultdict(list)
    for src in [ev.get('lab_site'), ev.get('people_page')]:
        if not src:
            continue
        row, _ = kit.stored(src)
        if not row:
            continue
        b_ = link_base(row, src)
        lk = classify_links(site_links(kit, row, b_), b_, SCHOOLS[school]['domain'])
        for k in ('alumni', 'pubs', 'people'):
            for u in lk.get(k, [])[:3]:
                if u.rstrip('/') in used or u in found[k]:
                    continue
                found[k].append(u)
    wb = {}
    for k, us in found.items():
        for u in us:
            r = kit.get(u)
            checks.append(dict(source=f'{k}_link_not_used_by_prior_pass', url=u, at=now(), result=result_of(r),
                               sha256=r.get('sha256'), capture_url=r.get('capture_url')))
            if k == 'alumni' and r.get('status') == 200:
                first = max(WINDOW[0], pi_start_year(p) or WINDOW[0])
                rows = kit.cdx(u, frm=first, to=WINDOW[1])
                caps = []
                for ts in spread([r_[0] for r_ in rows], 3):
                    orig = next(r_[1] for r_ in rows if r_[0] == ts)
                    cu = kit.lpcap.wayback_id(ts, orig)
                    rr = kit.fetch(cu, check_robots=False)
                    checks.append(dict(source='wayback_capture', url=cu, at=now(), result=result_of(rr), sha256=rr.get('sha256')))
                    if rr.get('status') == 200:
                        caps.append(cu)
                wb[u] = caps
    return dict(checks=checks, new_pages={k: v for k, v in found.items()}, wayback=wb)


# ---------------------------------------------------------------- context
def load_ctx(school, kit=None, plan=True):
    cfg = SCHOOLS[school]
    ctx = dict(school=school, cfg=cfg)
    ctx['pis'] = read(H / school / 'pis.json')
    ctx['students'] = read(H / school / 'students.json')
    lp = collections.defaultdict(list)
    for r in read(H / school / 'lab_papers.jsonl.gz'):
        lp[r['pi']].append(r)
    ctx['lab_papers'] = lp
    ev = H / school / 'labpage-evidence.json'
    ctx['prior'] = {r['pi']: r for r in read(ev)} if ev.exists() else {}
    inp = H / school / 'labpage-input.json'
    ctx['input'] = {r['pi']: r for r in read(inp)} if inp.exists() else {}
    ctx['dossier'] = {}
    ctx['plan'] = {}
    if cfg['family'] == 'pm':
        d = H / cfg['tools'] / cfg['dossier']
        ctx['dossier'] = read(d) if d.exists() else {}
        if plan and kit is not None:
            import importlib
            ctx['plan'] = importlib.import_module(cfg['plan']).P
    ctx['pubs_rows'], ctx['pubs_rows_pages'] = collections.defaultdict(list), collections.defaultdict(list)
    pr = H / school / 'labpage-pubs.jsonl.gz'
    if pr.exists() and cfg['family'] != 'pm':
        for r in read(pr):
            ctx['pubs_rows'][r['pi']].append(r)
            u = r.get('page_url') or r.get('url')
            if u and u not in ctx['pubs_rows_pages'][r['pi']]:
                ctx['pubs_rows_pages'][r['pi']].append(u)
    ctx['manual'] = {}
    mp = H / 'labpage-tools-epfl-berkeley' / 'manual_pages.json'
    if cfg['family'] == 'eb' and mp.exists():
        ctx['manual'] = read(mp).get(school) or {}
    ctx['seeds'] = {}
    if cfg['family'] == 'st':  # Stanford's pass kept its pages in decisions.json and wrote no evidence file
        dp = H / cfg['tools'] / 'decisions.json'
        for pi_, d_ in (read(dp) if dp.exists() else {}).items():
            ctx['seeds'][pi_] = [x['url'] for x in d_.get('pages') or [] if x.get('url')]
    hf = P.FULLTEXT_PUSH / 'raw' / f'pi-homepages-{school}.json'
    ctx['homepage_finds'] = read(hf) if hf.exists() else {}
    ctx['dblp_persons'] = {}
    return ctx


def load_dblp(ctx):
    if not ctx['dblp_persons']:
        want = {pid for p in ctx['pis'] for pid in p.get('dblp') or []}
        d = read(H / 'dblp-dump-persons.json.gz')['persons']
        ctx['dblp_persons'] = {k: v for k, v in d.items() if k in want}
    return ctx['dblp_persons']


def discovery_path(school):
    return H / school / 'labpage-audit-discovery.jsonl'


def read_discovery(school):
    out = {}
    p = discovery_path(school)
    if p.exists():
        for line in open(p, encoding='utf-8'):
            if line.strip():
                r = json.loads(line)
                out[r['pi']] = r  # the latest record per PI wins
    return out


def cmd_discover(school, only=None, redo=False, redo_unrecorded=False):
    if SCHOOLS[school].get('read_only'):
        sys.exit(f'{school} is read-only here: audit it from its own lab-page outputs')
    kit = Kit(school)
    ctx = load_ctx(school, kit)
    load_dblp(ctx)
    done = read_discovery(school)
    out = open(discovery_path(school), 'a', encoding='utf-8')
    for p in ctx['pis']:
        if only and p['pi'] not in only:
            continue
        rec_ = ctx['prior'].get(p['pi']) or {}
        unrec = not (rec_.get('lab_site') and not is_profile(rec_['lab_site'], SCHOOLS[school]['domain']))
        if p['pi'] in done and not redo and not (redo_unrecorded and unrec):
            continue
        kit.robots_log.clear()
        prior = ctx['prior'].get(p['pi'])
        try:
            rec = discover_lab(kit, school, p, ctx, full=True)
            if prior:
                rec['prior_scan'] = scan_prior(kit, school, p, ctx)
        except Exception as e:  # noqa: BLE001 (one lab's failure is recorded and the run goes on; --redo retries it)
            rec = dict(pi=p['pi'], checked_at=now(), checks=[dict(source='discovery_error', url=None, at=now(), result=repr(e)[:300])],
                       chosen=dict(lab_site=None), sites=[], wayback={}, error=repr(e)[:300])
        rec['had_prior_record'] = bool(prior)
        out.write(json.dumps(rec, ensure_ascii=False) + '\n')
        out.flush()
        print(json.dumps(dict(pi=p['pi'], chosen=rec['chosen'].get('lab_site'), kind=rec['chosen'].get('kind'),
                              people=rec['chosen'].get('people_page'), pubs=rec['chosen'].get('pubs_page'),
                              checks=len(rec['checks'])), ensure_ascii=False), flush=True)
    out.close()



# ---------------------------------------------------------------- students
ROLE_OK = {'phd', 'postdoc', 'masters', 'undergraduate', 'member', 'other'}


def build_students(ctx, pi):
    """[(display name, [name + aliases], record)] of the lab's students in the build."""
    out = []
    for r in ctx['students'].get(pi) or []:
        out.append((r['name'], [r['name']] + list(r.get('aliases') or []), r))
    return out


def corrections(school):
    p = H / 'student-corrections.json'
    return [x for x in (read(p) if p.exists() else []) if x.get('school') == school]


CREDIT_RX = re.compile(r'©|\bcopyright\b|template design|designed by|design by|powered by|all rights reserved|photo(graph)? (by|credit)', re.I)
COADV_RX = re.compile(r'(?:joint(?:ly)?|co-?advised|co-?supervised|co-?mentored|co-?advisor|together)\s+(?:with|by)\s+(?:(?:Prof\.?|Professor|Dr\.?)\s+)?'
                      r'([A-Z][\w.\'’-]+(?:\s+[A-Z][\w.\'’-]+){1,3})')


_plaus = {}


def plausible(kit, name):
    """lpdom.plausible_person (hierarchy/labpage-tools-epfl-berkeley): the given name occurs in bylines or rosters."""
    if 'f' not in _plaus:
        sys.path.append(str(H / 'labpage-tools-epfl-berkeley'))
        import lpdom
        _plaus['f'] = lpdom.plausible_person
    try:
        return _plaus['f'](name)
    except Exception:  # noqa: BLE001
        return True


def coadvisers(kit, school, src):
    """Names written after 'joint with' / 'co-advised with' on a page: co-advisers, not members."""
    try:
        t = kit.lpev.text(school, src)
    except (KeyError, ValueError):
        return []
    return list(dict.fromkeys(m.group(1) for m in COADV_RX.finditer(t)))


YEAR_ = r'(?:19[89]\d|20[0-2]\d)'


def entry_years(desc, head):
    """(years, basis) stated by the entry itself; never a neighbour's dates or a bio's degree dates.
      '(Postdoc, 2010-2014)' -> [2010, 2014]; '(PhD student, MIT ORC, 2022 -)' -> [2022, None] (an open range is a start);
      '(Ph.D. in applied math 2014)' or 'PhD 2021' -> [None, 2014] (a degree year ends the stay); 'MIT Undergraduate Student, 2020'
      -> [2020, 2020]; a section heading that is only a year ('2019') -> that year, basis section_year_heading; else
      (None, 'none'): the build keeps undated students."""
    d = (desc or '')[:90]
    m = re.match(r'^\W{0,3}\(([^()]{0,80})\)', d)
    seg = m.group(1) if m else re.split(r'(?<=[a-z0-9)])\.\s|\s(?:received|graduated from|is|was|joined|works?)\s', d, maxsplit=1)[0][:70]
    r = re.search(r'(%s)\s*(?:-|–|—|to|until)\s*(%s|present|now|current|today)?' % (YEAR_, YEAR_), seg, re.I)
    if r:
        b = r.group(2)
        return [int(r.group(1)), int(b) if b and b[:2] in ('19', '20') else None], 'stated_in_entry'
    ys = [int(y) for y in re.findall(r'(?<!\d)(%s)(?!\d)' % YEAR_, seg)]
    if len(ys) == 1:
        if re.search(r"\bph\.?\s?d|\bdegree|\bgraduated|\bclass of|\bm\.?s\.?\b|\bb\.?s\.?\b|\bm\.?eng|\bthesis|\balum|\buntil|\bleft|'\d\d", seg, re.I):
            return [None, ys[0]], 'stated_in_entry'
        return [ys[0], ys[0]], 'stated_in_entry'
    if head and re.fullmatch(r'\W*(%s)\W*' % YEAR_, head.split(' > ')[-1].strip()):
        y = int(re.search(YEAR_, head.split(' > ')[-1]).group(0))
        return [y, y], 'section_year_heading'
    return None, 'none'


ROLE_NEAR = re.compile(r"^\W{0,3}[(,:–—-]?\s*(?:[A-Z][\w.&'-]*\s){0,2}?(?:visiting\s|joint\s|former\s|current\s|\d(?:st|nd|rd|th)[- ]year\s)?"
                       r"(ph\.?\s?d|post-?doc|postdoctoral|master|m\.?s\.?\b|m\.?eng|meng|undergrad|b\.?s\.?e?\b|ug\b|urop|superurop|"
                       r"graduate|grad\b|doctoral|student|candidate|research|visiting|lab manager|engineer|scientist|staff|intern)", re.I)


def entry_role(desc, head, role_of):
    """(role, basis): the role the entry states right after the name ('(PhD student, ...)', ', Postdoc', 'MIT Undergraduate
    Student'), else the role its section heading names ('PhD Students', 'Post-doctoral Scholars'), else (None, 'none').
    A role word further into a bio ('received his B.S. ...', 'Ph.D. in Electrical Engineering from ...') never counts."""
    d = (desc or '')[:60]
    if ROLE_NEAR.match(d):
        r = role_of(d[:45])[0]
        if r and r != 'member':
            return r, 'entry'
    h = (head or '').split(' > ')[-1]
    r = role_of(h)[0] if h else None
    if not r and head and ' > ' in head:
        r = role_of(head.split(' > ')[0])[0]
    if r and r != 'member':
        return r, 'section_heading'
    return None, 'none'


def paren_years(desc):
    """Years in the parenthetical right after a name: '(Ph.D. in applied math 2014)', '(Postdoc, 2010-2014)'."""
    m = re.match(r'^\W{0,3}\(([^()]{0,60})\)', desc or '')
    if not m:
        return None
    ys = [int(y) for y in re.findall(r'(?<!\d)((?:19[89]|20[0-2])\d)(?!\d)', m.group(1))]
    if not ys:
        return None
    if len(ys) >= 2:
        return [min(ys), max(ys)]
    return [None, ys[0]] if re.search(r'ph\.?\s?d|degree|graduat|class|m\.?s\.?|b\.?s|postdoc|alum|until|left', m.group(1), re.I) else [ys[0], ys[0]]


def pm_candidates(kit, school, pi, plan, held):
    """Every name autom.extract proposes from a lab plan's pages (lpauto.rows_for's sources), with the disposition
    rows_for gives it (None: kept as an evidence row). plan keys: see lpauto.py."""
    import lpauto
    names = kit.names
    drop = [names.fold(x) for x in plan.get('drop', [])]
    keep = [names.fold(x) for x in plan.get('keep', [])]
    yrs = {names.fold(k): v for k, v in plan.get('years', {}).items()}
    roles_ = {names.fold(k): v for k, v in plan.get('roles', {}).items()}
    drop_heads = re.compile(plan['drop_heads'], re.I) if plan.get('drop_heads') else None
    only_heads = re.compile(plan['only_heads'], re.I) if plan.get('only_heads') else None
    srcs = [(s, False) for s in plan.get('auto', plan.get('people', []) if 'rows' not in plan else [])]
    for u in plan.get('wb', []):
        caps = (plan.get('wb_caps') or {}).get(u) or lpauto.wb_captures(school, u)
        for c in caps or []:
            y = int(re.search(r'/web/(\d{4})', c).group(1))
            if lpauto.wb_from(school, pi, plan) <= y <= plan.get('wb_to', 2026):
                srcs.append((c, True))
    cands, unreadable = [], []
    auto_plan = bool(plan.get('strict')) or plan.get('notes', '').startswith('lab-page audit discovery')
    homepage_people = bool(plan.get('homepage_people'))
    coadv = {}
    for src, is_cap in srcs:
        spans = plan.get('span', {})
        orig = None
        if is_cap:
            m_ = kit.lpcap.WAYBACK_RX.match(src)
            orig = m_.group(2) if m_ else None
        sp = spans.get(src) or (spans.get(orig) or spans.get(orig.replace('http://', 'https://')) or spans.get('*')
                                if is_cap and orig else None)
        try:
            ext = kit.autom.extract(school, src, pi, held, span=sp)
        except (ValueError, KeyError) as e:
            if not is_cap:
                unreadable.append((src, str(e)[:200]))
            continue
        for x in ext:
            fn = names.fold(x['name'])
            x['is_cap'] = is_cap
            x['src'] = src
            x['alumni'] = bool(x.get('alumni') or (x['head'] and kit.autom.ALUMNI_RX.search(x['head']))
                               or src in plan.get('alumni_pages', ()) or (orig is not None and any(
                                   orig.replace('http://', 'https://').rstrip('/') == unwayback(a).replace('http://', 'https://').rstrip('/')
                                   for a in plan.get('alumni_pages', ()))))
            x['under_people_heading'] = bool(x['head'] and kit.autom.HEADWORD.search(x['head']))
            x['single_token'] = len(names.parse(x['name'])['tokens']) < 2
            if fn in yrs:
                x['years'], x['years_basis'] = yrs[fn], 'reviewer'
            else:
                x['years'], x['years_basis'] = entry_years(x.get('desc'), x.get('head'))
            x['role'], x['role_basis'] = entry_role(x.get('desc'), x.get('head'), kit.autom._role)
            if fn in roles_:
                x['role'], x['role_basis'] = roles_[fn], 'reviewer'
            if src not in coadv:
                coadv[src] = coadvisers(kit, school, src)
            flagged = [f for f in x['flags'] if f != 'weak-quote']
            why = None
            if CREDIT_RX.search(x.get('quote') or '') or CREDIT_RX.search((x.get('desc') or '')[:60]):
                why, x['detail'] = 'name_unresolved', 'site credit or footer'
            elif any(names.match_one(x['name'], c) for c in coadv[src]):
                why, x['detail'] = 'not_a_student', 'named as a co-adviser (joint with / co-advised with)'
            elif auto_plan and (m_el := (ELSEWHERE_RX.search((x.get('desc') or '')[:220]) or DEGREE_AT_RX.search((x.get('desc') or '')[:120]))) and \
                    not re.search(SCHOOL_NAMES.get(school, '^$'), m_el.group(1)):
                why, x['detail'] = 'at_previous_school', f"the entry places the person at {m_el.group(1)}"
            elif re.search(r'\brotation', (x.get('head') or '') + ' ' + (x.get('desc') or '')[:60], re.I):
                why, x['detail'] = 'not_a_student', 'rotation student'
            elif re.search(r'\bfaculty\b|vice[- ]chancellor|\bdean\b|professors?\b', x.get('head') or '', re.I) and \
                    not ALUMNI_RX.search(x.get('head') or ''):
                why, x['detail'] = 'not_a_student', 'listed under a faculty heading'
            elif re.search(r'high[- ]school', (x.get('head') or '') + ' ' + (x.get('desc') or '')[:60], re.I):
                why, x['detail'] = 'not_a_student', 'high-school outreach student'
            elif auto_plan and not (STUDENT_HEAD.search(x.get('head') or '') or
                                    (not homepage_people and (x['under_people_heading'] or x.get('qkind') == 'name+role'))):
                why = 'not_in_people_section'  # on a homepage, names in the bio prose are collaborators and mentors
            elif auto_plan and plan.get('shared_page') and not re.search(r'\b' + re.escape(fold(family(pi))) + r'\b', fold((x.get('desc') or '')[:200])):
                why, x['detail'] = 'shared_page_no_adviser', f"a people page shared by {plan['shared_page']} labs; the entry does not name this PI"
            elif auto_plan and not plan.get('shared_page') and (fold(family(pi)) in fold((x.get('desc') or '')[:160]) or
                                re.search(r'[“"]|\b(proceedings|conference|journal|workshop|arxiv|ICASSP|Interspeech|ACL|EMNLP|NeurIPS|'
                                          r'ICML|CVPR|pp\.)\b', (x.get('desc') or '')[:160])):
                why, x['detail'] = 'not_in_people_section', 'a byline or citation, not a member entry'
            elif auto_plan and (not (HOMEPAGE_HEAD if homepage_people else STRICT_HEAD).search(x.get('head') or '') or
                                NOT_MEMBER_HEAD.search(x.get('head') or '')):
                why, x['detail'] = 'not_in_people_section', f"section '{(x.get('head') or '')[:60]}' is not a member list"
            elif auto_plan and (not plausible(kit, x['name']) or re.match(r'^[A-Z]\.\s', x['name']) or
                                all(t.isupper() and len(t) <= 4 for t in x['name'].split())):
                why, x['detail'] = 'name_unresolved', 'not a plausible full person name (automatic plan)'
            elif fn in drop or any(names.match_one(x['name'], d) for d in plan.get('drop', [])):
                why = 'reviewer_excluded'
            elif flagged and fn not in keep:
                why = 'outside_2016_2026' if flagged == ['pre-2016'] else 'not_a_student'
            elif (drop_heads and x['head'] and drop_heads.search(x['head'])) or \
                    (plan.get('drop_desc') and re.search(plan['drop_desc'], x['desc'][:80])) or \
                    (only_heads and not (x['head'] and only_heads.search(x['head']))):
                why = 'reviewer_excluded'
            elif is_cap and not x['under_people_heading']:
                why = 'not_in_people_section'
            x['why'] = why
            cands.append(x)
    start = plan.get('pi_start')
    for x in cands:
        if x['why']:
            continue
        fn = names.fold(x['name'])
        ys = x['years']
        if start and start >= 2010 and x['role'] == 'phd' and ys and ys[1] and ys[1] <= start + 4 and fn not in keep:
            x['why'], x['detail'] = 'at_previous_school', f"PhD finished {ys[1]}, within 4 years of the PI's arrival ({start}): begun before it"
            continue
        last = (ys[1] if ys[1] is not None else ys[0]) if ys else None
        end_ = plan.get('pi_end')
        if end_ and fn not in keep and (not ys or (ys[0] or last or 0) > end_):
            x['why'], x['detail'] = 'after_pi_left', (f"the PI left the school in {end_}; " +
                                                      ('undated: cannot place before the move' if not ys else f'dated from {ys[0] or last}'))
            continue
        if auto_plan and start and start >= 2010 and ys and ys[0] and ys[0] < start and fn not in keep:
            x['why'], x['detail'] = 'at_previous_school', f"began {ys[0]}, before the PI's arrival ({start})"
            continue
        current_ = re.search(r'\b(current|present|now)\b', x.get('head') or '', re.I) or \
            re.search(r'\b(\d(st|nd|rd|th)[- ]year|candidate|is a (ph\.?\s?d|graduate|doctoral))', x.get('desc') or '', re.I)
        if plan.get('prior_reviewed') and not ys and not current_ and fn not in keep:
            x['why'], x['detail'] = 'undated_cannot_place', 'undated, not marked current, and not kept by the school\'s own reviewed pass'
            continue
        cap_y = int(re.search(r'/web/(\d{4})', x.get('capture_url') or '/web/2026').group(1))
        destination = re.match(r'^\W{0,3}[-–—]\s*\S', x.get('desc') or '') or \
            re.search(r'\b(now|currently) (at|a|an|with)\b|→|->|\bposition:', (x.get('desc') or '')[:100], re.I)
        listed_now = cap_y >= 2025 and not destination and not x['alumni']  # on a 2025-26 page, not with a later job
        if auto_plan and (start is None or start < 2014) and not ys and fn not in keep and not listed_now and not \
                re.search(r'\b(current|present|now)\b', x.get('head') or '', re.I) and not \
                re.search(r'\b(\d(st|nd|rd|th)[- ]year|candidate|is a (ph\.?\s?d|graduate|doctoral))', x.get('desc') or '', re.I):
            x['why'], x['detail'] = 'undated_cannot_place', (f"an undated entry of a lab older than the window (PI from {start or 'before 2016'}), "
                                                             "not marked current" + ('; it names a later position' if destination else ''))
            continue
        if start and start >= WINDOW[0] and last == start and fn not in keep:  # R-PAP-13's transition year, for people
            x['why'], x['detail'] = 'at_previous_school', f"dated only to the PI's arrival year ({start}): cannot place at this school"
            continue
        if plan.get('min_last_year') and ys and ys[1] is not None and ys[1] < plan['min_last_year']:
            x['why'] = 'at_previous_school'
        elif plan.get('require_years') and not ys and fn not in keep:
            x['why'] = 'undated_cannot_place'
        elif fn not in keep:
            seen = any(c['is_cap'] and not c['alumni'] and not c['why'] and names.match_one(c['name'], x['name']) for c in cands)
            x['why'] = student_reason(dict(x, seen_current_2016=seen), start, plan.get('alumni_ok'))
    return cands, unreadable


def typo_pair(names, a, b):
    """One lab, same first name, family names of 4+ letters one transposition or letter apart ('Mikio Aio' / 'Mikio Aoi')."""
    import difflib
    pa, pb = names.parse(a)['tokens'], names.parse(b)['tokens']
    if len(pa) < 2 or len(pb) < 2 or names.compact(pa[0]) != names.compact(pb[0]):
        return False
    fa, fb = names.compact(pa[-1]), names.compact(pb[-1])
    return min(len(fa), len(fb)) >= 3 and fa != fb and sorted(fa) == sorted(fb) or \
        (min(len(fa), len(fb)) >= 5 and difflib.SequenceMatcher(None, fa, fb).ratio() >= 0.8)


def src_recency(r):
    """Sort key: a live page first, then Wayback captures by timestamp."""
    m = re.search(r'/web/(\d{8,14})', r.get('capture_url') or '')
    return '99999999' if not r.get('is_cap') and not m else (m.group(1) if m else '0')


def group_people(names, rows):
    """Rows of one lab grouped by person (names.match_one within the lab; R-HIER-03: never across labs)."""
    groups = []
    for r in rows:
        g = next((g for g in groups if any(names.match_one(r['name'], o['name']) or typo_pair(names, r['name'], o['name']) for o in g)), None)
        if g is None:
            groups.append([r])
        else:
            g.append(r)
    return groups


STUDENT_REASON_ORDER = ('genuinely_missing', 'evidence_not_in_build', 'dropped_by_review', 'shared_page_no_adviser', 'after_pi_left', 'at_previous_school', 'outside_2016_2026',
                        'undated_alumni_cannot_place', 'undated_cannot_place', 'not_in_people_section', 'reviewer_excluded',
                        'not_a_student', 'name_unresolved')


def audit_students(kit, ctx, p, lab, plan, auto_plan=False):
    """The students section of one lab's audit record, and proposed student additions."""
    school, pi = ctx['school'], p['pi']
    names = kit.names
    bs = build_students(ctx, pi)
    held = [n for _, ns, _ in bs for n in ns]
    sec = dict(page_status=None, pages=[], listed_current=[], listed_alumni=[], matched_in_build=0, missing_from_build=[],
               extra_in_build_not_on_page=0, reason_code=None, reason=None)
    adds = []
    if lab['status'] == 'none_found' and lab['reason_code'] != 'pi_homepage_only_no_lab_site':
        sec.update(page_status='no_lab_page', reason_code='no_lab_page', reason='no lab page or homepage: nothing to audit')
        return sec, adds
    cands, unreadable = pm_candidates(kit, school, pi, dict(plan, pi_start=pi_start_year(p), pi_end=pi_left_year(p)), held) if plan else ([], [])
    prior = ctx['prior'].get(pi) or {}
    ev_rows = list(prior.get('students') or [])
    sec['pages'] = sorted({c['src'] for c in cands} | {r.get('capture_url') or r['url'] for r in ev_rows})
    if not cands and not ev_rows:
        why = 'no_people_section'
        if unreadable:
            why = 'page_not_captured'
        sec.update(page_status=why, reason_code=why,
                   reason=('the lab page lists no students or members' if why == 'no_people_section' else
                           'the people page has no stored capture: ' + '; '.join(u for u, _ in unreadable)[:300]))
        return sec, adds
    sec['page_status'] = 'audited'
    rows = []
    for r in ev_rows:
        rows.append(dict(name=r['name'], role=r.get('role'), years=r.get('years'), quote=r.get('quote'), url=r['url'],
                         capture_url=r.get('capture_url'), sha256=r['sha256'], kept=True,
                         alumni=bool(ALUMNI_RX.search(r.get('note') or '')), why=None, aliases=r.get('aliases') or []))
    for c in cands:
        rows.append(dict(name=c['name'], role=c['role'], years=c['years'], quote=c['quote'], url=c['url'], capture_url=c.get('capture_url'),
                         sha256=c['sha256'], kept=False, alumni=c['alumni'], why=c['why'], head=c.get('head'), desc=c.get('desc'),
                         is_cap=c['is_cap'], detail=c.get('detail'), role_basis=c.get('role_basis'), years_basis=c.get('years_basis')))
    drops = {(x.get('pi'), x.get('student')) for x in corrections(school) if x.get('action') == 'drop'}
    matched_build = set()
    for g in group_people(names, rows):
        nm = g[0]['name']
        alln = [r['name'] for r in g] + [a for r in g for a in r.get('aliases') or []]
        hit = None
        for n in alln:
            h, kind = names.match(n, held)
            if h and kind != 'first-name-only':
                hit = (h, kind)
                break
        alumni = all(r['alumni'] for r in g)
        ys = [y for r in g for y in (r.get('years') or []) if y]
        item = dict(name=nm, role=next((r['role'] for r in g if r.get('role')), None), years=[min(ys), max(ys)] if ys else None)
        (sec['listed_alumni'] if alumni else sec['listed_current']).append(item)
        if hit:
            sec['matched_in_build'] += 1
            matched_build.add(next(i for i, (_, ns, _) in enumerate(bs) if hit[0] in ns))
            continue
        kept = [r for r in g if r['kept']]
        ok_ = sorted((r for r in g if not r['why']), key=src_recency, reverse=True)  # the live page, else the newest capture
        best = next((r for r in g if r['kept']), None) or (ok_[0] if ok_ else g[0])
        if kept:
            slug = re.sub('[^a-z0-9]+', '-', fold(nm)).strip('-')
            rc = 'dropped_by_review' if any(x[0] == pi and str(x[1] or '').endswith(':' + slug) for x in drops) else 'evidence_not_in_build'
        elif not any(r['why'] for r in g) or any(not r['why'] for r in g):
            rc = 'genuinely_missing'
        else:
            rc = min((r['why'] for r in g), key=lambda w: STUDENT_REASON_ORDER.index(w) if w in STUDENT_REASON_ORDER else 99)
        miss = dict(name=nm, role=best.get('role'), years=item['years'], quote=best.get('quote'), url=best.get('capture_url') or best['url'],
                    sha256=best['sha256'], reason_code=rc)
        if best.get('head'):
            miss['section'] = best['head']
        det = next((r.get('detail') for r in g if r.get('detail')), None)
        if det:
            miss['detail'] = det
        sec['missing_from_build'].append(miss)
        if rc == 'genuinely_missing':
            years, ybasis = best.get('years'), best.get('years_basis') or 'none'
            if not years:  # a date another capture of the same person states
                dated = [r for r in ok_ if r.get('years')]
                if dated:
                    years, ybasis = dated[0]['years'], dated[0].get('years_basis') or 'stated_in_entry'
            try:  # the evidence check the build's lab-page rows pass: the quote is verbatim on the stored capture and names the person
                row = kit.lpev.M(school, nm, best.get('role') if best.get('role') in ROLE_OK else 'member', years,
                                 best.get('capture_url') or best['sha256'], quote=best['quote'],
                                 note=f"lab-page audit {TODAY}; section: {best.get('head')}")
            except (ValueError, KeyError) as e:
                miss['reason_code'] = 'name_unresolved'
                miss['note'] = f'quote check failed: {str(e)[:120]}'
                continue
            row.update(pi=pi, alumni=alumni, rule='LP-STU-01', auto=True, pi_first_year=pi_start_year(p),
                       role=best.get('role') if best.get('role') in ROLE_OK else None, role_basis=best.get('role_basis') or 'none',
                       years=years, years_basis=ybasis if years else 'none')
            adds.append(row)
    sec['extra_in_build_not_on_page'] = len(bs) - len(matched_build)
    by = collections.Counter(m['reason_code'] for m in sec['missing_from_build'])
    if by.get('genuinely_missing'):
        sec.update(reason_code='gaps_proposed', reason=f"{by['genuinely_missing']} listed members missing from the build, proposed as additions")
    elif sec['missing_from_build']:
        sec.update(reason_code='all_missing_explained', reason='; '.join(f'{k}: {v}' for k, v in by.most_common()))
    else:
        sec.update(reason_code='complete', reason='every listed member is in the build')
    return sec, adds


# ---------------------------------------------------------------- papers
EXTERNAL_INDEX = re.compile(r'dblp|google scholar|scholar\.google|semantic scholar|orcid|links? (?:to )?(?:his|her|their)? ?(?:dblp|scholar)', re.I)


def paper_sources(ctx, p, lab, plan):
    """Pubs pages ({pubs_page, spec, years}) and manual entries (lpev.P dicts) of a lab plan."""
    pages, manual = [], []
    for x in plan.get('pubs') or []:
        if isinstance(x, dict) and x.get('pubs_page'):
            pages.append(x)
        elif isinstance(x, dict) and x.get('title'):
            manual.append(x)
    return pages, manual


def audit_key(pi, e):
    return hashlib.sha1(f"{pi}|{norm_title(e.get('title'))}|{e.get('year')}".encode()).hexdigest()[:16]


def collect_papers(kit, ctx, p, lab, plan):
    """(papers section without reasons for unresolved entries, entries) of one lab. Every entry: title, year, venue, links,
    url, capture_url, sha256, quote, in_window, match (how), audit_key."""
    pi = p['pi']
    sec = dict(pubs_page_status=None, pages=[], listed=0, in_window_2016_2026=0, matched_in_lab_papers=0, missing=[],
               reason_code=None, reason=None)
    if lab['status'] == 'none_found' and lab['reason_code'] != 'pi_homepage_only_no_lab_site':
        sec.update(pubs_page_status='no_lab_page', reason_code='no_lab_page', reason='no lab page or homepage')
        return sec, []
    pages, manual = paper_sources(ctx, p, lab, plan)
    if not pages and not manual:
        notes = (ctx['prior'].get(pi) or {}).get('notes') or plan.get('notes') or ''
        st = 'external_index_only' if re.search(r'no (separate )?publications? (page|list)[^.]*(dblp|scholar)|links? (to )?(dblp|google scholar)|'
                                                 r'(dblp|scholar)[^.]*instead', notes, re.I) else 'no_pubs_page'
        sec.update(pubs_page_status=st, reason_code=st,
                   reason=('the site points to DBLP / Google Scholar instead of listing papers' if st == 'external_index_only'
                           else 'the lab page has no publications list'))
        return sec, []
    idx = PaperIndex(ctx['lab_papers'].get(pi) or [])
    ents, seen, bad = [], set(), []
    for pg in pages:
        try:
            r, es = kit.pubx.extract(ctx['school'], pg['pubs_page'], pg.get('spec') or {})
        except KeyError as e:
            bad.append(('page_not_captured', pg['pubs_page'], str(e)[:160]))
            continue
        except Exception as e:  # noqa: BLE001 (a page the extractor cannot read)
            bad.append(('page_unparseable', pg['pubs_page'], repr(e)[:160]))
            continue
        if not es and pg.get('prior_url'):
            es = [dict(title=x.get('title'), year=x.get('year'), venue=x.get('venue'), links=x.get('links') or [],
                       quote=x.get('quote'), from_prior_parse=True) for x in prior_rows_for(ctx, pi, pg['prior_url'])]
        if not es:
            bad.append(('page_unparseable', pg['pubs_page'], 'no entries extracted'))
            continue
        sec['pages'].append(dict(url=r['url'], capture_url=r.get('capture_url'), sha256=r['sha256'], entries=len(es), spec=pg.get('spec') or {}))
        for e in es:
            e.update(url=r['url'], capture_url=r.get('capture_url'), sha256=r['sha256'])
            ents.append(e)
    for m in manual:
        ents.append(dict(title=m['title'], year=m.get('year'), venue=m.get('venue'), links=m.get('links') or [], quote=m.get('quote'),
                         url=m.get('url'), capture_url=m.get('capture_url'), sha256=m.get('sha256')))
    out = []
    for e in ents:
        k = norm_title(e['title'])
        if not k or k in seen:
            continue
        seen.add(k)
        y = e.get('year')
        e['in_window'] = bool(y and WINDOW[0] <= int(y) <= WINDOW[1])
        how, row = idx.match(e)
        e['match'] = how
        e['matched_work'] = (row or {}).get('atlasWorkId') or (row or {}).get('work')
        e['audit_key'] = audit_key(pi, e)
        out.append(e)
    sec['listed'] = len(out)
    sec['in_window_2016_2026'] = sum(e['in_window'] for e in out)
    sec['matched_in_lab_papers'] = sum(1 for e in out if e['in_window'] and e['match'])
    sec['matched_outside_window'] = sum(1 for e in out if not e['in_window'] and e['match'])
    if bad:
        sec['page_problems'] = [dict(status=a, url=b, detail=c) for a, b, c in bad]
    sec['pubs_page_status'] = 'audited' if sec['pages'] or manual else (bad[0][0] if bad else 'no_pubs_page')
    return sec, out


AUTHOR_TAIL = re.compile(r"[\s.,;:]+(?:[A-Z][\w'’.-]*\s){1,3}[A-Z][\w'’-]*(?:\s*\*)?(?:\s*,\s*(?:and\s+)?(?:[A-Z][\w'’.-]*\s){1,3}[A-Z][\w'’-]*\*?)+.*$")
AUTHOR_ONLY = re.compile(r"^[A-Z][\w'’-]+, [A-Z][\w.]*(?: [A-Z]\.?)?$")


def clean_listed_title(title, p):
    """(title, how): a listed title with the byline run into it ('Reasoning about physical interactions with object-centric
    models Michael Janner, Sergey Levine, William T Free...') loses the byline when the cut-off part names the PI or holds
    three or more names; a title that is only an author ('Freeman, Joshua T') is marked for the arXiv title (how
    'author_only'); else (title, None)."""
    t = title or ''
    if AUTHOR_ONLY.match(t.strip()):
        return t, 'author_only'
    m = AUTHOR_TAIL.search(t)
    if m and m.start() >= 20:
        tail = fold(m.group(0))
        if any(fold(family(n)) in tail for n in [p['pi']] + list(p.get('names') or [])) or tail.count(',') >= 2:
            return t[:m.start()].rstrip(' .,;:'), 'author_tail_cut'
    return t, None


def arxiv_titles(ids):
    """{arXiv id: title} from the local arXiv OAI-PMH index labpage_recover reads (one pass; only when needed)."""
    import labpage_recover as LR
    want, out = set(ids), {}
    if not want:
        return out
    for f in sorted(LR.ARXIV_OAI.glob('*.jsonl.gz')):
        for line in gzip.decompress(f.read_bytes()).decode().splitlines():
            if line and any(i in line[:40] for i in want):
                a = json.loads(line)
                if a['id'] in want:
                    out[a['id']] = re.sub(r'\s+', ' ', a['title']).strip()
        if len(out) == len(want):
            break
    return out


def fix_titles_from_arxiv(adds):
    """Rows whose title was only an author name, or whose resolved work is an arXiv id with no OpenAlex record, take the
    arXiv record's own title (title_basis arxiv_oai)."""
    need = [a for a in adds if a.get('arxiv') and (a.get('title_basis') == 'author_only' or not (a.get('evidence') or {}).get('oa'))]
    got = arxiv_titles({a['arxiv'] for a in need})
    for a in need:
        t = got.get(a['arxiv'])
        if t:
            a.setdefault('listed_title', a.get('title'))
            a['title'], a['title_basis'] = t, 'arxiv_oai'
        elif a.get('title_basis') == 'author_only':
            a['flags'] = list(a.get('flags') or []) + ['title_is_an_author_name']
    return adds


def recover_dir(school):
    return H / school / 'labpage-audit-recover'


def recover_verdicts(school):
    """{audit_key: (status, junk reason, accepted row or None)} from the shadow recovery store."""
    db = recover_dir(school) / 'hierarchy' / school / 'labpage-recover.sqlite'
    if not db.exists():
        return {}
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    acc = {(pi, k): json.loads(r) for pi, k, r in c.execute('select pi, key, row from accepted')}
    out = {}
    for pi, key, status, reason, row in c.execute('select pi, key, status, reason, row from rows'):
        try:
            r = json.loads(row)
        except (TypeError, ValueError):
            continue
        ak = r.get('audit_key')
        if ak:
            out[ak] = (status, reason, acc.get((pi, key.split(':', 2)[0] + ':' + key.split(':', 2)[1]) if key.count(':') >= 2 else (pi, key)))
    c.close()
    return out


def finish_papers(sec, ents, p, verdicts):
    """Reasons for every listed entry that is not a lab paper; accepted recoveries become proposed additions."""
    start = pi_start_year(p)
    adds = []
    for e in ents:
        if e['match']:
            continue
        base = dict(title=e['title'], year=e.get('year'), venue=e.get('venue'), url=e.get('capture_url') or e.get('url'),
                    sha256=e.get('sha256'))
        if not e.get('year'):
            sec['missing'].append(dict(base, reason_code='undated_entry'))
            continue
        if not e['in_window']:
            sec['missing'].append(dict(base, reason_code='outside_window'))
            continue
        st, why, acc = verdicts.get(e['audit_key'], ('candidate', None, None))
        rc = paper_reason(st, why, e.get('year'), start)
        if rc == 'matched':
            sec['matched_in_lab_papers'] += 1
            continue
        item = dict(base, reason_code=rc, quote=e.get('quote'))
        if st == 'junk' and why:
            item['detail'] = why
        sec['missing'].append(item)
        if rc == 'genuinely_missing' and acc:
            a_ = dict(acc, pi=p['pi'], rule='LP-PAP-01', audit_key=e['audit_key'])
            t_, how_ = clean_listed_title(a_.get('title'), p)
            if how_:
                a_['listed_title'], a_['title'], a_['title_basis'] = a_.get('title'), t_, how_
            adds.append(a_)
    by = collections.Counter(m['reason_code'] for m in sec['missing'] if m['reason_code'] != 'outside_window')
    if sec['pubs_page_status'] != 'audited':
        return adds
    if by.get('genuinely_missing'):
        sec.update(reason_code='gaps_proposed', reason=f"{by['genuinely_missing']} listed papers pass the build rule but are not lab papers: proposed")
    elif by.get('not_yet_resolved'):
        sec.update(reason_code='not_yet_resolved', reason=f"{by['not_yet_resolved']} listed papers await the recovery step")
    elif by:
        sec.update(reason_code='all_missing_explained', reason='; '.join(f'{k}: {v}' for k, v in by.most_common()))
    else:
        sec.update(reason_code='complete', reason='every listed in-window paper is a lab paper')
    return adds


# ---------------------------------------------------------------- the lab record
def page_evidence(kit, url, names_):
    row, views = kit.stored(url) if url else (None, None)
    if not row:
        return None, ''
    txt = views.get('html') or views.get('pdf') or views.get('raw') or ''
    m = re.search(r'<title[^>]*>(.*?)</title>', kit.lpcap.decode(row['content'][:30000]), re.I | re.S)
    title = kit.lpcap.collapse(re.sub(r'<[^>]+>', ' ', m.group(1))) if m else ''
    ev = dict(url=row['url'], sha256=row['sha256'], quote=pi_quote(txt, names_))
    if row.get('capture_url'):
        ev['capture_url'] = row['capture_url']
    return ev, title


def none_reason(p, d, checks):
    """The reason no lab page was found (LAB_REASONS), from the checks."""
    title = fold(' '.join(str(x) for x in [p.get('title'), p.get('rank')] if x))
    start, end = pi_start_year(p), pi_end_year(p)
    if d and any(s.get('other_school') for s in d.get('sites') or []) and end:
        return 'pi_left_school_site_moved', "the PI's live site is at another institution; the school-era site is gone"
    if 'emerit' in title:
        return 'emeritus_or_admin_no_lab', 'emeritus appointment, no lab site'
    if start and start >= 2025:
        return 'new_arrival_no_site_yet', f'joined in {start}; no school lab site yet'
    cand = [c for c in checks if c['source'] == 'candidate_site']
    if cand and all(c['result'] == 'robots_disallowed' for c in cand):
        return 'host_blocked_by_robots', 'robots.txt disallows the only candidate site; no Wayback capture'
    if cand and all(c['result'] == 'bot_challenge' for c in cand):
        return 'host_challenge_no_wayback', 'the only candidate site serves a bot challenge; no Wayback capture'
    if cand and all(re.match(r'http_(4|5)|unreachable|no_capture', c['result']) for c in cand):
        return 'site_dead_no_wayback', 'the known site no longer answers and Wayback holds no capture'
    if any(c['source'] == 'school_profile' and c['result'].startswith('ok') for c in checks):
        return 'profile_only_no_homepage', 'only the department profile exists; it links no homepage or lab site'
    return 'no_web_presence_found', 'no homepage or lab site at any source checked'


# ---------------------------------------------------------------- per-toolkit adapters
PEOPLE_PATH = re.compile(r'people|member|team|student|alumni|group|personnel|advisee|former|lab', re.I)
PUBS_PATH = re.compile(r'publication|papers|pubs|bibliograph|/cv|vita|talks|thesis|teaching|course', re.I)
STRICT_HEAD = re.compile(r'\b(students?|ph\.?\s?d|post-?docs?|post-?doctoral|alumni|alumnae|graduated|graduates|advisees?|members?|team|'
                         r'people|researchers|visitors|undergrad\w*|masters?|interns?|doctoral|staff|former|current)\b', re.I)
HOMEPAGE_HEAD = re.compile(r'\b(students?|ph\.?\s?d|post-?docs?|post-?doctoral|advisees?|alumni|graduated|mentees|group members|'
                           r'lab members|research group|my group)\b', re.I)  # a homepage used as the people page: only these sections
NOT_MEMBER_HEAD = re.compile(r'committee|publication|papers|thesis|theses|talks?|course|collaborat|co-?authors?|press|news|award|'
                             r'service|editor|reviewer|program', re.I)


def adapter_plan(kit, ctx, p, prior):
    """A plan (lpauto keys) for a lab the school's own lab-page pass recorded, read from that pass's outputs:
      cmu       labpage-evidence.json: lab_site, people_page, people_pages (live URLs and Wayback id_ captures),
                pubs_pages [{url, mode, entries, ...}] (hierarchy/labpage-tools-cmu)
      eb        labpage-evidence.json: lab_site, people_page; publications pages = the urls of the PI's rows in
                labpage-pubs.jsonl.gz; reviewer overrides in labpage-tools-epfl-berkeley/manual_pages.json (people: [] =
                the discovered page was rejected; drop: names)
      michigan  labpage-evidence.json (tools/labpage_students_school.py): lab_site, people_page
    The re-parse runs autom.extract over these pages under the strict rules (strict: True); the pass's own rows stay the
    kept evidence rows."""
    pi = p['pi']
    start = pi_start_year(p) or WINDOW[0]
    pages = [prior.get('people_page')] + list(prior.get('people_pages') or [])
    if ctx['cfg']['family'] == 'michigan':  # the Michigan pass's pages live in its school_web container
        pages += sorted({r.get('capture_url') for r in prior.get('students') or [] if r.get('capture_url')})
        kit.import_school_web(str(P.CAPTURES / 'michigan.sqlite'), [prior.get('people_page'), prior.get('lab_site')] + pages)
    man = (ctx.get('manual') or {}).get(pi) or {}
    if 'people' in man:
        pages = list(man['people'])
    live, caps = [], collections.defaultdict(list)
    for u in pages:
        if not u or (u != prior.get('people_page') and not PEOPLE_PATH.search(urlsplit(unwayback(u)).path or '')) or \
                PUBS_PATH.search(urlsplit(unwayback(u)).path or ''):
            continue  # the pass also cited publication lists and homepages for single rows; only people pages are re-parsed
        if re.match(r'^https?://web\.archive\.org/web/', u):
            caps[unwayback(u)].append(u)
        elif u not in live:
            live.append(u)
    pubs = [x['url'] for x in prior.get('pubs_pages') or [] if isinstance(x, dict) and x.get('url')]
    pubs += [u for u in ctx.get('pubs_rows_pages', {}).get(pi, []) if u not in pubs]
    if man.get('no_pubs'):
        pubs = []
    plan = dict(people=[kit.src_of(u) for u in live], wb=list(caps), wb_caps=dict(caps),
                alumni_pages=[u for u in live if re.search(r'alumni|former|past', u, re.I)],
                drop=list(man.get('drop') or []), wb_from=max(WINDOW[0], start), min_last_year=max(WINDOW[0], start),
                pubs=[dict(pubs_page=kit.src_of(u), spec={}, years=list(WINDOW), prior_url=u) for u in pubs[:4]],
                strict=True, prior_reviewed=True,
                homepage_people=bool(prior.get('people_page') and prior.get('lab_site') and
                                     prior['people_page'].rstrip('/') == prior['lab_site'].rstrip('/')), notes=f"lab-page audit adapter ({ctx['cfg']['family']}): {str(prior.get('notes') or '')[:300]}")
    return plan


def prior_rows_for(ctx, pi, url):
    """The school's earlier parse of one publications page (labpage-pubs.jsonl.gz rows: the entries it could not match),
    used when pubx finds no entries on the page."""
    return [r for r in ctx.get('pubs_rows', {}).get(pi, []) if url in (r.get('url'), r.get('page_url'), r.get('capture_url'))]


def lab_record(kit, ctx, p, disc):
    """The lab_page section and the plan the students and papers audits read."""
    school, pi = ctx['school'], p['pi']
    dom = SCHOOLS[school]['domain']
    names_ = list(dict.fromkeys([pi] + list(p.get('names') or [])))
    prior = ctx['prior'].get(pi)
    d = disc.get(pi)
    checks = list((d or {}).get('checks') or [])
    if not d and prior:  # the 2026-10-22 pass's own dossier is the record of what it checked
        for pg in (ctx['dossier'].get(pi) or {}).get('pages', []):
            checks.append(dict(source='prior_labpage_pass_2026-10-22', url=pg.get('capture_url') or pg['url'], at='2026-10-22',
                               result='ok' if pg.get('status') == 200 else (pg.get('error') or f"http_{pg.get('status')}"),
                               kind=pg.get('kind')))
    for c in ((d or {}).get('prior_scan') or {}).get('checks') or []:
        checks.append(c)
    lab = dict(status=None, urls=dict(lab_site=None, people_page=None, alumni_page=None, pubs_page=None), evidence=None,
               reason_code=None, reason=None, checks=checks, discovery_run=bool(d), prior_record=bool(prior))
    plan = dict(ctx['plan'].get(pi) or {})
    if prior and ctx['cfg']['family'] != 'pm':
        plan = adapter_plan(kit, ctx, p, prior)
    site = people = alumni = pubs = None
    if prior and prior.get('lab_site') and not is_profile(prior['lab_site'], dom):
        site, people = prior['lab_site'], prior.get('people_page')
        alumni = next(iter(plan.get('alumni_pages') or []), None)
        pubs = next((x['url'] for x in prior.get('pubs_pages') or []), None) or \
            next((x['pubs_page'] for x in plan.get('pubs') or [] if isinstance(x, dict) and x.get('pubs_page')), None)
        sc = (d or {}).get('prior_scan') or {}
        new_al = [u for u in (sc.get('new_pages') or {}).get('alumni', []) if kit.stored(u)[0]]
        if new_al:  # alumni pages the 2026-10-22 pass never read
            alumni = alumni or new_al[0]
            plan['people'] = list(plan.get('people') or []) + new_al
            plan['alumni_pages'] = list(plan.get('alumni_pages') or []) + new_al
            plan['wb'] = list(plan.get('wb') or []) + new_al
            plan['wb_caps'] = dict(plan.get('wb_caps') or {}, **{u: sc.get('wayback', {}).get(u, []) for u in new_al})
        new_pubs = [u for u in (sc.get('new_pages') or {}).get('pubs', []) if kit.stored(u)[0]]
        if new_pubs and not any(isinstance(x, dict) and x.get('pubs_page') for x in plan.get('pubs') or []) and \
                not any(isinstance(x, dict) and x.get('title') for x in plan.get('pubs') or []):
            pubs = new_pubs[0]
            plan['pubs'] = [dict(pubs_page=new_pubs[0], spec={}, years=list(WINDOW), note='lab-page audit: publications link the 2026-10-22 pass did not use')]
        lab['source'] = ctx['cfg'].get('prior_label', 'prior_labpage_pass_2026-10-22')
    elif d and d['chosen'].get('lab_site'):
        ch = d['chosen']
        site, people, alumni, pubs = ch['lab_site'], ch.get('people_page'), ch.get('alumni_page'), ch.get('pubs_page')
        start = pi_start_year(p) or WINDOW[0]
        srcs = [kit.src_of(u) for u in (people, alumni) if u]
        plan = dict(people=srcs, wb=[u for u in (people, alumni) if u], wb_caps=d.get('wayback') or {},
                    alumni_pages=[alumni, kit.src_of(alumni)] if alumni else [],
                    homepage_people=bool(people and people.rstrip('/') == site.rstrip('/')),
                    wb_from=max(WINDOW[0], start), min_last_year=max(WINDOW[0], start),
                    pubs=[dict(pubs_page=kit.src_of(pubs), spec={}, years=list(WINDOW))] if pubs else [],
                    notes='lab-page audit discovery (automatic plan)')
        if ch.get('other_school'):
            lab['moved_site'] = site
        lab['source'] = 'labpage_audit_discovery'
    if site:
        ev, title = page_evidence(kit, site, names_)
        lab['evidence'] = ev
        lab['title'] = title
        lab['urls'].update(lab_site=site, people_page=people, alumni_page=alumni, pubs_page=pubs)
        if lab.get('moved_site') and pi_end_year(p):
            lab.update(status='none_found', reason_code='pi_left_school_site_moved',
                       reason="the PI left the school; the only site found is at the new institution, not this school's lab page")
        elif lab.get('moved_site'):
            st_ = pi_start_year(p)
            rc = 'new_arrival_no_site_yet' if st_ and st_ >= 2025 else 'site_at_other_institution'
            lab.update(status='none_found', reason_code=rc,
                       reason=(f"joined in {st_}; the only site found is at the previous institution (its students are not this school's)"
                               if rc == 'new_arrival_no_site_yet' else
                               "the only site found is at another institution (joint or previous appointment): not this school's lab page"))
        elif is_lab_site(title, site, people):
            lab.update(status='found', reason_code='lab_site', reason=LAB_REASONS['lab_site'])
        else:
            lab.update(status='none_found', reason_code='pi_homepage_only_no_lab_site', reason=LAB_REASONS['pi_homepage_only_no_lab_site'])
    else:
        rc, why = none_reason(p, d, checks)
        if prior and prior.get('notes'):
            why += f" (2026-10-22 pass: {prior['notes'][:240]})"
        lab.update(status='none_found', reason_code=rc, reason=why)
        if prior and prior.get('lab_site') and is_profile(prior['lab_site'], dom):
            lab['urls']['profile'] = prior['lab_site']
    return lab, plan


def shared_people_pages(ctx, disc):
    """People pages the discovery chose for 2+ labs of the school (BLISS's students.html for Anantharam and Courtade)."""
    c = collections.Counter()
    for d in disc.values():
        u = (d.get('chosen') or {}).get('people_page')
        if u:
            c[re.sub(r'^https?://(www\.)?', '', u).rstrip('/')] += 1
    return {k: n for k, n in c.items() if n >= 2}


def assemble(kit, ctx, disc, verdicts=None, keep=None):
    recs, stu_adds, pap_adds, rec_rows = [], [], [], []
    shared = shared_people_pages(ctx, disc)
    for p in ctx['pis']:
        lab, plan = lab_record(kit, ctx, p, disc)
        pp_ = re.sub(r'^https?://(www\.)?', '', lab['urls'].get('people_page') or '').rstrip('/')
        if pp_ in shared and plan.get('notes', '').startswith('lab-page audit discovery'):
            plan = dict(plan, shared_page=shared[pp_])
            lab['shared_people_page'] = shared[pp_]
        if lab.get('moved_site'):
            plan = dict(plan, people=[], wb=[], pubs=[])
        st, sa = audit_students(kit, ctx, p, lab, plan)
        ps, ents = collect_papers(kit, ctx, p, lab, plan)
        for e in ents:
            if e['in_window'] and not e['match']:
                rec_rows.append(dict(pi=p['pi'], title=e['title'], year=e['year'], venue=e.get('venue'), links=e.get('links') or [],
                                     url=e.get('url'), capture_url=e.get('capture_url'), sha256=e.get('sha256'), quote=e.get('quote'),
                                     audit_key=e['audit_key']))
        if keep is not None:
            keep[p['pi']] = (p, copy.deepcopy(ps), ents)
        pa = finish_papers(ps, ents, p, verdicts or {})
        recs.append(dict(school=ctx['school'], pi=p['pi'], labId=p.get('labId'), departments=p.get('departments'),
                         audited_at=now(), lab_page=lab, students=st, papers=ps))
        stu_adds += sa
        pap_adds += pa
    return recs, stu_adds, pap_adds, rec_rows


# ---------------------------------------------------------------- recover (labpage_recover in a shadow tree)
def patch_mpcap(mpcap):
    """>= 3 s per host, and robots.txt groups naming AI agents honoured, for labpage_recover's PDF fetches."""
    import urllib.robotparser
    mpcap.DEFAULT_GAP = max(mpcap.DEFAULT_GAP, HOST_GAP)
    orig = mpcap.robots_allowed

    def robots_allowed(url):
        if not orig(url):
            return False
        sp = urlsplit(url)
        con = mpcap.connect()
        row = con.execute('SELECT status, content FROM captures WHERE url=? AND error IS NULL ORDER BY id DESC LIMIT 1',
                          (f'{sp.scheme}://{sp.netloc}/robots.txt',)).fetchone()
        con.close()
        if not row or row[0] != 200 or not row[1]:
            return True
        body = zlib.decompress(row[1]).decode('utf-8', 'replace')
        if '<html' in body[:500].lower():
            return True
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(body.splitlines())
        return all(rp.can_fetch(a, url) for a in AI_AGENTS)
    mpcap.robots_allowed = robots_allowed


def relink(target, link):
    """link -> target, replacing a link that points elsewhere (a stale path from before the 2026-10-30 project move)."""
    if not Path(target).exists():
        return
    if link.is_symlink() and os.readlink(link) != str(target):
        link.unlink()
    if not link.is_symlink():
        os.symlink(target, link)


def cmd_recover(school, title_credits=600):
    kit = Kit(school)
    ctx = load_ctx(school, kit)
    disc = read_discovery(school)
    _, _, _, rows = assemble(kit, ctx, disc)
    return run_recovery(school, rows, title_credits)


def run_recovery(school, rows, title_credits=600):
    root = recover_dir(school)
    sh = root / 'hierarchy' / school
    sh.mkdir(parents=True, exist_ok=True)
    for f in ('pis.json', 'lab_papers.jsonl.gz', 'openalex-sweep.sqlite', 'pi-works.sqlite'):
        relink(H / school / f, sh / f)
    relink(H / 'cs-venues.json', root / 'hierarchy' / 'cs-venues.json')
    db = sh / 'labpage-recover.sqlite'
    if not db.exists() and (H / school / 'labpage-recover.sqlite').exists():  # reuse the earlier run's arXiv index and OpenAlex cache
        src = sqlite3.connect(f"file:{H / school / 'labpage-recover.sqlite'}?mode=ro", uri=True)
        dst = sqlite3.connect(db)
        src.backup(dst)
        dst.execute('delete from rows')
        dst.execute('delete from accepted')
        dst.execute('delete from tries')
        dst.commit()
        dst.close()
        src.close()
    with gzip.open(sh / 'labpage-pubs.jsonl.gz', 'wt', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(json.dumps(dict(school=school, recover_rows=len(rows))), flush=True)
    import labpage_recover as LR
    LR.HERE = root
    patch_mpcap(LR.mpcap)
    lockdir = os.path.join(os.environ.get('TMPDIR') or '/tmp', 'lp-ratelimit')  # node-local per-host stamps (not the old scratch path)
    LR.mpcap.LOCKDIR = lockdir
    if not os.environ.get('OPENALEX_API_KEY'):
        print('warning: OPENALEX_API_KEY not set: no OpenAlex DOI or title resolution', flush=True)
    return LR.run(school, workers=4, title_credits=title_credits, floor=OPENALEX_FLOOR)


# ---------------------------------------------------------------- audit and summary
def school_summary(recs, stu_adds, pap_adds):
    labs = collections.Counter(r['lab_page']['status'] for r in recs)
    by_reason = collections.Counter(r['lab_page']['reason_code'] for r in recs)
    s_page = collections.Counter(r['students']['page_status'] for r in recs)
    s_miss = collections.Counter(m['reason_code'] for r in recs for m in r['students']['missing_from_build'])
    p_page = collections.Counter(r['papers']['pubs_page_status'] for r in recs)
    p_miss = collections.Counter(m['reason_code'] for r in recs for m in r['papers']['missing'])
    return dict(
        labs=len(recs), lab_page=dict(labs), lab_page_by_reason=dict(by_reason),
        discovery_run=sum(r['lab_page']['discovery_run'] for r in recs),
        students=dict(page_status=dict(s_page),
                      listed=sum(len(r['students']['listed_current']) + len(r['students']['listed_alumni']) for r in recs),
                      listed_current=sum(len(r['students']['listed_current']) for r in recs),
                      listed_alumni=sum(len(r['students']['listed_alumni']) for r in recs),
                      matched_in_build=sum(r['students']['matched_in_build'] for r in recs),
                      missing_by_reason=dict(s_miss), genuinely_missing=s_miss.get('genuinely_missing', 0),
                      proposed_additions=len(stu_adds),
                      extra_in_build_not_on_page=sum(r['students']['extra_in_build_not_on_page'] for r in recs
                                                     if r['students']['page_status'] == 'audited')),
        papers=dict(page_status=dict(p_page), listed=sum(r['papers']['listed'] for r in recs),
                    in_window=sum(r['papers']['in_window_2016_2026'] for r in recs),
                    matched_in_lab_papers=sum(r['papers']['matched_in_lab_papers'] for r in recs),
                    missing_by_reason=dict(p_miss), genuinely_missing=p_miss.get('genuinely_missing', 0),
                    proposed_additions=len(pap_adds)),
    )


def cmd_audit(school):
    if SCHOOLS[school].get('read_only'):
        sys.exit(f'{school}: read-only audit from its own outputs is not implemented yet')
    kit = Kit(school)
    ctx = load_ctx(school, kit)
    disc = read_discovery(school)
    verdicts = recover_verdicts(school)
    recs, stu_adds, pap_adds, _ = assemble(kit, ctx, disc, verdicts)
    write_audit(school, recs, stu_adds, pap_adds)


def refinish(recs, keep, verdicts):
    """The papers sections and paper additions again under new recovery verdicts, from the sections kept before
    finish_papers ran (the students sections and lab pages do not depend on the recovery)."""
    adds = []
    for r in recs:
        p, ps0, ents = keep[r['pi']]
        ps = copy.deepcopy(ps0)
        adds += finish_papers(ps, ents, p, verdicts)
        r['papers'] = ps
    return adds


def cmd_recover_audit(school, title_credits=600):
    """recover, then audit, in one process: the labs are assembled once (CMU's assembly takes over an hour)."""
    kit = Kit(school)
    ctx = load_ctx(school, kit)
    disc = read_discovery(school)
    keep = {}
    recs, stu_adds, _, rows = assemble(kit, ctx, disc, recover_verdicts(school), keep=keep)
    run_recovery(school, rows, title_credits)
    pap_adds = refinish(recs, keep, recover_verdicts(school))
    write_audit(school, recs, stu_adds, pap_adds)


def write_audit(school, recs, stu_adds, pap_adds):
    fix_titles_from_arxiv(pap_adds)
    out = H / school / 'labpage-audit.jsonl.gz'
    with gzip.open(str(out) + '.tmp', 'wt', encoding='utf-8') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    os.replace(str(out) + '.tmp', out)
    summ = school_summary(recs, stu_adds, pap_adds)
    adds = dict(school=school, generated_at=now(), tool='tools/labpage_audit.py', standard='docs/LAB-PAGES.md',
                status='proposed, unreviewed: not read by tools/pi_hierarchy.py until wired (docs/LAB-PAGES.md, integration)',
                rules={'LP-STU-01': RULE_TEXT['LP-STU-01'], 'LP-PAP-01': RULE_TEXT['LP-PAP-01']},
                students=stu_adds, papers=pap_adds)
    json.dump(adds, open(H / school / 'labpage-additions.json', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    sp = H / 'labpage-audit-summary.json'
    allsum = read(sp) if sp.exists() else {}
    allsum[school] = dict(summ, audited_at=now())
    json.dump(allsum, open(sp, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    write_md(allsum)
    print(json.dumps({school: summ}, indent=1, ensure_ascii=False))


RULE_TEXT = {
    'LP-STU-01': ("A person listed on the PI's own lab page (people, members, alumni section; live page or a Wayback id_ capture), "
                  "under a people heading, not the PI, not in a faculty/collaborator/staff section, not another PI of the school, whose "
                  "stated years do not end before 2016 or before the PI's appointment at the school, and who is dated or listed as "
                  "current on a 2016+ capture (undated alumni only when the lab has only ever been at this school) is a lab member: "
                  "the same admission the 2026-10-22 lab-page rows had (labpage-evidence.json, R-STU-01 'researched advisees'), with "
                  "url, sha256 and a verbatim quote naming the person."),
    'LP-PAP-01': ("A paper listed on the PI's own lab publications page whose resolved work carries the PI on the byline, falls in "
                  "the PI's appointment (R-PAP-01) and whose PI authorship lists the school (or page 1 ties the school to the PI) is a "
                  "lab paper with identity 'labpage_listing' (R-PAP-04: the lab's own publications page), exactly the rows "
                  "tools/labpage_recover.py accepts into labpage-recovered.jsonl.gz."),
}


def write_md(allsum):
    order = [s for s in SCHOOLS if s in allsum]
    L = ['# Lab-page audit', '', f'Generated {now()} by `tools/labpage_audit.py`; method and reason codes in `docs/LAB-PAGES.md`.', '',
         '## Lab pages', '', '| school | labs | found | none found | none found by reason |', '|---|---:|---:|---:|---|']
    for s in order:
        x = allsum[s]
        rs = ', '.join(f'{k} {v}' for k, v in sorted(x['lab_page_by_reason'].items(), key=lambda kv: -kv[1]) if k != 'lab_site')
        L.append(f"| {s} | {x['labs']} | {x['lab_page'].get('found', 0)} | {x['lab_page'].get('none_found', 0)} | {rs} |")
    L += ['', '## Students listed on lab pages', '', '| school | listed | current | alumni | in build | missing (reason: n) | genuinely missing | proposed |',
          '|---|---:|---:|---:|---:|---|---:|---:|']
    for s in order:
        x = allsum[s]['students']
        rs = ', '.join(f'{k} {v}' for k, v in sorted(x['missing_by_reason'].items(), key=lambda kv: -kv[1]) if k != 'genuinely_missing')
        L.append(f"| {s} | {x['listed']} | {x['listed_current']} | {x['listed_alumni']} | {x['matched_in_build']} | {rs} | "
                 f"{x['genuinely_missing']} | {x['proposed_additions']} |")
    L += ['', '## Papers listed on lab pages', '', '| school | listed | 2016-2026 | lab papers | missing (reason: n) | genuinely missing | proposed |',
          '|---|---:|---:|---:|---|---:|---:|']
    for s in order:
        x = allsum[s]['papers']
        rs = ', '.join(f'{k} {v}' for k, v in sorted(x['missing_by_reason'].items(), key=lambda kv: -kv[1]) if k != 'genuinely_missing')
        L.append(f"| {s} | {x['listed']} | {x['in_window']} | {x['matched_in_lab_papers']} | {rs} | {x['genuinely_missing']} | {x['proposed_additions']} |")
    L += ['', '## Hand checks of proposed additions', '',
          '| school | checked | students sampled | membership errors | role/year errors | papers sampled | paper errors | notes |',
          '|---|---|---:|---:|---:|---:|---:|---|']
    for s_ in order:
        hp = H / s_ / 'labpage-handcheck.json'
        if not hp.exists():
            continue
        hc = read(hp)
        for k in [hc] + list(hc.get('rechecks') or []):
            st, pa = k.get('students') or {}, k.get('papers') or {}
            L.append(f"| {s_} | {k.get('checked_at', '')} | {st.get('sampled', '')} | {st.get('membership_errors', '')} | "
                     f"{st.get('role_or_year_errors', st.get('role_errors', ''))} | {pa.get('sampled', '')} | {pa.get('errors', '')} | "
                     f"{str(k.get('label') or '')[:80]} |")
    open(H / 'LABPAGE-AUDIT.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n')


def cmd_summary():
    sp = H / 'labpage-audit-summary.json'
    write_md(read(sp) if sp.exists() else {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['discover', 'recover', 'audit', 'recover-audit', 'all', 'summary'])
    ap.add_argument('school', nargs='?')
    ap.add_argument('--pi', nargs='*')
    ap.add_argument('--redo', action='store_true')
    ap.add_argument('--redo-unrecorded', action='store_true', help='discover again every lab the 2026-10-22 pass did not record')
    ap.add_argument('--title-credits', type=int, default=600)
    a = ap.parse_args()
    if a.cmd in ('discover', 'all'):
        cmd_discover(a.school, a.pi, a.redo, a.redo_unrecorded)
    if a.cmd == 'recover':
        cmd_recover(a.school, a.title_credits)
    if a.cmd in ('recover-audit', 'all'):
        cmd_recover_audit(a.school, a.title_credits)
    if a.cmd == 'audit':
        cmd_audit(a.school)
    if a.cmd == 'summary':
        cmd_summary()


if __name__ == '__main__':
    main()
