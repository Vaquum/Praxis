import fs from 'node:fs/promises';
import fsSync from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const scriptPath = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(scriptPath), '..', '..');
const siteRoot = path.resolve(repoRoot, 'docs-site');
const outRoot = path.resolve(siteRoot, '.generated', 'docs');

const repoBlobBaseUrl = 'https://github.com/Vaquum/Praxis/blob/main';
const repoTreeBaseUrl = 'https://github.com/Vaquum/Praxis/tree/main';

const sectionCategories = [
  {
    dir: 'overview',
    label: 'Overview',
    position: 1,
    slug: '/overview',
    description: 'What Praxis is, how it fits into Vaquum, and where to start.'
  },
  {
    dir: 'guides',
    label: 'Guides',
    position: 2,
    slug: '/guides',
    description: 'Practical workflows for installing, verifying, and understanding Praxis.'
  },
  {
    dir: 'reference',
    label: 'Reference',
    position: 3,
    slug: '/reference',
    description: 'Current interfaces, runtime boundaries, and implementation reference for Praxis.'
  },
  {
    dir: 'developer',
    label: 'Developer',
    position: 4,
    slug: '/developer',
    description: 'Contributor and maintainer guidance for the Praxis docs and codebase.'
  },
  {
    dir: 'packages',
    label: 'Packages',
    position: 5,
    slug: '/packages',
    description: 'Module ownership, boundaries, and canonical entry points inside Praxis.'
  }
];

const docs = [
  {
    source: 'README.md',
    dest: 'index.md',
    slug: '/',
    title: 'Praxis',
    sidebarLabel: 'Home'
  },
  {
    source: 'docs/README.md',
    dest: 'overview/docs-hub.md',
    slug: '/overview/docs-hub',
    sidebarPosition: 1
  },
  {
    source: 'docs/TechnicalDebt.md',
    dest: 'overview/technical-debt.md',
    slug: '/overview/technical-debt',
    sidebarPosition: 2,
    title: 'Technical Debt'
  },
  {
    source: 'docs/Setup-And-Verification.md',
    dest: 'guides/setup-and-verification.md',
    slug: '/guides/setup-and-verification',
    sidebarPosition: 1,
    title: 'Setup And Verification'
  },
  {
    source: 'docs/Launcher.md',
    dest: 'guides/launcher.md',
    slug: '/guides/launcher',
    sidebarPosition: 2,
    title: 'Launcher'
  },
  {
    source: 'docs/Trading.md',
    dest: 'guides/trading.md',
    slug: '/guides/trading',
    sidebarPosition: 3,
    title: 'Trading'
  },
  {
    source: 'docs/Trade-Lifecycle.md',
    dest: 'guides/trade-lifecycle.md',
    slug: '/guides/trade-lifecycle',
    sidebarPosition: 4,
    title: 'Trade Lifecycle'
  },
  {
    source: 'docs/Binance-Spot-Testnet.md',
    dest: 'guides/binance-spot-testnet.md',
    slug: '/guides/binance-spot-testnet',
    sidebarPosition: 5,
    title: 'Binance Spot Testnet'
  },
  {
    source: 'docs/Developer/README.md',
    dest: 'developer/developer-home.md',
    slug: '/developer/home',
    sidebarPosition: 1,
    sidebarLabel: 'Developer Home'
  },
  {
    source: 'docs/Developer/Documentation-System.md',
    dest: 'developer/documentation-system.md',
    slug: '/developer/documentation-system',
    sidebarPosition: 2
  },
  {
    source: 'docs/Event-Spine.md',
    dest: 'reference/event-spine.md',
    slug: '/reference/event-spine',
    sidebarPosition: 1,
    title: 'Event Spine'
  },
  {
    source: 'docs/Trading-State.md',
    dest: 'reference/trading-state.md',
    slug: '/reference/trading-state',
    sidebarPosition: 2,
    title: 'Trading State'
  },
  {
    source: 'docs/Venue-Adapter.md',
    dest: 'reference/venue-adapter.md',
    slug: '/reference/venue-adapter',
    sidebarPosition: 3,
    title: 'Venue Adapter'
  },
  {
    source: 'docs/Execution-Manager.md',
    dest: 'reference/execution-manager.md',
    slug: '/reference/execution-manager',
    sidebarPosition: 4,
    title: 'Execution Manager'
  },
  {
    source: 'docs/Recovery-And-Reconciliation.md',
    dest: 'reference/recovery-and-reconciliation.md',
    slug: '/reference/recovery-and-reconciliation',
    sidebarPosition: 5,
    title: 'Recovery And Reconciliation'
  },
  {
    source: 'docs/Trade-Outcomes.md',
    dest: 'reference/trade-outcomes.md',
    slug: '/reference/trade-outcomes',
    sidebarPosition: 6,
    title: 'Trade Outcomes'
  },
  {
    source: 'docs/Slippage-And-Order-Book.md',
    dest: 'reference/slippage-and-order-book.md',
    slug: '/reference/slippage-and-order-book',
    sidebarPosition: 7,
    title: 'Slippage And Order Book'
  },
  {
    source: 'praxis/README.md',
    dest: 'packages/praxis.md',
    slug: '/packages/praxis',
    sidebarPosition: 1,
    sidebarLabel: 'Praxis'
  },
  {
    source: 'praxis/core/README.md',
    dest: 'packages/core.md',
    slug: '/packages/core',
    sidebarPosition: 2,
    sidebarLabel: 'Core'
  },
  {
    source: 'praxis/core/domain/README.md',
    dest: 'packages/core-domain.md',
    slug: '/packages/core-domain',
    sidebarPosition: 3,
    sidebarLabel: 'Core Domain'
  },
  {
    source: 'praxis/infrastructure/README.md',
    dest: 'packages/infrastructure.md',
    slug: '/packages/infrastructure',
    sidebarPosition: 4,
    sidebarLabel: 'Infrastructure'
  }
];

