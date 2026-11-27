"""Consolidate the lab-page audit into a per-PI website register.

A URL is not complete coverage unless it is this school's lab/home page and has
capture provenance. Unsearched PIs and incomplete evidence remain pending.
Outputs are generated audit records, not reviewed student admission evidence.
"""
import argparse
import gzip
import json
import re
import sqlite3
import sys
import unicodedata
import zlib
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import atlas_paths as P

FOUND_RESULTS = ('ok', 'ok_wayback', 'does_not_name_pi_kept_strong_source')
WEBSITE_REASONS = ('lab_site', 'pi_homepage_only_no_lab_site')
OFFICIAL_LINK_SOURCES = ('school_profile_link', 'department_listing_link', 'official_link_chain', 'web_search_reviewed')
# owner ruling 2026-11-11: a web-search-found personal or lab site counts as the lab page when the page itself names the PI at the school
# (a distinctive tie): a `web_search_reviewed` check carries the live fetch (sha256, date), the verbatim name and school-tie quotes and the reviewer
RESEARCH_OUTPUT_PATH = re.compile(r'/(?:publications?|papers?|reports?)(?:/|\.|$)|/(?:news|blog)/[12][0-9]{3}(?:/|$)|/articles?/[^/]+', re.I)   # an article about the PI (vice.com/en/article/..., UW 2026-11-22) is press, not a site
INSTITUTIONAL_PROFILE_HOST = re.compile(r'(?:^|\.)(?:researchportal|facultyprofiles)\.[a-z0-9.-]*hk$', re.I)
INSTITUTIONAL_ROOT = re.compile(r'^(?:www\.)?(?:hkust\.edu\.hk|ust\.hk|hkust-gz\.edu\.cn)$', re.I)
IDENTITY_INDEX_HOST = re.compile(r'(?:^|\.)(?:orcid\.org|dblp\.org|openalex\.org|researchgate\.net|scholar\.google\.[a-z.]+)$', re.I)
LINKED_NOT_FETCHED = 'official_link_not_fetched_robots'   # linked by an official profile; the host's robots.txt gives no permission, so the site is recorded by URL only and never fetched
ABSENCE_REASONS = {
    'profile_only_no_homepage', 'no_web_presence_found', 'site_dead_no_wayback',
    'host_blocked_by_robots', 'host_access_blocked', 'host_challenge_no_wayback', 'pi_left_school_site_moved',
    'site_at_other_institution', 'new_arrival_no_site_yet', 'emeritus_or_admin_no_lab',
    'site_retired_archive_redirect',   # 2026-11-15 (EPFL): the profile links a host whose robots.txt answers 302 to the school's own archive host; the host is retired, nothing is read from the archive
}



def capture_body_view(content):
    """Decode storage zlib and an HTTP gzip envelope for reading, keeping source hashes unchanged.

    Captures retain the original HTTP bytes and their SHA. A malformed gzip body
    is unreadable evidence; it must not certify a page name or an outbound link.
    """
    if not isinstance(content, (bytes, bytearray)):
        return content
    try:
        content = zlib.decompress(content)
    except zlib.error:
        pass
    if content.startswith(b'\x1f\x8b'):
        try:
            return gzip.decompress(content)
        except (OSError, EOFError, zlib.error):
            return b''
    return content


def how_found(lp):
    """Keep the actual discovery source and source-page URL, without guessing."""
    url = (lp.get('urls') or {}).get('lab_site')
    for c in lp.get('checks') or []:
        if c.get('source') == 'candidate_site' and c.get('url') == url and c.get('result') in FOUND_RESULTS:
            via = c.get('via')
            on = next((x.get('on') for x in lp['checks'] if x.get('source') == via and x.get('url') == url and x.get('on')), None)
            return via, on, c
    return lp.get('source'), None, None


def dated_checks(checks):
    """A schema note or empty list is not evidence that a website was searched."""
    return [c for c in checks if c.get('url') and c.get('at') and c.get('result')
            and c.get('source') != 'openalex_author']


def selection_gaps(url):
    """Obvious non-homepage selections; personal/group people pages remain eligible."""
    parsed = urlsplit(url)
    gaps = []
    if re.match(r'^profiles?\.', parsed.hostname or '') or IDENTITY_INDEX_HOST.search(parsed.hostname or '') or INSTITUTIONAL_PROFILE_HOST.search(parsed.hostname or ''):
        gaps.append('selected_url_is_profile_card')
    if INSTITUTIONAL_ROOT.match(parsed.hostname or '') and not [x for x in parsed.path.split('/') if x]:
        gaps.append('selected_url_is_profile_card')   # a university's own front page is not a person's or lab's website
    import labpage_audit as _LA
    if _LA.charter_profile_page(url) and 'selected_url_is_profile_card' not in gaps:
        gaps.append('selected_url_is_profile_card')   # the charter's [web].profile_pages (set_profile_pages)
    if RESEARCH_OUTPUT_PATH.search(parsed.path):
        gaps.append('selected_url_is_research_output')
    if re.search(r'\.(?:pdf|ps|docx?)$', parsed.path, re.I):
        gaps.append('selected_url_is_document')
    if re.match(r'^(?:webdev|forms?|feedback|survey)\.', parsed.hostname or '', re.I) or re.search(r'/(?:feedback|contact-us|report-a-problem)(?:/|$)', parsed.path, re.I):
        gaps.append('selected_url_is_feedback_form')   # 2026-11-15: GT Biggs was given webdev.iac.gatech.edu/feedback as her website
    return gaps


TIE_SOURCES = set()      # charter [labpages].official_tie_sources: discovery sources whose listing of the site counts as the official tie (CUHK D-0079)
NAME_WAIVER = [False]    # charter [labpages].official_link_site_needs_no_name: a site the PI's own official profile links stays even if its page never names the PI (CUHK D-0078)


def set_tie_policy(school):
    """Read the school's tie policy from its charter (owner rulings per school: CUHK D-0078 / D-0079). No charter or no keys: the default rules."""
    TIE_SOURCES.clear()
    NAME_WAIVER[0] = False
    try:
        import school_config as SC
        cfg = SC.get(school)
        TIE_SOURCES.update(SC.field(cfg, 'labpages.official_tie_sources') or [])
        NAME_WAIVER[0] = bool(SC.field(cfg, 'labpages.official_link_site_needs_no_name'))
    except Exception:  # noqa: BLE001 (a fixture: no charter)
        pass


def official_check(check, url):
    if check.get('source') in TIE_SOURCES:
        # the PI's own DBLP person record or ORCID researcher-urls list this exact site (owner ruling per school; the site is still checked to be the person's own)
        return check.get('result') == 'listed' and bool(check.get('at')) and any(normalized_link(u) == normalized_link(url) for u in check.get('urls') or [])
    if check.get('source') == 'web_search_reviewed':
        return bool(check.get('url') == url and check.get('at') and re.fullmatch(r'[a-fA-F0-9]{64}', check.get('sha256') or '')
                    and (check.get('tie_quote') or '').strip() and (check.get('name_quote') or '').strip() and check.get('reviewer'))
    if check.get('source') not in OFFICIAL_LINK_SOURCES or normalized_link(check.get('url')) != normalized_link(url) or not check.get('on'):
        return False
    if check['source'] != 'official_link_chain':
        return True
    chain = check.get('provenance_chain') or []
    if len(chain) != 2 or chain[0].get('source_url') != check['on'] or normalized_link(chain[-1].get('url')) != normalized_link(url):
        return False
    if normalized_link(chain[0].get('url')) != normalized_link(chain[1].get('source_url')):
        return False
    return all(c.get('href') and c.get('source_fetched_at') and re.fullmatch(r'[a-fA-F0-9]{64}', c.get('source_sha256') or '') for c in chain)


def official_absence_check(check, url):
    """The reviewed 'no official page links it' record (`official_link_status: absent_reviewed`): the tool read the PI's own official page(s) (each dated, with its
    capture hash) and none links the site, which was found elsewhere (DBLP/ORCID/search). Never made without at least one readable official page."""
    pages = check.get('pages_read') or []
    return bool(check.get('source') == 'official_link_absent_reviewed' and normalized_link(check.get('url')) == normalized_link(url) and check.get('at')
                and (check.get('reason') or '').strip() and pages
                and all(pg.get('url') and pg.get('at') and re.fullmatch(r'[a-fA-F0-9]{64}', pg.get('sha256') or '') for pg in pages))


SPACE_HOST = re.compile(r'^(?:staff|faculty|jszy)\.[a-z0-9-]+\.edu\.cn$', re.I)


def space_root(url, root_only=False):
    """(host, user) of a university faculty-space address (staff.ustc.edu.cn/~x/, faculty.ustc.edu.cn/x/, jszy.whu.edu.cn/x/). With root_only, None unless the
    address IS the space root (the user segment alone, or its zh_CN/en home: /x/zh_CN/index.htm)."""
    p = urlsplit(url or '')
    segs = [x for x in p.path.split('/') if x]
    if not SPACE_HOST.match(p.hostname or '') or not segs:
        return None
    if root_only and not (len(segs) == 1 or (segs[1].lower() in ('zh_cn', 'en') and (len(segs) == 2 or (len(segs) == 3 and segs[2].lower() in ('index.htm', 'index.html'))))):
        return None
    return (p.hostname.lower(), segs[0].lstrip('~').lower())


def same_site_by_root(linked, registered):
    """An official link to a faculty-space ROOT confirms a registered page under that root (owner 2026-11-25)."""
    root = space_root(linked, root_only=True)
    return bool(root and root == space_root(registered))


