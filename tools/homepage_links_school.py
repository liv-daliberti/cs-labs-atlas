"""Identity links on a protocol school's PI homepages (protocol stage 5): the DBLP person page and the ORCID a PI's own
homepage links. The pages are the ones tools/periods_school.py fetched (live where allowed, else Wayback id_ captures in
captures/<key>.sqlite); nothing new is fetched. A school with a lab-websites register also gets each PI's register-chosen website, read
from the stage-3 capture stores (hierarchy/<key>/raw/labpage-audit-captures.sqlite, labpage-captures.sqlite) by url or final_url: a PI's own
homepage is where a dblp.org/pid or orcid.org link usually is (UMD 2026-11-25: 10 + 10 such links the department profiles never carry).

link     an <a href> to dblp.org/pid/<pid> (or dblp.uni-trier.de/pid/...) or to orcid.org/<id> on a page whose text names
         the PI's family name; the quote is the href exactly as on the page, the sha256 that of the stored page
decision one distinct DBLP pid (or ORCID) across the PI's pages is the PI's; several distinct ones are left out and listed
-> hierarchy/<key>/homepage-identity.json {pi: {dblp: {pid, url, sha256, quote} | null, orcid: [..], conflicts: [..]}};
   census_build.py takes the DBLP pid when tools/dblp_ids_school.py decided none, and adds the ORCIDs
usage: homepage_links_school.py <key>
"""
import collections, json, re, sys, zlib

import atlas_paths as P  # noqa: E402
import school_web as W  # noqa: E402
import periods_school as PS  # noqa: E402

DBLP = re.compile(r'href=["\']?(https?://(?:www\.)?dblp\.(?:org|uni-trier\.de)/pid/([\w/-]+?)(?:\.html)?)["\'#?>\s]', re.I)
ORCID = re.compile(r'href=["\']?(https?://(?:www\.)?orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX]))', re.I)


def register_pages(key):
    """{pi: [(url, sha256, html)]}: the stored pages of the lab-websites register's VERIFIED website rows (the PI's own homepage or lab page, an official profile
    links it and it names the PI: lab_websites.verify_websites). A Han-keyed PI's English homepage never holds the Han name, so the stage-4 homepage fetch
    alone misses it (PKU 2026-11-25)."""
    import sqlite3

    from lab_websites import capture_stores
    f = P.data('lab-websites.json', key)
    if not f.exists():
        return {}
    rows = [r for r in json.loads(f.read_text()).get('labs', []) if r.get('coverage') == 'website' and r.get('verified') and r.get('sha256') and r.get('url')]
    out = {}
    for path in capture_stores(key):
        con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        for r in rows:
            if any(r['pi'] == pi_ and r['sha256'] == sh_ for pi_, ls_ in out.items() for _, sh_, _ in ls_):
                continue
            row = con.execute('select content from captures where sha256=? and content is not null limit 1', (r['sha256'],)).fetchone()
            if row:
                b = row[0]
                try:
                    b = zlib.decompress(b)
                except zlib.error:
                    pass
                out.setdefault(r['pi'], []).append((r['url'], r['sha256'], b.decode('utf-8', 'replace')))
    return out


def main(key):
    c = W.con(key); out, n = {}, collections.Counter()
    reg = register_pages(key)
    latin = {x['pi']: [y.lower() for y in x.get('names') or [] if y.isascii()] for x in json.loads(P.data('pis.json', key).read_text())}
    for t in PS.targets(key):
        fam = t['name'].split()[-1].lower()
        pages = list(reg.get(t['name'], []))
        for u in t['urls']:
            r = c.execute('select status, sha256, raw_zlib from live where url=?', (u,)).fetchone()
            if r and r[0] == 200 and r[2]:
                pages.append((u, r[1], zlib.decompress(r[2]).decode('utf-8', 'replace')))
            for cap, sha, raw in c.execute('select capture_url, sha256, raw_zlib from captures where page_url=? and http_status=200', (u,)):
                if raw:
                    pages.append((cap, sha, W.body(raw).decode('utf-8', 'replace')))
        d, o = {}, {}
        for u, sha, h in pages:
            if fam not in h.lower() and not any(nm in h.lower() for nm in latin.get(t['name'], [])) and (u, sha) not in {(a, b) for a, b, _ in reg.get(t['name'], [])}:
                continue
            for m in DBLP.finditer(h):
                d.setdefault('https://dblp.org/pid/' + m.group(2).rstrip('/'), dict(url=u, sha256=sha, quote=m.group(1)))
            for m in ORCID.finditer(h):
                o.setdefault(m.group(2), dict(orcid=m.group(2), url=u, sha256=sha, quote=m.group(1)))
        rec = dict(dblp=None, orcid=list(o.values()), conflicts=[])
        if len(d) == 1:
            pid, ev = next(iter(d.items())); rec['dblp'] = dict(pid=pid, **ev); n['dblp'] += 1
        elif len(d) > 1:
            rec['conflicts'] = sorted(d); n['dblp_conflict'] += 1
        n['orcid'] += bool(o)
        if rec['dblp'] or rec['orcid'] or rec['conflicts']:
            out[t['name']] = rec
    P.data_w('homepage-identity.json', key).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    # census ADDITIONS take stage-5 DBLP ids only from dblp-ids.json (pihier.census.fold_dblp_ids): a homepage-linked pid goes there too, for a PI with none
    f = P.data('dblp-ids.json', key)
    ids = json.loads(f.read_text()) if f.exists() else {}
    for name, rec in out.items():
        if rec['dblp'] and not (ids.get(name) or {}).get('pid'):
            ev = rec['dblp']
            ids[name] = dict(pid=ev['pid'], basis='homepage_link', confidence='medium', url=ev['pid'], quote=ev['quote'], sha256=ev['sha256'],
                             homepage=ev['url'], orcid=[o['orcid'] for o in rec['orcid']], candidates=1)
            n['merged_into_dblp_ids'] += 1
    P.data_w('dblp-ids.json', key).write_text(json.dumps(ids, indent=1, ensure_ascii=False))
    print(json.dumps(dict(pis=len(PS.targets(key)), **n)))


if __name__ == '__main__':
    main(sys.argv[1])
