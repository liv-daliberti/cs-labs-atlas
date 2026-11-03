import { createServer } from 'node:http';
import { readFile, realpath } from 'node:fs/promises';
import path from 'node:path';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { fileURLToPath } from 'node:url';
import { serveAtlas } from '../lib/atlas-storage.mjs';
import { readiness } from './readiness.mjs';
import { FileBucket } from './file-bucket.mjs';

/** Node equivalent of workerd's bounded stream; no buffering of entire papers. */
export class FixedLengthStream extends TransformStream {
  constructor(expected) {
    let bytes = 0;
    super({
      transform(chunk, controller) {
        bytes += chunk.byteLength;
        if (bytes > expected) throw new Error('Response exceeds declared length');
        controller.enqueue(chunk);
      },
      flush() {
        if (bytes !== expected) throw new Error('Response shorter than declared length');
      },
    });
  }
}

export async function createAtlasServer(dataDirectory, { onError = console.error } = {}) {
  globalThis.FixedLengthStream ??= FixedLengthStream;
  const directory = await realpath(dataDirectory);
  const config = JSON.parse(await readFile(path.join(directory, 'config.json'), 'utf8'));
  if (config.schema !== 1 || !/^[a-f0-9]{64}$/.test(config.manifestSha256)) {
    throw new Error('Invalid publication bundle configuration');
  }
  const bucket = new FileBucket(path.join(directory, 'objects'));
  if (!(await bucket.head('objects/' + config.manifestSha256)))
    throw new Error('Publication manifest is missing');

  return createServer(async (incoming, outgoing) => {
    try {
      const started = performance.now();
      const url = new URL(incoming.url, 'http://localhost');
      outgoing.on('finish', () => {
        if (process.env.ATLAS_ACCESS_LOG === '1')
          console.log(
            JSON.stringify({
              event: 'request',
              method: incoming.method,
              path: url.pathname,
              status: outgoing.statusCode,
              durationMs: Math.round(performance.now() - started),
            }),
          );
      });
      let response;
      if (url.pathname.startsWith('/api/')) {
        // Portable publications are read-only. Deploy a new bundle to update.
        response = new Response('Not found', { status: 404 });
      } else if (url.pathname === '/readyz') {
        if (!['GET', 'HEAD'].includes(incoming.method))
          response = new Response(null, { status: 405 });
        else {
          const state = await readiness(bucket, config);
          response = new Response(incoming.method === 'HEAD' ? null : JSON.stringify(state), {
            headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
          });
        }
      } else if (url.pathname === '/healthz') {
        response = new Response(
          incoming.method === 'HEAD'
            ? null
            : JSON.stringify({ status: 'ok', release: config.release }),
          {
            status: ['GET', 'HEAD'].includes(incoming.method) ? 200 : 405,
            headers: { 'Content-Type': 'application/json' },
          },
        );
      } else {
        const request = new Request(url, { method: incoming.method, headers: incoming.headers });
        response = await serveAtlas(request, { ATLAS_BUCKET: bucket }, config);
      }
      response.headers.set('X-Content-Type-Options', 'nosniff');
      response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
      outgoing.writeHead(response.status, Object.fromEntries(response.headers));
      if (response.body && incoming.method !== 'HEAD')
        await pipeline(Readable.fromWeb(response.body), outgoing);
      else outgoing.end();
    } catch (error) {
      onError('Atlas request failed: ' + error.message);
      if (!outgoing.headersSent)
        outgoing.writeHead(503, { 'Content-Type': 'text/plain', 'Cache-Control': 'no-store' });
      if (outgoing.headersSent && outgoing.statusCode !== 503) outgoing.destroy();
      else outgoing.end('Atlas data is temporarily unavailable.');
    }
  });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const directory = process.env.ATLAS_DATA_DIR || process.argv[2];
  if (!directory) throw new Error('Set ATLAS_DATA_DIR to a publication bundle (see README).');
  const port = Number(process.env.PORT || 8787);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid PORT');
  const host = process.env.HOST || '127.0.0.1';
  const server = await createAtlasServer(directory);
  server.listen(port, host, () => console.log(`Atlas listening on http://${host}:${port}`));
  for (const signal of ['SIGINT', 'SIGTERM']) {
    process.on(signal, () => server.close(() => process.exit(0)));
  }
}
