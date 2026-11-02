import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash, randomBytes} from 'node:crypto';
import {gzipSync, gunzipSync} from 'node:zlib';
import {princetonRelease, servePrinceton} from '../lib/princeton-release.mjs';
import {uploadObject} from '../lib/atlas-storage.mjs';
import {CHUNK_BYTES, GRAPH_PATH, INDEX_PATH, validateChunks, chunkRuntimeProbe} from '../lib/chunked-graph.mjs';
const sha = b => createHash('sha256').update(b).digest('hex');
let digestsCreated = 0;
class NodeDigestStream extends WritableStream {
  constructor() {
    const hash = createHash('sha256'); let resolve, reject;
    const digest = new Promise((yes, no) => { resolve = yes; reject = no; });
    // Production provides this API natively. This test adapter hashes incrementally.
    super({write(value) { hash.update(value); }, close() { resolve(Uint8Array.from(hash.digest()).buffer); }, abort(reason) { reject(reason); }});
    this.digest = digest; digest.catch(() => {}); digestsCreated++;
  }
}
Object.defineProperty(crypto, 'DigestStream', {value: NodeDigestStream, configurable: true});
globalThis.FixedLengthStream = class extends TransformStream {
  constructor(length) {
    let count = 0;
    super({transform(value, controller) { count += value.byteLength; if (count > length) throw new Error('Fixed length exceeded'); controller.enqueue(value); }, flush() { if (count !== length) throw new Error('Fixed length truncated'); }});
  }
};
const plain = randomBytes(CHUNK_BYTES + 283), gzip = gzipSync(plain, {level: 1, mtime: 123});
const dataParts = [];
for (let offset = 0; offset < gzip.length; offset += CHUNK_BYTES) dataParts.push(gzip.subarray(offset, offset + CHUNK_BYTES));
const canonical = {storage: 'chunks-v1', sha256: sha(gzip), size: gzip.length, type: 'application/gzip', chunks: dataParts.map((b, i) => ({offset: i * CHUNK_BYTES, size: b.length, sha256: sha(b)}))};
class Bucket {
  objects = new Map(); gets = []; heads = []; cancelled = 0; corrupt = new Map();
  install(key, bytes) { this.objects.set(key, {bytes, sha: sha(bytes)}); }
  async put(key, body, options = {}) {
    const bytes = Buffer.from(await new Response(body).arrayBuffer()), existing = this.objects.get(key);
    if (options.sha256 && options.sha256 !== sha(bytes)) throw new Error('Checksum mismatch');
    if (options.onlyIf?.etagDoesNotMatch === '*' && existing) return null;
    if (options.onlyIf?.etagMatches && options.onlyIf.etagMatches !== existing?.sha) return null;
    this.install(key, bytes); return this.head(key);
  }
  metadata(key) { const o = this.objects.get(key); return o ? {size: o.bytes.length, etag: o.sha, checksums: {sha256: Uint8Array.from(Buffer.from(o.sha, 'hex')).buffer}} : null; }
  async head(key) { this.heads.push(key); return this.metadata(key); }
  async get(key, options) {
    this.gets.push(key); const object = this.objects.get(key); if (!object) return null;
    let bytes = this.corrupt.has(key) ? this.corrupt.get(key)(object.bytes) : object.bytes;
    if (options?.range) bytes = bytes.subarray(options.range.offset, options.range.offset + options.range.length);
    let offset = 0; const bucket = this;
    const body = new ReadableStream({pull(controller) { if (offset >= bytes.length) { controller.close(); return; } const next = bytes.subarray(offset, offset + 65536); offset += next.length; controller.enqueue(next); }, cancel() { bucket.cancelled++; }}, {highWaterMark: 0});
    return {...this.metadata(key), body, json: async () => JSON.parse(bytes), arrayBuffer: async () => Uint8Array.from(bytes).buffer};
  }
}
const clone = x => structuredClone(x);
const request = (input, method = 'PUT', query = '') => new Request('https://atlas.test/api/princeton-release' + query, {method, ...(method === 'PUT' ? {body: JSON.stringify(input)} : {})});
const graphRequest = (headers = {}, method = 'GET') => new Request('https://atlas.test/' + GRAPH_PATH, {method, headers});
async function setup() {
  const bucket = new Bucket();
  for (const bytes of dataParts) bucket.install('objects/' + sha(bytes), bytes);
  const index = Buffer.from('compact fixture'); bucket.install('objects/' + sha(index), index);
  const files = {[GRAPH_PATH]: clone(canonical), [INDEX_PATH]: {sha256: sha(index), size: index.length, type: 'application/gzip'}};
  const save = async (files, nonce = '') => { const bytes = Buffer.from(JSON.stringify({schema: 1, files, nonce})), digest = sha(bytes); bucket.install('objects/' + digest, bytes); return digest; };
  const env = {ATLAS_BUCKET: bucket};
  const publish = async (files, previous = null, nonce = '') => princetonRelease(request({manifestSha256: await save(files, nonce), previousManifestSha256: previous}), env);
  return {bucket, env, files, save, publish};
}
const pointer = bucket => bucket.objects.get('updates/princeton/current.json')?.bytes.toString();

