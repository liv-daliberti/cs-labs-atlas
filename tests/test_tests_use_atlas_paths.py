"""Fixtures reach their files through atlas_paths.data, never by joining 'hierarchy' by hand (the move of 2026-11-01 broke every fixture that did).
The allowed files have the layout itself as their subject (path strings, a flat fixture on purpose) or name repository paths of code."""
import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ALLOWED = {'test_relocate_data.py', 'test_data_routing.py', 'test_labpage_audit_roots.py', 'test_script_map.py', 'test_slurm_snapshot.py',
           'test_vendor_and_paths.py', 'test_tests_use_atlas_paths.py', 'test_protocol_rules_michigan.py', 'test_job_code_snapshot.py',
           'test_atlas_paths.py', 'test_schemas.py', 'test_ft_data_slots.py', 'test_atlas_release.py'}
HAND_JOIN = re.compile(r"/\s*'(hierarchy|census|listings|periods)'\s*/|(tmp_path|root|WORK|HERE)\s*/\s*'(hierarchy|census|periods)'|[(,]\s*'hierarchy/")


def test_fixtures_do_not_join_hierarchy_by_hand():
    bad = []
    for f in sorted(TESTS.glob('test_*.py')):
        if f.name in ALLOWED:
            continue
        for n, ln in enumerate(f.read_text().splitlines(), 1):
            if HAND_JOIN.search(ln) and 'route-ok' not in ln:
                bad.append(f'{f.name}:{n}: {ln.strip()[:100]}')
    assert not bad, 'use atlas_paths.data(..., root=tmp_path) so the test runs in either layout:\n' + '\n'.join(bad)
