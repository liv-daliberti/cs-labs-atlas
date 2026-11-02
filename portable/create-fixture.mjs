/** Small, explicitly synthetic dataset for CI; never a research release. */
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { gzipSync } from 'node:zlib';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.resolve(process.argv[2] || 'outputs/fixture');
await mkdir(path.join(output, 'objects'), { recursive: true });
const files = {};
async function put(bytes) {
  const sha256 = createHash('sha256').update(bytes).digest('hex');
  await writeFile(path.join(output, 'objects', sha256), bytes);
  return { sha256, size: bytes.length };
}
async function asset(name, bytes, type) {
  files[name] = { ...(await put(bytes)), type };
}
for (const name of [
  'cs-departments.html',
  'cs-departments.js',
  'cs-departments.css',
  'styles.css',
  'research-data.js',
  'assets/lab-map.css',
  'assets/paper-reader.js',
]) {
  await asset(
    name,
    await readFile(path.join(root, 'atlas', name)),
    name.endsWith('.html') ? 'text/html' : name.endsWith('.css') ? 'text/css' : 'text/javascript',
  );
}
const xml = Buffer.from(
  '<article><body><title>Fixture paper</title><p>Synthetic full text for browser tests.</p></body></article>',
);
const paper = await put(xml);
const schools = [{ id: 'fixture', name: 'Fixture University', uni: 'fixture' }];
await asset(
  'data/cs-hierarchy/index.json',
  Buffer.from(JSON.stringify({ schools, pending: [] })),
  'application/json',
);
const data = {
  school: schools[0],
  builtAt: '2026-11-02T00:00:00Z',
  counts: { labs: 2, labsComplete: 1, papers: 1 },
  departments: [{ name: 'Computer Science', coverage: 'full', labs: [0, 1] }],
  papers: [
    {
      t: 'Fixture paper',
      w: 'fixture-paper',
      y: 2026,
      b: ['Fixture PI'],
      nb: 1,
      u: 'https://example.org/fixture',
    },
  ],
  students: [{ n: 'Fixture Student', r: 'PhD student', id: 'fixture-student' }],
  labs: [
    {
      id: 'fixture-lab',
      name: 'Fixture research group',
      pi: { name: 'Fixture PI' },
      dept: 'Computer Science',
      otherDepts: [],
      periods: [],
      listings: [],
      papers: [[0, 'anchored_author_id', 'P']],
      students: [[0, 'advisee', [2026, 2026], '']],
      links: [[0, 0, 'v']],
    },
    {
      id: 'empty-lab',
      name: 'Hidden empty lab',
      pi: { name: 'Empty PI' },
      dept: 'Computer Science',
      otherDepts: [],
      periods: [],
      listings: [],
      papers: [],
      students: [],
      links: [],
    },
  ],
};
await asset(
  'data/cs-hierarchy/fixture.json.gz',
  gzipSync(JSON.stringify(data)),
  'application/gzip',
);
await asset(
  'data/local-papers.json',
  Buffer.from(
    JSON.stringify({
      schema: 2,
      records: [{ path: 'papers/' + paper.sha256 + '.xml', sha256: paper.sha256, format: 'xml' }],
      works: { 'fixture-paper': 0 },
      files: {},
    }),
  ),
  'application/json',
);
await asset(
  'data/reader-objects.json',
  Buffer.from(
    JSON.stringify({
      schema: 1,
      files: { [paper.sha256]: paper.size },
      formats: { [paper.sha256]: 'xml' },
    }),
  ),
  'application/json',
);
await asset(
  'downloads/cs-hierarchy-labs.csv',
  Buffer.from('lab,papers\nfixture-lab,1\n'),
  'text/csv',
);
const manifest = await put(Buffer.from(JSON.stringify({ schema: 1, files })));
await writeFile(
  path.join(output, 'config.json'),
  JSON.stringify({ schema: 1, release: 'synthetic-ci-fixture', manifestSha256: manifest.sha256 }),
);
console.log(output);
