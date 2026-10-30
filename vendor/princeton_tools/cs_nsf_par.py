# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015/tools/cs_nsf_par.py (sha256 aa30b44bef84b77121343e6a2b67f51ebe6348a168ba106687d1f29619842ad9); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Accepted manuscripts of Princeton CS papers from the NSF Public Access Repository (par.nsf.gov).

NSF requires funded papers' accepted manuscripts (or published articles) to be deposited in PAR, where they are
public. For every structure paper (cs-structure/papers.json) without a local copy, PAR is searched by exact
title phrase (NSF-funded papers first, from cs-structure/paper_meta.jsonl.gz); a result counts only when its
title is identical after normalization, and its full-text link (servlets/purl/<id>) becomes a candidate,
labelled with PAR's own version label (Accepted Manuscript / Published Article). robots.txt sets no rule for
general crawlers; requests are one per 3 s. Resumable (cs-structure/raw/nsf_par/).

search   -> cs-structure/raw/nsf_par/results_NNN.json.gz
package  -> discovery/claude-cs-open-copies-nsfpar-20261017/ (cs_open_copies package format)
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, json, re, sqlite3, sys, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

STAGE = P.SWEEPS / 'claude-princeton-20261015'  # vendored: the data root (was Path(__file__).resolve().parents[1])
ST = STAGE / 'cs-structure'
RAW = ST / 'raw' / 'nsf_par'
FULLTEXT = P.STORES / 'princeton'
PACKAGE = FULLTEXT / 'discovery' / 'claude-cs-open-copies-nsfpar-20261017'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cs_open_copies import nt


def catalog():
    from catalog_snapshot import snapshot  # chunked reads: never hold a long lock against the collector
    snap = snapshot()
    return snap, snap['status'], snap['doi']


def wid_of(p, st, dois):
    if p['key'].startswith('W:') and 'paper_oa_' + p['key'][2:] in st:
        return 'paper_oa_' + p['key'][2:]
    return dois.get(p['doi']) if p['doi'] else None


def parse(html):
    out = []
    for b in html.split('class="article item document"')[1:]:
        b = b[:8000]
        t = re.search(r'class="title"[^>]*>(.*?)</', b, re.S)
        purl = re.findall(r'servlets/purl/(\d+)', b)
        if t and purl:
            out.append(dict(title=re.sub(r'<[^>]+>|\s+', ' ', t.group(1)).strip(), purl=purl[0],
                            biblio=(re.findall(r'/biblio/(\d+)', b) or [''])[0], labels=re.findall(r'alt="([^"]+)"', b)[:4]))
    return out


def search():
    import requests
    papers = json.loads((ST / 'papers.json').read_text())
    _, st, dois = catalog()
    nsf = set()
    meta = ST / 'paper_meta.jsonl.gz'
    if meta.exists():
        for line in gzip.decompress(meta.read_bytes()).decode().splitlines():
            r = json.loads(line)
            if any('National Science Foundation' in f for f in r.get('funders') or []):
                nsf.add(r['key'])
    RAW.mkdir(parents=True, exist_ok=True)
    done = set()
    for f in RAW.glob('results_*.json.gz'):
        done |= {r['key'] for r in json.loads(gzip.decompress(f.read_bytes()))}
    todo = []
    for p in papers:
        w = wid_of(p, st, dois)
        if (w and st[w] in ('downloaded', 'fulltext_xml')) or p['key'] in done or len(nt(p['title'] or '')) < 25 or not (p['year'] and p['year'] >= 2015):
            continue
        todo.append(p)
    todo.sort(key=lambda p: (p['key'] not in nsf, -(p['year'] or 0)))
    print(json.dumps(dict(todo=len(todo), nsf_funded_first=sum(1 for p in todo if p['key'] in nsf))), flush=True)
    s = requests.Session(); s.headers['User-Agent'] = UA
    batch, n, last = [], len(list(RAW.glob('results_*.json.gz'))), 0
    for p in todo:
        words = re.sub(r'[^A-Za-z0-9 ]+', ' ', p['title']).split()
        url = 'https://par.nsf.gov/search/term:' + quote('"' + ' '.join(words) + '"')
        time.sleep(max(0, 3 - (time.monotonic() - last))); last = time.monotonic()
        try:
            r = s.get(url, timeout=(15, 60))
            status, res = r.status_code, (parse(r.text) if r.status_code == 200 else [])
        except Exception as e:
            status, res = type(e).__name__, []
        if status == 429 or (isinstance(status, int) and status >= 500):
            time.sleep(120)
        batch.append(dict(key=p['key'], title=p['title'], query=url, status=status, results=res,
                          match=[x for x in res if nt(x['title']) == nt(p['title'])], at=datetime.now(timezone.utc).isoformat()))
        if len(batch) >= 100:
            (RAW / f'results_{n:03d}.json.gz').write_bytes(gzip.compress(json.dumps(batch).encode())); n += 1
            print(json.dumps(dict(saved=n * 100, matched=sum(1 for b in batch if b['match']))), flush=True); batch = []
    if batch:
        (RAW / f'results_{n:03d}.json.gz').write_bytes(gzip.compress(json.dumps(batch).encode()))


def package():
    papers = {p['key']: p for p in json.loads((ST / 'papers.json').read_text())}
    snap, st, dois = catalog()
    known = defaultdict(set)
    for w, us in snap['candidates'].items():
        known[w] |= set(us)
    for w, us in snap['attempts'].items():
        known[w] |= set(us)
    PACKAGE.mkdir(parents=True, exist_ok=True); (PACKAGE / 'evidence').mkdir(exist_ok=True)
    rows, n = [], Counter()
    for f in sorted(RAW.glob('results_*.json.gz')):
        ev = PACKAGE / 'evidence' / f.name.replace('.json.gz', '.json')
        recs = json.loads(gzip.decompress(f.read_bytes()))
        ev.write_text(json.dumps(dict(rule=__doc__, searches=recs)))
        for r in recs:
            n['searched'] += 1; n['matched'] += bool(r['match'])
            if r['key'] not in papers:
                continue  # the paper list was rebuilt after this search
            w = wid_of(papers[r['key']], st, dois)
            if not w:
                continue
            for m in r['match']:
                u = f"https://par.nsf.gov/servlets/purl/{m['purl']}"
                if u in known[w]:
                    continue
                known[w].add(u)
                ver = 'acceptedVersion' if any('Accepted' in l for l in m['labels']) else 'publishedVersion' if any('Published' in l for l in m['labels']) else None
                rows.append(dict(work_id=w, url=u, landing_url=f"https://par.nsf.gov/biblio/{m['biblio']}" if m['biblio'] else None, license=None,
                                 version=ver, metadata_source=str(ev), source='nsf_par_exact_title', detail=m['purl']))
                n['candidates'] += 1
    with open(PACKAGE / 'cs-open-copies-candidates.jsonl', 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    (PACKAGE / 'work-ids.txt').write_text('\n'.join(dict.fromkeys(r['work_id'] for r in rows)) + '\n')
    (PACKAGE / 'summary.json').write_text(json.dumps(dict(created_at=datetime.now(timezone.utc).isoformat(), counts=dict(n),
                                                          works_gaining_candidate=len({r['work_id'] for r in rows}), requires_packages=[], rules=__doc__), indent=1))
    print(json.dumps(dict(n, works=len({r['work_id'] for r in rows}))))


if __name__ == '__main__':
    {'search': search, 'package': package}[sys.argv[1]]()
