# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/epfl_infoscience.py (sha256 698fb87dc3f058dd5b4cb89d1f5b4da3989cddec5501ff663037e525be0ec6ac); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""EPFL Infoscience evidence for the EPFL unipapers stage.

Infoscience is EPFL's institutional research repository (DSpace-CRIS, run by the EPFL
Library). Its public REST API (robots.txt leaves /server/api open) exposes:
  - OrgUnit entities: acronym, institutional unit code, director, active flag, parent.
  - Person entities: SCIPER, ORCID/OpenAlex identifiers, unit affiliation.
  - Publications the Library attributes to each unit (RELATION.OrgUnit.publications).
Responses run ~40 KB per record, so bodies are stored gzip-compressed. The recorded
sha256 is of the uncompressed bytes exactly as served.

Layout under data/reviews/unipapers/<EPFL>/infoscience/:
  bodies/<source_id>.json.gz   sources.jsonl   attempts.jsonl
  unit_matches.json            inventory lab -> Infoscience OrgUnit (exact code or acronym)
  publications.csv.gz          derived, one row per (lab, Infoscience item)

CLI (project interpreter, project root):
  python scripts/epfl_infoscience.py orgunits
  python scripts/epfl_infoscience.py match
  python scripts/epfl_infoscience.py unit-pubs [LAB_ID ...]
  python scripts/epfl_infoscience.py extract
  python scripts/epfl_infoscience.py resolve    free OpenAlex DOI singletons for units without a verified PI
  python scripts/epfl_infoscience.py activity-fetch | activity-build   dated unit activity -> data/batches/epfl_infoscience_activity
