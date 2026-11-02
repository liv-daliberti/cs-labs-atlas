#!/usr/bin/env python3
"""Project a verified frozen release's reader decisions into the site's indexes.

Usage: python scripts/import-reader-release.py RELEASE_DIRECTORY
No downloads or network writes. The release is the complete hosted-file allowlist.
"""
import argparse
import collections
import csv
import gzip
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def verified(release, manifest, name):
    entry = manifest['files'][name]
    data = (release / name).read_bytes()
    if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
        raise ValueError('Release checksum mismatch: ' + name)
    return data


def source_url(row):
    url = row.get('source_url') or ''
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password:
        raise ValueError('Readable row lacks a valid source URL: ' + row['key'])
    return url


def project(release, stores=None):
    manifest = json.loads((release / 'MANIFEST.json').read_text())
    summary = json.loads(verified(release, manifest, 'reader/SUMMARY.json'))
    if not summary.get('site_sync'):
        raise ValueError('Release reader export lacks its site sync')
    hosted = list(csv.DictReader(verified(release, manifest, 'reader/hosted-files.tsv').decode().splitlines(), delimiter='\t'))
    files = {}
    for row in hosted:
        sha, size = row['sha256'], int(row['bytes'])
        ext = Path(row['path']).suffix.removeprefix('.')
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha) or ext not in ('pdf', 'xml'):
            raise ValueError('Unsupported hosted file: ' + row['path'])
        if not 5 <= size <= 512 * 2**20:
            raise ValueError('Hosted object exceeds the server limit: ' + sha)
        files[sha] = dict(path=f'papers/{sha}.{ext}', sha256=sha, bytes=size, format=ext)
        if size > 96 * 2**20:
            # The upload endpoint accepts 96 MiB; preserve the original paper
            # bytes through independently verified, bounded storage chunks.
            store_root = (stores or ROOT.parent / 'stores').resolve()
            source = (store_root / row['school'] / row['path']).resolve()
            if not source.is_relative_to(store_root):
                raise ValueError('Hosted file escapes the stores directory')
            chunk_dir = ROOT / 'atlas-storage/chunks'
            chunk_dir.mkdir(parents=True, exist_ok=True)
            chunks, offset, full = [], 0, hashlib.sha256()
            with source.open('rb') as handle:
                for part in iter(lambda: handle.read(32 * 2**20), b''):
                    full.update(part)
                    digest = hashlib.sha256(part).hexdigest()
                    (chunk_dir / digest).write_bytes(part)
                    chunks.append(dict(sha256=digest, size=len(part), offset=offset))
                    offset += len(part)
            if offset != size or full.hexdigest() != sha:
                raise ValueError('Stored paper differs from the release: ' + sha)
            files[sha]['chunks'] = chunks
    candidates = collections.defaultdict(dict)
    by_school = {}
    for school in manifest['counts']:
        counts = collections.Counter()
        data = verified(release, manifest, f'reader/{school}.jsonl.gz')
        for line in gzip.decompress(data).splitlines():
            row = json.loads(line)
            if row.get('readable') is not True:
                raise ValueError('Non-readable row in reader export')
            item = dict(sourceUrl=source_url(row) if row.get('source_url') or row['decision'] == 'link' else None,
                        license=row.get('license'), version=row.get('version'))
            if row['decision'] == 'host':
                file = files[row['sha256']]
                if file['bytes'] != row['bytes'] or file['format'] != row['format']:
                    raise ValueError('Hosted row differs from release allowlist')
                item.update({k: v for k, v in file.items() if k != 'chunks'}, identityCheck=row.get('identity_check'))
            elif row['decision'] == 'link':
                item.update(link=True, sourceKind=row.get('source_kind'), linkBasis=row.get('link_basis'))
            else:
                raise ValueError('Unknown reader decision')
            identity = row.get('atlas_work_id') or row['key']
            encoded = json.dumps(item, sort_keys=True, separators=(',', ':'))
            rank = (0 if item.get('path') else 1, 0 if item.get('format') == 'pdf' else 1, encoded)
            for key in row['lookup_keys']:
                if not key:
                    continue
                previous = candidates[key].get(identity)
                if previous is None or rank < previous[0]:
                    candidates[key][identity] = (rank, encoded)
            counts[row['decision']] += 1
        by_school[school] = dict(counts)
    # A shared DOI/other alias cannot silently resolve two different accepted works.
    ambiguous = sorted(key for key, values in candidates.items() if len(values) > 1)
    selected = {key: next(iter(values.values()))[1] for key, values in candidates.items() if len(values) == 1}
    encoded_records = sorted(set(selected.values()))
    record_ids = {value: i for i, value in enumerate(encoded_records)}
    records = [json.loads(value) for value in encoded_records]
    index = dict(schema=2, release=manifest['release'], updatedAt=manifest['created'],
                 copySemantics='Hosted copies and verified source links from the frozen research release. Availability does not establish authorship or lab membership.',
                 records=records, works={key: record_ids[value] for key, value in sorted(selected.items())}, files=files)
    compact = dict(schema=1, release=manifest['release'], files={sha: f['bytes'] for sha, f in sorted(files.items())},
                   formats={sha: f['format'] for sha, f in files.items() if f['format'] != 'pdf'},
                   chunks={sha: f['chunks'] for sha, f in files.items() if 'chunks' in f})
    report = dict(release=manifest['release'], hostedFiles=len(files), readerRecords=len(records), lookupKeys=len(selected),
                  bySchool=by_school, ambiguousAliases=ambiguous)
    return index, compact, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release', type=Path)
    parser.add_argument('--stores', type=Path, help='Full-text stores (default: sibling stores/)')
    args = parser.parse_args()
    index, compact, report = project(args.release.resolve(), args.stores)
    outputs = [(ROOT / 'atlas/data/local-papers.json', index),
               (ROOT / 'atlas/data/reader-objects.json', compact),
               (ROOT / 'deployment/reader.json', report)]
    for target, value in outputs:
        temporary = target.with_suffix('.tmp')
        temporary.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')
        temporary.replace(target)
    print(json.dumps({k: v for k, v in report.items() if k != 'ambiguousAliases'}))


if __name__ == '__main__':
    main()
