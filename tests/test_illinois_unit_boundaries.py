import cs_related_school as C


def test_entry_boundary_cannot_borrow_the_next_persons_professor_title():
    html = '''<div class="directory-list">
      <div class="item person"><div class="name">Alex Researcher</div><div class="title">Research Engineer</div></div>
      <div class="item person"><div class="name">Pat Faculty</div><div class="title">Professor</div></div>
      <div class="item person"><div class="name">Lee Retired</div><div class="title">EMER PROF</div></div>
      <div class="item person"><div class="name">Chris Faculty</div><div>they/them</div><div class="title">Associate Professor</div></div>
      </div>'''
    url = 'https://example.edu/faculty'
    flat = C.W.flat(C.W.extract.blocks(html.encode(), 'text/html', url))
    bounded = C.directory_entry_text(html, url, flat)
    pages = [('UNIT', url, 'hash', '20261123', bounded)]
    assert not C.faculty_evidence(pages, ['Alex Researcher'])
    assert not C.faculty_evidence(pages, ['Lee Retired'])
    assert C.faculty_evidence(pages, ['Pat Faculty'])[0]['ladder']
    evidence = C.faculty_evidence(pages, ['Chris Faculty'])[0]
    assert evidence['ladder'] and evidence['quote'] in flat
