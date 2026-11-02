'use strict';
const $=s=>document.querySelector(s),fmt=n=>new Intl.NumberFormat('en').format(n),el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x;};
const COLORS={biological_and_health_sciences:'#58c6b1',social_sciences:'#bd91ce',physical_sciences:'#89a7ed',mathematics_and_statistics:'#89a7ed',chemical_sciences:'#89a7ed',engineering_and_technology:'#d3b27d',computer_and_information_sciences:'#d3b27d',earth_and_environmental_sciences:'#618f81',agricultural_and_veterinary_sciences:'#79a887',interdisciplinary:'#839ba8'};
const state={country:'',field:'',leadership:'',view:'combined',sizing:'units',from:2016,to:2026,tab:'atlas',selected:'root',page:0,labView:'both',unitKind:''};
let cameraZoom,nodeLayer,labelCandidates,cameraFrame=0,renderedSizing=null;
const camera={transform:d3.zoomIdentity,angle:0};
let DATA,uniById,labById,nodeById,tree,focus,currentView,nodes,labels,visibleLabs=[],activeUniversities=[];
let expandedUniversity=null, navigation=0, globalMetrics=null, refreshVersion=0;
const assetCache=new Map();
let labMap=null,mapRecords=new Map(),authorshipLines,nodeIcons,selectedMapRecord=null;
// Computer-science scope (owner requests 2026-10-21 and 2026-10-22). scripts/build-cs-scope.py marks every lab
// (csScope; csShown: the CS departments' PI labs with lab papers at their schools, CS units with papers elsewhere)
// and writes counts, summaries and metrics over exactly the shown labs; the app reads only those. Hidden records
// stay in the data and are not shown.
const CS_COLORS={field:'#d3b27d',department:'#89a7ed'};
const outOfScope=new Map();let outOfScopeUniversities=new Map();
const CS_REASON_LABELS={field:'Field: computer and information sciences',department:'Computing department',field_and_department:'Field and computing department',cs_department_pi_lab:'PI lab of a CS department'};
const PI_SCHOOL_NAMES={princeton:'Princeton',cmu:'CMU',epfl:'EPFL',mit:'MIT',berkeley:'Berkeley',stanford:'Stanford'};
const plural=(n,one,many)=>fmt(n)+' '+(n===1?one:many);
function scopeNote(text){const box=$('#scope-note');if(!box)return;box.textContent=text||'';box.hidden=!text;}
function applyCSScope(data){
 const cs=data.csScope;if(!cs?.rule||!cs.counts||!cs.overview||!cs.metricsFile)throw new Error('The CS scope is missing from this dataset; run scripts/build-cs-scope.py');
 CSScope.configure(cs.rule);AtlasAffiliations.setLabelFilter(CSScope.departmentLabels);
 const empty={stats:{works:0,publishing:0,groupLinks:0,oa:null,meanAuthors:null,topicCount:0,entropy:null,international:null,hhi:null},annual:[]};
 for(const u of data.universities){u.counts=u.csScope?.counts||[];u.overview=u.csScope?.overview||{combined:empty,reviewed:empty,strict:empty};}
 outOfScopeUniversities=new Map(data.universities.filter(u=>!u.csScope?.labs).map(u=>[u.id,u]));
 data.universities=data.universities.filter(u=>u.csScope?.labs>0);data.counts=cs.counts;data.overview=cs.overview;data.metricsFile=cs.metricsFile;
 return data;
}
// "N units without papers are not shown" (owner decision 2026-10-22), per university and in the totals.
function hiddenCounts(unis){const h={no_papers:0,no_lab_papers:0,replaced_by_pi_labs:0};for(const u of unis)for(const k of Object.keys(h))h[k]+=u.csScope?.hidden?.[k]||0;return h;}
function piSchoolNames(){const ids=Object.keys(DATA.csScope.hierarchy||{}).map(id=>PI_SCHOOL_NAMES[id]||id);return ids.length>1?ids.slice(0,-1).join(', ')+' and '+ids[ids.length-1]:ids.join('');}
function hiddenNote(h,oneSchool=false){const parts=[];
 if(h.no_papers)parts.push(plural(h.no_papers,'CS unit','CS units')+' without papers '+(h.no_papers===1?'is':'are')+' not shown');
 if(h.no_lab_papers)parts.push(plural(h.no_lab_papers,'PI lab','PI labs')+' without lab papers '+(h.no_lab_papers===1?'is':'are')+' not shown');
 if(h.replaced_by_pi_labs)parts.push(plural(h.replaced_by_pi_labs,'earlier inventory unit','earlier inventory units')+(oneSchool?'':' at '+piSchoolNames())+' '+(h.replaced_by_pi_labs===1?'is':'are')+' replaced by the CS departments’ PI labs');
 return parts.join(' · ');}
function hiddenShort(u){const h=u.csScope?.hidden||{},parts=[];if(h.no_papers)parts.push(fmt(h.no_papers)+' without papers');if(h.no_lab_papers)parts.push(plural(h.no_lab_papers,'PI lab','PI labs')+' without lab papers');if(h.replaced_by_pi_labs)parts.push(fmt(h.replaced_by_pi_labs)+' inventory units replaced');return parts.join(' · ');}
function allCSUniversities(){return [...DATA.universities,...outOfScopeUniversities.values()].filter(u=>u.csScope?.inScope||u.csScope?.piLabs);}
function hiddenTotals(){return hiddenCounts(allCSUniversities().filter(u=>!state.country||u.country===state.country));}
function csDepartmentsLink(u,query=''){const a=el('a','Open in CS departments →','aside-button');a.href='cs-departments.html?school='+encodeURIComponent(u.csScope.school)+query;return a;}
function labelField(v){return (v||'Unclassified').replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());}
function safeLink(url,text){const a=el('a',text);try{const u=new URL(url);if(['http:','https:'].includes(u.protocol)){a.href=u.href;a.target='_blank';a.rel='noopener';}}catch{}return a;}

function accepted(lab){return (lab.papers||[]).filter(p=>p[state.view]&&DATA.works[p.work]&&DATA.works[p.work].year>=state.from&&DATA.works[p.work].year<=state.to);}
function labCount(lab){return Object.entries(lab.paperCounts?.[state.view]||{}).reduce((n,[y,v])=>n+(+y>=state.from&&+y<=state.to?v:0),0);}
function matches(field,status,uid){return (!state.field||field===state.field)&&(!state.leadership||status===state.leadership)&&(!state.country||uniById.get(uid)?.country===state.country);}
function countCells(u,unfiltered=false){return (u?.counts||DATA.counts).filter(c=>unfiltered||matches(c.field,c.status,c.u));}
function countUnits(u,key='n',unfiltered=false){return d3.sum(countCells(u,unfiltered),c=>c[key]||0);}
function relevantLabs(u){return (u.labs||[]).filter(l=>matches(l.field,l.leadershipStatus,u.id));}
function filteredUniversities(){return DATA.universities.filter(u=>!state.country||u.country===state.country).filter(u=>(!state.field&&!state.leadership)||countUnits(u));}
function isDefaultScope(){return !state.country&&!state.field&&!state.leadership&&state.from===2016&&state.to===2026;}
// Works without an open-access flag (oaUnknown: CS departments PI-lab papers) are left out of the open-access share,
// as in scripts/lazy_atlas.py summarize_metrics.
function summarize(metrics,allowed=null,labs=null){
 const years=new Map();for(let y=state.from;y<=state.to;y++)years.set(y,{year:y,activity:0,publishing:0,works:0,links:0,oa:null,oaCount:0,oaUnknown:0,groups:new Set()});
 if(labs){for(const l of labs)for(const y of l.years)if(years.has(y))years.get(y).activity++;}
 else for(const c of metrics.units)if(matches(c.field,c.status,c.u))for(const [y,n] of Object.entries(c.years))if(years.has(+y))years.get(+y).activity+=n;
 const totals={works:0,oa:0,oaUnknown:0,authorsKnown:0,authorsSum:0,countriesKnown:0,international:0},topics=new Map(),groups=new Set(),labCounts=new Map();let groupLinks=0;
 for(const b of metrics.buckets){
  if(b.view!==state.view)continue;
  const members=b.members.filter(m=>matches(m.field,m.status,m.uni)&&(!allowed||allowed.has(m.lab)));if(!members.length)continue;
  const gids=new Set(members.flatMap(m=>m.groups)),lids=new Set(members.map(m=>m.lab));
  for(const [y,v] of Object.entries(b.years)){
   const a=years.get(+y);if(!a||!v.works)continue;
   for(const k of Object.keys(totals))totals[k]+=v[k]||0;
   for(const [topic,n] of Object.entries(v.topics))topics.set(topic,(topics.get(topic)||0)+n);
   gids.forEach(g=>{groups.add(g);a.groups.add(g);});groupLinks+=v.works*gids.size;
   lids.forEach(l=>labCounts.set(l,(labCounts.get(l)||0)+v.works));
   a.works+=v.works;a.links+=v.works*lids.size;a.oaCount+=v.oa;a.oaUnknown+=v.oaUnknown||0;
  }
 }
 const topicTotal=d3.sum(topics.values()),links=d3.sum(labCounts.values());
 const stats={works:totals.works,publishing:groups.size,groupLinks,oa:totals.works-totals.oaUnknown?totals.oa/(totals.works-totals.oaUnknown):null,meanAuthors:totals.authorsKnown?totals.authorsSum/totals.authorsKnown:null,topicCount:topics.size,entropy:topicTotal?-d3.sum(topics.values(),n=>n/topicTotal*Math.log2(n/topicTotal)):null,international:totals.countriesKnown?totals.international/totals.countriesKnown:null,hhi:links?d3.sum(labCounts.values(),n=>(n/links)**2):null};
 return {stats,annual:[...years.values()].map(a=>({year:a.year,activity:a.activity,publishing:a.groups.size,works:a.works,links:a.links,oa:a.works-a.oaUnknown?a.oaCount/(a.works-a.oaUnknown):null}))};
}
function globalSummary(){return globalMetrics?summarize(globalMetrics):DATA.overview[state.view];}
function universitySummary(u){if(u.loaded)return scopeSummary(relevantLabs(u),u);if(globalMetrics)return summarize({units:globalMetrics.units.filter(c=>c.u===u.id),buckets:globalMetrics.buckets.map(b=>({...b,members:b.members.filter(m=>m.uni===u.id)}))});return u.overview[state.view];}
function scopeSummary(labs,u){const unique=[...new Map(labs.map(l=>[l.id,l])).values()];return summarize(u.metrics,new Set(unique.map(l=>l.id)),unique);}
function loadStatus(message='',retry=null){
 const box=$('#load-status');box.replaceChildren();box.hidden=!message;$('#map').setAttribute('aria-busy',message&&!retry?'true':'false');
 if(message)box.append(el('span',message));
 if(retry){const b=el('button','Retry');b.onclick=retry;box.append(b);}
}
async function fetchAsset(path){
 if(!assetCache.has(path))assetCache.set(path,(async()=>{
  if(!DATA.assets[path])throw new Error('Unrecognized data file');
  const response=await fetch(path,{cache:'no-cache'});if(!response.ok)throw new Error('Request failed ('+response.status+')');
  const bytes=await response.arrayBuffer();
  if(globalThis.crypto?.subtle){const digest=await crypto.subtle.digest('SHA-256',bytes),hash=[...new Uint8Array(digest)].map(v=>v.toString(16).padStart(2,'0')).join('');if(hash!==DATA.assets[path])throw new Error('Dataset changed; reload this page');}
  const decoded=path.endsWith('.gz')?await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text():new TextDecoder().decode(bytes);
  return JSON.parse(decoded);
 })().catch(error=>{assetCache.delete(path);throw error;}));
 return assetCache.get(path);
}
async function ensureUniversity(u){
 if(u.loaded)return;
 // A school of the CS departments view loads its PI labs (data/cs-pi-labs) instead of its inventory shard.
 const data=await fetchAsset(u.csScope?.labsFile||u.labsFile);if(data.id!==u.id)throw new Error('University data mismatch');
 u.labs=data.labs.filter(l=>{if(CSScope.shown(l))return true;outOfScope.set(l.id,{name:l.name,uniId:u.id,hidden:l.csHidden||null});return false;});u.metrics=data.metrics;
 u.labs.forEach(l=>{l.uniId=u.id;labById.set(l.id,l);});u.loaded=true;
}
async function ensureLab(lab){
 if(lab.papersLoaded)return;
 if(lab.hierarchy){const detail=CSPILabs.detail(lab,await fetchAsset(lab.hierarchy.file));lab.papers=detail.papers;Object.assign(DATA.works,detail.works);LabMapRecords.setPeople(lab.id,detail.people);}
 else if(lab.papersFile){const data=await fetchAsset(lab.papersFile);if(data.labId!==lab.id)throw new Error('Lab data mismatch');lab.papers=data.papers;Object.assign(DATA.works,data.works);}
 else lab.papers=[];
 lab.papersLoaded=true;
}
async function ensureMetrics(){if(!globalMetrics)globalMetrics=await fetchAsset(DATA.metricsFile);}
const LEADERSHIP_LABELS={missing_name:'PI / leader missing',name_recorded:'Name awaiting leadership review',leadership_reviewed:'Leadership source checked',publication_identity_verified:'Publication identity verified'};
function row(label,value){const r=el('div',undefined,'detail-row');r.append(el('span',label),el('strong',String(value)));return r;}

