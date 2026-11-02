'use strict';
const AtlasAffiliations = (() => {
 function canonicalLabel(lab,label){return (lab.uniId==='princeton-university'||lab.university_id==='princeton-university')&&label==='Department of Computer Science'?'Computer Science':label;}
 let labelFilter=null;
 // Optional view-level narrowing of a lab's labels (the CS atlas keeps computing departments; see cs-scope.js).
 function setLabelFilter(filter){labelFilter=typeof filter==='function'?filter:null;}
 function labels(lab){const princeton=lab.uniId==='princeton-university'||lab.university_id==='princeton-university';const all=[...new Set([lab.department,...(Array.isArray(lab.departments)?lab.departments:[])].filter(x=>typeof x==='string'&&x.trim()).flatMap(x=>princeton?x.split(';'):[x]).map(x=>canonicalLabel(lab,x.trim())).filter(Boolean))];return labelFilter&&all.length?labelFilter(lab,all):all;}
 function occurrence(lab,label){return label===labels(lab)[0]||!label?lab.id:lab.id+'::affiliation::'+encodeURIComponent(label);}
 function group(labs){const groups=new Map(),unassigned=[];for(const lab of labs){const names=labels(lab);if(!names.length)unassigned.push(lab);for(const name of names){if(!groups.has(name))groups.set(name,[]);groups.get(name).push(lab);}}return {groups,unassigned};}
 function uniqueLabs(node){return [...new Map(node.leaves().filter(n=>n.data.kind==='lab').map(n=>[n.data.record.id,n.data.record])).values()];}
 function peers(member,university,labs){const lab=labs.get(member.lab),names=lab?labels(lab):(member.department?[member.department]:[]);return names.length?names.map(name=>university+'::'+name):[member.lab];}
 return {labels,occurrence,group,uniqueLabs,peers,canonicalLabel,setLabelFilter};
})();
if(typeof module!=='undefined')module.exports=AtlasAffiliations;
