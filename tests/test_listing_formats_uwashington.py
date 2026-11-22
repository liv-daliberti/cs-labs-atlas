"""University of Washington listing formats (excerpts of real 2026 live pages, contact details removed)."""
import tomllib
from pathlib import Path

import listing_formats as F
from listing_rows import rank_of

ALLEN = """<div class="e-con-inner"><a href="https://www.cs.washington.edu/people/faculty/alterman-naomi/"><img src="x.jpg"/></a></div>
<p class="elementor-heading-title elementor-size-default"><a href="https://www.cs.washington.edu/people/faculty/alterman-naomi/" aria-label="Read the bio for Alterman, Naomi">Naomi Alterman</a></p>
<p class="elementor-heading-title elementor-size-default">Assistant Teaching Professor</p>
<p class="elementor-heading-title elementor-size-default"><a href="https://www.cs.washington.edu/people/faculty/aravkin-aleksandr/" aria-label="Read the bio for Aravkin, Aleksandr">Aleksandr Aravkin</a></p>
<p class="elementor-heading-title elementor-size-default">Adjunct</p>
<p class="elementor-heading-title elementor-size-default">Department of Applied Mathematics</p>
<p class="elementor-heading-title elementor-size-default">Professor &amp; Interim Director</p>"""

ECE = """<div class="stafftemplate--entry"><a href="https://people.ece.uw.edu/anant/"><img alt="x"/></a><span class="stafftemplate--name"><a href="https://people.ece.uw.edu/anant/">M.P. (Anant) Anantram</a></span><span class="stafftemplate--title">Professor; Director, NanoES Institute</span><span class="stafftemplate--email"><a href="mailto:a@u.washington.edu">a@u.washington.edu</a></span></div>
<div class="stafftemplate--entry"><span class="stafftemplate--name">Jane Roe</span><span class="stafftemplate--title">Assistant Professor</span></div>"""

ISCHOOL = """<article style="display: block;" class="section-block card clearfix" id="section-all" data-categories="all"></article>
<article aria-label="Cindy Aden" id="card-adenc" class="card clearfix" data-type="faculty,emeritus" data-categories="" data-unit="" data-letter="a"> <div class="c clearfix"> <div class="info"> <h2 class="h1"> <a href="/people/faculty/profile/adenc" aria-label="Cindy Aden profile"> Cindy Aden </a> </h2> <p class="small"> <em>Teaching Professor Emeritus</em> </p> <address><a href="mailto:adenc@uw.edu">adenc@uw.edu</a></address> </div> </div> </article>
<article aria-label="Eric Aker" id="card-akereric" class="card clearfix" data-type="visitingguest,faculty" data-categories="" data-unit="" data-letter="a"> <div class="info"> <h2 class="h1"> <a href="/people/faculty/profile/akereric"> Eric Aker </a> </h2> <p class="small"> <em>Visiting Lecturer</em> </p> </div> </article>"""

AMATH = """<h2 class="directory-item__name"><a href="/people/ivana-bozic" hreflang="und">Ivana Bozic</a></h2> <strong class="directory-item__title">Professor<br>Graduate Program Coordinator</strong> </div>
<h2 class="directory-item__name"><a href="/people/x-y">X Y</a></h2> <strong class="directory-item__title">Boeing Professor of Applied Mathematics<br>Adjunct Professor of Mathematics</strong>"""

HCDE = """<div class="column"><figure><img alt="Arpita B."/></figure></div> <div class="column"> <h2><a href="https://www.hcde.washington.edu/arpita"><strong>Arpita B</strong></a></h2> <p>Assistant Teaching Professor</p> </div> <div class="column"> <h3>Specialization</h3> <p>Human computer interaction</p> </div>"""


def test_allen_cards_group_titles_under_their_name_link():
    name, rows = F.parse(ALLEN)
    assert name == 'uw_allen_cards' and [r['name_listed'] for r in rows] == ['Naomi Alterman', 'Aleksandr Aravkin']
    assert rows[0]['titles'] == ['Assistant Teaching Professor'] and rows[0]['homepage'].endswith('/alterman-naomi/')
    assert rows[1]['titles'] == ['Adjunct', 'Department of Applied Mathematics', 'Professor & Interim Director']


