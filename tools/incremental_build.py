"""Reuse an unchanged native school package, without granting any scientific gate."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path

import atlas_paths as P

CODE = Path(__file__).resolve().parents[1]
OUTPUTS = ('pis.json', 'students.json', 'lab_papers.jsonl.gz', 'student_papers.jsonl.gz', 'report.json', 'home-departments-school.json')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for part in iter(lambda: handle.read(2**20), b''):
            h.update(part)
    return h.hexdigest()


def inputs(school):
    from school_closeout import input_specs, fingerprint
    specs = input_specs(school)
    def key(name):
        path = Path(name)
        # Job code snapshots move between /tmp directories; their logical paths
        # and bytes, rather than the allocation directory, identify an input.
        if path.is_relative_to(P.SCHOOL_CONFIGS):
            return 'charter/' + path.relative_to(P.SCHOOL_CONFIGS).as_posix()
        if path.is_relative_to(CODE):
            return 'code/' + path.relative_to(CODE).as_posix()
        return str(path)
    result = {key(name): fingerprint(name, spec['content']) for name, spec in specs.items()}
    for path in (P.data('dblp-dump-persons.json.gz'), P.DBLP_DUMP / (P.DBLP_DUMP_FILE + '.md5')):
        result[str(path)] = fingerprint(path)
    # Include the whole tool dependency surface, including dynamically imported helpers.
    for base in (CODE / 'tools', CODE / 'schemas'):
        for path in sorted(base.rglob('*.py' if base.name == 'tools' else '*.json')):
            if '__pycache__' not in path.parts:
                result[key(path)] = digest(path)
    for name in ('paths.sh', 'docs/RULES.md', 'docs/evidence-whitelist.json'):
        path = CODE / name
        result[key(path)] = digest(path) if path.exists() else None
    return result


def output_hashes(directory):
    return {name: digest(directory / name) if (directory / name).is_file() else None for name in OUTPUTS}


def run_school(school, build, *, force=False, directory=None, input_state=None):
    directory = Path(directory) if directory else (Path(os.environ['PI_HIERARCHY_OUT']) / school
                  if os.environ.get('PI_HIERARCHY_OUT') else P.data('report.json', school).parent)
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / '.incremental-build.json'
    input_state = input_state or inputs
    with (directory / '.incremental-build.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        before = input_state(school)
        outputs = output_hashes(directory)
        try:
            previous = json.loads(receipt.read_text())
        except (OSError, ValueError):
            previous = {}
        if not force and previous.get('school') == school and previous.get('inputs') == before and \
                previous.get('outputs') == outputs and all(outputs[name] for name in OUTPUTS[:5]):
            return dict(school=school, action='reused', reason='inputs, code and package hashes unchanged')
        build(school)
        after = input_state(school)
        if before != after:
            receipt.unlink(missing_ok=True)
            raise RuntimeError(f'{school}: inputs changed during build; no reusable receipt written')
        outputs = output_hashes(directory)
        if not all(outputs[name] for name in OUTPUTS[:5]):
            raise RuntimeError(f'{school}: builder did not produce a complete package')
        temp = receipt.with_suffix('.tmp')
        temp.write_text(json.dumps(dict(schema=1, school=school, inputs=after, outputs=outputs), sort_keys=True) + '\n')
        temp.replace(receipt)
        return dict(school=school, action='built', reason='forced' if force else 'missing or changed inputs/package')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('schools', nargs='*', help='Defaults to the registered research schools')
    parser.add_argument('--force', action='store_true', help='Build even when the exact package can be reused')
    args = parser.parse_args(argv)
    from pihier.build import build
    for school in args.schools or P.SCHOOL_IDS:
        print(json.dumps(run_school(school, build, force=args.force)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
