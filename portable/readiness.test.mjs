import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readiness } from './readiness.mjs';
test('readiness checks many schools without opening unused storage bodies', async () => {
  const objects = new Map();
  let gets = 0;
  const put = (value) => {
    const raw = JSON.stringify(value),
      sha256 = createHash('sha256').update(raw).digest('hex');
    objects.set(sha256, raw);
    return { sha256, size: Buffer.byteLength(raw) };
  };
  const schools = Array.from({ length: 20 }, (_, i) => ({ id: 'school-' + i }));
  const files = Object.fromEntries(
    ['index.html', 'cs-departments.html', 'data.json', 'data/reader-objects.json'].map((name) => [
      name,
      put({ name }),
    ]),
  );
  files['data/cs-hierarchy/index.json'] = put({ schools });
  for (const school of schools) files['data/cs-hierarchy/' + school.id + '.json.gz'] = put(school);
  const manifest = put({ schema: 1, files });
  const bucket = {
    async head(key) {
      const sha = key.slice(8),
        raw = objects.get(sha);
      return raw
        ? {
            size: Buffer.byteLength(raw),
            checksums: { sha256: Uint8Array.from(Buffer.from(sha, 'hex')).buffer },
          }
        : null;
    },
    async get(key) {
      gets++;
      const raw = objects.get(key.slice(8));
      return {
        ...(await this.head(key)),
        async json() {
          return JSON.parse(raw);
        },
      };
    },
  };
  assert.equal(
    (await readiness(bucket, { release: 'fixture', manifestSha256: manifest.sha256 })).status,
    'ready',
  );
  assert.equal(gets, 2, 'Only manifest and school index bodies should open');
  objects.delete(
    files['data/school-missing']?.sha256 || files['data/cs-hierarchy/school-19.json.gz'].sha256,
  );
  await assert.rejects(() => readiness(bucket, { manifestSha256: manifest.sha256 }), /unavailable/);
});
