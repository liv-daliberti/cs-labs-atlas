"""Websites a school's own per-person profile pages link, read live (stage 3, CMU 2026-11-11).

Why: the register's `profile_only_no_homepage` reason said "no profile page was read" for most CMU PIs, and a fresh look at the official Scholars@CMU
profiles shows 'Personal Website' links (Acquisti: https://www.heinz.cmu.edu/~acquisti/). tools/profile_links.py only re-reads stored captures, which for
CMU held the department *listing*, not each PI's own profile. This finds each PI's own official profile pages and records what they link:
  - candidates: the profile URL in the census row, the census source URLs and register checks on the school's own live hosts that are per-person pages,
    and the PI's Scholars@CMU page (the portal's sitemap slug equals the folded full name exactly once; --portal-sitemap);
  - fetched live through tools/school_web.py (hosts.json use=live only, robots honoured, per-host delay, challenge hosts never retried);
  - an anchor whose text (name tokens and '(opens in a new tab)' removed) is a website/homepage/lab/group label is the PI's official website link;
  - the linked page (stored capture, else a live host) must name the PI -> the PI's website with an official `school_profile_link` check; a link whose page
    cannot be read here becomes an access reason that names the official link; nothing goes through Wayback.
Rows are changed only for `profile_only_no_homepage` / `no_web_presence_found` reasons. Search-found sites that no official page links stay absence rows.
usage: profile_links_live.py <key> --in <register.json> --out <register.json> [--dry] [--portal-sitemap URL] [--limit N]
"""
import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import atlas_paths as P  # noqa: E402
import lab_websites as LW  # noqa: E402
import profile_links as PL  # noqa: E402
import school_web as W  # noqa: E402

ANCHOR = PL.ANCHOR
LABEL = re.compile(r'^\W*(?:(?:personal|my|lab|group|research group|faculty|home|professional|academic|external)\s+)?(?:web\s?site|web\s?page|home\s?page|site)\W*$|'
                   r'^\W*(?:personal (?:site|page)|lab|research group|group|lab website|group website)\W*$|'
                   r'^\W*(?:[\w&\'-]+\s+){1,6}(?:lab|laboratory|group|research group)\s+(?:web\s?site|web\s?page|home\s?page)\W*$', re.I)
LISTINGISH = re.compile(r'/(?:faculty|people|directory|persons?)/?$|faculty-name|/people/index|/directory/(?:faculty|all)|adjunct|courtesy|emerit|faculty-index|affiliated', re.I)
FILE_PATH = re.compile(r'\.(?:pdf|docx?|jpe?g|png|gif)$', re.I)
OPENS = re.compile(r'\(opens in a new tab\)', re.I)


def label_of(text, pi):
    t = OPENS.sub(' ', re.sub(r'[⁠​]', '', text))
    t = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t)).strip()
    for w in sorted(PL.fold(pi).split(), key=len, reverse=True):
        t = re.sub(r'\b' + re.escape(w) + r"(?:'s)?\b", ' ', t, flags=re.I)
    return re.sub(r'\s+', ' ', t).strip()


def profile_anchors(html, base, pi, own):
    out = []
    if len(ANCHOR.findall(html)) > 160:   # a listing page: the stored-capture pass (profile_links.py) reads those card by card
        return out
    for m in ANCHOR.finditer(html):
        href, inner = m.group(1), m.group(2)
        u = urljoin(base, href.replace('&amp;', '&'))
        sp = urlsplit(u)
        if sp.scheme not in ('http', 'https') or PL.SKIP_HOST.search(sp.hostname or '') or FILE_PATH.search(sp.path):
            continue
        if LW.normalized_link(u) in own or 'symplectic' in (sp.hostname or ''):
            continue
        text = label_of(inner, pi)
        personal = bool(re.search(r'^/(?:~|users?/)' + re.escape(PL.fold(pi).split()[-1][:4]), sp.path, re.I)) or bool(re.search(r'^/~[a-z]*' + re.escape(PL.fold(pi).split()[-1][-4:]), sp.path, re.I))
        if LABEL.search(text) or personal or (not text and PL.fold(pi).split()[-1] in (sp.hostname or '').lower() and sp.path.strip('/') == ''):
            out.append((u, label_of(inner, '') or text))
    return out


