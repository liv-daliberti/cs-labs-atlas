"""An owner robots exception for faculty lists must not open profile pages."""
import pytest
import school_web as W


STUB = '<html><head><title>Request Error</title></head><body>error id 1</body></html>'
FACULTY = 'https://www3.ntu.edu.sg/SCSE/moss_staffac.asp'


@pytest.fixture
def finite_ruling(monkeypatch):
    monkeypatch.setattr(W, '_robots_no_rules_rulings', lambda: {
        'www3.ntu.edu.sg': {'allowed_paths': ['/SCE/moss_staffac.asp', '/SCSE/moss_staffac.asp']},
        'personal.ntu.edu.sg': {},
    })


def test_finite_exception_authorizes_only_listed_paths(finite_ruling):
    assert W.robots_decision(200, STUB, FACULTY)[:2] == (True, True)
    assert W.robots_decision(200, STUB, FACULTY.replace('/SCSE/', '/scse/'))[:2] == (True, True)
    for url in [
        'https://www3.ntu.edu.sg/home/person/',
        'https://www3.ntu.edu.sg/SCSE/moss_staffsearch2014.asp',
        FACULTY + '?profile=1',
        FACULTY + '#profile',
        'https://other.example/SCSE/moss_staffac.asp',
    ]:
        assert W.robots_decision(200, STUB, url)[:2] == (False, False)


def test_scoped_ruling_is_not_exported_to_host_wide_callers(finite_ruling):
    assert W.robots_ruled_hosts() == frozenset({'personal.ntu.edu.sg'})
    assert W.robots_decision(200, STUB, 'https://personal.ntu.edu.sg/person/')[:2] == (True, True)


@pytest.mark.parametrize('status', [-1, 401, 403, 405, 429, 500, 503])
def test_finite_exception_does_not_override_new_access_failures(finite_ruling, status):
    assert W.robots_decision(status, '', FACULTY)[:2] == (False, False)


def test_real_rules_and_challenges_still_close_finite_path(finite_ruling):
    assert W.robots_decision(200, 'User-agent: *\nDisallow: /SCSE/\n', FACULTY)[:2] == (False, False)
    challenge = '<html><title>Just a moment...</title><div class="cf-chl"></div></html>'
    assert W.robots_decision(200, challenge, FACULTY)[:2] == (False, False)
