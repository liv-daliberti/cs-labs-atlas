"""Websites the school's own profile pages link, for register rows that have no website (stage 3, Stanford 2026-11-10).

Why: Stanford lab and personal sites live on *.stanford.edu, so the lab-page discovery treats them as institutional and records `profile_only_no_homepage`
even when the PI's profile links 'Lab Website' / 'Personal Site' (fresh reviewer, 20 rows: 14 had such a link). For every register row with coverage reason or
pending, this reads the PI's official profile pages (stored captures, plus the live profile `?tab=bio` page, robots honoured through tools/school_web.py) for outgoing
anchors that name a website/homepage/lab/group, keeps a link whose page the fetcher can read and that names the PI, and records it as the PI's website with an
official `school_profile_link` check (profile URL, anchor, profile sha256). A link whose host refuses the crawler (robots, 403, challenge) becomes an access
reason with the official link kept in website_note; nothing is worked around and nothing goes through Wayback. The earlier reason is kept in `prior_reason`.
usage: profile_site_links.py <key> --in <register.json> --out <register.json> [--fetch] [--limit N]
"""
import argparse
import json
import re
import time
import zlib
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import atlas_paths as P  # noqa: E402
import lab_websites as LW  # noqa: E402
import school_web as W  # noqa: E402

ANCHOR = re.compile(r'<a\b[^>]*?href\s*=\s*["\']([^"\'#][^"\']*)["\'][^>]*>(.*?)</a>', re.I | re.S)
TAG = re.compile(r'<[^>]+>')
KEYWORD = re.compile(r'web\s?site|home\s?page|personal|\blab\b|laborator|\bgroup\b|\bmy\b|research (?:group|page)|\bcentre\b|\bcenter\b', re.I)
GENERIC_HOSTS = re.compile(r'(?:^|\.)(?:stanford\.edu|stanfordhealthcare\.org|stanfordchildrens\.org|orcid\.org|doi\.org|google\.com|linkedin\.com|twitter\.com|x\.com|'
                           r'facebook\.com|youtube\.com|webofscience\.com|pubmed\.gov|nih\.gov|dblp\.org|openalex\.org|wikipedia\.org|instagram\.com|researchgate\.net)$', re.I)
STANFORD_GENERIC_PATH = re.compile(r'^(?:www|visit|giving|profiles|cs|engineering|soe|med|ee|me|statistics|stanford)\.stanford\.edu$|^(?:www\.)?stanford\.edu$', re.I)
GENERIC_PROFILE_LINK = re.compile(r'/(?:people|profile|profiles|intranet|directory|faculty|search|about|news|events)(?:/|$|\?)', re.I)


def fold(t):
    import unicodedata
    return re.sub(r'[^a-z ]+', ' ', unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower())


def family(pi):
    return fold(pi).split()[-1] if fold(pi).split() else ''


def stored_html(school, url):
    """(html, sha256) of a stored 200 capture of exactly this URL in the audit/lab-page stores, else None."""
    import sqlite3
    for name in ('labpage-audit-captures.sqlite', 'labpage-captures.sqlite'):
        p = P.data(name, school)
        if not Path(p).exists():
            continue
        c = sqlite3.connect(f'file:{p}?mode=ro', uri=True)
        r = c.execute('select content, sha256 from captures where url=? and status=200 and capture_url is null order by id desc limit 1', (url,)).fetchone()
        if r and r[0]:
            b = r[0]
            try:
                b = zlib.decompress(b)
            except Exception:  # noqa: BLE001
                pass
            return (b.decode('utf-8', 'replace') if isinstance(b, bytes) else b), r[1]
    return None


def profile_pages(row, domain):
    out, seen = [], set()
    for c in row.get('checks') or []:
        u = c.get('url') or ''
        if c.get('source') not in ('school_profile', 'department_listing', 'pi_evidence_url') or not u.startswith('http'):
            continue
        sp = urlsplit(u)
        if 'web.archive.org' in (sp.hostname or '') or not re.search(r'(?:^|\.)' + domain + r'$', sp.hostname or ''):
            continue
        if sp.path.rstrip('/').count('/') < 1 or re.search(r'/(?:faculty|people|directory)/?$|faculty-name|adjunct|courtesy|emerit', sp.path):
            continue   # a listing, not the PI's page
        base = u.split('?')[0].split('#')[0]
        for v in (base, base + '?tab=bio'):
            if 'profiles.stanford.edu' not in v and v.endswith('?tab=bio'):
                continue
            if v not in seen:
                seen.add(v); out.append(v)
    return out