def scholars_map(c, sitemap):
    """folded full name -> [urls] from the portal sitemap (slug '<id>-<first>-<last>')."""
    res = W.live(c, sitemap)
    if not res or res[0] != 200:
        return {}
    html = W.live_html(c, sitemap)
    out = {}
    for u in re.findall(r'<loc>([^<]+)</loc>', html):
        slug = urlsplit(u).path.strip('/')
        m = re.fullmatch(r'\d+-(.+)', slug)
        if m:
            out.setdefault(' '.join(m.group(1).split('-')), []).append(u)
    return out


RI_API = 'https://www.ri.cmu.edu/wp-json/people/v1/get_all'


def ri_homepages(key):
    """{folded name: (homepage_url, listing sha256)} from the stored official RI people API (metadata.homepage_url, names and aliases)."""
    sp = PL.stored_page(key, RI_API)
    if not sp:
        return {}
    try:
        data = json.loads(sp[0])
    except ValueError:
        return {}
    out = {}
    stack = [data]
    while stack:
        d = stack.pop()
        if isinstance(d, dict):
            hp = ((d.get('metadata') or {}).get('homepage_url') or '').strip()
            if d.get('name') and 'metadata' in d and str(d.get('category', '')).startswith('ri-faculty'):
                for n in [d['name']] + list(d.get('aliases') or []):
                    if hp.startswith('http'):
                        out[' '.join(PL.fold(n).split())] = (hp, sp[1])
            stack.extend(v for v in d.values() if isinstance(v, (dict, list)))
        elif isinstance(d, list):
            stack.extend(d)
    return out


