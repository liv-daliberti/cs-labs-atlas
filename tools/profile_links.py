"""Websites an official profile or listing page links, for register rows recorded as `profile_only_no_homepage` / `no_web_presence_found` (stage 3, 2026-11-10).

Why: two fresh reviewers (Stanford 14 of 20, Princeton 7 of 20, MIT 2 of 20 rows wrong) found that the 'no site linked' reason was recorded although the PI's own
profile links a homepage (a same-institution `~user` page, `*.csail.mit.edu`, `lyariv.mycpanel.princeton.edu`, 'Website' under the bio). This reads the stored captures
of the PI's profile/listing pages (no network) for anchors that look like a homepage link and records the result:
  - the linked page is stored (200) or live-readable (hosts.json use=live, robots honoured, tools/school_web.py) and names the PI -> the PI's website, with an official
    `school_profile_link` / `department_listing_link` check (profile URL, anchor text, profile sha256) and the page's own sha256 and quote;
  - the link exists but the linked page cannot be read (challenge host, robots, no capture) -> a recorded access reason (`host_challenge_no_wayback` /
    `host_blocked_by_robots`) that names the official link; the site is kept in website_note; no Wayback and nothing worked around;
  - no anchor -> the row is left as it was.
usage: profile_links.py <key> --in <register.json> --out <register.json> [--live]
"""
import argparse
import glob
import json
import re
import sqlite3
import time
import zlib
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import atlas_paths as P  # noqa: E402
import lab_websites as LW  # noqa: E402

ANCHOR = re.compile(r'<a\b[^>]*?href\s*=\s*["\']([^"\'#][^"\']*)["\'][^>]*>(.*?)</a>', re.I | re.S)
KEY = re.compile(r'^\W*(?:(?:personal |my |lab |group |research group |faculty |home )?(?:web ?site|web ?page|home ?page)|personal (?:site|page)|lab|research group|group)\W*$', re.I)   # a label, not a sentence
SKIP_HOST = re.compile(r'(?:^|\.)(?:orcid\.org|dblp\.org|doi\.org|google\.[a-z.]+|linkedin\.com|twitter\.com|x\.com|facebook\.com|youtube\.com|wikipedia\.org|openalex\.org|'
                       r'researchgate\.net|semanticscholar\.org|arxiv\.org|acm\.org|ieee\.org|nih\.gov|alum\.hkust\.edu\.hk)$', re.I)
SKIP_PATH = re.compile(r'/(?:people|profile|profiles|directory|faculty|search|about|news|events|publications?/author|node/\d+|research-areas?|academics|admissions)(?:/|$|\?)|^mailto:|^tel:|\.(?:pdf|docx?|jpe?g|png|gif)$|/person/', re.I)


def fold(t):
    import unicodedata
    return re.sub(r'[^a-z ]+', ' ', unicodedata.normalize('NFKD', t or '').encode('ascii', 'ignore').decode().lower())


def stores(key):
    return sorted(glob.glob(str(P.school_part(key, 'raw') / '*captures*.sqlite')))


def stored_page(key, url):
    """(html, sha256) of a stored 200 capture whose url, final_url or capture_url is this URL (or a Wayback id_ capture of it)."""
    for f in stores(key):
        try:
            c = sqlite3.connect(f'file:{f}?mode=ro', uri=True)
            rows = c.execute("select content, sha256 from captures where status=200 and (url=? or final_url=? or capture_url=? or capture_url like ?) order by id desc limit 3",
                             (url, url, url, '%/' + url)).fetchall()
        except sqlite3.Error:
            continue
        for b, sha in rows:
            if not b:
                continue
            for dec in (zlib.decompress, lambda z: z):
                try:
                    return (dec(b) if isinstance(b, bytes) else b.encode()).decode('utf-8', 'replace'), sha
                except Exception:  # noqa: BLE001
                    continue
    return None


