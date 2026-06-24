---
name: okf-archivist
description: Use at the end of substantive turns in repositories with OKF wiki infrastructure, or for explicit OKF wiki/documentation maintenance. Maps changed paths through documentation/solutions.manifest.json, decides whether branch-local OKF docs or routing cards need updates, checks for routing-health defects such as wrong subsystem or broad-doc detours, rebuilds generated wiki readers, validates the wiki pipeline, and reports touched or skipped solutions.
---

# OKF Archivist

Keep branch-local OKF documentation aligned with the code that just changed. Prefer the smallest truthful doc/routing update; do not backfill broad prose during a routine archivist pass.

## Gate

Skip and state why when:

- The checkout has no `documentation/solutions.manifest.json` or no OKF docs in the active branch.
- The turn has no relevant code/config/tooling changes after generated wiki artefacts and OKF-only churn are excluded.
- The turn only changed OKF docs and the generated readers were already rebuilt and checked.

Wrappers may narrow this gate for a repo, such as `vp/`/`Web/` only or all game/runtime/tooling paths.

## Workflow

1. Respect local `AGENTS.md`, `.codex/config.toml`, and repo memory first.
2. Inspect current state: `git status --short`, `git diff --name-status`, `git diff --stat`, and relevant hunks, including staged and untracked files.
3. Load `documentation/solutions.manifest.json`; for known changed paths, run `python tools/docs/map_changed_paths.py` if present. For repos bootstrapped by `okf-wiki-initialiser`, the manifest/docs/tooling contract is in `skills/okf-wiki-initialiser/references/bootstrap-contract.md`.
4. Read only the matched first-hop docs before broad prose: prefer each solution's `routing_guidance.card`, then `solution.md` only if ownership or impact is still unclear.
5. Decide doc impact. Update OKF docs when behaviour, ownership, entrypoints, public API/controller/service surface, domain model, persistence, cross-solution contracts, runtime/build wiring, or future file routing changed. Skip mechanical refactors, test-only edits, typo fixes, generated churn, and cleanup with no behaviour/routing change.
6. Check routing health using evidence from the turn. Fix the smallest routing doc when there is a clear:
   - wrong subsystem route;
   - broad-doc detour before owner files;
   - `routing_guidance.card` missing its own card or `solution.md` at the start of `read_first`;
   - large source files in `routing_guidance.card` that should live in symptom-specific `routing.md` routes;
   - missing symptom/search vocabulary;
   - cross-solution handoff;
   - unexpected mapper `unmapped` or `ambiguous` paths;
   - stale file, ownership, runtime, or build claim.
   Do not invent token/time/command-count targets during routine archivist work.
7. Update shallowly: usually `docs/okf/<solution>/routing.md`, `solution.md`, `log.md`, and sometimes `documentation/solutions.manifest.json`. If the repo still has a legacy context map or compatibility wiki pages, keep them aligned only where the change affects routing or claims.
8. Rebuild and validate with the repo pipeline, normally:

```powershell
.\tools\docs\build_all_wikis.ps1
.\tools\docs\build_all_wikis.ps1 -Check
```

Use `-BrowserSmoke` when generator/template/reader JavaScript/browser behaviour changed. Run repo-required build/tests for implementation changes unless the repo wrapper explicitly narrows validation.

## Rules

- Treat OKF docs as branch-local truth. Do not point one branch/repo at another repo's docs as live truth.
- Do not run scaffold/backfill generators during routine passes unless the task explicitly asks for bootstrapping.
- Never mutate timestamps during check mode.
- If the mapper reports excluded, ambiguous, or unmapped paths, preserve that in the report.

## Report

Say what was touched or skipped, why, routing-health outcome, validation commands/results, and any bootstrap blocker.

