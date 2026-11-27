"""Guard (2026-11-26): live code reads and writes per-school data through atlas_paths, never by hand-joining hierarchy/<school>/..., stores/<school>,
fulltext-push/checks, listings/<school> or captures/<school> (SCHOOL-LAYOUT-PLAN.md: the per-school move is then a flip of the placement and needs no
compatibility links). Comments and docstrings are exempt; a code line that must name such a path (a recorded wording, a release's flat layout,
tracked code that stays in hierarchy/) carries `route-ok` and a reason. Frozen history (vendor/, archive/, docs/) is not scanned.

The second pass: fulltext-push/, ai-writing/ and the lab-page tool kits are held by live sessions and still hand-join; they may not gain a hit (SECOND_PASS
is the count per file on 2026-11-26; lower it as a file is routed, delete the entry at zero) and a new file there must have none."""
import collections

import pytest

import route_school_paths as R

SECOND_PASS = {
    'ai-writing/dose/lab_ai_main_tags.py': 1,
    'ai-writing/entropy32/e32.py': 1,
    'ai-writing/entropy32/ftrefs.py': 1,
    'ai-writing/figlab/manifest.py': 1,
    'ai-writing/sections/pilot.py': 2,
    'ai-writing/sections/review.py': 1,
    'ai-writing/sections/run_split.py': 1,
    'ai-writing/study/study_common.py': 2,
    'ai-writing/study/study_delta_build.py': 1,
    'ai-writing/study/study_delta_oa.py': 1,
    'ai-writing/study/study_hetero_attr.py': 1,
    'ai-writing/study/study_hetero_authors.py': 1,
    'ai-writing/study/study_prep.py': 2,
    'ai-writing/study/study_report.py': 1,
    'ai-writing/study/study_snapshot.py': 5,
    'fulltext-push/add_works.py': 1,
    'fulltext-push/addworks-1029.slurm': 1,
    'fulltext-push/addworks-1104.slurm': 1,
    'fulltext-push/addworks-1105.slurm': 1,
    'fulltext-push/berkeley_catalog.py': 1,
    'fulltext-push/chain_labpages.sh': 1,
    'fulltext-push/chain_others.sh': 1,
    'fulltext-push/chain_refresh.sh': 1,
    'fulltext-push/channels-1030.slurm': 1,
    'fulltext-push/checks.py': 1,
    'fulltext-push/defense-scan.slurm': 2,
    'fulltext-push/downloads.slurm': 1,
    'fulltext-push/ftp_common.py': 1,
    'fulltext-push/local-reuse/princeton_import.slurm': 1,
    'fulltext-push/missing_breakdown.py': 1,
    'fulltext-push/newsteps.slurm': 1,
    'fulltext-push/oa_editions.slurm': 1,
    'fulltext-push/princeton_pass.sh': 1,
    'fulltext-push/priority_file.py': 1,
    'fulltext-push/proceedings_extra.py': 1,
    'fulltext-push/recover-1030.slurm': 1,
    'fulltext-push/repath_evidence.py': 1,
    'fulltext-push/repull-addworks.slurm': 1,
    'fulltext-push/review_access.py': 3,
    'fulltext-push/review_identity.py': 3,
    'fulltext-push/school-collector.slurm': 1,
    'fulltext-push/stanford_catalog.py': 2,
    'fulltext-push/wayback_rotate.py': 1,
    'hierarchy/labpage-tools-cmu/w_b05_raw.py': 1,
    'hierarchy/labpage-tools-stanford/seeds.py': 1,
}


def test_live_code_has_no_hardcoded_per_school_paths():
    hits = R.scan(R.REPO, R.ALLOW_PREFIXES)
    assert not hits, 'route these through atlas_paths (data/data_w, store, checks_db, school_part, reviewed_path, school_dir) or add `route-ok: <reason>`:\n' + \
        '\n'.join(f'{p}:{n}: {t[:140]}' for p, n, t in hits)


@pytest.mark.skipif(not (R.REPO / '.git').exists(), reason='needs the git checkout')
def test_second_pass_directories_do_not_gain_hits():
    got = collections.Counter(p for p, _, _ in R.scan(R.REPO, R.ALWAYS) if p.startswith(('fulltext-push/', 'ai-writing/', 'hierarchy/labpage-tools-')))
    worse = {p: (n, SECOND_PASS.get(p, 0)) for p, n in got.items() if n > SECOND_PASS.get(p, 0)}
    assert not worse, f'new hand-joined per-school paths (now, allowed): {worse}'


def hits(path, src):
    return [n for _, n, _ in R.scan_text(path, src)]


def test_scanner_flags_code_not_prose():
    src = '"""doc: hierarchy/<school>/pis.json"""\n# hierarchy/{school}/derived\nx = P.HIERARCHY / key / "raw"\n'
    assert hits('tools/x.py', src) == [3]
    assert hits('tools/x.py', 'def f(s):\n    """hierarchy/{s}/raw"""\n    return f"hierarchy/{s}/derived/a.json"\n') == [3]
    assert hits('tools/x.py', 'y = f"stores/{school}/catalog.sqlite"  # route-ok: recorded wording\n') == []
    assert hits('tools/x.py', 'p = CODE / "hierarchy" / key / "reviewed" / "a.json"\n') == []          # reviewed stays in git
    assert hits('tools/x.py', 'p = CODE / "hierarchy" / key / "derived" / "a.json"\n') == [1]
    assert hits('tools/x.py', 'p = Path(P.STORES) / school\n') == [1]
    assert hits('tools/x.sh', '# stores/$school\nls "$CS_ATLAS_STORES/$school"\n') == [2]
    assert hits('tools/x.sh', 'ls "$(cs_atlas_store "$s")"\n') == []
    assert hits('tests/test_x.py', 'p = tmp / "hierarchy" / "mit" / "raw"\n') == []                    # fixtures are policed elsewhere
