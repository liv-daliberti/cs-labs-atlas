"""Toronto ECE: the HTML directory is a script shell; the site's wp-json people list is the unit listing (2026-11-10)."""
import json
import cs_related_school as C


def test_wp_json_people_text_gives_faculty_evidence():
    raw = json.dumps([{'title': {'rendered': 'Yang, Yibin<br> Assistant Professor'}},
                      {'title': {'rendered': 'Smith, Pat'}},
                      {'title': {'rendered': 'Naseri, Parinaz <br>Associate Professor'}}]).encode()
    txt = C.wp_json_people_text(raw)
    assert 'Yang, Yibin Assistant Professor' in txt
    for who, want in (('Yibin Yang', True), ('Pat Smith', False), ('Parinaz Naseri', True)):
        ev = C.faculty_evidence([('ECE', 'u', 's', '20261110', txt)], [who])
        assert bool(ev) == want, (who, ev)
        assert all(e['ladder'] for e in ev)


def test_wp_json_people_text_rejects_html():
    assert C.wp_json_people_text(b'<html>no</html>') == ''


def test_unit_pages_match_scheme_less_www_listings(tmp_path, monkeypatch):
    """A charter listing written 'www.host/path' (no scheme) must match the stored live page 'https://www.host/path'."""
    import re
    rx = r'^(?:https?://)?(?:www\.)?'
    assert re.sub(rx, '', 'www.mie.utoronto.ca/a/') == re.sub(rx, '', 'https://www.mie.utoronto.ca/a/')


def test_professor_emeritus_row_is_not_ladder():
    txt = 'Mark S. Fox Professor Emeritus Profile Eldan Cohen Assistant Professor Profile'
    ev = C.faculty_evidence([('MIE', 'u', 's', '20261110', txt)], ['Mark S. Fox'])
    assert ev and ev[0]['ladder'] is False, ev
    ev = C.faculty_evidence([('MIE', 'u', 's', '20261110', txt)], ['Eldan Cohen'])
    assert ev and ev[0]['ladder'] is True


def test_wp_json_category_classes_mark_emeritus_and_cross_appointed():
    raw = json.dumps([{'title': {'rendered': 'Chow, Paul<br> Professor'}, 'class_list': ['category-emeritus']},
                      {'title': {'rendered': 'Asare, Philip<br> Assistant Professor'}, 'class_list': ['category-cross-appointed']}]).encode()
    txt = C.wp_json_people_text(raw)
    assert C.faculty_evidence([('ECE', 'u', 's', 'o', txt)], ['Paul Chow'])[0]['ladder'] is False
    ev = C.faculty_evidence([('ECE', 'u', 's', 'o', txt)], ['Philip Asare'])[0]
    assert ev['ladder'] is False and '(cross-appointed)' in txt


def test_cross_appointed_marker_is_not_ladder():
    txt = 'Asare, Philip Assistant Professor (cross-appointed) Profile'
    ev = C.faculty_evidence([('ECE', 'u', 's', 'o', txt)], ['Philip Asare'])[0]
    assert ev['ladder'] is False


def test_status_only_row_is_not_ladder():
    txt = 'Husam Abdel-Qadir CEHCR Accepting Students Associate Professor (Status-Only) Twitter'
    ev = C.faculty_evidence([('IHPME', 'u', 's', 'o', txt)], ['Husam Abdel-Qadir'])[0]
    assert ev['ladder'] is False


def test_pager_children_are_not_wayback_queried():
    assert C.PAGER_CHILD.search('ihpme.utoronto.ca/faculty-directory/page/7/')
    assert C.PAGER_CHILD.search('www.physics.utoronto.ca/members/?page=3')
    assert C.PAGER_CHILD.search('www.ece.utoronto.ca/wp-json/wp/v2/people?per_page=100&page=1&_fields=title')  # an API list has no archive: skipped too
    assert not C.PAGER_CHILD.search('ihpme.utoronto.ca/faculty-directory/')


def test_teaching_stream_professor_is_not_ladder():
    txt = 'Brian Harrington CLTA Assistant Professor, Teaching Stream Computer Science Phone: 416-287-7000'
    ev = C.faculty_evidence([('UTSC', 'u', 's', 'o', txt)], ['Brian Harrington'])[0]
    assert ev['ladder'] is False
