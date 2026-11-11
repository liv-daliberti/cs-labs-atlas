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
RESEARCH_OUTPUT_PATH = re.compile(r'/(?:publications?|papers?|reports?)(?:/|\.|$)|/(?:news|blog)/[12][0-9]{3}(?:/|$)', re.I)
INSTITUTIONAL_PROFILE_HOST = re.compile(r'(?:^|\.)(?:researchportal|facultyprofiles)\.[a-z0-9.-]*hk$', re.I)
INSTITUTIONAL_ROOT = re.compile(r'^(?:www\.)?(?:hkust\.edu\.hk|ust\.hk|hkust-gz\.edu\.cn)$', re.I)
IDENTITY_INDEX_HOST = re.compile(r'(?:^|\.)(?:orcid\.org|dblp\.org|openalex\.org|researchgate\.net|scholar\.google\.[a-z.]+)$', re.I)
ABSENCE_REASONS = {
    'profile_only_no_homepage', 'no_web_presence_found', 'site_dead_no_wayback',
    'host_blocked_by_robots', 'host_access_blocked', 'host_challenge_no_wayback', 'pi_left_school_site_moved',
    'site_at_other_institution', 'new_arrival_no_site_yet', 'emeritus_or_admin_no_lab',
}


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
    if RESEARCH_OUTPUT_PATH.search(parsed.path):
        gaps.append('selected_url_is_research_output')
    if re.search(r'\.(?:pdf|ps|docx?)$', parsed.path, re.I):
        gaps.append('selected_url_is_document')
    return gaps


def official_check(check, url):
    if check.get('source') == 'web_search_reviewed':
        return bool(check.get('url') == url and check.get('at') and re.fullmatch(r'[a-fA-F0-9]{64}', check.get('sha256') or '')
                    and (check.get('tie_quote') or '').strip() and (check.get('name_quote') or '').strip() and check.get('reviewer'))
    if check.get('source') not in OFFICIAL_LINK_SOURCES or check.get('url') != url or not check.get('on'):
        return False
    if check['source'] != 'official_link_chain':
        return True
    chain = check.get('provenance_chain') or []
    if len(chain) != 2 or chain[0].get('source_url') != check['on'] or chain[-1].get('url') != url:
        return False
    if normalized_link(chain[0].get('url')) != normalized_link(chain[1].get('source_url')):
        return False
    return all(c.get('href') and c.get('source_fetched_at') and re.fullmatch(r'[a-fA-F0-9]{64}', c.get('source_sha256') or '') for c in chain)


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
        elif results & {'robots_disallowed', 'bot_challenge', 'off_limits', 'http_403', 'host_access_blocked'}:
            out['reason_type'] = 'access_blocked'
        elif code == 'site_dead_no_wayback':
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
    for p in ctx['pis']:
        if p['pi'] not in disc:
            continue
        # Discovery from older code may mistake a university profile for a lab.
        d = disc[p['pi']]
        chosen = (d.get('chosen') or {}).get('lab_site')
        review_needed = None
        invalid = lambda u: L.is_profile(u, ctx['cfg']['domain']) or selection_gaps(u)
        if chosen and invalid(chosen):
            verified = {c.get('url') for c in d.get('checks') or [] if c.get('source') == 'candidate_site' and c.get('result') in FOUND_RESULTS}
            replacement = next((s for s in d.get('sites') or [] if s.get('url') in verified and not invalid(s['url'])), None)
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


def build(school, refresh=False):
    with open(P.data('pis.json', school)) as f:
        pis = list(dict.fromkeys(p['pi'] for p in json.load(f)))
    recs = {}
    audit = P.data('labpage-audit.jsonl.gz', school)
    if audit.exists():
        with gzip.open(audit, 'rt') as f:
            for line in f:
                r = json.loads(line)
                recs[r['pi']] = r
    if refresh:
        recs = refresh_records(school, recs)
    labs = [entry(recs[p]) if p in recs else dict(pi=p, status='unaudited', coverage='pending',
            evidence_gaps=['audit_record_missing']) for p in pis]
    return dict(school=school, tool='tools/lab_websites.py', source='labpage-audit.jsonl.gz',
                source_exists=audit.exists(), refreshed_from_cached_discovery=refresh, review_status='generated; student admissions require separate review', labs=labs)


def counts(doc):
    c = dict(labs=len(doc['labs']), website=0, reason=0, neither=0, official_link_not_recorded=0, pending_archive=0, access_blocked=0)
    for e in doc['labs']:
        if e.get('reason_type') in ('pending_archive', 'access_blocked'):
            c[e['reason_type']] += 1
        outcome = e.get('coverage')
        c[outcome if outcome in ('website', 'reason') else 'neither'] += 1
        if outcome == 'website' and e.get('official_link_status') != 'recorded':
            c['official_link_not_recorded'] += 1
    c['documented'] = c['neither'] == 0
    c['complete'] = c['documented'] and c['pending_archive'] == 0
    c['official_provenance_complete'] = c['complete'] and c['official_link_not_recorded'] == 0
    return c


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
    """Compare http/https and fragment variants, never different hosts or paths."""
    p = urlsplit(url or '')
    return p.netloc.lower(), p.path.rstrip('/'), p.query


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
    try:
        content = zlib.decompress(content)
    except (zlib.error, TypeError):
        pass
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
    try:
        content = zlib.decompress(content)
    except (zlib.error, TypeError):
        pass
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
            content = page['content']
            try:
                content = zlib.decompress(content)
            except (zlib.error, TypeError):
                pass
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


