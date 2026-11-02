import {serveAtlas} from './atlas-storage.mjs';
import {GRAPH_PATH, INDEX_PATH, MAX_ASSET_READS, validateChunks, verifyChunkedGraph, chunkRuntimeProbe, verifiedObject} from './chunked-graph.mjs';

const KEY = 'updates/princeton/current.json';
const HEX = /^[a-f0-9]{64}$/;
const ALLOWED = /^data\/princeton-network(?:-[a-z0-9]+)?\.json(?:\.gz)?$/;
const headers = {'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'};
const json = (data,status=200) => Response.json(data,{status,headers});
const hex = value => [...new Uint8Array(value)].map(x=>x.toString(16).padStart(2,'0')).join('');

async function readBoundedInput(request) {
  if(!request.body)throw new Error('Missing request body');
  const reader=request.body.getReader(),parts=[];let size=0;
  try{
    for(;;){
      const {done,value}=await reader.read();if(done)break;
      size+=value.byteLength;
      if(size>8192){await reader.cancel();throw new RangeError('Request too large');}
      parts.push(value);
    }
  }finally{reader.releaseLock();}
  const bytes=new Uint8Array(size);let offset=0;
  for(const part of parts){bytes.set(part,offset);offset+=part.byteLength;}
  return JSON.parse(new TextDecoder().decode(bytes));
}

// Every route is behind the confirmed owner-private Sites dispatch boundary.
// Credentials are acquired per run and never appear in this application.
export async function princetonRelease(request,env) {
  const bucket=env.ATLAS_BUCKET;
  if(!bucket)return json({error:'Storage unavailable'},503);
  const existing=await bucket.get(KEY);
  const previous=existing?await existing.json():null;
  if(request.method==='GET') {
    if(new URL(request.url).searchParams.get('probe')==='chunks-v1')return json(await chunkRuntimeProbe());
    return json(previous||{manifestSha256:null,updatedAt:null});
  }
  if(request.method!=='PUT')return json({error:'Method not allowed'},405);
  if(Number(request.headers.get('Content-Length')||0)>8192)return json({error:'Request too large'},413);
  let input;
  try {input=await readBoundedInput(request);} catch(error) {return json({error:error instanceof RangeError?'Request too large':'Invalid JSON'},error instanceof RangeError?413:400);}
  if(!input||!HEX.test(input.manifestSha256||'')||!(input.previousManifestSha256===null||HEX.test(input.previousManifestSha256||'')))return json({error:'Manifest and previous revision are required'},400);
  if((previous?.manifestSha256||null)!==input.previousManifestSha256)return json({error:'Release changed; read and merge the latest data first',current:previous?.manifestSha256||null},409);
  const object=await bucket.get('objects/'+input.manifestSha256);
  if(!object||object.size>1024*1024||!object.checksums?.sha256||hex(object.checksums.sha256)!==input.manifestSha256)return json({error:'Verified manifest not found'},400);
  let manifest;
  try {manifest=await object.json();}catch{return json({error:'Invalid manifest JSON'},400);}
  if(manifest.schema!==1||!manifest.files||Array.isArray(manifest.files)||typeof manifest.files!=='object')return json({error:'Invalid release manifest'},400);
  const files=Object.entries(manifest.files);
  if(!files.length||files.length>32||!manifest.files['data/princeton-network.json.gz'])return json({error:'Release must contain the Princeton graph and at most 32 assets'},400);
  let assetReads=0;
  for(const [name,entry] of files){
    if(!ALLOWED.test(name)||!entry||typeof entry!=='object'||Array.isArray(entry))return json({error:'Invalid Princeton data asset'},400);
    if(entry.storage==='chunks-v1'){
      try{validateChunks(name,entry);}catch(error){return json({error:error.message},400);}
      if(!manifest.files[INDEX_PATH]||manifest.files[INDEX_PATH].storage!==undefined)return json({error:'Chunked graph releases require a compact browse index'},400);
      assetReads+=entry.chunks.length;
    }else{
      if(entry.storage!==undefined||entry.chunks!==undefined||!HEX.test(entry.sha256||'')||!Number.isSafeInteger(entry.size)||entry.size<1||entry.size>96*2**20||entry.type!==(name.endsWith('.gz')?'application/gzip':'application/json; charset=utf-8'))return json({error:'Invalid Princeton data asset'},400);
      assetReads++;
    }
  }
  if(assetReads>MAX_ASSET_READS)return json({error:'Release exceeds the asset-read budget'},400);
  // Check small ordinary assets before spending streaming work on the graph.
  for(const [,entry] of files.filter(([,entry])=>entry.storage!=='chunks-v1')){
    if(!verifiedObject(await bucket.head('objects/'+entry.sha256),entry))return json({error:'Release references an unverified asset'},400);
  }
  const graph=manifest.files[GRAPH_PATH];
  if(graph.storage==='chunks-v1'){
    try{await verifyChunkedGraph(bucket,graph);}catch(error){return json({error:'Chunked graph verification failed: '+error.message},400);}
  }
  const next={schema:1,manifestSha256:input.manifestSha256,previousManifestSha256:input.previousManifestSha256,updatedAt:new Date().toISOString(),note:String(input.note||'').slice(0,500)};
  const bytes=new TextEncoder().encode(JSON.stringify(next)+'\n');
  const checksum=hex(await crypto.subtle.digest('SHA-256',bytes));
  await bucket.put('objects/'+checksum,bytes,{sha256:checksum,onlyIf:{etagDoesNotMatch:'*'},httpMetadata:{contentType:'application/json'}});
  const saved=await bucket.put(KEY,bytes,{sha256:checksum,onlyIf:existing?{etagMatches:existing.etag}:{etagDoesNotMatch:'*'},httpMetadata:{contentType:'application/json'}});
  if(!saved)return json({error:'Concurrent update; read and merge the latest data first'},409);
  return json({...next,receiptSha256:checksum},201);
}

export async function servePrinceton(request,env){
  let name;
  try{name=decodeURIComponent(new URL(request.url).pathname).replace(/^\/+/, '');}catch{return null;}
  if(!ALLOWED.test(name)||!env.ATLAS_BUCKET)return null;
  const pointer=await env.ATLAS_BUCKET.get(KEY);
  if(!pointer)return null;
  const current=await pointer.json();
  if(!HEX.test(current.manifestSha256||''))return json({error:'Princeton release unavailable'},503);
  return serveAtlas(request,env,{manifestSha256:current.manifestSha256,mode:'r2'});
}