function renderLegend(papers){
 const entries=papers?[...(labMap?.students.some(p=>p.isPI)?[['PI / lab advisor','#e8ba70']]:[]),['Researcher','#c7a6f0'],['Paper · open access','#69cbb0'],['Paper · other / unknown access','#8daae4'],['Verified authorship connection','#dfccff'],['Candidate / profile-listing connection','#a89bc0']]:[['Computer & information sciences',CS_COLORS.field],['Computing department · other recorded field',CS_COLORS.department],[state.sizing==='works'?'No linked works yet':'Inventory pending','']];
 const box=$('#map-legend');box.replaceChildren();for(const [name,color] of entries){const item=el('span'),swatch=el('i');if(name==='Researcher')swatch.className='student-swatch';if(name.includes('connection'))swatch.className='line-swatch'+(name.startsWith('Candidate')?' candidate-line-swatch':'');if(color)swatch.style.background=color;else swatch.className='unknown';item.append(swatch,document.createTextNode(name));box.append(item);}
}
function setStats(){const n=countUnits(),named=countUnits(null,'named'),verified=countUnits(null,'verified'),hidden=hiddenNote(hiddenTotals());$('#s-unis').textContent=fmt(activeUniversities.length);$('#s-labs').textContent=fmt(n);$('#s-named').textContent=fmt(named);$('#s-active').textContent=fmt(countUnits(null,'active'));$('#s-works').textContent=fmt(globalSummary().stats.works);$('#works-view-label').textContent=state.view==='combined'?'accepted research works':state.view==='strict'?'works · PI last author only':'works · reviewed bibliography only';$('#leadership-note').textContent=fmt(named)+' of '+fmt(n)+' computer science labs in the current filters have a recorded PI or leader name ('+(n?100*named/n:0).toFixed(1)+'%). '+fmt(verified)+' have verified publication identities. Blank names are collection gaps.';const note=$('#hidden-note');if(note){note.textContent=hidden?hidden+'.':'';note.hidden=!hidden;}}
function hierarchy(){
 activeUniversities=filteredUniversities();visibleLabs=activeUniversities.filter(u=>u.id===expandedUniversity).flatMap(relevantLabs);
 const children=activeUniversities.map(u=>{
  const labs=u.id===expandedUniversity?relevantLabs(u):[],leaf=(l,name)=>({id:AtlasAffiliations.occurrence(l,name),name:l.name,kind:'lab',field:l.field,record:l,university:u,value:1});
  const {groups,unassigned}=AtlasAffiliations.group(labs);
  const branches=[...groups].map(([name,list])=>({id:u.id+'::'+name,name,kind:'department',university:u,children:list.map(l=>leaf(l,name))}));
  branches.push(...unassigned.map(l=>leaf(l,null)));
  const counts=countCells(u),byField=d3.rollup(counts,v=>d3.sum(v,c=>c.n),c=>c.field);
  return{id:u.id,name:u.name,kind:'university',record:u,known:countUnits(u),field:[...byField].sort((a,b)=>b[1]-a[1])[0]?.[0],children:branches.length?branches:undefined,value:branches.length?undefined:Math.max(1,countUnits(u))};
 });
 const root=d3.hierarchy({id:'root',name:'All universities',kind:'root',children:children.length?children:undefined,value:children.length?undefined:1}).sum(d=>d.value||0).sort((a,b)=>b.value-a.value||a.data.name.localeCompare(b.data.name));
 d3.pack().size([700,700]).padding(d=>d.depth===0?7:d.depth===1?5:2)(root);
 root.eachAfter(n=>{if(n.data.kind==='department'){const counts=d3.rollup(n.leaves(),v=>v.length,l=>l.data.field);n.data.field=[...counts].sort((a,b)=>b[1]-a[1])[0]?.[0];}});
 tree=root;nodeById=new Map(root.descendants().map(n=>[n.data.id,n]));
}
function unitMatches(lab){return !state.unitKind||ResearchUnitKinds.get(lab).key===state.unitKind;}
function departmentLabs(d){return AtlasAffiliations.uniqueLabs(nodeById.get(d.id)).filter(unitMatches);}
function unitControls(d){const box=$('#unit-type-controls');box.hidden=d.kind!=='department';if(box.hidden)return;const labs=AtlasAffiliations.uniqueLabs(nodeById.get(d.id)),counts=new Map();labs.forEach(l=>{const key=ResearchUnitKinds.get(l).key;counts.set(key,(counts.get(key)||0)+1);});const select=$('#unit-kind');select.replaceChildren();const all=el('option','All research units ('+labs.length+')');all.value='';select.append(all);for(const [key,label] of Object.entries(ResearchUnitKinds.labels)){if(!counts.has(key))continue;const option=el('option',label+' ('+counts.get(key)+')');option.value=key;select.append(option);}select.value=state.unitKind;select.onchange=()=>{state.unitKind=select.value;state.page=0;window.atlas.select(state.selected,false);};}
function unitBreakdown(box,labs){const counts=new Map();labs.forEach(l=>{const type=ResearchUnitKinds.get(l);counts.set(type.label,(counts.get(type.label)||0)+1);});const section=el('div',undefined,'unit-breakdown');for(const [label,n] of counts)section.append(row(label,n));box.append(section);}
function workTree(selection){
 const peers=(selection.children||[]).filter(n=>selection.data.kind!=='department'||unitMatches(n.data.record)),u=selection.data.kind==='root'?null:selection.data.kind==='university'?selection.data.record:selection.data.university;
 const ids=new Set(peers.map(n=>n.data.id));
 const labNodes=new Map((selection.children||[]).filter(n=>n.data.kind==='lab').map(n=>[n.data.record.id,n.data.id]));
 const peerFor=m=>selection.data.kind==='root'?[m.uni]:selection.data.kind==='university'?AtlasAffiliations.peers(m,u.id,labById):[labNodes.get(m.lab)||m.lab];
 const totals=AtlasSizing.counts(u?u.metrics:globalMetrics,m=>peerFor(m).filter(id=>ids.has(id)),m=>matches(m.field,m.status,m.uni)&&(!u||labById.has(m.lab)),state.view,state.from,state.to);
 const layout=AtlasSizing.layout(d3,peers.map(n=>({id:n.data.id,count:totals.selected.get(n.data.id)||0,reference:totals.reference.get(n.data.id)||0})));
 const points=new Map(layout.points.map(p=>[p.id,p]));
 const root=d3.hierarchy({...selection.data,children:peers.map(n=>({...n.data,children:undefined,unitCount:n.data.kind==='university'?n.data.known:AtlasAffiliations.uniqueLabs(n).length,workCount:points.get(n.data.id).count,noLinkedWorks:points.get(n.data.id).missing}))});
 root.x=350;root.y=350;root.r=350;
 for(const n of root.children||[])Object.assign(n,points.get(n.data.id));
 root.sizing={mode:'works',scale:layout.scale,maxReference:layout.maxReference};
 return root;
}
function unitTree(selection){
 const peers=(selection.children||[]).filter(n=>selection.data.kind!=='department'||unitMatches(n.data.record)),counts=peers.map(n=>({id:n.data.id,count:n.data.kind==='university'?n.data.known:AtlasAffiliations.uniqueLabs(n).length,reference:n.data.kind==='university'?n.data.known:AtlasAffiliations.uniqueLabs(n).length}));
 const layout=AtlasSizing.layout(d3,counts),points=new Map(layout.points.map(p=>[p.id,p]));
 const root=d3.hierarchy({...selection.data,children:peers.map(n=>({...n.data,children:undefined,unitCount:points.get(n.data.id).count}))});root.x=350;root.y=350;root.r=350;
 for(const n of root.children||[])Object.assign(n,points.get(n.data.id));root.sizing={mode:'units'};return root;
}
function renderSizeKey(){
 const box=$('#size-key'),svg=d3.select('#size-key-svg'),enabled=renderedSizing?.mode==='works';box.hidden=!enabled;if(!enabled)return;
 const matrix=$('#map').getScreenCTM();if(!matrix)return;const pixels=renderedSizing.scale*690/currentView[2]*camera.transform.k*Math.hypot(matrix.a,matrix.b);
 const cap=AtlasSizing.niceCount((31/pixels)**2),caption=$('#size-key-caption');svg.selectAll('*').remove();
 if(cap<1){svg.attr('hidden',true);caption.textContent='Area scale: 1 work has a diameter of '+fmt(Math.round(pixels*2))+' pixels at this zoom. Hollow circles: no linked works yet.';return;}
 svg.attr('hidden',null);const values=[...new Set([Math.max(1,AtlasSizing.niceCount(cap/4)),cap])];
 values.forEach((value,i)=>{const x=58+i*126,r=Math.sqrt(value)*pixels;svg.append('circle').attr('cx',x).attr('cy',35).attr('r',r).attr('fill','#8baaaa22').attr('stroke','#b1c9cc').attr('data-count',value);svg.append('text').attr('x',x).attr('y',84).attr('text-anchor','middle').text(fmt(value)+' '+(value===1?'work':'works'));});
 caption.textContent='Area ∝ distinct works · hollow markers: no linked works yet. Scale stays fixed across years and publication views within this selection.';
}
function fill(n){if(n.data.kind==='pi')return '#e8ba70';if(n.data.kind==='student')return '#c7a6f0';if(n.data.kind==='paper')return n.data.record.oa?'#69cbb0':'#8daae4';if(n.data.kind==='university'&&!n.data.known)return '#30424f';if(n.data.kind==='lab')return CSScope.reasonOf(n.data.record)==='department'?CS_COLORS.department:CS_COLORS.field;return CS_COLORS.field;}
function cameraPoint(d){const v=currentView,k=690/v[2],a=camera.angle*Math.PI/180,x=(d.x-v[0])*k,y=(d.y-v[1])*k;return camera.transform.apply([500+x*Math.cos(a)-y*Math.sin(a),365+x*Math.sin(a)+y*Math.cos(a)]);}
function drawCamera(){
 if(!nodeLayer||!currentView)return;
 const t=camera.transform;nodeLayer.attr('transform',`${t.toString()} rotate(${camera.angle},500,365)`);
 nodeIcons?.attr('display',d=>d.r*690/currentView[2]*t.k>15?null:'none').attr('transform',d=>{const p=cameraPoint(d),offset=d.r*690/currentView[2]*t.k>25?Math.min(22,d.r*690/currentView[2]*t.k*.42):0;return `translate(${p[0]-7},${p[1]-offset-7})`;});
 labelCandidates.attr('display',d=>d.r*690/currentView[2]*t.k>25?null:'none').attr('transform',d=>{const p=cameraPoint(d);return `translate(${p[0]},${p[1]})`;}).text(d=>shortName(d.data.name,d.r*690/currentView[2]*t.k));
 labelCandidates.filter(d=>d.r*690/currentView[2]*t.k>25).each(function(d){const width=d.r*690/currentView[2]*t.k*1.65;let text=this.textContent;while(this.getComputedTextLength()>width&&text.length>1){text=text.slice(0,-1);this.textContent=text+'…';}});
 $('#zoom-level').textContent=Math.round(t.k*100)+'%';$('#rotation-level').textContent=camera.angle+'°';
 $('#zoom-in').disabled=t.k>=24;$('#zoom-out').disabled=t.k<=.25;renderSizeKey();
}
function scheduleCamera(){if(!cameraFrame)cameraFrame=requestAnimationFrame(()=>{cameraFrame=0;drawCamera();});}
function stopMapAnimation(){d3.select('#map').interrupt();$('#tooltip').hidden=true;}
function zoomMap(factor){stopMapAnimation();d3.select('#map').call(cameraZoom.scaleBy,factor,[500,365]);}
function rotateMap(degrees){
 stopMapAnimation();const t=camera.transform,a=degrees*Math.PI/180,center=t.apply([500,365]),dx=center[0]-500,dy=center[1]-365;
 const next=[500+dx*Math.cos(a)-dy*Math.sin(a),365+dx*Math.sin(a)+dy*Math.cos(a)];
 camera.angle=(camera.angle+degrees+360)%360;
 d3.select('#map').call(cameraZoom.transform,d3.zoomIdentity.translate(next[0]-500*t.k,next[1]-365*t.k).scale(t.k));
}
function resetCamera(){stopMapAnimation();camera.angle=0;currentView=[focus.x,focus.y,focus.r*2+18];toView(currentView);d3.select('#map').call(cameraZoom.transform,d3.zoomIdentity);}
function setupCamera(){
 const svg=d3.select('#map');
 cameraZoom=d3.zoom().extent([[0,0],[1000,730]]).scaleExtent([.25,24]).clickDistance(5)
  .on('start',e=>{if(e.sourceEvent){stopMapAnimation();svg.classed('is-dragging',true);}})
  .on('zoom',e=>{camera.transform=e.transform;scheduleCamera();})
  .on('end',()=>{svg.classed('is-dragging',false);drawCamera();});
 svg.call(cameraZoom).on('dblclick.zoom',null);
 $('#zoom-in').onclick=()=>zoomMap(1.4);$('#zoom-out').onclick=()=>zoomMap(1/1.4);
 $('#rotate-left').onclick=()=>rotateMap(-15);$('#rotate-right').onclick=()=>rotateMap(15);$('#reset-view').onclick=resetCamera;
 svg.on('keydown.camera',e=>{let handled=true;if(['+','='].includes(e.key))zoomMap(1.4);else if(e.key==='-')zoomMap(1/1.4);else if(e.key==='[')rotateMap(-15);else if(e.key===']')rotateMap(15);else if(e.key==='0')resetCamera();else if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){stopMapAnimation();const dx=e.key==='ArrowLeft'?50:e.key==='ArrowRight'?-50:0,dy=e.key==='ArrowUp'?50:e.key==='ArrowDown'?-50:0;svg.call(cameraZoom.translateBy,dx/camera.transform.k,dy/camera.transform.k);}else handled=false;if(handled)e.preventDefault();});
}
function toView(v){const k=690/v[2];currentView=v;nodes.attr('transform',d=>`translate(${500+(d.x-v[0])*k},${365+(d.y-v[1])*k})`).attr('r',d=>Math.max(0,d.r*k));authorshipLines?.attr('x1',d=>500+(d.source.x-v[0])*k).attr('y1',d=>365+(d.source.y-v[1])*k).attr('x2',d=>500+(d.target.x-v[0])*k).attr('y2',d=>365+(d.target.y-v[1])*k);drawCamera();}
function paint(root,target,animate=false){
 const svg=d3.select('#map'),wasAdjusted=camera.angle!==0||camera.transform.k!==1||camera.transform.x!==0||camera.transform.y!==0,preserveCamera=root.sizing?.mode==='works'&&renderedSizing?.mode==='works'&&focus?.data.id===root.data.id;
 renderedSizing=root.sizing||null;
 svg.interrupt();svg.selectAll('*').interrupt();svg.selectAll('*').remove();
 if(cameraFrame){cancelAnimationFrame(cameraFrame);cameraFrame=0;}
 if(!preserveCamera){camera.transform=d3.zoomIdentity;camera.angle=0;}svg.property('__zoom',camera.transform);
 const desc=root.descendants().filter(d=>d!==root);
 nodeLayer=svg.append('g').attr('class','map-nodes');
 const positions=new Map(desc.map(d=>[d.data.id,d]));
 authorshipLines=nodeLayer.append('g').selectAll('line').data((root.connections||[]).filter(e=>positions.has(e.student)&&positions.has(e.paper)).map(e=>({...e,source:positions.get(e.student),target:positions.get(e.paper)}))).join('line').attr('class',e=>'authorship-line'+(e.status==='verified'?'':' candidate-authorship-line')).attr('aria-label',LabMapRecords.connectionLabel);
 authorshipLines.append('title').text(LabMapRecords.connectionLabel);
 nodes=nodeLayer.selectAll('circle').data(desc).join('circle').attr('class',d=>'node'+(d.data.kind==='pi'?' pi-node':d.data.kind==='student'?' student-node':'')+(d.data.studentOnly?' student-paper':'')+(d.data.noLinkedWorks?' no-linked-works':'')).attr('data-work-count',d=>d.data.workCount??null).attr('data-node-id',d=>d.data.id).attr('data-kind',d=>d.data.kind).attr('data-unit-kind',d=>d.data.kind==='lab'?ResearchUnitKinds.get(d.data.record).key:null).attr('role','button').attr('tabindex',0).attr('aria-label',d=>(d.data.kind==='pi'?'PI / lab advisor':d.data.kind)+': '+d.data.name).attr('fill',fill).attr('fill-opacity',d=>d.children?.length ? .10 : (d.data.kind==='university'&&!d.data.known ? .15 : .38)).attr('stroke',fill).attr('stroke-opacity',d=>d.data.kind==='university'&&!d.data.known ? .4 : .6).attr('stroke-width',.7)
 .on('click',(event,d)=>{if(event.defaultPrevented)return;event.stopPropagation();select(d.data.id);})
 .on('keydown',(event,d)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();event.stopPropagation();select(d.data.id);}})
 .on('mousemove',(event,d)=>{if(!$('#map').classList.contains('is-dragging'))tooltip(event,d);}).on('mouseleave',()=>$('#tooltip').hidden=true);
 nodes.append('title').text(d=>d.data.name+(d.data.workCount!==undefined?' · '+fmt(d.data.workCount)+' linked works'+(d.data.noLinkedWorks?' · No linked works yet':''):''));
 nodeIcons=svg.append('g').attr('aria-hidden','true').selectAll('path').data(desc.filter(d=>['student','pi','paper'].includes(d.data.kind))).join('path').attr('class','node-icon').attr('d',d=>d.data.kind!=='paper'?'M10,4a3,3 0 1,1 -6,0a3,3 0 1,1 6,0 M1,15v-2a6,6 0 0,1 12,0v2':'M3,0h7l4,4v12H3z M10,0v5h4 M6,8h5 M6,11h5');
 labels=svg.append('g').attr('class','map-labels').selectAll('text').data(desc).join('text').attr('class','node-label').attr('display','none').attr('font-size',d=>['paper','student','pi'].includes(d.data.kind)?10:12);
 focus=target||root;const view=[focus.x,focus.y,focus.r*2+18];
 labelCandidates=labels.filter(d=>d.parent===focus);
 nodes.attr('display',d=>isWithin(d,focus)&&d.depth<=focus.depth+2?null:'none');
 if(animate&&currentView&&!wasAdjusted){const start=currentView.slice();svg.transition().duration(matchMedia('(prefers-reduced-motion: reduce)').matches?0:500).tween('zoom',()=>{const interpolate=d3.interpolateZoom(start,view);return t=>toView(interpolate(t));});}else toView(view);
 svg.on('click',event=>{if(!event.defaultPrevented)goBack();});
}
function isWithin(n,parent){let p=n;while(p){if(p===parent)return true;p=p.parent;}return false;}
function shortName(name,r){const clean=name.replace(/^The /,'').replace('University of ','').replace('University','Univ.').replace('Swiss Federal Institute of Technology Lausanne','EPFL').replace('Massachusetts Institute of Technology','MIT');const compact=clean.replace(/^(Department|School|Faculty) of /,'');const max=Math.max(3,Math.floor(r*1.65/7));return compact.length>max?compact.slice(0,max-1)+'…':compact;}
function tooltip(event,d){const tip=$('#tooltip');tip.replaceChildren(el('span',d.data.name));let sub='';if(d.data.kind==='university')sub=d.data.known?`${fmt(d.data.known)} computer science labs with papers · ARWU ${d.data.record.rank}`:'Inventory pending · number of labs unknown';else if(d.data.kind==='department')sub=`${fmt(d.data.unitCount??d.leaves().length)} computer science labs`;else if(d.data.kind==='lab')sub=`${fmt(labCount(d.data.record))} linked works in this view`;else if(['student','pi'].includes(d.data.kind))sub=d.data.memberships.map(AdvisorAttribution.contextLabel).join('; ');else if(d.data.kind==='paper')sub=`${d.data.record.year} · ${d.data.studentOnly?'Researcher-linked work; check connection evidence':d.data.record.journal||d.data.record.type}`;if(d.data.workCount!==undefined)sub+=' · '+fmt(d.data.workCount)+' distinct linked works'+(d.data.noLinkedWorks?' · No linked works yet':'');tip.append(el('small',sub));tip.hidden=false;const box=$('#map-wrap').getBoundingClientRect();tip.style.left=Math.min(event.clientX-box.left+14,box.width-tip.offsetWidth-10)+'px';tip.style.top=Math.max(5,event.clientY-box.top-45)+'px';}
function paperTree(lab){
 const u=uniById.get(lab.uniId);labMap=LabMapRecords.collect(lab,accepted(lab),DATA.works,state.from,state.to,state.view);selectedMapRecord=null;
 mapRecords=new Map([...labMap.students,...labMap.papers].map(d=>[d.id,d]));
 const children=[...(state.labView!=='papers'?labMap.students:[]),...(state.labView!=='students'?labMap.papers:[])];
 const root=d3.pack().size([700,700]).padding(8)(d3.hierarchy({id:lab.id,name:lab.name,kind:'lab',record:lab,university:u,value:children.length?undefined:1,children:children.length?children:undefined}).sum(d=>d.value||0).sort((a,b)=>(a.data.kind==='pi'?-1:a.data.kind==='student'?0:1)-(b.data.kind==='pi'?-1:b.data.kind==='student'?0:1)||(b.data.record?.year||0)-(a.data.record?.year||0)||a.data.name.localeCompare(b.data.name)));
 root.connections=labMap.links;return root;
}
function highlightMap(id){
 selectedMapRecord=id;const related=new Set([id]);for(const e of labMap?.links||[])if(e.student===id||e.paper===id){related.add(e.student);related.add(e.paper);}
 nodes?.classed('is-selected',d=>d.data.id===id).classed('is-related',d=>id&&related.has(d.data.id)).classed('is-muted',d=>id&&!related.has(d.data.id));
 nodeIcons?.classed('is-muted',d=>id&&!related.has(d.data.id));
 authorshipLines?.classed('is-active',e=>e.student===id||e.paper===id).classed('is-muted',e=>id&&e.student!==id&&e.paper!==id);
 $('#lab-map-clear').hidden=!id;$('#lab-map-selection').hidden=!id;
 if(id){const record=mapRecords.get(id),linked=(labMap?.links||[]).filter(e=>e.student===id||e.paper===id),verified=linked.filter(e=>e.status==='verified').length;$('#lab-map-selection').textContent=record.name+' · '+fmt(verified)+' verified authorship connections · '+fmt(linked.length-verified)+' candidate or profile-listing connections in the selected years.';}
}
function labControls(isLab){
 $('#lab-view-controls').hidden=!isLab;$('.size-control').hidden=isLab;
 if(!isLab){labMap=null;mapRecords.clear();selectedMapRecord=null;return;}
 document.querySelectorAll('[data-lab-map-view]').forEach(b=>{b.setAttribute('aria-pressed',String(b.dataset.labMapView===state.labView));b.onclick=()=>{state.labView=b.dataset.labMapView;select(state.selected,false);};});
 const extra=labMap.papers.filter(p=>p.studentOnly).length;
 $('#lab-map-summary').textContent=fmt(labMap.students.length)+' researcher records ('+fmt(labMap.studentCount)+' with student roles) · '+fmt(labMap.acceptedCount)+' source-associated papers'+(extra?' · '+fmt(extra)+' additional researcher-linked works':'')+' · '+fmt(labMap.verifiedCount)+' verified authorship connections · '+fmt(labMap.candidateCount)+' candidate or profile-listing connections. People include separately sourced roster, advising, and paper-specific collaboration contexts. '+(labById.get(state.selected)?.hierarchy?'Lab papers have the PI on the byline, a supported university connection, and a date inside the PI’s appointment. A stated advisee co-author can support the connection when affiliations are absent. People include the PI, stated advisees and members of the PI’s own unit; candidate connections are supported name matches on each lab paper’s byline.':labById.get(state.selected)?.unitType==='department_publication_context'?'Department records preserve individually sourced research, including work with no established lab attribution.':'Default lab papers require PI authorship and supported faculty / lab dates. Roster and advising records stay visible even without qualifying papers.');
 $('#lab-map-clear').hidden=true;$('#lab-map-selection').hidden=true;$('#lab-map-clear').onclick=()=>{highlightMap(null);detail(nodeById.get(state.selected).data);};
}
function studentDetail(box,d){
 box.append(el('h2',d.record.name),el('p',d.lab.name));
 for(const [label,value] of AdvisorAttribution.personDetails(d.record))box.append(row(label,value));
 for(const m of d.memberships){for(const [label,value] of AdvisorAttribution.contextDetails(m))box.append(row(label,value));if(m.degreeDate)box.append(row('Degree date',m.degreeDate),el('p',m.dateMeaning||'Degree date; lab membership end is unresolved.'));if(m.membershipObservedOn)box.append(row('Membership source date',m.membershipObservedOn));
  const proof=el('details',undefined,'student-evidence');proof.append(el('summary',AdvisorAttribution.contextEvidenceLabel(m)));for(const e of m.evidence||[]){if(e.quote||e.excerpt)proof.append(el('blockquote',e.quote||e.excerpt));if(e.year)proof.append(el('p','Source year: '+e.year));if(e.url)proof.append(safeLink(e.url,'Relationship source ↗'));}box.append(proof);
 }
 if(d.record.profileUrl)box.append(safeLink(d.record.profileUrl,'Researcher profile ↗'));

 if(d.record.personalWorkCount!==undefined)box.append(el('p',fmt(d.record.personalWorkCount)+' confirmed personal papers in 2016–2026. The lab map includes only papers that pass this lab’s PI authorship and date checks.'));const links=labMap.links.filter(e=>e.student===d.id);box.append(el('hr'),el('h3','Paper connections · '+links.length));
 if(!links.length)box.append(el('p','No paper connections collected in these years. This does not mean the researcher has no publications.'));
 for(const e of links){const paper=mapRecords.get(e.paper),b=el('button',paper.record.year+' · '+paper.name,'student-work-button');b.onclick=()=>select(e.paper);box.append(b,el('p',LabMapRecords.connectionLabel(e)+' · '+LabMapRecords.period(e.authorship),'student-work-note'));}
 const b=el('button','← Back to lab','aside-button');b.onclick=()=>{highlightMap(null);detail(nodeById.get(state.selected).data);};box.append(b);
}
function paperStudents(box,d){
 const links=labMap?.links.filter(e=>e.paper===d.id)||[];if(!links.length)return;
 box.append(el('hr'),el('h3','Researcher connections · '+links.length));
 for(const e of links){const person=mapRecords.get(e.student),b=el('button',person.name,'student-work-button');b.onclick=()=>select(e.student);box.append(b,el('p',LabMapRecords.connectionLabel(e)+' · '+LabMapRecords.period(e.authorship),'student-work-note'));
  const proof=el('details',undefined,'student-evidence');proof.append(el('summary',LabMapRecords.connectionLabel(e)),el('p',e.authorship.identityBasis||'Source-backed connection'));for(const source of (e.authorship.evidence||[]).slice(0,4))proof.append(safeLink(source.url,'Authorship source ↗'),el('br'));box.append(proof);
 }
}