def entry(rec):
    lp = rec.get('lab_page') or {}
    urls, ev = lp.get('urls') or {}, lp.get('evidence') or {}
    checks = lp.get('checks') or []
    dated = dated_checks(checks)
    out = dict(pi=rec['pi'], status=lp.get('status'), reason_code=lp.get('reason_code'),
               reason=lp.get('reason'), audited_at=rec.get('audited_at'), checks=checks,
               places_checked=sorted({f"{c.get('source')}:{c.get('result')}" for c in dated}),
               checked_at=max((c['at'] for c in dated), default=None),
               students_page_status=(rec.get('students') or {}).get('page_status'),
               papers_page_status=(rec.get('papers') or {}).get('pubs_page_status'))
    gaps = []
    if rec.get('website_review_needed'):
        gaps.append('rejected_candidate_requires_search')
        out['review_note'] = rec['website_review_needed']
    if not dated:
        gaps.append('no_dated_source_check')
    if urls.get('lab_site'):
        via, on, chk = how_found(lp)
        out.update(url=urls['lab_site'], kind=('lab_site' if lp.get('reason_code') == 'lab_site' else 'pi_homepage'),
                   people_page=urls.get('people_page'), alumni_page=urls.get('alumni_page'),
                   pubs_page=urls.get('pubs_page'), found_via=via, listed_on=on,
                   sha256=ev.get('sha256') or (chk or {}).get('sha256'), evidence=ev)
        if lp.get('reason_code') in WEBSITE_REASONS:
            gaps.extend(selection_gaps(urls['lab_site']))
            if not re.fullmatch(r'[a-fA-F0-9]{64}', out.get('sha256') or ''):
                gaps.append('page_capture_hash_missing')
            if not via:
                gaps.append('discovery_source_missing')
            # An index is a useful lead, but does not establish the official link
            # required by the top-25 brief. Keep this visible for follow-up.
            official = [c for c in checks if official_check(c, urls['lab_site'])]
            out['official_link_status'] = 'recorded' if official else 'not_recorded'
            out['official_link_evidence'] = official
            out['coverage'] = 'pending' if gaps else 'website'
        else:
            out['kind'] = 'other_institution_site'
            out['coverage'] = 'pending' if gaps or not out['reason'] or lp.get('reason_code') not in ABSENCE_REASONS else 'reason'
    elif lp.get('reason_code') in ABSENCE_REASONS and out['reason'] and dated:
        out['coverage'] = 'reason'
    else:
        gaps.append('absence_reason_not_supported')
        out['coverage'] = 'pending'
    out['upstream_audit_reason'] = out.get('reason')
    if out.get('coverage') == 'website':
        out['reason'] = 'Captured lab/group website.' if out.get('kind') == 'lab_site' else 'Captured PI homepage used as the lab-page fallback.'
    # Failed/deferred attempts are a reason access is incomplete, never proof a
    # site does not exist. Preserve the upstream reason, but state its scope.
    if out['coverage'] == 'reason':
        results = {c.get('result') for c in checks}
        code = out['reason_code']
        if code in ('site_at_other_institution', 'pi_left_school_site_moved') or out.get('kind') == 'other_institution_site':
            out['reason_type'] = 'other_institution'
        elif results & {'wayback_only_host', 'wayback_deferred', 'cooldown', 'http_429'}:
            out['reason_type'] = 'pending_archive'
        elif results & {'robots_disallowed', 'robots_unknown', 'unreachable', 'bot_challenge', 'off_limits', 'http_403', 'host_access_blocked'}:   # robots_unknown / unreachable: a candidate host that could not be read is an access outcome, never 'no web presence' (CUHK 2026-11-25: ee.cuhk.edu.hk times out)
            out['reason_type'] = 'access_blocked'
        elif code in ('site_dead_no_wayback', 'site_retired_archive_redirect'):
            out['reason_type'] = 'site_unavailable'
        else:
            out['reason_type'] = 'search_no_eligible_site'
        observations = '; '.join(f"{c.get('source')} {c['url']}: {c['result']}" for c in dated[:4])
        more = f'; {len(dated) - 4} further dated checks retained' if len(dated) > 4 else ''
        out['reason'] = f"No eligible website established for this school from the recorded checks ({out['reason_type']}): {observations}{more}."
        out['reason_scope'] = 'Recorded search/access outcome; not proof no website exists or that an archive has no capture.'
    if gaps:
        out['coverage'] = 'pending'
    out['evidence_gaps'] = gaps
    return out


def refresh_records(school, recs):
    """Refresh only website evidence from cached discovery; do not fetch or admit students."""
    import labpage_audit as L
    kit = L.Kit(school)
    ctx = L.load_ctx(school, kit, plan=False)
    disc = L.read_discovery(school)
    # New schools capture official profiles/landing pages through school_web.
    # Reuse those bytes; importing the cache is not a new crawl or people review.
    landing_urls = set()
    for d in disc.values():
        landing_urls.add((d.get('chosen') or {}).get('lab_site'))
        landing_urls.update(c.get('url') for c in d.get('checks') or [] if c.get('source') == 'school_profile')
    kit.import_school_web(str(P.data('school-captures.sqlite', school)), sorted(u for u in landing_urls if u))
    chrome = profile_chrome(disc)
    for p in ctx['pis']:
        if p['pi'] not in disc:
            continue
        # Discovery from older code may mistake a university profile for a lab.
        d = disc[p['pi']]
        chosen = (d.get('chosen') or {}).get('lab_site')
        review_needed = None
        invalid = lambda u: L.is_profile(u, ctx['cfg']['domain']) or selection_gaps(u) or normalized_link(u) in chrome
        if chosen and invalid(chosen):
            res = {c.get('url'): c.get('result') for c in d.get('checks') or [] if c.get('source') == 'candidate_site' and c.get('result') in FOUND_RESULTS}
            # a candidate whose page names the PI outranks one kept only for its strong source (UW Shi: the ECE 'Innovation' nav page)
            order = sorted((s for s in d.get('sites') or [] if s.get('url') in res), key=lambda s: res[s['url']] not in ('ok', 'ok_wayback'))
            replacement = next((s for s in order if not invalid(s['url'])), None)
            if replacement:
                d = dict(d, chosen={'lab_site': replacement['url'], 'other_school': replacement.get('other_school')})
            else:
                d = dict(d, chosen={})
                review_needed = 'Selected URL was an institutional profile or research output; no eligible cached alternative. Further website search required.'
            disc[p['pi']] = d
        lp, _ = L.lab_record(kit, ctx, p, disc)
        old = recs.get(p['pi']) or {}
        # A new page needs its own review; an old page's audited status cannot
        # silently transfer to a different discovery target.
        same_pages = (old.get('lab_page') or {}).get('urls') == lp.get('urls')
        recs[p['pi']] = dict(old, pi=p['pi'], lab_page=lp, audited_at=d.get('checked_at'), website_review_needed=review_needed,
                            students=(old.get('students') if same_pages else None) or {'page_status': 'pending_review'},
                            papers=(old.get('papers') if same_pages else None) or {'pubs_page_status': 'pending_review'})
    return recs


CHROME_MIN_PIS = 8


def profile_chrome(disc):
    """{normalized URL} that the official profiles of CHROME_MIN_PIS or more different PIs link: the profile template's navigation
    ('Innovation' -> ece.uw.edu/entrepreneurship/, 'University of Washington' -> www.washington.edu on every UW ECE profile), never a
    person's own link. A shared group site is linked by a handful of its PIs' profiles, far below the bar."""
    import collections
    n, hosts, per_host = collections.Counter(), collections.defaultdict(set), collections.Counter()
    for pi, d in disc.items():
        links = {(normalized_link(c.get('url')), urlsplit(c.get('on') or '').hostname or '') for c in d.get('checks') or []
                 if c.get('source') == 'school_profile_link' and c.get('url')}
        for u, h in links:
            hosts[u].add(h)
        n.update({u for u, _ in links})
        per_host.update({urlsplit(c.get('url') or '').hostname or '' for c in d.get('checks') or [] if c.get('source') == 'school_profile'})
    # chrome = on at least half of the profiles of the profile host that links it (a 10-PI theory group site linked from 10 of ~80 CSE
    # profiles is a group site; an ECE nav link sits on every ECE profile)
    return {u for u, k in n.items() if k >= CHROME_MIN_PIS and k >= 0.5 * max([per_host[h] for h in hosts[u]] or [0])}


def build(school, refresh=False):
    set_tie_policy(school)
    import labpage_audit as _LA
    _LA.set_profile_pages(school)
    with open(P.data('pis.json', school)) as f:
        pi_rows = json.load(f)
    pis = list(dict.fromkeys(p['pi'] for p in pi_rows))
    recs = {}
    audit = P.data('labpage-audit.jsonl.gz', school)
    if audit.exists():
        with gzip.open(audit, 'rt') as f:
            for line in f:
                r = json.loads(line)
                recs[r['pi']] = r
    for p in pi_rows:   # an audit record kept under a census spelling of the same person belongs to the package's canonical PI
        if p['pi'] not in recs:
            alias = next((n for n in p.get('names') or [] if n in recs and n != p['pi']), None)
            if alias:
                recs[p['pi']] = dict(recs[alias], pi=p['pi'], alias_of=alias)
    if refresh:
        recs = refresh_records(school, recs)
    labs = [entry(recs[p]) if p in recs else dict(pi=p, status='unaudited', coverage='pending',
            evidence_gaps=['audit_record_missing']) for p in pis]
    return dict(school=school, tool='tools/lab_websites.py', source='labpage-audit.jsonl.gz', pi_keys=sorted(pis),
                source_exists=audit.exists(), refreshed_from_cached_discovery=refresh, review_status='generated; student admissions require separate review', labs=labs)


def counts(doc):
    c = dict(labs=len(doc['labs']), website=0, reason=0, neither=0, official_link_not_recorded=0, pending_archive=0, access_blocked=0)
    for e in doc['labs']:
        if e.get('reason_type') in ('pending_archive', 'access_blocked'):
            c[e['reason_type']] += 1
        outcome = e.get('coverage')
        if outcome == 'linked_not_fetched':
            c['linked_not_fetched'] = c.get('linked_not_fetched', 0) + 1
            continue
        c[outcome if outcome in ('website', 'reason') else 'neither'] += 1
        if outcome == 'website' and e.get('official_link_status') not in ('recorded', 'absent_reviewed'):
            c['official_link_not_recorded'] += 1
    c['documented'] = c['neither'] == 0
    c['complete'] = c['documented'] and c['pending_archive'] == 0
    c['official_provenance_complete'] = c['complete'] and c['official_link_not_recorded'] == 0
    return c


def retained_review(row):
    r = row.get('retained_review')
    return isinstance(r, dict) and bool(r.get('reviewer')) and bool(r.get('reviewed_on')) and bool(str(r.get('why') or '').strip())


