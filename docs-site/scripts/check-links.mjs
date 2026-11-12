import {execFileSync} from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
import {content, hash} from '../reader/render.mjs';

const output = 'reader-build';
const {basePath, origin} = content.product;
const build = JSON.parse(await fs.readFile(path.join(output, 'build.json'), 'utf8'));
const routes = JSON.parse(await fs.readFile(path.join(output, 'routes.json'), 'utf8'));
const search = JSON.parse(await fs.readFile(path.join(output, 'search.json'), 'utf8'));
const head = execFileSync('git', ['rev-parse', 'HEAD'], {encoding: 'utf8'}).trim();
if (build.head !== head) throw Error('Reader build belongs to a different checkout revision');

for (const [name, expected] of Object.entries(build.files)) {
  if (hash(await fs.readFile(path.join(output, name))) !== expected) {
    throw Error('Built reader member changed: ' + name);
  }
}

const htmlByUrl = new Map();
for (const {source, url, sha256} of routes) {
  if (source && hash(await fs.readFile(path.join('..', source))) !== sha256) {
    throw Error('Reader source changed since build: ' + source);
  }
  const html = await fs.readFile(path.join(output, url.slice(basePath.length), 'index.html'), 'utf8');
  htmlByUrl.set(url, html);
}
htmlByUrl.set(basePath + '/404.html', await fs.readFile(path.join(output, '404.html'), 'utf8'));

const anchors = new Map([...htmlByUrl].map(([url, html]) =>
  [url, new Set([...html.matchAll(/\sid="([^"]+)"/g)].map(match => match[1]))]));
const failures = new Set();
function check(target, from) {
  const {pathname, hash, origin: destination} = new URL(target.replaceAll('&amp;', '&'), origin + from);
  if (destination !== origin || !pathname.startsWith(basePath + '/')) return;
  if (anchors.has(pathname)) {
    const anchor = decodeURIComponent(hash.slice(1)).replace(/-L(\d+)-L\d+$/, '-L$1');
    if (anchor && !anchors.get(pathname).has(anchor)) failures.add(from + ' → ' + pathname + hash);
  } else if (!Object.hasOwn(build.files, decodeURIComponent(pathname.slice(basePath.length + 1)))) {
    failures.add(from + ' → ' + pathname);
  }
}
for (const [url, html] of htmlByUrl) {
  for (const match of html.matchAll(/\s(?:href|src)="([^"]+)"/g)) check(match[1], url);
}
const searchable = new Set();
for (const item of search) {
  check(item.route, basePath + '/search.json');
  searchable.add(item.route.split('#')[0]);
}
for (const {url} of routes) {
  if (!searchable.has(url)) failures.add('Missing from search: ' + url);
}
if (failures.size) throw Error('Broken reader destinations:\n' + [...failures].join('\n'));
console.log('Links, search and source hashes verified for ' + routes.length + ' reader routes.');
