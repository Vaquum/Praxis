import SECURITY_HEADERS from './security-headers.json' with {type: 'json'};
import CONTENT from '../reader/content.json' with {type: 'json'};

function withSecurityHeaders(response) {
  const secured = new Response(response.body, response);
  for (const [key, value] of Object.entries(SECURITY_HEADERS)) {
    secured.headers.set(key, value);
  }
  return secured;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const basePath = env.DOCS_BASE_PATH ?? CONTENT.product.basePath;

    if (basePath && (url.pathname === '/' || url.pathname === basePath)) {
      url.pathname = basePath + '/';
      return withSecurityHeaders(Response.redirect(url, 302));
    }

    if (basePath && ['/robots.txt', '/sitemap.xml'].includes(url.pathname)) {
      url.pathname = basePath + url.pathname;
      return withSecurityHeaders(Response.redirect(url, 302));
    }

    if (!url.pathname.startsWith(basePath + '/')) {
      return withSecurityHeaders(new Response('Not found', { status: 404 }));
    }

    url.pathname = url.pathname.slice(basePath.length);

    return withSecurityHeaders(await env.ASSETS.fetch(new Request(url, request)));
  },
};
