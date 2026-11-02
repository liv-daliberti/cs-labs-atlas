// Keep large canonical assets reproducible without oversized Git objects.
import {createHash} from 'node:crypto';
import {readFile,writeFile,mkdir,readdir,rename} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const manifestPath=path.join(root,'atlas-source/manifest.json');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
async function readManifest(){try{return JSON.parse(await readFile(manifestPath,'utf8'));}catch(e){if(e.code==='ENOENT')return {schema:1,files:{}};throw e;}}
function target(name){
  if(name.startsWith('/')||name.includes('\\')||name.split('/').some(x=>!x||x==='.'||x==='..'))throw new Error('Invalid source asset path');
  return path.join(root,'atlas',name);
}
export async function restoreAtlasAssets(){
  const manifest=await readManifest();if(manifest.schema!==1)throw new Error('Unknown source asset schema');
  for(const [name,entry] of Object.entries(manifest.files)){
    const destination=target(name);let current;
    try{current=await readFile(destination);}catch(e){if(e.code!=='ENOENT')throw e;}
    if(current&&current.length===entry.size&&sha(current)===entry.sha256)continue;
    if(current)throw new Error('Canonical asset changed; run source-atlas-assets.mjs pack before building: '+name);
    const pieces=[];
    for(const piece of entry.chunks){
      if(!/^[a-f0-9]{64}$/.test(piece.sha256))throw new Error('Invalid source chunk');
      const bytes=await readFile(path.join(root,'atlas-source/chunks',piece.sha256));
      if(bytes.length!==piece.size||sha(bytes)!==piece.sha256)throw new Error('Source chunk checksum mismatch');
      pieces.push(bytes);
    }
    const bytes=Buffer.concat(pieces);
    if(bytes.length!==entry.size||sha(bytes)!==entry.sha256)throw new Error('Reconstructed source asset mismatch');
    await mkdir(path.dirname(destination),{recursive:true});
    await writeFile(destination+'.restoring',bytes);await rename(destination+'.restoring',destination);
  }
}
async function pack(){
  const manifest=await readManifest();
  async function scan(directory,prefix=''){
    for(const entry of await readdir(directory,{withFileTypes:true})){
      if(entry.name.startsWith('.'))continue;
      if(prefix===''&&entry.name==='papers')continue; // Reader objects use the frozen release's store allowlist.
      const name=prefix+entry.name;
      if(entry.isDirectory()){await scan(path.join(directory,entry.name),name+'/');continue;}
      if(!entry.isFile())throw new Error('Unsupported asset entry');
      const bytes=await readFile(target(name));
      if(bytes.length<24*2**20&&!manifest.files[name])continue;
      const chunks=[];await mkdir(path.join(root,'atlas-source/chunks'),{recursive:true});
      for(let offset=0;offset<bytes.length;offset+=16*2**20){
        const piece=bytes.subarray(offset,offset+16*2**20),hash=sha(piece);
        await writeFile(path.join(root,'atlas-source/chunks',hash),piece);
        chunks.push({sha256:hash,size:piece.length});
      }
      manifest.files[name]={sha256:sha(bytes),size:bytes.length,chunks};
    }
  }
  await scan(path.join(root,'atlas'));
  await writeFile(manifestPath,JSON.stringify(manifest,null,2)+'\n');
  const ignorePath=path.join(root,'.gitignore'),start='# BEGIN chunked atlas assets',end='# END chunked atlas assets';
  let ignore=await readFile(ignorePath,'utf8');
  const block=[start,...Object.keys(manifest.files).sort().map(name=>'/atlas/'+name),end].join('\n');
  if(ignore.includes(start))ignore=ignore.slice(0,ignore.indexOf(start))+block+ignore.slice(ignore.indexOf(end)+end.length);
  else ignore=ignore.trimEnd()+'\n\n'+block+'\n';
  await writeFile(ignorePath,ignore);
  await restoreAtlasAssets();
  console.log(JSON.stringify({packedAssets:Object.keys(manifest.files).length,sourceBytes:Object.values(manifest.files).reduce((n,x)=>n+x.size,0),maximumChunkBytes:16*2**20}));
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  if(process.argv[2]==='pack')await pack();
  else if(!process.argv[2]||process.argv[2]==='restore')await restoreAtlasAssets();
  else throw new Error('Expected pack or restore');
}
