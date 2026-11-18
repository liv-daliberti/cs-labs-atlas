import cs_related_school as C


def test_same_dblp_pid_is_the_census_person():
    census = {'王伟': dict(name='王伟', aliases=[], dblp=['https://dblp.org/pid/01/2122-1'])}
    assert C.census_alias(census, ['Wei Wang'], ['https://dblp.org/pid/01/2122-1']) == '王伟'
    assert C.census_alias(census, ['Wei Wang'], ['https://dblp.org/pid/99/1']) is None
