import { createHash } from 'node:crypto';
import { pathToFileURL } from 'node:url';
export async function smoke(origin, expectedManifest) {
  const get = async (path) => {
    const response = await fetch(new URL(path, origin), {
      signal: AbortSignal.timeout(30000),
      redirect: 'error',
    });
    if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
    return response;
  };
  const ready = await (await get('/readyz')).json();
  if (expectedManifest && ready.manifestSha256 !== expectedManifest)
    throw new Error('Wrong deployed release');
  for (const path of ['/', '/cs-departments.html', '/data.json', '/data/cs-hierarchy/index.json'])
    await (await get(path)).arrayBuffer();
  const index = await (await get('/data/reader-objects.json')).json();
  const first = Object.keys(index.files)[0];
  if (first) {
    const response = await get('/papers/' + first + '.' + (index.formats?.[first] || 'pdf'));
    const hash = createHash('sha256');
    let bytes = 0;
    for await (const part of response.body) {
      bytes += part.length;
      hash.update(part);
    }
    if (hash.digest('hex') !== first || bytes !== index.files[first])
      throw new Error('Paper smoke checksum failed');
  }
  const maintenance = await fetch(new URL('/api/atlas-storage/' + '0'.repeat(64), origin), {
    method: 'HEAD',
    redirect: 'error',
  });
  if (![401, 403, 404].includes(maintenance.status))
    throw new Error('Maintenance endpoint is publicly accessible');
  return ready;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  console.log(
    JSON.stringify(await smoke(process.argv[2] || 'http://127.0.0.1:8787', process.argv[3])),
  );
}
