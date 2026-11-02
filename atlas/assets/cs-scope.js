'use strict';
// The atlas's computer-science scope, and what it shows, in the browser. The rule is defined only in
// scripts/cs_scope.py; scripts/build-cs-scope.py marks every lab (csScope / csScopeReason)
// and copies the rule into data.json (csScope.rule) and data/cs-scope-rule.json.
// This module applies that generated copy. Do not add or edit patterns here.
const CSScope=(()=>{
 let rule=null,pattern=null;
 function configure(r){if(!r||r.schema!==1||!r.field||!r.departmentPattern)throw new Error('CS scope rule missing; run scripts/build-cs-scope.py');rule=r;pattern=new RegExp(r.departmentPattern,(r.flags||'').replace(/[gy]/g,''));return api;}
 async function ensure(path='data/cs-scope-rule.json'){if(rule)return api;const response=await fetch(path,{cache:'no-cache'});if(!response.ok)throw new Error('CS scope rule unavailable ('+response.status+')');return configure(await response.json());}
 function ready(){if(!rule)throw new Error('CS scope rule not loaded');}
 function computingDepartment(name){ready();return typeof name==='string'&&pattern.test(name);}
 // Same decision as cs_scope.reason(); used only for records the build did not mark.
 function reason(lab){ready();const field=lab?.field===rule.field,department=computingDepartment(lab?.department||'');return field&&department?'field_and_department':field?'field':department?'department':null;}
 function inScope(lab){return typeof lab?.csScope==='boolean'?lab.csScope:reason(lab)!==null;}
 function reasonOf(lab){return typeof lab?.csScope==='boolean'?(lab.csScope?lab.csScopeReason||reason(lab):null):reason(lab);}
 // What the atlas shows (owner decision 2026-10-22, "PI labs with papers only"): the build marks every record it
 // writes with csShown (scripts/cs_scope.py unit_visibility / pi_lab_visibility); csHidden names why one is hidden.
 function shown(lab){return lab?.csShown===true;}
 function hiddenLabel(reason){return rule?.hiddenReasons?.[reason]||'';}
 // A CS lab is grouped under its computing department labels; a lab with none keeps all of its labels.
 function departmentLabels(lab,labels){const computing=labels.filter(computingDepartment);return computing.length?computing:labels;}
 const api={configure,ensure,computingDepartment,reason,reasonOf,inScope,shown,hiddenLabel,departmentLabels,get rule(){return rule;}};
 return api;
})();
if(typeof module!=='undefined')module.exports=CSScope;
