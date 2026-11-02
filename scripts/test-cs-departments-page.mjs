// Drive atlas/cs-departments.js against the built data with a minimal DOM stub (no browser is installed here):
// every school loads, departments filter the labs, search narrows them, a lab opens with its papers, students and
// links, a student filters the papers, and the URL keeps school/dept/lab. PI labs without lab papers are never listed or
// opened (owner 2026-10-22, "PI labs with papers only"), and each one has a recorded reason in cs-hierarchy/hidden-labs.json.
import fs from 'node:fs'; import zlib from 'node:zlib'; import vm from 'node:vm'; import path from 'node:path';
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..', 'atlas');
const els = new Map(); let url = '';
const attrs = s => Object.fromEntries([...s.matchAll(/data-([a-z]+)="([^"]*)"/g)].map(m => [m[1], m[2].replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>')]));
function el(id) {
  if (!els.has(id)) els.set(id, { id, innerHTML: '', textContent: '', hidden: false, value: '', _q: {},
    setAttribute() {}, scrollIntoView() {},
    querySelectorAll(sel) {
      const re = sel === 'tr[data-i]' ? /<tr data-i="[^"]*"[^>]*>/g : sel === '[data-school]' ? /<button[^>]*data-school="[^"]*"[^>]*>/g :
        sel === '[data-reader]' ? /<div[^>]*data-reader="[^"]*"[^>]*>/g : sel === '[data-abstract]' ? /<details[^>]*data-abstract="[^"]*"[^>]*>/g : sel === '[data-st]' ? /<button[^>]*data-st="[^"]*"[^>]*>/g : sel === 'button' ? /<button[^>]*>/g : null;
      if (!re) throw Error('selector not stubbed: ' + sel);
      const out = [...this.innerHTML.matchAll(re)].map(m => ({ dataset: attrs(m[0]), setAttribute() {}, onclick: null, onkeydown: null, open: false, body: {textContent:'',innerHTML:''}, querySelector() {return this.body;} }));
      this._q[sel] = out; return out; } });
  return els.get(id);
}
const ctx = { console, URLSearchParams, setTimeout, Promise,
  location: { get search() { return url; } }, history: { replaceState(_, __, u) { url = u; } },
  document: { getElementById: el }, fetch: null,
  PaperReader: {append(box,work){box.readerWork=work;}} };
