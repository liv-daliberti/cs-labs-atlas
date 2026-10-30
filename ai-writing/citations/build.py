"""Compact analysis tables from the OpenAlex (and S2) caches.

-> citations/data/citing.parquet   one row per paragraph-scored lab paper (2016-2026): key, school, year, labs (JSON
                                   list of 'school|PI'), ai_share, n_par, field/subfield of its OpenAlex primary_topic,
                                   n_refs_oa (OpenAlex referenced_works), n_refs_s2
   citations/data/edges_oa.parquet  (ci = citing row, wid = cited OpenAlex work as int)
   citations/data/works_oa.parquet  one row per cited OpenAlex work (see work_row)
   citations/data/edges_s2.parquet, works_s2.parquet  the same from Semantic Scholar (cited work = S2 paperId)

Published vs preprint-only (OpenAlex), rule `pubclass`:
  published     some location's source.type is journal, conference, book series or ebook platform; or no such
                location but the work is Crossref-registered (indexed_in has crossref) and its type is a publisher type
                (article, conference-paper, book, book-chapter, review, letter, editorial, erratum, paratext, ...)
  preprint      otherwise, when some location is a repository (arXiv, SSRN, bioRxiv, institutional) or type = preprint
  other         dissertations, datasets, reports, software, and works with no location at all
`pubclass_strict` drops the Crossref fallback (published needs a journal/conference/book location).
S2 rule (works_s2): published if S2's publicationVenue is a journal or conference that is not a preprint server
(arXiv, bioRxiv, medRxiv, SSRN, Research Square, ... which S2 types as 'journal'), or there is a venue string or a DOI;
preprint if the venue is a preprint server, or there is an arXiv id and no venue; other otherwise (mostly unmatched
reference stubs with no metadata).
`pubclass_s2`     = pubclass, except that a preprint whose arXiv id S2 places at a journal or conference venue counts
                    as published (the ML-conference failure mode: NeurIPS/ICLR/ICML papers that OpenAlex knows only as
                    their arXiv record).
"""
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.append(str(_Path(__file__).resolve().parents[2] / 'tools'))  # atlas_paths: every path
import atlas_paths as P  # noqa: E402
import gzip, json, re, sqlite3, zlib
from collections import Counter
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
AIW = HERE.parent
DATA = HERE / 'data'
CACHE = P.CACHE / 'citations'
PUB_SRC = {'journal', 'conference', 'book series', 'ebook platform'}
NOT_PUBLISHER_TYPES = {'preprint', 'posted-content', 'dissertation', 'dataset', 'report', 'standard', 'grant', 'peer-review',
                       'software', 'other', 'retraction', None}
PREPRINT_SERVERS = re.compile(r'^(arxiv(\.org)?|biorxiv|medrxiv|ssrn|social science research network|research square|preprints?(\.org)?|chemrxiv|techrxiv|'
                              r'psyarxiv|osf preprints|socarxiv|engrxiv|eartharxiv|authorea)\b', re.I)
ARX = re.compile(r'arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z\-\.]+/[0-9]{7})', re.I)


def log(**kw):
    print(json.dumps(kw, default=str), flush=True)


def wint(w):
    return int(w.rsplit('/', 1)[-1][1:])


def ro(path):
    return sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=600)


def arxiv_of(w):
    d = (w.get('doi') or '').lower()
    if '10.48550/arxiv.' in d:
        return d.split('10.48550/arxiv.', 1)[1]
    for L in w.get('locations') or []:
        m = ARX.search(L.get('landing_page_url') or '') or ARX.search(L.get('pdf_url') or '')
        if m:
            return m.group(1).lower()
    return None


def pubclass(w, strict=False):
    srcs = [((L.get('source') or {}).get('type')) for L in (w.get('locations') or [])]
    if (w.get('primary_location') or {}).get('source'):
        srcs.append(w['primary_location']['source'].get('type'))
    if any(s in PUB_SRC for s in srcs):
        return 'published'
    t = w.get('type')
    if not strict and 'crossref' in (w.get('indexed_in') or []) and t not in NOT_PUBLISHER_TYPES:
        return 'published'
    if t == 'preprint' or 'repository' in srcs:
        return 'preprint'
    return 'other'


