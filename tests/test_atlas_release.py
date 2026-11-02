"""tools/atlas_release.py (ROADMAP #37): the order, stop at the first failure, resume, and the confirmation for external steps."""
import json

import pytest

import atlas_release as AR


class Runner:
    def __init__(self, fail=None):
        self.calls, self.fail = [], fail

    def __call__(self, argv, env=None, stdout=None, stderr=None, cwd=None):
        stage = (env or {}).get('STAGES') or argv[1].rsplit('/', 1)[-1]
        self.calls.append(stage)
        class R:
            returncode = 1 if stage == self.fail else 0
        return R()


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(AR.P, 'SCRATCH', tmp_path / 'scratch')
    monkeypatch.setattr(AR, 'preflight', lambda c: (True, 'clean'))
    monkeypatch.setattr(AR, 'check_notes', lambda c: (True, 'notes ok'))
    monkeypatch.setattr(AR, 'handoff', lambda c: (True, 'note added'))
    pushed = []
    monkeypatch.setattr(AR, 'push_export', lambda c: pushed.append(1) or (True, 'pushed'))
    monkeypatch.setattr('sys.stdin', type('S', (), {'isatty': staticmethod(lambda: False)})())
    return pushed


def test_order_matches_the_roadmap():
    assert AR.ORDER == ['preflight', 'rebuild', 'validate', 'regression', 'reader', 'release', 'notes', 'tree', 'export', 'export-push', 'hf-upload', 'handoff']


def test_stops_at_the_first_failure(env):
    r = Runner(fail='validate')
    rc = AR.main(['--tag', 't1', '--from', 'rebuild', '--only', 'rebuild,validate,regression,reader', '--yes-push', '--yes-hf'], runner=r)
    assert rc == 1 and len(r.calls) == 2 and r.calls[1] == 'validate'          # regression and reader never ran
    st = json.loads((AR.P.SCRATCH / 't1' / 'run.json').read_text())
    assert st['rebuild']['ok'] and not st['validate']['ok'] and 'regression' not in st


def test_external_steps_need_the_flag_and_resume_skips_passed_steps(env):
    r = Runner()
    rc = AR.main(['--tag', 't2', '--from', 'tree', '--release-id', '2026-11-02'], runner=r)
    assert rc == 3 and env == [] and r.calls == ['organize_tree.py', 'export_release.py']
    rc = AR.main(['--tag', 't2', '--from', 'tree', '--resume', '--yes-push', '--yes-hf'], runner=r)
    assert rc == 0 and env == [1] and r.calls.count('organize_tree.py') == 1
    assert r.calls[-1].startswith('hf_upload')


def test_dry_run_lists_every_step_and_runs_nothing(env, capsys):
    r = Runner()
    assert AR.main(['--tag', 't3', '--dry-run'], runner=r) == 0 and r.calls == []
    out = capsys.readouterr().out
    order = [ln.split()[0] for ln in out.splitlines() if ln.strip()]
    assert order == AR.ORDER
    assert 'EXTERNAL --yes-push' in out and 'EXTERNAL --yes-hf' in out


def test_handoff_note_text_has_host_link_and_take_down(tmp_path):
    d = tmp_path / 'rel'
    (d / 'reader').mkdir(parents=True)
    (d / 'MANIFEST.json').write_text(json.dumps(dict(created='2026-11-02T00:00:00Z', code=dict(commit='a' * 40), counts={'mit': dict(pis=1, lab_papers=2, students=3, student_paper_links=4)})))
    summ = dict(totals=dict(readable=5, lab_papers=9, host=2, link=3, not_readable=4), currently_hosted_not_permitted=7, link_check_request_urls=11,
                site_sync=dict(site_files=20, keep=10, unpublish=10, unpublish_by_reason={'not_in_stores': 6, 'license': 4}, upload=3))
    (d / 'reader' / 'SUMMARY.json').write_text(json.dumps(summ))
    t = AR.render_handoff('2026-11-02', d)
    assert '| mit | 1 | 2 | 3 | 4 |' in t and '## Host' in t and '## Link' in t and '## Take down (required)' in t
    assert t.index('## Host') < t.index('## Link') < t.index('## Take down')
    assert 'Remove 10 files' in t and 'not_in_stores: 6, license: 4' in t and 'reader/unpublish.tsv' in t and 'without touching our stores' in t
    assert 'Handoff for Codex' not in t and 'goes UP' not in t
    assert 'GitHub export: not performed' in t and 'Hugging Face upload: not performed' in t
    assert 'scripts/release.py prepare --release 2026-11-02' in t
    (d / 'reader' / 'SUMMARY.json').write_text(json.dumps(dict(summ, site_sync=None)))
    try:
        AR.render_handoff('2026-11-02', d)
        raise AssertionError('the note must fail without a site sync')
    except ValueError:
        pass


def test_site_target_has_no_external_steps(env, capsys):
    runner = Runner()
    assert AR.main(['--target', 'site', '--dry-run'], runner=runner) == 0
    assert [line.split()[0] for line in capsys.readouterr().out.splitlines()] == AR.SITE_ORDER
    assert runner.calls == []


def test_unknown_step_and_implicit_resume_rejected(env):
    for args in (['--only', 'typo'], ['--only', ''], ['--tag', '../outside'], ['--resume'], ['--release-id', 'latest'], ['--from', 'notes'],
                 ['--target', 'site', '--only', 'hf-upload']):
        with pytest.raises(SystemExit) as error:
            AR.main(args, runner=Runner())
        assert error.value.code == 2


def test_resume_binds_release_and_source_options(env):
    runner = Runner()
    assert AR.main(['--tag', 'bound', '--from', 'tree', '--release-id', '2026-11-02'], runner=runner) == 3
    for extra in (['--release-id', '2026-11-03'], ['--schools', 'mit'], ['--target', 'site']):
        with pytest.raises(SystemExit):
            AR.main(['--tag', 'bound', '--resume', *extra], runner=runner)
    with pytest.raises(SystemExit):
        AR.main(['--tag', 'bound', '--from', 'tree', '--release-id', '2026-11-02'], runner=runner)


def test_freeze_receipt_retained_across_restart(env, monkeypatch, tmp_path):
    from argparse import Namespace
    context = AR.Ctx(Namespace(tag='receipt', schools=None, allow_swings=False, export_dir=None, release_id=None))
    context.dir.mkdir(parents=True)
    def freeze(argv, **kwargs):
        kwargs['stdout'].write(json.dumps({'release': '2026-11-02', 'dir': str(tmp_path / 'release')}) + '\n')
        return type('Result', (), {'returncode': 0})()
    assert AR.run_step('release', context, freeze)[0]
    assert context.release_id == '2026-11-02'
    for step in ('tree', 'export', 'hf-upload'):
        argv, _ = AR.cmd_for(step, context)
        assert '2026-11-02' in argv and 'latest' not in argv
    assert not AR.run_step('release', context, Runner())[0]


def test_resume_rechecks_preflight(env, monkeypatch):
    assert AR.main(['--tag', 'dirty-resume', '--only', 'preflight'], runner=Runner()) == 0
    monkeypatch.setattr(AR, 'preflight', lambda c: (False, 'uncommitted tracked changes'))
    with pytest.raises(SystemExit) as error:
        AR.main(['--tag', 'dirty-resume', '--only', 'preflight', '--resume'], runner=Runner())
    assert error.value.code == 2
