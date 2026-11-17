"""Per-school evidence store, phase 1 (docs/EVIDENCE-STORE.md): a lossless SQLite copy of the reviewed JSON files, and the way back.

  import   <school>... | --all   read the reviewed files into <store dir>/<school>/evidence.sqlite (a fresh file each time)
  export   <school>... | --all   write the reviewed files' content again from the stores (--out DIR, laid out like the code root)
  verify   <school>... | --all   import into a scratch store and export again; every file must come back (byte or canonical-JSON identical)
  overlay  <school> --out DIR    an overlay code root (tools/overlay_root.py) whose reviewed files are the exported ones
  coverage <school>... | --all   the files and records the converters cannot represent

Nothing reads the store yet. Lossless rule: every decision keeps its original record as JSON (column `record`); the claim columns
(person, kind, value, source, who/when) are an index projected from the record by claim() below, best effort and recomputable.
A file is cut into containers (a list, a map, or a school -> person map); the rest of the file is the skeleton. The shared reviewed
files (hierarchy/reviewed/) are split over the school stores by school; what names no school goes to the store `_shared`.
"""
import argparse
import contextlib
import copy
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402
import school_config as S  # noqa: E402

SQL = Path(__file__).resolve().parents[1] / 'schemas' / 'evidence' / 'evidence-store.sql'
SHARED = '_shared'
TIMEOUT = 60
# Top-level keys whose value is a map of decisions (a list of dicts is a container whatever its key).
MAP_KEYS = {'decisions', 'people', 'pis', 'confirmed', 'unresolved', 'not_departures', 'packages', 'verdicts'}
LIST_KEYS = {'rows', 'records', 'reviews', 'labs', 'papers', 'students', 'additions', 'holds', 'exclusions', 'sources', 'anchors', 'pairs', 'facts', 'cdx', 'sample'}
SKIP_FILES = ('student-recall-check.20',)   # dated audit samples (not decisions): still imported, only named here for coverage notes

# ---------------------------------------------------------------- reading and writing JSON with the file's own formatting


class DuplicateKey(ValueError):
    pass