async function select(id,animate=true){
 const token=++navigation;scopeNote('');
 if(outOfScope.has(id)&&!labById.has(id)){const o=outOfScope.get(id),where=o.name+' ('+(uniById.get(o.uniId)?.name||outOfScopeUniversities.get(o.uniId)?.name||o.uniId)+')';scopeNote(o.hidden==='no_lab_papers'?where+' is not shown in the CS atlas: it has no lab papers yet. PI labs without lab papers are not listed on CS departments either; the reason is kept with the data.':o.hidden==='no_papers'?where+' is not shown in the CS atlas: no papers are linked to it yet.':where+' is not in the CS atlas: its field and department are outside computer science.');return;}
 try{
  if(mapRecords.has(id)){loadStatus();const record=mapRecords.get(id);highlightMap(id);detail(record);if(matchMedia('(max-width:760px)').matches)$('#detail').scrollIntoView({behavior:'smooth',block:'start'});return;}
  if(DATA.works[id]){
   loadStatus();const parent=labById.get(state.selected)||nodeById.get(state.selected)?.data.record;const edge=parent?.papers?.find(p=>p.work===id);
   if(edge)detail({kind:'paper',record:DATA.works[id],lab:parent,edge});return;
  }
  const university=uniById.get(id),existing=nodeById?.get(id),lab=labById.get(id)||(existing?.data.kind==='lab'?existing.data.record:null);
  if(university){loadStatus(university.loaded?'':'Loading '+university.name+' labs…');await ensureUniversity(university);}
  else if(lab){loadStatus(lab.papersLoaded?'':'Loading '+lab.name+' papers…');await ensureLab(lab);await LabMapRecords.ensure(lab);}
  else if(id!=='root'&&!existing)return;
  if(state.sizing==='works'&&id==='root')await ensureMetrics();
  if(token!==navigation)return;
  expandedUniversity=id==='root'?null:university?.id||lab?.uniId||existing?.data.university?.id;
  state.selected=id;state.page=0;hierarchy();
  const n=nodeById.get(id)||tree;state.selected=n.data.id;if(n.data.kind==='department'&&!AtlasAffiliations.uniqueLabs(n).some(unitMatches))state.unitKind='';
  if(n.data.kind==='lab')paint(paperTree(n.data.record),null,false);else if(state.sizing==='works')paint(workTree(n),null,false);else paint(unitTree(n),null,false);
  labControls(n.data.kind==='lab');unitControls(n.data);renderLegend(n.data.kind==='lab');
  $('#map-size-note').textContent=n.data.kind==='lab'?'Each bubble is one researcher or paper. Solid lines show verified authorship; dashed lines show candidate authorship or a verified profile listing. Dashed paper borders mark researcher-linked works without a separate lab association. Years filter papers; roster and advising observations retain their separate source years.':state.sizing==='works'?'Size: distinct linked works in the selected years and publication view. Shared works count once within each circle. Positions and scale use the full 2016–2026 combined view; compare peers at this level. Hollow markers mean no linked works yet.':'Size: computer science labs in each circle. Affiliation groups can overlap; their counts must not be added together. University totals count each lab once. Compare peers at this level.';
  detail(n.data);breadcrumbs(n);renderList(n.data);loadStatus();
  $('#search').placeholder=n.data.kind==='root'?'Search universities…':n.data.kind==='lab'?'Search people, papers, or university labs…':'Search this university’s labs / PIs…';
  if(state.tab==='trends')await renderTrends();
 }catch(error){if(token===navigation)loadStatus('Could not load this selection. '+error.message,()=>select(id,animate));}
}
function goBack(){if(state.selected==='root'){select('root');return;}const n=nodeById.get(state.selected);select(n?.parent?.data.id||'root');}
function breadcrumbs(n){const box=$('#breadcrumb');box.replaceChildren();n.ancestors().reverse().forEach((v,i)=>{if(i)box.append(el('span','/'));const b=el('button',v.data.kind==='root'?'World':v.data.name);b.onclick=()=>select(v.data.id);box.append(b);});$('#back').disabled=n.depth===0;}
function detail(d){const box=$('#detail');box.replaceChildren();box.append(el('div',d.kind==='root'?'RESEARCH ATLAS':d.kind==='department'?'DEPARTMENT / SCHOOL':d.kind==='paper'?'PUBLICATION':d.kind==='pi'?'PI / LAB ADVISOR':d.kind==='lab'?ResearchUnitKinds.get(d.record).label.toUpperCase():d.kind.toUpperCase(), 'eyebrow'));
 if(['student','pi'].includes(d.kind)){studentDetail(box,d);return;}
 if(d.kind==='root'){const hidden=hiddenNote(hiddenTotals());box.append(el('h2','Computer science, worldwide.'),el('p','Follow the circles from university to computing department, lab, and publication. Each level brings the underlying sources into view.'),el('hr'),row('Universities in view',activeUniversities.length),row('Computer science labs with papers',fmt(countUnits())),row('Publication-linked PI groups',globalSummary().stats.publishing),el('span','COLLECTION IN PROGRESS','pill'),el('p',state.sizing==='works'?'Circle area shows distinct linked works in the selected years and authorship view. Hollow markers mean no linked works yet in this selection. Collection coverage is uneven; these counts are observed lower bounds.':'Only computer science labs with papers are shown: at '+piSchoolNames()+' each CS faculty PI’s own lab, from the CS departments view; elsewhere the CS units with linked papers. Each lab counts equally; enclosing areas are approximate. Switch Bubble size to Linked works to compare collected output.'));if(hidden)box.append(el('p',hidden+'.','hidden-note'));
 const b=el('button','Explore labs with publication links →','aside-button');b.onclick=()=>{const u=activeUniversities.find(u=>universitySummary(u).stats.works);if(u)select(u.id);};box.append(b);return;}
 if(d.kind==='university'){const u=d.record,labs=relevantLabs(u),pi=!!u.csScope?.school,hidden=hiddenNote(u.csScope?.hidden||{},true);box.append(el('h2',u.name),el('p',u.country+' · ARWU '+u.rank),el('hr'),row(pi?'PI labs with lab papers':'CS units with papers',fmt(labs.length)),pi?row('PI labs in the CS departments view',fmt(u.csScope.piLabs)):row('CS units in the inventory',fmt(u.csScope.inScope)),row('Works in this view',fmt(scopeSummary(labs,u).stats.works)),row('With PI / leader names',fmt(labs.filter(l=>l.pi).length)+' / '+fmt(labs.length)),row('Publication identities verified',labs.filter(l=>l.pis.length).length),row('Collection','Partial / incomplete'));if(hidden)box.append(el('p',hidden+'.','hidden-note'));
  if(pi)box.append(el('p','Each CS faculty PI’s own lab, from the CS departments view. A lab paper has the PI on the byline with a university affiliation, inside the PI’s appointment. Open a department to explore its labs, then a lab for its papers and students.'),csDepartmentsLink(u));
  else{box.append(row('Dated activity verified',labs.filter(l=>l.years.length).length),el('p','Open a department or research unit to explore its labs and publications.'));const assigned=labs.filter(l=>l.department).length;box.append(row('With recorded department / school',fmt(assigned)+' / '+fmt(labs.length)));if(assigned<labs.length)box.append(el('p',fmt(labs.length-assigned)+' units are shown directly under the university while we verify their department affiliations.'));}
  if(u.url)box.append(safeLink(u.url,'University website ↗'));if(u.sweepReport&&state.view==='strict'){const b=el('button','Show reviewed lab publications','aside-button');b.onclick=async()=>{state.view='combined';$('#view').value='combined';await refresh();await select(u.id,false);};box.append(b);}return;}
 if(d.kind==='department'){const labs=departmentLabs(d),all=AtlasAffiliations.uniqueLabs(nodeById.get(d.id)),pi=!!d.university.csScope?.school;box.append(el('h2',d.name),el('p',d.university.name),el('hr'),row(pi?'PI labs with lab papers':state.unitKind?'Units of selected type':'Research units & source contexts',labs.length),row('Linked works',scopeSummary(labs,d.university).stats.works));if(state.unitKind)box.append(row('All inventoried units',all.length));
  if(pi){box.append(el('p',labs.some(l=>l.departmentCoverage==='full')?'A computing department, covered in full: each faculty PI it lists has one lab, shown here when it has lab papers.':'Faculty of this department are listed when they work in computer science: their papers at the school are in CS venues (DBLP-indexed). The department is not covered in full.'),csDepartmentsLink(d.university,'&dept='+encodeURIComponent(d.name)));return;}
  unitBreakdown(box,labs);box.append(el('p','Counts distinguish labs from centers and broader research communities. Units can have several affiliations and are counted once within this selection. Source labels remain visible on each record.'));return;}
 if(d.kind==='lab'&&d.record.hierarchy){const l=d.record,u=d.university,inView=accepted(l).length;box.append(el('h2',l.name),el('p',u.name),el('p',l.department+(l.departmentCoverage==='full'?'':' · home department of a PI the computing departments list')),el('hr'),row('PI',l.pi),row('In the CS atlas through',CS_REASON_LABELS[l.csScopeReason]),row('Lab papers · 2016–2026',fmt(l.labPapers)),row('Lab papers in this view',fmt(inView)),row('Students',fmt(l.students)),row('Student–paper links',fmt(l.studentPaperLinks)+' ('+fmt(l.verifiedStudentPaperLinks)+' verified)'));
  if(l.otherDepartments?.length)box.append(el('p','Also listed by: '+l.otherDepartments.join('; ')));
  const yrs=el('div',undefined,'mini-years');for(let y=2016;y<=2026;y++){const n=l.paperCounts.combined[y]||0,x=el('span',String(y).slice(2),n?'yes':'');x.title=y+': '+plural(n,'lab paper','lab papers');yrs.append(x);}box.append(yrs,el('p','Filled years have lab papers. A lab paper has the PI on the byline, that authorship lists the university, and it falls in the PI’s reviewed faculty period or the year of a captured department listing. Students are stated advisees and members of the PI’s own unit.'));
  if(!inView)box.append(el('p',state.view==='combined'?'No lab papers in the selected years.':'Lab papers of the CS departments view appear in the All research publication view.'));
  box.append(csDepartmentsLink(u,'&lab='+encodeURIComponent(l.hierarchy.id)));if(l.url)box.append(safeLink(l.url,'Lab page ↗'),el('br'));for(const p of l.pis)box.append(safeLink(p.source,p.name+' · DBLP identity ↗'),el('br'));return;}
 if(d.kind==='lab'){const l=d.record,kind=ResearchUnitKinds.get(l);box.append(el('h2',l.name),el('p',d.university.name),...(l.department?[el('p',l.department)]:[]),el('hr'),row('Unit type',kind.label),row('Discipline',labelField(l.field)),row('In the CS atlas through',CS_REASON_LABELS[CSScope.reasonOf(l)]||'Computer science scope'),row(kind.key==='adviser_group_listing'?'Source-listed advisor':kind.key==='pi_lab'?'PI':kind.key==='center_institute'?'Director / listed leaders':'PI / listed leaders',l.pi||'Not yet identified'),row(kind.key==='adviser_group_listing'?'Source review':'Leadership review',LEADERSHIP_LABELS[l.leadershipStatus]),row('Source-associated works in this view',accepted(l).length),row('Researcher records',LabMapRecords.roster(l).length||'Coverage missing'),row('Dated activity',l.years.length?'Supported in '+l.years.join(', '):'Not yet verified'));box.append(el('p',kind.note||'Organization type checked against the linked source.','unit-type-note'));if(kind.sourceUrl)box.append(safeLink(kind.sourceUrl,'Unit type evidence ↗'));if(l.unitStatus)box.append(row('Unit status',l.unitStatus.replaceAll('_',' ')+(l.closedOn?' · '+l.closedOn:'')),safeLink(l.statusSource||l.unitStatusSource,'Status evidence ↗'));if(l.researchSummary)box.append(el('p',l.researchSummary));if(l.departments?.length>1)box.append(el('p','Also listed with: '+l.departments.filter(x=>x!==l.department).join('; ')));if(l.researchLinkCount||l.sweepReport){box.append(row('Source-associated works',accepted(l).length),row('Candidate / profile-listing connections',labMap?.candidateCount||0));}if(state.view==='strict'&&Object.values(l.paperCounts?.reviewed||{}).some(n=>n>0)){const b=el('button','Show reviewed lab publications','aside-button');b.onclick=async()=>{state.view='combined';$('#view').value='combined';const affiliationPath=state.selected;await refresh();await select(affiliationPath,false);};box.append(b);}const yrs=el('div',undefined,'mini-years');for(let y=2016;y<=2026;y++){const x=el('span',String(y).slice(2),l.years.includes(y)?'yes':'');x.title=y+': '+(l.years.includes(y)?'Dated evidence':'Unknown activity');yrs.append(x);}box.append(yrs);box.append(el('p','Filled years have dated lab evidence. Empty years mean unknown activity. The year filter applies to publications.'));if(l.url)box.append(safeLink(l.url,'Unit website ↗'),el('br'));box.append(safeLink(l.source,'Official directory source ↗'));if(!l.department)box.append(el('p','Department affiliation is being checked. The university source is linked above.'));if(l.departmentSource)box.append(el('br'),safeLink(l.departmentSource,'Department affiliation evidence ↗'));if(l.leadership.length){box.append(el('hr'),el('span',kind.key==='adviser_group_listing'?'SOURCE-LISTED ADVISOR':'SOURCED LEADERSHIP','eyebrow'));l.leadership.forEach(p=>{box.append(el('p',p.name+' · '+p.role),safeLink(p.source,'Leadership evidence ↗'));});box.append(el('p',kind.key==='adviser_group_listing'?'These records identify the source-listed advisor. They do not establish a separate laboratory or a continuous advising interval.':'These sources record listed leadership. Historical tenure and additional co-leaders still need review.'));}else if(l.pi&&!l.pis.length&&!l.leadershipHistory?.length){box.append(el('p','A name is recorded, but its leadership role and publication identity still need review.'));}if(l.pis.length){box.append(el('hr'));l.pis.forEach(p=>box.append(safeLink(p.source,p.name+' · identity evidence ↗'),el('br')));}if(l.bibliographyUrls?.length){box.append(el('hr'));l.bibliographyUrls.slice(0,4).forEach((url,i)=>box.append(safeLink(url,'Research / bibliography source '+(i+1)+' ↗'),el('br')));}if(l.evidence.length){box.append(el('hr'));l.evidence.slice(0,3).forEach(e=>{box.append(el('p',e.start+' · '+labelField(e.type)),safeLink(e.url,'Dated activity source ↗'));});}if(!accepted(l).length)box.append(el('p','No accepted publication links in this view and date range. Publication collection or bibliography review may still be pending.'));return;}
 if(d.kind==='paper'){const w=d.record;if(d.studentOnly)box.append(el('p','This work is linked through a researcher record. Read each connection’s verification status below. It is not counted as accepted lab output in this publication view.'));PaperReader.append(box,w);const piPaper=w.source==='cs-departments';box.append(el('h2',w.title),el('p',w.journal||labelField(w.type)),el('hr'),row('Published',w.date||w.year),row('Authors',w.byline||w.authors||'Unknown'),row('Open access',w.oa===null?'Not established':w.oa?'Yes':'No / not indexed as OA'),row('Citations at collection',w.citations??'Unknown'),row('Retraction flagged',piPaper||w.retracted==null?'Not checked':w.retracted?'Yes':'No flag in index'),row('View',piPaper&&!d.studentOnly?'CS departments lab paper':d.studentOnly?'Researcher-linked work · see connection evidence':state.view==='strict'?'PI last author':state.view==='combined'?'Strict + reviewed':'Reviewed bibliography'),el('p',d.edge?.reason?.includes('reviewed_exact_lab_arxiv_bibliography_verified_PI_missing_affiliation')?'Reviewed lab bibliography · verified PI':(d.edge?.reason||'')));if(d.edge?.reason?.includes('reviewed_exact_lab_arxiv_bibliography_verified_PI_missing_affiliation'))box.append(el('p','This exact arXiv preprint is listed in the lab bibliography and its complete author list matches a verified PI. Publication-time university affiliation is missing, so it is included through the reviewed bibliography rule. Historical lab tenure remains unknown.'));if(d.edge?.strict&&!d.edge?.reviewed)box.append(el('p','Verified PI identity and university affiliation on this paper. Historical membership of the named lab may be unresolved.'));if(w.doi)box.append(safeLink(w.doi.startsWith('http')?w.doi:'https://doi.org/'+w.doi,'Read publication / DOI ↗'),el('br'));if(!w.doi&&w.url)box.append(safeLink(w.url,'Read publication ↗'),el('br'));if(w.openalex)box.append(safeLink(w.openalex,'OpenAlex record ↗'));if(d.edge?.reviewSource)box.append(el('br'),safeLink(d.edge.reviewSource,'Lab bibliography evidence ↗'));paperStudents(box,d);const b=el('button','← Back to lab','aside-button');b.onclick=()=>{highlightMap(null);detail(nodeById.get(state.selected).data);};box.append(b);}
}
function renderList(d){let headers,data,title,caption;
 if(d.kind==='root'){const hidden=hiddenNote(hiddenTotals());headers=['University','Country / region','ARWU','CS labs shown','Not shown','Linked works'];data=activeUniversities.map(u=>({id:u.id,values:[u.name,u.country,u.rank,fmt(countUnits(u)),hiddenShort(u)||'—',fmt(universitySummary(u).stats.works)]}));title='Universities';caption='Universities with computer science labs that have papers; collection is incomplete.'+(hidden?' '+hidden+'.':'');}
 else if(d.kind==='university'){const n=nodeById.get(d.id),children=n.children||[],direct=children.some(v=>v.data.kind==='lab'),pi=!!d.record.csScope?.school,hidden=hiddenNote(d.record.csScope?.hidden||{},true);headers=['Department or research unit','Type',pi?'PI labs':'Computer science units','Linked works'];data=children.slice().sort((a,b)=>(a.data.kind==='department'?0:1)-(b.data.kind==='department'?0:1)||a.data.name.localeCompare(b.data.name)).map(v=>({id:v.data.id,values:[v.data.name,v.data.kind==='department'?(pi?(AtlasAffiliations.uniqueLabs(v).some(l=>l.departmentCoverage==='full')?'Computing department':'Home department of listed PIs'):'Department / school'):ResearchUnitKinds.get(v.data.record).label,AtlasAffiliations.uniqueLabs(v).length,scopeSummary(AtlasAffiliations.uniqueLabs(v),d.record).stats.works]}));title=direct?'Departments & research units':'Departments & schools';caption=d.record.name+(hidden?' · '+hidden:'');}
 else if(d.kind==='department'&&d.university.csScope?.school){headers=['PI lab','PI','Lab papers','Students','Student–paper links'];data=nodeById.get(d.id).leaves().filter(n=>unitMatches(n.data.record)).map(n=>{const l=n.data.record;return {id:n.data.id,values:[l.name,l.pi,labCount(l),l.students,l.studentPaperLinks]};});title='PI labs';caption=d.name+' · lab papers in the selected years and publication view';}
 else if(d.kind==='department'){headers=['Research unit','Unit type','PI / listed leaders','Leadership status','Linked works'];data=nodeById.get(d.id).leaves().filter(n=>unitMatches(n.data.record)).map(n=>({id:n.data.id,values:[n.data.name,ResearchUnitKinds.get(n.data.record).label,n.data.record.pi||'Not yet identified',LEADERSHIP_LABELS[n.data.record.leadershipStatus],labCount(n.data.record)]}));title='Labs, centers & research groups';caption=d.name+' · organization types and publication coverage';}
 else if(d.kind==='lab'){headers=['Researcher or publication','Kind','Date / roster status','Connection'];data=[];
  if(state.labView!=='papers')for(const person of labMap.students)data.push({id:person.id,values:[person.name,person.isPI?'PI / lab advisor':person.isStudent?'Student':'Researcher',person.memberships.map(AdvisorAttribution.contextLabel).join('; '),labMap.links.filter(e=>e.student===person.id&&e.status==='verified').length+' verified · '+labMap.links.filter(e=>e.student===person.id&&e.status!=='verified').length+' candidate / profile listing']});
  if(state.labView!=='students')for(const paper of [...labMap.papers].sort((a,b)=>b.record.year-a.record.year))data.push({id:paper.id,values:[paper.name,'Paper',paper.record.date||paper.record.year,paper.studentOnly?'Researcher connection · see verification status':paper.edge?.library?paper.edge.reason:'Accepted lab publication']});
  title=state.labView==='both'?'People + papers':state.labView==='students'?'People':'Papers';caption='Select a row or bubble to explore its evidence and connections.';
 }
 else return;
 $('#list-title').textContent=title;$('#list-caption').textContent=caption;
 $('#list-head').replaceChildren();const h=el('tr');headers.forEach(v=>h.append(el('th',v)));$('#list-head').append(h);
 const body=$('#list-body');body.replaceChildren();const pageSize=20;state.page=Math.min(state.page,Math.max(0,Math.ceil(data.length/pageSize)-1));
 data.slice(state.page*pageSize,(state.page+1)*pageSize).forEach(r=>{const tr=el('tr');tr.dataset.id=r.id;tr.tabIndex=0;tr.setAttribute('aria-label','Explore '+r.values[0]);r.values.forEach((v,i)=>{const td=el('td');if(headers[i]==='Unit type'){td.className='unit-type-cell';td.append(el('span',String(v),'unit-type-pill'));}else td.textContent=String(v);tr.append(td);});tr.onclick=()=>select(r.id);tr.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(r.id);}};body.append(tr);});
 if(!data.length){const tr=el('tr'),td=el('td','No records collected for this selection yet.','empty');td.colSpan=headers.length;tr.append(td);body.append(tr);}
 const pages=$('#list-pagination');pages.replaceChildren(el('span',data.length?`${state.page*pageSize+1}–${Math.min((state.page+1)*pageSize,data.length)} of ${fmt(data.length)}`:'0 collected records'));if(data.length>pageSize){for(const [text,dir] of [['←',-1],['→',1]]){const b=el('button',text);b.setAttribute('aria-label',dir<0?'Previous page':'Next page');b.disabled=state.page+dir<0||(state.page+dir)*pageSize>=data.length;b.onclick=()=>{state.page+=dir;renderList(d);};pages.append(b);}}
}

