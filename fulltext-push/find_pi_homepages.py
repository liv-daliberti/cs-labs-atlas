"""Homepages of the PIs whose lab pages were never captured (the CS-related faculty added on 2026-10-22..26: EPFL,
Princeton, Berkeley), for the pihomes fallback of labpage_channel.py (2026-10-26).

For each such PI with lab papers still missing:
  1  their department listings (hierarchy/<school>/pis.json 'listings', the census evidence): a listing URL that is a
     profile page (its path carries the PI's family name) is used as is; otherwise the live listing page (fetched once,
     robots.txt honoured, 3 s per request, cached in raw/pihomes.sqlite) gives the profile: the link whose anchor
     text is one of the PI's names
  2  the live profile page: the links reading website / homepage / personal page / lab / group (or whose anchor text is
     itself a URL), off the profile's own path, never social or scholar-index sites
-> raw/pi-homepages-<school>.json {PI: [homepage URLs]} with raw/pi-homepages-<school>-evidence.json (listing, profile,
anchor text per URL). Nothing here downloads papers.
usage: find_pi_homepages.py <school> ... [--dry]
"""
import html, json, re, sqlite3, sys, zlib
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F
import labpage_channel as lc

WEB = re.compile(r'^\W*(?:(?:personal|lab|group|research|faculty|professional|my)\s+)*(?:web\s*site|website|home\s*page|homepage|web\s*page|webpage|'
                 r'site|page|lab(?:oratory)?|group|research group|lab website|group website|visit (?:website|lab|my website))\W*$', re.I)
SOCIAL = ('linkedin.com', 'twitter.com', 'x.com', 'facebook.com', 'instagram.com', 'youtube.com', 'scholar.google.com', 'orcid.org', 'researchgate.net',
          'dblp.org', 'dblp.uni-trier.de', 'github.com', 'wikipedia.org', 'bsky.app', 'mastodon.social', 'academia.edu', 'semanticscholar.org',
          'scopus.com', 'webofscience.com', 'doi.org', 'google.com', 'zoom.us', 'calendly.com')


def links(body, base):
    out = []
    for m in re.finditer(r'<a\s[^>]*href\s*=\s*["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', body, re.S | re.I):
        txt = html.unescape(re.sub(r'<[^>]+>', ' ', m.group(2)))
        txt = re.sub(r'\s+', ' ', txt).strip()
        try:
            u = lc.unwrap(urljoin(base, html.unescape(m.group(1).strip())))
        except ValueError:
            continue
        if u.startswith('http'):
            out.append((u, txt))
    return out


def main():
    import requests
    from lab_channels import Pacer, polite_get
    dry = '--dry' in sys.argv
    s = requests.Session(); s.headers['User-Agent'] = F.UA
    pacer, robots = Pacer(3.0), {}
    cache = sqlite3.connect(str(F.P.FT_RAW / 'pihomes.sqlite'))
    cache.execute('CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, ok INT, fetched_at TEXT, body BLOB)')

    def get(u):
        row = cache.execute('SELECT ok, body FROM pages WHERE url=?', (u,)).fetchone()
        if row:
            return zlib.decompress(row[1]).decode('utf-8', 'replace') if row[0] else None
        if dry:
            return None
        body = polite_get(s, u, pacer, robots)
        cache.execute('INSERT OR REPLACE INTO pages VALUES (?,?,?,?)', (u, int(body is not None), F.now(), zlib.compress((body or '').encode())))
        cache.commit()
        return body

    for school in [a for a in sys.argv[1:] if not a.startswith('--')]:
        ev = {x['pi'] for x in lc.lab_evidence(school)}
        pis = [p for p in json.loads((F.P.data('pis.json', school)).read_text()) if p['pi'] not in ev]
        papers = F.lab_papers(school)
        cs = F.catalog_state(school, with_urls=False)
        missing = Counter(pi for r in papers.values() if not F.is_local(school, r, cs) for pi in r['pis'])
        out_f = F.P.FT_RAW / f'pi-homepages-{school}.json'
        found = json.loads(out_f.read_text()) if out_f.exists() else {}
        evid_f = F.P.FT_RAW / f'pi-homepages-{school}-evidence.json'
        evid = json.loads(evid_f.read_text()) if evid_f.exists() else {}
        n = Counter()
        for p in sorted(pis, key=lambda p: -missing.get(p['pi'], 0)):
            pi = p['pi']
            if not missing.get(pi) or pi in found:
                continue
            names = [x for x in dict.fromkeys([pi] + list(p.get('names') or [])) if x]
            fam = F.nt(pi.split()[-1])
            keys = {F.nt(x) for x in names} | {F.nt(' '.join(reversed(x.split(', ')))) for x in names if ', ' in x}
            profiles = []
            for l in p.get('listings') or []:
                u = lc.unwrap(l.get('url') or '')
                if not u.startswith('http'):
                    continue
                u = re.sub(r'^http://', 'https://', re.sub(r':80/', '/', u))
                if fam and fam in F.nt(urlsplit(u).path):
                    profiles.append((u, None)); continue
                body = get(u)
                if not body:
                    continue
                for v, txt in links(body, u):
                    k = F.nt(txt)
                    if k and (k in keys or any(k.endswith(x) and len(x) >= 8 for x in keys)) and lc.host(v).split('.')[-2:] == lc.host(u).split('.')[-2:]:
                        profiles.append((v, u))
            profiles = list(dict.fromkeys(profiles))[:3]
            n['pis'] += 1; n['with_profile'] += bool(profiles)
            homes = []
            for prof, listing in profiles:
                body = get(prof)
                if not body:
                    continue
                ph = lc.host(prof)
                for v, txt in links(body, prof):
                    h = lc.host(v)
                    if any(h == b or h.endswith('.' + b) for b in SOCIAL) or v.rstrip('/') == prof.rstrip('/'):
                        continue
                    if re.search(r'\.(?:pdf|jpe?g|png|docx?|ics|vcf)$', v, re.I):
                        continue
                    is_url_text = bool(re.match(r'^(?:https?://|www\.)\S+$', txt)) and lc.host('http://' + re.sub(r'^https?://', '', txt)) == h
                    if WEB.match(txt) or is_url_text:
                        if h == ph and not ('~' in v or fam in F.nt(urlsplit(v).path)):
                            continue  # the department site's own navigation
                        homes.append(v)
                        evid.setdefault(pi, []).append(dict(homepage=v, anchor=txt, profile=prof, listing=listing, at=F.now()))
            homes = list(dict.fromkeys(homes))[:3]
            n['with_homepage'] += bool(homes)
            if homes:
                found[pi] = homes
            print(json.dumps(dict(school=school, pi=pi, missing=missing[pi], profiles=[x for x, _ in profiles], homes=homes)), flush=True)
            if not dry:
                out_f.write_text(json.dumps(found, indent=1)); evid_f.write_text(json.dumps(evid, indent=1))
        print(json.dumps(dict(school=school, **n)), flush=True)


if __name__ == '__main__':
    main()
