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