def preserve_reviewed_entries(previous, current, aliases=None):
    """A cache refresh must not undo a source-specific manual identity review.

    Changed captures or newly discovered destinations still need fresh review;
    only the identical reviewed source, or an explicit current census alias,
    can retain the earlier decision.
    """
    if previous.get('school') != current.get('school'):
        return current
    prior = {r['pi']: r for r in previous.get('labs', [])}
    for i, row in enumerate(current['labs']):
        # A row the reviewed register marks `retained_review` {reviewer, reviewed_on, why} is the reviewed decision: a cache refresh never replaces it
        # (HKUST 2026-11-25: a refresh from cached discovery undid seven accepted rows and dropped the profile-link checks of hand-verified sites).
        # The row may sit under a spelling of the same person (a census alias the package keys by its canonical name); it is carried to the canonical key.
        kept = next((prior[n] for n in [row['pi']] + list((aliases or {}).get(row['pi'], [])) if n in prior and retained_review(prior[n])), None)
        if kept is not None:
            current['labs'][i] = dict(kept, pi=row['pi'], preserved_review_on_refresh=True, **({'alias_of': kept['pi']} if kept['pi'] != row['pi'] else {}))
            continue
        old = prior.get(row['pi']) or {}
        review = old.get('classification_review') or {}
        if isinstance(review, str):
            review = {'reason': review}  # earlier reviewed school registers
        if not review and not old.get('review_note'):
            continue
        reviewed_sources = {(normalized_link(old.get('url')), old.get('sha256'))}
        source = review.get('source') or {}
        reviewed_sources.add((normalized_link(review.get('old_url')), source.get('sha256')))
        # Earlier Michigan review stored the correction's source hash in its
        # dated check, with the literal previous URL in `on`.
        for check in old.get('checks') or []:
            if check.get('source', '').startswith('reviewed_cached_') or check.get('source') == 'reviewed_capture_original_url':
                reviewed_sources.add((normalized_link(check.get('on')), check.get('source_sha256')))
        same_source = bool(row.get('sha256') and (normalized_link(row.get('url')), row['sha256']) in reviewed_sources)
        alias = review.get('reviewed_alias')
        reviewed_alias = row.get('status') == 'unaudited' and alias and alias in (aliases or {}).get(row['pi'], [])
        if same_source or reviewed_alias:
            current['labs'][i] = dict(old, preserved_review_on_refresh=True)
    return current




def normalized_link(url):
    """Compare http/https, default-port (:80/:443), doubled-slash, directory-index ('/index.shtml') and fragment variants, never different
    hosts or paths (UW 2026-11-22: the iSchool profile links 'http://vsdesign.org//index.shtml' for https://vsdesign.org/; the archived EE
    listing at www2.ee.washington.edu:80 links the profile recorded as http://www2.ee.washington.edu/...)."""
    p = urlsplit(url or '')
    try:
        port = p.port
    except ValueError:
        port = None
    host = re.sub(r'^www\.', '', (p.hostname or '').lower()) + (f':{port}' if port not in (None, 80, 443) else '')   # 'www.x.com' and 'x.com' are one site (CUHK Zhenyu Yan: the profile links www.yanzhenyu.com, DBLP lists yanzhenyu.com); other subdomains stay different
    path = re.sub(r'/{2,}', '/', p.path)
    path = re.sub(r'/index\.(?:s?html?|php)$', '/', path, flags=re.I)
    return host, path.rstrip('/'), p.query


def listing_link_context(content, base, target, pi):
    """An exact homepage link in this PI's named card, never a page-wide match."""
    from bs4 import BeautifulSoup

    def normalized_name(text):
        text = ''.join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
        return ' '.join(re.findall(r'\w+', text.casefold()))

    name = normalized_name(pi)
    parts = name.split()
    if len([p for p in parts if len(p) > 1]) < 2:
        return None  # initials need an explicit reviewed identity mapping
    names = {name, ' '.join(parts[-1:] + parts[:-1])}
    core = [p for p in parts if len(p) > 1]   # a card without the middle initial ('Otis, Brian' for Brian P. Otis, UW EE 2016 table)
    names |= {' '.join(core), ' '.join(core[-1:] + core[:-1])}
    content = capture_body_view(content)
    soup = BeautifulSoup(content, 'html.parser')
    for anchor in soup.find_all('a', href=True):
        url = urljoin(base, anchor['href'])
        url = re.sub(r'^https?://web\.archive\.org/web/[^/]+/(https?://)', r'\1', url)
        if normalized_link(url) != target:
            continue
        if normalized_name(anchor.get_text(' ', strip=True)) in names:
            return url, anchor.get_text(' ', strip=True), anchor.get_text(' ', strip=True)
        for card in list(anchor.parents)[:5]:
            if card.name in ('body', 'html', '[document]'):
                break
            text = card.get_text(' ', strip=True)
            if len(text) > 1200:
                break
            headings = card.find_all(re.compile(r'^h[1-6]$'))
            # A container with several headings can span several PI cards.
            if len(headings) == 1 and normalized_name(headings[0].get_text(' ', strip=True)) in names:
                return url, anchor.get_text(' ', strip=True), text
    return None


def literal_links(content, base):
    """Resolved destinations together with the exact href in cached HTML."""
    from bs4 import BeautifulSoup
    content = capture_body_view(content)
    for anchor in BeautifulSoup(content, 'html.parser').find_all('a', href=True):
        url = urljoin(base, anchor['href'])
        url = re.sub(r'^https?://web\.archive\.org/web/[^/]+/(https?://)', r'\1', url)
        if url.startswith(('http://', 'https://')):
            yield url, anchor.get_text(' ', strip=True), anchor['href']


def cached_profile_chain(profile, source_url, target_url, cached_page, link_base, pi=None):
    """Official profile -> named lab/home link -> selected page, all cached."""
    target = normalized_link(target_url)
    candidates = 0
    for intermediate, anchor, href in literal_links(profile['content'], link_base(profile, source_url)):
        parsed = urlsplit(intermediate)
        cross_host = parsed.hostname != urlsplit(target_url).hostname
        if selection_gaps(intermediate):
            continue
        if cross_host and (not pi or not re.search(r'personal|home.?page|web.?site|web.?page|\blab\b', anchor, re.I)):
            continue
        if parsed.hostname == urlsplit(source_url).hostname and parsed.path in ('', '/'):
            continue  # university navigation is not a PI's lab/home link
        if not re.search(r'lab|group|research|home|web', anchor, re.I):
            continue
        candidates += 1
        if candidates > 4:
            break
        page = cached_page(intermediate)
        if not page or page.get('status') != 200 or not page.get('content'):
            continue
        identity_quote = None
        if cross_host:
            from bs4 import BeautifulSoup
            content = capture_body_view(page['content'])
            tokens = re.findall(r'\w+', pi)
            if len([t for t in tokens if len(t) > 1]) < 2:
                continue
            text = BeautifulSoup(content, 'html.parser').get_text(' ', strip=True)
            match = re.search(r'(?<!\w)' + r'[\W_]+'.join(map(re.escape, tokens)) + r'(?!\w)', text, re.I)
            if not match:
                continue
            identity_quote = match.group(0)
        for dest, text, raw_href in literal_links(page['content'], link_base(page, intermediate)):
            if normalized_link(dest) != target:
                continue
            chain = [dict(source_url=source_url, url=intermediate, href=href, anchor=anchor,
                          source_sha256=profile.get('sha256'), source_fetched_at=profile.get('fetched_at'),
                          source_capture_url=profile.get('capture_url'), via='literal_html_href'),
                     dict(source_url=intermediate, url=target_url, linked_url=dest, href=raw_href, anchor=text,
                          source_sha256=page.get('sha256'), source_fetched_at=page.get('fetched_at'),
                          source_capture_url=page.get('capture_url'), via='literal_html_href')]
            check = dict(source='official_link_chain', url=target_url, on=source_url,
                         at=profile.get('fetched_at'), result='listed_via_recorded_chain',
                         original_link=intermediate, provenance_chain=chain,
                         provenance='recovered_from_cached_profile_lab_chain')
            if identity_quote:
                check['intermediate_identity_quote'] = identity_quote
            if official_check(check, target_url):
                return check
    return None


def confirm_profile_links(school, doc):
    """Record what the official pages say about a site the register already holds (reviewed/profile-links.json rows with `confirms`,
    tools/official_profile_links.py). A link equal to the registered address, or to the faculty-space root it sits under, is the official link (the check
    keeps `linked_url`). A PI whose own official page(s) were read and link nothing keeps the site with `official_link_status: absent_reviewed` and the dated
    pages read; a PI whose pages could not be read stays open. The row's site is never replaced."""
    path = P.data('profile-links.json', school)
    if not Path(path).exists():
        return doc
    prof = {r['pi']: r for r in json.loads(Path(path).read_text()).get('rows', []) if r.get('confirms')}
    for r in doc['labs']:
        pr = prof.get(r['pi'])
        if not pr or r.get('coverage') != 'website' or r.get('official_link_status') == 'recorded' or normalized_link(pr.get('confirms')) != normalized_link(r.get('url')):
            continue
        lk = pr.get('link')
        if lk and pr.get('sha256') and (normalized_link(lk['url']) == normalized_link(r.get('url')) or same_site_by_root(lk['url'], r.get('url'))):
            check = dict(source='school_profile_link', url=r['url'], on=pr['profile_url'], at=pr['fetched_at'], result='listed', anchor=lk.get('anchor'),
                         linked_url=lk['url'], source_sha256=pr['sha256'], source_capture_url=pr.get('capture_url'), provenance='recorded_from_profile_links_json')
            status = 'recorded'
        else:
            pages = [dict(url=t['url'], at=pr['fetched_at'], sha256=t['sha256']) for t in pr.get('tried') or [] if t.get('status') in ('ok', 'ok_wayback') and t.get('sha256')]
            if lk or not pages or r.get('official_link_status') == 'absent_reviewed':
                continue
            via = r.get('found_via') or 'a prior search'
            check = dict(source='official_link_absent_reviewed', url=r['url'], at=pr['fetched_at'], result='no_link_on_official_pages', pages_read=pages,
                         reason=f"no official page links it; found via DBLP/ORCID ({via}); {len(pages)} official page(s) of the PI's unit read {pr['fetched_at'][:10]} and none links this address")
            status = 'absent_reviewed'
        r['checks'] = list(r.get('checks') or []) + [check]
        r['official_link_status'], r['official_link_evidence'] = status, [check]
        if status == 'recorded':
            r['listed_on'] = pr['profile_url']
    return doc


