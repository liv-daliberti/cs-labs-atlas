"""tools/relocate_schools.py on a fake tree in tmp_path: the plan, its refusals, the root tidy-up and the apply (nothing outside tmp_path is touched)."""
import os

import relocate_schools as S


def tree(tmp_path):
    root = tmp_path / 'hs'
    code = root / 'code'
    for d in ['hierarchy/mit/derived', 'hierarchy/mit/raw', 'hierarchy/mit/reports', 'hierarchy/mit/reviewed', 'hierarchy/mit/work', 'hierarchy/mit/tmp',
              'hierarchy/cmu/derived', 'hierarchy/cmu/reviewed', 'hierarchy/derived/reader', 'hierarchy/reviewed',
              'listings/mit/raw', 'captures', 'census', 'periods', 'fulltext-push/checks', 'ai-writing/data/embeddings/bge_m3/mit',
              'stores/mit/objects', 'stores/cmu', 'schools', 'site', 'x', 'site-host-update-1115', 'hierarchy-root-placeholder']:
        base = root if d.startswith(('stores', 'schools', 'site', 'x')) else code
        (base / d).mkdir(parents=True)
    (code / 'hierarchy/mit/derived/pis.json').write_text('[]')
    (code / 'hierarchy/mit/derived/report.md').write_text('tracked report')
    (code / 'hierarchy/mit/reports/STAGE-1.md').write_text('tracked')
    (code / 'hierarchy/mit/reports/scratch.json').write_text('{}')
    (code / 'hierarchy/mit/STRAY.txt').write_text('x')
    (code / 'hierarchy/mit/inputs-manifest.sha256.json').write_text('{}')
    (code / 'hierarchy/derived/reader/mit.jsonl.gz').write_text('x')
    (code / 'hierarchy/reviewed/listings-input-mit.json').write_text('{}')
    (code / 'captures/mit.sqlite').write_text('')
    (code / 'hierarchy/mit/raw/school-captures.sqlite').write_text('data')
    (code / 'captures/cmu.sqlite').write_text('real captures')
    (code / 'fulltext-push/checks/mit.sqlite').write_text('db')
    (root / 'slurm-1.out').write_text('x')
    (root / 'slurm-2.out').write_text('x')
    for n in S.SITE_LOOSE[:1]:
        (root / n).mkdir()
    (root / 'site-worktrees').mkdir()
    (root / 'hierarchy/logs').mkdir(parents=True)
    (root / 'hierarchy/logs/rebuild-1.out').write_text('x')
    (code / 'schools').mkdir()
    for s in ('mit', 'cmu', 'TEMPLATE'):
        (code / 'schools' / f'{s}.toml').write_text('status = "released"\n')
    cfg = dict(ROOT=root, CODE=code, SCHOOLS_TREE=root / 'schools', STORES=root / 'stores', LISTINGS=code / 'listings', CAPTURES=code / 'captures',
               CENSUS=code / 'census', PERIODS=code / 'periods', FT_CHECKS=code / 'fulltext-push/checks', EMBEDDINGS=code / 'ai-writing/data/embeddings',
               HIERARCHY=code / 'hierarchy', SLURM_LOGS=root / 'logs/slurm', MIGRATIONS=root / 'archive/migrations')
    tracked = {'hierarchy/mit/derived/report.md', 'hierarchy/mit/reports/STAGE-1.md', 'hierarchy/mit/reviewed/x.json', 'hierarchy/reviewed/listings-input-mit.json'}
    return cfg, tracked


def by(entries, **kw):
    return [e for e in entries if all(e.get(k) == v for k, v in kw.items())]


def test_school_keys_skip_the_template(tmp_path):
    cfg, _ = tree(tmp_path)
    assert S.school_keys(cfg['CODE'] / 'schools') == ['cmu', 'mit']


def test_plan_maps_each_location_to_the_school_directory(tmp_path):
    cfg, tracked = tree(tmp_path)
    cfg, schools, entries = S.build(cfg, ['mit', 'cmu'], tracked=tracked)
    T = cfg['SCHOOLS_TREE'] / 'mit'
    new = {e['old']: e['new'] for e in entries if e['kind'] in ('rename', 'git-mv')}
    H = cfg['HIERARCHY'] / 'mit'
    assert new[str(H / 'raw')] == str(T / 'raw')
    assert new[str(H / 'work')] == str(T / 'work') and new[str(H / 'tmp')] == str(T / 'tmp')
    assert new[str(cfg['LISTINGS'] / 'mit')] == str(T / 'listings')
    assert new[str(cfg['STORES'] / 'mit')] == str(T / 'store')
    assert new[str(cfg['FT_CHECKS'] / 'mit.sqlite')] == str(T / 'checks' / 'mit.sqlite')
    assert new[str(cfg['EMBEDDINGS'] / 'bge_m3' / 'mit')] == str(T / 'ai' / 'embeddings' / 'bge_m3')
    assert new[str(cfg['HIERARCHY'] / 'derived/reader/mit.jsonl.gz')] == str(T / 'derived' / 'reader.jsonl.gz')
    assert new[str(H / 'inputs-manifest.sha256.json')] == str(T / 'derived' / 'inputs-manifest.sha256.json')
    assert new[str(cfg['CAPTURES'] / 'cmu.sqlite')] == str(cfg['SCHOOLS_TREE'] / 'cmu' / 'raw' / 'school-captures.sqlite')
    gm = by(entries, kind='git-mv')
    assert [e['new'] for e in gm] == [str(H / 'reviewed' / 'listings-input.json')]


