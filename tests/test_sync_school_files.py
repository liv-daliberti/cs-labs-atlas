"""sync_school_files copies only what .gitignore admits, only when changed."""
import subprocess

import sync_school_files as T


def test_copies_admitted_files_only(tmp_path):
    main, wt = tmp_path / 'main', tmp_path / 'wt'
    for r in (main, wt):
        (r / 'hierarchy' / 'u' / 'reports').mkdir(parents=True); (r / 'hierarchy' / 'u' / 'raw').mkdir(); (r / 'hierarchy' / 'u' / 'tmp').mkdir()
    (wt / '.gitignore').write_text('*\n!*/\n!*.md\n!hierarchy/*/reviewed/x.json\n')
    subprocess.run(['git', '-C', str(wt), 'init', '-q'], check=True)
    (main / 'hierarchy' / 'u' / 'reports' / 'STAGE-0.md').write_text('report')
    (main / 'hierarchy' / 'u' / 'raw' / 'sweep.sqlite').write_text('data')
    (main / 'hierarchy' / 'u' / 'tmp' / 'note.md').write_text('scratch')
    assert T.sync('u', main, wt, dry=True) == ['hierarchy/u/reports/STAGE-0.md'] and not (wt / 'hierarchy/u/reports/STAGE-0.md').exists()
    assert T.sync('u', main, wt) == ['hierarchy/u/reports/STAGE-0.md'] and (wt / 'hierarchy/u/reports/STAGE-0.md').read_text() == 'report'
    assert T.sync('u', main, wt) == [] and not (wt / 'hierarchy/u/raw/sweep.sqlite').exists() and not (wt / 'hierarchy/u/tmp/note.md').exists()


def test_a_newer_worktree_file_is_kept(tmp_path):
    import os
    main, wt = tmp_path / 'main', tmp_path / 'wt'
    for r in (main, wt):
        (r / 'hierarchy' / 'u' / 'reports').mkdir(parents=True)
    (wt / '.gitignore').write_text('*\n!*/\n!*.md\n')
    subprocess.run(['git', '-C', str(wt), 'init', '-q'], check=True)
    a, b = main / 'hierarchy/u/reports/R.md', wt / 'hierarchy/u/reports/R.md'
    a.write_text('old'); b.write_text('new edit')
    os.utime(a, (1000, 1000))
    skipped = []
    assert T.sync('u', main, wt, skipped=skipped) == [] and b.read_text() == 'new edit' and skipped == ['hierarchy/u/reports/R.md']
    assert T.sync('u', main, wt, force=True) == ['hierarchy/u/reports/R.md'] and b.read_text() == 'old'
