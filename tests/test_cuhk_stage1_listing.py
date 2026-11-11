import listing_formats as F


def test_cuhk_cse_faculty_table_keeps_role_and_profile_without_contact():
    page = '''<table class="foo-table"><tr><th>Photo</th><th>Name</th><th>Email</th>
    <th>Phone</th><th>Office</th><th>Position</th></tr>
    <tr><td></td><td><a href="/people/faculty/alice/">Alice Example</a></td>
    <td>alice@cse.cuhk.edu.hk</td><td>3943 0000</td><td>Room 12</td>
    <td>Associate Professor</td></tr>
    <tr><td></td><td>Bob Example</td><td></td><td></td><td></td>
    <td>Professor (by courtesy)</td></tr></table>'''
    name, rows = F.parse(page)
    assert name == 'cuhk_cse_faculty_table'
    assert rows == [
        dict(name_listed='Alice Example', titles=['Associate Professor'],
             homepage=None, division=None, profile='/people/faculty/alice/'),
        dict(name_listed='Bob Example', titles=['Professor (by courtesy)'],
             homepage=None, division=None, profile=None),
    ]
