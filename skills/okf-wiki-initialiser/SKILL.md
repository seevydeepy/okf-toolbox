---
name: okf-wiki-initialiser
description: "Use when a repository does not yet have OKF wiki infrastructure, or when the user explicitly asks to bootstrap, initialise, repair, or backfill an OKF-conformant wiki. Creates a self-contained shallow branch-local OKF setup using the bundled bootstrap contract and script: documentation/solutions.manifest.json, docs/okf solution bundles, routing_guidance.card files, mapping/build tooling, and generated wiki readers; then, only when explicitly requested, orchestrates deeper per-solution/subsystem explorer agents to backfill routing and bundle detail."
---

# OKF Wiki Initialiser

Bootstrap OKF from zero. Do not rely on another repo having examples.

## Required Reference

Before writing files, read `references/bootstrap-contract.md`. It defines the manifest schema, required bundle files, generated reader contract, mapper output, and validation checklist.

## Gate

- If `documentation/solutions.manifest.json` and `docs/okf/` already exist, do not reinitialise; repair only the missing or broken pieces the user asked about.
- If ownership boundaries are too ambiguous to create useful routing, ask before writing the manifest.
- Do not point at another branch/repo's docs as live truth. Use existing repos only for source-code understanding, not as required templates.

## Shallow Pass

1. Respect local `AGENTS.md`, `.codex/config.toml`, and repo memory.
2. Inspect `git status --short`, top-level layout, build files, project/package files, existing docs, and obvious runtime/application entrypoints.
3. Choose logical solutions/subsystems from real boundaries: projects, apps, services, packages, routes, modules, or domain folders. Prefer fewer accurate bundles over many guessed bundles.
4. Create a tiny bootstrap spec, usually in a temp file, with each solution's `id`, `name`, `summary`, `owned_paths`, and `keywords`.
5. Run the bundled bootstrapper:

```powershell
python <okf-toolbox>\skills\okf-wiki-initialiser\scripts\bootstrap_okf.py --repo . --spec <spec.json>
```

Use repeated `--solution "id|Name|Summary|path1,path2|keyword1,keyword2"` only for very small repos.

The script creates the full conformant infrastructure: manifest, per-solution bundles, `routing_guidance.card`, mapper, wiki builder, and generated-reader pipeline.

6. Run the generated pipeline:

```powershell
.\tools\docs\build_all_wikis.ps1
.\tools\docs\build_all_wikis.ps1 -Check
python tools/docs/map_changed_paths.py <representative-owned-path>
```

7. Remove any temporary bootstrap spec unless the user wants it tracked.

## Deep Backfill

Run this only after a successful shallow pass and explicit user approval.

1. Start one medium-or-higher explorer subagent per solution/subsystem, or small batches if the repo is large.
2. Give each explorer only its solution bundle, manifest entry, owned paths, and read/write boundary.
3. Ask each explorer to inspect source evidence and update only that solution's `solution.md`, `routing.md`, and `log.md`.
4. Main agent reviews every diff, removes duplicated prose, fixes handoffs, then rebuilds/checks the wiki.
5. Use `okf-archivist` afterwards for routing-health review.

## Report

State solutions created, validation commands/results, mapper matched/excluded/unmapped/ambiguous examples, and whether the shallow pass is Archivist-ready.

End with an explicit deep-backfill call to action. Do not merely say it was skipped. Say whether it is ready or blocked, why, and invite the user to approve the next pass, for example:

```text
Next step available: the shallow OKF wiki is ready for deep backfill. Say "run the deep backfill" and I will launch per-solution explorers to fill entrypoints, handoffs, routing evidence, and logs.
```

