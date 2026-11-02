"""The reader export (2026-11-01, owner decision): which confirmed full-text copies the site may host, and a source link for the rest.

Owner rule: host a copy ONLY when its license allows redistribution; every other confirmed copy gets a "Read at source" link. A
paper with a confirmed copy is READABLE either way (the site shows it as readable, green); only a paper with no confirmed copy
stays not readable.

Inputs, per school (read-only):
  lab papers   the working package hierarchy/<school>/lab_papers.jsonl.gz (a release carries the same file);
  the store    stores/<school>/catalog.sqlite: works, assets, candidates. A paper's confirmed copy is found by the coverage counter's
               own rule (tools/lab_paper_copies.resolve): status downloaded or fulltext_xml, identity not pending
               (provider_link_only_review_pending), never quarantined (status quarantined_*; a path under quarantine/ is refused too).
License, per copy, normalised (normalise_license):
  1. assets.license of the stored file; else candidates.license of the URL it came from;
  2. for an arXiv copy with none: the licence OpenAlex records for that arXiv deposit in the local OpenAlex works the code already
     holds (fulltext-push/raw/openalex_works.jsonl, ledger_openalex.jsonl, stanford-oa-works.sqlite, the CMU stage's
     openalex_works.json.gz). OpenAlex copies the licence from arXiv's metadata; an arXiv deposit with no licence there is arXiv's
     non-exclusive licence (arxiv.org/licenses/nonexclusive-distrib), basis arxiv_default. No network. NOTE: the local arXiv OAI
     index (raw/arxiv_oai) keeps no licence field, so it cannot answer this; an arXiv id absent from every local OpenAlex file has
     basis arxiv_unknown and is LINK;
  HOST  cc-by, cc-by-sa, cc-by-nc, cc-by-nc-sa, cc-by-nd, cc-by-nc-nd, cc0, public-domain;  LINK  everything else (none, other-oa, tdm,
  arxiv-nonexclusive, ...).
Source link, per LINK copy (source_url, source_kind): the arXiv abs page, else a repository landing page, else the open publisher page
or the DOI, from the candidate or asset URLs (a landing page before a bare PDF URL).
Outputs (hierarchy/reader/{<school>.jsonl.gz, hosted-files.tsv, currently-hosted-not-permitted.tsv, SUMMARY.json, README.md};
make_release copies the directory to reader/ in the release): docs in the README text below and schemas/reader.schema.json.

usage: reader_export.py [school ...] [--site-local-papers FILE] [--out DIR]        (default: every released school; Slurm, it reads the catalogs)
"""
import argparse, collections, gzip, json, re, sqlite3, sys, time, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402  (every path in one place)
import lab_paper_copies as LPC  # noqa: E402  (the coverage counter's rule)
import reader_links as RL  # noqa: E402  (candidate URLs confirmed as this paper become source links)

HOST = frozenset(['cc-by', 'cc-by-sa', 'cc-by-nc', 'cc-by-nc-sa', 'cc-by-nd', 'cc-by-nc-nd', 'cc0', 'public-domain'])
LOCAL, PENDING = LPC.LOCAL, LPC.PENDING
ARXIV_NONEXCLUSIVE = 'arxiv-nonexclusive'
REPOSITORY_HOSTS = re.compile(
    r'(dspace|/handle/\d|escholarship\.org|infoscience\.epfl\.ch|dash\.harvard|hal\.science|hal\.archives|zenodo\.org|osti\.gov|ncbi\.nlm\.nih\.gov/pmc|'
    r'europepmc\.org|kilthub|eprints|repository|repositories|ir\.library|dataspace\.princeton|digitalcommons|scholarworks|deepblue|'
    r'oar\.princeton|figshare\.com|ora\.ox|research-collection|purl\.|handle\.net|doaj\.org|core\.ac\.uk|semantic.?scholar|biorxiv|medrxiv|'
    r'ssrn\.com|openreview\.net|aclanthology\.org|proceedings\.mlr\.press|papers\.nips\.cc|openaccess\.thecvf\.com)', re.I)
ARXIV_ID = re.compile(r'(?:arxiv\.org/(?:abs|pdf)/|arxiv[:.]|arxiv-dataset/arxiv/arxiv/pdf/\d{4}/)((?:\d{4}\.\d{4,5})|(?:[a-z\-]+(?:\.[A-Z]{2})?/\d{7}))(?:v\d+)?', re.I)


