/* data: loaded before app.js; shared atlas state is initialized there. */
'use strict';
async function fetchAsset(path) {
  if (!assetCache.has(path))
    assetCache.set(
      path,
      (async () => {
        if (!DATA.assets[path]) throw new Error('Unrecognized data file');
        const response = await fetch(path, { cache: 'no-cache' });
        if (!response.ok) throw new Error('Request failed (' + response.status + ')');
        const bytes = await response.arrayBuffer();
        if (globalThis.crypto?.subtle) {
          const digest = await crypto.subtle.digest('SHA-256', bytes),
            hash = [...new Uint8Array(digest)].map((v) => v.toString(16).padStart(2, '0')).join('');
          if (hash !== DATA.assets[path]) throw new Error('Dataset changed; reload this page');
        }
        const decoded = path.endsWith('.gz')
          ? await new Response(
              new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')),
            ).text()
          : new TextDecoder().decode(bytes);
        return JSON.parse(decoded);
      })().catch((error) => {
        assetCache.delete(path);
        throw error;
      }),
    );
  return assetCache.get(path);
}

async function ensureUniversity(u) {
  if (u.loaded) return;
  // A school of the CS departments view loads its PI labs (data/cs-pi-labs) instead of its inventory shard.
  const data = await fetchAsset(u.csScope?.labsFile || u.labsFile);
  if (data.id !== u.id) throw new Error('University data mismatch');
  u.labs = data.labs.filter((l) => {
    if (CSScope.shown(l)) return true;
    outOfScope.set(l.id, { name: l.name, uniId: u.id, hidden: l.csHidden || null });
    return false;
  });
  u.metrics = data.metrics;
  u.labs.forEach((l) => {
    l.uniId = u.id;
    labById.set(l.id, l);
  });
  u.loaded = true;
}

async function ensureLab(lab) {
  if (lab.papersLoaded) return;
  if (lab.hierarchy) {
    const detail = CSPILabs.detail(lab, await fetchAsset(lab.hierarchy.file));
    lab.papers = detail.papers;
    Object.assign(DATA.works, detail.works);
    LabMapRecords.setPeople(lab.id, detail.people);
  } else if (lab.papersFile) {
    const data = await fetchAsset(lab.papersFile);
    if (data.labId !== lab.id) throw new Error('Lab data mismatch');
    lab.papers = data.papers;
    Object.assign(DATA.works, data.works);
  } else lab.papers = [];
  lab.papersLoaded = true;
}

async function ensureMetrics() {
  if (!globalMetrics) globalMetrics = await fetchAsset(DATA.metricsFile);
}

async function loadDataset() {
  const response = await fetch('data.json', { cache: 'no-store' });
  window.DatasetUpdates?.observe(response);
  if (!response.ok) throw new Error('Dataset request failed');
  const data = await response.json();
  if (data.bundleFormat !== 'lazy-atlas-v1') throw new Error('Unsupported dataset format');
  applyCSScope(data);
  document.querySelectorAll('a[download][href^="downloads/"]').forEach((a) => {
    const original = a.getAttribute('href').slice(10),
      logical = original.replace(/\.gz$/, ''),
      name = data.downloads?.[original] || data.downloads?.[logical];
    if (name) {
      a.href = 'downloads/' + name;
      const label = a.textContent
        .replace(/\s*[↧↓]/g, '')
        .replace(/\s*·\s*(?:CSV\s*)?gzip\b/gi, '')
        .replace(/\s*·\s*CSV\s*$/i, '')
        .trim();
      a.textContent = label + (name.endsWith('.gz') ? ' · CSV gzip ↧' : ' ↧');
    }
  });
  return data;
}
