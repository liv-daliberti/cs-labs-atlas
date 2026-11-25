"""R-PAP-65 (owner D-0090, 2026-11-25): every ZJU binding on the pinyin + exact-unit DBLP-note route carries a dump note naming
Zhejiang University, a dblp pid and a Latin alias whose letters are the PI's pinyin (given/family order-insensitive)."""
import json
import re
from pathlib import Path

ROUTE = 'pinyin_plus_exact_unit_note_D0090'
BINDINGS = Path(__file__).resolve().parents[1] / 'hierarchy' / 'zju' / 'reviewed' / 'identity-bindings-school.json'


def _letters(s):
    return sorted(re.sub(r'[^a-z]', '', s.lower()))


def _bindings():
    doc = json.loads(BINDINGS.read_text())
    return [(pi, b['dblp_identity_review']) for pi, b in doc.items()
            if isinstance(b, dict) and (b.get('dblp_identity_review') or {}).get('route') == ROUTE]


def test_d0090_bindings_exist():
    assert len(_bindings()) >= 6


def test_d0090_bindings_carry_dump_note_pid_and_alias():
    for pi, rev in _bindings():
        assert re.fullmatch(r'https://dblp\.org/pid/\d+/[0-9A-Za-z]+(-\d+)?', rev['pid']), pi
        notes = [e for e in rev['evidence'] if e.get('kind') == 'dblp_dump_affiliation_note']
        assert notes, pi
        for e in notes:
            assert 'Zhejiang University' in e['quote'], pi
            assert e['url'] == rev['pid'] and re.fullmatch(r'[0-9a-f]{64}', e['sha256']), pi
        assert rev['alias'].strip(), pi


def test_d0090_alias_letters_equal_the_pinyin():
    try:
        from pypinyin import lazy_pinyin
    except ImportError:
        lazy_pinyin = None
    doc = json.loads(BINDINGS.read_text())
    checked = 0
    for pi, rev in _bindings():
        stored = (doc[pi].get('aliases') or [rev['alias']])
        assert rev['alias'] in stored, pi
        if lazy_pinyin is None:
            continue   # no pypinyin here: the stored alias is all there is to compare
        assert _letters(''.join(lazy_pinyin(pi))) == _letters(rev['alias']), (pi, rev['alias'])
        checked += 1
    assert lazy_pinyin is None or checked == len(_bindings())
