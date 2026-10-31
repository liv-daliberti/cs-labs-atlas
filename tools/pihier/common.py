"""What every stage of the build shares: the charter tables, the date, the readers, the work keys and the evidence order."""
import collections, datetime, gzip, json, re, sqlite3, unicodedata, zlib
from pathlib import Path

import atlas_paths as P  # every path in one place
import school_config as _S  # the school charters schools/<key>.toml: protocol stage 0

HERE = P.WORK
SITE = P.SITE_DATA
DBLP = {k: _S.dblp_sweep(k) for k in _S.keys() if _S.dblp_sweep(k)}  # pre-protocol schools' cached DBLP lists
INST = {k: _S.inst(k) for k in _S.keys()}  # the primary lineage id ([ids].openalex[0])
AFF = {k: _S.aff(k) for k in _S.keys()}  # [affiliation].regex, tested by school_config.py --check
TODAY = datetime.date.today().isoformat()
WINDOW_START = 2016  # the atlas window is 2016-2026: the sweeps fetch works published 2016 and later
NOT_PAPERS = {'dataset', 'paratext', 'peer-review', 'erratum', 'supplementary-materials', 'other', 'grant', 'standard', 'retraction', 'reference-entry', 'libguides'}
SCHOOL_LOOSE = {k: _S.field(_S.get(k), 'affiliation.loose') or _S.aff(k) for k in _S.keys()}
# the school's own units whose names hold an institution word (2026-10-29: CMU's 'Neuroscience Institute' had made the
# HALPER authorship of Andreas Pfenning read as another institution): a raw affiliation string made only of such unit
# names and department words names no other institution
OWN_UNITS = {k: rx for k in _S.keys() for rx in [_S.own_units(k)] if rx}  # [affiliation].own_units (R-PAP-09)


def read(p):
    b = Path(p).read_bytes()
    return json.loads(gzip.decompress(b) if str(p).endswith('.gz') else b)


def norm_title(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)


def ndoi(s):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(s or '').strip(), flags=re.I).lower()


def source_year(s):
    m = re.search(r'/web/(\d{4})\d{4,10}', s.get('url') or '')
    if m:
        return int(m.group(1))
    o = str(s.get('observed') or s.get('observedAt') or s.get('date') or '')
    return int(o[:4]) if re.match(r'\d{4}', o) else None


def sweep_works(school, here=None):
    c = sqlite3.connect(f"file:{P.data('openalex-sweep.sqlite', school, root=here or HERE)}?mode=ro", uri=True)
    for (body,) in c.execute('select body from pages order by year, page'):
        yield from json.loads(zlib.decompress(body))


def best_sources(srcs, k=2):
    """Up to k evidence items, complete ones first (url, sha256 and a quote; 2026-10-29 evidence check): the collection's
    MIT records write the quoted sentence as 'statement', which becomes the quote (quote_field='statement')."""
    out = []
    for q in srcs or []:
        if isinstance(q, dict) and not str(q.get('quote') or '').strip() and str(q.get('statement') or '').strip():
            q = dict(q, quote=q['statement'], quote_field='statement')
        out.append(q)
    full = lambda q: isinstance(q, dict) and bool(q.get('url')) and bool(re.fullmatch(r'[0-9a-f]{64}', str(q.get('sha256') or ''))) and bool(str(q.get('quote') or '').strip())
    return sorted(out, key=lambda q: not full(q))[:k]


def as_list(v):
    """An identity field as a list: census rows give a single DBLP/ORCID/OpenAlex id as a string, list() would split it into characters."""
    return [v] if isinstance(v, str) else list(v or [])


def as_years(v, n=None):
    """A record's years as integers (2026-10-31, validation findings): a string ('2020', '2019-2021') gives the 4-digit
    years in it (few-students-evidence.json had strings, read before character by character), a list its integer-like
    items; years outside 1950 .. next year are dropped (a lab page's 2099 placeholder), counted in n."""
    items = re.findall(r'(?<!\d)\d{4}(?!\d)', v) if isinstance(v, str) else list(v or [])
    out = []
    for y in items:
        y = int(y) if isinstance(y, int) or (isinstance(y, str) and y.strip().isdigit()) else None
        if y is None:
            continue
        if 1950 <= y <= int(TODAY[:4]) + 1:
            out.append(y)
        elif n is not None:
            n['record_years_out_of_range_dropped'] += 1
    if isinstance(v, str) and n is not None:
        n['record_years_parsed_from_string'] += 1
    return out


def iso_date(v):
    """A date written as a Wayback timestamp or digits (20260128, 2026012820, 20260128203237) as ISO (2026-01-28);
    anything else unchanged (2026-10-31: a reviewed period's asof '2026012820' read as unresolved)."""
    return f'{v[:4]}-{v[4:6]}-{v[6:8]}' if isinstance(v, str) and re.fullmatch(r'\d{8}(?:\d{2}){0,3}', v) else v


def collection_work_matcher(works):
    """cwork(oa work) -> the collection work id it is (by DOI, else by normalized title within one year), or None."""
    # collection works by DOI and title
    by_doi, by_title = {}, collections.defaultdict(list)
    for wid, w in works.items():
        for d in [w.get('doi')] + [a for a in (w.get('aliases') or []) if str(a).startswith('10.') or 'doi.org' in str(a)]:
            if d:
                by_doi.setdefault(ndoi(d), wid)
        if w.get('title'):
            by_title[norm_title(w['title'])].append(wid)

    def cwork(oa):
        d = ndoi(oa.get('doi'))
        if d and d in by_doi:
            return by_doi[d]
        for wid in by_title.get(norm_title(oa.get('title')), []):
            y = works[wid].get('year')
            if not y or not oa.get('publication_year') or abs(int(str(y)[:4]) - oa['publication_year']) <= 1:
                return wid
        return None
    return cwork


class Ctx:
    """The state one school's build carries from stage to stage. `here` is the data root the inputs are read from (the
    main checkout, atlas_paths.WORK), `site` the site collections, `out` where the package is written; `n` holds the
    report's counts in the order the stages add them."""

    def __init__(self, school, here=None, site=None, out=None):
        self.school = school
        self.here = Path(here) if here is not None else HERE
        self.site = Path(site) if site is not None else SITE
        self.out = out
        self.n = collections.Counter()
