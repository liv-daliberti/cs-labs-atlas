/* Source-backed membership and work observations; identity strength stays explicit. */
'use strict';
window.LabMapRecords=(()=>{
 const byLab=new Map(),collectionRequests=new Map();
 const student=m=>['graduate_student','undergraduate_student','student_unspecified'].includes(m.memberType);
 const doi=w=>String(w.doi||'').replace(/^https?:\/\/(?:dx\.)?doi\.org\//i,'').toLowerCase();
 const graphId=w=>w.canonicalGraphWorkId||w.networkId||w.library?.networkId||'';
 const key=w=>graphId(w)?'graph:'+graphId(w):doi(w)?'doi:'+doi(w):w.arxiv?'arxiv:'+w.arxiv:String(w.id);
 const keys=w=>[...new Set([key(w),...([w.id,w.library?.id,...(w.aliases||[]),...(w.library?.aliases||[])].filter(Boolean).flatMap(id=>[String(id),'graph:'+id]))])];
 function group(labId,people){const g=new Map();for(const person of people){const memberships=AdvisorAttribution.contexts(person).filter(m=>m.labId===labId);if(memberships.length)g.set(person.id,{person,memberships});}byLab.set(labId,g);}
 // People of a CS departments PI lab come from its school file (atlas/assets/cs-pi-labs.js), not a people file.
 function setPeople(labId,people){group(labId,people);}
 async function ensure(lab){
  if(!lab.peopleFile||byLab.has(lab.id))return;
  if(!collectionRequests.has(lab.peopleFile))collectionRequests.set(lab.peopleFile,readResearchJSON(lab.peopleFile).then(data=>{
   if(data.schema!==1||data.labId!==lab.id)throw Error('Lab people data mismatch');group(lab.id,data.people);
  }).catch(e=>{collectionRequests.delete(lab.peopleFile);throw e;}));
  await collectionRequests.get(lab.peopleFile);
 }
 function roster(lab){const found=new Map();for(const id of [lab.id,...(lab.aliases||[])])for(const r of byLab.get(id)?.values()||[]){if(!found.has(r.person.id))found.set(r.person.id,{person:r.person,memberships:[]});for(const m of r.memberships)if(!found.get(r.person.id).memberships.includes(m))found.get(r.person.id).memberships.push(m);}return [...found.values()].sort((a,b)=>Number(b.memberships.some(student))-Number(a.memberships.some(student))||a.person.name.localeCompare(b.person.name));}
 function collect(lab,accepted,works,from,to,view){
  const students=roster(lab).map(r=>({id:(r.person.isPI?'pi:':'student:')+r.person.id,name:r.person.name,kind:r.person.isPI?'pi':'student',isPI:!!r.person.isPI,isStudent:!r.person.isPI&&r.memberships.some(student),lab,record:r.person,memberships:r.memberships,value:1}));
  const papers=new Map(),byKey=new Map(),links=[];
  function index(n){papers.set(n.id,n);for(const k of keys(n.record)){if(!byKey.has(k))byKey.set(k,n);else if(byKey.get(k)!==n)byKey.set(k,null);}}
  for(const edge of accepted){const w=works[edge.work];if(!w)continue;index({id:w.id,name:w.title,kind:'paper',lab,record:w,edge,value:1,studentOnly:false});}
  for(const s of students)for(const w of s.record.works||[]){
   if(!s.memberships.some(m=>w.labId?m.labId===w.labId:m.labName===w.labName))continue;
   if(view&&w.views&&!w.views.includes(view))continue;  // e.g. a student link to a CS departments lab paper
   const year=Number((w.date||'').slice(0,4));if(!year||year<from||year>to)continue;
   const matches=[...new Set(keys(w).map(k=>byKey.get(k)).filter(Boolean))];let p=matches.length===1?matches[0]:null;
   if(!p){const id='studentwork:'+key(w);p=papers.get(id);if(!p){p={id,name:w.title,kind:'paper',lab,record:{...w,id,year,oa:null,citations:null},value:1,studentOnly:true};index(p);}}
   const status=w.status==='verified'?'verified':w.connectionType==='profile_listing'?'profile_listing':'candidate';
   const existing=links.find(e=>e.student===s.id&&e.paper===p.id);
   if(!existing)links.push({student:s.id,paper:p.id,authorship:w,status,observations:[w]});else{existing.observations.push(w);if(status==='verified'){existing.status=status;existing.authorship=w;}}
  }
  return {students,papers:[...papers.values()],links,acceptedCount:[...papers.values()].filter(p=>!p.studentOnly).length,studentCount:students.filter(p=>p.isStudent).length,verifiedCount:links.filter(e=>e.status==='verified').length,candidateCount:links.filter(e=>e.status!=='verified').length};
 }
 const period=w=>w.piAuthorship?(w.facultyBasis==='P'?'PI authorship and university affiliation verified within a reviewed faculty appointment.':'PI authorship and university affiliation verified in the department faculty listing year '+w.facultyBasis.slice(1)+'.'):w.labPeriod==='supported'?'Publication falls within the recorded membership interval.':w.labPeriod==='outside'?'Publication is outside the recorded membership interval.':'Lab membership at publication is unresolved.';
 const connectionLabel=e=>e.status==='verified'?'Verified authorship':e.status==='profile_listing'?'Profile listing verified · authorship awaiting review':'Candidate authorship · awaiting review';
 return {ensure,setPeople,roster,collect,key,period,connectionLabel};
})();
