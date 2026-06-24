---
name: okf-wiki-initialiser
description: Use when a repository does not yet have OKF wiki infrastructure, or when the user explicitly asks to bootstrap, initialise, repair, or backfill an OKF-conformant wiki. Creates a shallow branch-local OKF setup with documentation/solutions.manifest.json, docs/okf solution bundles, mapping/build tooling, and generated readers; then, only when explicitly requested, orchestrates deeper per-solution/subsystem explorer agents to backfill routing and bundle detail.
---

# OKF Wiki Initialiser

Bootstrap OKF with the smallest useful first pass, then stop unless the user asks for deep backfill.

## Gate

- If `documentation/solutions.manifest.json` and `docs/okf/` already exist, do not reinitialise; repair only the missing/broken pieces the user asked about.
- If ownership boundaries are ambiguous enough to create bad routing, ask before writing the manifest.
- Do not borrow another branch or repo's docs as live truth. Use them only as implementation examples.

## Shallow Pass

1. Respect local `AGENTS.md`, `.codex/config.toml`, and repo memory.
2. Inspect `git status --short`, top-level layout, build files, solution/project files, existing docs, and obvious runtime/application entrypoints.
3. Choose logical solutions/subsystems from existing boundaries: projects, apps, top-level modules, services, routes, packages, or domain folders. Prefer fewer accurate bundles over many guessed bundles.
4. Reuse the nearest local OKF implementation for infrastructure when available, copying only portable pieces such as:
   - `documentation/solutions.manifest.json` shape;
   - `tools/docs/build_all_wikis.ps1`;
   - `tools/docs/map_changed_paths.py`;
   - generated wiki reader templates/helpers.
5. Create shallow bundles under `docs/okf/<solution>/` with only evidence-backed routing:
   - `solution.md`: purpose, entrypoints, owned paths, neighbouring systems;
   - `routing.md`: first-hop routing card, symptoms/search terms, handoffs;
   - `log.md`: bootstrap notes and known gaps.
6. Add manifest entries that point changed paths to first-hop docs. Mark ambiguous paths in the log instead of guessing.
7. Build and check the wiki pipeline:

```powershell
.\tools\docs\build_all_wikis.ps1
.\tools\docs\build_all_wikis.ps1 -Check
```

If no portable generator seed exists, create the manifest and shallow bundles, then report generator bootstrap as the blocker instead of inventing a large bespoke generator.

## Deep Backfill

Run this only after a successful shallow pass and explicit user approval.

1. Start one medium-or-higher explorer subagent per solution/subsystem, or small batches if the repo is large.
2. Give each explorer only its solution bundle, manifest entry, owned paths, and read/write boundary.
3. Ask each explorer to inspect source evidence and update only that solution's `solution.md`, `routing.md`, and `log.md`.
4. Main agent reviews every diff, removes duplicated prose, fixes handoffs, then rebuilds/checks the wiki.
5. Use `okf-archivist` afterwards for routing-health review.

## Report

State solutions created, tooling copied or skipped, validation results, ambiguous ownership, and whether deep backfill is ready or still blocked.