function search(){
 const q=$('#search').value.trim().toLowerCase(),box=$('#search-results');box.replaceChildren();box.hidden=!q;if(!q)return;
 const matches=[];for(const u of activeUniversities)if(u.name.toLowerCase().includes(q))matches.push({id:u.id,title:u.name,sub:'University · '+u.country});
 const u=uniById.get(expandedUniversity);
 for(const lab of u?relevantLabs(u):[]){
  if((lab.name+' '+lab.pi+' '+(lab.aliases||[]).join(' ')).toLowerCase().includes(q))matches.push({id:lab.id,title:lab.name,sub:u.name+' · '+(lab.pi||lab.department||'Research unit')});
  if(lab.id===(labById.get(state.selected)||nodeById.get(state.selected)?.data.record)?.id)for(const edge of accepted(lab)){const w=DATA.works[edge.work];if((w.title+' '+(w.doi||'')).toLowerCase().includes(q))matches.push({id:state.selected,paper:w.id,title:w.title,sub:w.year+' · '+lab.name});}
 }
 for(const person of labMap?.students||[])if(person.name.toLowerCase().includes(q))matches.push({id:state.selected,paper:person.id,title:person.name,sub:(person.isPI?'PI / lab advisor':person.isStudent?'Student':'Researcher')+' · '+person.lab.name});
 for(const paper of labMap?.papers.filter(p=>p.studentOnly)||[])if((paper.name+' '+(paper.record.doi||'')).toLowerCase().includes(q))matches.push({id:state.selected,paper:paper.id,title:paper.name,sub:'Researcher-linked work · '+paper.record.year});
 for(const r of matches.slice(0,25)){const b=el('button');b.append(el('span',r.title),el('small',r.sub));b.onclick=async()=>{if(r.href){location.href=r.href;return;}await setTab('atlas');await select(r.id,false);if(r.paper)await select(r.paper);box.hidden=true;$('#search').value='';};box.append(b);}
 if(!matches.length)box.append(el('div',u?'No computer science matches in this university.':'No matching universities with computer science units. Open a university to search its labs.','empty'));
}
function chart(id,points,color){const svg=d3.select(id);svg.selectAll('*').remove();const width=560,height=260,m={l:40,r:14,t:24,b:34},x=d3.scaleBand().domain(points.map(p=>p.year)).range([m.l,width-m.r]).padding(.36),max=d3.max(points,p=>p.value)||1,y=d3.scaleLinear().domain([0,max]).nice().range([height-m.b,m.t]);svg.append('g').attr('class','chart-grid').selectAll('line').data(y.ticks(4).filter(Number.isInteger)).join('line').attr('x1',m.l).attr('x2',width-m.r).attr('y1',d=>y(d)).attr('y2',d=>y(d));svg.append('g').selectAll('text').data(y.ticks(4).filter(Number.isInteger)).join('text').attr('class','chart-label').attr('x',m.l-8).attr('y',d=>y(d)+3).attr('text-anchor','end').text(d=>fmt(d));svg.append('g').selectAll('rect').data(points).join('rect').attr('x',d=>x(d.year)).attr('y',d=>y(d.value)).attr('width',x.bandwidth()).attr('height',d=>height-m.b-y(d.value)).attr('fill',color).attr('opacity',d=>d.year===2026 ? .45 : .85).attr('rx',2).append('title').text(d=>d.year+': '+fmt(d.value)+(d.year===2026?' (partial year)':''));svg.append('g').selectAll('text').data(points).join('text').attr('class','chart-label').attr('x',d=>x(d.year)+x.bandwidth()/2).attr('y',height-12).attr('text-anchor','middle').text(d=>String(d.year).slice(2)+(d.year===2026?'*':''));svg.append('g').selectAll('text').data(points).join('text').attr('class','chart-label').attr('x',d=>x(d.year)+x.bandwidth()/2).attr('y',d=>y(d.value)-7).attr('text-anchor','middle').text(d=>d.value||'0');}

