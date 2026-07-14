---
name: okf-wiki-initialiser
description: "Bootstrap, repair, or backfill OKF route-pack and wiki infrastructure, including repository-wide discovery of semantic product seams with solution/project fallbacks. Use only when the user explicitly asks to initialise, repair, or backfill, or when expected OKF infrastructure is demonstrably broken; mere absence supports diagnosis or proposal only."
---

# OKF Route-Pack Initialiser

Bootstrap OKF route packs from zero. Do not rely on another repo having examples.

This skill may inspect, diagnose, and propose a bootstrap/repair/backfill plan before implementation authority. Do not write tracked repository files, create route packs, repair OKF docs, run backfill workers, create worktrees, commit, merge, or rebuild generated readers until active-mode implementation/tracked-doc authority covers those changes.

## Required Reference

Before writing files in an approved implementation phase, read `references/bootstrap-contract.md`. It defines the manifest schema, required bundle files, route-card contract, generated reader contract, mapper output, and validation checklist. Read `references/renderer-limitations.md` only when authoring complex Markdown, diagnosing generated reader output, or changing renderer/template behaviour.

## Gate

- Mere absence of OKF files does not select bootstrap implementation. Diagnose and propose options only unless the user explicitly requests initialisation, repair, or backfill and active authority permits tracked-doc changes.
- If a `solutions.manifest.json` already exists under `docs/`, `documentation/`, `doc/`, `wiki/`, `manual(s)/`, or a similar documentation folder and matching OKF bundles exist, do not reinitialise; repair only the missing or broken pieces the user asked about.
- If ownership boundaries are too ambiguous to create useful routing, ask before writing the manifest.
- Do not point at another branch/repo's docs as live truth. Use existing repos only for source-code understanding, not as required templates.
- Treat user requests to initialise, repair, optimise, or backfill as requirements evidence until active-mode implementation/tracked-doc authority exists.

## Repair Existing OKF

Use this when a repo already has OKF files that drifted from `references/bootstrap-contract.md`.

1. Find the existing documentation root, manifest, affected route cards, bundle docs, generated-reader scripts, mapper, checker, and `AGENTS.md` routing block.
2. Run the repo's existing checks first: `build_all_wikis.ps1`, `build_all_wikis.ps1 -Check`, `build_all_wikis.ps1 -Check -BrowserSmoke`, `check_okf_route_cards.py`, and representative `map_changed_paths.py` cases when those files exist.
3. Compare failures to `references/bootstrap-contract.md`; patch only missing or broken contract pieces after active-mode implementation/tracked-doc authority exists.
4. Do not rerun `bootstrap_okf.py --force` over an existing implementation unless intentionally replacing bootstrap files.
5. Rerun the failed checks and use `okf-archivist` afterwards when routing ownership, cards, or bundle docs changed.

## Shallow Pass

1. Respect local agent instructions (`AGENTS.md`, `.codex/config.toml`, `.cursor/rules/`) and repo memory.
2. Inspect `git status --short`, the complete repository layout, build/workspace files, project/package files, existing docs, runtime/application entrypoints, deployment units, domain folders, and shared-library seams. Never infer priority or ownership from the repository, checkout, branch, story, or feature name.
3. Ask the bundled bootstrapper for a read-only candidate spec:

```powershell
python <okf-toolbox>\skills\okf-wiki-initialiser\scripts\bootstrap_okf.py --repo . --discover-only > <temp-spec>.json
```

Discovery is evidence-led and repository-wide. It first groups related build descriptors beneath a meaningful semantic family root, then falls back to production solution/workspace files, then project/package files, and finally top-level source directories only when stronger evidence is absent. Test, QA, benchmark, sample, and example descriptors do not become standalone bundles; keep them inside or map them back to their production owner.

