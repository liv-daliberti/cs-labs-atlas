"""Send identity passes that do not meet identity_rule.own_doi_title_ok back to the pending state (2026-11-03, ROADMAP #25).

A copy whose identity_check carries auto_alt_title_20261031 or auto_pdf_meta_title_20261102 is reverted to provider_link_only_review_pending
(works and assets rows) when its DOI is not an arXiv DOI and the title it was matched with shares under 80% of the shorter title's significant
words with the catalog title; --works <file> adds explicit (school, work id) pairs (a hand-judged doubtful pass). Under the catalog lock, after a
locked backup; every change is logged in <store>/staged/reverted-passes.jsonl (work, old tag, titles), so it is reversible. Nothing is deleted
and no file moves: a pending copy simply stops counting.
usage: identity_revert_doubtful.py plan|apply <school> ... [--works FILE]
"""
import json, sqlite3, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ftp_common as F  # noqa: E402
import identity_rule as R  # noqa: E402

TAGS = ('auto_alt_title_20261031', 'auto_pdf_meta_title_20261102', 'auto_alt_title_20261103')
PENDING = R.PENDING
OUT = F.P.ft_review('20261030')


def doubtful(school, extra=()):
    plan = OUT / f'identity-review-alt-{school}.json'
    titles = {x['work']: x.get('alt_title') for x in json.loads(plan.read_text())['rows']} if plan.exists() else {}
    db = sqlite3.connect(f'file:{F.FT / school / "catalog.sqlite"}?mode=ro', uri=True, timeout=120)
    out = []
    for w, t in titles.items():
        row = db.execute('SELECT identity_check, title, doi FROM works WHERE id=?', (w,)).fetchone()
        if row and row[0] in TAGS and not R.own_doi_title_ok(row[2], row[1], t):
            out.append(dict(work=w, tag=row[0], title=row[1], matched=t, doi=row[2]))
    for s, w in extra:
        if s == school:
            row = db.execute('SELECT identity_check, title, doi FROM works WHERE id=?', (w,)).fetchone()
            if row and row[0] in TAGS and not any(o['work'] == w for o in out):
                out.append(dict(work=w, tag=row[0], title=row[1], matched=titles.get(w), doi=row[2], explicit=True))
    db.close()
    return out


def apply(school, rows):
    store = F.FT / school
    F.backup_catalog(store, 'before-revert-passes')
    db = sqlite3.connect(str(store / 'catalog.sqlite'), timeout=120)
    db.execute('PRAGMA busy_timeout=120000')
    n = 0
    log = store / 'staged' / 'reverted-passes.jsonl'
    log.parent.mkdir(exist_ok=True)
    with log.open('a') as lf:
        for r in rows:
            with F.catalog_lock(store):
                c = db.execute('UPDATE works SET identity_check=? WHERE id=? AND identity_check=?', (PENDING, r['work'], r['tag'])).rowcount
                db.execute('UPDATE assets SET identity_check=? WHERE work_id=? AND identity_check=?', (PENDING, r['work'], r['tag']))
                db.commit()
            n += c
            lf.write(json.dumps(dict(r, reverted_at=F.now(), by='identity_revert_doubtful.py')) + '\n')
    db.close()
    return n


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    extra = []
    if '--works' in sys.argv:
        f = sys.argv[sys.argv.index('--works') + 1]
        extra = [tuple(x) for x in json.load(open(f))]
        args = [a for a in args if a != f]
    cmd, schools = args[0], args[1:]
    for s in schools:
        rows = doubtful(s, extra)
        print(json.dumps(dict(school=s, doubtful=len(rows), **({'reverted': apply(s, rows)} if cmd == 'apply' and rows else {}))), flush=True)
