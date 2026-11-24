"""School-local home reviews must reach the shared input consumed by the site."""
import hashlib
import json
import runpy
from pathlib import Path

import home_department_registry as HOME
import make_release as R


def decision(name='Ann', home='Statistics', **extra):
    return dict(school='stanford', name=name, status='accepted', home_department=home,
                home_basis='listed_title', reviewed_home_evidence=[dict(url='https://example.edu/ann', sha256='a' * 64, quote='Ann')],
                evidence=dict(url='https://example.edu/ann', sha256='a' * 64, quote='Ann'), **extra)


def write_inputs(root, shared, local):
    hierarchy = root / R.REL_HIERARCHY
    (hierarchy / 'stanford').mkdir(parents=True)
    (hierarchy / 'home-departments.json').write_text(json.dumps(shared))
    path = hierarchy / 'stanford/home-departments.json'
    path.write_text(json.dumps(local))
    return hierarchy, path


def test_local_review_reaches_the_legacy_site_builder_and_manifest(tmp_path):
    old = decision(home='Computer Science')
    reviewed = decision()
    other = dict(decision(name='Other'), school='other')
    hierarchy, local = write_inputs(tmp_path, [old, other], [reviewed])
    original_local = local.read_bytes()
    entry = R.freeze_home_departments(tmp_path, ['stanford'])
    shared = hierarchy / 'home-departments.json'
    rows = json.loads(shared.read_text())
    assert rows == [other, reviewed]
    assert local.read_bytes() == original_local
    assert entry == dict(bytes=shared.stat().st_size, sha256=hashlib.sha256(shared.read_bytes()).hexdigest())
    # Exercise the existing site consumer against the newly frozen shared input.
    builder = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'vendor/site_builder/build-cs-hierarchy.py'))
    home = {r['name']: r for r in rows if r['school'] == 'stanford' and r['status'] == 'accepted'}
    pi = dict(pi='Ann', departments=['CS'], rank='courtesy')
    assert builder['department']('stanford', builder['SCHOOLS']['stanford'], pi, home) == ('Statistics', 'affiliated')


def test_local_hold_does_not_reanimate_the_old_shared_home(tmp_path):
    hold = dict(decision(), status='hold', home_department=None)
    hierarchy, _ = write_inputs(tmp_path, [decision(home='Computer Science')], [hold])
    R.freeze_home_departments(tmp_path, ['stanford'])
    rows = json.loads((hierarchy / 'home-departments.json').read_text())
    assert rows == [hold]
    assert not HOME.review(rows[0])['primary_resolved']


def test_per_pi_release_cannot_add_back_a_held_pi_from_the_local_register(tmp_path):
    hierarchy, _ = write_inputs(tmp_path, [], [decision('Included'), decision('Held')])
    per = dict(stanford=dict(plan=dict(partial=True, included=['Included'], held={'Held': ['not admitted']})))
    R.freeze_home_departments(tmp_path, ['stanford'], per)
    assert [r['name'] for r in json.loads((hierarchy / 'home-departments.json').read_text())] == ['Included']


def test_release_with_only_shared_homes_keeps_its_own_snapshot(tmp_path, monkeypatch):
    import atlas_paths as P

    hierarchy, local = write_inputs(tmp_path, [decision()], [])
    local.unlink()
    # There is no fallback to the working registry, even if it would differ.
    monkeypatch.setattr(P, 'HIERARCHY', tmp_path / 'unrelated-live')
    R.freeze_home_departments(tmp_path, ['stanford'])
    assert json.loads((hierarchy / 'home-departments.json').read_text()) == [decision()]
