#!/usr/bin/env python3
"""Prepare and verify a publication using ordinary Python, Node, Git and JSON.

No command in this program deploys a site or changes research evidence.
See docs/PUBLISHING.md for the research freeze and hosting adapter.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from release_inputs import verify_release

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'outputs/publishing'
RELEASE_ID = re.compile(r'\d{4}-\d{2}-\d{2}(?:\.\d+)?')
RECEIPTS = {'deployment/validation.json', 'deployment/upload-verification.json'}


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(path)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(2**20), b''):
            digest.update(block)
    return digest.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def lock():
    # One writer per checkout, including separate invocations by different tools.
    REPORTS.mkdir(parents=True, exist_ok=True)
    with (REPORTS / 'lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another publication command is running in this checkout') from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def source_fingerprint():
    result = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                            cwd=ROOT, check=True, capture_output=True)
    entries = {}
    for name in sorted(set(os.fsdecode(result.stdout).split('\0')) - {''} - RECEIPTS):
        path = ROOT / name
        if path.is_symlink():
            entries[name] = {'link': os.readlink(path)}
        else:
            entries[name] = sha(path) if path.is_file() else None
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


def build_fingerprint():
    directory = ROOT / 'dist'
    entries = {p.relative_to(directory).as_posix(): sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}
    require(entries, 'Production build is missing; run prepare')
    return hashlib.sha256(json.dumps(entries, sort_keys=True).encode()).hexdigest()


def selected_release(args):
    pin = read(ROOT / 'deployment/release.json')
    rid = args.release or pin['release']
    require(RELEASE_ID.fullmatch(rid), 'Use an exact release ID, never latest or a path')
    directory = args.releases_dir.resolve() / rid
    # An existing pin is an independent expected digest, not a newly trusted hash.
    expected = pin['manifestSha256'] if pin['release'] == rid else None
    manifest = verify_release(directory, expected, rid)
    require(manifest.get('evidence_check') is True, 'Research evidence gate did not pass')
    require(not manifest['code'].get('uncommitted_tracked_changes'), 'Release contains uncommitted research inputs')
    require(manifest.get('reader', {}).get('site_sync'), 'Release lacks a reader export with a site sync')
    return directory, manifest


def check_commands():
    return [
        ('contract-check', [sys.executable, 'scripts/validate-data.py']),
        ('hierarchy-check', [sys.executable, 'scripts/test-cs-hierarchy.py']),
        ('scope-check', [sys.executable, 'scripts/test-cs-scope.py']),
        ('pages-check', [sys.executable, 'scripts/test-site-pages.py']),
        ('reader-check', [sys.executable, 'scripts/test-reader-release.py']),
        ('pipeline-check', [sys.executable, 'scripts/test-release.py']),
        ('browser-model-check', ['node', '--test', 'scripts/test-cs-departments-page.mjs', 'scripts/test-paper-reader.mjs']),
        ('storage-check', ['node', '--test', 'scripts/test-atlas-storage.mjs', 'scripts/test-atlas-update-auth.mjs',
                           'scripts/test-princeton-release.mjs', 'scripts/test-chunked-transport.mjs']),
    ]


def execute(name, argv, env, state, directory):
    logfile = directory / (name + '.log')
    state['steps'][name] = {'status': 'running', 'argv': argv, 'log': str(logfile)}
    write(directory / 'state.json', state)
    with logfile.open('w') as log:
        result = subprocess.run(argv, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    state['steps'][name].update(status='passed' if result.returncode == 0 else 'failed', exitCode=result.returncode)
    write(directory / 'state.json', state)
    print(json.dumps({'step': name, 'exitCode': result.returncode, 'log': str(logfile)}), flush=True)
    require(result.returncode == 0, f'{name} failed; see {logfile}')


def verify_assets():
    plan = read(ROOT / 'atlas-storage/upload-plan.json')
    require(Path(plan['sourceDirectory']).resolve() == (ROOT / 'atlas').resolve(), 'Upload plan belongs to another checkout')
    require(sha(ROOT / plan['manifestFile']) == plan['manifestSha256'], 'Asset manifest changed')
    require(read(ROOT / 'lib/atlas-release.json')['manifestSha256'] == plan['manifestSha256'], 'Runtime asset pin differs')
    require(read(ROOT / plan['manifestFile'])['files'] == plan['files'], 'Upload plan differs from asset manifest')
    for name, entry in plan['files'].items():
        path = (ROOT / 'atlas' / name).resolve()
        require(not name.startswith('papers/'), 'Paper files must use the reader allowlist')
        require(path.is_relative_to((ROOT / 'atlas').resolve()), 'Asset path escapes atlas/')
        require(path.stat().st_size == entry['size'] and sha(path) == entry['sha256'], 'Asset changed: ' + name)
    return plan


def prepare(args):
    require(shutil.which('node') and shutil.which('npm'), 'Node and npm must be on PATH (see package.json engines)')
    require((ROOT / 'node_modules').is_dir(), 'Install dependencies with npm ci first')
    directory, manifest = selected_release(args)
    rid = manifest['release']
    out = REPORTS / rid
    out.mkdir(parents=True, exist_ok=True)
    state = dict(schema=1, release=rid, status='preparing', startedAt=now(), steps={},
                 researchManifestSha256=sha(directory / 'MANIFEST.json'), published=False,
                 browserVerification={'performed': False, 'reason': 'Separate browser review; automated DOM tests are not visual QA.'})
    write(out / 'state.json', state)
    write(ROOT / 'deployment/upload-verification.json', {'release': rid, 'allUploadsVerified': False})
    write(ROOT / 'deployment/validation.json', {'release': rid, 'status': 'preparing'})
    try:
        env = dict(os.environ, ATLAS_RELEASES_DIR=str(args.releases_dir.resolve()))
        pin = read(ROOT / 'deployment/release.json')
        pin.update(release=rid, manifestSha256=state['researchManifestSha256'], researchCommit=manifest['code']['commit'],
                   hierarchy=f'releases/{rid}/hierarchy')
        write(ROOT / 'deployment/release.json', pin)
        for name, argv in [
            ('hierarchy', [sys.executable, 'scripts/build-cs-hierarchy.py']),
            ('reader', [sys.executable, 'scripts/import-reader-release.py', str(directory), '--stores', str(args.stores.resolve())]),
            ('scope', [sys.executable, 'scripts/build-cs-scope.py']),
        ]:
            execute(name, argv, env, state, out)
        data = read(ROOT / 'atlas/data.json')
        for name in data['assets']:
            data['assets'][name] = sha(ROOT / 'atlas' / name)
        (ROOT / 'atlas/data.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
        execute('source-pack', ['node', 'scripts/source-atlas-assets.mjs', 'pack'], env, state, out)
        execute('storage-plan', ['node', 'scripts/prepare-atlas.mjs', 'atlas', 'r2'], env, state, out)
        for name, argv in check_commands():
            execute(name, argv, env, state, out)
        plan = verify_assets()
        shutil.copyfile(ROOT / plan['manifestFile'], ROOT / 'deployment/asset-manifest.json')
        execute('production-build', ['npm', 'run', 'build'], env, state, out)
        # Check again after the framework build/restoration, before certifying it.
        verify_assets()
        state.update(status='prepared', completedAt=now(), assetManifestSha256=plan['manifestSha256'],
                     sourceFingerprint=source_fingerprint(), buildFingerprint=build_fingerprint())
        write(ROOT / 'deployment/validation.json', state)
        write(out / 'state.json', state)
        print(json.dumps({'release': rid, 'status': state['status'], 'report': str(out / 'state.json')}))
    except (Exception, KeyboardInterrupt):
        state['status'] = 'failed'
        write(out / 'state.json', state)
        write(ROOT / 'deployment/validation.json', state)
        raise


def prepared(args):
    directory, manifest = selected_release(args)
    require(read(ROOT / 'deployment/release.json')['release'] == manifest['release'], 'Release differs from the site pin')
    state = read(REPORTS / manifest['release'] / 'state.json')
    require(state['status'] in ('prepared', 'uploaded'), 'Preparation has not completed')
    require(state['researchManifestSha256'] == sha(directory / 'MANIFEST.json'), 'Research release changed')
    require(state['sourceFingerprint'] == source_fingerprint(), 'Source changed after preparation; run prepare again')
    require(state['buildFingerprint'] == build_fingerprint(), 'Build changed after preparation; run prepare again')
    plan = verify_assets()
    require(state['assetManifestSha256'] == plan['manifestSha256'], 'Prepared asset manifest changed')
    return directory, state


def upload(args):
    directory, state = prepared(args)
    result = subprocess.run([sys.executable, 'scripts/upload-atlas.py', '--reader-release', str(directory),
                             '--stores', str(args.stores.resolve()), '--only-unverified', '--workers', str(args.workers)], cwd=ROOT)
    require(result.returncode == 0, 'Upload failed; rerun upload to resume verified objects')
    receipt = read(ROOT / 'atlas-storage/upload-verification.json')
    require(receipt.get('allUploadsVerified') is True and receipt['manifestSha256'] == state['assetManifestSha256'] and
            receipt.get('origin') == read(ROOT / 'deployment/release.json')['origin'].rstrip('/'),
            'Upload receipt does not match the prepared release')
    write(ROOT / 'deployment/upload-verification.json', receipt)
    state.update(status='uploaded', uploadedAt=now())
    write(REPORTS / state['release'] / 'state.json', state)
    print(json.dumps({'release': state['release'], 'status': 'uploaded', 'published': False}))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['plan', 'prepare', 'status', 'upload', 'ready', 'verify-live'])
    parser.add_argument('--release', help='Exact immutable release ID (default: deployment/release.json)')
    parser.add_argument('--releases-dir', type=Path, default=Path(os.environ.get('ATLAS_RELEASES_DIR', ROOT.parent / 'releases')))
    parser.add_argument('--stores', type=Path, default=ROOT.parent / 'stores')
    parser.add_argument('--workers', type=int, choices=range(1, 33), default=8)
    args = parser.parse_args(argv)
    try:
        if args.command == 'plan':
            directory, manifest = selected_release(args)
            print(json.dumps(dict(release=manifest['release'], researchCommit=manifest['code']['commit'],
                                  verifiedFiles=len(manifest['files']), counts=manifest['counts'],
                                  readerSync=manifest['reader']['site_sync'],
                                  stages=['hierarchy', 'reader', 'scope', 'source-pack', 'storage-plan'] +
                                         [name for name, _ in check_commands()] + ['production-build', 'upload', 'hosting-adapter', 'verify-live'],
                                  networkWrites=False), indent=2))
        elif args.command == 'status':
            rid = args.release or read(ROOT / 'deployment/release.json')['release']
            require(RELEASE_ID.fullmatch(rid), 'Use an exact release ID')
            path = REPORTS / rid / 'state.json'
            print(json.dumps(read(path) if path.exists() else {'release': rid, 'status': 'not-prepared'}, indent=2))
        else:
            with lock():
                if args.command == 'prepare':
                    prepare(args)
                elif args.command == 'upload':
                    upload(args)
                elif args.command == 'ready':
                    directory, state = prepared(args)
                    receipt = read(ROOT / 'deployment/upload-verification.json')
                    require(state['status'] == 'uploaded' and receipt.get('allUploadsVerified') is True and
                            receipt['manifestSha256'] == state['assetManifestSha256'] and
                            receipt.get('origin') == read(ROOT / 'deployment/release.json')['origin'].rstrip('/'),
                            'Verified upload to this origin is required before deployment')
                    print(json.dumps({'release': state['release'], 'ready': True, 'published': False,
                                      'project_id': read(ROOT / '.openai/hosting.json')['project_id'],
                                      'assetManifestSha256': state['assetManifestSha256']}))
                elif args.command == 'verify-live':
                    from verify_publication import verify
                    directory, manifest = selected_release(args)
                    require(manifest['release'] == read(ROOT / 'deployment/release.json')['release'], 'Release differs from the site pin')
                    verify(directory, args.stores.resolve(), REPORTS / manifest['release'] / 'live.json')
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(f'Publication stopped: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Publication interrupted; rerun the same command. Preparation restarts, uploads resume.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    sys.exit(main())
