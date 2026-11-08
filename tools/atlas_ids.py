"""Stable atlas ids for people, works and labs (2026-10-29, owner; docs/IDS.md, rules R-ID-01..05).

  atl:p:<12 hex>            a person (PI or student), one id across labs and schools
  atl:w:<12 hex>            a work (a unique paper; editions share it), one id across labs and schools
  atl:l:<school>:<pi-slug>  a PI lab (one per PI and school)

Ids are opaque and deterministic: an entity's anchors (identifiers) are ranked, and a new id is the sha256 of its strongest
anchor. Once issued an id never changes: the registry (hierarchy/ids/registry.sqlite) retains every anchor's history,
and a later build finds an entity's id through its active anchors, so a new ORCID or DOI joins the existing id.
An explicitly retired corrupt work identifier remains in audited history and cannot resolve or be reused as an active anchor.
Two issued ids that turn out to be one entity are merged by a redirect (the earlier-issued id stays; the other is kept in
the registry with status 'redirect', never reissued).

Anchors (strongest first)
  person  orcid:<id> | openalex:<A id> (reviewed for a PI; for a student, a byline author id that is a PI's reviewed id,
          with a compatible name) | dblp:<pid> | coll:<school>:<collection person id> | name:<school>:<name>:<evidence url>
  work    doi:<doi> (not arXiv) | openalex:<W id> | dblp:<key> | arxiv:<id> | coll:<school>:<collection work> | labpage:<sha1>
  lab     lab:<school>:<person atlas id>
Name anchors are a fallback for records with no identifier (ext: students); they carry the evidence url, so the same name
on two different pages never joins two records (R-HIER-03: a name alone never makes one person across labs). A join by
an identifier between two people whose family names differ is refused and reported (conflicts).

Writes the ids into the packages in place (hierarchy/<school>/):
  pis.json            atlasId, labId, appointments (every school where this person is a PI, with the lab id)
  students.json       atlasId (and alsoPi: the PI appointments of a student who is faculty in the atlas)
  lab_papers.jsonl.gz atlasWorkId
  student_papers.jsonl.gz  studentAtlasId, atlasWorkId, labId
and hierarchy/ids/: registry.sqlite, crossref.tsv.gz (atlas id <-> OpenAlex, DBLP, ORCID, DOI, arXiv, collection ids,
legacy ids), redirects.tsv, persons-cross-school.json, IDS-REPORT.json.
A missing registry is seeded from releases/latest/hierarchy/ids/registry.sqlite.
usage: atlas_ids.py [--registry PATH] [--dir HIERARCHY] [--no-sweep] [school ...]   (default: every released school)
"""
import argparse, collections, csv, gzip, hashlib, io, json, os, re, runpy, shutil, sqlite3, sys, tempfile, unicodedata, zlib
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit

if __name__ == '__main__' and sys.flags.isolated:
    # Reuse the existing allowlisted entrypoint; downloaded reviews never add the caller's cwd to imports.
    runpy.run_path(str(Path(__file__).with_name('pi_hierarchy.py')), run_name='atlas_ids_bootstrap')

import atlas_paths as P  # noqa: E402  (every path in one place)

RANK = {'orcid': 0, 'openalex': 1, 'dblp': 2, 'coll': 3, 'name': 4,                                   # people
        'doi': 0, 'oaw': 1, 'dblpkey': 2, 'arxiv': 3, 'collw': 4, 'labpage': 5}                     # works
STRONG_PERSON = {'orcid', 'openalex', 'dblp'}
WSCHEME = {'doi': 'doi', 'oaw': 'openalex', 'dblpkey': 'dblp', 'arxiv': 'arxiv', 'collw': 'coll', 'labpage': 'labpage'}
SEP = '\x1f'


# ---------------------------------------------------------------- normalizers

def fold(s):
    s = unicodedata.normalize('NFKD', str(s or '')); s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.translate(str.maketrans({'ı': 'i', 'ł': 'l', 'Ł': 'l', 'ø': 'o', 'Ø': 'o', 'đ': 'd', 'ß': 'ss', 'æ': 'ae'})).lower()


def nname(s):
    s = fold(s)
    if ',' in s:  # 'Family, Given'
        a, b = s.split(',', 1); s = b + ' ' + a
    return '-'.join(re.findall(r'[a-z0-9]+', s))


def slug(s):  # as tools/export_release.py and tools/organize_tree.py
    s = unicodedata.normalize('NFKD', str(s)); s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def name_toks(s):
    s = fold(s)
    if ',' in s:
        a, b = s.split(',', 1); s = b + ' ' + a
    t = [x for x in re.findall(r'[a-z]+', s) if x not in {'jr', 'sr', 'ii', 'iii', 'iv', 'dr', 'prof'}]
    return t


def family(s):
    t = name_toks(s)
    return t[-1] if t else ''


def compatible(a, b, nick=None):
    """Two forms of one person's name: the same family name and the same first full given name (or a nickname pair).
    Initials never count."""
    ta, tb = name_toks(a), name_toks(b)
    if not ta or not tb or ta[-1] != tb[-1]:
        return False
    ga = [x for x in ta[:-1] if len(x) > 1]; gb = [x for x in tb[:-1] if len(x) > 1]
    if not ga or not gb:
        return False
    if set(ga) & set(gb):
        return True
    return bool(nick) and any(nick(x, y) for x in ga for y in gb)


def norm_orcid(o):
    m = re.search(r'(\d{4}-\d{4}-\d{4}-\d{3}[\dXx])', str(o or ''))
    return m.group(1).upper() if m else None


def norm_oa(o, kind='A'):
    m = re.search(rf'\b({kind}\d+)\b', str(o or ''))
    return m.group(1) if m else None


def norm_dblp_pid(u):
    u = str(u or '')
    m = re.search(r'dblp\.org/pid/(.+?)(?:\.html|\.xml)?$', u) or re.match(r'^(?:pid/)?([a-z0-9]+/[\w-]+)$', u)
    return m.group(1) if m else None


def norm_dblp_key(u):
    u = str(u or '')
    while u.startswith('https://dblp.org/rec/'):
        u = u[len('https://dblp.org/rec/'):]
    return u if re.match(r'^(conf|journals|books|series|phd|reference|tr|persons|informal)/', u) else None


def norm_doi(d):
    d = str(d or '').strip().lower()
    d = re.sub(r'^(?:doi:|https?://(?:dx\.)?doi\.org/)', '', d)
    return d if d.startswith('10.') else None


def arxiv_of(doi):
    m = re.match(r'^10\.48550/arxiv\.(.+)$', doi or '')
    return re.sub(r'v\d+$', '', m.group(1)) if m else None


# ---------------------------------------------------------------- anchors

def work_anchors(r, school):
    """The anchors of one lab-paper row (and its editions)."""
    out = set()
    for x in [r] + list(r.get('editions') or []):
        oa = str(x.get('oa') or ''); w = str(x.get('work') or '')
        for d in (x.get('doi'), w[4:] if w.startswith('doi:') else None):
            d = norm_doi(d)
            if d:
                out.add(('arxiv', arxiv_of(d)) if arxiv_of(d) else ('doi', d))
        if w.startswith('arxiv:'):
            out.add(('arxiv', re.sub(r'v\d+$', '', w[6:])))
        if oa.startswith('https://openalex.org/') and norm_oa(oa, 'W'):
            out.add(('oaw', norm_oa(oa, 'W')))
        elif oa.startswith('https://dblp.org/rec/') and norm_dblp_key(oa):
            out.add(('dblpkey', norm_dblp_key(oa)))
        elif oa.startswith('labpage:'):
            out.add(('labpage', oa[8:]))
        if w and not re.match(r'^(doi:|arxiv:|https?:|labpage:)', w):
            out.add(('collw', f'{school}:{w}'))
    return out