def test_tracked_files_stay_and_their_directory_is_moved_child_by_child(tmp_path):
    cfg, tracked = tree(tmp_path)
    cfg, schools, entries = S.build(cfg, ['mit'], tracked=tracked)
    H, T = cfg['HIERARCHY'] / 'mit', cfg['SCHOOLS_TREE'] / 'mit'
    olds = {e['old'] for e in by(entries, kind='rename')}
    assert str(H / 'derived') not in olds and str(H / 'derived' / 'pis.json') in olds
    assert str(H / 'derived' / 'report.md') not in olds
    assert str(H / 'reports' / 'scratch.json') in olds and str(H / 'reports' / 'STAGE-1.md') not in olds
    assert {e['old'] for e in by(entries, kind='stay-tracked')} == {str(cfg['CODE'] / 'hierarchy/mit/derived/report.md'), str(cfg['CODE'] / 'hierarchy/mit/reports/STAGE-1.md')}
    assert [e['old'] for e in by(entries, kind='leftover')] == [str(H / 'STRAY.txt')]
    assert by(entries, kind='link') == [dict(kind='link', old=str(T / 'reviewed'), new=str(H / 'reviewed'), group='reviewed', school='mit',
                                            note=by(entries, kind='link')[0]['note'])]


def test_zero_byte_prelayout_capture_is_a_removal_not_a_move(tmp_path):
    cfg, tracked = tree(tmp_path)
    cfg, schools, entries = S.build(cfg, ['mit'], tracked=tracked)
    assert [e['old'] for e in by(entries, kind='remove-approval', school='mit')] == [str(cfg['CAPTURES'] / 'mit.sqlite')]
    assert not S.check_plan(by(entries, school='mit', kind='remove-approval'))
    (cfg['CAPTURES'] / 'mit.sqlite').write_text('not empty')
    _, _, entries = S.build(cfg, ['mit'], tracked=tracked)
    assert any('two non-empty copies' in c for c in S.check_plan(entries))


def test_conflicts_destination_exists(tmp_path):
    cfg, tracked = tree(tmp_path)
    (cfg['SCHOOLS_TREE'] / 'mit' / 'raw').mkdir(parents=True)
    cfg, schools, entries = S.build(cfg, ['mit'], tracked=tracked)
    assert any('destination exists' in c for c in S.check_plan(entries))


def test_root_tidy_up_lists_removals_and_moves(tmp_path):
    cfg, tracked = tree(tmp_path)
    cfg, schools, entries = S.build(cfg, ['mit'], tracked=tracked)
    root = cfg['ROOT']
    logs = {e['old']: e['new'] for e in by(entries, group='slurm-logs')}
    assert logs[str(root / 'slurm-1.out')] == str(cfg['SLURM_LOGS'] / 'slurm-1.out')
    assert str(root / 'hierarchy/logs/rebuild-1.out') in logs
    wt = by(entries, kind='git-worktree-move')
    assert [(e['old'], e['new']) for e in wt] == [(str(root / 'site-interim-1120'), str(root / 'site-worktrees' / 'site-interim-1120'))]
    rem = {e['old'] for e in by(entries, kind='remove-approval') if e['school'] is None}
    assert {str(root / 'x'), str(root / 'site-host-update-1115'), str(root / 'hierarchy')} <= rem


def test_order_makes_directories_before_moves_and_dirs_before_files_into_them(tmp_path):
    cfg, tracked = tree(tmp_path)
    cfg, schools, entries = S.build(cfg, ['cmu', 'mit'], tracked=tracked)
    ordered = S.order(entries)
    kinds = [e['kind'] for e in ordered]
    assert kinds.index('rename') > max(i for i, k in enumerate(kinds) if k == 'mkdir')
    seen = set()
    for e in ordered:
        if e['kind'] == 'mkdir':
            seen.add(e['new'])
        elif e['kind'] == 'rename':
            parent = os.path.dirname(e['new'])
            assert parent in seen or os.path.isdir(parent), e
            seen.add(e['new'])


def test_apply_moves_links_and_records(tmp_path):
    cfg, tracked = tree(tmp_path)
    cfg, schools, entries = S.build(cfg, ['mit'], tracked=tracked)
    entries = [e for e in entries if e['kind'] != 'git-mv' and e['kind'] != 'git-worktree-move']
    S.apply_plan(entries, cfg, tmp_path / 'rec.jsonl', compat=True)
    T = cfg['SCHOOLS_TREE'] / 'mit'
    assert (T / 'derived' / 'pis.json').exists() and (T / 'raw' / 'school-captures.sqlite').read_text() == 'data'
    assert (T / 'reports' / 'scratch.json').exists() and (cfg['HIERARCHY'] / 'mit' / 'reports' / 'STAGE-1.md').exists()
    assert os.path.islink(T / 'reviewed') and os.readlink(T / 'reviewed') == str(cfg['HIERARCHY'] / 'mit' / 'reviewed')
    assert os.path.islink(cfg['HIERARCHY'] / 'mit' / 'raw')                  # temporary compat link at the old path
    assert (T / 'store' / 'objects').is_dir() and (T / 'checks' / 'mit.sqlite').exists() and (T / 'ai' / 'embeddings' / 'bge_m3').is_dir()
    assert (cfg['SLURM_LOGS'] / 'slurm-1.out').exists()
    assert (tmp_path / 'rec.jsonl').read_text().count('permanent-link') == 1
