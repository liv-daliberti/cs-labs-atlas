"""The OpenAlex bulk snapshot as a compact local store (ROADMAP #24; plan: docs/OPENALEX-SNAPSHOT.md).

The public snapshot (s3://openalex, 675 GB of gzipped works) is streamed over HTTPS, filtered to what the pipeline reads, and
never written to disk: only a few GB of kept works, authors and institutions land, as one SQLite file per snapshot date at
OA_SNAPSHOT/<date>/openalex.sqlite.

Kept works: an authorship institution whose lineage holds a charter id (schools/*.toml ids.openalex + openalex_related, minus
openalex_excluded), or an authorship by one of our people (oaAuthorIds + reviewedOpenAlex of every school's pis.json). Datasets
with DOI prefix 10.17989 (ENCODE records) are dropped. Kept authors: our people and authors affiliated with a charter
institution. Institutions: all (0.2 GB).

usage:
  oa_snapshot.py filter <task> <of> [--date D]   one array task: streams its share of the parts (balanced by size), writes a part
                                                 file to OA_SNAPSHOT-scratch (job-local /tmp first, one sequential copy after)
  oa_snapshot.py merge [--date D] [--keep-parts] [--no-promote]  attaches the parts into OA_SNAPSHOT/<date>/openalex.sqlite, checks counts,
                                                 removes the parts, writes manifest.json, points `current` at it
  oa_snapshot.py status [--date D]                what is stored
Reader (import oa_snapshot): work(id_or_doi), works_by_lineage(inst, year=None), works_by_author(author_id), author(id),
institution(id), snapshot_date(). Every row carries `snapshot_date`; callers apply their own age rule and fall back to the API.
"""
import argparse, hashlib, json, os, re, shutil, sqlite3, sys, time, zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas_paths as P  # noqa: E402

BASE = os.environ.get('OA_SNAPSHOT_BASE', 'https://openalex.s3.amazonaws.com/')
ENTITIES = ('works', 'authors', 'institutions')
TOKEN = re.compile(rb'https://openalex\.org/([AI][0-9]+)"')  # every author and institution id in a line, in any key
ENCODE_PREFIX = 'https://doi.org/10.17989'
USER_AGENT = 'HomogenizingScienceResearch/0.2 (academic metadata inventory)'

SCHEMA = '''
CREATE TABLE IF NOT EXISTS works (id TEXT PRIMARY KEY, doi TEXT, year INTEGER, type TEXT, title TEXT, updated_date TEXT, body BLOB);
CREATE TABLE IF NOT EXISTS work_inst (work_id TEXT, inst TEXT, PRIMARY KEY (work_id, inst));
CREATE TABLE IF NOT EXISTS work_author (work_id TEXT, author_id TEXT, PRIMARY KEY (work_id, author_id));
CREATE TABLE IF NOT EXISTS authors (id TEXT PRIMARY KEY, name TEXT, orcid TEXT, updated_date TEXT, body BLOB);
CREATE TABLE IF NOT EXISTS institutions (id TEXT PRIMARY KEY, name TEXT, ror TEXT, body BLOB);
CREATE TABLE IF NOT EXISTS parts (url TEXT PRIMARY KEY, records INTEGER, kept INTEGER, bytes INTEGER);
'''
INDEXES = '''
CREATE INDEX IF NOT EXISTS works_doi ON works(doi);
CREATE INDEX IF NOT EXISTS works_year ON works(year);
CREATE INDEX IF NOT EXISTS work_inst_inst ON work_inst(inst);
CREATE INDEX IF NOT EXISTS work_author_author ON work_author(author_id);
'''


def short(i):
    return (i or '').rsplit('/', 1)[-1]


# ---------------------------------------------------------------- what to keep
def targets():
    """(lineage ids to keep, ids to exclude, our author ids) from the charters and the PI lists."""
    import school_config as SC
    inst, excl, authors = set(), set(), set()
    for k in SC.keys():
        cfg = SC.get(k)
        inst |= set(SC.sweep_ids(k)); excl |= set(cfg['ids'].get('openalex_excluded') or [])
        try:
            for p in json.load(open(P.data('pis.json', k))):
                authors |= {short(a) for a in (p.get('oaAuthorIds') or []) + (p.get('reviewedOpenAlex') or [])}
        except (OSError, ValueError, KeyError):
            pass
    return inst - excl, excl, {a for a in authors if a}


