"""DBLP person ids for a Han-name school's census people by DIRECT URL BINDING (owner-accepted rule, D-0005 note 2026-11-18).

dblp_ids_school.py finds candidates by Latin name forms, which a roster of Han names never matches. Here the join is the roster's own link: a
DBLP person record (`<www key="homepages/...">`, DBLP's dump, never dblp.org) that lists as `<url>` the profile page the department roster
links for a person (resolved against the capture's original URL) is that person's record. The URL is the identity; no pinyin or name form is used.
A URL that two different roster people link, or two DBLP records that list, is ambiguous and binds nobody.

  dblp_url_binding_school.py <key> [--csrankings <recall.json>]
                                         with --csrankings, a CSRankings entry's homepage (its DBLP pid, as scratch/pi-recall-1118/recall.json candidates carry them:
                                         csr in srcs, one dblp pid) counts as a URL the DBLP record lists, basis 'csrankings_homepage_url'; writes/merges hierarchy/<key>/dblp-ids.json {person: {pid, basis: 'homepage_url', url, dump, sha256, quote,
                                         orcid, names, candidates: 1, n_window, roster_profile, roster_evidence}} (existing pids are never overwritten)
"""
import collections, hashlib, json, re, sys, urllib.parse

import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
from dblp_dump_persons import records, text, AUTH, URL, YEAR  # noqa: E402


def nurl(u):
    u = re.sub(r'^https?://(?:www\.)?', '', (u or '').strip().lower())
    u = re.sub(r'^([^/]+?):(?:80|443)(?=/|$)', r'\1', u)
    u = re.sub(r'(?i)/(?:zh_cn|en)(?:/index\.html?)?$', '', u.split('#')[0].rstrip('/'))   # the language variants of one personal-site page (jszy/faculty.* /zh_CN, /en)
    return re.sub(r'/index\.html?$', '', u).rstrip('/')


def original_of(capture_url):
    m = re.search(r'/web/\d{14}[a-z_]*/(https?://.+)$', capture_url or '')
    return m.group(1) if m else capture_url


def roster_urls(rows):
    """{normalized absolute profile url: {person: evidence}} from the saved listing rows (profile, quote, capture, sha)."""
    out = collections.defaultdict(dict)
    for r in rows:
        prof = r.get('profile')
        if not prof or not r.get('capture_url'):
            continue
        absu = urllib.parse.urljoin(original_of(r['capture_url']), prof)
        out[nurl(absu)].setdefault(r['name'], dict(url=r['capture_url'], sha256=r['sha256'], quote=r['quote'], profile=absu))
    return out


def bind(rows, dblp_recs):
    """[(person, record, roster evidence)] for unambiguous URL matches. dblp_recs: [{pid, urls, ...}]."""
    ru = roster_urls(rows)
    by_url = collections.defaultdict(list)
    for rec in dblp_recs:
        for u in rec['urls']:
            if nurl(u) in ru:
                by_url[nurl(u)].append(rec)
    hits = collections.defaultdict(set)
    for u, recs in by_url.items():
        for rec in recs:
            for person in ru[u]:
                hits[person].add((rec['pid'], u))
    out = []
    for person, h in hits.items():
        pids = {p for p, _ in h}
        if len(pids) != 1:
            continue
        pid, u = sorted(h)[0]
        if any(len(ru[x]) != 1 or len({r['pid'] for r in by_url[x]}) != 1 for _, x in h):
            continue   # a url linked by several roster people or listed by several DBLP records
        rec = next(r for r in by_url[u] if r['pid'] == pid)
        out.append((person, rec, ru[u][person], u))
    return out


def main(key, recall=None):
    rows = json.loads(P.data('rows.json', key).read_text())
    ru = roster_urls(rows)
    recs = []
    csr = {}   # dblp pid suffix -> CSRankings homepages
    if recall:
        for c in json.load(open(recall))['candidates'].get(key, []):
            if 'csr' in (c.get('srcs') or []) and len(c.get('dblp') or []) == 1:
                csr.setdefault(c['dblp'][0], []).extend('http://' + h if not h.startswith('http') else h for h in c.get('home') or [])
    for typ, k, body in records():
        if typ != 'www' or not k.startswith('homepages/'):
            continue
        urls = [text(u) for u in URL.findall(body)]
        extra = csr.get(k.split('/', 1)[1], [])
        n_dblp = len(urls)
        urls = urls + [u for u in extra if u not in urls]
        if not any(nurl(u) in ru for u in urls):
            continue
        recs.append(dict(n_dblp=n_dblp, pid='https://dblp.org/pid/' + k.split('/', 1)[1], urls=urls, names=[text(a) for _, a in AUTH.findall(body)],
                         orcid=sorted({m.group(1) for u in urls for m in [re.search(r'orcid\.org/([0-9X-]{19})', u)] if m}),
                         sha256=hashlib.sha256(body.encode()).hexdigest()))
    bound = bind(rows, recs)
    lo, hi = (S.get(key).get('window') or [2016, 2026])
    owner = {nm: r['pid'] for _, r, _, _ in bound for nm in r['names']}
    cnt = collections.Counter()
    for typ, k, body in records():
        if typ in ('www', 'data'):
            continue
        hit = {owner[a] for _, a in AUTH.findall(body) for a in [text(a)] if a in owner}
        y = YEAR.search(body)
        if hit and y and lo <= int(y.group(1)) <= hi:
            for p in hit:
                cnt[p] += 1
    out_p = P.data_w('dblp-ids.json', key)
    cur = json.loads(out_p.read_text()) if out_p.exists() else {}
    n = 0
    for person, rec, ev, u in sorted(bound):
        if (cur.get(person) or {}).get('pid'):
            continue
        cur[person] = dict(pid=rec['pid'], basis='homepage_url' if any(nurl(x) == u for x in rec['urls'][:rec['n_dblp']]) else 'csrankings_homepage_url', url=rec['pid'], dump=P.DBLP_DUMP_FILE, sha256=rec['sha256'],
                           quote=f"<url>{next(x for x in rec['urls'] if nurl(x) == u)}</url>", orcid=rec['orcid'], names=rec['names'], candidates=1,
                           n_window=cnt[rec['pid']], roster_profile=ev['profile'], roster_evidence=dict(url=ev['url'], sha256=ev['sha256'], quote=ev['quote']))
        n += 1
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(cur, indent=1, ensure_ascii=False))
    print(json.dumps(dict(key=key, roster_profile_urls=len(ru), dblp_records_linking=len(recs), bound=len(bound), written=n)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[sys.argv.index('--csrankings') + 1] if '--csrankings' in sys.argv else None)
