"""tools/job_code_snapshot.sh: a job runs the code of one commit, whatever happens to the main checkout while it runs."""
import os
import subprocess
from pathlib import Path

HELPER = Path(__file__).resolve().parents[1] / 'tools' / 'job_code_snapshot.sh'


def git(repo, *a):
    return subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@example.org', *a], capture_output=True, text=True, check=True).stdout.strip()


def repo_with_code(tmp_path):
    r = tmp_path / 'code'
    (r / 'tools').mkdir(parents=True)
    (r / 'tools' / 'x.py').write_text('print("v1")\n')
    (r / 'schools').mkdir()
    git(r, 'init', '-q')
    git(r, 'add', '-A')
    git(r, 'commit', '-qm', 'v1')
    return r


def run(r, script, env_extra=None):
    env = dict(os.environ, CS_ATLAS_CODE=str(r), TMPDIR=str(r.parent), SLURM_JOB_ID='42')
    env.pop('CS_ATLAS_SNAPSHOT_COMMIT', None)
    env.update(env_extra or {})
    return subprocess.run(['bash', '-c', f'. {HELPER} || exit 9\n{script}'], capture_output=True, text=True, env=env)


def test_snapshot_pins_the_commit_while_the_checkout_is_rewritten(tmp_path):
    r = repo_with_code(tmp_path)
    v1 = git(r, 'rev-parse', 'HEAD')
    # the job starts at v1; then a "landing" rewrites the live file, deletes another and moves HEAD
    script = f'''
cat "$CS_ATLAS_TOOLS/x.py"
echo 'print("v2")' > {r}/tools/x.py; rm -rf {r}/schools
git -C {r} -c user.name=t -c user.email=t@example.org commit -qam v2
cat "$CS_ATLAS_TOOLS/x.py"; echo "commit=$CS_ATLAS_SNAPSHOT_COMMIT"; echo "code=$CS_ATLAS_CODE tools=$CS_ATLAS_TOOLS"
'''
    p = run(r, script)
    assert p.returncode == 0, p.stderr
    out = p.stdout.splitlines()
    assert out[0].startswith('code snapshot: commit ' + v1) and '(job-start)' in out[0]
    assert out[1] == 'print("v1")' and out[2] == 'print("v1")'              # unchanged by the landing
    assert f'commit={v1}' in out and f'code={r} tools={tmp_path}/atlas-code-{os.environ.get("USER", "u")}-42/tools' in out
    assert (r / 'tools' / 'x.py').read_text() == 'print("v2")\n'                     # the live checkout did move
    assert not (tmp_path / f'atlas-code-{os.environ.get("USER", "u")}-42').exists()  # removed by the EXIT trap


def test_submit_time_commit_wins_over_head_and_bad_commit_fails(tmp_path):
    r = repo_with_code(tmp_path)
    v1 = git(r, 'rev-parse', 'HEAD')
    (r / 'tools' / 'x.py').write_text('print("v2")\n')
    git(r, 'commit', '-qam', 'v2')
    p = run(r, 'cat "$CS_ATLAS_TOOLS/x.py"', {'CS_ATLAS_SNAPSHOT_COMMIT': v1})
    assert p.stdout.splitlines()[0].endswith('data stays at ' + str(r)) and '(submit)' in p.stdout and p.stdout.splitlines()[1] == 'print("v1")'
    bad = run(r, 'echo not-reached', {'CS_ATLAS_SNAPSHOT_COMMIT': '0' * 40})
    assert bad.returncode == 9 and 'no such commit' in bad.stderr and 'not-reached' not in bad.stdout


def test_atlas_paths_follow_the_snapshot_and_provenance_records_it(tmp_path, monkeypatch):
    import atlas_paths
    import provenance
    env = {'CS_ATLAS_CODE': str(tmp_path / 'code'), 'CS_ATLAS_TOOLS': str(tmp_path / 'snap' / 'tools')}
    p = atlas_paths._resolve(env)
    assert p['TOOLS'] == tmp_path / 'snap' / 'tools' and p['CODE'] == tmp_path / 'code' and p['HIERARCHY'] == tmp_path / 'code' / 'hierarchy'
    monkeypatch.setenv('CS_ATLAS_SNAPSHOT_COMMIT', 'a' * 40)
    st = provenance.code_state()
    assert st['commit'] == 'a' * 40 and st['snapshot'] is True


def test_a_full_tmp_falls_back_to_dev_shm(tmp_path):
    r = repo_with_code(tmp_path)
    out = run(r, 'echo "$CS_ATLAS_SNAPSHOT"', {'SNAPSHOT_MIN_KB': '999999999999'})
    assert out.returncode == 0 and out.stdout.splitlines()[-1].startswith('/dev/shm/atlas-code-') and 'fallback' in out.stderr
    assert run(r, 'echo "$CS_ATLAS_SNAPSHOT"').stdout.splitlines()[-1].startswith(str(tmp_path))


def test_provenance_checks_the_snapshot_source_not_data_overlay_links(tmp_path, monkeypatch):
    import provenance
    source = repo_with_code(tmp_path)
    (source / 'tools' / 'pi_hierarchy.py').write_text('print("builder")\n')
    git(source, 'add', 'tools/pi_hierarchy.py')
    git(source, 'commit', '-qm', 'builder')
    commit = git(source, 'rev-parse', 'HEAD')
    overlay = tmp_path / 'private-data-overlay'
    overlay.mkdir()
    (overlay / '.git').symlink_to(source / '.git', target_is_directory=True)
    (overlay / 'tools').symlink_to(source / 'tools', target_is_directory=True)
    monkeypatch.setattr(provenance.P, 'WORK', overlay)
    monkeypatch.setenv('CS_ATLAS_SNAPSHOT_COMMIT', commit)
    monkeypatch.setenv('SNAPSHOT_REPO', str(source))
    state = provenance.code_state()
    assert state['commit'] == commit and state['snapshot'] is True
    assert not state['dirty'] and state['dirty_paths'] == []
    # A real uncommitted source edit is still a failure, with a bound diff.
    (source / 'tools' / 'pi_hierarchy.py').write_text('print("uncommitted")\n')
    state = provenance.code_state()
    assert state['dirty'] and 'tools/pi_hierarchy.py' in state['dirty_paths']
    assert len(state['diff_sha256']) == 64
