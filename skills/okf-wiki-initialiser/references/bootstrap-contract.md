# OKF Route-Pack Bootstrap Contract

Use this contract when bootstrapping a repository that has no existing OKF examples. The bootstrap must leave enough route-card structure for `okf-router` to start work without broad prose reads, and for `okf-archivist` to maintain routing later.

## Documentation root

Reuse an existing root documentation folder before creating a new one. Prefer `docs/`, then `documentation/`, `doc/`, `wiki/`, `manual/`, `manuals/`, then similarly named folders containing `doc`, `wiki`, or `manual`. Create root `docs/` only when no similar folder exists.

In this contract, `<docs-root>` means that chosen folder.

## Required files

A conformant shallow bootstrap creates these files:

```text
<docs-root>/solutions.manifest.json
<docs-root>/wiki.html
AGENTS.md
<docs-root>/okf/index.md
<docs-root>/okf/<solution-id>/routing_guidance.card
<docs-root>/okf/<solution-id>/solution.md
<docs-root>/okf/<solution-id>/routing.md
<docs-root>/okf/<solution-id>/log.md
<docs-root>/okf/<solution-id>/wiki.html
tools/docs/build_all_wikis.ps1
tools/docs/build_okf_wikis.py
tools/docs/map_changed_paths.py
tools/docs/check_okf_route_cards.py
```

Generated files are `<docs-root>/wiki.html`, `<docs-root>/okf/index.md`, and each `<docs-root>/okf/<solution-id>/wiki.html`. Keep generated content deterministic: no timestamps.

Generated HTML readers are self-contained route-pack browsers, not the source of truth. They must provide sidebar navigation, search, type filtering, working Markdown links, outgoing-link and backlink sections, and route metadata panels when frontmatter supplies routing fields. The umbrella reader is built as a virtual bundle over all solution bundles, so cross-solution links can be browsed from one file. Markdown authoring limits for generated readers are documented in `renderer-limitations.md` in this references folder.

`AGENTS.md` is created or patched with a marked `OKF-ROUTING` block. Preserve any existing instructions outside the markers. The block tells the agent to use `$okf-router` at the start of substantive repository work for route evidence only and `$okf-archivist` at the end of substantive changes. It must not imply that OKF routing declares requirements stable, approves plans, authorises implementation, creates worktrees, or bypasses any active workflow/repository gate.

## Bootstrap script

Prefer the bundled script over hand-writing infrastructure:

```powershell
python <okf-toolbox>\skills\okf-wiki-initialiser\scripts\bootstrap_okf.py --repo . --spec okf-bootstrap.json
```

Minimal `okf-bootstrap.json`:

```json
{
  "solutions": [
    {
      "id": "web",
      "name": "Web",
      "summary": "User-facing web application.",
      "owned_paths": ["src/web/"],
      "keywords": ["controller", "view", "route"]
    }
  ]
}
```

For one-off use, repeat `--solution` instead:

```powershell
python <skill>\scripts\bootstrap_okf.py --repo . --solution "web|Web|User-facing web application.|src/web/|controller,view,route"
```

Use lower-case kebab-case ids. Put `/` on directory prefixes (`src/web/`), and exact paths for files.

## Manifest contract

`<docs-root>/solutions.manifest.json` must contain:

- `okf_version`: string, currently `1.0`.
- `wiki.root`: normally `<docs-root>/okf`.
- `wiki.umbrella`: normally `<docs-root>/wiki.html`.
- `routing.primary_doc`: `routing_guidance.card`.
- `routing.bundle_docs`: at least `solution.md`, `routing.md`, `log.md`.
- `routing.card_check`: normally `tools/docs/check_okf_route_cards.py`.
- `excluded_paths`: generated or OKF-maintenance paths the Archivist should ignore for ordinary code-change routing.
- `solutions[]`: one entry per logical solution/subsystem.

Each solution entry must contain:

- `id`, `name`, `summary`.
- `owned_paths`: path prefixes or exact files used by `map_changed_paths.py`.
- `routing_keywords`: search/symptom terms.
- `docs.root`, `docs.routing_guidance_card`, `docs.solution`, `docs.routing`, `docs.log`, `docs.wiki`.

