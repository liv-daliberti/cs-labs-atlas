import {
  GRAPH_PATH,
  validateChunks,
  verifiedObject,
  chunkParts,
  concatenateChunks,
  lengthCheckedBody,
} from './chunked-graph.mjs';
// Reuse the graph's bounded streaming layout for the two growing people exports.
// The graph update API retains its original graph-only descriptor validation.
const chunkedJSONPaths = new Set([
  'data/princeton-students.json',
  'downloads/princeton_students.json',
]);
function validateAtlasChunks(name, entry) {
  if (name === GRAPH_PATH) return validateChunks(name, entry);
  if (/^papers\/[a-f0-9]{64}\.(pdf|xml)$/.test(name))
    return validateChunks(GRAPH_PATH, {
      storage: entry.storage,
      sha256: entry.sha256,
      size: entry.size,
      type: 'application/gzip',
      chunks: entry.chunks,
    });
  if (!chunkedJSONPaths.has(name) || entry.type !== 'application/json; charset=utf-8')
    throw new Error('Unsupported chunked asset');
  validateChunks(GRAPH_PATH, { ...entry, type: 'application/gzip' });
}
const HEX = /^[a-f0-9]{64}$/;
const manifests = new Map();
const paperIndexes = new Map();
const privateHeaders = {
  'Cache-Control': 'private, no-cache',
  'X-Content-Type-Options': 'nosniff',
};
const hex = (value) =>
  [...new Uint8Array(value)].map((x) => x.toString(16).padStart(2, '0')).join('');
const json = (value, status = 200) => Response.json(value, { status, headers: privateHeaders });

// Reading is public. Route wrappers authenticate maintenance requests with
// protectedAtlasUpdate before any object-storage access. No browser-side
// upload control is exposed.
export async function uploadObject(request, env) {
  if (!env.ATLAS_BUCKET) return json({ error: 'Storage unavailable' }, 503);
  const sha = new URL(request.url).pathname.split('/').at(-1);
  if (!HEX.test(sha || '')) return json({ error: 'Invalid object identifier' }, 400);
  const key = 'objects/' + sha;
  const existing = await env.ATLAS_BUCKET.head(key);
  if (existing) {
    if (!existing.checksums?.sha256 || hex(existing.checksums.sha256) !== sha)
      return json({ error: 'Stored checksum mismatch' }, 409);
    const headers = {
      ...privateHeaders,
      'X-Atlas-Sha256': sha,
      'Content-Length': String(existing.size),
    };
    if (request.method === 'HEAD') return new Response(null, { headers });
    if (request.method === 'PUT')
      return json({ sha256: sha, size: existing.size, already_present: true });
  }
  if (request.method === 'HEAD')
    return new Response(null, { status: 404, headers: privateHeaders });
  if (request.method !== 'PUT')
    return new Response(null, { status: 405, headers: { ...privateHeaders, Allow: 'PUT, HEAD' } });
  const length = request.headers.get('Content-Length');
  if (!length || !/^\d+$/.test(length)) return json({ error: 'Content-Length required' }, 411);
  const size = Number(length);
  if (!Number.isSafeInteger(size) || size > 96 * 2 ** 20)
    return json({ error: 'Object too large' }, 413);
  let object;
  try {
    object = await env.ATLAS_BUCKET.put(key, request.body, {
      sha256: sha,
      onlyIf: { etagDoesNotMatch: '*' },
      customMetadata: { sha256: sha },
      httpMetadata: { contentType: 'application/octet-stream' },
    });
  } catch {
    return json({ error: 'Upload or checksum verification failed' }, 400);
  }
  if (!object) object = await env.ATLAS_BUCKET.head(key);
  if (
    !object ||
    object.size !== size ||
    !object.checksums?.sha256 ||
    hex(object.checksums.sha256) !== sha
  )
    return json({ error: 'Upload verification failed' }, 502);
  return json({ sha256: sha, size: object.size, already_present: false }, 201);
}

function resolvePath(pathname, files) {
  let name;
  try {
    name = decodeURIComponent(pathname).replace(/^\/+/, '');
  } catch {
    return null;
  }
  if (
    name.includes('\\') ||
    name.includes('\0') ||
    name.split('/').some((x) => x === '.' || x === '..')
  )
    return null;
  if (!name) name = 'index.html';
  if (Object.hasOwn(files, name)) return name;
  if (name.endsWith('/') && Object.hasOwn(files, name + 'index.html')) return name + 'index.html';
  if (!name.split('/').at(-1).includes('.') && Object.hasOwn(files, name + '.html'))
    return name + '.html';
  return null;
}

