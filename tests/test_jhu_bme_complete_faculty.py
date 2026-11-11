import listing_formats as F


def test_old_bme_complete_faculty_keeps_department_section_and_credentials_out():
    html = '''<div id="main-content"><h1>JHU BME complete faculty listing</h1>
      <h2>All Department Faculty</h2><table class="stripe"><tr>
      <td class="people"><a href="/people/primary.php?id=1">Alex B. Example, PhD</a></td>
      <td class="people">Professor of Biomedical Engineering</td></tr></table>
      <h2>Institute Faculty in Other Departments</h2><table class="stripe"><tr>
      <td class="people">Robin Example, MD</td><td class="people">Professor</td>
      <td class="people">Electrical and Computer Engineering</td></tr></table></div>'''
    fmt, rows = F.parse(html)
    assert fmt == 'jhu_bme_complete_faculty'
    assert rows == [dict(name_listed='Alex B. Example',
                         titles=['Professor of Biomedical Engineering'],
                         homepage='/people/primary.php?id=1',
                         division='All Department Faculty')]