test('publishes and downloads exactly the original gzip, with legacy-compatible metadata', async () => {
  const x = await setup(); assert.equal((await x.publish(x.files)).status, 201);
  const response = await servePrinceton(graphRequest(), x.env);
  assert.equal(response.status, 200); assert.equal(response.headers.get('ETag'), '"' + canonical.sha256 + '"');
  assert.equal(response.headers.get('Content-Length'), String(gzip.length));
  assert.equal(response.headers.get('Content-Encoding'), null); assert.match(response.headers.get('Cache-Control'), /no-transform/);
  assert.match(response.headers.get('Content-Disposition'), /princeton-network.json.gz/);
  const actual = Buffer.from(await response.arrayBuffer()); assert.deepEqual(actual, gzip); assert.deepEqual(gunzipSync(actual), plain);
});

test('HEAD, conditionals and ranges within/across chunk boundaries use whole-file semantics', async () => {
  const x = await setup(); await x.publish(x.files); const etag = '"' + canonical.sha256 + '"';
  let response = await servePrinceton(graphRequest({}, 'HEAD'), x.env);
  assert.equal(response.status, 200); assert.equal(response.headers.get('Content-Length'), String(gzip.length)); assert.equal(await response.text(), '');
  response = await servePrinceton(graphRequest({'If-None-Match': 'W/' + etag}), x.env); assert.equal(response.status, 304);
  for (const [value, start, end] of [['bytes=12-91', 12, 91], [`bytes=${CHUNK_BYTES - 9}-${CHUNK_BYTES + 12}`, CHUNK_BYTES - 9, CHUNK_BYTES + 12], ['bytes=-17', gzip.length - 17, gzip.length - 1]]) {
    response = await servePrinceton(graphRequest({Range: value, 'If-Range': etag}), x.env);
    assert.equal(response.status, 206); assert.equal(response.headers.get('Content-Range'), `bytes ${start}-${end}/${gzip.length}`);
    assert.deepEqual(Buffer.from(await response.arrayBuffer()), gzip.subarray(start, end + 1));
  }
  for (const range of ['bytes=1-0', 'bytes=-0', 'bytes=999999999-', 'bytes=0-1,4-5']) assert.equal((await servePrinceton(graphRequest({Range: range}), x.env)).status, 416);
  response = await servePrinceton(graphRequest({Range: 'bytes=1-2', 'If-Range': '"old"'}), x.env); assert.equal(response.status, 200); await response.body.cancel();
});

test('descriptor rejects gaps, overlaps, reorder metadata, mixed modes, illegal paths and limits before reads', async () => {
  const cases = [];
  for (const change of [e => e.chunks[1].offset++, e => e.chunks[1].offset--, e => e.size++, e => e.chunks[0].size--, e => e.chunks.reverse(), e => e.storage = 'unknown', e => e.extra = 1, e => e.size = 512 * 2**20 + 1, e => e.chunks[0].sha256 = 'X'.repeat(64)]) { const entry = clone(canonical); change(entry); cases.push(entry); }
  for (const entry of cases) {
    const x = await setup(); x.files[GRAPH_PATH] = entry; const before = x.bucket.heads.length;
    assert.equal((await x.publish(x.files)).status, 400); assert.equal(pointer(x.bucket), undefined); assert.equal(x.bucket.heads.length, before);
  }
  const x = await setup(); delete x.files[INDEX_PATH]; assert.equal((await x.publish(x.files)).status, 400);
  assert.throws(() => validateChunks('data/princeton-network-other.json.gz', canonical));
  const direct = {...canonical}; delete direct.storage; x.files[GRAPH_PATH] = direct; assert.equal((await x.publish(x.files)).status, 400);
  const budget = await setup(); budget.files[GRAPH_PATH] = {...canonical, size: 16 * CHUNK_BYTES, chunks: Array.from({length: 16}, (_, i) => ({offset: i * CHUNK_BYTES, size: CHUNK_BYTES, sha256: canonical.chunks[0].sha256}))};
  for (let i = 0; i < 25; i++) budget.files[`data/princeton-network-a${i}.json.gz`] = clone(budget.files[INDEX_PATH]);
  assert.equal((await budget.publish(budget.files)).status, 400); assert.equal(pointer(budget.bucket), undefined);
});

test('missing, corrupt, truncated, reordered and wrong-whole-hash data never replace the current pointer', async () => {
  for (const mode of ['missing', 'corrupt', 'truncated', 'wrong-whole', 'reordered']) {
    const x = await setup(); const legacy = clone(x.files); legacy[GRAPH_PATH] = clone(legacy[INDEX_PATH]);
    const first = await (await x.publish(legacy)).json(); const before = pointer(x.bucket);
    if (mode === 'missing') x.bucket.objects.delete('objects/' + canonical.chunks[1].sha256);
    if (mode === 'corrupt') x.bucket.corrupt.set('objects/' + canonical.chunks[1].sha256, b => { const altered = Buffer.from(b); altered[0] ^= 1; return altered; });
    if (mode === 'truncated') x.bucket.corrupt.set('objects/' + canonical.chunks[1].sha256, b => b.subarray(0, -1));
    if (mode === 'wrong-whole') x.files[GRAPH_PATH].sha256 = 'f'.repeat(64);
    if (mode === 'reordered') [x.files[GRAPH_PATH].chunks[0].sha256, x.files[GRAPH_PATH].chunks[1].sha256] = [x.files[GRAPH_PATH].chunks[1].sha256, x.files[GRAPH_PATH].chunks[0].sha256];
    const response = await x.publish(x.files, first.manifestSha256); assert.equal(response.status, 400, mode); assert.equal(pointer(x.bucket), before, mode);
  }
});

