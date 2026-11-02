"""The exact immutable research release used by the site builder and its checks."""
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = json.loads((ROOT / 'deployment/release.json').read_text())
RELEASE = PIN['release']
if not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:\.\d+)?', RELEASE):
    raise ValueError('Invalid pinned research release')
DIRECTORY = Path(os.environ.get('ATLAS_RELEASES_DIR', ROOT.parent / 'releases')) / RELEASE
HIERARCHY = DIRECTORY / 'hierarchy'


def verify_release(directory, expected_sha=None, expected_id=None):
    directory = Path(directory).resolve()
    raw = (directory / 'MANIFEST.json').read_bytes()
    if expected_sha and hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError('Pinned research manifest checksum mismatch')
    manifest = json.loads(raw)
    if expected_id and manifest['release'] != expected_id:
        raise ValueError('Research release identity mismatch')
    if not manifest.get('files'):
        raise ValueError('Research manifest has no files')
    for name, entry in manifest['files'].items():
        path = (directory / name).resolve()
        if Path(name).is_absolute() or not path.is_relative_to(directory):
            raise ValueError('Release path escapes its directory')
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(2**20), b''):
                digest.update(chunk)
        if path.stat().st_size != entry['bytes'] or digest.hexdigest() != entry['sha256']:
            raise ValueError('Research release checksum mismatch: ' + name)
    return manifest


def verify():
    manifest = verify_release(DIRECTORY, PIN['manifestSha256'], RELEASE)
    print(json.dumps(dict(release=RELEASE, verifiedFiles=len(manifest['files']))))


if __name__ == '__main__':
    verify()
