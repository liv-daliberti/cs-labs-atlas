# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-cmu-20261017/tools/arxiv_oai.py (sha256 e5b46fc1b0b89f3f116041bba44dddc59ce7440764560f7f0691bcd961ca2734); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""A local index of arXiv metadata (2015–) for exact-title matching, from arXiv's OAI-PMH interface
(https://oaipmh.arxiv.org/oai, the documented bulk-metadata route; no robots.txt rule on that host). export.arxiv.org
(robots.txt: Disallow: /) is not used.

harvest  ListRecords, metadataPrefix=arXiv, sets cs / stat / eess / math / physics:quant-ph / q-bio, from 2015-01-01;
         one request per 5 s, Retry-After honoured on 503; resumable by resumption token. Kept per record: arXiv id,
         title, author family names, DOI, categories, first-version date -> raw/arxiv_oai/<set>_NNNN.jsonl.gz
match    papers without a local copy (usage: match [cmu] [epfl] [princeton]; default all three):
           cmu        in-scope CMU catalog works (people/scope.json) with no arXiv candidate yet
           epfl       in-scope EPFL catalog works (../claude-epfl-20261019/people/scope.json), likewise
           princeton  Princeton CS structure papers (../claude-princeton-20261015/cs-structure/papers.json)
         an arXiv record matches when its normalized title is identical, it shares an author family name with the
         paper's people, and its first version is no more than 1 year after / 3 years before the paper. The arXiv id
         goes through tools/arxiv_bulk.py's bulk-copy listing: CMU and EPFL candidates into their catalogs;
         Princeton ones into the package discovery/claude-arxiv-titles-<date>/.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, html, json, re, sqlite3, sys, time, unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

STAGE = P.SWEEPS / 'claude-cmu-20261017'  # vendored: the data root (was Path(__file__).resolve().parents[1])
RAW = STAGE / 'raw' / 'arxiv_oai'
BASE = 'https://oaipmh.arxiv.org/oai'
UA = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
SETS = ['cs', 'stat', 'eess', 'q-bio', 'physics:quant-ph', 'math']  # most useful first; match runs after the first four
NS = {'o': 'http://www.openarchives.org/OAI/2.0/', 'a': 'http://arxiv.org/OAI/arXiv/'}
sys.path.insert(0, str(Path(__file__).resolve().parent))


def nt(t):
    t = unicodedata.normalize('NFKD', html.unescape(t or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', re.sub(r'\$[^$]*\$', '', t))


def fam(n):
    t = re.sub(r'[^a-z ]', ' ', unicodedata.normalize('NFKD', n or '').encode('ascii', 'ignore').decode().lower()).split()
    return t[-1] if t else ''


def harvest():
    import requests
    s = requests.Session(); s.headers['User-Agent'] = UA
    RAW.mkdir(parents=True, exist_ok=True)
    state_f = RAW / 'state.json'
    state = json.loads(state_f.read_text()) if state_f.exists() else {}
    last = 0
    for st in SETS:
        if state.get(st, {}).get('done'):
            continue
        tok = state.get(st, {}).get('token'); n = state.get(st, {}).get('chunks', 0)
        while True:
            params = {'verb': 'ListRecords', 'resumptionToken': tok} if tok else {'verb': 'ListRecords', 'metadataPrefix': 'arXiv', 'set': st, 'from': '2015-01-01'}
            for attempt in range(8):
                time.sleep(max(0, 5 - (time.monotonic() - last))); last = time.monotonic()
                try:
                    r = s.get(BASE, params=params, timeout=(15, 300))
                except Exception:
                    time.sleep(60); continue
                if r.status_code == 200:
                    break
                time.sleep(int(r.headers.get('Retry-After', 60)) if r.status_code == 503 else 60 * (attempt + 1))
            else:
                print(json.dumps(dict(stopped=st, status=r.status_code)), flush=True); return
            root = ET.fromstring(r.content)
            recs = []
            for rec in root.iter('{http://www.openarchives.org/OAI/2.0/}record'):
                m = rec.find('.//a:arXiv', NS)
                if m is None:
                    continue
                recs.append(dict(id=m.findtext('a:id', '', NS), title=' '.join((m.findtext('a:title', '', NS) or '').split()),
                                 families=[x.findtext('a:keyname', '', NS) for x in m.findall('a:authors/a:author', NS)],
                                 doi=m.findtext('a:doi', None, NS), categories=m.findtext('a:categories', '', NS), created=m.findtext('a:created', '', NS)))
            (RAW / f"{st.replace(':', '_')}_{n:05d}.jsonl.gz").write_bytes(gzip.compress('\n'.join(json.dumps(x) for x in recs).encode()))
            n += 1
            t = root.find('.//o:resumptionToken', NS)
            tok = t.text if t is not None and t.text else None
            state[st] = dict(token=tok, chunks=n, done=not tok, size=(t.get('completeListSize') if t is not None else None))
            state_f.write_text(json.dumps(state))
            if n % 50 == 0:
                print(json.dumps(dict(set=st, chunks=n, size=state[st]['size'])), flush=True)
            if not tok:
                break
        print(json.dumps(dict(set_done=st, chunks=n)), flush=True)


STOP = set('a an the of for and in on to with via from by at is are as its into using toward towards over under through'.split())


def words(t):
    t = unicodedata.normalize('NFKD', html.unescape(t or '')).encode('ascii', 'ignore').decode().lower()
    return [w for w in re.sub(r'[^a-z0-9 ]', ' ', re.sub(r'\$[^$]*\$', ' ', t)).split() if w not in STOP]


def index():
    by_title = defaultdict(list); by_words = defaultdict(list); by_prefix = defaultdict(list)
    for f in sorted(RAW.glob('*.jsonl.gz')):
        for line in gzip.decompress(f.read_bytes()).decode().splitlines():
            if not line:
                continue
            r = json.loads(line)
            k = nt(r['title'])
            if len(k) >= 20:
                rec = (r['id'], [fam(x) for x in r['families']], int((r['created'] or '0')[:4] or 0), k)
                by_title[k].append(rec)
                ws = words(r['title'])
                if len(ws) >= 4:
                    by_words[' '.join(sorted(set(ws)))].append(rec)
                if len(k) >= 40:
                    by_prefix[k[:40]].append(rec)
    return by_title, by_words, by_prefix


def match_one(idx, title, year, people):
    """(arXiv id, tier): exact normalized title; else the same set of significant title words; else one title is the
    other plus a subtitle (both >= 40 characters). Every tier needs a shared author family name and a year from 1 after
    to 3 before the paper."""
    by_title, by_words, by_prefix = idx
    fams = {fam(p) for p in people} - {''}
    ok = lambda afams, y: fams & set(afams) and (not year or not y or -1 <= year - y <= 3)
    k = nt(title)
    for aid, afams, y, _ in by_title.get(k, []):
        if ok(afams, y):
            return aid, 'exact_title'
    ws = words(title)
    if len(ws) >= 4:
        for aid, afams, y, _ in by_words.get(' '.join(sorted(set(ws))), []):
            if ok(afams, y):
                return aid, 'same_title_words'
    if len(k) >= 40:
        for aid, afams, y, ak in by_prefix.get(k[:40], []):
            if (ak.startswith(k) or k.startswith(ak)) and ok(afams, y):
                return aid, 'title_with_or_without_subtitle'
    return None, None


CATALOGS = {'cmu': (STAGE / 'people' / 'scope.json', ('cmu_faculty', 'cmu_students', 'cmu_postdocs')),
            'epfl': (P.SWEEPS / 'claude-epfl-20261019/people/scope.json',
                     ('school_faculty', 'school_students', 'school_postdocs'))}


def catalog_hits(idx, school, tiers):
    scope_path, keys = CATALOGS[school]
    out = P.STORES / school
    db = sqlite3.connect(f'file:{out / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    scope = json.loads(scope_path.read_text())['scope']
    have = {w for (w,) in db.execute("SELECT id FROM works WHERE status IN ('downloaded','fulltext_xml')")}
    lane = out / 'staged' / 'arxiv-candidates.jsonl'
    staged = {json.loads(l)['work_id'] for l in lane.open()} if lane.exists() else set()
    hits = {}
    for w, title, year, g in db.execute('SELECT id, title, year, graph_json FROM works'):
        if w in have or w in staged or not scope.get(w, {}).get('in_scope') or w.startswith(f'{school}_thesis_'):
            continue
        g = json.loads(g)
        aid, tier = match_one(idx, title, year, [n for k in keys for n in g.get(k) or []])
        if aid:
            hits[w] = aid; tiers[f'{school}:{tier}'] += 1
    return hits


def insert_catalog(school, hits, urls):
    out = P.STORES / school
    ev = out / 'discovery' / f'claude-{school}-catalog' / 'evidence' / 'arxiv-title-matches.json'
    ev.parent.mkdir(parents=True, exist_ok=True)
    ev.write_text(json.dumps(dict(rule=__doc__, created_at=datetime.now(timezone.utc).isoformat(), matches={w: dict(arxiv=a, url=urls.get(a)) for w, a in hits.items()})))
    db = sqlite3.connect(str(out / 'catalog.sqlite'), timeout=300)
    for attempt in range(20):  # the collector writes to the same catalog: wait out its locks
        try:
            added = sum(db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)', (w, urls[a], f'https://arxiv.org/abs/{a}', None, 'submittedVersion', str(ev))).rowcount
                        for w, a in hits.items() if urls.get(a))
            db.commit(); return added
        except sqlite3.OperationalError:
            db.rollback(); time.sleep(30)
    return 0


def princeton_hits(idx, tiers):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'princeton_tools'))
    from catalog_snapshot import snapshot
    snap = snapshot(max_age_s=3600); st, dois = snap['status'], snap['doi']
    hits = {}
    for p in json.loads(P.SWEEPS / 'claude-princeton-20261015/cs-structure/papers.json'.read_text()):
        w = ('paper_oa_' + p['key'][2:]) if p['key'].startswith('W:') and 'paper_oa_' + p['key'][2:] in st else dois.get(p['doi']) if p['doi'] else None
        if not w or st.get(w) in ('downloaded', 'fulltext_xml'):
            continue
        aid, tier = match_one(idx, p['title'], p['year'], p['faculty'] + p['students'])
        if aid:
            hits[w] = aid; tiers['princeton:' + tier] += 1
    return hits


def princeton_package(hits, urls):
    pkg = P.STORES / 'princeton/discovery' / ('claude-arxiv-titles-' + datetime.now(timezone.utc).strftime('%Y%m%d%H%M'))
    (pkg / 'evidence').mkdir(parents=True, exist_ok=True)
    pev = pkg / 'evidence' / 'arxiv-title-matches.json'
    pev.write_text(json.dumps(dict(rule=__doc__, created_at=datetime.now(timezone.utc).isoformat(), matches={w: dict(arxiv=a, url=urls.get(a)) for w, a in hits.items()})))
    rows = [dict(work_id=w, url=urls[a], landing_url=f'https://arxiv.org/abs/{a}', license=None, version='submittedVersion', metadata_source=str(pev),
                 source='arxiv_oai_title_match', detail=a) for w, a in hits.items() if urls.get(a)]
    with open(pkg / 'cs-open-copies-candidates.jsonl', 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    (pkg / 'work-ids.txt').write_text('\n'.join(r['work_id'] for r in rows) + '\n')
    (pkg / 'summary.json').write_text(json.dumps(dict(created_at=datetime.now(timezone.utc).isoformat(), counts=dict(matched=len(hits), candidates=len(rows)),
                                                      works_gaining_candidate=len(rows), requires_packages=[], rules=__doc__), indent=1))
    return dict(princeton_matched=len(hits), princeton_candidates=len(rows), package=str(pkg))


def match(schools=('cmu', 'epfl', 'princeton')):
    from arxiv_bulk import listing
    idx = index()
    print(json.dumps(dict(arxiv_titles=len(idx[0]))), flush=True)
    tiers = __import__('collections').Counter()
    hits = {s: catalog_hits(idx, s, tiers) for s in schools if s in CATALOGS and CATALOGS[s][0].exists()}
    prin = princeton_hits(idx, tiers) if 'princeton' in schools else {}
    urls = listing([a for h in list(hits.values()) + [prin] for a in h.values()])
    res = {f'{s}_matched': len(h) for s, h in hits.items()}
    res.update({f'{s}_candidates': insert_catalog(s, h, urls) for s, h in hits.items()})
    if prin:
        res.update(princeton_package(prin, urls))
    print(json.dumps(dict(tiers=dict(tiers), **res)))


if __name__ == '__main__':
    harvest() if sys.argv[1] == 'harvest' else match(tuple(sys.argv[2:]) or ('cmu', 'epfl', 'princeton'))