test('verification receipts avoid rehashing unchanged immutable data but still check every object', async () => {
  const x = await setup(); const first = await (await x.publish(x.files)).json(); const count = digestsCreated;
  const second = await (await x.publish(x.files, first.manifestSha256, 'new-index-release')).json(); assert.equal(digestsCreated, count);
  x.bucket.objects.delete('objects/' + canonical.chunks[1].sha256); const before = pointer(x.bucket);
  assert.equal((await x.publish(x.files, second.manifestSha256, 'missing-chunk')).status, 400); assert.equal(pointer(x.bucket), before);
  assert.equal((await servePrinceton(graphRequest({}, 'HEAD'), x.env)).status, 503);
});

test('oversized or corrupt receipts trigger bounded revalidation; request bodies are bounded without Content-Length', async () => {
  const x = await setup(); let current = await (await x.publish(x.files)).json();
  const key = [...x.bucket.objects.keys()].find(key => key.startsWith('updates/princeton/verified-chunks/'));
  x.bucket.install(key, Buffer.alloc(2049));
  const before = x.bucket.cancelled, count = digestsCreated;
  current = await (await x.publish(x.files, current.manifestSha256, 'recheck')).json();
  assert.equal(x.bucket.cancelled, before + 1); assert.ok(digestsCreated > count);
  const previous = pointer(x.bucket);
  assert.equal((await princetonRelease(new Request('https://atlas.test/api/princeton-release', {method: 'PUT', body: 'x'.repeat(8193)}), x.env)).status, 413);
  assert.equal(pointer(x.bucket), previous);
});

test('concurrent publishers CAS once, and an in-flight reader retains its original manifest', async () => {
  const x = await setup(); const [a, b] = await Promise.all([x.publish(x.files, null, 'a'), x.publish(x.files, null, 'b')]);
  assert.deepEqual([a.status, b.status].sort(), [201, 409]);
  const oldResponse = await servePrinceton(graphRequest(), x.env); const current = JSON.parse(pointer(x.bucket));
  const changed = Buffer.from(dataParts[1]); changed[0] ^= 1; x.bucket.install('objects/' + sha(changed), changed);
  const next = clone(x.files); next[GRAPH_PATH].chunks[1].sha256 = sha(changed); next[GRAPH_PATH].sha256 = sha(Buffer.concat([dataParts[0], changed]));
  assert.equal((await x.publish(next, current.manifestSha256)).status, 201);
  assert.equal(sha(Buffer.from(await oldResponse.arrayBuffer())), canonical.sha256);
});

test('cancelled and truncated downloads stop opening future chunks and fail visibly', async () => {
  const x = await setup(); await x.publish(x.files); x.bucket.gets = [];
  const response = await servePrinceton(graphRequest(), x.env), reader = response.body.getReader();
  assert.equal((await reader.read()).value.length, 65536); await reader.cancel('closed');
  assert.equal(x.bucket.gets.filter(key => canonical.chunks.some(c => key === 'objects/' + c.sha256)).length, 1);
  assert.ok(x.bucket.cancelled > 0);
  x.bucket.corrupt.set('objects/' + canonical.chunks[1].sha256, b => b.subarray(0, -1));
  await assert.rejects(async () => (await servePrinceton(graphRequest(), x.env)).arrayBuffer(), /Truncated/);
});

test('interrupted uploads never create an object or mutate the release; runtime probe is read only', async () => {
  const x = await setup(); await x.publish(x.files); const before = pointer(x.bucket), target = 'a'.repeat(64);
  const body = new ReadableStream({start(c) { c.enqueue(new Uint8Array([1])); c.error(new Error('disconnected')); }});
  const response = await uploadObject(new Request('https://atlas.test/api/atlas-storage/' + target, {method: 'PUT', body, duplex: 'half', headers: {'Content-Length': '40'}}), x.env);
  assert.equal(response.status, 400); assert.equal(x.bucket.objects.has('objects/' + target), false); assert.equal(pointer(x.bucket), before);
  assert.equal((await chunkRuntimeProbe()).supported, true);
  Object.defineProperty(crypto, 'DigestStream', {value: undefined, configurable: true});
  try { const probe = await princetonRelease(request(null, 'GET', '?probe=chunks-v1'), x.env); assert.equal((await probe.json()).supported, false); }
  finally { Object.defineProperty(crypto, 'DigestStream', {value: NodeDigestStream, configurable: true}); }
  assert.equal(pointer(x.bucket), before);
});
