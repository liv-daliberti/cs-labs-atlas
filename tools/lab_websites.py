"""Consolidate the lab-page audit into a per-PI website register.

A URL is not complete coverage unless it is this school's lab/home page and has
capture provenance. Unsearched PIs and incomplete evidence remain pending.
Outputs are generated audit records, not reviewed student admission evidence.
"""
import argparse
import gzip
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import atlas_paths as P

FOUND_RESULTS = ('ok', 'ok_wayback', 'does_not_name_pi_kept_strong_source')
WEBSITE_REASONS = ('lab_site', 'pi_homepage_only_no_lab_site')
RESEARCH_OUTPUT_PATH = re.compile(r'/(?:publications?|papers|reports|news|blog)/[12][0-9]{3}/', re.I)
ABSENCE_REASONS = {
    'profile_only_no_homepage', 'no_web_presence_found', 'site_dead_no_wayback',
    'host_blocked_by_robots', 'host_challenge_no_wayback', 'pi_left_school_site_moved',
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
    if not dated:
        gaps.append('no_dated_source_check')
    if urls.get('lab_site'):
        via, on, chk = how_found(lp)
        out.update(url=urls['lab_site'], kind=('lab_site' if lp.get('reason_code') == 'lab_site' else 'pi_homepage'),
                   people_page=urls.get('people_page'), alumni_page=urls.get('alumni_page'),
                   pubs_page=urls.get('pubs_page'), found_via=via, listed_on=on,
                   sha256=ev.get('sha256') or (chk or {}).get('sha256'), evidence=ev)
        if lp.get('reason_code') in WEBSITE_REASONS:
            if RESEARCH_OUTPUT_PATH.search(urlsplit(urls['lab_site']).path):
                gaps.append('selected_url_is_research_output')
            if not re.fullmatch(r'[a-fA-F0-9]{64}', out.get('sha256') or ''):
                gaps.append('page_capture_hash_missing')
            if not via:
                gaps.append('discovery_source_missing')
            # An index is a useful lead, but does not establish the official link
            # required by the top-25 brief. Keep this visible for follow-up.
            official = [c for c in checks if c.get('source') == 'school_profile_link'
                        and c.get('url') == urls['lab_site'] and c.get('on')]
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
    # Failed/deferred attempts are a reason access is incomplete, never proof a
    # site does not exist. Preserve the upstream reason, but state its scope.
    if out['coverage'] == 'reason':
        results = {c.get('result') for c in checks}
        code = out['reason_code']
        if code in ('site_at_other_institution', 'pi_left_school_site_moved') or out.get('kind') == 'other_institution_site':
            out['reason_type'] = 'other_institution'
        elif results & {'wayback_only_host', 'wayback_deferred', 'cooldown', 'http_429'}:
            out['reason_type'] = 'pending_archive'
        elif results & {'robots_disallowed', 'bot_challenge', 'off_limits', 'http_403'}:
            out['reason_type'] = 'access_blocked'
        elif code == 'site_dead_no_wayback':
            out['reason_type'] = 'site_unavailable'
        else:
            out['reason_type'] = 'search_no_eligible_site'
        out['reason_scope'] = 'Recorded search/access outcome; not proof no website exists.'
    out['evidence_gaps'] = gaps
    return out


def refresh_records(school, recs):
    """Refresh only website evidence from cached discovery; do not fetch or admit students."""
    import labpage_audit as L
    kit = L.Kit(school)
    ctx = L.load_ctx(school, kit, plan=False)
    disc = L.read_discovery(school)
    for p in ctx['pis']:
        if p['pi'] not in disc:
            continue
        # Discovery from older code may mistake a university profile for a lab.
        d = disc[p['pi']]
        chosen = (d.get('chosen') or {}).get('lab_site')
        if chosen and L.is_profile(chosen, ctx['cfg']['domain']):
            d = dict(d, chosen={})
            disc[p['pi']] = d
        lp, _ = L.lab_record(kit, ctx, p, disc)
        old = recs.get(p['pi']) or {}
        # A new page needs its own review; an old page's audited status cannot
        # silently transfer to a different discovery target.
        same_pages = (old.get('lab_page') or {}).get('urls') == lp.get('urls')
        recs[p['pi']] = dict(old, pi=p['pi'], lab_page=lp, audited_at=d.get('checked_at'),
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




def normalized_link(url):
    """Compare http/https and fragment variants, never different hosts or paths."""
    p = urlsplit(url or '')
    return p.netloc.lower(), p.path.rstrip('/'), p.query


def enrich_official_links(school, doc):
    """Recover exact official-profile links from stored HTML, with no network."""
    import labpage_audit as L
    kit = L.Kit(school)
    domain = L.SCHOOLS[school]['domain']
    for r in doc['labs']:
        if r.get('coverage') != 'website' or r.get('official_link_status') == 'recorded':
            continue
        target = normalized_link(r['url'])
        for c in list(r.get('checks') or []):
            source_url = c.get('url') or ''
            if c.get('source') != 'school_profile' and not L.is_profile(source_url, domain):
                continue
            if not re.search(domain, urlsplit(source_url).hostname or ''):
                continue
            page, _ = kit.stored(source_url)
            if not page or page.get('status') != 200 or not page.get('sha256') or not page.get('content'):
                continue
            links = L.site_links(kit, page, L.link_base(page, source_url))
            match = next(((url, text) for url, text in links if normalized_link(url) == target), None)
            if match:
                check = dict(source='school_profile_link', url=r['url'], on=source_url,
                             at=c.get('at') or page.get('fetched_at'), result='listed',
                             anchor=match[1], linked_url=match[0], source_sha256=page['sha256'],
                             provenance='recovered_from_cached_profile_html')
                r['checks'].append(check)
                r['official_link_status'] = 'recorded'
                r['official_link_evidence'] = [check]
                r['listed_on'] = source_url
                break
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
        if r.get('reason_type') == 'pending_archive':
            bad.append(f'{pi}: website archive evidence pending')
        if not dated_checks(r.get('checks') or []):
            bad.append(f'{pi}: website audit lacks a dated source check')
        if r.get('url') and r.get('reason_code') in WEBSITE_REASONS:
            if RESEARCH_OUTPUT_PATH.search(urlsplit(r['url']).path):
                bad.append(f'{pi}: selected website is a dated research-output page')
            if not re.fullmatch(r'[a-fA-F0-9]{64}', r.get('sha256') or '') or not r.get('found_via'):
                bad.append(f'{pi}: website capture hash or discovery provenance missing')
            if require_official and not any(c.get('source') == 'school_profile_link' and c.get('url') == r['url'] and c.get('on')
                                            for c in r.get('checks') or []):
                bad.append(f'{pi}: website official discovery link not recorded')
        elif r.get('reason_code') not in ABSENCE_REASONS or not r.get('reason'):
            bad.append(f'{pi}: no website or supported absence/access reason')
    return bad

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('cmd', choices=['build', 'summary'])
    ap.add_argument('schools', nargs='+')
    ap.add_argument('--out')
    ap.add_argument('--refresh-discovery', action='store_true', help='Refresh website evidence from cached discovery (no network; no student admissions)')
    ap.add_argument('--enrich-official-links', action='store_true', help='Recover links from cached official profile HTML; no network')
    ap.add_argument('--require-complete', action='store_true', help='Fail when any PI lacks a documented URL/reason')
    ap.add_argument('--require-official-provenance', action='store_true', help='Also require recorded official links to every website')
    a = ap.parse_args()
    if a.out and len(a.schools) != 1:
        ap.error('--out requires exactly one school (avoid overwriting its register)')
    failed = False
    for s in a.schools:
        doc = build(s, refresh=a.refresh_discovery)
        if a.enrich_official_links:
            doc = enrich_official_links(s, doc)
        summary = counts(doc)
        if a.cmd == 'build':
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
