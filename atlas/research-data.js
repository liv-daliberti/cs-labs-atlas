/* Lossless loading of packaged bibliography assets. */
'use strict';
window.readResearchJSON=async function(path){
 const compressed=path.endsWith('.json.gz')||/-(?:sweep|research|students|lab-connections)\.json$/.test(path);
 const target=path.endsWith('.gz')?path:compressed?path+'.gz':path;
 const response=await fetch(target,{cache:'no-cache'});
 if(!response.ok)throw Error('Could not load '+target+': '+response.status);
 if(!compressed)return response.json();
 const bytes=new Uint8Array(await response.arrayBuffer());
 if(bytes[0]===0x1f&&bytes[1]===0x8b){
  const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
  return new Response(stream).json();
 }
 // Some hosts apply Content-Encoding and the browser decompresses automatically.
 return JSON.parse(new TextDecoder().decode(bytes));
};
