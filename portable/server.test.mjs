import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtemp, mkdir, writeFile, rm, symlink } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { once } from 'node:events';
import { createAtlasServer } from './server.mjs';
import { FileBucket } from './file-bucket.mjs';

const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');

async function fixture(t) {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'atlas-server-'));
  await mkdir(path.join(directory, 'objects'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  const put = async (value) => {
    const bytes = Buffer.isBuffer(value) ? value : Buffer.from(value);
    const sha256 = digest(bytes);
    await writeFile(path.join(directory, 'objects', sha256), bytes);
    return { sha256, size: bytes.length };
  };
  const paper = await put('%PDF-1.7\nfixture paper\n');
  const withdrawn = await put('%PDF-1.7\nwithdrawn fixture\n');
  const index = await put(JSON.stringify({ schema: 1, files: { [paper.sha256]: paper.size } }));
  const home = await put('<!doctype html><title>Atlas fixture</title>');
  const manifest = await put(
    JSON.stringify({
      schema: 1,
      files: {
        'index.html': { ...home, type: 'text/html' },
        'data/reader-objects.json': { ...index, type: 'application/json' },
      },
    }),
  );
  await writeFile(
    path.join(directory, 'config.json'),
    JSON.stringify({ schema: 1, release: 'fixture', manifestSha256: manifest.sha256 }),
  );
  const errors = [];
  const server = await createAtlasServer(directory, { onError: (error) => errors.push(error) });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(
    () =>
      new Promise((resolve) => {
        server.close(resolve);
        server.closeAllConnections();
      }),
  );
  return {
    directory,
    put,
    paper,
    withdrawn,
    errors,
    base: 'http://127.0.0.1:' + server.address().port,
  };
}

test('real HTTP serves exact bytes, HEAD, ETags and byte ranges', async (t) => {
  const f = await fixture(t);
  let response = await fetch(f.base);
  assert.equal(response.status, 200);
  assert.equal(await response.text(), '<!doctype html><title>Atlas fixture</title>');
  const etag = response.headers.get('ETag');
  assert.equal((await fetch(f.base, { headers: { 'If-None-Match': etag } })).status, 304);
  response = await fetch(f.base, { method: 'HEAD' });
  assert.equal(await response.text(), '');
  assert.ok(Number(response.headers.get('Content-Length')) > 0);
  response = await fetch(f.base + '/papers/' + f.paper.sha256 + '.pdf', {
    headers: { Range: 'bytes=0-4' },
  });
  assert.equal(response.status, 206);
  assert.equal(await response.text(), '%PDF-');
  assert.equal((await fetch(f.base, { headers: { Range: 'bytes=9000-10000' } })).status, 416);
  assert.deepEqual(f.errors, []);
});

test('only admitted papers are public and all write routes are closed', async (t) => {
  const f = await fixture(t);
  for (const name of [
    '/papers/' + f.withdrawn.sha256 + '.pdf',
    '/objects/' + f.paper.sha256,
    '/config.json',
    '/%00secret',
  ]) {
    assert.equal((await fetch(f.base + name)).status, 404, name);
  }
  for (const method of ['GET', 'HEAD', 'PUT', 'DELETE']) {
    assert.equal(
      (await fetch(f.base + '/api/atlas-storage/' + f.paper.sha256, { method })).status,
      404,
    );
  }
  assert.equal((await fetch(f.base, { method: 'POST' })).status, 405);
});

test('changed files fail closed, including after a successful cached read', async (t) => {
  const f = await fixture(t);
  const url = f.base + '/papers/' + f.paper.sha256 + '.pdf';
  assert.equal((await fetch(url)).status, 200);
  await writeFile(path.join(f.directory, 'objects', f.paper.sha256), 'corrupted bytes');
  const response = await fetch(url);
  assert.equal(response.status, 503);
  assert.match(await response.text(), /temporarily unavailable/);
  assert.match(f.errors[0], /checksum mismatch/);
});

test('bucket rejects traversal and symlinks and supports lazy JSON reads', async (t) => {
  const f = await fixture(t);
  const bucket = new FileBucket(path.join(f.directory, 'objects'));
  assert.equal(await bucket.head('../config.json'), null);
  const entry = await f.put('{"fixture":true}');
  const object = await bucket.get('objects/' + entry.sha256);
  assert.deepEqual(await object.json(), { fixture: true });
  const link = 'f'.repeat(64);
  await symlink(path.join(f.directory, 'config.json'), path.join(f.directory, 'objects', link));
  await assert.rejects(() => bucket.head('objects/' + link), /regular file/);
});

test('health endpoint identifies the bundle without exposing host details', async (t) => {
  const f = await fixture(t);
  assert.deepEqual(await (await fetch(f.base + '/healthz')).json(), {
    status: 'ok',
    release: 'fixture',
  });
  assert.equal(await (await fetch(f.base + '/healthz', { method: 'HEAD' })).text(), '');
});
