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


def test_openalex_extension_needs_unique_candidate_and_share():
    c = dict(name='Hang Tu', aliases=[], source='openalex_rule', openalex=['https://openalex.org/A1'], oa_cs_share=1.0, oa_works=9)
    people = [dict(name='涂航')]
    assert [(p, x['openalex'][0]) for p, x in B.oa_bind(people, [c])] == [('涂航', 'https://openalex.org/A1')]
    assert B.oa_bind(people, [c, dict(c, source='dblp_affiliation')]) == []
    assert B.oa_bind(people, [dict(c, oa_cs_share=0.5)]) == []


def test_alias_spellings_of_one_candidate_do_not_block():
    c = dict(name='Zongpeng Li', aliases=['Li Zongpeng', 'Zongpeng  Li'], source='openalex_rule', openalex=['https://openalex.org/A9'], oa_cs_share=0.9, oa_works=83)
    assert len(B.oa_bind([dict(name='李宗鹏')], [c])) == 1
