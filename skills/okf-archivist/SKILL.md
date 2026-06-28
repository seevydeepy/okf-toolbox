---
name: okf-archivist
description: "Maintain OKF route-pack wiki material after substantive repository changes. Use at end of turns in repos with OKF infrastructure or when asked for routing-card, wiki, or documentation optimisation; map changed paths through manifests and update only relevant route-owned material."
---

# OKF Archivist

Optimise branch-local OKF route cards from real work. Keep them aligned with the code that just changed, and improve the next agent's first hop when the turn exposed a better route. Prefer the smallest truthful routing update; do not backfill broad prose during a routine archivist pass.

## Gate

Skip and state why when:

- The checkout has no discoverable `solutions.manifest.json` under `docs/`, `documentation/`, `doc/`, `wiki/`, `manual(s)/`, or a similar documentation folder, or no OKF docs in the active branch.
- The turn has no relevant code/config/tooling changes after generated wiki artefacts and OKF-only churn are excluded.
- The turn only changed OKF docs and the generated readers were already rebuilt and checked.

Wrappers may narrow this gate to explicit solution-owned paths or broad application/tooling paths for that repository.

## Workflow

1. Respect local agent instructions (`AGENTS.md`, `.codex/config.toml`, `.cursor/rules/`) and repo memory first.
2. Inspect current state: `git status --short`, `git diff --name-status`, `git diff --stat`, and relevant hunks, including staged and untracked files.
3. Locate and load `solutions.manifest.json`, preferring existing `docs/`, then `documentation/`, `doc/`, `wiki/`, `manual/`, `manuals/`, then similarly named documentation folders. For known changed paths, run `python tools/docs/map_changed_paths.py` if present. For repos bootstrapped by `okf-wiki-initialiser`, the manifest/docs/tooling contract is in `skills/okf-wiki-initialiser/references/bootstrap-contract.md`.
4. Read only the matched first-hop docs before broad prose: prefer each solution's `routing_guidance.card`, then `solution.md` only if ownership or impact is still unclear.
5. Decide route-pack impact. Update OKF route cards/docs when behaviour, ownership, entrypoints, public API/controller/service surface, domain model, persistence, cross-solution contracts, runtime/build wiring, validation commands, or future file routing changed. Skip mechanical refactors, test-only edits, typo fixes, generated churn, and cleanup with no behaviour/routing change.
6. Optimise routing using evidence from the turn. If the agent had to discover a better owner, first file, search term, handoff, validation command, or stale claim while doing the work, update the relevant route card or `routing.md` so the next agent starts there.
7. Check routing health using evidence from the turn. Fix the smallest routing doc when there is a clear:
   - wrong subsystem route;
   - broad-doc detour before owner files;
   - `routing_guidance.card` missing its own card or `solution.md` at the start of `read_first`;
   - large source files in `routing_guidance.card` that should live in symptom-specific `routing.md` routes;
   - missing symptom/search vocabulary;
   - cross-solution handoff;
   - missing or stale validation commands;
   - repeated fallback to broad source search that a route card could prevent;
   - concrete repo-exploration lesson that would save future token/time without adding broad prose;
   - unexpected mapper `unmapped` or `ambiguous` paths;
   - stale file, ownership, runtime, or build claim.
   Do not invent token/time/command-count targets during routine archivist work.
8. Update shallowly: usually the matched `routing_guidance.card` for first-hop improvements, the matched `<docs-root>/okf/<solution>/routing.md` for symptom-specific routing, `solution.md` for stable ownership, `log.md` for evidence or unresolved ambiguity, and sometimes the discovered `solutions.manifest.json`. If the repo still has a legacy context map or compatibility wiki pages, keep them aligned only where the change affects routing or claims.
9. Rebuild and validate with the repo pipeline, normally:

```powershell
.\tools\docs\build_all_wikis.ps1
.\tools\docs\build_all_wikis.ps1 -Check
```

Run `python tools/docs/check_okf_route_cards.py --repo .` when the repo has that checker and route cards changed; generated `build_all_wikis.ps1` may already run it. Use `-BrowserSmoke` when generator/template/reader JavaScript/browser behaviour changed. Run repo-required build/tests for implementation changes unless the repo wrapper explicitly narrows validation.

## Rules

- Treat OKF docs as branch-local truth. Do not point one branch/repo at another repo's docs as live truth.
- Do not run scaffold/backfill generators during routine passes unless the task explicitly asks for bootstrapping.
- Never mutate timestamps during check mode.
- If the mapper reports excluded, ambiguous, or unmapped paths, preserve that in the report.
- Optimise only from evidence observed in this turn or explicit repo exploration. Do not add speculative routes, generic keywords, or aspirational handoffs.

## Report

Say what was touched or skipped, why, what routing was improved or why no optimisation was justified, validation commands/results, and any bootstrap blocker.