def keep_work(w, inst, excl, authors):
    """The kept work's projection and its (institution, author) key sets, or None."""
    if w.get('type') == 'dataset' and (w.get('doi') or '').startswith(ENCODE_PREFIX):
        return None
    hit_i, hit_a, ships = set(), set(), []
    for a in w.get('authorships') or []:
        aid = short((a.get('author') or {}).get('id'))
        for x in a.get('institutions') or []:
            # exclusion is per affiliation: an author with UChicago AND an excluded Argonne affiliation keeps the UChicago hit
            # (the whole authorship used to be dropped: UChicago PROTOCOL-FRICTION 20)
            ids = {short(l) for l in (x.get('lineage') or [])} | {short(x.get('id'))}
            if not (ids & excl):
                hit_i |= ids & inst
        if aid in authors:
            hit_a.add(aid)
        ships.append(a)
    if not hit_i and not hit_a:
        return None
    return project_work(w), hit_i, {short((a.get('author') or {}).get('id')) for a in ships} & authors | hit_a


def project_work(w):
    keep = ('id', 'doi', 'title', 'display_name', 'ids', 'publication_year', 'publication_date', 'type', 'language', 'authorships',
            'primary_location', 'locations', 'best_oa_location', 'open_access', 'biblio', 'cited_by_count', 'is_retracted',
            'is_paratext', 'created_date', 'updated_date')
    out = {k: w.get(k) for k in keep if k in w}
    out['authorships'] = [{k: a.get(k) for k in ('author', 'author_position', 'institutions', 'raw_affiliation_strings', 'raw_author_name', 'is_corresponding') if k in a}
                          for a in w.get('authorships') or []]
    return out


def project_author(a):
    return {k: a.get(k) for k in ('id', 'display_name', 'display_name_alternatives', 'orcid', 'ids', 'works_count', 'cited_by_count',
                                  'last_known_institutions', 'affiliations', 'updated_date', 'created_date') if k in a}


def project_inst(x):
    return {k: x.get(k) for k in ('id', 'display_name', 'ror', 'country_code', 'type', 'lineage', 'associated_institutions',
                                  'international', 'homepage_url') if k in x}


def pack(o):
    return zlib.compress(json.dumps(o, ensure_ascii=False, separators=(',', ':')).encode(), 6)


def unpack(b):
    return json.loads(zlib.decompress(b))


# ---------------------------------------------------------------- the manifest and the stream
def get(url, **kw):
    import requests
    kw.setdefault('timeout', (30, 120))
    kw.setdefault('headers', {})['User-Agent'] = USER_AGENT
    return requests.get(url, **kw)


def manifest(entity):
    """(snapshot date, [(url, bytes, records)]) from data/jsonl/<entity>/manifest.json."""
    r = get(f'{BASE}data/jsonl/{entity}/manifest.json')
    r.raise_for_status()
    m = r.json()
    return m['date'], [(e['url'].replace('s3://openalex/', BASE), e['meta']['content_length'], e['meta']['record_count']) for e in m['files']]


def all_parts(date=None):
    """[(entity, url, bytes, records)] over works, authors, institutions; the manifest date must match `date` if given."""
    out, d0 = [], None
    for ent in ENTITIES:
        d, parts = manifest(ent)
        d0 = d0 or d
        if d != d0 or (date and d != date):
            raise SystemExit(f'manifest dates differ: {ent} {d} vs {d0}/{date}')
        out += [(ent, u, b, r) for u, b, r in parts]
    return d0, out


def share(parts, task, of):
    """Deterministic balanced split by size (longest first onto the lightest task)."""
    loads = [0] * of
    mine = []
    for ent, u, b, r in sorted(parts, key=lambda p: (-p[2], p[1])):
        i = loads.index(min(loads))
        loads[i] += b
        if i == task:
            mine.append((ent, u, b, r))
    return sorted(mine, key=lambda p: p[1])


def stream_lines(url, chunk=4 << 20):
    """Decompressed lines of one gzipped JSONL part, streamed (never stored)."""
    r = get(url, stream=True)
    r.raise_for_status()
    d = zlib.decompressobj(31)
    rest = b''
    for data in r.iter_content(chunk):
        buf = rest + d.decompress(data)
        lines = buf.split(b'\n')
        rest = lines.pop()
        yield from lines
    tail = rest + d.flush()
    if tail.strip():
        yield tail


def filter_part(ent, url, inst, excl, authors):
    """Rows kept from one part: ('works', ...), ('authors', ...) or ('institutions', ...) tuples."""
    works, wi, wa, auth, insts, n = [], [], [], [], [], 0
    for line in stream_lines(url):
        n += 1
        if not line:
            continue
        if ent == 'institutions':
            x = json.loads(line)
            insts.append((x['id'], x.get('display_name'), x.get('ror'), pack(project_inst(x))))
            continue
        toks = {t.decode() for t in TOKEN.findall(line)}
        if ent == 'works':
            if not (toks & inst or toks & authors):
                continue
            w = json.loads(line)
            r = keep_work(w, inst, excl, authors)
            if r:
                p, hi, ha = r
                works.append((w['id'], w.get('doi'), w.get('publication_year'), w.get('type'), w.get('title'), w.get('updated_date'), pack(p)))
                wi += [(w['id'], i) for i in hi]
                wa += [(w['id'], a) for a in ha]
        else:  # authors: ours, or affiliated with a charter institution
            if not (toks & inst or toks & authors):
                continue
            a = json.loads(line)
            if short(a['id']) in authors or toks & inst:
                auth.append((a['id'], a.get('display_name'), a.get('orcid'), a.get('updated_date'), pack(project_author(a))))
    return n, works, wi, wa, auth, insts


