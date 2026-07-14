#!/usr/bin/env python3
"""Bootstrap a minimal OKF route-pack infrastructure in a repository."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass, field
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
SOLUTION_SUFFIXES = {".sln", ".slnx", ".code-workspace"}
PROJECT_SUFFIXES = {
    ".csproj",
    ".fsproj",
    ".vbproj",
    ".vcproj",
    ".vcxproj",
    ".dbp",
    ".dbproj",
    ".sqlproj",
}
PROJECT_FILENAMES = {
    "build.gradle",
    "build.gradle.kts",
    "cargo.toml",
    "go.mod",
    "package.json",
    "pom.xml",
    "pyproject.toml",
}
IGNORED_DISCOVERY_DIRS = {
    ".agents",
    ".cursor",
    ".git",
    ".hg",
    ".idea",
    ".svn",
    ".vs",
    ".vscode",
    "__pycache__",
    "bin",
    "coverage",
    "dist",
    "docs",
    "documentation",
    "manual",
    "manuals",
    "node_modules",
    "obj",
    "out",
    "target",
    "third-party",
    "third_party",
    "vendor",
    "wiki",
}
SUPPORT_DIRECTORY_TOKENS = {
    "external",
    "externals",
    "fixture",
    "fixtures",
    "generated",
    "libraries",
    "shared",
    "testdata",
    "thirdparty",
}
TEST_TOKENS = {
    "acceptance",
    "benchmark",
    "benchmarks",
    "example",
    "examples",
    "qa",
    "sample",
    "samples",
    "test",
    "testing",
    "tests",
}
GENERIC_SEAM_NAMES = {
    "app",
    "apps",
    "common",
    "component",
    "components",
    "lib",
    "libs",
    "libraries",
    "library",
    "module",
    "modules",
    "package",
    "packages",
    "project",
    "projects",
    "service",
    "services",
    "solution",
    "solutions",
    "source",
    "src",
    "vp",
    "web",
}
TOKEN_PATTERN = re.compile(r"[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|[A-Z]?[a-z]+|[0-9]+")


@dataclass
class DiscoveryCandidate:
    root: Path | None
    descriptors: list[Path]
    source_kind: str
    promoted: bool = False
    additional_roots: list[Path] = field(default_factory=list)
    supporting_descriptors: list[Path] = field(default_factory=list)


def normalise_id(value: str) -> str:
    ident = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not ident:
        raise ValueError("solution id must contain a letter or digit")
    return ident


def normalise_path(value: str) -> str:
    cleaned = value.strip().replace("\\", "/")
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    cleaned = cleaned.lstrip("/")
    if not cleaned:
        raise ValueError("owned path cannot be blank")
    return cleaned


def name_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    for chunk in re.sub(r"[^A-Za-z0-9]+", " ", value).split():
        matches = TOKEN_PATTERN.findall(chunk)
        tokens.extend((matches or [chunk]))
    return [token.lower() for token in tokens if token]


def name_key(value: str) -> str:
    return "".join(name_tokens(value))


def humanise_name(value: str) -> str:
    words: list[str] = []
    for chunk in re.sub(r"[^A-Za-z0-9]+", " ", value).split():
        words.extend(TOKEN_PATTERN.findall(chunk) or [chunk])
    return " ".join(word if word.isupper() else word.capitalize() for word in words)


def descriptor_kind(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in SOLUTION_SUFFIXES:
        return "solution"
    if suffix in PROJECT_SUFFIXES or path.name.lower() in PROJECT_FILENAMES:
        return "project"
    return None


def descriptor_label(path: Path) -> str:
    return path.parent.name if path.name.lower() in PROJECT_FILENAMES else path.stem


def is_test_path(repo: Path, path: Path) -> bool:
    relative = path.relative_to(repo)
    return any(TEST_TOKENS.intersection(name_tokens(part)) for part in relative.parts)


def find_build_descriptors(repo: Path) -> dict[str, list[Path]]:
    descriptors: dict[str, list[Path]] = {"solution": [], "project": []}
    for current, dirnames, filenames in os.walk(repo):
        dirnames[:] = sorted(
            name for name in dirnames
            if not name.startswith(".") and name.lower() not in IGNORED_DISCOVERY_DIRS
        )
        current_path = Path(current)
        for filename in sorted(filenames):
            path = current_path / filename
            kind = descriptor_kind(path)
            if kind:
                descriptors[kind].append(path)
    return descriptors


def is_meaningful_seam_name(value: str) -> bool:
    key = name_key(value)
    return len(key) >= 4 and key not in GENERIC_SEAM_NAMES


def is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def choose_semantic_root(repo: Path, descriptor: Path, peers: list[Path]) -> tuple[Path | None, bool]:
    if descriptor.parent == repo:
        return None, False

    root = descriptor.parent
    promoted = False
    descriptor_name = name_key(descriptor_label(descriptor))
    ancestor = descriptor.parent.parent
    while ancestor != repo and is_under(ancestor, repo):
        ancestor_name = name_key(ancestor.name)
        lexical_family = (
            is_meaningful_seam_name(ancestor.name)
            and (ancestor_name in descriptor_name or descriptor_name in ancestor_name)
        )
        family_peers = [path for path in peers if is_under(path, ancestor)]
        branches = {
            path.relative_to(ancestor).parts[0]
            for path in family_peers
            if path.relative_to(ancestor).parts
        }
        structural_family = (
            is_meaningful_seam_name(ancestor.name)
            and len(family_peers) >= 2
            and len(branches) >= 2
        )
        if lexical_family or structural_family:
            root = ancestor
            promoted = True
        ancestor = ancestor.parent
    return root, promoted


def merge_nested_candidates(candidates: list[DiscoveryCandidate]) -> list[DiscoveryCandidate]:
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            len(candidate.root.parts) if candidate.root else 10_000,
            candidate.root.as_posix() if candidate.root else candidate.descriptors[0].as_posix(),
        ),
    )
    removed: set[int] = set()
    for index, outer in enumerate(ordered):
        if index in removed or outer.root is None:
            continue
        for nested_index, inner in enumerate(ordered):
            if nested_index == index or nested_index in removed or inner.root is None:
                continue
            if outer.root != inner.root and is_under(inner.root, outer.root):
                # Prefix ownership cannot represent nested independent owners without
                # ambiguity. Keep the outer semantic/solution seam and expose every
                # absorbed descriptor as discovery evidence for human review.
                outer.descriptors.extend(inner.descriptors)
                outer.additional_roots.extend(inner.additional_roots)
                outer.supporting_descriptors.extend(inner.supporting_descriptors)
                outer.promoted = True
                removed.add(nested_index)
    return [candidate for index, candidate in enumerate(ordered) if index not in removed]


def group_descriptors(repo: Path, descriptors: list[Path], source_kind: str) -> list[DiscoveryCandidate]:
    groups: dict[str, DiscoveryCandidate] = {}
    for descriptor in descriptors:
        root, promoted = choose_semantic_root(repo, descriptor, descriptors)
        key = root.as_posix() if root else f"@{descriptor.relative_to(repo).as_posix()}"
        if key not in groups:
            groups[key] = DiscoveryCandidate(root, [], source_kind, promoted)
        groups[key].descriptors.append(descriptor)
        groups[key].promoted = groups[key].promoted or promoted
    return merge_nested_candidates(list(groups.values()))


def candidate_owned_paths(repo: Path, candidate: DiscoveryCandidate) -> list[str]:
    if candidate.root is None:
        paths = [candidate.descriptors[0].relative_to(repo).as_posix()]
    else:
        paths = [candidate.root.relative_to(repo).as_posix().rstrip("/") + "/"]
    paths.extend(path.relative_to(repo).as_posix().rstrip("/") + "/" for path in candidate.additional_roots)
    return list(dict.fromkeys(paths))


def candidate_name(candidate: DiscoveryCandidate) -> str:
    if candidate.root and name_key(candidate.root.name) not in GENERIC_SEAM_NAMES:
        return humanise_name(candidate.root.name)
    return humanise_name(descriptor_label(candidate.descriptors[0]))


def candidate_keywords(repo: Path, candidate: DiscoveryCandidate, name: str) -> list[str]:
    values: list[str] = []
    sources = [name]
    if candidate.root:
        sources.extend(candidate.root.relative_to(repo).parts)
    sources.extend(descriptor_label(path) for path in candidate.descriptors)
    for source in sources:
        for token in name_tokens(source):
            if token not in TEST_TOKENS and token not in values:
                values.append(token)
    return values[:10] or [normalise_id(name)]


def candidate_basis(candidate: DiscoveryCandidate) -> tuple[str, str]:
    if candidate.promoted or len(candidate.descriptors) > 1:
        return "semantic-family", "high"
    if candidate.source_kind == "solution":
        return "solution-fallback", "medium"
    if candidate.source_kind == "project":
        return "project-fallback", "low"
    return "directory-fallback", "low"


def top_level_directory_candidates(repo: Path) -> list[DiscoveryCandidate]:
    candidates: list[DiscoveryCandidate] = []
    content_directories = source_content_directories(repo)
    for path in sorted(repo.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_dir() or path.name.startswith(".") or path.name.lower() in IGNORED_DISCOVERY_DIRS:
            continue
        if path in content_directories:
            candidates.append(DiscoveryCandidate(path, [path], "directory"))
    return candidates


def source_content_directories(repo: Path) -> set[Path]:
    directories: set[Path] = set()
    for current, dirnames, filenames in os.walk(repo):
        dirnames[:] = [
            name for name in dirnames
            if not name.startswith(".") and name.lower() not in IGNORED_DISCOVERY_DIRS
        ]
        if not filenames:
            continue
        path = Path(current)
        while path != repo and is_under(path, repo):
            directories.add(path)
            path = path.parent
    return directories


def ignored_source_roots(repo: Path) -> list[Path]:
    roots: list[Path] = []
    for current, dirnames, _ in os.walk(repo):
        current_path = Path(current)
        ignored = [name for name in dirnames if name.lower() in IGNORED_DISCOVERY_DIRS]
        roots.extend(current_path / name for name in ignored)
        dirnames[:] = [name for name in dirnames if name.lower() not in IGNORED_DISCOVERY_DIRS]
    return roots


def directory_fallbacks(
    repo: Path,
    candidates: list[DiscoveryCandidate],
) -> tuple[list[DiscoveryCandidate], list[Path]]:
    candidate_roots = [candidate.root for candidate in candidates if candidate.root]
    content_directories = source_content_directories(repo)
    fallbacks: list[DiscoveryCandidate] = []
    support_roots: list[Path] = []

    def visit(path: Path) -> None:
        if path not in content_directories:
            return
        if path.name.startswith(".") or path.name.lower() in IGNORED_DISCOVERY_DIRS:
            return
        if any(is_under(path, root) for root in candidate_roots):
            return
        descendants = [root for root in candidate_roots if is_under(root, path)]
        if not descendants:
            tokens = set(name_tokens(path.name))
            if tokens.intersection(TEST_TOKENS) or tokens.intersection(SUPPORT_DIRECTORY_TOKENS):
                support_roots.append(path)
            else:
                fallbacks.append(DiscoveryCandidate(path, [path], "directory"))
            return
        for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
            if child.is_dir():
                visit(child)

    for child in sorted(repo.iterdir(), key=lambda item: item.name.lower()):
        if child.is_dir():
            visit(child)
    return fallbacks, support_roots


def minimal_prefixes(repo: Path, paths: list[Path]) -> list[str]:
    prefixes: list[Path] = []
    for path in sorted(set(paths), key=lambda item: (len(item.parts), item.as_posix().lower())):
        if not any(is_under(path, prefix) for prefix in prefixes):
            prefixes.append(path)
    return [
        path.relative_to(repo).as_posix().rstrip("/") + ("/" if path.is_dir() else "")
        for path in prefixes
    ]


def owner_affinity_keys(candidate: DiscoveryCandidate) -> set[str]:
    values = [candidate_name(candidate)]
    if candidate.root:
        values.append(candidate.root.name)
    values.extend(descriptor_label(path) for path in candidate.descriptors)
    return {name_key(value) for value in values if name_key(value)}


def test_affinity_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for value in (descriptor_label(path), path.parent.name):
        tokens = [token for token in name_tokens(value) if token not in TEST_TOKENS]
        if tokens:
            keys.add("".join(tokens))
    return keys


def attach_test_descriptors(repo: Path, candidates: list[DiscoveryCandidate], test_descriptors: list[Path]) -> list[Path]:
    uncovered: list[Path] = []
    for descriptor in test_descriptors:
        owning = [
            candidate for candidate in candidates
            if candidate.root and is_under(descriptor, candidate.root)
        ]
        if owning:
            owning[0].supporting_descriptors.append(descriptor)
            continue
        affinity = test_affinity_keys(descriptor)
        matches = [candidate for candidate in candidates if affinity.intersection(owner_affinity_keys(candidate))]
        if len(matches) == 1:
            matches[0].additional_roots.append(descriptor.parent)
            matches[0].supporting_descriptors.append(descriptor)
        else:
            uncovered.append(descriptor)
    return uncovered


def discover_solution_spec(repo: Path) -> dict:
    descriptors = find_build_descriptors(repo)
    all_solutions = descriptors["solution"]
    production_solutions = [path for path in all_solutions if not is_test_path(repo, path)]
    candidates = group_descriptors(repo, production_solutions, "solution")

    solution_roots = [candidate.root for candidate in candidates if candidate.root]
    all_projects = descriptors["project"]
    production_projects = [
        path for path in all_projects
        if not is_test_path(repo, path)
        and not any(is_under(path, root) for root in solution_roots)
    ]
    project_candidates = group_descriptors(repo, production_projects, "project")
    candidates.extend(project_candidates)
    if not candidates:
        candidates = top_level_directory_candidates(repo)

    uncovered_fallbacks, support_roots = directory_fallbacks(repo, candidates)

    candidates = merge_nested_candidates(candidates)
    test_descriptors = [path for path in all_solutions + all_projects if is_test_path(repo, path)]
    uncovered_tests = attach_test_descriptors(repo, candidates, test_descriptors)
    candidate_roots = [candidate.root for candidate in candidates if candidate.root]
    owned_directory_roots = candidate_roots + [
        root for candidate in candidates for root in candidate.additional_roots
    ]
    support_roots = [
        path for path in support_roots
        if not any(is_under(path, root) for root in owned_directory_roots)
    ]
    ignored_roots = [
        path for path in ignored_source_roots(repo)
        if path.name != ".git"
        and path.name.lower() not in DOC_ROOT_PREFERENCES
        and not any(is_under(path, root) for root in owned_directory_roots)
    ]
    excluded_paths = minimal_prefixes(
        repo,
        [path if path.parent == repo else path.parent for path in uncovered_tests]
        + support_roots
        + ignored_roots,
    )
    seen_ids: set[str] = set()
    solutions: list[dict] = []
    for candidate in sorted(candidates, key=lambda item: candidate_owned_paths(repo, item)[0].lower()):
        name = candidate_name(candidate)
        ident = normalise_id(name)
        if ident in seen_ids:
            context = candidate.root.parent.name if candidate.root else candidate.descriptors[0].parent.name
            contextual_id = normalise_id(f"{context}-{name}")
            ident = contextual_id if contextual_id not in seen_ids else f"{ident}-{len(seen_ids) + 1}"
        seen_ids.add(ident)
        owned_paths = candidate_owned_paths(repo, candidate)
        basis, confidence = candidate_basis(candidate)
        solutions.append({
            "id": ident,
            "name": name,
            "summary": f"{name} product seam inferred from repository build structure under `{owned_paths[0]}`.",
            "owned_paths": owned_paths,
            "keywords": candidate_keywords(repo, candidate, name),
            "discovery": {
                "basis": basis,
                "confidence": confidence,
                "evidence": sorted(
                    path.relative_to(repo).as_posix()
                    for path in candidate.descriptors + candidate.supporting_descriptors
                ),
            },
        })

    if not solutions:
        raise ValueError("could not discover any semantic seam, solution, project, or source-directory fallback")

    warnings: list[str] = []
    if project_candidates:
        warnings.append("Some paths were not covered by a production solution/workspace and used project-file fallback.")
    if uncovered_fallbacks:
        warnings.append("Some source roots were not covered by a production solution or project descriptor and require semantic review.")
    if candidates and all(candidate.source_kind == "directory" for candidate in candidates):
        warnings.append("No production solution or project descriptors were found; directory fallback was used for the repository.")
    return {
        "discovery_version": "1.0",
        "strategy": "semantic-product-seams-with-solution-project-fallback",
        "review_required": True,
        "fallback_order": ["semantic-family", "solution", "project", "top-level-directory"],
        "solutions": solutions,
        "excluded_paths": excluded_paths,
        "uncovered_roots": [candidate_owned_paths(repo, candidate)[0] for candidate in uncovered_fallbacks],
        "warnings": warnings,
    }


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


def load_bootstrap_input(args: argparse.Namespace, repo: Path) -> tuple[list[Solution], list[str]]:
    raw: list[dict] = []
    excluded_paths: list[str] = []
    if args.discover:
        payload = discover_solution_spec(repo)
        if payload.get("uncovered_roots"):
            roots = ", ".join(payload["uncovered_roots"])
            raise ValueError(
                f"discovery left source roots requiring semantic review: {roots}; "
                "run --discover-only, review the candidates, then bootstrap with --spec"
            )
        raw.extend(payload["solutions"])
        excluded_paths.extend(payload.get("excluded_paths", []))
    if args.spec:
        payload = json.loads(Path(args.spec).read_text(encoding="utf-8"))
        if payload.get("uncovered_roots"):
            roots = ", ".join(payload["uncovered_roots"])
            raise ValueError(
                f"bootstrap spec still contains unresolved uncovered_roots: {roots}; "
                "assign or exclude them and clear the reviewed list before bootstrap"
            )
        raw.extend(payload.get("solutions", []))
        excluded_paths.extend(payload.get("excluded_paths", []))
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
        if not solution.keywords:
            raise ValueError(f"solution {solution.id} needs at least one keyword")
        seen.add(solution.id)
    return solutions, list(dict.fromkeys(normalise_path(path) for path in excluded_paths))


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

    At the start of substantive repository work, if `{paths.manifest}` exists, use `$okf-router` to select the relevant OKF route-card evidence before broad source inspection. If the skill is unavailable, manually inspect the manifest and read only the matched `{paths.okf_root}/<id>/routing_guidance.card`, then `solution.md` if needed.

    OKF routing is evidence for the next workflow step only. It does not declare requirements stable, write or approve plans, create worktrees, start implementation, or bypass any active workflow or repository gate.

    At the end of substantive code, config, tooling, ownership, or routing changes, use `$okf-archivist` to check whether OKF route cards or docs need updating.
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


def manifest(solutions: list[Solution], paths: OkfPaths, excluded_paths: list[str] | None = None) -> dict:
    exclusions = [
        f"{paths.okf_root}/",
        paths.umbrella,
        paths.manifest,
        "tools/docs/",
        ".agents/",
        ".cursor/",
        ".github/",
        ".gitignore",
        "AGENTS.md",
    ]
    exclusions.extend(excluded_paths or [])
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
            "card_check": "tools/docs/check_okf_route_cards.py",
        },
        "excluded_paths": list(dict.fromkeys(exclusions)),
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
    return f"""# {solution.name} Routing Card

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
validation:
- python tools/docs/map_changed_paths.py <representative-owned-path>
- .\\tools\\docs\\build_all_wikis.ps1 -Check
stale_notes:
- Review after ownership, entrypoint, handoff, or validation changes.
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