def profile_card_rows(school, doc):
    """A unit's own per-person profile card (charter [web].profile_pages) is never the PI's website (owner 2026-11-25): a row whose site is such a card becomes
    the absence `profile_only_no_homepage` ('official profile only, no personal site') quoting the dated card check. Other rows are untouched."""
    import labpage_audit as L
    L.set_profile_pages(school)
    for i, r in enumerate(doc['labs']):
        if r.get('coverage') not in ('website', 'pending') or not r.get('url') or not L.charter_profile_page(r['url']):
            continue
        card, at = r['url'], r.get('checked_at') or r.get('audited_at')
        sha = r.get('sha256') or ''
        if not at:
            continue
        row = dict(r, checks=list(r.get('checks') or []) + [dict(source='school_profile', url=card, at=at, result='ok', sha256=sha or None)])
        for k in ('url', 'sha256', 'evidence', 'found_via', 'listed_on', 'official_link_status', 'official_link_evidence', 'kind', 'evidence_gaps', 'review_note', 'linked_site', 'robots'):
            row.pop(k, None)
        row.update(status='none_found', coverage='reason', reason_code='profile_only_no_homepage', reason_type='search_no_eligible_site', rejected_url=card,
                   reason=f"official profile only, no personal site: the selected page {card} (read {at[:10]}{', sha256 ' + sha[:12] if sha else ''}) is the unit's own profile card for this PI")
        row['places_checked'] = sorted({f"{c['source']}:{c['result']}" for c in row['checks'] if c.get('url') and c.get('at') and c.get('result')})
        row['checked_at'] = max((c['at'] for c in row['checks'] if c.get('at')), default=None)
        doc['labs'][i] = row
    return doc


def enrich_official_links(school, doc):
    """Recover exact official profile/card links from cached HTML, with no network."""
    doc = confirm_profile_links(school, profile_card_rows(school, doc))
    import labpage_audit as L
    kit = L.Kit(school)
    domain = L.SCHOOLS[school]['domain']
    pages = {}
    def cached_page(url):
        if url not in pages:
            page, _ = kit.stored(url)
            if not page:
                page, _ = kit.stored(kit.src_of(url))
            pages[url] = page
        return pages[url]

    for r in doc['labs']:
        if r.get('coverage') != 'website' or r.get('official_link_status') == 'recorded':
            continue
        target = normalized_link(r['url'])
        for c in list(r.get('checks') or []):
            source_url = c.get('url') or ''
            listing = c.get('source') == 'department_listing'
            if not listing and c.get('source') != 'school_profile' and not L.is_profile(source_url, domain):
                continue
            if not re.search(r'(?:^|\.)(?:' + domain + r')$', urlsplit(source_url).hostname or ''):
                continue
            page = cached_page(source_url)
            if not page or page.get('status') != 200 or not page.get('sha256') or not page.get('content'):
                continue
            if listing:
                match = listing_link_context(page['content'], L.link_base(page, source_url), target, r['pi'])
            else:
                links = L.site_links(kit, page, L.link_base(page, source_url))
                match = next(((url, text) for url, text in links if normalized_link(url) == target), None)
            if match:
                check = dict(source='department_listing_link' if listing else 'school_profile_link', url=r['url'], on=source_url,
                             at=c.get('at') or page.get('fetched_at'), result='listed',
                             anchor=match[1], linked_url=match[0], source_sha256=page['sha256'],
                             source_capture_url=page.get('capture_url'),
                             provenance='recovered_from_cached_listing_card' if listing else 'recovered_from_cached_profile_html')
                if listing:
                    check['source_quote'] = match[2]
                r['checks'].append(check)
                r['official_link_status'] = 'recorded'
                r['official_link_evidence'] = [check]
                r['listed_on'] = source_url
                break
            if not listing:
                check = cached_profile_chain(page, source_url, r['url'], cached_page, L.link_base, pi=r['pi'])
                if check:
                    r['checks'].append(check)
                    r['official_link_status'] = 'recorded'
                    r['official_link_evidence'] = [check]
                    r['listed_on'] = source_url
                    break
    return doc

def capture_stores(school):
    """The lab-page capture stores of a school, plus the person-website fetch store (tools/person_fetch.py) when it exists."""
    paths = [P.data('labpage-audit-captures.sqlite', school), P.data('labpage-captures.sqlite', school),
             Path(P.ROOT) / 'scratch' / 'websites-b' / f'captures-{school}.sqlite']
    return [p for p in paths if p.exists()]


def wayback_captures(school):
    """{url: (sha256, fetched_at, bytes)} for 200 captures the Wayback slow lane stored for the website queue
    (scratch/own-pages/wayback-captures-<school>-websites.sqlite, tools queue_fetch.py: table cap(url, status, final, body, sha256, fetched))."""
    path = Path(P.ROOT) / 'scratch' / 'own-pages' / f'wayback-captures-{school}-websites.sqlite'
    out = {}
    if path.exists():
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        for url, sha, at, body in con.execute("select url, sha256, fetched, body from cap where status=200 and body is not null"):
            out[url] = (sha, at, body)
    return out


def stored_captures(school, urls):
    """{url: (sha256, fetched_at, text)} for stored 200 captures of exactly these URLs (lab-page audit stores; no network)."""
    out = {}
    for path in capture_stores(school):
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        for url, sha, at, blob in con.execute("select url, sha256, fetched_at, content from captures where status=200 and sha256 is not null and content is not null"):
            if url in urls and url not in out:
                out[url] = (sha, at, capture_body_view(blob).decode('utf-8', 'replace'))
    for url, (sha, at, body) in wayback_captures(school).items():
        if url in urls and url not in out:
            out[url] = (sha, at, capture_body_view(body).decode('utf-8', 'replace'))
    return out


def url_variants(url):
    """The spellings a stored capture of `url` may carry: scheme, www, trailing slash, the two HKUST host families (x.hkust.edu.hk / x.ust.hk, with and
    without www) and, on the CSE host, the `/~login/` and `/faculty/login/` forms of the same personal page (their bytes are identical)."""
    p = urlsplit(url)
    host = p.netloc
    hosts = {host, host[4:] if host.startswith('www.') else 'www.' + host}
    for h in list(hosts):
        if h.endswith('.hkust.edu.hk'):
            hosts.add(h[:-len('.hkust.edu.hk')] + '.ust.hk')
            hosts.add('www.' + h[:-len('.hkust.edu.hk')] + '.ust.hk')
            hosts.add('home.' + h[:-len('.hkust.edu.hk')] + '.ust.hk')
        elif h.endswith('.ust.hk'):
            hosts.add(re.sub(r'^www\.', '', h)[:-len('.ust.hk')] + '.hkust.edu.hk')
    path = p.path or '/'
    paths = {path, path.rstrip('/') or '/', path.rstrip('/') + '/'} | ({''} if path.strip('/') == '' else set())   # a bare host is also stored without its slash
    if any(h.startswith(('cse.', 'www.cse.', 'home.cse.')) for h in hosts):
        hosts |= {'cs.ust.hk', 'www.cs.ust.hk', 'home.cs.ust.hk'}   # the department's old name
    cse = re.fullmatch(r'/(?:~|faculty/)([^/]+)/?', path)
    if cse and any(h.startswith(('cse.', 'www.cse.', 'home.cse.')) for h in hosts):
        paths |= {f'/~{cse.group(1)}/', f'/~{cse.group(1)}', f'/faculty/{cse.group(1)}/', f'/faculty/{cse.group(1)}'}
    q = f'?{p.query}' if p.query else ''
    return {f'{sch}://{h}{port}{pa}{q}' for sch, port in (('http', ''), ('http', ':80'), ('https', ''), ('https', ':443')) for h in hosts for pa in paths}   # Wayback-fallback captures carry the default port


