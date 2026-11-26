import eth_js_hand as E


def test_professor_section_only_for_professor_lists():
    assert E.professor_section('https://hest.ethz.ch/en/department/people/professors.html')
    assert E.professor_section('https://baug.ethz.ch/en/department/people/professors.html')
    assert E.professor_section('https://www.phys.ethz.ch/the-department/people/professors.html')
    assert E.professor_section('https://ethz.ch/en/the-eth-zurich/organisation/who-is-who/mtec.html')


def test_general_people_lists_are_not_ladder_evidence():
    for url in ('https://mtec.ethz.ch/people.html', 'https://baug.ethz.ch/en/department/people/staff.html',
                'https://biol.ethz.ch/en/the-department/people.html', 'https://bsse.ethz.ch/people.html',
                'https://mat.ethz.ch/department/people.html', 'https://www.phys.ethz.ch/the-department/people.html'):
        assert not E.professor_section(url)
