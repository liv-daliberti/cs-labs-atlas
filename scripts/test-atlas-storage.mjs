import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {serveAtlas,uploadObject} from '../lib/atlas-storage.mjs';
const digest=b=>createHash('sha256').update(b).digest('hex');
// Node test adapter for the native workerd fixed-length streaming API.
globalThis.FixedLengthStream=class extends TransformStream{
 constructor(length){let count=0;super({transform(value,controller){count+=value.byteLength;if(count>length)throw new Error('Fixed length exceeded');controller.enqueue(value);},flush(){if(count!==length)throw new Error('Fixed length truncated');}});}
};

class Bucket{
  objects=new Map(); writes=0;
  async put(key,body,opts={}){
    const b=Buffer.from(await new Response(body).arrayBuffer());
    if(opts.sha256&&digest(b)!==opts.sha256)throw new Error('checksum mismatch');
    if(opts.onlyIf?.etagDoesNotMatch==='*'&&this.objects.has(key))return null;
    this.objects.set(key,b);this.writes++;return this.head(key);
  }
  async head(key){const b=this.objects.get(key);return b?{size:b.length,checksums:{sha256:Uint8Array.from(Buffer.from(digest(b),'hex')).buffer}}:null;}
  async get(key,opts={}){const b=this.objects.get(key),meta=await this.head(key);if(!b)return null;const range=opts.range;return {...meta,body:new Blob([range?b.subarray(range.offset,range.offset+range.length):b]).stream(),json:async()=>JSON.parse(b.toString())};}
}
const request=(url,method='GET',headers={},body)=>new Request('https://atlas.test'+url,{method,headers,...(body!==undefined?{body,duplex:'half'}:{})});
const putRequest=(sha,body)=>request('/api/atlas-storage/'+sha,'PUT',{'Content-Length':String(body.length)},body);
test('uploads validate checksums and remain immutable behind the Sites access boundary',async()=>{
  const b=new Bucket(),env={ATLAS_BUCKET:b},body=Buffer.from('verified bytes'),sha=digest(body);
  assert.equal((await uploadObject(putRequest('0'.repeat(64),body),env)).status,400);assert.equal(b.writes,0);
  let r=await uploadObject(putRequest(sha,body),env);assert.equal(r.status,201);assert.deepEqual(await r.json(),{sha256:sha,size:body.length,already_present:false});
  r=await uploadObject(putRequest(sha,Buffer.from('do not replace')),env);assert.equal(r.status,200);assert.equal(b.writes,1);assert.deepEqual(b.objects.get('objects/'+sha),body);
  assert.equal((await uploadObject(request('/api/atlas-storage/'+sha,'HEAD'),env)).status,200);
});
test('R2 release routes preserve bytes, headers, ranges and release boundaries',async()=>{
  const bucket=new Bucket(),body=Buffer.from('0123456789'),sha=digest(body);
  await bucket.put('objects/'+sha,body,{sha256:sha});
  const bytes=Buffer.from(JSON.stringify({schema:1,files:{'index.html':{sha256:sha,size:10,type:'text/html'},'data/payload.json.gz':{sha256:sha,size:10,type:'application/gzip'}}}));
  const manifestSha256=digest(bytes);await bucket.put('objects/'+manifestSha256,bytes,{sha256:manifestSha256});
  const env={ATLAS_BUCKET:bucket},config={manifestSha256};
  let r=await serveAtlas(request('/'),env,config);assert.equal(r.status,200);assert.equal(await r.text(),'0123456789');assert.equal(r.headers.get('Content-Length'),'10');
  r=await serveAtlas(request('/data/payload.json.gz'),env,config);assert.equal(r.headers.get('Content-Type'),'application/gzip');assert.equal(r.headers.get('Content-Encoding'),null);
  r=await serveAtlas(request('/','HEAD'),env,config);assert.equal(await r.text(),'');assert.equal(r.headers.get('Content-Length'),'10');
  r=await serveAtlas(request('/','GET',{'If-None-Match':'W/"'+sha+'"'}),env,config);assert.equal(r.status,304);
  r=await serveAtlas(request('/','GET',{Range:'bytes=2-5'}),env,config);assert.equal(r.status,206);assert.equal(await r.text(),'2345');assert.equal(r.headers.get('Content-Range'),'bytes 2-5/10');
  r=await serveAtlas(request('/','GET',{Range:'bytes=-3'}),env,config);assert.equal(await r.text(),'789');
  assert.equal((await serveAtlas(request('/','GET',{Range:'bytes=20-30'}),env,config)).status,416);
  r=await serveAtlas(request('/','GET',{Range:'bytes=2-5','If-Range':'"stale"'}),env,config);assert.equal(r.status,200);assert.equal(await r.text(),'0123456789');
  assert.equal((await serveAtlas(request('/missing'),env,config)).status,404);
  assert.equal((await serveAtlas(request('/%00secret'),env,config)).status,404);
  assert.equal((await serveAtlas(request('/'),env,{manifestSha256:'f'.repeat(64)})).status,503);
});
test('every bootstrap/public asset exactly reconstructs the canonical dataset',async()=>{
  const plan=JSON.parse(await readFile('atlas-storage/upload-plan.json')),boot=JSON.parse(await readFile('lib/atlas-bootstrap.json'));
  const config=JSON.parse(await readFile('lib/atlas-release.json'));let embedded=0,staticFiles=0;
  for(const [name,entry]of Object.entries(plan.files)){
    const expected=await readFile(path.join(plan.sourceDirectory,name));assert.equal(digest(expected),entry.sha256,name);
    if(entry.storage==='chunks-v1'){
      const full=createHash('sha256');let offset=0;
      for(const part of entry.chunks){const bytes=await readFile(path.join('atlas-storage/chunks',part.sha256));assert.equal(part.offset,offset);assert.equal(bytes.length,part.size);assert.equal(digest(bytes),part.sha256);full.update(bytes);offset+=bytes.length;}
      assert.equal(offset,entry.size);assert.equal(full.digest('hex'),entry.sha256,name);
    }
    if(boot[name]){
      const response=await serveAtlas(request('/'+name),{},config,boot);assert.equal(response.status,200,name);
      assert.equal(digest(Buffer.from(await response.arrayBuffer())),entry.sha256,name);embedded++;
    }else if(config.mode==='bootstrap'){
      assert.equal(digest(await readFile(path.join('public',name))),entry.sha256,name);staticFiles++;
    }
  }
  const manifest=await readFile(plan.manifestFile);assert.equal(digest(manifest),plan.manifestSha256);
  console.log(JSON.stringify({verifiedFiles:Object.keys(plan.files).length,embedded,staticFiles}));
});
test('compact paper admission serves old and new copies without loading a large descriptive catalogue',async()=>{
 const bucket=new Bucket(),body=Buffer.from('%PDF-1.4 checked test bytes'),sha=digest(body);
 await bucket.put('objects/'+sha,body,{sha256:sha});
 const compact=Buffer.from(JSON.stringify({schema:1,files:{[sha]:body.length}})),cs=digest(compact);
 await bucket.put('objects/'+cs,compact,{sha256:cs});
 const release=Buffer.from(JSON.stringify({schema:1,files:{'data/reader-objects.json':{sha256:cs,size:compact.length,type:'application/json'},'data/local-papers.json':{sha256:'a'.repeat(64),size:20*2**20,type:'application/json'}}})),ms=digest(release);
 await bucket.put('objects/'+ms,release,{sha256:ms});
 const env={ATLAS_BUCKET:bucket},config={manifestSha256:ms};
 const r=await serveAtlas(request('/papers/'+sha+'.pdf','GET',{Range:'bytes=0-7'}),env,config);
 assert.equal(r.status,206);assert.equal(await r.text(),'%PDF-1.4');
 assert.equal((await serveAtlas(request('/papers/'+'b'.repeat(64)+'.pdf'),env,config)).status,404);
 const oldIndex=Buffer.from(JSON.stringify({schema:1,works:{old:{sha256:sha,bytes:body.length,path:'papers/'+sha+'.pdf'}},files:{}})),is=digest(oldIndex);
 await bucket.put('objects/'+is,oldIndex,{sha256:is});
 const oldRelease=Buffer.from(JSON.stringify({schema:1,files:{'data/local-papers.json':{sha256:is,size:oldIndex.length,type:'application/json'}}})),os=digest(oldRelease);
 await bucket.put('objects/'+os,oldRelease,{sha256:os});
 assert.equal((await serveAtlas(request('/papers/'+sha+'.pdf'),env,{manifestSha256:os})).status,200);
});