def normalise_license(raw):
    """'CC BY 4.0', 'cc_by', 'https://creativecommons.org/licenses/by-nc/4.0/' -> 'cc-by', 'cc-by-nc'; CC0 -> 'cc0'; public domain ->
    'public-domain'; arXiv's non-exclusive licence -> 'arxiv-nonexclusive'; anything else -> its lower-case slug; empty -> None."""
    if raw is None:
        return None
    t = str(raw).strip().lower()
    if not t or t in ('none', 'null', 'unknown', 'n/a', 'na'):
        return None
    if 'arxiv.org/licenses' in t or 'nonexclusive-distrib' in t or t in ('arxiv', 'arxiv-nonexclusive'):
        return ARXIV_NONEXCLUSIVE
    m = re.search(r'creativecommons\.org/(?:licenses|publicdomain)/([a-z\-]+)', t)
    if m:
        t = 'cc-' + m.group(1) if m.group(1) not in ('zero', 'mark') else ('cc0' if m.group(1) == 'zero' else 'public-domain')
    elif 'creativecommons.org/publicdomain/zero' in t:
        t = 'cc0'
    t = re.sub(r'[\s_]+', '-', t.replace('+', ''))
    t = re.sub(r'^cc-?by', 'cc-by', t) if t.startswith('ccby') else t
    t = re.sub(r'[-v]*\d(?:\.\d)?$', '', t) if re.match(r'^cc', t) and not t.startswith('cc0') else t   # drop the version (cc-by-4.0)
    m = re.match(r'^cc-?by(?:-?(nc))?(?:-?(nd|sa))?(?:[-v]*\d[\d.]*)?$', t)
    if m:
        t = 'cc-by' + ('-nc' if m.group(1) else '') + ('-' + m.group(2) if m.group(2) else '')
    t = re.sub(r'^cc-?0.*$', 'cc0', t)
    t = re.sub(r'^cc-zero.*$', 'cc0', t)
    if t in ('public-domain', 'publicdomain', 'pd', 'pdm', 'public-domain-mark'):
        t = 'public-domain'
    return t.strip('-') or None


def arxiv_id_of(*texts):
    for t in texts:
        m = ARXIV_ID.search(str(t or ''))
        if m:
            return m.group(1)
        m = re.search(r'10\.48550/arxiv\.([0-9]{4}\.[0-9]{4,5})', str(t or ''), re.I)
        if m:
            return m.group(1)
    return None


class ArxivLicenses:
    """arXiv id -> licence, from OpenAlex work records already on disk (locations[].license of the arXiv deposit). `known(id)` says the
    id appears in some record at all, so a missing licence can be read as arXiv's non-exclusive default (basis arxiv_default)."""

    def __init__(self):
        self.lic, self.seen = {}, set()
        self.locs = {}   # OpenAlex work (W id) -> normalised URLs of its locations (reader_links basis openalex_location)

    def add_body(self, b):
        if isinstance(b, dict) and b.get('locations'):
            w = RL.oa_short(b.get('id'))
            if w:
                u = self.locs.setdefault(w, set())
                for loc in b['locations']:
                    for x in (loc.get('landing_page_url'), loc.get('pdf_url'), loc.get('doi')) + ((str(loc.get('id'))[4:] if str(loc.get('id')).startswith('doi:') else None,)):
                        n = RL.norm_url(x)
                        if n:
                            u.add(n)
                    a = arxiv_id_of(loc.get('id'))
                    if a:
                        u.add('arxiv:' + a.lower())
        for loc in (b.get('locations') or []) if isinstance(b, dict) else []:
            aid = arxiv_id_of(loc.get('id'), loc.get('landing_page_url'), loc.get('pdf_url'))
            if not aid:
                continue
            self.seen.add(aid)
            lic = normalise_license(loc.get('license') or loc.get('license_id'))
            if lic and not self.lic.get(aid):
                self.lic[aid] = lic

    @classmethod
    def from_files(cls, paths):
        self = cls()
        for p in paths:
            p = Path(p)
            if not p.exists():
                continue
            if p.suffix == '.sqlite':
                db = sqlite3.connect(f'file:{p}?mode=ro', uri=True, timeout=60)
                for (body,) in db.execute('select body from works'):
                    if isinstance(body, bytes):
                        body = zlib.decompress(body) if body[:1] != b'{' else body
                    try:
                        self.add_body(json.loads(body))
                    except ValueError:
                        pass
                continue
            op = gzip.open if p.suffix == '.gz' else open
            with op(p, 'rt') as f:
                if p.name.endswith('.json.gz') or p.suffix == '.json':
                    d = json.load(f)
                    for b in (d.values() if isinstance(d, dict) else d):
                        self.add_body(b.get('body', b) if isinstance(b, dict) else b)
                else:
                    for line in f:
                        d = json.loads(line)
                        self.add_body(d.get('body', d))
        return self

    def get(self, aid):
        """(licence or None, basis): arxiv_openalex | arxiv_default | arxiv_unknown."""
        if aid in self.lic:
            return self.lic[aid], 'arxiv_openalex'
        if aid in self.seen:
            return ARXIV_NONEXCLUSIVE, 'arxiv_default'
        return None, 'arxiv_unknown'


