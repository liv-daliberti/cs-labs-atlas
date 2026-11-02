'use strict';
const ResearchUnitKinds=(()=>{
 const labels={adviser_group_listing:'Advising source listing',department_publication_context:'Department publication context',pi_lab:'PI-led lab',pi_advising_group:'PI research / advising group',research_group:'Research group',project:'Project',lab_group:'Lab / research group',center_institute:'Center / institute',umbrella_group:'Research community / umbrella group',program:'Program / initiative',facility:'Facility',other:'Other / type awaiting review'};
 function get(lab){
  // A PI lab of the CS departments view: one faculty PI and the people they advise (owner decisions 2026-10-21/22).
  if(lab.unitType==='pi_lab')return {key:'pi_lab',label:labels.pi_lab,reviewed:true,note:'One faculty PI and the people they advise, as the CS departments view lists them. Centres and multi-PI groups are not labs.'};
  if(['adviser_group_listing','department_publication_context'].includes(lab.unitType||lab.type)){const key=lab.unitType||lab.type;return {key,label:labels[key],reviewed:true,note:lab.unitTypeNote||'Source context for people and work; this is not a separately verified laboratory.'};}
  const type=lab.type||'',key=/^(research_)?(center|institute)$/.test(type)?'center_institute':/(facility|platform)/.test(type)?'facility':/(program|initiative|project)/.test(type)?'program':/(cluster|consortium)/.test(type)?'umbrella_group':/(laboratory|research_group|^lab$)/.test(type)?'lab_group':'other';
  return {key,label:labels[key],reviewed:false,note:key==='lab_group'?'Recorded as a lab or research group. Whether it is one PI-led lab or a broader research community still needs review.':'Based on the recorded unit type. Organizational structure is still being reviewed.'};
 }
 return {get,labels};
})();
if(typeof module!=='undefined')module.exports=ResearchUnitKinds;
