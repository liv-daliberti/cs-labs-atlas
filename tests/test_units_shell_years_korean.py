import cs_related_school as CR


def test_korean_directory_is_not_a_shell():
    ko = '교수 ' + ' '.join(f'김아무개{i} 부교수 연구분야 전산이론 사무실 N1 {i}' for i in range(30))
    en = ' '.join(f'Person{i} Associate Professor of Computer Science, Office {i}' for i in range(30))
    assert not CR.shell_capture(ko) and not CR.shell_capture(en)


def test_shells_and_nav_pages_still_fail():
    assert CR.shell_capture('')
    assert CR.shell_capture(None)
    assert CR.shell_capture('You need to enable JavaScript to run this app. ' * 20)          # long, no titles
    assert CR.shell_capture('교수 Professor Professor')                                      # titles but under 500 characters
    assert CR.shell_capture('x' * 600 + ' 교수 교수')                                       # only two titles
