# Build Prompt

Use the following prompt to hand this repository to a Codex agent:

> You are starting without prior conversation context. Build the complete Omarchy News Radar project located at `~/Projects/plugins/omarchy-news-radar`. Change to that existing Git repository first, verify its identity and working-tree state, and perform all project work there. Do not create a replacement project elsewhere.
>
> Start by reading `AGENTS.md` and every document it marks as required, in the stated order. Treat those documents as the product and engineering contract. Resolve small omissions with the simplest design that preserves those contracts; do not silently change a documented product decision.
>
> Implement the project end to end, not just a prototype or another planning pass. This includes the deterministic Python collector and publisher, schemas and fixtures, the static feed and optional static website, the Omarchy panel plugin, the local client/cache/state helper, the explicitly authorized and reversible `Super+Shift+N` shortcut reassignment, tests, build tooling, documentation, and reproducible verification. Keep the main plugin panel-only. Do not add a top-bar widget to v1; preserve the documented separate-companion-plugin boundary for any future indicator.
>
> Use clean, maintainable code with small modules, explicit interfaces, deterministic behavior, strict validation, atomic writes, bounded inputs, helpful failures, and no unnecessary dependencies. Remote content must remain untrusted plain text. Replace only the exact audited default Editor binding through the documented explicit authorization; never overwrite a personal, modified, ambiguous, or unrelated shortcut or configuration. Do not activate or test desktop integration on the host system.
>
> Work autonomously through the phases in `docs/IMPLEMENTATION.md`. Use the current local Omarchy source as the contract reference and the disposable Omarchy Plugin Lab for integration and visual acceptance. Run every relevant test and quality check, fix failures, and collect the evidence required by `docs/TESTING.md` and `docs/RELEASE.md`.
>
> Do not create remote repositories, push, publish, open pull requests, contact maintainers, or change external services without explicit authorization. If credentials or an external decision are genuinely required, finish all local work first and report the exact remaining action.
>
> When complete, provide a concise handoff covering what was built, the important files, every verification command and result, Plugin Lab evidence, any deliberately deferred items, and the exact steps the owner can take to review and publish the project.
