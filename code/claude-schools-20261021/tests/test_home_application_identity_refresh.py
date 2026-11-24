"""A home application can preserve reviewed ID additions without accepting a merge."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    'final_home_application_for_tests',
    Path(__file__).resolve().parents[1] / 'reports/homes-finish-1123/apply.py')
APP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(APP)


@pytest.fixture
def approved_refresh(monkeypatch, tmp_path):
    monkeypatch.setattr(APP, 'HERE', tmp_path)
    (tmp_path / 'decisions.json').write_text('{}\n')
    before = dict(pi='Existing Faculty', names=['Existing Faculty'], personIds=['issued-person'],
                  dblp=['https://dblp.org/pid/original'], orcid=[])
    after = {**before, 'orcid': ['0000-0000-0000-0001']}
    review = dict(result='pass', reviewer='independent-home-reviewer',
                  home_decisions_sha256=APP.file_sha(tmp_path / 'decisions.json'), records=1,
                  verdicts=[dict(school='example', name=before['pi'], before=before, after=after,
                                 old_sha256=APP.digest(before), new_sha256=APP.digest(after), verdict='pass')])
    def save():
        (tmp_path / 'identity-refresh-review.json').write_text(json.dumps(review))
    save()
    return before, after, review, save


def test_unchanged_identity_needs_no_refresh_approval(approved_refresh):
    before, _, _, _ = approved_refresh
    (APP.HERE / 'identity-refresh-review.json').unlink()
    APP.verify_identity('example', before['pi'], APP.digest(before), before)


def test_exact_independently_approved_identifier_addition_keeps_the_same_home_subject(approved_refresh):
    before, after, _, _ = approved_refresh
    APP.verify_identity('example', before['pi'], APP.digest(before), after)


@pytest.mark.parametrize('change', ['rename', 'alias', 'person_id', 'remove_identifier'])
def test_even_a_refresh_receipt_cannot_authorize_identity_or_identifier_removal(approved_refresh, change):
    before, after, review, save = approved_refresh
    proposed = copy.deepcopy(after)
    if change == 'rename':
        proposed['pi'] = 'Different Faculty'
    elif change == 'alias':
        proposed['names'].append('New Alias')
    elif change == 'person_id':
        proposed['personIds'].append('different-issued-person')
    else:
        proposed['dblp'] = []
    review['verdicts'][0].update(after=proposed, new_sha256=APP.digest(proposed))
    save()
    with pytest.raises(AssertionError):
        APP.verify_identity('example', before['pi'], APP.digest(before), proposed)


def test_unreviewed_further_identifier_addition_is_refused(approved_refresh):
    before, after, _, _ = approved_refresh
    proposed = {**after, 'dblp': after['dblp'] + ['https://dblp.org/pid/unreviewed']}
    with pytest.raises(AssertionError):
        APP.verify_identity('example', before['pi'], APP.digest(before), proposed)


def test_refresh_approval_is_bound_to_the_reviewed_home_decisions(approved_refresh):
    before, after, _, _ = approved_refresh
    (APP.HERE / 'decisions.json').write_text('{"different": "home"}\n')
    with pytest.raises(AssertionError):
        APP.verify_identity('example', before['pi'], APP.digest(before), after)
