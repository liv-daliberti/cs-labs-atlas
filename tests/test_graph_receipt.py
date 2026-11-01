"""A catalog without a 'graph' receipt must not stop the collector's export (Michigan, 2026-11-01)."""
import json
import sqlite3
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]
for d in (CODE / 'fulltext-push', CODE / 'vendor' / 'homogenizing_scripts'):
    if str(d) not in sys.path:
        sys.path.append(str(d))
import add_works as A  # noqa: E402
import collect_princeton_fulltext as C  # noqa: E402


def make(tmp_path):
    (tmp_path / 'catalog.sqlite').touch()
    db = sqlite3.connect(str(tmp_path / 'catalog.sqlite'))
    db.execute('CREATE TABLE receipts (key TEXT PRIMARY KEY, value TEXT)')
    db.execute("INSERT INTO receipts VALUES ('created', 'onboarding')")
    db.commit()
    return db


def test_export_reads_no_graph_as_none_and_a_graph_as_json(tmp_path):
    db = make(tmp_path)
    assert C.source_graph(db) is None
    db.execute("INSERT INTO receipts VALUES ('graph', ?)", (json.dumps({'works': 3}),)); db.commit()
    assert C.source_graph(db) == {'works': 3}


def test_add_works_writes_the_graph_receipt_once_under_the_lock(tmp_path):
    db = make(tmp_path)
    assert A.ensure_graph_receipt(db, 'michigan', 12455) is True
    assert A.ensure_graph_receipt(db, 'michigan', 99) is False
    assert C.source_graph(db)['works'] == 12455
    assert (tmp_path / '.catalog-write.lock').exists()
