# Vendored 2026-10-30 from /n/fs/resemble/maxent-grpo/.research-sweeps/claude-princeton-20261015/tools/cs_pi_works.py (sha256 5248b04838b682ceb3581c19601985349057122f667e064973d2bc7bea862867); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""Every 2016–2026 paper with a verified Princeton CS lab head on the byline, tiered for the lab.

Steps (resumable):
  identities  verified (lab, PI, OpenAlex author) pairs: the CS page anchors (cs-papers/anchored.json),
              the Princeton list anchors (identity/proposals.json) and, when present, DBLP/ORCID-verified
              heads from cs-pi-works/extra_identities.json.
  fetch       each author's OpenAlex works 2016-01-01..2026-10-12 (cursor paging, API key), stored
              gzip with the sha256 of the bytes as served.
  tier        per (lab, PI, work), research paper types only, not retracted:
                A  the PI's own authorship lists Princeton (I20089843);
                B  the PI is on the byline and at least one member from the lab's own people page
                   (full-name match, middle initials not required) is a co-author, and either the PI's
                   authorship carries no institution at all (metadata gap) or that member's authorship
                   lists Princeton;
                excluded otherwise (e.g. pre-Princeton work, other-institution collaborations).
  package     discovery/claude-cs-pi-works-20261015/ for the full-text catalog: associations (kind pi),
              new works (tier B papers outside the institutional corpus) with their open-access
              candidates, and evidence per link.
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import glob, gzip, hashlib, json, os, re, sys, time, unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import requests

STAGE = P.SWEEPS / 'claude-princeton-20261015'  # vendored: the data root (was Path(__file__).resolve().parents[1])
# SCOPE=princeton runs the same pipeline over every Princeton unit (all divisions), into its own
# work folder and package; the default scope is the Computer Science units.
SCOPE = os.environ.get('SCOPE', 'cs')
WORK = STAGE / ('cs-pi-works' if SCOPE == 'cs' else 'pr-pi-works')
FULLTEXT = P.STORES / 'princeton'
PACKAGE = FULLTEXT / ('discovery/claude-cs-pi-works-20261015' if SCOPE == 'cs' else 'discovery/claude-princeton-pi-works-20261016')
DIVISIONS = ['eng-cbe-cee-materials', 'eng-ece-mae-orfe', 'computer-science', 'molbio-lsi', 'eeb-pni-psychology',
             'chemistry', 'physics-astro-geo-math', 'social-sciences', 'cs-roster']


def division_files(name):
    """(units/research file, capture dir) for each division: claude/ output when present, else the root."""
    out = []
    for d in DIVISIONS:
        root = STAGE / d
        for base in (root / 'claude', root):
            if (base / name).exists():
                out.append((base / name, root)); break
    if (CS_TOP / name).exists():
        out.append((CS_TOP / name, CS_TOP))
    return out
CS_TOP = P.SWEEPS / 'claude-cs-top-20261014/princeton-university'
PRINCETON = 'https://openalex.org/I20089843'
START, END = '2016-01-01', '2026-10-12'
TYPES = {'article', 'conference-paper', 'review', 'preprint', 'report', 'data-paper', 'software-paper', 'proceedings-article'}


def norm(text):
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', text).strip()


def full_tokens(name):
    t = norm(name).split()
    full = [x for x in t if len(x) > 1]
    return full if len(full) >= 2 else t


def cs_units():
    units = {u['lab_id']: u for u in json.loads((STAGE / 'cs_units_live.json').read_text())}
    if SCOPE != 'cs':
        for l in json.loads((STAGE / 'baseline_princeton-university.json').read_text())['live_labs']:
            units.setdefault(l['lab_id'], dict(lab_id=l['lab_id'], name=l['name'], pis=list(l.get('pi') or []), url=l.get('homepage') or ''))
    sources = [STAGE / 'cs-roster/final_units.json'] if SCOPE == 'cs' else [f for f, _ in division_files('final_units.json')]
    for f in sources:
        if not f.exists():
            continue
        for u in json.loads(f.read_text()):
            key = u.get('existing_id') or 'new:' + (u.get('url') or u['name'])
            entry = units.setdefault(key, dict(lab_id=key, name=u['name'], pis=[], url=u.get('url', '')))
            for x in u.get('leaders', []):
                if x['name'] not in entry['pis']:
                    entry['pis'].append(x['name'])
    return units


