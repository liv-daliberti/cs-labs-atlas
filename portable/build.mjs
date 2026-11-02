import { cp, mkdir, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const output = path.join(root, 'dist');
await rm(output, { recursive: true, force: true });
for (const filename of [
  'portable/server.mjs',
  'portable/file-bucket.mjs',
  'lib/atlas-storage.mjs',
  'lib/chunked-graph.mjs',
]) {
  await mkdir(path.dirname(path.join(output, filename)), { recursive: true });
  await cp(path.join(root, filename), path.join(output, filename));
}
await writeFile(
  path.join(output, 'package.json'),
  JSON.stringify({ private: true, type: 'module', engines: { node: '>=22.13.0' } }) + '\n',
);
console.log('Built dist/: dependency-free Node server. Supply ATLAS_DATA_DIR at runtime.');
