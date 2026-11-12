from tools import listing_formats as LF


def test_berkeley_directory_keeps_faculty_only():
    html = '''<table class="eecs-static-table"><tbody>
      <tr><td><a href="/faculty/a">A, Ada</a></td><td></td><td></td><td></td><td>Faculty</td><td>CS</td><td></td></tr>
      <tr><td>B, Bob</td><td></td><td></td><td></td><td>Staff</td><td>EECS</td><td></td></tr>
      <tr><td>C, Cal</td><td></td><td></td><td></td><td>Lecturer</td><td>EECS</td><td></td></tr>
      </tbody></table>'''
    rows = LF.berkeley_eecs_directory(html)
    assert [(r['name_listed'], r['titles']) for r in rows] == [
        ('A, Ada', ['Faculty']), ('C, Cal', ['Lecturer'])]


def test_berkeley_faculty_old_and_new_layouts():
    html = '''<table><tr><td><strong><a href="/Faculty/Homepages/ada.html">Ada A</a></strong><br>Professor</td></tr></table>
      <div class="cc-image-list__item"><div class="cc-image-list__item__content">
      <h3><a href="/Faculty/Homepages/bob.html">Bob B</a></h3><p><strong>Associate Professor</strong></p>
      </div></div>'''
    assert [(r['name_listed'], r['titles'][0]) for r in LF.berkeley_eecs_faculty(html)] == [
        ('Ada A', 'Professor'), ('Bob B', 'Associate Professor')]
