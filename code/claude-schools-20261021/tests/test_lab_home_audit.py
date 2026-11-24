import lab_home_audit as A


EV = dict(url='https://example.edu/faculty', sha256='a' * 64, quote='Ann, Professor')
CFG = dict(departments=[dict(code='CS', name='Computer Science')], affiliated_units=[], census={})


def test_department_code_aliases_do_not_create_false_conflicts():
    shared = dict(status='accepted', home_department='Department of Computer Science', evidence=EV, home_basis='listed_title')
    local = dict(status='accepted', home_department='CS', evidence=EV, home_basis='listed_title')
    assert A.assess(local, shared, local, CFG, {}) == []


def test_missing_and_ambiguous_homes_cannot_receive_clear_status():
    assert A.assess(None, None, None, CFG, {}) == ['missing_home']
    row = dict(status='accepted', home_department='CS', home_basis='primary_unresolved', evidence=EV)
    assert A.assess(row, None, row, CFG, {}) == ['primary_unresolved']


def test_single_unit_proposal_requires_same_unit_captured_listing():
    pi = dict(departments=['CS'], rank='ladder', listings=[dict(EV, kind='dept_listing:CS', year=2025)])
    assert A.proposed_from_listing(pi, CFG)['home_department'] == 'Computer Science'
    assert A.proposed_from_listing(dict(pi, departments=['CS', 'STAT']), CFG) is None
    assert A.proposed_from_listing(dict(pi, listings=[dict(EV, kind='unit_listing:ML', year=2025)]), CFG) is None
    assert A.proposed_from_listing(dict(pi, rank='courtesy'), CFG) is None


def test_quote_for_another_faculty_member_does_not_verify_this_pi():
    assert not A.quote_names_pi('Siu On Chan, Adjunct Assistant Professor', ['CHAN Lai Wan'])
    assert A.quote_names_pi('László Babai, Professor', ['Laszlo Babai'])
    assert A.quote_names_pi('Nathan Srebro, Professor', ['Nati Srebro', 'Nathan Srebro'])
    assert A.quote_names_pi('James Evans, Professor of Sociology', ['James A. Evans'])


def test_explicit_uppercase_family_name_first_is_exact_name_evidence():
    assert A.quote_names_pi('CHEN Tao', ['Tao Chen'])
    assert A.quote_names_pi('NAIR Chandra M.', ['Chandra Nair'])
    assert A.quote_names_pi('Pheng Ann Heng, Professor', ['HENG Pheng Ann'])
    assert not A.quote_names_pi('TAO CHEN', ['Chen Tao'])
    assert not A.quote_names_pi('CHAN Siu On', ['Lai Wan Chan'])
    assert not A.quote_names_pi('CHEN T.', ['Tao Chen'])
    assert not A.quote_names_pi('CHEN Tao, Associate Professor', ['Tao Chen'])


def subject_fixture():
    pid = 'https://dblp.org/pid/12/345'
    homepage = 'https://faculty.example.edu/wang'
    pi = dict(pi='Wei Wang', dblp=[pid])
    evidence = dict(EV, url=homepage + '/zh_CN/index.htm', quote='王伟', subject_name='王伟',
                    subject_binding=dict(kind='dblp_homepage', person_id=pid,
                                         decision_name='Wei Wang', homepage=homepage))
    profile = dict(verified=True, subject='王伟', headers=['王伟'], personal_links=[])
    persons = [dict(pid=pid, urls=[homepage])]
    return evidence, pi, profile, persons


def test_unique_dblp_homepage_binds_captured_chinese_subject():
    evidence, pi, profile, persons = subject_fixture()
    assert A.accepted_profile_subject(evidence, pi, [], profile, persons, A.homepage_owners(persons))
    assert not A.accepted_profile_subject(evidence, pi, [], dict(profile, verified=False), persons,
                                          A.homepage_owners(persons))
    assert not A.accepted_profile_subject(evidence, pi, [], dict(profile, subject='陈国良'), persons,
                                          A.homepage_owners(persons))


