"""`atlas new-school <key> --name "University of X"` (ROADMAP #19): stage 0 of docs/ADDING-A-SCHOOL.md as one command.

Makes, for a school that does not exist yet (it refuses when any of them does):
  schools/<key>.toml          the charter, from schools/TEMPLATE.toml with key, name, short, order, started and status = "onboarding"
  hierarchy/<key>/            the data folders raw/ reviewed/ derived/ work/ reports/ and tmp/ (ignored by git)
  <STORES>/<key>/             the full-text store: catalog.sqlite with the schema below (EMPTY: never a copy of another school's store),
                              the folders fulltext-push/store_layout.py requires, and a receipts row recording who created it and when
  hierarchy/<key>/reports/new-school.json   the receipt of this command
then runs the stage-0 check (tools/school_config.py check) and prints what is still to fill in. The command succeeds when it made
everything; the stage-0 gate itself passes only when the charter is filled in and reviewed (atlas charters, atlas stage-gate).

  new_school.py <key> --name NAME [--short NAME] [--order N] [--site-uni ID] [--dry-run]
"""
import argparse, datetime, json, re, sqlite3, sys
from pathlib import Path

import atlas_paths as P  # noqa: E402
import catalog_alias  # noqa: E402
import school_config as S  # noqa: E402

CODE = Path(__file__).resolve().parents[1]
SUBDIRS = ('raw', 'reviewed', 'derived', 'work', 'reports', 'tmp')
STORE_DIRS = ('objects', 'sources', 'staged', 'by_lab', 'discovery', 'quarantine', 'backups')
CATALOG_DDL = '''
CREATE TABLE IF NOT EXISTS works (
  id TEXT PRIMARY KEY, title TEXT, doi TEXT, year INTEGER,
  graph_json TEXT NOT NULL, oa_json TEXT, metadata_source TEXT,
  status TEXT NOT NULL DEFAULT 'queued', file_path TEXT,
  sha256 TEXT, byte_count INTEGER, pages INTEGER,
  download_url TEXT, downloaded_at TEXT, identity_check TEXT);
CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, kind TEXT, name TEXT, record_json TEXT);
CREATE TABLE IF NOT EXISTS edges (id TEXT PRIMARY KEY, source TEXT, target TEXT, kind TEXT, record_json TEXT);
CREATE INDEX IF NOT EXISTS edges_source ON edges(source);
CREATE INDEX IF NOT EXISTS edges_target ON edges(target);
CREATE TABLE IF NOT EXISTS candidates (
  work_id TEXT, url TEXT, landing_url TEXT, license TEXT, version TEXT,
  metadata_source TEXT, PRIMARY KEY(work_id,url));
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY, work_id TEXT, url TEXT, observed_at TEXT,
  status TEXT, detail TEXT);
CREATE INDEX IF NOT EXISTS attempts_work_url ON attempts(work_id,url);
CREATE TABLE IF NOT EXISTS receipts (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS assets (work_id TEXT,kind TEXT,url TEXT,path TEXT,sha256 TEXT,bytes INTEGER,version TEXT,license TEXT,metadata_source TEXT,downloaded_at TEXT,identity_check TEXT,PRIMARY KEY(work_id,kind,url));
CREATE TABLE IF NOT EXISTS access_review (work_id TEXT PRIMARY KEY, verdict TEXT, cause TEXT, causes_json TEXT, max_attempt_id INTEGER, reviewed_at TEXT, review TEXT);
CREATE INDEX IF NOT EXISTS works_slim ON works(id, status, doi, title, year, identity_check, byte_count, sha256);
'''


def charter_text(key, name, short, order, site_uni, today, template):
    t = template.read_text()
    for field, val in (('key', key), ('name', name), ('short', short), ('site_uni', site_uni), ('started', today)):
        t, n = re.subn(rf'^{field} = "[^"]*"', f'{field} = {json.dumps(val)}', t, count=1, flags=re.M)
        if n != 1:
            raise SystemExit(f'schools/TEMPLATE.toml has no line "{field} = \\"...\\""')
    t, n = re.subn(r'^order = \d+', f'order = {order}', t, count=1, flags=re.M)
    if n != 1:
        raise SystemExit('schools/TEMPLATE.toml has no "order = N" line')
    return t


def next_order(schools_dir):
    best = 0
    for f in Path(schools_dir).glob('*.toml'):
        m = re.search(r'^order\s*=\s*(\d+)', f.read_text(), re.M)
        best = max(best, int(m.group(1)) if m else 0)
    return best + 1


def make_store(store, key, now):
    store.mkdir(parents=True)
    for d in STORE_DIRS:
        (store / d).mkdir()
    (store / 'summary.json').write_text('{}\n')
    db = sqlite3.connect(store / 'catalog.sqlite')
    try:
        db.executescript(CATALOG_DDL)
        db.executescript(catalog_alias.SCHEMA)
        db.execute('insert into receipts values (?,?)', ('created', json.dumps(dict(by='tools/new_school.py', at=now, school=key, empty=True))))
        db.commit()
    finally:
        db.close()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('key')
    ap.add_argument('--name', required=True)
    ap.add_argument('--short')
    ap.add_argument('--order', type=int)
    ap.add_argument('--site-uni', default='')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--schools-dir', default=str(CODE / 'schools'), help=argparse.SUPPRESS)
    ap.add_argument('--hierarchy-dir', default=str(P.HIERARCHY), help=argparse.SUPPRESS)
    ap.add_argument('--stores-dir', default=str(P.STORES), help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    if not re.fullmatch(r'[a-z0-9]+', a.key):
        ap.error('the key is lower-case letters and digits only')
    schools, hier, stores = Path(a.schools_dir), Path(a.hierarchy_dir) / a.key, Path(a.stores_dir) / a.key
    charter = schools / f'{a.key}.toml'
    taken = [str(p) for p in (charter, hier, stores) if p.exists()]
    if taken:
        raise SystemExit('refused: already exists: ' + ', '.join(taken))
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    text = charter_text(a.key, a.name, a.short or a.name.replace('University of ', ''), a.order or next_order(schools), a.site_uni, now[:10], schools / 'TEMPLATE.toml')
    plan = [f'charter  {charter}', f'folders  {hier}/{{{",".join(SUBDIRS)}}}', f'store    {stores} (empty catalog.sqlite, never a copy of another school\'s)']
    print('\n'.join(plan))
    if a.dry_run:
        print('dry run: nothing was made')
        return 0
    charter.write_text(text)
    for d in SUBDIRS:
        (hier / d).mkdir(parents=True)
    make_store(stores, a.key, now)
    (hier / 'reports' / 'new-school.json').write_text(json.dumps(dict(school=a.key, name=a.name, at=now, charter=str(charter), store=str(stores), stage=0), indent=1) + '\n')
    probs = S.check(a.key) if schools.resolve() == Path(P.SCHOOL_CONFIGS).resolve() else []
    print(f'made {a.key}. Stage 0 is open: fill {charter.name} (TEMPLATE.toml documents every field), then `atlas charters`, and run the stage with `atlas stage-gate {a.key} 0 --run` (docs/ADDING-A-SCHOOL.md: each stage runs to its first review step).')
    for p in probs:
        print('  to do: ' + p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
