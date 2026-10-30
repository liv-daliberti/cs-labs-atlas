# Vendored 2026-10-30 from /n/fs/resemble/homogenizing-science/scripts/unipapers_lib.py (sha256 f7228ef55ee02fcdee4738876f348cf35a956c2d3a419d50995f5ab664485c93); see vendor/PROVENANCE.tsv and tools/vendor_sync.py.
"""University-by-university publication linking for labs already in the inventory.

One university at a time: capture official evidence that ties a lab's named leader to an
ORCID (institutional profile or the lab homepage the directory links), check that ORCID
against OpenAlex singletons, and record official lab bibliographies. Nothing here touches
the shared publication tables; scripts/merge_unipapers.py validates and merges a stage.

Layout:
  data/reviews/unipapers/<university_id>/snapshots/<source_id>.<ext>   original bytes
  data/reviews/unipapers/<university_id>/sources.jsonl                 one line per capture
  data/reviews/unipapers/<university_id>/attempts.jsonl                every request
  data/reviews/unipapers/<university_id>/raw/                          OpenAlex singleton cache
  data/reviews/unipapers/<university_id>/proposals.json                reviewed identities, bibliographies, gaps

CLI (project interpreter, project root):
  python scripts/unipapers_lib.py labs     UID [--todo]
  python scripts/unipapers_lib.py fetch    UID URL [URL ...]
  python scripts/unipapers_lib.py show     UID SOURCE_ID [--links] [--grep REGEX] [--max N]
  python scripts/unipapers_lib.py orcids   UID SOURCE_ID
  python scripts/unipapers_lib.py author   UID ORCID [ORCID ...]
  python scripts/unipapers_lib.py works    UID DOI [DOI ...]
  python scripts/unipapers_lib.py list     UID
  python scripts/unipapers_lib.py anchor   UID LAB_ID SOURCE_ID SELECTOR --tokens GIVEN SURNAME [--pi-name NAME] [--propose]
  python scripts/unipapers_lib.py gap      UID LAB_ID REASON
OpenAlex calls are singletons (authors/orcid:, works/doi:), which do not draw on the list budget.
"""
import argparse, csv, hashlib, json, re, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sweep10_lib as L
from publications import Client, normalize_name, institution_ids, author_name_evidence

ROOT = L.ROOT
STAGE = ROOT / 'data/reviews/unipapers'
ORCID = re.compile(r'(\d{4}-\d{4}-\d{4}-\d{3}[\dX])')


def stage(uid):
    return STAGE / uid


def read_csv(path):
    with Path(path).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def fetch(uid, url):
    d = stage(uid)
    (d / 'snapshots').mkdir(parents=True, exist_ok=True)
    source_id = L.stable_id('src_up', url)
    now = datetime.now(timezone.utc).isoformat()
    attempt = dict(source_id=source_id, requested_url=url, retrieved_at_utc=now, university_id=uid)
    ok, why = L.robots_allowed(url)
    if not ok:
        attempt.update(status='robots_disallowed', http_status='', error=why)
        L.append_jsonl(d / 'attempts.jsonl', attempt)
        return attempt
    try:
        r = L.get(url)
    except Exception as e:
        attempt.update(status='request_failed', http_status='', error=f'{type(e).__name__}: {e}'[:400])
        L.append_jsonl(d / 'attempts.jsonl', attempt)
        return attempt
    attempt.update(http_status=r.status_code, final_url=r.url)
    if r.status_code != 200 or not r.content:
        attempt.update(status='http_error', error=f'HTTP {r.status_code}')
        L.append_jsonl(d / 'attempts.jsonl', attempt)
        return attempt
    path = d / 'snapshots' / (source_id + L._ext(r.headers.get('Content-Type', ''), r.url))
    path.write_bytes(r.content)
    archive = re.match(r'https?://web\.archive\.org/web/(\d{8,14})', r.url or url)
    meta = dict(source_id=source_id, requested_url=url, final_url=r.url, observed_on=L.AS_OF, retrieved_at_utc=now,
                http_status=r.status_code, content_type=r.headers.get('Content-Type', ''),
                sha256=hashlib.sha256(r.content).hexdigest(), snapshot_path=str(path.relative_to(ROOT)),
                archive_capture=archive.group(1) if archive else '')
    L.append_jsonl(d / 'sources.jsonl', meta)
    attempt.update(status='captured', sha256=meta['sha256'], bytes=len(r.content))
    L.append_jsonl(d / 'attempts.jsonl', attempt)
    return dict(attempt, **meta)


