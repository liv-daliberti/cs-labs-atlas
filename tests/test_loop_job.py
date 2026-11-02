"""loop_job.sh: a download loop restarts itself on USR1 (time limit near) but stays stopped on TERM (ROADMAP #18)."""
import os
import signal
import subprocess
import time
from pathlib import Path

CODE = Path(__file__).resolve().parents[1]


def make(tmp_path, atlas_out=''):
    code = tmp_path / 'code'
    (code / 'bin').mkdir(parents=True)
    calls = tmp_path / 'calls.txt'
    (code / 'bin' / 'atlas').write_text(f'#!/bin/bash\necho "$PWD :: $*" >> {calls}\nenv | grep -c "^SLURM_" >> {calls}\n{atlas_out}\necho "Submitted batch job 4242"\n')
    (code / 'bin' / 'atlas').chmod(0o755)
    child_log = tmp_path / 'child.txt'
    script = tmp_path / 'job.sh'
    script.write_text(f'''#!/bin/bash
export CS_ATLAS_CODE={code} RESTART_LOG={tmp_path}/restart.log SLURM_JOB_ID=7 SLURM_ARRAY_TASK_ID=3
. {CODE}/fulltext-push/loop_job.sh
run_restartable fulltext-push/downloads.slurm --array=3 -- bash -c 'trap "echo child-got-TERM >> {child_log}; exit 0" TERM; echo started >> {child_log}; while :; do sleep 0.2; done'
echo "exit=$?" >> {child_log}
''')
    return script, calls, child_log, tmp_path / 'restart.log'


def run_and_signal(script, child_log, sig):
    p = subprocess.Popen(['bash', str(script)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for _ in range(100):
        if child_log.exists() and 'started' in child_log.read_text():
            break
        time.sleep(0.1)
    os.kill(p.pid, sig)
    p.wait(timeout=30)
    return p


def test_usr1_stops_the_child_then_resubmits_with_a_clean_environment(tmp_path):
    script, calls, child_log, rlog = make(tmp_path)
    run_and_signal(script, child_log, signal.SIGUSR1)
    assert 'child-got-TERM' in child_log.read_text()
    lines = calls.read_text().splitlines()
    assert lines[0].endswith(':: submit --test-only fulltext-push/downloads.slurm --array=3')
    assert lines[2].endswith(':: submit fulltext-push/downloads.slurm --array=3')
    assert lines[0].startswith(str(tmp_path / 'code'))  # from the code root
    assert lines[1] == '0' and lines[3] == '0'  # no SLURM_* leaks into the new submission
    assert 'resubmitted: Submitted batch job 4242' in rlog.read_text()


def test_term_stops_for_good(tmp_path):
    script, calls, child_log, rlog = make(tmp_path)
    run_and_signal(script, child_log, signal.SIGTERM)
    assert 'child-got-TERM' in child_log.read_text()
    assert not calls.exists() and not rlog.exists()


def test_preempts_refuses_the_resubmit(tmp_path):
    script, calls, child_log, rlog = make(tmp_path, atlas_out='echo "Preempts: 1234"')
    run_and_signal(script, child_log, signal.SIGUSR1)
    assert 'resubmit refused: Preempts' in rlog.read_text()
    assert len(calls.read_text().splitlines()) == 2  # only the --test-only call
