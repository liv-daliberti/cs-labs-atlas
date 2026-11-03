"""oa_institutions: name search and lineage children from a snapshot's institutions table."""
import sqlite3

import oa_institutions as I
import oa_snapshot as O

OA = 'https://openalex.org/'


def test_search_and_lineage(tmp_path, monkeypatch):
    d = tmp_path / '2026-10-14'; d.mkdir()
    db = sqlite3.connect(d / 'openalex.sqlite'); db.executescript(O.SCHEMA)
    for i, n, lin, typ in [('I1', 'University of X', ['I1'], 'education'), ('I2', 'X National Laboratory', ['I2', 'I1'], 'facility'), ('I3', 'Y University', ['I3'], 'education')]:
        db.execute('insert into institutions values (?,?,?,?)', (OA + i, n, 'https://ror.org/' + i.lower(), O.pack(dict(id=OA + i, display_name=n, type=typ, country_code='US',
                                                                              lineage=[OA + x for x in lin], associated_institutions=[]))))
    db.commit(); db.close()
    (tmp_path / 'current').symlink_to('2026-10-14')
    monkeypatch.setattr(O, '_conns', {})
    assert [r[0] for r in I.search('x', root=tmp_path)] == ['I2', 'I1']   # starts with 'x' first
    me, kids = I.lineage('I1', root=tmp_path)
    assert me[1] == 'University of X' and kids == [('I2', 'X National Laboratory', 'facility')]
    assert [r[0] for r in I.search('univ', root=tmp_path, type_='education')] == ['I1', 'I3']
    assert [r[0] for r in I.search('national', root=tmp_path)] == ['I2']
    assert [r[0] for r in I.search('x', root=tmp_path, type_='facility')] == ['I2']


def test_children_counts(tmp_path, monkeypatch):
    d = tmp_path / '2026-10-14'; d.mkdir()
    db = sqlite3.connect(d / 'openalex.sqlite'); db.executescript(O.SCHEMA)
    for i, n, lin in [('I1', 'University of X', ['I1']), ('I2', 'X National Laboratory', ['I2', 'I1'])]:
        db.execute('insert into institutions values (?,?,?,?)', (OA + i, n, '', O.pack(dict(id=OA + i, display_name=n, type='education', country_code='US',
                                                                      lineage=[OA + x for x in lin], associated_institutions=[]))))
    for w, year, insts in [('W1', 2020, ['I1', 'I2']), ('W2', 2021, ['I2']), ('W3', 2022, ['I1']), ('W4', 2010, ['I2'])]:
        db.execute('insert into works (id, year, body) values (?,?,?)', (OA + w, year, O.pack(dict(id=OA + w, authorships=[dict(institutions=[dict(id=OA + i) for i in insts])]))))
    for w in ('W1', 'W2', 'W3', 'W4'):
        db.execute('insert into work_inst values (?,?)', (OA + w, 'I1'))   # the sweep stores the school's id for every kept work
    db.commit(); db.close()
    (tmp_path / 'current').symlink_to('2026-10-14')
    monkeypatch.setattr(O, '_conns', {})
    r = I.children_counts('I1', root=tmp_path)
    assert r == {'I1': ('University of X', 2, 0), 'I2': ('X National Laboratory', 2, 1)}
