# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-cmu-20261017/tools/europepmc_lookup.py (sha256 a949154dbf4a8eefc2c7d245f761e6ed7539d573c33ea1e24a1edbe99f12f854); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""PubMed Central copies through Europe PMC, for papers with a DOI and no local copy at Princeton CS, CMU SCS and
EPFL IC (in-scope works).

search   Europe PMC's REST search (www.ebi.ac.uk/europepmc/webservices/rest/search; robots.txt allows it, crawl delay
         10 s: one request per 10 s), 25 DOIs per query (DOI:"..." OR ...), resultType lite: each hit's DOI, PMID,
         PMCID, open-access and author-manuscript flags. Cached in raw/europepmc.jsonl (one record per DOI asked).
files    for every hit with a PMCID: the article's files in NLM's PMC Article Datasets on AWS (pmc-oa-opendata, a
         public S3 listing; the open-access subset and author manuscripts), PDF before JATS XML, as in
         tools/cmu_more_copies.py. www.ncbi.nlm.nih.gov/pmc/articles/* is disallowed by robots.txt and not used.
CMU / EPFL: candidates straight into data/fulltext/<school>/catalog.sqlite; Princeton: package
discovery/claude-europepmc-<date><time>/ (cs_open_copies format), imported at a safe phase.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import json, re, sqlite3, sys, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

STAGE = P.SWEEPS / 'claude-cmu-20261017'  # vendored: the data root (was Path(__file__).resolve().parents[1])
CACHE = STAGE / 'raw' / 'europepmc.jsonl'
FT = P.STORES
API = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
S3 = 'https://pmc-oa-opendata.s3.amazonaws.com'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from s2_key_lookup import princeton_targets, catalog_targets

SCOPES = {'cmu': STAGE / 'people' / 'scope.json',
          'epfl': P.SWEEPS / 'claude-epfl-20261019/people/scope.json'}


def plan():
    out = {'princeton': princeton_targets()}
    for school, scope in SCOPES.items():
        if scope.exists():
            out[school] = catalog_targets(school, scope)
    return out


def search(dois):
    import requests
    s = requests.Session(); s.headers['User-Agent'] = UA
    done = {}
    if CACHE.exists():
        for line in CACHE.open():
            r = json.loads(line); done[r['doi']] = r
    todo = [d for d in dict.fromkeys(dois) if d not in done or done[d].get('error')]
    print(json.dumps(dict(dois=len(set(dois)), todo=len(todo), cached=len(done))), flush=True)
    last = 0.0
    with CACHE.open('a') as f:
        for i in range(0, len(todo), 25):
            chunk = todo[i:i + 25]
            q = ' OR '.join(f'DOI:"{d}"' for d in chunk)
            res = None
            for attempt in range(4):
                time.sleep(max(0, 10.0 - (time.monotonic() - last))); last = time.monotonic()
                try:
                    r = s.get(API, params={'query': q, 'resultType': 'lite', 'format': 'json', 'pageSize': 100}, timeout=(15, 120))
                    if r.status_code == 200:
                        res = r.json().get('resultList', {}).get('result', []); break
                    if r.status_code == 429:
                        time.sleep(120)
                except Exception:
                    time.sleep(30)
            hits = {}
            for h in res or []:
                d = (h.get('doi') or '').lower()
                if d in chunk:
                    hits[d] = dict(pmid=h.get('pmid'), pmcid=h.get('pmcid'), oa=h.get('isOpenAccess'), auth_man=h.get('authMan'), in_pmc=h.get('inPMC'))
            now = datetime.now(timezone.utc).isoformat()
            for d in chunk:
                rec = dict(doi=d, at=now, **hits.get(d, {})) if res is not None else dict(doi=d, at=now, error=True)
                done[d] = rec; f.write(json.dumps(rec) + '\n')
            f.flush()
            if (i // 25) % 40 == 39:
                print(json.dumps(dict(asked=i + len(chunk), of=len(todo), with_pmcid=sum(1 for d in todo[:i + len(chunk)] if done[d].get('pmcid')))), flush=True)
    return done


def files(s, pmcid, memo):
    if pmcid in memo:
        return memo[pmcid]
    n = re.sub(r'\D', '', pmcid)
    time.sleep(0.5)
    try:
        r = s.get(f'{S3}/?list-type=2&prefix=PMC{n}.', timeout=60)
        keys = re.findall(r'<Key>([^<]+)</Key>', r.text) if r.status_code == 200 else []
    except Exception:
        keys = []
    ver = max((int(x.group(1)) for k in keys if (x := re.search(r'\.(\d+)/', k))), default=None)
    memo[pmcid] = [f'{S3}/{k}' for ext in ('pdf', 'xml') if ver and (k := f'PMC{n}.{ver}/PMC{n}.{ver}.{ext}') in keys]
    return memo[pmcid]


def main():
    import requests
    p = plan()
    dois = [t['doi'].lower() for ts, _ in p.values() for t in ts if t['doi'] and not t['doi'].lower().startswith('10.48550/') and '_thesis_' not in t['work_id']]
    done = search(dois)
    s = requests.Session(); s.headers['User-Agent'] = UA
    memo, n = {}, Counter()
    stamp = datetime.now(timezone.utc)
    for school, (ts, known) in p.items():
        rows = []
        for t in ts:
            r = done.get((t['doi'] or '').lower()) or {}
            if not r.get('pmcid') or any('pmc-oa-opendata' in u for u in known[t['work_id']]):
                continue
            n[f'{school}_with_pmcid'] += 1
            for u in files(s, r['pmcid'], memo):
                if u not in known[t['work_id']]:
                    rows.append((t['work_id'], u, f"https://pmc.ncbi.nlm.nih.gov/articles/{r['pmcid']}/", r['pmcid']))
        if school == 'princeton':
            pkg = FT / 'princeton' / 'discovery' / f"claude-europepmc-{stamp.strftime('%Y%m%d%H%M')}"
            (pkg / 'evidence').mkdir(parents=True, exist_ok=True)
            ev = pkg / 'evidence' / 'europepmc.json'
            ev.write_text(json.dumps(dict(rule=__doc__, lookups=[done[t['doi'].lower()] for t in ts if t['doi'] and t['doi'].lower() in done])))
            out = [dict(work_id=w, url=u, landing_url=land, license=None, version=None, metadata_source=str(ev), source='europepmc_pmc_open_data', detail=pid)
                   for w, u, land, pid in rows]
            with open(pkg / 'cs-open-copies-candidates.jsonl', 'w') as f:
                for r in out:
                    f.write(json.dumps(r) + '\n')
            (pkg / 'work-ids.txt').write_text('\n'.join(dict.fromkeys(r['work_id'] for r in out)) + '\n')
            (pkg / 'summary.json').write_text(json.dumps(dict(created_at=stamp.isoformat(), counts=dict(rows=len(out)), works_gaining_candidate=len({r['work_id'] for r in out}),
                                                              requires_packages=[], rules=__doc__), indent=1))
            n['princeton_package'] = pkg.name
        else:
            ev = FT / school / 'discovery' / f'claude-{school}-catalog' / 'evidence' / f"europepmc-{stamp.strftime('%Y%m%d')}.json"
            ev.parent.mkdir(parents=True, exist_ok=True)
            ev.write_text(json.dumps(dict(rule=__doc__, lookups=[done[t['doi'].lower()] for t in ts if t['doi'] and t['doi'].lower() in done])))
            db = sqlite3.connect(str(FT / school / 'catalog.sqlite'), timeout=300)
            for attempt in range(20):  # the collector writes to the same catalog: wait out its locks
                try:
                    n[f'{school}_candidates'] = sum(db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)', (w, u, land, None, None, str(ev))).rowcount
                                                    for w, u, land, _ in rows)
                    db.commit(); break
                except sqlite3.OperationalError:
                    db.rollback(); time.sleep(30)
        n[f'{school}_works'] = len({r[0] for r in rows})
    print(json.dumps(dict(n)))


if __name__ == '__main__':
    main()
