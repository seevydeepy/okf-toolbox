#!/usr/bin/env python3
"""Bootstrap a minimal OKF wiki infrastructure in a repository."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


@dataclass
class Solution:
    id: str
    name: str
    summary: str
    owned_paths: list[str]
    keywords: list[str]


@dataclass(frozen=True)
class OkfPaths:
    docs_root: str
    okf_root: str
    manifest: str
    index: str
    umbrella: str


DOC_ROOT_PREFERENCES = ("docs", "documentation", "doc", "wiki", "manual", "manuals")
SIMILAR_DOC_TOKENS = ("doc", "wiki", "manual")


def normalise_id(value: str) -> str:
    ident = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not ident:
        raise ValueError("solution id must contain a letter or digit")
    return ident


def normalise_path(value: str) -> str:
    cleaned = value.strip().replace("\\", "/").lstrip("./")
    if not cleaned:
        raise ValueError("owned path cannot be blank")
    return cleaned


def parse_solution(value: str) -> Solution:
    parts = value.split("|")
    if len(parts) != 5:
        raise ValueError("--solution must be 'id|Name|Summary|path1,path2|keyword1,keyword2'")
    ident, name, summary, paths, keywords = parts
    return Solution(
        id=normalise_id(ident),
        name=name.strip() or ident.strip(),
        summary=summary.strip() or f"{name.strip() or ident.strip()} solution.",
        owned_paths=[normalise_path(p) for p in paths.split(",") if p.strip()],
        keywords=[k.strip() for k in keywords.split(",") if k.strip()],
    )


def load_solutions(args: argparse.Namespace) -> list[Solution]:
    raw: list[dict] = []
    if args.spec:
        payload = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        raw.extend(payload.get("solutions", []))
    for item in args.solution or []:
        parsed = parse_solution(item)
        raw.append(parsed.__dict__)
    solutions = [
        Solution(
            id=normalise_id(item["id"]),
            name=item.get("name", item["id"]).strip(),
            summary=item.get("summary", f"{item.get('name', item['id'])} solution.").strip(),
            owned_paths=[normalise_path(p) for p in item.get("owned_paths", [])],
            keywords=[str(k).strip() for k in item.get("keywords", []) if str(k).strip()],
        )
        for item in raw
    ]
    if not solutions:
        raise ValueError("provide at least one solution via --spec or --solution")
    seen: set[str] = set()
    for solution in solutions:
        if solution.id in seen:
            raise ValueError(f"duplicate solution id: {solution.id}")
        if not solution.owned_paths:
            raise ValueError(f"solution {solution.id} needs at least one owned_path")
        seen.add(solution.id)
    return solutions


def write(path: Path, text: str, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"refusing to overwrite {path}; pass --force to replace")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(text).strip() + "\n", encoding="utf-8", newline="\n")


def rel_to_repo(repo: Path, path: Path) -> str:
    return path.relative_to(repo).as_posix()


def find_existing_manifest(repo: Path) -> Path | None:
    for root in DOC_ROOT_PREFERENCES:
        path = repo / root / "solutions.manifest.json"
        if path.exists():
            return path
    for path in sorted(repo.glob("*/solutions.manifest.json")):
        if any(token in path.parent.name.lower() for token in SIMILAR_DOC_TOKENS):
            return path
    return None


def preferred_docs_root(repo: Path) -> str:
    dirs = [path for path in repo.iterdir() if path.is_dir() and not path.name.startswith(".")]
    for wanted in DOC_ROOT_PREFERENCES:
        for path in dirs:
            if path.name.lower() == wanted:
                return path.name
    similar = sorted(path.name for path in dirs if any(token in path.name.lower() for token in SIMILAR_DOC_TOKENS))
    return similar[0] if similar else "docs"


def choose_okf_paths(repo: Path) -> OkfPaths:
    existing_manifest = find_existing_manifest(repo)
    docs_root = rel_to_repo(repo, existing_manifest.parent) if existing_manifest else preferred_docs_root(repo)
    docs_root = normalise_path(docs_root)
    okf_root = f"{docs_root}/okf"
    return OkfPaths(
        docs_root=docs_root,
        okf_root=okf_root,
        manifest=f"{docs_root}/solutions.manifest.json",
        index=f"{okf_root}/index.md",
        umbrella=f"{docs_root}/wiki.html",
    )


AGENTS_START = "<!-- OKF-ROUTING:START -->"
AGENTS_END = "<!-- OKF-ROUTING:END -->"


def agents_block(paths: OkfPaths) -> str:
    return dedent(f"""
    {AGENTS_START}
    ## OKF Routing

    At the start of substantive repository work, if `{paths.manifest}` exists, use `$okf-router` to select the relevant OKF bundle before broad source inspection. If the skill is unavailable, manually inspect the manifest and read only the matched `{paths.okf_root}/<id>/routing_guidance.card`, then `solution.md` if needed.

    At the end of substantive code, config, tooling, ownership, or routing changes, use `$okf-archivist` to check whether OKF docs need updating.
    {AGENTS_END}
