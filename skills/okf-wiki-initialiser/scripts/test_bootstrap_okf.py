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


def touch_descriptor(repo: Path, relative: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n", encoding="utf-8")


def assert_semantic_discovery(bootstrap_module) -> None:
    assert bootstrap_module.normalise_path(".agents/") == ".agents/"
    with tempfile.TemporaryDirectory(prefix="okf-discovery-products-") as tmp:
        repo = Path(tmp)
        for relative in [
            "vp/AlertingService/AlertingService.sln",
            "vp/BIService/BIService.sln",
            "vp/DIDService/DIDService.slnx",
            "vp/ServiceManager/ServiceManager.Gateway/ServiceManager.Gateway.sln",
            "vp/ServiceManager/ServiceManager.Testing/ServiceManager.Tests.slnx",
            "Web/Designer/Digitalk.Web.Designer/Digitalk.Web.Designer.sln",
            "Web/Common/Digitalk.Carrier.Data/Digitalk.Carrier.Data.csproj",
            "Web/Common/Digitalk.Carrier.Data.Tests/Digitalk.Carrier.Data.Tests.csproj",
            "vp/PolicyEngine/policy.py",
            "vendor/Libraries/readme.txt",
        ]:
            touch_descriptor(repo, relative)

        payload = bootstrap_module.discover_solution_spec(repo)
        solutions = {item["id"]: item for item in payload["solutions"]}
        assert {"alerting-service", "bi-service", "did-service", "service-manager", "designer"}.issubset(solutions)
        assert "vp/PolicyEngine/" in payload["uncovered_roots"]
        assert solutions["service-manager"]["owned_paths"] == ["vp/ServiceManager/"]
        assert solutions["service-manager"]["discovery"]["basis"] == "semantic-family"
        assert solutions["digitalk-carrier-data"]["discovery"]["basis"] == "project-fallback"
        assert not any("test" in item["id"] for item in payload["solutions"])
        assert solutions["digitalk-carrier-data"]["owned_paths"] == [
            "Web/Common/Digitalk.Carrier.Data/",
            "Web/Common/Digitalk.Carrier.Data.Tests/",
        ]
        assert "Web/Common/Digitalk.Carrier.Data.Tests/" not in payload["excluded_paths"]
        assert "vendor/" not in {item["owned_paths"][0] for item in payload["solutions"]}
        assert "vendor/" in payload["excluded_paths"]
        assert payload["review_required"] is True
        assert payload["fallback_order"] == ["semantic-family", "solution", "project", "top-level-directory"]

        result = run([sys.executable, str(BOOTSTRAP), "--repo", str(repo), "--discover-only"], repo)
        assert json.loads(result.stdout)["solutions"] == payload["solutions"]
        assert not (repo / "docs").exists()
        assert not (repo / "AGENTS.md").exists()
        direct = subprocess.run(
            [sys.executable, str(BOOTSTRAP), "--repo", str(repo), "--discover"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        assert direct.returncode != 0
        assert "requiring semantic review" in direct.stderr

    with tempfile.TemporaryDirectory(prefix="okf-discovery-direct-") as tmp:
        repo = Path(tmp)
        touch_descriptor(repo, "src/Inventory.Worker/Inventory.Worker.csproj")
        touch_descriptor(repo, "src/Payments.Api/Payments.Api.csproj")
        touch_descriptor(repo, "src/Payments.Api.Tests/Payments.Api.Tests.csproj")
        touch_descriptor(repo, ".agents/local.txt")
        run([sys.executable, str(BOOTSTRAP), "--repo", str(repo), "--discover"], repo)
        manifest = json.loads((repo / "docs/solutions.manifest.json").read_text(encoding="utf-8"))
        assert {item["id"] for item in manifest["solutions"]} == {"inventory-worker", "payments-api"}
        assert all("discovery" not in item for item in manifest["solutions"])
        payments = next(item for item in manifest["solutions"] if item["id"] == "payments-api")
        assert payments["owned_paths"] == ["src/Payments.Api/", "src/Payments.Api.Tests/"]
        assert "src/Payments.Api.Tests/" not in manifest["excluded_paths"]
        mapped = json.loads(run([
            sys.executable,
            str(repo / "tools/docs/map_changed_paths.py"),
            "--repo",
            str(repo),
            "src/Inventory.Worker/Inventory.Worker.csproj",
            "src/Payments.Api.Tests/Payments.Api.Tests.csproj",
            ".agents/local.txt",
        ], repo).stdout)
        assert {item["path"]: item["solution_id"] for item in mapped["matched"]} == {
            "src/Inventory.Worker/Inventory.Worker.csproj": "inventory-worker",
            "src/Payments.Api.Tests/Payments.Api.Tests.csproj": "payments-api",
        }
        assert mapped["excluded"] == [".agents/local.txt"]
        assert not mapped["unmapped"]
        assert not mapped["ambiguous"]
        run_build_checks(repo)


def assert_git_visibility_filter(bootstrap_module) -> None:
    with tempfile.TemporaryDirectory(prefix="okf-discovery-git-visible-") as tmp:
        repo = Path(tmp)
        run(["git", "init"], repo)
        (repo / ".gitignore").write_text("local-artifacts/\n", encoding="utf-8")
        touch_descriptor(repo, "src/Payments.Api/Payments.Api.csproj")
        touch_descriptor(repo, "local-artifacts/Ghost.Service/Ghost.Service.csproj")
        touch_descriptor(repo, ".devcontainer/devcontainer.json")

        visible_files = bootstrap_module.git_visible_files(repo)
        assert visible_files is not None
        assert not any("local-artifacts" in path.parts for path in visible_files)

        payload = bootstrap_module.discover_solution_spec(repo)
        assert {item["id"] for item in payload["solutions"]} == {"payments-api"}
        assert payload["uncovered_roots"] == []
        assert "local-artifacts/" not in payload["excluded_paths"]
        assert ".devcontainer/" in payload["excluded_paths"]


def main() -> int:
    bootstrap_module = load_bootstrap_module()
    assert_semantic_discovery(bootstrap_module)
    assert_git_visibility_filter(bootstrap_module)
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