def candidates(row, cen, live_hosts, school_rx, portal):
    out = []
    e = cen.get(row['pi']) or {}
    for u in [e.get('profile_url')] + [s.get('url') for s in e.get('sources') or []] + [k.get('url') for k in row.get('checks') or []
                                                                                          if k.get('source') in ('school_profile', 'pi_evidence_url', 'school_profile_link')]:
        if not u or not str(u).startswith('http'):
            continue
        sp = urlsplit(u)
        if (sp.hostname or '') not in live_hosts or not school_rx.search(sp.hostname or '') or LISTINGISH.search(sp.path) or sp.path.strip('/') == '':
            continue
        if u.endswith(('.json', '.pdf')):
            continue
        toks = [w for w in PL.fold(row['pi']).split() if len(w) > 2]
        if not any(t in u.lower() for t in toks):
            continue   # not a per-person address: a multi-person listing card would attribute a neighbour's link (fresh reviewer, Titzer/Aldrich)
        out.append(u.split('#')[0])
    names = [row['pi']] + list(e.get('aliases') or [])
    for n in names:
        hit = portal.get(' '.join(PL.fold(re.sub(r'\s*\([^)]*\)', '', n)).split()))
        if hit and len(hit) == 1:
            out.append(hit[0])
    return list(dict.fromkeys(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('key'); ap.add_argument('--in', dest='inp', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--dry', action='store_true'); ap.add_argument('--portal-sitemap', default=None); ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    doc = json.loads(Path(a.inp).read_text())
    h = json.loads(P.data('hosts.json', a.key).read_text())
    live_hosts = {x['host'] for x in (h.get('hosts', h) if isinstance(h, dict) else h) if x.get('use') == 'live'}
    c = W.con(a.key)
    import labpage_audit as LA
    school_rx = re.compile(r'(?:^|\.)' + LA.SCHOOLS[a.key]['domain'] + r'$', re.I)
    cen = json.loads(Path(P.data('census-faculty.json', a.key)).read_text())
    cen = {x['name']: x for x in (cen if isinstance(cen, list) else cen.get('faculty', cen))}
    portal = scholars_map(c, a.portal_sitemap) if a.portal_sitemap else {}
    ri = ri_homepages(a.key)
    stats = dict(rows=0, no_candidate=0, fetched=0, unreadable=0, no_anchor=0, adopted=0, access_reason=0, page_not_naming_pi=0)
    log = []
    done = 0
    for r in doc['labs']:
        research_output = 'selected_url_is_research_output' in (r.get('evidence_gaps') or [])
        if not research_output and (r.get('coverage') != 'reason' or r.get('reason_code') not in ('profile_only_no_homepage', 'no_web_presence_found')):
            continue
        if a.limit and done >= a.limit:
            break
        stats['rows'] += 1
        cands = candidates(r, cen, live_hosts, school_rx, portal)
        ri_hit = ri.get(' '.join(PL.fold(re.sub(r'\s*\([^)]*\)', '', r['pi'])).split()))
        if not cands and not ri_hit:
            stats['no_candidate'] += 1
            continue
        if a.dry:
            log.append((r['pi'], cands))
            continue
        done += 1
        own = set() | ({LW.normalized_link(r['url'])} if research_output and r.get('url') else set())
        found = None
        read_pages = []
        for u in cands:
            res = W.live(c, u)
            if not res or res[0] != 200:
                stats['unreadable'] += 1
                continue
            stats['fetched'] += 1
            html = W.live_html(c, u)
            if not PL.names(html, r['pi']):
                continue
            read_pages.append((u, res[1]))
            for link, text in profile_anchors(html, u, r['pi'], {LW.normalized_link(u)} | own):
                found = dict(link=link, text=text, on=u, sha=res[1])
                break
            if found:
                break
        if not found and ri_hit:
            found = dict(link=ri_hit[0], text='homepage_url (RI people API)', on=RI_API, sha=ri_hit[1])
        if not found:
            stats['no_anchor'] += 1
            if read_pages and not r.get('read_profile_note'):
                now = time.strftime('%Y-%m-%d', time.gmtime())
                for u, sha in read_pages:
                    r['checks'] = list(r.get('checks') or []) + [dict(source='school_profile', url=u, at=time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime()), result='ok', sha256=sha,
                                                                      provenance='live_profile_page_stage3', note='names the PI; no website or lab link')]
                r['read_profile_note'] = [u for u, _ in read_pages]
                pages = ', '.join(u for u, _ in read_pages[:2])
                site = 'the site a search found is kept in website_note and is not reached from any official page' if r.get('website_note') else 'no site was found by search either'
                r['reason'] = (f"The official profile page{'s' if len(read_pages) > 1 else ''} {pages} (read live {now}) name{'' if len(read_pages) > 1 else 's'} the PI and link nothing labelled as a personal, lab or group website (area or project mentions are not counted); "
                               f"the department listing links none either; {site}.")
            continue
        link, host = found['link'], urlsplit(found['link']).hostname or ''
        chk = dict(source='school_profile_link', url=link, on=found['on'], at=time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime()), result='listed', anchor=found['text'],
                   linked_url=link, source_sha256=found['sha'], provenance='live_profile_page_stage3')
        page = PL.stored_page(a.key, link)
        if not page and host in live_hosts:
            res = W.live(c, link)
            if res and res[0] == 200:
                page = (W.live_html(c, link), res[1])
        if page and PL.names(page[0], r['pi']):
            note = dict(prior_reason_code=r.get('reason_code'), prior_reason=r.get('reason'), prior_url=r.get('url') if research_output else None, why='an official profile page links this site (stage-3 live profile pass)')
            r['website_note'] = dict(r.get('website_note') or {}, **note)
            r.update(coverage='website', url=link, kind='pi_homepage', reason_code='pi_homepage_only_no_lab_site', found_via='school_profile_link', listed_on=found['on'], sha256=page[1],
                     evidence=dict(url=link, sha256=page[1], quote=None, source='profile_link_live_pass'), official_link_status='recorded', official_link_evidence=[chk], verified=True,
                     reason='Captured PI homepage linked from the official profile.')
            for k in ('reason_type', 'reason_scope', 'evidence_gaps'):
                r.pop(k, None)
            r['checks'] = list(r.get('checks') or []) + [chk]
            stats['adopted'] += 1
        elif page:
            stats['page_not_naming_pi'] += 1   # the linked page was read and does not name the PI: not adopted, left as it was
            r['checks'] = list(r.get('checks') or []) + [dict(chk, result='listed_page_does_not_name_pi')]
        else:
            r['checks'] = list(r.get('checks') or []) + [chk]
            r['website_note'] = dict(r.get('website_note') or {}, official_link=link, official_link_on=found['on'], official_link_sha256=found['sha'],
                                     why='the official profile links this site; its page could not be read here (no stored capture, host not live or refused)')
            r.update(reason_code='host_challenge_no_wayback', reason_type='access_blocked',
                     reason=f"The official page {found['on']} links {link} (anchor '{found['text']}'); that page could not be read (no stored capture; host challenge, robots or not a live host), so it is recorded as an access reason, not as absence. No Wayback was used.",
                     reason_scope='Recorded search/access outcome; not proof no website exists or that an archive has no capture.')
            stats['access_reason'] += 1
    if a.dry:
        print(json.dumps(stats)); print(sum(1 for _ in log), 'rows with candidates'); return
    Path(a.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