def _pairs(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise DuplicateKey(k)
        d[k] = v
    return d


def parse(text):
    return json.loads(text, object_pairs_hook=_pairs)


def guess_styles(text):
    """Candidate dump styles, the likeliest first (a full search costs a dump of a 15 MB file per candidate)."""
    first = text[:400]
    indent = None
    if first.startswith(('{\n', '[\n')):
        rest = first.split('\n', 2)[1]
        indent = len(rest) - len(rest.lstrip(' ')) or None
    compact = first.startswith(('{"', '[{', '["')) and indent is None and ('", "' not in text[:2000] and '": "' not in text[:2000])
    ascii_ = '\\u' in text
    nl = text.endswith('\n')
    seen, out = set(), []
    for ind in (indent, 1, 2, None, 4, 3, 0):
        for cmp_ in ((compact,) if ind is None and compact else (False, True)):
            for a in (ascii_, not ascii_):
                for srt in (False, True):
                    s = (ind, a, cmp_, srt, nl)
                    if s not in seen:
                        seen.add(s)
                        out.append(dict(indent=ind, ascii=a, compact=cmp_, sort=srt, newline=nl))
    return out


def dumps(doc, st):
    st = st or dict(indent=1, ascii=False, compact=False, sort=False, newline=True)
    sep = (',', ':') if st['compact'] else ((',', ': ') if st['indent'] is not None else (', ', ': '))
    return json.dumps(doc, indent=st['indent'], ensure_ascii=st['ascii'], sort_keys=st['sort'], separators=sep) + ('\n' if st['newline'] else '')


def find_style(doc, text):
    for st in guess_styles(text):
        if dumps(doc, st) == text:
            return st
    return None


def compact(x):
    return json.dumps(x, ensure_ascii=False, separators=(',', ':'))


# ---------------------------------------------------------------- cutting a document into containers


def _is_map(v):
    return isinstance(v, dict) and v and all(isinstance(x, (dict, list)) for x in v.values())


def _decision_container(k, v):
    if isinstance(v, list):
        return 'list' if v and all(isinstance(x, dict) for x in v) else None
    return 'map' if k in MAP_KEYS and _is_map(v) else None


def containers_of(doc, school_split=False):
    """[(path, kind)] of the decision containers of a document. A root list, a root map (every value a dict or list; `_`-keys stay in the
    skeleton), or per top-level key: a non-empty list of dicts, or a map under MAP_KEYS. No container: the whole document is one 'doc' row."""
    if isinstance(doc, list):
        return [((), 'list')] if doc else []
    if not isinstance(doc, dict):
        return [((), 'doc')]
    live = {k: v for k, v in doc.items() if not k.startswith('_')}
    if live and all(isinstance(v, (dict, list)) for v in live.values()) and not any(k in MAP_KEYS or k in LIST_KEYS for k in live):
        return [((), 'map2' if school_split and all(isinstance(v, dict) for v in live.values()) else 'map')]
    out = []
    for k, v in doc.items():
        kind = _decision_container(k, v)
        if kind:
            out.append(((k,), kind))
    return out or ([] if not doc else [((), 'doc')])


def cut(doc, school_split=False):
    """(skeleton, key_order, containers, rows) where rows are (container index, seq, entry_key, sub_key, record)."""
    conts = containers_of(doc, school_split)
    rows = []
    if not conts:
        return doc, (list(doc) if isinstance(doc, dict) else None), [], rows
    if conts[0][0] == () and conts[0][1] == 'doc':
        return None, None, [dict(path=[], kind='doc')], [(0, 0, None, None, doc)]
    skeleton = copy.copy(doc) if isinstance(doc, dict) else None
    order = list(doc) if isinstance(doc, dict) else None
    for ci, (path, kind) in enumerate(conts):
        node = doc if not path else doc[path[0]]
        if kind == 'list':
            rows += [(ci, i, None, None, r) for i, r in enumerate(node)]
        elif kind == 'map':
            rows += [(ci, i, k, None, v) for i, (k, v) in enumerate((k, v) for k, v in node.items() if path or not k.startswith('_'))]
        else:   # map2: outer key -> {inner key: record}; an outer value that is not a non-empty map of records is one whole-section row
            i = 0
            for k, v in node.items():
                if k.startswith('_') and not path:
                    continue
                if isinstance(v, dict) and v and all(isinstance(x, dict) for x in v.values()):
                    for sk, sv in v.items():
                        rows.append((ci, i, k, sk, sv))
                        i += 1
                else:
                    rows.append((ci, i, k, None, v))
                    i += 1
        if path:
            skeleton[path[0]] = None
        elif isinstance(doc, dict):   # a root map: entries leave the skeleton, `_` keys stay
            skeleton = {k: v for k, v in doc.items() if k.startswith('_')}
        else:
            skeleton = None
    return skeleton, order, [dict(path=list(p), kind=k) for p, k in conts], rows


def assemble(skeleton, key_order, containers, rows):
    """The document back from its skeleton and rows [(container, seq, entry_key, sub_key, record)] (any order)."""
    if containers and containers[0]['kind'] == 'doc':
        return rows[0][4]
    doc = copy.deepcopy(skeleton) if skeleton is not None else None
    for ci, c in enumerate(containers):
        mine = sorted((r for r in rows if r[0] == ci), key=lambda r: r[1])
        if c['kind'] == 'list':
            node = [r[4] for r in mine]
        else:
            node = {}
            for _, _, k, sk, rec in mine:
                if sk is None:
                    node[k] = rec
                else:
                    node.setdefault(k, {})[sk] = rec
        if c['path']:
            doc[c['path'][0]] = node
        elif isinstance(node, dict):
            doc = {**(doc or {}), **node}
        else:
            doc = node
    if isinstance(doc, dict) and key_order:
        doc = {k: doc[k] for k in key_order if k in doc} | {k: v for k, v in doc.items() if k not in key_order}
    return doc


# ---------------------------------------------------------------- the claim columns (a projection of the record)

PERSON_FIELDS = ('name', 'pi', 'person', 'student', 'listed_name', 'full_name', 'display_name', 'canonical_name', 'census_name')
KIND_BY_LAYER = {
    'census-additions.json': 'admission', 'faculty-periods.json': 'period', 'student-decisions.json': 'student_membership',
    'student-corrections.json': 'student_membership', 'few-students-evidence.json': 'student_membership',
    'student-link-exclusions.json': 'student_membership', 'student-identity-review.json': 'identity_link',
    'student-name-candidates.json': 'identity_link', 'openalex-identity-review.json': 'identity_link',
    'identity-bindings-school.json': 'identity_link', 'paper-claim-review.json': 'paper_claim', 'home-department-decisions.json': 'home_department',
    'home-departments.json': 'home_department', 'cs-related-home-departments.json': 'home_department', 'lab-coverage-reasons.json': 'lab_reason',
    'zero-paper-review.json': 'lab_reason', 'chain-reasons.json': 'lab_reason', 'labpage-additions.json': 'student_membership',
    'gap-evidence.json': 'student_membership', 'cs-related-source-exclusions.json': 'exclusion',
}
DECISION_LAYERS = ('cs-related-review.json', 'missing-pi-review.json', 'missed-labs-review.json', 'stage2-preliminary-decisions.json', 'cs-related-hand.json')
NOT_PERSON_SUB = ('chain-reasons.json',)   # the inner key is a category, not a person
FACETS = (('exclusion', ('excluded', 'exclude', 'exclusion', 'exclude_why')), ('hold', ('no_identity',)), ('period', ('periods', 'faculty_periods')),
          ('identity_link', ('aliases', 'dblp', 'orcid', 'openalex', 'collection_person_id', 'mixed_openalex', 'not_openalex', 'identity_resolution')),
          ('home_department', ('home_department',)), ('rank', ('rank', 'is_pi', 'primary_stated', 'pi_basis')))
EXCLUDING = ('not_', 'excluded', 'does_not', 'too_few', 'no_', 'faculty_no', 'faculty_not', 'research_or_other', 'not_at_school', 'rejected', 'reject')


def decision_kind(d):
    d = str(d)
    if d == 'excluded_unresolved':
        return 'excluded_unresolved'
    if d.startswith(('held', 'hold')):
        return 'hold'
    if d in ('census_alias', 'alias_added', 'already_in_census_as'):
        return 'identity_link'
    if d in ('accepted', 'qualifies', 'admit', 'admitted'):
        return 'cs_related'
    if d.startswith(('pending', 'unresolved')):
        return 'review_note'
    if d.startswith(EXCLUDING) or d.startswith('already') or d.startswith('previously'):
        return 'exclusion'
    return 'other'


def _s(v):
    if v is None or v == '':
        return None
    return v if isinstance(v, str) else compact(v)


def _first(rec, names, strings_only=True):
    for n in names:
        v = rec.get(n)
        if isinstance(v, str) and v:
            return v
        if not strings_only and v not in (None, '', [], {}):
            return _s(v)
    return None


def _url_of(rec):
    u = _first(rec, ('source_url', 'url', 'profile_url', 'source', 'official_profile_url'))
    if u and u.startswith('http'):
        return u
    for k in ('evidence', 'sources', 'faculty_evidence', 'home_department_evidence', 'openalex_evidence', 'dblp_evidence', 'identity_evidence'):
        v = rec.get(k)
        for item in (v if isinstance(v, list) else [v]):
            if isinstance(item, dict):
                for kk in ('url', 'source_url', 'source'):
                    if isinstance(item.get(kk), str) and item[kk].startswith('http'):
                        return item[kk]
            elif isinstance(item, str) and item.startswith('http'):
                return item
    return None


def _evidence_field(rec, names):
    for k in ('evidence', 'sources'):
        v = rec.get(k)
        for item in (v if isinstance(v, list) else [v]):
            if isinstance(item, dict):
                x = _first(item, names)
                if x:
                    return x
    return None


def claim(layer, rec, entry_key=None, sub_key=None):
    """The projected columns of one record. Never the other way: the record is the truth."""
    r = rec if isinstance(rec, dict) else {}
    person = None
    if layer not in NOT_PERSON_SUB:
        person = _first(r, PERSON_FIELDS) or sub_key or entry_key
        if isinstance(r.get('pi'), str) and layer in ('student-corrections.json', 'student-link-exclusions.json', 'student-identity-review.json', 'student-name-candidates.json'):
            person = r['pi']
    elif sub_key is None:
        person = entry_key
    if layer in ('census-overrides.json', 'census-overrides-school.json', 'student-decisions.json') and not r.get('name'):
        person = sub_key or entry_key
    facets = [k for k, keys in FACETS if any(r.get(x) not in (None, '', [], {}, False) for x in keys)] if isinstance(rec, dict) else []
    if layer.startswith('census-overrides'):
        kind = next((f for f in ('exclusion', 'hold', 'period', 'identity_link', 'home_department', 'rank') if f in facets), 'other')
    elif layer in DECISION_LAYERS or ('decision' in r and isinstance(r.get('decision'), str) and layer not in KIND_BY_LAYER):
        kind = decision_kind(r.get('decision'))
        if layer == 'paper-claim-review.json':
            kind = 'paper_claim'
    elif layer == 'paper-claim-review.json':
        kind = 'hold' if r.get('decision') == 'hold' else 'paper_claim'
    else:
        kind = KIND_BY_LAYER.get(layer) or ('evidence' if isinstance(rec, dict) else 'other')
    value = {}
    for k in ('decision', 'reason', 'reason_code', 'sources_tried', 'rank', 'title_as_listed', 'is_pi', 'pi_basis', 'facultyStart', 'facultyEnd', 'role',
              'facultyRole', 'periods', 'no_identity', 'why_no_identity', 'home_department', 'verdict', 'status', 'action', 'canonical_name', 'why',
              'excluded', 'exclusion'):
        if k in r and r[k] not in (None, ''):
            value[k] = r[k]
    return dict(
        person_key=_s(person), claim_kind=kind, facets=compact(facets) if facets else None, value=compact(value) if value else None,
        source_url=_url_of(r),
        source_date=_first(r, ('captured', 'capture_date', 'captured_at', 'fetched', 'fetched_at', 'retrieved')) or _evidence_field(r, ('captured', 'capture_date', 'fetched', 'retrieved', 'date')),
        source_kind=_first(r, ('source_kind', 'kind')) or _evidence_field(r, ('kind', 'source_kind')),
        decided_by=_first(r, ('decided_by', 'addedBy', 'added_by', 'reviewer')),
        decided_at=_first(r, ('decided_at', 'reviewedOn', 'reviewed_on', 'reviewed_at', 'reviewed', 'added')),
        reviewed_by=_first(r, ('reviewed_by', 'reviewer')) or _s(r.get('independent_review') if isinstance(r.get('independent_review'), str) else None),
        review_ref=_s(_first(r, ('review_ref', 'review', 'id'), strings_only=False)) if not isinstance(r.get('review'), (dict, list)) else None,
        supersedes=_first(r, ('supersedes', 'superseded_hold', 'prior_exclusion_preserved_in')),
    )


# ---------------------------------------------------------------- reading the reviewed files of a checkout

def code_root(root=None):
    return Path(root or P.CODE)


def school_dir(school, root=None):
    return code_root(root) / 'hierarchy' / school / 'reviewed'


def shared_dir(root=None):
    return code_root(root) / 'hierarchy' / 'reviewed'


def school_ids(root=None):
    h = code_root(root) / 'hierarchy'
    known = set(S.keys())
    return sorted(d.name for d in h.iterdir() if d.name in known and (d / 'reviewed').is_dir())


def layer_files(d):
    return sorted(f for f in Path(d).glob('*.json') if f.is_file())


def other_files(d):
    """Files in a reviewed directory the JSON converters do not cover (csv tables, subdirectories)."""
    return sorted(f.name + ('/' if f.is_dir() else '') for f in Path(d).iterdir() if f.is_dir() or f.suffix != '.json')


def shared_owner(name, doc, schools):
    """How a shared file splits over school stores: 'list' (items with a school field), 'schoolmap' (top-level keys are schools), or None (all _shared)."""
    if isinstance(doc, list) and doc and all(isinstance(x, dict) and x.get('school') in schools for x in doc):
        return 'list'
    if isinstance(doc, dict):
        live = [k for k in doc if not k.startswith('_')]
        if live and all(k in schools for k in live):
            return 'schoolmap'
    return None


# ---------------------------------------------------------------- the store


def store_dir(d=None):
    return Path(d or os.environ.get('CS_ATLAS_EVIDENCE_DIR') or P.STORES)


def store_path(school, d=None):
    return store_dir(d) / school / 'evidence.sqlite'


def connect(path):
    con = sqlite3.connect(str(path), timeout=TIMEOUT)
    con.execute(f'PRAGMA busy_timeout={TIMEOUT * 1000}')
    return con


def create(con):
    con.executescript(SQL.read_text())


class Builder:
    """Collects one school's store in a local temp file, then copies it into place."""

    def __init__(self, school, tmpdir):
        self.school = school
        self.path = Path(tmpdir) / f'{school}.sqlite'
        self.con = connect(self.path)
        self.con.execute('PRAGMA journal_mode=OFF')
        self.con.execute('PRAGMA synchronous=OFF')
        create(self.con)
        self.layers = {}

    def add_layer(self, name, scope, text, doc, rel, school_split=False, error=None):
        sha = hashlib.sha256(text.encode()).hexdigest()
        if error:
            skeleton, order, conts, rows, style, verbatim = None, None, [], [], None, text
        else:
            skeleton, order, conts, rows = cut(doc, school_split)
            style = find_style(doc, text)
            verbatim = None
        cur = self.con.execute('INSERT INTO layer (name, scope, skeleton, containers, key_order, style, sha256, nbytes, source_path, verbatim, layout_text) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                               (name, scope, None if skeleton is None else compact(skeleton), compact(conts), None if order is None else compact(order),
                                None if style is None else compact(style), sha, len(text.encode()), rel, verbatim, text if (style is None and not error) else None))
        self.layers[name] = cur.lastrowid
        return cur.lastrowid, rows

    def add_rows(self, layer_id, name, rows, school=None, owner=None):
        n = 0
        for ci, seq, ek, sk, rec in rows:
            sch = owner(ci, seq, ek, sk, rec) if owner else school
            c = claim(name, rec, ek, sk)
            self.con.execute('INSERT INTO evidence (school, layer_id, container, seq, entry_key, sub_key, person_key, claim_kind, facets, value, source_url, source_date, '
                             'source_kind, decided_by, decided_at, reviewed_by, review_ref, supersedes, record) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                             (sch, layer_id, ci, seq, ek, sk, c['person_key'], c['claim_kind'], c['facets'], c['value'], c['source_url'], c['source_date'], c['source_kind'],
                              c['decided_by'], c['decided_at'], c['reviewed_by'], c['review_ref'], c['supersedes'], compact(rec)))
            n += 1
        return n

    def close(self, dest, meta):
        for k, v in meta.items():
            self.con.execute('INSERT OR REPLACE INTO meta VALUES (?,?)', (k, str(v)))
        self.con.commit()
        self.con.close()
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix('.sqlite.new')
        shutil.copyfile(self.path, tmp)
        os.replace(tmp, dest)
        self.path.unlink()