"""
import argparse, csv, gzip, hashlib, io, json, re, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sweep10_lib as L

ROOT = L.ROOT
UID = 'swiss-federal-institute-of-technology-lausanne'
OUT = ROOT / 'data/reviews/unipapers' / UID / 'infoscience'
API = 'https://infoscience.epfl.ch/server/api/discover/search/objects?'
PAGE = 100
# Infoscience issue dates can precede the OpenAlex publication date by a few weeks, so the
# capture starts one year before the 2016 window. Work dates are filtered downstream.
# Infoscience reads a bare-year bound as 1 January, so [2015 TO 2026] stops at 2026-01-01;
# a second open-ended query from 2026 (SINCE) recovers everything issued later.
DATE_MIN, DATE_MAX, SINCE = '2015', '2026', '2026'
PLACEHOLDER = '#PLACEHOLDER_PARENT_METADATA_VALUE#'


def captured():
    return {m['requested_url']: m for m in L.read_jsonl(OUT / 'sources.jsonl')}


def fetch_json(url, done=None):
    """Capture one API response (resumable: an already-captured URL is not re-requested)."""
    done = captured() if done is None else done
    if url in done:
        return done[url]
    (OUT / 'bodies').mkdir(parents=True, exist_ok=True)
    source_id = L.stable_id('src_is', url)
    now = datetime.now(timezone.utc).isoformat()
    attempt = dict(source_id=source_id, requested_url=url, retrieved_at_utc=now, university_id=UID)
    ok, why = L.robots_allowed(url)
    if not ok:
        L.append_jsonl(OUT / 'attempts.jsonl', dict(attempt, status='robots_disallowed', error=why))
        raise RuntimeError('robots.txt disallows ' + url)
    r = L.get(url, timeout=120)
    attempt.update(http_status=r.status_code, final_url=r.url)
    if r.status_code != 200 or not r.content:
        L.append_jsonl(OUT / 'attempts.jsonl', dict(attempt, status='http_error', error=f'HTTP {r.status_code}'))
        raise RuntimeError(f'HTTP {r.status_code}: {url}')
    digest = hashlib.sha256(r.content).hexdigest()
    path = OUT / 'bodies' / (source_id + '_' + digest[:12] + '.json.gz')
    tmp = path.with_suffix('.part')
    tmp.write_bytes(gzip.compress(r.content, 6))
    tmp.replace(path)
    meta = dict(source_id=source_id, requested_url=url, final_url=r.url, observed_on=L.AS_OF, retrieved_at_utc=now,
                http_status=r.status_code, content_type=r.headers.get('Content-Type', ''), sha256=digest,
                snapshot_path=str(path.relative_to(ROOT)), storage='gzip')
    L.append_jsonl(OUT / 'sources.jsonl', meta)
    L.append_jsonl(OUT / 'attempts.jsonl', dict(attempt, status='captured', sha256=digest, bytes=len(r.content)))
    done[url] = meta
    return meta


def load(meta):
    """Decompress a capture and check it against the hash of the bytes as served."""
    data = (ROOT / meta['snapshot_path']).read_bytes()
    if meta.get('storage') == 'gzip':
        data = gzip.decompress(data)
    assert hashlib.sha256(data).hexdigest() == meta['sha256'], 'Changed capture: ' + meta['snapshot_path']
    return json.loads(data)


def search_url(configuration, page, scope='', query='', dated=False, since=''):
    params = dict(configuration=configuration, size=PAGE, page=page)
    if scope:
        params['scope'] = scope
    if query:
        params['query'] = query
    if dated:
        params['f.dateIssued.min'], params['f.dateIssued.max'] = DATE_MIN, DATE_MAX
    if since:
        params['f.dateIssued.min'] = since
    return API + urlencode(params)


def paged(configuration, scope='', query='', dated=False, done=None, since=''):
    """Every page of one discovery query; returns the captured metadata in page order."""
    done = captured() if done is None else done
    metas, page = [], 0
    while True:
        meta = fetch_json(search_url(configuration, page, scope, query, dated, since), done)
        metas.append(meta)
        info = load(meta)['_embedded']['searchResult']['page']
        page += 1
        if page >= info.get('totalPages', 0):
            return metas


def listing_metas(orgunit_uuid, done):
    """Captured pages of a unit's publication listing (window query, then the SINCE
    supplement), or None while any page is missing."""
    metas = []
    for kind in ('dated', 'since'):
        page = 0
        while True:
            url = search_url('RELATION.OrgUnit.publications', page, scope=orgunit_uuid,
                             dated=kind == 'dated', since=SINCE if kind == 'since' else '')
            if url not in done:
                return None
            metas.append(done[url])
            page += 1
            if page >= load(done[url])['_embedded']['searchResult']['page'].get('totalPages', 0):
                break
    return metas


def objects(meta):
    result = load(meta)['_embedded']['searchResult']
    return [o['_embedded']['indexableObject'] for o in result.get('_embedded', {}).get('objects', [])]


def values(item, key):
    return [v['value'] for v in item['metadata'].get(key, []) if v['value'] != PLACEHOLDER]


def first(item, key):
    found = values(item, key)
    return found[0] if found else ''


def orgunit_rows():
    rows = []
    for meta in paged('orgunit'):
        for item in objects(meta):
            rows.append(dict(uuid=item['uuid'], handle=item.get('handle', ''), title=first(item, 'dc.title'),
                             acronym=first(item, 'oairecerif.acronym'), unit_code=first(item, 'epfl.unit.code'),
                             unit_type=first(item, 'dc.type'), active=first(item, 'epfl.orgUnit.active'),
                             directors=values(item, 'crisou.director'),
                             parent=first(item, 'organization.parentOrganization'),
                             created=first(item, 'dc.date.created'), source_id=meta['source_id']))
    return rows


def match():
    """Pair each inventory EPFL unit with exactly one Infoscience OrgUnit.

    The institutional unit code from the reviewed unit-API head record is used where it
    exists; otherwise the directory acronym must equal exactly one OrgUnit acronym, or,
    failing that, exactly one OrgUnit acronym ignoring letter case.
    Ambiguous or missing pairs are recorded and left unmatched.
    """
    units = orgunit_rows()
    by_code, by_acro, by_folded = {}, {}, {}
    for u in units:
        if u['unit_code']:
            by_code.setdefault(u['unit_code'], []).append(u)
        if u['acronym']:
            by_acro.setdefault(u['acronym'], []).append(u)
            by_folded.setdefault(u['acronym'].casefold(), []).append(u)
    codes = {}
    for r in csv.DictReader(open(ROOT / 'data/processed/leadership_evidence.csv', encoding='utf-8')):
        if r['university_id'] == UID and r['evidence_format'] == 'epfl_unit_json_head':
            codes[r['lab_id']] = str(json.loads(r['structured_evidence'])['unit_code'])
    out = []
    for lab in csv.DictReader(open(ROOT / 'data/processed/labs.csv', encoding='utf-8')):
        if lab['university_id'] != UID:
            continue
        row = dict(lab_id=lab['lab_id'], lab_name=lab['lab_name'], acronym=lab['acronym'], unit_code=codes.get(lab['lab_id'], ''))
        if row['unit_code']:
            hits, method = by_code.get(row['unit_code'], []), 'unit_code'
        else:
            hits, method = by_acro.get(lab['acronym'], []) if lab['acronym'] else [], 'acronym'
            if not hits and lab['acronym']:
                # Directory styling ("BioRob") versus the institutional unit acronym ("BIOROB").
                hits, method = by_folded.get(lab['acronym'].casefold(), []), 'acronym_casefold'
        if len(hits) == 1:
            u = hits[0]
            row.update(status='matched', method=method, orgunit_uuid=u['uuid'], orgunit_title=u['title'],
                       orgunit_acronym=u['acronym'], orgunit_code=u['unit_code'], orgunit_active=u['active'],
                       orgunit_directors=u['directors'], orgunit_source_id=u['source_id'])
        else:
            row.update(status='ambiguous' if hits else 'not_found', method=method, candidates=[h['uuid'] for h in hits])
        out.append(row)
    write_json(OUT / 'orgunits.json', units)
    write_json(OUT / 'unit_matches.json', out)
    print(json.dumps(dict(orgunits=len(units), active=sum(u['active'] == 'true' for u in units),
                          types=Counter(u['unit_type'] for u in units).most_common(8),
                          labs=len(out), status=Counter(r['status'] + ':' + r['method'] for r in out))))


def unit_pubs(lab_ids):
    matches = [r for r in json.loads((OUT / 'unit_matches.json').read_text()) if r['status'] == 'matched']
    if lab_ids:
        matches = [r for r in matches if r['lab_id'] in lab_ids]
    done = captured()
    for i, r in enumerate(matches, 1):
        try:
            metas = paged('RELATION.OrgUnit.publications', scope=r['orgunit_uuid'], dated=True, done=done)
            paged('RELATION.OrgUnit.publications', scope=r['orgunit_uuid'], since=SINCE, done=done)
            total = load(metas[0])['_embedded']['searchResult']['page']['totalElements']
            print(f"{i}/{len(matches)} {r['acronym']} records={total} pages={len(metas)}", flush=True)
        except Exception as e:
            print(f"{i}/{len(matches)} {r['acronym']} FAILED {str(e)[:200]}", flush=True)


FIELDS = ['lab_id', 'orgunit_uuid', 'item_uuid', 'handle', 'doi', 'pmid', 'issued', 'item_type', 'title',
          'authors', 'author_authorities', 'author_orcids', 'unit_ids', 'unit_managers', 'unit_manager_authorities',
          'source_id', 'source_sha256']


def extract():
    matches = [r for r in json.loads((OUT / 'unit_matches.json').read_text()) if r['status'] == 'matched']
    done = captured()
    rows, missing = [], []
    for r in matches:
        metas = listing_metas(r['orgunit_uuid'], done)
        if metas is None:
            missing.append(r['lab_id']); continue
        seen = set()
        for meta in metas:
            for item in objects(meta):
                if item['uuid'] in seen:
                    continue
                seen.add(item['uuid'])
                md = item['metadata']
                rows.append(dict(lab_id=r['lab_id'], orgunit_uuid=r['orgunit_uuid'], item_uuid=item['uuid'],
                                 handle=item.get('handle', ''), doi=first(item, 'dc.identifier.doi').lower(),
                                 pmid=first(item, 'dc.identifier.pmid'), issued=first(item, 'dc.date.issued'),
                                 item_type=first(item, 'dc.type'), title=first(item, 'dc.title')[:300],
                                 authors=json.dumps([v['value'] for v in md.get('dc.contributor.author', [])], ensure_ascii=False),
                                 author_authorities=json.dumps([v.get('authority') for v in md.get('dc.contributor.author', [])]),
                                 author_orcids=json.dumps([v['value'] for v in md.get('epfl.author.orcid', [])]),
                                 unit_ids=json.dumps(values(item, 'cris.virtual.unitId')),
                                 unit_managers=json.dumps(values(item, 'cris.virtual.unitManager'), ensure_ascii=False),
                                 unit_manager_authorities=json.dumps([v.get('authority') for v in md.get('cris.virtual.unitManager', []) if v['value'] != PLACEHOLDER]),
                                 source_id=meta['source_id'], source_sha256=meta['sha256']))
    buf = io.StringIO()
    w = csv.DictWriter(buf, FIELDS, lineterminator='\n')
    w.writeheader(); w.writerows(rows)
    tmp = OUT / 'publications.csv.gz.part'
    tmp.write_bytes(gzip.compress(buf.getvalue().encode('utf-8'), 6))
    tmp.replace(OUT / 'publications.csv.gz')
    print(json.dumps(dict(labs_matched=len(matches), labs_missing_capture=len(missing), rows=len(rows),
                          rows_with_doi=sum(bool(x['doi']) for x in rows),
                          distinct_dois=len({x['doi'] for x in rows if x['doi']}))))


def held_lab_ids():
    """Inventory EPFL units without a verified publication identity."""
    verified = {r['lab_id'] for r in csv.DictReader(open(ROOT / 'data/publications/pi_identities.csv', encoding='utf-8'))}
    return {r['lab_id'] for r in csv.DictReader(open(ROOT / 'data/processed/labs.csv', encoding='utf-8'))
            if r['university_id'] == UID and r['lab_id'] not in verified}


def publication_rows():
    with gzip.open(OUT / 'publications.csv.gz', 'rt', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def resolve(spacing=0.2, workers=4):
    """Free OpenAlex singleton lookups (works/doi:) for units still lacking a verified identity.

    Results land in the stage cache (data/reviews/unipapers/<EPFL>/raw) under the same
    source ids the shared collector uses, so a later merge can seed them unchanged.
    """
    import threading, time
    from concurrent.futures import ThreadPoolExecutor
    from publications import Client
    from bibliography_anchor import work_by_doi
    held = held_lab_ids()
    dois = sorted({r['doi'] for r in publication_rows() if r['lab_id'] in held and r['doi']})
    stage = OUT.parent
    lock, last, local = threading.Lock(), [0.0], threading.local()
    def gate():
        with lock:
            time.sleep(max(0, spacing - (time.monotonic() - last[0])))
            last[0] = time.monotonic()
    def one(doi):
        if not hasattr(local, 'client'):
            local.client = Client(out=stage); local.client.request_gate = gate
        try:
            work_by_doi(local.client, doi)
            return 'ok'
        except (RuntimeError, ValueError) as e:
            return 'not_indexed' if 'HTTP 404' in str(e) else ('different_doi' if 'different DOI' in str(e) else 'error:' + str(e)[:80])
    print(json.dumps(dict(held_labs=len(held), dois=len(dois))), flush=True)
    outcome = Counter()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, status in enumerate(pool.map(one, dois), 1):
            outcome[status.split(':')[0]] += 1
            if status.startswith('error') and 'budget' in status:
                print('STOP', status, flush=True); break
            if i % 500 == 0:
                print(i, dict(outcome), flush=True)
    print('done', dict(outcome), flush=True)


ACTIVITY = ROOT / 'data/batches/epfl_infoscience_activity'
SOURCE_FIELDS = ['source_id', 'requested_url', 'final_url', 'observed_on', 'retrieved_at_utc', 'http_status',
                 'content_type', 'sha256', 'snapshot_path', 'error']
EVIDENCE_FIELDS = ['evidence_id', 'lab_id', 'source_id', 'source_url', 'evidence_type', 'event_start', 'event_end',
                   'date_text', 'evidence_quote', 'evidence_summary', 'reviewed_on', 'review_method', 'affiliation_supported']


def activity_url(orgunit_uuid, year):
    """The earliest record the EPFL Library attributes to this unit in this calendar year.

    A bare-year upper bound means 1 January, so [Y TO Y+1] with ascending issue dates
    puts year-Y records first; activity_build still checks the issue year."""
    return API + urlencode(dict(configuration='RELATION.OrgUnit.publications', scope=orgunit_uuid, size=1, page=0,
                                sort='dc.date.issued,ASC',
                                **{'f.dateIssued.min': str(year), 'f.dateIssued.max': str(year + 1)}))


def activity_targets():
    """(lab, OrgUnit, year) for every in-window year with a dated record on the unit's listing."""
    matches = {r['lab_id']: r for r in json.loads((OUT / 'unit_matches.json').read_text()) if r['status'] == 'matched'}
    years = {}
    for r in publication_rows():
        if r['lab_id'] in matches and '2016-01-01' <= r['issued'][:10] <= L.AS_OF and len(r['issued']) >= 4:
            years.setdefault(r['lab_id'], set()).add(int(r['issued'][:4]))
    return [(lab_id, matches[lab_id]['orgunit_uuid'], y) for lab_id in sorted(years) for y in sorted(years[lab_id])]


