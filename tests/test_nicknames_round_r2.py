"""R-LNK-04b (2026-11-05, round-r2 pooled failures): Fotis/Fotios and Giorgos/Georgios are nickname pairs; Robert/Robin is not (Netzorg is a
reviewed same-person decision), and Izzy stays."""
import json
from pathlib import Path

import pytest

import atlas_paths as P
from pihier import names

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def table(monkeypatch):
    real = P.data
    monkeypatch.setattr(names.P, 'data', lambda n, *a, **k: real('student-identity-review.json', root=ROOT).parent / n)
    monkeypatch.setattr(names, 'NICK_MAP', None)
    yield
    monkeypatch.setattr(names, 'NICK_MAP', None)


def test_R_LNK_04b_greek_short_forms(table):
    assert names.nick_ok('fotis', 'fotios') and names.nick_ok('giorgos', 'georgios') and names.nick_ok('izzy', 'isabel')


def test_R_LNK_04b_robin_is_not_a_nickname_of_robert(table):
    assert not names.nick_ok('robin', 'robert')


def test_R_LNK_04b_netzorg_is_a_reviewed_same_person_decision():
    rev = json.loads(P.data('student-identity-review.json', root=ROOT).read_text())
    x = next(r for r in rev if r['pi'] == 'Bin Yu' and 'Netzorg' in r['a'][1])
    assert x['verdict'] == 'same_person' and x['b'][1] == 'Robin Netzorg' and all(len(e['sha256']) == 64 for e in x['evidence'])


def test_R_LNK_04b_one_person_under_two_labs_keeps_every_alias():
    import inspect
    from pihier import links
    src = inspect.getsource(links.link_students)
    assert "forms[sid] = list(dict.fromkeys(forms.get(sid, []) + fs))" in src   # Netzorg's alias Robin (Bin Yu) survives the Anumanchipalli record
