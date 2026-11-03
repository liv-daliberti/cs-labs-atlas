"""accuracy/sample.py --school: a school outside the six released ones is drawn with the same seed and method into its own
file, and the released draws are unchanged (the 2026-11-02 Michigan stage 9)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'accuracy'))
import sample as S  # noqa: E402


def test_alumni_fallback_rules():
    rel = {'type': 'researched_advising', 'years': [2019, 2021]}
    assert S.alumni_relation(rel, ['phd_alumnus']) == 2021
    assert S.alumni_relation(rel, ['phd']) is None                  # a current student has no PhD year
    assert S.alumni_relation(rel, ['postdoc_alumnus']) is None
    assert S.alumni_relation({'type': 'researched_membership', 'years': [2020]}, ['phd_alumnus']) is None


def test_thesis_relation_unchanged():
    rel = {'type': 'thesis_adviser', 'years': [2020], 'sources': [{'kind': 'phd_thesis', 'url': 'u', 'quote': 'Degree: PhD, 2020'}]}
    assert S.thesis_relation(rel, 'cmu') == 2020
    assert S.thesis_relation({'type': 'researched_advising', 'years': [2020], 'sources': [{'url': 'u', 'quote': 'PhD alumni'}]}, 'cmu') is None


@pytest.mark.nfs
def test_released_draw_independent_of_other_schools(tmp_path):
    one = S.main(['mit'], tmp_path / 'a.json')['schools']['mit']
    two = S.main(['michigan', 'mit'], tmp_path / 'b.json')['schools']['mit']   # the seed is reset per school
    assert one == two
    assert json.loads((tmp_path / 'a.json').read_text())['schools']['mit']['lab_precision'] == one['lab_precision']
    assert S.OUT.name == 'sample.json' and S.SCHOOLS == ['princeton', 'cmu', 'epfl', 'mit', 'berkeley', 'stanford']