def identities():
    units = cs_units()
    out = {}
    anchored = STAGE / 'cs-papers/anchored.json'
    if anchored.exists():
        for a in json.loads(anchored.read_text())['anchored']:
            out[(a['lab_id'], a['openalex_author_id'])] = dict(lab_id=a['lab_id'], pi=a['leader'], author=a['openalex_author_id'],
                                                               orcid=a.get('orcid', ''), method='cs_lab_page_bibliography_anchor')
    proposals = STAGE / 'identity/proposals.json'
    if proposals.exists():
        for p in json.loads(proposals.read_text()):
            lab = p.get('existing_id') or p['lab']
            if lab in units:
                out.setdefault((lab, p['openalex_author_id']), dict(lab_id=lab, pi=p['leader'], author=p['openalex_author_id'],
                                                                  orcid=p.get('orcid', ''), method='princeton_lab_list_anchor'))
    if SCOPE != 'cs' and (STAGE / 'cs-pi-works/identities.json').exists():
        for r in json.loads((STAGE / 'cs-pi-works/identities.json').read_text()):
            out.setdefault((r['lab_id'], r['author']), r)
    extra = WORK / 'extra_identities.json'
    if extra.exists():
        for e in json.loads(extra.read_text()):
            out.setdefault((e['lab_id'], e['author']), e)
    WORK.mkdir(exist_ok=True)
    rows = sorted(out.values(), key=lambda r: (r['lab_id'], r['pi']))
    (WORK / 'identities.json').write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    print(json.dumps(dict(cs_units=len(units), verified_pairs=len(rows), labs=len({r['lab_id'] for r in rows}),
                          authors=len({r['author'] for r in rows}), by_method=dict(Counter(r['method'] for r in rows)))))


def fetch():
    key = os.environ['OPENALEX_API_KEY']
    rows = json.loads((WORK / 'identities.json').read_text())
    (WORK / 'raw').mkdir(parents=True, exist_ok=True)
    state_path = WORK / 'fetch_state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    session = requests.Session(); session.headers['User-Agent'] = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'
    for author in sorted({r['author'] for r in rows}):
        aid = author.rsplit('/', 1)[-1]
        s = state.setdefault(aid, dict(cursor='*', pages=[], complete=False))
        while not s['complete']:
            params = {'filter': f'authorships.author.id:{aid},from_publication_date:{START},to_publication_date:{END}',
                      'per_page': 200, 'cursor': s['cursor'], 'api_key': key}
            for attempt in range(5):
                try:
                    r = session.get('https://api.openalex.org/works', params=params, timeout=120)
                    if r.status_code in (429, 500, 502, 503, 504):
                        time.sleep(2 ** attempt); continue
                    r.raise_for_status(); break
                except requests.RequestException:
                    time.sleep(5 * (attempt + 1))
            data = r.json()
            path = WORK / 'raw' / f'{aid}_{len(s["pages"]):03d}.json.gz'
            path.write_bytes(gzip.compress(r.content, 6))
            s['pages'].append(dict(path=str(path), sha256=hashlib.sha256(r.content).hexdigest(), records=len(data.get('results', []))))
            nxt = data.get('meta', {}).get('next_cursor')
            s['complete'] = not data.get('results') or not nxt
            s['cursor'] = nxt
            state_path.write_text(json.dumps(state))
            time.sleep(0.15)
    print(json.dumps(dict(authors=len(state), pages=sum(len(s['pages']) for s in state.values()),
                          works=sum(p['records'] for s in state.values() for p in s['pages']))))