const mappingBySource = new Map(docs.map((doc) => [normalizePath(doc.source), doc]));

function normalizePath(value) {
  return value.split(path.sep).join('/');
}

async function ensureDir(dir) {
  await fs.mkdir(dir, {recursive: true});
}

async function writeJson(filePath, value) {
  await ensureDir(path.dirname(filePath));
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`);
}

function buildFrontMatter(doc) {
  const lines = ['---'];

  if (doc.slug) {
    lines.push(`slug: ${doc.slug}`);
  }
  if (doc.title) {
    lines.push(`title: ${doc.title}`);
  }
  if (typeof doc.sidebarPosition === 'number') {
    lines.push(`sidebar_position: ${doc.sidebarPosition}`);
  }
  if (doc.sidebarLabel) {
    lines.push(`sidebar_label: ${doc.sidebarLabel}`);
  }
  if (doc.dest === 'index.md') {
    lines.push('pagination_next: null');
    lines.push('pagination_prev: null');
  }

  if (!doc.source.startsWith('virtual:')) {
    lines.push(`custom_edit_url: ${repoBlobBaseUrl}/${doc.source}`);
  }

  lines.push('---', '');
  return lines.join('\n');
}

function resolveDocLink(fromSource, target) {
  if (
    !target ||
    target.startsWith('http://') ||
    target.startsWith('https://') ||
    target.startsWith('mailto:') ||
    target.startsWith('#')
  ) {
    return target;
  }

  const [targetPath, targetHash] = target.split('#');
  if (!targetPath) {
    return target;
  }
  if (targetPath.startsWith('/')) {
    return target;
  }

  const resolvedSource = normalizePath(
    path.posix.normalize(
      path.posix.join(path.posix.dirname(normalizePath(fromSource)), targetPath)
    )
  );
  let targetDoc = mappingBySource.get(resolvedSource);

  if (!targetDoc && !path.posix.extname(resolvedSource)) {
    targetDoc = mappingBySource.get(normalizePath(path.posix.join(resolvedSource, 'README.md')));
  }

  if (!targetDoc) {
    const repoFsPath = path.resolve(repoRoot, resolvedSource);
    if (fsSync.existsSync(repoFsPath)) {
      const repoUrlBase = fsSync.statSync(repoFsPath).isDirectory()
        ? repoTreeBaseUrl
        : repoBlobBaseUrl;
      return targetHash ? `${repoUrlBase}/${resolvedSource}#${targetHash}` : `${repoUrlBase}/${resolvedSource}`;
    }
    return target;
  }

  const currentDoc = mappingBySource.get(normalizePath(fromSource));
  const fromDest = currentDoc ? normalizePath(currentDoc.dest) : '';
  const toDest = normalizePath(targetDoc.dest);
  let relative = normalizePath(path.posix.relative(path.posix.dirname(fromDest), toDest));
  if (!relative) {
    relative = path.posix.basename(toDest);
  }
  return targetHash ? `${relative}#${targetHash}` : relative;
}

function rewriteLinks(content, fromSource) {
  return content.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, label, target) => {
    const rewritten = resolveDocLink(fromSource, target.trim());
    return `[${label}](${rewritten})`;
  });
}

function rewriteOutsideCode(content, transform) {
  let out = '';
  let index = 0;
  let inFence = false;
  let inInlineCode = false;
  let plainStart = 0;

  const flush = (endIndex) => {
    if (plainStart >= endIndex) return;
    const chunk = content.slice(plainStart, endIndex);
    out += inFence || inInlineCode ? chunk : transform(chunk);
  };

  while (index < content.length) {
    if (content.startsWith('```', index)) {
      flush(index);
      inFence = !inFence;
      out += '```';
      index += 3;
      plainStart = index;
      continue;
    }

    if (!inFence && content[index] === '`') {
      flush(index);
      inInlineCode = !inInlineCode;
      out += '`';
      index += 1;
      plainStart = index;
      continue;
    }

    index += 1;
  }

  flush(content.length);

  return out;
}

function normalizeForMdx(content) {
  return rewriteOutsideCode(content, (chunk) =>
    chunk
      .replace(
        /<p align="center">([\s\S]*?)<\/p>/g,
        '<div align="center">$1</div>'
      )
      .replace(/<br>/g, '<br />')
      .replace(/<hr>/g, '<hr />')
      .replace(/<img([^>]*?)(?<!\/)>/g, '<img$1 />')
  );
}

async function copyDoc(doc) {
  const destPath = path.resolve(outRoot, doc.dest);
  const raw = doc.source.startsWith('virtual:')
    ? doc.content
    : await fs.readFile(path.resolve(repoRoot, doc.source), 'utf8');
  const rewritten = normalizeForMdx(rewriteLinks(raw, doc.source));
  const output = `${buildFrontMatter(doc)}${rewritten}`;

  await ensureDir(path.dirname(destPath));
  await fs.writeFile(destPath, output);
}

async function writeCategoryFiles() {
  for (const category of sectionCategories) {
    const categoryPath = path.resolve(outRoot, category.dir, '_category_.json');
    await writeJson(categoryPath, {
      label: category.label,
      position: category.position,
      collapsible: true,
      collapsed: false,
      link: {
        type: 'generated-index',
        slug: category.slug,
        title: category.label,
        description: category.description
      }
    });
  }
}

async function main() {
  await fs.rm(outRoot, {recursive: true, force: true});
  await ensureDir(outRoot);
  await writeCategoryFiles();

  for (const doc of docs) {
    await copyDoc(doc);
  }
}

await main();
