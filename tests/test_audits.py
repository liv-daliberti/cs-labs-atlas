"""The student audit's same-person test and the chain audit's revisit_after reopening."""
import json

import chain_audit
import student_audit


def test_student_audit_compatible():
    assert not student_audit.compatible('Yuan Li', 'Yu-Jhe Li')       # two people in Kitani's lab
    assert student_audit.compatible('Xiang Li', 'Xiang Lisa Li')
    assert student_audit.compatible('Dan Klein', 'Daniel Klein')
    assert student_audit.compatible('Wei Li', 'Li Wei')                # same tokens reordered
    assert not student_audit.compatible('Xin Li', 'Xinyu Li')


def test_revisit_due():
    ov = {'Jane Arrival': {'exclude': True, 'revisit_after': '2026-10-01'},
          'Later Arrival': {'exclude': True, 'revisit_after': '2027-09-01'},
          'Plain Exclusion': {'exclude': True}}
    assert chain_audit.revisit_due(ov, '2026-10-29') == {'jane arrival'}
    assert chain_audit.revisit_due(ov, '2027-09-01') == {'jane arrival', 'later arrival'}


def test_revisit_after_reopens_coverage(tmp_path, monkeypatch):
    # a listed person decided by an exclusion stays decided until revisit_after, then is an open coverage item again
    school = tmp_path / 'princeton'
    school.mkdir()
    (school / 'listed-not-in-census.json').write_text(json.dumps([{'name': 'Jane Arrival', 'titles': ['Assistant Professor'], 'years': [2026]}]))
    for f, v in (('pis.json', []), ('students.json', {})):
        (school / f).write_text(json.dumps(v))
    monkeypatch.setattr(chain_audit, 'H', tmp_path)

    def coverage(revisit_after):
        ov = {'princeton': {'Jane Arrival': {'exclude': True, 'why': 'new arrival, no group yet', 'revisit_after': revisit_after}}}
        (tmp_path / 'census-overrides.json').write_text(json.dumps(ov))
        return chain_audit.audit('princeton')['checks']['coverage']

    later = coverage('2999-01-01')
    assert later['n_unexplained'] == 0 and sum(later['explained'].values()) == 1
    due = coverage('2000-01-01')
    assert due['n_unexplained'] == 1
    assert 'revisit due' in json.dumps(due['unexplained'])
