---
name: okf-router
description: Use at the start of substantive repository work when the checkout has OKF infrastructure such as documentation/solutions.manifest.json or docs/okf/. Selects the relevant branch-local OKF solution bundle before broad source inspection by mapping mentioned or changed paths, reading only matched routing_guidance.card and solution.md first, and reporting unmapped or ambiguous routing instead of guessing.
---

# OKF Router

Select the smallest useful OKF bundle before broad source inspection. This skill routes; it does not update documentation.

## Gate

Skip and state why when:

- The checkout has neither `documentation/solutions.manifest.json` nor `docs/okf/`.
- The user asks only for a trivial command or isolated non-repository answer.
- A repository-specific wrapper gives a narrower routing path.

If `docs/okf/` exists without `documentation/solutions.manifest.json`, report that the branch is not fully bootstrapped and use explicit user paths or repo-local instructions only.

## Workflow

1. Respect local `AGENTS.md`, `.codex/config.toml`, and repo memory first.
2. Inspect `documentation/solutions.manifest.json`.
3. Build candidate paths from the user prompt, `git diff --name-only`, `git diff --name-only --cached`, and `git ls-files --others --exclude-standard`. Do not scan the whole repo unless the user asks for a broad audit.
4. When candidate paths exist and `tools/docs/map_changed_paths.py` exists, run:

```powershell
python tools/docs/map_changed_paths.py <candidate-paths>
```

5. For matched solutions, read only each matched `docs.routing_guidance_card`, then `docs.solution` if ownership or first files are still unclear.
6. If there are no candidate paths, select by manifest `routing_keywords`, solution names, owned paths, and obvious prompt terms. If still unclear, ask or proceed with the smallest source inspection needed to find the owner.
7. Preserve `excluded`, `unmapped`, and `ambiguous` mapper output in the report. Do not hide ambiguous ownership by reading every bundle.

## Rules

- Treat OKF docs as branch-local truth. Do not point this repo at another branch or repository's OKF docs as live truth.
- Prefer `routing_guidance.card` before broader prose.
- Do not edit OKF docs during routing. Use `okf-archivist` later if the turn changes code, config, tooling, ownership, or routing.
- If all matched paths are generated OKF/wiki files, report them as excluded and avoid routing into implementation bundles.

## Report

State selected solution ids, first-hop docs read, and any excluded, unmapped, or ambiguous paths that affect the work.
