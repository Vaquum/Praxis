# Documentation System Contract

## Purpose

This page defines how Praxis documentation should be structured, written, built, and improved. It is the operating contract for the docs system and the reference point for later documentation changes.

The goal is not only to make individual pages better. The goal is to make Praxis documentation behave like one coherent product.

## What 10/10 Means

For Praxis, 10/10 docs means the full system is:

- accurate to the code and current Vaquum architecture
- easy to enter for a new user
- honest about implemented scope versus RFC intent
- coherent across the product home page, docs hub, and developer docs
- grounded in real runtime behavior, real tests, and real recovery paths
- ready to power a standalone Praxis docs site later and a Vaquum docs portal after that

## Product Docs Model

### Current Site Direction

Praxis should eventually get its own standalone docs site from this repository.

- The initial site build target should be Docusaurus.
- The site should be built in this repository.
- The site should deliver a complete Praxis-only docs experience.
- The site should work as a standalone product site first.
- The site should later be portable into a broader Vaquum docs system without rewriting the content model.
- Canonical content should remain owned by repository markdown, not by site-only copies of the docs.

### Future Vaquum Docs Direction

The long-term target is `docs.vaquum.fi` as the Vaquum documentation entry point.

- `docs.vaquum.fi` should present all Vaquum product docs: Origo, Limen, Nexus, Praxis, and Veritas.
- Each product should still feel discrete, self-contained, and product-native.
- The first Vaquum-wide version should behave like a portal to product docs, not like one merged blob of markdown.
- The Praxis docs system should therefore be designed to plug into a future Vaquum docs shell without losing its own identity.

## Canonical Source Rules

Praxis documentation should have one clear ownership model.

