import dblp_pinyin_binding_school as B


def rec(pid, *names):
    return dict(pid=pid, names=list(names), school_note='Wuhan University', orcid=[], sha256='s')


def test_keys_cover_both_orders():
    k = B.keys_of('何德彪')
    assert 'debiaohe' in k and 'hedebiao' in k


def test_unique_on_both_sides_binds():
    got = B.bind([dict(name='何德彪', evidence=None)], [rec('p1', 'Debiao He')])
    assert [(p, r['pid']) for p, r in got] == [('何德彪', 'p1')]


def test_two_dblp_records_bind_nobody():
    assert B.bind([dict(name='何德彪', evidence=None)], [rec('p1', 'Debiao He'), rec('p2', 'Debiao He 0002')]) == []


def test_roster_homophones_bind_nobody():
    people = [dict(name='李艳', evidence=None), dict(name='李燕', evidence=None)]
    assert B.bind(people, [rec('p1', 'Yan Li')]) == []