test('reader release admits XML and withdraws previously hosted files',async()=>{
 const bucket=new Bucket(),old=Buffer.from('%PDF-1.4 withdrawn'),oldSha=digest(old);
 await bucket.put('objects/'+oldSha,old,{sha256:oldSha});
 const xml=Buffer.from('<article><body><p>Approved full text</p></body></article>'),sha=digest(xml);
 await bucket.put('objects/'+sha,xml,{sha256:sha});
 const compact=Buffer.from(JSON.stringify({schema:1,files:{[sha]:xml.length},formats:{[sha]:'xml'}})),cs=digest(compact);
 await bucket.put('objects/'+cs,compact,{sha256:cs});
 const manifest=Buffer.from(JSON.stringify({schema:1,files:{'data/reader-objects.json':{sha256:cs,size:compact.length,type:'application/json'}}})),ms=digest(manifest);
 await bucket.put('objects/'+ms,manifest,{sha256:ms});const env={ATLAS_BUCKET:bucket},config={manifestSha256:ms};
 const response=await serveAtlas(request('/papers/'+sha+'.xml'),env,config);
 assert.equal(response.status,200);assert.equal(response.headers.get('Content-Type'),'application/xml; charset=utf-8');assert.equal(await response.text(),xml.toString());
 assert.equal((await serveAtlas(request('/papers/'+sha+'.pdf'),env,config)).status,404,'wrong format must not be admitted');
 assert.equal((await serveAtlas(request('/papers/'+oldSha+'.pdf'),env,config)).status,404,'stored bytes are not public without release admission');
});

