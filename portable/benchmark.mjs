import { writeFile, mkdir } from 'node:fs/promises';
const origin = process.argv[2] || 'http://127.0.0.1:8787';
async function measure(path) {
  const start = performance.now();
  const r = await fetch(new URL(path, origin), { signal: AbortSignal.timeout(60000) });
  let bytes = 0;
  for await (const b of r.body) bytes += b.length;
  return { path, status: r.status, bytes, milliseconds: Math.round(performance.now() - start) };
}
const index = await (await fetch(new URL('/data/reader-objects.json', origin))).json();
const paper =
  Object.keys(index.files).find((k) => index.files[k] > 2 ** 20) || Object.keys(index.files)[0];
const paths = [
  '/',
  '/data.json',
  ...(paper ? ['/papers/' + paper + '.' + (index.formats?.[paper] || 'pdf')] : []),
];
const report = { origin, at: new Date().toISOString(), first: [], warm: [], concurrent: [] };
for (const p of paths) {
  report.first.push(await measure(p));
  report.warm.push(await measure(p));
}
report.concurrent = await Promise.all(Array.from({ length: 8 }, () => measure(paths.at(-1))));
await mkdir('outputs', { recursive: true });
await writeFile('outputs/performance.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
