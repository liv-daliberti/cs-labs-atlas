"""CMU School of Computer Science Stage 1: one page reader per site era, the charter's slots and listing groups (2026-11-13)."""
import importlib.util
import pathlib
import re

import pytest

from tools import listing_formats as F
from tools import listing_rows as LR
from tools import school_config as S
from tools import stage_gate as G

ROOT = pathlib.Path(__file__).resolve().parents[1]  # route-ok: code files, not data


def read(fmt, html):
    return F.FORMATS[fmt][0](html)


def test_csd_two_cell_names_print_last_first_without_a_comma():
    html = '''<table class="views-table"><tbody><tr class="odd">
      <td class="views-field views-field-field-computed-last-name"><a href="https://www.csd.cs.cmu.edu/people/faculty/umut-acar">Acar</a></td>
      <td class="views-field views-field-field-computed-first-name"><a href="/x">Umut</a></td>
      <td class="views-field views-field-field-computed-prof-title">  Associate Professor </td>
      <td class="views-field views-field-field-computed-building">9231 Gates<br/>412-268-6791<br/><a href="mailto:[email removed]">[email removed]</a></td></tr></tbody></table>'''
    (e,) = read('cmu_scs_views_table', html)
    assert e['name_listed'] == 'Acar, Umut' and e['titles'] == ['Associate Professor'] and e['quote_name'] == 'Acar Umut'
    assert 'mailto' not in repr(e) and '412' not in repr(e)
    flat = 'Name Title Office Acar Umut Associate Professor 9231 Gates 412-268-6791'
    assert LR.quote_of(flat, e) == 'Acar Umut Associate Professor'


def test_csd_one_link_cell_and_the_2026_single_cell_layout():
    link_cell = '''<table><tbody><tr><td class="views-field views-field-field-computed-last-name"><a href="/p/a">Acar, Umut</a> </td>
      <td class="views-field views-field-field-computed-prof-title">Associate Professor</td></tr></tbody></table>'''
    assert read('cmu_scs_views_table', link_cell)[0]['name_listed'] == 'Acar, Umut'
    single = '''<table><thead><tr><th>Name/Contact</th></tr></thead><tbody><tr><td class="views-field views-field-views-conditional-field"><a href="/p/a"><img alt="x"/></a></td>
      <td class="views-field views-field-field-first-name"><a href="/people/faculty/umut-acar">Acar, Umut</a><br/>
Professor
<br/><br/>9101 Gates<br/><a href="mailto:[email removed]">[email removed]</a></td></tr></tbody></table>'''
    (e,) = read('cmu_scs_views_table', single)
    assert (e['name_listed'], e['titles'], e['profile']) == ('Acar, Umut', ['Professor'], '/people/faculty/umut-acar')
    assert 'quote_name' not in e


def test_lti_directory_grid_and_core_faculty_bio_cards():
    grid = '''<table><tr class="row-1"><td class="col-1"><div class="views-field views-field-nothing"><span class="field-content"><a href="/people/1/james-baker"><h2>James Baker</h2></a></span></div>
      <div class="views-field views-field-field-computed-prof-title"><div class="field-content">Distinguished Career Professor</div></div>
      <div><span class="label">Email: </span><a href="mailto:[email removed]">[email removed]</a></div></td></tr></table>'''
    assert read('cmu_lti_directory', grid) == [dict(name_listed='James Baker', titles=['Distinguished Career Professor'], homepage=None, division=None, profile='/people/1/james-baker')]
    cards = '''<div class="section-id" id="core-faculty-bios"><div class="filterable"><a href="bisk-yonatan.html"><img alt=""/></a>
      <h2><a class="name" href="bisk-yonatan.html">   Yonatan   Bisk  </a></h2><h3>Assistant Professor</h3><p><a class="cta" href="bisk-yonatan.html">Read full bio</a></p></div></div>
      <div class="section-id" id="affiliated-faculty"><div class="filterable"><h2><a class="name" href="x.html">Someone Else</a></h2><h3>Professor</h3></div></div>'''
    assert [(e['name_listed'], e['titles']) for e in read('cmu_lti_cards', cards)] == [('Yonatan Bisk', ['Assistant Professor'])]


