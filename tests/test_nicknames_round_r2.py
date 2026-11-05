"""R-LNK-04b (2026-11-05, round-r2 pooled failures): Fotis/Fotios and Giorgos/Georgios are nickname pairs; Robert/Robin is not (Netzorg is a
reviewed same-person decision), and Izzy stays."""
import json
from pathlib import Path

import pytest

from pihier import names

HIER = Path(__file__).resolve().parents[1] / 'hierarchy' / 'reviewed'


@pytest.fixture
def table(monkeypatch):
    monkeypatch.setattr(names.P, 'data', lambda n, *a, **k: HIER / n)
    monkeypatch.setattr(names, 'NICK_MAP', None)
    yield
    monkeypatch.setattr(names, 'NICK_MAP', None)


def test_greek_short_forms(table):
    assert names.nick_ok('fotis', 'fotios') and names.nick_ok('giorgos', 'georgios') and names.nick_ok('izzy', 'isabel')


def test_robin_is_not_a_nickname_of_robert(table):
    assert not names.nick_ok('robin', 'robert')


def test_netzorg_is_a_reviewed_same_person_decision():
    rev = json.loads((HIER / 'student-identity-review.json').read_text())
    x = next(r for r in rev if r['pi'] == 'Bin Yu' and 'Netzorg' in r['a'][1])
    assert x['verdict'] == 'same_person' and x['b'][1] == 'Robin Netzorg' and all(len(e['sha256']) == 64 for e in x['evidence'])