- [README.md](../../README.md) is the product home page and first-success entry point.
- [docs/README.md](../README.md) is the canonical public docs hub.
- `/docs` is the canonical source for public concepts, workflows, and architecture pages.
- `/docs/Developer` is the canonical source for contributor and maintainer process docs.
- RFC-4001 in [issue #1](https://github.com/Vaquum/Praxis/issues/1) is the canonical design target, but not the canonical source of current behavior.
- the repository code is the canonical source for current behavior whenever the docs and RFC do not match implementation.
- examples should be derived from real runnable flows in this repository, not imaginary or hand-waved pseudo-usage.

Content should be authored once whenever possible. If the same explanation appears in multiple places, one page should be canonical and the others should route to it.

## Information Architecture

The docs site should be organized into five top-level sections:

- `Overview`
- `Guides`
- `Reference`
- `Developer`
- `Packages`

The source files can remain in their current repository layout, but the built site should present them through this information architecture.

### Section Responsibilities

- `Overview` explains what Praxis is, what it is not, and how the whole system fits together.
- `Guides` teach workflows and tasks from start to finish.
- `Reference` documents surfaces, invariants, arguments, outputs, and edge cases.
- `Developer` documents contribution, release, maintenance, and internal documentation rules.
- `Packages` explains module ownership, boundaries, entry points, and where to read next.

## Narrative Spine

Every major public page should reinforce the same core Praxis story:

1. Praxis turns trading decisions into venue actions, durable state, and auditable outcomes.
2. Decisions enter through manager-facing trading interfaces and are routed to per-account runtimes.
3. State-changing facts are persisted in the Event Spine and projected into trading state.
4. Venue adapters handle exchange communication, validation, submission, reconciliation, and execution reports.
5. Startup replay and recovery rebuild runtime state from the durable event log.
6. Outcomes move back downstream to manager and broader Vaquum systems.
7. Strategy generation and upstream research happen outside Praxis.

If a page does not help a reader understand its place in that story, it should route clearly to the pages that do.

## Register And Writing Rules

All Praxis documentation should use the same register:

- precise
- technical
- concise
- accessible to an informed new user
- direct rather than academic
- product-truthful rather than hype-driven

### Writing Rules

- Start with what the thing is and why a reader would use it.
- Prefer concrete behavior over abstract framing.
- Keep theory only where it directly improves practical understanding.
- Explain current surface area honestly; do not imply future behavior as present behavior.
- Be explicit when describing RFC intent versus implemented Praxis behavior.
- Prefer examples that show commands, events, outcomes, and recovery effects.
- Do not use unexplained internal jargon.
- Do not duplicate large sections of content across pages.
- End pages with explicit reading routes or next steps when useful.

## Page Types And Required Blocks

Every page should fit one primary page type.

### Home Page

Purpose: product framing and first success.

Required blocks:

- what Praxis is
- what Praxis is not
- capability summary
- first successful verification path
- clear routes into the rest of the docs

### Docs Hub

Purpose: route readers by task and audience.

Required blocks:

- system overview
- reading order by user type
- high-level architecture map
- explicit routes into guides, reference, developer docs, and package docs

### Guide

Purpose: teach a job or workflow from start to finish.

Required blocks:

- what this guide covers
- prerequisites
- current scope
- at least one concrete example
- expected artefacts or outputs
- related pages or next steps

### Reference

Purpose: document an interface or surface comprehensively and predictably.

Required blocks:

- short intro and scope
- conventions or naming rules
- structured entry documentation
- output behavior where relevant
- edge cases or caveats where relevant

### Developer Page

Purpose: guide contributors and maintainers.

Required blocks:

- page purpose
- required reading or prerequisites
- process or checklist
- failure cases or review notes where relevant
- linked related maintenance pages

### Package README

Purpose: orient readers inside a module without replacing canonical public docs.

Required blocks:

- what the package owns
- what it does not own
- key entry points
- major dependencies or adjacent modules
- link to canonical public docs

## Navigation And Cross-Link Rules

Navigation should reduce guesswork.

- The home page and docs hub must both provide reading paths by task.
- Large pages should be indexed near the top.
- Public workflow pages should link forward through the narrative spine.
- Package READMEs should link outward to canonical docs rather than trying to become their own mini-sites.
- Cross-links should prefer the next page a reader should open, not every vaguely related page.
- Links should only point to pages that exist, unless the link intentionally targets an external canonical source such as an RFC issue.

## Terminology Rules

Use one terminology set across the whole docs system.

- Product name: `Praxis`
- Durable event log: `Event Spine`
- Durable runtime view: `Trading State`
- Command intake and routing core: `Execution Manager`
- Manager-facing execution runtime: `Trading`
- Venue boundary: `Venue Adapter`
- Current paper venue target: `Binance Spot testnet`

### Naming Rules

- Use `Trading sub-system` and `Account sub-system` when referring to the RFC-defined subsystems.
- Do not describe the Account sub-system as implemented unless the code actually ships it.
- Do not describe future execution modes as fully supported unless the runtime actually executes them.
- Do not describe upstream research or downstream oversight responsibilities as if they live inside Praxis.
- Keep `event-sourced` language exact and tied to the Event Spine, replay, and derived state model.

## Example And Artefact Rules

Examples should be operationally real.

- Prefer examples that can be run locally in this repository.
- Prefer examples validated against actual Praxis tests or runtime flows.
- When an example depends on testnet access, credentials, or venue reachability, say so explicitly.
- Show commands, emitted events, or runtime artefacts where they are important to understanding the workflow.
- Avoid examples that imply live-trading guarantees when the documented path is testnet or paper trading.

## Site Build Rules

These rules should guide the site build implemented in a later slice.

- Praxis should get a standalone docs site built in this repository.
- The initial implementation should use Docusaurus.
- The site should support local development and static build.
- The site should support both standalone deployment and later subpath deployment.
- The site base URL should be environment-driven so the same content can support both modes.
- Search should work across the full Praxis docs corpus.
- Broken internal links should fail the build.
- The site navigation should reflect the five top-level sections in this contract.

## Future Vaquum Portal Contract

The Praxis docs system should expose a minimal product-docs contract that can later be consumed by a Vaquum-wide docs portal.

That contract should include:

- product id
- product name
- short product tagline
- current docs version label
- deployment base path
- primary navigation sections
- source repository URL

This does not mean Praxis should wait for a Vaquum-wide shell. Praxis should be excellent as a standalone docs product first.

## Rewrite Slices

The docs buildout should be tracked in the following order.

| Slice | Name | Scope | Definition of Done |
| --- | --- | --- | --- |
| 1 | Docs System Contract | Define structure, voice, page types, ownership, navigation model, site boundary, and rewrite slices. | This contract exists, is linked from the docs hub, and is accepted as the operating manual for later slices. |
| 2 | Top-Level Narrative | Rewrite the product home and docs hub so Praxis has one clear entry story and reading flow. | A new user can enter the docs without guessing what to read next. |
| 3 | Core Workflow Guides | Add guide pages for setup, verification, command submission, replay, and recovery. | A reader can go from install to a meaningful Praxis verification path using the guide layer. |
| 4 | Reference Layer | Add reference pages for Trading, Execution Manager, Event Spine, venue adapters, domain types, and runtime invariants. | The main surfaces are documented in a predictable and trustworthy way. |
| 5 | Developer Layer | Add contributor, maintenance, release, and review docs around current practice. | A contributor can maintain Praxis without relying on tribal knowledge. |
| 6 | Package README Alignment | Align package READMEs with the same contract and route them to canonical docs. | Package READMEs feel like part of one system rather than isolated notes. |
| 7 | Docs-Site Build | Add the site build, docs assembly model, product metadata, local dev/build/check commands, and navigation shell. | The Praxis docs site builds locally, renders the current corpus, and enforces link integrity. |
| 8 | Final Cohesion Pass | Sweep the entire corpus for terminology, duplication, examples, links, navigation, and consistency. | The docs read as one coherent product and meet the 10/10 acceptance bar. |

## Acceptance Bar For The Whole Overhaul

The overhaul should be considered complete when all of the following are true:

- a new user can reach a first meaningful Praxis verification path without guessing
- a serious user can understand how Praxis fits into the broader Vaquum architecture
- a contributor can find the canonical page for any subsystem quickly
- examples are grounded in real Praxis runtime behavior and test flows
- reference pages are easy to navigate and trustworthy
- the standalone Praxis docs site feels complete
- the same docs system can later plug into a Vaquum-wide docs portal without conceptual rework

## How To Use This Page

Before rewriting any major docs slice:

- confirm the target page type
- confirm where the page sits in the narrative spine
- confirm whether the page is canonical or secondary
- confirm which slice the change belongs to

If a proposed docs change conflicts with this contract, update this page first or explicitly document the exception.
