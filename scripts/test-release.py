"""Publication safety tests: small fixtures, no network or research data writes."""
from argparse import Namespace
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import publication_io
import release
from release_inputs import verify_release


class PublicationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'site'
        self.root.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.releases = Path(self.temp.name) / 'releases'
        self.directory = self.releases / '2026-11-02'
        self.directory.mkdir(parents=True)
        self.data = self.directory / 'data.json'
        self.data.write_text('{}')
        self.manifest = dict(release='2026-11-02', evidence_check=True, code={'commit': 'a' * 40},
                             counts={}, reader={'site_sync': {'keep': 1}},
                             files={'data.json': {'bytes': 2, 'sha256': release.sha(self.data)}})
        release.write(self.directory / 'MANIFEST.json', self.manifest)
        release.write(self.root / 'deployment/release.json', dict(release='2026-11-02',
                      manifestSha256=release.sha(self.directory / 'MANIFEST.json'), origin='https://example.org'))
        (self.root / '.gitignore').write_text('outputs/\ndist/\nnode_modules/\natlas/\natlas-storage/\n')
        self.args = Namespace(release='2026-11-02', releases_dir=self.releases, stores=self.root.parent / 'stores', workers=1)
        for name, value in [('ROOT', self.root), ('REPORTS', self.root / 'outputs/publishing')]:
            patcher = patch.object(release, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_tampering_and_traversal_fail_before_pin_change(self):
        pin = (self.root / 'deployment/release.json').read_bytes()
        self.data.write_text('{"tampered":true}')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            release.selected_release(self.args)
        self.assertEqual(pin, (self.root / 'deployment/release.json').read_bytes())
        self.manifest['files'] = {'../outside': {'bytes': 0, 'sha256': '0' * 64}}
        release.write(self.directory / 'MANIFEST.json', self.manifest)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            verify_release(self.directory)

    def test_uncommitted_or_failed_evidence_is_rejected(self):
        for change in ({'evidence_check': False}, {'code': {'uncommitted_tracked_changes': ['input.json']}}):
            manifest = dict(self.manifest, **change)
            release.write(self.directory / 'MANIFEST.json', manifest)
            pin = release.read(self.root / 'deployment/release.json')
            pin['manifestSha256'] = release.sha(self.directory / 'MANIFEST.json')
            release.write(self.root / 'deployment/release.json', pin)
            with self.assertRaises(ValueError):
                release.selected_release(self.args)

    def test_exact_id_required(self):
        for rid in ['latest', '../2026-11-02', '/tmp/release']:
            self.args.release = rid
            with self.assertRaisesRegex(ValueError, 'exact release ID'):
                release.selected_release(self.args)

    def test_source_and_build_receipts_detect_changes(self):
        (self.root / 'app.js').write_text('first')
        (self.root / 'dist').mkdir()
        (self.root / 'dist/index.js').write_text('build')
        source = release.source_fingerprint()
        build = release.build_fingerprint()
        # Recording status does not invalidate the source it describes.
        release.write(self.root / 'deployment/upload-verification.json', {'allUploadsVerified': True})
        self.assertEqual(source, release.source_fingerprint())
        (self.root / 'app.js').write_text('second')
        self.assertNotEqual(source, release.source_fingerprint())
        (self.root / 'dist/index.js').write_text('changed')
        self.assertNotEqual(build, release.build_fingerprint())

    def test_plan_has_no_writes_or_subprocesses(self):
        before = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('*'))
        with patch.object(release.subprocess, 'run', side_effect=AssertionError('plan executed a command')):
            self.assertEqual(release.main(['plan', '--releases-dir', str(self.releases)]), 0)
        self.assertEqual(before, sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('*')))

    def test_failed_preparation_invalidates_old_success_and_stops(self):
        (self.root / 'node_modules').mkdir()
        release.write(release.REPORTS / '2026-11-02/state.json', {'status': 'uploaded'})
        calls = []
        def fail(argv, **kwargs):
            calls.append(argv)
            return Namespace(returncode=1)
        with patch.object(release.shutil, 'which', return_value='/usr/bin/tool'), patch.object(release.subprocess, 'run', side_effect=fail):
            with self.assertRaisesRegex(ValueError, 'hierarchy failed'):
                release.prepare(self.args)
        self.assertEqual(len(calls), 1)
        self.assertEqual(release.read(release.REPORTS / '2026-11-02/state.json')['status'], 'failed')
        self.assertFalse(release.read(self.root / 'deployment/upload-verification.json')['allUploadsVerified'])

    def test_upload_never_runs_with_stale_source(self):
        (self.root / 'dist').mkdir()
        (self.root / 'dist/index.js').write_text('build')
        release.write(release.REPORTS / '2026-11-02/state.json', dict(status='prepared',
                      researchManifestSha256=release.sha(self.directory / 'MANIFEST.json'), sourceFingerprint='stale'))
        with patch.object(release.subprocess, 'run', wraps=subprocess.run) as run:
            with self.assertRaisesRegex(ValueError, 'Source changed'):
                release.upload(self.args)
        self.assertTrue(all(call.args[0][0] == 'git' for call in run.call_args_list))

    def test_concurrent_writer_refused(self):
        with release.lock():
            with self.assertRaisesRegex(ValueError, 'Another publication'):
                with release.lock():
                    self.fail('second writer acquired the lock')

    def test_asset_bytes_and_runtime_pin_are_checked(self):
        atlas = self.root / 'atlas'; atlas.mkdir()
        (atlas / 'index.html').write_text('hello')
        files = {'index.html': {'size': 5, 'sha256': release.sha(atlas / 'index.html')}}
        release.write(self.root / 'atlas-storage/releases/manifest.json', {'files': files})
        digest = release.sha(self.root / 'atlas-storage/releases/manifest.json')
        release.write(self.root / 'atlas-storage/upload-plan.json', dict(sourceDirectory=str(atlas), files=files,
                      manifestFile='atlas-storage/releases/manifest.json', manifestSha256=digest))
        release.write(self.root / 'lib/atlas-release.json', {'manifestSha256': digest})
        self.assertEqual(release.verify_assets()['manifestSha256'], digest)
        (atlas / 'index.html').write_text('other')
        with self.assertRaisesRegex(ValueError, 'Asset changed'):
            release.verify_assets()

    def test_receipts_cannot_be_reused_for_another_origin(self):
        receipts = {'schema': 2, 'origin': 'https://one.example', 'objects': {'a': {'verified': True}}}
        self.assertTrue(publication_io.scoped_receipts(receipts, 'https://one.example'))
        self.assertEqual(publication_io.scoped_receipts(receipts, 'https://two.example'), {})
        self.assertEqual(publication_io.scoped_receipts(receipts['objects'], 'https://one.example'), {})

    def test_ready_requires_successful_upload_to_current_origin(self):
        release.write(self.root / '.openai/hosting.json', {'project_id': 'fixture-project'})
        state = {'release': '2026-11-02', 'status': 'uploaded', 'assetManifestSha256': 'a' * 64}
        receipt = {'allUploadsVerified': True, 'manifestSha256': 'a' * 64, 'origin': 'https://another.example'}
        with patch.object(release, 'prepared', return_value=(self.directory, state)):
            release.write(self.root / 'deployment/upload-verification.json', receipt)
            self.assertEqual(release.main(['ready']), 1)
            receipt['origin'] = 'https://example.org'
            release.write(self.root / 'deployment/upload-verification.json', receipt)
            self.assertEqual(release.main(['ready']), 0)
            state['status'] = 'prepared'
            self.assertEqual(release.main(['ready']), 1)

    def test_origin_and_short_credentials_rejected(self):
        self.assertEqual(publication_io.origin('https://example.org/'), 'https://example.org')
        for value in ['http://example.org', 'https://user:secret@example.org', 'https://example.org/path', 'https://example.org?token=value']:
            with self.assertRaises(ValueError):
                publication_io.origin(value)
        with patch.dict(os.environ, {'ATLAS_UPDATE_TOKEN': 'short'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'at least 32'):
                publication_io.credentials(update=True)


if __name__ == '__main__':
    unittest.main()
