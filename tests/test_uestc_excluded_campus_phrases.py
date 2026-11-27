"""An excluded campus cannot borrow UESTC's derived parent ID; real dual evidence survives."""
import copy
from pathlib import Path
import tomllib

import pytest
import school_config as S
from pihier import common as C, papers

MAIN = 'University of Electronic Science and Technology of China'
OA = 'https://openalex.org/'
OBSERVED = [
    'School of Arts and Sciences, Chengdu College of University of Electronic Science and Technology of China',
    'School of Computer Science, Zhongshan Institute, University of Electronic Science and Technology of China, Zhongshan, China',
    'School of Computer, Zhongshan Institute, University of Electronic Science and Technology of China, Zhongshan, China',
    'Zhongshan Institute, University of Electronic Science and Technology of China, Guangdong, 528402 China',
    'Zhongshan InstituteUniversity of Electronic Science and Technology of China Guangdong 528402 China',
]


@pytest.fixture(autouse=True)
def school_charter(monkeypatch):
    cfg = tomllib.loads((Path(__file__).resolve().parents[1] / 'schools' / 'uestc.toml').read_text())
    original = S.get
    monkeypatch.setattr(S, 'get', lambda key: cfg if key == 'uestc' else original(key))


def authorship(raw, metadata='both'):
    ids = {'primary_only': ['I150229711'], 'excluded_only': ['I4405281183'],
           'both': ['I150229711', 'I4405281183'], 'none': []}[metadata]
    return dict(raw_affiliation_strings=raw,
                institutions=[dict(id=OA + key, display_name=key, lineage=[OA + key]) for key in ids])


@pytest.mark.parametrize('raw', OBSERVED)
@pytest.mark.parametrize('metadata', ['primary_only', 'excluded_only', 'both', 'none'])
def test_observed_child_only_authorship_cannot_borrow_primary_id(raw, metadata):
    source = authorship([raw], metadata)
    original = copy.deepcopy(source)
    assert C.excluded_school_only(source, 'uestc')
    assert papers._authorship_school_via({}, source, OA + 'I150229711', S.aff_rx('uestc'), school='uestc') == []
    assert source == original


@pytest.mark.parametrize('raw', [
    [f'School of Computer Science and Engineering, {MAIN}'],
    [OBSERVED[0], f'School of Computer Science and Engineering, {MAIN}'],
    [f'School of Computer Science and Engineering, {MAIN}; {OBSERVED[1]}'],
    [f'{OBSERVED[4]}; School of Computer Science and Engineering, {MAIN}'],
    [f'Shenzhen Institute for Advanced Study, {MAIN}, Shenzhen, China'],
    [f'State Key Laboratory of Electronic Thin Films and Integrated Devices, {MAIN}'],
])
def test_independent_main_dual_and_included_units_remain_available(raw):
    source = authorship(raw)
    original = copy.deepcopy(source)
    assert not C.excluded_school_only(source, 'uestc')
    assert papers._authorship_school_via({}, source, OA + 'I150229711', S.aff_rx('uestc'), school='uestc')
    assert source == original


@pytest.mark.parametrize('raw', ['UESTC Chengdu College', 'UESTC Zhongshan Institute', '电子科技大学成都学院', '电子科技大学中山学院'])
def test_existing_forward_and_han_exclusions_are_preserved(raw):
    assert C.excluded_school_only(authorship([raw]), 'uestc')


def test_primary_metadata_without_literal_campus_evidence_is_not_newly_excluded():
    assert not C.excluded_school_only(authorship([], 'primary_only'), 'uestc')
