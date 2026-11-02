import test from 'node:test';
import assert from 'node:assert/strict';
import {protectedAtlasUpdate} from '../lib/atlas-update-auth.mjs';
import {uploadObject} from '../lib/atlas-storage.mjs';
import {princetonRelease} from '../lib/princeton-release.mjs';
const token='test-only-'.repeat(8);
test('maintenance routes reject anonymous, wrong and spoofed-identity requests before storage access',async()=>{
  for(const handler of [uploadObject,princetonRelease])for(const method of ['GET','HEAD','PUT'])for(const headers of [{},{'X-Atlas-Update-Token':'wrong'},{'oai-authenticated-user-email':'owner@example.com'},{'X-Atlas-Update-Token':'x'.repeat(513)}]) {
    const env={ATLAS_UPDATE_TOKEN:token,get ATLAS_BUCKET(){throw Error('Unauthorized storage access');}};
    const response=await protectedAtlasUpdate(handler)(new Request('https://site.test/api/update',{method,headers}),env);
    assert.equal(response.status,403);assert.equal(response.headers.get('Cache-Control'),'private, no-store');
  }
});
test('missing configuration fails closed; exact token alone authorizes the handler',async()=>{
  let calls=0;const handle=protectedAtlasUpdate(()=>{calls++;return new Response('ok');});
  const request=new Request('https://site.test/api/update',{headers:{'X-Atlas-Update-Token':token}});
  for(const expected of [undefined,'', 'short'])assert.equal((await handle(request,{ATLAS_UPDATE_TOKEN:expected})).status,403);
  assert.equal(calls,0);
  assert.equal((await handle(request,{ATLAS_UPDATE_TOKEN:token})).status,200);assert.equal(calls,1);
});
