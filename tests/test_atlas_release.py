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
    rc = AR.main(['--tag', 't2', '--from', 'tree'], runner=r)
    assert rc == 3 and env == [] and r.calls == ['tree', 'export_release.py']     # stopped before the push, nothing published
    rc = AR.main(['--tag', 't2', '--from', 'tree', '--resume', '--yes-push', '--yes-hf'], runner=r)
    assert rc == 0 and env == [1] and r.calls.count('tree') == 1                    # tree and export were not run again; hf ran with its flag
    assert r.calls[-1].startswith('hf_upload')


def test_dry_run_lists_every_step_and_runs_nothing(env, capsys):
    r = Runner()
    assert AR.main(['--tag', 't3', '--dry-run'], runner=r) == 0 and r.calls == []
    out = capsys.readouterr().out
    assert out.index('rebuild') < out.index('validate') < out.index('regression') < out.index('reader') < out.index('release') < out.index('export-push') < out.index('hf-upload')
    assert 'EXTERNAL --yes-push' in out and 'EXTERNAL --yes-hf' in out


def test_handoff_note_text(tmp_path):
    d = tmp_path / 'rel'
    (d / 'reader').mkdir(parents=True)
    (d / 'MANIFEST.json').write_text(json.dumps(dict(created='2026-11-02T00:00:00Z', code=dict(commit='a' * 40), counts={'mit': dict(pis=1, lab_papers=2, students=3, student_paper_links=4)})))
    (d / 'reader' / 'SUMMARY.json').write_text(json.dumps(dict(totals=dict(readable=5, lab_papers=9, host=2, link=3, not_readable=4), currently_hosted_not_permitted=7, link_check_request_urls=11)))
    t = AR.render_handoff('2026-11-02', d)
    assert '| mit | 1 | 2 | 3 | 4 |' in t and '5 of 9 lab papers are readable' in t and 'release-2026-11-02' in t