def write_part(db, ent, url, size, rows):
    n, works, wi, wa, auth, insts = rows
    db.executemany('INSERT OR REPLACE INTO works VALUES (?,?,?,?,?,?,?)', works)
    db.executemany('INSERT OR IGNORE INTO work_inst VALUES (?,?)', wi)
    db.executemany('INSERT OR IGNORE INTO work_author VALUES (?,?)', wa)
    db.executemany('INSERT OR REPLACE INTO authors VALUES (?,?,?,?,?)', auth)
    db.executemany('INSERT OR REPLACE INTO institutions VALUES (?,?,?,?)', insts)
    db.execute('INSERT OR REPLACE INTO parts VALUES (?,?,?,?)', (url, n, len(works) + len(auth) + len(insts), size))
    db.commit()


def scratch_dir(date):
    return P.SCRATCH / f'openalex-{date}'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def cmd_filter(task, of, date=None, parts=None, tmp=None):
    d, allp = (date, parts) if parts is not None else all_parts(date)
    inst, excl, authors = targets()
    mine = share(allp, task, of)
    tmp = Path(tmp or os.environ.get('TMPDIR') or '/tmp') / f'oa-part-{d}-{task:02d}.sqlite'
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(str(tmp))
    db.executescript(SCHEMA)
    t0, done = time.time(), 0
    for ent, url, size, _ in mine:
        for attempt in range(4):
            try:
                rows = filter_part(ent, url, inst, excl, authors)
                break
            except Exception as e:  # network or gzip error: the part restarts, nothing of it was written
                print(json.dumps(dict(part_retry=url, attempt=attempt, error=str(e)[:120])), flush=True)
                time.sleep(20 * (attempt + 1))
        else:
            raise SystemExit(f'part failed after retries: {url}')
        write_part(db, ent, url, size, rows)
        done += 1
        print(json.dumps(dict(task=task, parts_done=done, of=len(mine), url=url.rsplit('/', 2)[-2:], records=rows[0], kept=len(rows[1]) + len(rows[4]) + len(rows[5]),
                              seconds=int(time.time() - t0))), flush=True)
    db.close()
    out = scratch_dir(d)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f'part-{task:02d}.sqlite'
    shutil.copyfile(tmp, str(dest) + '.part')  # one sequential write of the finished part
    os.replace(str(dest) + '.part', dest)
    (out / f'part-{task:02d}.done').write_text(json.dumps(dict(bytes=dest.stat().st_size, sha256=sha(dest), parts=len(mine), of=of)))
    tmp.unlink(missing_ok=True)
    print(json.dumps(dict(task=task, finished=str(dest), bytes=dest.stat().st_size)), flush=True)


def cmd_merge(date, of=None, keep_parts=False, parts=None, promote=True):
    out = scratch_dir(date)
    dones = sorted(out.glob('part-*.done'))
    if not dones or (of and len(dones) != of):
        raise SystemExit(f'expected {of} finished parts in {out}, found {len(dones)}')
    final_dir = P.OA_SNAPSHOT / date
    final_dir.mkdir(parents=True, exist_ok=True)
    final = final_dir / 'openalex.sqlite'
    tmp = Path(str(final) + '.part')
    tmp.unlink(missing_ok=True)
    db = sqlite3.connect(str(tmp))
    db.executescript(SCHEMA)
    expect = {'works': 0, 'work_inst': 0, 'work_author': 0, 'authors': 0, 'institutions': 0, 'parts': 0}
    for dn in dones:
        part = dn.with_suffix('.sqlite')
        meta = json.loads(dn.read_text())
        if sha(part) != meta['sha256']:
            raise SystemExit(f'checksum differs: {part}')
        db.execute('ATTACH ? AS p', (str(part),))
        for t in expect:
            expect[t] += db.execute(f'SELECT COUNT(*) FROM p.{t}').fetchone()[0]
            db.execute(f'INSERT OR REPLACE INTO main.{t} SELECT * FROM p.{t}')
        db.commit()
        db.execute('DETACH p')
    db.executescript(INDEXES)
    got = {t: db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in expect}
    nparts = got['parts']
    if parts is not None and nparts != len(parts):
        raise SystemExit(f'the parts table holds {nparts} manifest parts, expected {len(parts)}')
    db.execute('PRAGMA optimize')
    db.close()
    os.replace(tmp, final)
    man = dict(snapshot_date=date, built_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), counts=got, rows_before_dedup=expect,
               parts_files=len(dones), source=BASE, store_bytes=final.stat().st_size)
    (final_dir / 'manifest.json').write_text(json.dumps(man, indent=1))
    if promote:  # a refresh builds a new dated store and leaves `current` alone (oa_snapshot_refresh.py promote switches it)
        cur = P.OA_SNAPSHOT / 'current'
        if cur.is_symlink() or cur.exists():
            cur.unlink()
        cur.symlink_to(date)
    if not keep_parts:
        for dn in dones:
            dn.with_suffix('.sqlite').unlink(missing_ok=True); dn.unlink()
        try:
            out.rmdir()
        except OSError:
            pass
        man['parts_removed'] = len(dones)
        (final_dir / 'manifest.json').write_text(json.dumps(man, indent=1))
    print(json.dumps(man), flush=True)


