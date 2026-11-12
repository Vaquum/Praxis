# Praxis docs site

Praxis uses the Limen static reader from Vaquum/Limen at `0927e47e`. The site reads `README.md`, `CHANGELOG.md`, the full `docs/` tree and the package READMEs. `reader/content.json` sets the Book order and the Reference and Developer navigation. Wiki articles and spines get their routes from their source paths. Their YAML evidence is available on the rendered page.

Run these commands from `docs-site` with Node.js 22.

```sh
npm ci
npm start
```

Open [the Praxis book](http://127.0.0.1:4330/praxis/). Run `npm run build` after editing a source. Use `DOCS_BASE_URL=/ npm start` for a root-mounted preview and `READER_PORT` to choose a port.

```sh
npm run check
npm run security:audit
npx playwright install chromium webkit
npm run check:reader
```

The build writes static assets to `reader-build/`. `routes.json` records each source and its SHA-256 digest. `build.json` records the checkout commit and the generated file hashes. `npm run check` verifies source coverage, links and search against the built pages. The browser checks exercise the reader on desktop and mobile using the same asset routing and headers as `src/worker.js`.
