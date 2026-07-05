#!/usr/bin/env python3
"""Tiny self-check for the OKF bootstrapper."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


sys.dont_write_bytecode = True


HERE = Path(__file__).resolve().parent
BOOTSTRAP = HERE / "bootstrap_okf.py"


def load_bootstrap_module():
    spec = importlib.util.spec_from_file_location("bootstrap_okf", BOOTSTRAP)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)


def write_spec(repo: Path) -> Path:
    spec = repo / "okf-bootstrap.json"
    spec.write_text(json.dumps({
        "solutions": [
            {
                "id": "web",
                "name": "Web",
                "summary": "Demo web surface.",
                "owned_paths": ["src/web/"],
                "keywords": ["route", "page"],
            },
            {
                "id": "api",
                "name": "API",
                "summary": "Demo API surface.",
                "owned_paths": ["src/api/"],
                "keywords": ["endpoint", "payload"],
            },
        ]
    }), encoding="utf-8")
    return spec


def run_build_checks(repo: Path) -> None:
    ps = shutil.which("powershell") or shutil.which("pwsh")
    if ps:
        run([ps, "-ExecutionPolicy", "Bypass", "-File", str(repo / "tools/docs/build_all_wikis.ps1")], repo)
        run([ps, "-ExecutionPolicy", "Bypass", "-File", str(repo / "tools/docs/build_all_wikis.ps1"), "-Check"], repo)
        run([ps, "-ExecutionPolicy", "Bypass", "-File", str(repo / "tools/docs/build_all_wikis.ps1"), "-Check", "-BrowserSmoke"], repo)
    else:
        run([sys.executable, str(repo / "tools/docs/build_okf_wikis.py"), "--repo", str(repo)], repo)
        run([sys.executable, str(repo / "tools/docs/build_okf_wikis.py"), "--repo", str(repo), "--check"], repo)
        run([sys.executable, str(repo / "tools/docs/build_okf_wikis.py"), "--repo", str(repo), "--check", "--browser-smoke"], repo)


def create_demo_sources(repo: Path) -> None:
    (repo / "src" / "web").mkdir(parents=True)
    (repo / "src" / "web" / "app.txt").write_text("demo\n", encoding="utf-8")
    (repo / "src" / "api").mkdir(parents=True)
    (repo / "src" / "api" / "api.txt").write_text("demo\n", encoding="utf-8")


def add_link_fixture(repo: Path, root: str) -> None:
    solution = repo / root / "okf" / "web" / "solution.md"
    solution.write_text(
        solution.read_text(encoding="utf-8")
        + "\n## Link Smoke\n\n"
        + "- [Routing details](routing.md)\n"
        + "- [API bundle](../api/solution.md)\n",
        encoding="utf-8",
        newline="\n",
    )


def assert_rich_wiki_links(repo: Path, root: str) -> None:
    web_html = (repo / root / "okf" / "web" / "wiki.html").read_text(encoding="utf-8")
    umbrella_html = (repo / root / "wiki.html").read_text(encoding="utf-8")
    assert "single-file OKF reader" in web_html
    assert "#doc/routing.md" in web_html
    assert "../api/wiki.html#doc/solution.md" in web_html
    assert "[Routing details](routing.md)" not in web_html
    assert "#doc/solutions/web/routing.md" in umbrella_html
    assert "#doc/solutions/api/solution.md" in umbrella_html


def assert_manifest_root(repo: Path, root: str) -> None:
    manifest = json.loads((repo / root / "solutions.manifest.json").read_text(encoding="utf-8"))
    assert manifest["wiki"]["root"] == f"{root}/okf"
    assert manifest["wiki"]["index"] == f"{root}/okf/index.md"
    assert manifest["wiki"]["umbrella"] == f"{root}/wiki.html"
    assert manifest["routing"]["card_check"] == "tools/docs/check_okf_route_cards.py"
    assert manifest["solutions"][0]["docs"]["routing_guidance_card"] == f"{root}/okf/web/routing_guidance.card"


def assert_route_card_contract(repo: Path, root: str) -> None:
    card = (repo / root / "okf" / "web" / "routing_guidance.card").read_text(encoding="utf-8")
    assert "validation:\n- python tools/docs/map_changed_paths.py <representative-owned-path>" in card
    assert "stale_notes:\n- Review after ownership, entrypoint, handoff, or validation changes." in card
    run([sys.executable, str(repo / "tools/docs/check_okf_route_cards.py"), "--repo", str(repo)], repo)


def assert_route_card_checker_rejects_bad_card(repo: Path, root: str) -> None:
    card = repo / root / "okf" / "web" / "routing_guidance.card"
    original = card.read_text(encoding="utf-8")
    bad = original.replace(
        "validation:\n"
        "- python tools/docs/map_changed_paths.py <representative-owned-path>\n"
        "- .\\tools\\docs\\build_all_wikis.ps1 -Check\n",
        "",
        1,
    )
    card.write_text(bad, encoding="utf-8", newline="\n")
    result = subprocess.run(
        [sys.executable, str(repo / "tools/docs/check_okf_route_cards.py"), "--repo", str(repo)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "validation" in result.stdout
    card.write_text(original, encoding="utf-8", newline="\n")


def assert_missing_keywords_fail_fast() -> None:
    with tempfile.TemporaryDirectory(prefix="okf-bootstrap-keywords-") as tmp:
        repo = Path(tmp)
        result = subprocess.run(
            [
                sys.executable,
                str(BOOTSTRAP),
                "--repo",
                str(repo),
                "--solution",
                "bad|Bad|Bad surface.|src/bad/|",
            ],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode != 0
        assert "needs at least one keyword" in result.stderr


def main() -> int:
    bootstrap_module = load_bootstrap_module()
    with tempfile.TemporaryDirectory(prefix="okf-bootstrap-") as tmp:
        repo = Path(tmp)
        create_demo_sources(repo)
        (repo / "AGENTS.md").write_text("Use British English.\n", encoding="utf-8")
        spec = write_spec(repo)
        run([sys.executable, str(BOOTSTRAP), "--repo", str(repo), "--spec", str(spec)], repo)
        add_link_fixture(repo, "docs")
        run_build_checks(repo)
        assert_rich_wiki_links(repo, "docs")
        mapped = run([sys.executable, str(repo / "tools/docs/map_changed_paths.py"), "--repo", str(repo), "src/web/app.txt"], repo)
        payload = json.loads(mapped.stdout)
        assert payload["matched"][0]["solution_id"] == "web"
        assert (repo / "docs/solutions.manifest.json").exists()
        assert (repo / "docs/wiki.html").exists()
        assert (repo / "docs/okf/web/routing_guidance.card").exists()
        assert not (repo / "documentation").exists()
        assert_manifest_root(repo, "docs")
        assert_route_card_contract(repo, "docs")
        assert_route_card_checker_rejects_bad_card(repo, "docs")
        agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
        assert agents.startswith("Use British English.")
        assert agents.count("<!-- OKF-ROUTING:START -->") == 1
        assert bootstrap_module.agents_block(bootstrap_module.choose_okf_paths(repo)) in agents
        assert "$okf-router" in agents
        assert "$okf-archivist" in agents
        assert "OKF routing is evidence for the next workflow step only." in agents
        assert "does not declare requirements stable" in agents
        run([sys.executable, str(BOOTSTRAP), "--repo", str(repo), "--spec", str(spec), "--force"], repo)
        agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
        assert agents.count("<!-- OKF-ROUTING:START -->") == 1
        assert bootstrap_module.agents_block(bootstrap_module.choose_okf_paths(repo)) in agents
    with tempfile.TemporaryDirectory(prefix="okf-bootstrap-existing-docs-") as tmp:
        repo = Path(tmp)
        (repo / "documentation").mkdir()
        create_demo_sources(repo)
        spec = write_spec(repo)
        run([sys.executable, str(BOOTSTRAP), "--repo", str(repo), "--spec", str(spec)], repo)
        add_link_fixture(repo, "documentation")
        run_build_checks(repo)
        assert_rich_wiki_links(repo, "documentation")
        assert (repo / "documentation/solutions.manifest.json").exists()
        assert (repo / "documentation/wiki.html").exists()
        assert (repo / "documentation/okf/web/routing_guidance.card").exists()
        assert not (repo / "docs").exists()
        assert_manifest_root(repo, "documentation")
        assert_route_card_contract(repo, "documentation")
    with tempfile.TemporaryDirectory(prefix="okf-bootstrap-root-precedence-") as tmp:
        repo = Path(tmp)
        (repo / "manual").mkdir()
        (repo / "wiki").mkdir()
        create_demo_sources(repo)
        spec = write_spec(repo)
        run([sys.executable, str(BOOTSTRAP), "--repo", str(repo), "--spec", str(spec)], repo)
        assert (repo / "wiki/solutions.manifest.json").exists()
        assert not (repo / "manual/solutions.manifest.json").exists()
        assert_manifest_root(repo, "wiki")
    assert_missing_keywords_fail_fast()
    print("OKF bootstrap self-check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
