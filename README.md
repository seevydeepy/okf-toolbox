# OKF Toolbox (Cursor Plugin)

OKF Toolbox gives Cursor agents structured routing evidence for repository work: bootstrap route packs, read the smallest relevant route card before broad source inspection, and keep route cards aligned with code after substantive changes. Routing evidence does not replace requirements elicitation, saved-plan approval, implementation authorisation, tracked-doc approval, or repository-specific gates.

## What it does

1. **Bootstrap** — Initialise OKF route-pack infrastructure in a repository that lacks it (`$okf-wiki-initialiser`).
2. **Route** — At the start of substantive work, select the relevant route-card evidence before broad source inspection (`$okf-router`, enforced by an always-on rule). This is not an implementation or planning approval.
3. **Maintain** — At the end of substantive code/config/tooling changes, update route cards and rebuild generated readers when needed and when the active workflow authorises tracked docs edits (`$okf-archivist`, enforced by an always-on rule).

Route cards (`routing_guidance.card`) are the workflow primitive. Generated `wiki.html` readers are deterministic views over the route pack for humans; agents should route through cards and bundle markdown, not treat HTML as source of truth.

## Install (Cursor)

For the Cursor app marketplace flow, point Cursor at this folder's marketplace manifest:

`okf-toolbox/.cursor-plugin/marketplace.json`

Reload or reinstall the plugin after updates. Do not edit installed cache copies under `~/.cursor/plugins/cache/` — treat this source folder as canonical.

Codex can load the same skills from `.codex-plugin/plugin.json` in this folder if you use both agents.

## What installs automatically

- **Rules** (always on): `rules/okf-routing.mdc`, `rules/okf-archivist.mdc`
- **Skills**: `okf-router`, `okf-archivist`, `okf-wiki-initialiser`

Cursor engagement is driven by the always-on rules. Codex also allows implicit invocation for the same skills through the bundled `agents/openai.yaml` metadata.

## What you do in a repository

1. **First time in a repo without OKF** — Ask the agent to bootstrap OKF (or invoke `$okf-wiki-initialiser`). The agent inspects repo layout first; manifest, route-card, validation-tooling, and generated-reader writes require the active saved-plan approval gate.
2. **Normal work** — Work as usual. When `docs/solutions.manifest.json` (or equivalent under `documentation/`, `wiki/`, etc.) exists, agents gather route evidence at turn start and run the archivist pass at turn end when changes warrant it. Follow the active agent, planning, worktree, tracked-doc, and approval gates separately.
3. **Deep backfill** — Optional second pass to fill entrypoints, handoffs, and evidence-backed routing prose per solution; requires explicit saved-plan approval after a successful shallow bootstrap.

## Prerequisites (bootstrapped repositories)

- **Python 3** on `PATH` (bootstrap and validation scripts).
- **PowerShell** for `.\tools\docs\build_all_wikis.ps1` on Windows (typical Digitalk workflow).
- On systems without PowerShell, run the generated Python builder directly: `python tools/docs/build_okf_wikis.py --repo .` and `--check` / `--browser-smoke` as needed.

## Canonical contract

This plugin defines the OKF manifest and route-card contract (`owned_paths`, `routing_guidance.card`, `tools/docs/check_okf_route_cards.py`, etc.). Older branches that still use legacy Digitalk OKF manifest shapes need migration before this plugin's tooling applies there.

## Renderer limitations

Generated wiki HTML uses a hand-rolled Markdown subset. See `skills/okf-wiki-initialiser/references/renderer-limitations.md` for supported syntax and known gaps.

## License

MIT — see [LICENSE](LICENSE). Copyright Charles van der Pol.
