"""Manifest of a school's gitignored inputs: write, then check detects a missing, changed and unlisted file; build outputs are not inputs."""
import hashlib

import pytest

import input_manifest as M


@pytest.fixture(autouse=True)
def _split_placement(monkeypatch):
    """The fixture tree is hierarchy/<school>/...; the school placement has its own test below."""
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', 'split')


def tree(tmp_path):
    s = tmp_path / 'hierarchy' / 'newu'
    (s / 'derived').mkdir(parents=True)
    (s / 'raw').mkdir()
    (tmp_path / 'listings' / 'newu' / 'derived').mkdir(parents=True)
    (s / 'derived' / 'census-faculty.json').write_text('{"faculty": []}')
    (s / 'derived' / 'pis.json').write_text('output')
    (s / 'raw' / 'openalex-sweep.sqlite').write_bytes(b'x' * 20000)
    (tmp_path / 'listings' / 'newu' / 'derived' / 'listings.json').write_text('[]')
    return tmp_path


def test_write_hashes_inputs_not_outputs(tmp_path):
    root = tree(tmp_path)
    files = M.write(root, 'newu')
    assert set(files) == {'hierarchy/newu/derived/census-faculty.json', 'hierarchy/newu/raw/openalex-sweep.sqlite', 'listings/newu/derived/listings.json'}
    assert files['hierarchy/newu/raw/openalex-sweep.sqlite'] == {'sha256': hashlib.sha256(b'x' * 20000).hexdigest(), 'bytes': 20000}
    assert M.check(root, 'newu') == []


def test_check_names_missing_changed_and_new(tmp_path):
    root = tree(tmp_path)
    M.write(root, 'newu')
    (root / 'hierarchy/newu/derived/census-faculty.json').write_text('{"faculty": [1]}')   # changed (size differs)
    (root / 'hierarchy/newu/raw/openalex-sweep.sqlite').write_bytes(b'y' * 20000)          # changed (same size, other bytes)
    (root / 'listings/newu/derived/listings.json').unlink()                               # missing
    (root / 'hierarchy/newu/derived/collection.json.gz').write_bytes(b'z')                # new
    bad = dict(M.check(root, 'newu'))
    assert bad['hierarchy/newu/derived/census-faculty.json'].startswith('size')
    assert bad['hierarchy/newu/raw/openalex-sweep.sqlite'] == 'sha256 changed'
    assert bad['listings/newu/derived/listings.json'] == 'missing'
    assert bad['hierarchy/newu/derived/collection.json.gz'] == 'not in the manifest'


def test_cli_exit_codes(tmp_path, capsys):
    root = tree(tmp_path)
    assert M.main(['check', 'newu', '--root', str(root)]) == 1   # no manifest yet
    assert M.main(['write', 'newu', '--root', str(root)]) == 0
    assert M.main(['check', 'newu', '--root', str(root)]) == 0


def test_mutable_store_change_warns_but_passes(tmp_path, capsys):
    root = tree(tmp_path)
    (root / 'hierarchy/newu/raw/school-captures.sqlite').write_bytes(b'a' * 10)
    M.write(root, 'newu')
    (root / 'hierarchy/newu/raw/school-captures.sqlite').write_bytes(b'b' * 10)   # a collector appended
    assert M.main(['check', 'newu', '--root', str(root)]) == 0
    assert 'mutable store' in capsys.readouterr().out


def test_school_placement_manifest_lies_in_derived_and_is_not_its_own_input(tmp_path, monkeypatch):
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', 'school')
    s = tmp_path / 'schools' / 'newu'
    (s / 'derived').mkdir(parents=True)
    (s / 'raw').mkdir()
    (s / 'listings' / 'derived').mkdir(parents=True)
    (s / 'derived' / 'census-faculty.json').write_text('{"faculty": []}')
    (s / 'raw' / 'openalex-sweep.sqlite').write_bytes(b'x' * 100)
    files = M.write(tmp_path, 'newu')
    assert set(files) == {'hierarchy/newu/derived/census-faculty.json', 'hierarchy/newu/raw/openalex-sweep.sqlite'}   # the keys are stable labels
    assert M.manifest_path(tmp_path, 'newu') == s / 'derived' / 'inputs-manifest.sha256.json' and M.manifest_path(tmp_path, 'newu').exists()
    assert M.check(tmp_path, 'newu') == []
