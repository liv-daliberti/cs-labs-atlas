"""NTU unit-directory formats (EEE/CEE cards, WKWSCI/ADM/SBS profile lists, SPMS tables, Medicine table): real markup, shortened, no contact cells."""
import cs_related_school as CR
from listing_formats import ntu_unit_text, parse
from listing_rows import rank_of

EEE = '''<article class="coe-about-leadership__card" data-faculty-card data-category="associate-professor" data-name="Andy Wai Hoong KHONG" data-email="[email removed]">
<img alt="Andy Wai Hoong Khong"><h3 class="coe-about-leadership__name">Andy Wai Hoong KHONG</h3><p class="coe-about-leadership__role">Associate Professor</p>
<p class="coe-about-leadership__contact"><a href="https://dr.ntu.edu.sg/entities/person/Andy-Khong">Profile</a></p></article>'''
WKW = '''<div class="ntu-profile-list"><div class="profile-row"><div class="profile-row-content"><h3 class="profile-row-name"><a href="https://dr.ntu.edu.sg/cris/rp/rp00497"><span class="name-text">Prof Lee Chei Sian</span></a></h3>
<div class="profile-row-designation">Associate Chair, Faculty</div></div></div></div>'''
SBS = '''<div class="ntu-profile-list"><div class="profile-card"><div class="profile-card-content"><h3 class="profile-card-name"><a href="/sbs/lab"><span class="name-text">Sabapathy, Kanaga</span></a></h3>
<div class="profile-card-designation">Professor and Chair<br>Lee Wee Nam Professor<br></div></div></div></div>'''
SPMS = '''<td style="width: 18%">x</td><td style="line-height: normal"><strong style="font-size: 110%">BRUNO, Annalisa</strong> <br><span style="font-size: 94%">Associate Professor</span> <br>
<div><a href="https://dr.ntu.edu.sg/cris/rp/rp02344">Profile</a> | <a href="mailto:[email removed]">mail</a></div></td>'''
MED = '''<table><thead><tr><th colspan="3">Faculty and Joint Faculty</th></tr></thead><tbody><tr><td><a href="https://dr.ntu.edu.sg/cris/rp/rp01310">​Prof Joseph SUNG​</a></td>
<td>​Dean<br>Distinguished University Professor</td><td>[email removed]</td></tr></tbody></table>'''


def test_each_format_emits_name_without_honorific_or_capitals_and_titles():
    f, r = parse(EEE); assert f == 'ntu_coe_cards' and r[0]['name_listed'] == 'Andy Wai Hoong Khong' and r[0]['titles'] == ['Associate Professor']
    f, r = parse(WKW); assert f == 'ntu_profile_cards' and r[0]['name_listed'] == 'Lee Chei Sian' and r[0]['titles'][0] == 'Professor'
    f, r = parse(SBS); assert r[0]['name_listed'] == 'Kanaga Sabapathy' and r[0]['titles'] == ['Professor and Chair', 'Lee Wee Nam Professor']
    f, r = parse(SPMS); assert f == 'ntu_spms_table' and r[0]['name_listed'] == 'Annalisa Bruno' and rank_of(r[0]['titles']) == 'ladder'
    f, r = parse(MED); assert f == 'ntu_medicine_table' and r[0]['name_listed'] == 'Joseph Sung' and 'Dean' in r[0]['titles']


def test_no_contact_cells_in_the_verification_text():
    for h in (EEE, WKW, SBS, SPMS, MED):
        t = ntu_unit_text(h)
        assert '@' not in t and 'mailto' not in t


def test_review_finds_dblp_style_name_with_initials_on_an_uppercase_surname_page():
    text = ntu_unit_text(EEE)
    ev = CR.faculty_evidence([('EEE', 'https://www.ntu.edu.sg/eee/about-us/our-people', 'a' * 64, '20261110', text)], ['Andy W. H. Khong'])
    assert len(ev) == 1 and ev[0]['ladder'] and ev[0]['quote'].startswith('Andy Wai Hoong Khong')
    ev = CR.faculty_evidence([('SPMS', 'u', 'a' * 64, '20261110', ntu_unit_text(SPMS))], ['Annalisa Bruno'])
    assert len(ev) == 1 and ev[0]['ladder']
