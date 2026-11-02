
'use strict';
window.DatasetUpdates=(()=>{
 let etag='',timer=null,pending=false,changed=false,lastCheck=0;
 function observe(response){etag=response.headers.get('ETag')||'';}
 async function check(){
  if(!etag||pending||changed||document.hidden||Date.now()-lastCheck<10000)return;
  pending=true;lastCheck=Date.now();
  try{const response=await fetch('data.json',{method:'HEAD',cache:'no-store'}),next=response.headers.get('ETag');
   if(response.ok&&next&&next!==etag){changed=true;const notice=document.getElementById('dataset-update');if(notice)notice.hidden=false;}
  }catch{}finally{pending=false;}
 }
 function start(){if(timer!==null)return;const button=document.getElementById('reload-dataset');if(button)button.onclick=()=>location.reload();window.addEventListener('focus',check);document.addEventListener('visibilitychange',check);timer=setInterval(check,120000);}
 return {observe,start,check};
})();