def activity_fetch():
    """Small uncompressed captures, so evidence text replays directly from each snapshot."""
    (ACTIVITY / 'sources').mkdir(parents=True, exist_ok=True)
    done = {r['requested_url'] for r in L.read_jsonl(ACTIVITY / 'captures.jsonl')}
    targets = [t for t in activity_targets() if activity_url(t[1], t[2]) not in done]
    print('lab-years to capture', len(targets), flush=True)
    for i, (lab_id, uuid, year) in enumerate(targets, 1):
        url = activity_url(uuid, year)
        source_id = L.stable_id('src_isact', url)
        now = datetime.now(timezone.utc).isoformat()
        try:
            r = L.get(url, timeout=120)
        except Exception as e:
            print('FAILED', lab_id, year, type(e).__name__, flush=True); continue
        if r.status_code != 200 or not r.content:
            print('FAILED', lab_id, year, r.status_code, flush=True); continue
        path = ACTIVITY / 'sources' / (source_id + '.json')
        path.write_bytes(r.content)
        L.append_jsonl(ACTIVITY / 'captures.jsonl', dict(source_id=source_id, requested_url=url, final_url=r.url, observed_on=L.AS_OF,
                                                          retrieved_at_utc=now, http_status=r.status_code,
                                                          content_type=r.headers.get('Content-Type', ''),
                                                          sha256=hashlib.sha256(r.content).hexdigest(),
                                                          snapshot_path=str(path.relative_to(ROOT)), error='',
                                                          lab_id=lab_id, orgunit_uuid=uuid, year=year))
        if i % 100 == 0:
            print(i, '/', len(targets), flush=True)
    print('done', flush=True)