async function manifest(env, config) {
  if (!HEX.test(config.manifestSha256 || '') || !env.ATLAS_BUCKET) return null;
  if (manifests.has(config.manifestSha256)) return manifests.get(config.manifestSha256);
  const object = await env.ATLAS_BUCKET.get('objects/' + config.manifestSha256);
  if (!object) return null;
  if (!object.checksums?.sha256 || hex(object.checksums.sha256) !== config.manifestSha256)
    throw new Error('Manifest checksum mismatch');
  const value = await object.json();
  if (value.schema !== 1 || !value.files || typeof value.files !== 'object')
    throw new Error('Invalid atlas manifest');
  // A long-lived isolate must not retain every prior release manifest.
  if (manifests.size >= 8) manifests.delete(manifests.keys().next().value);
  manifests.set(config.manifestSha256, value);
  return value;
}

function byteRange(value, size) {
  const m = /^bytes=(\d*)-(\d*)$/.exec(value);
  if (!m || (!m[1] && !m[2]) || !size) return null;
  const start = m[1] ? Number(m[1]) : Math.max(0, size - Number(m[2]));
  const end = m[1] ? (m[2] ? Math.min(size - 1, Number(m[2])) : size - 1) : size - 1;
  return Number.isSafeInteger(start) &&
    Number.isSafeInteger(end) &&
    start >= 0 &&
    start <= end &&
    start < size
    ? { offset: start, length: end - start + 1 }
    : null;
}

async function indexedPaper(pathname, release, env) {
  const match = /^\/papers\/([a-f0-9]{64})\.(pdf|xml)$/.exec(pathname);
  if (!match) return null;
  // Keep serving admission small as the descriptive reader catalogue grows.
  // Older releases continue to use the original full-index representation.
  const compact = !!release.files['data/reader-objects.json'];
  const indexEntry = release.files[compact ? 'data/reader-objects.json' : 'data/local-papers.json'];
  if (
    !indexEntry ||
    !HEX.test(indexEntry.sha256) ||
    !Number.isSafeInteger(indexEntry.size) ||
    indexEntry.size > 8 * 2 ** 20
  )
    return null;
  let papers = paperIndexes.get(indexEntry.sha256);
  if (!papers) {
    const object = await env.ATLAS_BUCKET.get('objects/' + indexEntry.sha256);
    if (!verifiedObject(object, indexEntry)) throw new Error('Stored-paper index unavailable');
    const data = await object.json();
    if (
      data.schema !== 1 ||
      !(compact ? data.files : data.works) ||
      typeof (compact ? data.files : data.works) !== 'object'
    )
      throw new Error('Invalid stored-paper index');
    papers = new Map();
    const entries = compact
      ? Object.entries(data.files).map(([sha256, bytes]) => ({
          sha256,
          bytes,
          path: 'papers/' + sha256 + '.' + (data.formats?.[sha256] || 'pdf'),
          format: data.formats?.[sha256] || 'pdf',
          chunks: data.chunks?.[sha256],
        }))
      : [...Object.values(data.works), ...Object.values(data.files || {})];
    for (const file of entries) {
      const format = file?.format || 'pdf';
      if (
        !file ||
        !['pdf', 'xml'].includes(format) ||
        !HEX.test(file.sha256 || '') ||
        file.path !== 'papers/' + file.sha256 + '.' + format ||
        !Number.isSafeInteger(file.bytes) ||
        file.bytes < 5 ||
        file.bytes > 512 * 2 ** 20
      )
        continue;
      const previous = papers.get(file.sha256);
      if (previous && previous.size !== file.bytes)
        throw new Error('Conflicting stored-paper metadata');
      const entry = {
        sha256: file.sha256,
        size: file.bytes,
        type: format === 'xml' ? 'application/xml; charset=utf-8' : 'application/pdf',
        format,
      };
      if (file.chunks) {
        entry.storage = 'chunks-v1';
        entry.chunks = file.chunks;
        validateAtlasChunks(file.path, entry);
      } else if (file.bytes > 96 * 2 ** 20) continue;
      papers.set(file.sha256, entry);
    }
    if (paperIndexes.size >= 8) paperIndexes.delete(paperIndexes.keys().next().value);
    paperIndexes.set(indexEntry.sha256, papers);
  }
  const paper = papers.get(match[1]);
  return paper?.format === match[2] ? paper : null;
}

