"""An HTTP 200 access challenge may still contain genuine paper titles and links."""
import sqlite3

import labpage_channel as lc


def test_access_receipt_with_research_content_cannot_supply_bibliography(tmp_path, monkeypatch):
    database = tmp_path / 'captures.sqlite'
    body = b'<p>Federated clinical queries <a href="paper.pdf">PDF</a></p>'
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE captures (id INTEGER PRIMARY KEY, url TEXT, final_url TEXT, '
                   'capture_url TEXT, status INTEGER, content_type TEXT, content BLOB, error TEXT)')
        for number, (name, error) in enumerate([
                ('challenge', 'bot-challenge'), ('valid', None), ('valid-empty-error', '')], 1):
            db.execute('INSERT INTO captures VALUES (?, ?, NULL, NULL, 200, ?, ?, ?)',
                       (number, 'https://lab.example/' + name, 'text/html', body, error))
    monkeypatch.setattr(lc, 'captures_db', lambda school: database)

    rows = list(lc.iter_captures('harvard'))

    assert [row[0] for row in rows] == ['https://lab.example/valid', 'https://lab.example/valid-empty-error']
    assert all(row[-1] == body for row in rows)
