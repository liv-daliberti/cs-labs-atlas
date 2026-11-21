"""school-collector.slurm keeps the downloads.slurm pre-step (2026-11-21): ledger_found + reader_link become candidates and the
priority file orders the loop. When the loops moved to school-collector.slurm the step was dropped, and 7.7k ledger-found open
copies in 22 schools never became candidates."""
import re
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'fulltext-push' / 'school-collector.slurm'


def text():
    return SCRIPT.read_text()


def test_syntax():
    subprocess.run(['bash', '-n', str(SCRIPT)], check=True)


def test_ledger_found_and_reader_link_run_under_the_shared_lock():
    t = text()
    assert re.search(r'channel_runner\.py "\$SCHOOL" ledger_found reader_link', t)
    assert 'run_steps-ledger_found.lock' in t          # one school at a time, the lock downloads.slurm uses
    assert 'EXTRA_PIDS+=($!)' in t                     # stopped with the loop at a restart


def test_stamp_skips_an_unchanged_ledger():
    t = text()
    assert 'unavailable.jsonl.gz' in t and 'reader/$SCHOOL.jsonl.gz' in t
    assert '"$LF_SIG" != "$(cat "$LF_STAMP"' in t
    assert re.search(r'&& printf .%s\\n. "\$LF_SIG" > "\$LF_STAMP"', t)   # written only after a clean run


def test_loop_gets_the_priority_file():
    t = text()
    assert 'priority_file.py "$SCHOOL"' in t
    assert 'latest/hierarchy/$SCHOOL/unavailable.jsonl.gz' in t   # unreleased schools skip it
    loop = next(l for l in t.splitlines() if 'lab_first_loop.py "$SCHOOL"' in l)
    assert '"${PRIORITY_ARGS[@]}"' in loop
