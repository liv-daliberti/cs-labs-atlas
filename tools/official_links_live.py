"""Official discovery links for a lab-website register, read from the school's own profile and listing pages (stage 3).

For every register row whose website has no recorded official link, fetch (robots honoured, per-host pacing, challenge hosts skipped: tools/school_web.py live)
the school-domain profile and department-listing pages the audit already used, and record a `school_profile_link` / `department_listing_link` check when the page
links the website (href compared with lab_websites.normalized_link). Only hosts whose hosts.json verdict is use=live are fetched; a host that serves a challenge is
never retried and nothing goes through Wayback here. The register is rewritten in place (--in) or to --out; rows are changed only by appending a check.
--absence  (second step, reviewed policy, reversible) a website still without an official link is replaced by a recorded access reason, the site kept in `website_note`
           with its hash: the department profile was read and links no site (`profile_only_no_homepage`), or the profile host refused us (robots, 403 or a bot challenge:
           `host_blocked_by_robots` / `host_challenge_no_wayback`). A row with no dated profile check at all is left alone and reported.
usage: official_links_live.py <key> --in <register.json> [--out <register.json>] [--dry] [--absence]
"""
import argparse, collections, json, re, time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import atlas_paths as P  # noqa: E402
import lab_websites as LW  # noqa: E402
import school_web as W  # noqa: E402

HREF = re.compile(r'''(?:href|data-href)\s*=\s*["']([^"'#][^"']*)["']''', re.I)


def live_hosts(key):
    h = json.loads(P.data('hosts.json', key).read_text())
    return {x['host'] for x in (h.get('hosts', h) if isinstance(h, dict) else h) if x.get('use') == 'live'}


