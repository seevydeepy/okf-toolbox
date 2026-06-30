# OKF Wiki Renderer Limitations

The generated readers (`<docs-root>/wiki.html`, `<docs-root>/okf/<solution-id>/wiki.html`) are built by `tools/docs/build_okf_wikis.py`, copied from the okf-toolbox bootstrap template. The converter is intentionally small and dependency-free; it is not a full CommonMark or GFM implementation.

## Source of truth

Edit route cards and bundle markdown under `<docs-root>/okf/`. Regenerate with `.\tools\docs\build_all_wikis.ps1` (or `python tools/docs/build_okf_wikis.py --repo .`). Do not hand-edit generated HTML except to inspect output.

## Supported

| Feature | Notes |
|---------|--------|
| ATX headings (`#` … `######`) | Anchor ids generated for in-page navigation |
| Paragraphs | Blank lines separate blocks |
| Fenced code blocks | Language class on `<pre><code>` when a fence info string is present |
| Bold / italic | `**`, `__`, `*`, `_` |
| Inline code | Backticks |
| Markdown links | In-bundle links become `#doc/<path>`; cross-solution `../<peer-id>/<page>` rewrites to peer `wiki.html` or umbrella `#doc/solutions/...` |
| Blockquotes | Lines starting with `>` |
| Horizontal rules | `---`, `***`, `___` on their own line |
| Simple pipe tables | Header row + separator row + body rows |

## Not supported or degraded

| Feature | Behaviour |
|---------|-----------|
| Setext headings | Treated as plain text |
| Nested lists | Not preserved; list items may flatten |
| Images / `![]()` | Not rendered as `<img>` |
| Task lists (`- [ ]`) | Checkbox syntax not honoured |
| Strikethrough, autolinks, footnotes | Ignored or passed through as text |
| Complex tables | No colspan, nested blocks in cells, etc. |

## Authoring guidance

- Keep OKF bundle pages short and route-focused; prefer bullet lists over deep nesting.
- Use markdown links for in-bundle and cross-solution navigation; avoid absolute `/concept.md` paths.
- Put large source-file routes in `routing.md`, not in `routing_guidance.card`, unless a file is always the universal first hop.
- If you need syntax outside this subset, keep the critical routing content in plain prose and bullets that the renderer handles reliably.

## Validation

`.\tools\docs\build_all_wikis.ps1 -Check -BrowserSmoke` rejects structurally invalid generated readers (missing payload, navigation, article host, or internal links). That smoke test does not prove full Markdown fidelity — only that the reader shell and link graph are usable.
