/** Small, explicitly synthetic dataset for CI; never a research release. */
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile, readdir } from 'node:fs/promises';
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
async function codeFiles(dir = '') {
  for (const entry of await readdir(path.join(root, 'atlas', dir), { withFileTypes: true })) {
    const name = path.posix.join(dir, entry.name);
    if (['data', 'downloads', 'papers'].includes(name)) continue;
    if (entry.isDirectory()) await codeFiles(name);
    else if (/\.(html|js|css)$/.test(name))
      await asset(
        name,
        await readFile(path.join(root, 'atlas', name)),
        name.endsWith('.html')
          ? 'text/html'
          : name.endsWith('.css')
            ? 'text/css'
            : 'text/javascript',
      );
  }
}
await codeFiles();

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
// Both real pages use a deliberately small synthetic atlas, never copied research records.
const field = 'computer_and_information_sciences';
const status = 'publication_identity_verified';
const counts = [
  { u: 'fixture', field, status, n: 1, named: 1, verified: 1, active: 1, years: { 2026: 1 } },
];
const stats = {
  works: 1,
  publishing: 1,
  groupLinks: 1,
  oa: null,
  meanAuthors: 1,
  topicCount: 0,
  entropy: null,
  international: null,
  hhi: 1,
};
const overview = Object.fromEntries(
  ['combined', 'strict', 'reviewed'].map((view) => [
    view,
    { stats, annual: [{ year: 2026, activity: 1, publishing: 1, works: 1, links: 1, oa: null }] },
  ]),
);
const rule = {
  schema: 1,
  field,
  departmentPattern: 'computer',
  flags: 'i',
  shown: 'Synthetic fixture only',
};
const metrics = {
  units: [{ u: 'fixture', field, status, years: { 2026: 1 } }],
  buckets: ['combined', 'strict', 'reviewed'].map((view) => ({
    view,
    members: [{ uni: 'fixture', lab: 'fixture-lab', field, status, groups: ['fixture-pi'] }],
    years: { 2026: { works: 1, oa: 0, oaUnknown: 1, topics: {} } },
  })),
};
const lab = {
  id: 'fixture-lab',
  name: 'Fixture research group',
  pi: 'Fixture PI',
  pis: [{ name: 'Fixture PI' }],
  field,
  department: 'Computer Science',
  departments: ['Computer Science'],
  type: 'pi_lab',
  unitType: 'pi_lab',
  csScope: true,
  csShown: true,
  csScopeReason: 'cs_department_pi_lab',
  leadershipStatus: status,
  years: [2026],
  evidence: [],
  leadership: [],
  paperCounts: { combined: { 2026: 1 }, strict: {}, reviewed: {} },
  hierarchy: {
    file: 'data/cs-hierarchy/fixture.json.gz',
    id: 'fixture-lab',
    index: 0,
    school: 'fixture',
  },
};
await asset(
  'data/fixture-university.json.gz',
  gzipSync(JSON.stringify({ id: 'fixture', labs: [lab], metrics })),
  'application/gzip',
);
await asset('data/fixture-metrics.json.gz', gzipSync(JSON.stringify(metrics)), 'application/gzip');
const hidden = { no_papers: 0, no_lab_papers: 1, replaced_by_pi_labs: 0 };
const scope = {
  labs: 1,
  inScope: 2,
  piLabs: 2,
  school: 'fixture',
  labsFile: 'data/fixture-university.json.gz',
  counts,
  overview,
  hidden,
};
const atlas = {
  bundleFormat: 'lazy-atlas-v1',
  asOf: '2026-11-02',
  universities: [
    {
      id: 'fixture',
      name: 'Fixture University',
      country: 'Synthetic',
      rank: '1',
      rankLow: 1,
      labs: [],
      csScope: scope,
      labsFile: scope.labsFile,
    },
  ],
  works: {},
  downloads: {},
  fields: [],
  publicationSummary: { window_end: '2026-11-02' },
  csScope: {
    rule,
    counts,
    overview,
    metricsFile: 'data/fixture-metrics.json.gz',
    hierarchy: { fixture: {} },
    summary: { labs: 1, byReason: { cs_department_pi_lab: 1 }, hidden },
  },
  assets: Object.fromEntries(
    Object.entries(files)
      .filter(([name]) => name.startsWith('data/'))
      .map(([name, entry]) => [name, entry.sha256]),
  ),
};
await asset('data.json', Buffer.from(JSON.stringify(atlas)), 'application/json');
await asset(
  'data/publication.json',
  Buffer.from(
    JSON.stringify({
      release: 'Synthetic development dataset',
      coverage: 'Test data only; not research evidence',
      researchRelease: 'none',
    }),
  ),
  'application/json',
);
const manifest = await put(Buffer.from(JSON.stringify({ schema: 1, files })));
await writeFile(
  path.join(output, 'config.json'),
  JSON.stringify({ schema: 1, release: 'synthetic-ci-fixture', manifestSha256: manifest.sha256 }),
);
console.log(output);