def read_layer(f):
    text = Path(f).read_text()
    try:
        return text, parse(text), None
    except (ValueError, RecursionError) as e:   # JSON error or DuplicateKey
        return text, None, f'{type(e).__name__}: {str(e)[:80]}'


def import_all(schools, dest=None, root=None, log=print):
    """Import the reviewed files of `schools` (and the shared files, split over the schools and `_shared`) into the stores. Returns a report."""
    root = code_root(root)
    schools = list(schools)
    known = set(school_ids(root))
    report = dict(schools={}, shared={}, unrepresentable=[])
    builders = {}
    tmp = tempfile.mkdtemp(prefix='evidence-')
    try:
        def builder(s):
            if s not in builders:
                builders[s] = Builder(s, tmp)
            return builders[s]
        for s in schools:
            b = builder(s)
            rep = report['schools'][s] = dict(files=0, rows=0, whole_doc_files=0, verbatim_files=0, empty_files=0, other_files=other_files(school_dir(s, root)))
            for f in layer_files(school_dir(s, root)):
                text, doc, err = read_layer(f)
                rel = str(f.relative_to(root))
                lid, rows = b.add_layer(f.name, 'school', text, doc, rel, error=err)
                rep['files'] += 1
                if err:
                    rep['verbatim_files'] += 1
                    report['unrepresentable'].append(dict(school=s, file=f.name, why=err))
                    continue
                if not rows:
                    rep['empty_files'] += 1
                elif rows[0][0] == 0 and json.loads(b.con.execute('SELECT containers FROM layer WHERE layer_id=?', (lid,)).fetchone()[0])[0]['kind'] == 'doc':
                    rep['whole_doc_files'] += 1
                rep['rows'] += b.add_rows(lid, f.name, rows, school=s)
        # the shared files: each school store gets its slice, `_shared` the descriptor and what names no school
        sh = builder(SHARED)
        report['shared'] = dict(files=0, rows=0, whole_doc_files=0, verbatim_files=0, empty_files=0, other_files=other_files(shared_dir(root)))
        for f in layer_files(shared_dir(root)):
            text, doc, err = read_layer(f)
            rel = str(f.relative_to(root))
            report['shared']['files'] += 1
            if err:
                sh.add_layer(f.name, 'shared', text, doc, rel, error=err)
                report['shared']['verbatim_files'] += 1
                report['unrepresentable'].append(dict(school=SHARED, file=f.name, why=err))
                continue
            owner_kind = shared_owner(f.name, doc, known)
            lid, rows = sh.add_layer(f.name, 'shared', text, doc, rel, school_split=owner_kind == 'schoolmap')
            if not rows:
                report['shared']['empty_files'] += 1
            elif owner_kind is None and json.loads(sh.con.execute('SELECT containers FROM layer WHERE layer_id=?', (lid,)).fetchone()[0])[0]['kind'] == 'doc':
                report['shared']['whole_doc_files'] += 1
            by = {}
            for r in rows:
                s = r[4].get('school') if owner_kind == 'list' else r[2] if owner_kind == 'schoolmap' else None
                s = s if s in known else SHARED
                if s != SHARED and s not in schools:
                    continue   # a school that was not asked for: its slice is not imported now
                by.setdefault(s, []).append(r)
            for s, rs in by.items():
                if s == SHARED:
                    report['shared']['rows'] += sh.add_rows(lid, f.name, rs, school=SHARED)
                    continue
                b = builder(s)
                if f.name not in b.layers:   # the slice needs the layer row in its own store (the full descriptor stays in _shared)
                    cur = b.con.execute('INSERT INTO layer (name, scope, skeleton, containers, key_order, style, sha256, nbytes, source_path) VALUES (?,?,?,?,?,?,?,?,?)',
                                        sh.con.execute('SELECT name, scope, skeleton, containers, key_order, style, sha256, nbytes, source_path FROM layer WHERE layer_id=?', (lid,)).fetchone())
                    b.layers[f.name] = cur.lastrowid
                report['shared']['rows'] += b.add_rows(b.layers[f.name], f.name, rs, school=s)
        for s, b in builders.items():
            n = b.con.execute('SELECT COUNT(*) FROM evidence').fetchone()[0]
            b.close(store_path(s, dest), dict(school=s, rows=n, imported_from=str(root), layout_version=1))
            log(f'  {s}: {n} rows -> {store_path(s, dest)}')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return report