async function renderTrends(){
 const token=navigation,selected=nodeById.get(state.selected),scoped=$('#use-map-scope').checked&&selected&&selected.data.kind!=='root';
 let result;
 try{
  if(scoped){const u=selected.data.kind==='university'?selected.data.record:selected.data.university,labs=selected.data.kind==='department'?departmentLabs(selected.data):AtlasAffiliations.uniqueLabs(selected);result=scopeSummary(labs,u);}
  else if(isDefaultScope())result=globalSummary();
  else{loadStatus('Loading summary statistics…');await ensureMetrics();if(token!==navigation)return;result=globalSummary();loadStatus();}
 }catch(error){loadStatus('Could not load statistics. '+error.message,renderTrends);return;}
 $('#trend-scope').textContent=(scoped?selected.data.name:'Computer science at all filtered universities')+' · Observed counts in the selected years and publication view.';
 const {annual,stats:s}=result;
 chart('#activity-chart',annual.map(d=>({year:d.year,value:d.activity})),'#4e9b83');chart('#papers-chart',annual.map(d=>({year:d.year,value:d.works})),'#678db4');
 const body=$('#annual-body');body.replaceChildren();annual.forEach(a=>{const tr=el('tr');[a.year+(a.year===2026?'*':''),fmt(a.activity),fmt(a.publishing),fmt(a.works),fmt(a.links),a.oa===null?'—':(100*a.oa).toFixed(1)+'%'].forEach(v=>tr.append(el('td',String(v))));body.append(tr);});
 const pct=n=>n===null?'—':(100*n).toFixed(1)+'%',fixed=(n,d)=>n===null?'—':n.toFixed(d);
 const cards=[['Publishing PI groups',fmt(s.publishing)],['Works / publishing group',s.publishing?(s.groupLinks/s.publishing).toFixed(1):'—'],['Known open-access share',pct(s.oa)],['Mean author team size',fixed(s.meanAuthors,1)],['Distinct indexed topics',fmt(s.topicCount)],['Topic diversity · bits',fixed(s.entropy,2)],['Cross-country works',pct(s.international)],['Lab-output concentration',fixed(s.hhi,3)]];
 const box=$('#metric-cards');box.replaceChildren();cards.forEach(([name,value])=>{const c=el('div');c.append(el('strong',value),el('span',name));box.append(c);});
}
function renderCoverage(){const s=DATA.csScope.summary,h=s.hidden,pi=s.byReason.cs_department_pi_lab;const cards=[['Universities in the cohort',300],['Universities with CS labs shown',DATA.universities.length],['Computer science labs shown',countUnits(null,'n',true)],['PI labs of the CS departments · '+piSchoolNames(),pi],['CS units with papers at other universities',countUnits(null,'n',true)-pi],['CS units without papers · not shown',h.no_papers],['PI labs without lab papers · not shown',h.no_lab_papers],['Earlier inventory units replaced by PI labs',h.replaced_by_pi_labs],['Shown labs with dated activity',countUnits(null,'active',true)],['Shown labs with PI / leader names',countUnits(null,'named',true)],['Publication identities verified',countUnits(null,'verified',true)],['Complete university inventories',0]];const box=$('#coverage-cards');box.replaceChildren();cards.forEach(([name,value])=>{const c=el('div');c.append(el('strong',fmt(value)),el('span',name));box.append(c);});const body=$('#coverage-body');body.replaceChildren();allCSUniversities().sort((a,b)=>(a.rankLow||999)-(b.rankLow||999)||a.name.localeCompare(b.name)).forEach(u=>{const tr=el('tr'),shown=uniById.has(u.id),n=shown?countUnits(u,'n',true):0;[u.name,u.rank,fmt(n),hiddenShort(u)||'—',shown?fmt(countUnits(u,'active',true)):'—',shown?fmt(countUnits(u,'named',true))+' / '+fmt(n):'—'].forEach(v=>tr.append(el('td',String(v))));if(shown){tr.dataset.id=u.id;tr.tabIndex=0;tr.onclick=async()=>{state.country='';state.field='';state.leadership='';$('#country').value='';$('#field').value='';$('#leadership').value='';await refresh();await setTab('atlas');await select(u.id,false);};tr.onkeydown=e=>{if(e.key==='Enter')tr.click();};}else tr.className='not-shown';body.append(tr);});}

