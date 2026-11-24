import gzip
import json

import chain_audit as A


def test_pi_keys_preserve_chinese_names_and_existing_latin_normalization():
    assert A.norm('潘 理') == A.norm('潘理') == '潘理'
    assert A.norm('潘理') != A.norm('沈艳艳')
    assert A.norm('白 石') != A.norm('陈 博')
    assert A.norm('José O’Neill') == A.norm('Jose O Neill')


def test_one_chinese_lab_cannot_clear_another_labs_paper_or_link_gap(tmp_path, monkeypatch):
    school = tmp_path / 'princeton'
    school.mkdir()
    names = ['潘 理', '沈艳艳', '白 石']
    (school / 'pis.json').write_text(json.dumps([
        dict(pi=name, names=[name], personIds=[name], lab={}) for name in names]))
    (school / 'students.json').write_text(json.dumps({
        name: [dict(person='same-id', name='Jane Doe', roles=['phd'],
                    relations=[dict(years=[2020])])] for name in names[:2]}))
    (tmp_path / 'census-overrides.json').write_text('{}')
    with gzip.open(school / 'lab_papers.jsonl.gz', 'wt') as stream:
        for i, name in enumerate(names[:2]):
            stream.write(json.dumps(dict(pi=name, year=2020, work=f'W{i}', oa=f'W{i}')) + '\n')
    with gzip.open(school / 'student_papers.jsonl.gz', 'wt') as stream:
        stream.write(json.dumps(dict(pi='潘理', student='same-id', oa='W0')) + '\n')
    monkeypatch.setattr(A, 'H', tmp_path)
    monkeypatch.setattr(A.CO, 'onboarding', lambda school: False)

    checks = A.audit('princeton')['checks']
    assert checks['papers']['pass'] == 2
    assert [item['key'] for item in checks['papers']['unexplained']] == ['白 石']
    assert checks['links']['pass'] == 1
    assert [item['pi'] for item in checks['links']['unexplained']] == ['沈艳艳']