## Bundle contract

`routing_guidance.card` is the first-hop card. Keep it short and route-focused:

```text
# <Name> Routing Card

id: <id>
owned_paths:
  - <path/>
read_first:
  - <docs-root>/okf/<id>/routing_guidance.card
  - <docs-root>/okf/<id>/solution.md
keywords:
  - <keyword>
handoffs:
  - Unknown until deep backfill.
validation:
  - python tools/docs/map_changed_paths.py <representative-owned-path>
  - .\tools\docs\build_all_wikis.ps1 -Check
stale_notes:
  - Review after ownership, entrypoint, handoff, or validation changes.
```

`solution.md` captures stable ownership: purpose, owned paths, entrypoints, neighbours, and maintenance notes.

`routing.md` captures routing: when to read this bundle, symptoms/search terms, first files to inspect, and handoffs.

`log.md` records bootstrap and backfill evidence, including ambiguous ownership and known gaps.

## Mapper contract

`python tools/docs/map_changed_paths.py <paths...>` prints JSON with:

- `matched`: paths mapped to one solution.
- `excluded`: OKF/generated/tooling paths intentionally ignored.
- `unmapped`: paths no solution owns.
- `ambiguous`: paths matching more than one solution.

Archivist reports excluded, unmapped, and ambiguous paths instead of hiding them.

## Card checker contract

`python tools/docs/check_okf_route_cards.py --repo .` must fail when a routing card is not self-sufficient enough for first-hop routing. It checks that every manifest solution has a card, the card id matches the manifest id, `read_first` starts with the card and `solution.md`, manifest-owned paths and keywords are mirrored in the card, and these sections are non-empty: `owned_paths`, `read_first`, `keywords`, `handoffs`, `validation`, and `stale_notes`.

## Validation

After bootstrap, run:

```powershell
.\tools\docs\build_all_wikis.ps1
.\tools\docs\build_all_wikis.ps1 -Check
.\tools\docs\build_all_wikis.ps1 -Check -BrowserSmoke
python tools/docs/check_okf_route_cards.py --repo .
python tools/docs/map_changed_paths.py <representative-owned-path>
```

A shallow pass is complete only when the build/check pass, every solution has the required bundle files, every route card passes the card checker, representative owned paths map correctly, `AGENTS.md` contains one `OKF-ROUTING` block, and ambiguous ownership is recorded rather than guessed away.

`-BrowserSmoke` must reject structurally invalid generated readers: missing OKF data payload, missing document navigation, missing article host, or no internal links. Markdown links in bundle docs must render as HTML anchors. Per-solution readers keep in-bundle links as `#doc/...` links and rewrite cross-solution authoring links of the form `../<solution-id>/<page>` to the peer solution `wiki.html`; the umbrella reader rewrites those links to `#doc/solutions/<solution-id>/<page>`.

## Deep backfill boundary

Do not run deep backfill during the default bootstrap. After the shallow pass, one explorer may be assigned per solution to fill only that solution's `solution.md`, `routing.md`, and `log.md`. The main agent must review handoffs and rerun the validation above.

Before accepting deep backfill:

- Run a full tracked-file mapper pass, for example `$paths = git ls-files; python tools/docs/map_changed_paths.py @paths` in PowerShell; report and fix unexpected `unmapped` or `ambiguous` paths.
- Verify every `routing_guidance.card` keeps `read_first` starting with its own `<docs-root>/okf/<id>/routing_guidance.card` and `<docs-root>/okf/<id>/solution.md`.
- Verify every `routing_guidance.card` passes `python tools/docs/check_okf_route_cards.py --repo .`.
- Keep broad source files out of `routing_guidance.card` unless they are the universal first owner file; put symptom-specific source routes in `routing.md`.
- Rebuild/check the generated readers, and inspect generated links when generator or Markdown shape changed.

The final bootstrap report must offer the deep backfill as the next step. Do not frame it as merely "skipped"; state whether it is ready or blocked, and ask the user to approve it if they want the wiki filled beyond the shallow scaffold.
