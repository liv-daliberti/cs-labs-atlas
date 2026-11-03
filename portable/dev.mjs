import { spawnSync } from 'node:child_process';
import { createAtlasServer } from './server.mjs';
const result = spawnSync(process.execPath, ['portable/create-fixture.mjs'], { stdio: 'inherit' });
if (result.status) process.exit(result.status);
const server = await createAtlasServer('outputs/fixture');
server.listen(8787, '127.0.0.1', () =>
  console.log(
    'Synthetic development dataset: http://127.0.0.1:8787 (both pages; not research evidence)',
  ),
);
