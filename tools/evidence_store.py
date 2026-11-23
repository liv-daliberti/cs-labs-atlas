"""Per-school evidence store, phase 1 (docs/EVIDENCE-STORE.md): a lossless SQLite copy of the reviewed JSON files, and the way back.

  import   <school>... | --all   read the reviewed files into <store dir>/<school>/evidence.sqlite (a fresh file each time)
  export   <school>... | --all   write the reviewed files' content again from the stores (--out DIR, laid out like the code root)
  verify   <school>... | --all   import into a scratch store and export again; every file must come back (byte or canonical-JSON identical)
  overlay  <school> --out DIR    an overlay code root (tools/overlay_root.py) whose reviewed files are the exported ones
  coverage <school>... | --all   the files and records the converters cannot represent

  backup / restore   a sqlite online backup (integrity_check, sha256) of every flagged store into archive/evidence-store-backups/<UTC stamp>/, newest 14 per school kept
           (`backup --loop` is the daily Slurm job fulltext-push/evidence-backup.slurm); restore puts one back (docs/EVIDENCE-STORE.md)
  add-layer <school> --layer NAME.json --shape list|map [--container-key K [--skeleton JSON]]   a new, empty layer in a store-sourced school's store
  flagged  / find / record / sync / check   phase 2 (R3a): a school whose charter says [evidence] source = "store" writes its decisions HERE
           (record), and its reviewed JSON files are an export (sync) that check/pre-commit/doctor keep honest.
Phase 1 builders read none of it; with the flag, readers still read the exported JSON view, so nothing downstream changes. Lossless rule: every decision keeps its original record as JSON (column `record`); the claim columns
(person, kind, value, source, who/when) are an index projected from the record by claim() below, best effort and recomputable.
A file is cut into containers (a list, a map, or a school -> person map); the rest of the file is the skeleton. The shared reviewed
files (hierarchy/reviewed/) are split over the school stores by school; what names no school goes to the store `_shared`.
"""
import argparse
import contextlib
import copy
import fnmatch
import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

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


def insert_row(con, school, layer_id, layer_name, ci, seq, ek, sk, rec):
    c = claim(layer_name, rec, ek, sk)
    return con.execute('INSERT INTO evidence (school, layer_id, container, seq, entry_key, sub_key, person_key, claim_kind, facets, value, source_url, source_date, '
                       'source_kind, decided_by, decided_at, reviewed_by, review_ref, supersedes, record) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (school, layer_id, ci, seq, ek, sk, c['person_key'], c['claim_kind'], c['facets'], c['value'], c['source_url'], c['source_date'], c['source_kind'],
                        c['decided_by'], c['decided_at'], c['reviewed_by'], c['review_ref'], c['supersedes'], compact(rec))).lastrowid


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
            insert_row(self.con, sch, layer_id, name, ci, seq, ek, sk, rec)
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
            if source_of(s) == 'store' and store_path(s, dest).exists():
                raise SourceOfTruth(f'{s}: charter [evidence] source = "store" and {store_path(s, dest)} exists; a fresh import would erase its recorded decisions. '
                                    f'Record decisions with `evidence_store.py record`; to start over, move the store file away yourself.')
            b = builder(s)
            rep = report['schools'][s] = dict(files=0, rows=0, whole_doc_files=0, verbatim_files=0, empty_files=0, other_files=other_files(school_dir(s, root)))
            for f in layer_files(school_dir(s, root)):
                if source_of(s) == 'store' and is_unmanaged(s, f.name):
                    continue
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
    pairs = [(f, outroot / 'hierarchy' / s / 'reviewed' / f.name, s) for s in schools for f in layer_files(school_dir(s, root)) if not (source_of(s) == 'store' and is_unmanaged(s, f.name))]
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


# ---------------------------------------------------------------- phase 2: a school whose store is the source of truth


class SourceOfTruth(RuntimeError):
    """A write, an import or an edit that the school's [evidence] source = "store" flag does not allow."""


def is_unmanaged(school, name):
    try:
        pats = S.evidence_unmanaged(school)
    except KeyError:
        return False
    return any(fnmatch.fnmatch(name, p) for p in pats)


def source_of(school):
    try:
        return S.evidence_source(school)
    except KeyError:
        return 'json'


def flagged(schools=None):
    return [s for s in (schools if schools is not None else S.keys()) if source_of(s) == 'store']


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def rendered(school, stores_dir=None):
    """{layer name: text} of the school's own (scope 'school') layers as the store renders them now."""
    sp = store_path(school, stores_dir)
    if not sp.exists():
        raise SourceOfTruth(f'{school}: no evidence store at {sp} (import it first: evidence_store.py import {school})')
    return {n: render(e) for n, e in load_layers([sp]).items() if e['scope'] == 'school' and e['have_desc']}


def sync(school, root=None, stores_dir=None):
    """Write the school's reviewed JSON files (the compatibility view) from its store into the code root; only files whose bytes differ. Returns the changed names."""
    changed = []
    d = school_dir(school, root)
    d.mkdir(parents=True, exist_ok=True)
    for name, text in sorted(rendered(school, stores_dir).items()):
        f = d / name
        if f.exists() and f.read_text() == text:
            continue
        tmp = f.with_name(f.name + '.sync-tmp')
        tmp.write_text(text)
        os.replace(tmp, f)
        changed.append(name)
    return changed


