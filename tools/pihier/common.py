"""What every stage of the build shares: the charter tables, the date, the readers, the work keys and the evidence order."""
import collections, copy, datetime, gzip, hashlib, json, re, sqlite3, unicodedata, zlib
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
    # Preserve the established Latin/ASCII fold; other scripts keep their literal letters and digits.
    out = []
    for c in unicodedata.normalize('NFKC', str(s or '')).lower():
        name = unicodedata.name(c, '')
        if c.isascii() or name.startswith('LATIN '):
            folded = unicodedata.normalize('NFKD', c).encode('ascii', 'ignore').decode()
            out.extend(x for x in folded if 'a' <= x <= 'z' or '0' <= x <= '9')
        elif c.isalnum() and not name.startswith('MODIFIER LETTER '):
            out.append(c)
    return ''.join(out)


def ndoi(s):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(s or '').strip(), flags=re.I).lower()


def source_year(s):
    m = re.search(r'/web/(\d{4})\d{4,10}', s.get('url') or '')
    if m:
        return int(m.group(1))
    o = str(s.get('observed') or s.get('observedAt') or s.get('date') or '')
    return int(o[:4]) if re.match(r'\d{4}', o) else None


def related_gate(school):
    """The charter's related and excluded affiliation entries, or None without either restriction."""
    ids = _S.get(school)['ids']
    rel, excluded = set(ids.get('openalex_related') or []), set(ids.get('openalex_excluded') or [])
    return (rel, _S.aff_rx(school), _S.inst(school), excluded) if rel or excluded else None


def gate_related(w, gate, joint=None):
    """Apply charter scope per affiliation on a copy. Excluded children cannot lend the primary lineage;
    a separate direct primary entry and the authorship's own raw text remain. Related entries retain the
    existing raw-text or documented joint-appointment exception. Joint appointments never override exclusion.
    Three-item gates remain accepted for callers using the original related-only interface."""
    rel, rx, inst = gate[:3]
    excluded = gate[3] if len(gate) > 3 else set()
    sch = inst.rsplit('/', 1)[-1]
    w = copy.deepcopy(w)
    for a in w.get('authorships') or []:
        raws = a.get('raw_affiliation_strings') or []
        who = ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKD', (a.get('raw_author_name') or (a.get('author') or {}).get('display_name') or '')).lower()))
        cited = (joint or {}).get(who, set())
        for x in a.get('institutions') or []:
            direct = str(x.get('id') or '').rsplit('/', 1)[-1]
            ids = {str(l).rsplit('/', 1)[-1] for l in (x.get('lineage') or [])} | {direct}
            if direct == sch:  # a true primary entry is independent of another excluded affiliation
                continue
            denied = bool(ids & excluded) or (ids & rel and not (ids & cited) and not any(rx.search(z or '') for z in raws))
            if denied and sch in ids:
                x['lineage'] = [l for l in (x.get('lineage') or []) if str(l).rsplit('/', 1)[-1] != sch]
    return w


def school_scope_work(w, school):
    """One school-specific view; original shared metadata is never modified."""
    gate = related_gate(school)
    return gate_related(w, gate, joint_appointments(school)) if gate else w


def excluded_school_only(authorship, school):
    """Excluded-campus raw text cannot borrow a derived primary ID or another author's affiliation."""
    explicit = _S.field(_S.get(school), 'affiliation.excluded_regex')
    gate = related_gate(school)
    if not explicit and (not gate or len(gate) < 4 or not gate[3]):
        return False
    raws = authorship.get('raw_affiliation_strings') or []
    rx = gate[1] if gate else _S.aff_rx(school)
    # A broad school name inside an explicitly excluded campus is not
    # independent primary evidence. Remove only the matched spans for this
    # check; another primary occurrence in the same raw string still counts.
    primary_raws = [re.sub(explicit, ' ', raw or '', flags=re.I) for raw in raws] if explicit else raws
    if any(rx.search(raw or '') for raw in primary_raws):
        return False  # independent primary or dual raw evidence remains available
    if explicit and any(re.search(explicit, raw or '', re.I) for raw in raws):
        return True  # literal excluded-campus evidence outranks a derived primary ID
    if not gate or len(gate) < 4 or not gate[3]:
        return False
    _, rx, inst, excluded = gate
    sch = inst.rsplit('/', 1)[-1]
    entries = [{str(x.get('id') or '').rsplit('/', 1)[-1]} |
               {str(i).rsplit('/', 1)[-1] for i in x.get('lineage') or []}
               for x in authorship.get('institutions') or []]
    has_excluded = any(ids & excluded for ids in entries)
    if has_excluded and any(re.search(SCHOOL_LOOSE[school], raw or '', re.I) for raw in raws):
        return True  # named school variant fails the charter's primary-campus pattern
    if any(sch in ids and not ids & excluded for ids in entries):
        return False
    if any(str(x.get('id') or '').rsplit('/', 1)[-1] == sch for x in authorship.get('institutions') or []):
        return False
    return has_excluded