def candidate_links(html, base, pi):
    out = []
    for href, inner in ANCHOR.findall(html or ''):
        if href.startswith(('mailto:', 'tel:', 'javascript:')):
            continue
        u = urljoin(base, href.replace('&amp;', '&'))
        sp = urlsplit(u)
        if sp.scheme not in ('http', 'https') or not sp.hostname:
            continue
        text = ' '.join(TAG.sub(' ', inner).split())
        host = sp.hostname.lower()
        generic_site = bool(GENERIC_HOSTS.search(host)) and not (host.endswith('.stanford.edu') and not STANFORD_GENERIC_PATH.match(host))
        if host.endswith('.stanford.edu') and STANFORD_GENERIC_PATH.match(host):
            # a path on a department host is a PI page only when it is a ~user page or names the PI
            generic_site = not (re.search(r'/~[^/]+', sp.path) or family(pi) in fold(sp.path))
        if generic_site or GENERIC_PROFILE_LINK.search(sp.path) and host == urlsplit(base).hostname:
            continue
        if not (KEYWORD.search(text) or family(pi) in fold(host + ' ' + sp.path)):
            continue
        out.append((u, text))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('key'); ap.add_argument('--in', dest='inp', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--fetch', action='store_true', help='fetch live profile ?tab=bio pages and the linked sites (robots honoured, paced)')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()
    import labpage_audit as L
    doc = json.loads(Path(a.inp).read_text())
    domain = L.SCHOOLS[a.key]['domain']
    c = W.con(a.key)
    stats = dict(rows=0, with_link=0, website=0, access_reason=0, unreadable=0, not_pi=0, no_link=0)
    now = lambda: time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime())  # noqa: E731
    n = 0
    for r in doc['labs']:
        if r.get('coverage') not in ('reason', 'pending') or r.get('reason_type') == 'pending_archive' or \
                any(str(x.get('provenance', '')).startswith('stage3_excluded') for x in r.get('checks') or []):
            continue   # (pending_archive rows wait for the Wayback job; PI-excluded rows have no profile of a PI)
        if a.limit and n >= a.limit:
            break
        n += 1; stats['rows'] += 1
        cands = []
        for pu in profile_pages(r, domain):
            got = stored_html(a.key, pu)
            html, sha = got if got else (None, None)
            if a.fetch and (html is None or pu.endswith('?tab=bio')):
                res = W.live(c, pu)
                if res and res[0] == 200:
                    html, sha = W.live_html(c, pu), res[1]
            if not html:
                continue
            for u, text in candidate_links(html, pu, r['pi']):
                cands.append((u, text, pu, sha))
        noted = (r.get('website_note') or {}).get('replaced_url')
        seen, uniq = set(), []
        for u, text, pu, sha in cands:
            k = LW.normalized_link(u)
            if k not in seen:
                seen.add(k); uniq.append((u, text, pu, sha))
        # a lab link first, then the others
        uniq.sort(key=lambda x: (not re.search(r'lab|group|center|centre', x[1], re.I), x[0]))
        if noted and not any(LW.normalized_link(noted) == LW.normalized_link(u) for u, *_ in uniq):
            pass
        if not uniq:
            stats['no_link'] += 1
            continue
        stats['with_link'] += 1
        chosen, blocked = None, None
        for u, text, pu, sha in uniq[:4]:
            if LW.selection_gaps(u):
                continue
            if not a.fetch:
                continue
            res = W.live(c, u)
            if res is None:
                blocked = blocked or (u, text, pu, sha, 'robots_or_blocked')
                continue
            st, body_sha, blocks = res
            if st in (401, 403, 429, 999):
                blocked = blocked or (u, text, pu, sha, f'http_{st}')
                continue
            if st != 200 or not body_sha:
                continue
            if family(r['pi']) not in fold(W.flat(blocks)) and family(r['pi']) not in fold(u):
                stats['not_pi'] += 1
                continue
            chosen = (u, text, pu, sha, body_sha)
            break
        if chosen:
            u, text, pu, sha, body_sha = chosen
            link = dict(source='school_profile_link', url=u, on=pu, at=now(), result='listed', anchor=text, linked_url=u, source_sha256=sha, provenance='stage3_profile_links_2026-11-10')
            site = dict(source='candidate_site', url=u, at=now(), result='ok', provenance='stage3_profile_links_2026-11-10')
            kind = 'lab_site' if re.search(r'lab|group|center|centre', text + ' ' + urlsplit(u).hostname, re.I) else 'pi_homepage'
            r['prior_reason'] = dict(reason_code=r.get('reason_code'), reason=r.get('reason'), reason_type=r.get('reason_type'))
            for k in ('reason', 'reason_type', 'reason_scope', 'evidence_gaps', 'review_note'):
                r.pop(k, None)
            r['checks'] = list(r.get('checks') or []) + [site, link]
            r.update(coverage='website', url=u, kind=kind, reason_code='lab_site' if kind == 'lab_site' else 'pi_homepage_only_no_lab_site', sha256=body_sha,
                     evidence=dict(url=u, sha256=body_sha, quote=None), found_via='school_profile_link', listed_on=pu, official_link_status='recorded',
                     official_link_evidence=[link], status='found', reason='Website linked from the PI\'s official profile page and read by the crawler; it names the PI.')
            stats['website'] += 1
        elif blocked:
            u, text, pu, sha, why = blocked
            link = dict(source='school_profile_link', url=u, on=pu, at=now(), result='listed', anchor=text, linked_url=u, source_sha256=sha, provenance='stage3_profile_links_2026-11-10')
            r['checks'] = list(r.get('checks') or []) + [link, dict(source='candidate_site', url=u, at=now(), result=why)]
            r['website_note'] = dict(replaced_url=u, why='official profile links this site but the crawler may not read it (' + why + '); kept as a lead, not a selected website', anchor=text, profile=pu)
            r.update(coverage='reason', reason_code='host_blocked_by_robots' if 'robots' in why else 'host_access_blocked', reason_type='access_blocked',
                     reason=f"The official profile ({pu}) links {u} ('{text}'), but the host refuses this crawler ({why}); no Wayback use here. Recorded access outcome.",
                     reason_scope='Recorded search/access outcome; not proof no website exists or that an archive has no capture.')
            stats['access_reason'] += 1
        else:
            stats['unreadable'] += 1
    Path(a.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