def local_openalex_files():
    return [P.FT_RAW / 'openalex_works.jsonl', P.FT_RAW / 'ledger_openalex.jsonl', P.FT_RAW / 'stanford-oa-works.sqlite',
            P.archive_sweep('claude-cmu-20261017') / 'raw' / 'openalex_works.json.gz'] + [P.data('pi-works.sqlite', s) for s in P.SCHOOL_IDS]


def url_kind(url):
    u = str(url or '')
    if not re.match(r'https?://', u):
        return None
    if re.search(r'arxiv\.org/(abs|pdf)/|arxiv-dataset/arxiv', u, re.I):
        return 'arxiv'
    if re.search(r'^https?://(dx\.)?doi\.org/', u, re.I):
        return 'doi'
    if REPOSITORY_HOSTS.search(u):
        return 'repository'
    return 'publisher'


def pick_source(doi, arxiv, urls):
    """The best open URL for a LINK copy: the arXiv abs page, else a repository landing page, else the open publisher page, else the
    DOI. `urls` are (url, is_landing) pairs from the candidates, the asset and the download; a landing page beats a bare file URL
    within a kind, and the order given breaks ties. Returns (url, kind) or (None, None)."""
    if arxiv:
        return f'https://arxiv.org/abs/{arxiv}', 'arxiv'
    best = {}
    for i, (u, landing) in enumerate(urls):
        k = url_kind(u)
        if k in ('repository', 'publisher') and (k not in best or (landing and not best[k][1])):
            best.setdefault(k, (u, landing, i))
            if landing and not best[k][1]:
                best[k] = (u, landing, i)
    for k in ('repository', 'publisher'):
        if k in best:
            return best[k][0], k
    if doi:
        return f'https://doi.org/{re.sub(r"^https?://(?:dx[.])?doi[.]org/", "", str(doi), flags=re.I)}', 'doi'
    return None, None


def decide(raw_license, arxiv, arxiv_lic):
    """(decision, license, basis-of-the-licence). raw_license is (value, basis) of the catalog's own licence data or None."""
    lic, basis = None, 'none'
    if raw_license and normalise_license(raw_license[0]):
        lic, basis = normalise_license(raw_license[0]), raw_license[1]
    elif arxiv and arxiv_lic is not None:
        lic, basis = arxiv_lic.get(arxiv)
    return ('host' if lic in HOST else 'link'), lic, basis


class LinkTools:
    """Turns the catalog candidates of a paper with no stored copy into a confirmed source link (reader_links.confirm)."""

    def __init__(self, arxiv_lic, verdict_file=None, s2_cache=None, oa_cache=None, arx_index=None):
        sys.path.append(str(P.FULLTEXT_PUSH))
        import identity_rule as IR
        self.IR, self.locs = IR, arxiv_lic.locs
        self.s2 = s2_cache or P.archive_sweep('claude-cmu-20261017') / 'raw' / 's2_key.jsonl'
        self.oa = oa_cache or P.FT_RAW / 'ledger_openalex.jsonl'
        self.arx_index = arx_index or RL.ArxivIndex()
        self.verdicts = RL.load_verdicts(verdict_file) if verdict_file else {}

    def candidate_link(self, school, key, r, cid, cands, bad, requests):
        """The link record for the paper, or None (its unconfirmed candidates go to `requests`)."""
        eds = [r] + list(r.get('editions') or [])
        paper = dict(key=key, doi=[d for d in dict.fromkeys(LPC.ndoi(e.get('doi')) for e in eds) if d], oa=[w for w in dict.fromkeys(RL.oa_short(e.get('oa')) for e in eds) if w],
                     title=r.get('title'), first_author=RL.fam((r.get('byline') or [''])[0]))
        urls = RL.clean_candidates(cands, bad)
        if not urls:
            return None
        oa_full = r.get('oa')
        basis, hit = RL.confirm(paper, urls, self.locs, lambda doi: self.IR.mapped_arxiv(doi, self.s2, self.oa, oa_full), self.arx_index, self.verdicts)
        if not basis:
            requests.extend(RL.request_rows(school, key, paper, urls))
            return None
        arxiv = next((a for a in (arxiv_id_of(u) for u in hit) if a), None)
        src, kind = pick_source(r.get('doi'), arxiv, [(u, True) for u in hit])
        if not src:
            return None
        return dict(school=school, key=key, atlas_work_id=r.get('atlasWorkId'), oa=r.get('oa'), doi=r.get('doi'), arxiv=arxiv or r.get('arxiv'), title=r.get('title'),
                    year=r.get('year'), readable=True, decision='link', license=None, license_basis='none', source_url=src, source_kind=kind, sha256=None,
                    bytes=None, format=None, path=None, version=None, identity_check=None, catalog_work=cid, link_basis=basis, stored_copy=False,
                    lookup_keys=[k for k in (key, r.get('atlasWorkId'), 'doi:' + LPC.ndoi(r['doi']) if r.get('doi') else None,
                                             'arxiv:' + (arxiv or r['arxiv']) if (arxiv or r.get('arxiv')) else None) if k])


