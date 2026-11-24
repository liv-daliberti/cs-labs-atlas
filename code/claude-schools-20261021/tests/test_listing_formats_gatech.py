"""Georgia Tech listing formats: Drupal 7 gt-person-box (2016-2023), Drupal 9 profile cards (2023-), ECE and ISyE templates (excerpts of real captures)."""
import listing_formats as F

GT_PEOPLE = """<div class="gt-person-box vcard block"><div class='block-title-wrapper'><h4 class='name fn'><a href="/people/mostafa-ammar">Mostafa Ammar</a></h4></div>
<div class='gt-people-content clearfix'>Regents&#039; Professor; Associate Chair <br /><strong>Research Areas:</strong> Networks<br /><a href="mailto:m@x">Email</a></div></div>
<div class="gt-person-box vcard"><h4 class='name fn'><a href="/people/9744/a-b">Alexandra Boldyreva</a></h4><div class='gt-people-content'>Associate Professor E-Mail</div></div>
<ul class="pager"><li><a href="/people/faculty?title=&amp;page=1">2</a></li></ul>"""

GT_CARD = """<div class="row profile-card__content variant-directory"><div class="card-block"><h4 class="card-block__title"><a href="/people/jacob-abernethy" hreflang="en">Jacob Abernethy</a></h4>
<h6 class="card-block__subtitle mb-2 text-muted">Associate Professor</h6></div></div>
<div class="row profile-card__content variant-directory"><div class="card-block"><h4 class="card-block__title"><a href="/people/x-y">X Y</a></h4>
<h6 class="card-block__subtitle mb-2 text-muted">Executive Director, Institute for Data…</h6></div></div>"""

ECE_OLD = """<div class="faculty-staff-information"><div class="field-full-name"><a href="/faculty-staff-directory/cecil-o-alford">Cecil  O  Alford</a></div>
<div class="field-jobtitle">Professor Emeritus</div></div>"""

ECE_NEW = """<div data-history-node-id="1375" class="node"><a href="/directory/ali-adibi"><div class="field field--name-field-person-name field--type-name field--label-hidden"><div class="field__item">Ali Adibi</div></div></a>
<div class="top-padding-5px field field--name-field-person-official-job-title field--type-string"><div class="field__item">Professor</div></div></div>"""

ISYE_OLD = """<!-- Person --><div class="fields"><div class="info"><h4 class="name"><a href="/users/christos-alexopoulos">
 Christos Alexopoulos </a></h4><div class="views-field views-field-field-emp-title"><div class="field-content">Professor</div></div></div></div>
<!-- Person --><div class="fields"><h4 class="field-content name"><a href="/users/s-a">Shabbir Ahmed</a></h4><div class="views-field views-field-field-emp-title"><div class="field-content">Anderson-Interface Chair and Professor</div></div></div>"""

ISYE_CARD = """<div class="w-100 px-0 pt-0 person-name"><a href="/users/sigrun-andradottir" target="_blank"><a href="/users/sigrun-andradottir" hreflang="en">Sigrun Andradottir</a></a></div>
      <div class="person-type fs8">Professor    </div>"""


def test_gt_people_keeps_entity_apostrophes_and_drops_email_text():
    name, rows = F.parse(GT_PEOPLE)
    assert name == 'gt_people' and [r['name_listed'] for r in rows] == ['Mostafa Ammar', 'Alexandra Boldyreva']
    assert rows[0]['titles'] == ["Regents' Professor", 'Associate Chair'] and rows[1]['titles'] == ['Associate Professor']
    assert rows[0]['homepage'] == '/people/mostafa-ammar'


def test_a_gt_pager_with_an_escaped_page_link_is_paged():
    assert F.is_paged(GT_PEOPLE) and not F.is_paged(GT_CARD)


def test_gt_card_titles_may_be_truncated_by_the_site():
    name, rows = F.parse(GT_CARD)
    assert name == 'gt_card' and rows[0]['titles'] == ['Associate Professor'] and rows[1]['titles'] == ['Executive Director, Institute for Data…']


def test_ece_and_isye_templates():
    assert F.parse(ECE_OLD) == ('ece_old', [dict(name_listed='Cecil O Alford', titles=['Professor Emeritus'], homepage='/faculty-staff-directory/cecil-o-alford', division=None)])
    n, r = F.parse(ECE_NEW); assert n == 'ece_new' and r[0]['name_listed'] == 'Ali Adibi' and r[0]['titles'] == ['Professor'] and r[0]['homepage'] == '/directory/ali-adibi'
    n, r = F.parse(ISYE_OLD); assert n == 'isye_old' and [x['name_listed'] for x in r] == ['Christos Alexopoulos', 'Shabbir Ahmed'] and r[1]['titles'] == ['Anderson-Interface Chair and Professor']
    n, r = F.parse(ISYE_CARD); assert n == 'isye_card' and r[0]['name_listed'] == 'Sigrun Andradottir' and r[0]['titles'] == ['Professor']