def test_ece_staff_drops_contact_and_splits_titles():
    name, rows = F.parse(ECE)
    assert name == 'uw_ece_staff' and len(rows) == 2
    assert rows[0]['titles'] == ['Professor', 'Director, NanoES Institute'] and 'mailto' not in str(rows)
    assert rows[1]['homepage'] is None


def test_ischool_cards_skip_section_blocks_and_keep_group():
    name, rows = F.parse(ISCHOOL)
    assert name == 'uw_ischool_card' and [r['name_listed'] for r in rows] == ['Cindy Aden', 'Eric Aker']
    assert rows[0]['division'] == 'faculty,emeritus' and rows[0]['titles'] == ['Teaching Professor Emeritus'] and 'uw.edu' not in str(rows)


def test_amath_and_hcde_directories():
    name, rows = F.parse(AMATH)
    assert name == 'uw_amath_directory' and rows[0]['titles'] == ['Professor', 'Graduate Program Coordinator']
    assert rows[1]['titles'][0] == 'Boeing Professor of Applied Mathematics'
    name, rows = F.parse(HCDE)
    assert name == 'uw_hcde_columns' and rows[0]['name_listed'] == 'Arpita B' and rows[0]['titles'] == ['Assistant Teaching Professor']


def test_charter_rank_words_classify_uw_titles():
    rw = tomllib.loads((Path(__file__).resolve().parents[1] / 'schools/uwashington.toml').read_text())['census']['rank_words']
    assert rank_of(['Assistant Teaching Professor'], rw) == 'teaching'
    assert rank_of(['Adjunct', 'Department of Applied Mathematics'], rw) == 'adjunct'
    assert rank_of(['Professor'], rw) == 'ladder' and rank_of(['Teaching Professor Emeritus'], rw) == 'emeritus'


ALLEN_2019 = """<h2>Faculty</h2><div class='row directory-row'> <div class='col-sm-10'> <div class='directory-name'><a href='http://www.timalthoff.com/'>Tim Althoff</a></div> <div class='directory-office'>CSE2 313</div> </div></div>
<div class='row directory-row'> <div class='col-sm-10'> <div class='directory-name'><a href='https://www.cs.washington.edu/people/faculty/anderson/'>Richard Anderson</a></div> </div></div>"""

ALLEN_2016 = """<h2>Faculty</h2><a name='A'></a> <div class='people-short-listing-name'><a href='https://www.cs.washington.edu/people/faculty/anderson/'> <div class='people-short-listing-contact'> <div class='people-short-listing-name'><a href='https://www.cs.washington.edu/people/faculty/anderson/'>Richard Anderson</a></div></a></div>"""


def test_allen_directory_eras_read_names_under_the_faculty_heading():
    for html, want in ((ALLEN_2019, ['Tim Althoff', 'Richard Anderson']), (ALLEN_2016, ['Richard Anderson'])):
        name, rows = F.parse(html)
        assert name == 'uw_allen_directory'
        assert [r['name_listed'] for r in rows] == want
        assert all(r['titles'] == ['Faculty'] for r in rows)   # no per-person rank on these pages


STAT = """<link rel="canonical" href="https://stat.uw.edu/people/faculty" /><div class="faculty-column views-col col-1"><div class="views-field views-field-title"><span class="field-content person-name"><a href="/people/yen-chi-chen" hreflang="en">Yen-Chi Chen</a></span></div><div class="views-field views-field-field-position"><strong class="field-content"><a href="/taxonomy/term/1437" hreflang="en">Associate Professor</a></strong></div><div class="views-field views-field-field-named-faculty-position"><em class="field-content"></em></div></div>
<div class="faculty-column views-col col-2"><div class="views-field views-field-title"><span class="field-content person-name"><a href="/people/fang-han" hreflang="en">Fang Han</a></span></div><div class="views-field views-field-field-position"><strong class="field-content"><a href="/taxonomy/term/1" hreflang="en">Professor</a></strong></div><div class="views-field views-field-field-named-faculty-position"><em class="field-content">Job &amp; Gertrude Tamaki Endowed Professorship</em></div></div>"""


def test_stat_people_rank_and_named_position():
    name, rows = F.parse(STAT)
    assert name == 'uw_stat_people'
    assert [(r['name_listed'], r['titles']) for r in rows] == [('Yen-Chi Chen', ['Associate Professor']), ('Fang Han', ['Professor', 'Job & Gertrude Tamaki Endowed Professorship'])]
