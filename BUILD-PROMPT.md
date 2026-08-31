# Build Prompt

Use the following prompt to hand this repository to a Codex agent:

> You are starting without prior conversation context. Build the complete Omarchy News Radar project located at `~/Projects/plugins/omarchy-news-radar`. Change to that existing Git repository first, verify its identity and working-tree state, and perform all project work there. Do not create a replacement project elsewhere.
>
> Start by reading `AGENTS.md` and every document it marks as required, in the stated order. Treat those documents as the product and engineering contract. Resolve small omissions with the simplest design that preserves those contracts; do not silently change a documented product decision.
>
> Implement the project end to end, not just a prototype or another planning pass. This includes the deterministic Python collector and publisher, schemas and fixtures, the static feed and optional static website, the Omarchy panel and optional default-on newspaper widget, the local client/cache/state/preferences helper, the explicit and reversible conflict-free `Super+Alt+N` shortcut setup, tests, build tooling, documentation, and reproducible verification. Prove zero-gap widget hiding and panel restoration in the Plugin Lab.
>
> Use clean, maintainable code with small modules, explicit interfaces, deterministic behavior, strict validation, atomic writes, bounded inputs, helpful failures, and no unnecessary dependencies. Remote textual content must remain untrusted plain text; optional images must be inspected, mirrored from the fixed marketplace origin, and exposed only as same-origin content-addressed rasters. Install the Radar shortcut only when the audited chord is free; never overwrite a personal, ambiguous, or unrelated shortcut or configuration, and never displace Editor. Do not activate or test desktop integration on the host system.
>
> Work autonomously through the phases in `docs/IMPLEMENTATION.md`. Use the current local Omarchy source as the contract reference and the disposable Omarchy Plugin Lab for integration and visual acceptance. Run every relevant test and quality check, fix failures, and collect the evidence required by `docs/TESTING.md` and `docs/RELEASE.md`.
>
> Do not create remote repositories, push, publish, open pull requests, contact maintainers, or change external services without explicit authorization. If credentials or an external decision are genuinely required, finish all local work first and report the exact remaining action.
>
> When complete, provide a concise handoff covering what was built, the important files, every verification command and result, Plugin Lab evidence, any deliberately deferred items, and the exact steps the owner can take to review and publish the project.