4. Review and correct the candidate spec before writing. Every independently deployed or operated service/application must receive equal consideration, regardless of the current feature focus. Prefer stable product/domain ownership over one bundle per file, but retain solution/project fallbacks when no stronger seam is evidenced. Collapse shared implementation projects into a product owner when source/dependency evidence supports that relationship; otherwise retain the explicit project fallback rather than guessing. Resolve every reported `uncovered_root` by assigning an evidenced owner, adding a legitimate semantic bundle, or excluding non-product/generated/vendor material. Reject unexplained broad catch-all roots, overlapping prefixes, missing production descriptors, and feature-name bias.
5. Keep the reviewed bootstrap spec in a temp file with each solution's `id`, `name`, `summary`, `owned_paths`, and `keywords`, only when plan/ledger rules permit that pre-approval artefact or after approval. `discovery` evidence fields may remain in the temp spec; the generated manifest intentionally keeps only the stable routing contract.
6. After approval, run the bundled bootstrapper with the reviewed spec:

```powershell
python <okf-toolbox>\skills\okf-wiki-initialiser\scripts\bootstrap_okf.py --repo . --spec <spec.json>
```

Use repeated `--solution "id|Name|Summary|path1,path2|keyword1,keyword2"` only for very small repos.

When the discovery output is demonstrably unambiguous, has no `uncovered_roots`, and has already been reviewed in the current task, `--discover` may bootstrap the same inferred seams directly. The command fails closed when source roots still need semantic review:

```powershell
python <okf-toolbox>\skills\okf-wiki-initialiser\scripts\bootstrap_okf.py --repo . --discover
```

The script reuses an existing documentation root such as `docs/`, `documentation/`, `doc/`, `wiki/`, or `manual(s)/`; only creates root `docs/` when no similar folder exists. It creates the full conformant infrastructure: manifest, per-solution bundles, `routing_guidance.card`, route-card checker, mapper, wiki builder, generated-reader pipeline, and a marked root `AGENTS.md` OKF routing block.

7. Run the generated pipeline:

```powershell
.\tools\docs\build_all_wikis.ps1
.\tools\docs\build_all_wikis.ps1 -Check
python tools/docs/check_okf_route_cards.py --repo .
python tools/docs/map_changed_paths.py <representative-owned-path>
```

Confirm `AGENTS.md` contains one `OKF-ROUTING` marker block that calls `$okf-router` at the start of substantive work for route evidence only, calls `$okf-archivist` at the end of substantive changes, and does not present routing as requirements stability, plan approval, implementation authorisation, or a bypass for active workflow/repository gates.

8. Remove any temporary bootstrap spec unless the user wants it tracked.

## Deep Backfill

Run this only after a successful shallow pass and explicit active-mode authority for tracked docs backfill.

1. When the active operation mode, delegation rubric, host capacity, and solution independence permit delegation, assign bounded explorers to independent solutions in a single safe wave or small batches. In solo mode, or when delegation is blocked or the solutions are tightly coupled, process them sequentially in the main agent.
2. Give each delegated explorer only its solution bundle, manifest entry, owned paths, and read/write boundary.
3. Ask each delegated explorer to inspect source evidence and update only that solution's `solution.md`, `routing.md`, and `log.md` after active-mode tracked-doc authority exists.
4. Main agent reviews every diff, removes duplicated prose, fixes handoffs, then runs the backfill checks in `references/bootstrap-contract.md`.
5. Keep each `routing_guidance.card` as a narrow first-hop card: `read_first` must start with its own card and `solution.md`, and the card must pass `check_okf_route_cards.py`. Put large source files in `routing.md` symptom routing unless they are always the first owner file.
6. Use `okf-archivist` afterwards for routing-health review.

## Report

State solutions created, validation commands/results, mapper matched/excluded/unmapped/ambiguous examples, and whether the shallow pass is Archivist-ready.

End with an explicit deep-backfill call to action. Do not merely say it was skipped. Say whether it is ready or blocked, why, and invite the user to approve the next pass, for example:

```text
Next step available: the shallow OKF route pack is ready for deep backfill. Say "plan the deep backfill" to use the planning workflow first, or explicitly ask me to backfill now if you want Default-mode implementation authority for the tracked docs edits.
```
