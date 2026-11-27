"""The third data placement, 'school' (owner decision 2026-11-26): every per-school DATA_FILES entry and the per-school slots resolve to
<SCHOOLS_TREE>/<school>/..., selected with CS_ATLAS_DATA_LAYOUT=school; the default stays 'split', so today's paths are unchanged."""
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import atlas_paths as P

CODE = Path(__file__).resolve().parents[1]


def per_school():
    return [(n, k, f, s) for n, k, f, s in P.DATA_FILES if '{school}' in s]


def test_default_is_unchanged_and_school_is_a_selectable_third_placement(monkeypatch):
    assert P.DATA_LAYOUT_DEFAULT == 'split'
    monkeypatch.delenv('CS_ATLAS_DATA_LAYOUT', raising=False)
    assert P.data_layout() == 'split'
    assert P.data('pis.json', 'mit', root='/r') == Path('/r/hierarchy/mit/derived/pis.json')
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', 'school')
    assert P.data_layout() == 'school'
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', 'nonsense')
    with pytest.raises(ValueError):
        P.data_layout()


def test_every_per_school_entry_resolves_under_schools_school():
    assert per_school()
    for name, kind, flat, split in per_school():
        rel = P.data(name, 'mit', root='/r', layout='school').relative_to('/r')
        assert rel.parts[:2] == ('schools', 'mit'), (name, rel)
        part = rel.parts[2]
        if kind == 'reviewed':
            assert part == 'reviewed' or part == 'listings', (name, rel)
        if kind == 'raw':
            assert part in ('raw', 'listings'), (name, rel)


def test_kind_directories_follow_the_split_ones():
    d = lambda n, s='mit': P.data(n, s, root='/r', layout='school')   # noqa: E731
    assert d('pis.json') == Path('/r/schools/mit/derived/pis.json')
    assert d('openalex-sweep.sqlite') == Path('/r/schools/mit/raw/openalex-sweep.sqlite')
    assert d('school-captures.sqlite') == Path('/r/schools/mit/raw/school-captures.sqlite')
    assert d('gap-evidence.json') == Path('/r/schools/mit/reviewed/gap-evidence.json')
    assert d('faculty-periods.json') == Path('/r/schools/mit/reviewed/faculty-periods.json')
    assert d('census-faculty.json') == Path('/r/schools/mit/derived/census-faculty.json')
    assert d('dblp-recover.sqlite') == Path('/r/schools/mit/work/dblp-recover.sqlite')
    assert d('tmp') == Path('/r/schools/mit/tmp')
    assert d('listings.json') == Path('/r/schools/mit/listings/derived/listings.json')
    assert d('listings-captures.sqlite') == Path('/r/schools/mit/listings/raw/captures.sqlite')
    assert d('reader.jsonl.gz') == Path('/r/schools/mit/derived/reader.jsonl.gz')
    assert d('sweep.log') == Path('/r/schools/mit/work/sweep.log')
    assert d('listings-input.json') == Path('/r/schools/mit/reviewed/listings-input.json')


def test_shared_entries_do_not_move():
    for name, kind, flat, split in P.DATA_FILES:
        if '{school}' not in split:
            assert P.data(name, root='/r', layout='school') == P.data(name, root='/r', layout='split'), name


def test_without_a_root_schools_follow_the_schools_tree_slot(monkeypatch):
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', 'school')
    assert P.data('pis.json', 'cmu') == P.SCHOOLS_TREE / 'cmu' / 'derived' / 'pis.json'


def test_data_w_creates_the_school_directory(tmp_path, monkeypatch):
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', 'school')
    p = P.data_w('pis.json', 'mit', root=tmp_path)
    assert p == tmp_path / 'schools' / 'mit' / 'derived' / 'pis.json' and p.parent.is_dir()


def test_school_slots_store_checks_ai(monkeypatch):
    monkeypatch.delenv('CS_ATLAS_DATA_LAYOUT', raising=False)
    assert P.store('mit') == P.STORES / 'mit'
    assert P.checks_db('mit') == P.FT_CHECKS / 'mit.sqlite'
    assert P.ai_dir('mit', 'bge_m3') == P.EMBEDDINGS / 'bge_m3' / 'mit'
    monkeypatch.setenv('CS_ATLAS_DATA_LAYOUT', 'school')
    assert P.store('mit') == P.SCHOOLS_TREE / 'mit' / 'store'
    assert P.store('stanford') == P.SCHOOLS_TREE / 'stanford' / 'store'
    assert P.checks_db('mit') == P.SCHOOLS_TREE / 'mit' / 'checks' / 'mit.sqlite'
    assert P.ai_dir('mit', 'bge_m3') == P.SCHOOLS_TREE / 'mit' / 'ai' / 'embeddings' / 'bge_m3'
    assert P.school_dir('mit', 'reviewed') == P.SCHOOLS_TREE / 'mit' / 'reviewed'
    with pytest.raises(ValueError):
        P.school_dir('mit', 'nonsense')


def test_flat_of_reads_the_school_placement_back_to_the_flat_names():
    for name, kind, flat, split in per_school():
        rel = str(P.data(name, 'mit', root='/r', layout='school').relative_to('/r'))
        assert P.flat_of(rel) == flat.format(school='mit'), name
    assert P.flat_of('schools/mit/derived/pis.json') == 'hierarchy/mit/pis.json'


def test_slurm_logs_slot_and_paths_sh(monkeypatch):
    assert P.SLURM_LOGS == P.ROOT / 'logs' / 'slurm'
    assert 'CS_ATLAS_SLURM_LOGS=' in P.shell()
    assert (CODE / 'paths.sh').read_text() == P.shell()


@pytest.mark.parametrize('layout_name', ['flat', 'split', 'school'])
def test_python_cli_resolves_in_every_placement(layout_name):
    env = dict(os.environ, CS_ATLAS_DATA_LAYOUT=layout_name)
    r = subprocess.run([sys.executable, '-c', 'import atlas_paths as P; print(P.data("pis.json", "mit", root="/r"))'],
                       capture_output=True, text=True, env=dict(env, PYTHONPATH=str(CODE / 'tools')), check=True)
    assert re.match(r'/r/(hierarchy/mit(/derived)?|schools/mit/derived)/pis.json$', r.stdout.strip())