def load_layers(stores):
    """{name: dict(desc..., rows=[...])} merged over the given store paths."""
    out = {}
    for sp in stores:
        with contextlib.closing(connect(sp)) as con:
            for lid, name, scope, skel, conts, order, style, sha, nbytes, verb, layout in con.execute(
                    'SELECT layer_id, name, scope, skeleton, containers, key_order, style, sha256, nbytes, verbatim, layout_text FROM layer'):
                e = out.setdefault(name, dict(scope=scope, skeleton=None, containers=None, order=None, style=None, sha=sha, nbytes=nbytes, verbatim=None, layout=None, rows=[], have_desc=False))
                if scope == 'shared' and sp.parent.name == SHARED or scope == 'school':
                    e.update(skeleton=None if skel is None else json.loads(skel), containers=json.loads(conts), order=None if order is None else json.loads(order),
                             style=None if style is None else json.loads(style), sha=sha, nbytes=nbytes, verbatim=verb, layout=layout, have_desc=True)
                for ci, seq, ek, sk, rec in con.execute('SELECT container, seq, entry_key, sub_key, record FROM evidence WHERE layer_id=?', (lid,)):
                    e['rows'].append((ci, seq, ek, sk, json.loads(rec)))
    return out


def render(e):
    if e['verbatim'] is not None:
        return e['verbatim']
    doc = assemble(e['skeleton'], e['order'], e['containers'], e['rows'])
    if e['style'] is None and e['layout'] is not None and parse(e['layout']) == doc:   # hand-formatted file, content unchanged: its own bytes
        return e['layout']
    return dumps(doc, e['style'])