def test_bio_pages_h1_h2_then_h2_h3_skip_page_furniture():
    old = '''<div id="mainContent"><div class="content"><h1>Core Faculty-Machine Learning</h1><a name="bio1"></a><h1>Maria Florina Balcan</h1><div class="floatleft"></div>
      <h2>Associate Professor</h2><p>Bio</p><div class="hr"></div><h1>Ziv Bar-Joseph</h1><h2>Professor</h2></div></div>'''
    assert [(e['name_listed'], e['titles']) for e in read('cmu_bio_h1_h2', old)] == [('Maria Florina Balcan', ['Associate Professor']), ('Ziv Bar-Joseph', ['Professor'])]
    new = '''<h2>School of Computer Science</h2><div class="content"><h2>
        Maria
        Florina
        Balcan </h2><h3>Associate Professor/Co-Director, Machine Learning</h3><h3 class="collapsed">Bio</h3><div><p>Dr. Balcan</p></div></div>
      <div class="grid"><div><h2><a href="http://www.cs.cmu.edu/~ninamf/">Maria-Florina Balcan</a></h2><h3>Professor, Computer Science</h3><h4>Research Interests</h4></div></div>'''
    assert [(e['name_listed'], e['titles']) for e in read('cmu_bio_h2_h3', new)] == [
        ('Maria Florina Balcan', ['Associate Professor/Co-Director, Machine Learning']), ('Maria-Florina Balcan', ['Professor, Computer Science'])]


def test_ri_legacy_table_and_wordpress_cards():
    legacy = '''<table><tr><td><font style="font-size:15px;font-weight:bold;"><a class="hidden_link" href="http://www.cs.cmu.edu/~cga">Chris Atkeson</a></font></td></tr>
      <tr><td><b>Professor, RI/HCII</b></td></tr><tr><td><b>Email:</b> <img src="e.php"/></td></tr><tr><td><b>Office:</b> NSH A527</td></tr></table>'''
    assert [(e['name_listed'], e['titles']) for e in read('cmu_ri_legacy', legacy)] == [('Chris Atkeson', ['Professor, RI/HCII'])]
    cards = '''<div class="ri_person"><div class="ri_person_info"><strong><a href="https://www.ri.cmu.edu/ri-faculty/henny-admoni/">Henny Admoni</a></strong><br/>
      Associate Professor <br/></div></div><strong><a href="https://www.ri.cmu.edu/people/">Not a person</a></strong>'''
    assert [(e['name_listed'], e['titles']) for e in read('cmu_ri_cards', cards)] == [('Henny Admoni', ['Associate Professor'])]


def test_hcii_drupal7_cards_and_drupal9_teasers():
    d7 = '''<ul class="t-card-listing"><li class="o-card--wrapper t-card-listing--card"><h3><a href="/people/vincent-aleven">Vincent Aleven</a></h3>
      <div class="panel-pane pane-entity-field pane-node-field-up2-job-title">  Associate Professor and Director </div></li></ul>'''
    d9 = '''<div class="person-teaser"><a href="/people/x"><img alt=""/></a><div class="faculty-content-heading"><h2><a href="/people/vincent-aleven"><span>Vincent Aleven</span></a></h2>
      <h3 class="faculty-content-heading-position">Professor </h3></div><div class="person-links"><a href="mailto:[email removed]">[email removed]</a></div></div>'''
    assert [(e['name_listed'], e['titles']) for e in read('cmu_hcii_cards', d7)] == [('Vincent Aleven', ['Associate Professor and Director'])]
    assert [(e['name_listed'], e['titles']) for e in read('cmu_hcii_cards', d9)] == [('Vincent Aleven', ['Professor'])]


