import source from './content.json' with {type: 'json'};

const basePath = (process.env.DOCS_BASE_URL ?? source.product.basePath).replace(/\/+$/, '');
if (basePath && !/^\/[\w-]+(?:\/[\w-]+)*$/.test(basePath)) {
  throw Error('DOCS_BASE_URL must be an absolute path');
}

export const content = {
  ...source,
  product: {...source.product, basePath, origin: new URL(process.env.DOCS_SITE_URL ?? source.product.origin).origin}
};