def person_anchor_str(k, v):
    return f'p|{k}:{v}'


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        p = self.p
        p.setdefault(x, x)
        while p[x] != x:
            p[x] = p[p[x]]; x = p[x]
        return x

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            if b < a:
                a, b = b, a
            self.p[b] = a


# ---------------------------------------------------------------- registry

SCHEMA = """
create table if not exists ids (id text primary key, kind text not null, minted_from text not null, issued text not null,
                                status text not null default 'active', redirect_to text, note text);
create table if not exists anchors (anchor text primary key, id text not null, kind text not null, first_seen text not null);
create table if not exists meta (k text primary key, v text);
"""


def open_registry(path, seed=True):
    path = Path(path)
    if not path.exists() and seed:
        rel = P.RELEASES / 'latest' / P.REL_HIERARCHY / 'ids' / 'registry.sqlite'
        if rel.exists():
            path.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(rel, path); path.chmod(0o644)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=120)
    db.executescript(SCHEMA)
    return db


def registry_fingerprint(db):
    """Logical preimage of the complete registry, including schema and every user table, independent of backup headers."""
    schema = db.execute("select type,name,tbl_name,sql from sqlite_master where name not glob 'sqlite_*' order by type,name").fetchall()
    encode = lambda v: json.dumps(v, ensure_ascii=False, separators=(',', ':'), default=lambda b: {'blob_hex': b.hex()}).encode()
    quote = lambda s: '"' + s.replace('"', '""') + '"'
    tables = {}
    for (name,) in db.execute("select name from sqlite_master where type='table' and name not glob 'sqlite_*' order by name"):
        columns = [r[1] for r in db.execute('pragma table_info(' + quote(name) + ')')]
        h, count = hashlib.sha256(), 0
        for row in db.execute('select * from ' + quote(name) + ' order by ' + ','.join(map(quote, columns))):
            h.update(encode(row) + b'\n'); count += 1
        tables[name] = dict(rows=count, sha256=h.hexdigest())
    return dict(schema_sha256=hashlib.sha256(encode(schema)).hexdigest(), tables=tables)


def retired_work_anchors(db):
    if not db.execute("select 1 from sqlite_master where type='table' and name='retired_work_anchors'").fetchone():
        return {}
    return dict(db.execute('select anchor,review_id from retired_work_anchors'))


def _check_retired_work_anchors(db, comps):
    retired = retired_work_anchors(db)
    holds = [dict(component=str(c), anchors=[a for _, a in anchors],
                  retired_anchors=[a for _, a in anchors if a in retired],
                  retirement_reviews={a: retired[a] for _, a in anchors if a in retired},
                  reason='retired work anchor requires explicit source review')
             for c, anchors in comps.items() if any(a in retired for _, a in anchors)]
    if holds:
        raise WorkIDConflict(holds)


_ANCHOR_COLUMNS = ('anchor', 'id', 'kind', 'first_seen')
_ID_COLUMNS = ('id', 'kind', 'minted_from', 'issued', 'status', 'redirect_to', 'note')
_RETIREMENT_DDL = (
    '''create table if not exists retired_work_anchors (
       anchor text primary key, id text not null, kind text not null check(kind='work'), first_seen text not null,
       retired_at text not null, review_id text not null, review_sha256 text not null,
       source_registry_sha256 text not null, review_json text not null)''',
    '''create trigger if not exists retired_anchor_no_insert before insert on anchors
       when exists(select 1 from retired_work_anchors where anchor=new.anchor)
       begin select raise(abort, 'retired work anchor cannot become active'); end''',
    '''create trigger if not exists retired_anchor_no_update before update on anchors
       when exists(select 1 from retired_work_anchors where anchor=new.anchor)
       begin select raise(abort, 'retired work anchor cannot become active'); end''',
    '''create trigger if not exists retired_anchor_history_no_update before update on retired_work_anchors
       begin select raise(abort, 'retired anchor history is immutable'); end''',
    '''create trigger if not exists retired_anchor_history_no_delete before delete on retired_work_anchors
       begin select raise(abort, 'retired anchor history is immutable'); end''',
)