def venue_of(w):
    """(source id, source type): the primary location's source, else the first journal/conference location's."""
    s = (w.get('primary_location') or {}).get('source') or {}
    if s.get('id') and s.get('type') != 'repository':
        return s['id'].rsplit('/', 1)[-1], s.get('type')
    for L in w.get('locations') or []:
        t = L.get('source') or {}
        if t.get('type') in PUB_SRC and t.get('id'):
            return t['id'].rsplit('/', 1)[-1], t['type']
    if s.get('id'):
        return s['id'].rsplit('/', 1)[-1], s.get('type')
    return None, None


def abstract_words(inv):
    return sum(len(v) for v in inv.values()) if inv else 0


def work_row(wid, w):
    pt = w.get('primary_topic') or {}
    vid, vt = venue_of(w)
    return dict(wid=wid, year=w.get('publication_year'), type=w.get('type'), cbc=w.get('cited_by_count') or 0,
                field=(pt.get('field') or {}).get('display_name'), subfield=(pt.get('subfield') or {}).get('display_name'),
                domain=(pt.get('domain') or {}).get('display_name'), venue=vid, venue_type=vt,
                pubclass=pubclass(w), pubclass_strict=pubclass(w, strict=True), arxiv=arxiv_of(w),
                abs_words=abstract_words(w.get('abstract_inverted_index')), has_title=bool(w.get('display_name')))


def citing_table():
    sc = {}
    for line in gzip.open(AIW / 'paragraph_scores.jsonl.gz', 'rt'):
        s = json.loads(line)
        if s.get('ai_share') is not None and s.get('n_paragraphs'):
            sc[s['key']] = s
    rows = []
    for line in gzip.open(AIW / 'papers.jsonl.gz', 'rt'):
        p = json.loads(line)
        try:
            y = int(p.get('year'))
        except (TypeError, ValueError):
            continue
        if p['key'] not in sc or not 2016 <= y <= 2026:
            continue
        labs = []
        for l in p['labs']:
            i = f"{p['school']}|{l['pi']}"
            if i not in labs:
                labs.append(i)
        s = sc[p['key']]
        rows.append(dict(key=p['key'], school=p['school'], year=y, date=p.get('date'), labs=json.dumps(labs), venue_name=p.get('venue'),
                         ptype=p.get('type'), ai_share=float(s['ai_share']), n_par=int(s['n_paragraphs'])))
    return pd.DataFrame(rows)


def build_oa(C):
    pos = {k: i for i, k in enumerate(C.key)}
    c = ro(CACHE / 'openalex.sqlite')
    ci, wi, nref = [], [], np.zeros(len(C), int)
    fld, sub, otype = [None] * len(C), [None] * len(C), [None] * len(C)
    for k, b in c.execute('select key, data from citing where status = 1'):
        if k not in pos:
            continue
        i = pos[k]; w = json.loads(zlib.decompress(b))
        refs = sorted({wint(x) for x in w.get('referenced_works') or []})
        nref[i] = len(refs); ci += [i] * len(refs); wi += refs
        pt = w.get('primary_topic') or {}
        fld[i] = (pt.get('field') or {}).get('display_name'); sub[i] = (pt.get('subfield') or {}).get('display_name'); otype[i] = w.get('type')
    C['n_refs_oa'], C['field'], C['subfield'], C['oa_type'] = nref, fld, sub, otype
    E = pd.DataFrame(dict(ci=np.array(ci, np.int32), wid=np.array(wi, np.int64)))
    W, merged = [], {}
    for wid, st, b in c.execute('select wid, status, data from works where status > 0'):
        w = json.loads(zlib.decompress(b))
        r = work_row(wint(wid), w)
        if st == 2 and wint(w['id']) != r['wid']:
            merged[r['wid']] = wint(w['id'])
        W.append(r)
    W = pd.DataFrame(W)
    n_fetched = c.execute('select count(*) from works').fetchone()[0]
    log(oa_edges=len(E), oa_works=len(W), fetched=n_fetched, merged=len(merged))
    return E, W