def apply_profile_links(school, doc):
    """The homepage an official unit profile links is the PI's website (reviewed/profile-links.json, tools/official_profile_links.py).

    A linked address with a stored page capture becomes the row's website with the dated official-link check; a linked address nobody has captured
    keeps the row pending (`linked_site_not_captured`), never an absence; a profile read and quoted that links no homepage turns an unlinked,
    unreviewed site into the absence `profile_only_no_homepage`. A row the register retains (`retained_review`) is a reviewed decision and is left alone."""
    path = P.data('profile-links.json', school)
    if not Path(path).exists():
        return doc
    prof = {r['pi']: r for r in json.loads(Path(path).read_text()).get('rows', [])}
    for i, lab in enumerate(doc['labs']):
        pr = prof.get(lab['pi'])
        if not pr or retained_review(lab) or pr.get('status') not in ('ok', 'ok_wayback') or pr.get('confirms'):   # a `confirms` row only vouches for a site the register holds
            continue
        at = pr['fetched_at']
        pchk = dict(source='school_profile', url=pr['profile_url'], at=at, result=pr['status'], sha256=pr['sha256'])
        if pr.get('capture_url'):
            pchk['capture_url'] = pr['capture_url']
        link = pr.get('link')
        # this profile's and this link's earlier checks are replaced (a rebuild must not stack them)
        base_checks = [c for c in lab.get('checks') or [] if not (c.get('source') == 'school_profile' and c.get('url') == pr['profile_url'])
                       and not (c.get('source') == 'school_profile_link' and link and normalized_link(c.get('url')) == normalized_link(link['url']))]
        if link:
            site = link['url']
            lchk = dict(source='school_profile_link', url=site, at=at, result='listed', anchor=link.get('anchor'), on=pr['profile_url'])
            cap = stored_captures(school, url_variants(site))
            same_path = lambda k: urlsplit(k).path.rstrip('/') == urlsplit(site).path.rstrip('/')   # noqa: E731
            exact = next((k for k in cap if normalized_link(k) == normalized_link(site)), None) or next((k for k in cap if same_path(k)), None)   # the capture of the linked address (or its host twin) comes before a ~login twin
            hit_url = exact or next(iter(cap), None)
            hit = cap.get(hit_url) if hit_url else None
            row = dict(lab, checks=base_checks + [pchk, lchk])
            for k in ('rejected_url', 'rejected_reason', 'reason_type', 'review_prior', 'website_note', 'review_note', 'review_sources', 'evidence_gaps'):
                row.pop(k, None)
            if hit:
                kind = lab.get('kind') or 'pi_homepage'
                row.update(status='none_found', coverage='website', reason_code='lab_site' if kind == 'lab_site' else 'pi_homepage_only_no_lab_site',
                           reason='Captured lab/group website.' if kind == 'lab_site' else 'Captured PI homepage used as the lab-page fallback.',
                           url=site, kind=kind, found_via='school_profile_link', listed_on=pr['profile_url'], sha256=hit[0],
                           evidence=dict(url=site, captured_url=hit_url, sha256=hit[0], quote=None), official_link_status='recorded', official_link_evidence=[lchk], evidence_gaps=[])
            elif (pr.get('link_robots') or {}).get('allowed') is False:
                rb = pr['link_robots']
                for k in ('sha256', 'evidence', 'kind'):
                    row.pop(k, None)
                row.update(status='none_found', coverage='linked_not_fetched', reason_code=LINKED_NOT_FETCHED, url=site, kind='pi_homepage',
                           found_via='school_profile_link', listed_on=pr['profile_url'], official_link_status='recorded', official_link_evidence=[lchk],
                           robots=rb, evidence_gaps=[],
                           reason=(f"linked by the official profile {pr['profile_url']}; not fetched: robots.txt of {rb['host']} "
                                   + (f"refuses it ({rb.get('rule')}, group {rb.get('agent')})" if rb.get('verdict') == 'refused' else f"gives no usable permission ({rb.get('rule')})")
                                   + f", checked {rb['checked_at'][:10]}"))
            else:
                for k in ('url', 'sha256', 'evidence', 'found_via', 'listed_on', 'official_link_status', 'official_link_evidence', 'kind', 'robots'):
                    row.pop(k, None)
                row.update(coverage='pending', evidence_gaps=['linked_site_not_captured'], linked_site=site,
                           review_note=f"the official profile links {site}, which no stored capture holds (a host that disallows fetching, or not yet fetched)")
            row['places_checked'] = sorted({f"{c['source']}:{c['result']}" for c in row['checks'] if c.get('url') and c.get('at') and c.get('result')})
            row['checked_at'] = max((c['at'] for c in row['checks'] if c.get('at')), default=None)
            doc['labs'][i] = row
        elif lab.get('coverage') == 'website' and not any(c.get('source') in ('web_search_reviewed', 'official_link_chain', 'department_listing_link') and official_check(c, lab.get('url'))
                                                          for c in lab.get('checks') or []):   # a link an earlier profile showed does not survive a profile that shows none
            quote = (pr.get('note') or 'the profile page carries no Personal Webpage / Homepage link')
            row = dict(lab, checks=base_checks + [pchk])
            for k in ('url', 'sha256', 'evidence', 'found_via', 'listed_on', 'official_link_status', 'official_link_evidence', 'kind', 'evidence_gaps'):
                row.pop(k, None)
            row.update(status='none_found', coverage='reason', reason_code='profile_only_no_homepage', reason_type='search_no_eligible_site',
                       reason=f"the official profile {pr['profile_url']} (read {at[:10]}, sha256 {pr['sha256'][:12]}) links no homepage: {quote}",
                       rejected_url=lab.get('url'))
            doc['labs'][i] = row
    return doc


def unit_listing_alias_links(school, doc):
    """A unit directory whose embedded JSON row carries the person's own profile path (`"path":[{"alias":"\\/eejzhang"...}]`, HKUST ECE people_list) is an official
    listing link to that profile page. When a lab's website is that profile page (same host, same path) and no official link is recorded, add a
    `department_listing_link` check whose `on` is the listing URL and whose quote is the literal alias, with the stored listing's sha256. Literal match only."""
    import hashlib
    path = P.data('school-captures.sqlite', school)
    if not Path(path).exists():
        return doc
    try:
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        listings = {u: (sha, capture_body_view(raw).decode('utf-8', 'replace')) for u, sha, raw in con.execute("select url, sha256, raw_zlib from live where raw_zlib is not null and (url like '%people_list%' or url like '%/people%')")}
    except (sqlite3.DatabaseError, zlib.error):
        return doc
    for r in doc.get('labs', []):
        if r.get('coverage') != 'website' or r.get('official_link_status') == 'recorded' or not r.get('url'):
            continue
        site = urlsplit(r['url'])
        alias = '\\/' + site.path.strip('/')
        for lu, (sha, body) in listings.items():
            if urlsplit(lu).netloc != site.netloc or not site.path.strip('/') or ('"alias":"' + alias + '"') not in body:
                continue
            if hashlib.sha256(body.encode('utf-8', 'replace')).hexdigest() != sha and not sha:
                continue
            chk = dict(source='department_listing_link', url=r['url'], on=lu, result='listed', at=r.get('checked_at') or r.get('audited_at'),
                       anchor='listing JSON row path alias ' + alias.replace('\\', ''), source_sha256=sha)
            r['checks'] = list(r.get('checks') or []) + [chk]
            r['official_link_status'], r['official_link_evidence'] = 'recorded', [chk]
            break
    return doc


def archived_official_links(school, doc):
    """Official links from the school's own stored pages, no network (UW 2026-11-22: departed PIs whose current directory no longer lists them,
    and profile links that reach the site through a stub page). For a website row with no recorded official link:
    (1) a profile link to a stub page whose recorded `meta_refresh_target` check lands on the selected site is the profile linking that site
        (the stub's refresh is a redirect; Sumit Roy depts.washington.edu/funlab/ -> wp.ece.uw.edu/funlab/);
    (2) an archived department listing (stage-1 store listings/<key>/raw/captures.sqlite) whose card for this PI links the site literally
        (listing_link_context, card-scoped) -> `department_listing_link`, with the capture's hash and Wayback URL;
    (3) an archived official profile (school-captures.sqlite `captures`, a Wayback id_ capture on the school's own domain) that names the PI and
        links the site literally -> `school_profile_link`. Literal hrefs only; the newest capture wins."""
    import labpage_audit as L
    domain = L.SCHOOLS[school]['domain']
    on_domain = re.compile(r'(?:^|\.)(?:' + domain + r')$')
    todo = [r for r in doc.get('labs', []) if r.get('coverage') == 'website' and r.get('official_link_status') != 'recorded' and r.get('url')]
    if not todo:
        return doc

    def record(r, check):
        r['checks'].append(check)
        r['official_link_status'] = 'recorded'
        r['official_link_evidence'] = [check]
        r['listed_on'] = check['on']

    def original(cu):
        return re.sub(r'^https?://web\.archive\.org/web/[0-9]+(?:id_)?/', '', cu)

    def rows(path, sql):
        if not Path(path).exists():
            return []
        try:
            con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
            return list(con.execute(sql))
        except sqlite3.DatabaseError:
            return []

    left = []
    for r in todo:
        checks = r.get('checks') or []
        refresh = next((c for c in checks if c.get('source') == 'meta_refresh_target' and c.get('result') == 'ok'
                        and normalized_link(c.get('url')) == normalized_link(r['url']) and c.get('on')), None)
        link = refresh and next((c for c in checks if c.get('source') == 'school_profile_link' and c.get('on')
                                 and normalized_link(c.get('url')) == normalized_link(refresh['on'])), None)
        prof = link and next((c for c in checks if c.get('source') == 'school_profile' and c.get('url') == link['on'] and c.get('result') == 'ok'), None)
        if link and prof and on_domain.search(urlsplit(link['on']).hostname or ''):
            record(r, dict(source='school_profile_link', url=r['url'], on=link['on'], at=link.get('at'), result='listed', anchor=link.get('anchor'),
                           linked_url=link['url'], via='meta_refresh', refresh_check_at=refresh.get('at'), source_sha256=prof.get('sha256'),
                           provenance='recovered_profile_link_through_meta_refresh_stub'))
        else:
            left.append(r)
    if not left:
        return doc
    listing_caps = rows(P.data('listings-captures.sqlite', school),
                        "select capture_url, wayback_timestamp, sha256, raw_zlib from captures where http_status=200 and raw_zlib is not null order by wayback_timestamp desc")
    profile_caps = rows(P.data('school-captures.sqlite', school),
                        "select capture_url, wayback_timestamp, sha256, raw_zlib from captures where http_status=200 and raw_zlib is not null order by wayback_timestamp desc")
    for r in left:
        t_net, t_path, _ = normalized_link(r['url'])
        needle = (t_net.removeprefix('www.') + t_path).encode()
        tokens = [x for x in re.findall(r'\w+', unicodedata.normalize('NFKD', r['pi']).encode('ascii', 'ignore').decode()) if len(x) > 1]
        done = False
        for kind, caps in (('listing', listing_caps), ('profile', profile_caps)):
            for cu, ts, sha, raw in caps:
                if not isinstance(cu, str) or not cu:
                    continue  # no archived source URL: this row cannot establish an official discovery link
                try:
                    body = capture_body_view(raw)
                except zlib.error:
                    continue
                page = original(cu)
                # a same-host page links relatively ('/people/faculty/otis_brian/' on the archived EE table): the path alone is the prefilter there
                if not sha or not (needle in body or (normalized_link(page)[0] == t_net and t_path.encode() in body)):
                    continue
                if not on_domain.search(urlsplit(page).hostname or ''):
                    continue
                if kind == 'listing':
                    match = listing_link_context(body, page, normalized_link(r['url']), r['pi'])
                    if not match:
                        continue
                    check = dict(source='department_listing_link', url=r['url'], on=page, at=ts, result='listed', anchor=match[1], linked_url=match[0],
                                 source_quote=match[2][:600], source_sha256=sha, source_capture_url=cu, provenance='recovered_from_archived_department_listing')
                else:
                    text = body.decode('utf-8', 'replace')
                    if len(tokens) < 2 or not re.search(r'(?<!\w)' + r'[\W_]+'.join(map(re.escape, tokens)) + r'(?!\w)', text, re.I):
                        continue
                    hit = next(((u, a, h) for u, a, h in literal_links(body, page) if normalized_link(u) == normalized_link(r['url'])), None)
                    if not hit:
                        continue
                    check = dict(source='school_profile_link', url=r['url'], on=page, at=ts, result='listed', anchor=hit[1], linked_url=hit[0],
                                 href=hit[2], source_sha256=sha, source_capture_url=cu, provenance='recovered_from_archived_official_profile')
                record(r, check)
                done = True
                break
            if done:
                break
    return doc


