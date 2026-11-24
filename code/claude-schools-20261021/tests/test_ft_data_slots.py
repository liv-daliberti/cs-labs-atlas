"""The data side of fulltext-push/ (ROADMAP item 10): slots derive from CODE, not from the (snapshot-movable) FULLTEXT_PUSH."""
from pathlib import Path

import atlas_paths as P
import route_ft_data as R


def test_slots_are_the_old_locations_and_survive_a_snapshot():
    code = Path('/c/code')
    p = P._resolve({'CS_ATLAS_CODE': str(code)})
    for name, d in (('FT_DATA', ''), ('FT_RAW', 'raw'), ('FT_CHECKS', 'checks'), ('FT_LOGS', 'logs'), ('FT_LOCAL_REUSE', 'local-reuse')):
        assert p[name] == code / 'fulltext-push' / d if d else p[name] == code / 'fulltext-push'
    q = P._resolve({'CS_ATLAS_CODE': str(code), 'CS_ATLAS_FULLTEXT_PUSH': '/tmp/snap/fulltext-push'})   # a job's code snapshot
    assert q['FULLTEXT_PUSH'] == Path('/tmp/snap/fulltext-push') and q['FT_RAW'] == code / 'fulltext-push' / 'raw'
    assert P.ft_review('20261030') == P.FT_DATA / 'review-20261030'


def test_route_check_finds_hand_joins(tmp_path):
    (tmp_path / 'local-reuse').mkdir()
    (tmp_path / 'a.py').write_text("x = F.HERE / 'raw' / 'a.json'\ny = P.FT_RAW / 'a.json'\nz = HERE / 'review-20261030'\n# HERE / 'logs'\n")
    (tmp_path / 'b.sh').write_text("echo x >> logs/steps.log\necho y >> $CS_ATLAS_FT_LOGS/steps.log\n#SBATCH --output=fulltext-push/logs/x.out\n")
    (tmp_path / 'local-reuse' / 'c.py').write_text("INV = HERE / 'inventory.sqlite'\n")
    got = sorted((f.name, n) for f, n, _ in R.scan(tmp_path))
    assert got == [('a.py', 1), ('a.py', 3), ('b.sh', 1), ('c.py', 1)]


def test_fulltext_push_joins_no_data_directory_by_hand():
    """Every read and write of raw/, checks/, logs/, local-reuse data and review-<stamp>/ goes through the slots, so a code
    snapshot sees the shared data (docs/CONTRIBUTING.md)."""
    assert R.scan(Path(__file__).resolve().parents[1] / 'fulltext-push') == []


def test_route_check_finds_fulltext_push_joins_outside_fulltext_push(tmp_path):
    """FULLTEXT_PUSH / 'raw' in tools/ or vendor/ resolves inside a code snapshot (2026-11-01: s2-pace, labpage_audit, collector_wrapper)."""
    (tmp_path / 'fulltext-push').mkdir()
    (tmp_path / 'tools').mkdir()
    (tmp_path / 'vendor').mkdir()
    (tmp_path / 'tools' / 'a.py').write_text("hf = P.FULLTEXT_PUSH / 'raw' / 'x.json'\nok = P.FULLTEXT_PUSH / 'channel_runner.py'\nok2 = P.FT_RAW / 'x'\n")
    (tmp_path / 'vendor' / 'b.py').write_text("PACE = P.FULLTEXT_PUSH / 'logs/s2-pace'\nr = CODE_ROOT / 'fulltext-push' / 'raw' / 'l.jsonl'\n")
    (tmp_path / 'tools' / 'c.sh').write_text('cat "$CS_ATLAS_FULLTEXT_PUSH/logs/x.log"\nsh "$CS_ATLAS_FULLTEXT_PUSH/run_steps.sh"\n')
    got = sorted((f.name, n) for f, n, _ in R.scan_outside(tmp_path))
    assert got == [('a.py', 1), ('b.py', 1), ('b.py', 2), ('c.sh', 1)]


def test_repository_has_no_fulltext_push_data_joins_outside_it():
    """No exceptions: every join of FULLTEXT_PUSH onto a data directory outside fulltext-push/ goes through the slots."""
    code = Path(__file__).resolve().parents[1]
    left = {f.relative_to(code).as_posix() for f, _, _ in R.scan_outside(code)}
    assert not left, left
