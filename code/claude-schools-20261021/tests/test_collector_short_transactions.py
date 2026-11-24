"""The collector holds sqlite's lock only in short transactions (ROADMAP #20 follow-up, 2026-11-02): the pass-start backfill takes the catalog
write lock, and export() reads with fetchall() so no cursor stays open while files are written (an open cursor keeps the shared lock and
makes every other writer fail with 'database is locked')."""
import re
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
V = CODE / 'vendor' / 'homogenizing_scripts'


def test_the_pass_start_backfill_holds_the_catalog_lock():
    s = (V / 'collect_princeton_fulltext_expanded.py').read_text()
    i = s.index("with CL.catalog_lock(args.out)")
    j = s.index('INSERT OR IGNORE INTO assets', i)
    k = s.index('db.commit()', j)
    assert i < j < k and s[i:k].count('\n') < 12  # the insert and its commit are inside the lock block


def test_export_does_not_iterate_open_cursors():
    s = (V / 'collect_princeton_fulltext.py').read_text()
    body = s[s.index('def export('):]
    body = body[:body.index('\ndef ', 10)] if '\ndef ' in body[10:] else body
    for m in re.finditer(r'for \w+ in db\.execute\(', body):
        line = body[m.start():body.index('\n', m.start())]
        assert '.fetchall()' in line or 'LIMIT' in line, line[:120]
    e = (V / 'collect_princeton_fulltext_expanded.py').read_text()
    fin = e[e.index('def finish('):e.index('def ', e.index('def finish(') + 5)]
    assert 'db.execute(\'SELECT * FROM assets ORDER BY work_id,kind,url\').fetchall()' in fin
    assert not re.search(r'for \w+ in db\.execute\((?:(?!fetchall).)*\):\n', fin)


def test_the_expanded_collector_still_imports():
    import collect_princeton_fulltext_expanded as c  # noqa: E402
    assert hasattr(c, 'CL') and hasattr(c.CL, 'catalog_lock')