def candidates(row, domain, hosts):
    seen, out = set(), []
    for c in row.get('checks') or []:
        u = c.get('url') or ''
        if c.get('source') not in ('school_profile', 'department_listing') or not u.startswith('http'):
            continue
        host = urlsplit(u).hostname or ''
        if 'web.archive.org' in host or not re.search(r'(?:^|\.)' + re.escape(domain) + r'$', host) or host not in hosts or u in seen:
            continue
        seen.add(u)
        out.append((c['source'], u))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('key'); ap.add_argument('--in', dest='inp', required=True); ap.add_argument('--out'); ap.add_argument('--dry', action='store_true'); ap.add_argument('--absence', action='store_true'); ap.add_argument('--hand')
    a = ap.parse_args()
    import labpage_audit as L
    doc = json.loads(Path(a.inp).read_text())
    domain = L.SCHOOLS[a.key]['domain']
    hosts = live_hosts(a.key)
    c = W.con(a.key)
    stats = dict(rows=0, fetched=0, linked=0, skipped_no_candidate=0)
    cache = {}
    for r in doc['labs']:
        if not r.get('url') or r.get('official_link_status') == 'recorded' or r.get('coverage') not in ('website', 'pending'):
            continue
        stats['rows'] += 1
        target = LW.normalized_link(r['url'])
        cands = candidates(r, domain, hosts)
        if not cands:
            stats['skipped_no_candidate'] += 1
            continue
        for source, u in cands:
            if u not in cache:
                if a.dry:
                    cache[u] = None
                    continue
                res = W.live(c, u)
                stats['fetched'] += 1
                cache[u] = (res, W.live_html(c, u)) if res and res[0] == 200 else None
            got = cache[u]
            if not got:
                continue
            (status, sha, _), html = got
            hit = next((h for h in HREF.findall(html) if LW.normalized_link(urljoin(u, h)) == target), None)
            if hit:
                chk = dict(source='department_listing_link' if source == 'department_listing' else 'school_profile_link', url=r['url'], on=u,
                           at=time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime()), result='listed', anchor=hit, linked_url=urljoin(u, hit),
                           source_sha256=sha, provenance='live_fetch_stage3_official_links')
                r['checks'] = list(r.get('checks') or []) + [chk]
                r['official_link_status'] = 'recorded'
                r['official_link_evidence'] = [chk]
                r['listed_on'] = u
                stats['linked'] += 1
                break
    if a.hand:   # reviewed decisions {pi: {reject_url, reason_code, reason}}: a selected page that is not a lab or home page becomes a recorded reason, the page kept in website_note
        hand = json.loads(Path(a.hand).read_text())
        for r in doc['labs']:
            h = hand.get(r['pi'])
            if h and r.get('url') == h['reject_url']:
                r['website_note'] = dict(replaced_url=r.pop('url'), replaced_sha256=r.pop('sha256', None), replaced_kind=r.pop('kind', None), why=h['why'])
                for k in ('evidence', 'found_via', 'listed_on', 'official_link_status', 'official_link_evidence', 'people_page', 'alumni_page', 'pubs_page', 'verified'):
                    r.pop(k, None)
                r.pop('evidence_gaps', None)
                r.update(coverage='reason', reason_code=h['reason_code'], reason_type='search_no_eligible_site', reason=h['reason'],
                         reason_scope='Recorded search/access outcome; not proof no website exists or that an archive has no capture.', hand_reviewed=True)
    if a.absence:
        stats['absence'] = collections.Counter()
        for r in doc['labs']:
            if not (r.get('url') or r.get('rejected_url')) or r.get('official_link_status') == 'recorded' or r.get('coverage') not in ('website', 'pending'):
                continue
            prof = [c for c in r.get('checks') or [] if c.get('source') == 'school_profile' and c.get('url') and c.get('at')]
            read = [c for c in prof if str(c.get('result', '')).startswith('ok')]
            refused = [c for c in prof if c.get('result') in ('robots_disallowed', 'http_403', 'bot_challenge', 'http_429')]
            if read:
                code, rtype = 'profile_only_no_homepage', 'search_no_eligible_site'
                why = (f"The department profile ({read[0]['url']}, read {read[0]['at'][:10]}) and the department listing link no personal or lab website for this PI; "
                       'the site a search found is kept in website_note and is not reached from any official page.')
            elif refused:
                code, rtype = ('host_blocked_by_robots', 'access_blocked') if refused[0]['result'] == 'robots_disallowed' else ('host_challenge_no_wayback', 'access_blocked')
                why = (f"The official profile ({refused[0]['url']}) was refused to this crawler ({refused[0]['result']}, {refused[0]['at'][:10]}) and no stored official page links the site; "
                       'the site a search found is kept in website_note.')
            elif [c for c in r.get('checks') or [] if c.get('source') == 'department_listing' and str(c.get('result', '')).startswith('ok') and c.get('at')]:
                lc = [c for c in r['checks'] if c.get('source') == 'department_listing' and str(c.get('result', '')).startswith('ok') and c.get('at')][0]
                code, rtype = 'profile_only_no_homepage', 'search_no_eligible_site'
                why = (f"The department listing ({lc['url']}, read {lc['at'][:10]}) links no personal or lab website for this PI and no profile page was read; "
                       'the site a search found is kept in website_note and is not reached from any official page.')
            else:
                stats['absence']['left_no_profile_check'] += 1
                continue
            r['website_note'] = dict(replaced_url=r.get('url') or r.get('rejected_url'), replaced_sha256=r.get('sha256'), replaced_kind=r.get('kind'), found_via=r.get('found_via'),
                                     people_page=r.pop('people_page', None), alumni_page=r.pop('alumni_page', None), pubs_page=r.pop('pubs_page', None),
                                     why='no stored or live official page links this site (reviewed policy, reversible)')
            for k in ('url', 'kind', 'sha256', 'evidence', 'found_via', 'listed_on', 'official_link_status', 'official_link_evidence', 'rejected_url', 'rejected_reason', 'verified', 'unverified_reason'):
                r.pop(k, None)
            r.pop('evidence_gaps', None)
            r.update(coverage='reason', reason_code=code, reason_type=rtype, reason=why,
                     reason_scope='Recorded search/access outcome; not proof no website exists or that an archive has no capture.')
            stats['absence'][code] += 1
        stats['absence'] = dict(stats['absence'])
    print(json.dumps(stats))
    if not a.dry:
        Path(a.out or a.inp).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