def official_homepage_fallback(school, doc):
    """Owner-delegated choice (coordinator, 2026-11-10, HKUST; reversible): a website whose URL no official link reaches is replaced by the official personal page the
    department profile itself links ('Personal Webpage', a school_profile_link check) when a stored 200 capture of that exact page exists. The earlier selection (a lab
    site or a DBLP URL) stays in `website_note` with its hash, so nothing is lost; the student and paper audits already ran on it."""
    for r in doc.get('labs', []):
        rejected = r.get('coverage') == 'pending' and r.get('rejected_url')   # the chosen site did not name the PI (a lab site shared by several PIs)
        if not rejected and (r.get('coverage') != 'website' or r.get('official_link_status') == 'recorded' or not r.get('url')):
            continue
        r_url = r.get('url') or r.get('rejected_url')
        links = [c for c in r.get('checks') or [] if c.get('source') == 'school_profile_link' and c.get('on') and c.get('url') and c.get('result') in ('listed', 'ok')]
        listing = next((c for c in r.get('checks') or [] if c.get('source') == 'department_listing' and c.get('result') == 'ok' and c.get('url')), None)
        for c in r.get('checks') or []:   # the department profile IS the PI's personal page ('/~id' on the school host), reached from the department listing
            if c.get('source') == 'school_profile' and c.get('result') == 'ok' and listing and re.match(r'^/~[^/]+/?$', urlsplit(c.get('url') or '').path):
                links.append(dict(source='department_listing_link', url=c['url'], on=listing['url'], result='listed', at=c.get('at'), anchor='department listing to the personal profile page'))
        for chk in links:
            variants = {chk['url'], chk['url'].rstrip('/'), chk['url'].rstrip('/') + '/'}
            caps = stored_captures(school, variants)
            hit = next((caps[v] for v in variants if v in caps), None)
            sha = (hit or {}).get('sha256') if isinstance(hit, dict) else (hit[0] if hit else None)
            if not sha:
                continue
            if chk['url'].rstrip('/') == r_url.rstrip('/'):
                continue   # the rejected or already-selected site itself
            if selection_gaps(chk['url']):
                continue   # a profile card the profile links ('Faculty Webpage' -> people.ece.uw.edu/ostendorf/, UW 2026-11-23) is never the fallback
            if any(c.get('source') == 'meta_refresh_target' and c.get('result') == 'ok' and normalized_link(c.get('on')) == normalized_link(chk['url'])
                   and normalized_link(c.get('url')) == normalized_link(r_url) for c in r.get('checks') or []):
                continue   # the profile links the redirect stub of the selected site itself (UW Shlizerman: /shlizee/ -> /shlizee/NW/index.html)
            r['website_note'] = dict(replaced_url=r_url, replaced_sha256=r.get('sha256'), replaced_kind=r.get('kind'), found_via=r.get('found_via'),
                                     why='no official link reaches this URL; the department profile links the personal page now selected (owner-delegated, reversible)')
            for k in ('rejected_url', 'rejected_reason', 'evidence_gaps'):
                r.pop(k, None) if rejected else None
            r.update(coverage='website', url=chk['url'], kind='pi_homepage', reason_code='pi_homepage_only_no_lab_site', found_via='school_profile_link', listed_on=chk['on'], sha256=sha,
                     evidence=dict(url=chk['url'], sha256=sha, quote=None), official_link_status='recorded', official_link_evidence=[chk])
            if chk not in (r.get('checks') or []):
                r['checks'] = list(r.get('checks') or []) + [chk]   # a synthesized department-listing link must sit in the dated checks the gate reads
            for k in ('people_page', 'alumni_page', 'pubs_page'):
                r['website_note'][k] = r.pop(k, None)
            r['reason'] = 'Captured PI homepage used as the lab-page fallback.'
            break
        else:
            blocked = next((c for c in r.get('checks') or [] if c.get('source') == 'school_profile' and c.get('result') == 'robots_disallowed' and c.get('url')), None)
            if r.get('coverage') == 'website' and r.get('official_link_status') != 'recorded' and r.get('url') and blocked and listing:
                # the department listing links only the institutional profile, whose robots.txt disallows reading it, and no stored official page links the personal site:
                # record an access reason and keep the site (with its hash) in website_note; nothing is fetched against robots.txt.
                r['website_note'] = dict(replaced_url=r['url'], replaced_sha256=r.get('sha256'), replaced_kind=r.get('kind'), found_via=r.get('found_via'),
                                         people_page=r.pop('people_page', None), alumni_page=r.pop('alumni_page', None), pubs_page=r.pop('pubs_page', None),
                                         why='no stored official page links this site; the only official profile (' + blocked['url'] + ') is disallowed by its robots.txt')
                for k in ('url', 'kind', 'sha256', 'evidence', 'found_via', 'listed_on', 'official_link_status', 'official_link_evidence'):
                    r.pop(k, None)
                r.update(coverage='reason', reason_code='host_blocked_by_robots', reason_type='access_blocked',
                         reason='The department listing links only the institutional faculty profile, which robots.txt disallows; the PI\'s own site is not linked from any stored official page (kept in website_note).',
                         reason_scope='Recorded search/access outcome; not proof no website exists or that an archive has no capture.')
    for r in doc.get('labs', []):
        if r.get('coverage') == 'pending' and 'rejected_candidate_requires_search' in (r.get('evidence_gaps') or []) and not r.get('url'):
            # every discovered candidate was an institutional page (university front page, research portal): the search found no eligible homepage
            r.update(coverage='reason', reason_code='profile_only_no_homepage', reason_type='no_eligible_website',
                     reason="The only candidates the discovery found were institutional pages (a university front page or the research portal), which are never a person's or lab's website; no eligible homepage was established from the recorded checks.",
                     reason_scope='Recorded search outcome; not proof no website exists.', evidence_gaps=[])
            r.pop('review_note', None)
    return doc


def attach_stored_captures(school, doc):
    """A prior-pass site with no hash gets one from a stored capture of that exact page, when the page names the PI."""
    def fold(t):
        return re.sub(r'[^a-z ]+', ' ', unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower())
    todo = [r for r in doc['labs'] if 'page_capture_hash_missing' in (r.get('evidence_gaps') or []) and r.get('url')]
    caps = stored_captures(school, {r['url'] for r in todo})
    for r in todo:
        got = caps.get(r['url'])
        toks = fold(r['pi']).split()
        if not got or not toks or toks[-1] not in fold(got[2]) or toks[0] not in fold(got[2]):
            continue
        r['sha256'], r['capture_fetched_at'] = got[0], got[1]
        r['evidence'] = dict(r.get('evidence') or {}, url=r['url'], sha256=got[0], source='stored_capture')
        r['evidence_gaps'] = [g for g in r['evidence_gaps'] if g != 'page_capture_hash_missing']
        if not r['evidence_gaps']:
            r['coverage'] = 'website'
    return doc

LAB_WORDS = re.compile(r'\b(lab|labs|laboratory|group|research group|team|centre|center|institute|institut|chair|professorship|lehrstuhl|seminar)\b', re.I)
PERSONAL_PATH = re.compile(r'/(?:~|people/(?!index\.|$)[^/]|person/|persons/|personal/|profile|staff/|bio\b)', re.I)   # /people/ alone is a group's members page; /people/<slug> is a person's page
GENERIC_HOST_LABELS = {'www', 'people', 'pages', 'web', 'sites', 'home', 'en', 'de'}


def site_kind(url, text='', domains=(), dept_hosts=(), lists_members=False):
    """The one lab-vs-homepage rule (2026-11-25), for discovery-coded and hand-reviewed rows alike. A personal path (~user, /people/<slug>,
    /personal/) is the PI's homepage. Otherwise a lab/group/chair/institute word in the page title or heading, a page that lists members,
    or a dedicated host of the school's own domain (not www/people, not a department host such as ee.ethz.ch) makes a lab site."""
    parts = urlsplit(url or '')
    if PERSONAL_PATH.search(parts.path):
        return 'pi_homepage'
    if lists_members or LAB_WORDS.search(text or ''):
        return 'lab_site'
    host = (parts.hostname or '').lower()
    bare = host[4:] if host.startswith('www.') else host
    for d in domains:
        if bare.endswith('.' + d) and bare not in {h.lower() for h in dept_hosts}:
            label = bare[:-(len(d) + 1)].split('.')[0]
            if label and label not in GENERIC_HOST_LABELS:
                return 'lab_site'
    if bare in {h.lower() for h in dept_hosts} and re.match(r'^/(?!(?:en|de|fr|the|about|news|jobs|people|research|education|index)\b)[a-z]{2,6}(?:/|$)', parts.path):
        return 'lab_site'   # a group's short path on its department's host (bsse.ethz.ch/cbg, math.ethz.ch/sfs)
    return 'pi_homepage'


def reviewed_site_kind(rv, domains=(), dept_hosts=()):
    """site_kind for a hand-reviewed row: the reviewed group heading (kept in the note) and members flag are its text."""
    note = str(rv.get('note') or '')
    heading = note.split('group heading:')[-1] if 'group heading:' in note else ''
    return site_kind(rv.get('url'), heading, domains, dept_hosts, lists_members='lists members: True' in note)


def dept_hosts(school):
    """Hosts of the charter's departments and affiliated units (their pages are not a lab's own site)."""
    try:
        import school_config as SC
        cfg = SC.get(school)
        out = set()

        def walk(o):
            if isinstance(o, dict):
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
            elif isinstance(o, str) and o.startswith('http'):
                out.add((urlsplit(o).hostname or '').lower())
        walk(SC.field(cfg, 'departments') or []); walk(SC.field(cfg, 'affiliated_units') or [])
        return out
    except Exception:  # noqa: BLE001 (a fixture: no charter)
        return set()


def website_review(school, near=None):
    """{(person, url): decision row} from person-website-review.json (next to `near` when given, else the data path)."""
    path = (Path(near).parent / 'person-website-review.json') if near else P.data('person-website-review.json', school)
    if not path.exists():
        path = P.data('person-website-review.json', school)
    return {(r['person'], r['url']): r for r in json.loads(path.read_text()).get('rows', [])} if path.exists() else {}