def export_files(stores, outroot, only=None):
    """Write every layer of the stores under outroot (hierarchy/<school>/reviewed/<name>, hierarchy/reviewed/<name>). Returns {(scope, school, name): path}."""
    done = {}
    layers = {}
    for sp in stores:
        school = sp.parent.name
        for name, e in load_layers([sp]).items():
            layers.setdefault((e['scope'], school if e['scope'] == 'school' else None, name), []).append(e)
    shared = load_layers(stores)
    for (scope, school, name), es in sorted(layers.items(), key=lambda kv: str(kv[0])):
        if scope == 'shared':
            e = shared[name]
            p = Path(outroot) / 'hierarchy' / 'reviewed' / name
        else:
            e = es[0]
            p = Path(outroot) / 'hierarchy' / school / 'reviewed' / name
        if only and name not in only:
            continue
        if not e['have_desc']:
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render(e))
        done[(scope, school, name)] = p
    return done


def compare(root, outroot, schools):
    """Per file: 'byte' (identical bytes), 'canonical' (same JSON, other formatting) or 'DIFF'. Counts and the lists of non-byte files."""
    res = dict(byte=0, canonical=[], diff=[], missing=[])
    root, outroot = Path(root), Path(outroot)
    pairs = [(f, outroot / 'hierarchy' / s / 'reviewed' / f.name, s) for s in schools for f in layer_files(school_dir(s, root))]
    pairs += [(f, outroot / 'hierarchy' / 'reviewed' / f.name, SHARED) for f in layer_files(shared_dir(root))]
    for src, dst, s in pairs:
        if not dst.exists():
            res['missing'].append(f'{s}/{src.name}')
        elif src.read_bytes() == dst.read_bytes():
            res['byte'] += 1
        else:
            try:
                same = json.loads(src.read_text()) == json.loads(dst.read_text())
            except ValueError:
                same = False
            (res['canonical'] if same else res['diff']).append(f'{s}/{src.name}')
    return res