def joint_appointments(school):
    """{folded PI name: {related ids}} from the school's census overrides (`joint_appointments`: [{institution, url, sha256, quote}])."""
    import census_overrides as CO
    out = {}
    for name, o in CO.section(school).items():
        ids = {str(j.get('institution')).rsplit('/', 1)[-1] for j in o.get('joint_appointments') or [] if j.get('url') and j.get('quote')}
        if ids:
            out[' '.join(re.findall(r'\w+', unicodedata.normalize('NFKD', name).lower()))] = ids
    return out


def work_sha(w):
    """sha256 of a fetched OpenAlex work record as the reviewed files store it (sorted keys, no ASCII escaping)."""
    return hashlib.sha256(json.dumps(w, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


POST_SNAPSHOT_CUTOFF = '2026-10-14'   # D-0073: works OpenAlex created after the sweep snapshot enter only as reviewed per-PI additions


def post_snapshot_works(school, here=None, n=None):
    """The reviewed post-snapshot works of hierarchy/<school>/reviewed/post-snapshot-works.json (tools/post_snapshot_works.py, owner decision D-0073): an entry
    is wired only when it names its reviewer and reason, still hashes to its stored sha256, and was created after the snapshot. Yields the stored OpenAlex record."""
    f = P.data('post-snapshot-works.json', school, root=here or HERE)
    if not f.exists():
        return
    done = set()
    for e in (json.loads(f.read_text()).get('works') or {}).values():
        w = e.get('record')
        why = None if (e.get('reviewed_by') and e.get('why') and w) else 'not_reviewed'
        why = why or (None if work_sha(w) == e.get('sha256') else 'hash_changed')
        why = why or (None if str(w.get('created_date') or '')[:10] > POST_SNAPSHOT_CUTOFF else 'not_after_snapshot')
        if n is not None:
            n['post_snapshot_works_' + ('wired' if not why else 'not_wired:' + why)] += 1
        if not why and w['id'] not in done:   # one record per work, whichever PIs share it (the entries are keyed work|PI)
            done.add(w['id'])
            yield w


def sweep_works(school, here=None, n=None):
    c = sqlite3.connect(f"file:{P.data('openalex-sweep.sqlite', school, root=here or HERE)}?mode=ro", uri=True)
    gate = related_gate(school)
    joint = joint_appointments(school) if gate else None
    seen = set()
    for (body,) in c.execute('select body from pages order by year, page'):
        for w in json.loads(zlib.decompress(body)):
            seen.add(w.get('id'))
            yield gate_related(w, gate, joint) if gate else w
    for w in post_snapshot_works(school, here, n):   # D-0073: reviewed additions after the snapshot (never a work the snapshot already holds)
        if w.get('id') not in seen:
            yield gate_related(w, gate, joint) if gate else w


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


def accepted_additions(school, kind, here=None, n=None):
    """The lab-page additions of one kind ('students' | 'papers') the build reads (docs/LAB-PAGES.md, acceptance bar;
    2026-10-31): only when hierarchy/<school>/labpage-acceptance.json accepts that kind and names the additions file the
    build sees by its sha256 (additions regenerated after the hand check are not wired until accepted again). Written by
    the lab-page agent's tools; read only here. A school with additions but no accepted kind counts the reason in n."""
    acc_f, add_f = P.data('labpage-acceptance.json', school, root=here), P.data('labpage-additions.json', school, root=here)
    why = None
    if not acc_f.exists():
        why = 'no_acceptance'
    else:
        acc = read(acc_f)
        if not (acc.get(kind) or {}).get('accepted'):
            why = 'not_accepted'
        elif not add_f.exists():
            why = 'no_additions_file'
        elif hashlib.sha256(add_f.read_bytes()).hexdigest() != acc.get('additions_sha256'):
            why = 'additions_changed_since_acceptance'
    if why:
        if n is not None and add_f.exists():
            n[f'labpage_additions_{kind}_not_wired:{why}'] += 1
        return []
    rows = list(read(add_f).get(kind) or [])
    if n is not None:
        n[f'labpage_additions_{kind}_wired'] += len(rows)
    return rows


def collection_work_matcher(works):
    """cwork(oa work) -> the collection work id it is (by DOI, else by normalized title within one year), or None."""
    # collection works by DOI and title
    by_doi, by_title = {}, collections.defaultdict(list)
    for wid, w in works.items():
        for d in [w.get('doi')] + [a for a in (w.get('aliases') or []) if str(a).startswith('10.') or 'doi.org' in str(a)]:
            if d:
                by_doi.setdefault(ndoi(d), wid)
        if title_key := norm_title(w.get('title')):
            by_title[title_key].append(wid)

    def cwork(oa):
        d = ndoi(oa.get('doi'))
        if d and d in by_doi:
            return by_doi[d]
        title_key = norm_title(oa.get('title'))
        for wid in by_title.get(title_key, []) if title_key else []:
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
        self.initials_merges = []  # merges only the optional-initials rule made (R-STU-13), for the report
        self.typo_pairs = []  # (pi, record id, record id): one-letter surname typos left for review (R-STU-13)
        self.corroborated = []  # lab-page students wired by R-STU-20 (report.json labpageStudentsCorroborated)
        self.labpage_set_aside = []  # accepted lab-page papers the build did not keep, with the reason (report.json)
