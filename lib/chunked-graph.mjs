// Canonical gzip slices are immutable objects; they are never recompressed.
export const GRAPH_PATH = 'data/princeton-network.json.gz';
export const INDEX_PATH = 'data/princeton-network-index.json.gz';
export const CHUNK_BYTES = 32 * 2 ** 20;
export const MAX_CHUNKS = 16;
export const MAX_GRAPH_BYTES = CHUNK_BYTES * MAX_CHUNKS;
export const MAX_ASSET_READS = 40;
const HEX = /^[a-f0-9]{64}$/;
export const hex = value => [...new Uint8Array(value)].map(x => x.toString(16).padStart(2, '0')).join('');
const fail = message => { throw new Error(message); };
const onlyKeys = (value, keys) => value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).every(key => keys.includes(key));

export function validateChunks(name, entry) {
  if (name !== GRAPH_PATH || !onlyKeys(entry, ['storage', 'sha256', 'size', 'type', 'chunks']) || entry.storage !== 'chunks-v1' || entry.type !== 'application/gzip' || !HEX.test(entry.sha256 || '') || !Number.isSafeInteger(entry.size) || entry.size < 1 || entry.size > MAX_GRAPH_BYTES) fail('Invalid chunked graph descriptor');
  if (!Array.isArray(entry.chunks) || !entry.chunks.length || entry.chunks.length > MAX_CHUNKS) fail('Invalid chunk count');
  let total = 0;
  for (const [i, chunk] of entry.chunks.entries()) {
    if (!onlyKeys(chunk, ['offset', 'size', 'sha256']) || !HEX.test(chunk.sha256 || '') || !Number.isSafeInteger(chunk.offset) || chunk.offset !== total || !Number.isSafeInteger(chunk.size) || chunk.size < 1 || chunk.size > CHUNK_BYTES || (i < entry.chunks.length - 1 && chunk.size !== CHUNK_BYTES)) fail('Invalid chunk offset or size');
    total += chunk.size;
  }
  if (total !== entry.size) fail('Chunk total differs from graph size');
  return entry;
}

export function verifiedObject(object, expected) {
  return !!object && object.size === expected.size && !!object.checksums?.sha256 && hex(object.checksums.sha256) === expected.sha256;
}

function digestStream() {
  if (typeof crypto.DigestStream !== 'function') fail('Streaming SHA-256 is unavailable in this runtime');
  return new crypto.DigestStream('SHA-256');
}

export async function chunkRuntimeProbe() {
  try {
    if (typeof FixedLengthStream !== 'function') fail('Fixed-length streaming is unavailable in this runtime');
    const digest = digestStream(), writer = digest.getWriter();
    await writer.write(new TextEncoder().encode('a'));
    await writer.write(new TextEncoder().encode('bc'));
    await writer.close();
    if (hex(await digest.digest) !== 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad') fail('Streaming SHA-256 probe failed');
    return {supported: true, storage: 'chunks-v1', chunkBytes: CHUNK_BYTES, maxChunks: MAX_CHUNKS, maxGraphBytes: MAX_GRAPH_BYTES, maxAssetReads: MAX_ASSET_READS};
  } catch (error) {
    return {supported: false, storage: 'chunks-v1', error: error.message};
  }
}

// workerd omits Content-Length for an ordinary ReadableStream even when the
// response specifies it. The native fixed-length stream supplies known length,
// enforces that length, and propagates errors/cancellation through pipeTo.
export function lengthCheckedBody(body, length) {
  if (typeof FixedLengthStream !== 'function') fail('Fixed-length streaming is unavailable');
  const fixed = new FixedLengthStream(length);
  body.pipeTo(fixed.writable).catch(() => {}); // The readable side carries errors.
  return fixed.readable;
}

async function descriptorKey(entry) {
  // Canonical ordering means irrelevant manifest property ordering cannot fork receipts.
  const value = {storage: entry.storage, sha256: entry.sha256, size: entry.size, chunks: entry.chunks.map(c => [c.offset, c.size, c.sha256])};
  return hex(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(value))));
}