def _retirement_review(review):
    if not isinstance(review, dict) or review.get('version') != 1 or review.get('action') != 'retire_work_anchors':
        raise ValueError('work anchor retirement needs version 1 and an explicit action')
    for k in ('id', 'reviewed_by', 'reviewed_at', 'reason'):
        if not isinstance(review.get(k), str) or not review[k].strip():
            raise ValueError('work anchor retirement needs reviewer, date, id and reason')
    if datetime.strptime(review['reviewed_at'], '%Y-%m-%d').strftime('%Y-%m-%d') != review['reviewed_at']:
        raise ValueError('retirement review date must be YYYY-MM-DD')
    if not re.fullmatch('[0-9a-f]{64}', str(review.get('source_registry_sha256') or '')):
        raise ValueError('work anchor retirement needs the physical source registry hash')
    if not isinstance(review.get('expected_registry'), dict):
        raise ValueError('work anchor retirement needs a complete logical registry preimage')
    evidence = review.get('evidence')
    if not isinstance(evidence, list) or not evidence or any(
            not isinstance(e, dict) or not re.match(r'https?://', str(e.get('url') or ''))
            or not re.fullmatch('[0-9a-f]{64}', str(e.get('sha256') or ''))
            or not isinstance(e.get('quote'), str) or not e['quote'].strip() for e in evidence):
        raise ValueError('work anchor retirement needs original URL, SHA256 and quoted evidence')
    rows = review.get('retirements')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError('work anchor retirement needs 1-100 exact anchor preimages')
    seen = set()
    for row in rows:
        a, i = (row.get('expected_anchor'), row.get('expected_id')) if isinstance(row, dict) else (None, None)
        if not isinstance(a, dict) or set(a) != set(_ANCHOR_COLUMNS) or not isinstance(i, dict) or set(i) != set(_ID_COLUMNS) \
                or a['kind'] != 'work' or i['kind'] != 'work' or a['id'] != i['id'] \
                or not re.fullmatch(r'atl:w:[0-9a-f]{12}', str(i['id'])) \
                or not re.fullmatch(r'w\|(?:doi|openalex|dblp|arxiv|coll|labpage):[^\s]+', str(a['anchor'])) \
                or a['anchor'] in seen:
            raise ValueError('invalid, non-work or duplicate anchor retirement preimage')
        seen.add(a['anchor'])
    text = json.dumps(review, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return text, hashlib.sha256(text.encode()).hexdigest()


def _retirement_state(db, review, review_hash):
    retired = retired_work_anchors(db); already = []
    for row in review['retirements']:
        expected = row['expected_anchor']; anchor = expected['anchor']
        actual = db.execute('select ' + ','.join(_ANCHOR_COLUMNS) + ' from anchors where anchor=?', (anchor,)).fetchone()
        if anchor in retired:
            history = db.execute('select anchor,id,kind,first_seen,review_sha256 from retired_work_anchors where anchor=?', (anchor,)).fetchone()
            if actual or history[:4] != tuple(expected[k] for k in _ANCHOR_COLUMNS) or history[4] != review_hash:
                raise ValueError('conflicting or resurrected retired anchor: ' + anchor)
            already.append(anchor); continue
        if actual != tuple(expected[k] for k in _ANCHOR_COLUMNS):
            raise ValueError('active anchor preimage mismatch: ' + anchor)
        actual_id = db.execute('select ' + ','.join(_ID_COLUMNS) + ' from ids where id=?', (expected['id'],)).fetchone()
        if actual_id != tuple(row['expected_id'][k] for k in _ID_COLUMNS):
            raise ValueError('issued ID preimage mismatch: ' + anchor)
    if already and len(already) != len(review['retirements']):
        raise ValueError('partial retirement state; source review required')
    if not already and registry_fingerprint(db) != review['expected_registry']:
        raise ValueError('complete registry preimage mismatch')
    return bool(already)


def retire_work_anchors(registry, review, backup=None, write=False):
    """Offline, exact-source retirement on a copied registry. Dry run by default; writes require a fresh whole backup.

    The public registry is replaced atomically only after its full preimage is rechecked. Issued IDs are never changed.
    Retired keys remain in immutable history and cannot be used by assignment or active cross-reference exports.
    """
    text, review_hash = _retirement_review(review); registry = Path(registry)
    def file_hash(p):
        with open(p, 'rb') as source:
            return hashlib.file_digest(source, 'sha256').hexdigest()
    source_hash = file_hash(registry)
    src = sqlite3.connect('file:' + str(registry) + '?mode=ro', uri=True, timeout=120)
    try:
        src.execute('begin'); already = _retirement_state(src, review, review_hash); before = registry_fingerprint(src)
        result = dict(status='already_retired' if already else 'planned', review_id=review['id'], review_sha256=review_hash,
                      source_registry_sha256=source_hash, registry_before=before,
                      anchors=[r['expected_anchor'] for r in review['retirements']], issued_ID_changes=0)
        if already:
            return result
        if source_hash != review['source_registry_sha256']:
            raise ValueError('physical registry preimage mismatch')
        if not write:
            return result
        if backup is None:
            raise ValueError('retirement write requires a new whole-registry backup path')
        backup = Path(backup)
        if backup.resolve() == registry.resolve() or backup.exists() or backup.is_symlink():
            raise ValueError('retirement backup must be a new file separate from the registry')
        backup.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents an existing receipt/backup from being overwritten.
        with backup.open('xb'):
            pass
        copied = sqlite3.connect(str(backup))
        try:
            src.backup(copied)
            if registry_fingerprint(copied) != before:
                raise ValueError('whole-registry backup preimage mismatch')
        finally:
            copied.close()
    finally:
        src.close()
    local = Path(tempfile.mkdtemp(prefix='atlas-anchor-retirement-', dir=os.environ.get('ATLAS_IDS_LOCAL_DIR') or tempfile.gettempdir()))
    try:
        candidate = local / 'registry.sqlite'; shutil.copy2(backup, candidate); db = sqlite3.connect(str(candidate))
        try:
            db.execute('begin immediate'); _retirement_state(db, review, review_hash)
            for ddl in _RETIREMENT_DDL:
                db.execute(ddl)
            for row in review['retirements']:
                a = row['expected_anchor']
                n = db.execute('delete from anchors where anchor=? and id=? and kind=? and first_seen=?', tuple(a[k] for k in _ANCHOR_COLUMNS)).rowcount
                if n != 1:
                    raise ValueError('anchor changed during retirement: ' + a['anchor'])
                db.execute('insert into retired_work_anchors values (?,?,?,?,?,?,?,?,?)',
                           tuple(a[k] for k in _ANCHOR_COLUMNS) + (review['reviewed_at'], review['id'], review_hash, source_hash, text))
            after = registry_fingerprint(db)
            if before['tables']['ids'] != after['tables']['ids']:
                raise ValueError('retirement must not change any issued ID')
            db.commit()
        except BaseException:
            db.rollback(); raise
        finally:
            db.close()
        # Like normal ID preparation, replacement is serialized by the owner; also reject a changed source preimage.
        check = sqlite3.connect('file:' + str(registry) + '?mode=ro', uri=True, timeout=120)
        try:
            check.execute('begin')
            if file_hash(registry) != source_hash or registry_fingerprint(check) != before or file_hash(registry) != source_hash:
                raise ValueError('registry changed while retirement was prepared')
        finally:
            check.close()
        fd, name = tempfile.mkstemp(prefix='.' + registry.name + '.retire-', dir=registry.parent); os.close(fd)
        temporary = Path(name)
        try:
            shutil.copy2(candidate, temporary); temporary.chmod(registry.stat().st_mode & 0o777); os.replace(temporary, registry)
        finally:
            temporary.unlink(missing_ok=True)
        result.update(status='retired', registry_after=after, prepared_registry_sha256=file_hash(registry),
                      backup=str(backup), backup_sha256=file_hash(backup), active_crossrefs_must_be_regenerated=True)
        return result
    finally:
        shutil.rmtree(local, ignore_errors=True)


def resolve(db, i):
    seen = set()
    while i and i not in seen:
        seen.add(i)
        row = db.execute('select status, redirect_to from ids where id=?', (i,)).fetchone()
        if not row or row[0] != 'redirect':
            return i
        i = row[1]
    return i


def mint(db, prefix, anchor, kind, today, taken):
    n = 0
    while True:
        h = hashlib.sha256((anchor + ('' if n == 0 else f'#{n}')).encode()).hexdigest()[:12]
        i = f'{prefix}{h}'
        if i not in taken and not db.execute('select 1 from ids where id=?', (i,)).fetchone():
            db.execute('insert into ids (id, kind, minted_from, issued) values (?,?,?,?)', (i, kind, anchor, today))
            taken.add(i)
            return i
        n += 1


def assign(db, kind, prefix, comps, today, stats):
    """comps: {component key: sorted list of (rank, anchor string)}. Returns {component key: id}. Deterministic: components are
    processed in the order of their strongest anchor; a registry hit wins; several hits merge into the earliest issued."""
    out = {}
    taken = set()
    # an anchor held by two components (two rows of one lab the builder keeps apart behind one OpenAlex record; a join
    # refused for differing family names) is ambiguous: it never finds or merges ids, and it is never registered; it is
    # used only to recognise the id that was minted from it
    cnt = collections.Counter(a for c in comps for _, a in comps[c])
    amb = {a for a, n in cnt.items() if n > 1}
    stats['ambiguous_anchors'] += len(amb)
    if kind == 'work':
        _check_retired_work_anchors(db, comps)
        holds = [dict(component=str(c), anchors=[a for _, a in comps[c]],
                      reason='source-distinct work has no unambiguous identifier')
                 for c in comps if not any(a not in amb for _, a in comps[c])]
        if holds:
            raise WorkIDConflict(holds)
    order = sorted(comps, key=lambda c: (comps[c], str(c)))
    claims = collections.defaultdict(list)
    issued = lambda i: (db.execute('select issued from ids where id=?', (i,)).fetchone() or ('9',))[0] + i
    for c in order:
        own = [a for _, a in comps[c] if a not in amb]
        hits = set()
        for a in own:
            row = db.execute('select id from anchors where anchor=?', (a,)).fetchone()
            if row:
                hits.add(resolve(db, row[0]))
        if not hits:
            mine = {a for _, a in comps[c]}
            for a in mine & amb:
                row = db.execute('select id from anchors where anchor=?', (a,)).fetchone()
                if row:
                    i = resolve(db, row[0]); mf = db.execute('select minted_from from ids where id=?', (i,)).fetchone()
                    if mf and mf[0] in mine:
                        hits.add(i)
        hits = sorted(hits, key=issued)
        if hits:
            keep = hits[0]
            for other in hits[1:]:
                db.execute("update ids set status='redirect', redirect_to=? where id=?", (keep, other))
                db.execute('update anchors set id=? where id=?', (keep, other))
                stats['redirects_new'] += 1
            claims[keep].append(c)
        else:
            out[c] = mint(db, prefix, (own or [a for _, a in comps[c]])[0], kind, today, taken); stats['minted'] += 1
    for i, cs in claims.items():  # one id claimed by several components (an entity that the data now splits)
        if len(cs) == 1:
            out[cs[0]] = i; stats['reused'] += 1; continue
        mf = db.execute('select minted_from from ids where id=?', (i,)).fetchone()[0]
        keeper = next((c for c in cs if mf in {a for _, a in comps[c]}), cs[0])
        for c in cs:
            if c == keeper:
                out[c] = i; stats['reused'] += 1
            else:
                out[c] = mint(db, prefix, ([a for _, a in comps[c] if a not in amb] or [comps[c][0][1]])[0], kind, today, taken); stats['split_minted'] += 1
    for c, i in out.items():
        for _, a in comps[c]:
            if a in amb:
                continue
            row = db.execute('select id from anchors where anchor=?', (a,)).fetchone()
            if row is None:
                db.execute('insert into anchors (anchor, id, kind, first_seen) values (?,?,?,?)', (a, i, kind, today))
            elif resolve(db, row[0]) != i and (kind == 'work' or len(claims.get(resolve(db, row[0]), [])) <= 1):
                # A work split retains only this component's unambiguous lead anchors. Register its own source key
                # with the newly minted work ID, even when the old ID covered several components. Otherwise every
                # replay finds that old ID again and mints another orphan. Shared/ambiguous DOI anchors stay untouched.
                split_work = kind == 'work' and len(claims.get(resolve(db, row[0]), [])) > 1
                db.execute('update anchors set id=? where anchor=?', (i, a))
                if split_work:
                    stats['split_work_anchors_rebound'] += 1
    return out


# ---------------------------------------------------------------- reading

def load_school(D):
    pis = json.loads((D / 'pis.json').read_text())
    stu = json.loads((D / 'students.json').read_text())
    rows = [json.loads(l) for l in gzip.open(D / 'lab_papers.jsonl.gz', 'rt')]
    sp = [json.loads(l) for l in gzip.open(D / 'student_papers.jsonl.gz', 'rt')]
    return pis, stu, rows, sp


def student_urls(r):
    return sorted({q.get('url') for rel in r.get('relations') or [] for q in rel.get('sources') or [] if q.get('url')})


COADVISED = re.compile(r'\bco[-\s]?(?:advised|supervised)\s*(?:with\b|by\b|w/)\s*', re.I)
COADVISED_MENTION = re.compile(r'\bco[-\s]?(?:advis|supervis)', re.I)
STUDENT_DESCRIPTORS = {'phd', 'ph', 'd', 'student', 'master', 'masters', 'msc', 'ms', 'm', 's', 'sc',
                       'undergraduate', 'fall', 'spring', 'summer', 'autumn', 'since', 'from', 'present', 'started'}
COADVISED_PREFIX = STUDENT_DESCRIPTORS | {'is', 'was', 'are', 'were', 'not', 'never', 'no', 'longer', 'without',
                                      'currently', 'also', 'jointly', 'former', 'current', 'has', 'have', 'had', 'been', 'be', 'as'}


class CoadvisingIDConflict(ValueError):
    """Source-backed external memberships need review before any registry/package writes."""
    def __init__(self, holds):
        self.holds = holds
        super().__init__('Co-advising ID preparation held: ' + '; '.join(
            h['school'] + '/' + h['native_person'] + ': ' + h['reason'] for h in holds))


class WorkIDConflict(ValueError):
    """The scientific rows remain separate but cannot yet be assigned stable, source-bound work identities."""
    def __init__(self, holds):
        self.holds = holds
        super().__init__('Work ID preparation held: ' + '; '.join(h['reason'] + ': ' + h['component'] for h in holds))


def _coadvising_text_toks(text):
    # Prose commas separate clauses; unlike a standalone person's name, they never reverse the text.
    return [w for w in re.findall(r'[a-z]+', fold(text)) if w not in {'dr', 'prof', 'professor'}]


def _contains_name(tokens, name):
    return any(tokens[i:i + len(name)] == name for i in range(len(tokens) - len(name) + 1))


def _student_before_coadvising(prefix, names):
    tokens = _coadvising_text_toks(prefix)
    for name in names:
        words = name_toks(name)
        if len(words) < 2 or not any(len(w) > 1 for w in words[:-1]):
            continue
        for i in range(len(tokens) - len(words) + 1):
            if tokens[i:i + len(words)] == words and set(tokens[i + len(words):]) <= STUDENT_DESCRIPTORS:
                return True
    return False


def student_coadvising_clauses(quote, names):
    """Exact source spans for this student's clauses, including negated ones; roster boilerplate is not a clause."""
    words = [(fold(m.group()), m.start(), m.end()) for m in re.finditer(r'[^\W\d_]+', quote, re.UNICODE)
             if fold(m.group()) not in {'dr', 'prof', 'professor'}]
    clauses = []
    for mention in COADVISED_MENTION.finditer(quote):
        before = [w for w in words if w[2] <= mention.start()]
        tokens = [w[0] for w in before]
        starts = []
        for name in names:
            nw = name_toks(name)
            if len(nw) < 2 or not any(len(w) > 1 for w in nw[:-1]):
                continue
            for i in range(len(tokens) - len(nw) + 1):
                if tokens[i:i + len(nw)] == nw and set(tokens[i + len(nw):]) <= COADVISED_PREFIX:
                    starts.append(before[i][1])
        if starts:
            end = re.search(r'[);\n]', quote[mention.start():])
            end = mention.start() + end.start() if end else len(quote)
            start = max(starts)
            negative = re.search(r'\b(?:not|never|without|no longer)\s+$', quote[:start], re.I)
            if negative:
                start = negative.start()
            clauses.append(dict(start=start, end=end, text=quote[start:end]))
    return clauses


def _identity_url(url):
    """Only the HTTP empty-path/root spelling is equivalent; no guessed aliases or redirect expansion."""
    p = urlsplit(str(url or ''))
    if p.scheme not in {'http', 'https'} or not p.hostname or p.username or p.password or p.fragment:
        return None
    return urlunsplit((p.scheme, p.netloc.lower(), p.path or '/', p.query, ''))


class _PersonLink(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.current = [dict(attrs).get('href'), []]

    def handle_data(self, data):
        if self.current is not None:
            self.current[1].append(data)

    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append((self.current[0], ' '.join(self.current[1]))); self.current = None


def reviewed_cross_lab_identities(data, ents, hdir, nick=None):
    """An exact reviewed shared personal page adds a normal name+URL anchor, never a name-only/global join."""
    path = P.data('student-identity-review.json', root=hdir)
    if not path.exists():
        return []
    records = json.loads(path.read_text())
    if not isinstance(records, list):
        raise ValueError('student identity reviews must be a list')
    proofs, seen = [], set()
    for review in records:
        if review.get('scope') != 'cross_lab' or review.get('school') not in data:
            continue
        school = review['school']; name = review.get('canonical_name') or ''; url = _identity_url(review.get('identity_url'))
        members = review.get('memberships') or []
        keys = [('stu', school, m.get('pi'), m.get('person')) for m in members]
        if review.get('verdict') != 'same_person' or not url or len(set(keys)) != len(keys) or len(keys) < 2 \
                or len({k[2] for k in keys}) != len(keys) or len({k[3] for k in keys}) != 1 \
                or not str(keys[0][3]).startswith('ext:') or any(k not in ents or k in seen for k in keys) \
                or not all(any(compatible(name, n, nick) for n in ents[k]['names']) for k in keys):
            raise ValueError('invalid or conflicting cross-lab identity review: ' + str(review.get('canonical_name')))
        evidence = review.get('evidence') or []
        cited = lambda q: bool(re.fullmatch(r'[0-9a-fA-F]{64}', str(q.get('sha256') or ''))
                               and _identity_url(q.get('url')) and str(q.get('quote') or '').strip())
        primary = [q for q in evidence if q.get('kind') == 'primary_person_page' and cited(q)
                   and _identity_url(q['url']) == url and _contains_name(_coadvising_text_toks(q['quote']), name_toks(name))]
        if not primary:
            raise ValueError('cross-lab identity review lacks its named primary personal page: ' + name)
        for key in keys:
            student = next(r for r in data[school][1][key[2]] if r['person'] == key[3])
            sources = {(q.get('url'), q.get('sha256')) for rel in student.get('relations') or [] for q in rel.get('sources') or []}
            links = []
            for q in evidence:
                if q.get('kind') != 'roster_person_link' or q.get('pi') != key[2] or q.get('person') != key[3] \
                        or not cited(q) or (q['url'], q['sha256']) not in sources:
                    continue
                parser = _PersonLink(); parser.feed(q['quote'])
                if any(_identity_url(href) == url and any(compatible(label, n, nick) for n in ents[key]['names'])
                       for href, label in parser.links):
                    links.append(q)
            if not links:
                raise ValueError('cross-lab identity review lacks exact membership roster link: ' + str(key))
        anchor = ('name', f'{school}:{nname(name)}:{url}')
        for key in keys:
            ents[key]['anchors'].add(anchor)
        seen.update(keys); proofs.append(dict(school=school, native_person=keys[0][3], keys=keys,
                                              canonical_name=name, identity_url=url, evidence=evidence,
                                              reviewed_input_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return proofs


def _coadvisers_named(label, pi_names):
    tokens = _coadvising_text_toks(label)
    matched = collections.defaultdict(set)
    for pi, names in pi_names.items():
        for name in names:
            words = name_toks(name)
            if len(words) > 1 and any(len(w) > 1 for w in words[:-1]) and _contains_name(tokens, words):
                matched[tuple(words)].add(pi)
    full = {pi for candidates in matched.values() if len(candidates) == 1 for pi in candidates}
    if full:
        return full
    # A short qualifier such as "w/ Junxian" is allowed only when that complete given name is unique in the school.
    short = [w for w in tokens if w not in {'professor', 'with', 'by'}]
    if len(short) == 1 and len(short[0]) > 1:
        return {pi for pi, names in pi_names.items() for name in names if name_toks(name)[:1] == short}
    return set()


def coadvised_external_groups(data, ents, registry, nick=None):
    """Join a shared native ext: record only through reciprocal, cited co-adviser evidence within one school.

    Native external ids select candidates; they are never global person anchors. Names alone, unqualified roster
    mentions and one-sided co-advising do not prove identity. A new join that would redirect two issued person ids
    requires review instead of silently merging them. All validation precedes assign(), commit() and package writes.
    """
    groups = collections.defaultdict(list)
    for school, (pis, students, _, _) in data.items():
        for pi, records in students.items():
            for r in records:
                if str(r['person']).startswith('ext:'):
                    groups[school, r['person']].append((('stu', school, pi, r['person']), r))
    joins, holds = [], []
    for (school, person), records in sorted(groups.items()):
        if len(records) < 2:
            continue
        citations = [(k, q) for k, r in records for rel in r.get('relations') or [] for q in rel.get('sources') or []]
        keys = [k for k, _ in records]
        clauses = [(key, q, span) for key, q in citations
                   for span in student_coadvising_clauses(str(q.get('quote') or ''), ents[key]['names'])]
        shared = {k: {j for j in keys if j != k and ents[k]['anchors'] & ents[j]['anchors']} for k in keys}
        reached = {keys[0]}
        while True:
            expanded = reached | {j for k in reached for j in shared[k]}
            if expanded == reached:
                break
            reached = expanded
        shared_identity = len(reached) == len(keys)
        if not clauses and not shared_identity:
            continue  # another student's qualifier or roster boilerplate is not this person's identity claim
        base = dict(school=school, native_person=person, records=[dict(pi=k[2], name=r['name']) for k, r in records])
        if len(set(keys)) != len(keys) or not all(any(compatible(a, b, nick) for a in ents[x]['names'] for b in ents[y]['names'])
                                                for x in keys for y in keys):
            holds.append(dict(base, reason='incompatible names or duplicate memberships for a co-advised external id'))
            continue
        base['student_specific_clauses'] = [dict(pi=k[2], url=q.get('url'), sha256=q.get('sha256'), span=span)
                                           for k, q, span in clauses]
        if any(re.search(r'\b(?:not|never|no longer|without|except|excluding)\b', span['text'], re.I) for _, _, span in clauses):
            holds.append(dict(base, reason='negative student-specific co-advising evidence needs review'))
            continue
        issued = {resolve(registry, row[0]) for key in keys for kind, value in ents[key]['anchors']
                  if (row := registry.execute('select id from anchors where anchor=?', (person_anchor_str(kind, value),)).fetchone())}
        if len(issued) > 1:
            holds.append(dict(base, reason='co-advising join reaches multiple issued person IDs; explicit redirect review required', issued_ids=sorted(issued)))
            continue
        if shared_identity:
            joins.append(dict(base, keys=keys, basis='shared_identity_anchor', sources=[],
                              shared_anchors=[dict(from_pi=k[2], to_pi=j[2], anchors=sorted(ents[k]['anchors'] & ents[j]['anchors']))
                                              for k in keys for j in sorted(shared[k])]))
            continue
        pi_names = {p['pi']: p.get('names') or [p['pi']] for p in data[school][0]}
        edges = collections.defaultdict(list)
        for key, q, span in clauses:
            quote = span['text']
            if not re.fullmatch(r'[0-9a-fA-F]{64}', str(q.get('sha256') or '')) or not re.match(r'https?://', str(q.get('url') or '')):
                continue
            for m in COADVISED.finditer(quote):
                prefix = quote[:m.start()]
                if re.search(r'\b(?:not|never|no longer|without)\b', prefix[-40:], re.I) or not _student_before_coadvising(prefix, ents[key]['names']):
                    continue
                label = re.split(r'[);\n]', quote[m.end():], maxsplit=1)[0]
                if re.search(r'\b(?:not|never|no longer|except|excluding)\b', label, re.I):
                    continue
                targets = _coadvisers_named(label, pi_names)
                # Exact full names may list several advisers, but a given-only ambiguity is never narrowed to this group.
                if len(targets) > 1 and len(_coadvising_text_toks(label)) == 1:
                    continue
                for target in keys:
                    if target != key and target[2] in targets:
                        edges[key, target].append(dict(q, quote_span=span))
        linked = {k: {j for j in keys if edges[k, j] and edges[j, k]} for k in keys}
        reached = {keys[0]}
        while True:
            expanded = reached | {j for k in reached for j in linked[k]}
            if expanded == reached:
                break
            reached = expanded
        if len(reached) != len(keys):
            holds.append(dict(base, reason='reciprocal source-bound co-advising evidence is unresolved',
                              supported_directions=[dict(from_pi=k[2], to_pi=j[2], sources=v) for (k, j), v in edges.items() if v]))
            continue
        joins.append(dict(base, keys=keys, basis='reciprocal_coadvising', sources=[dict(from_pi=k[2], to_pi=j[2], source=q)
                                                  for (k, j), vv in sorted(edges.items()) if linked[k] and j in linked[k] for q in vv]))
    if holds:
        raise CoadvisingIDConflict(holds)
    return joins


def byline_author_ids(school, wanted, hdir):
    """{(openalex work id, raw byline name): author id} for the wanted pairs, from the school's OpenAlex sweep."""
    out = {}
    db = P.SchoolDir(school, hdir) / 'openalex-sweep.sqlite'
    if not wanted or not db.exists():
        return out
    want_w = {w for w, _ in wanted}
    c = sqlite3.connect(f'file:{db}?mode=ro', uri=True, timeout=120)
    for (body,) in c.execute('select body from pages'):
        for w in json.loads(zlib.decompress(body)):
            wid = norm_oa(w.get('id'), 'W')
            if wid not in want_w:
                continue
            for a in w.get('authorships') or []:
                raw = a.get('raw_author_name') or (a.get('author') or {}).get('display_name')
                aid = norm_oa((a.get('author') or {}).get('id'), 'A')
                if aid and (wid, raw) in wanted:
                    out[(wid, raw)] = aid
    c.close()
    return out


# ---------------------------------------------------------------- main

def run(schools, hdir, registry, use_sweep=True, today=None, write=True):
    """Validate work-only certificates first; their transaction cannot repair issued identities.

    A caller-owned transaction remains owned by the caller. Scoped publication
    inside one is held; write=False can stage IDs under a savepoint, never a dry run.
    Ordinary packages retain their existing transaction behavior.
    """
    from pihier.member_paper_reviews import validate_scoped, work_only
    data = {s: load_school(P.SchoolDir(s, Path(hdir))) for s in schools}
    for s, (pis, stu, rows, sp) in data.items():
        validate_scoped(s, stu, rows, sp, pis=pis)
    guarded = any(work_only(x) for _, _, _, sp in data.values() for x in sp)
    if not guarded:
        return _run(schools, hdir, registry, data, registry.commit, False, use_sweep, today, write)
    if registry.in_transaction and write:
        raise ValueError('exact-work ID publication requires its own transaction; caller transaction retained')
    registry.execute('savepoint atlas_exact_member_work')
    pending = True

    def finish():
        nonlocal pending
        registry.execute('release savepoint atlas_exact_member_work')
        pending = False

    try:
        return _run(schools, hdir, registry, data, finish, True, use_sweep, today, write)
    except Exception:
        if pending:
            registry.execute('rollback to savepoint atlas_exact_member_work')
            registry.execute('release savepoint atlas_exact_member_work')
        raise


def _run(schools, hdir, registry, data, finish, guarded, use_sweep, today, write):
    today = today or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    hdir = Path(hdir)
    try:
        sys.path.insert(0, str(P.TOOLS)); from pi_hierarchy import nick_ok  # noqa: E402
    except Exception:  # pragma: no cover
        nick_ok = None
    from pihier.member_paper_reviews import validate_scoped, work_only
    # Check every source edition before splitting can discard an edition anchor, and before any person/lab writes.
    _check_retired_work_anchors(registry, {
        (s, j): sorted((RANK[k], f'w|{WSCHEME[k]}:{v}') for k, v in work_anchors(r, s))
        for s, (_, _, rows, _) in data.items() for j, r in enumerate(rows)})
    stats = collections.Counter()
    # ---- people
    ents = {}      # entity key -> dict(kind, school, name, anchors set of (k, v), ref)
    for s, (pis, stu, rows, sp) in data.items():
        for p in pis:
            k = ('pi', s, p['pi'])
            A = {('orcid', o) for o in map(norm_orcid, (p.get('orcid') or []) + (p.get('orcidFromDblp') or [])) if o}
            mixed = {norm_oa(x) for x in p.get('mixedOpenAlex') or []}
            A |= {('openalex', a) for a in map(norm_oa, p.get('reviewedOpenAlex') or []) if a and a not in mixed}
            A |= {('dblp', d) for d in map(norm_dblp_pid, p.get('dblp') or []) if d}
            A |= {('coll', f'{s}:{i}') for i in p.get('personIds') or [] if i and not str(i).startswith('ext:')}
            if not A:
                urls = sorted({e.get('url') for q in p.get('periods') or [] for e in q.get('evidence') or [] if e.get('url')}
                              | {l.get('url') for l in p.get('listings') or [] if l.get('url')})
                A = {('name', f'{s}:{nname(p["pi"])}:{u}') for u in urls[:1]} or {('name', f'{s}:{nname(p["pi"])}:pi')}
            ents[k] = dict(kind='pi', school=s, name=p['pi'], names=p.get('names') or [p['pi']], anchors=A)
        for pi, recs in stu.items():
            for r in recs:
                k = ('stu', s, pi, r['person'])
                ids_ = [r['person']] + [m for m in r.get('merged') or []]
                A = {('coll', f'{s}:{i}') for i in ids_ if i and not str(i).startswith('ext:')}
                if not A:
                    urls = student_urls(r)
                    A = {('name', f'{s}:{nname(r["name"])}:{u}') for u in urls} or {('name', f'{s}:{nname(r["name"])}:lab:{slug(pi)}')}
                ents[k] = dict(kind='stu', school=s, name=r['name'], names=[r['name']] + list(r.get('aliases') or []), anchors=A)
    # Existing normal member anchors identify issued history, not certificate URLs.
    # A certificate cannot silently split or redirect that history after removing an OA bridge.
    scoped_issued = {}
    for s, (_, stu, _, sp) in data.items():
        for x in sp:
            if not work_only(x):
                continue
            key = ('stu', s, x['pi'], x['student'])
            issued = {resolve(registry, row[0]) for a in ents[key]['anchors']
                      if (row := registry.execute('select id from anchors where anchor=?', (person_anchor_str(*a),)).fetchone())}
            member = next(r for r in stu[x['pi']] if r['person'] == x['student'])
            prior = member.get('atlasId')
            if prior and registry.execute('select 1 from ids where id=?', (prior,)).fetchone():
                issued.add(resolve(registry, prior))
            scoped_issued[key] = issued
            if len(issued) > 1:
                raise ValueError('exact-work certificate reaches multiple issued member IDs; separate identity review required')
    # students who are PIs elsewhere in the atlas: a byline author id on one of the student's linked lab papers that is a
    # PI's reviewed OpenAlex id, with compatible names (Danqi Chen: Manning's student at Stanford, PI at Princeton)
    pi_by_oa = collections.defaultdict(list)
    for k, e in ents.items():
        if e['kind'] == 'pi':
            for a, v in e['anchors']:
                if a == 'openalex':
                    pi_by_oa[v].append(k)
    student_oa_evidence = {}
    if use_sweep:
        for s, (pis, stu, rows, sp) in data.items():
            wanted = {(norm_oa(x.get('oa'), 'W'), x.get('byline')) for x in sp if not work_only(x) and x.get('byline') and norm_oa(x.get('oa'), 'W')}
            # cheap prefilter: only bylines whose family name is some PI's family name
            pi_fams = {family(n) for e in ents.values() if e['kind'] == 'pi' for n in e['names']}
            wanted = {(w, b) for w, b in wanted if family(b) in pi_fams}
            got = byline_author_ids(s, wanted, hdir)
            for x in sp:
                if work_only(x):
                    continue  # another ordinary row may have populated this same (work, byline) key
                aid = got.get((norm_oa(x.get('oa'), 'W'), x.get('byline')))
                if not aid or aid not in pi_by_oa:
                    continue
                sk = ('stu', s, x['pi'], x['student'])
                if sk not in ents:
                    continue
                for pk in pi_by_oa[aid]:
                    if pk[1:] == (s, x['pi']):
                        continue
                    if any(compatible(a, b, nick_ok) for a in ents[sk]['names'] for b in ents[pk]['names']) and \
                            any(compatible(x['byline'], b, nick_ok) for b in ents[pk]['names']):
                        ents[sk]['anchors'].add(('openalex', aid))
                        student_oa_evidence.setdefault(sk, dict(openalex=aid, work=x.get('oa'), byline=x.get('byline'), pi=pk[2], pi_school=pk[1]))
    reviewed_identities = reviewed_cross_lab_identities(data, ents, hdir, nick_ok)
    coadvising = coadvised_external_groups(data, ents, registry, nick_ok)
    uf = UF(); by_anchor = collections.defaultdict(list)
    for k, e in ents.items():
        uf.find(k)
        for a in e['anchors']:
            by_anchor[a].append(k)
    for group in coadvising:
        for key in group['keys'][1:]:
            uf.union(group['keys'][0], key)
    conflicts = []
    for a, ks in sorted(by_anchor.items()):
        k0 = ks[0]
        for k in ks[1:]:
            if a[0] in STRONG_PERSON and not any(family(x) == family(y) for x in ents[k0]['names'] for y in ents[k]['names']):
                conflicts.append(dict(anchor=person_anchor_str(*a), a=list(k0), b=list(k))); continue
            uf.union(k0, k)
    comps = collections.defaultdict(set)
    for k in ents:
        comps[uf.find(k)] |= {(RANK[a], person_anchor_str(a, v)) for a, v in ents[k]['anchors']}
    comps = {c: sorted(v) for c, v in comps.items()}
    pid = assign(db := registry, 'person', 'atl:p:', comps, today, stats)
    person_of = {k: pid[uf.find(k)] for k in ents}
    for key, issued in scoped_issued.items():
        if issued and (person_of[key] not in issued or any(resolve(registry, old) != old for old in issued)):
            raise ValueError('exact-work certificate would change an issued member ID; separate identity review required')
    # ---- labs
    lab_comps = {}
    for k, e in ents.items():
        if e['kind'] == 'pi':
            lab_comps[k] = [(0, f'l|lab:{e["school"]}:{person_of[k]}')]
    lab_ids = {}
    for k, anchors in sorted(lab_comps.items()):
        row = db.execute('select id from anchors where anchor=?', (anchors[0][1],)).fetchone()
        if row:
            lab_ids[k] = row[0]; stats['labs_reused'] += 1
        else:
            i = f'atl:l:{k[1]}:{slug(k[2])}'
            n = 1
            while db.execute('select 1 from ids where id=?', (i,)).fetchone():
                n += 1; i = f'atl:l:{k[1]}:{slug(k[2])}-{n}'
            db.execute('insert into ids (id, kind, minted_from, issued) values (?,?,?,?)', (i, 'lab', anchors[0][1], today))
            db.execute('insert into anchors (anchor, id, kind, first_seen) values (?,?,?,?)', (anchors[0][1], i, 'lab', today))
            lab_ids[k] = i; stats['labs_minted'] += 1
    # ---- works
    wents = {}
    for s, (pis, stu, rows, sp) in data.items():
        for j, r in enumerate(rows):
            wents[(s, j)] = work_anchors(r, s) or {('collw', f'{s}:row:{r["pi"]}:{r.get("title")}')}
    wuf = UF(); wby = collections.defaultdict(list)
    for k, A in wents.items():
        wuf.find(k)
        for a in A:
            wby[a].append(k)
    for a, ks in wby.items():
        for k in ks[1:]:
            wuf.union(ks[0], k)
    # a component holding two rows of one lab is two papers the builder kept apart (e.g. two Zenodo versions behind one
    # OpenAlex record): such rows join only through their own lead record (row oa / doi / work), not through editions
    groups = collections.defaultdict(list)
    for k in wents:
        groups[wuf.find(k)].append(k)
    for g, ks in list(groups.items()):
        labs_ = collections.Counter((k[0], data[k[0]][2][k[1]]['pi']) for k in ks)
        if max(labs_.values()) > 1:
            stats['work_components_split'] += 1
            for k in ks:
                wuf.p[k] = k
            lead = {k: work_anchors(dict(data[k[0]][2][k[1]], editions=[]), k[0]) for k in ks}
            for k in ks:  # these rows register only their own lead anchors (an edition that is another row's lead is not theirs)
                wents[k] = lead[k] or wents[k]
            lb = collections.defaultdict(list)
            for k in ks:
                for a in lead[k]:
                    lb[a].append(k)
            for a, kk in lb.items():
                if len({(k[0], data[k[0]][2][k[1]]['pi']) for k in kk}) < len(kk):
                    stats['ambiguous_lead_work_anchors'] += 1
                    continue  # a DOI colliding inside one lab must not rejoin those works through another lab
                for k in kk[1:]:
                    if (k[0], data[k[0]][2][k[1]]['pi']) != (kk[0][0], data[kk[0][0]][2][kk[0][1]]['pi']):
                        wuf.union(kk[0], k)
    wcomps = collections.defaultdict(set)
    for k, A in wents.items():
        wcomps[wuf.find(k)] |= {(RANK[a], f'w|{WSCHEME[a]}:{v}') for a, v in A}
    wcomps = {c: sorted(v) for c, v in wcomps.items()}
    try:
        wid = assign(db, 'work', 'atl:w:', wcomps, today, stats)
    except WorkIDConflict:
        if not guarded:
            db.rollback()  # guarded runs roll back their own savepoint, retaining a caller's transaction
        raise
    work_of = {k: wid[wuf.find(k)] for k in wents}
    # ---- appointments and cross-school persons
    appts = collections.defaultdict(list)
    for k, e in ents.items():
        if e['kind'] == 'pi':
            appts[person_of[k]].append(dict(school=k[1], pi=k[2], labId=lab_ids[k]))
    for v in appts.values():
        v.sort(key=lambda a: (a['school'], a['pi']))
    stud_of = collections.defaultdict(list)
    for k, e in ents.items():
        if e['kind'] == 'stu':
            stud_of[person_of[k]].append(dict(school=k[1], pi=k[2], labId=lab_ids.get(('pi', k[1], k[2])), record=k[3]))
    cross = []
    for i in sorted(set(appts) | set(stud_of)):
        schools_ = {a['school'] for a in appts.get(i, [])} | {a['school'] for a in stud_of.get(i, [])}
        if len(appts.get(i, [])) > 1 or (appts.get(i) and stud_of.get(i) and len(schools_) > 1):
            ev = [student_oa_evidence[k] for k in ents if person_of[k] == i and k in student_oa_evidence]
            anchors_ = sorted({person_anchor_str(a, v) for k in ents if person_of[k] == i for a, v in ents[k]['anchors'] if a in STRONG_PERSON})
            cross.append(dict(atlasId=i, name=next(a['pi'] for a in appts[i]), appointments=appts[i],
                              studentRecords=stud_of.get(i, []), matchedBy=anchors_, studentEvidence=ev))
    # ---- ID annotations, validated before commit or package publication
    if write:
        for s, (pis, stu, rows, sp) in data.items():
            for p in pis:
                k = ('pi', s, p['pi'])
                p['atlasId'] = person_of[k]; p['labId'] = lab_ids[k]
                p['appointments'] = appts[person_of[k]]
                p['asStudent'] = [x for x in stud_of.get(person_of[k], []) if (x['school'], x['pi']) != (s, p['pi'])]
            for pi, recs in stu.items():
                for r in recs:
                    i = person_of[('stu', s, pi, r['person'])]
                    r['atlasId'] = i
                    if appts.get(i):
                        r['alsoPi'] = appts[i]
                    else:
                        r.pop('alsoPi', None)
            key = {(s, j): r for j, r in enumerate(rows)}
            for j, r in enumerate(rows):
                r['atlasWorkId'] = work_of[(s, j)]
            by_work = {}
            for j, r in enumerate(rows):
                for x in (r.get('work'), r.get('oa')):
                    if x:
                        by_work.setdefault((r['pi'], x), r['atlasWorkId'])
            for x in sp:
                x['studentAtlasId'] = person_of.get(('stu', s, x['pi'], x['student']))
                x['atlasWorkId'] = by_work.get((x['pi'], x.get('work'))) or by_work.get((x['pi'], x.get('oa')))
                x['labId'] = lab_ids.get(('pi', s, x['pi']))
            del key
            try:
                validate_scoped(s, stu, rows, sp, pis=pis)
            except ValueError:
                if not guarded:
                    db.rollback()
                raise
    scoped_links = sum(work_only(x) for _, _, _, sp in data.values() for x in sp)
    if scoped_links:
        stats['exact_work_links_validated'] = scoped_links
    finish()
    # ---- write (all scoped post-ID preimages have passed)
    if write:
        for s, (pis, stu, rows, sp) in data.items():
            D = P.SchoolDir(s, hdir)
            tmpf = D.tmp('pis.json', '.ids-tmp'); tmpf.write_text(json.dumps(pis, indent=1, ensure_ascii=False)); tmpf.replace(D / 'pis.json')
            tmpf = D.tmp('students.json', '.ids-tmp'); tmpf.write_text(json.dumps(stu, indent=1, ensure_ascii=False)); tmpf.replace(D / 'students.json')
            for name, rr in (('lab_papers', rows), ('student_papers', sp)):
                tmpf = D.tmp(f'{name}.jsonl.gz', '.ids-tmp')
                with P.gzip_text(tmpf) as f:
                    for r in rr:
                        f.write(json.dumps(r, ensure_ascii=False) + '\n')
                tmpf.replace(D / f'{name}.jsonl.gz')
        out = P.hfile(hdir, 'ids'); out.mkdir(parents=True, exist_ok=True)
        # cross-reference table
        xr = set()
        for k, e in ents.items():
            i = person_of[k]
            for a, v in e['anchors']:
                scheme = {'orcid': 'orcid', 'openalex': 'openalex_author', 'dblp': 'dblp_person', 'coll': 'collection_person', 'name': 'name_evidence'}[a]
                xr.add((i, 'person', scheme, v))
            if e['kind'] == 'pi':
                xr.add((i, 'person', 'legacy_pi_id', f'{k[1]}:{slug(k[2])}'))
                xr.add((lab_ids[k], 'lab', 'legacy_lab_id', f'{k[1]}:{slug(k[2])}'))
                xr.add((lab_ids[k], 'lab', 'pi_atlas_id', i))
            else:
                xr.add((i, 'person', 'legacy_student_id', k[3] if str(k[3]).startswith('ext:') else f'{k[1]}:{k[3]}'))
        for k, A in wents.items():
            i = work_of[k]
            for a, v in A:
                scheme = {'doi': 'doi', 'oaw': 'openalex_work', 'dblpkey': 'dblp_key', 'arxiv': 'arxiv', 'collw': 'collection_work', 'labpage': 'labpage'}[a]
                xr.add((i, 'work', scheme, v))
        buf = io.StringIO(); w = csv.writer(buf, delimiter='\t', lineterminator='\n')
        w.writerow(['atlas_id', 'entity', 'scheme', 'value'])
        w.writerows(sorted(xr))
        with open(out / 'crossref.tsv.gz.tmp', 'wb') as f:
            with gzip.GzipFile(fileobj=f, mode='wb', mtime=0) as g:
                g.write(buf.getvalue().encode())
        (out / 'crossref.tsv.gz.tmp').replace(out / 'crossref.tsv.gz')
        red = db.execute("select id, redirect_to, kind from ids where status='redirect' order by id").fetchall()
        (out / 'redirects.tsv').write_text('old_id\tnew_id\tentity\n' + ''.join(f'{a}\t{resolve(db, b)}\t{c}\n' for a, b, c in red))
        (out / 'persons-cross-school.json').write_text(json.dumps(dict(
            _doc='People who hold PI appointments at two or more atlas schools, or are a student at one school and a PI at '
                 'another, joined by ORCID, a reviewed OpenAlex author id or a DBLP person (never by name alone); '
                 'tools/atlas_ids.py, docs/IDS.md.', persons=cross), indent=1, ensure_ascii=False) + '\n')
    rep = dict(at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), schools=list(schools), stats=dict(stats),
               people=len(set(person_of.values())), pi_people=len(appts), student_records=sum(1 for k in ents if k[0] == 'stu'),
               works=len(set(work_of.values())), work_rows=len(work_of), labs=len(lab_ids), cross_school_persons=len(cross),
               students_matched_to_pi_elsewhere=len(student_oa_evidence),
               coadvised_student_groups=sum(g['basis'] == 'reciprocal_coadvising' for g in coadvising),
               shared_external_identity_groups=len(coadvising),
               reviewed_cross_lab_identity_groups=len(reviewed_identities),
               reviewed_cross_lab_identity_evidence=[{k: v for k, v in g.items() if k != 'keys'} for g in reviewed_identities],
               coadvising_evidence=[{k: v for k, v in g.items() if k != 'keys'} for g in coadvising],
               conflicts_refused=len(conflicts), conflicts=conflicts[:50],
               registry=dict(ids=db.execute('select count(*) from ids').fetchone()[0],
                             anchors=db.execute('select count(*) from anchors').fetchone()[0],
                             redirects=db.execute("select count(*) from ids where status='redirect'").fetchone()[0],
                             retired_work_anchors=len(retired_work_anchors(db))))
    if write:
        (P.hfile(hdir, 'ids') / 'IDS-REPORT.json').write_text(json.dumps(rep, indent=1, ensure_ascii=False) + '\n')
    return dict(report=rep, person_of=person_of, work_of=work_of, lab_ids=lab_ids, cross=cross)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('schools', nargs='*')
    ap.add_argument('--dir', default=str(P.HIERARCHY))
    ap.add_argument('--registry', default=str(P.data('ids') / 'registry.sqlite'))
    ap.add_argument('--no-sweep', action='store_true', help='skip the OpenAlex byline author ids (student -> PI elsewhere)')
    ap.add_argument('--retire-work-anchors', type=Path, help='offline exact source review JSON; dry run unless --apply-retirements')
    ap.add_argument('--retirement-backup', type=Path, help='new whole-registry backup required when applying retirements')
    ap.add_argument('--apply-retirements', action='store_true', help='apply the exact reviewed retirement; no package or auxiliary writes')
    a = ap.parse_args(argv)
    if a.retire_work_anchors:
        args = list(sys.argv[1:] if argv is None else argv)
        if a.schools or not any(x == '--registry' or x.startswith('--registry=') for x in args):
            ap.error('retirement requires an explicit --registry and does not take schools')
        if not sys.flags.isolated:
            ap.error('retirement review input requires isolated Python (-I)')
        with a.retire_work_anchors.open('rb') as source:
            raw = source.read(5 * 1024 * 1024 + 1)
        if len(raw) > 5 * 1024 * 1024:
            ap.error('retirement review exceeds 5 MB')
        review = json.loads(raw)
        result = retire_work_anchors(a.registry, review, backup=a.retirement_backup, write=a.apply_retirements)
        result['review_file_sha256'] = hashlib.sha256(raw).hexdigest()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if a.apply_retirements or a.retirement_backup:
        ap.error('retirement options require --retire-work-anchors')
    # The registry lives on NFS, where every SQLite lock change drops the page cache: a run re-read the 56 MB file ~150
    # times (8.5 GB) and three runs on 2026-11-03 hung for good inside a lock call. So the run works on a copy on local
    # disk and the result replaces the registry in one rename; a failed run leaves the registry as it was.
    reg = Path(a.registry)
    work = Path(tempfile.mkdtemp(prefix='atlas-ids-', dir=os.environ.get('ATLAS_IDS_LOCAL_DIR') or tempfile.gettempdir()))
    try:
        local = work / 'registry.sqlite'
        if reg.exists():
            shutil.copy2(reg, local)
        else:
            open_registry(reg).close()  # seed from the latest release (or empty) at the real path, then copy it
            shutil.copy2(reg, local)
        db = open_registry(local, seed=False)
        res = run(a.schools or list(P.SCHOOL_IDS), a.dir, db, use_sweep=not a.no_sweep)
        db.close()
        tmp = reg.with_name(f'.{reg.name}.{os.getpid()}.tmp')
        shutil.copy2(local, tmp); tmp.chmod(0o644)
        os.replace(tmp, reg)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    r = res['report']
    print(json.dumps({k: v for k, v in r.items() if k != 'conflicts'}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