async function setTab(tab){if(!['atlas','trends','coverage'].includes(tab))tab='atlas';state.tab=tab;history.replaceState(null,'',tab==='coverage'?'#coverage':location.pathname+location.search);document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));document.querySelectorAll('.panel').forEach(p=>p.hidden=p.id!==tab+'-panel');if(tab==='trends')await renderTrends();if(tab==='atlas'&&currentView)drawCamera();}
async function refresh(){
 const version=++refreshVersion,token=++navigation,selected=state.selected;
 try{
  if(!isDefaultScope()||state.sizing==='works'){loadStatus('Loading summary statistics…');await ensureMetrics();}
  if(version!==refreshVersion||token!==navigation)return;
  hierarchy();setStats();await select(nodeById.has(selected)?selected:'root',false);$('#search-results').hidden=true;
 }catch(error){if(version===refreshVersion)loadStatus('Could not update filters. '+error.message,refresh);}
}
function initialPublicationView(search){const view=new URLSearchParams(search).get('view');return ['strict','reviewed','combined'].includes(view)?view:'combined';}
async function loadDataset(){
 const response=await fetch('data.json',{cache:'no-store'});window.DatasetUpdates?.observe(response);if(!response.ok)throw new Error('Dataset request failed');
 const data=await response.json();if(data.bundleFormat!=='lazy-atlas-v1')throw new Error('Unsupported dataset format');applyCSScope(data);
 document.querySelectorAll('a[download][href^="downloads/"]').forEach(a=>{const original=a.getAttribute('href').slice(10),logical=original.replace(/\.gz$/,''),name=data.downloads?.[original]||data.downloads?.[logical];if(name){a.href='downloads/'+name;const label=a.textContent.replace(/\s*[↧↓]/g,'').replace(/\s*·\s*(?:CSV\s*)?gzip\b/gi,'').replace(/\s*·\s*CSV\s*$/i,'').trim();a.textContent=label+(name.endsWith('.gz')?' · CSV gzip ↧':' ↧');}});
 return data;
}
async function init(){try{DATA=await loadDataset();window.DatasetUpdates?.start();state.view=initialPublicationView(location.search);$('#view').value=state.view;uniById=new Map(DATA.universities.map(u=>[u.id,u]));labById=new Map();DATA.universities.forEach(u=>u.labs.forEach(l=>{l.uniId=u.id;labById.set(l.id,l);}));$('#cutoff').textContent='DATA UPDATED '+DATA.asOf+' · PAPERS THROUGH '+DATA.publicationSummary.window_end;{const s=DATA.csScope.summary,pi=s.byReason.cs_department_pi_lab;$('#collection-note').textContent=`${fmt(s.labs)} computer science labs with papers across ${fmt(DATA.universities.length)} universities: ${fmt(pi)} PI labs of the CS departments at ${piSchoolNames()}, and ${fmt(s.labs-pi)} CS units with linked papers elsewhere. ${fmt(DATA.overview.combined.stats.works)} distinct accepted research works.`;}$('#footer-note').textContent=`Data updated ${DATA.asOf} · Publications through ${DATA.publicationSummary.window_end} · Incomplete inventory`;for(const c of [...new Set(DATA.universities.map(u=>u.country))].sort()){const o=el('option',c);o.value=c;$('#country').append(o);}for(let y=2016;y<=2026;y++){for(const id of ['from','to']){const o=el('option',String(y));o.value=y;$('#'+id).append(o);}}$('#from').value=2016;$('#to').value=2026;for(const key of ['country','leadership','view','sizing','from','to'])$('#'+key).onchange=()=>{state[key]=['from','to'].includes(key)?Number($('#'+key).value):$('#'+key).value;if(state.from>state.to){if(key==='from')state.to=state.from;else state.from=state.to;$('#from').value=state.from;$('#to').value=state.to;}refresh();};$('#clear').onclick=()=>{Object.assign(state,{country:'',field:'',leadership:'',view:'combined',sizing:'units',from:2016,to:2026,selected:'root',unitKind:''});for(const k of ['country','field','leadership','view','sizing','from','to'])$('#'+k).value=state[k];$('#search').value='';refresh();};$('#show-missing-leaders').onclick=()=>{state.leadership='missing_name';$('#leadership').value='missing_name';refresh();};$('#use-map-scope').onchange=renderTrends;$('#search').oninput=search;$('#search').onkeydown=e=>{if(e.key==='Escape')$('#search-results').hidden=true;};document.addEventListener('click',e=>{if(!e.target.closest('.search-label'))$('#search-results').hidden=true;});$('#back').onclick=goBack;$('#reset-map').onclick=()=>select('root');document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>setTab(b.dataset.tab));setupCamera();window.addEventListener('resize',()=>{if(currentView)renderSizeKey();});await refresh();renderCoverage();const blockers=DATA.publicationSummary.api_collection_blockers||[];if(blockers.length){$('#publication-status').hidden=false;$('#publication-status').textContent='Recorded collection limits: '+blockers.join(' ');}window.atlas={state,select,getData:()=>DATA,getSizing:()=>renderedSizing,getCamera:()=>({scale:camera.transform.k,x:camera.transform.x,y:camera.transform.y,rotation:camera.angle})};const route=new URLSearchParams(location.search);if(['strict','reviewed','combined'].includes(route.get('view'))){state.view=route.get('view');$('#view').value=state.view;await refresh();}const routeUni=route.get('university');if(uniById.has(routeUni)){await select(routeUni,false);const requestedDepartment=route.get('department');if(requestedDepartment){const label=AtlasAffiliations.canonicalLabel({uniId:routeUni},requestedDepartment),id=routeUni+'::'+label;if(nodeById.has(id))await select(id,false);else scopeNote(requestedDepartment+' is not a computer science department in the CS atlas at '+uniById.get(routeUni).name+'.');}const requestedLab=route.get('lab');if(requestedLab&&labById.get(requestedLab)?.uniId===routeUni)await select(requestedLab,false);else if(requestedLab&&outOfScope.get(requestedLab)?.uniId===routeUni)await select(requestedLab,false);else if(requestedLab)scopeNote('That lab is not shown in the CS atlas at '+uniById.get(routeUni).name+'.');}else if(outOfScopeUniversities.has(routeUni)){const o=outOfScopeUniversities.get(routeUni);scopeNote(o.name+' is not in the CS atlas: '+(o.csScope?.inScope?hiddenNote(o.csScope.hidden,true)+', so no computer science units with papers are shown there.':'no computer science units are recorded there.'));}if(location.hash==='#coverage')await setTab('coverage');}catch(error){$('#error').hidden=false;$('#error').textContent='The dataset could not load. Serve this folder over HTTP and retry. '+error.message;console.error(error);}}
init();