test('large reader papers preserve original hashes and cross-chunk ranges',async()=>{
 const bucket=new Bucket(),a=Buffer.alloc(32*2**20,65),b=Buffer.from('last-page'),whole=Buffer.concat([a,b]),sha=digest(whole);
 const chunks=[a,b].map((bytes,i)=>({sha256:digest(bytes),size:bytes.length,offset:i?a.length:0}));
 for(const [i,bytes] of [a,b].entries())await bucket.put('objects/'+chunks[i].sha256,bytes,{sha256:chunks[i].sha256});
 const compact=Buffer.from(JSON.stringify({schema:1,files:{[sha]:whole.length},chunks:{[sha]:chunks}})),cs=digest(compact);
 await bucket.put('objects/'+cs,compact,{sha256:cs});
 const manifest=Buffer.from(JSON.stringify({schema:1,files:{'data/reader-objects.json':{sha256:cs,size:compact.length,type:'application/json'}}})),ms=digest(manifest);
 await bucket.put('objects/'+ms,manifest,{sha256:ms});const env={ATLAS_BUCKET:bucket},config={manifestSha256:ms},url='/papers/'+sha+'.pdf';
 let response=await serveAtlas(request(url,'GET',{Range:'bytes='+String(a.length-2)+'-'+String(a.length+3)}),env,config);
 assert.equal(response.status,206);assert.equal(await response.text(),'AAlast');
 response=await serveAtlas(request(url),env,config);assert.equal(digest(Buffer.from(await response.arrayBuffer())),sha);
 bucket.objects.delete('objects/'+chunks[1].sha256);
 assert.equal((await serveAtlas(request(url),env,config)).status,503,'missing chunk must fail before serving');
});

test('large people JSON streams across verified chunks with byte ranges and unchanged URLs',async()=>{
 const bucket=new Bucket(),a=Buffer.alloc(32*2**20,65),b=Buffer.from('tail-bytes'),whole=Buffer.concat([a,b]);
 const chunks=[a,b].map((x,i)=>({sha256:digest(x),size:x.length,offset:i?a.length:0}));
 for(const [i,x] of [a,b].entries())await bucket.put('objects/'+chunks[i].sha256,x,{sha256:chunks[i].sha256});
 const entry={storage:'chunks-v1',sha256:digest(whole),size:whole.length,type:'application/json; charset=utf-8',chunks};
 const release=Buffer.from(JSON.stringify({schema:1,files:{'data/princeton-students.json':entry,'downloads/princeton_students.json':entry,'data/not-allowed.json':entry}})),ms=digest(release);
 await bucket.put('objects/'+ms,release,{sha256:ms});const env={ATLAS_BUCKET:bucket},config={manifestSha256:ms};
 let r=await serveAtlas(request('/data/princeton-students.json','HEAD'),env,config);assert.equal(r.status,200);assert.equal(+r.headers.get('Content-Length'),whole.length);assert.equal(r.headers.get('Content-Type'),entry.type);
 r=await serveAtlas(request('/downloads/princeton_students.json','GET',{Range:'bytes='+String(a.length-2)+'-'+String(a.length+3)}),env,config);assert.equal(r.status,206);assert.equal(await r.text(),'AAtail');
 r=await serveAtlas(request('/data/princeton-students.json'),env,config);assert.equal(digest(Buffer.from(await r.arrayBuffer())),entry.sha256);
 assert.equal((await serveAtlas(request('/data/not-allowed.json'),env,config)).status,502);
 bucket.objects.delete('objects/'+chunks[1].sha256);assert.equal((await serveAtlas(request('/data/princeton-students.json'),env,config)).status,503);
});