def activity_build():
    """Write the batch CSVs finalize.py integrates. activity_evidence.csv is written last."""
    from common import clean, source_text
    captures = list({r['requested_url']: r for r in L.read_jsonl(ACTIVITY / 'captures.jsonl')}.values())
    sources, evidence, skipped = [], [], Counter()
    for c in captures:
        meta = {k: c[k] for k in SOURCE_FIELDS}
        data = (ROOT / meta['snapshot_path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == meta['sha256']
        payload = json.loads(data)
        assert f"scope={c['orgunit_uuid']}" in payload['_links']['self']['href']
        items = [o['_embedded']['indexableObject'] for o in payload['_embedded']['searchResult'].get('_embedded', {}).get('objects', [])]
        text = source_text(meta)
        kept = None
        for item in items:
            issued, title = first(item, 'dc.date.issued'), clean(first(item, 'dc.title'))
            if not ('2016-01-01' <= issued[:10] <= L.AS_OF and issued.startswith(str(c['year']))):
                skipped['issue_date_outside_window'] += 1; continue
            if title and title not in text:
                # JSON escapes quotation marks and backslashes; quote the longest unescaped stretch.
                parts = sorted((p.strip() for p in re.split(r'["\\]', title)), key=len, reverse=True)
                title = next((p for p in parts if len(p) >= 25 and p in text), '')
            if not title or issued not in text:
                skipped['title_not_verbatim_in_capture'] += 1; continue
            kept = (item, issued, title)
        if not kept:
            continue
        item, issued, title = kept
        start = issued if len(issued) == 10 else (issued + '-01' if len(issued) == 7 else issued + '-01-01')
        end = issued if len(issued) == 10 else (issued + '-28' if len(issued) == 7 else issued + '-12-31')
        end = min(end, L.AS_OF)
        sources.append(meta)
        evidence.append(dict(evidence_id=L.stable_id('ev_isact', c['lab_id'] + '|' + c['source_id']), lab_id=c['lab_id'],
                             source_id=c['source_id'], source_url=c['requested_url'], evidence_type='institutional_repository_unit_publication',
                             event_start=start, event_end=end, date_text=issued, evidence_quote=title,
                             evidence_summary='Infoscience, EPFL\'s institutional repository, attributes this publication (issued '
                             + issued + ') to the unit in its EPFL Library unit listing. This supports research output by the unit '
                             'in that year; it does not establish continuous operation or any PI\'s tenure.',
                             reviewed_on=L.AS_OF, review_method='official_repository_unit_attribution_exact_record', affiliation_supported='True'))
    _write_csv(ACTIVITY / 'sources.csv', sources, SOURCE_FIELDS)
    _write_csv(ACTIVITY / 'activity_evidence.csv', evidence, EVIDENCE_FIELDS)
    print(json.dumps(dict(captures=len(captures), evidence=len(evidence), labs=len({e['lab_id'] for e in evidence}),
                          lab_years=len({(e['lab_id'], e['event_start'][:4]) for e in evidence}), skipped=dict(skipped))))


def _write_csv(path, rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fields, extrasaction='ignore', lineterminator='\n')
    w.writeheader(); w.writerows(rows)
    tmp = path.with_suffix('.part')
    tmp.write_text(buf.getvalue(), encoding='utf-8')
    tmp.replace(path)


def write_json(path, value):
    tmp = path.with_suffix(path.suffix + '.part')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=1) + '\n')
    tmp.replace(path)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('orgunits'); sub.add_parser('match'); sub.add_parser('extract'); sub.add_parser('resolve'); sub.add_parser('activity-fetch'); sub.add_parser('activity-build')
    p = sub.add_parser('unit-pubs'); p.add_argument('lab_ids', nargs='*')
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.cmd == 'orgunits':
        print(len(orgunit_rows()), 'orgunits captured')
    elif a.cmd == 'match':
        match()
    elif a.cmd == 'unit-pubs':
        unit_pubs(set(a.lab_ids))
    elif a.cmd == 'extract':
        extract()
    elif a.cmd == 'resolve':
        resolve()
    elif a.cmd == 'activity-fetch':
        activity_fetch()
    elif a.cmd == 'activity-build':
        activity_build()


if __name__ == '__main__':
    main()