def verify(schools, root=None, log=print):
    """Import into a scratch store, export again, compare with the originals."""
    root = code_root(root)
    tmp = tempfile.mkdtemp(prefix='evidence-verify-')
    try:
        rep = import_all(schools, dest=tmp, root=root, log=lambda *_: None)
        stores = [store_path(s, tmp) for s in list(schools) + [SHARED]]
        export_files(stores, Path(tmp) / 'out')
        res = compare(root, Path(tmp) / 'out', schools)
        # shared files can only be rebuilt whole when every school store is present: only compare them when all schools were imported
        if set(schools) != set(school_ids(root)):
            keep = {f.name for f in layer_files(shared_dir(root))}
            res['missing'] = [m for m in res['missing'] if m.split('/')[-1] not in keep or not m.startswith(SHARED)]
            res['diff'] = [m for m in res['diff'] if not m.startswith(SHARED)]
            res['canonical'] = [m for m in res['canonical'] if not m.startswith(SHARED)]
        res['import'] = rep
        return res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def overlay(school, out, stores_dir, root=None, worktree=None, control=False):
    """An overlay code root (overlay_root.py) in which the school's reviewed files and the shared reviewed files are the exported ones
    (control: the root's own files, copied the same way, so a comparison differs only in where the bytes came from)."""
    import overlay_root as O
    root = code_root(root)
    O.build(school, out, worktree=worktree, main=root, private=False)
    schools = school_ids(root)
    tmp = tempfile.mkdtemp(prefix='evidence-overlay-')
    try:
        if control:
            for rel in (Path('hierarchy') / school / 'reviewed', Path('hierarchy') / 'reviewed'):
                (Path(tmp) / rel).mkdir(parents=True)
                for f in layer_files(root / rel):
                    shutil.copyfile(f, Path(tmp) / rel / f.name)
        else:
            export_files([store_path(s, stores_dir) for s in schools + [SHARED]], tmp)
        n = 0
        for src, rel in ((Path(tmp) / 'hierarchy' / school / 'reviewed', Path('hierarchy') / school / 'reviewed'), (Path(tmp) / 'hierarchy' / 'reviewed', Path('hierarchy') / 'reviewed')):
            for f in sorted(src.glob('*.json')):
                dst = Path(out) / rel / f.name
                if dst.is_symlink() or dst.exists():
                    dst.unlink()
                shutil.copyfile(f, dst)
                n += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['import', 'export', 'verify', 'overlay', 'coverage'])
    ap.add_argument('schools', nargs='*')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--store-dir', help='default $CS_ATLAS_EVIDENCE_DIR or the stores dir')
    ap.add_argument('--out')
    ap.add_argument('--root', help='code root to read the reviewed files from (default CS_ATLAS_CODE)')
    ap.add_argument('--json', help='write the report here')
    ap.add_argument('--control', action='store_true', help='overlay: copy the root\'s own reviewed files instead of the exported ones')
    a = ap.parse_args(argv)
    root = code_root(a.root)
    schools = school_ids(root) if a.all else a.schools
    if not schools:
        ap.error('name a school or pass --all')
    if a.cmd in ('import', 'coverage'):
        rep = import_all(schools, dest=a.store_dir if a.cmd == 'import' else tempfile.mkdtemp(prefix='evidence-cov-'), root=root)
        print(json.dumps(rep, indent=1)[:3000] if not a.json else f'report -> {a.json}')
    elif a.cmd == 'export':
        if not a.out:
            ap.error('--out')
        done = export_files([store_path(s, a.store_dir) for s in schools + [SHARED]], a.out)
        print(f'{len(done)} files under {a.out}')
        return 0
    elif a.cmd == 'verify':
        rep = verify(schools, root)
        print(f'byte-identical {rep["byte"]}; canonical-only {len(rep["canonical"])}; DIFF {len(rep["diff"])}; missing {len(rep["missing"])}')
    else:
        if len(schools) != 1 or not a.out:
            ap.error('overlay takes one school and --out')
        n = overlay(schools[0], a.out, a.store_dir, root, control=a.control)
        print(f'overlay {a.out}: {n} regenerated reviewed files')
        return 0
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1, default=str))
    return 1 if a.cmd == 'verify' and (rep['diff'] or rep['missing']) else 0


if __name__ == '__main__':
    sys.exit(main())
