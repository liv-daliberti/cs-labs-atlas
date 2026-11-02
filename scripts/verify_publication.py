"""Read-only production checks, usable by a person, CI, or any assistant."""
import csv
import hashlib
import json
from pathlib import Path

import requests

from publication_io import credentials, headers, origin
from release import ROOT, now, read, require, verify_assets, write


def verify(release, stores, output):
    pin = read(ROOT / 'deployment/release.json')
    base = origin(pin['origin'])
    plan = verify_assets()
    session = requests.Session()
    session.headers.update(headers(credentials()))
    checks = []
    report = {'release': pin['release'], 'url': base, 'passed': False, 'checks': checks, 'checkedAt': now()}
    # Overwrite any older success before making requests.
    write(output, report)

    def request(method, path, **kwargs):
        try:
            return session.request(method, base + '/' + path, timeout=90, allow_redirects=False, **kwargs)
        except requests.RequestException:
            raise ValueError('Live verification request failed; no credentials logged') from None

    def passed(name):
        checks.append({'check': name, 'passed': True})

    try:
        for name in ('data/cs-hierarchy/index.json', 'data/reader-objects.json'):
            response = request('GET', name)
            require(response.status_code == 200, f'{name}: HTTP {response.status_code}')
            require(hashlib.sha256(response.content).hexdigest() == plan['files'][name]['sha256'], 'Live bytes differ: ' + name)
            passed(name + ' matches prepared bytes')
        compact = response.json()
        require(compact['release'] == pin['release'], 'Live release identity differs')
        with (release / 'reader/hosted-files.tsv').open() as handle:
            rows = list(csv.DictReader(handle, delimiter='\t'))
        require(set(compact['files']) == {row['sha256'] for row in rows}, 'Live allowlist differs from frozen release')
        passed('exact frozen hosted-file allowlist')

        def check_range(row, start, end):
            extension = Path(row['path']).suffix
            response = request('GET', 'papers/' + row['sha256'] + extension, headers={'Range': f'bytes={start}-{end}'})
            require(response.status_code == 206, f'Paper range: HTTP {response.status_code}')
            source = (stores / row['school'] / row['path']).resolve()
            require(source.is_relative_to(stores.resolve()), 'Store path escapes its directory')
            with source.open('rb') as handle:
                handle.seek(start)
                require(response.content == handle.read(end - start + 1), 'Live paper range differs from stored bytes')

        pdf = next((row for row in rows if row['path'].endswith('.pdf')), None)
        if pdf:
            check_range(pdf, 0, min(15, int(pdf['bytes']) - 1))
            passed('hosted PDF range bytes')
        xml = next((row for row in rows if row['path'].endswith('.xml')), None)
        if xml:
            response = request('HEAD', 'papers/' + xml['sha256'] + '.xml')
            require(response.status_code == 200 and response.headers.get('Content-Type', '').startswith('application/xml') and
                    'attachment' in response.headers.get('Content-Disposition', ''), 'XML response headers differ')
            passed('hosted XML admission and download headers')
        for digest, chunks in compact.get('chunks', {}).items():
            row = next(row for row in rows if row['sha256'] == digest)
            boundary = chunks[1]['offset']
            check_range(row, boundary - 4, boundary + 4)
            passed('range across storage chunks: ' + digest)
        with (release / 'reader/unpublish.tsv').open() as handle:
            old = next(csv.DictReader(handle, delimiter='\t'), None)
        if old:
            require(old['sha256'] not in compact['files'], 'Withdrawn paper remains admitted')
            extension = Path(old['path']).suffix or '.pdf'
            require(request('HEAD', 'papers/' + old['sha256'] + extension).status_code == 404, 'Withdrawn paper remains accessible')
            passed('withdrawn paper is no longer served')
        require(request('HEAD', 'api/atlas-storage/' + '0' * 64).status_code in (401, 403), 'Maintenance API accepted missing update token')
        passed('maintenance API rejects missing update credentials')
        report['passed'] = True
    finally:
        write(output, report)
        session.close()
    print(json.dumps(report))
