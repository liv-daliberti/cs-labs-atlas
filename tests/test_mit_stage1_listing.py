from tools.listing_formats import mit_eecs_faculty_cards, mit_eecs_legacy_faculty, mit_csail_pi


def test_mit_legacy_faculty_keeps_printed_title_and_excludes_navigation():
    html = '''<a href="/people/faculty-advisors">Faculty</a>
    <ul class="faculty-list"><li class="views-row">
      <div class="views-field-title"><span class="card-title"><a href="/person/one">Ada Example</a></span></div>
      <div class="views-field-field-person-title">Associate Professor of EECS</div>
    </li><li class="views-row">
      <div class="views-field-title"><span class="card-title">Grace Example</span></div>
      <div class="views-field-field-person-title">Senior Lecturer</div>
    </li></ul>'''
    assert mit_eecs_legacy_faculty(html) == [
        dict(name_listed='Ada Example', titles=['Associate Professor of EECS'],
             homepage=None, division=None, profile='/person/one'),
        dict(name_listed='Grace Example', titles=['Senior Lecturer'],
             homepage=None, division=None, profile=None),
    ]


def test_mit_faculty_role_cards_ignore_research_terms_and_email():
    html = '''<div class="facetwp-template"><div class="people-entry">
      <h5><a href="/people/ada/">Ada Example</a></h5>
      <p>Professor, [CS and AI+D]</p>
      <ul><li>ada@example.edu</li></ul>
      <div class="people-research"><p>Robotics</p></div>
    </div></div>'''
    assert mit_eecs_faculty_cards(html) == [dict(
        name_listed='Ada Example', titles=['Professor, [CS and AI+D]'],
        homepage=None, division=None, profile='/people/ada/')]


def test_mit_csail_old_json_trailing_comma_and_new_card():
    old = '{"items":[{"label":"Ada Example","position":"Professor","url":"/user/1"},]}'
    assert mit_csail_pi(old)[0]['name_listed'] == 'Ada Example'
    html = '''<div class="info-block"><a href="/person/ada"><h2 class="card-heading">Ada Example</h2></a>
      <div class="field--name-field-title">Professor</div></div>'''
    assert mit_csail_pi(html)[0]['titles'] == ['Professor']


def test_mit_csail_solr_requires_all_docs_and_normalizes_names():
    import json
    doc = {'ss_title': 'Ada  Example', 'ss_field_title': 'Professor',
           'ss_name': 'Core/Dual', 'ss_url': '/person/ada'}
    assert mit_csail_pi(json.dumps({'response': {'numFound': 2, 'docs': [doc]}})) == []
    assert mit_csail_pi(json.dumps({'response': {'numFound': 1, 'docs': [doc]}}))[0]['name_listed'] == 'Ada Example'
