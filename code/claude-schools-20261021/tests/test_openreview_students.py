"""R-STU-27: a student's own OpenReview profile as dated student-adviser evidence (tools/openreview_students.py). Synthetic fixtures only."""
import json
import re

import pytest

import openreview_students as O
import selfdeclared_candidates as C

SPEC = dict(domains=['ust.hk'], names=['hong kong university of science and technology'], excluded=re.compile(r'guang\s*zhou', re.I))
PI = ['Ada Lovelace']
WIN = (2018, 2026)


def prof(pid='~Jane_Doe1', name='Jane Doe', hist=None, rels=None):
    return dict(id=pid, content=dict(names=[dict(fullname=name)],
                                     history=hist if hist is not None else [dict(position='PhD student', institution=dict(name='HKUST', domain='cse.ust.hk'), start=2019, end=2023)],
                                     relations=rels if rels is not None else [dict(relation='PhD Advisor', name='Ada Lovelace', username='~Ada_Lovelace1', start=2019, end=2023)]))


def val(profiles, pi=PI, name='Jane Doe'):
    return O.validate(profiles, SPEC, pi, WIN, name)


def test_R_STU_27_validated_profile_is_admitted_with_dates_and_role():
    r = val([prof()])
    assert r['status'] == 'admitted' and r['role'] == 'phd' and r['flags'] == []
    row = O.build_row(r, dict(pi='Ada Lovelace', name='Jane Doe', window=WIN), 'ab' * 32, '2026-11-13T00:00:00')
    assert row['years'] == [2019, 2023] and row['url'] == 'https://openreview.net/profile?id=~Jane_Doe1'
    assert row['rule'] == 'R-STU-27' and row['evidence_kind'] == 'self_declared_openreview' and 'PhD Advisor: Ada Lovelace' in row['quote']
    assert '@' not in json.dumps(row)


def test_R_STU_27_each_of_the_three_conditions_is_needed():
    other = [dict(position='PhD student', institution=dict(name='MIT', domain='mit.edu'), start=2019, end=2023)]
    assert val([prof(hist=other)])['status'] == 'none'                                   # not at this school
    late = [dict(position='PhD student', institution=dict(name='HKUST', domain='ust.hk'), start=2005, end=2010)]
    assert val([prof(hist=late)])['status'] == 'none'                                    # dates do not overlap the appointment
    assert val([prof(rels=[dict(relation='PhD Advisor', name='Alan Turing')])])['status'] == 'none'   # adviser is someone else
    assert val([prof(rels=[dict(relation='Collaborator', name='Ada Lovelace')])])['status'] == 'none'
    assert val([prof(hist=[dict(position='Postdoc', institution=dict(name='HKUST', domain='ust.hk'), start=2019, end=2023)])])['status'] == 'none'


def test_R_STU_27_guangzhou_campus_is_not_the_school():
    gz = [dict(position='PhD student', institution=dict(name='HKUST (Guangzhou)', domain='hkust-gz.edu.cn'), start=2019, end=2023)]
    assert val([prof(hist=gz)])['status'] == 'none'


def test_R_STU_27_hyphen_and_space_fold_and_username_match():
    assert O.name_match('Jia-Wang Li', 'Jiawang Li') and O.name_match('Jia Wang Li', 'Jiawang Li')
    assert not O.name_match('Wang', 'Wang') and not O.name_match('Li Wang', 'Li Chen')
    rel = [dict(relation='Advisor', name='A. L.', username='~Ada_Lovelace1')]
    assert val([prof(rels=rel)])['status'] == 'admitted'


def test_R_STU_27_co_advised_is_admitted_only_when_the_pi_is_named():
    both = [dict(relation='PhD Advisor', name='Ada Lovelace'), dict(relation='PhD Advisor', name='Alan Turing')]
    r = val([prof(rels=both)])
    assert r['status'] == 'admitted' and 'co_advised' in r['flags']
    assert val([prof(rels=[dict(relation='PhD Advisor', name='Alan Turing'), dict(relation='PhD Advisor', name='Grace Hopper')])])['status'] == 'none'


def test_R_STU_27_second_same_name_profile_holds():
    twin = prof(pid='~Jane_Doe2', hist=[])
    r = val([prof(), twin])
    assert r['status'] == 'held' and 'second_same_name_profile' in r['flags']
    elsewhere = prof(pid='~Jane_Doe3', hist=[dict(position='PhD student', institution=dict(name='MIT', domain='mit.edu'), start=2019, end=2023)], rels=[])
    assert val([prof(), elsewhere])['status'] == 'admitted'      # clearly another person


