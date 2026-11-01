"""DBLP persons affiliated with a school, from DBLP's own dump (never dblp.org): protocol stage 2 census discovery.

One streamed pass over atlas_paths.DBLP_DUMP_XML (two when --pubs):
  pass 1  person records (<www key="homepages/...">) whose <note type="affiliation"> matches the school's affiliation
          regex (schools/<key>.toml [affiliation].regex), or one of whose <url>s is on a school web domain
          ([web].domains, e.g. umich.edu, web.eecs.umich.edu/~x). Notes carry DBLP's own label ('University of Michigan,
          Ann Arbor, MI, USA') and, for former affiliations, a label='former' attribute, kept as `former`.
  pass 2  (--pubs) for those persons: publication counts per year 2016-2026 and the share of their records in the
          window that DBLP indexes at all (every DBLP record is a computing venue), first/last year in the window
-> hierarchy/<key>/dblp-affiliated.json  {school, dump, rule, persons: [{pid, names, affiliations: [{text, former}],
   urls, orcid, matched_by, pubs_by_year, n_window}]}
usage: dblp_affiliated.py <key> [--pubs]     (nice; ~15 min per pass, memory: the person set only)
"""
import collections, json, re, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402
from dblp_dump_persons import records, text, AUTH, NOTE, URL, YEAR  # noqa: E402

NOTE_ATTR = re.compile(r'<note([^>]*)type="affiliation"([^>]*)>(.*?)</note>', re.S)


def main(key, pubs=False):
    cfg = S.get(key); aff = S.aff_rx(key)
    doms = [d.lower() for d in (cfg.get('web') or {}).get('domains') or []]
    xhosts = [d.lower() for d in (cfg.get('web') or {}).get('excluded_hosts') or []]  # other campuses on the domain

    def school_host(u):
        h = re.sub(r'^https?://', '', u).split('/')[0].split(':')[0].lower()
        return any(h == d or h.endswith('.' + d) for d in doms) and not any(h == x or h.endswith('.' + x) for x in xhosts)
    persons = {}
    t0 = time.time()
    for typ, k, body in records():
        if typ != 'www' or not k.startswith('homepages/'):
            continue
        affs = [dict(text=text(v), former='former' in (a + b)) for a, b, v in NOTE_ATTR.findall(body)]
        urls = [text(u) for u in URL.findall(body)]
        by = []
        if any(aff.search(a['text']) for a in affs):
            by.append('affiliation_note')
        if any(school_host(u) for u in urls):
            by.append('url_domain')
        if not by:
            continue
        pid = 'https://dblp.org/pid/' + k.split('/', 1)[1]
        persons[pid] = dict(pid=pid, names=[text(a) for _, a in AUTH.findall(body)], affiliations=affs, urls=urls,
                            orcid=sorted({m.group(1) for u in urls for m in [re.search(r'orcid\.org/([0-9X-]{19})', u)] if m}),
                            matched_by=by, disambiguation=any(t == 'disambiguation' for t, _ in NOTE.findall(body)))
    print(json.dumps(dict(pass1=len(persons), secs=round(time.time() - t0))), flush=True)
    if pubs:
        owner = collections.defaultdict(set)
        for pid, p in persons.items():
            for n in p['names']:
                owner[n].add(pid)
        cnt = {pid: collections.Counter() for pid in persons}
        for typ, k, body in records():
            if typ in ('www', 'data'):
                continue
            hit = {u for _, a in AUTH.findall(body) for u in owner.get(text(a), ())}
            if not hit:
                continue
            y = YEAR.search(body); y = int(y.group(1)) if y else None
            for u in hit:
                cnt[u][y] += 1
        lo, hi = cfg.get('window') or [2016, 2026]
        for pid, p in persons.items():
            c = cnt[pid]
            p['pubs_by_year'] = {str(y): c[y] for y in sorted(y for y in c if y and lo <= y <= hi)}
            p['n_window'] = sum(p['pubs_by_year'].values()); p['n_all'] = sum(c.values())
    out = P.data('dblp-affiliated.json', key)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(school=key, dump=P.DBLP_DUMP_FILE, rule=__doc__.split('\n-> ')[0], built_at=time.strftime('%Y-%m-%dT%H:%M:%S'),
                                   persons=sorted(persons.values(), key=lambda p: p['names'][0] if p['names'] else '')), indent=1, ensure_ascii=False))
    print(json.dumps(dict(persons=len(persons), out=str(out), secs=round(time.time() - t0))), flush=True)


if __name__ == '__main__':
    main(sys.argv[1], '--pubs' in sys.argv)