def batches(seq, n=400):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def copy_for(wid, w, assets, cands, arxiv_lic):
    """One confirmed copy of catalog work `wid` -> dict, or None when it is not a hostable/linkable confirmed copy.
    w = works row dict, assets = [asset dict], cands = [candidate dict]."""
    if not w or w['status'] not in LOCAL or w['identity_check'] == PENDING:
        return None
    fmt = 'xml' if w['status'] == 'fulltext_xml' else 'pdf'
    sha = w['sha256']
    chosen = next((a for a in assets if a['sha256'] == sha and a['kind'] in ('pdf', 'xml') and a['identity_check'] != PENDING), None)
    if chosen is None and not sha:   # a full-text XML work keeps its file on the asset row only
        chosen = next((a for a in assets if a['kind'] == fmt and a['sha256'] and a['identity_check'] != PENDING), None)
        sha = (chosen or {}).get('sha256')
    path = (chosen or {}).get('path') or w['file_path']
    if not sha or not path or 'quarantine' in str(path):
        return None
    dl = w['download_url'] or (chosen or {}).get('url')
    raw = None
    if chosen and normalise_license(chosen['license']):
        raw = (chosen['license'], 'asset')
    else:
        cand = next((c for c in cands if c['url'] in (dl, (chosen or {}).get('url')) and normalise_license(c['license'])), None)
        if cand:
            raw = (cand['license'], 'candidate')
        else:
            other = next((a for a in assets if a['sha256'] == sha and normalise_license(a['license'])), None)
            if other:
                raw = (other['license'], 'asset')
    urls = [(c['landing_url'], True) for c in cands if c['landing_url']] + [(c['url'], False) for c in cands if c['url']]
    urls += [(u, False) for u in (dl, (chosen or {}).get('url')) if u]
    arxiv = arxiv_id_of(dl, (chosen or {}).get('url'), *[c['url'] for c in cands], *[c['landing_url'] for c in cands], w['doi'])
    decision, lic, basis = decide(raw, arxiv, arxiv_lic)
    src, kind = pick_source(w['doi'], arxiv, urls)
    return dict(catalog_work=wid, format=fmt, decision=decision, license=lic, license_basis=basis, source_url=src, source_kind=kind,
                sha256=sha, bytes=w['byte_count'] or (chosen or {}).get('bytes'), path=path, version=(chosen or {}).get('version'), identity_check=w['identity_check'],
                download_url=dl, arxiv=arxiv)


