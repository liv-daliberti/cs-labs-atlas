"""Johns Hopkins listing formats (excerpts of real captures)."""
import listing_formats as F
import listing_rows as R

WSE = """<ul class="entity_list_items" id="item_list" aria-label="Faculty"><li class="entity_list_item"><div class="entity" itemscope itemtype="https://schema.org/Person"><div class="entity_header"><div class="entity_info">
<h2 class="entity_name" itemprop="name"><a class="entity_name_link" href="https://www.cs.jhu.edu/faculty/yair-amir/">Yair Amir</a></h2>
<div class="entity_title">Professor Emeritus</div><div class="entity_department"><a href="https://www.cs.jhu.edu/"><span>Department of Computer Science</span></a></div></div></div></div></li>
<li class="entity_list_item"><div class="entity"><h2 class="entity_name" itemprop="name"><a class="entity_name_link" href="https://www.cs.jhu.edu/faculty/jason-eisner/">Jason Eisner</a></h2>
<div class="entity_title">Bloomberg Distinguished Professor</div></div></li></ul>"""


def test_wse_entity_reads_name_title_and_homepage():
    name, rows = F.parse(WSE)
    assert name == 'wse_entity' and [r['name_listed'] for r in rows] == ['Yair Amir', 'Jason Eisner']
    assert rows[0]['titles'] == ['Professor Emeritus'] and rows[1]['titles'] == ['Bloomberg Distinguished Professor']
    assert rows[0]['homepage'].endswith('/faculty/yair-amir/')


# Visible excerpts of the two official CS contact lists, retrieved 2026-11-06.
# Source receipts (raw SHA-256 and URL) are in JHU's STAGE-1-SOURCE-REVIEW.md.
CONTACTS = '''<div class="contact_block"><script type="application/ld+json">
{"@type":"Person","name":"Roy Adams","jobTitle":"Assistant Professor, Psychiatry and Behavioral Sciences"}
</script><div class="contact_info"><h2 class="contact_name">Roy Adams</h2>
<div class="contact_title">Assistant Professor, Psychiatry and Behavioral Sciences</div>
<div class="contact_links"><a class="contact_link" href="https://royadams.github.io/">
<span class="contact_link_label">Personal Website</span></a></div></div></div>
<div class="contact_block"><div class="contact_info"><h2 class="contact_name">Joel Bader</h2>
<div class="contact_title">Professor, Biomedical Engineering &amp; Oncology</div>
<a class="contact_link" href="https://www.bme.jhu.edu/people/faculty/joel-bader/">
<span class="contact_link_label">Faculty Profile</span></a></div></div>'''


def test_wse_contact_reads_visible_entries_once_and_separates_profile_from_homepage():
    fmt, rows = F.parse(CONTACTS)
    assert fmt == 'wse_contact'
    assert len(rows) == CONTACTS.count('class="contact_name"') == 2
    assert rows[0] == dict(name_listed='Roy Adams', titles=['Assistant Professor, Psychiatry and Behavioral Sciences'],
                           homepage='https://royadams.github.io/', division=None)
    assert rows[1]['titles'] == ['Professor, Biomedical Engineering & Oncology']
    assert rows[1]['homepage'] is None
    assert rows[1]['profile'] == 'https://www.bme.jhu.edu/people/faculty/joel-bader/'
    assert set(rows[0]) == {'name_listed', 'titles', 'homepage', 'division'}


def test_wse_contact_carries_section_without_inventing_a_title():
    html = '''<div class="contact_block"><h2 class="contact_block_title">Research Faculty</h2>
<h2 class="contact_name">Soudeh Ghorbani</h2><div class="contact_title">Associate Research Professor</div></div>
<div class="contact_block"><h2 class="contact_name">William Gray-Roncal</h2>
<div class="contact_title">Assistant Research Professor</div></div>
<div class="contact_block"><h2 class="contact_block_title">Visiting Faculty</h2>
<h2 class="contact_name">Xiang Xiang</h2><div class="contact_title">Visiting Associate Professor</div></div>
<div class="contact_block"><h2 class="contact_name">No title listed</h2></div>'''
    _, rows = F.parse(html)
    assert len(rows) == html.count('class="contact_name"') == 4
    assert [r['division'] for r in rows] == ['Research Faculty', 'Research Faculty', 'Visiting Faculty', 'Visiting Faculty']
    assert rows[-1]['titles'] == [] and rows[-1]['homepage'] is None


def test_announced_incoming_professor_does_not_prove_a_faculty_appointment():
    assert R.rank_of(['Incoming Assistant Professor']) == 'other'
    assert R.listing_rank(['Incoming Assistant Professor'], [], 'courtesy') == 'other'
    assert R.rank_of(['Assistant Professor']) == 'ladder'


def test_secondary_listing_context_keeps_home_title_and_nonladder_ranks():
    title = ['Professor, Biomedical Engineering & Oncology']
    assert R.listing_rank(title, [], 'courtesy') == 'courtesy'
    assert title == ['Professor, Biomedical Engineering & Oncology']
    assert R.listing_rank(['Associate Research Professor'], [], 'courtesy') == 'research'
    assert R.listing_rank(['Professor Emeritus'], [], 'courtesy') == 'emeritus'


# Excerpts of the CS faculty page as archived 2016-06-14 and 2019-03-25 (web.archive.org id_ captures).
CARDS = '''<div class="highlight-box faculty-member-card">
      <h3><a href="http://www.cs.jhu.edu/faculty/david-yarowsky/" style='color:#5E6F7F;'>David Yarowsky</a></h3>
  <h6>Professor</h6>
<p><a href="http://www.cs.jhu.edu/research/language-speech-processing/">Language &amp; Speech Processing Group</a></p>
</div>
<div class="highlight-box faculty-member-card">
      <h3><a href="https://www.cs.jhu.edu/faculty/mathias-unberath/" style='color:#5E6F7F;'>Mathias Unberath</a></h3>
  <p><H6>ASSISTANT RESEARCH PROFESSOR</H6></p>
</div>'''


def test_wse_card_reads_2016_to_2020_cards():
    fmt, rows = F.parse(CARDS)
    assert fmt == 'wse_card' and [r['name_listed'] for r in rows] == ['David Yarowsky', 'Mathias Unberath']
    assert rows[0]['titles'] == ['Professor'] and rows[1]['titles'] == ['ASSISTANT RESEARCH PROFESSOR']
