'use strict';
// Drive the real atlas/app.js against the real data with a stub DOM (no browser is installed here) and check that
// the app shows exactly what scripts/build-cs-scope.py marks as shown (owner decisions 2026-10-21/22): at the CS
// departments' schools their PI labs with lab papers, elsewhere CS units with papers; no shown lab has zero papers;
// every shown lab at those schools is a cs-hierarchy PI lab; counts, stats, hidden notes, trends and annual metrics
// come from the shown labs; a PI lab opens with the papers, students and links of its cs-hierarchy record; deep links
// to hidden or non-CS records show a short note. Run by scripts/test-cs-scope.py; works on Node 16+.
const fs=require('node:fs'),vm=require('node:vm'),zlib=require('node:zlib'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const S=path.resolve(__dirname,'..','atlas');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const DATA_RAW=fs.readFileSync(path.join(S,'data.json'));
const FILE_CACHE=new Map();
function readFile(rel){if(!FILE_CACHE.has(rel))FILE_CACHE.set(rel,fs.readFileSync(path.join(S,rel)));return FILE_CACHE.get(rel);}
function readJSON(rel){const b=readFile(rel);return JSON.parse((rel.endsWith('.gz')?zlib.gunzipSync(b):b).toString('utf8'));}

// ---- minimal DOM ----
class E{
 constructor(tag='div',id=''){this.tagName=String(tag).toUpperCase();this.id=id;this.children=[];this.attrs={};this.dataset={};this.style={setProperty(){}};this.hidden=false;this.value='';this._text='';this.isConnected=true;const cls=new Set();this.classList={add:c=>cls.add(c),remove:c=>cls.delete(c),toggle:(c,on)=>{(on??!cls.has(c))?cls.add(c):cls.delete(c);},contains:c=>cls.has(c)};this.className='';}
 get textContent(){return this._text+this.children.map(c=>typeof c==='string'?c:c.textContent||'').join('');}
 set textContent(t){this._text=String(t??'');this.children=[];}
 get childElementCount(){return this.children.filter(c=>c instanceof E).length;}
 append(...xs){this.children.push(...xs);} appendChild(x){this.children.push(x);return x;}
 insertBefore(x,ref){const i=this.children.indexOf(ref);if(i<0)this.children.push(x);else this.children.splice(i,0,x);return x;}
 replaceChildren(...xs){this._text='';this.children=xs;}
 setAttribute(k,v){this.attrs[k]=String(v);} getAttribute(k){return this.attrs[k]??null;} removeAttribute(k){delete this.attrs[k];}
 addEventListener(){} scrollIntoView(){} focus(){} getBoundingClientRect(){return {width:1000,height:730,left:0,top:0};}
 querySelectorAll(s){const match=e=>s.startsWith('.')?String(e.className||'').split(/\s+/).includes(s.slice(1)):e.tagName===s.toUpperCase();const walk=e=>e.children.filter(x=>x instanceof E).flatMap(x=>[...(match(x)?[x]:[]),...walk(x)]);return walk(this);}
 querySelector(s){return this.querySelectorAll(s)[0]||null;}
}
const all=(e,tag)=>[...(e.tagName===tag?[e]:[]),...e.children.flatMap(x=>x instanceof E?all(x,tag):[])];

// ---- browser API polyfills over node zlib (Node 16 has no fetch / Blob / Response / DecompressionStream) ----
class PDecompressionStream{constructor(kind){this.gzip=kind==='gzip';}}
class PBlob{constructor(parts){this.buf=Buffer.concat(parts.map(p=>Buffer.from(p instanceof ArrayBuffer?new Uint8Array(p):p)));}stream(){const buf=this.buf;return {pipeThrough:ds=>({bytes:ds?.gzip?zlib.gunzipSync(buf):buf})};}}
class PResponse{constructor(body){this.buf=body?.bytes||Buffer.from(body||'');}async text(){return this.buf.toString('utf8');}async json(){return JSON.parse(this.buf.toString('utf8'));}async arrayBuffer(){return this.buf.buffer.slice(this.buf.byteOffset,this.buf.byteOffset+this.buf.length);}}
async function fetchStub(target){
 const rel=String(target).split('?')[0].replace(/^\.\//,'');const file=path.join(S,rel);
 if(!file.startsWith(S)||!fs.existsSync(file))return {ok:false,status:404,headers:{get:()=>null},async json(){throw Error('404 '+rel);},async text(){return '';},async arrayBuffer(){return new ArrayBuffer(0);}};
 const buf=rel==='data.json'?DATA_RAW:readFile(rel);
 return {ok:true,status:200,headers:{get:()=>null},async json(){return JSON.parse(buf.toString('utf8'));},async text(){return buf.toString('utf8');},async arrayBuffer(){return buf.buffer.slice(buf.byteOffset,buf.byteOffset+buf.length);}};
}
async function readResearchJSON(p){for(const rel of p.endsWith('.gz')?[p]:[p,p+'.gz']){if(fs.existsSync(path.join(S,rel)))return readJSON(rel);}throw Error('Could not load '+p);}

const CODE=['assets/d3.min.js','assets/atlas-sizing.js','assets/atlas-affiliations.js','assets/cs-scope.js','assets/advisor-attribution.js','assets/lab-map-records.js','assets/research-unit-kinds.js','assets/cs-pi-labs.js','modules/data.js','modules/metrics.js','modules/map.js','modules/records.js','modules/navigation.js'].map(f=>[f,fs.readFileSync(path.join(S,f),'utf8')]);
const APP=fs.readFileSync(path.join(S,'app.js'),'utf8');assert(/\ninit\(\);\s*$/.test(APP),'app.js must end with init();');
// index.html loads exactly these scripts, in this order, plus three browser-only helpers stubbed below.
{const page=fs.readFileSync(path.join(S,'index.html'),'utf8'),src=[...page.matchAll(/<script[^>]*src="([^"]+)"/g)].map(m=>m[1]);
 assert.deepEqual(src.filter(f=>CODE.some(([c])=>c===f)),CODE.map(([f])=>f),'index.html script order');
 assert.deepEqual(src.filter(f=>!CODE.some(([c])=>c===f)),['assets/dataset-updates.js','research-data.js','assets/paper-reader.js','app.js','assets/publication.js'],'index.html scripts');}

async function boot(search='',hash=''){
 const els=new Map(),get=s=>{if(!els.has(s))els.set(s,new E('div',s.startsWith('#')?s.slice(1):''));return els.get(s);};
 get('#error').hidden=true;get('#scope-note').hidden=true;get('#load-status').hidden=true;
 const tabs=['atlas','trends','coverage'].map(t=>{const b=new E('button');b.className='tab';b.dataset.tab=t;return b;});
 const panels=['atlas','trends','coverage'].map(t=>{const p=get('#'+t+'-panel');p.className='panel';p.hidden=t!=='atlas';return p;});
 const labViews=['both','students','papers'].map(v=>{const b=new E('button');b.dataset.labMapView=v;return b;});
 const document={querySelector:get,querySelectorAll:s=>s==='.tab'?tabs:s==='.panel'?panels:s==='[data-lab-map-view]'?labViews:[],createElement:t=>new E(t),createTextNode:t=>({textContent:String(t)}),addEventListener(){}};
 const ctx={console,URL,URLSearchParams,Intl,Map,Set,Promise,Math,JSON,Date,Number,String,Array,Object,Error,TypeError,RegExp,Symbol,Uint8Array,ArrayBuffer,TextDecoder,TextEncoder,
  Blob:PBlob,Response:PResponse,DecompressionStream:PDecompressionStream,fetch:fetchStub,readResearchJSON,setTimeout,clearTimeout,
  location:{href:'https://atlas.test/'+search+hash,search,hash,pathname:'/'},history:{replaceState(){}},document,
  matchMedia:()=>({matches:false}),requestAnimationFrame:()=>1,cancelAnimationFrame(){},addEventListener(){},getComputedStyle:()=>({}),
  PaperReader:{append(){}},__readAsset:rel=>{const b=readFile(rel);return {digest:sha(b),json:JSON.parse((rel.endsWith('.gz')?zlib.gunzipSync(b):b).toString('utf8'))};}};
 ctx.window=ctx;ctx.globalThis=ctx;vm.createContext(ctx);
 for(const [name,code] of CODE)vm.runInContext(code,ctx,{filename:name});
 vm.runInContext(APP.replace(/\ninit\(\);\s*$/,'\n'),ctx,{filename:'app.js'});
 // The map canvas and charts need a real SVG; record what would be drawn instead. Asset loading keeps its checks:
 // the path must be registered in data.json assets and the bytes must match the recorded sha256.
 vm.runInContext(`paint=(root)=>{globalThis.lastPaint=root;renderedSizing=root.sizing||null;};setupCamera=()=>{};globalThis.charts={};chart=(id,points)=>{charts[id]=points;};
 fetchAsset=async function(path){if(!assetCache.has(path))assetCache.set(path,(async()=>{if(!DATA.assets[path])throw new Error('Unrecognized data file '+path);const r=__readAsset(path);if(r.digest!==DATA.assets[path])throw new Error('Dataset changed: digest mismatch for '+path);return r.json;})().catch(e=>{assetCache.delete(path);throw e;}));return assetCache.get(path);};`,ctx);
 await vm.runInContext('init()',ctx);
 const run=code=>vm.runInContext(code,ctx);
 assert(get('#error').hidden&&!get('#error').textContent,'init failed: '+get('#error').textContent);
 return {ctx,get,run};
}
const fmt=n=>new Intl.NumberFormat('en').format(n);
const same=(a,b,m)=>assert.deepEqual(JSON.parse(JSON.stringify(a)),JSON.parse(JSON.stringify(b)),m); // values cross VM realms

(async()=>{
 const report={};const data=JSON.parse(DATA_RAW);const cs=data.csScope;assert(cs&&cs.rule&&cs.rule.shown&&cs.summary.hidden,'data.json has no csScope shown rule; run scripts/build-cs-scope.py');
 const csUnis=data.universities.filter(u=>u.csScope.labs>0),hiddenOnly=data.universities.filter(u=>!u.csScope.labs),piUnis=csUnis.filter(u=>u.csScope.school);
 const hierarchyOf=u=>readJSON(cs.hierarchy[u.csScope.school].file);
 const hasPapers=l=>['combined','reviewed','strict'].some(v=>Object.values(l.paperCounts?.[v]||{}).reduce((a,b)=>a+b,0)>0);
 assert(piUnis.length===Object.keys(cs.hierarchy).length&&piUnis.length>0,'every CS departments school is in view');
 // ---------- default view: header stats and the totals' hidden note ----------
 const A=await boot();const {get,run}=A;
 assert.equal(run('DATA.universities.length'),csUnis.length,'universities without shown labs must disappear');
 assert.equal(run('activeUniversities.length'),csUnis.length);
 assert.equal(get('#s-unis').textContent,fmt(csUnis.length));
 assert.equal(get('#s-labs').textContent,fmt(cs.summary.labs),'stats row lab count');
 assert.equal(cs.summary.labs,cs.counts.reduce((n,c)=>n+c.n,0));
 assert.equal(get('#s-named').textContent,fmt(cs.counts.reduce((n,c)=>n+c.named,0)));
 assert.equal(get('#s-active').textContent,fmt(cs.counts.reduce((n,c)=>n+c.active,0)));
 assert.equal(get('#s-works').textContent,fmt(cs.overview.combined.stats.works),'stats row works');
 const H0=cs.summary.hidden,hiddenText=get('#hidden-note').textContent;
 assert(!get('#hidden-note').hidden&&hiddenText.includes(fmt(H0.no_papers)+' CS units without papers are not shown')&&hiddenText.includes(fmt(H0.no_lab_papers)+' PI labs without lab papers are not shown')&&hiddenText.includes(fmt(H0.replaced_by_pi_labs)+' earlier inventory units'),'totals hidden note: '+hiddenText);
 report.totalsNote=hiddenText;
 assert(get('#collection-note').textContent.startsWith(fmt(cs.summary.labs)+' computer science labs with papers'),'collection note');
 assert.equal(run('tree.children.length'),csUnis.length,'map root shows only universities with shown labs');
 assert.equal(run('countUnits()'),cs.summary.labs);
 const rootRows=all(get('#list-body'),'TR').filter(r=>r.dataset.id);assert(rootRows.length===20&&rootRows.every(r=>run('uniById.has('+JSON.stringify(r.dataset.id)+')')));
 assert(get('#list-caption').textContent.includes('without papers are not shown'),'root list caption');
 for(const u of hiddenOnly)assert(!run('uniById.has('+JSON.stringify(u.id)+')'),u.id+' has no shown labs and must not be in view');
 get('#search').value='university';run('search()');assert(all(get('#search-results'),'BUTTON').length>0);
 // the country filter narrows the hidden totals too
 {const country='Switzerland',unis=data.universities.filter(u=>u.country===country&&(u.csScope.inScope||u.csScope.piLabs));run("state.country='Switzerland'");await run('refresh()');
  const want=unis.reduce((n,u)=>n+u.csScope.hidden.no_papers,0);assert(!want||get('#hidden-note').textContent.includes(fmt(want)+' CS unit'),'country hidden note');assert.equal(get('#s-labs').textContent,fmt(unis.reduce((n,u)=>n+u.csScope.labs,0)));run("state.country=''");await run('refresh()');}
 // ---------- every university: shown labs, departments, counts, hidden notes ----------
 let labsSeen=0,piLabsSeen=0,inventoryDepartments=0;const perSchool={};
 for(const u of csUnis){
  const id=JSON.stringify(u.id);await run('select('+id+',false)');
  assert.equal(run('state.selected'),u.id,'could not open '+u.id+': '+get('#load-status').textContent);
  const labs=run('uniById.get('+id+').labs');
  assert.equal(labs.length,u.csScope.labs,u.id+' app labs vs csScope.labs');
  assert(labs.every(l=>l.csShown===true&&l.csScope===true),u.id+' shows a lab not marked shown');
  assert(labs.every(l=>l.hierarchy?l.labPapers>0&&Object.values(l.paperCounts.combined).reduce((a,b)=>a+b,0)===l.labPapers:hasPapers(l)),u.id+' shows a lab with zero papers');
  const detailText=get('#detail').textContent;
  if(u.csScope.school){
   // every shown lab is a PI lab of the CS departments view; every PI lab with lab papers is shown
   const H=hierarchyOf(u),ids=new Set(labs.map(l=>l.id));
   for(const l of labs){const hl=H.labs[l.hierarchy.index];assert(l.csScopeReason==='cs_department_pi_lab'&&l.unitType==='pi_lab'&&hl&&hl.id===l.hierarchy.id&&hl.papers.length===l.labPapers&&hl.students.length===l.students&&hl.links.length===l.studentPaperLinks&&hl.dept===l.department&&hl.pi.name===l.pi,u.id+' shown lab is not its hierarchy PI lab: '+l.id);}
   assert.equal(labs.length,H.labs.filter(l=>l.papers.length).length,u.id+' PI labs with papers');
   assert.equal(new Set(labs.map(l=>l.hierarchy.index)).size,labs.length);
   assert.equal(u.csScope.hidden.no_lab_papers,H.labs.filter(l=>!l.papers.length).length);
   assert.equal(u.csScope.piLabs,H.labs.length);
   const shard=readJSON(u.labsFile);assert.equal(u.csScope.hidden.replaced_by_pi_labs,shard.labs.filter(l=>l.csScope).length,u.id+' replaced inventory units');
   assert(shard.labs.every(l=>l.csShown===false&&(l.csScope?l.csHidden==='replaced_by_pi_labs':l.csHidden===null)),u.id+' inventory unit not hidden');
   for(const l of shard.labs)if(!ids.has(l.id))assert(!run('labById.has('+JSON.stringify(l.id)+')'),u.id+' inventory unit reachable: '+l.id);
   // departments: exactly the hierarchy departments with a shown lab, each holding its own labs
   const branches=run('nodeById.get('+id+')').children||[],want=new Map();for(const l of H.labs)if(l.papers.length)want.set(l.dept,(want.get(l.dept)||0)+1);
   assert(branches.every(b=>b.data.kind==='department'),u.id+' PI lab outside a department');
   same(branches.map(b=>[b.data.name,b.leaves().length]).sort(),[...want].sort(),u.id+' department branches');
   for(const b of branches){await run('select('+JSON.stringify(b.data.id)+',false)');const rows=all(get('#list-body'),'TR').filter(r=>r.dataset.id);assert.equal(rows.length,Math.min(20,want.get(b.data.name)),u.id+' department rows '+b.data.name);assert(get('#detail').textContent.includes('PI labs with lab papers'+want.get(b.data.name)),u.id+' department count '+b.data.name);}
   await run('select('+id+',false)');
   assert(detailText.includes('PI labs with lab papers'+fmt(labs.length)),u.id+' detail count');
   if(u.csScope.hidden.no_lab_papers)assert(detailText.includes(fmt(u.csScope.hidden.no_lab_papers)+' PI lab'),u.id+' hidden PI labs note');
   assert(detailText.includes(fmt(u.csScope.hidden.replaced_by_pi_labs)+' earlier inventory unit'),u.id+' replaced note');
   piLabsSeen+=labs.length;perSchool[u.csScope.school]={shown:labs.length,piLabs:u.csScope.piLabs,noLabPapers:u.csScope.hidden.no_lab_papers,inventoryReplaced:u.csScope.hidden.replaced_by_pi_labs,departments:branches.length};
  }else{
   const shard=readJSON(u.labsFile),shown=shard.labs.filter(l=>l.csShown===true);
   same(labs.map(l=>l.id).sort(),shown.map(l=>l.id).sort(),u.id+' shown labs vs csShown');
   assert(shown.every(l=>l.csScope&&hasPapers(l)&&!l.hierarchy));
   assert.equal(u.csScope.hidden.no_papers,shard.labs.filter(l=>l.csScope&&!hasPapers(l)).length,u.id+' hidden count');
   assert.equal(u.csScope.inScope,shard.labs.filter(l=>l.csScope).length);
   for(const l of shard.labs)if(!l.csShown)assert(!run('labById.has('+JSON.stringify(l.id)+')')&&run('outOfScope.has('+JSON.stringify(l.id)+')'),u.id+' hidden lab reachable');
   const n=u.csScope.hidden.no_papers;if(n)assert(detailText.includes(fmt(n)+' CS unit'+(n===1?'':'s')+' without papers'),u.id+' hidden note in detail');
   for(const b of run('nodeById.get('+id+')').children||[]){if(b.data.kind==='department')inventoryDepartments++;assert(b.leaves().every(n=>n.data.record.csShown===true));}
  }
  const want={n:labs.length,named:labs.filter(l=>l.pi).length,reviewed:labs.filter(l=>['leadership_reviewed','publication_identity_verified'].includes(l.leadershipStatus)).length,verified:labs.filter(l=>l.leadershipStatus==='publication_identity_verified').length,active:labs.filter(l=>(l.years||[]).length).length};
  for(const [k,v] of Object.entries(want))assert.equal(run('countUnits(uniById.get('+id+'),'+JSON.stringify(k)+')'),v,u.id+' count '+k);
  const s=run('universitySummary(uniById.get('+id+'))');assert.equal(s.stats.works,u.csScope.overview.combined.stats.works,u.id+' works vs csScope.overview');same(s.annual.map(a=>a.works),u.csScope.overview.combined.annual.map(a=>a.works));same(s.annual.map(a=>a.activity),u.csScope.overview.combined.annual.map(a=>a.activity));
  const rows=all(get('#list-body'),'TR').filter(r=>r.dataset.id);assert.equal(rows.length,Math.min(20,(run('nodeById.get('+id+')').children||[]).length),u.id+' list rows');
  labsSeen+=labs.length;
 }
 report.universities=csUnis.length;report.labsShown=labsSeen;report.piLabsShown=piLabsSeen;report.inventoryDepartmentBranches=inventoryDepartments;report.schools=perSchool;
 assert.equal(labsSeen,cs.summary.labs,'every shown lab is reachable');
 // ---------- a PI lab opens with its papers, students and links ----------
 let opened=0,people=0,papers=0;
 for(const u of piUnis){
  const H=hierarchyOf(u),labs=run('uniById.get('+JSON.stringify(u.id)+').labs');
  const sample=[labs.find(l=>l.studentPaperLinks>0&&l.verifiedStudentPaperLinks>0),labs.find(l=>!l.students),labs.find(l=>l.departmentCoverage!=='full'),labs[labs.length-1]].filter(Boolean);
  for(const l of new Map(sample.map(x=>[x.id,x])).values()){
   await run('select('+JSON.stringify(l.id)+',false)');assert.equal(run('state.selected'),l.id,'PI lab '+l.id+' did not open: '+get('#load-status').textContent);
   const m=run('labMap'),hl=H.labs[l.hierarchy.index];
   assert.equal(m.acceptedCount,hl.papers.length,l.id+' papers');assert.equal(m.papers.length,hl.papers.length,l.id+' paper bubbles');
   assert.equal(m.students.length,hl.students.length+1,l.id+' PI and roster');assert.equal(m.links.length,hl.links.length+hl.papers.length,l.id+' PI and roster links');
   assert.equal(m.verifiedCount,hl.links.filter(k=>k[2]==='v').length+hl.papers.length,l.id+' verified links');
   same(m.papers.map(p=>p.name).sort(),hl.papers.map(p=>H.papers[p[0]].t||'(untitled)').sort(),l.id+' paper titles');
   same(m.students.filter(p=>!p.isPI).map(p=>p.name).sort(),hl.students.map(st=>H.students[st[0]].n).sort(),l.id+' student names');
   assert(m.students.every(p=>p.memberships.length===1&&p.memberships[0].labId===l.id),l.id+' memberships');
   const pi=m.students.find(p=>p.isPI);assert(pi&&pi.kind==='pi'&&pi.name===hl.pi.name&&!pi.isStudent,l.id+' PI node');
   const piLinks=m.links.filter(e=>e.student===pi.id);assert.equal(piLinks.length,m.papers.length,l.id+' PI connects to every accepted paper');
   assert(piLinks.every(e=>e.status==='verified'&&e.authorship.piAuthorship),l.id+' verified PI evidence');
   await run('select('+JSON.stringify(pi.id)+')');assert(get('#detail').textContent.includes('PI / LAB ADVISOR')&&get('#detail').textContent.includes('Paper connections'),l.id+' PI detail');
   await run('select('+JSON.stringify(l.id)+',false)');
   const text=get('#detail').textContent;assert(text.includes('PI lab of a CS department')&&text.includes('Open in CS departments')&&text.includes('Lab papers · 2016–2026'+fmt(l.labPapers)),l.id+' lab detail');
   const listRows=all(get('#list-body'),'TR').filter(r=>r.dataset.id);assert.equal(listRows.length,Math.min(20,m.students.length+m.papers.length),l.id+' list rows');
   if(m.links.length){const e=m.links.find(e=>e.status==='verified')||m.links[0];await run('select('+JSON.stringify(e.paper)+')');assert(get('#detail').textContent.includes('Researcher connections')&&get('#detail').textContent.includes('CS departments lab paper'),l.id+' paper connections');await run('select('+JSON.stringify(e.student)+')');assert(get('#detail').textContent.includes('Paper connections'),l.id+' student connections');}
   // the student and paper views of the same lab
   for(const v of ['students','papers','both']){run('state.labView='+JSON.stringify(v));await run('select('+JSON.stringify(l.id)+',false)');assert.equal(run('lastPaint').children?.length||0,v==='students'?m.students.length:v==='papers'?m.papers.length:m.students.length+m.papers.length,l.id+' '+v+' bubbles');}
   opened++;people+=m.students.length;papers+=m.papers.length;
  }
 }
 // lab maps of CS units elsewhere still open with their papers
 for(const uid of ['stanford-university','eth-zurich','harvard-university','tsinghua-university']){const labs=run('uniById.get('+JSON.stringify(uid)+')?.labs||[]');for(const l of labs.filter(l=>l.papersFile).slice(0,3)){await run('select('+JSON.stringify(l.id)+',false)');assert.equal(run('state.selected'),l.id);assert(run('labMap').acceptedCount>0,l.id+' lab map has no papers');assert(get('#detail').textContent.includes('In the CS atlas through'));opened++;}}
 report.labMapsOpened=opened;report.piLabMapPeople=people;report.piLabMapPapers=papers;
 // ---------- trends, annual metrics and the work-sized map ----------
 await run("select('root',false)");await run("setTab('trends')");
 same(run("charts['#papers-chart']").map(p=>p.value),cs.overview.combined.annual.map(a=>a.works),'trends use annual works of shown labs');
 same(run("charts['#activity-chart']").map(p=>p.value),cs.overview.combined.annual.map(a=>a.activity),'trends use activity of shown labs');
 assert.equal(all(get('#annual-body'),'TR').length,cs.overview.combined.annual.length);
 run("state.sizing='works'");await run('refresh()');assert.equal(run('DATA.metricsFile'),cs.metricsFile);assert(run('globalMetrics')&&run('globalMetrics.buckets.every(b=>b.members.every(m=>m.lab))'));
 const js=run('summarize(globalMetrics)'),py=cs.overview.combined;assert.equal(js.stats.works,py.stats.works,'JS and Python summaries agree');assert.equal(js.stats.publishing,py.stats.publishing);same(js.annual.map(a=>a.works),py.annual.map(a=>a.works));
 const close=(a,b)=>a===null||b===null?a===b:Math.abs(a-b)<1e-9;assert(close(js.stats.oa,py.stats.oa),'open-access share excludes works without an open-access flag');assert(js.annual.every((a,i)=>close(a.oa,py.annual[i].oa)));
 for(const u of piUnis){const q=JSON.stringify(u.id),s=run('summarize({units:globalMetrics.units.filter(c=>c.u==='+q+'),buckets:globalMetrics.buckets.map(b=>({...b,members:b.members.filter(m=>m.uni==='+q+')}))})');assert.equal(s.stats.works,u.csScope.overview.combined.stats.works,u.id+' works from the global metrics');assert.equal(s.stats.oa,null,u.id+' PI-lab papers have no open-access flag');}
 run("state.sizing='units'");await run('refresh()');
 // ---------- coverage: every university with CS units, shown or not, and its hidden counts ----------
 await run("setTab('coverage')");const allCS=data.universities.filter(u=>u.csScope.inScope||u.csScope.piLabs),covRows=all(get('#coverage-body'),'TR');
 assert.equal(covRows.length,allCS.length,'coverage lists every university with CS units');
 for(const r of covRows){const u=allCS.find(x=>x.name===r.children[0].textContent);assert(u,'coverage row '+r.children[0].textContent);assert.equal(r.children[2].textContent,fmt(u.csScope.labs));assert.equal(Boolean(r.dataset.id),u.csScope.labs>0);}
 const cards=get('#coverage-cards').textContent;for(const [label,n] of [['CS units without papers · not shown',H0.no_papers],['PI labs without lab papers · not shown',H0.no_lab_papers],['Earlier inventory units replaced by PI labs',H0.replaced_by_pi_labs],['Computer science labs shown',cs.summary.labs]])assert(cards.includes(fmt(n)+label),'coverage card '+label);
 await run("setTab('organizations')");assert.equal(run('state.tab'),'atlas','only the atlas, trends and coverage tabs exist');
 report.trends={works:js.stats.works,years:js.annual.length};
 // ---------- deep links ----------
 const harvard=data.universities.find(u=>u.id==='harvard-university'),hs=readJSON(harvard.labsFile),noPaper=hs.labs.find(l=>l.csHidden==='no_papers'),nonCS=hs.labs.find(l=>!l.csScope);
 let B=await boot('?university=harvard-university&lab='+encodeURIComponent(noPaper.id));assert(B.get('#scope-note').textContent.includes('no papers are linked to it yet'),'no-paper unit note');assert.equal(B.run('state.selected'),'harvard-university');
 report.deepLinkNoPapers=B.get('#scope-note').textContent;
 B=await boot('?university=harvard-university&lab='+encodeURIComponent(nonCS.id));assert(B.get('#scope-note').textContent.includes('is not in the CS atlas'),'non-CS unit note');
 const pu=piUnis.find(u=>u.csScope.hidden.no_lab_papers),hiddenPI=readJSON(pu.csScope.labsFile).labs.find(l=>!l.csShown);
 B=await boot('?university='+pu.id+'&lab='+encodeURIComponent(hiddenPI.hierarchy.id));assert(B.get('#scope-note').textContent.includes('no lab papers yet'),'hidden PI lab note');
 report.deepLinkHiddenPILab=B.get('#scope-note').textContent;
 // the links cs-departments.html writes (./?university=<uni>&lab=<hierarchy id>) open the PI lab
 for(const u of piUnis){const H=hierarchyOf(u),lab=H.labs.find(l=>l.papers.length&&l.students.length);B=await boot('?university='+u.id+'&lab='+encodeURIComponent(lab.id));assert.equal(B.run('state.selected'),lab.id,u.id+' cs-departments link');assert(B.get('#scope-note').hidden);}
 const hiddenUni=hiddenOnly.find(u=>u.csScope.inScope),noCSUni=hiddenOnly.find(u=>!u.csScope.inScope);
 B=await boot('?university='+hiddenUni.id);assert(B.get('#scope-note').textContent.includes(fmt(hiddenUni.csScope.hidden.no_papers)+' CS unit')&&B.get('#scope-note').textContent.includes('without papers'),'university without shown labs note: '+B.get('#scope-note').textContent);report.deepLinkUniversityWithoutShownLabs=B.get('#scope-note').textContent;assert.equal(B.run('state.selected'),'root');
 if(noCSUni){B=await boot('?university='+noCSUni.id);assert(B.get('#scope-note').textContent.includes('no computer science units are recorded there'));}
 B=await boot('?university=princeton-university&department=Chemistry');assert(B.get('#scope-note').textContent.includes('is not a computer science department'),'non-CS department note');assert.equal(B.run('state.selected'),'princeton-university');
 B=await boot('?university=princeton-university&department=Computer%20Science&view=combined');assert.equal(B.run('state.selected'),'princeton-university::Computer Science');assert(B.get('#scope-note').hidden);
 const csRows=all(B.get('#list-body'),'TR').filter(r=>r.dataset.id);assert(csRows.length&&csRows.every(r=>B.run('labById.get('+JSON.stringify(r.dataset.id)+')?.hierarchy?.school')==='princeton'),'Princeton CS list rows are PI labs');
 B=await boot('','#organizations');assert.equal(B.run('state.tab'),'atlas');
 B=await boot('','#coverage');assert.equal(B.run('state.tab'),'coverage');
 console.log(JSON.stringify({passed:true,...report},null,1));
})().catch(e=>{console.error(e);process.exit(1);});
