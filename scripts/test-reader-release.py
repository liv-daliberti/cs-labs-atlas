import gzip
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('reader_import', Path(__file__).with_name('import-reader-release.py'))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


class ReaderReleaseTest(unittest.TestCase):
    def fixture(self, root):
        sha = 'a' * 64
        host = dict(key='paper_a', atlas_work_id='atl:w:a', readable=True, decision='host', sha256=sha,
                    bytes=50, format='pdf', source_url='https://example.org/a', license='cc-by',
                    lookup_keys=['paper_a', 'doi:10.1234/ambiguous'])
        link = dict(key='paper_b', atlas_work_id='atl:w:b', readable=True, decision='link',
                    source_url='https://example.org/b', lookup_keys=['paper_b', 'doi:10.1234/ambiguous'])
        bodies = {
            'reader/SUMMARY.json': json.dumps({'site_sync': {'keep': 0}}).encode(),
            'reader/hosted-files.tsv': f'sha256\tbytes\tschool\tpath\n{sha}\t50\tprinceton\tobjects/{sha}.pdf\n'.encode(),
            'reader/princeton.jsonl.gz': gzip.compress(('\n'.join(map(json.dumps, [host, link]))+'\n').encode()),
        }
        manifest = dict(release='test', created='2026-11-02T00:00:00Z', counts={'princeton': {}}, files={})
        for name, data in bodies.items():
            path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
            manifest['files'][name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        (root/'MANIFEST.json').write_text(json.dumps(manifest))

    def test_exact_allowlist_and_ambiguous_alias(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); self.fixture(root)
            index, compact, report=reader.project(root)
            self.assertEqual(set(index['files']), {'a'*64})
            self.assertEqual(set(compact['files']), set(index['files']))
            self.assertEqual(set(index['works']), {'paper_a', 'paper_b'})
            self.assertEqual(report['ambiguousAliases'], ['doi:10.1234/ambiguous'])
            self.assertTrue(index['records'][index['works']['paper_b']]['link'])
            self.assertNotIn('path', index['records'][index['works']['paper_b']])

    def test_tampered_release_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); self.fixture(root)
            (root/'reader/hosted-files.tsv').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                reader.project(root)


if __name__ == '__main__':
    unittest.main()
