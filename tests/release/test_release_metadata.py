from __future__ import annotations

import json
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_VERSION = "0.11.0"


def _read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _read_toml(path: str) -> dict:
    return tomllib.loads((ROOT / path).read_text(encoding="utf-8"))


def test_release_versions_are_synchronized():
    package_lock = _read_json("desktop/package-lock.json")
    cargo_lock = _read_toml("desktop/src-tauri/Cargo.lock")
    app_package = next(package for package in cargo_lock["package"] if package["name"] == "app")
    marketplace = _read_json(".claude-plugin/marketplace.json")

    versions = {
        "python": _read_toml("pyproject.toml")["project"]["version"],
        "desktop": _read_json("desktop/package.json")["version"],
        "desktop_lock": package_lock["version"],
        "desktop_lock_root": package_lock["packages"][""]["version"],
        "tauri": _read_json("desktop/src-tauri/tauri.conf.json")["version"],
        "cargo": _read_toml("desktop/src-tauri/Cargo.toml")["package"]["version"],
        "cargo_lock": app_package["version"],
        "claude_plugin": _read_json("plugins/nber-cli/.claude-plugin/plugin.json")["version"],
        "codex_plugin": _read_json("plugins/nber-cli/.codex-plugin/plugin.json")["version"],
        "marketplace": marketplace["version"],
        "marketplace_plugin": marketplace["plugins"][0]["version"],
    }

    assert versions == {name: EXPECTED_VERSION for name in versions}


def test_release_changelogs_include_current_version():
    headings = {
        "CHANGELOG.md": f"## [{EXPECTED_VERSION}] - 2026-08-15",
        "docs/en/changelog.md": f"## {EXPECTED_VERSION} - 2026-08-15",
        "docs/zh/changelog.md": f"## {EXPECTED_VERSION} - 2026-08-15",
    }

    for path, heading in headings.items():
        assert heading in (ROOT / path).read_text(encoding="utf-8")


def test_python_and_desktop_use_the_same_release_tag():
    desktop_workflow = (ROOT / ".github/workflows/desktop.yml").read_text(encoding="utf-8")
    publish_workflow = (ROOT / ".github/workflows/publish.yml").read_text(encoding="utf-8")

    assert '- "v*"' in desktop_workflow
    assert "desktop-v" not in desktop_workflow
    assert "if: startsWith(github.event.release.tag_name, 'v')" in publish_workflow


def test_desktop_signing_checks_are_opt_in():
    workflow = (ROOT / ".github/workflows/desktop.yml").read_text(encoding="utf-8")

    assert workflow.count("vars.DESKTOP_REQUIRE_SIGNING == 'true'") == 4


def test_github_release_uses_the_product_name_in_its_title():
    workflow = (ROOT / ".github/workflows/desktop.yml").read_text(encoding="utf-8")

    assert "name: NBER-CLI ${{ github.ref_name }}" in workflow


def test_sdist_excludes_local_temporary_files():
    sdist_excludes = _read_toml("pyproject.toml")["tool"]["hatch"]["build"]["targets"][
        "sdist"
    ]["exclude"]

    assert "/tmp" in sdist_excludes