""").strip()


def patch_agents(repo: Path, paths: OkfPaths) -> str:
    path = repo / "AGENTS.md"
    original = path.read_text(encoding="utf-8") if path.exists() else ""
    pattern = re.compile(f"{re.escape(AGENTS_START)}.*?{re.escape(AGENTS_END)}", re.S)
    block = agents_block(paths)
    if pattern.search(original):
        updated = pattern.sub(block, original).rstrip() + "\n"
    elif original.strip():
        updated = original.rstrip() + "\n\n" + block + "\n"
    else:
        updated = block + "\n"
    if updated != original:
        path.write_text(updated, encoding="utf-8", newline="\n")
        return "updated"
    return "unchanged"


def solution_docs(solution: Solution, okf_root: str) -> dict[str, str]:
    root = f"{okf_root}/{solution.id}"
    return {
        "root": root,
        "routing_guidance_card": f"{root}/routing_guidance.card",
        "solution": f"{root}/solution.md",
        "routing": f"{root}/routing.md",
        "log": f"{root}/log.md",
        "wiki": f"{root}/wiki.html",
    }


def manifest(solutions: list[Solution], paths: OkfPaths) -> dict:
    return {
        "okf_version": "1.0",
        "wiki": {
            "root": paths.okf_root,
            "index": paths.index,
            "umbrella": paths.umbrella,
            "generated_files": [paths.index, paths.umbrella],
        },
        "routing": {
            "primary_doc": "routing_guidance.card",
            "bundle_docs": ["solution.md", "routing.md", "log.md"],
        },
        "excluded_paths": [
            f"{paths.okf_root}/",
            paths.umbrella,
            paths.manifest,
            "tools/docs/",
        ],
        "solutions": [
            {
                "id": s.id,
                "name": s.name,
                "summary": s.summary,
                "owned_paths": s.owned_paths,
                "routing_keywords": s.keywords,
                "docs": solution_docs(s, paths.okf_root),
            }
            for s in solutions
        ],
    }


def bullet(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) or "- Unknown until deep backfill."


def card(solution: Solution, docs: dict[str, str]) -> str:
    return f"""
    # {solution.name} Routing Card

    id: {solution.id}
    owned_paths:
    {bullet(solution.owned_paths)}
    read_first:
    - {docs["routing_guidance_card"]}
    - {docs["solution"]}
    keywords:
    {bullet(solution.keywords)}
    handoffs:
    - Unknown until deep backfill.
    """


def solution_md(solution: Solution) -> str:
    return f"""
    # {solution.name}

    ## Purpose

    {solution.summary}

    ## Owned Paths

    {bullet(solution.owned_paths)}

    ## Entrypoints

    - Unknown until deep backfill.

    ## Neighbouring Systems

    - Unknown until deep backfill.

    ## Maintenance Notes

    - Keep this page focused on stable ownership, entrypoints, and contracts.
    - Use `routing.md` for symptom/search routing details.
    """


def routing_md(solution: Solution, docs: dict[str, str]) -> str:
    return f"""
    # {solution.name} Routing

    ## Read This When

    - A change touches one of this solution's owned paths.
    - A symptom matches one of this solution's routing keywords.

    ## First Files To Inspect

    - `{docs["routing_guidance_card"]}`
    - `{docs["solution"]}`

    ## Owned Paths

    {bullet(solution.owned_paths)}

    ## Symptoms And Search Terms

    {bullet(solution.keywords)}

    ## Handoffs

    - Unknown until deep backfill.
    """


def log_md(solution: Solution) -> str:
    return f"""
    # {solution.name} OKF Log

    ## Bootstrap

    - Shallow OKF bundle created from repository structure.
    - Deep backfill has not run yet.

    ## Known Gaps

    - Entrypoints, neighbouring systems, and cross-solution handoffs need evidence-backed backfill.
    """


BUILD_OKF_WIKIS = r'''
#!/usr/bin/env python3
"""Generate deterministic OKF wiki readers from solutions.manifest.json."""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path


def rel(repo: Path, value: str) -> Path:
    return repo / value.replace("\\", "/")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


DOC_ROOT_PREFERENCES = ("docs", "documentation", "doc", "wiki", "manual", "manuals")
SIMILAR_DOC_TOKENS = ("doc", "wiki", "manual")


def find_manifest(repo: Path) -> Path:
    for root in DOC_ROOT_PREFERENCES:
        path = repo / root / "solutions.manifest.json"
        if path.exists():
            return path
    for path in sorted(repo.glob("*/solutions.manifest.json")):
        if any(token in path.parent.name.lower() for token in SIMILAR_DOC_TOKENS):
            return path
    raise FileNotFoundError("could not find solutions.manifest.json in a docs/documentation-like folder")


def markdown_to_html(text: str) -> str:
    out: list[str] = []
    in_list = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("# "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h1>{html.escape(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<h2>{html.escape(line[3:].strip())}</h2>")
        elif line.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{html.escape(line[2:].strip())}</li>")
        elif line.strip():
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<p>{html.escape(line.strip())}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def page(title: str, body: str) -> str:
    return "\n".join([
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        f"  <title>{html.escape(title)}</title>",
        '  <style>body{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;line-height:1.5} code{background:#f3f3f3;padding:.1rem .25rem}</style>',
        "</head>",
        "<body>",
        body,
        "</body>",
        "</html>",
        "",
    ])


def expected_outputs(repo: Path, manifest: dict) -> dict[Path, str]:
    outputs: dict[Path, str] = {}
    links = []
    for solution in manifest.get("solutions", []):
        docs = solution["docs"]
        required = [docs["routing_guidance_card"], docs["solution"], docs["routing"], docs["log"]]
        missing = [p for p in required if not rel(repo, p).exists()]
        if missing:
            raise FileNotFoundError(f"{solution['id']} missing OKF docs: {', '.join(missing)}")
        body = [f"<h1>{html.escape(solution['name'])}</h1>"]
        for key in ("routing_guidance_card", "solution", "routing", "log"):
            body.append(markdown_to_html(read(rel(repo, docs[key]))))
        wiki_path = rel(repo, docs["wiki"])
        outputs[wiki_path] = page(f"{solution['name']} OKF Wiki", "\n".join(body))
        links.append(f"- [{solution['name']}]({docs['wiki']})")
    index_md = "# OKF Wiki Index\n\n" + "\n".join(links) + "\n"
    outputs[rel(repo, manifest["wiki"].get("index", "docs/okf/index.md"))] = index_md
    outputs[rel(repo, manifest["wiki"].get("umbrella", "docs/wiki.html"))] = page("OKF Wiki", markdown_to_html(index_md))
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--browser-smoke", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    manifest = json.loads(read(find_manifest(repo)))
    outputs = expected_outputs(repo, manifest)
    stale: list[str] = []
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or read(path) != content:
                stale.append(str(path.relative_to(repo)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    if args.browser_smoke:
        for path, content in outputs.items():
            if path.suffix == ".html" and "<html" not in content.lower():
                raise RuntimeError(f"bad html output: {path}")
    if stale:
        print("OKF generated files are stale:")
        for item in stale:
            print(f"- {item}")
        return 1
    print("OKF wiki build check passed." if args.check else "OKF wiki build complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

MAP_CHANGED_PATHS = r'''
#!/usr/bin/env python3
"""Map changed paths to OKF solutions using solutions.manifest.json."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def norm(value: str) -> str:
    return value.strip().replace("\\", "/").lstrip("./")