def load_catalog(school, hosted_shas=()):
    """Read the store's works in short chunks (lab_paper_copies.chunks), as the coverage counter does. -> (db, status, by_doi,
    local_titles, title_local, sha_refs)."""
    db = sqlite3.connect(f'file:{P.STORES / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    db.execute('pragma busy_timeout = 120000')
    status, by_doi, local_titles, title_local, sha_refs = {}, {}, set(), {}, collections.defaultdict(list)
    for wid, doi, st, title, ic, sha in LPC.chunks(db, 'id, doi, status, title, identity_check, sha256'):
        if st == 'downloaded' and ic == PENDING:
            st = 'identity_unconfirmed'
        if status.get(wid) not in LOCAL:
            status[wid] = st
        if doi and (st in LOCAL or LPC.ndoi(doi) not in by_doi):
            by_doi[LPC.ndoi(doi)] = wid
        if st in LOCAL and title:
            t = re.sub(r'[^a-z0-9]', '', title.lower())
            local_titles.add(t)
            title_local.setdefault(t, wid)
        if sha and sha in hosted_shas:
            sha_refs[sha].append(wid)
    return db, status, by_doi, local_titles, title_local, sha_refs


def fetch(db, ids):
    """works / assets / candidates rows of the given catalog work ids, as {id: dict}, {id: [dict]}, {id: [dict]}."""
    works, assets, cands = {}, collections.defaultdict(list), collections.defaultdict(list)
    for part in batches(sorted(set(ids))):
        q = ','.join('?' * len(part))
        for r in db.execute(f'select id, doi, title, year, status, file_path, sha256, byte_count, download_url, identity_check from works where id in ({q})', part):
            works[r[0]] = dict(zip(('id', 'doi', 'title', 'year', 'status', 'file_path', 'sha256', 'byte_count', 'download_url', 'identity_check'), r))
        for r in db.execute(f'select work_id, kind, url, path, sha256, bytes, version, license, identity_check from assets where work_id in ({q})', part):
            assets[r[0]].append(dict(zip(('work_id', 'kind', 'url', 'path', 'sha256', 'bytes', 'version', 'license', 'identity_check'), r)))
        for r in db.execute(f'select work_id, url, landing_url, license, version from candidates where work_id in ({q})', part):
            cands[r[0]].append(dict(zip(('work_id', 'url', 'landing_url', 'license', 'version'), r)))
    return works, assets, cands


def school_rows(school, lab_rows, arxiv_lic, hosted_shas=frozenset(), db_parts=None, links=None):
    """-> (records, stats, hosted_check, requests) for one school. hosted_check = {sha: [copy dict]} for the shas the site hosts today.
    `links` (a reader_links.LinkTools) turns the catalog candidates of papers with no stored copy into confirmed source links."""
    db, status, by_doi, local_titles, title_local, sha_refs = db_parts or load_catalog(school, hosted_shas)
    matches = {}
    out, counts = LPC.resolve(school, lab_rows, status, by_doi, local_titles, matches=matches)
    first = {}
    for r in lab_rows:
        first.setdefault(r['work'] or r['oa'], r)
    need = set()
    cid_of = {}
    for key, (cid, st) in matches.items():
        if st in LOCAL:
            c = cid if status.get(cid) in LOCAL else title_local.get(re.sub(r'[^a-z0-9]', '', (first[key].get('title') or '').lower()))
            if c:
                cid_of[key] = c
                need.add(c)
    for shas in sha_refs.values():
        need.update(shas)
    works, assets, cands = fetch(db, need)
    copies = {c: copy_for(c, works.get(c), assets.get(c, []), cands.get(c, []), arxiv_lic) for c in need}
    open_cands = set()   # papers with no usable stored copy whose catalog work has an open-source candidate
    rest = {cid for key, (cid, st) in matches.items() if cid and not copies.get(cid_of.get(key))}
    cand_rows, bad_urls = collections.defaultdict(list), collections.defaultdict(set)
    for part in batches(rest):
        q = ','.join('?' * len(part))
        for r in db.execute(f'select work_id, url, landing_url from candidates where work_id in ({q})', part):
            cand_rows[r[0]].append(dict(url=r[1], landing_url=r[2]))
        for r in db.execute(f"select work_id, url from attempts where work_id in ({q}) and (status = 'identity_mismatch' or detail like 'identity unconfirmed%')", part):
            bad_urls[r[0]].add(r[1])
        for r in db.execute(f"select work_id, url from assets where work_id in ({q}) and kind = 'identity_mismatch_pdf'", part):
            bad_urls[r[0]].add(r[1])
    open_cands = set(cand_rows)
    requests = []
    recs, stats = [], collections.Counter()
    for key, r in first.items():
        stats['lab_papers'] += 1
        cp = copies.get(cid_of.get(key))
        if cp and cp['decision'] == 'link' and not cp['source_url']:   # a link with nothing to open is not readable
            stats['link_without_source_url'] += 1
            cp = None
        if not cp:
            cid = matches.get(key, (None,))[0]
            if links is not None and cid in open_cands:
                rec = links.candidate_link(school, key, r, cid, cand_rows[cid], bad_urls[cid], requests)
                if rec:
                    stats['link'] += 1
                    stats['link_basis:' + rec['link_basis']] += 1
                    stats['newly_readable_from_candidates'] += 1
                    stats['license:link:none'] += 1
                    stats['basis:none'] += 1
                    stats['source_kind:' + str(rec['source_kind'])] += 1
                    recs.append(rec)
                    continue
            stats['not_readable'] += 1
            if cid in open_cands:
                stats['not_readable_with_open_candidate'] += 1
            continue
        stats['link_basis:confirmed_copy'] += cp['decision'] == 'link' and 1 or 0
        stats[cp['decision']] += 1
        stats['license:%s:%s' % (cp['decision'], cp['license'] or 'none')] += 1
        stats['basis:' + cp['license_basis']] += 1
        if cp['decision'] == 'link':
            stats['source_kind:' + str(cp['source_kind'])] += 1
        recs.append(dict(
            school=school, key=key, atlas_work_id=r.get('atlasWorkId'), oa=r.get('oa'), doi=r.get('doi'), arxiv=cp['arxiv'] or r.get('arxiv'),
            title=r.get('title'), year=r.get('year'), readable=True, decision=cp['decision'], license=cp['license'],
            license_basis=cp['license_basis'], source_url=cp['source_url'], source_kind=cp['source_kind'], sha256=cp['sha256'],
            bytes=cp['bytes'], format=cp['format'], path=cp['path'] if cp['decision'] == 'host' else None, version=cp['version'],
            identity_check=cp['identity_check'], catalog_work=cp['catalog_work'], link_basis=('confirmed_copy' if cp['decision'] == 'link' else None), stored_copy=True,
            lookup_keys=[k for k in (key, r.get('atlasWorkId'), 'doi:' + LPC.ndoi(r['doi']) if r.get('doi') else None,
                                     'arxiv:' + (cp['arxiv'] or r.get('arxiv')) if (cp['arxiv'] or r.get('arxiv')) else None) if k]))
    chk = collections.defaultdict(list)
    for sha, wids in sha_refs.items():
        for wid in wids:
            w = works.get(wid)
            cp = copies.get(wid)
            chk[sha].append(cp or dict(catalog_work=wid, decision='not_confirmed', license=None, license_basis='none', status=(w or {}).get('status'),
                                       identity_check=(w or {}).get('identity_check'), bytes=(w or {}).get('byte_count')))
    return recs, stats, chk, requests


def hosted_not_permitted(hosted_files, checks):
    """Rows (sha256, bytes, path, reason, license, basis, schools, works) for the hosted files the rule would NOT host. Strict: a file
    several works reference is permitted only when every confirmed reference is HOST."""
    rows = []
    for sha, f in sorted(hosted_files.items()):
        refs = [(s, c) for s, lst in checks.items() for c in lst.get(sha, [])]
        if not refs:
            rows.append((sha, f.get('bytes'), f.get('path'), 'not_in_stores', '', '', '', ''))
            continue
        confirmed = [(s, c) for s, c in refs if c['decision'] in ('host', 'link')]
        if not confirmed:
            rows.append((sha, f.get('bytes'), f.get('path'), 'no_confirmed_copy', '', '', ','.join(sorted({s for s, _ in refs})), ','.join(c['catalog_work'] for _, c in refs[:3])))
        elif any(c['decision'] != 'host' for _, c in confirmed):
            bad = [(s, c) for s, c in confirmed if c['decision'] != 'host']
            lic = ','.join(sorted({str(c['license']) for _, c in bad}))
            rows.append((sha, f.get('bytes'), f.get('path'), 'license', lic, ','.join(sorted({c['license_basis'] for _, c in bad})),
                         ','.join(sorted({s for s, _ in bad})), ','.join(c['catalog_work'] for _, c in bad[:3])))
    return rows


README = """# Reader export (generated by tools/reader_export.py; do not edit)

Rule (owner, 2026-11-01): the site HOSTS a copy only when its licence allows redistribution; every other paper that has a confirmed copy,
or a candidate source URL confirmed to be the paper, is shown with a "Read at source" link. Hosted and linked papers are BOTH READABLE (green);
only a paper with neither stays not readable. A candidate-only link is never hosted: we hold no copy.

## Files
- `<school>.jsonl.gz`: one row per lab paper that is readable (schema: schemas/reader.schema.json). THE READABLE FIELD IS `readable` (always
  true in these files; a paper without a row is not readable). Other fields: `key` (paper key), `atlas_work_id`, `oa`, `doi`, `arxiv`, `title`,
  `year`, `decision` (`host` | `link`), `stored_copy` (true when we hold a confirmed copy), `link_basis` (null for host; `confirmed_copy` =
  linked although we hold a confirmed copy whose licence does not allow hosting; for a candidate URL with no stored copy: `arxiv_id_doi` |
  `openalex_location` | `arxiv_metadata` | `landing_page_metadata`, see below), `license` and `license_basis` (asset | candidate | arxiv_openalex |
  arxiv_default | arxiv_unknown | none), `source_url` + `source_kind` (arxiv | repository | publisher | doi: the open page to read at the source),
  `sha256`, `bytes`, `format` (pdf | xml), `path` (store-relative `objects/<sha256>.pdf`; host rows only) - sha256, bytes and format are null
  without a stored copy -, `lookup_keys` (the keys the site looks a work up by: the paper key, the atlas id, `doi:<doi>`, `arxiv:<id>`).
- `hosted-files.tsv`: sha256, bytes, school, path, for the uploader. One row per file to HOST (deduplicated by sha256).
- `currently-hosted-not-permitted.tsv`: files in site/atlas/data/local-papers.json `files` today that this rule would NOT host (unpublish them).
- `link-check-requests.tsv`: candidate URLs of papers not yet confirmed, grouped by host, for the polite landing-page check (below).
- `link-verdicts.jsonl` (input, written by the downloads agent): one JSON object per checked URL: `key`, `url`, `verdict` (`match` | `mismatch` |
  `unreachable`), `title_seen`, `authors_seen`, `fetched_at`, `robots_ok`. A `match` makes the paper a link with basis `landing_page_metadata` at the next run.
- `SUMMARY.json`: counts per school: confirmed copies, host, link, link_by_basis, readable (= host + link), not readable, by licence, by licence basis.

## How a candidate URL becomes a link (no network)
Strongest first: `arxiv_id_doi` (the candidate is an arXiv URL and the Semantic Scholar / OpenAlex DOI to arXiv mapping the identity rule uses ties it to the
paper's DOI, and the arXiv record's own title shares three quarters of the shorter title's words, and a Zenodo/Figshare/Dryad/OSF deposit DOI never counts), `openalex_location` (the URL, normalised, is a listed location of
the same OpenAlex work), `arxiv_metadata` (the arXiv record's title matches the paper's, both ways, at 90% of at least four significant words, and the first author's
family name matches), `landing_page_metadata` (a verdict file entry). A candidate the catalog found to be another document never counts.

## How the site shows readable (Codex)
The site's readable state is the presence of an entry for the work in `data/local-papers.json` -> `works` (looked up by `PaperReader.find`
in atlas/assets/paper-reader.js under the work's id, library id, canonical id, aliases, `doi:<doi>`, `arxiv:<id>`). The reader button
`Read here · stored PDF` appears when there is one, otherwise the text `No full-text copy stored here yet`.
- HOST row: write the existing entry as today: `works[<lookup key>] = {path: 'papers/<sha256>.pdf', sha256, bytes, sourceUrl: <store download url>,
  version, license, identityCheck: identity_check}` (and `files[<sha256>]`, `reader-objects.json` `files[<sha256>] = bytes`). Upload the file
  listed in hosted-files.tsv.
- LINK row (any `link_basis`): write an entry WITHOUT `path`: `works[<lookup key>] = {sourceUrl: source_url, link: true, sourceKind: source_kind,
  linkBasis: link_basis, license, version}`; no file is uploaded and nothing goes into `files` or reader-objects. In `PaperReader.append`, an entry with
  `link: true` should render the same green `aside-button read-local-paper` with the label `Read at source ↗` that opens `sourceUrl` in a new tab
  (`rel="noopener"`), instead of opening the dialog. Everything that counts papers as readable should count entries with a `path` or `link`.
- Rows with `decision: host` and `license` set may show "License: <license>" as the existing reader does (`file.license`).
- Papers with no row here are not readable: leave them as they are.
Mapping to local-papers.json fields: sha256 -> sha256; bytes -> bytes; path -> `papers/<sha256>.pdf` (the site's own object names); catalog download url
-> sourceUrl (HOST); source_url -> sourceUrl (LINK); version -> version; license -> license; identity_check -> identityCheck.
"""


def write_outputs(school_recs, per_school_stats, hosted_not, outdir, built_at, lab_counts, extra=None, requests=None):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    seen, hosted = set(), []
    for school, recs in school_recs.items():
        with gzip.open(outdir / f'{school}.jsonl.gz', 'wt') as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n')
        for r in recs:
            if r['decision'] == 'host' and r['sha256'] not in seen:
                seen.add(r['sha256'])
                hosted.append((r['sha256'], r['bytes'], school, r['path']))
    (outdir / 'hosted-files.tsv').write_text('sha256\tbytes\tschool\tpath\n' + ''.join('\t'.join(str(x) for x in row) + '\n' for row in sorted(hosted)))
    reqs = sorted((r for rows in (requests or {}).values() for r in rows), key=lambda r: (r[0], r[1], r[2], r[6]))
    (outdir / 'link-check-requests.tsv').write_text('host\tschool\tkey\ttitle\tdoi\tfirst_author_family\turl\turl_kind\n' + ''.join(
        '\t'.join(str(x).replace('\t', ' ').replace('\n', ' ') for x in row) + '\n' for row in reqs))
    (outdir / 'currently-hosted-not-permitted.tsv').write_text(
        'sha256\tbytes\tpath\treason\tlicense\tbasis\tschools\tworks\n' + ''.join('\t'.join('' if x is None else str(x) for x in row) + '\n' for row in hosted_not))
    summ = dict(built_at=built_at, rule='host only licences %s; every other confirmed copy is a source link; readable = host + link' % ', '.join(sorted(HOST)),
                schools={}, totals=collections.Counter())
    for school, st in per_school_stats.items():
        d = dict(lab_papers=st['lab_papers'], confirmed_copies=st['host'] + st['link'] - st['newly_readable_from_candidates'], host=st['host'], link=st['link'],
                 readable=st['host'] + st['link'], not_readable=st['not_readable'],
                 not_readable_with_open_candidate=st['not_readable_with_open_candidate'],
                 link_without_source_url=st['link_without_source_url'],
                 link_by_basis={k[len('link_basis:'):]: v for k, v in sorted(st.items()) if k.startswith('link_basis:') and v},
                 newly_readable_from_candidates=st['newly_readable_from_candidates'],
                 link_check_requests=len({(r[1], r[2]) for r in (requests or {}).get(school, [])}),
                 by_license={k[len('license:'):]: v for k, v in sorted(st.items()) if k.startswith('license:')},
                 by_license_basis={k[len('basis:'):]: v for k, v in sorted(st.items()) if k.startswith('basis:')},
                 link_source_kinds={k[len('source_kind:'):]: v for k, v in sorted(st.items()) if k.startswith('source_kind:')})
        summ['schools'][school] = d
        for k in ('lab_papers', 'confirmed_copies', 'host', 'link', 'readable', 'not_readable'):
            summ['totals'][k] += d[k]
    summ['totals'] = dict(summ['totals'])
    summ['currently_hosted_not_permitted'] = len(hosted_not)
    summ['hosted_files'] = len(hosted)
    hosts = collections.Counter(r[0] for r in reqs)
    summ['link_check_request_urls'] = len(reqs)
    summ['link_check_request_hosts'] = dict(hosts.most_common(25))
    summ.update(extra or {})
    (outdir / 'SUMMARY.json').write_text(json.dumps(summ, indent=1, sort_keys=True))
    (outdir / 'README.md').write_text(README)
    return summ


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('schools', nargs='*')
    ap.add_argument('--site-local-papers', help="the site's data/local-papers.json (read only), for the currently-hosted check")
    ap.add_argument('--out', default=str(P.data('reader-SUMMARY.json').parent))
    a = ap.parse_args(argv)
    schools = a.schools or list(P.SCHOOL_IDS)
    hosted_files = {}
    if a.site_local_papers and Path(a.site_local_papers).exists():
        hosted_files = {sha: dict(bytes=f.get('bytes'), path=f.get('path')) for sha, f in json.load(open(a.site_local_papers))['files'].items()}
    t0 = time.time()
    arxiv_lic = ArxivLicenses.from_files(local_openalex_files())
    print(f'arXiv licences: {len(arxiv_lic.lic)} with a licence, {len(arxiv_lic.seen)} ids seen ({time.time() - t0:.0f} s)', flush=True)
    recs, stats, checks, requests = {}, {}, {}, {}
    links = LinkTools(arxiv_lic, P.data('reader-link-verdicts.jsonl'))
    for s in schools:
        rows = [json.loads(l) for l in gzip.open(P.data('lab_papers.jsonl.gz', s), 'rt')]
        recs[s], stats[s], checks[s], requests[s] = school_rows(s, rows, arxiv_lic, frozenset(hosted_files), links=links)
        print(s, json.dumps({k: v for k, v in stats[s].items() if not k.startswith(('license:', 'basis:', 'source_kind:'))}), flush=True)
    hosted_not = hosted_not_permitted(hosted_files, checks) if hosted_files else []
    summ = write_outputs(recs, stats, hosted_not, a.out, time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), None, requests=requests,
                         extra=dict(arxiv_licences=dict(with_licence=len(arxiv_lic.lic), ids_seen=len(arxiv_lic.seen))))
    print(json.dumps(summ['totals']), 'not permitted:', len(hosted_not))
    return 0


if __name__ == '__main__':
    sys.exit(main())