# ---------------------------------------------------------------- shared reviewed files: one school's slice (charter [evidence] shared = "store")


def shared_of(school):
    try:
        return S.evidence_shared(school)
    except KeyError:
        return 'json'


def slice_of(doc, owner, school):
    """The school's rows of a shared document as cut() numbers them (container, seq, entry_key, sub_key, record); owner is 'list' or 'schoolmap'."""
    skeleton, order, conts, rows = cut(doc, school_split=owner == 'schoolmap')
    if owner == 'list':
        return [r for r in rows if r[4].get('school') == school]
    return [r for r in rows if r[2] == school]


def patch_slice(text, owner, school, rows):
    """The shared file `text` with only `school`'s slice replaced by `rows` (the store's rows, any order); every other byte-for-byte as is.
    Unchanged content returns `text` itself. A list file: the school's items are replaced in place by seq, extra rows go after its last item, a surplus
    item is dropped. A school-keyed map: the school's section is rebuilt from the rows (added at the end when new)."""
    doc = parse(text)
    rows = sorted(rows, key=lambda r: r[1])
    if owner == 'list':
        pos = [i for i, x in enumerate(doc) if isinstance(x, dict) and x.get('school') == school]
        recs = [r[4] for r in rows]
        new = list(doc)
        for p, rec in zip(pos, recs):
            new[p] = rec
        extra = recs[len(pos):]
        drop = set(pos[len(recs):])
        at = (pos[-1] + 1) if pos else len(new)
        new = new[:at] + extra + new[at:]
        new = [x for i, x in enumerate(new) if i not in drop] if drop else new
    else:
        new = dict(doc)
        if rows:
            if any(r[3] is None for r in rows):
                new[school] = rows[0][4]
            else:
                new[school] = {r[3]: r[4] for r in rows}
    if compact(new) == compact(doc):
        return text
    return dumps(new, find_style(doc, text))


def shared_layers(con):
    """{name: (layer_id, owner kind 'list'|'schoolmap')} of the shared layers a store holds a slice of."""
    out = {}
    for lid, name, conts in con.execute("SELECT layer_id, name, containers FROM layer WHERE scope = 'shared'"):
        kinds = json.loads(conts)
        out[name] = (lid, 'schoolmap' if kinds and kinds[0]['kind'] == 'map2' else 'list')
    return out


def shared_texts(school, root=None, stores_dir=None, staged=None):
    """{name: (current text or None, patched text)} for every shared file the school's store holds a slice of. `staged`: read the git index instead of the tree."""
    root = code_root(root)
    sp = store_path(school, stores_dir)
    out = {}
    with contextlib.closing(connect(sp)) as con:
        for name, (lid, owner) in sorted(shared_layers(con).items()):
            rel = str(Path('hierarchy') / 'reviewed' / name)
            f = root / rel
            cur = _staged(root, rel) if staged is not None else f.read_text() if f.exists() else None
            if cur is None:
                out[name] = (None, None)
                continue
            rows = [(ci, seq, ek, sk, json.loads(rec)) for ci, seq, ek, sk, rec in con.execute('SELECT container, seq, entry_key, sub_key, record FROM evidence WHERE layer_id = ?', (lid,))]
            out[name] = (cur, patch_slice(cur, owner, school, rows))
    return out


def sync_shared(school, root=None, stores_dir=None):
    """Rewrite the school's slice of each shared reviewed file in the root from its store (only files whose bytes change). Returns the changed names."""
    changed = []
    d = shared_dir(root)
    for name, (cur, new) in shared_texts(school, root, stores_dir).items():
        if cur is None or cur == new:
            continue
        tmp = d / (name + '.sync-tmp')
        tmp.write_text(new)
        os.replace(tmp, d / name)
        changed.append(name)
    return changed


def adopt_shared(school, root=None, stores_dir=None, log=print):
    """One-time (re-runnable until the charter flag is set) move of the school's slices of the shared files into its store: every shared file that is a list of
    items with a `school` field or a school-keyed map gets a shared layer in the store, with the school's current rows (replacing an earlier snapshot)."""
    if shared_of(school) == 'store':
        raise SourceOfTruth(f'{school}: [evidence] shared = "store" already; its slices are recorded decisions, a re-adopt would erase them')
    root = code_root(root)
    known = set(school_ids(root))
    sp = store_path(school, stores_dir)
    if not sp.exists():
        raise SourceOfTruth(f'{school}: no evidence store at {sp}')
    with contextlib.closing(connect(sp)) as con:
        create(con)
        con.execute('BEGIN IMMEDIATE')
        try:
            own = {r[0] for r in con.execute("SELECT name FROM layer WHERE scope = 'school'")}
            old = [r[0] for r in con.execute("SELECT layer_id FROM layer WHERE scope = 'shared'")]
            for lid in old:
                con.execute('DELETE FROM evidence WHERE layer_id = ?', (lid,))
                con.execute('DELETE FROM layer WHERE layer_id = ?', (lid,))
            tot = 0
            for f in layer_files(shared_dir(root)):
                text, doc, err = read_layer(f)
                if err:
                    continue
                owner = shared_owner(f.name, doc, known)
                if owner is None:
                    continue
                if f.name in own:
                    raise SourceOfTruth(f'{school}: the school file {f.name} has the name of a shared file; the store keys layers by name')
                skeleton, order, conts, rows = cut(doc, owner == 'schoolmap')
                style = find_style(doc, text)
                cur = con.execute('INSERT INTO layer (name, scope, skeleton, containers, key_order, style, sha256, nbytes, source_path, layout_text) VALUES (?,?,?,?,?,?,?,?,?,?)',
                                  (f.name, 'shared', None if skeleton is None else compact(skeleton), compact(conts), None if order is None else compact(order),
                                   None if style is None else compact(style), sha(text), len(text.encode()), str(f.relative_to(root)), text if style is None else None))
                mine = slice_of(doc, owner, school)
                for ci, seq, ek, sk, rec in mine:
                    insert_row(con, school, cur.lastrowid, f.name, ci, seq, ek, sk, rec)
                tot += len(mine)
                log(f'  {f.name}: {len(mine)} {school} rows ({owner})')
            con.execute('COMMIT')
        except BaseException:
            con.execute('ROLLBACK')
            raise
    return tot