def load_script_template(name: str) -> str:
    return (Path(__file__).resolve().parent / name).read_text(encoding="utf-8")


BUILD_OKF_WIKIS = load_script_template("build_okf_wikis_template.py")

CHECK_ROUTE_CARDS = r'''
#!/usr/bin/env python3
"""Check OKF routing cards are usable as first-hop route-pack entries."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DOC_ROOT_PREFERENCES = ("docs", "documentation", "doc", "wiki", "manual", "manuals")
SIMILAR_DOC_TOKENS = ("doc", "wiki", "manual")
SECTION_NAMES = ("owned_paths", "read_first", "keywords", "handoffs", "validation", "stale_notes")


def norm(value: str) -> str:
    cleaned = value.strip().replace("\\", "/")
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned.lstrip("/")


def find_manifest(repo: Path) -> Path:
    for root in DOC_ROOT_PREFERENCES:
        path = repo / root / "solutions.manifest.json"
        if path.exists():
            return path
    for path in sorted(repo.glob("*/solutions.manifest.json")):
        if any(token in path.parent.name.lower() for token in SIMILAR_DOC_TOKENS):
            return path
    raise FileNotFoundError("could not find solutions.manifest.json in a docs/documentation-like folder")


def scalar(text: str, key: str) -> str:
    match = re.search(rf"^\s*{re.escape(key)}:\s*(.+?)\s*$", text, re.M)
    return match.group(1).strip() if match else ""


def section_values(lines: list[str], section: str) -> list[str]:
    values: list[str] = []
    collecting = False
    section_header = f"{section}:"
    for raw in lines:
        line = raw.strip()
        if line == section_header:
            collecting = True
            continue
        if collecting and re.match(r"^[A-Za-z_][A-Za-z0-9_]*:\s*$", line):
            break
        if collecting and line.startswith("- "):
            values.append(line[2:].strip())
    return values


def check_card(repo: Path, solution: dict, errors: list[str]) -> None:
    docs = solution.get("docs") or {}
    card_rel = norm(str(docs.get("routing_guidance_card") or ""))
    solution_rel = norm(str(docs.get("solution") or ""))
    if not card_rel:
        errors.append(f"{solution.get('id', '<unknown>')}: missing docs.routing_guidance_card")
        return
    card_path = repo / card_rel
    if not card_path.exists():
        errors.append(f"{solution.get('id', '<unknown>')}: missing routing card {card_rel}")
        return

    text = card_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    sid = str(solution.get("id") or "").strip()
    if scalar(text, "id") != sid:
        errors.append(f"{card_rel}: id does not match manifest solution id {sid}")

    sections = {name: section_values(lines, name) for name in SECTION_NAMES}
    for name, values in sections.items():
        if not values:
            errors.append(f"{card_rel}: missing non-empty {name} section")

    owned = [norm(p) for p in solution.get("owned_paths", [])]
    card_owned = [norm(p) for p in sections["owned_paths"]]
    missing_owned = [p for p in owned if p not in card_owned]
    if missing_owned:
        errors.append(f"{card_rel}: owned_paths missing manifest paths {missing_owned}")

    read_first = [norm(p) for p in sections["read_first"]]
    expected_first = [card_rel, solution_rel]
    if read_first[:2] != expected_first:
        errors.append(f"{card_rel}: read_first must start with {expected_first}")

    keywords = [str(k).strip() for k in solution.get("routing_keywords", []) if str(k).strip()]
    card_keywords = sections["keywords"]
    missing_keywords = [k for k in keywords if k not in card_keywords]
    if not keywords:
        errors.append(f"{card_rel}: manifest routing_keywords is empty")
    elif missing_keywords:
        errors.append(f"{card_rel}: keywords missing manifest terms {missing_keywords}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check OKF routing-card completeness.")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    manifest_path = find_manifest(repo)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    for solution in manifest.get("solutions", []):
        check_card(repo, solution, errors)
    if errors:
        print("OKF route-card check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("OKF route-card check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
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
    cleaned = value.strip().replace("\\", "/")
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned.lstrip("/")


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
$CardCheck = Join-Path $PSScriptRoot 'check_okf_route_cards.py'
$Script = Join-Path $PSScriptRoot 'build_okf_wikis.py'
& python $CardCheck --repo $RepoRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$Args = @($Script, '--repo', $RepoRoot)
if ($Check) { $Args += '--check' }
if ($BrowserSmoke) { $Args += '--browser-smoke' }
& python @Args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
'''