def members_by_lab():
    """Lab members from the labs' own people pages (all staged CS sources), keyed like cs_units()."""
    units = cs_units()
    by_url = {u.get('url'): k for k, u in units.items() if u.get('url')}
    by_name = {norm(u['name']): k for k, u in units.items()}
    files = [f for f, _ in division_files('final_units.json')]
    out = defaultdict(dict)
    for f in files:
        if not f.exists():
            continue
        for u in json.loads(f.read_text()):
            key = u.get('existing_id') or by_url.get(u.get('url')) or by_name.get(norm(u['name']))
            if key is None:
                key = 'new:' + (u.get('url') or u['name'])
            if key not in units:
                continue
            for m in u.get('members', []):
                toks = full_tokens(m.get('name', ''))
                if len(toks) >= 2:
                    out[key][' '.join(toks)] = dict(name=m['name'], role=m.get('role', ''), status=m.get('status', ''),
                                                    source_url=m.get('source_url', ''), source_key=m.get('source_key', ''))
    return out


def iter_works(aid, state):
    for p in state[aid]['pages']:
        raw = gzip.decompress(Path(p['path']).read_bytes())
        assert hashlib.sha256(raw).hexdigest() == p['sha256']
        yield from json.loads(raw)['results']


def tier():
    rows = json.loads((WORK / 'identities.json').read_text())
    state = json.loads((WORK / 'fetch_state.json').read_text())
    members = members_by_lab()
    out, counts = [], Counter()
    for ident in rows:
        aid = ident['author'].rsplit('/', 1)[-1]
        if aid not in state:
            continue
        lab_members = members.get(ident['lab_id'], {})
        pi_tokens = set(full_tokens(ident['pi']))
        for w in iter_works(aid, state):
            if w.get('type') not in TYPES or w.get('is_retracted') or w.get('is_paratext'):
                counts['nonpaper_or_retracted'] += 1; continue
            auths = w.get('authorships') or []
            pi = [a for a in auths if (a.get('author') or {}).get('id') == ident['author']]
            if len(pi) != 1:
                counts['pi_not_unique_on_byline'] += 1; continue
            pi_insts = {i.get('id') for i in (pi[0].get('institutions') or [])}
            coauthors = []
            for a in auths:
                if a is pi[0]:
                    continue
                name = (a.get('author') or {}).get('display_name') or a.get('raw_author_name') or ''
                toks = norm(name).split()
                for key, m in lab_members.items():
                    need = key.split()
                    if need[0] in toks and need[-1] in toks and all(t in toks for t in need) and set(need) != pi_tokens:
                        coauthors.append(dict(member=m['name'], byline=name, role=m['role'], status=m['status'],
                                              princeton=any(i.get('id') == PRINCETON for i in (a.get('institutions') or [])),
                                              source_url=m['source_url']))
                        break
            if PRINCETON in pi_insts:
                t = 'A'
            elif coauthors and (not pi_insts or any(c['princeton'] for c in coauthors)):
                t = 'B'
            else:
                counts['excluded_not_princeton_lab_work'] += 1; continue
            counts['tier_' + t] += 1
            out.append(dict(lab_id=ident['lab_id'], pi=ident['pi'], author=ident['author'], identity_method=ident['method'],
                            work=w['id'], doi=(w.get('doi') or '').replace('https://doi.org/', '').lower(), title=w.get('display_name') or '',
                            year=w.get('publication_year'), date=w.get('publication_date'), type=w.get('type'),
                            pi_position=pi[0].get('author_position'), pi_princeton=PRINCETON in pi_insts,
                            lab_member_coauthors=coauthors, tier=t))
    (WORK / 'tiered.json').write_text(json.dumps(out, ensure_ascii=False))
    per_lab = Counter(r['lab_id'] for r in out)
    units = cs_units()
    print(json.dumps(dict(counts=dict(counts), lab_works=len(out), distinct_works=len({r['work'] for r in out}),
                          with_member_coauthor=sum(1 for r in out if r['lab_member_coauthors']),
                          labs=len(per_lab), labs_with_members=len(members),
                          per_lab=[(units[k]['name'][:30], n) for k, n in per_lab.most_common(60)]), ensure_ascii=False))




