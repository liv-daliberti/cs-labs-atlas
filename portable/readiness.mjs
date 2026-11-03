/** Shared readiness check for the Node and hosted storage adapters. */
export async function readiness(bucket, config) {
  const read = async (entry) => {
    const object = await bucket.get('objects/' + entry.sha256);
    if (!object || object.size !== entry.size) throw new Error('Required object unavailable');
    const actual = [...new Uint8Array(object.checksums?.sha256 || [])]
      .map((x) => x.toString(16).padStart(2, '0'))
      .join('');
    if (actual !== entry.sha256) throw new Error('Required checksum unavailable');
    return object;
  };
  const object = await bucket.get('objects/' + config.manifestSha256);
  if (!object) throw new Error('Manifest unavailable');
  const digest = [...new Uint8Array(object.checksums?.sha256 || [])]
    .map((x) => x.toString(16).padStart(2, '0'))
    .join('');
  if (digest !== config.manifestSha256) throw new Error('Manifest checksum mismatch');
  const manifest = await object.json();
  const required = [
    'index.html',
    'cs-departments.html',
    'data.json',
    'data/cs-hierarchy/index.json',
    'data/reader-objects.json',
  ];
  for (const name of required) {
    if (!manifest.files?.[name]) throw new Error('Required asset missing: ' + name);
    await read(manifest.files[name]);
  }
  const schools = await (await read(manifest.files['data/cs-hierarchy/index.json'])).json();
  for (const school of schools.schools || []) {
    const entry = manifest.files['data/cs-hierarchy/' + school.id + '.json.gz'];
    if (!entry) throw new Error('School asset missing');
    await read(entry);
  }
  return { status: 'ready', release: config.release, manifestSha256: config.manifestSha256 };
}
