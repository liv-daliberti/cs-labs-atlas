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
import fcntl
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
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import census_overrides as CO  # noqa: E402
import student_decisions as SD  # noqa: E402
import visiting as VIS  # noqa: E402

H = P.HIERARCHY
HT = Path(__file__).resolve().parents[1] / 'hierarchy'   # the tracked lab-page toolkits (hierarchy/labpage-tools-*) of THIS checkout or snapshot, not the main checkout's: a toolkit fix on a branch must be the code that runs (Georgia Tech friction 29)
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
    'site_at_other_institution': "a people page of a lab at another institution (its host, or a header naming another school and never this one)",
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
class SchoolTable(dict):
    """The legacy schools' hand tables; any other charter school gets an entry from its charter (protocol schools since Michigan: pages in the
    school_web container, family 'michigan'), so a new school needs no edit here (UChicago PROTOCOL-FRICTION 26)."""
    def __missing__(self, key):
        import school_config
        try:
            cfg = school_config.get(key)
        except KeyError:
            raise KeyError(key) from None
        doms = (cfg.get('web') or {}).get('domains') or []
        return dict(family='michigan', domain='|'.join(re.escape(d) for d in doms) or '^$')


def own_names(school, table):
    """Own-institution spellings of a school: the hand table's, else the key, the name's initials and its long words (charter name)."""
    if school in table:
        return table[school]
    import school_config
    name = school_config.get(school).get('name') or school
    words = [w for w in re.findall(r"[A-Za-z]+", name) if w.lower() not in ('of', 'the', 'at', 'and')]
    return {school.upper(), ''.join(w[0] for w in words).upper()} | {w.upper() for w in words if len(w) >= 5 and w.lower() != 'university'}


def school_names_rx(school):
    if school in SCHOOL_NAMES:
        return SCHOOL_NAMES[school]
    import school_config
    return re.escape(school_config.get(school).get('name') or school) + '|' + re.escape(school)


LEGACY_SCHOOLS = {'princeton', 'mit', 'cmu', 'epfl', 'berkeley', 'stanford', 'michigan'}   # the hand-table schools: their lab pages legitimately omit the PI's name
SCHOOLS = SchoolTable({
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
})
SCHOOL_NAMES = dict(princeton=r'Princeton', mit=r'MIT|Massachusetts Institute', cmu=r'CMU|Carnegie Mellon', epfl=r'EPFL|[EÉ]cole Polytechnique',
                    berkeley=r'Berkeley|UCB', stanford=r'Stanford', michigan=r'Michigan|UMich|U-M\b')
DEGREE_AT_RX = re.compile(r"\b(?i:ph\.?\s?d|m\.?s|b\.?s|m\.?eng|msc|bsc)\.?,?\s*(?:19|20)\d\d\s*\(([A-Z][\w&.' -]{1,40})\)")  # 'PhD 2016 (DTU)'
ELSEWHERE_RX = re.compile(r"\b(?i:ph\.?\s?d\.?|graduate|doctoral|master'?s|undergraduate) (?i:student|candidate)"
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


NEWS_LINE = re.compile(r'\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+20[12]\d\s*[:\-–]', re.I)


OTHER_INST = re.compile(r'(?:@|\bat\s+|,\s*|\(\s*)(?:the\s+)?(?:University of [A-Z][\w-]+|(?:[A-Z][\w-]+ ){1,3}(?:University|Institute of Technology|College)|Universit[ée] [A-Z][\w-]+(?: [A-Z][\w-]+)?|MIT|UCSB|UCLA|UCSD|Caltech|CMU|'
                        r'Dartmouth|Virginia Tech|Purdue|Rice|Brown|Cornell|Yale|Harvard|Columbia|Duke|Emory|Vanderbilt|Northwestern|NYU|UIUC|Berkeley|Stanford|Penn State|Texas A&M|Ohio State|Wisconsin)\b')


def advised_by_other(desc, quote, pi):
    """R-LAB-03 (Georgia Tech round 2): 'Shriya Karam (MIT ORC PhD, advised by Alexandre Jacquillat)' under 'Other students': the entry names its own adviser and the PI is not one of them."""
    m = re.search(r'(?<!co-)(?<!co )(?<!jointly )(?<!joint )advised by\s+([^;)\]]{3,80})', f'{desc or ""} {quote or ""}', re.I)   # 'co-advised by Prof. X' on this PI's page is a co-supervision tie: a member (HKUST re-audit ruling)
    return bool(m) and fold(family(pi)) not in fold(m.group(1))


def primary_adviser_other(desc, quote, pi):
    """'(PhD, started in 2025, primary advisor Prof. Guoming Tang )' on another professor's page: the entry names a different primary advisor / supervisor (no co- / joint wording), so the student is that
    professor's, not this PI's (HKUST Qiong Luo's DSA-program list)."""
    t = f'{desc or ""} {quote or ""}'
    m = re.search(r'(?<!co-)(?<!co )(?<!joint )(?<!second )\b(?:primary\s+|main\s+|principal\s+)?(?:advisor|adviser|supervisor)\b\s*(?:is|:)?\s*((?:Prof\.?|Professor|Dr\.?)?\s*[A-Z][^;)\]]{2,60})', t)
    return bool(m) and fold(family(pi)) not in fold(m.group(1)) and not re.search(r'\bco-?(?:advis|supervis)|\bjoint', t, re.I)


def author_list_item(quote, ptxt):
    """A run of comma-separated personal names ('Wei Fu, Jiaxuan Gao, Xujie Shen, ...', 'Simon C. H. Yu, Wilbur C. K. Wong, and') that is followed on the page by a quoted paper title or a venue is the byline of
    a reference, not a roster (HKUST Chung, Yuan). Needs the page text to see what follows the run."""
    q = (quote or '').strip()
    pieces = [x.strip(' *') for x in re.split(r',|\band\b', q) if x.strip(' *')]
    namey = [x for x in pieces if re.fullmatch(r"[A-Z][\w.'\u2019-]*(?:\s+[A-Z][\w.'\u2019-]*){0,3}", x)]
    if (len(pieces) < 3 and not re.search(r'(?:,|\band)\s*$', q)) or len(pieces) < 2 or len(namey) < len(pieces) - 1 or ',' not in q or '(' in q:
        return False
    j = (ptxt or '').find(q)
    after = (ptxt or '')[j + len(q): j + len(q) + 700] if j >= 0 else ''
    return bool(re.search(r'[\u201c"][^\u201d"]{12,}[\u201d"]|\barXiv\b|\bProceedings\b|\bConference\b|\bJournal\b|\bet al\b|\(\s*(?:19|20)\d\d\s*\)', after[:600] + ' ' + q))


def other_institution_entry(desc, quote, school):
    """A roster entry whose descriptor says the person is at ANOTHER institution ('M.S. student, ECE@Rice University, Sept. 2017 - Sept. 2019'): the PI's lab at the previous institution
    (Georgia Tech round 4: Celine Lin's Rice-era students). Georgia Tech itself, and the 'Next Move' destination after it, do not count: only text before 'Next Move' / an arrow is read."""
    t = re.split(r'next move|→|->|\bnow\b', f'{desc or ""} {quote or ""}', flags=re.I)[0]
    own = {'michigan': 'michigan', 'gatech': 'georgia', 'uchicago': 'chicago'}.get(school, school.lower())
    return any(own not in m.group(0).lower() and not re.search(school_names_rx(school), m.group(0)) for m in OTHER_INST.finditer(t))   # the school's own full name never counts (CMU: 'Carnegie Mellon University')


def stale_list(x, page_alumni):
    """R-LAB-02: an undated current entry on a page whose newest dated alumnus left at least 8 years before the page's capture year (Georgia Tech round 2: Ahamad's 2024 capture
    lists 2000s students as 'Current Graduate Students' above 'Former Ph.D. Students (2001)')."""
    last = page_alumni.get(x.get('capture_url'))
    m = re.search(r'/web/(\d{4})', x.get('capture_url') or '')
    return bool(last and m and int(m.group(1)) - last >= 8)


STAFF_RX = re.compile(r'\b(?:administrative|admin)\s+(?:associate|assistant|coordinator|manager)|\bexecutive assistant\b|\boffice manager\b|\b(?:program|student services|department) (?:coordinator|administrator|manager)\b', re.I)
# Stanford round 7 (2026-11-11): the Contact block of a Stanford Profile lists the PI's administrators ('Contact Administrator Renee Quiroz',
# 'Contact Admin. Support Melissa Cromosini', 'Alternate Contact Isabelle London'); the block's heading chain ends in 'Contact', and the
# profile's degree line above it ('Ph.D., MIT, ... (2010)') had read it as a PhD-students section.
CONTACT_HEAD_RX = re.compile(r'^\W*(?:alternate\s+|primary\s+)?contacts?\b', re.I)
CONTACT_STAFF_RX = re.compile(r'\b(?:administrator|admin\.?\s+support|administrative(?:\s+support)?|alternate contact|assistant to)\s*$', re.I)
FOOTER_YEAR_RX = re.compile(r'(?:©|\bcopyright\b|\blast (?:updated|modified)\b)\D{0,30}((?:19|20)\d\d)', re.I)


PROSE_COLLAB_RX = re.compile(r'\b(?:worked|work|collaborated|collaborates?|collaborating|co-?authored)\s+(?:closely\s+)?with\s*$', re.I)
CHAIR_AFTER_RX = re.compile(r'^\W{0,3}(?:co-?chairs?|chairs?|co-?advisors?|advisors?|committee|readers?)\b', re.I)


def prose_nonmember(name, desc, quote):
    """Stanford round 7: a name that is a faculty collaborator or committee chair, not a member. 'I also worked with Vahideh Manshadi' (Ashlagi) is
    prose about a collaborator; 'Will Monroe (2018 ...; Lyn Frazier co-chair)' in a PI's dissertation list names the student's other chair."""
    q = (quote or '').rstrip()
    before = q[:-len(name)] if name and q.endswith(name) else ''
    if PROSE_COLLAB_RX.search(before):
        return 'a collaborator named in a sentence ("worked with ..."), not a member'
    if CHAIR_AFTER_RX.search(desc or ''):
        return 'named as a co-chair or adviser of a listed student, not a member'
    return None


INCOMING_RX = re.compile(r"\bincoming\b|\badmitted\s+(?:for|to|in)\b|\bwill\s+(?:join|start|begin)\b[^.]{0,40}\b(?:fall\s+|spring\s+)?20(?:2[7-9]|3\d)\b|\b(?:fall|spring|autumn)\s+20(?:2[7-9]|3\d)\b|[(\uff08]\s*20(?:2[7-9]|3\d)\s*[)\uff09]|\b(?:to\s+)?(?:start|commence|begin|join)\w*\b[^.;)]{0,50}\b20(?:2[7-9]|3\d)\b", re.I)
JOINT_OTHER_RX = re.compile(r"(?:co-?supervised\s+by|jointly?\s+(?:supervised|trained|training|program|with)|joint\s+(?:PhD|training|student))[^.;]{0,90}?\b(?:Laboratory|Institute|Academy)\b|\b(?:Shanghai\s+AI\s+Laborator\w*|Shanghai\s+Innovation\s+Institute|Shanghai\s+Artificial\s+Intelligence\s+Laborator\w*)\b", re.I)


def incoming_entry(desc, quote):
    """'incoming Ph.D. (Fall 2027)', 'admitted for 2027', 'will join in fall 2027': a future student is not a member yet (SJTU round 6: 3 wrong rows)."""
    return bool(INCOMING_RX.search(f'{desc or ""}'[:140]) or INCOMING_RX.search((quote or '')[:140]))


def joint_other_institute_entry(desc, quote, school):
    """A joint or co-supervised entry with another institute ('Co-supervised by Prof. X (Shanghai AI Laboratory)'): not a member of this school's lab unless the page ties it to the PI's lab here (SJTU round 6: Zihan Guo)."""
    m = JOINT_OTHER_RX.search(f'{desc or ""}'[:160])
    return bool(m) and not re.search(school_names_rx(school), m.group(0))


def admin_staff_entry(head, desc, quote):
    """Stanford rounds 6 and 7: an 'Administrative Associate' (Jenny Lam), or any name in the Contact block of a Stanford Profile (Pavone,
    Demszky, Hinds, Wong: administrators and alternate contacts), is staff, not a student of the lab. The staff title in the entry decides, and
    a student / PhD word in the entry itself keeps the name; a name under a heading that ends in 'Contact' is never read as an advisee."""
    t = f'{desc or ""} {quote or ""}'[:160]
    if re.search(r'\b(?:ph\.?d|student|postdoc|candidate|advisee)\b', t, re.I):
        return False
    last_head = (head or '').split(' > ')[-1] if ' > ' in (head or '') else (head or '')
    if CONTACT_HEAD_RX.search(last_head):
        return True
    before = (quote or '').rsplit(' ', 2)[0] if quote else ''
    return bool(STAFF_RX.search(t) or CONTACT_STAFF_RX.search(before))


def stale_footer_year(text, capture_year=None):
    """Stanford round 6 (open repair 2 of docs/LAB-PAGES.md) and round 7: the newest year of a copyright / last-updated footer when it is before 2016,
    else None. A page that says 'Copyright 2012' is an old page even when captured in 2024; its 'current' students are pre-window. Round 7: a page
    that also names any year from 2016 on is maintained (Kozyrakis's students page: footer 2008, entries to 2018), so the footer alone never decides."""
    ys = [int(m.group(1)) for m in FOOTER_YEAR_RX.finditer(text or '')]
    last = max(ys) if ys else None
    if not last or last >= 2016 or (capture_year is not None and capture_year < last + 2):
        return None
    if any(int(y) >= 2016 for y in re.findall(r'(?<!\d)(20[12]\d)(?!\d)', text or '')):
        return None
    return last


TALK_HEAD = re.compile(r'\b(?:invited talks?|keynotes?|talks?|awards?|honors?|service|news|outreach|organizer|new position)\b', re.I)


def talk_item(head, quote):
    """A line under a CV / news heading ('Invited Talk NeurIPS-ViGIL', 'Outreach', 'New Position') is not a roster entry (Georgia Tech round 4: Jesse Thomason)."""
    return bool(TALK_HEAD.search(head or '') and not re.search(r'student|member|people|advis', head or '', re.I))


def byline_item(quote):
    """A candidate whose whole quote is 'Name,' is one name of a publication byline ('Zhongjie Shi, Wenjing Liao  Generalization ...'), not a roster entry (Georgia Tech round 3)."""
    q = (quote or '').strip()
    return bool(q) and q.endswith(',') and (len(q.split()) <= 4 or q.count(',') >= 3)   # 'A, B , C, D,': a comma-separated author list (HKUST hand check 2026-11-10)


MPHIL_RX = re.compile(r'\bm\.?\s?phil\b|\bmaster\s+by\s+research\b|\bMbR\b', re.I)


def label_role(desc, head):
    """The role an entry's own first label states ('(MPhil student, ...)', '(RA, 2025-2026)', '(Exchange student, undergrad)', '(Research intern, graduate student from X)',
    '(UGVIS, 2024)'), which the roster's section heading must not outvote, else a nameless-role row under an 'M.Phil. Students' heading. None when the entry states no such label.
    The first comma-separated label decides; a later 'graduate student' / 'undergraduate' qualifies an internship, it is not the role (HKUST re-audit 2026-11-12)."""
    d = (desc or '').strip()
    m = re.match(r'^\W{0,3}\(?\s*([^,()]{1,60})(?:,([^()]{0,70}))?', d)
    if m:
        first, rest = re.sub(r'\s*(?:19|20)\d\d\b.*$', '', m.group(1).strip()), (m.group(2) or '')   # '(RA 2026, PhD@...)': a year after the label is not part of it
        if re.search(r'\bvisiting\b', first, re.I):
            return None   # R-STU-17 reads these
        if MPHIL_RX.search(first):
            return 'masters'
        if re.search(r'\bexchange\b', first, re.I):
            return 'visiting'
        if re.fullmatch(r'(?:UG|PG)VIS', first):
            return 'visiting'   # HKUST 'UGVIS' / 'PGVIS': an undergraduate / postgraduate visiting student
        if re.search(r'\bintern(?:ship)?\b', first, re.I):
            return 'undergraduate' if re.search(r'undergrad|\bUG\b', first + ' ' + rest, re.I) else 'other'
        if re.fullmatch(r'(?:RA|research assistant|research associate|part-time research assistant)', first, re.I):
            return 'other'
    if re.match(r'^\W{0,3}Current position:', d):   # an alumni card 'Name Current position: X <dates> University Postdoctoral fellow in ...': the stay's own role follows the dates (HKUST uav Xin Zhou)
        d2 = re.sub(r'^\W{0,3}Current position:.*?(?=(?:[A-Z][a-z]+\s+)?(?:19|20)\d\d\s*[-\u2013])', '', d, count=1, flags=re.S)
        if d2 != d and re.search(r'^.{0,140}?\bpost-?doc(?:toral)?\b\s+(?:fellow|researcher|associate|scholar)', d2[:200], re.I | re.S):
            return 'postdoc'
    last = (head or '').split(' > ')
    if any(re.search(r'\bm\.?\s?phil\b[^>]*\bstudents?\b|\bmaster\s+by\s+research\b', h, re.I) for h in last) and not re.search(r'\b(?:ph\.?\s?d|doctoral|postdoc)', ' '.join(last[-1:]), re.I):
        return 'masters'
    return None


def localize_quote(x, ptxt):
    """A candidate whose quote runs from a section heading or the previous entries ('Ivan (Yin Fung) Lok (UROP, 2025) Li Zhang ... Chaobo Jia') gets the entry's own text
    'Name (descriptor)' when the page text holds it verbatim, so the quote names this person and no neighbour (HKUST re-audit: Chaobo Jia, Zeyu Xiong, Yichuan Li)."""
    q = x.get('quote') or ''
    name, desc = x.get('name') or '', re.sub(r'\s+', ' ', x.get('desc') or '').strip()
    if not name or not desc or q.startswith(name) or not ptxt:
        return
    pt = re.sub(r'\s+', ' ', ptxt)
    for n in (100, 70, 45, 28):
        cut = desc[:n].rstrip()
        if n < len(desc) and ' ' in cut:
            cut = cut.rsplit(' ', 1)[0]
        for cand in (name + ' ' + cut, name + cut):
            if cand in pt and len(cand) > len(name) + 4:
                x['quote'], x['qkind'] = cand, 'name+role'
                return


def citation_fragment_item(quote, desc=None):
    """A candidate whose quote opens on a closing bracket ('), San Francisco', ') . DOI website . · Pei Wang') is the tail of a reference line (a conference place, a paper's author), not a roster entry."""
    if re.match(r'^\s*[)\]]', quote or ''):
        return True
    return bool(re.search(r'[\u201c"][^\u201d"]{15,}[\u201d"]', (quote or '') + ' ' + (desc or '')))   # a quoted paper title in the entry: a bibliography line, not a roster entry


PUBLICATION_HEAD = re.compile(r'\b(?:selected\s+)?(?:publications?|papers|preprints?|journal articles?|conference papers?|refereed)\b', re.I)
CITATION_TAIL = re.compile(r'[\u201c"][^\u201d"]{12,}[\u201d"]\s*[.,]?\s*(?:in\b|to appear|proceedings|arxiv|ieee|acm|usenix|\w+ \d{4}|\()', re.I)


def publication_item(head, desc, quote):
    """A name inside a publication list ('Xiaozhe Yao, Youhe Jiang, ... \u201cLLMFabric: ...\u201d In 20th USENIX ...', HKUST hand check 2026-11-10: 5 of 13 sampled
    students were coauthors) is a paper coauthor, not a roster entry: the section is a publications heading, or the entry carries a quoted title followed by a venue."""
    if head and PUBLICATION_HEAD.search(head.split(' > ')[-1]) and not re.search(r'\b(?:students?|alumni|members?|team|people)\b', head, re.I):
        return True
    q = quote or ''
    if re.match(r"^(?:[A-Z][\w.'\u2019-]+(?:\s+[A-Z][\w.'\u2019-]+){0,3}\s*,\s*){3,}[A-Z]", q.strip()) and not re.search(r'\b(?:students?|alumni|members?|team|people|group)\b', (head or '') + ' ' + q[:30], re.I):
        return True   # 'Weiyu Xie , Mingxing Zhang , Xia Liao , ... Yongwei Wu The 29th ACM ...': an author list of a paper, not a roster (Tsinghua round 1, \u7ae0\u660e\u661f's page)
    if len(q) > 120 and len(re.findall(r'\b[A-Z]{3,}[A-Za-z]*\s+(?:19|20)\d\d\b', q)) >= 2:
        return True   # several 'CRYPTO 2024' venue-year strings in one quote: a publication list read as a roster (CMU round 6, Jain: Ying Feng)
    return bool(CITATION_TAIL.search((desc or '')[:400]) or CITATION_TAIL.search((quote or '')[:400]))


def current_position_list(head):
    """A section called 'Current Position' is the alumni's job column ('Ebrahim Shaji  Current Position'): its names are alumni, undated."""
    return bool(head and re.match(r'\s*current position\b', head, re.I))


def news_item(text):
    """A dated news sentence ('August 2025: Patrick Kastner and I just received a seed grant') names a collaborator, not a roster entry (Georgia Tech round 2)."""
    return bool(NEWS_LINE.search(text or ''))


def moved_in_alumnus(start, ys, alumni, destination):
    """A PI who arrived at the school inside the window (first period / listing year 2016+) lists alumni of their previous institution on the same page: an UNDATED entry that is an
    alumnus or names a later position ('(Current: Faculty at ...)', '-> Google') cannot be placed at this school (Georgia Tech round 1: Prakash's Virginia Tech PhDs)."""
    return bool(start and start >= WINDOW[0] and not ys and (alumni or destination))


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
            if int(m.group(1)) <= WINDOW[0] and re.search(r'LOWER BOUND', q.get('note') or ''):
                continue   # a lower bound at the window's floor is the first dated listing, not an arrival (CMU round 6: Grossmann, 2016-06-03, was read as a new lab)
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


# Owner ruling 2026-11-12: a robots.txt that answers HTTP 200 with an HTML page holding no robots lines (an SPA catch-all) is 'no rules';
# a service-error / challenge / login page (cloudflare, captcha, anubis, 'Request Error', 'Access Denied', ...) is still not permission.
ROBOTS_LINE_RX = re.compile(r'^\s*(?:user-agent|disallow|allow|sitemap|crawl-delay)\s*:', re.I | re.M)
ROBOTS_HTML_REFUSE_RX = re.compile(r'cf[-_]chl|cf-browser-verification|just a moment|attention required|checking your browser|verify you are (?:a )?human|making sure you.re not a bot|'
                                   r'techaro|anubis[-_.]|g-recaptcha|h-captcha|data-sitekey|bot[- ]?(?:detection|check|protection)|traffic check|type=["\']?password|'
                                   r'<title>[^<]{0,80}(?:log\s?in|sign\s?in|forbidden|unauthori[sz]ed|blocked|error|denied|captcha|challenge|cloudflare|anubis)', re.I)
ROBOTS_HTML_SHORT_RX = re.compile(r'cloudflare|captcha|anubis|request\s+error|access\s+denied|challenge', re.I)   # a short page (a service error / bot-check stub) saying so; a long SPA shell may mention a CDN or a research challenge


def html_robots_is_no_rules(body):
    """True for a 200 robots.txt body that is an HTML page without any robots line and without challenge/error/login markers."""
    b = body or ''
    if '<html' not in b[:2000].lower() and '<!doctype html' not in b[:500].lower():
        return False
    return not ROBOTS_LINE_RX.search(b) and not ROBOTS_HTML_REFUSE_RX.search(b[:60000]) and not (len(b) < 12000 and ROBOTS_HTML_SHORT_RX.search(b))



def names_project_agents(robots_body):
    names = '|'.join(re.escape(agent) for agent in AI_AGENTS)
    return bool(re.search(r'^\s*user-agent\s*:\s*(?:' + names + r')\s*(?:#.*)?$', robots_body, re.I | re.M))

def _host_throttle():
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'fulltext-push'))
    try:
        import host_throttle as HT
        return HT
    except ImportError:
        return None
    finally:
        _sys.path.pop(0)