def _staged(root, rel):
    r = subprocess.run(['git', '-C', str(root), 'show', f':{rel}'], capture_output=True, text=True, timeout=60)
    return r.stdout if r.returncode == 0 else None


def check_view(school, root=None, stores_dir=None, staged=None):
    """Problems of the JSON view of a store-sourced school (empty list: view == store). `staged`: set of repo-relative paths; only those are compared, from the git index."""
    root = code_root(root)
    out = []
    sp = store_path(school, stores_dir)
    if not sp.exists():
        return [f'{school}: flagged "store" but {sp} does not exist']
    text = rendered(school, stores_dir)
    with contextlib.closing(connect(sp)) as con:
        recorded = dict(con.execute('SELECT name, sha256 FROM layer WHERE scope = ?', ('school',)))
    d = school_dir(school, root)
    for name, t in sorted(text.items()):
        rel = str(Path('hierarchy') / school / 'reviewed' / name)
        if staged is not None and rel not in staged:
            continue
        if recorded.get(name) != sha(t):
            out.append(f'{school}/{name}: the store disagrees with its own layer hash (store edited outside evidence_store.py?)')
        have = _staged(root, rel) if staged is not None else (d / name).read_text() if (d / name).exists() else None
        if have is None:
            out.append(f'{rel}: missing from the view; run `evidence_store.py sync {school}`')
        elif have != t:
            out.append(f'{rel}: differs from the {school} evidence store. {school} is store-sourced (schools/{school}.toml [evidence] source = "store"): '
                       f'do NOT edit the JSON. Record the decision with `evidence_store.py record {school} --layer {name} ...`, then `evidence_store.py sync {school}`.')
    if shared_of(school) == 'store':
        for name, (cur, new) in shared_texts(school, root, stores_dir, staged).items():
            rel = f'hierarchy/reviewed/{name}'
            if staged is not None and rel not in staged:
                continue
            if cur is None:
                out.append(f'{rel}: missing; the {school} slice cannot be checked')
            elif cur != new:
                out.append(f'{rel}: the {school} slice differs from the {school} evidence store (schools/{school}.toml [evidence] shared = "store"): do NOT edit {school} rows '
                           f'in the shared file. Record the decision with `evidence_store.py record {school} --layer {name} ...`, then `evidence_store.py sync {school}`. '
                           f'Other schools\' rows stay editable.')
    if staged is None:
        for f in layer_files(d):
            if f.name not in text and not is_unmanaged(school, f.name):
                out.append(f'{school}/{f.name}: a reviewed file the store does not hold (the store is the source of truth; a new kind of reviewed file needs a layer added to the store by the coordinator): remove it')
    else:
        for rel in sorted(staged):
            if rel.startswith(f'hierarchy/{school}/reviewed/') and rel.endswith('.json') and Path(rel).name not in text and not is_unmanaged(school, Path(rel).name):
                out.append(f'{rel}: a reviewed file the {school} store does not hold (it is store-sourced); decisions go through `evidence_store.py record`')
    return out


# ---------------------------------------------------------------- backups: the stores are not in git and hold the decision history (write_log, superseded rows)

BACKUP_KEEP = 14
BACKUP_NAME = '-evidence.sqlite'


def backup_root(d=None):
    return Path(d or os.environ.get('CS_ATLAS_EVIDENCE_BACKUPS') or Path(P.ARCHIVE) / 'evidence-store-backups')


def backup_one(school, dest_dir, stores_dir=None):
    """sqlite online backup of one store into dest_dir/<school>-evidence.sqlite, then integrity_check on the copy. Returns (path, sha256, nbytes)."""
    sp = store_path(school, stores_dir)
    if not sp.exists():
        raise SourceOfTruth(f'{school}: no evidence store at {sp}')
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = dest_dir / f'{school}{BACKUP_NAME}'
    tmp = out.with_name(out.name + '.part')
    if tmp.exists():
        tmp.unlink()
    with contextlib.closing(connect(sp)) as src, contextlib.closing(sqlite3.connect(str(tmp), timeout=TIMEOUT)) as dst:
        src.backup(dst)
        res = dst.execute('PRAGMA integrity_check').fetchall()
        n = dst.execute('SELECT COUNT(*) FROM evidence').fetchone()[0]
        n_src = src.execute('SELECT COUNT(*) FROM evidence').fetchone()[0]
    if res != [('ok',)] or n != n_src:
        tmp.unlink()
        raise RuntimeError(f'{school}: backup failed its check (integrity_check {res[:2]}, rows {n} vs {n_src}); nothing kept')
    os.replace(tmp, out)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    return out, digest, out.stat().st_size


