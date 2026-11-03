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