def university_labs(uid):
    labs = [r for r in read_csv(ROOT / 'data/processed/labs.csv') if r['university_id'] == uid]
    leaders = {}
    for r in read_csv(ROOT / 'data/processed/leadership_evidence.csv'):
        leaders.setdefault(r['lab_id'], []).append(r)
    verified = Counter(r['lab_id'] for r in read_csv(ROOT / 'data/publications/pi_identities.csv'))
    reviews = json.loads((ROOT / 'data/publications/identity_reviews.json').read_text())
    reviewed = Counter(r['lab_id'] for r in reviews)
    bibs = Counter(r['lab_id'] for r in json.loads((ROOT / 'data/publications/bibliography_sources.json').read_text()))
    insts = Counter(r['openalex_institution_id'] for r in reviews
                    if any(l['lab_id'] == r['lab_id'] for l in labs))
    return labs, leaders, verified, reviewed, bibs, insts


def leader_names(lab, leaders):
    """Named leaders: reviewed leadership rows, else the directory's recorded PI string."""
    names = [r['person_name'] for r in leaders.get(lab['lab_id'], [])]
    if not names and lab['principal_investigator']:
        names = [x.strip() for x in re.split(r';|\n| & ', lab['principal_investigator']) if x.strip()]
    return list(dict.fromkeys(names))


def author(uid, orcid):
    data, meta = Client(out=stage(uid)).api('authors/orcid:' + orcid)
    return data, meta


def install(uid, meta):
    """Expose a stage capture to publications.Client(out=stage) under its requested URL."""
    from publications import sid, atomic_json
    raw_dir = stage(uid) / 'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    body = (ROOT / meta['snapshot_path']).read_bytes()
    assert hashlib.sha256(body).hexdigest() == meta['sha256']
    source_id = sid('src', meta['requested_url'])
    if not (raw_dir / (source_id + '.meta.json')).exists():
        (raw_dir / (source_id + '.body')).write_bytes(body)
        atomic_json(raw_dir / (source_id + '.meta.json'),
                    {**meta, 'source_id': source_id, 'original_source_id': meta['source_id'],
                     'original_snapshot_path': meta['snapshot_path'],
                     'snapshot_path': str((raw_dir / (source_id + '.body')).relative_to(ROOT)), 'http_status': 200})
    return source_id


def resolve(uid, dois, workers=8):
    """Free singleton DOI lookups into the stage cache; returns {doi: work or error string}."""
    import threading, time
    from concurrent.futures import ThreadPoolExecutor
    from bibliography_anchor import work_by_doi
    lock, last, local = threading.Lock(), [0.0], threading.local()
    def gate():
        with lock:
            time.sleep(max(0, .12 - (time.monotonic() - last[0])))
            last[0] = time.monotonic()
    def one(doi):
        if not hasattr(local, 'client'):
            local.client = Client(out=stage(uid)); local.client.request_gate = gate
        try:
            return doi, work_by_doi(local.client, doi)[0]
        except (RuntimeError, ValueError) as e:
            return doi, str(e)[:160]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(one, dois))


def load_proposals(uid):
    path = stage(uid) / 'proposals.json'
    return json.loads(path.read_text()) if path.exists() else {'identities': [], 'bibliographies': [], 'gaps': []}


