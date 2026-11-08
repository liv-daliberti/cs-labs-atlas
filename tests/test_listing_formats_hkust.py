from listing_formats import parse
from listing_rows import rank_of


def test_hkust_bilingual_names_roles_and_profiles_without_contact_cells():
    html = '''<table><tr><th>Name</th><th>Rank</th></tr>
    <tr class="search"><td class="name"><a href="profile/zxf">Xiaofang ZHOU<br>周曉方</a></td>
    <td>Named Professor of Engineering<br>&nbsp;Chair Professor and Head</td>
    <td><a href="javascript:msend('zxf')">private-contact</a></td><td>55551234</td></tr>
    <tr class="search"><td class="name"><a href="profile/other">Robin EXAMPLE</a></td>
    <td>Visiting Professor</td><td>another-contact</td></tr></table>'''
    _, rows = parse(html, 'hkust_faculty_table')
    assert len(rows) == 2
    assert rows[0]['name_listed'] == 'Xiaofang ZHOU 周曉方'
    assert rows[0]['titles'] == ['Named Professor of Engineering', 'Chair Professor and Head']
    assert rows[0]['profile'] == 'profile/zxf'
    assert rows[0]['homepage'] is None
    assert rank_of(rows[0]['titles']) == 'ladder'
    assert rank_of(rows[1]['titles']) == 'visiting'
    assert 'private-contact' not in str(rows)
    assert '55551234' not in str(rows)


def test_hkust_ignores_unlinked_and_incomplete_table_rows():
    html = '<tr class="search"><td class="name">No link</td><td>Professor</td></tr>'
    assert parse(html, 'hkust_faculty_table')[1] == []
