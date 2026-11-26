import listing_formats as F


def test_kaist_cs_horiz_keeps_name_rank_group_and_profile():
    html = '''<div class="list_warp"><p class="line"><span>Professor</span></p><ul>
      <li class="horiz_item"><div class="item fix" onclick="facultyView(12, 160)"><div class="infoTxt">
      <p class="name">Doo\u00adHwan Bae </p><p class="depart">Professor, 석좌교수</p>
      <p class="text">Office: 503, N1<br/>042-350-3539</p></div></div></li></ul>
      <p class="line"><span>Emeritus</span></p><ul>
      <li class="horiz_item"><div class="item fix" onclick="facultyView(77, 160)"><div class="infoTxt">
      <p class="name">강민석</p><p class="depart">명예교수</p></div></div></li></ul></div>'''
    fmt, rows = F.parse(html)
    assert fmt == 'kaist_cs_horiz'
    assert rows == [
        dict(name_listed='DooHwan Bae', titles=['Professor, 석좌교수', 'Professor'], homepage=None, division='Professor',
             profile='/people/view?idx=12&kind=faculty', quote_name='Doo\u00adHwan Bae'),
        dict(name_listed='강민석', titles=['명예교수', 'Emeritus'], homepage=None, division='Emeritus',
             profile='/people/view?idx=77&kind=faculty'),
    ]


def test_kaist_gsds_people_lists_names_without_titles():
    html = '''<div class="people-list"><div class="people-list-item"><div class="people-list-item-cont"><strong>가현욱</strong>
      <ul><li><strong>Focus Area</strong><span>데이터사이언스 방법론</span></li><li><strong>E-mail</strong><span>hyun.ka@kaist.ac.kr</span></li></ul>
      <div class="people-list-item-cont-util"><a href="https://aailab.kaist.ac.kr">홈페이지</a></div></div></div>
      <div class="people-list-item"><div class="people-list-item-cont"><strong>강금석</strong></div></div></div>'''
    fmt, rows = F.parse(html)
    assert fmt == 'kaist_gsds_people'
    assert [(r['name_listed'], r['titles'], r['homepage']) for r in rows] == [('가현욱', [], 'https://aailab.kaist.ac.kr'), ('강금석', [], None)]