def school_domains(school):
    try:
        import school_config as SC
        return list(SC.field(SC.get(school), 'web.domains') or [])
    except Exception:  # noqa: BLE001 (a fixture: no charter)
        return []


def verify_websites(school, doc, near=None):
    set_tie_policy(school)
    """A lab or PI website counts only when its stored page names the PI. verified/unverified_reason on every website row; a clear
    mismatch (the page has no surname and the address has no name token, e.g. a student-affairs page) is dropped to `rejected_url` and the
    lab goes back to pending, so no unverified or wrong URL is shown as a lab's website."""
    from person_fetch import GENERIC, last_name_on_page, names_person, plausible_owner
    try:
        reg_names = {x['pi']: x.get('names') for x in json.loads(P.data('pis.json', school).read_text())}   # the registry's Latin names for Han-keyed PIs
    except (OSError, ValueError, KeyError, TypeError):
        reg_names = {}
    shared = {}
    for r in doc['labs']:
        if r.get('url'):
            shared.setdefault(normalized_link(r['url']), set()).add(r['pi'])
    # a row the reviewed register retains (`retained_review`) is a reviewed decision: build-time verification and move checks never reject or rewrite it
    rows = [r for r in doc['labs'] if r.get('url') and r.get('coverage') == 'website' and not retained_review(r)]
    shas = {r['sha256'] for r in rows if r.get('sha256')}
    shas |= {c['sha256'] for r in rows for c in r.get('checks') or [] if c.get('source') == 'people_link' and c.get('sha256')}
    text = {}
    for path in capture_stores(school):
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        for sha in list(shas - set(text)):
            row = con.execute("select content from captures where sha256=? and content is not null limit 1", (sha,)).fetchone()
            if row:
                text[sha] = capture_body_view(row[0])
    for sha, _at, body in wayback_captures(school).values():
        text.setdefault(sha, capture_body_view(body))
    review = website_review(school, near)
    wbcaps = wayback_captures(school)
    found = [rv for rv in review.values() if rv.get('decision') == 'website_found' and rv.get('reviewer') and rv.get('sha256') and rv.get('name_quote') and rv.get('tie_quote')]
    for rv in found:   # a reviewed site discovery missed (a profile naming it as text, a unit profile discovery never read): owner ruling 2026-11-11
        for r in doc['labs']:
            if r['pi'] == rv['person']:
                chk = dict(source='web_search_reviewed', url=rv['url'], at=rv.get('at'), sha256=rv['sha256'], name_quote=rv['name_quote'], tie_quote=rv['tie_quote'],
                           reviewer=rv['reviewer'], result='primary_page_names_pi_and_uw', reviewed_on=rv.get('reviewed_on'), note=rv.get('reason'))
                prior = {k: r.get(k) for k in ('coverage', 'reason_code', 'url', 'rejected_url')}
                kind_ = reviewed_site_kind(rv, school_domains(school), dept_hosts(school))
                r.update(coverage='website', url=rv['url'], kind=kind_, reason_code='lab_site' if kind_ == 'lab_site' else 'pi_homepage_only_no_lab_site', sha256=rv['sha256'],
                         found_via='web_search_reviewed', official_link_status='recorded', official_link_evidence=[chk], verified=True,
                         verified_by='hand_review', verification_reason=rv.get('reason'), reason='Captured lab/group website.' if kind_ == 'lab_site' else 'Captured PI homepage used as the lab-page fallback.',
                         review_prior=prior)
                r['checks'] = [c for c in r.get('checks') or [] if c.get('source') != 'web_search_reviewed'] + [chk]
                for k in ('reason_type', 'rejected_url', 'rejected_reason', 'evidence_gaps', 'review_note', 'linked_site'):
                    r.pop(k, None)
    for rv in review.values():   # a reviewed absence (any row of the person, website or reason): the code must be a supported absence reason
        if rv.get('decision') != 'absence' or rv.get('reason_code') not in ABSENCE_REASONS or not (rv.get('reason') and rv.get('reviewer')):
            continue
        for r in doc['labs']:
            if r['pi'] == rv['person']:
                if r.get('url'):
                    r['rejected_url'] = r.pop('url')
                for k in ('sha256', 'evidence', 'people_page', 'alumni_page', 'pubs_page', 'found_via', 'listed_on', 'official_link_status',
                          'official_link_evidence', 'verified', 'kind', 'evidence_gaps', 'review_note', 'linked_site'):
                    r.pop(k, None)
                r.update(coverage='reason', reason_code=rv['reason_code'], rejected_reason=rv['reason'],
                         reason_type='other_institution' if rv['reason_code'] in ('pi_left_school_site_moved', 'site_at_other_institution') else 'search_no_eligible_site',
                         reason=f"reviewed ({rv['reviewer']}, {rv.get('reviewed_on')}): {rv['reason']}", review_sources=rv.get('sources') or [])
                # the reviewer's own dated look at each source it cites is a dated source check: a PI the discovery never found an official profile
                # for (an accepted addition) would otherwise carry only undated or url-less checks and fail the gate (PKU 2026-11-25)
                when = rv.get('at') or (f"{rv['reviewed_on']}T00:00:00+00:00" if rv.get('reviewed_on') else None)
                cited = [dict(source='reviewed_absence_source', url=s_['url'], at=when, result='reviewed_' + (rv.get('reason_code') or 'absence'), sha256=s_.get('sha256'), quote=s_.get('quote'))
                         for s_ in ({'url': s} if isinstance(s, str) else s for s in rv.get('sources') or []) if isinstance(s_, dict) and s_.get('url') and when]   # ETH reviews cite bare urls
                r['checks'] = [c for c in r.get('checks') or [] if c.get('source') != 'reviewed_absence_source'] + cited
    rows = [r for r in rows if r.get('coverage') == 'website' and r.get('url')]
    for r in rows:
        def live_dest(c):   # the destination of a LIVE fetch (an archived capture's final URL is its Wayback address: never a move)
            f = c.get('final_url') or ''
            return None if (c.get('capture_url') or 'web.archive.org' in f) else (urlsplit(f).hostname or None)
        moved = next((c for c in r.get('checks') or [] if c.get('source') == 'candidate_site' and normalized_link(c.get('url')) == normalized_link(r.get('url'))
                      and live_dest(c) and live_dest(c) != urlsplit(r['url']).hostname
                      and not re.search(r'(?:^|\.)(?:' + '|'.join(re.escape(d_) for d_ in school_domains(school)) + r')$', live_dest(c))), None) if school_domains(school) else None
        if moved:   # a live redirect to another host moved only when the page it lands on no longer names the school (Witten's UW page forwards to her own
            # danielawitten.com, which names UW: not moved)
            body_ = text.get(r.get('sha256'))
            page_ = body_.decode('utf-8', 'replace') if isinstance(body_, (bytes, bytearray)) else (body_ or '')
            try:
                import school_config as SC
                school_rx = SC.aff_rx(school)
            except Exception:  # noqa: BLE001
                school_rx = None
            if not page_ or (school_rx and school_rx.search(page_)):
                moved = None
        if moved:   # the school-era address now redirects to another institution (UW Guestrin: homes.cs.washington.edu/~guestrin/ -> guestrin.su.domains)
            r['rejected_url'], r['rejected_reason'] = r.pop('url'), f"the address now redirects to {moved['final_url']} (another institution); the stored page is not the school-era site"
            for k in ('sha256', 'evidence', 'people_page', 'alumni_page', 'pubs_page', 'found_via', 'listed_on', 'official_link_status', 'official_link_evidence', 'verified', 'kind'):
                r.pop(k, None)
            r.update(coverage='reason', reason_code='pi_left_school_site_moved', reason_type='other_institution',
                     reason=r['rejected_reason'] + '; the PI left the school')
    reviewed_pis = {rv['person'] for rv in found}
    doms, dhosts = school_domains(school), dept_hosts(school)
    for r in doc['labs']:   # discovery-coded rows follow the same rule as hand-reviewed ones
        if r.get('coverage') == 'website' and r.get('url') and r['pi'] not in reviewed_pis and r.get('kind') == 'pi_homepage' \
                and site_kind(r['url'], '', doms, dhosts) == 'lab_site':
            r.update(kind='lab_site', reason_code='lab_site', reason='Captured lab/group website.')
    rows = [r for r in rows if r.get('coverage') == 'website' and r.get('url')]
    for r in rows:
        body = text.get(r.get('sha256'))
        rv = review.get((r['pi'], r['url']))
        if rv and rv['decision'] == 'verified':
            r['verified'], r['verified_by'], r['verification_reason'] = True, 'hand_review', rv['reason']
            r.pop('unverified_reason', None)
            continue
        if rv and rv['decision'] == 'unresolved':
            if r['url'] in wbcaps:   # the slow lane has since read the page: judge it on its text
                body = capture_body_view(wbcaps[r['url']][2])
                r['sha256'] = wbcaps[r['url']][0]
            else:
                r['verified'], r['unverified_reason'] = False, rv['reason']
                continue
        elif rv and rv['decision'] == 'profile_only' and rv.get('reason') and rv.get('reviewer'):
            # a reviewed new search (person-website-review.json): the PI has only the official profile; the selected page is not theirs.
            # Recorded as the absence reason profile_only_no_homepage with the review's sources (UW Kolko, Storti, Prat 2026-11-23)
            r['rejected_url'] = r.pop('url')
            r['rejected_reason'] = rv['reason']
            for k in ('sha256', 'evidence', 'people_page', 'alumni_page', 'pubs_page', 'found_via', 'listed_on', 'official_link_status',
                      'official_link_evidence', 'verified', 'kind'):
                r.pop(k, None)
            r.update(coverage='reason', reason_code='profile_only_no_homepage', reason_type='search_no_eligible_site',
                     reason=f"reviewed new search ({rv['reviewer']}, {rv.get('reviewed_on')}): {rv['reason']}", review_sources=rv.get('sources') or [])
            continue
        elif rv and rv['decision'] == 'rejected':
            r['verified'] = False
            r['rejected_url'] = r.pop('url')
            r['rejected_reason'] = rv['reason']
            for k in ('sha256', 'evidence', 'people_page', 'alumni_page', 'pubs_page', 'found_via', 'listed_on', 'official_link_status',
                      'official_link_evidence', 'verified', 'kind'):
                r.pop(k, None)
            r['coverage'] = 'pending'
            r['evidence_gaps'] = list(r.get('evidence_gaps') or []) + ['website_rejected_by_review']
            r['reason'] = rv['reason'] + '; a new search is needed'
            continue
        if body is None:
            r['verified'], r['unverified_reason'] = False, 'no stored capture of the page to check against'
            continue
        r['verified'], quote = names_person(body, r['pi'], reg_names.get(r['pi']))
        if not r['verified'] and any(official_check(c, r['url']) for c in r.get('checks') or []):
            # a shared group site the PI's official profile links, whose own people page names the PI (UW Tom Anderson: the Allen
            # profile links syslab.cs.washington.edu; its front page names nobody, /people/ lists 'Tom Anderson')
            # the site itself or the target its stub redirects to (UW Roy: depts.washington.edu/funlab/ -> wp.ece.uw.edu/funlab/, whose /members/ names him)
            site = {normalized_link(r['url'])} | {normalized_link(c.get('url')) for c in r.get('checks') or []
                                                  if c.get('source') == 'meta_refresh_target' and c.get('result') == 'ok'
                                                  and normalized_link(c.get('on')) == normalized_link(r['url'])}
            for c in r.get('checks') or []:
                pb = text.get(c.get('sha256')) if c.get('source') == 'people_link' and c.get('result') == 'ok' else None
                if pb is not None and normalized_link(c.get('on')) in site:
                    # the full name, or the surname as a word: an officially linked lab's own members page ('J. Christopher Rudell', 'Prof. Rudell')
                    ok, q = names_person(pb, r['pi'], reg_names.get(r['pi']))
                    if not ok and last_name_on_page(pb, r['pi'], reg_names.get(r['pi'])):
                        ok, q = True, f"surname {r['pi'].split()[-1]!r} on the lab's own people page"
                    if ok:
                        r['verified'], quote = True, q
                        r['verified_via'] = dict(source='people_link', url=c['url'], sha256=c['sha256'])
                        break
        if r['verified']:
            r['verification_quote'] = quote
            r.pop('unverified_reason', None)
        # an officially linked page that names the PI nowhere (page, address, its own people page) is not the PI's site: UW Prat's profile
        # links the Neuroplasticity & Language Lab, directed by Qi Cheng (independent websites audit 2026-11-22)
        elif (not last_name_on_page(body, r['pi'], reg_names.get(r['pi'])) and not plausible_owner(r['url'], r['pi'])
              and not (NAME_WAIVER[0] and any(official_check(c, r['url']) and c.get('source') in ('school_profile_link', 'department_listing_link', 'official_link_chain') for c in r.get('checks') or []))):
            r['rejected_url'] = r.pop('url')
            r['rejected_reason'] = (f"stored page does not name {r['pi']} (no surname on the page, none in the address) and the URL is "
                                    + ('also assigned to other PIs' if len(shared[normalized_link(r['rejected_url'])]) > 1 else 'a generic page' if GENERIC.search(r['rejected_url'])
                                       else 'not linked from an official page' if r.get('official_link_status') != 'recorded' else 'its own people page does not name the PI either'))
            for k in ('sha256', 'evidence', 'people_page', 'alumni_page', 'pubs_page', 'found_via', 'listed_on', 'official_link_status',
                      'official_link_evidence', 'verified', 'kind'):
                r.pop(k, None)
            r['coverage'] = 'pending'
            r['evidence_gaps'] = list(r.get('evidence_gaps') or []) + ['website_rejected_page_does_not_name_pi']
            r['reason'] = r['rejected_reason'] + '; a new search is needed'
        else:
            r['unverified_reason'] = 'stored page does not carry the PI full name' + (' (surname present)' if last_name_on_page(body, r['pi'], reg_names.get(r['pi'])) else ' (address names the PI)')
    return doc