def enrich_official_links(school, doc):
    """Recover exact official profile/card links from cached HTML, with no network."""
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
                try:
                    blob = zlib.decompress(blob)
                except zlib.error:
                    pass
                out[url] = (sha, at, blob.decode('utf-8', 'replace'))
    for url, (sha, at, body) in wayback_captures(school).items():
        if url in urls and url not in out:
            out[url] = (sha, at, body.decode('utf-8', 'replace'))
    return out


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
        listings = {u: (sha, zlib.decompress(raw).decode('utf-8', 'replace')) for u, sha, raw in con.execute("select url, sha256, raw_zlib from live where raw_zlib is not null and (url like '%people_list%' or url like '%/people%')")}
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


def website_review(school, near=None):
    """{(person, url): decision row} from person-website-review.json (next to `near` when given, else the data path)."""
    path = (Path(near).parent / 'person-website-review.json') if near else P.data('person-website-review.json', school)
    if not path.exists():
        path = P.data('person-website-review.json', school)
    return {(r['person'], r['url']): r for r in json.loads(path.read_text()).get('rows', [])} if path.exists() else {}


def verify_websites(school, doc, near=None):
    """A lab or PI website counts only when its stored page names the PI. verified/unverified_reason on every website row; a clear
    mismatch (the page has no surname and the address has no name token, e.g. a student-affairs page) is dropped to `rejected_url` and the
    lab goes back to pending, so no unverified or wrong URL is shown as a lab's website."""
    from person_fetch import GENERIC, last_name_on_page, names_person, plausible_owner
    shared = {}
    for r in doc['labs']:
        if r.get('url'):
            shared.setdefault(normalized_link(r['url']), set()).add(r['pi'])
    rows = [r for r in doc['labs'] if r.get('url') and r.get('coverage') == 'website']
    shas = {r['sha256'] for r in rows if r.get('sha256')}
    text = {}
    for path in capture_stores(school):
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        for sha in list(shas - set(text)):
            row = con.execute("select content from captures where sha256=? and content is not null limit 1", (sha,)).fetchone()
            if row:
                try:
                    text[sha] = zlib.decompress(row[0])
                except zlib.error:
                    text[sha] = row[0]
    for sha, _at, body in wayback_captures(school).values():
        text.setdefault(sha, body)
    review = website_review(school, near)
    wbcaps = wayback_captures(school)
    for r in rows:
        body = text.get(r.get('sha256'))
        rv = review.get((r['pi'], r['url']))
        if rv and rv['decision'] == 'verified':
            r['verified'], r['verified_by'], r['verification_reason'] = True, 'hand_review', rv['reason']
            r.pop('unverified_reason', None)
            continue
        if rv and rv['decision'] == 'unresolved':
            if r['url'] in wbcaps:   # the slow lane has since read the page: judge it on its text
                body = wbcaps[r['url']][2]
                r['sha256'] = wbcaps[r['url']][0]
            else:
                r['verified'], r['unverified_reason'] = False, rv['reason']
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
        r['verified'], quote = names_person(body, r['pi'])
        if r['verified']:
            r['verification_quote'] = quote
            r.pop('unverified_reason', None)
        elif (not last_name_on_page(body, r['pi']) and not plausible_owner(r['url'], r['pi'])
              and (r.get('official_link_status') != 'recorded' or len(shared[normalized_link(r['url'])]) > 1 or GENERIC.search(r['url']))):
            r['rejected_url'] = r.pop('url')
            r['rejected_reason'] = (f"stored page does not name {r['pi']} (no surname on the page, none in the address) and the URL is "
                                    + ('also assigned to other PIs' if len(shared[normalized_link(r['rejected_url'])]) > 1 else 'a generic page' if GENERIC.search(r['rejected_url']) else 'not linked from an official page'))
            for k in ('sha256', 'evidence', 'people_page', 'alumni_page', 'pubs_page', 'found_via', 'listed_on', 'official_link_status',
                      'official_link_evidence', 'verified', 'kind'):
                r.pop(k, None)
            r['coverage'] = 'pending'
            r['evidence_gaps'] = list(r.get('evidence_gaps') or []) + ['website_rejected_page_does_not_name_pi']
            r['reason'] = r['rejected_reason'] + '; a new search is needed'
        else:
            r['unverified_reason'] = 'stored page does not carry the PI full name' + (' (surname present)' if last_name_on_page(body, r['pi']) else ' (address names the PI)')
    return doc


def gate(doc, expected_pis, require_official=True):
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
        if r.get('reason_type') == 'pending_archive':
            bad.append(f'{pi}: website archive evidence pending')
        if not dated_checks(r.get('checks') or []):
            bad.append(f'{pi}: website audit lacks a dated source check')
        if r.get('url') and r.get('reason_code') in WEBSITE_REASONS:
            for problem in selection_gaps(r['url']):
                description = {'selected_url_is_profile_card': 'an institutional profile card or identity index',
                               'selected_url_is_research_output': 'a research-output page',
                               'selected_url_is_document': 'a document, not a lab/home webpage'}[problem]
                bad.append(f'{pi}: selected website is {description}')
            if not re.fullmatch(r'[a-fA-F0-9]{64}', r.get('sha256') or '') or not r.get('found_via'):
                bad.append(f'{pi}: website capture hash or discovery provenance missing')
            if require_official and not any(official_check(c, r['url']) for c in r.get('checks') or []):
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
