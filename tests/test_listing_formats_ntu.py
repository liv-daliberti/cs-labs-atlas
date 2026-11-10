"""NTU SCSE 2021 faculty list: one real card (Wayback capture 20210515230315 of www.ntu.edu.sg/scse/about-us/our-people/faculty, e-mail removed)."""
from listing_formats import parse
from listing_rows import rank_of

CARD = '''<div class="card-rows__item"><div class="img-card img-card--horizontal img-card--portrait img-card--academic">
<div class="img-card__body"><h3 class="img-card__title"><a href="https://dr.ntu.edu.sg//cris/rp/rp00083" target="_blank">Assoc Prof A S Madhukumar<span class="icon icon-external-link"></span></a></h3>
<span class="img-card__subtitle">School of Computer Science and Engineering</span>
<p class="img-card__desc">A S Madhukumar received his B. Tech degree ... ...</p>
<p class="img-card__interests"><span class="label">Appointments: </span><br />Associate Professor, School of Computer Science and Engineering</p>
<p class="img-card__interests"><span class="label">Keywords:</span><br />Computer Science and Engineering</p></div></div></div>
<div class="img-card img-card--academic"><div class="img-card__body"><h3 class="img-card__title"><a href="https://dr.ntu.edu.sg//cris/rp/rp1">Dr Althea Liang</a></h3>
<p class="img-card__interests"><span class="label">Appointments: </span><br />Lecturer, School of Computer Science and Engineering<br />Associate Chair</p></div></div>'''


def test_ntu_scse_cards_name_without_honorific_titles_and_profile():
    fmt, rows = parse(CARD)
    assert fmt == 'ntu_img_cards' and len(rows) == 2
    assert rows[0]['name_listed'] == 'A S Madhukumar'
    assert rows[0]['titles'] == ['Associate Professor, School of Computer Science and Engineering']
    assert rows[0]['profile'].endswith('rp00083') and 'ntu.edu.sg' not in rows[0]['name_listed']
    assert rank_of(rows[0]['titles']) == 'ladder'
    assert rows[1]['name_listed'] == 'Althea Liang' and rows[1]['titles'][1] == 'Associate Chair'
    assert rank_of(rows[1]['titles']) != 'ladder'


def test_ntu_cards_ignore_other_markup():
    assert parse('<div class="img-card">no academic modifier</div>', 'ntu_img_cards')[1] == []