def test_s3d_index_keeps_core_and_affiliated_sections_without_titles_and_drops_postdocs():
    html = '''<h2>School of Computer Science</h2><h1>Core Faculty</h1><div><h2><a href="core-faculty/agarwal-yuvraj.html">  Dr.  Yuvraj    Agarwal  </a></h2><p><a class="cta">Read full bio</a></p></div>
      <div><h2>Matt Bass</h2></div><h1>Affiliated Faculty</h1><div><h2>Dr. Randal Bryant</h2></div><h1>Post Docs</h1><div><h2>Dr. Matthew Babcock</h2></div>'''
    assert [(e['name_listed'], e['titles'], e['division']) for e in read('cmu_s3d_index', html)] == [
        ('Yuvraj Agarwal', [], 'Core Faculty'), ('Matt Bass', [], 'Core Faculty'), ('Randal Bryant', [], 'Affiliated Faculty')]


def test_cbd_connections_keep_the_middle_name_and_cards_read_the_bold_title():
    old = '''<div class="cn-entry"><div style="margin-left: 10px;"><strong><a href="/name/robert-murphy/"><span class="fn n notranslate"> <span class="given-name">Robert</span> <span class="additional-name">F</span>
      <span class="family-name">Murphy</span> </span></a></strong><div><span class="title notranslate">Head Professor</span><span class="org">Carnegie Mellon University</span></div></div></div>'''
    assert [(e['name_listed'], e['titles']) for e in read('cmu_cbd_connections', old)] == [('Robert F Murphy', ['Head Professor'])]
    new = '''<div><h2>Ziv Bar-Joseph</h2><p><img alt="" src="x.jpg"/></p><p><strong><span>FORE Systems Professor</span></strong><br/>Carnegie Mellon University<br/>Computational Biology Department</p>
      <a class="btn" href="bar-joseph.html">View Profile</a></div>'''
    assert [(e['name_listed'], e['titles']) for e in read('cmu_cbd_cards', new)] == [('Ziv Bar-Joseph', ['FORE Systems Professor'])]


def test_cmu_readers_never_return_contact_lines_and_never_autodetect():
    for name in [n for n in F.FORMATS if n.startswith('cmu_')]:
        assert not F.FORMATS[name][1].search('<h2>Name</h2><h3>Professor</h3>')
    assert len([n for n in F.FORMATS if n.startswith('cmu_')]) == 18


def test_scs_directory_feed_counts_a_record_only_for_the_unit_its_own_dept_list_names():
    feed = ('{"data": [{"n": "Umut Acar", "aff": "Faculty", "titl": ["Professor"], "dept": ["Computer Science Department", "ECE: Electrical &amp; Computer Engineering"]},'
            '{"n": "Byron Yu", "aff": "Faculty", "titl": ["Professor, ECE-BME"], "dept": ["Robotics Institute"]},'
            '{"n": "Gina Student", "aff": "Student", "titl": ["Ph.D. Student"], "dept": ["Computer Science Department"]},'
            '{"n": "Ziv Bar-Joseph", "aff": "Faculty", "titl": ["Professor"], "dept": ["Ray and Stephanie Lane Computational Biology Department"]},'
            '{"sn": "NoName", "dept": ["Computer Science Department"]}]}')
    assert [(e['name_listed'], e['titles'], e['division']) for e in read('cmu_scs_directory_csd', feed)] == [
        ('Umut Acar', ['Professor'], 'Faculty'), ('Gina Student', ['Ph.D. Student'], 'Student')]   # the charter slot's title_filter drops the student
    assert [e['name_listed'] for e in read('cmu_scs_directory_ri', feed)] == ['Byron Yu']
    assert [e['name_listed'] for e in read('cmu_scs_directory_cbd', feed)] == ['Ziv Bar-Joseph']
    assert read('cmu_scs_directory_csd', '<html>not json</html>') == []


# ---- the charter ----------------------------------------------------------------------------------------------------

