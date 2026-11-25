"""Identity links on a protocol school's PI homepages (protocol stage 5): the DBLP person page and the ORCID a PI's own
homepage links. The pages are the ones tools/periods_school.py fetched (live where allowed, else Wayback id_ captures in
captures/<key>.sqlite); nothing new is fetched.

link     an <a href> to dblp.org/pid/<pid> (or dblp.uni-trier.de/pid/...) or to orcid.org/<id> on a page whose text names
         the PI's family name; the quote is the href exactly as on the page, the sha256 that of the stored page
decision one distinct DBLP pid (or ORCID) across the PI's pages is the PI's; several distinct ones are left out and listed
-> hierarchy/<key>/homepage-identity.json {pi: {dblp: {pid, url, sha256, quote} | null, orcid: [..], conflicts: [..]}};
   census_build.py takes the DBLP pid when tools/dblp_ids_school.py decided none, and adds the ORCIDs
usage: homepage_links_school.py <key> [--fetch]     (--fetch: also read the pages of the reviewed website register that no earlier step stored, live, robots honoured)
"""
import collections, json, re, sys, unicodedata, zlib

import atlas_paths as P  # noqa: E402
import school_web as W  # noqa: E402
import periods_school as PS  # noqa: E402
import school_config as S  # noqa: E402

DBLP = re.compile(r'href=["\']?(https?://(?:www\.)?dblp\.(?:org|uni-trier\.de)/pid/([\w/-]+?)(?:\.html)?)["\'#?>\s]', re.I)
ORCID = re.compile(r'href=["\']?(https?://(?:www\.)?orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX]))', re.I)


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s or '') if not unicodedata.combining(c)).lower()


def page_links(h, family):
    """({dblp person url: {quote}}, {orcid: {quote}}) of a page whose text names the family name (accent-folded: 'Čapkun' / 'Capkun')."""
    if fold(family) not in fold(h):
        return {}, {}
    d = {'https://dblp.org/pid/' + m.group(2).rstrip('/'): dict(quote=m.group(1)) for m in DBLP.finditer(h)}
    o = {m.group(2): dict(orcid=m.group(2), quote=m.group(1)) for m in ORCID.finditer(h)}
    return d, o


def register_urls(key):
    """{PI: [live urls]} of the reviewed website register (lab-websites.json website rows, plus person-website-review.json found rows):
    the PI's own pages, which the listing and census urls do not cover (2026-11-25: 2 ORCIDs for 231 PIs because only those were read)."""
    out = collections.defaultdict(list)
    reg = P.data('lab-websites.json', key)
    for r in (json.loads(reg.read_text()).get('labs') or []) if reg.exists() else []:
        if r.get('coverage') == 'website' and r.get('url') and 'web.archive.org' not in r['url']:
            out[r['pi']].append(r['url'])
    return out


def main(key, fetch=False):
    c = W.con(key); out, n = {}, collections.Counter()
    reg = register_urls(key)
    for t in PS.targets(key):
        fam = t['name'].split()[-1]
        pages = []
        for u in list(dict.fromkeys(t['urls'] + reg.get(t['name'], []))):
            if fetch and u in reg.get(t['name'], []) and not c.execute('select 1 from live where url=? and status=200', (u,)).fetchone():
                host = re.sub(r'^https?://', '', u).split('/')[0].lower()
                if S.host_use(key, host) == 'live' and host not in W._blocked:
                    W.live(c, u)
            r = c.execute('select status, sha256, raw_zlib from live where url=?', (u,)).fetchone()
            if r and r[0] == 200 and r[2]:
                pages.append((u, r[1], zlib.decompress(r[2]).decode('utf-8', 'replace')))
            for cap, sha, raw in c.execute('select capture_url, sha256, raw_zlib from captures where page_url=? and http_status=200', (u,)):
                if raw:
                    pages.append((cap, sha, W.body(raw).decode('utf-8', 'replace')))
        d, o = {}, {}
        for u, sha, h in pages:
            pd, po = page_links(h, fam)
            for k, v in pd.items():
                d.setdefault(k, dict(url=u, sha256=sha, **v))
            for k, v in po.items():
                o.setdefault(k, dict(url=u, sha256=sha, **v))
        rec = dict(dblp=None, orcid=list(o.values()), conflicts=[])
        if len(d) == 1:
            pid, ev = next(iter(d.items())); rec['dblp'] = dict(pid=pid, **ev); n['dblp'] += 1
        elif len(d) > 1:
            rec['conflicts'] = sorted(d); n['dblp_conflict'] += 1
        n['orcid'] += bool(o)
        if rec['dblp'] or rec['orcid'] or rec['conflicts']:
            out[t['name']] = rec
    P.data_w('homepage-identity.json', key).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(dict(pis=len(PS.targets(key)), **n)))


if __name__ == '__main__':
    main(sys.argv[1], fetch='--fetch' in sys.argv)