def save_proposals(uid, value):
    from publications import atomic_json
    atomic_json(stage(uid) / 'proposals.json', value)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('labs'); p.add_argument('uid'); p.add_argument('--todo', action='store_true')
    p = sub.add_parser('fetch'); p.add_argument('uid'); p.add_argument('urls', nargs='+')
    p = sub.add_parser('show'); p.add_argument('uid'); p.add_argument('source_id')
    p.add_argument('--links', action='store_true'); p.add_argument('--grep', default=''); p.add_argument('--max', type=int, default=20000)
    p = sub.add_parser('orcids'); p.add_argument('uid'); p.add_argument('source_id')
    p = sub.add_parser('author'); p.add_argument('uid'); p.add_argument('orcids', nargs='+')
    p = sub.add_parser('works'); p.add_argument('uid'); p.add_argument('dois', nargs='+')
    p = sub.add_parser('list'); p.add_argument('uid')
    p = sub.add_parser('anchor'); p.add_argument('uid'); p.add_argument('lab_id'); p.add_argument('source_id'); p.add_argument('selector')
    p.add_argument('--tokens', nargs='+', required=True); p.add_argument('--pi-name', default='')
    p.add_argument('--institution', default=''); p.add_argument('--propose', action='store_true'); p.add_argument('--note', default='')
    p.add_argument('--more', nargs='+', default=[], help='further pages: SOURCE_ID or SOURCE_ID::SELECTOR (default: same selector)')
    p.add_argument('--pubmed', action='store_true', help='PubMed links inside the selectors also identify listed works')
    p.add_argument('--text-ids', action='store_true', help='DOIs and "PMID: n" printed inside the selectors also identify listed works')
    p.add_argument('--name-source', default='', help='capture whose visible text gives the official full name when the inventory records a short form')
    p = sub.add_parser('gap'); p.add_argument('uid'); p.add_argument('lab_id'); p.add_argument('reason')
    p = sub.add_parser('bib', help='propose an official lab bibliography for a lab whose leader identity is already verified')
    p.add_argument('uid'); p.add_argument('lab_id'); p.add_argument('source_id'); p.add_argument('selector')
    p.add_argument('--pubmed', action='store_true'); p.add_argument('--text-ids', action='store_true')
    p.add_argument('--propose', action='store_true'); p.add_argument('--note', default='')
    a = ap.parse_args()
    if a.cmd == 'labs':
        labs, leaders, verified, reviewed, bibs, insts = university_labs(a.uid)
        print(f'{len(labs)} labs; OpenAlex institution ids used by existing reviews: {dict(insts)}')
        for lab in sorted(labs, key=lambda r: r['lab_name'].casefold()):
            if a.todo and verified[lab['lab_id']]:
                continue
            names = '; '.join(leader_names(lab, leaders)) or '-'
            print(f"{lab['lab_id']}\t{lab['lab_name'][:50]}\tleaders={names[:60]}\tverified={verified[lab['lab_id']]}"
                  f"\treviews={reviewed[lab['lab_id']]}\tbib={bibs[lab['lab_id']]}\thome={lab['homepage_url']}\tdir={lab['directory_source_url']}")
    elif a.cmd == 'fetch':
        for url in a.urls:
            r = fetch(a.uid, url)
            extra = ''
            if r.get('status') == 'captured':
                t = L.text(r)
                title = ''
                if r['snapshot_path'].endswith('.html'):
                    ts = L.soup(r).title
                    title = L.clean(ts.get_text()) if ts else ''
                found = sorted(set(ORCID.findall(L.raw(r).decode('utf-8', 'ignore'))))
                extra = f" bytes={r['bytes']} text_chars={len(t)} title={title[:80]!r} orcids={found[:4]}"
                if r['snapshot_path'].endswith('.html') and len(t) < 600:
                    extra += ' WARNING: little visible text (client-rendered shell?)'
            print(f"{r['source_id']} {r['status']} http={r.get('http_status', '')} {r.get('final_url', url)}{extra} {r.get('error', '')}")
    elif a.cmd in ('show', 'orcids'):
        meta = L.sources(stage(a.uid))[a.source_id]
        if a.cmd == 'orcids':
            s = L.soup(meta)
            print('title:', L.clean(s.title.get_text()) if s.title else '')
            for link in s.select('a[href*="orcid.org/"]'):
                block = link.find_parent(['li', 'div', 'section', 'article', 'p', 'td']) or link
                print(ORCID.search(link['href']).group(1) if ORCID.search(link['href']) else link['href'],
                      '|', L.clean(link.get_text(' '))[:60], '|', L.clean(block.get_text(' '))[:200])
            bare = sorted(set(ORCID.findall(L.raw(meta).decode('utf-8', 'ignore'))))
            print('all ORCID-shaped strings in bytes:', bare)
        elif a.links:
            for i, link in enumerate(L.soup(meta).select('a[href]')):
                line = f"{i}\t{L.clean(link.get_text(' '))}\t{urljoin(meta.get('final_url') or meta['requested_url'], link['href'])}"
                if not a.grep or re.search(a.grep, line, re.I):
                    print(line[:300])
        else:
            t = L.text(meta)
            if a.grep:
                for m in re.finditer(a.grep, t, re.I):
                    print('...' + t[max(0, m.start() - 150):m.end() + 150] + '...')
            else:
                print(t[:a.max])
    elif a.cmd == 'author':
        _, _, _, _, _, insts = university_labs(a.uid)
        for orcid in a.orcids:
            try:
                data, meta = author(a.uid, orcid)
            except Exception as e:
                print(orcid, 'ERROR', str(e)[:200]); continue
            inst = {i: '' for i in institution_ids(data)}
            hit = sorted(set(inst) & set(insts))
            print(f"{orcid}\t{data['id']}\t{data.get('display_name')}\talts={(data.get('display_name_alternatives') or [])[:5]}"
                  f"\tworks={data.get('works_count')}\tuniversity_inst_match={hit}\tlast_known={[i.get('display_name') for i in data.get('last_known_institutions') or []]}")
    elif a.cmd == 'works':
        c = Client(out=stage(a.uid))
        for doi in a.dois:
            try:
                w, _ = c.api('works/doi:' + doi.lower().removeprefix('https://doi.org/'))
            except Exception as e:
                print(doi, 'ERROR', str(e)[:200]); continue
            byline = [(x.get('author', {}).get('display_name'), x.get('author_position'),
                       [i.get('display_name') for i in x.get('institutions', [])][:2]) for x in w.get('authorships', [])]
            print(doi, w['id'], w.get('publication_date'), (w.get('title') or '')[:70], '| last:', byline[-1] if byline else None)
    elif a.cmd == 'anchor':
        from bibliography_anchor import (FORMAT, ANCHOR_MIN_SHARE, ANCHOR_MIN_WORKS, COMPETITOR_MAX_SHARE,
                                         listed_dois, tally, anchor_author)
        labs, leaders, verified, reviewed, bibs, insts = university_labs(a.uid)
        lab = next(r for r in labs if r['lab_id'] == a.lab_id)
        captures = L.sources(stage(a.uid))
        meta = captures[a.source_id]
        pages = [(meta, a.selector)] + [(captures[x.split('::')[0]], x.split('::', 1)[1] if '::' in x else a.selector) for x in a.more]
        dois = set()
        for page, selector in pages:
            install(a.uid, page)
            dois |= set(listed_dois(L.decoded(page), selector, a.pubmed, a.text_ids))
        dois = sorted(dois)
        found = resolve(a.uid, dois)
        from bibliography_anchor import unique_works
        works = unique_works([w for w in found.values() if isinstance(w, dict)])
        in_window = sum('2016-01-01' <= (w.get('publication_date') or '') <= '2026-10-12' for w in works)
        ranked = tally(works, a.tokens)
        failed = sum(not isinstance(w, dict) for w in found.values())
        print(f"{lab['lab_name']}: listed={len(dois)} unique_works={len(works)} in_window={in_window} failed={failed} listed_twice={len(dois) - failed - len(works)}")
        for aid, n in ranked[:4]:
            print(f'   {aid} on {n} ({n / max(1, len(works)):.0%})')
        if not ranked:
            print('NO ANCHOR: no full-name byline'); return
        primary, hits = ranked[0]
        inst = a.institution or (max(insts, key=insts.get) if insts else '')
        data, src = Client(out=stage(a.uid)).api('authors/' + primary.rsplit('/', 1)[-1])
        orcid = (data.get('orcid') or '').rsplit('/', 1)[-1]
        print(f"   author={data.get('display_name')} orcid={orcid or '-'} works={data.get('works_count')} "
              f"university_in_history={inst in institution_ids(data)} name_evidence={author_name_evidence(data, a.tokens)}")
        name_source = {}
        if a.name_source:
            from publications import normalize_name
            src = L.sources(stage(a.uid))[a.name_source]
            assert normalize_name(' '.join(a.tokens)) in normalize_name(L.text(src)), 'name source does not print the full name'
            name_source = dict(source_url=src['requested_url'], sha256=src['sha256'], source_id=src['source_id'], full_name=' '.join(a.tokens))
        review = dict(lab_id=lab['lab_id'], pi_name=a.pi_name or ' '.join(a.tokens), profile_name_tokens=a.tokens, orcid=orcid,
                      **({'name_token_source': name_source} if name_source else {}),
                      openalex_author_id=primary, openalex_institution_id=inst,
                      identity_evidence_format=FORMAT, identity_evidence_url=meta['requested_url'],
                      identity_profile_sha256=meta['sha256'], bibliography_selector=a.selector,
                      anchor_dois=sorted(d for d, w in found.items() if isinstance(w, dict)),
                      bibliography_pages=[dict(url=pg['requested_url'], sha256=pg['sha256'], selector=sel) for pg, sel in pages[1:]],
                      pubmed_links=a.pubmed, text_identifiers=a.text_ids,
                      anchor_thresholds=dict(min_works=ANCHOR_MIN_WORKS, min_share=ANCHOR_MIN_SHARE, competitor_max_share=COMPETITOR_MAX_SHARE),
                      review_status='accepted', reviewed_on=L.AS_OF, university_id=a.uid, notes=a.note)
        try:
            _, _, _, stats = anchor_author(review, Client(out=stage(a.uid), offline=True))
        except ValueError as e:
            print('ANCHOR REFUSED:', e); return
        print(f"ANCHOR OK: {stats['anchor_hits']}/{stats['anchor_works']}")
        if a.propose:
            props = load_proposals(a.uid)
            props['identities'] = [r for r in props['identities'] if (r['lab_id'], r['openalex_author_id']) != (lab['lab_id'], primary)] + [review]
            for page, selector in pages:
                bib = dict(lab_id=lab['lab_id'], source_url=page['requested_url'], selector=selector,
                           review_status='accepted_official_lab_bibliography', reviewed_on=L.AS_OF, source_id=page['source_id'],
                           source_sha256=page['sha256'], pubmed_links=a.pubmed, text_identifiers=a.text_ids,
                           notes=a.note or 'Official lab publication list linked from the lab homepage; selector bounds the lab list.')
                props['bibliographies'] = [r for r in props['bibliographies'] if (r['lab_id'], r['source_url']) != (bib['lab_id'], bib['source_url'])] + [bib]
            save_proposals(a.uid, props)
            print('proposed identity + bibliography for', lab['lab_name'])
    elif a.cmd == 'bib':
        from bibliography_anchor import listed_dois
        from publications import classify_link, identity_author_ids
        labs, *_ = university_labs(a.uid)
        lab = next(r for r in labs if r['lab_id'] == a.lab_id)
        meta = L.sources(stage(a.uid))[a.source_id]
        install(a.uid, meta)
        dois = listed_dois(L.decoded(meta), a.selector, a.pubmed, a.text_ids)
        found = resolve(a.uid, dois)
        works = {w['id']: w for w in found.values() if isinstance(w, dict)}
        idents = [r for r in read_csv(ROOT / 'data/publications/pi_identities.csv') if r['lab_id'] == a.lab_id]
        tied = set()
        for w in works.values():
            if not '2016-01-01' <= (w.get('publication_date') or '') <= '2026-10-12':
                continue
            for ident in idents:
                link = classify_link(ident, w, w['id'], {'review_status': 'accepted', 'source_url': meta['requested_url']})
                if link and link['broader_reviewed']:
                    tied.add(w['id'])
        print(f"{lab['lab_name']}: listed={len(dois)} resolved={len(works)} verified_identities={len(idents)} tied_in_window={len(tied)}")
        if a.propose:
            props = load_proposals(a.uid)
            bib = dict(lab_id=lab['lab_id'], source_url=meta['requested_url'], selector=a.selector,
                       review_status='accepted_official_lab_bibliography', reviewed_on=L.AS_OF, source_id=meta['source_id'],
                       source_sha256=meta['sha256'], pubmed_links=a.pubmed, text_identifiers=a.text_ids,
                       notes=a.note or 'Official lab publication list linked from the lab homepage; selector bounds the lab list.')
            props['bibliographies'] = [r for r in props['bibliographies'] if (r['lab_id'], r['source_url']) != (bib['lab_id'], bib['source_url'])] + [bib]
            save_proposals(a.uid, props)
    elif a.cmd == 'gap':
        props = load_proposals(a.uid)
        props['gaps'] = [r for r in props['gaps'] if r['lab_id'] != a.lab_id] + [dict(lab_id=a.lab_id, reason=a.reason)]
        save_proposals(a.uid, props)
    elif a.cmd == 'list':
        for m in L.sources(stage(a.uid)).values():
            print(m['source_id'], m['http_status'], m.get('archive_capture', ''), m['final_url'])
        for r in L.read_jsonl(stage(a.uid) / 'attempts.jsonl'):
            if r['status'] != 'captured':
                print('FAILED', r['status'], r.get('http_status', ''), r['requested_url'], r.get('error', ''))


if __name__ == '__main__':
    main()