def backups_of(school, root=None):
    """[(stamp dir name, file)] of the school's backups, oldest first."""
    r = backup_root(root)
    if not r.is_dir():
        return []
    return [(d.name, d / f'{school}{BACKUP_NAME}') for d in sorted(r.iterdir()) if d.is_dir() and (d / f'{school}{BACKUP_NAME}').exists()]


def prune_backups(school, keep=BACKUP_KEEP, root=None):
    """Delete the school's backups beyond the newest `keep` (and their line in SHA256SUMS; an emptied stamp directory goes). Returns the number removed."""
    mine = backups_of(school, root)
    gone = mine[:-keep] if keep > 0 and len(mine) > keep else []
    for stamp, f in gone:
        d = f.parent
        f.unlink()
        sums = d / 'SHA256SUMS'
        if sums.exists():
            lines = [x for x in sums.read_text().splitlines() if not x.endswith(f.name)]
            sums.write_text('\n'.join(lines) + '\n' if lines else '')
        if not any(d.glob('*' + BACKUP_NAME)):
            for x in d.iterdir():
                x.unlink()
            d.rmdir()
    return len(gone)


def backup(schools=None, stores_dir=None, root=None, keep=BACKUP_KEEP, log=print):
    """Back up every flagged school (or `schools`) into <root>/<UTC stamp>/, write SHA256SUMS, prune to the newest `keep` per school. Returns {school: sha256}."""
    schools = list(schools) if schools else flagged()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    dest = backup_root(root) / stamp
    done = {}
    lines = []
    for s in schools:
        out, digest, n = backup_one(s, dest, stores_dir)
        lines.append(f'{digest}  {out.name}')   # run `sha256sum -c SHA256SUMS` inside the stamp directory
        done[s] = digest
        log(f'backup {s}: {out} ({n} bytes, integrity ok, sha256 {digest[:16]})')
    if lines:
        (dest / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')
    for s in schools:
        k = prune_backups(s, keep, root)
        if k:
            log(f'backup {s}: pruned {k} older than the newest {keep}')
    return done


def last_backup_age_h(school, root=None):
    b = backups_of(school, root)
    if not b:
        return None
    return (time.time() - b[-1][1].stat().st_mtime) / 3600


def backup_loop(stores_dir=None, root=None, keep=BACKUP_KEEP, every_h=24.0, poll_s=900, min_free_gb=50, once=False, log=print):
    """The daily backup job: every poll_s, back up each flagged school whose newest backup is older than every_h (or missing); skipped while the share has
    less than min_free_gb free. One JSON line per action."""
    while True:
        try:
            due = [s for s in flagged() if (last_backup_age_h(s, root) is None or last_backup_age_h(s, root) >= every_h)]
            if due:
                free = int(subprocess.run(['df', '-B1G', '--output=avail', str(P.ROOT)], capture_output=True, text=True, timeout=60, check=True).stdout.split()[-1])
                if free < min_free_gb:
                    log(json.dumps(dict(at=now(), skipped='low disk', free_gb=free, floor_gb=min_free_gb, due=due)))
                else:
                    done = backup(due, stores_dir, root, keep, log=lambda *_: None)
                    log(json.dumps(dict(at=now(), backed_up={s: h[:16] for s, h in done.items()})))
        except Exception as e:   # a failed backup must not kill the loop: it is retried at the next poll and shows in the log
            log(json.dumps(dict(at=now(), error=str(e)[:300])))
        if once:
            return 0
        time.sleep(poll_s)


def restore(school, from_file, stores_dir=None, force=False, log=print):
    """Restore a store from a backup file: verify the SHA256SUMS line (when present) and integrity_check, move the live store aside to <store>.pre-restore-<stamp>,
    copy the backup in. Refuses without --force while a live store exists whose write_log is longer than the backup's."""
    from_file = Path(from_file)
    sums = from_file.parent / 'SHA256SUMS'
    if sums.exists():
        want = [x.split()[0] for x in sums.read_text().splitlines() if x.endswith(from_file.name)]
        have = hashlib.sha256(from_file.read_bytes()).hexdigest()
        if want and want[0] != have:
            raise RuntimeError(f'{from_file}: sha256 differs from SHA256SUMS; not restoring')
    with contextlib.closing(connect(from_file)) as con:
        if con.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
            raise RuntimeError(f'{from_file}: integrity_check failed; not restoring')
    sp = store_path(school, stores_dir)
    if sp.exists():
        with contextlib.closing(connect(sp)) as live, contextlib.closing(connect(from_file)) as old:
            try:
                nl = live.execute('SELECT COUNT(*) FROM write_log').fetchone()[0]
            except sqlite3.OperationalError:
                nl = 0
            try:
                no = old.execute('SELECT COUNT(*) FROM write_log').fetchone()[0]
            except sqlite3.OperationalError:
                no = 0
        if nl > no and not force:
            raise SourceOfTruth(f'{school}: the live store has {nl} logged writes, the backup {no}; restoring loses {nl - no}. Pass --force to do it anyway (the live file is kept as .pre-restore-*)')
        aside = sp.with_name(sp.name + '.pre-restore-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
        os.replace(sp, aside)
        log(f'{school}: live store kept as {aside}')
    sp.parent.mkdir(parents=True, exist_ok=True)
    tmp = sp.with_name(sp.name + '.restore-tmp')
    shutil.copyfile(from_file, tmp)
    os.replace(tmp, sp)
    log(f'{school}: restored {sp} from {from_file}; then `evidence_store.py check {school}` and, if the view differs, `sync {school}`')
    return sp


def _find(con, layer, ident=None, entry_key=None, sub_key=None):
    q = 'SELECT e.id, e.container, e.seq, e.entry_key, e.sub_key, e.record FROM evidence e JOIN layer l ON l.layer_id = e.layer_id WHERE l.name = ?'
    a = [layer]
    if ident is not None:
        q += ' AND e.id = ?'
        a.append(ident)
    if entry_key is not None:
        q += ' AND e.entry_key = ?'
        a.append(entry_key)
    if sub_key is not None:
        q += ' AND e.sub_key = ?'
        a.append(sub_key)
    return con.execute(q + ' ORDER BY e.container, e.seq', a).fetchall()


def find(school, layer, key=None, text=None, stores_dir=None):
    """Rows of a layer whose entry key / person key equals `key`, or whose record contains `text`: [(id, container, seq, entry_key, sub_key, record dict)]."""
    sp = store_path(school, stores_dir)
    with contextlib.closing(connect(sp)) as con:
        rows = [(i, c, q, ek, sk, json.loads(r)) for i, c, q, ek, sk, r in _find(con, layer)]
    return [r for r in rows if (key is None or key in (r[3], r[4]) or key == (claim(layer, r[5], r[3], r[4])['person_key'])) and (text is None or text in json.dumps(r[5], ensure_ascii=False))]


def add_layer(school, layer, *, key=None, skeleton=None, shape='list', stores_dir=None, root=None):
    """Create an EMPTY school-scope layer in a store-sourced school's store (coordinator ruling 2026-11-19: a new kind of reviewed file).
    The layer is a list or map container: a root container (`key` None) or the container under top-level `key` of a dict
    whose other keys are the fixed `skeleton` (e.g. release-corrections.json: school, against_release, decided, pi_renames + `classes`). Rows are then
    added with `record` and the file written with `sync`; the dump style is the one import gives a new file (indent 1, newline). Raises SourceOfTruth
    for a json-sourced school, a missing store, or a layer that already exists."""
    if source_of(school) != 'store':
        raise SourceOfTruth(f'{school} is not store-sourced (schools/{school}.toml [evidence] source = "store"): create its reviewed JSON file by hand')
    sp = store_path(school, stores_dir)
    if not sp.exists():
        raise SourceOfTruth(f'{school}: no evidence store at {sp}')
    if not layer.endswith('.json') or '/' in layer:
        raise SourceOfTruth(f'{layer!r} is not a reviewed file name')
    if shape not in ('list', 'map'):
        raise SourceOfTruth(f'unsupported layer shape {shape!r}: use list or map')
    skeleton = dict(skeleton or {})
    if key is None and skeleton:
        raise SourceOfTruth('a root container has no skeleton: pass --container-key to put it under a key')
    if key is not None and key in skeleton:
        raise SourceOfTruth(f'the skeleton must not hold the container key {key!r}')
    empty = [] if shape == 'list' else {}
    doc = empty if key is None else {**skeleton, key: empty}
    sk = None if key is None else {**skeleton, key: None}
    conts = [dict(path=[] if key is None else [key], kind=shape)]
    text = dumps(doc, None)
    rel = str((school_dir(school, root) / layer).relative_to(code_root(root)))
    with contextlib.closing(connect(sp)) as con:
        create(con)
        con.execute('BEGIN IMMEDIATE')
        try:
            if con.execute('SELECT 1 FROM layer WHERE name = ? AND scope = ?', (layer, 'school')).fetchone():
                raise SourceOfTruth(f'{school}: layer {layer!r} already exists; record rows into it')
            con.execute('INSERT INTO layer (name, scope, skeleton, containers, key_order, style, sha256, nbytes, source_path, verbatim, layout_text) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                        (layer, 'school', None if sk is None else compact(sk), compact(conts), None if key is None else compact(list(sk)),
                         compact(dict(indent=1, ascii=False, compact=False, sort=False, newline=True)), sha(text), len(text.encode()), rel, None, None))
            con.execute('COMMIT')
        except BaseException:
            con.execute('ROLLBACK')
            raise
    return text


def record(school, layer, rec, *, source, decided_by, reviewed_by=None, supersede=None, entry_key=None, sub_key=None, container=None, note=None, stores_dir=None, shared=False):
    """Add (or supersede, `supersede` = the evidence id) one decision row of a store-sourced school. `rec` is the entry exactly as the reviewed file holds it
    (a list item, or the value of a map entry); `source` and `decided_by` are mandatory and logged in write_log. The claim columns are refreshed from the
    record, the layer hash follows the new rendering. Returns the evidence id. Raises SourceOfTruth for a school that is not store-sourced."""
    if source_of(school) != 'store':
        raise SourceOfTruth(f'{school} is not store-sourced (schools/{school}.toml [evidence] source = "store"): edit its reviewed JSON files instead')
    if shared and shared_of(school) != 'store':
        raise SourceOfTruth(f'{school}: its slices of the shared files are not store-sourced (schools/{school}.toml [evidence] shared = "store"); edit hierarchy/reviewed/{layer} instead')
    if not source or not decided_by:
        raise SourceOfTruth('a recorded decision needs --source and --decided-by')
    sp = store_path(school, stores_dir)
    if not sp.exists():
        raise SourceOfTruth(f'{school}: no evidence store at {sp}')
    with contextlib.closing(connect(sp)) as con:
        create(con)   # idempotent: adds write_log to a phase-1 store
        con.execute('BEGIN IMMEDIATE')
        try:
            lay = con.execute('SELECT layer_id, containers FROM layer WHERE name = ? AND scope = ?', (layer, 'shared' if shared else 'school')).fetchone()
            if not lay:
                raise SourceOfTruth(f'{school}: no layer {layer!r} in the store (names: {", ".join(r[0] for r in con.execute("SELECT name FROM layer WHERE scope = ? ORDER BY name", ("school",)))})')
            lid, conts = lay[0], json.loads(lay[1])
            c = claim(layer, rec, entry_key, sub_key)
            if supersede is not None:
                old = con.execute('SELECT id, container, seq, entry_key, sub_key, record FROM evidence WHERE id = ? AND layer_id = ?', (supersede, lid)).fetchone()
                if not old:
                    raise SourceOfTruth(f'{school}/{layer}: no decision row {supersede}')
                eid, ci, seq, ek, sk = old[0], old[1], old[2], old[3], old[4]
                c = claim(layer, rec, ek, sk)
                con.execute('UPDATE evidence SET record = ? WHERE id = ?', (compact(rec), eid))
            else:
                if container is None:
                    if len(conts) != 1:
                        raise SourceOfTruth(f'{layer} has {len(conts)} containers; pass --container N')
                    container = 0
                kind = conts[container]['kind']
                if kind == 'doc':
                    raise SourceOfTruth(f'{layer} is a whole-document row: supersede it (--supersede ID), there is nothing to add to')
                if kind == 'list' and (entry_key or sub_key):
                    raise SourceOfTruth(f'{layer} is a list: no --entry-key/--sub-key')
                if kind != 'list' and not entry_key:
                    raise SourceOfTruth(f'{layer} is a map: --entry-key is required' + (' (and --sub-key)' if kind == 'map2' else ''))
                if kind != 'list' and _find(con, layer, entry_key=entry_key, sub_key=sub_key if kind == 'map2' else None) and (kind == 'map' or sub_key):
                    raise SourceOfTruth(f'{layer}: entry {entry_key!r} exists; supersede it (find its id with `find`)')
                seq = (con.execute('SELECT MAX(seq) FROM evidence WHERE layer_id = ? AND container = ?', (lid, container)).fetchone()[0] or -1) + 1
                ci, ek, sk = container, entry_key, sub_key
                eid = con.execute('INSERT INTO evidence (school, layer_id, container, seq, entry_key, sub_key, person_key, claim_kind, facets, value, source_url, source_date, '
                                  'source_kind, decided_by, decided_at, reviewed_by, review_ref, supersedes, record) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                                  (school, lid, ci, seq, ek, sk, c['person_key'], c['claim_kind'], c['facets'], c['value'], c['source_url'], c['source_date'], c['source_kind'],
                                   c['decided_by'], c['decided_at'], c['reviewed_by'], c['review_ref'], c['supersedes'], compact(rec))).lastrowid
            # provenance of this write: columns the record does not carry are filled from the arguments (the record stays exactly the file's entry)
            con.execute('UPDATE evidence SET person_key = ?, claim_kind = ?, facets = ?, value = ?, source_url = ?, source_date = ?, source_kind = ?, '
                        'decided_by = COALESCE(?, ?), decided_at = COALESCE(?, ?), reviewed_by = COALESCE(?, ?), review_ref = ?, supersedes = ? WHERE id = ?',
                        (c['person_key'], c['claim_kind'], c['facets'], c['value'], c['source_url'] or (source if str(source).startswith('http') else None), c['source_date'], c['source_kind'],
                         c['decided_by'], decided_by, c['decided_at'], now(), c['reviewed_by'], reviewed_by, c['review_ref'],
                         c['supersedes'] or (f'evidence:{supersede}' if supersede is not None else None), eid))
            con.execute('INSERT INTO write_log (evidence_id, action, at, decided_by, reviewed_by, source, note, old_record) VALUES (?,?,?,?,?,?,?,?)',
                        (eid, 'supersede' if supersede is not None else 'add', now(), decided_by, reviewed_by, source, note, old[5] if supersede is not None else None))
            # the layer hash follows the rendering, so check_view tells a store edit made by this API from any other
            if not shared:   # a shared file's slice has no whole-file hash: check_view compares the patched file itself
                e = load_layers_con(con, sp)[layer]
                text = render(e)
                con.execute('UPDATE layer SET sha256 = ?, nbytes = ? WHERE layer_id = ?', (sha(text), len(text.encode()), lid))
            con.execute('COMMIT')
        except BaseException:
            con.execute('ROLLBACK')
            raise
    return eid