def test_R_STU_27_common_name_pi_flag_and_generic_role_hold():
    r = val([prof(rels=[dict(relation='PhD Advisor', name='Wei Wang')])], pi=['Wei Wang'])
    assert r['status'] == 'admitted' and 'common_name_pi' in r['flags']
    gen = [dict(position='Graduate student', institution=dict(name='HKUST', domain='ust.hk'), start=2019, end=2023)]
    assert val([prof(hist=gen, rels=[dict(relation='Advisor', name='Ada Lovelace')])])['status'] == 'held'
    assert val([prof(hist=gen)])['role'] == 'phd'                   # a PhD Advisor relation fixes the role


class Resp:
    def __init__(self, code, body):
        self.status_code, self._b = code, body
        self.text = json.dumps(body)

    def json(self):
        return self._b


class Fake:
    def __init__(self, codes):
        self.codes, self.headers, self.calls = list(codes), {}, []

    def post(self, url, **kw):
        self.calls.append(('post', url))
        return Resp(200, dict(token='tok'))

    def get(self, url, **kw):
        self.calls.append(('get', kw['params']['term']))
        c = self.codes.pop(0)
        return Resp(c, dict(profiles=[prof()], count=1) if c == 200 else {})


def env(tmp_path):
    p = tmp_path / 'e.env'
    p.write_text('OPENREVIEW_USERNAME=x@example.org\nOPENREVIEW_PASSWORD=pw\n')
    return p


def client(tmp_path, codes, **kw):
    t = [0.0]
    sl = []
    cl = O.Client(tmp_path / 'c', state=tmp_path / 's', session=Fake(codes), env_path=env(tmp_path), clock=lambda: t[0] + sum(sl), sleep=sl.append, **kw)
    cl.sleeps = sl
    return cl


def test_R_STU_27_cache_means_no_request_is_repeated_and_spacing_holds(tmp_path):
    cl = client(tmp_path, [200, 200])
    cl.search('Jane Doe')
    cl.search('Jane Doe')
    cl.search('John Roe')
    assert [c for c in cl.session.calls if c[0] == 'get'] == [('get', 'Jane Doe'), ('get', 'John Roe')]
    assert cl.n == 3 and all(s >= 9.9 for s in cl.sleeps[1:]) and oct(O.term_file(tmp_path / 'c', 'Jane Doe').stat().st_mode)[-3:] == '600'


@pytest.mark.parametrize('code', [429, 401, 403])
def test_R_STU_27_first_refusal_stops_for_the_day_without_retry(tmp_path, code):
    cl = client(tmp_path, [code, 200])
    with pytest.raises(O.Stop):
        cl.search('Jane Doe')
    assert len([c for c in cl.session.calls if c[0] == 'get']) == 1
    with pytest.raises(O.Stop):                                  # a new process the same UTC day refuses to start
        O.Client(tmp_path / 'c', state=tmp_path / 's', session=Fake([200]), env_path=env(tmp_path))
    O.Client(tmp_path / 'c', state=tmp_path / 's', dry=True)     # dry run is allowed


def test_R_STU_27_budget_and_dry_run_make_no_request(tmp_path):
    cl = client(tmp_path, [200, 200], budget=2)                  # login + one search
    cl.search('Jane Doe')
    with pytest.raises(O.Stop):
        cl.search('John Roe')
    dry = O.Client(tmp_path / 'c', state=tmp_path / 's', dry=True, session=Fake([]))
    assert dry.search('Jane Doe')['profiles'] and dry.search('Never Cached') is None and dry.session.calls == []


def test_R_STU_27_challenge_text_stops(tmp_path):
    cl = client(tmp_path, [200])
    cl.session.get = lambda url, **kw: Resp(200, dict(note='Please complete the captcha'))
    cl.login()
    with pytest.raises(O.Stop):
        cl.search('Jane Doe')


def test_R_STU_27_run_writes_reviewed_additions_shape_from_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(O, 'school_spec', lambda s: SPEC)
    cl = client(tmp_path, [200], dry=False)
    cand = [dict(school='x', pi='Ada Lovelace', pinames=PI, window=list(WIN), name='Jane Doe', score=1.0)]
    out = O.run('x', tmp_path / 'c', cands=cand, client=cl)
    assert list(out) [:3] == ['school', 'generated_at', 'rules'] and 'R-STU-27' in out['rules'] and out['papers'] == []
    assert len(out['students']) == 1 and len(out['students'][0]['sha256']) == 64 and out['summary']['requests'] == 2


