import dblp_url_binding_school as B


def row(name, prof, cap='https://web.archive.org/web/20230101000000id_/https://cs.x.edu.cn/szdw/list.htm'):
    return dict(name=name, profile=prof, capture_url=cap, sha256='h', quote=name)


def rec(pid, *urls):
    return dict(pid=pid, urls=list(urls), names=['A B'], orcid=[], sha256='s', n_dblp=len(urls))


def test_relative_profile_binds_by_exact_url():
    got = B.bind([row('王伟', '../info/1019/2493.htm')], [rec('p1', 'http://cs.x.edu.cn/info/1019/2493.htm'), rec('p2', 'http://other/')])
    assert [(g[0], g[1]['pid']) for g in got] == [('王伟', 'p1')]


def test_shared_url_or_two_records_bind_nobody():
    assert B.bind([row('甲', '../a.htm'), row('乙', '../a.htm')], [rec('p1', 'https://cs.x.edu.cn/a.htm')]) == []
    assert B.bind([row('甲', '../a.htm')], [rec('p1', 'https://cs.x.edu.cn/a.htm'), rec('p2', 'cs.x.edu.cn/a.htm')]) == []
