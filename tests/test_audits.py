"""The student audit's same-person test and the chain audit's revisit_after reopening."""
import json

import chain_audit
import student_audit


def test_R_AUD_03_student_audit_compatible():
    assert not student_audit.compatible('Yuan Li', 'Yu-Jhe Li')       # two people in Kitani's lab
    assert student_audit.compatible('Xiang Li', 'Xiang Lisa Li')
    assert student_audit.compatible('Dan Klein', 'Daniel Klein')
    assert student_audit.compatible('Wei Li', 'Li Wei')                # same tokens reordered
    assert not student_audit.compatible('Xin Li', 'Xinyu Li')


def test_R_AUD_02_revisit_due():
    ov = {'Jane Arrival': {'exclude': True, 'revisit_after': '2026-10-01'},
          'Later Arrival': {'exclude': True, 'revisit_after': '2027-09-01'},
          'Plain Exclusion': {'exclude': True}}
    assert chain_audit.revisit_due(ov, '2026-10-29') == {'jane arrival'}
    assert chain_audit.revisit_due(ov, '2027-09-01') == {'jane arrival', 'later arrival'}


def test_R_AUD_02_revisit_after_reopens_coverage(tmp_path, monkeypatch):
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


def test_R_AUD_01_the_seven_chain_checks(tmp_path, monkeypatch):
    # every check is reported, each item counted as passing, explained or open
    school = tmp_path / 'princeton'
    school.mkdir()
    (school / 'pis.json').write_text('[]')
    (school / 'students.json').write_text('{}')
    (tmp_path / 'census-overrides.json').write_text('{}')
    monkeypatch.setattr(chain_audit, 'H', tmp_path)
    checks = chain_audit.audit('princeton')['checks']
    assert list(checks) == chain_audit.CHECKS == ['coverage', 'pi', 'students', 'papers', 'links', 'copies', 'one_person']
    assert all({'total', 'explained', 'unexplained'} <= set(c) for c in checks.values())


def test_mphil_member_without_paper_has_non_phd_link_explanation(tmp_path):
    import gzip

    school = tmp_path / 'princeton'
    school.mkdir()
    (school / 'pis.json').write_text(json.dumps([{'pi': 'Ada Lovelace', 'piBasis': {'kind': 'own_lab'}}]))
    (school / 'students.json').write_text(json.dumps({'Ada Lovelace': [
        {'person': 'p_student', 'name': 'Student One', 'roles': ['mphil'], 'relations': []}
    ]}))
    with gzip.open(school / 'lab_papers.jsonl.gz', 'wt') as out:
        out.write(json.dumps({'pi': 'Ada Lovelace', 'year': 2024, 'oa': 'W1'}) + '\n')

    links = chain_audit.audit('princeton', hierarchy=tmp_path)['checks']['links']
    assert links['total'] == 1
    assert links['n_unexplained'] == 0
    assert links['explained']['non-PhD advisee (mphil): thesis-only is normal'] == 1


def test_R_AUD_08_link_diagnosis_counts_school_authorships_only(tmp_path, monkeypatch):
    import gzip
    import link_diagnosis as LD
    H = tmp_path
    (H / 'princeton').mkdir()
    open_item = dict(pi='Ada Lovelace', student='Qian Yu', id='p_qy', years=[2019, 2020], roles=['phd'])
    monkeypatch.setattr(chain_audit, 'audit', lambda *args, **kwargs: dict(checks=dict(links=dict(unexplained=[open_item]))))
    (H / 'chain-audit.json').write_text(json.dumps(dict(schools=[dict(school='princeton', checks=dict(links=dict(unexplained=[open_item])))])))
    (H / 'princeton' / 'pis.json').write_text(json.dumps([dict(pi='Ada Lovelace', reviewedOpenAlex=['A1'], periods=[], listings=[])]))
    (H / 'princeton' / 'students.json').write_text(json.dumps({'Ada Lovelace': [dict(person='p_qy', name='Qian Yu')]}))
    for f in ('lab_papers', 'student_papers'):
        with gzip.open(H / 'princeton' / f'{f}.jsonl.gz', 'wt'):
            pass
    inst = 'https://openalex.org/' + LD.INST['princeton']
    at = lambda name, aid, school: dict(raw_author_name=name, author=dict(id=aid),
                                        institutions=[dict(id=inst if school else 'https://openalex.org/I1', lineage=[])])
    sweep = [dict(id='W1', publication_year=2020, type='article', authorships=[at('Q. Yu', 'X1', True)]),        # initials only
             dict(id='W2', publication_year=2020, type='article', authorships=[at('Qian Yu', 'X2', False)]),     # not the school
             dict(id='W3', publication_year=2020, type='dataset', authorships=[at('Qian Yu', 'X3', True)])]     # not a paper
    monkeypatch.setattr(LD, 'H', H)
    monkeypatch.setattr(LD, 'sweep_works', lambda s: iter(sweep))
    LD.run('princeton')
    out = json.loads((H / 'princeton' / 'link-diagnosis.json').read_text())
    assert out['students']['Ada Lovelace | p_qy']['category'] == 'no_school_work'
    # the same initials under an author id that also carries the full given name at the school do count
    sweep.append(dict(id='W4', publication_year=2019, type='article', authorships=[at('Qian Yu', 'X1', True)]))
    LD.run('princeton')
    out = json.loads((H / 'princeton' / 'link-diagnosis.json').read_text())
    assert out['students']['Ada Lovelace | p_qy']['category'] == 'publishes_without_pi'
    assert out['students']['Ada Lovelace | p_qy']['n_school_works'] == 2
    assert not LD.compatible('Po-Ta Chen', 'Po-Hsuan Chen') and LD.compatible('Qian Yu', 'Q. Yu')