def is_match(path: str, owned: str) -> bool:
    owned = norm(owned)
    path = norm(path)
    if owned.endswith("/"):
        return path.startswith(owned)
    return path == owned or path.startswith(owned + "/")


DOC_ROOT_PREFERENCES = ("docs", "documentation", "doc", "wiki", "manual", "manuals")
SIMILAR_DOC_TOKENS = ("doc", "wiki", "manual")


def find_manifest(repo: Path) -> Path:
    for root in DOC_ROOT_PREFERENCES:
        path = repo / root / "solutions.manifest.json"
        if path.exists():
            return path
    for path in sorted(repo.glob("*/solutions.manifest.json")):
        if any(token in path.parent.name.lower() for token in SIMILAR_DOC_TOKENS):
            return path
    raise FileNotFoundError("could not find solutions.manifest.json in a docs/documentation-like folder")


def git_paths(repo: Path) -> list[str]:
    commands = [
        ["git", "diff", "--name-only", "--cached"],
        ["git", "diff", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    found: list[str] = []
    for command in commands:
        result = subprocess.run(command, cwd=repo, text=True, capture_output=True, check=False)
        if result.returncode == 0:
            found.extend(p for p in result.stdout.splitlines() if p.strip())
    return sorted(set(found))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    manifest_path = find_manifest(repo)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = [norm(p) for p in (args.paths or git_paths(repo))]
    excluded_prefixes = [norm(p) for p in manifest.get("excluded_paths", [])]
    result = {"manifest": str(manifest_path), "matched": [], "excluded": [], "unmapped": [], "ambiguous": []}
    for path in paths:
        if any(is_match(path, prefix) for prefix in excluded_prefixes):
            result["excluded"].append(path)
            continue
        matches = [s for s in manifest.get("solutions", []) if any(is_match(path, p) for p in s.get("owned_paths", []))]
        if len(matches) == 1:
            s = matches[0]
            result["matched"].append({"path": path, "solution_id": s["id"], "docs": s["docs"]})
        elif len(matches) > 1:
            result["ambiguous"].append({"path": path, "solution_ids": [s["id"] for s in matches]})
        else:
            result["unmapped"].append(path)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

BUILD_ALL_WIKIS_PS1 = r'''
param(
    [switch]$Check,
    [switch]$BrowserSmoke
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$Script = Join-Path $PSScriptRoot 'build_okf_wikis.py'
$Args = @($Script, '--repo', $RepoRoot)
if ($Check) { $Args += '--check' }
if ($BrowserSmoke) { $Args += '--browser-smoke' }
& python @Args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
'''


def bootstrap(repo: Path, solutions: list[Solution], force: bool) -> None:
    existing_manifest = find_existing_manifest(repo)
    paths = choose_okf_paths(repo)
    manifest_path = repo / paths.manifest
    if existing_manifest and not force:
        raise FileExistsError("OKF manifest already exists; use --force only when intentionally replacing bootstrap files")
    data = manifest(solutions, paths)
    write(manifest_path, json.dumps(data, indent=2), True)
    for solution in solutions:
        docs = solution_docs(solution, paths.okf_root)
        write(repo / docs["routing_guidance_card"], card(solution, docs), force)
        write(repo / docs["solution"], solution_md(solution), force)
        write(repo / docs["routing"], routing_md(solution, docs), force)
        write(repo / docs["log"], log_md(solution), force)
    write(repo / "tools/docs/build_okf_wikis.py", BUILD_OKF_WIKIS, True)
    write(repo / "tools/docs/map_changed_paths.py", MAP_CHANGED_PATHS, True)
    write(repo / "tools/docs/build_all_wikis.ps1", BUILD_ALL_WIKIS_PS1, True)
    agents_status = patch_agents(repo, paths)
    print(f"Bootstrapped OKF for {len(solutions)} solution(s).")
    print(f"OKF docs root: {paths.docs_root}")
    print(f"AGENTS.md OKF routing block {agents_status}.")
    print("Run: .\\tools\\docs\\build_all_wikis.ps1")
    print("Run: .\\tools\\docs\\build_all_wikis.ps1 -Check")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="repository root to bootstrap")
    parser.add_argument("--spec", help="JSON spec with a solutions array")
    parser.add_argument("--solution", action="append", help="id|Name|Summary|path1,path2|keyword1,keyword2")
    parser.add_argument("--force", action="store_true", help="overwrite existing generated/bootstrap files")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    bootstrap(repo, load_solutions(args), args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
