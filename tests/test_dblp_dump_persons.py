import json
import runpy
import sys
from pathlib import Path

import pytest


@pytest.fixture
def targets(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'argv', ['dblp_dump_persons.py'])
    module = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'tools' / 'dblp_dump_persons.py'), run_name='dump_targets_test')
    monkeypatch.setattr(module['P'], 'data', lambda filename, school=None: tmp_path / filename)
    monkeypatch.setattr(module['CO'], 'section', lambda school: {})
    return module['source_targets'], module['CO']


def write(tmp_path, filename, data):
    (tmp_path / filename).write_text(json.dumps(data))


def test_core_census_pis_are_targets_before_any_native_package_exists(targets, tmp_path):
    lookup, _ = targets
    write(tmp_path, 'census-faculty.json', {'faculty': [
        dict(name='Richard Gibbens', aliases=['Richard J. Gibbens'], is_pi=True,
             dblp=['https://dblp.org/pid/g/RichardJGibbens']),
        dict(name='Graduate Student', is_pi=False, dblp=['https://dblp.org/pid/student']),
    ]})
    pids, names = lookup('cambridge')
    assert pids == {'https://dblp.org/pid/g/RichardJGibbens'}
    assert names == {'richard gibbens', 'richard j gibbens'}


def test_reviewed_addition_id_and_alias_are_targets_without_native_outputs(targets, tmp_path, monkeypatch):
    lookup, overrides = targets
    write(tmp_path, 'census-additions.json', [dict(name='Avery Scientist', is_pi=True, dblp=[])])
    monkeypatch.setattr(overrides, 'section', lambda school: {'Avery Scientist': {
        'dblp': ['https://dblp.org/pid/avery'], 'aliases': ['Avery J. Scientist'],
    }})
    pids, names = lookup('cambridge')
    assert pids == {'https://dblp.org/pid/avery'}
    assert 'avery j scientist' in names


def test_existing_native_names_and_dropped_identity_records_remain_available(targets, tmp_path):
    lookup, _ = targets
    write(tmp_path, 'pis.json', [dict(names=['Avery Scientist'], dblp=['https://dblp.org/pid/avery/'],
                                     dblpDropped=['https://dblp.org/pid/dropped'])])
    assert lookup('cambridge') == ({'https://dblp.org/pid/avery', 'https://dblp.org/pid/dropped'}, {'avery scientist'})


def test_bare_census_and_legacy_string_pid_are_supported(targets, tmp_path):
    lookup, _ = targets
    write(tmp_path, 'census-faculty.json', [dict(name='Avery Scientist', is_pi=True, dblp='https://dblp.org/pid/avery')])
    assert lookup('cambridge') == ({'https://dblp.org/pid/avery'}, {'avery scientist'})


def test_native_pi_key_applies_reviewed_bindings_and_exclusions(targets, tmp_path, monkeypatch):
    lookup, overrides = targets
    write(tmp_path, 'pis.json', [dict(pi='Avery Scientist', names=['Avery Scientist'], dblp=[]),
                                 dict(pi='Excluded Person', names=['Excluded Person'], dblp=['https://dblp.org/pid/excluded'])])
    monkeypatch.setattr(overrides, 'section', lambda school: {
        'Avery Scientist': {'dblp': ['https://dblp.org/pid/avery'], 'aliases': ['Avery J. Scientist']},
        'Excluded Person': {'exclude': True},
    })
    assert lookup('cambridge') == ({'https://dblp.org/pid/avery'}, {'avery scientist', 'avery j scientist'})


def test_explicit_nonpi_additions_and_reviewed_exclusions_are_not_pi_targets(targets, tmp_path, monkeypatch):
    lookup, overrides = targets
    write(tmp_path, 'census-additions.json', [dict(name='Not Faculty', is_pi=False, dblp=['https://dblp.org/pid/nonpi'])])
    write(tmp_path, 'census-faculty.json', {'faculty': [dict(name='Excluded Person', is_pi=True, dblp=['https://dblp.org/pid/excluded'])]})
    monkeypatch.setattr(overrides, 'section', lambda school: {'Excluded Person': {'exclude': True}})
    assert lookup('cambridge') == (set(), set())


def test_missing_optional_native_and_census_files_are_not_stub_requirements(targets):
    lookup, _ = targets
    assert lookup('cambridge') == (set(), set())