CFG = S.get('cmu')
DEPTS = {d['code']: d for d in CFG['departments']}


def test_seven_scs_units_are_full_coverage_departments():
    assert list(DEPTS) == ['CSD', 'MLD', 'LTI', 'RI', 'HCII', 'S3D', 'CBD']
    assert all(d["coverage"] == "full" and d.get("listing_groups") for d in DEPTS.values())
    assert {c for c, d in DEPTS.items() if d.get("listing_gaps")} == {"CSD", "LTI"} and all(list(DEPTS[c]["listing_gaps"]) == ["2018"] for c in ("CSD", "LTI"))
    assert S.check('cmu') == []


def test_every_listing_names_a_registered_cmu_reader_and_eras_with_one_slot_do_not_overlap_across_formats():
    for d in DEPTS.values():
        assert S.listing_group_errors(d) == []
        by = {}
        for s in d['listings']:
            assert s['format'] in F.FORMATS and s['format'].startswith('cmu_'), (s['slot'], s.get('format'))
            by.setdefault(s['slot'], []).append(s)
        for slot, eras in by.items():
            for a in eras:
                for b in eras:
                    if a is not b and a['format'] != b['format']:
                        assert a['to'] < b['from'] or b['to'] < a['from'], (slot, a['url'], b['url'])


@pytest.mark.parametrize('code', list(DEPTS))
def test_listing_groups_cover_every_year_of_the_window(code):
    d = DEPTS[code]
    lo, hi = CFG['window']
    for y in range(lo, hi + 1):
        assert any(g['from'] <= f'{y}1231' and g['to'] >= f'{y}0101' for g in d['listing_groups']), (code, y)


def test_a_missing_page_keeps_the_year_open_and_a_complete_set_closes_it(monkeypatch, tmp_path):
    import json
    cov = {'HCII': {str(y): {'HCII faculty H1': 'ok', 'HCII faculty H2': 'ok'} for y in range(2016, 2027)}}
    for code in DEPTS:
        cov.setdefault(code, {str(y): {f'{DEPTS[code]["listing_groups"][0]["slots"][0]} H1': 'ok'} for y in range(2016, 2027)})
    monkeypatch.setattr(G.P, 'data', lambda name, key: tmp_path / name)
    (tmp_path / 'coverage.json').write_text(json.dumps(cov))
    items = G.g1_years('cmu')
    assert any(i.startswith('HCII 2020: ') and 'page 2' in i for i in items)   # page 1 alone is 35 of about 44 people
    assert not any(i.startswith('HCII 2016') or i.startswith('HCII 2023') for i in items)
    cov['HCII']['2020']['HCII faculty, page 2 (2020-2022 pagination) H2'] = 'ok'
    (tmp_path / 'coverage.json').write_text(json.dumps(cov))
    assert not any(i.startswith('HCII 2020') for i in G.g1_years('cmu'))


def test_charter_slots_are_config_slots_with_the_same_urls():
    path = ROOT / 'listings' / 'scripts' / 'config_cmu.py'  # route-ok: code file, not data
    spec = importlib.util.spec_from_file_location('config_cmu_under_test', path)
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    config = {s['slot']: {u[0] for u in s['urls']} for s in cfg.SLOTS}
    for d in DEPTS.values():
        for s in d['listings']:
            assert s['slot'] in config, s['slot']
            assert s['url'] in config[s['slot']], (s['slot'], s['url'])
            assert next(x for x in cfg.SLOTS if x['slot'] == s['slot'])['dept'] == d['code']


def test_gate_three_knows_every_home_label_of_the_released_census():
    homes = G.known_homes('cmu')
    for label in ['CSD', 'MLD', 'LTI', 'RI', 'HCII', 'S3D', 'CBD', 'ECE', 'MechE', 'Tepper', 'Heinz', 'Statistics & Data Science']:
        assert label in homes
    rx = {k: re.compile(v) for k, v in CFG['census']['home_units'].items()}
    assert all(rx[k].search(k) for k in rx)