export async function verifyChunkedGraph(bucket, entry) {
  validateChunks(GRAPH_PATH, entry);
  const descriptorSha256 = await descriptorKey(entry);
  const receiptKey = 'updates/princeton/verified-chunks/' + descriptorSha256 + '.json';
  const cached = await bucket.get(receiptKey);
  if (cached && cached.size > 2048) await cached.body?.cancel();
  if (cached && cached.size <= 2048) {
    try {
      const bytes = await cached.arrayBuffer();
      if (bytes.byteLength !== cached.size || !cached.checksums?.sha256 || hex(await crypto.subtle.digest('SHA-256', bytes)) !== hex(cached.checksums.sha256)) fail('Invalid verification receipt checksum');
      const receipt = JSON.parse(new TextDecoder().decode(bytes));
      if (receipt.schema === 1 && receipt.descriptorSha256 === descriptorSha256 && receipt.graphSha256 === entry.sha256 && receipt.size === entry.size) {
        for (const chunk of entry.chunks) if (!verifiedObject(await bucket.head('objects/' + chunk.sha256), chunk)) fail('A verified graph chunk is unavailable');
        return {cached: true, descriptorSha256};
      }
    } catch (error) {
      // Missing or invalid objects must not be hidden by a stale receipt.
      if (error.message === 'A verified graph chunk is unavailable') throw error;
    }
  }
  const whole = digestStream(), wholeWriter = whole.getWriter();
  let total = 0;
  try {
    for (const chunk of entry.chunks) {
      const object = await bucket.get('objects/' + chunk.sha256);
      if (!verifiedObject(object, chunk)) { await object?.body?.cancel(); fail('Unverified graph chunk'); }
      const part = digestStream(), partWriter = part.getWriter(), reader = object.body.getReader();
      let count = 0;
      try {
        for (;;) {
          const {done, value} = await reader.read();
          if (done) break;
          count += value.byteLength;
          if (count > chunk.size) fail('Graph chunk exceeds declared size');
          await partWriter.write(value);
          await wholeWriter.write(value);
        }
        await partWriter.close();
        if (count !== chunk.size || hex(await part.digest) !== chunk.sha256) fail('Graph chunk bytes failed verification');
        total += count;
      } catch (error) {
        await reader.cancel(error).catch(() => {});
        await partWriter.abort(error).catch(() => {});
        // Avoid an unhandled rejection from an aborted DigestStream.
        await Promise.resolve(part.digest).catch(() => {});
        throw error;
      } finally { reader.releaseLock(); }
    }
    await wholeWriter.close();
    if (total !== entry.size || hex(await whole.digest) !== entry.sha256) fail('Canonical graph checksum mismatch');
  } catch (error) {
    await wholeWriter.abort(error).catch(() => {});
    await Promise.resolve(whole.digest).catch(() => {});
    throw error;
  }
  const bytes = new TextEncoder().encode(JSON.stringify({schema: 1, descriptorSha256, graphSha256: entry.sha256, size: total}) + '\n');
  const checksum = hex(await crypto.subtle.digest('SHA-256', bytes));
  await bucket.put(receiptKey, bytes, {sha256: checksum, onlyIf: {etagDoesNotMatch: '*'}, httpMetadata: {contentType: 'application/json'}});
  return {cached: false, descriptorSha256};
}

export function chunkParts(entry, range) {
  const start = range?.offset || 0, end = start + (range?.length ?? entry.size);
  return entry.chunks.filter(c => c.offset < end && c.offset + c.size > start).map(chunk => {
    const offset = Math.max(start, chunk.offset) - chunk.offset;
    return {chunk, offset, length: Math.min(end, chunk.offset + chunk.size) - chunk.offset - offset};
  });
}

// Only one body reader exists at once. Pull controls opening subsequent objects;
// disconnecting cancels the active reader and prevents further object fetches.
export function concatenateChunks(bucket, parts) {
  let index = 0, reader = null, count = 0, cancelled = false;
  return new ReadableStream({
    async pull(controller) {
      try {
        while (!cancelled) {
          if (!reader) {
            if (index >= parts.length) { controller.close(); return; }
            const part = parts[index];
            const object = await bucket.get('objects/' + part.chunk.sha256, {range: {offset: part.offset, length: part.length}});
            if (cancelled) { await object?.body?.cancel(); return; }
            if (!verifiedObject(object, part.chunk)) { await object?.body?.cancel(); fail('Graph chunk unavailable'); }
            reader = object.body.getReader(); count = 0;
          }
          const current = reader, {done, value} = await current.read();
          if (cancelled) return;
          if (done) {
            if (count !== parts[index].length) fail('Truncated graph chunk');
            current.releaseLock(); reader = null; index++; continue;
          }
          count += value.byteLength;
          if (count > parts[index].length) fail('Graph chunk exceeds requested range');
          controller.enqueue(value); return;
        }
      } catch (error) {
        if (reader) await reader.cancel(error).catch(() => {});
        if (!cancelled) controller.error(error);
      }
    },
    async cancel(reason) { cancelled = true; if (reader) await reader.cancel(reason).catch(() => {}); }
  }, {highWaterMark: 0});
}