# ---------------------------------------------------------------- package and import
MATCH = {'A': 'verified_pi_on_byline_with_princeton_affiliation',
         'B': 'verified_pi_and_lab_member_coauthors_affiliation_gap'}


def catalog_index():
    import sqlite3
    db = sqlite3.connect(f'file:{FULLTEXT}/catalog.sqlite?mode=ro', uri=True, timeout=120)
    by_oa, by_doi = {}, {}
    for wid, doi, oa, graph in db.execute('SELECT id,doi,json_extract(oa_json,"$.id"),json_extract(graph_json,"$.openalex") FROM works'):
        for x in (oa, graph):
            if x:
                by_oa[x] = wid
        if doi:
            by_doi[doi.lower()] = wid
    return by_oa, by_doi


def package():
    tiered = json.loads((WORK / 'tiered.json').read_text())
    state = json.loads((WORK / 'fetch_state.json').read_text())
    by_oa, by_doi = catalog_index()
    (PACKAGE / 'evidence').mkdir(parents=True, exist_ok=True)
    full = {}
    for aid in state:
        for p in state[aid]['pages']:
            raw = gzip.decompress(Path(p['path']).read_bytes())
            for w in json.loads(raw)['results']:
                full[w['id']] = (w, p['path'])
    def evidence(record):
        blob = json.dumps(record, sort_keys=True, ensure_ascii=False)
        path = PACKAGE / 'evidence' / (hashlib.sha256(blob.encode()).hexdigest() + '.json')
        path.write_text(blob)
        return str(path)
    assoc, new_works, cands, seen_new = [], [], [], set()
    identities_by = {(r['lab_id'], r['author']): r for r in json.loads((WORK / 'identities.json').read_text())}
    for t in tiered:
        w, page = full[t['work']]
        wid = by_oa.get(t['work']) or (by_doi.get(t['doi']) if t['doi'] else None)
        if wid is None:
            wid = 'paper_oa_' + t['work'].rsplit('/', 1)[-1]
            if wid not in seen_new:
                seen_new.add(wid)
                node = {'id': wid, 'type': 'paper', 'name': w.get('display_name') or '', 'year': w.get('publication_year'),
                        'date': w.get('publication_date'), 'doi': t['doi'], 'openalex': w['id'], 'workType': w.get('type'),
                        'url': w.get('doi') or w['id'], 'sourceUrls': [w['id']], 'status': 'verified_pi_lab_work'}
                new_works.append(dict(id=wid, node=node, metadata=w, source=page,
                                      rule='verified Princeton CS lab head on byline with a lab member co-author; '
                                           'PI affiliation missing in OpenAlex; 2016-01-01 through 2026-10-12'))
                for loc in w.get('locations') or []:
                    if not loc.get('is_oa'):
                        continue
                    url = loc.get('pdf_url'); landing = loc.get('landing_page_url') or ''
                    host = (re.match(r'https?://([^/]+)', url or landing or '') or [None, ''])[1]
                    if not url and host in {'arxiv.org', 'export.arxiv.org'}:
                        url = landing
                    if url and url.startswith('http'):
                        cands.append(dict(work_id=wid, url=url, landing_url=landing, license=loc.get('license'),
                                          version=loc.get('version'), metadata_source=page))
        ident = identities_by[(t['lab_id'], t['author'])]
        ev = evidence(dict(lab_id=t['lab_id'], work_id=wid, openalex_work=t['work'], kind='pi', person=t['pi'], tier=t['tier'],
                           match=MATCH[t['tier']], pi_author=t['author'], pi_identity_method=ident['method'], pi_orcid=ident.get('orcid', ''),
                           pi_position=t['pi_position'], pi_princeton_affiliation=t['pi_princeton'],
                           lab_member_coauthors=t['lab_member_coauthors'], openalex_page=page, title=t['title'], year=t['year']))
        assoc.append(dict(work_id=wid, lab_id=t['lab_id'], kind='pi', person=t['pi'], source_url=t['work'],
                          evidence_path=ev, match=MATCH[t['tier']], title=t['title']))
    if (WORK / 'records.json').exists():
        for r in json.loads((WORK / 'records.json').read_text()):
            kind = 'pi' if r['own_page'] else 'listed'
            ev = evidence(dict(lab_id=r['lab_id'], work_id=r['work_id'], kind=kind, match='staged_official_bibliography_record_' + r['how'],
                               title=r['title'], doi=r['doi'], source_url=r['source_url'], source_key=r['source_key'],
                               source_sha256=r['source_sha256'], stage=r['stage']))
            assoc.append(dict(work_id=r['work_id'], lab_id=r['lab_id'], kind=kind, person='', source_url=r['source_url'],
                              evidence_path=ev, match='staged_official_bibliography_record_' + r['how'], title=r['title']))
    def write(name, rows):
        (PACKAGE / name).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    # Roster units not yet on the site get stable provisional IDs plus a registry for the export.
    units = cs_units()
    def site_id(lab):
        prefix = 'lab_claude_csroster_' if SCOPE == 'cs' else 'lab_claude_pr_'
        return lab if not lab.startswith('new:') else prefix + hashlib.sha256(lab[4:].encode()).hexdigest()[:16]
    for a in assoc:
        a['lab_id'] = site_id(a['lab_id'])
    registry = []
    for key, u in units.items():
        if key.startswith('new:') and any(a['lab_id'] == site_id(key) for a in assoc):
            registry.append(dict(id=site_id(key), name=u['name'], departments=['Computer Science'] if SCOPE == 'cs' else [], url=u.get('url', ''),
                                 source=u.get('url', ''), leaders=u.get('pis', []), unitType='research_group',
                                 provenance='cs-roster staged unit (claude-princeton-20261015/cs-roster/final_units.json)'))
    (PACKAGE / 'labs.json').write_text(json.dumps(registry, indent=1, ensure_ascii=False))
    write('associations.jsonl', assoc); write('new-works.jsonl', new_works); write('new-work-candidates.jsonl', cands)
    (PACKAGE / 'work-ids.txt').write_text('\n'.join(sorted({a['work_id'] for a in assoc})) + '\n')
    summary = dict(associations=len(assoc), works=len({a['work_id'] for a in assoc}), new_works=len(new_works),
                   new_work_candidates=len(cands), labs=len({a['lab_id'] for a in assoc}),
                   by_tier=dict(Counter(a['match'] for a in assoc)), created_at=datetime.now(timezone.utc).isoformat())
    (PACKAGE / 'summary.json').write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary))