def load_layers_con(con, sp):
    """load_layers on an open connection (inside a write transaction, so it sees the uncommitted rows)."""
    out = {}
    for lid, name, scope, skel, conts, order, style, sh, nbytes, verb, layout in con.execute(
            'SELECT layer_id, name, scope, skeleton, containers, key_order, style, sha256, nbytes, verbatim, layout_text FROM layer'):
        rows = [(ci, seq, ek, sk, json.loads(rec)) for ci, seq, ek, sk, rec in con.execute('SELECT container, seq, entry_key, sub_key, record FROM evidence WHERE layer_id = ?', (lid,))]
        out[name] = dict(scope=scope, skeleton=None if skel is None else json.loads(skel), containers=json.loads(conts), order=None if order is None else json.loads(order),
                         style=None if style is None else json.loads(style), sha=sh, nbytes=nbytes, verbatim=verb, layout=layout, rows=rows, have_desc=True)
    return out


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
        elif source_of(school) == 'store':   # store-sourced: only the school's own files come from its store; the shared files stay the root's
            d = Path(tmp) / 'hierarchy' / school / 'reviewed'
            d.mkdir(parents=True)
            for name, text in rendered(school, stores_dir).items():
                (d / name).write_text(text)
            for f in layer_files(school_dir(school, root)):   # unmanaged files (tool-regenerated samples) are the root's own
                if is_unmanaged(school, f.name):
                    shutil.copyfile(f, d / f.name)
            if shared_of(school) == 'store':   # its slices of the shared files patched into the root's own copies
                (Path(tmp) / 'hierarchy' / 'reviewed').mkdir(parents=True)
                for f in layer_files(shared_dir(root)):   # the root's own shared files first (the unsliceable ones stay as they are), then the patched slices
                    shutil.copyfile(f, Path(tmp) / 'hierarchy' / 'reviewed' / f.name)
                for name, (cur, new) in shared_texts(school, root, stores_dir).items():
                    if new is not None:
                        (Path(tmp) / 'hierarchy' / 'reviewed' / name).write_text(new)
        else:
            export_files([store_path(s, stores_dir) for s in schools + [SHARED]], tmp)
        n = 0
        for src, rel in ((Path(tmp) / 'hierarchy' / school / 'reviewed', Path('hierarchy') / school / 'reviewed'), (Path(tmp) / 'hierarchy' / 'reviewed', Path('hierarchy') / 'reviewed')):
            for f in sorted(src.glob('*.json')) if src.is_dir() else []:
                dst = Path(out) / rel / f.name
                if dst.is_symlink() or dst.exists():
                    dst.unlink()
                shutil.copyfile(f, dst)
                n += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return n