def archive_original_url(url):
    """Original host policy also applies to CDX lookups and playback URLs."""
    if (urlsplit(url).hostname or '') not in ('web.archive.org', 'archive.org'):
        return None
    if '/cdx/' in urlsplit(url).path:
        return (parse_qs(urlsplit(url).query).get('url') or [''])[0].rstrip('*')
    return unwayback(url)



def transport_policy_denied(host_use, host):
    return host_use(host) in ('none', 'wayback-only')


def live_only_send(send, deferred, request, denied=None, record_denial=None, record_redirect=None, **kwargs):
    """Also stop archive redirects at the transport boundary, before any socket call."""
    if (urlsplit(request.url).hostname or '') in ('web.archive.org', 'archive.org'):
        deferred.add(request.url)
        raise RuntimeError('archive network disabled by live-first mode')
    host = urlsplit(request.url).hostname or ''
    if denied and denied(host):
        raise RuntimeError(f'live host previously refused access: {host}')
    # A redirect destination has not passed its own robots/source checks.
    # Return the 3xx response for recorded follow-up; never automatically visit it.
    kwargs['allow_redirects'] = False
    response = send(request, **kwargs)
    if record_redirect and getattr(response, 'status_code', None) in (301, 302, 303, 307, 308):
        record_redirect(request.url, response.status_code, response.headers.get('Location'))
    if record_denial and getattr(response, 'status_code', None) in (403, 429):
        record_denial(host, response.status_code)
    return response


def remember_live_redirect(school, url, status, location):
    """Keep held destinations reviewable without treating them as fetched pages."""
    path = P.RATE_STAMPS / 'labpage-held-redirects.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as out:
        fcntl.flock(out, fcntl.LOCK_EX)
        out.write(json.dumps(dict(school=school, url=url, status=status, location=location,
                                  checked_at=now(), result='redirect_held_unchecked_destination')) + '\n')


def live_denials(path=None):
    path = Path(path or P.RATE_STAMPS / 'labpage-live-denials.json')
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def remember_live_denial(host, status, path=None):
    path = Path(path or P.RATE_STAMPS / 'labpage-live-denials.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        states = live_denials(path)
        states.setdefault(host, {'status': status, 'at': now()})
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(states))
        temp.replace(path)


def cached_archive_only(lpcap, school, url, deferred):
    hit = lpcap.cached(school, url)
    if hit:
        return hit
    deferred.add(url)
    return {'url': url, 'capture_url': None, 'status': None, 'error': 'archive-deferred-live-first', 'content': b''}

class Kit:
    """hierarchy/labpage-tools-princeton-mit loaded for one school: lpcap (fetch + store), lpev (capture lookup and quote
    checks), autom (member extraction), pubx (publication extraction), names (matching). New captures go to
    hierarchy/<school>/labpage-audit-captures.sqlite (LPCAP_LOCAL); reads also cover the school's earlier stores.
    Patched here, not in the toolkit: >= 3 s per host (Wayback 6 s), and robots.txt groups naming AI agents honoured."""

    def __init__(self, school):
        cfg = SCHOOLS[school]
        self.school = school
        self.deferred_archive_urls = set()
        self.store = P.data('labpage-audit-captures.sqlite', school)
        os.environ['LPCAP_LOCAL'] = str(self.store)
        extra = [str(P.data(f, school)) for f in cfg.get('extra_stores', [])]
        if (P.data('labpage-captures.sqlite', school)).exists():
            extra.append(str(P.data('labpage-captures.sqlite', school)))
        os.environ['LPCAP_EXTRA'] = ':'.join(extra)
        sys.path.insert(0, str(HT / PM))
        import lpcap, lpev, autom, pubx, names  # noqa: E401
        self.lpcap, self.lpev, self.autom, self.pubx, self.names = lpcap, lpev, autom, pubx, names
        if os.environ.get('CS_ATLAS_LABPAGE_LIVE_ONLY') == '1':
            send = lpcap._sess.send
            lpcap._sess.send = lambda request, **kw: live_only_send(
                send, self.deferred_archive_urls, request,
                denied=lambda host: live_denials().get(host) or (hasattr(self, 'host_use') and transport_policy_denied(self.host_use, host)),
                record_denial=remember_live_denial,
                record_redirect=lambda url, status, location: remember_live_redirect(school, url, status, location), **kw)
        lpcap.ROOT = pubx.ROOT = str(H)  # the toolkit's own constant predates tools/atlas_paths.py; its file paths now go through atlas_paths.data
        for k_ in list(lpcap.DBS) + [school]:
            lpcap.DBS[k_] = str(P.data('labpage-captures.sqlite', k_))
            lpcap.SISTER[k_] = [p_.replace(str(Path(p_).parents[1]), str(H)) for p_ in lpcap.SISTER.get(k_, [])]
        lpcap.DEFAULT_GAP = max(lpcap.DEFAULT_GAP, HOST_GAP)
        lpcap.LOCKDIR = str(P.RATE_STAMPS / 'hosts')  # shared per-host stamps (atlas_paths RATE_STAMPS), one pace for every job and node
        owait = lpcap._wait
        def _guarded_wait(host):
            owait(host or '_no-host_')  # a link with no host must not name the lock directory itself
            if (host or '').endswith('archive.org'):
                # shared Wayback clock and 429 cooldown (fulltext-push/host_throttle.py, 2026-11-10): wait the cooldown out, low priority
                HT = _host_throttle()
                if HT is not None:
                    HT.wait_slot('web.archive.org', WAYBACK_GAP, low=True)
        lpcap._wait = _guarded_wait
        oinsert = lpcap._insert

        def _insert_noting_429(con, orig, final, cap, status, body, ctype, err, *a, **k):
            if status == 429 and 'archive.org' in str(orig) + str(final):
                HT = _host_throttle()
                if HT is not None:
                    HT.record_429('web.archive.org')   # every client now waits the shared cooldown
            return oinsert(con, orig, final, cap, status, body, ctype, err, *a, **k)
        lpcap._insert = _insert_noting_429
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
        if os.environ.get('CS_ATLAS_LABPAGE_LIVE_ONLY') == '1':
            # Seed the shared stop list from recorded refusals, so a fresh batch
            # does not ask a denied host again merely because its process is new.
            for source in dict.fromkeys([str(self.store), lpcap.DBS[school]]):
                if not os.path.exists(source):
                    continue
                with sqlite3.connect(f'file:{source}?mode=ro', uri=True) as db:
                    denied_rows = db.execute('SELECT url, final_url, status FROM captures WHERE capture_url IS NULL AND status IN (403,429)').fetchall()
                for url, final, status in denied_rows:
                    host = urlsplit(final or url).hostname or ''
                    if host and not host.endswith('archive.org'):
                        remember_live_denial(host, status)
        try:  # the school charter's host policy (schools/<key>.toml): 'none' is never fetched, live or Wayback; 'wayback-only'
            import school_config as SC  # hosts are read only from Wayback id_ captures (Michigan: Deep Blue, news, record; umich.edu)
            SC.get(school)
            self.host_use = lambda h: SC.host_use(school, h)
        except Exception:  # noqa: BLE001 (a school without a charter: every host live, robots and challenges still checked)
            self.host_use = lambda h: 'live'
        ofetch = lpcap.fetch

        def fetch(school_, url, **kw):
            original = archive_original_url(url)
            use = self.host_use(urlsplit(original).hostname or '') if original else self.host_use(lpcap.host_of(url) or '')
            if original and (use == 'none' or not self._ai_allowed(original)):
                return {'url': url, 'capture_url': None, 'status': None, 'error': 'off-limits-host', 'content': b''}
            if original and os.environ.get('CS_ATLAS_LABPAGE_LIVE_ONLY') == '1':
                return cached_archive_only(lpcap, school_, url, self.deferred_archive_urls)
            if use == 'none':
                return {'url': url, 'capture_url': None, 'status': None, 'error': 'off-limits-host', 'content': b''}
            if not original and os.environ.get('CS_ATLAS_LABPAGE_LIVE_ONLY') == '1':
                refusal = live_denials().get(urlsplit(url).hostname or '')
                if refusal and not lpcap.cached(school_, url):
                    return {'url': url, 'capture_url': None, 'status': None, 'http_status': refusal['status'],
                            'error': 'previous-host-refusal-no-retry', 'content': b''}

            if use == 'wayback-only' and not lpcap.WAYBACK_RX.match(url) and 'web.archive.org/cdx/' not in url:
                return {'url': url, 'capture_url': None, 'status': None, 'error': 'wayback-only-host', 'content': b''}
            return ofetch(school_, url, **kw)
        lpcap.fetch = fetch
        pis = read(P.data('pis.json', school))  # autom's is-a-PI flag: every PI of the school, not only the 2026-10-22 input
        autom._all_pis[school] = list(dict.fromkeys(n for p_ in pis for n in [p_['pi']] + list(p_.get('names') or [])))

    def _ai_allowed(self, url):
        import urllib.robotparser
        sp = urlsplit(url)
        # the URL's own scheme first. A usable own-scheme row decides. An own-scheme redirect or error row defers to a usable row of the other scheme
        # when there is one (NTU: http://www robots 301 shadowed the https 200); alone it stays 'not permission'. No own-scheme row: the other scheme's newest row.
        other = 'https' if sp.scheme == 'http' else 'http'
        own, oth = f'{sp.scheme}://{sp.netloc}/robots.txt', f'{other}://{sp.netloc}/robots.txt'
        sel = 'SELECT status, content FROM captures WHERE url=? AND capture_url IS NULL '
        clean = 'AND error IS NULL AND status NOT IN (301,302,303,307,308) '
        body, st, recorded = '', None, False
        for path in [str(self.store), self.lpcap.DBS[self.school]]:
            if not os.path.exists(path):
                continue
            c = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=60)
            row = c.execute(sel + clean + 'ORDER BY id DESC LIMIT 1', (own,)).fetchone()
            if not row:
                own_any = c.execute(sel + 'ORDER BY id DESC LIMIT 1', (own,)).fetchone()
                row = (c.execute(sel + clean + 'ORDER BY id DESC LIMIT 1', (oth,)).fetchone() if own_any else None) or own_any \
                    or c.execute(sel + 'ORDER BY id DESC LIMIT 1', (oth,)).fetchone()
            c.close()
            if row:
                recorded = True
                st, body = row[0], (zlib.decompress(row[1]).decode('utf-8', 'replace') if row[1] else '')
                break
        if not recorded:
            return True  # caller's robots fetch has not occurred yet
        if st == 200 and '<html' in body[:500].lower() and html_robots_is_no_rules(body):
            return True  # an SPA catch-all page served at /robots.txt: no rules (owner 2026-11-12)
        if st != 200 or '<html' in body[:500].lower():
            return st in (404, 410)  # redirects/errors/challenge HTML are not usable permission
        if os.environ.get('CS_ATLAS_LABPAGE_LIVE_ONLY') == '1' and names_project_agents(body):
            return False  # the top-25/source policy excludes hosts naming these agents entirely
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
        tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'live', 'captures'} <= tables:
            # Older schools use an unrelated pages/linkcheck database at this
            # logical path. Their normal lpcap caches remain the source of bytes.
            src.close()
            return 0
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
    if r.get('error') == 'robots-unknown':
        return 'robots_unknown'
    if r.get('error') in ('bot-challenge', 'host-challenged-skip'):
        return 'bot_challenge'
    if r.get('error') == 'off-limits-host':
        return 'off_limits'
    if r.get('error') == 'archive-deferred-live-first':
        return 'wayback_deferred'
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
WEBWORD = re.compile(r'\b(web\s*sites?|websites?|home\s*pages?|homepages?|web\s*pages?|webpages?|personal pages?|personal sites?|lab|laboratory|'   # plural: Oxford CS 'Personal web pages with links'
                     r'group|research group|research site|visit)\b', re.I)
PEOPLE_LINK = re.compile(r'^\W*((our|the|lab|group|current)\s+)?(people|members?|team|group members?|lab members?|students?|'
                         r'personnel|researchers|group|lab|research group|who we are|advisees|phd students|\u5728\u8bfb\u7814\u7a76\u751f|\u5728\u8bfb\u5b66\u751f|\u56e2\u961f\u6210\u5458|\u8bfe\u9898\u7ec4\u6210\u5458|\u5b9e\u9a8c\u5ba4\u6210\u5458|\u6210\u5458|\u5b66\u751f|\u7814\u7a76\u751f|\u4eba\u5458|\u56e2\u961f)\W*$', re.I)
ALUMNI_LINK = re.compile(r'\b(alumni|alumnae|alums|former (members|students|group members|lab members)|past (members|students)|'
                         r'graduated students|previous members)\b', re.I)
PUBS_LINK = re.compile(r'^\W*((selected|recent|all|full|research|our|lab|group)\s+)?(publications?|papers|bibliography|pubs|'
                       r'publication list|list of publications)\W*$', re.I)
STUDENT_HEAD = re.compile(r'\b(students?|advisees?|ph\.?\s?d|postdocs?|group members|lab members|current members|alumni|'
                          r'graduated|mentees|research group|post-?docs?|post-?doctoral|graduates?|undergrad\w*|members|team|people|'
                          r'researchers|visitors|former|current|doctoral|masters?|interns?|staff)\b', re.I)
GENERIC_PAGE_RX = re.compile(r'/(undergraduate|graduate|admissions?|visit|apply|news|events?|students|academics|programs?|'
                             r'giving|calendar|directory|about-us|contact)\b', re.I)