def import_catalog():
    """Insert under the catalog's importer lock (the collector must be paused)."""
    import fcntl, sqlite3
    with (FULLTEXT / '.collector.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        db = sqlite3.connect(str(FULLTEXT / 'catalog.sqlite'), timeout=300)
        n = Counter()
        for line in (PACKAGE / 'new-works.jsonl').open():
            r = json.loads(line); node = r['node']
            db.execute('INSERT OR IGNORE INTO nodes VALUES (?,?,?,?)', (r['id'], 'paper', node['name'], json.dumps(node)))
            cur = db.execute('INSERT OR IGNORE INTO works(id,title,doi,year,graph_json,oa_json,metadata_source,status) VALUES (?,?,?,?,?,?,?,?)',
                             (r['id'], node['name'], node['doi'] or None, node['year'], json.dumps(node), json.dumps(r['metadata']), r['source'], 'queued'))
            n['works_added'] += cur.rowcount
            db.execute('INSERT OR REPLACE INTO collection_scope VALUES (?,?,?)', (r['id'], r['source'], r['rule']))
        for line in (PACKAGE / 'new-work-candidates.jsonl').open():
            c = json.loads(line)
            n['candidates_added'] += db.execute('INSERT OR IGNORE INTO candidates VALUES (?,?,?,?,?,?)',
                                                tuple(c[k] for k in ['work_id', 'url', 'landing_url', 'license', 'version', 'metadata_source'])).rowcount
        for line in (PACKAGE / 'associations.jsonl').open():
            a = json.loads(line)
            assert db.execute('SELECT 1 FROM works WHERE id=?', (a['work_id'],)).fetchone()
            n['links_added'] += db.execute('INSERT OR IGNORE INTO work_lab_sources VALUES (?,?,?,?,?,?,?)',
                                           (a['work_id'], a['lab_id'], a['kind'], a['person'], a['source_url'], a['evidence_path'], a['match'])).rowcount
        raw = (PACKAGE / 'summary.json').read_bytes()
        db.execute('INSERT OR REPLACE INTO receipts VALUES (?,?)', ('discovery:' + str(PACKAGE), json.dumps(dict(
            path=str(PACKAGE), sha256=hashlib.sha256(raw).hexdigest(), imported_at=datetime.now(timezone.utc).isoformat()))))
        db.commit()
        print(json.dumps(dict(n)))


def records():
    """Entries from the CS units' own publication lists (agent-validated against their captures),
    resolved to catalog works by exact DOI / arXiv DOI, else a unique exact normalized title."""
    import sqlite3
    units = cs_units()
    by_url = {u.get('url'): k for k, u in units.items() if u.get('url')}
    by_name = {norm(u['name']): k for k, u in units.items()}
    db = sqlite3.connect(f'file:{FULLTEXT}/catalog.sqlite?mode=ro', uri=True, timeout=120)
    by_doi, by_title = {}, defaultdict(list)
    for wid, title, doi, year in db.execute('SELECT id,title,doi,year FROM works'):
        if doi:
            by_doi[doi.lower()] = wid
        t = norm(title)
        if len(t) >= 25:
            by_title[t].append((wid, year))
    sources = division_files('final_research.json') if SCOPE != 'cs' else [
        (STAGE / 'computer-science/claude/final_research.json', STAGE / 'computer-science'),
        (CS_TOP / 'final_research.json', CS_TOP), (STAGE / 'cs-roster/final_research.json', STAGE / 'cs-roster')]
    out, counts = [], Counter()
    for path, capdir in sources:
        if not path.exists():
            continue
        manifest = {}
        for line in (capdir / 'source_manifest.jsonl').open():
            m = json.loads(line); manifest[m['source_key']] = m
        for r in json.loads(path.read_text()):
            key = r.get('existing_id') or by_url.get(r.get('unit_url')) or by_name.get(norm(r.get('unit_name')))
            if key is None and (capdir.name == 'cs-roster' or SCOPE != 'cs'):
                key = 'new:' + (r.get('unit_url') or r.get('unit_name'))
            if key not in units:
                counts['unit_not_cs'] += 1; continue
            if r.get('publication_year') and not (2016 <= int(r['publication_year']) <= 2026):
                counts['outside_window'] += 1; continue
            doi = (r.get('doi') or '').lower()
            wid, how = (by_doi.get(doi), 'exact_doi') if doi in by_doi else (None, None)
            if not wid:
                hits = by_title.get(norm(r.get('title')), [])
                if len(hits) > 1 and r.get('publication_year'):
                    hits = [h for h in hits if h[1] == r['publication_year']]
                if len(hits) == 1:
                    wid, how = hits[0][0], 'exact_title'
            if not wid:
                counts['not_in_catalog'] += 1; continue
            m = manifest.get(r.get('source_key'), {})
            counts[how] += 1
            out.append(dict(lab_id=key, work_id=wid, how=how, title=r.get('title', ''), doi=doi, source_url=r.get('source_url', ''),
                            source_key=r.get('source_key', ''), source_sha256=m.get('sha256', ''), stage=capdir.name,
                            own_page=('own page' in (r.get('attribution_note') or '').lower()) or ' research group' in units[key]['name']))
    dedup = {(o['lab_id'], o['work_id']): o for o in out}
    (WORK / 'records.json').write_text(json.dumps(list(dedup.values()), ensure_ascii=False))
    print(json.dumps(dict(counts=dict(counts), links=len(dedup), labs=len({k[0] for k in dedup}))))


def anchor_more():
    """Bibliography anchor on the union of a unit's matched catalog works (page captures + list records)
    for heads still unverified. Same rule: full-name author on >=50% (>=5), no competitor >=20%,
    Princeton in the author's OpenAlex history."""
    import sqlite3
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'homogenizing_scripts'))
    from publications import Client, author_name_evidence, institution_ids
    units = cs_units()
    have = {(r['lab_id'], r['pi']) for r in json.loads((WORK / 'identities.json').read_text())}
    works = defaultdict(set)
    m = WORK.parent / 'cs-papers/matches.json'
    if m.exists():
        for x in json.loads(m.read_text()):
            works[x['lab_id']].add(x['work_id'])
    for x in json.loads((WORK / 'records.json').read_text()):
        works[x['lab_id']].add(x['work_id'])
    db = sqlite3.connect(f'file:{FULLTEXT}/catalog.sqlite?mode=ro', uri=True, timeout=120)
    need = {w for ws in works.values() for w in ws}
    oa = {}
    for wid, raw in db.execute('SELECT id,oa_json FROM works WHERE oa_json IS NOT NULL'):
        if wid in need:
            oa[wid] = json.loads(raw)
    client = Client(out=WORK / 'openalex')
    extra, gaps = [], []
    for key, u in units.items():
        for leader in dict.fromkeys(u.get('pis', [])):
            if (key, leader) in have:
                continue
            toks = full_tokens(leader)
            ws = [w for w in works.get(key, ()) if w in oa]
            counts = Counter()
            for w in ws:
                counts.update({(a.get('author') or {}).get('id') for a in oa[w].get('authorships') or []
                               if all(t in norm((a.get('author') or {}).get('display_name') or '').split() for t in toks)} - {None})
            ranked = counts.most_common()
            if not ranked or ranked[0][1] < 5 or ranked[0][1] / len(ws) < 0.5 or any(c / len(ws) >= 0.2 for _, c in ranked[1:]):
                gaps.append(dict(lab_id=key, lab=u['name'], pi=leader, works=len(ws), top=ranked[:2])); continue
            author, meta = client.api('authors/' + ranked[0][0].rsplit('/', 1)[-1])
            if author_name_evidence(author, toks) and 'https://openalex.org/I20089843' in institution_ids(author):
                extra.append(dict(lab_id=key, pi=leader, author=author['id'], orcid=(author.get('orcid') or '').rsplit('/', 1)[-1],
                                  method='cs_combined_list_anchor', evidence=dict(hits=ranked[0][1], works=len(ws), author_sha256=meta['sha256'])))
            else:
                gaps.append(dict(lab_id=key, lab=u['name'], pi=leader, works=len(ws), reason='name/Princeton check failed'))
    path = WORK / 'extra_identities.json'
    prior = json.loads(path.read_text()) if path.exists() else []
    merged = {(e['lab_id'], e['author']): e for e in prior + extra}
    path.write_text(json.dumps(list(merged.values()), indent=1, ensure_ascii=False))
    (WORK / 'identity_gaps_combined.json').write_text(json.dumps(gaps, indent=1, ensure_ascii=False))
    print(json.dumps(dict(newly_verified=len(extra), still_unverified=len(gaps),
                          unverified=[(g['lab'][:30], g['pi'], g['works']) for g in gaps][:40]), ensure_ascii=False))


COMMANDS = {'anchor-more': anchor_more, 'identities': identities, 'fetch': fetch, 'tier': tier, 'records': records, 'package': package, 'import': import_catalog}


if __name__ == '__main__':
    COMMANDS[sys.argv[1]]()