export async function serveAtlas(request, env, config, bootstrap = {}) {
  if (!['GET', 'HEAD'].includes(request.method))
    return new Response(null, { status: 405, headers: { ...privateHeaders, Allow: 'GET, HEAD' } });
  const pathname = new URL(request.url).pathname;
  const bootName = resolvePath(pathname, bootstrap);
  if (bootName) {
    const entry = bootstrap[bootName];
    const headers = {
      ...privateHeaders,
      'Content-Type': entry.type,
      ETag: '"' + entry.sha256 + '"',
    };
    if (request.headers.get('If-None-Match') === headers.ETag)
      return new Response(null, { status: 304, headers });
    if (request.method === 'HEAD')
      return new Response(null, { headers: { ...headers, 'Content-Length': String(entry.size) } });
    const bytes = Uint8Array.from(atob(entry.gzip), (c) => c.charCodeAt(0));
    return new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')), {
      headers,
    });
  }
  const release = await manifest(env, config);
  if (!release)
    return new Response('Atlas data is temporarily unavailable.', {
      status: 503,
      headers: privateHeaders,
    });
  let name = resolvePath(pathname, release.files),
    entry = name ? release.files[name] : null;
  if (!entry) {
    try {
      entry = await indexedPaper(pathname, release, env);
    } catch {
      return new Response('Stored-paper index unavailable', {
        status: 503,
        headers: privateHeaders,
      });
    }
    if (entry) name = pathname.slice(1);
  }
  if (!entry) return new Response('Not found', { status: 404, headers: privateHeaders });
  if (!entry || !HEX.test(entry.sha256) || !Number.isSafeInteger(entry.size) || entry.size < 0)
    return new Response('Invalid asset metadata', { status: 502, headers: privateHeaders });
  const chunked = entry.storage === 'chunks-v1';
  if (chunked) {
    try {
      validateAtlasChunks(name, entry);
    } catch {
      return new Response('Invalid chunked graph metadata', {
        status: 502,
        headers: privateHeaders,
      });
    }
  } else if (entry.storage !== undefined || entry.chunks !== undefined)
    return new Response('Unsupported asset storage', { status: 502, headers: privateHeaders });
  const etag = '"' + entry.sha256 + '"';
  const headers = new Headers({
    ...privateHeaders,
    'Content-Type': entry.type,
    ETag: etag,
    'Accept-Ranges': 'bytes',
  });
  if (entry.format === 'xml')
    headers.set('Content-Disposition', 'attachment; filename="' + name.split('/').at(-1) + '"');
  if (name === GRAPH_PATH) {
    headers.set('Cache-Control', 'private, no-cache, no-transform');
    headers.set('Content-Disposition', 'attachment; filename="princeton-network.json.gz"');
    headers.set('X-Princeton-Graph-Storage', chunked ? 'chunks-v1' : 'direct');
  }
  if (
    request.headers
      .get('If-None-Match')
      ?.split(',')
      .some((x) => x.trim().replace(/^W\//, '') === etag || x.trim() === '*')
  )
    return new Response(null, { status: 304, headers });
  let range;
  const requested = request.headers.get('Range'),
    ifRange = request.headers.get('If-Range');
  if (request.method === 'GET' && requested && (!ifRange || ifRange === etag)) {
    range = byteRange(requested, entry.size);
    if (!range)
      return new Response(null, {
        status: 416,
        headers: { ...Object.fromEntries(headers), 'Content-Range': 'bytes */' + entry.size },
      });
  }
  headers.set('Content-Length', String(range ? range.length : entry.size));
  if (range)
    headers.set(
      'Content-Range',
      `bytes ${range.offset}-${range.offset + range.length - 1}/${entry.size}`,
    );
  if (chunked) {
    const parts = chunkParts(entry, range);
    // At most 16 heads and 16 sequential gets. Fail missing objects before headers.
    for (const part of parts)
      if (!verifiedObject(await env.ATLAS_BUCKET.head('objects/' + part.chunk.sha256), part.chunk))
        return new Response('Graph chunk unavailable', { status: 503, headers: privateHeaders });
    return new Response(
      request.method === 'HEAD'
        ? null
        : lengthCheckedBody(
            concatenateChunks(env.ATLAS_BUCKET, parts),
            range ? range.length : entry.size,
          ),
      { status: range ? 206 : 200, headers },
    );
  }
  const object =
    request.method === 'HEAD'
      ? await env.ATLAS_BUCKET.head('objects/' + entry.sha256)
      : await env.ATLAS_BUCKET.get('objects/' + entry.sha256, range ? { range } : undefined);
  if (!verifiedObject(object, entry))
    return new Response('Atlas asset unavailable', { status: 503, headers: privateHeaders });
  return new Response(request.method === 'HEAD' ? null : object.body, {
    status: range ? 206 : 200,
    headers,
  });
}
