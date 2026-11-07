from listing_formats import parse
from listing_rows import rank_of


def test_oxford_semantic_person_roles_and_missing_link():
    html = '<li itemscope="itemscope" class="personIndex"><a href="/people/A"><span itemprop="name">Alex Smith</span></a><span class="list-unbulleted-extra">Associate Professor of Computer Science</span></li><li class="personIndex"><span itemprop="name">Robin Doe</span><span class="list-unbulleted-extra">Doctoral Student, Departmental Lecturer</span></li>'
    fmt, rows = parse(html)
    assert fmt == 'oxford_person_index'
    assert len(rows) == 2
    assert rows[0]['homepage'] == '/people/A'
    assert rank_of(rows[0]['titles']) == 'ladder'
    assert rows[1]['homepage'] is None
    assert rank_of(rows[1]['titles']) != 'ladder'


def test_cambridge_keeps_literal_roles_and_discards_contacts():
    html = '<table><tr><td class="views-field views-field-title"><a href="/people/ab1">Alex Smith (emeritus)</a></td><td>0123456789</td><td class="views-field views-field-field-sd-classifications-ref"><a href="/faculty">Faculty</a></td></tr><tr><td class="views-field views-field-title"><a href="/people/cd2">Robin Doe</a></td><td class="views-field views-field-field-sd-classifications-ref"><a href="/students">PhD students</a></td></tr></table>'
    fmt, rows = parse(html)
    assert fmt == 'cambridge_directory'
    assert rows[0]['name_listed'] == 'Alex Smith'
    assert rows[0]['titles'] == ['Faculty', 'emeritus']
    assert rank_of(rows[0]['titles']) == 'emeritus'
    assert rows[1]['titles'] == ['PhD students']
    assert rank_of(['Faculty']) == 'other'
    assert '0123456789' not in str(rows)


def test_cambridge_profile_uses_explicit_title_field_only():
    html = '<h1 class="campl-sub-title">Prof Cecilia Mascolo FRS </h1><div class="cst-job-titles campl-no-top-padding"><ul><li>Professor of Mobile Systems</li></ul></div><p>Former professor somewhere else; contact details here.</p>'
    _, rows = parse(html, 'cambridge_profile')
    assert rows == [dict(name_listed='Cecilia Mascolo', titles=['Professor of Mobile Systems'], homepage=None, division=None)]
    assert parse('<h1 class="campl-sub-title">Someone</h1><p>My adviser is a Professor.</p>', 'cambridge_profile')[1] == []
