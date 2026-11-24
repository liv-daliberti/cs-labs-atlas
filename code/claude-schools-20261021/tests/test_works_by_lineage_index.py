"""works_by_lineage reads work_inst through its own index (JHU sweep: the default plan scanned works_year, 100 s a query) and returns the rows the old query did."""
import sqlite3

import oa_snapshot as S

OLD = 'SELECT w.body, w.id FROM work_inst i JOIN works w ON w.id=i.work_id WHERE i.inst=?'


def db():
    c = sqlite3.connect(':memory:')
    c.executescript(S.SCHEMA + S.INDEXES)
    for n in range(200):
        wid = f'W{n:04d}'
        c.execute('insert into works values (?,?,?,?,?,?,?)', (wid, None, 2016 + n % 11, 'article', wid, '2026-10-01', b'x'))
        for inst in ('I1', 'I2') if n % 3 == 0 else ('I1',) if n % 2 else ('I3',):
            c.execute('insert into work_inst values (?,?)', (wid, inst))
    c.execute('analyze')
    return c


def test_same_rows_as_the_old_query_with_and_without_a_year():
    c = db()
    for inst in ('I1', 'I2', 'I3', 'I9'):
        assert c.execute(S.LINEAGE_Q + ' ORDER BY w.id', (inst,)).fetchall() == c.execute(OLD + ' ORDER BY w.id', (inst,)).fetchall()
        for y in (2016, 2020, 2026):
            assert c.execute(S.LINEAGE_Q + ' AND w.year=? ORDER BY w.id', (inst, y)).fetchall() == c.execute(OLD + ' AND w.year=? ORDER BY w.id', (inst, y)).fetchall()


def test_the_plan_uses_the_institution_index_not_works_year():
    plan = ' '.join(r[3] for r in db().execute('explain query plan ' + S.LINEAGE_Q + ' AND w.year=? ORDER BY w.id', ('I1', 2020)))
    assert 'work_inst_inst' in plan and 'works_year' not in plan
