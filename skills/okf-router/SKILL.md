---
name: okf-router
description: "Select branch-local OKF route evidence for repository work. Use when a checkout has OKF route-pack infrastructure such as solutions.manifest.json, route cards, or documentation bundles; this is routing only and does not authorise planning or implementation."
---

# OKF Router

Select the smallest useful OKF route card before broad source inspection. This skill routes; it does not update documentation, declare requirements stable, write or approve plans, create worktrees, start implementation, or bypass Superpowers Lite or repo-specific gates.

## Gate

Skip and state why when:

- The checkout has neither `solutions.manifest.json` under `docs/`, `documentation/`, `doc/`, `wiki/`, `manual(s)/`, or a similar documentation folder, nor OKF bundles.
- The user asks only for a trivial command or isolated non-repository answer.
- A repository-specific wrapper gives a narrower routing path.

If OKF bundles exist without a discoverable `solutions.manifest.json`, report that the branch is not fully bootstrapped and use explicit user paths or repo-local instructions only.

## Workflow

1. Respect local agent instructions (`AGENTS.md`, `.codex/config.toml`, `.cursor/rules/`) and repo memory first.
2. Locate and inspect `solutions.manifest.json`. Prefer existing `docs/`, then `documentation/`, `doc/`, `wiki/`, `manual/`, `manuals/`, then similarly named documentation folders. Do not create a documentation folder during routing.
3. Build candidate paths from the user prompt, `git diff --name-only`, `git diff --name-only --cached`, and `git ls-files --others --exclude-standard`. A focused symbol/path grep is allowed first when it is the fastest way to identify candidate paths; reduce line-qualified grep hits to repo-relative file paths and feed them back into this candidate set instead of using them as direct edit targets, plan approval, or a route-card bypass. Do not scan the whole repo unless the user asks for a broad audit.
4. When candidate paths exist and `tools/docs/map_changed_paths.py` exists, run:

```powershell
python tools/docs/map_changed_paths.py <candidate-paths>
```

5. For matched solutions, read only each matched `docs.routing_guidance_card`, then `docs.solution` if ownership or first files are still unclear.
6. If there are no candidate paths, select by manifest `routing_keywords`, solution names, owned paths, and obvious prompt terms. If still unclear, ask or proceed with the smallest source inspection needed to find the owner.
7. Preserve `excluded`, `unmapped`, and `ambiguous` mapper output in the report. Do not hide ambiguous ownership by reading every bundle.

## Rules

- Treat OKF docs as branch-local truth. Do not point this repo at another branch or repository's OKF docs as live truth.
- Prefer `routing_guidance.card` before broader prose. Treat the card as the workflow primitive; the generated wiki is a human-readable view over the route pack.
- Treat OKF routing as evidence for the next workflow step only. It never replaces requirements elicitation, active-mode implementation authority, tracked-doc approval, worktree policy, validation policy, or any other active agent/repository instruction.
- Do not edit OKF docs during routing. Use `okf-archivist` later if the turn changes code, config, tooling, ownership, or routing.
- If all matched paths are generated OKF/wiki files, report them as excluded and avoid routing into implementation bundles.

## Report

State selected solution ids, first-hop docs read, and any excluded, unmapped, or ambiguous paths that affect the work.
