'use strict';
// PI labs of the CS departments view inside the CS atlas (owner decision 2026-10-22, "PI labs with papers only").
// scripts/build-cs-scope.py (rule: scripts/cs_scope.py) writes the PI labs the atlas shows, with their counts, to
// data/cs-pi-labs/<university>.json.gz. When a lab opens, its papers and students come from the same school file
// that cs-departments.html shows (data/cs-hierarchy/<school>.json.gz), so both pages show the same records.
// This module only reshapes that file into the atlas lab view's papers, works and people; it decides nothing.
const CSPILabs=(()=>{
 const MEMBER_TYPE={'PhD student':'graduate_student','PhD alumnus':'graduate_student','Master’s':'graduate_student','Thesis student':'graduate_student',Undergraduate:'undergraduate_student',Student:'student_unspecified',Postdoc:'postdoc','Lab member':'member'};
 const IDENTITY={dblp_person_page_doi:'PI’s DBLP page',dblp_person_page_title:'PI’s DBLP page',dblp_verified_collection_work:'PI’s verified work',anchored_author_id:'PI’s OpenAlex author id',advisee_coauthor:'advisee co-author',reviewed_openalex_author_id:'PI’s reviewed OpenAlex author id',pi_orcid:'PI’s ORCID',advisee_anchored_author_id:'PI’s OpenAlex author id (seen with their advisees)',pi_institutional_publication_list:'PI’s department publication list'};
 const LINK_BASIS={collection_person_link:'Recorded authorship in the collection',byline_name_with_school_affiliation:'Name on a school-affiliated byline entry (candidate)'};
 const workId=(school,p)=>'cs-pi-lab:'+school+':'+(p.w||p.oa);
 function work(school,p){
  const shown=p.b||[];
  return {id:workId(school,p),title:p.t||'(untitled)',year:p.y,date:p.d||String(p.y||''),journal:p.v||'',type:'Lab paper',doi:p.doi||null,url:p.u||p.oa||'',openalex:p.oa||null,
   authors:p.nb||null,byline:shown.join(', ')+(p.nb>shown.length?' … ('+p.nb+' authors)':''),oa:null,citations:null,aliases:[p.w,p.atlasId,p.oa].filter(Boolean),source:'cs-departments'};
 }
 // data: the school's cs-hierarchy file; lab: the atlas record (hierarchy: {school, index, id}).
 function detail(lab,data){
  const h=data.labs?.[lab.hierarchy.index];
  if(!h||h.id!==lab.hierarchy.id)throw new Error('The CS departments data changed after this atlas was built; run scripts/build-cs-scope.py');
  const school=lab.hierarchy.school,works={},papers=[],byStudent=new Map();
  for(const [i,identity,appointment] of h.papers){
   const w=work(school,data.papers[i]);works[w.id]=w;
   papers.push({work:w.id,combined:true,reason:'CS departments lab paper · PI identity: '+(IDENTITY[identity]||identity)+' · appointment: '+(appointment==='P'?'reviewed faculty period':'department faculty listing '+appointment.slice(1))});
  }
  for(const [s,i,status,basis] of h.links){
   const p=data.papers[i];if(!byStudent.has(s))byStudent.set(s,[]);
   byStudent.get(s).push({id:workId(school,p),title:p.t,date:p.d||String(p.y||''),doi:p.doi||null,labId:lab.id,views:['combined'],status:status==='v'?'verified':'candidate',identityBasis:LINK_BASIS[basis]||basis,evidence:[]});  // a link to a lab paper: shown in the lab-paper view only
  }
  const people=h.students.map(([s,relation,years,url,quote])=>{
   const st=data.students[s],advisee=relation==='advisee';
   return {id:st.id,name:st.n,works:byStudent.get(s)||[],memberships:[{labId:lab.id,labName:lab.name,relationshipType:advisee?'academic_advising':'lab_membership',advisorName:advisee?lab.pi:undefined,
    role:st.r,memberType:MEMBER_TYPE[st.r]||'member',status:advisee?'stated advisee':'member of the PI’s own unit',observedRange:years||null,
    observedOn:years?(years[0]===years[1]?String(years[0]):years[0]+'–'+years[1]+' (first and last source years)'):undefined,evidence:url||quote?[{url:url||'',quote:quote||''}]:[]}]};
  });
  // Every accepted PI-lab paper already carries verified PI authorship. Project that
  // evidence into the graph, without inferring authorship from the advising role.
  const piIds=new Set(h.pi.ids||[]);
  const existingPI=people.find(person=>piIds.has(person.id));
  const pi=existingPI||{id:h.pi.ids?.[0]||'cs-pi:'+school+':'+h.id,name:h.pi.name,works:[],memberships:[]};
  pi.isPI=true;
  pi.profileUrl=h.pi.dblp?.[0]||pi.profileUrl;
  pi.memberships.push({labId:lab.id,labName:lab.name,relationshipType:'lab_leadership',role:'PI / lab advisor',memberType:'principal_investigator',status:'PI of this own lab',evidence:[...(h.url?[{url:h.url}]:[]),...h.periods.flatMap(period=>period.ev||[])]});
  for(const [i,identity,appointment,appointmentDate] of h.papers){
   const p=data.papers[i];
   pi.works.push({id:workId(school,p),title:p.t,date:p.d||String(p.y||''),doi:p.doi||null,labId:lab.id,views:['combined'],status:'verified',piAuthorship:true,facultyBasis:appointment,appointmentDate,
    identityBasis:'Verified PI author: '+(IDENTITY[identity]||identity)+'; this authorship lists the university.',
    evidence:[{url:p.oa||p.u||(p.doi?'https://doi.org/'+p.doi:'')},...(h.pi.dblp||[]).map(url=>({url}))].filter(e=>e.url)});
  }
  if(!existingPI)people.unshift(pi);
  return {papers,works,people};
 }
 return {detail,workId};
})();
if(typeof module!=='undefined')module.exports=CSPILabs;
