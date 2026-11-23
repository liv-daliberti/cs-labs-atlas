import listing_formats as LF
import school_config as S
from listing_rows import listing_rank


def test_illinois_cards_preserve_titles_profiles_and_slot_categories():
    html = '''<nav><a href="/fake">Menu Person</a></nav>
      <div class="directory-list">
        <div class="item person cat15"><div class="details">
          <div class="name"><a href="/people/adve">Sarita V Adve</a></div>
          <div class="title">Richard T. Cheng Professor</div>
          <div class="contact">private@example.org 555-1234</div>
        </div></div>
        <div class="item person cat5"><div class="details">
          <div class="name"><a href="/people/chen">Deming Chen</a></div>
          <div class="title">Professor, Electrical and Computer Engineering</div>
        </div></div>
        <div class="item person"><div class="details">
          <div class="name"><a href="/people/teacher">Example Teacher</a></div>
          <div class="title">Teaching Associate Professor</div>
        </div></div>
        <div class="item person"><div class="name">No evidence</div></div>
      </div>'''
    _, rows = LF.parse(html, 'illinois_directory_cards')
    assert len(rows) == 3
    assert rows[0] == dict(name_listed='Sarita V Adve', titles=['Richard T. Cheng Professor'], profile='/people/adve')
    assert listing_rank(rows[0]['titles'], [], 'main') == 'ladder'
    assert listing_rank(rows[1]['titles'], [], 'courtesy') == 'courtesy'
    ranks = S.field(S.get('uiuc'), 'census.rank_words')
    assert listing_rank(rows[2]['titles'], [], 'main', ranks) == 'teaching'
    assert listing_rank(['Research Associate Professor'], [], 'main', ranks) == 'research'
    assert listing_rank(['Asst Prof'], [], 'main', ranks) == 'ladder'
    assert all('private@' not in str(r) and '555-' not in str(r) for r in rows)


def test_cs_affiliate_and_adjunct_slots_do_not_admit_the_other_category():
    html = '''<div class="directory-list">
      <div class="item person cat5"><div class="details">
        <div class="name"><a href="/a">Faculty Affiliate</a></div>
        <div class="title">Professor, Electrical and Computer Engineering</div>
      </div></div>
      <div class="item person cat3"><div class="details">
        <div class="name"><a href="/b">Faculty Adjunct</a></div>
        <div class="title">Professor, Another Institution</div>
      </div></div></div>'''
    _, affiliates = LF.parse(html, 'illinois_cs_affiliates')
    _, adjuncts = LF.parse(html, 'illinois_cs_adjuncts')
    assert [r['name_listed'] for r in affiliates] == ['Faculty Affiliate']
    assert [r['name_listed'] for r in adjuncts] == ['Faculty Adjunct']
    assert listing_rank(adjuncts[0]['titles'], [], 'adjunct') == 'adjunct'
