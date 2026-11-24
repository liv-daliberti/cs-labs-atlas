import json

import chain_audit as A


def test_partial_release_retains_reviewed_gaps_without_inventing_reasons(tmp_path, monkeypatch):
    school = tmp_path / 'princeton'
    school.mkdir()
    pis = [dict(pi=name, names=[name], personIds=[name], lab={},
                title='Assistant Professor', listings=[dict(year=2026)])
           for name in ['Reviewed Gap', 'Held Identity', 'Unreviewed Gap']]
    (school / 'pis.json').write_text(json.dumps(pis))
    (school / 'students.json').write_text('{}')
    (school / 'lab-coverage-reasons.json').write_text(json.dumps({
        'Reviewed Gap': {'papers': {'code': 'snapshot_limited', 'why': 'Historical sources still missing.'}}}))
    (tmp_path / 'census-overrides.json').write_text(json.dumps({'princeton': {
        'Held Identity': {'no_identity': True, 'why_no_identity': 'Reviewed name collision; papers withheld.'}}}))
    monkeypatch.setattr(A, 'H', tmp_path)
    monkeypatch.setattr(A.CO, 'onboarding', lambda school: False)

    def no_automatic_reasons(school):
        raise AssertionError('Released school must not acquire census-derived reasons')

    monkeypatch.setattr(A.LC, 'lab_rows', no_automatic_reasons)
    result = A.audit('princeton')['checks']
    assert result['papers']['n_unexplained'] == 1
    assert result['papers']['unexplained'][0]['key'] == 'Unreviewed Gap'
    assert sum(result['papers']['explained'].values()) == 2
    assert result['students']['n_unexplained'] == 3
