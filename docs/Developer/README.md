# Developer Home

This is the starting point for contributing to Praxis itself. Use it to find the right maintenance path before you change code, docs, or release metadata.

For cross-product Vaquum process and organization-wide norms, see the external [Vaquum Developer Docs](https://dev-docs.vaquum.fi/#/). Use the pages below for Praxis-specific contribution and maintenance rules that still belong in this repo.

## Read This First

Before opening or updating a Praxis PR:

- read the relevant Praxis page for the task you are doing
- check the repo PR template and satisfy every applicable item
- update docs, changelog, tests, and version metadata when the change requires it
- treat the code as authoritative when it diverges from RFC-4001

## Route By Task

| If you are doing this | Read this next | Why |
|---|---|---|
| changing docs structure, navigation, or page roles | [Documentation System Contract](Documentation-System.md) | Defines the docs architecture, page types, site model, and rewrite rules. |
| reasoning about intended architecture versus current implementation | [RFC-4001](https://github.com/Vaquum/Praxis/issues/1) | Defines the design target that current code only partially implements. |
| checking known constraints in the shipped implementation | [../TechnicalDebt.md](../TechnicalDebt.md) | Captures current debt and migration notes already acknowledged in the repo. |

## Common Contributor Workflow

1. Understand the affected subsystem and read the canonical page for it.
2. Compare the intended model in RFC-4001 with the current implementation when that distinction matters.
3. Make the code change, doc change, or release metadata change together when they belong together.
4. Run the relevant validation locally.
5. Review the full GitHub diff yourself before requesting review.
6. Make sure the PR template items are genuinely true, not just checked.

## Scope Notes

- `/docs` is the canonical public docs layer.
- `/docs/Developer` is the canonical Praxis contributor layer.
- RFC-4001 is the canonical design target, but not the canonical source of current runtime behavior.
- repository code is the final source of truth for shipped behavior.

## Read Next

- [Documentation System Contract](Documentation-System.md)
- [Technical Debt](../TechnicalDebt.md)
- [RFC-4001](https://github.com/Vaquum/Praxis/issues/1)