# ---------------------------------------------------------------- the reader
_conns = {}


def snapshot_date(root=None):
    cur = Path(root or P.OA_SNAPSHOT) / 'current'
    return os.readlink(cur) if cur.is_symlink() else None


def conn(root=None, date=None):
    root = Path(root or P.OA_SNAPSHOT)
    d = date or snapshot_date(root)
    if d is None:
        raise FileNotFoundError(f'no OpenAlex snapshot under {root}')
    key = (str(root), d)
    if key not in _conns:
        _conns[key] = (sqlite3.connect(f'file:{root / d / "openalex.sqlite"}?mode=ro', uri=True, timeout=60), d)
    return _conns[key]


def _w(row, d):
    w = unpack(row[0])
    w['snapshot_date'] = d
    return w


def work(key, root=None):
    """A work by OpenAlex id (W..., URL or short) or DOI; None when absent (the caller then asks the API)."""
    db, d = conn(root)
    k = key.strip()
    if k.lower().startswith('10.'):
        k = 'https://doi.org/' + k
    if k.lower().startswith('http') and 'doi.org' in k.lower():
        r = db.execute('SELECT body FROM works WHERE doi=? COLLATE NOCASE', (k,)).fetchone()
    else:
        r = db.execute('SELECT body FROM works WHERE id=?', (k if k.startswith('http') else 'https://openalex.org/' + k,)).fetchone()
    return _w(r, d) if r else None


def works_by_lineage(inst, year=None, root=None):
    db, d = conn(root)
    q = 'SELECT w.body FROM work_inst i JOIN works w ON w.id=i.work_id WHERE i.inst=?' + (' AND w.year=?' if year else '') + ' ORDER BY w.id'
    for r in db.execute(q, (short(inst), year) if year else (short(inst),)):
        yield _w(r, d)


def works_by_author(author_id, root=None):
    db, d = conn(root)
    for r in db.execute('SELECT w.body FROM work_author a JOIN works w ON w.id=a.work_id WHERE a.author_id=? ORDER BY w.id', (short(author_id),)):
        yield _w(r, d)


def author(aid, root=None):
    db, d = conn(root)
    r = db.execute('SELECT body FROM authors WHERE id=?', (aid if aid.startswith('http') else 'https://openalex.org/' + aid,)).fetchone()
    if not r:
        return None
    a = unpack(r[0]); a['snapshot_date'] = d
    return a


def institution(iid, root=None):
    db, d = conn(root)
    r = db.execute('SELECT body FROM institutions WHERE id=?', (iid if iid.startswith('http') else 'https://openalex.org/' + iid,)).fetchone()
    return unpack(r[0]) if r else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    f = sub.add_parser('filter'); f.add_argument('task', type=int); f.add_argument('of', type=int); f.add_argument('--date')
    m = sub.add_parser('merge'); m.add_argument('--date', required=True); m.add_argument('--of', type=int); m.add_argument('--keep-parts', action='store_true'); m.add_argument('--no-promote', action='store_true', help='do not point `current` at the new store')
    s = sub.add_parser('status'); s.add_argument('--date')
    a = ap.parse_args(argv)
    if a.cmd == 'filter':
        cmd_filter(a.task, a.of, a.date)
    elif a.cmd == 'merge':
        cmd_merge(a.date, a.of, a.keep_parts, promote=not a.no_promote)
    else:
        d = a.date or snapshot_date()
        print(json.dumps(json.load(open(P.OA_SNAPSHOT / d / 'manifest.json'))) if d else 'no snapshot')


if __name__ == '__main__':
    main()
