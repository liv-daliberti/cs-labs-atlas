"""Portable publication bundles preserve the frozen allowlist without network access."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('bundle_site', Path(__file__).with_name('bundle-site.py'))
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class BundleTest(unittest.TestCase):
    def test_copy_bundle_is_independent_and_withdrawn_files_are_excluded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            site = root / 'site'
            release = root / 'release'
            stores = root / 'stores'
            for directory in [site / 'atlas/data', site / 'deployment', release / 'reader', stores / 'fixture/objects']:
                directory.mkdir(parents=True)
            paper = b'%PDF-1.7\nfixture\n'
            sha = hashlib.sha256(paper).hexdigest()
            source = stores / 'fixture/objects' / (sha + '.pdf')
            source.write_bytes(paper)
            (source.parent / 'withdrawn.pdf').write_bytes(b'not admitted')
            table = release / 'reader/hosted-files.tsv'
            table.write_text(f'sha256\tbytes\tschool\tpath\n{sha}\t{len(paper)}\tfixture\tobjects/{sha}.pdf\n')
            manifest = dict(release='2026-11-02', evidence_check=True,
                            files={'reader/hosted-files.tsv': {'bytes': table.stat().st_size, 'sha256': bundle.digest(table)}})
            (release / 'MANIFEST.json').write_text(json.dumps(manifest))
            (site / 'deployment/release.json').write_text(json.dumps({'release': '2026-11-02', 'manifestSha256': bundle.digest(release / 'MANIFEST.json')}))
            compact = site / 'atlas/data/reader-objects.json'
            compact.write_text(json.dumps({'release': '2026-11-02', 'files': {sha: len(paper)}}))
            asset_manifest = {'schema': 1, 'files': {'data/reader-objects.json': {
                'sha256': bundle.digest(compact), 'size': compact.stat().st_size, 'type': 'application/json'}}}
            (site / 'deployment/asset-manifest.json').write_text(json.dumps(asset_manifest))
            original_root = bundle.ROOT
            bundle.ROOT = site
            try:
                output = root / 'bundle'
                receipt = bundle.build(release, stores, output, verify_papers=True)
                self.assertEqual(receipt['hostedFiles'], 1)
                self.assertEqual(len(list((output / 'objects').iterdir())), 3)
                self.assertNotEqual((output / 'objects' / sha).stat().st_ino, source.stat().st_ino)
                source.write_bytes(b'changed after bundle')
                self.assertEqual((output / 'objects' / sha).read_bytes(), paper)
                with self.assertRaises(ValueError):
                    bundle.build(release, stores, root / 'bad-bundle')
                self.assertFalse((root / 'bad-bundle').exists())
            finally:
                bundle.ROOT = original_root


if __name__ == '__main__':
    unittest.main()