def linked_not_fetched_problems(pi, r):
    """The evidence the state "linked by an official profile, not fetched (robots)" needs: the linked URL, a dated official-link check for exactly that URL
    (the profile that links it), the dated, hashed profile capture that check names, and a robots record of the linked host that gives no permission
    (host, robots.txt URL, the rule or error, and the check date). Without any of these the row is not this state."""
    bad = []
    url, checks, rb = r.get('url'), r.get('checks') or [], r.get('robots') or {}
    if not url:
        return [f'{pi}: linked-not-fetched row has no linked URL']
    link = next((c for c in checks if c.get('source') == 'school_profile_link' and normalized_link(c.get('url')) == normalized_link(url) and c.get('on') and c.get('at')), None)
    if not link:
        bad.append(f'{pi}: linked-not-fetched row has no dated official-link check for {url}')
    else:
        prof = next((c for c in checks if c.get('source') == 'school_profile' and c.get('url') == link['on'] and c.get('at')
                     and re.fullmatch(r'[a-fA-F0-9]{64}', c.get('sha256') or '')), None)
        if not prof:
            bad.append(f'{pi}: linked-not-fetched row has no dated, hashed capture of the profile {link["on"]}')
    host = urlsplit(url).netloc
    verdict_ok = (rb.get('verdict') == 'refused' and str(rb.get('rule') or '').startswith('Disallow:')) or (rb.get('verdict') == 'no_usable_permission' and str(rb.get('rule') or '').startswith('no usable robots.txt'))
    if rb.get('allowed') is not False or not verdict_ok or not rb.get('checked_at') or rb.get('host') != host or not str(rb.get('robots_url') or '').endswith('/robots.txt'):
        bad.append(f'{pi}: linked-not-fetched row has no robots record that refuses {host} (host, robots_url, rule, checked_at)')
    return bad


def gate(doc, expected_pis, require_official=True):
    import labpage_audit as _LA
    if doc.get('school'):
        _LA.set_profile_pages(doc['school'])
        set_tie_policy(doc['school'])
    """Check persisted records independently of their precomputed coverage label."""
    rows = {r['pi']: r for r in doc.get('labs', [])}
    bad = []
    for pi in expected_pis:
        r = rows.get(pi)
        if not r:
            bad.append(f'{pi}: website audit record missing')
            continue
        if r.get('review_note'):
            bad.append(f'{pi}: {r["review_note"]}')
        if r.get('reason_code') == LINKED_NOT_FETCHED:
            bad += linked_not_fetched_problems(pi, r)
            continue
        if r.get('reason_type') == 'pending_archive':
            bad.append(f'{pi}: website archive evidence pending')
        if not dated_checks(r.get('checks') or []):
            bad.append(f'{pi}: website audit lacks a dated source check')
        if r.get('url') and r.get('reason_code') in WEBSITE_REASONS:
            for problem in selection_gaps(r['url']):
                description = {'selected_url_is_profile_card': 'an institutional profile card or identity index',
                               'selected_url_is_research_output': 'a research-output page',
                               'selected_url_is_document': 'a document, not a lab/home webpage',
                               'selected_url_is_feedback_form': 'a site feedback or contact form, not a lab/home webpage'}[problem]
                bad.append(f'{pi}: selected website is {description}')
            if not re.fullmatch(r'[a-fA-F0-9]{64}', r.get('sha256') or '') or not r.get('found_via'):
                bad.append(f'{pi}: website capture hash or discovery provenance missing')
            if require_official and not any(official_check(c, r['url']) or official_absence_check(c, r['url']) for c in r.get('checks') or []):
                bad.append(f'{pi}: website official discovery link not recorded')
        elif r.get('reason_code') not in ABSENCE_REASONS or not r.get('reason'):
            bad.append(f'{pi}: no website or supported absence/access reason')
    return bad

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cmd', choices=['build', 'summary', 'enrich'])
    ap.add_argument('schools', nargs='+')
    ap.add_argument('--out')
    ap.add_argument('--refresh-discovery', action='store_true', help='Refresh website evidence from cached discovery (no network; no student admissions)')
    ap.add_argument('--enrich-official-links', action='store_true', help='Recover links from cached official profile HTML; no network')
    ap.add_argument('--require-complete', action='store_true', help='Fail when any PI lacks a documented URL/reason')
    ap.add_argument('--require-official-provenance', action='store_true', help='Also require recorded official links to every website')
    a = ap.parse_args()
    if a.out and len(a.schools) != 1:
        ap.error('--out requires exactly one school (avoid overwriting its register)')
    if a.cmd == 'enrich' and (not a.out or a.refresh_discovery):
        ap.error('enrich requires an existing --out register and cannot refresh discovery')
    failed = False
    for s in a.schools:
        doc = json.loads(Path(a.out).read_text()) if a.cmd == 'enrich' else build(s, refresh=a.refresh_discovery)
        if doc.get('school') != s:
            ap.error('existing register school does not match requested school')
        if a.cmd == 'build':
            previous_path = Path(a.out) if a.out else P.data('lab-websites.json', s)
            if previous_path.exists():
                previous = json.loads(previous_path.read_text())
                pis = json.loads(P.data('pis.json', s).read_text())
                doc = preserve_reviewed_entries(previous, doc, aliases={p['pi']: p.get('names', []) for p in pis})
        if a.cmd == 'build':
            doc = unit_listing_alias_links(s, doc)
            doc = official_homepage_fallback(s, doc)
            doc = archived_official_links(s, doc)
            doc = apply_profile_links(s, doc)
            doc = profile_card_rows(s, doc)
        if a.enrich_official_links or a.cmd == 'enrich':
            doc = enrich_official_links(s, attach_stored_captures(s, doc))
        if a.cmd in ('build', 'enrich'):
            doc = verify_websites(s, doc, a.out)
            if a.cmd == 'build' and any(x.get('coverage') == 'pending' and x.get('rejected_url') for x in doc['labs']):
                doc = official_homepage_fallback(s, doc)   # a lab site shared by several PIs was rejected: the profile-linked personal page, then verified again
                doc = verify_websites(s, doc, a.out)
        summary = counts(doc)
        if a.cmd in ('build', 'enrich'):
            out = Path(a.out) if a.out else P.data_w('lab-websites.json', s)
            out.parent.mkdir(parents=True, exist_ok=True)
            tmp = out.with_name(out.name + '.tmp')
            tmp.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
            tmp.replace(out)
        print(s, json.dumps(summary))
        failed |= (a.require_complete and not summary['complete']) or (a.require_official_provenance and not summary['official_provenance_complete'])
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