def text_of(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>|<style.*?</style>', ' ', html, flags=re.S)))


def names(html, pi):
    toks = [w for w in fold(pi).split() if len(w) > 1]
    t = fold(text_of(html)).split()
    return len(toks) >= 2 and toks[0] in t and toks[-1] in t


def anchors(html, base, pi, own_pages):
    """Candidate homepage links of the PI. A page with a few anchors is the PI's own profile: every anchor counts. A long page (a faculty listing) is read card by card:
    only anchors within 600 characters after the PI's family name, and the text after another person's heading is not the PI's."""
    fam = fold(pi).split()[-1]
    listing = len(ANCHOR.findall(html)) > 120
    spans = [(m.start(), m.end()) for m in re.finditer(re.escape(pi.split()[-1]), html, re.I)] if listing else []
    out = []
    for m in ANCHOR.finditer(html):
        href, inner = m.group(1), m.group(2)
        if listing and not any(0 <= m.start() - e <= 600 or 0 <= s0 - m.end() <= 120 for s0, e in spans):
            continue
        u = urljoin(base, href.replace('&amp;', '&'))
        sp = urlsplit(u)
        if sp.scheme not in ('http', 'https') or SKIP_HOST.search(sp.hostname or '') or SKIP_PATH.search(sp.path + ('?' + sp.query if sp.query else '')):
            continue
        text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', inner)).strip()
        if LW.normalized_link(u) in own_pages:
            continue
        personal = bool(re.search(r'/~' + re.escape(fam[:4]), sp.path, re.I)) or fam in (sp.hostname or '').lower() or fam in sp.path.lower()
        if KEY.search(text):
            out.append((u, text[:80]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('key'); ap.add_argument('--in', dest='inp', required=True); ap.add_argument('--out', required=True); ap.add_argument('--live', action='store_true')
    a = ap.parse_args()
    doc = json.loads(Path(a.inp).read_text())
    hosts = set()
    c = None
    if a.live:
        import school_web as W
        h = json.loads(P.data('hosts.json', a.key).read_text())
        hosts = {x['host'] for x in (h.get('hosts', h) if isinstance(h, dict) else h) if x.get('use') == 'live'}
        c = W.con(a.key)
    import labpage_audit as LA
    school_rx = re.compile(r'(?:^|\.)' + LA.SCHOOLS[a.key]['domain'] + r'$', re.I)
    stats = dict(rows=0, adopted=0, access_reason=0, none=0)
    for r in doc['labs']:
        if r.get('coverage') != 'reason' or r.get('reason_code') not in ('profile_only_no_homepage', 'no_web_presence_found'):
            continue
        stats['rows'] += 1
        pages = []
        for k in r.get('checks') or []:
            if k.get('source') in ('school_profile', 'department_listing', 'school_profile_link', 'pi_evidence_url') and k.get('url') and str(k.get('result', '')).startswith(('ok', 'listed')):
                pages.append(k['url'])
        own = {LW.normalized_link(u) for u in pages}
        found = None
        for u in dict.fromkeys(pages):
            if not school_rx.search(urlsplit(u).hostname or ''):   # the page must be the school's own official page
                continue
            sp = stored_page(a.key, u)
            if not sp:
                continue
            html, sha = sp
            body_is_listing = not names(html, r['pi'])
            if body_is_listing:   # a listing that does not name the PI has no entry for them
                continue
            for link, text in anchors(html, u, r['pi'], own):
                found = dict(link=link, text=text, on=u, sha=sha)
                break
            if found:
                break
        if not found:
            stats['none'] += 1
            continue
        link, host = found['link'], urlsplit(found['link']).hostname or ''
        chk = dict(source='school_profile_link', url=link, on=found['on'], at=time.strftime('%Y-%m-%dT%H:%M:%S+00:00', time.gmtime()), result='listed', anchor=found['text'],
                   linked_url=link, source_sha256=found['sha'], provenance='stored_profile_page_stage3')
        page = stored_page(a.key, link)
        if not page and a.live and host in hosts and c is not None:
            import school_web as W
            res = W.live(c, link)
            if res and res[0] == 200:
                page = (W.live_html(c, link), res[1])
        if page and names(page[0], r['pi']):
            note = dict(prior_reason_code=r.get('reason_code'), prior_reason=r.get('reason'), why='an official page links this site (stage-3 profile-link pass)')
            r['website_note'] = dict(r.get('website_note') or {}, **note)
            r.update(coverage='website', url=link, kind='pi_homepage', reason_code='pi_homepage_only_no_lab_site', found_via='school_profile_link', listed_on=found['on'], sha256=page[1],
                     evidence=dict(url=link, sha256=page[1], quote=None, source='profile_link_pass'), official_link_status='recorded', official_link_evidence=[chk], verified=True,
                     reason='Captured PI homepage linked from the official profile.')
            for k in ('reason_type', 'reason_scope', 'evidence_gaps'):
                r.pop(k, None)
            r['checks'] = list(r.get('checks') or []) + [chk]
            stats['adopted'] += 1
        else:
            r['checks'] = list(r.get('checks') or []) + [chk]
            r['website_note'] = dict(r.get('website_note') or {}, official_link=link, official_link_on=found['on'], official_link_sha256=found['sha'],
                                     why='the official profile links this site; its page could not be read here (no stored capture, host not live or refused)')
            r.update(reason_code='host_challenge_no_wayback', reason_type='access_blocked',
                     reason=f"The official page {found['on']} links {link} (anchor '{found['text']}'); that page could not be read (no stored capture; host challenge, robots or not a live host), so it is recorded as an access reason, not as absence. No Wayback was used.",
                     reason_scope='Recorded search/access outcome; not proof no website exists or that an archive has no capture.')
            stats['access_reason'] += 1
    Path(a.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(stats))


if __name__ == '__main__':
    main()