def phase2(a, ap, root):
    if a.cmd == 'flagged':
        print('\n'.join(flagged()))
        return 0
    schools = a.schools or flagged()
    if a.cmd == 'backup':
        if a.loop:
            return backup_loop(a.store_dir, a.backup_dir, a.keep, every_h=a.every_h, once=a.once, log=lambda m: print(m, flush=True))
        try:
            backup(schools, a.store_dir, a.backup_dir, a.keep)
        except (SourceOfTruth, RuntimeError) as e:
            print(f'refused: {e}', file=sys.stderr)
            return 2
        return 0
    if a.cmd == 'restore':
        if len(schools) != 1 or not a.from_file:
            ap.error('restore takes one school and --from-file BACKUP.sqlite')
        try:
            restore(schools[0], a.from_file, a.store_dir, a.force)
        except (SourceOfTruth, RuntimeError) as e:
            print(f'refused: {e}', file=sys.stderr)
            return 2
        return 0
    if a.cmd == 'check':
        bad = 0
        staged = None
        if a.staged:
            staged = set(subprocess.run(['git', '-C', str(root), 'diff', '--cached', '--name-only', '--diff-filter=ACMRD'], capture_output=True, text=True, timeout=60).stdout.split())
        for s in schools:
            if source_of(s) != 'store':
                print(f'{s}: json-sourced (nothing to check)')
                continue
            if staged is not None and not any(x.startswith(f'hierarchy/{s}/reviewed/') or (x.startswith('hierarchy/reviewed/') and shared_of(s) == 'store') for x in staged):
                continue
            probs = check_view(s, root, a.store_dir, staged)
            bad += len(probs)
            print('\n'.join(probs) if probs else f'{s}: the JSON view matches the store ({len(rendered(s, a.store_dir))} files)')
        return 1 if bad else 0
    if len(schools) != 1:
        ap.error(f'{a.cmd} takes one school')
    s = schools[0]
    try:
        if a.cmd == 'sync':
            if source_of(s) != 'store':
                ap.error(f'{s} is not store-sourced')
            ch = sync(s, root, a.store_dir)
            sh = sync_shared(s, root, a.store_dir) if shared_of(s) == 'store' else []
            print(f'{s}: {len(ch)} reviewed files rewritten from the store' + (': ' + ', '.join(ch) if ch else '') + (f'; shared files patched (its slice only): {", ".join(sh) or "none changed"}' if shared_of(s) == 'store' else ''))
            return 0
        if a.cmd == 'add-layer':
            if not a.layer or a.shape not in ('list', 'map'):
                ap.error('add-layer needs --layer NAME.json and --shape list|map')
            add_layer(s, a.layer, key=a.container_key, skeleton=json.loads(a.skeleton) if a.skeleton else None, shape=a.shape, stores_dir=a.store_dir, root=root)
            print(f'{s}/{a.layer}: empty {a.shape} layer created in the store; record rows with `record`, then `sync` writes the file')
            return 0
        if a.cmd == 'adopt-shared':
            n = adopt_shared(s, root, a.store_dir)
            print(f'{s}: {n} rows of its slices of the shared files are now in its store; set [evidence] shared = "store" in the charter in the same commit once the build proof passes')
            return 0
        if not a.layer:
            ap.error('--layer')
        if a.cmd == 'find':
            for i, c, q, ek, sk, rec in find(s, a.layer, a.key, a.text, a.store_dir):
                print(json.dumps(dict(id=i, container=c, seq=q, entry_key=ek, sub_key=sk, record=rec), ensure_ascii=False))
            return 0
        text = a.record if a.record is not None else Path(a.record_file).read_text() if a.record_file else None
        if text is None:
            ap.error('--record or --record-file')
        eid = record(s, a.layer, json.loads(text), shared=a.shared, source=a.source, decided_by=a.decided_by, reviewed_by=a.reviewed_by, supersede=a.supersede,
                     entry_key=a.entry_key, sub_key=a.sub_key, container=a.container, note=a.note, stores_dir=a.store_dir)
        print(f'{s}/{a.layer}: decision row {eid} {"superseded" if a.supersede is not None else "added"}')
        if not a.no_sync:
            ch = sync(s, root, a.store_dir) + (sync_shared(s, root, a.store_dir) if a.shared and shared_of(s) == 'store' else [])
            print(f'JSON view rewritten under {school_dir(s, root)}: {", ".join(ch) or "nothing changed"}; commit it on your branch (hook: hierarchy/{s}/reviewed is a store export)')
        return 0
    except SourceOfTruth as e:
        print(f'refused: {e}', file=sys.stderr)
        return 2


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['import', 'export', 'verify', 'overlay', 'coverage', 'flagged', 'find', 'record', 'sync', 'check', 'backup', 'restore', 'adopt-shared', 'add-layer'])
    ap.add_argument('schools', nargs='*')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--store-dir', help='default $CS_ATLAS_EVIDENCE_DIR or the stores dir')
    ap.add_argument('--out')
    ap.add_argument('--root', help='code root to read the reviewed files from (default CS_ATLAS_CODE)')
    ap.add_argument('--json', help='write the report here')
    ap.add_argument('--control', action='store_true', help='overlay: copy the root\'s own reviewed files instead of the exported ones')
    ap.add_argument('--layer', help='find/record: the reviewed file name, e.g. census-additions.json')
    ap.add_argument('--key', help='find: entry key or person name')
    ap.add_argument('--text', help='find: substring of the record')
    ap.add_argument('--record', help='record: the entry as JSON (exactly as the reviewed file holds it)')
    ap.add_argument('--record-file', help='record: a file holding that JSON')
    ap.add_argument('--supersede', type=int, metavar='ID', help='record: replace the row with this evidence id (from `find`)')
    ap.add_argument('--entry-key', help='record, map layers: the new entry\'s key')
    ap.add_argument('--sub-key', help='record, school-keyed maps: the inner key')
    ap.add_argument('--container', type=int)
    ap.add_argument('--shape', choices=['list', 'map'], help='add-layer: the new layer is a list or person-keyed map container')
    ap.add_argument('--container-key', help='add-layer: the container sits under this top-level key (default: a root container)')
    ap.add_argument('--skeleton', help='add-layer, with --container-key: the other top-level keys of the file as JSON')
    ap.add_argument('--source', help='record: URL or file reference supporting the decision')
    ap.add_argument('--decided-by')
    ap.add_argument('--reviewed-by')
    ap.add_argument('--note')
    ap.add_argument('--shared', action='store_true', help='find/record: the layer is a shared reviewed file (hierarchy/reviewed/<name>); needs [evidence] shared = "store"')
    ap.add_argument('--no-sync', action='store_true', help='record: do not rewrite the JSON view afterwards')
    ap.add_argument('--staged', action='store_true', help='check: compare the git-index content of the staged reviewed files (pre-commit)')
    ap.add_argument('--backup-dir', help='backup/restore: default <archive>/evidence-store-backups')
    ap.add_argument('--keep', type=int, default=BACKUP_KEEP, help='backup: newest N per school kept (default 14)')
    ap.add_argument('--loop', action='store_true', help='backup: the daily job (back up what is older than --every-h, poll every 15 min)')
    ap.add_argument('--once', action='store_true', help='backup --loop: one pass')
    ap.add_argument('--every-h', type=float, default=24.0)
    ap.add_argument('--from-file', help='restore: the backup file')
    ap.add_argument('--force', action='store_true', help='restore: even when the live store has more logged writes')
    a = ap.parse_args(argv)
    root = code_root(a.root)
    if a.cmd in ('flagged', 'find', 'record', 'sync', 'check', 'backup', 'restore', 'adopt-shared', 'add-layer'):
        # the JSON view is code: write and compare the checkout this tool runs from (your worktree), never the main checkout by accident
        return phase2(a, ap, Path(a.root) if a.root else Path(__file__).resolve().parents[1])
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
