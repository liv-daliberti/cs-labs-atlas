import {mkdir,readdir,readFile,writeFile,copyFile,rm,lstat} from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gzipSync,gunzipSync} from 'node:zlib';
import {restoreAtlasAssets} from './source-atlas-assets.mjs';
await restoreAtlasAssets();
const root=process.cwd(), source=path.resolve(process.argv[2]||'atlas'), mode=process.argv[3]||'r2';
if(!['bootstrap','r2'].includes(mode))throw new Error('Expected bootstrap or r2 mode');
if(source===path.join(root,'public')||source===path.join(root,'dist'))throw new Error('Keep canonical atlas sources separate from generated framework output');
const sha=b=>createHash('sha256').update(b).digest('hex');
const mime=name=>name.endsWith('.pdf')?'application/pdf':name.endsWith('.txt')?'text/plain; charset=utf-8':name.endsWith('.json')?'application/json; charset=utf-8':name.endsWith('.html')?'text/html; charset=utf-8':name.endsWith('.js')?'text/javascript; charset=utf-8':name.endsWith('.css')?'text/css; charset=utf-8':name.endsWith('.csv')?'text/csv; charset=utf-8':name.endsWith('.svg')?'image/svg+xml':name.endsWith('.png')?'image/png':name.endsWith('.jpg')||name.endsWith('.jpeg')?'image/jpeg':name.endsWith('.webp')?'image/webp':name.endsWith('.gz')?'application/gzip':name.endsWith('.xz')?'application/x-xz':name.endsWith('.xlsx')?'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':'application/octet-stream';
async function walk(dir,prefix=''){let files=[];for(const e of (await readdir(dir,{withFileTypes:true})).sort((a,b)=>a.name.localeCompare(b.name))){if(e.name.startsWith('.'))continue;const relative=prefix+e.name,full=path.join(dir,e.name);if(e.isSymbolicLink())throw new Error('Symlinks are not atlas assets');if(e.isDirectory())files.push(...await walk(full,relative+'/'));else if(e.isFile())files.push(relative);}return files;}
// Paper bytes are admitted only by the release's reader index. Historical local
// PDFs, page images and extracted text must not bypass that allowlist as assets.
const files={},bootstrap={},paths=(await walk(source)).filter(name=>!name.startsWith('papers/'));let sourceBytes=0,publicBytes=0,embeddedBytes=0;
await rm(path.join(root,'public'),{recursive:true,force:true});await mkdir(path.join(root,'public'),{recursive:true});
for(const name of paths){
  const full=path.join(source,name),bytes=await readFile(full),entry={sha256:sha(bytes),size:bytes.length,type:mime(name)};
  if(mode==='r2'&&bytes.length>96*2**20){
    if(!['data/princeton-students.json','downloads/princeton_students.json'].includes(name)||bytes.length>512*2**20)throw new Error('Unsupported oversized asset: '+name);
    entry.storage='chunks-v1';entry.chunks=[];
    await mkdir(path.join(root,'atlas-storage/chunks'),{recursive:true});
    for(let offset=0;offset<bytes.length;offset+=32*2**20){
      const part=bytes.subarray(offset,offset+32*2**20),hash=sha(part);
      await writeFile(path.join(root,'atlas-storage/chunks',hash),part);
      entry.chunks.push({offset,size:part.length,sha256:hash});
    }
  }
  files[name]=entry;sourceBytes+=bytes.length;
  if(mode==='bootstrap'){
    // Compress textual payloads inside the transitional Worker. Their GET bodies
    // decompress to the exact source bytes, preserving every current URL.
    if(name==='index.html'||((name.endsWith('.json')||name.endsWith('.csv'))&&bytes.length>=65536)){
      const compressed=gzipSync(bytes,{level:9});if(!gunzipSync(compressed).equals(bytes))throw new Error('Compression mismatch');
      bootstrap[name]={...entry,gzip:compressed.toString('base64')};embeddedBytes+=compressed.length;
    }else{const destination=path.join(root,'public',name);await mkdir(path.dirname(destination),{recursive:true});await copyFile(full,destination);publicBytes+=bytes.length;}
  }
}
const manifest=Buffer.from(JSON.stringify({schema:1,files})+'\n'),manifestSha256=sha(manifest);
await mkdir(path.join(root,'atlas-storage/releases'),{recursive:true});
await writeFile(path.join(root,'atlas-storage/releases',manifestSha256+'.json'),manifest);
await writeFile(path.join(root,'atlas-storage/upload-plan.json'),JSON.stringify({schema:1,sourceDirectory:source,manifestSha256,manifestFile:'atlas-storage/releases/'+manifestSha256+'.json',files},null,2)+'\n');
await writeFile(path.join(root,'lib/atlas-release.json'),JSON.stringify({manifestSha256,mode})+'\n');
await writeFile(path.join(root,'lib/atlas-bootstrap.json'),JSON.stringify(bootstrap)+'\n');
await writeFile(path.join(root,'atlas-storage/preparation.json'),JSON.stringify({mode,files:paths.length,sourceBytes,publicBytes,embeddedGzipBytes:embeddedBytes,manifestSha256},null,2)+'\n');
console.log(JSON.stringify({mode,files:paths.length,sourceBytes,publicBytes,embeddedGzipBytes:embeddedBytes,manifestSha256}));
