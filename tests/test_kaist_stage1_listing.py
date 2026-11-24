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
