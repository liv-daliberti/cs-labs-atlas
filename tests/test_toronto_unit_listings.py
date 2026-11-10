"""Toronto ECE: the HTML directory is a script shell; the site's wp-json people list is the unit listing (2026-11-10)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import cs_related_school as C  # noqa: E402


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
