"""student_audit.write_shared replaces only the audited schools' entries of the shared file (2026-11-25 incident)."""
import json

import student_audit as SA


def test_single_school_run_keeps_the_other_schools(tmp_path):
    f = tmp_path / 'student-audit.json'
    f.write_text(json.dumps([{'school': 'a', 'v': 1}, {'school': 'b', 'v': 1}, {'school': 'c', 'v': 1}]))
    out = SA.write_shared([{'school': 'b', 'v': 2}], f)
    assert [r['school'] for r in out] == ['a', 'b', 'c']
    assert json.loads(f.read_text()) == [{'school': 'a', 'v': 1}, {'school': 'b', 'v': 2}, {'school': 'c', 'v': 1}]
    SA.write_shared([{'school': 'd', 'v': 1}], f)
    assert [r['school'] for r in json.loads(f.read_text())] == ['a', 'b', 'c', 'd']


def test_missing_or_broken_file_starts_fresh(tmp_path):
    f = tmp_path / 'student-audit.json'
    assert SA.write_shared([{'school': 'a'}], f) == [{'school': 'a'}]
    f.write_text('{broken')
    assert SA.write_shared([{'school': 'b'}], f) == [{'school': 'b'}]