def test_faculty_role_pointer_cannot_bind_another_professor():
    evidence, pi, profile, persons = subject_fixture()
    pi['piBasis'] = dict(evidence)
    review = dict(name=pi['pi'], decision='accepted', dblp=pi['dblp'], faculty_evidence=[evidence])
    evidence['subject_binding']['kind'] = 'accepted_census_faculty_profile'
    assert not A.accepted_profile_subject(evidence, pi, [review], profile, persons,
                                          A.homepage_owners(persons))


def test_shared_homepage_and_unlabelled_publication_link_do_not_bind():
    evidence, pi, profile, persons = subject_fixture()
    shared = persons + [dict(pid='other', urls=persons[0]['urls'])]
    assert not A.accepted_profile_subject(evidence, pi, [], profile, shared, A.homepage_owners(shared))
    evidence['url'] = 'https://faculty.example.edu/another'
    assert not A.accepted_profile_subject(evidence, pi, [], profile, persons, A.homepage_owners(persons))
    profile['personal_links'] = persons[0]['urls']
    assert A.accepted_profile_subject(evidence, pi, [], profile, persons, A.homepage_owners(persons))


def test_homepage_normalization_preserves_identity_parameters():
    assert A.homepage_key('https://faculty.example.edu/wang/en/index.htm') == A.homepage_key('http://faculty.example.edu/wang')
    assert A.homepage_key('https://example.edu/profile?id=123') != A.homepage_key('https://example.edu/profile?id=456')
    assert A.homepage_key('https://example.edu/people#wang') is None


def test_reviewed_alias_requires_explicit_alias_and_exact_accepted_receipt():
    evidence, pi, profile, persons = subject_fixture()
    evidence['subject_binding']['kind'] = 'accepted_reviewed_alias'
    pi['piBasis'] = dict(evidence)
    decision = dict(name=pi['pi'], decision='accepted', dblp=pi['dblp'], cjk_name='王伟', receipt=dict(evidence))
    assert A.accepted_profile_subject(evidence, pi, [decision], profile, persons, {})
    decision['receipt']['sha256'] = 'b' * 64
    assert not A.accepted_profile_subject(evidence, pi, [decision], profile, persons, {})
    decision['receipt']['sha256'] = evidence['sha256']
    decision.pop('cjk_name')
    decision['evidence_kept'] = dict(cjk_name='王伟')
    assert not A.accepted_profile_subject(evidence, pi, [decision], profile, persons, {})


def test_retained_profile_requires_original_hash_and_reads_only_labelled_self_links(tmp_path, monkeypatch):
    import hashlib
    import sqlite3
    import zlib

    raw = ('<title>王伟 - 教师主页</title><h1>王伟</h1>'
           '<div>个人主页：<a href="https://wang.example.org">https://wang.example.org</a></div>'
           '<p>Publication: <a href="https://coauthor.example.org">Other author</a></p>').encode()
    path = tmp_path / 'school-captures.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('create table live (url text,status integer,sha256 text,raw_zlib blob)')
        db.execute('insert into live values (?,?,?,?)', (EV['url'], 200, hashlib.sha256(raw).hexdigest(), zlib.compress(raw)))
    monkeypatch.setattr(A.P, 'data', lambda filename, school: tmp_path / filename)
    ev = dict(EV, sha256=hashlib.sha256(raw).hexdigest(), quote='王伟')
    info = A.captured_profile_subject(ev, 'test', {})
    assert info['verified'] and info['subject'] == '王伟'
    assert info['personal_links'] == ['https://wang.example.org']
    assert not A.captured_profile_subject(dict(ev, quote='李伟'), 'test', {})['verified']
    assert not A.captured_profile_subject(dict(ev, sha256='0' * 64), 'test', {})['verified']
