"""Build preflight: a missing or stub required input makes the build refuse, naming the file."""
import pytest

from pihier import preflight
import atlas_paths as P


def _tree(tmp_path, census_bytes=5000, school='hkust'):
    path = P.data('census-faculty.json', school, root=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'x' * census_bytes)
    return path


def test_a_missing_input_is_named(tmp_path):
    bad = dict(preflight.problems('hkust', root=tmp_path))
    assert any(p.endswith('census-faculty.json') and why == 'missing' for p, why in bad.items())
    with pytest.raises(preflight.MissingInput) as e:
        preflight.check('hkust', root=tmp_path)
    assert 'census-faculty.json' in str(e.value) and 'collection.json.gz' in str(e.value) and 'refusing' in str(e.value)


def test_a_stub_census_is_missing(tmp_path):
    _tree(tmp_path, census_bytes=120, school='tsinghua')   # the 120-byte stub that cut Tsinghua's lab papers from 7,901 to 2,203
    bad = dict(preflight.problems('tsinghua', root=tmp_path))
    assert list(bad.values())[0].startswith('a stub: 120 bytes')
    with pytest.raises(preflight.MissingInput, match='census-faculty.json'):
        preflight.check('tsinghua', root=tmp_path)


def test_complete_inputs_pass(tmp_path):
    _tree(tmp_path, school='tsinghua')
    preflight.check('tsinghua', root=tmp_path)
    assert preflight.required_for('tsinghua') == ['census-faculty.json'] and 'collection.json.gz' in preflight.required_for('zju')


def test_an_empty_census_is_fine_when_the_reviewed_additions_hold_the_faculty(tmp_path):
    _tree(tmp_path, census_bytes=153, school='sjtu')
    with pytest.raises(preflight.MissingInput, match='census-faculty.json'):
        preflight.check('sjtu', root=tmp_path)
    add = P.data('census-additions.json', 'sjtu', root=tmp_path)
    add.parent.mkdir(parents=True, exist_ok=True)
    add.write_bytes(b'x' * 5000)
    preflight.check('sjtu', root=tmp_path)