def bootstrap(repo: Path, solutions: list[Solution], force: bool, excluded_paths: list[str] | None = None) -> None:
    existing_manifest = find_existing_manifest(repo)
    paths = choose_okf_paths(repo)
    manifest_path = repo / paths.manifest
    if existing_manifest and not force:
        raise FileExistsError("OKF manifest already exists; use --force only when intentionally replacing bootstrap files")
    data = manifest(solutions, paths, excluded_paths)
    write(manifest_path, json.dumps(data, indent=2), True)
    for solution in solutions:
        docs = solution_docs(solution, paths.okf_root)
        write(repo / docs["routing_guidance_card"], card(solution, docs), force)
        write(repo / docs["solution"], solution_md(solution), force)
        write(repo / docs["routing"], routing_md(solution, docs), force)
        write(repo / docs["log"], log_md(solution), force)
    write(repo / "tools/docs/build_okf_wikis.py", BUILD_OKF_WIKIS, True)
    write(repo / "tools/docs/map_changed_paths.py", MAP_CHANGED_PATHS, True)
    write(repo / "tools/docs/check_okf_route_cards.py", CHECK_ROUTE_CARDS, True)
    write(repo / "tools/docs/build_all_wikis.ps1", BUILD_ALL_WIKIS_PS1, True)
    agents_status = patch_agents(repo, paths)
    print(f"Bootstrapped OKF route pack for {len(solutions)} solution(s).")
    print(f"OKF route-pack docs root: {paths.docs_root}")
    print(f"AGENTS.md OKF routing block {agents_status}.")
    print("Run: .\\tools\\docs\\build_all_wikis.ps1")
    print("Run: .\\tools\\docs\\build_all_wikis.ps1 -Check")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".", help="repository root to bootstrap")
    parser.add_argument("--spec", help="JSON spec with a solutions array")
    parser.add_argument("--solution", action="append", help="id|Name|Summary|path1,path2|keyword1,keyword2")
    parser.add_argument("--discover", action="store_true", help="discover product seams and bootstrap them directly")
    parser.add_argument("--discover-only", action="store_true", help="print a reviewable discovery spec without writing files")
    parser.add_argument("--force", action="store_true", help="overwrite existing generated/bootstrap files")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    if (args.discover or args.discover_only) and (args.spec or args.solution):
        parser.error("--discover/--discover-only cannot be combined with --spec or --solution")
    if args.discover and args.discover_only:
        parser.error("choose either --discover or --discover-only")
    if args.discover_only:
        print(json.dumps(discover_solution_spec(repo), indent=2))
        return 0
    solutions, excluded_paths = load_bootstrap_input(args, repo)
    bootstrap(repo, solutions, args.force, excluded_paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