def _diag(tmp_path, monkeypatch, sweep, pi_extra=None, years=(2016, 2020)):
    import gzip
    import link_diagnosis as LD
    H = tmp_path
    (H / 'princeton').mkdir()
    open_item = dict(pi='Ada Lovelace', student='Qian Yu', id='p_qy', years=list(years), roles=['phd'])
    monkeypatch.setattr(chain_audit, 'audit', lambda *args, **kwargs: dict(checks=dict(links=dict(unexplained=[open_item]))))
    (H / 'princeton' / 'pis.json').write_text(json.dumps([dict(pi='Ada Lovelace', reviewedOpenAlex=['A1'], periods=[], listings=[], **(pi_extra or {}))]))
    (H / 'princeton' / 'students.json').write_text(json.dumps({'Ada Lovelace': [dict(person='p_qy', name='Qian Yu')]}))
    for f in ('lab_papers', 'student_papers'):
        with gzip.open(H / 'princeton' / f'{f}.jsonl.gz', 'wt'):
            pass
    monkeypatch.setattr(LD, 'H', H)
    monkeypatch.setattr(LD, 'sweep_works', lambda s: iter(sweep))
    LD.run('princeton')
    return json.loads((H / 'princeton' / 'link-diagnosis.json').read_text())['students']['Ada Lovelace | p_qy']


def _work(wid, year, typ, pi_aff, title='A paper', doi='10.1/x', **kw):
    import link_diagnosis as LD
    inst = 'https://openalex.org/' + LD.INST['princeton']
    return dict(id=wid, publication_year=year, publication_date=f'{year}-06-01', type=typ, title=title, doi=doi, authorships=[
        dict(raw_author_name='Qian Yu', author=dict(id='X1'), institutions=[dict(id=inst, lineage=[])]),
        pi_aff], **kw)


def test_stage7_with_pi_not_a_paper(tmp_path, monkeypatch):
    LD_inst = 'https://openalex.org/' + __import__('link_diagnosis').INST['princeton']
    pi = dict(raw_author_name='Ada Lovelace', author=dict(id='A1'), institutions=[dict(id=LD_inst, lineage=[])])
    w = _work('W1', 2018, 'article', pi, title='Dataset for Analytical Engines', doi='10.5281/zenodo.123', primary_location=dict(source=dict(display_name='Zenodo')))
    assert _diag(tmp_path, monkeypatch, [w])['category'] == 'with_pi_not_a_paper'


def test_stage7_with_pi_before_window_by_venue_year(tmp_path, monkeypatch):
    import link_diagnosis as LD
    from pihier.common import norm_title
    monkeypatch.setattr(LD, 'dblp_venues', lambda p: {norm_title('Notes on the Analytical Engine'): (2012, 'conf/x/Lovelace12')})
    inst = 'https://openalex.org/' + LD.INST['princeton']
    pi = dict(raw_author_name='Ada Lovelace', author=dict(id='A1'), institutions=[dict(id=inst, lineage=[])])
    w = _work('W2', 2018, 'preprint', pi, title='Notes on the Analytical Engine')
    assert _diag(tmp_path, monkeypatch, [w])['category'] == 'with_pi_before_window'


def test_stage7_with_pi_other_institution_by_raw_affiliation(tmp_path, monkeypatch):
    pi = dict(raw_author_name='Ada Lovelace', author=dict(id='A1'), institutions=[], raw_affiliation_strings=['Society of Fellows, Harvard University, Cambridge, MA'])
    w = _work('W3', 2018, 'article', pi)
    assert _diag(tmp_path, monkeypatch, [w])['category'] == 'with_pi_at_other_institution'