PROFILE_RX = re.compile(r'/(people|faculty|directory|profiles?|persons?|staff|our-people|bios?)/(profile/|faculty/)?[^/?#]+'
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
    if not re.search(dom, h):
        return False
    if re.match(r'^profiles?\.', h):
        return '~' not in (url or '')
    m = re.search(dom, h)
    before = [l for l in h[:m.start()].strip('.').split('.') if l]
    if len(before) >= 2 and before[0] not in ('www', 'people', 'faculty', 'ihome', 'ee', 'cs'):   # a lab on a school sub-domain (nics.ee, hcsi.cs, fi.ee ...): its /people/<name>/ pages are the lab's, not a directory profile (Tsinghua site-finder, \u674e\u5b66\u6e05)
        return False
    return bool(PROFILE_RX.search(urlsplit(url).path or '') and '~' not in (url or ''))


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
        elif PEOPLE_LINK.match(t) or re.search(r'/(people|members|team|group|students?|lab-members|our-team|personnel)(\.html?|/)?$', path):
            out['people'].append(href)
    return {k: list(dict.fromkeys(v)) for k, v in out.items()}


def has_student_section(kit, row):
    try:
        t = kit.lpcap.page_text(row['content'], row.get('content_type'))
    except Exception:  # noqa: BLE001
        return False
    return bool(re.search(r'(current|graduate|ph\.?\s?d\.?|doctoral|former|past)\s+(students|advisees|members)|\bstudents\s*:|'
                          r'\badvisees\b|\bmy (students|group)\b|\bgroup members\b|\bpostdocs?\b', t, re.I))


def apply_registered_people_page(kit, ctx, pi, site_url, chosen, pages, add):
    """The lab-websites register's reviewed people_page for this PI, when it sits on the chosen site's host, is the people page whatever the site's own links say
    (AISL sjtuaiseclab.github.io/student/ was never linked as 'people'); it must still fetch (robots, pacing) as a 200 page."""
    reg = (ctx.get('registered') or {}).get(pi) or {}
    pp = reg.get('people_page')
    if not pp or chosen.get('people_page') == pp or urlsplit(pp).hostname != urlsplit(site_url).hostname:
        return False
    rr = kit.get(pp)
    add('registered_people_page', pp, result_of(rr), on=site_url, capture_url=rr.get('capture_url'), sha256=rr.get('sha256'))
    if rr.get('status') == 200 and rr.get('content'):
        chosen['people_page'] = pp
        pages.append(('people', pp))
        return True
    return False


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
    reg0_ = (ctx.get('registered') or {}).get(p['pi'])
    if reg0_ and full:
        add('lab_websites_register', reg0_['url'], 'registered')
        cand(reg0_['url'], 'earlier_homepage_find')
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
            if unit_profile_path(lu, names_):
                profiles.append(lu)   # the census listing page IS the unit's own profile of the PI ('/eezhiyao'): its links are read as a school profile
            if r.get('status') == 200 and r.get('content'):
                base = link_base(r, lu)
                for href, txt in site_links(kit, r, base):
                    if txt and len(txt) < 60 and any(kit.names.match_one(txt, n) for n in names_) and not social(href):
                        profiles.append(unwayback(href))
                    elif profile_slug_hit(href, names_) and not social(href):
                        # R-LAB-01 (2026-11-05): a directory card whose link text is 'Learn more about <name>' (ECE) matches no name, but its path ends in the PI's name slug
                        profiles.append(unwayback(href))
        prof_ = lab_profile_url(p)   # the census profile of a PI the current listing no longer shows (a departed PI's '/people/First.Last')
        if prof_:
            profiles.append(prof_)
        for e in [e for q in p.get('periods') or [] for e in q.get('evidence') or []] + [p.get('piBasis') or {}]:
            u = unwayback(e.get('url') or '')
            if re.search(dom, urlsplit(u).hostname or '') and re.search(r'/(people|faculty|profile|directory)/', u) and \
                    fam and fam.replace(' ', '-') in fold(u):
                profiles.append(u)
            elif re.search(dom, urlsplit(u).hostname or '') and str(e.get('kind') or '').startswith('unit_listing') and unit_profile_path(u, names_):
                profiles.append(u)   # a unit's own short profile address ('/eezhiyao', '/zilim': the unit handle carries a name token of the PI) that the census recorded as the PI's listing page
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
                    # a personal-page link on the profile's own host ('Personal web pages with links' -> /people/samson.abramsky/home.html, Oxford CS) when its path carries the PI's name
                    own_host_personal = own_host_personal_link(href, txt, ph, fam_toks) or same_account_personal_link(href, txt, prof)
                    if (WEBWORD.search(txt or '') and hh != ph) or (named and hh != ph) or own_host_personal or \
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
        prof_ = lab_profile_url(p)   # the census profile of a PI the current listing no longer shows (a departed PI's '/people/First.Last')
        if prof_:
            profiles.append(prof_)
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
        if recorded and src == 'prior_labpage_pass' and kit.stored(u)[0]:
            continue  # a prior URL without captured bytes still needs checking
        r = kit.get(u)
        res = result_of(r)
        txt = ''
        if r.get('status') == 200 and r.get('content'):
            try:
                txt = kit.lpcap.page_text(r['content'], r.get('content_type'))
            except Exception:  # noqa: BLE001
                txt = ''
        names_pi = bool(fam and fam in fold(txt))
        if txt and not names_pi:   # a Han-keyed PI's Latin-only page: the shared name signal (registry Latin names + pinyin family AND given), never identity (owner: pypinyin allowed as a signal)
            try:
                import pi_name_signal as N_
                names_pi = bool(N_.page_names_pi(txt, p['pi'], p.get('names')))
            except Exception:  # noqa: BLE001
                pass
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
        apply_registered_people_page(kit, ctx, p['pi'], s['url'], chosen, pages, add)
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
def wired_paper_row(r):
    """A lab-paper row the build took from the accepted lab-page additions (source 'labpage_addition:<rule>:<basis>')."""
    return str(r.get('source') or '').startswith('labpage_addition:')


def without_wired_additions(students, school, wired=None):
    """R13 (Georgia Tech friction 36): the build already holds the accepted additions, so an audit run against it saw every wired student as 'in the build' and regenerated the
    additions without them, which un-wired them at the next build. A student record whose relations ALL come from rows of the currently accepted additions (same PI, same page
    sha256) is dropped from the build the audit compares against; a record with another source (a roster, an adviser list) stays."""
    if wired is None:
        from pihier.common import accepted_additions
        wired = accepted_additions(school, 'students')
    shas = collections.defaultdict(set)
    for r in wired:
        shas[r['pi']].add(r.get('sha256'))
    out = {}
    for pi, recs in students.items():
        keep = []
        for r in recs:
            src = {x.get('sha256') for rel in r.get('relations') or [] for x in rel.get('sources') or []}
            if src and src <= shas.get(pi, set()):
                continue
            keep.append(r)
        out[pi] = keep
    return out


def load_ctx(school, kit=None, plan=True):
    cfg = SCHOOLS[school]
    ctx = dict(school=school, cfg=cfg)
    ctx['pis'] = read(P.data('pis.json', school))
    # reviewed departures not yet in a rebuilt pis.json (R-PAP-03): the audit reads census-overrides.json's faculty_end_moved
    # periods directly, so after_pi_left applies before the coordinator's rebuild lands
    ovs = CO.section(school)
    for p_ in ctx['pis']:
        o_ = ovs.get(p_['pi']) or {}
        pers = [q for q in o_.get('periods') or [] if q.get('end') and any(e.get('kind') == 'faculty_end_moved' for e in q.get('evidence') or [])]
        if pers and not any(q.get('end') for q in p_.get('periods') or []):
            p_['periods'] = [dict(q, asof=q.get('asof') or TODAY) for q in pers]
            p_['periods_from_overrides'] = True
    ctx['students'] = without_wired_additions(read(P.data('students.json', school)), school)
    lp = collections.defaultdict(list)
    for r in read(P.data('lab_papers.jsonl.gz', school)):
        if wired_paper_row(r):
            continue   # R13 for papers: a paper the build holds only through the accepted additions is not 'already a lab paper' for the audit that regenerates them
        lp[r['pi']].append(r)
    ctx['lab_papers'] = lp
    ev = P.data('labpage-evidence.json', school)
    ctx['prior'] = {r['pi']: r for r in read(ev)} if ev.exists() else {}
    inp = P.data('labpage-input.json', school)
    ctx['input'] = {r['pi']: r for r in read(inp)} if inp.exists() else {}
    ctx['dossier'] = {}
    ctx['plan'] = {}
    if cfg['family'] == 'pm':
        d = H / cfg['tools'] / cfg['dossier']  # route-ok: tracked code that stays in hierarchy/
        ctx['dossier'] = read(d) if d.exists() else {}
        if plan and kit is not None:
            import importlib
            ctx['plan'] = importlib.import_module(cfg['plan']).P
    ctx['pubs_rows'], ctx['pubs_rows_pages'] = collections.defaultdict(list), collections.defaultdict(list)
    pr = P.data('labpage-pubs.jsonl.gz', school)
    if pr.exists() and cfg['family'] != 'pm':
        for r in read(pr):
            ctx['pubs_rows'][r['pi']].append(r)
            u = r.get('page_url') or r.get('url')
            if u and u not in ctx['pubs_rows_pages'][r['pi']]:
                ctx['pubs_rows_pages'][r['pi']].append(u)
    ctx['manual'] = {}
    mp = HT / 'labpage-tools-epfl-berkeley' / 'manual_pages.json'
    if cfg['family'] == 'eb' and mp.exists():
        ctx['manual'] = read(mp).get(school) or {}
    ctx['seeds'] = {}
    if cfg['family'] == 'st':  # Stanford's pass kept its pages in decisions.json and wrote no evidence file
        dp = H / cfg['tools'] / 'decisions.json'  # route-ok: tracked code that stays in hierarchy/
        for pi_, d_ in (read(dp) if dp.exists() else {}).items():
            ctx['seeds'][pi_] = [x['url'] for x in d_.get('pages') or [] if x.get('url')]
    hf = P.FT_RAW / f'pi-homepages-{school}.json'
    ctx['homepage_finds'] = read(hf) if hf.exists() else {}
    ctx['registered'] = {}   # the lab-websites register's own reviewed lab site / people page per PI (a registered people_page is honoured by discovery)
    rp_ = P.data('lab-websites.json', school)
    if rp_.exists():
        try:
            for e_ in (read(rp_).get('labs') or []):
                if e_.get('pi') and e_.get('url') and e_.get('coverage') == 'website':
                    ctx['registered'][e_['pi']] = dict(url=e_['url'], people_page=e_.get('people_page'))
        except (ValueError, AttributeError, OSError):
            ctx['registered'] = {}
    ctx['dblp_persons'] = {}
    return ctx


def load_dblp(ctx):
    if not ctx['dblp_persons']:
        want = {pid for p in ctx['pis'] for pid in p.get('dblp') or []}
        d = read(P.data('dblp-dump-persons.json.gz'))['persons']
        own = P.data('dblp-dump-persons-school.json.gz', ctx['school'])   # an onboarding school's own persons (UChicago friction 43/44)
        if own.exists():
            d = {**d, **read(own)['persons']}
        ctx['dblp_persons'] = {k: v for k, v in d.items() if k in want}
    return ctx['dblp_persons']


def discovery_path(school):
    return P.data('labpage-audit-discovery.jsonl', school)


def read_discovery(school):
    out = {}
    p = discovery_path(school)
    if p.exists():
        for line in open(p, encoding='utf-8'):
            if line.strip():
                r = json.loads(line)
                out[r['pi']] = r  # the latest record per PI wins
    return out


def same_account_personal_link(href, txt, prof):
    """HKUST CSE style (2026-11-10): the profile /admin/people/faculty/profile/<id> links the personal page /~<id>/ or /faculty/<id>/ of the SAME account id on the same
    host, with the anchor 'Personal Webpage'. The account id need not contain the family name (wilfred, gchan, cktang)."""
    slug = [x for x in urlsplit(prof).path.split('/') if x][-1:] or ['']
    pth = urlsplit(href)
    return (pth.hostname or '') == (urlsplit(prof).hostname or '') and bool(WEBWORD.search(txt or '')) and bool(slug[0]) and \
        bool(re.match(r'^/(?:~' + re.escape(slug[0]) + r'|faculty/' + re.escape(slug[0]) + r')(?:/|$)', pth.path))


def own_host_personal_link(href, txt, ph, fam_toks):
    """A profile link on the profile's own host that is the PI's personal page: its anchor says homepage/web pages and its path carries the PI's family name, and it is not a
    publication list ('Personal web pages with links' -> /people/samson.abramsky/home.html on Oxford CS)."""
    return (urlsplit(href).hostname or '') == ph and bool(WEBWORD.search(txt or '')) and any(t in fold(href) for t in fam_toks) and not re.search(r'/publications?/', href)


def lab_profile_url(p):
    """The school profile URL the census recorded for a PI (pis.json lab.url, often a root-relative '/people/Samson.Abramsky'), made absolute against the
    host of the PI's newest department listing. None when the PI has no such URL or no listing to take the host from. Live department listings no longer
    show a PI who left, so discovery found no school profile for 34 Oxford PIs (2026-11-10)."""
    u = ((p.get('lab') or {}).get('url') or '').strip()
    if not u or re.match(r'^https?://web\.archive\.org', u):
        return None
    if u.startswith('/'):
        ls = sorted(p.get('listings') or [], key=lambda l: -(l.get('year') or 0))
        if not ls:
            return None
        base = urlsplit(unwayback(ls[0]['url']))
        u = f'{base.scheme}://{base.netloc}{u}'
    return u if re.search(r'/(people|faculty|profile|directory)/', u) else None


def profile_slug_hit(href, names):
    """The last path segment of a directory card's link is the PI's name slug ('/directory/arijit-raychowdhury', '/people/gregory-abowd-0'), a numeric suffix allowed.
    A slug needs at least a given and a family token, so a bare surname never matches."""
    seg = [x for x in urlsplit(href).path.split('/') if x][-1:]
    if not seg:
        return False
    s = seg[0].lower()
    for n in names:
        tk = [x for x in re.sub(r'[^a-z ]', ' ', fold(n)).split() if x]
        # '-' (gatech, Georgia Tech 'gregory-abowd-0') or '.' (Oxford CS '/people/Samson.Abramsky': discovery found no profile for 34 Oxford PIs, 2026-11-10) between the name tokens
        if len(tk) >= 2 and re.fullmatch(re.escape('-'.join(tk)) + r'(-\d+)?', s) or len(tk) >= 2 and re.fullmatch(re.escape('.'.join(tk)) + r'(\.\d+)?', s):
            return True
    return False


def unit_profile_path(url, names):
    """True when `url` is a short path (one or two segments) on the unit's host whose last segment carries a given-name or family-name token of the PI
    ('/eezhiyao' for Zhiyao Xie, '/zilim' for Zili Meng, '/eekhaled'); a listing index ('/people_list', '/people') never qualifies."""
    segs = [x for x in urlsplit(url).path.split('/') if x]
    if not segs or len(segs) > 2 or segs[-1].lower() in ('people', 'people_list', 'faculty', 'directory'):
        return False
    last = fold(segs[-1])
    toks = {t for n in names for t in re.findall(r'[a-z]{3,}', fold(n))}
    return any(t in last for t in toks)


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
        kit.deferred_archive_urls.clear()
        prior = ctx['prior'].get(p['pi'])
        try:
            rec = discover_lab(kit, school, p, ctx, full=True)
            if prior:
                rec['prior_scan'] = scan_prior(kit, school, p, ctx)
        except Exception as e:  # noqa: BLE001 (one lab's failure is recorded and the run goes on; --redo retries it)
            rec = dict(pi=p['pi'], checked_at=now(), checks=[dict(source='discovery_error', url=None, at=now(), result=repr(e)[:300])],
                       chosen=dict(lab_site=None), sites=[], wayback={}, error=repr(e)[:300])
        rec['checks'].extend(dict(source='wayback_pending', url=u, at=now(), result='wayback_deferred')
                             for u in sorted(kit.deferred_archive_urls))
        rec['had_prior_record'] = bool(prior)
        out.write(json.dumps(rec, ensure_ascii=False) + '\n')
        out.flush()
        print(json.dumps(dict(pi=p['pi'], chosen=rec['chosen'].get('lab_site'), kind=rec['chosen'].get('kind'),
                              people=rec['chosen'].get('people_page'), pubs=rec['chosen'].get('pubs_page'),
                              checks=len(rec['checks'])), ensure_ascii=False), flush=True)
    out.close()



# ---------------------------------------------------------------- students
ROLE_OK = {'phd', 'postdoc', 'masters', 'undergraduate', 'visiting', 'member', 'other'}   # `visiting`: R-STU-17, tools/visiting.py


def build_students(ctx, pi):
    """[(display name, [name + aliases], record)] of the lab's students in the build."""
    out = []
    for r in ctx['students'].get(pi) or []:
        out.append((r['name'], [r['name']] + list(r.get('aliases') or []), r))
    return out


def corrections(school):
    p = P.data('student-corrections.json')
    return [x for x in (read(p) if p.exists() else []) if x.get('school') == school]


CREDIT_RX = re.compile(r'©|\bcopyright\b|template design|designed by|design by|powered by|all rights reserved|photo(graph)? (by|credit)', re.I)
COADV_RX = re.compile(r'(?:joint(?:ly)?|co-?advised|co-?supervised|co-?mentored|co-?advisor|together)\s+(?:with|by)\s+(?:(?:Prof\.?|Professor|Dr\.?)\s+)?'
                      r'([A-Z][\w.\'’-]+(?:\s+[A-Z][\w.\'’-]+){1,3})')


_plaus = {}


def plausible(kit, name):
    """lpdom.plausible_person (hierarchy/labpage-tools-epfl-berkeley): the given name occurs in bylines or rosters."""
    if 'f' not in _plaus:
        sys.path.append(str(HT / 'labpage-tools-epfl-berkeley'))
        import lpdom
        _plaus['f'] = lpdom.plausible_person
    try:
        return _plaus['f'](name)
    except Exception:  # noqa: BLE001
        return True


INST_RX = re.compile(r"\b(?:University of [A-Z][\w-]+(?: [A-Z][\w-]+)?|[A-Z][\w-]+ University|UC [A-Z][a-z]+(?: [A-Z][a-z]+)?|"
                     r"ETH Z[uü]rich|ETH|EPFL|MIT|Stanford|Berkeley|Carnegie Mellon|CMU|Princeton|UCSD|UCLA|Harvard|Yale|Cornell|"
                     r"Columbia|Caltech|Georgia Tech|Max Planck|INRIA|Oxford|Cambridge|Toronto|TU [A-Z][a-z]+)\b")
_HOST_INST = re.compile(r'(ethz\.ch|\.ac\.[a-z]{2}$|\.edu$|\.edu\.[a-z]{2}$|mpg\.de|inria\.fr|uni-[a-z]+\.de|tum\.de)')


def page_institution(kit, school, src):
    """Another institution, when a people page belongs to a lab elsewhere: its host is another university's, or the page
    never names this school while its title or first 400 characters name another institution (Onur Mutlu's SAFARI pages
    at ETH, a lab that moved with its PI). Alumni placements and bios name other schools on every lab page, so a page that
    names this school anywhere is never another institution's. None otherwise."""
    try:
        row, views = kit.lpev.cap(school, src)
    except (KeyError, ValueError):
        return None
    host = urlsplit(unwayback(row.get('url') or '')).hostname or ''
    dom = SCHOOLS[school]['domain']
    if _HOST_INST.search(host) and not re.search(dom, host):
        return host
    text = views.get('html') or views.get('raw') or ''
    ft = re.search(r'(?:©|&copy;|\bcopyright\b)[^<>\n]{0,40}?\b((?:University of [A-Z][\w-]+(?: [A-Z][\w-]+)?)|(?:[A-Z][\w-]+ University))\b', text[-600:], re.I)
    if ft and not re.search(school_names_rx(school), ft.group(1)) and not re.search(school_names_rx(school), text[-600:]):
        return ft.group(1)   # a page whose own copyright footer names another university is that university's page (CMU round 7: Salakhutdinov's Toronto-era page)
    if re.search(school_names_rx(school), text):
        return None  # the school appears somewhere on the page: alumni placements and bios name other schools too
    m_ = re.search(r'<title[^>]*>(.*?)</title>', kit.lpcap.decode(row['content'][:30000]), re.I | re.S)
    head = ((m_.group(1) if m_ else '') + ' ' + text[:400])
    others = [m.group(0) for m in INST_RX.finditer(head)]
    return others[0] if others else None


def coadvisers(kit, school, src):
    """Names written after 'joint with' / 'co-advised with' on a page: co-advisers, not members."""
    try:
        t = kit.lpev.text(school, src)
    except (KeyError, ValueError):
        return []
    return list(dict.fromkeys(m.group(1) for m in COADV_RX.finditer(t)))


YEAR_ = r'(?:19[89]\d|20[0-2]\d)'


def entry_years_end_the_stay(years, basis, this_year=2026):
    """True when the years an entry states close the stay: a degree or end year with no start ([None, y], y <= this year), or a closed
    range that ended before this year. An open range ([a, None]) and a range ending this year stay current."""
    if basis != 'stated_in_entry' or not years or years[1] is None:
        return False
    return years[0] is None and years[1] <= this_year or years[0] is not None and years[1] < this_year


NON_US_CLASS_SCHOOLS = {'ntu', 'sjtu', 'tsinghua', 'zju', 'nus'}   # 'Class of 2024' cohort lines on these schools' lab pages belong to US-college affiliates (NTU round 4: Will Cong's lab)
ALUMNI_TABLE_ROW = re.compile(r'^\W{0,3}(?:NTU|[A-Z]{2,6})\s+(?:PhD|Ph\.D\.|Postdoc|RAP?)\s+(?:19|20)\d\d\b')   # 'NTU PhD 2026 Senior Researcher @ Apple': an alumni-table row
PLACEMENT_RX = re.compile(r'@|\bnow\b|\bWhere\s+now\b|(?:Ph\.?\s?D\.?|M\.?S\.?)\W{0,3}(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep)[a-z]*\.?\s+2026|\b(?:Senior|Research|Postdoc\w*|Assistant|Associate)\s+(?:Scientist|Researcher|Professor|Engineer|Fellow)\b|\bCo-?Founder\b|\bLecturer\b', re.I)   # 'NTU PhD 2026 Senior Researcher @ Apple': a placement after the year is an alumnus
AWARD_AFTER_YEAR = re.compile(r'(?:19|20)\d\d\s+(?:[\w&.-]+\s+){0,3}(?:scholarship|fellowship|award|prize|medal|honou?r|grant)', re.I)
AWARD_WORDS = re.compile(r'scholarship|fellowship|award|prize|medal|honou?r|grant|\\u5956\\u5b66\\u91d1|\\u5956', re.I)


CURRENT_LIST_HEAD = re.compile(r'\b(?:current|present|active)\b|\u73b0\u5728|\u5728\u8bfb|\u5728\u6821', re.I)
def m_has_range(d):
    return bool(re.search(r'(?:19|20)\d\d\s*(?:-|\u2013|\u2014|to|\u219d|\u2192)\s*(?:19|20|\d\d)', d[:60]))


OPEN_MONTH_RX = re.compile(r'(?<![\d./])((?:19|20)\d\d)\s*[./]\s*(?:0?[1-9]|1[0-2])(?:\s*[./]\s*(?:0?[1-9]|[12]\d|3[01]))?\s*(?:[-\u2013\u2014~\uff5e]\s*(?:\u81f3\u4eca|present|now|current)?|\u81f3\u4eca|to\s+(?:present|now))(?![\d./])', re.I)


def past_range_head(head):
    """A heading with a CLOSED year range that ended before this year ('Undergraduate. 2023-2024 FYP advisee'): its entries are a finished cohort, so a bare 'BS 2024' there is a graduation year (ZJU Kai Bu's alumni sub-lists)."""
    m = re.search(r'((?:19|20)\d\d)\s*[-\u2013\u2014]\s*((?:19|20)\d\d)', head or '')
    return bool(m) and int(m.group(2)) < 2026


def entry_years(desc, head):
    """(years, basis) stated by the entry itself; never a neighbour's dates or a bio's degree dates.
      '(Postdoc, 2010-2014)' -> [2010, 2014]; '(PhD student, MIT ORC, 2022 -)' -> [2022, None] (an open range is a start);
      '(Ph.D. in applied math 2014)' or 'PhD 2021' -> [None, 2014] (a degree year ends the stay); 'MIT Undergraduate Student, 2020'
      -> [2020, 2020]; a section heading that is only a year ('2019') -> that year, basis section_year_heading; else
      (None, 'none'): the build keeps undated students."""
    tm = re.match(r'^\s{0,3}\|?\s*[^|]{1,100}\|\s*((?:19|20)\d\d)\b', desc or '')
    if tm:  # '| Stanford Univ. Medical Center | 2004' (a 'Past Doctoral Students' table): the year ends the stay (Stanford round 3)
        return [None, int(tm.group(1))], 'stated_in_entry'
    dy = dissertation_entry_year(desc)
    if dy:
        return [None, dy], 'stated_in_entry'
    dm = re.search(r'\b[Dd]efended\b[^.\[]{0,50}?\b((?:19|20)\d\d)\b', (desc or '')[:220])
    if dm:  # 'Defended on the 6th of January, 2012.' ends the stay (Michigan round 1: Bayraktar's alumni list)
        return [None, int(dm.group(1))], 'stated_in_entry'
    d, nested_ = (desc or '')[:90], False
    if re.match(r'^\W{0,3}\([^()]{0,80}\([^()]{0,20}\)', d) and not re.search(r'\b(?:19|20)\d\d\b', re.match(r'^\W{0,3}\([^()]{0,80}\([^()]{0,20}\)', d).group(0)):
        d, nested_ = (desc or '')[:200], True   # '(MPhil student, HKUST (GZ) RBM, co-supervised with Prof. X, Fall 2022 - Summer 2024)': a nested bracket must not cut the dates off (HKUST Ma)
    mo = re.search(r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+((?:19|20)\d\d)\s*[~\uff5e\u2013\u2014-]\s*(?:present|now|current)?(?![\d\w])', d, re.I)
    if mo:   # 'Master Student, September 2022~': a stated open start (Tsinghua round 6, bcspl Members)
        return [int(mo.group(1)), None], 'stated_in_entry'
    dw_ = d[:150] if nested_ else d[:80]
    ss = re.search(r'\b(?:spring|summer|fall|autumn|winter)\s+((?:19|20)\d\d)\b(?!\s*[-\u2013\u2014~])', dw_, re.I)
    if ss and not re.search(r'\bsince\b', dw_, re.I) and len(re.findall(r'(?<!\d)(?:19|20)\d\d(?!\d)', dw_)) == 1:
        return [int(ss.group(1)), int(ss.group(1))], 'stated_in_entry'   # 'summer 2018' / 'Summer 2018 intern': a stay in that season
    sn = re.search(r'\bsince\s+(?:(?:spring|summer|fall|autumn|winter)\s+)?((?:19|20)\d\d)(?:\s+(?:spring|summer|fall|autumn|winter))?\b', d, re.I)
    if sn:   # 'Since 2022 Fall' / 'Since Fall 2022': an open start (SJTU dmcv roster)
        return [int(sn.group(1)), None], 'stated_in_entry'
    stm = re.search(r'\bstarted\s+(?:in\s+)?((?:19|20)\d\d)\b', d[:60], re.I)
    if stm and not re.search(r'\b(?:graduated|defended|finished)\b', d[:90], re.I):
        return [int(stm.group(1)), None], 'stated_in_entry'   # '(PhD, started in 2025)': a stated start, still current (HKUST Qiong Luo's DSA students were read as ended in 2025)
    om = OPEN_MONTH_RX.search(d)
    if om:   # 'PhD, 2024.9-' / '2024.9至今': an open-ended start with a month is a start year, still current (SJTU round, 马超's list)
        return [int(om.group(1)), None], 'stated_in_entry'
    m = re.match(r'^\W{0,3}\(([^()]{0,80})\)', d)
    if m and re.search(r'co-?advis|supervised', m.group(1), re.I):   # '(Co-Advised with Prof. X) (2020-, B.S. CS@ Y)': the dates sit in the next bracket (SJTU round 6)
        m2 = re.match(r'^\W{0,3}\([^()]{0,80}\)\s*\(([^()]{0,80})\)', d)
        m = m2 or m
    cl = re.match(r'^\s*(?:,\s*[A-Z][\w.\'\u2019 -]+){2,}\s*\(((?:19|20)\d\d)\)', (desc or '')[:260])
    if cl and not re.search(r'\b(?:alumni|former|graduated)\b', head or '', re.I):
        return [int(cl.group(1)), None], 'stated_in_entry'   # 'Jiafeng Xu, Peiyu Chen, ... Yunkai Zheng (2020)': a cohort list, its one year is the entry year of each (SJTU round 6)
    ab = re.match(r'^\W{0,3}(?:\([^()]{0,100}\)\s*)+((?:19|20)\d\d)(?![\d./-])', d)
    if ab and not m_has_range(d) and not re.search(r'\b(?:alumni|former|graduated)\b', head or '', re.I):
        return [int(ab.group(1)), None], 'stated_in_entry'   # '(2024 Zhongyuan Scholarship) 2022': the bare year after award brackets is the cohort / entry year (SJTU round 6)
    seg = m.group(1) if m else d[:150] if nested_ else re.split(r'(?<=[a-z0-9)])\.\s|\s(?:received|graduated from|is|was|joined|works?)\s', d, maxsplit=1)[0][:70]
    r = re.search(r'(%s)(?:\s*(?:spring|summer|fall|autumn|winter))?\s*(?:-|–|—|to|until|\u219d|\u21dd|\u2192|->)\s*(?:(?:spring|summer|fall|autumn|winter|[A-Z][a-z]{2,8}\.?)\s+)?(%s|\d\d(?!\d)|present|now|current|today)?'
                  % (YEAR_, YEAR_), seg, re.I)
    if r:
        a, b = int(r.group(1)), r.group(2)
        if b and re.fullmatch(r'\d\d', b):  # '(2017-18)', '(2020-22)'
            e_ = a // 100 * 100 + int(b)
            if e_ < a or e_ > a + 12 or int(b) in range(1, 13) and re.match(r'\s*[-\u2013]\s*\d\d[-\u2013:\s]\d', seg[seg.find(str(a)) + 4:] or ''):
                return None, 'none'  # '2020-05-24' is a date, not a stay
            return [a, e_], 'stated_in_entry'
        return [a, int(b) if b and b[:2] in ('19', '20') else None], 'stated_in_entry'
    ys = [int(y) for y in re.findall(r'(?<!\d)(%s)(?!\d)' % YEAR_, seg)]
    if len(ys) == 1 and head and re.search(r'\b(?:alumni|alumnae|alumnus|former|past|graduated|graduates)\b', head, re.I) and re.match(r'^\W{0,3}\(\s*(?:19|20)\d\d\s*\)', d):
        return [None, ys[0]], 'stated_in_entry'   # an alumni entry '(2020)' with no label: the one year is the graduation year, not a start (Tsinghua round 5: 徐明伟's Zhen Tang)
    if len(ys) == 1:
        if AWARD_AFTER_YEAR.search(seg) and not re.search(r"\bph\.?\s?d|\bdegree|\bgraduated|\bm\.?s\.?\b|\bb\.?s\.?\b|\bm\.?eng|\bthesis", seg, re.I):
            return None, 'none'   # '(2025 OPPO Scholarship)' dates an award, not the stay (SJTU round 1); a range above is unaffected
        if head and not re.search(r'\b(?:former|past|previous|alumni|alumnae|alumnus|graduated|graduates|class of|emeriti)\b', head, re.I) and not past_range_head(head) \
                and re.fullmatch(r"\W*(?:ph\.?\s?d\.?|m\.?s\.?|b\.?s\.?)(?:\s*[/&,]\s*(?:ph\.?\s?d\.?|m\.?s\.?|b\.?s\.?))*\W*(?:19|20)\d\d\W*", seg, re.I):
            return ([ys[0], ys[0]] if re.search(r'\bFYP\b|final[- ]year', f'{head} {desc}', re.I) else [ys[0], None]), 'stated_in_entry'   # (an FYP advisee of that year is [Y, Y]) '(Ph.D./M.S. 2023)' in a CURRENT list is the entry year, not an end year (SJTU round 5, 赵杰茹's page); real alumni there use YYYY-YYYY ranges
        if re.search(r"\bph\.?\s?d|\bdegree|\bgraduated|\bclass of|\bm\.?s\.?\b|\bb\.?s\.?\b|\bm\.?eng|\bthesis|\balum|\buntil|\bleft|'\d\d", seg, re.I):
            return [None, ys[0]], 'stated_in_entry'
        return [ys[0], ys[0]], 'stated_in_entry'
    fy = re.search(r'\b(?:FYP|final[- ]year\s+projects?)\b\D{0,8}((?:19|20)\d\d)', head or '', re.I)
    if fy:
        return [int(fy.group(1)), int(fy.group(1))], 'section_year_heading'   # 'FYP 2019' heading: a final-year-project advisee of that year
    if head and re.fullmatch(r'\W*(%s)\W*' % YEAR_, head.split(' > ')[-1].strip()):
        y = int(re.search(YEAR_, head.split(' > ')[-1]).group(0))
        return [y, y], 'section_year_heading'
    return None, 'none'


ROLE_NEAR = re.compile(r"^\W{0,3}[(,:–—-]?\s*(?:[\u4e00-\u9fff]+\s*)?(?:[A-Z][\w.&'-]*\s){0,2}?(?:visiting\s|joint\s|former\s|current\s|\d(?:st|nd|rd|th)[- ]year\s)?"
                       r"(ph\.?\s?d|post-?doc|postdoctoral|master|m\.?s\.?\b|m\.?eng|meng|undergrad|b\.?s\.?e?\b|ug\b|urop|superurop|"
                       r"graduate|grad\b|doctoral|student|candidate|research|visiting|lab manager|engineer|scientist|staff|intern)", re.I)


PRIOR_DEGREE_ANY = re.compile(r"(?:\b(?:accelerated\s+\d\+\d\s+)?(?:bachelor|master|undergraduate)['\u2019]?s?(?:\s+and\s+(?:bachelor|master)['\u2019]?s?)?\s+(?:from|at)\b)", re.I)
PRIOR_DEGREE = re.compile(r"^\W{0,3}\(?\s*(?:bachelor|master|undergraduate|b\.?\s?s\.?c?|m\.?\s?s\.?c?|mphil|b\.?eng|m\.?eng)['\u2019]?s?\s*(?:degree\s+)?(?:from|at)\b", re.I)


DISS_ENTRY_RX = re.compile(r'^\W{0,3}\(\s*((?:19[89]|20[0-2])\d)\s*,\s*(?![^)]*(?:post-?doc|visit|ph\.?\s?d))[^)]*(?:University|Univ\.|Stanford|UMass|Linguistics|Computer Science|Philosophy|Psychology|Department|Dept)[^)]*\)', re.I)


def dissertation_entry_year(desc):
    """Stanford round 7: '(2018, Stanford Linguistics; Cleo Condoravdi co-chair)' in a PI's list of advised dissertations is the student's degree
    year and department: a PhD whose stay ended that year, not a postdoc (Potts's list sat under a 'Postdocs' heading). None for any other entry."""
    m = DISS_ENTRY_RX.match(desc or '')
    return int(m.group(1)) if m else None


PRIOR_AT_RX = re.compile(r"\b(?:b\.?\s?s\.?c?|m\.?\s?s\.?c?|b\.?a\.?)\b[^.;()]{0,20}@[^.;()]{0,40}", re.I)   # '(2020-, B.S. CS@ Jilin University)': the degree held on arrival
PRIOR_FROM_RX = re.compile(r"\b(?:b\.?\s?s\.?c?|m\.?\s?s\.?c?|b\.?a\.?|b\.?eng|m\.?eng|m\.?phil|bachelor|master|undergraduate)['\u2019]?s?\s+(?:degree\s+)?from\b[^.;]{0,60}", re.I)


BIO_START_RX = re.compile(r'^\W{0,3}(?:received|obtained|earned|holds?|graduated|completed|got|has|had|is|was|will|joined|came|did|worked)\b', re.I)
NONPHD_HEAD_RX = re.compile(r'\b(?:research\s+associates?|research\s+assistants?|visiting\s+(?:students?|scholars?|researchers?)|interns?|research\s+staff|research\s+fellows?)\b', re.I)


def nearer_nonphd_heading(text, name, head):
    """True when a non-PhD heading ('Research Associates/ Research Assistants / Visiting Students') stands between the PhD heading the extractor assigned and the name on the page text: the
    extractor did not register it as a heading, so the names inherited the preceding PhD list (NTU round 6, Luu Anh Tuan's page; names may be written family-name first)."""
    if not (text and name and head):
        return False
    h = head.split(' > ')[-1]
    hp = text.find(h) if h else -1
    if hp < 0:
        return False
    toks_ = name.split()
    forms = [name, ' '.join(reversed(toks_))] if len(toks_) > 1 else [name]
    pos = [k for k in (text.find(f, hp + len(h)) for f in forms) if k >= 0]
    if not pos:
        return False
    if NONPHD_HEAD_RX.search(text[hp + len(h):min(pos)]):
        return True
    for m in NONPHD_HEAD_RX.finditer(text, hp + len(h)):   # also listed again right after a later non-PhD heading (the list is mixed: no role)
        if any(text.find(f, m.end(), m.end() + 700) >= 0 for f in forms):
            return True
    return False


ROLE_WORDS_FALLBACK = re.compile(r"\b(master|m\.?\s?s\.?|m\.?eng|mphil)['\u2019]?s?\b(?:\s+students?|\s*[\u00b7\u2022|,:-]\s*(?:y\d|year)|\s+candidates?)|\b(ph\.?\s?d\.?|doctoral)(?:\s+students?|\s+candidates?|\s*[\u00b7\u2022|,:-]\s*(?:y\d|year))|\bundergraduate\s+(?:students?|interns?|researchers?|assistants?)\b|\bmaster\s*[\u00b7\u2022]|\bph\.?\s?d\.?\s*[\u00b7\u2022]", re.I)


HAN_CARD_RX = re.compile(r"([\u4e00-\u9fff][\u4e00-\u9fff\u00b7]{1,3})\s*(\d{2})\u7ea7\s*(\u535a\u58eb\u7814\u7a76\u751f|\u7855\u58eb\u7814\u7a76\u751f|\u672c\u79d1\u751f|\u535a\u58eb\u540e|\u535a\u58eb\u751f|\u7855\u58eb\u751f|\u7814\u7a76\u751f)")
HAN_HEAD_RX = re.compile(r"(?<![\u4e00-\u9fff\u7ea7])(\u535a\u58eb\u540e|\u535a\u58eb\u751f|\u7855\u58eb\u751f|\u672c\u79d1\u751f|\u7814\u7a76\u52a9\u7406|\u6bd5\u4e1a\u751f|\u5df2\u6bd5\u4e1a|\u6821\u53cb|\u5f80\u5c4a)(?![\u4e00-\u9fff])")
HAN_ROLE = {'\u535a\u58eb\u7814\u7a76\u751f': 'phd', '\u535a\u58eb\u751f': 'phd', '\u7855\u58eb\u7814\u7a76\u751f': 'masters', '\u7855\u58eb\u751f': 'masters', '\u672c\u79d1\u751f': 'undergraduate', '\u535a\u58eb\u540e': 'postdoc', '\u7814\u7a76\u751f': None}


HAN_ITEM_KEYS = ('name', 'role', 'years', 'head', 'desc', 'quote', 'qkind', 'flags', 'alumni', 'held', 'held_kind', 'url', 'capture_url', 'sha256')   # the keys the toolkit's extract() rows carry


def han_item_dummy():
    return None


def han_card_item(c_, row_, names, held):
    """A Han member card in the shape of an extract() row (every reader of the candidates, audit_students included, needs url, sha256, qkind, held ...)."""
    h_, hk_ = names.match(c_['name'], list(held))
    return dict(name=c_['name'], head=c_['head'], desc=c_['desc'], quote=c_['quote'], qkind='name+role', flags=[], role=c_['role'], years=None,
                alumni=c_['alumni'], held=h_, held_kind=hk_, url=row_['url'], capture_url=row_.get('capture_url'), sha256=row_['sha256'], han_card=c_)


def apply_member_card(x, c, role_of):
    """Set a candidate from its own member-item card: role from the card's tag (else its category), years from its period, desc / head from
    the card, and a quote that is the card's own verbatim text (name, tag, adviser, period) when the page text holds it."""
    tag_desc = ' '.join(t for t in (c['tag'], c['advisor'], c['period']) if t)
    x['desc'], x['head'], x['template'] = tag_desc, c['head'], 'member-item'
    role, basis = entry_role(c['tag'], c['head'], role_of)
    if role:
        x['role'], x['role_basis'] = role, basis
    if c['years']:
        x['years'], x['years_basis'] = c['years'], 'stated_in_entry'
    for q in (' '.join((c['name'], tag_desc)), ' '.join((c['name'], c['tag'], c['period'])), ' '.join((c['name'], c['tag']))):
        q = re.sub(r'\s+', ' ', q).strip()
        if q in c['ptxt']:
            x['quote'], x['qkind'] = q, 'name+role'
            break


MEMBER_ITEM_RX = re.compile(r'<li\b[^>]*class="[^"]*\bmember-item\b[^"]*"[^>]*>(.*?)</li>', re.S | re.I)
MEMBER_PERIOD_RX = re.compile(r'^((?:19|20)\d\d)\s*[-\u2013\u2014]\s*(now|present|current|(?:19|20)\d\d)?$', re.I)


def member_item_cards(h):
    """Cards of a page whose roster is <li class="member-item"> blocks (name span, role tag, '(w/ Prof. X)' adviser line, period span) under
    <div class="member-category"> headings (Tsinghua 刘保君's members.html). Read from the DOM so that one card's role / adviser / period text is never
    taken for the next name's heading or quote. -> [dict(name, tag, advisor, period, years, head)] ; years from 'YYYY - now' / 'YYYY - YYYY'."""
    import html as _html

    def clean(x):
        return re.sub(r'\s+', ' ', _html.unescape(re.sub(r'<[^>]+>', ' ', x or ''))).strip()

    def part(body, c):
        m = re.search(r'class="[^"]*\b%s\b[^"]*"[^>]*>(.*?)</(?:span|div)>' % c, body, re.S | re.I)
        return clean(m.group(1)) if m else ''
    cards = []
    cats = [(m.start(), clean(m.group(1))) for m in re.finditer(r'<div\b[^>]*class="[^"]*\bmember-category\b[^"]*"[^>]*>(.*?)</div>', h or '', re.S | re.I)]
    for m in MEMBER_ITEM_RX.finditer(h or ''):
        body = m.group(1)
        name, tag, adv, per = part(body, 'member-name'), part(body, 'member-role-tag'), part(body, 'member-advisor'), part(body, 'member-period')
        if not name:
            continue
        head = next((c for pos, c in reversed(cats) if pos < m.start()), None)
        pm = MEMBER_PERIOD_RX.match(per or '')
        years = None
        if pm:
            end = pm.group(2)
            years = [int(pm.group(1)), None if not end or end.lower() in ('now', 'present', 'current') else int(end)]
        cards.append(dict(name=name, tag=tag, advisor=adv, period=per, years=years, head=head))
    return cards


ROLE_TEXT_HEAD_RX = re.compile(
    r"(?<![\w'])(ph\.?\s?d\.?|doctoral|master(?:'s)?|m\.?s\.?|undergraduate|bachelor)\s+students?\b"
    r"|(\u535a\u58eb\u751f|\u7855\u58eb\u751f|\u672c\u79d1\u751f)"
    r"|(?<![\w'.-])(?P<bare>(?-i:Masters?|M\.S\.|MS|Ph\.?D|Undergraduates?))(?=(?-i:\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}(?:\s|$)))(?!\s+(?:Thesis|Degree|Program|Student|Students|Research|Project|Candidate))",
    re.I)
ROLE_TEXT_STOP_RX = re.compile(r"\b(?:alumni|alumnae|former|past|graduated|faculty|professors?|staff|postdocs?|post-?doctoral|researchers?|visitors?)\b|\u5df2\u6bd5\u4e1a|\u6bd5\u4e1a\u751f|\u6821\u53cb|\u6559\u5e08|\u6559\u6388", re.I)


def role_from_preceding_heading(pre):
    """The role of the nearest role heading ('Ph.D Student', 'Master Student', \u535a\u58eb\u751f, \u7855\u58eb\u751f) in the page text before a roster name, unless an alumni / faculty / staff heading comes after it (SJTU dmcv roster)."""
    ms = list(ROLE_TEXT_HEAD_RX.finditer(pre or ''))
    if not ms:
        return None
    m = ms[-1]
    if ROLE_TEXT_STOP_RX.search(pre[m.end():]):
        return None
    k = (m.group(1) or m.group(2) or m.group('bare') or '').lower()
    return 'phd' if k.startswith(('ph', 'doctor', '\u535a')) else 'masters' if k.startswith(('master', 'm', '\u7855')) else 'undergraduate'


def han_member_cards(text, school_rx=r'\u4e0a\u6d77\u4ea4\u901a\u5927\u5b66|\u4ea4\u5927|\u6e05\u534e|\u6d59\u6c5f\u5927\u5b66|\u6d59\u5927'):
    """Member cards of a Chinese lab page: 'NAME NN\u7ea7\u535a\u58eb\u7814\u7a76\u751f (\u4e0e\u67d0\u6559\u6388\u8054\u5408\u57f9\u517b) bio ...' under \u535a\u58eb\u751f / \u7855\u58eb\u751f / \u7814\u7a76\u52a9\u7406 / \u5df2\u6bd5\u4e1a headings (SJTU ScaleLab people.html; the same form on Tsinghua / ZJU /
    SJTU pages). -> [dict(name, role, start year 20NN, alumni, head, quote, desc, member)]: the role is the label's (\u535a\u58eb->phd, \u7855\u58eb->masters, \u672c\u79d1->undergraduate, \u535a\u58eb\u540e->postdoc), the year is NN\u7ea7 (20NN), a \u6bd5\u4e1a / \u5df2\u6bd5\u4e1a / \u6821\u53cb heading marks alumni. A card
    that never names the school in its own text (research assistants of other universities, \u8054\u5408\u57f9\u517b with another institute) is member=False: the page must tie it to the school."""
    heads = [(m.start(), m.group(1)) for m in HAN_HEAD_RX.finditer(text or '')]
    cards = list(HAN_CARD_RX.finditer(text or ''))
    out = []
    for k, m in enumerate(cards):
        end = cards[k + 1].start() if k + 1 < len(cards) else m.end() + 240
        body = text[m.end():min(end, m.end() + 240)]
        hs = [h for pos, h in heads if pos < m.start()]
        head = hs[-1] if hs else ''
        alumni = head in ('\u6bd5\u4e1a\u751f', '\u5df2\u6bd5\u4e1a', '\u6821\u53cb', '\u5f80\u5c4a') or '\u5df2\u6bd5\u4e1a' in body[:12]
        ra = head == '\u7814\u7a76\u52a9\u7406'
        role = HAN_ROLE[m.group(3)] or None
        ties = bool(re.search(school_rx, m.group(0) + body))
        joint = '\u8054\u5408\u57f9\u517b' in (m.group(0) + body[:40])
        other_inst = bool(re.search(r'(?:\u9999\u6e2f|\u5317\u4eac|\u590d\u65e6|\u6d59\u6c5f|\u5357\u4eac|\u4e2d\u79d1\u9662|\u5c0f\u9e4f|\u6df1\u5733|\u4e0a\u6d77\u4eba\u5de5\u667a\u80fd\u5b9e\u9a8c\u5ba4)[^\uff0c\u3002]{0,8}(?:\u5927\u5b66|\u5b9e\u9a8c\u5ba4|\u7814\u7a76\u9662)', body[:80]))
        member = ties and not (ra and other_inst) and not (joint and other_inst)
        out.append(dict(name=m.group(1), role=role, year=2000 + int(m.group(2)), alumni=alumni, head=head, member=member,
                        quote=(head + ' ' + m.group(0)).strip(), desc=body[:100].strip(), ra=ra))
    return out


PERSON_HEAD_RX = re.compile(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}")


def role_fallback(text):
    """'Master Students', 'Ph.D Students', 'Master \u00b7 Y2', 'PhD \u00b7 Y3' state the role though the toolkit's reader does not know them (Tsinghua round 1: the page states it, the tool left None)."""
    m = ROLE_WORDS_FALLBACK.search((text or '')[:60])
    if not m:
        return None
    return 'masters' if m.group(1) or re.search(r'^\W*master', m.group(0), re.I) else 'phd' if m.group(2) or re.search(r'ph\.?\s?d', m.group(0), re.I) else 'undergraduate'


ENTRY_AS_HEAD_RX = re.compile(r"^[A-Z][\w'.-]+(?:\s+[A-Z][\w'.-]+){1,2}\s+(?:Ph\.?\s?D\.?|M\.?\s?S\.?|B\.?\s?S\.?|M\.?Eng)\b")   # 'Weiya Xu Ph.D., NUS' as a heading: the previous alumnus entry the extractor turned into one (ZJU \u7eaa\u5b88\u9886's NESA page)


def entry_role(desc, head, role_of):
    """(role, basis): the role the entry states right after the name ('(PhD student, ...)', ', Postdoc', 'MIT Undergraduate
    Student'), else the role its section heading names ('PhD Students', 'Post-doctoral Scholars'), else (None, 'none').
    A role word further into a bio ('received his B.S. ...', 'Ph.D. in Electrical Engineering from ...') never counts."""
    vis = VIS.visiting_role(desc, head, role_of)
    if vis:
        return vis   # R-STU-17: 'visiting student from CUHK', '(visiting, CUHK)', a 'Visiting Students' heading: a member of this lab, role `visiting`
    if re.search(r'^\W{0,3}(?:visiting\s+intern|visiting\s+student\s+intern|visitors?(?!\s+(?:professor|scientist|faculty|researcher))\b)', (desc or '')[:60], re.I):
        return 'visiting', 'entry'   # R-STU-17: a visiting intern / visitor / visiting student is a lab member with role visiting (HKUST re-audit)
    if dissertation_entry_year(desc):
        return 'phd', 'entry'
    d = (desc or '')[:60]
    am = re.match(r'^\W{0,3}[A-Z][A-Za-z]{1,10}\s+(Ph\.?\s?D\.?|Postdoc)\s+(?:19|20)\d\d\b', d)
    if am:
        return ('phd' if am.group(1).lower().startswith('ph') else 'postdoc'), 'entry'   # 'NTU PhD 2025 Postdoc @ Oxford': the stated degree is the role here, the post after it a placement (NTU round 1)
    dm = re.match(r'^\W{0,3}(?:Ph\.?\s?D\.?|M\.?S\.?|B\.?S\.?)\s*[,(]?\s*(?:19|20)\d\d\b', d)
    if dm and re.search(r'ph\.?\s?d', dm.group(0), re.I):
        return 'phd', 'entry'   # 'Ph.D. 2025, Post Doc @ Univ. of Illinois': the degree is the role, the post after it is the placement (UChicago round 2)
    if re.match(r'^\W{0,3}(?:(?:MPCS|MCAM|MSCAPP|MSc?|M\.S\.)\b|[^,]{1,25},\s*(?:MS|M\.S\.|MSc)\b)', d):
        return 'masters', 'entry'   # 'Noame Qin — MCAM, MS 2022' under an 'undergraduate & master's' heading: the entry's own degree is the role
    if re.search(r'\bFYP\s+advisee\b|\bSRTP\s+advisee\b|final[- ]year\s+project', d[:90], re.I) and not re.match(r'^\W{0,3}(?:ph\.?\s?d|master|m\.?s\b)', d, re.I):
        return 'undergraduate', 'entry'   # 'BS 2024. FYP advisee': a final-year-project advisee is an undergraduate (ZJU Kai Bu)
    if BIO_START_RX.match(d):
        pass   # 'received her B.S. in ...': a bio sentence never sets the role (the case-insensitive ROLE_NEAR read 'received her' as two capitalised words) (NTU round 6, Rui Jiao)
    elif PRIOR_DEGREE.match(d):
        pass   # 'Bachelor's from X, Hong Kong PhD Fellowship': the degree the person holds on arrival, not their role here (HKUST hand check 2026-11-10: 4 of 11 roles wrong); the section heading decides
    elif ROLE_NEAR.match(d):
        r = role_of(PRIOR_AT_RX.sub(' ', PRIOR_FROM_RX.sub(' ', PRIOR_DEGREE_ANY.sub(' ', d)))[:45])[0]   # 'Ph.D student, 2022/9/1 to present; B.S. from X': the degree after 'from' is prior education, never the role (HKUST Ling Shi roster)
        if not r:   # the reader's vocabulary lacks 'Master Student' / 'PhD Student' after a Chinese given name (SJTU round 6, Jia Xiang)
            fm = re.search(r"\b(master|m\.?s\.?|m\.?eng)['\u2019]?s?\s+students?\b|\b(ph\.?\s?d\.?|doctoral)\s+(?:student|candidate)\b|\bundergraduate\s+students?\b", PRIOR_AT_RX.sub(' ', PRIOR_FROM_RX.sub(' ', d))[:60], re.I)
            if fm:
                r = 'masters' if fm.group(1) else 'phd' if fm.group(2) else 'undergraduate'
        if r and r != 'member':
            return r, 'entry'
    fr = role_fallback(d) if re.match(r'^\W{0,3}(?:master|ph\.?\s?d)\b', d, re.I) else None
    if fr:
        return fr, 'entry'   # 'Master \u00b7 Y2', 'Ph.D. \u00b7 Y5 w/ Prof. X' right after the name
    h = (head or '').split(' > ')[-1]
    if ENTRY_AS_HEAD_RX.match(h):
        return None, 'none'
    r = role_of(h)[0] if h and not PERSON_HEAD_RX.fullmatch(h.strip()) else None   # a heading that is a person's name ('Zili Meng') is not a role ('Meng' read as M.Eng) (Tsinghua round 1: Zhen Tang)
    if not r and head and ' > ' in head:
        r = role_of(head.split(' > ')[0])[0] if not PERSON_HEAD_RX.fullmatch(head.split(' > ')[0].strip()) else None
    if not r:
        r = role_fallback(h) or (role_fallback(head.split(' > ')[0]) if head and ' > ' in head else None)
    if r and r != 'member' and h and re.search(r'post-?doc\w*', h, re.I) and re.search(r'ph\.?\s?d|doctoral\s+student|graduate\s+student', h, re.I):
        return None, 'none'   # a heading that mixes postdocs and PhD students states no role for its rows (NTU round 6: 'Current Post-doctorates and PhD students')
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


CURRENT_HEAD = re.compile(r'\b(current|present)\b|\u5728\u8bfb|\u73b0\u6709\u6210\u5458|\u73b0\u5f79|\u5728\u7ad9|\u5728\u6821', re.I)
CURRENT_ENTRY = re.compile(r'\b(current(ly)?\s+(a\s+)?(ph\.?\s?d|student|postdoc|member|graduate)|\d(st|nd|rd|th)[- ]year|candidate|'
                           r'is a (ph\.?\s?d|graduate|doctoral|master|post-?doc)|expected\s+(?:graduation\s+)?(?:19|20)\d\d|'
                           r'class of 20(?:2[6-9]|3\d))', re.I)


def current_marker(x):
    """An explicit current marker in the entry's own text or its own section heading (not a parent heading)."""
    own_head = (x.get('head') or '').split(' > ')[-1]
    mixed = re.search(r'\b(former|past|previous|alumni|alumnae|graduated)\b', own_head, re.I)  # 'Current and Former Students'
    label = re.match(r'\s*(?:current|present)\s*:\s*(?!\W*(?:\w+\s+){0,2}(?:students?|members?|phd|ph\.d|postdocs?|people|team|group|researchers?|fellows?|undergrad\w*|interns?)\b)\S', own_head, re.I)   # 'Current: J.D. Harvard Law School' is an alumnus's job, not a current-members heading (CMU round 6, Tai-Sing Lee)
    return bool((CURRENT_HEAD.search(own_head) and not mixed and not label) or CURRENT_ENTRY.search((x.get('desc') or '')[:160]) or current_page_url(x))


CURRENT_URL = re.compile(r'/(?:current[-_](?:students?|members?|team|people|group)|(?:students?|members?|people)/current)(?:/|\.html?)?$', re.I)


def current_page_url(x):
    """R-LAB-04 (Georgia Tech round 2, ICSRL): a page whose own address says current students ('.../current-students/') marks its undated entries as current at the capture: the
    page lists bios under one heading, so no entry or heading carries the word."""
    u = re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', x.get('capture_url') or x.get('url') or x.get('src') or '')
    return bool(CURRENT_URL.search(u.split('?')[0].split('#')[0]))



NONPERSON_NAME = re.compile(r'\b(?:distinguished|invited|keynote)\s+(?:talk|lecture)\b|'
                            r'^[A-Z0-9-]{2,}\s+(?:[Aa]rchitecture|[Rr]untime|[Pp]latform|[Ss]ystem)$|'
                            r"^[A-Za-z]+['\u2019]s\s+[A-Z]")   # a possessive title fragment ("Clifford's Geometric Algebra", Stanford round 7)
NONMEMBER_SECTION = re.compile(r'\bstudent\s+(?:reports?|projects?)\b|\bprospective\b|\bjoin\s+(?:the|our)\s+team\b|'
                              r'\b(?:postdoc|postdoctoral|phd|student)\s+positions?\b|scholar profile|citation data', re.I)


def nonmember_candidate(name, heading):
    """Reject obvious non-person titles and recruiting/report sections before admission."""
    if NONPERSON_NAME.search(name or ''):
        return 'name_unresolved', 'a talk or technical noun phrase, not a full person name'
    if NONMEMBER_SECTION.search(heading or ''):
        return 'not_in_people_section', 'a report, recruiting or citation section, not a member roster'
    h_ = (heading or '').split(' > ')[-1]
    if re.match(r'^\s*(?:Ph\.?\s?D|M\.?\s?S|B\.?\s?S|B\.?\s?E|Bachelor|Master)\b[^|]{0,80},\s*(?:19|20)\d\d\s*$', h_, re.I) and not re.search(r'\b(?:students?|alumni|members?|team|people|group)\b', h_, re.I):
        return 'not_in_people_section', 'an education line of a CV (a degree, field and year), not a member roster: the names under it are publication authors'   # Tsinghua round 2, madsys \u7ae0\u660e\u661f's page
    h_ = (heading or '').split(' > ')[-1]
    if re.search(r'\b(?:award|medal|prize|honou?rs?|recipient|scholarship|fellowship|thesis award)\b', h_, re.I) and not re.search(r'\b(?:students?|members?|people|team|alumni)\b', h_, re.I):
        return 'not_in_people_section', 'an award / honour heading (a sentence about a recipient), not a member roster'   # NTU round 6: Zhaoxi Chen under 'NTU PhD Medal of Honour'
    return None

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
    text_cache, html_cache = {}, {}
    auto_plan = bool(plan.get('strict')) or plan.get('notes', '').startswith('lab-page audit discovery')
    homepage_people = bool(plan.get('homepage_people'))
    coadv, inst_ = {}, {}
    for src, is_cap in srcs:
        spans = plan.get('span', {})
        orig = None
        if is_cap:
            m_ = kit.lpcap.WAYBACK_RX.match(src)
            orig = m_.group(2) if m_ else None
        sp = spans.get(src) or (spans.get(orig) or spans.get(orig.replace('http://', 'https://')) or spans.get('*')
                                if is_cap and orig else None)
        if re.search(r'\.pdf(?:$|[?#])', re.sub(r'^https?://web\.archive\.org/web/\d+(?:id_)?/', '', src), re.I):
            continue   # a PDF (a thesis linked from an alumni page) is not a people page; parsed as HTML a 13 MB one held the CMU audit for over an hour (Bigham)
        try:
            ext = kit.autom.extract(school, src, pi, held, span=sp)
        except (ValueError, KeyError) as e:
            if not is_cap:
                unreadable.append((src, str(e)[:200]))
            continue
        try:
            row_, _v = kit.lpev.cap(school, src)
            ptxt_ = kit.lpev.text(school, src)
            hc_ = han_member_cards(ptxt_, school_names_rx(school) + r'|\u4ea4\u5927') if re.search(r'\d{2}\u7ea7', ptxt_ or '') else []
        except (KeyError, ValueError):
            hc_, row_ = [], None
        mcards_ = {}
        try:   # a roster of <li class="member-item"> cards: each card's own tag / adviser / period (DOM), never the neighbour's
            row_h, _v2 = kit.lpev.cap(school, src)
            ch_ = row_h['content']
            try:
                ch_ = zlib.decompress(ch_)
            except Exception:  # noqa: BLE001 - stored uncompressed
                pass
            h_ = ch_.decode('utf-8', 'ignore') if 'member-item' in ch_[:2000000].decode('utf-8', 'ignore') else ''
            if h_:
                ptxt_m = re.sub(r'\s+', ' ', kit.lpev.text(school, src) or '')
                for c_ in member_item_cards(h_):
                    mcards_[names.fold(c_['name'])] = dict(c_, ptxt=ptxt_m)
        except (KeyError, ValueError, TypeError):
            mcards_ = {}
        have_ = {names.fold(e['name']) for e in ext}
        ext = list(ext)
        for c_ in hc_:
            if names.fold(c_['name']) in have_:
                continue
            if not row_:
                continue
            ext.append(han_card_item(c_, row_, names, held))
        for x in ext:
            fn = names.fold(x['name'])
            x['is_cap'] = is_cap
            x['src'] = src
            apply_template_reader(kit, school, src, x, html_cache)
            x['alumni'] = bool(x.get('alumni') or (x['head'] and kit.autom.ALUMNI_RX.search(x['head']))
                               or src in plan.get('alumni_pages', ()) or (orig is not None and any(
                                   orig.replace('http://', 'https://').rstrip('/') == unwayback(a).replace('http://', 'https://').rstrip('/')
                                   for a in plan.get('alumni_pages', ()))))
            if not x['alumni'] and ENTRY_AS_HEAD_RX.match((x.get('head') or '').split(' > ')[-1]):
                try:
                    if src not in text_cache:
                        text_cache[src] = kit.lpev.text(school, src)
                    has_alum_ = bool(re.search(r'\b(?:alumni|alumnae|graduated|former)\b', text_cache[src] or '', re.I))
                except (KeyError, ValueError):
                    has_alum_ = False
            else:
                has_alum_ = False
            if has_alum_:
                x['alumni'] = True   # a list whose entries read 'Name Ph.D., University' on a page with an Alumni section: the entries are alumni, their degree is the destination
            if not x['alumni'] and caps_heading_is_past(kit, school, src, x['name'], text_cache):
                x['alumni'] = True  # an all-caps 'PAST ...' / 'FORMER ...' heading the extractor's section did not follow
            x['under_people_heading'] = bool(x['head'] and kit.autom.HEADWORD.search(x['head']))
            if x.get('han_card'):
                x['under_people_heading'] = True   # \u535a\u58eb\u751f / \u7855\u58eb\u751f / \u672c\u79d1\u751f headings are people headings the Latin HEADWORD does not know
            x['single_token'] = len(names.parse(x['name'])['tokens']) < 2
            if fn in yrs:
                x['years'], x['years_basis'] = yrs[fn], 'reviewer'
            else:
                x['years'], x['years_basis'] = entry_years(x.get('desc'), x.get('head'))
                if ALUMNI_TABLE_ROW.match(x.get('desc') or ''):
                    x['alumni'] = True
                if entry_years_end_the_stay(x['years'], x['years_basis']) and not (x['years'] == [None, 2026] and not PLACEMENT_RX.search((x.get('desc') or '')[:260])):
                    # a degree year equal to this year in a current-student list is an expected graduation, not an end (SJTU rounds 2-3); a placement after it ('NTU PhD 2026 Senior Researcher @ Apple') is an alumnus
                    x['alumni'] = True  # '(PhD 2024, co-advised with ...)' on a current page: the entry itself says the stay ended (UChicago stage 6, round 1)
            x['role'], x['role_basis'] = entry_role(x.get('desc'), x.get('head'), kit.autom._role)
            lr_ = label_role(x.get('desc'), x.get('head'))
            if not lr_ and re.match(r'^\W{0,3}Current position:', x.get('desc') or '') and x.get('name'):
                try:   # the extractor cut the card's descriptor before the stay's own role line: read the page text after the name
                    if src not in text_cache:
                        text_cache[src] = kit.lpev.text(school, src)
                    qk_ = text_cache[src].find(x['name'])
                    lr_ = label_role(text_cache[src][qk_ + len(x['name']):qk_ + len(x['name']) + 400].strip(), x.get('head')) if qk_ >= 0 else None
                except (KeyError, ValueError):
                    pass
            if lr_ and not x.get('han_card'):
                x['role'], x['role_basis'] = lr_, 'entry'
            if x.get('name') and not (x.get('quote') or '').startswith(x['name']):
                try:
                    if src not in text_cache:
                        text_cache[src] = kit.lpev.text(school, src)
                    localize_quote(x, text_cache[src])
                except (KeyError, ValueError):
                    pass
            if x.get('han_card'):   # a Han member card states role (label), entry year (NN\u7ea7) and alumni (heading) itself
                hc = x['han_card']
                x['role'], x['role_basis'] = (hc['role'], 'entry') if hc['role'] else (None, 'none')
                x['years'], x['years_basis'] = ([hc['year'], None] if not hc['alumni'] else [hc['year'], None]), 'stated_in_entry'
                x['alumni'] = hc['alumni']
                x['single_token'] = False
            mc_ = mcards_.get(fn)
            if mc_:
                apply_member_card(x, mc_, kit.autom._role)
            if (x['role'] in (None, 'member') or (x.get('role_basis') == 'section_heading' and re.search(r'[\u00b7\u2022]\s*Y\d+\s*$', x.get('head') or ''))) and x.get('name') and not x['alumni']:   # (a chip-order card: the previous card's 'Ph.D. \u00b7 Y2' became the heading, the name's own label follows it) the label may follow the name on the page while the card's desc is empty ('ZL Zhuo Li Master \u00b7 Y3 ...'): Tsinghua round 1
                try:
                    if src not in text_cache:
                        text_cache[src] = kit.lpev.text(school, src)
                    pt_ = text_cache[src]
                    qj = pt_.find(x['name'])
                    tail_ = pt_[qj + len(x['name']):qj + len(x['name']) + 40].strip() if qj >= 0 else ''
                    fr_ = role_fallback(tail_) if re.match(r'^\W{0,3}(?:master|ph\.?\s?d)\b', tail_, re.I) else None
                    if fr_:
                        x['role'], x['role_basis'] = fr_, 'entry'
                except (KeyError, ValueError):
                    pass
            if not x['years'] and x.get('name') and not x['alumni']:   # 'Ke Fan \u6a0a\u73c2 Since 2022 Fall': the entry's own 'Since YYYY' follows the name on the page while the card's desc is empty (SJTU dmcv roster)
                try:
                    if src not in text_cache:
                        text_cache[src] = kit.lpev.text(school, src)
                    pt2_ = text_cache[src]
                    qj2 = pt2_.find(x['name'])
                    tl2 = pt2_[qj2 + len(x['name']):qj2 + len(x['name']) + 50] if qj2 >= 0 else ''
                    sn2 = re.match(r'^\s*(?:[\u4e00-\u9fff\u00b7]{2,4}\s*)?since\s+(?:(?:spring|summer|fall|autumn|winter)\s+)?((?:19|20)\d\d)\b', tl2, re.I)
                    if sn2:
                        x['years'], x['years_basis'] = [int(sn2.group(1)), None], 'stated_in_entry'
                except (KeyError, ValueError):
                    pass
            if x.get('role_basis') == 'section_heading' and x.get('name') and not x['alumni'] and x['role'] in ('phd', 'masters', 'undergraduate'):
                try:   # a bare role heading right before the first name of its list ('Master Haoran Wang 王浩然 Since 2024 Fall') outranks the chain's earlier heading (SJTU dmcv)
                    if src not in text_cache:
                        text_cache[src] = kit.lpev.text(school, src)
                    pt4_ = text_cache[src]
                    qj4 = pt4_.find(x['name'])
                    rh4_ = role_from_preceding_heading(pt4_[max(0, qj4 - 14):qj4 + len(x['name'])]) if qj4 > 0 else None
                    if rh4_ and rh4_ != x['role']:
                        x['role'] = rh4_
                except (KeyError, ValueError):
                    pass
            if x['role'] in (None, 'member') and x.get('name') and not x['alumni']:   # the role heading sits in the page text before the roster while the extractor's heading chain lost it ('Ph.D Student roster updated: ... Ke Fan'): SJTU dmcv
                try:
                    if src not in text_cache:
                        text_cache[src] = kit.lpev.text(school, src)
                    pt3_ = text_cache[src]
                    qj3 = pt3_.find(x['name'])
                    if qj3 > 0:
                        rh_ = role_from_preceding_heading(pt3_[max(0, qj3 - 2500):qj3 + len(x['name'])])   # the name itself closes the window: a bare 'Master' heading directly before the first name of its list reads (SJTU dmcv Haoran Wang)
                        if rh_:
                            x['role'], x['role_basis'] = rh_, 'section_heading'
                except (KeyError, ValueError):
                    pass
            if fn in roles_:
                x['role'], x['role_basis'] = roles_[fn], 'reviewer'
            if SD.visiting(ctx_decisions(school), pi, x['name']):
                x['role'], x['role_basis'] = 'visiting', 'reviewer'   # decided `visiting` for this lab (student-decisions.json, R-STU-17)
            if src not in coadv:
                coadv[src] = coadvisers(kit, school, src)
                inst_[src] = page_institution(kit, school, src)
            flagged = [f for f in x['flags'] if f != 'weak-quote']
            why = None
            if inst_.get(src):
                why, x['detail'] = 'site_at_other_institution', f"the page's header names {inst_[src]}, not this school"
            elif CREDIT_RX.search(x.get('quote') or '') or CREDIT_RX.search((x.get('desc') or '')[:60]):
                why, x['detail'] = 'name_unresolved', 'site credit or footer'
            elif fn not in keep and any(names.match_one(x['name'], pn_) for pn_ in plan.get('pi_names') or ()):
                why, x['detail'] = 'not_a_student', 'the PI himself or herself is never a row of the lab'
            elif x.get('han_card') and not x['han_card']['member']:
                why, x['detail'] = 'not_a_student', 'a card that never names this school (a research assistant of another university, or a joint entry with another institute): the page must tie it to the school'
            elif fn not in keep and incoming_entry(x.get('desc'), x.get('quote')):
                why, x['detail'] = 'not_a_student', 'an incoming / admitted-for-a-future-year entry is not a member yet'
            elif fn not in keep and joint_other_institute_entry(x.get('desc'), x.get('quote'), school):
                why, x['detail'] = 'not_a_student', 'a joint / co-supervised entry with another institute: not placed in this lab unless the page ties it to the PI'
            elif fn not in keep and admin_staff_entry(x.get('head'), x.get('desc'), x.get('quote')):
                why, x['detail'] = 'not_a_student', 'administrative staff (a contact-block or staff entry), not a lab member'
            elif fn not in keep and (pn := prose_nonmember(x['name'], x.get('desc'), x.get('quote'))):
                why, x['detail'] = 'not_a_student', pn
            elif fn not in keep and (sy := page_stale_footer(kit, school, src, text_cache)):
                why, x['detail'] = 'undated_cannot_place', f"the page's footer is dated {sy} (before 2016): an old page, its current list is pre-window"
            elif auto_plan and fn not in keep and (nonmember := nonmember_candidate(x.get('name'), x.get('head'))):
                why, x['detail'] = nonmember
            elif any(names.match_one(x['name'], c) for c in coadv[src]):
                why, x['detail'] = 'not_a_student', 'named as a co-adviser (joint with / co-advised with)'
            elif auto_plan and not x['alumni'] and x['role'] != 'visiting' and (m_el := (ELSEWHERE_RX.search((x.get('desc') or '')[:220]) or DEGREE_AT_RX.search((x.get('desc') or '')[:120]))) and \
                    not re.search(school_names_rx(school), m_el.group(1)):
                why, x['detail'] = 'at_previous_school', f"the entry places the person at {m_el.group(1)}"
            elif re.search(r'\brotation', (x.get('head') or '') + ' ' + (x.get('desc') or '')[:60], re.I):
                why, x['detail'] = 'not_a_student', 'rotation student'
            elif re.search(r'\bfaculty\b|vice[- ]chancellor|\bdean\b|professors?\b', x.get('head') or '', re.I) and \
                    not ALUMNI_RX.search(x.get('head') or '') and \
                    not re.match(r'^\W{0,3}(?:ph\.?\s?d|m\.?\s?sc?\b|master|bachelor|undergrad|visitor|intern|postdoc|research\s+(?:assistant|associate|engineer))', x.get('desc') or '', re.I):   # a member whose own entry states a student role under the PI's title heading ('ZJU100 Young Professor') is a member (ZJU \u9648\u660e\u5e05)
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
            elif auto_plan and not x.get('han_card') and not (homepage_people and re.match(r'^\W{0,3}(?:ph\.?\s?d|m\.?\s?sc?\b|master|bachelor|undergrad|visitor|intern|postdoc|research\s+(?:assistant|associate|engineer))', x.get('desc') or '', re.I) and not NOT_MEMBER_HEAD.search(x.get('head') or '')) and (not (HOMEPAGE_HEAD if homepage_people else STRICT_HEAD).search(x.get('head') or '') or
                                NOT_MEMBER_HEAD.search(x.get('head') or '')):
                why, x['detail'] = 'not_in_people_section', f"section '{(x.get('head') or '')[:60]}' is not a member list"
            elif auto_plan and not x.get('han_card') and (not plausible(kit, x['name']) or re.match(r'^[A-Z]\.\s', x['name']) or
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
    # the same person listed twice on a page (SJTU round 6/7): an incoming entry anywhere makes every entry of that person not a member yet; a person who is a current
    # graduate student in one list is not also an alumnus-undergraduate of the same page (Haolan Zhang under 'Undergraduate Students')
    for x in cands:
        if x['role'] == 'phd' and x.get('role_basis') == 'section_heading' and not x['why']:
            try:
                if x['src'] not in text_cache:
                    text_cache[x['src']] = kit.lpev.text(school, x['src'])
                if nearer_nonphd_heading(text_cache[x['src']], x['name'], x.get('head')):
                    x['role'], x['role_basis'] = None, 'withheld_heading_conflict'
            except (KeyError, ValueError):
                pass
    inc_names = [x['name'] for x in cands if incoming_entry(x.get('desc'), x.get('quote'))]
    cur_grad = [x for x in cands if x['role'] in ('phd', 'masters') and not x['alumni'] and not x['why']]
    for x in cands:
        if x['why'] or x['role'] == 'visiting':
            continue
        if inc_names and any(names.match_one(x['name'], n) for n in inc_names):
            x['why'], x['detail'] = 'not_a_student', 'the same person is listed as an incoming student (a future year): not a member yet'
        elif x['alumni'] and x['role'] == 'undergraduate' and any(c is not x and names.match_one(x['name'], c['name']) for c in cur_grad):
            x['why'], x['detail'] = 'not_a_student', 'the same person is listed as a current graduate student on this page'
    start = plan.get('pi_start')
    page_alumni = {}
    for x in cands:
        if x['alumni'] and x['years'] and x['years'][1]:
            page_alumni[x.get('capture_url')] = max(page_alumni.get(x.get('capture_url'), 0), int(x['years'][1]))
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
        if plan.get('prior_reviewed') and not ys and not current_marker(x) and fn not in keep:
            x['why'], x['detail'] = 'undated_cannot_place', 'undated, not marked current, and not kept by the school\'s own reviewed pass'
            continue
        destination = re.match(r'^\W{0,3}[-–—]\s*\S', x.get('desc') or '') or \
            re.search(r'\b(now|currently) (at|a|an|with)\b|→|->|\bposition:|\bcurrent(ly)?:|\bnext:', (x.get('desc') or '')[:100], re.I)
        # labs older than the window (coordinator, 2026-10-31): an undated name is an addition only with an explicit current
        # marker in its own entry or its own section heading - 'current', 'Nth-year', 'candidate', an expected graduation year
        # (a stated year makes the entry dated). The old path for names on a 2025-26 page without a later job is gone: it
        # caused membership errors at Berkeley, CMU and Princeton. strict_removed marks the names that path used to admit.
        if auto_plan and (start is None or start < 2014) and not ys and fn not in keep and not current_marker(x):
            cap_y = int(re.search(r'/web/(\d{4})', x.get('capture_url') or '/web/2026').group(1))
            x['why'], x['detail'] = 'undated_cannot_place', (f"an undated entry of a lab older than the window (PI from {start or 'before 2016'}) "
                                                             "without a current marker in its entry or section heading"
                                                             + ('; it names a later position' if destination else ''))
            x['strict_removed'] = bool(cap_y >= 2025 and not destination and not x['alumni'])
            continue
        if fn not in keep and not ys and current_position_list(x.get('head')):
            x['why'], x['detail'] = 'undated_alumni_cannot_place', "a name in the alumni job column ('Current Position'), undated"
            continue
        if fn not in keep and not ys and not x['alumni'] and stale_list(x, page_alumni):
            x['why'], x['detail'] = 'undated_cannot_place', ('R-LAB-02: the page lists dated alumni only up to ' + str(page_alumni.get(x.get('capture_url')))
                                                             + ', long before its capture: its undated current list is an old list')
            continue
        if fn not in keep and primary_adviser_other(x.get('desc'), x.get('quote'), pi):
            x['why'], x['detail'] = 'not_a_student', 'the entry names another professor as its primary advisor / supervisor (no co- / joint wording): that professor\'s student'
            continue
        if x.get('src') not in text_cache and ',' in (x.get('quote') or ''):
            try:
                text_cache[x['src']] = kit.lpev.text(school, x['src'])
            except (KeyError, ValueError):
                pass
        if fn not in keep and author_list_item(x.get('quote'), text_cache.get(x.get('src')) or ''):
            x['why'], x['detail'] = 'not_a_student', 'a run of personal names followed by a paper title or venue: a reference byline, not a roster'
            continue
        if fn not in keep and advised_by_other(x.get('desc'), x.get('quote'), pi):
            x['why'], x['detail'] = 'at_previous_school', 'R-LAB-03: the entry names its own adviser, and the PI is not one of them'
            continue
        if fn not in keep and not x['alumni'] and other_institution_entry(x.get('desc'), x.get('quote'), school):   # on an alumni list a trailing 'Master Student, HKUST' is the DESTINATION after the lab, not where the person was (ZJU Kai Bu's list)
            x['why'], x['detail'] = 'at_previous_school', 'the entry places the person at another institution (\'@<University>\' or \'at <University>\' in the descriptor)'
            continue
        if fn not in keep and talk_item(x.get('head'), x.get('quote')):
            x['why'], x['detail'] = 'not_a_student', 'the entry is a CV line (a talk, keynote or award), not a roster entry'
            continue
        if fn not in keep and publication_item(x.get('head'), x.get('desc'), x.get('quote')):
            x['why'], x['detail'] = 'not_a_student', 'the entry is inside a publication list (a paper coauthor), not a roster entry'
            continue
        if fn not in keep and citation_fragment_item(x.get('quote'), x.get('desc')):
            x['why'], x['detail'] = 'not_a_student', 'the quote opens on a closing bracket: the tail of a reference line (a venue place, a paper author), not a roster entry'
            continue
        if fn not in keep and byline_item(x.get('quote')):
            x['why'], x['detail'] = 'not_a_student', 'the entry is an author byline (a name and a comma), not a roster entry'
            continue
        if fn not in keep and news_item(x.get('quote') or x.get('desc') or ''):
            x['why'], x['detail'] = 'not_a_student', 'the entry is a dated news sentence, not a roster entry'
            continue
        if fn not in keep and moved_in_alumnus(start, ys, x['alumni'], destination):
            x['why'], x['detail'] = 'at_previous_school', (f"undated alumnus / entry naming a later position on the page of a PI who arrived in {start}: it may be an advisee of the previous institution, "
                                                           "so it cannot be placed at this school")
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


STUDENT_REASON_ORDER = ('genuinely_missing', 'evidence_not_in_build', 'dropped_by_review', 'site_at_other_institution', 'shared_page_no_adviser', 'after_pi_left', 'at_previous_school', 'outside_2016_2026',
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
    cands, unreadable = pm_candidates(kit, school, pi, dict(plan, pi_start=pi_start_year(p), pi_end=pi_left_year(p), pi_names=[n for n in (p.get('names') or []) if len(n.split()) >= 2 or re.search(r'[\u4e00-\u9fff]{2,}', n)] + [pi]), held) if plan else ([], [])
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
                         is_cap=c['is_cap'], detail=c.get('detail'), role_basis=c.get('role_basis'), years_basis=c.get('years_basis'),
                         strict_removed=c.get('strict_removed')))
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
        if rc == 'undated_cannot_place' and any(r.get('strict_removed') for r in g):
            miss['strict_current_rule'] = True  # admitted before the 2026-10-31 stricter rule
        sec['missing_from_build'].append(miss)
        if rc == 'genuinely_missing':
            years, ybasis = best.get('years'), best.get('years_basis') or 'none'
            if not years:  # a date another capture of the same person states
                dated = [r for r in ok_ if r.get('years')]
                if dated:
                    years, ybasis = dated[0]['years'], dated[0].get('years_basis') or 'stated_in_entry'
            nm_c, role_c = clean_parenthetical_name(nm)
            if nm_c != nm:
                nm = nm_c
                if role_c and (best.get('role') in (None, 'member', 'other', 'postdoc', 'phd') or (role_c == 'visiting' and best.get('role') != 'postdoc')):
                    best = dict(best, role=role_c, role_basis='entry_parenthetical')
            if role_c in ('phd', 'masters') and best.get('role') == 'undergraduate' and best.get('alumni'):
                # 'Haolan Zhang\uff08Ph.D, SJTU) 2023' under an 'Undergraduate Students' alumni heading: the bracket says he is now a graduate student here; the heading
                # describes where he came from (SJTU round 6, \u9a6c\u53f6\u6db5's page)
                best = dict(best, role=role_c, role_basis='entry_parenthetical', alumni=False)
                if years:
                    years = [years[1] or years[0], None]
            if best.get('role') in (None, 'member'):
                q_ = best.get('quote') or ''
                j_ = q_.find(nm.split()[0]) if nm else -1
                rm_ = re.search(r'\b(undergraduate|master|ph\.?\s?d|graduate)s?\s+students?\s+who\b[^.]{0,80}$', q_[:j_] if j_ > 0 else '', re.I)
                if rm_:   # 'Undergraduate Students who have worked with me for more than 1 year Qian Cao Zhuoyan Chen': a lead-in sentence that names the role (SJTU round 6)
                    k_ = rm_.group(1).lower()
                    best = dict(best, role='undergraduate' if k_.startswith('under') else 'masters' if k_.startswith('master') else 'phd' if k_.startswith('ph') else 'phd', role_basis='entry')
            if SD.excluded(ctx_decisions(school), pi, nm):
                miss['reason_code'], miss['detail'] = 'reviewer_excluded', 'decided not / unclear for this lab (student-decisions.json)'
                continue
            if SD.visiting(ctx_decisions(school), pi, nm):
                best = dict(best, role='visiting', role_basis='reviewer')
            why_ = (not_a_member_context(kit, school, nm, best) or page_lacks_pi(kit, school, p, best) or page_pi_elsewhere(kit, school, p, best) or names_another_adviser(p, best)
                    or repair_reason(kit, school, nm, dict(best, years=years), pi_start_year(p), p.get('pi')))
            if why_:  # a Stanford Profiles reader / program listing, or a name in a citation (Stanford round 1, 2026-11-01)
                miss['reason_code'], miss['detail'] = why_
                continue
            try:  # the evidence check the build's lab-page rows pass: the quote is verbatim on the stored capture and names the person
                row = kit.lpev.M(school, nm, best.get('role') if best.get('role') in ROLE_OK else 'member', years,
                                 best.get('capture_url') or best['sha256'], quote=best['quote'],
                                 note=f"lab-page audit {TODAY}; section: {best.get('head')}")
            except (ValueError, KeyError) as e:
                miss['reason_code'] = 'name_unresolved'
                miss['note'] = f'quote check failed: {str(e)[:120]}'
                continue
            # alumni: the best (newest) capture's reading; an older capture that listed the person as current must not keep a graduate 'current'
            row.update(pi=pi, alumni=bool(best.get('alumni', alumni)), rule='LP-STU-01', auto=True, pi_first_year=pi_start_year(p),
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


REPOSITORY_DOI = re.compile(r'^10\.5281/zenodo\.|^10\.6084/m9\.figshare|^10\.17605/osf\.io|^10\.5061/dryad')
ABSTRACT_CODE_TITLE = re.compile(r'^(?:[A-Z]{1,2}\d{1,3}(?:\.\d+)*\.|(?!(?:19|20)\d\d\s)\d{3,4})\s+\S')  # '0689 Automated ...', 'S72. FUNCTIONAL ...': a meeting abstract's number
TALK_TITLE = re.compile(r'\((?:keynote|invited talk|invited|tutorial|panel|talk|abstract|poster|extended abstract)\)\s*$|^keynote\s*:', re.I)
AOM_ABSTRACT_DOI = re.compile(r'^10\.5465/ambpp\.|^10\.5194/egusphere-egu|^10\.1093/schbul/sb[a-z]+\d+\.\d+|^10\.1093/sleep/zs[a-z]+\d+\.\d+')  # meeting abstracts (R-PAP-19): Academy of Management Proceedings, EGU General Assembly (egusphere-egu), Schizophrenia Bulletin supplements (EPFL round 1)


def addition_not_a_paper(row):
    """Why a recovered row is not a paper: tools/pihier/papers.not_a_paper (R-PAP-17/18/19/22) on its title, venue and DOI,
    and what that rule reads from the OpenAlex type, which a recovered row does not carry: a repository record (Zenodo,
    figshare, OSF, Dryad DOI), a title marked as a keynote, talk, poster or abstract, an Academy of Management meeting
    abstract. None for a paper."""
    from pihier.papers import not_a_paper
    t, d = str(row.get('title') or ''), ndoi(row.get('doi'))
    why = not_a_paper(dict(title=t, venue=row.get('venue'), doi=d, byline=row.get('byline') or [], type=row.get('type')))
    if why:
        return why
    if REPOSITORY_DOI.search(d):
        return 'repository_record'
    if TALK_TITLE.search(t) or ABSTRACT_CODE_TITLE.search(t):
        return 'talk_or_abstract_title'
    if AOM_ABSTRACT_DOI.search(d):
        return 'meeting_abstract:doi'
    return None


def recover_dir(school):
    return P.data('labpage-audit-recover', school)


def recover_verdicts(school):
    """{audit_key: (status, junk reason, accepted row or None)} from the shadow recovery store."""
    db = recover_dir(school) / 'hierarchy' / school / 'labpage-recover.sqlite'  # route-ok: the recovery's private root is flat
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



def page_stale_footer(kit, school, src, cache):
    """The pre-2016 footer year of a people page (stale_footer_year), read from the stored page text; None when unreadable or current."""
    try:
        if src not in cache:
            cache[src] = kit.lpev.text(school, src)
    except (KeyError, ValueError):
        return None
    m = re.search(r'/web/(\d{4})', src or '')
    return stale_footer_year(cache[src], int(m.group(1)) if m else None)


def caps_heading_is_past(kit, school, src, name, cache):
    """True when the closest ALL-CAPS heading before the name on the page text says PAST / FORMER / ALUMNI (Berkeley round 2,
    2026-10-31: Sastry's 'PAST POST-DOCTORAL RESEARCHERS' names were read under the 'CURRENT POST-DOCTORAL RESEARCHERS'
    section). Only a heading in capitals counts, so a name in prose is never moved."""
    try:
        if src not in cache:
            cache[src] = kit.lpev.text(school, src)
        t = cache[src]
    except (KeyError, ValueError):
        return False
    j = t.find(name)
    if j < 0:
        return False
    last = None
    for m in re.finditer(r'\b(?:CURRENT|PRESENT|PAST|FORMER|PREVIOUS|ALUMNI|ALUMNAE)\b(?: [A-Z][A-Z\-/&,]*){1,6}', t[:j]):
        last = m
    return bool(last and last.group(0).split()[0] in ('PAST', 'FORMER', 'PREVIOUS', 'ALUMNI', 'ALUMNAE'))


WEAK_PROFILE_LABEL = re.compile(r"Doctoral Dissertation Reader|Reader \(AC\)|\(Program\)|Program Advisor|Major Advisor|Orals Evaluator")
CITATION_CONTEXT = re.compile(r"\bpp\.\s*\d|\bPDF\s*\||\bView details for\b|\bProceedings of\b|\bTrans\. on\b|(?i:\bbibtex\b)|\bSupplemental\b|\bproject page\b|\[Link\]|\b(?:Journal|Transactions|Review|Letters|Conference) (?:on|of|in)\b[^.]{0,80}\((?:19|20)\d\d\)")


ADMIN_DESC = re.compile(r"\b(?:Secretary|Administrative\s+(?:Assistant|Specialist|Associate|Staff)|Group\s+Administrator|Office\s+Manager|Executive\s+Assistant)\b", re.I)
AFFILIATE_DESC = re.compile(r"^\W{0,3}(?:Research\s+|Senior\s+)?(?:Affiliate|Partner|Collaborator|Consulting\s+Professor|Adjunct)\b", re.I)
PROF_TITLE_DESC = re.compile(r"^\W{0,3}(?:\(\s*)?(?:consulting|courtesy|adjunct|emeritus|clinical)\s+(?:associate\s+|assistant\s+|full\s+)?(?:professor|faculty|lecturer)\b|^\W{0,3}(?:Professor|Associate Professor|Assistant Professor)\b|^\W{0,3}Visiting\s+(?:Scientist|Researcher|Faculty|Professor)\b", re.I)
BIO_TRIGGER = re.compile(r"(?:(?:kindly\s+)?hosted\s+by|worked\s+(?:closely\s+)?with|advised\s+by|advis[eo]rs?\s+(?:was|were|is|are)|mentored\s+by|supervised\s+by|collaborat\w+\s+with|together\s+with|studied\s+under|under\s+the\s+(?:guidance|supervision)\s+of)\s+", re.I)
BIO_TAIL = re.compile(r"^(?:(?:Prof\.?|Professor|Dr\.?)\s+)?(?:[A-Z]\.|[A-Z][\w'À-ſ-]+)(?:\s+(?:[A-Z]\.|[A-Z][\w'À-ſ-]+)){0,3}(?:\s*(?:,|and|&)\s+(?:(?:Prof\.?|Professor|Dr\.?)\s+)?(?:[A-Z]\.|[A-Z][\w'À-ſ-]+)(?:\s+(?:[A-Z]\.|[A-Z][\w'À-ſ-]+)){0,3})*\s*,?\s*(?:and\s+)?$")
OTHER_INST_ROLE = re.compile(r"\b(?:MS|M\.S\.|MSc|PhD|Ph\.D\.|BS|B\.S\.|Undergrad(?:uate)?|Master'?s?)\s+(?:Student|Candidate|Researcher)?\s*,?\s*(MIT|Harvard|Caltech|Cornell|Yale|Princeton|Columbia|Oxford|Cambridge|ETH|EPFL|NUS|Tsinghua|Stanford|Berkeley|CMU|UCLA|UCSD|Toronto|Waterloo|Michigan)\b")
OWN_INST_NAMES = {'michigan': {'MICHIGAN'}, 'stanford': {'STANFORD'}, 'mit': {'MIT'}, 'cmu': {'CMU'}, 'berkeley': {'BERKELEY'}, 'epfl': {'EPFL'}, 'princeton': {'PRINCETON'}}
FACULTY_HEAD = re.compile(r"\bVisiting\s+(?:Scientists?|Professors?|Faculty|Researchers?\s+at)\b|\bFaculty\b(?!.*student)|\bCollaborators?\b|\bLab\s+Affiliates?\b", re.I)
NAME_NOISE = re.compile(r"\b(?:AWS|Firecracker|Maria\s+Curie|Marie\s+Curie|Sk[lł]odowska|Fulbright|Humboldt|Erasmus|Docker|Linux|GitHub|Kubernetes|PyTorch|TensorFlow|Citadel|Fellowship|Scholarship|Award|Prize|Grant|Foundation|Oral'?s?|Orals?\s+Chair|Chair|Reader|Committee|Evaluator|Examiner|Moderator|Panelist|Complaint|Policy|Privacy|Accessibility|Transfer|Network|Learning)\b", re.I)
PAREN_TAIL = re.compile(r'\s*[(\uff08]([^()\uff08\uff09]{1,40})[)\uff09]\s*$')   # fullwidth brackets too (SJTU 2026-11-11: 'Qi Fan\uff08Master)')
COADVISER_BEFORE = re.compile(r"(?:co-?advis(?:ed|ors?|ing|e)|co-?taught|taught|co-?supervis\w*|jointly\s+\w+|joint(?:ly)?)\s*(?:with|w/|by|:)\s*$|\(\s*with\s+$|\bw/\s*$|\bwith\s+Prof\.?\s+$|co-?advis[eo]rs?\s*:?\s*$", re.I)
COLLAB_PROSE = re.compile(r"collaborat\w*\s+with\s+(?:the\s+|some\s+)?(?:\w+\s+){0,3}(?:students|researchers|postdocs)", re.I)
CITE_INITIALS = re.compile(r"[A-Z][\w'\u00C0-\u017F-]+(?:\s[A-Z][\w'\u00C0-\u017F-]+)*,\s(?:[A-Z]\.\s?){1,3}(?:,|\.|\s)")
OTHER_INST_LABEL = re.compile(r"^\s{1,3}((?:UC\s+[A-Z][a-z]+|UCL|UIUC|UCLA|UCSD|MIT|CMU|ETH(?:\s+Zurich)?|EPFL|NUS|NTU|HKUST|CUHK|KAIST|Caltech|Tsinghua|Peking|PKU|Stanford|Harvard|Oxford|Cambridge|Imperial|(?:The\s+)?University\s+of\s+[A-Z][A-Za-z]+(?:\s+[A-Z][a-z]+)?|[A-Z][a-z]+\s+University))(?=[\s,;)]|$)")
COLLAB_LIST_HEAD = re.compile(r"(?:Students|Collaborators?|People)\s+I\s+(?:Currently\s+)?(?:Work(?:ed)?|Collaborate)\s+with", re.I)
OTHER_INST_ANY = re.compile(OTHER_INST_LABEL.pattern.replace(r'^\s{1,3}(', r'\s(', 1))
FUTURE_START = re.compile(r"\b(?:incoming|will\s+join)\b|\b(?:Fall|Spring|Autumn)\s+202[7-9]\b|\b202[7-9]\s*(?:Fall|Spring|Autumn)\b", re.I)
OTHER_INST_AT = re.compile(r"@\s*([A-Z][A-Za-z]{1,8})\b")
OWN_INST = {'michigan': {'UM', 'UMICH', 'MICHIGAN', 'UMICHIGAN'}, 'stanford': {'STANFORD', 'SU'}, 'mit': {'MIT'},
            'cmu': {'CMU'}, 'berkeley': {'UCB', 'BERKELEY', 'UCBERKELEY'}, 'epfl': {'EPFL'}, 'princeton': {'PRINCETON'}}
ROLE_PAREN = (('postdoc', 'postdoc'), ('post-doc', 'postdoc'), ('phd', 'phd'), ('ph.d', 'phd'), ('master', 'masters'),
              ('ms student', 'masters'), ('undergrad', 'undergraduate'))


def clean_parenthetical_name(name):
    """('Linfeng Li (postdoc) (co-advisor)') -> ('Linfeng Li', 'postdoc'): trailing parentheticals are annotations, not the
    name; a role word in them is the entry's stated role (Michigan round 2)."""
    role, nm = None, name or ''
    nm = re.sub(r'^\s*[(\uff08]\s*co-?(?:supervis\w*|advis\w*)\s*[)\uff09]\s*', '', nm, flags=re.I)   # '(Co-supervision) Jiawen Zhang' (HKUST)
    tl = re.search(r'\s+(post-?doctorate|post-?doc|postdoctoral(?:\s+fellow)?|research\s+(?:associate|assistant|fellow))\s*$', nm, re.I)
    if tl and len(nm[:tl.start()].split()) >= 2:   # 'Zhai Chao Post-doctorate': the label glued to the name is the stated role, never a heading's phd (NTU round 6)
        role = 'postdoc' if tl.group(1).lower().startswith('post') else 'other'
        nm = nm[:tl.start()].strip()
    um = re.search(r'\s*[\uff08(]\s*(ph\.?\s?d|m\.?s\.?|b\.?s\.?|postdoc|master|undergrad\w*)\.?\s*$', nm, re.I)   # 'Haolan Zhang\uff08Ph.D': an unclosed bracket fragment (SJTU round 6, \u9a6c\u53f6\u6db5's page)
    if um and len(nm[:um.start()].split()) >= 2:
        for k, v in ROLE_PAREN:
            if k in um.group(1).lower() and role is None:
                role = v
        nm = nm[:um.start()].strip()
    while True:
        m = PAREN_TAIL.search(nm)
        if not m or len(nm[:m.start()].split()) < 2:
            break
        if role is None and VIS.says_visiting('(' + m.group(1) + ')'):
            role = 'visiting'   # 'Ann Lee (visiting, CUHK)', 'Bo Xu (visiting PhD, ETH)' (R-STU-17)
        for k, v in ROLE_PAREN:
            if k in m.group(1).lower() and role is None:
                role = v
        nm = nm[:m.start()].strip()
    return nm, role


_PI_NAMES = {}


def pi_alias_map(school):
    if school not in _PI_NAMES:
        _PI_NAMES[school] = {r['pi']: [r['pi']] + [n for n in (r.get('names') or []) if n != r['pi']] for r in read(P.data('pis.json', school))}
    return _PI_NAMES[school]


def other_pis_on_page(school, pi, text, k=None):
    """How many OTHER PIs of the school are named in full on the page: a page that lists several faculty and then all of their
    students (graphics.stanford.edu/people.html) is a shared page, not this PI's lab page (Stanford round 4). A Han-keyed PI is also counted by its Latin
    names (pis.json `names`) because the page is often written in English (Tsinghua round 2: 冯建华's dbgroup page lists seven professors in Latin)."""
    amap = pi_alias_map(school)
    t = fold(text if k is None else text[max(0, k - 900): k + 900]).lower()
    han = text if k is None else text[max(0, k - 900): k + 900]
    return sum(1 for n, al in amap.items() if n != pi and any(((len(a.split()) >= 2 and fold(a).lower() in t) or (re.search(r'[\u4e00-\u9fff]{2,}', a) and a in han)) for a in al))


def repair_reason(kit, school, name, best, start, pi=None):
    """(reason code, detail) for the 2026-11-01 repairs (owner exception, Stanford/CMU rounds 4-5; Michigan round 3), applied
    to every school: honorific / committee words in a name, a name inside a reference block (PubMed 'Surname, A. B.,' lists),
    a co-adviser named in a 'co-advised with X' phrase, a student of another institution ('@NUS'), and an undated entry of a
    lab older than the window without a current marker whatever the plan (the earlier rule ran for audit-discovered labs only).
    None for a member."""
    cm = re.search(r'/web/(\d{4})', best.get('capture_url') or '')
    if cm and int(cm.group(1)) < WINDOW[0] and not best.get('years'):
        return 'outside_2016_2026', f'listed on a {cm.group(1)} capture, before the window, and undated'
    ds = (best.get('desc') or '')[:90]
    if FACULTY_HEAD.search((best.get('head') or '').split(' > ')[-1]):
        return 'not_a_student', 'under a visiting-scientist, faculty or collaborator heading'
    if ADMIN_DESC.search(ds):
        return 'not_a_student', 'administrative staff (secretary, administrative assistant): not a lab member in the study'
    if PROF_TITLE_DESC.search(ds) and not re.search(r'student|candidate|postdoc', ds, re.I):
        return 'not_a_student', 'a consulting, courtesy, adjunct or professor title: faculty, not a student'
    if AFFILIATE_DESC.search(ds):
        return 'not_a_student', 'an affiliate, partner or collaborator of the group, not a member'
    if NAME_NOISE.search(name or ''):
        return 'name_unresolved', 'the name carries a committee or honorific word (Oral\'s Chair, Reader, Committee)'
    q = best.get('quote') or ''
    try:
        t = kit.lpev.text(school, best.get('capture_url') or best['sha256'])
    except (KeyError, ValueError):
        t = ''
    j = t.find(q) if q else -1
    if j >= 0:
        k = t.find(name.split()[0], j) if name else j
        k = j if k < 0 else k
        pic = re.sub(r'\s+', '', pi or '')
        if pic and re.match(r'\s*[(\uff08]\s*' + re.escape(pic) + r'\s*[)\uff09]', t[k + len(name or ''): k + len(name or '') + 30]):
            return 'not_a_student', "the PI's own name (the page title gives the PI's name with the Chinese form)"
        tg = re.search(r'\bLab\s+(Affiliates?|Members?)\b', t[k + len(name or ''): k + len(name or '') + 220])
        if tg and tg.group(1).lower().startswith('affiliate'):
            return 'not_a_student', 'tagged Lab Affiliate (an outside affiliate of the group), not a lab member'
        if re.search(r'Class\s+of\s+\d{4}[^.]{0,90}\b(?:Cornell|Johnson\s+Graduate|Chicago\s+Booth)|\b(?:Master|Doctoral)\s+(?:Student|Candidate)\b[^.]{0,80}\b(?:Cornell|Johnson\s+Graduate)', t[k + len(name or ''): k + len(name or '') + 200]) and 'CORNELL' not in own_names(school, OWN_INST):
            return 'site_at_other_institution', 'the entry places the person in a degree programme at another institution (Cornell Johnson), an outside student of a joint lab'
        if school in NON_US_CLASS_SCHOOLS and re.search(r'\bClass\s+of\s+(?:19|20)\d\d\b', t[k + len(name or ''): k + len(name or '') + 160]):
            return 'site_at_other_institution', "a 'Class of YYYY' entry is a US-college cohort line (an outside affiliate of the joint lab), not a lab member of this school"
        lm = OTHER_INST_LABEL.match(t[k + len(name or ''): k + len(name or '') + 40])
        if lm and best.get('role') != 'visiting' and not re.match(r'\s*[(\[]?(?:19|20)\d\d', t[k + len(name or '') + lm.end(): k + len(name or '') + lm.end() + 8]) and not (set(re.findall(r'[A-Za-z]{2,}', lm.group(1).upper())) & (own_names(school, OWN_INST) | own_names(school, OWN_INST_NAMES) | {'SJTU', 'JIAO', 'TONG'})):
            return 'site_at_other_institution', f'the entry labels the person with {lm.group(1)} (a card list of the PI\'s collaborators and students elsewhere)'
        wide = t[max(0, k - 1500): k + 600]
        if COLLAB_LIST_HEAD.search(t[max(0, k - 1500): k]) and len({m.group(1) for m in OTHER_INST_ANY.finditer(wide)}) >= 2:
            return 'not_a_student', "a mixed-institution list of people the PI 'works with' (students labelled with other universities): collaborators, not members"
        fs_seg = t[k + len(name or ''): k + len(name or '') + 45]
        fs_m = FUTURE_START.search(fs_seg)
        if fs_m and not re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+', fs_seg[:fs_m.start()]):   # the phrase belongs to this entry only when no other name sits between
            return 'not_a_student', 'an incoming student whose start is after the capture (admitted, Fall 2027): not yet a member'
        pre_bio = t[max(0, k - 140): k]
        tm = list(BIO_TRIGGER.finditer(pre_bio))
        if tm and (not pre_bio[tm[-1].end():].strip() or re.fullmatch(r'(?:Prof\.?|Professor|Dr\.?)\s*', pre_bio[tm[-1].end():].strip() + ' ') or BIO_TAIL.match(pre_bio[tm[-1].end():])) and len(re.findall(r'\b[a-z]{3,}\b', pre_bio[:tm[-1].start()])) >= 3:
            return 'not_a_student', 'named in a bio sentence (worked with / advised by ...), not listed as a member'
        om = None if best.get('role') == 'visiting' else OTHER_INST_ROLE.search(t[k + len(name): k + len(name) + 40])   # a visiting student is a student elsewhere by definition (R-STU-17)
        if om and om.group(1).upper() not in own_names(school, OWN_INST_NAMES) and not re.search(r'(?:now|next|currently|then|→|->|\bat)\W{0,3}(?:a\s+|an\s+)?$', t[k + len(name): k + len(name) + om.start()][-40:], re.I):
            return 'site_at_other_institution', f'the entry places the person at {om.group(1)}'
        if COADVISER_BEFORE.search(t[max(0, k - 40): k]):
            return 'not_a_student', 'named as the co-adviser of another member (co-advised with / jointly supervised with)'
        own_hdr = any(len(a_.split()) >= 2 and fold(a_).lower() in fold(t[:700]).lower() for a_ in pi_alias_map(school).get(pi, []))   # the page's own header names the PI (a 'Director Prof. X' line): his group's page, not a department page (Tsinghua round 4: routing.netlab)
        if pi and (other_pis_on_page(school, pi, t, k) >= 6 or (not own_hdr and ((other_pis_on_page(school, pi, t, k) >= 3 and len(re.findall(r'\bProfessor\b', t)) >= 5) or (other_pis_on_page(school, pi, t) >= 5 and len(re.findall(r'\bProfessor\b', t)) >= 5)))) and len(re.findall(r'co-?advis|jointly|\bw/|\(with ', t[max(0, k - 900): k + 900], re.I)) < 2 and not any(fold(al.split()[-1]).lower() in fold(t[k: k + 120]).lower() for al in pi_alias_map(school).get(pi, [pi])):
            return 'shared_page_no_adviser', 'a page that names several faculty and their students; the entry does not name this PI as adviser'
        if COLLAB_PROSE.search(t[max(0, k - 300): k]):
            return 'not_a_student', 'listed among collaborators ("collaborate with the PhD students ...")'
        win = t[max(0, k - 250): k + 250]
        if len(CITE_INITIALS.findall(win)) >= 3 or re.search(r'\bPubMed(?:ID)?\b', win):
            return 'name_unresolved', 'the name sits inside a reference block (author list of citations)'
        tail = t[k: k + 90]
        m = OTHER_INST_AT.search(tail)
        if m and best.get('role') != 'visiting' and m.group(1).upper() not in own_names(school, OWN_INST) | {'HOME'} and m.group(1).isupper():
            return 'site_at_other_institution', f'the entry places the person at another institution (@{m.group(1)})'
    if (start is None or start < 2014) and not best.get('years') and not current_marker(best) and not best.get('alumni_marked_dated'):
        return 'undated_cannot_place', 'an undated entry of a lab older than the window without a current marker in its entry or section heading'
    return None


def not_a_member_context(kit, school, name, best):
    """(reason code, detail) when the evidence for a student is not a membership statement: a Stanford Profiles reader / program /
    major-advisor heading (the profile lists the person as read-by or in-program, not as an advisee; pihier.students.WEAK_LABEL),
    or a name inside a publication citation (page text near the quote carries page ranges, PDF links or a venue). None otherwise."""
    q = best.get('quote') or ''
    try:
        t = kit.lpev.text(school, best.get('capture_url') or best['sha256'])
    except (KeyError, ValueError):
        t = ''
    j = t.find(q) if q else -1
    heads_rx = re.compile(r"Doctoral Dissertation Advisor|Doctoral Dissertation Co-Advisor|Doctoral Dissertation Reader|Postdoctoral Faculty Sponsor|"
                          r"Postdoctoral Research Mentor|Doctoral \(Program\)|Master's Program Advisor|Undergraduate Major Advisor|Orals Evaluator|Reader \(AC\)")
    if j >= 0 and (q or t):
        win = t[max(0, j - 500): j + max(q.find(name.split()[0]) if name else 0, 0) + 1]
        hs = list(heads_rx.finditer(win))
        if hs and WEAK_PROFILE_LABEL.search(hs[-1].group(0)):
            return 'not_a_student', 'profile reader / program / major-advisor listing, not an advisee'
    if j >= 0:  # a 'Rotating PhD Students' list: rotation students are not lab members (docs/LAB-PAGES.md, not_a_student)
        qn = q.find(name.split()[0]) if name else -1
        pre = t[max(0, j - 200): j + max(qn, 0)]
        rm = list(re.finditer(r'\b(?:Rotating|Rotation)\s+(?:Ph\.?D\.?\s+)?Students\b', pre))
        if rm and not re.search(r'Undergraduate|Alumni|Postdoc|Master|Visitors|Staff|Graduate Students', pre[rm[-1].end():]):
            return 'not_a_student', 'a rotation student'
    if j >= 0:
        k = t.find(name.split()[-1], j) if name else j
        k = j if k < 0 else k
        if CITATION_CONTEXT.search(t[max(0, k - 160): k + 160]):
            return 'name_unresolved', 'the name sits inside a publication citation'
    return None


ADVISER_LINE_RX = re.compile(r'\bAdvisors?\s*[-:\u2013]\s*(.*?)(?=Research Interests|Employment|Thesis|After graduating|$)', re.S)


def names_another_adviser(p, best):
    """An entry of a student list that gives each student's adviser ('Gene Li PhD - 2025 Advisor - Nati Srebro') names the adviser itself: a row under
    another PI of the same page is not this lab's student (UChicago stage 6: TTIC's alumni list under Shakhnarovich). Returns a reason pair or None."""
    m = ADVISER_LINE_RX.search(' '.join(str(x or '') for x in (best.get('desc'), best.get('quote'))))
    fam = str(p.get('pi') or '').split()[-1:] or ['']
    if m and fam[0] and fold(fam[0]).lower() not in fold(m.group(1)).lower():
        return ('shared_page_no_adviser', 'the entry names another adviser: ' + m.group(1).strip()[:80])
    return None


def page_pi_elsewhere(kit, school, p, best):
    """Toronto lab-page round 1 (2026-11-10): a project-team page that describes the PI herself as a researcher at ANOTHER institution
    ('Anwar Hithnawi is a research scientist at the NetSys Lab at UC Berkeley') is not this school's lab roster; its members are collaborators.
    The 150 characters after the PI's full name must name no school affiliation (the charter regex) and name another institution."""
    try:
        t = kit.lpev.text(school, best.get('capture_url') or best['sha256'])
    except (KeyError, ValueError):
        return None
    return pi_elsewhere_reason(t, str(p.get('pi') or ''), school)


OTHER_INST_RX = re.compile(r"\b(?:ETH|EPFL|MIT|Stanford|Berkeley|UC\s+[A-Z][a-z]+|Cambridge|Oxford|Carnegie Mellon|CMU|Cornell|Princeton|Harvard|Yale|Columbia|"
                           r"University of [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?|[A-Z][a-z]+ University|Institute of Technology|RISE|Google|Microsoft|Meta|IBM)\b", re.I)


def pi_elsewhere_reason(text, pi, school):
    if not text or not pi:
        return None
    fl = fold(text)
    i = fl.lower().find(fold(pi).lower())
    while i >= 0:
        seg = fl[i + len(pi): i + len(pi) + 150]
        if re.match(r"\s+(?:is|was)\s+(?:a|an|the)\b", seg):
            try:
                import school_config as SC
                aff = SC.aff_rx(school)
            except Exception:  # noqa: BLE001
                aff = re.compile(r'toronto|vector institute', re.I)
            if not aff.search(seg) and OTHER_INST_RX.search(seg):
                return ('site_at_other_institution', 'the page describes the PI as a researcher at another institution: a project or collaborator page, not this school\'s lab roster')
        i = fl.lower().find(fold(pi).lower(), i + 1)
    return None


def pi_family_tokens(pi):
    """Tokens that identify a PI's family name on a page. 'Raymond Chi-Wing WONG 黃智榮': the last token is the CJK name, which an English page never
    holds (HKUST 2026-11-11: 64 rows of 11 PIs were rejected as 'the page never names the PI'), so the last Latin token counts too. A pure-CJK name keeps its last token."""
    toks = str(pi or '').split()
    latin = [t for t in toks if re.fullmatch(r"[A-Za-z][A-Za-z'.\-]+", t)]
    out = toks[-1:] + latin[-1:]
    return list(dict.fromkeys(out)) or ['']


def pi_latin_given_family(p):
    import pi_name_signal as N
    return N.readings(p.get('pi'), p.get('names'))


def pi_full_name_on_page(text, p):
    """A SIGNAL that a page is about the PI, never identity binding (tools/pi_name_signal.py; shared with lab_websites/person_fetch)."""
    import pi_name_signal as N
    return N.page_names_pi(text, p.get('pi'), p.get('names'))


def page_lacks_pi(kit, school, p, best):
    """Stanford: a page that never names the PI is a department or program page (Journalism's students list under Hancock),
    not the lab's page. Other schools' lab pages legitimately omit the PI's name, so this applies to Stanford only."""
    if school in LEGACY_SCHOOLS and school not in ('stanford', 'berkeley'):
        return None   # a charter school (UChicago stage 6, 2026-11-03: the Statistics PhD alumni page had become 'the lab page' of three PIs) gets the rule too
    try:
        t = kit.lpev.text(school, best.get('capture_url') or best['sha256'])
    except (KeyError, ValueError):
        return None
    fam = pi_family_tokens(p.get('pi'))
    return None if (not t or any(fold(f).lower() in fold(t).lower() for f in fam) or pi_full_name_on_page(t, p)) else ('shared_page_no_adviser', 'the page never names the PI: a department or program page')


def apply_template_reader(kit, school, src, x, cache):
    """ROADMAP P2 #27: on a page built from a known template (Google Sites, WordPress, al-folio/Jekyll) take the candidate's section
    heading and entry text from the DOM (tools/lp_templates.py), not from the flattened text that runs adjacent one-line sections
    together. Sets x['head'], x['desc'] and x['template']; leaves the candidate alone when the template is unknown or the name
    is not found in an entry. LP_TEMPLATE_READERS=0 turns it off."""
    if os.environ.get('LP_TEMPLATE_READERS', '1') == '0':
        return
    import lp_templates
    if src not in cache:
        try:
            row, _ = kit.lpev.cap(school, src)
            c = row['content']
            try:
                import zlib
                c = zlib.decompress(c)
            except Exception:  # noqa: BLE001 - stored uncompressed
                pass
            h = c.decode('utf-8', 'ignore') if 'html' in (row.get('content_type') or '').lower() else ''
        except (KeyError, ValueError):
            h = ''
        cache[src] = (h, lp_templates.detect(h, src) if h else None, {})
    h, tmpl, memo = cache[src]
    if not tmpl:
        return
    if 'sections' not in memo:
        memo['sections'] = lp_templates.sections(h)
    head, entry = lp_templates.locate_in(memo['sections'], x['name'])
    if head and entry.lower().startswith(x['name'].lower()[:max(4, len(x['name']) - 6)]):  # one person per element: a run-on paragraph keeps the flattened reading
        low = entry.lower()
        j = low.find(x['name'].lower())
        new_desc = entry[j + len(x['name']):].strip() if j >= 0 else x.get('desc')
        role_of = kit.autom._role
        old_r, old_b = entry_role(x.get('desc'), x.get('head'), role_of)
        new_r = entry_role(new_desc, head, role_of)[0]
        if old_b == 'entry' or (new_r is None and old_r is not None):
            return  # the entry itself states the role (MS Student UM EECS), or the DOM states none: keep the flattened reading
        x['template'] = tmpl
        x['head'] = head
        x['desc'] = new_desc


def appointed_in(p, year):
    """The build's appointment test for a proposed paper (R-PAP-01, R-PAP-03) on the PI as the audit reads them, overrides
    included: a period that contains the year ('supported'), else a listing of that year that is not a stale page after an
    evidenced departure (listings_after_move). The recovery step judged against the pis.json it was shadowed on; this
    re-applies the rule to the current periods (2026-10-31: Haeupler 2023 after his 2022 end, Yao 2025 after her 2023-12 end)."""
    if not year:
        return True
    from pihier.periods import contains, listings_after_move
    pers = p.get('periods') or []
    if any(contains(q.get('start'), q.get('end'), str(year), q.get('asof') or TODAY) == 'supported' for q in pers):
        return True
    ls = {l['year']: l for l in p.get('listings') or [] if l.get('year')}
    stale = listings_after_move(ls, [], pers)
    return int(year) in ls and int(year) not in stale


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
        if rc == 'genuinely_missing' and acc and not appointed_in(p, acc.get('year') or e.get('year')):
            rc = paper_reason('outside_appointment', None, acc.get('year') or e.get('year'), start)
            st, why = 'outside_appointment', None
        if rc == 'matched':
            sec['matched_in_lab_papers'] += 1
            continue
        item = dict(base, reason_code=rc, quote=e.get('quote'))
        if st == 'junk' and why:
            item['detail'] = why
        sec['missing'].append(item)
        if rc == 'genuinely_missing' and acc:
            np_ = addition_not_a_paper(acc)
            if np_:  # the build's own not-paper rules (R-PAP-18/19) and the record kinds they do not see without a type
                item['reason_code'], item['detail'] = 'not_a_paper', np_
                continue
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
    url = url.strip() if url else url
    if url and getattr(kit, 'host_use', lambda host: 'live')(urlsplit(unwayback(url)).hostname or '') == 'none':
        return None, ''
    row, views = kit.stored(url) if url else (None, None)
    if not row and url:
        source = kit.src_of(url)  # cached archive lookup only; never fetch here
        if source != url:
            row, views = kit.stored(source)
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
INSTITUTION_LISTING = re.compile(r'^/(people|directory|alumni|students|our-people)(/(alumni|students|phd(-students)?|graduates?|faculty|staff|'
                                 r'postdocs?|all))?/?$', re.I)  # a department's own list (hcii.cmu.edu/people/alumni), not a lab's
PEOPLE_PATH = re.compile(r'people|member|team|student|alumni|group|personnel|advisee|former|lab', re.I)
PUBS_PATH = re.compile(r'publication|papers|pubs|bibliograph|/cv|vita|talks|thesis|teaching|course', re.I)
STRICT_HEAD = re.compile(r'\b(students?|ph\.?\s?d|post-?docs?|post-?doctoral|alumni|alumnae|graduated|graduates|advisees?|members?|team|'
                         r'people|researchers|visitors|undergrad\w*|masters?|interns?|doctoral|staff|former|current)\b|\u5728\u8bfb|\u7814\u7a76\u751f|\u535a\u58eb\u751f|\u7855\u58eb\u751f|\u672c\u79d1\u751f|\u5df2\u6bd5\u4e1a|\u6bd5\u4e1a\u751f|\u6821\u53cb|\u73b0\u6709\u6210\u5458|\u73b0\u5f79|\u5728\u7ad9|\u6210\u5458|\u7814\u7a76\u52a9\u7406', re.I)
HOMEPAGE_HEAD = re.compile(r'\b(students?|ph\.?\s?d|post-?docs?|post-?doctoral|advisees?|alumni|graduated|mentees|group members|'
                           r'lab members|research group|my group)\b', re.I)  # a homepage used as the people page: only these sections
NOT_MEMBER_HEAD = re.compile(r'committee|publication|papers|thesis|theses|talks?|course|collaborat|co-?authors?|press|news|award|'
                             r'service|editor|reviewer|program|\b[st]?pc\b|best[\w\s-]{0,24}paper', re.I)
# Tsinghua 2026-11-11 (zhang han 14 rows, huang minlie 1): 'TPC member > <paper title>' matched STRICT_HEAD through 'member' and 'NLPCC 2020 (Best Student
# Paper)' through 'student'; a technical-programme-committee list, a (S)PC heading or a best-paper heading is never a member list.


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
        kit.import_school_web(str(P.data('school-captures.sqlite', ctx['school'])), [prior.get('people_page'), prior.get('lab_site')] + pages)
    man = (ctx.get('manual') or {}).get(pi) or {}
    if 'people' in man:
        pages = list(man['people'])
    live, caps = [], collections.defaultdict(list)
    for u in pages:
        if not u or (u != prior.get('people_page') and not PEOPLE_PATH.search(urlsplit(unwayback(u)).path or '')) or \
                PUBS_PATH.search(urlsplit(unwayback(u)).path or '') or \
                (INSTITUTION_LISTING.search(urlsplit(unwayback(u)).path or '') and
                 urlsplit(unwayback(u)).hostname != urlsplit(prior.get('lab_site') or '').hostname) or \
                is_profile(unwayback(u), ctx['cfg'].get('domain', r'^$')):
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


def assemble(kit, ctx, disc, verdicts=None, keep=None, only=None):
    """only: a list of PIs to audit (a chunk, `audit-chunk`); the shared-page map is always computed over every PI."""
    recs, stu_adds, pap_adds, rec_rows = [], [], [], []
    shared = shared_people_pages(ctx, disc)
    for p in (ctx['pis'] if only is None else only):
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
            return html_robots_is_no_rules(body)
        if os.environ.get('CS_ATLAS_LABPAGE_LIVE_ONLY') == '1' and names_project_agents(body):
            return False  # the top-25/source policy excludes hosts naming these agents entirely
        rp = urllib.robotparser.RobotFileParser()
        rp.parse(body.splitlines())
        return all(rp.can_fetch(a, url) for a in AI_AGENTS)
    mpcap.robots_allowed = robots_allowed


class DeadlineRequests:
    """requests with an overall deadline per download (requests' read timeout is per chunk, so a server that trickles
    bytes can hold a worker forever) and a size cap; otherwise the requests module."""
    def __init__(self, deadline=150, cap=60 * 2 ** 20):
        import requests
        self._r, self.deadline, self.cap = requests, deadline, cap
        self.RequestException = requests.RequestException
        self.exceptions = requests.exceptions

    def get(self, url, **kw):
        import time as _t
        kw['stream'] = True
        r = self._r.get(url, **kw)
        t0, buf = _t.time(), bytearray()
        try:
            for chunk in r.iter_content(65536):
                buf += chunk
                if _t.time() - t0 > self.deadline or len(buf) > self.cap:
                    r.close()
                    raise self._r.exceptions.ReadTimeout(f'deadline or size cap reached for {url[:120]}')
        finally:
            r.close()
        r._content = bytes(buf)
        return r


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
    sh = root / 'hierarchy' / school  # route-ok: the recovery's private root is laid out flat
    sh.mkdir(parents=True, exist_ok=True)
    for f in ('pis.json', 'lab_papers.jsonl.gz', 'openalex-sweep.sqlite', 'pi-works.sqlite'):
        relink(P.data(f, school), sh / f)
    relink(P.data('cs-venues.json'), root / 'hierarchy' / 'cs-venues.json')  # route-ok: private flat root
    db = sh / 'labpage-recover.sqlite'
    if not db.exists() and (P.data('labpage-recover.sqlite', school)).exists():  # reuse the earlier run's arXiv index and OpenAlex cache
        src = sqlite3.connect(f"file:{P.data('labpage-recover.sqlite', school)}?mode=ro", uri=True)
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
    LR.requests = DeadlineRequests()  # 2026-10-31: Princeton and MIT hung for hours on one trickling PDF download
    patch_mpcap(LR.mpcap)
    LR.mpcap.LOCKDIR = str(P.RATE_STAMPS / 'hosts')  # shared per-host stamps (atlas_paths RATE_STAMPS)
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
                      removed_by_strict_current_rule=sum(1 for r in recs for m in r['students']['missing_from_build'] if m.get('strict_current_rule')),
                      proposed_additions=len(stu_adds),
                      extra_in_build_not_on_page=sum(r['students']['extra_in_build_not_on_page'] for r in recs
                                                     if r['students']['page_status'] == 'audited')),
        papers=dict(page_status=dict(p_page), listed=sum(r['papers']['listed'] for r in recs),
                    in_window=sum(r['papers']['in_window_2016_2026'] for r in recs),
                    matched_in_lab_papers=sum(r['papers']['matched_in_lab_papers'] for r in recs),
                    missing_by_reason=dict(p_miss), genuinely_missing=p_miss.get('genuinely_missing', 0),
                    proposed_additions=len(pap_adds)),
    )


_DEC = {}


def ctx_decisions(school):
    if school not in _DEC:
        _DEC[school] = SD.load(school)
    return _DEC[school]


def onboarding(school):
    import school_config
    try:
        return school_config.get(school).get('status') == 'onboarding'
    except KeyError:
        return False


def cmd_audit_chunk(school, i, n, out, only_pi=None):
    """Chunk i of n of the offline audit (the full run exceeds a 59 min Slurm job, CMU 2026-11-11): every n-th PI from i, -> <out>/chunk-<i>of<n>.json.
    Resumable: an existing chunk file is kept. `audit-merge` assembles the chunks and writes the outputs exactly as `audit` does."""
    f = Path(out) / (f'chunk-pi-{re.sub(r"[^a-z0-9]+", "-", only_pi[0].lower())}.json' if only_pi else f'chunk-{i}of{n}.json')
    if f.exists():
        return print('kept', f)
    kit = Kit(school)
    ctx = load_ctx(school, kit)
    import signal
    import time
    disc, verdicts = read_discovery(school), recover_verdicts(school)
    limit = int(os.environ.get('LABPAGE_PI_TIMEOUT', '0'))   # seconds per PI (0: none); a PI that exceeds it is listed in the chunk's `timeouts`, never silently dropped

    def _alarm(*_):
        raise TimeoutError('per-PI limit')
    recs, stu_adds, pap_adds, timeouts = [], [], [], []
    for p in ([q for q in ctx['pis'] if q['pi'] in only_pi] if only_pi else ctx['pis'][i::n]):
        t0 = time.time()
        if limit:
            signal.signal(signal.SIGALRM, _alarm); signal.alarm(limit)
        try:
            r, s_, p_, _ = assemble(kit, ctx, disc, verdicts, only=[p])
            recs += r; stu_adds += s_; pap_adds += p_
        except TimeoutError:
            timeouts.append(p['pi'])
        finally:
            signal.alarm(0)
        print(f"{p['pi']}: {time.time() - t0:.0f}s", flush=True)
    Path(out).mkdir(parents=True, exist_ok=True)
    f.with_suffix('.tmp').write_text(json.dumps([recs, stu_adds, pap_adds, timeouts], ensure_ascii=False))
    os.replace(f.with_suffix('.tmp'), f)


def cmd_audit_merge(school, n, out):
    kit = Kit(school)
    ctx = load_ctx(school, kit)
    order = {p['pi']: k for k, p in enumerate(ctx['pis'])}
    recs, stu_adds, pap_adds, late = [], [], [], []
    for i in range(n):
        r, s_, p_, *t_ = json.loads((Path(out) / f'chunk-{i}of{n}.json').read_text())   # chunks written before the per-PI limit have no timeouts list
        t_ = t_[0] if t_ else []
        recs += r; stu_adds += s_; pap_adds += p_; late += t_
    recs.sort(key=lambda r: order[r['pi']])
    for f_ in sorted(Path(out).glob('chunk-pi-*.json')):   # single-PI re-runs of timed-out PIs
        r, s_, p_, *_t = json.loads(f_.read_text())
        recs += r; stu_adds += s_; pap_adds += p_; late = [x for x in late if x not in {q['pi'] for q in r}]
    assert not late, f'PIs that exceeded the per-PI limit (re-run them): {late}'
    assert len(recs) == len(order), (len(recs), len(order))
    write_audit(school, recs, stu_adds, pap_adds)


def cmd_audit(school):
    if SCHOOLS[school].get('read_only'):
        sys.exit(f'{school}: read-only audit from its own outputs is not implemented yet')
    kit = Kit(school)
    ctx = load_ctx(school, kit)
    disc = read_discovery(school)
    verdicts = recover_verdicts(school)
    recs, stu_adds, pap_adds, _ = assemble(kit, ctx, disc, verdicts)
    write_audit(school, recs, stu_adds, pap_adds)


DEGREE_SENTENCE = re.compile(r'\b(?:received|obtained|earned|holds|graduated with)\b[^.]{0,50}\b(?:B\.?\s?S\.?|M\.?\s?S\.?|Ph\.?\s?D\.?|Bachelor|Master|degree)', re.I)


HEADING_ROLE_RX = re.compile(r"\b(Ph\.?\s?D\.?\s+Students?|Graduate\s+Students?|Doctoral\s+Students?|Research\s+Associates|Research\s+Assistants|Visiting\s+Students?|Post-?docs?|Postdoctoral\s+\w+|Master\w*\s+Students?|Undergraduates?|Alumni|Research\s+Fellows|Interns?)\b", re.I)


def withhold_heading_conflict(kit, school, r):
    """A role read from a PhD section heading while the nearest role heading before the name is another one (a 'Research Associates / Visiting
    Students' sub-heading inside the member list, NTU round 3): the role is withheld (a lab member of undetermined role)."""
    if r.get('role') != 'phd' or r.get('role_basis') != 'section_heading':
        return r
    try:
        t = kit.lpev.text(school, r.get('capture_url') or r['sha256'])
    except (KeyError, ValueError):
        return r
    j = t.find(r.get('quote') or '')
    k = t.find((r.get('name') or ' ').split()[0], j) if j >= 0 else -1
    if k < 0:
        return r
    m = list(HEADING_ROLE_RX.finditer(t[max(0, k - 1200): k]))
    if m and re.match(r'(?:research\s+(?:associates|assistants|fellows)|visiting\s+students?|interns?)\b', m[-1].group(1), re.I):
        return dict(r, role=None, role_basis='withheld_heading_conflict')
    return r


def withhold_bio_degree_role(r):
    """R-LAB-05 (Georgia Tech round 2): (a) in a page of member bios ('X received the B.S. ...') the role was read from the first degree sentence (a PhD student read as an
    undergraduate, a postdoc as a PhD): withheld (a lab member) unless the entry's own text says student, candidate or joined; (b) a degree suffix glued to the name by a
    table cell ('Danielle Generous MS', 'Rahul Tauro-Padival BS') is cut from the name; (c) a role whose quote does not hold the person's family name was read from a
    neighbour's cell: withheld."""
    q = r.get('quote') or ''
    nm = re.sub(r'\s+(?:MS|BS|MSc|BSc|M\.S\.|B\.S\.|PhD|Ph\.D\.)$', '', r.get('name') or '').strip()
    if nm != r.get('name'):
        r = dict(r, name=nm)
    fam = fold(nm.split()[-1]) if nm else ''
    if r.get('role') and ((DEGREE_SENTENCE.search(q) and not re.search(r'student|candidate|joined|postdoc', q, re.I)) or (fam and fam not in fold(q))):
        r = dict(r, role=None, role_basis='withheld_bio_degree_sentence')
    return r


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


def recorded_hand_review(existing):
    """The hand_review_* lists of an existing additions file: {(pi, name): decision}. A 'rejected' or 'held' row must not be proposed again and a
    'role_withheld' row keeps its null role (Harvard 2026-11-10: the generator re-proposed nine hand-rejected rows and restored six wrong roles)."""
    out = {}
    for k, rows in (existing or {}).items():
        if k.startswith('hand_review') and isinstance(rows, list):
            for r in rows:
                if isinstance(r, dict) and r.get('pi') and r.get('name') and r.get('decision') in ('rejected', 'held', 'role_withheld'):
                    out[(r['pi'], r['name'])] = r['decision']
    return out


def apply_hand_review(rows, decisions):
    kept = []
    for r in rows:
        d = decisions.get((r.get('pi'), r.get('name')))
        if d in ('rejected', 'held'):
            continue
        if d == 'role_withheld' and r.get('role'):
            r = dict(r, role=None, role_basis='withheld_hand_check_20261110')
        kept.append(r)
    return kept


def write_audit(school, recs, stu_adds, pap_adds):
    fix_titles_from_arxiv(pap_adds)
    out = P.data('labpage-audit.jsonl.gz', school)
    with gzip.open(str(out) + '.tmp', 'wt', encoding='utf-8') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    os.replace(str(out) + '.tmp', out)
    kit_w = Kit(school)
    summ = school_summary(recs, stu_adds, pap_adds)
    prev_f = P.data('labpage-additions.json', school)
    prev = read(prev_f) if prev_f.exists() else {}
    decided = recorded_hand_review(prev)
    adds = dict(school=school, generated_at=now(), tool='tools/labpage_audit.py', standard='docs/LAB-PAGES.md',
                status='proposed, unreviewed: not read by tools/pi_hierarchy.py until wired (docs/LAB-PAGES.md, integration)',
                rules={'LP-STU-01': RULE_TEXT['LP-STU-01'], 'LP-PAP-01': RULE_TEXT['LP-PAP-01']},
                students=apply_hand_review([withhold_bio_degree_role(withhold_heading_conflict(kit_w, school, r)) for r in withheld_if_membership_only(school, stu_adds)], decided), papers=pap_adds)
    for k, v in (prev or {}).items():   # recorded hand reviews survive a regeneration
        if k.startswith('hand_review'):
            adds[k] = v
    json.dump(adds, open(P.data_w('labpage-additions.json', school), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    if onboarding(school):
        # an onboarding school's summary stays in its own file: hierarchy/labpage-audit-summary.json and LABPAGE-AUDIT.md are TRACKED shared build
        # files that only the release rebuild writes (a stage-3 job rewrote them and blocked the release freeze: UChicago PROTOCOL-FRICTION 30)
        json.dump(dict(summ, audited_at=now()), open(P.data_w('labpage-audit-summary-school.json', school), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    else:
        sp = P.data('labpage-audit-summary.json')
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
    L += ['', '## Students listed on lab pages', '',
          '`removed by strict rule`: proposals the 2026-10-31 rule (undated names in older labs need an explicit current marker) removed.', '',
          '| school | listed | current | alumni | in build | missing (reason: n) | genuinely missing | proposed | removed by strict rule |',
          '|---|---:|---:|---:|---:|---|---:|---:|---:|']
    for s in order:
        x = allsum[s]['students']
        rs = ', '.join(f'{k} {v}' for k, v in sorted(x['missing_by_reason'].items(), key=lambda kv: -kv[1]) if k != 'genuinely_missing')
        L.append(f"| {s} | {x['listed']} | {x['listed_current']} | {x['listed_alumni']} | {x['matched_in_build']} | {rs} | "
                 f"{x['genuinely_missing']} | {x['proposed_additions']} | {x.get('removed_by_strict_current_rule', '-')} |")
    L += ['', '## Papers listed on lab pages', '', '| school | listed | 2016-2026 | lab papers | missing (reason: n) | genuinely missing | proposed |',
          '|---|---:|---:|---:|---|---:|---:|']
    for s in order:
        x = allsum[s]['papers']
        rs = ', '.join(f'{k} {v}' for k, v in sorted(x['missing_by_reason'].items(), key=lambda kv: -kv[1]) if k != 'genuinely_missing')
        L.append(f"| {s} | {x['listed']} | {x['in_window']} | {x['matched_in_lab_papers']} | {rs} | {x['genuinely_missing']} | {x['proposed_additions']} |")
    L += ['', '## Hand-check rounds (acceptance bar: docs/LAB-PAGES.md)', '',
          '| school | round | date | students | membership errors (doubtful = 0.5) | role/year errors | papers | paper errors | result | what changed |',
          '|---|---:|---|---:|---:|---:|---:|---:|---|---|']
    for s_ in order:
        hp = P.data('labpage-handcheck.json', s_)
        if not hp.exists():
            continue
        for k in read(hp).get('rounds') or []:
            st, pa = k.get('students') or {}, k.get('papers') or {}
            L.append(f"| {s_} | {k.get('round')} | {k.get('date')} | {st.get('sampled', '')} | {k.get('membership_score')} | "
                     f"{k.get('role_year_errors')} | {pa.get('sampled', '-')} | {'-' if k.get('paper_score') is None else k['paper_score']} | "
                     f"{k.get('result')} | {str(k.get('label') or '')[:70]} |")
    ext = []
    for s_ in order:
        ap_ = P.data('labpage-acceptance.json', s_)
        if ap_.exists() and read(ap_).get('round_limit_extended_by_owner'):
            ext.append(s_)
    if ext:
        L += ['', f"Round-limit exception (owner, 2026-11-01): {', '.join(ext)} students get rounds 4 and 5 with repairs in place "
                  "(`round_limit_extended_by_owner: 5` in the acceptance file); after round 5 the work stops. Princeton is not included."]
    open(P.data_w('LABPAGE-AUDIT.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')


def cmd_summary():
    sp = P.data('labpage-audit-summary.json')
    write_md(read(sp) if sp.exists() else {})


def cmd_sample(school, kind, n, seed):
    """A random sample of proposed additions with the page text around each quote (students) or the identity, school and
    appointment evidence (papers), for a hand-check round (docs/LAB-PAGES.md, acceptance bar). The seed makes it
    reproducible; every round uses a new seed."""
    import random
    rows = read(P.data('labpage-additions.json', school))[kind]
    random.seed(seed)
    sample = random.sample(rows, min(n, len(rows)))
    kit = Kit(school) if kind == 'students' else None
    for i, r in enumerate(sample, 1):
        if kind == 'students':
            src = r.get('capture_url') or r['sha256']
            try:
                t = kit.lpev.text(school, src)
            except (KeyError, ValueError):
                t = ''
            j = t.find(r['quote'])
            e_ = j + len(r['quote'])   # the name ends the quote: centre the window there (Stanford round 7: a long quote pushed the name out of the 650 printed characters)
            ctx = t[max(0, e_ - 450): e_ + 200] if j >= 0 else '(quote not found)'
            print(f"[{i}] {r['pi']} | {r['name']} | role={r.get('role')} ({r.get('role_basis')}) years={r.get('years')} "
                  f"({r.get('years_basis')}) alumni={r.get('alumni')} pi_from={r.get('pi_first_year')} | {src[:110]}")
            print('     CTX:', ctx.replace('\n', ' ')[:650])
        else:
            ev = r.get('evidence') or {}
            print(f"[{i}] {r['pi']} | {str(r.get('title'))[:110]} ({r.get('title_basis') or 'listed'}) | {r.get('year')} | doi={r.get('doi')}")
            print('     basis:', ev.get('basis'), ev.get('step'), '| via:', str(ev.get('school_via') or ev.get('quotes') or '')[:170],
                  '| app:', ev.get('appointment'))
            lp = ev.get('labpage') or {}
            print('     listed:', str(lp.get('listed_title'))[:110], lp.get('listed_year'), lp.get('url'))

# ---------------------------------------------------------------- membership-only students (2026-11-01, coordinator)
def withhold_roles(rows, years=False):
    """Students wired membership-only: a final round passed on membership but failed on role/year (docs/LAB-PAGES.md). The role
    (and, when the year check failed too, the years) are withheld: null, with a `role_basis` / `years_basis` saying why."""
    out = []
    for r in rows:
        r = dict(r)
        r['role'], r['role_basis'] = None, 'withheld_role_round_failed'
        if years:
            r['years'], r['years_basis'] = None, 'withheld_role_round_failed'
        out.append(r)
    return out


def withheld_if_membership_only(school, rows):
    ap = P.data('labpage-acceptance.json', school)
    if not ap.exists():
        return rows
    k = (json.loads(ap.read_text(encoding='utf-8')).get('students') or {})
    if k.get('accepted') and k.get('scope') == 'membership_only':
        return withhold_roles(rows, years=bool(k.get('years_withheld')))
    return rows


def membership_only(school, decision, root=None):
    """Wire a school's students membership-only: withhold roles in the additions file, record the scope in the acceptance, and
    stamp the new sha256. `decision` carries round, seed, sampled and the error breakdown."""
    d = Path(root) if root else P.SchoolDir(school)
    ap, add = d / 'labpage-acceptance.json', d / 'labpage-additions.json'
    acc = json.loads(ap.read_text(encoding='utf-8'))
    adds = json.loads(add.read_text(encoding='utf-8'))
    adds['students'] = withhold_roles(adds['students'], years=bool(decision.get('years_withheld')))
    raw = (json.dumps(adds, indent=1, ensure_ascii=False)).encode('utf-8')
    add.write_bytes(raw)
    acc['students'] = dict(accepted=True, scope='membership_only', counts=dict(proposed=len(adds['students'])), **decision)
    acc.update(additions_sha256=hashlib.sha256(raw).hexdigest(), additions_generated_at=adds.get('generated_at'))
    ap.write_text(json.dumps(acc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    return acc['students']


# ---------------------------------------------------------------- restamp (2026-10-31, coordinator)
def additions_keys(rows, kind):
    """{stable key: the fields that matter} of one kind of additions: students (pi, name) -> role, years; papers (pi, work
    key) -> title, year, doi."""
    out = {}
    for r in rows:
        if kind == 'students':
            out[(r['pi'], names_fold(r['name']))] = (r.get('role'), json.dumps(r.get('years')))
        else:
            out[(r['pi'], r.get('key') or r.get('doi') or norm_title_key(r.get('title')))] = (r.get('title'), r.get('year'), r.get('doi'))
    return out


def names_fold(n):
    import unicodedata
    return re.sub(r'\s+', ' ', ''.join(c for c in unicodedata.normalize('NFKD', str(n)) if not unicodedata.combining(c))).strip().lower()


def norm_title_key(t):
    return re.sub(r'[^a-z0-9]+', ' ', str(t or '').lower()).strip()


def compare_additions(old, new, kind):
    """(removed, added, changed) between the accepted additions and the regenerated ones, by stable key."""
    a, b = additions_keys(old.get(kind) or [], kind), additions_keys(new.get(kind) or [], kind)
    removed = sorted(k for k in a if k not in b)
    added = sorted(k for k in b if k not in a)
    changed = sorted(k for k in a if k in b and a[k] != b[k])
    return removed, added, changed


def find_accepted_file(add_path, sha, repo=None):
    """The additions file with this sha256: the working copy, else the newest git revision of it that hashes to it."""
    import subprocess
    add_path = Path(add_path)
    if hashlib.sha256(add_path.read_bytes()).hexdigest() == sha:
        return json.loads(add_path.read_text(encoding='utf-8'))
    repo = Path(repo or P.CODE)
    rel = str(add_path.resolve().relative_to(repo.resolve()))
    revs = subprocess.run(['git', '-C', str(repo), 'log', '--format=%H', '--', rel], capture_output=True, text=True).stdout.split()
    for h_ in revs:
        blob = subprocess.run(['git', '-C', str(repo), 'show', f'{h_}:{rel}'], capture_output=True).stdout
        if blob and hashlib.sha256(blob).hexdigest() == sha:
            return json.loads(blob.decode('utf-8'))
    return None


def restamp(school, root=None, repo=None, old=None, apply=True):
    """After the additions were regenerated, keep an acceptance valid only when it still describes the file: for every accepted
    kind compare the accepted set with the new one by stable key. A subset with the same fields (rows removed by existing
    rules) is re-stamped with the new sha256 and `restamped_from`; a kind with an added or changed row loses `accepted` (it
    needs a fresh hand-check round). Returns the report."""
    d = Path(root) if root else P.SchoolDir(school)
    ap, add = d / 'labpage-acceptance.json', d / 'labpage-additions.json'
    if not ap.exists():
        return dict(school=school, status='no_acceptance')
    acc = json.loads(ap.read_text(encoding='utf-8'))
    raw = add.read_bytes()
    new_sha = hashlib.sha256(raw).hexdigest()
    if new_sha == acc.get('additions_sha256'):
        return dict(school=school, status='current')
    new = json.loads(raw.decode('utf-8'))
    prev = old if old is not None else find_accepted_file(add, acc.get('additions_sha256'), repo)
    if prev is None:
        return dict(school=school, status='accepted_file_not_found', old_sha=acc.get('additions_sha256'))
    rep = dict(school=school, status='restamped', kinds={})
    for kind in ('students', 'papers'):
        k = acc.get(kind) or {}
        if not k.get('accepted'):
            continue
        rem, addd, chg = compare_additions(prev, new, kind)
        info = dict(removed=len(rem), added=len(addd), changed=len(chg), proposed=len(new.get(kind) or []))
        if addd or chg:
            info['result'] = 'needs_new_round'
            k.update(accepted=False, reason=f"rows added ({len(addd)}) or changed ({len(chg)}) since round {k.get('round')}: "
                     f"a fresh hand-check round is needed", restamped_from=dict(sha256=acc.get('additions_sha256'), added=len(addd), changed=len(chg)))
        else:
            info['result'] = 'subset'
            k['restamped_from'] = dict(sha256=acc.get('additions_sha256'), generated_at=acc.get('additions_generated_at'),
                                       removed=len(rem), reason='rows removed by existing rules on regeneration '
                                       '(appointment periods R-PAP-01/03, strict current rule); no row added or changed')
            k['counts'] = dict(k.get('counts') or {}, proposed=len(new.get(kind) or []))
        acc[kind] = k
        rep['kinds'][kind] = info
    acc.update(additions_sha256=new_sha, additions_generated_at=new.get('generated_at'))
    if apply:
        ap.write_text(json.dumps(acc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    return rep


def record_round(spec):
    """Record one hand-check round (docs/LAB-PAGES.md, acceptance bar) in the school's labpage-handcheck.json, and, when the spec
    carries `acceptance` ({kind: decision}), in labpage-acceptance.json stamped with the current additions file's sha256.
    spec: school, round, label, result, membership_score, paper_score, students / papers (sampled, seed, errors, items...)."""
    school = spec['school']
    hp, ap, add = P.data_w('labpage-handcheck.json', school), P.data_w('labpage-acceptance.json', school), P.data('labpage-additions.json', school)
    d = json.loads(hp.read_text(encoding='utf-8')) if hp.exists() else {'school': school, 'bar': 'docs/LAB-PAGES.md, acceptance bar (2026-10-31)', 'rounds': []}
    raw = add.read_bytes()
    a = json.loads(raw.decode('utf-8'))
    st, pa = spec.get('students'), spec.get('papers')
    rnd = {'round': spec['round'], 'date': spec.get('date') or TODAY, 'label': spec['label'], 'additions_generated_at': a['generated_at'],
           'students': st and {k: v for k, v in st.items() if k != 'items'}, 'papers': pa and {k: v for k, v in pa.items() if k != 'items'},
           'items': {**(st or {}).get('items', {}), **{('papers_' + k if k != 'papers' else 'papers'): v for k, v in (pa or {}).get('items', {}).items()}},
           'membership_score': spec.get('membership_score'), 'role_year_errors': (st or {}).get('role_or_year_errors'),
           'paper_score': spec.get('paper_score'), 'result': spec['result']}
    if spec.get('note'):
        rnd['note'] = spec['note']
    d['rounds'] = [r for r in d['rounds'] if r['round'] != spec['round']] + [rnd]
    hp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    if spec.get('acceptance'):
        acc = json.loads(ap.read_text(encoding='utf-8')) if ap.exists() else {}
        acc.update({'school': school, 'decided_at': spec.get('date') or TODAY, 'bar': 'docs/LAB-PAGES.md, acceptance bar',
                    'additions_file': str(add.relative_to(P.CODE)), 'additions_generated_at': a['generated_at'],
                    'additions_sha256': hashlib.sha256(raw).hexdigest()})
        acc.update(spec['acceptance'])
        ap.write_text(json.dumps(acc, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    return rnd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['discover', 'recover', 'audit', 'audit-chunk', 'audit-merge', 'recover-audit', 'all', 'summary', 'sample', 'restamp', 'record'])
    ap.add_argument('--kind', choices=['students', 'papers'], default='students')
    ap.add_argument('--n', type=int, default=20)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('school', nargs='?')
    ap.add_argument('--pi', nargs='*')
    ap.add_argument('--chunk', type=int, default=0)
    ap.add_argument('--of', type=int, default=1)
    ap.add_argument('--out', default=None)
    ap.add_argument('--redo', action='store_true')
    ap.add_argument('--live-first', action='store_true', help='Live discovery with cached-only Wayback; uncached archive requests remain pending')
    ap.add_argument('--redo-unrecorded', action='store_true', help='discover again every lab the 2026-10-22 pass did not record')
    ap.add_argument('--title-credits', type=int, default=600)
    a = ap.parse_args()
    if a.live_first:
        os.environ['CS_ATLAS_LABPAGE_LIVE_ONLY'] = '1'
    if a.cmd in ('recover', 'recover-audit', 'all'):  # where a stalled run waits (2026-10-31: Princeton and MIT stalled twice)
        import faulthandler
        faulthandler.dump_traceback_later(900, repeat=True)
    if a.cmd in ('discover', 'all'):
        cmd_discover(a.school, a.pi, a.redo, a.redo_unrecorded)
    if a.cmd == 'recover':
        cmd_recover(a.school, a.title_credits)
    if a.cmd in ('recover-audit', 'all'):
        cmd_recover_audit(a.school, a.title_credits)
    if a.cmd == 'audit':
        cmd_audit(a.school)
    if a.cmd == 'audit-chunk':
        cmd_audit_chunk(a.school, a.chunk, a.of, a.out, a.pi)
    if a.cmd == 'audit-merge':
        cmd_audit_merge(a.school, a.of, a.out)
    if a.cmd == 'sample':
        cmd_sample(a.school, a.kind, a.n, a.seed)
    if a.cmd == 'summary':
        cmd_summary()
    if a.cmd == 'record':
        print(record_round(json.load(open(a.school)))['result'])  # school = the spec file path
    if a.cmd == 'restamp':
        for s_ in ([a.school] if a.school else list(SCHOOLS)):
            print(json.dumps(restamp(s_), ensure_ascii=False))


if __name__ == '__main__':
    main()