ctx.window = ctx;
ctx.readResearchJSON = async p => { const b = fs.readFileSync(path.join(root, p)); return JSON.parse(p.endsWith('.gz') ? zlib.gunzipSync(b) : b); };
vm.createContext(ctx); vm.runInContext(fs.readFileSync(path.join(root, 'cs-departments.js'), 'utf8'), ctx);
const tick = () => new Promise(r => setTimeout(r, 30));
const assert = (c, m) => { if (!c) { console.error('FAIL:', m); process.exit(1); } };
for (let i = 0; i < 100 && !ctx.CSDepartments; i++) await tick();
assert(ctx.CSDepartments, 'page did not initialise: ' + el('csd-error').textContent);
const index = ctx.CSDepartments.getIndex(); const report = {};
const hiddenFile = JSON.parse(fs.readFileSync(path.join(root, index.hiddenLabsFile), 'utf8'));
for (const s of index.schools) {
  const tab = el('csd-schools')._q['[data-school]'].find(b => b.dataset.school === s.id); assert(tab, 'no tab for ' + s.id);
  tab.onclick(); for (let i = 0; i < 100 && ctx.CSDepartments.getData()?.school.id !== s.id; i++) await tick(); await tick();
  const data = ctx.CSDepartments.getData(); assert(data.school.id === s.id, 'school did not load ' + s.id);
  const rows = el('csd-rows')._q['tr[data-i]']; const listed = data.labs.filter(l => l.papers.length).length;
  assert(rows.length === listed, s.id + ' all-department rows ' + rows.length + ' != labs with papers ' + listed);
  assert(rows.every(r => data.labs[+r.dataset.i].papers.length > 0), s.id + ' a lab without lab papers is listed');
  const hidden = data.labs.map((l, i) => [l, i]).filter(([l]) => !l.papers.length);
  const recorded = hiddenFile.schools[s.id] || [];
  assert(hidden.length === recorded.length && hidden.length === s.hiddenLabs && hidden.every(([l, i]) => recorded.some(r => r.index === i && r.id === l.id && r.category && r.reason)),
    s.id + ' hidden labs and their recorded reasons differ');
  assert(el('csd-stats').innerHTML.includes('<strong>' + listed.toLocaleString('en-US') + '</strong><span>PI labs with lab papers'), s.id + ' stats count listed labs');
  const dept = data.departments[0];
  el('csd-dept-list')._q['button'].find(b => b.dataset.dept === dept.name).onclick();
  const drows = el('csd-rows')._q['tr[data-i]']; assert(drows.length >= dept.labs.filter(i => data.labs[i].papers.length).length, s.id + ' department rows');
  assert(url.includes('dept='), 'dept not in URL');
  const full = data.labs.findIndex(l => l.papers.length && l.students.length && l.links.length);
  const row = drows.find(r => +r.dataset.i === full) || el('csd-rows')._q['tr[data-i]'][0];
  el('csd-dept-list')._q['button'].find(b => b.dataset.dept === '').onclick();
  el('csd-rows')._q['tr[data-i]'].find(r => +r.dataset.i === full).onclick();
  const lab = data.labs[full]; const html = el('csd-lab').innerHTML;
  assert(!el('csd-lab').hidden && html.includes('Lab papers (' + lab.papers.length.toLocaleString('en-US')), s.id + ' lab panel papers');
  assert(html.includes('Students and lab members (' + lab.students.length.toLocaleString('en-US')), s.id + ' lab panel students');
  const readers=el('csd-lab')._q['[data-reader]'];
  assert(readers.length===Math.min(60,lab.papers.length),s.id+' reader controls for visible papers');
  assert(readers.every(box=>{const p=data.papers[+box.dataset.reader];return box.readerWork.id===(p.w||p.oa)&&box.readerWork.doi===p.doi;}),s.id+' reader controls use exact work identifiers');
  assert(url.includes('lab=' + encodeURIComponent(lab.id).replace(/%20/g, '+')) || url.includes('lab='), 'lab not in URL');
  const st = el('csd-lab')._q['[data-st]'].find(b => lab.links.some(k => k[0] === +b.dataset.st));
  st.onclick(); const filtered = el('csd-lab').innerHTML; const n = new Set(lab.links.filter(k => k[0] === +st.dataset.st).map(k => k[1])).size;
  assert(filtered.includes('Lab papers (' + n.toLocaleString('en-US') + ' with '), s.id + ' student filter count ' + n);
  el('csd-search').oninput({ target: { value: data.students[lab.students[0][0]].n } });
  assert(el('csd-rows')._q['tr[data-i]'].some(r => +r.dataset.i === full), s.id + ' search by student keeps the lab');
  el('csd-search').oninput({ target: { value: '' } });
  for (const d of el('csd-dept-list')._q['button'].filter(b => b.dataset.dept)) {  // every listed department has a listed lab
    d.onclick(); const r = el('csd-rows')._q['tr[data-i]'];
    assert(r.length > 0 && r.every(x => data.labs[+x.dataset.i].papers.length > 0), s.id + ' department ' + d.dataset.dept + ' rows');
  }
  el('csd-dept-list')._q['button'].find(b => b.dataset.dept === '').onclick();
  for (const [l, i] of hidden) {  // opening a hidden lab (a stale link or row) shows nothing
    el('csd-lab').hidden = true; ctx.CSDepartments.openLab(i, false);
    assert(el('csd-lab').hidden, s.id + ' hidden lab opened ' + l.name);
  }
  const abstractLab = data.labs.findIndex(l => l.papers.some(([i]) => data.papers[i].abstractFile));
  let abstractsChecked = 0;
  if (abstractLab >= 0) {
    ctx.CSDepartments.openLab(abstractLab, false);
    const disclosure = el('csd-lab')._q['[data-abstract]'][0];
    assert(disclosure, s.id + ' abstract disclosure missing');
    disclosure.open = true; await disclosure.ontoggle();
    assert(disclosure.dataset.loaded === 'true' && disclosure.body.innerHTML.includes('OpenAlex source'), s.id + ' abstract failed to load');
    abstractsChecked++;
  }
  report[s.id] = { abstractsChecked, labs: rows.length, hidden: hidden.length, hiddenCategories: [...new Set(recorded.map(r => r.category))], firstDept: dept.name, openedLab: lab.name, papers: lab.papers.length, students: lab.students.length };
}
// a deep link to a hidden lab loads the school without opening it, and says why
const h = Object.entries(hiddenFile.schools).find(([, r]) => r.length);
if (h) {
  url = '?school=' + h[0] + '&lab=' + encodeURIComponent(h[1][0].id);
  els.clear(); delete ctx.CSDepartments;
  vm.runInContext(fs.readFileSync(path.join(root, 'cs-departments.js'), 'utf8'), ctx);
  for (let i = 0; i < 100 && !ctx.CSDepartments; i++) await tick(); await tick();
  assert(el('csd-lab').hidden && !url.includes('lab='), 'deep link to a hidden lab opened it: ' + url);
  assert(el('csd-count').textContent.includes('is not listed: it has no lab papers'), 'deep link to a hidden lab: ' + el('csd-count').textContent);
  report.deepLinkHiddenLab = el('csd-count').textContent;
}
console.log(JSON.stringify({ passed: true, schools: index.schools.length, report }, null, 1));
