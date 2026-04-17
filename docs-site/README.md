# Praxis Docs Site

This is the standalone Praxis docs site scaffold. It follows the same model as Limen:

- Docusaurus for the site runtime
- repository markdown as the canonical content source
- an assembly step that maps repo docs into a generated docs corpus for the site

## Commands

Install dependencies:

```bash
npm install
```

Assemble the generated docs corpus:

```bash
npm run prepare-docs
```

Run the local dev server:

```bash
npm start
```

Run a production-style check build:

```bash
npm run check
```

Build the static site:

```bash
npm run build
```

## Notes

- The canonical source remains the repository markdown in `README.md` and `/docs`.
- Generated docs land in `docs-site/.generated/docs` and should not be committed.
- This scaffold currently maps the shipped Praxis docs plus a few honest bootstrap pages for guides, reference, and packages.
- The current environment here hit a webpack progress-plugin failure on Node `v25.9.0`. Use a supported LTS runtime such as Node `20` or `22` for local site work.