def build_s2(C):
    """S2 references: the cited work is the S2 paperId; metadata from the nested reference fields."""
    p = CACHE / 's2.sqlite'
    pos = {k: i for i, k in enumerate(C.key)}
    nref = np.full(len(C), -1)
    if not p.exists():
        C['n_refs_s2'] = nref
        return None, None, {}
    c = ro(p)
    ci, pid, W = [], [], {}
    arx_venue = {}
    for k, st, b in c.execute('select key, status, data from refs'):
        if k not in pos or not st:
            continue
        i = pos[k]; x = json.loads(zlib.decompress(b))
        refs = [r for r in (x.get('references') or []) if r.get('paperId')]
        seen = set()
        for r in refs:
            if r['paperId'] in seen:
                continue
            seen.add(r['paperId']); ci.append(i); pid.append(r['paperId'])
            if r['paperId'] not in W:
                pv = r.get('publicationVenue') or {}
                ex = r.get('externalIds') or {}
                ven = pv.get('id') or (r.get('venue') or None)
                vt = pv.get('type')
                arx = (ex.get('ArXiv') or '').lower() or None
                fos = [f['category'] for f in (r.get('s2FieldsOfStudy') or []) if f.get('source') == 's2-fos-model'] or \
                      [f['category'] for f in (r.get('s2FieldsOfStudy') or [])]
                isarx = bool(PREPRINT_SERVERS.search(pv.get('name') or r.get('venue') or ''))
                if vt in ('journal', 'conference') and not isarx:
                    cls = 'published'
                elif isarx or (arx and not ven) or 'Preprint' in str(r.get('publicationTypes')):
                    cls = 'preprint'
                elif ven:
                    cls = 'published'
                elif ex.get('DOI'):
                    cls = 'published'
                else:
                    cls = 'other'
                W[r['paperId']] = dict(pid=r['paperId'], year=r.get('year'), cbc=r.get('citationCount') or 0, venue=ven, venue_type=vt,
                                       field=fos[0] if fos else None, pubclass=cls, arxiv=arx, doi=(ex.get('DOI') or '').lower() or None)
                if arx and vt in ('journal', 'conference') and not isarx:
                    arx_venue[arx] = vt
        nref[i] = len(seen)
    C['n_refs_s2'] = nref
    W = pd.DataFrame(list(W.values()))
    code = {p_: j for j, p_ in enumerate(W.pid)}
    W['wid'] = np.arange(len(W))
    E = pd.DataFrame(dict(ci=np.array(ci, np.int32), wid=np.array([code[x] for x in pid], np.int64)))
    log(s2_edges=len(E), s2_works=len(W), s2_citing_with_refs=int((nref > 0).sum()), arxiv_with_venue=len(arx_venue))
    return E, W, arx_venue


def main():
    DATA.mkdir(exist_ok=True)
    C = citing_table()
    E, W = build_oa(C)
    E2, W2, arx_venue = build_s2(C)
    W['pubclass_s2'] = [('published' if (pc == 'preprint' and a and a in arx_venue) else pc) for pc, a in zip(W.pubclass, W.arxiv)]
    C.to_parquet(DATA / 'citing.parquet'); E.to_parquet(DATA / 'edges_oa.parquet'); W.to_parquet(DATA / 'works_oa.parquet')
    if E2 is not None:
        E2.to_parquet(DATA / 'edges_s2.parquet'); W2.to_parquet(DATA / 'works_s2.parquet')
    log(citing=len(C), pubclass=Counter(W.pubclass), strict=Counter(W.pubclass_strict), s2rule=Counter(W.pubclass_s2))


if __name__ == '__main__':
    main()
