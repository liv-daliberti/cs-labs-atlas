import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {princetonRelease,servePrinceton} from '../lib/princeton-release.mjs';
const sha=b=>createHash('sha256').update(b).digest('hex');
class Bucket{
  objects=new Map();
  async put(key,body,options={}){
    const b=Buffer.from(await new Response(body).arrayBuffer()),current=this.objects.get(key);
    if(options.sha256&&options.sha256!==sha(b))throw new Error('Checksum mismatch');
    if(options.onlyIf?.etagDoesNotMatch==='*'&&current)return null;
    if(options.onlyIf?.etagMatches&&(!current||options.onlyIf.etagMatches!==sha(current)))return null;
    this.objects.set(key,b);return this.head(key);
  }
  async head(key){const b=this.objects.get(key);return b?{size:b.length,etag:sha(b),checksums:{sha256:Uint8Array.from(Buffer.from(sha(b),'hex')).buffer}}:null;}
  async get(key){const b=this.objects.get(key);return b?{...await this.head(key),body:new Blob([b]).stream(),json:async()=>JSON.parse(b)}:null;}
}
const request=(data,method='PUT')=>new Request('https://atlas.test/api/princeton-release',{method,...(method==='PUT'?{body:JSON.stringify(data),headers:{'Content-Type':'application/json'}}:{})});
async function setup(){
  const bucket=new Bucket(),body=Buffer.from('gzip fixture'),digest=sha(body);
  await bucket.put('objects/'+digest,body,{sha256:digest});
  const files={'data/princeton-network.json.gz':{sha256:digest,size:body.length,type:'application/gzip'}};
  const save=async files=>{const b=Buffer.from(JSON.stringify({schema:1,files})),s=sha(b);await bucket.put('objects/'+s,b,{sha256:s});return s;};
  return {bucket,body,files,save,env:{ATLAS_BUCKET:bucket},manifest:await save(files)};
}
test('publishes verified graph atomically, serves exact bytes, rejects stale update',async()=>{
  const x=await setup();
  assert.equal((await princetonRelease(request(null,'GET'),x.env)).status,200);
  let r=await princetonRelease(request({manifestSha256:x.manifest,previousManifestSha256:null}),x.env);
  assert.equal(r.status,201);const receipt=await r.json();assert.ok(x.bucket.objects.has('objects/'+receipt.receiptSha256));
  r=await servePrinceton(new Request('https://atlas.test/data/princeton-network.json.gz'),x.env);
  assert.equal(r.status,200);assert.deepEqual(Buffer.from(await r.arrayBuffer()),x.body);
  assert.equal((await princetonRelease(request({manifestSha256:x.manifest,previousManifestSha256:null}),x.env)).status,409);
  assert.equal(await servePrinceton(new Request('https://atlas.test/index.html'),x.env),null);
});
test('rejects missing assets, incorrect sizes, and updates to unrelated atlas files',async()=>{
  const x=await setup();
  for(const files of [
    {'data/princeton-network.json.gz':{sha256:'f'.repeat(64),size:3,type:'application/gzip'}},
    {'data/princeton-network.json.gz':{...x.files['data/princeton-network.json.gz'],size:99}},
    {...x.files,'index.html':{...x.files['data/princeton-network.json.gz'],type:'text/html'}}
  ]){
    const manifest=await x.save(files);
    assert.equal((await princetonRelease(request({manifestSha256:manifest,previousManifestSha256:null}),x.env)).status,400);
  }
  assert.equal(x.bucket.objects.has('updates/princeton/current.json'),false);
});
test('compare-and-swap allows only one concurrent publisher',async()=>{
  const x=await setup(),input={manifestSha256:x.manifest,previousManifestSha256:null};
  const results=await Promise.all([princetonRelease(request(input),x.env),princetonRelease(request(input),x.env)]);
  assert.deepEqual(results.map(r=>r.status).sort(),[201,409]);
});
