import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { lstat, readFile } from 'node:fs/promises';
import path from 'node:path';
import { Readable } from 'node:stream';

const OBJECT_KEY = /^objects\/([a-f0-9]{64})$/;

/** Read-only adapter for the same immutable objects served by the R2 backend. */
export class FileBucket {
  #directory;
  #verified = new Map();

  constructor(directory) {
    this.#directory = path.resolve(directory);
  }

  async head(key) {
    const match = OBJECT_KEY.exec(key);
    if (!match) return null;
    const filename = path.join(this.#directory, match[1]);
    let stat;
    try {
      stat = await lstat(filename);
    } catch (error) {
      if (error.code === 'ENOENT') return null;
      throw error;
    }
    // A bundle must not follow links into unrelated files on the host.
    if (!stat.isFile()) throw new Error('Object is not a regular file');
    const signature = `${stat.dev}:${stat.ino}:${stat.size}:${stat.mtimeMs}:${stat.ctimeMs}`;
    if (this.#verified.get(key) !== signature) {
      const hash = createHash('sha256');
      for await (const chunk of createReadStream(filename)) hash.update(chunk);
      if (hash.digest('hex') !== match[1]) throw new Error('Object checksum mismatch');
      // Bound metadata even when a public crawler walks the entire library.
      if (this.#verified.size >= 4096) this.#verified.delete(this.#verified.keys().next().value);
      this.#verified.set(key, signature);
    }
    return {
      size: stat.size,
      checksums: { sha256: Uint8Array.from(Buffer.from(match[1], 'hex')).buffer },
    };
  }

  async get(key, options = {}) {
    const metadata = await this.head(key);
    if (!metadata) return null;
    const filename = path.join(this.#directory, OBJECT_KEY.exec(key)[1]);
    const range = options.range;
    const streamOptions = range
      ? { start: range.offset, end: range.offset + range.length - 1 }
      : {};
    return {
      ...metadata,
      // Create a stream only when the caller uses the body. JSON metadata reads
      // should not leave an unused open stream/file descriptor behind.
      get body() {
        return Readable.toWeb(createReadStream(filename, streamOptions));
      },
      async json() {
        return JSON.parse(await readFile(filename, 'utf8'));
      },
    };
  }
}
