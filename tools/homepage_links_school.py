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
import collections, json, re, sqlite3, sys, zlib
from pathlib import Path

import atlas_paths as P  # noqa: E402
import school_web as W  # noqa: E402
import periods_school as PS  # noqa: E402

DBLP = re.compile(r'href=["\']?(https?://(?:www\.)?dblp\.(?:org|uni-trier\.de)/pid/([\w/-]+?)(?:\.html)?)["\'#?>\s]', re.I)
ORCID = re.compile(r'href=["\']?(https?://(?:www\.)?orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX]))', re.I)


def register_pages(labs, dbs):
    """{pi: [(url, sha256, html)]} of the register-chosen website of each lab row (coverage 'website' with a url), from the newest stored 200
    capture of that url (url or final_url) in the first of `dbs` that has one."""
    out = {}
    for lab in labs:
        u = lab.get('url')
        if not u or lab.get('coverage') not in (None, 'website'):
            continue
        for db in dbs:
            if not Path(db).exists():
                continue
            con = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=60)
            try:
                r = con.execute('select sha256, content from captures where (url=? or final_url=?) and status=200 and content is not null '
                                'order by (url=?) desc, id desc limit 1', (u, u, u)).fetchone()
            except sqlite3.OperationalError:
                r = None
            con.close()
            if r:
                try:
                    body = zlib.decompress(r[1])
                except zlib.error:
                    body = r[1]
                out.setdefault(lab['pi'], []).append((u, r[0], body.decode('utf-8', 'replace')))
                break
    return out


def main(key):
    c = W.con(key); out, n = {}, collections.Counter()
    reg = P.data('lab-websites.json', key)
    site = register_pages(json.loads(reg.read_text()).get('labs', []) if reg.exists() else [],
                          [P.data('labpage-audit-captures.sqlite', key), P.data('labpage-captures.sqlite', key)])
    for t in PS.targets(key):
        fam = t['name'].split()[-1].lower()
        pages = []
        for u in t['urls']:
            r = c.execute('select status, sha256, raw_zlib from live where url=?', (u,)).fetchone()
            if r and r[0] == 200 and r[2]:
                pages.append((u, r[1], zlib.decompress(r[2]).decode('utf-8', 'replace')))
            for cap, sha, raw in c.execute('select capture_url, sha256, raw_zlib from captures where page_url=? and http_status=200', (u,)):
                if raw:
                    pages.append((cap, sha, W.body(raw).decode('utf-8', 'replace')))
        pages += site.get(t['name'], [])
        d, o = {}, {}
        for u, sha, h in pages:
            if fam not in h.lower():
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
    print(json.dumps(dict(pis=len(PS.targets(key)), **n)))


if __name__ == '__main__':
    main(sys.argv[1])