def test_R_STU_27_credentials_never_appear_in_output(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(O, 'school_spec', lambda s: SPEC)
    cl = client(tmp_path, [200])
    out = O.run('x', tmp_path / 'c', cands=[dict(school='x', pi='Ada Lovelace', pinames=PI, window=list(WIN), name='Jane Doe', score=1.0)], client=cl)
    blob = json.dumps(out) + capsys.readouterr().out
    assert 'example.org' not in blob and 'OPENREVIEW_PASSWORD' not in blob and '"pw"' not in blob
    assert 'host-rulings' in (O.__doc__ or '')


def test_R_STU_27_candidates_frozen_rule_and_priority():
    def mk(pi, cand, y, last=True, school='X'):
        return dict(pi=pi, title=f't{y}{cand}', year=y, oa=f'{pi}{cand}{y}', byline=[cand, pi], byline_school=[cand, pi],
                    authorship=dict(position='last' if last else 'middle', raw_name=pi))
    papers = [mk('Ada Lovelace', 'Jane Doe', y) for y in (2019, 2020, 2021)] + [mk('Alan Turing', 'Joe Blow', y) for y in (2019, 2020, 2021)]
    pis = [dict(pi='Ada Lovelace', names=['Ada Lovelace'], periods=[dict(start='2018', end=None)]), dict(pi='Alan Turing', names=['Alan Turing'])]
    stu = {'Alan Turing': [dict(name=f'S{i} Z') for i in range(1)]}
    data = dict(zip(['pis.json', 'students.json', 'lab_papers.jsonl.gz'], [pis, stu, papers]))
    out = C.generate('x', base=data.get)
    assert [c['name'] for c in out] == ['Jane Doe', 'Joe Blow'] and out[0]['n_students'] == 0 and out[0]['window'] == [2018, 2026]
    assert C.WEIGHTS['bias'] == -3.51 and C.THRESHOLD == -0.642
    assert C.generate('x', base=data.get, include_all=False) and all(len(c['name'].split()) >= 2 for c in out)


def test_R_STU_27_is_documented_with_host_ruling():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert '### R-STU-27' in (root / 'docs/RULES.md').read_text()
    h = json.loads((root / 'docs/host-rulings.json').read_text())
    r = next(x for x in h['hosts'] if x['host'] == 'api2.openreview.net')
    assert r['host_use'] == 'bounded' and r['min_delay_seconds'] >= 10 and r['stop_on'] and r['ruling_date'] == '2026-11-13'


def test_R_STU_27_a_url_containing_email_is_never_sent(tmp_path):
    cl = client(tmp_path, [200, 200])
    with pytest.raises(ValueError):
        cl.search('x email=a')                       # the search term would put email= into the query string
    with pytest.raises(ValueError):
        O.guard_url('https://api2.openreview.net/profiles?email=a')
    O.guard_url(O.BASE + '/profiles/search', {'term': 'Jane Doe', 'es': 'true'})
    assert not [c for c in cl.session.calls if c[0] == 'get']
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    h = json.loads((root / 'docs/host-rulings.json').read_text())
    r = next(x for x in h['hosts'] if x['host'] == 'api2.openreview.net')
    assert r['robots']['disallow'] == '/*?*email=' and r['robots']['checked'] == '2026-11-13'


def test_named_candidates_look_up_only_the_given_pairs():
    """--names: specific recall-missing (PI, name) pairs become candidates; unknown PIs, one-token names and repeats are skipped (2026-11-14)."""
    import selfdeclared_candidates as C
    data = {'pis.json': [{'pi': 'Ila Fiete', 'names': ['Ila Fiete'], 'periods': [{'start': '2019-07', 'end': None}]}], 'students.json': {'Ila Fiete': [{'name': 'Ann Lee'}]}}
    got = C.named_candidates('mit', [('Ila Fiete', 'Caitlin Lienkaemper'), ('Ila Fiete', 'Caitlin Lienkaemper'), ('Nobody', 'Jane Doe'), ('Ila Fiete', 'Madonna')], base=lambda n: data[n])
    assert [c['name'] for c in got] == ['Caitlin Lienkaemper']
    assert got[0]['window'] == [2019, 2026] and got[0]['n_students'] == 1 and got[0]['pinames']


def test_overlap_tolerates_string_and_missing_years():
    """2026-11-13 Stanford run crashed: a history year or window year was a string (str <= int)."""
    assert O._ov(dict(start='2021', end='2024'), (2020, 2026))
    assert O._ov(dict(start=2021, end=None), ('2020', '2026'))
    assert not O._ov(dict(start='2010', end='2012'), (2020, 2026))
    assert O._ov(dict(start='bad', end=None), (2020, 2026))


def test_expected_graduation_year_is_a_current_student():
    """A history end year in the capture year or later is an expected graduation (Berkeley Xutao Ma 2025-2030 was an alumnus): current, years end capped."""
    for end, alumni, last in ((2030, False, 2026), (2026, False, 2026), (2023, True, 2023), (None, False, 2026)):
        hist = [dict(position='PhD student', institution=dict(name='HKUST', domain='cse.ust.hk'), start=2021, end=end)]
        r = val([prof(hist=hist)])
        row = O.build_row(r, dict(pi='Ada Lovelace', name='Jane Doe', window=WIN), 'ab' * 32, '2026-11-13T00:00:00')
        assert row['alumni'] is alumni and row['years'] == [2021, last]
