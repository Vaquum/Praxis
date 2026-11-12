import {spawnSync} from 'node:child_process';
import fs from 'node:fs/promises';
import {gzipSync} from 'node:zlib';
import path from 'node:path';
import {withServer} from './proof-server.mjs';

let js = 0;
let css = 0;
for (const name of await fs.readdir('reader-build/assets')) {
  const extension = path.extname(name);
  if (extension !== '.mjs' && extension !== '.css') continue;
  const bytes = gzipSync(await fs.readFile(path.join('reader-build/assets', name))).length;
  if (extension === '.mjs') js += bytes;
  else css += bytes;
}
if (js > 60 * 1024 || css > 24 * 1024) {
  throw Error(`Reader asset budget exceeded: JS ${js}, CSS ${css}`);
}

await withServer('scripts/serve-reader.mjs', {READER_PORT: '0'}, port => {
  const result = spawnSync(process.execPath, ['node_modules/@playwright/test/cli.js', 'test'], {
    stdio: 'inherit',
    timeout: 180000,
    env: {...process.env, READER_PORT: String(port)}
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw Error('Reader browser checks failed: ' + result.status);
  console.log(`Reader browser checks passed. JS ${js}B gzip, CSS ${css}B gzip.`);
});
