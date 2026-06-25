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


def main() -> int:
    bootstrap_module = load_bootstrap_module()
    with tempfile.TemporaryDirectory(prefix="okf-bootstrap-") as tmp:
        repo = Path(tmp)
        (repo / "src" / "web").mkdir(parents=True)
        (repo / "src" / "web" / "app.txt").write_text("demo\n", encoding="utf-8")
        (repo / "AGENTS.md").write_text("Use British English.\n", encoding="utf-8")
        spec = repo / "okf-bootstrap.json"
        spec.write_text(json.dumps({
            "solutions": [{
                "id": "web",
                "name": "Web",
                "summary": "Demo web surface.",
                "owned_paths": ["src/web/"],
                "keywords": ["route", "page"],
            }]
        }), encoding="utf-8")
        run([sys.executable, str(BOOTSTRAP), "--repo", str(repo), "--spec", str(spec)], repo)
        ps = shutil.which("powershell") or shutil.which("pwsh")
        if ps:
            run([ps, "-ExecutionPolicy", "Bypass", "-File", str(repo / "tools/docs/build_all_wikis.ps1")], repo)
            run([ps, "-ExecutionPolicy", "Bypass", "-File", str(repo / "tools/docs/build_all_wikis.ps1"), "-Check"], repo)
        else:
            run([sys.executable, str(repo / "tools/docs/build_okf_wikis.py"), "--repo", str(repo)], repo)
            run([sys.executable, str(repo / "tools/docs/build_okf_wikis.py"), "--repo", str(repo), "--check"], repo)
        mapped = run([sys.executable, str(repo / "tools/docs/map_changed_paths.py"), "--repo", str(repo), "src/web/app.txt"], repo)
        payload = json.loads(mapped.stdout)
        assert payload["matched"][0]["solution_id"] == "web"
        assert (repo / "documentation/wiki.html").exists()
        assert (repo / "docs/okf/web/routing_guidance.card").exists()
        agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
        assert agents.startswith("Use British English.")
        assert agents.count("<!-- OKF-ROUTING:START -->") == 1
        assert bootstrap_module.AGENTS_BLOCK in agents
        assert "$okf-router" in agents
        assert "$okf-archivist" in agents
        run([sys.executable, str(BOOTSTRAP), "--repo", str(repo), "--spec", str(spec), "--force"], repo)
        agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
        assert agents.count("<!-- OKF-ROUTING:START -->") == 1
        assert bootstrap_module.AGENTS_BLOCK in agents
    print("OKF bootstrap self-check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
