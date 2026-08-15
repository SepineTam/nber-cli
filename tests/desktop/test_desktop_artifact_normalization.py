from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _load_artifact_normalizer():
    script = ROOT / "scripts" / "normalize-desktop-artifacts.py"
    spec = importlib.util.spec_from_file_location("normalize_desktop_artifacts", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_base_name_uses_tauri_version():
    normalizer = _load_artifact_normalizer()

    assert (
        normalizer.build_base_name("windows", "x86_64-pc-windows-msvc")
        == "NBER-CLI-Desktop-v0-11-0-Windows-x64"
    )
    assert (
        normalizer.build_base_name("linux", "x86_64-unknown-linux-gnu")
        == "NBER-CLI-Desktop-v0-11-0-Linux-x64"
    )


def test_rename_windows_artifact(tmp_path, monkeypatch):
    normalizer = _load_artifact_normalizer()
    monkeypatch.setattr(normalizer, "TARGET_DIR", tmp_path)
    bundle_dir = tmp_path / "x86_64-pc-windows-msvc" / "release" / "bundle" / "nsis"
    bundle_dir.mkdir(parents=True)
    installer = bundle_dir / "NBER-CLI Desktop_0.8.1_x64-setup.exe"
    installer.write_bytes(b"installer")

    renamed = normalizer.rename_windows_artifacts("NBER-CLI-Desktop-v0-8-1-Windows-x64")

    assert renamed == [bundle_dir / "NBER-CLI-Desktop-v0-8-1-Windows-x64.exe"]
    assert renamed[0].read_bytes() == b"installer"
    assert not installer.exists()


def test_rename_macos_artifact(tmp_path, monkeypatch):
    normalizer = _load_artifact_normalizer()
    monkeypatch.setattr(normalizer, "TARGET_DIR", tmp_path)
    bundle_dir = tmp_path / "aarch64-apple-darwin" / "release" / "bundle" / "dmg"
    bundle_dir.mkdir(parents=True)
    installer = bundle_dir / "NBER-CLI Desktop_0.8.1_aarch64.dmg"
    installer.write_bytes(b"installer")

    renamed = normalizer.rename_macos_artifacts("NBER-CLI-Desktop-v0-8-1-macOS-arm64")

    assert renamed == [bundle_dir / "NBER-CLI-Desktop-v0-8-1-macOS-arm64.dmg"]
    assert renamed[0].read_bytes() == b"installer"
    assert not installer.exists()


def test_rename_linux_appimage_artifact(tmp_path, monkeypatch):
    normalizer = _load_artifact_normalizer()
    monkeypatch.setattr(normalizer, "TARGET_DIR", tmp_path)
    bundle_dir = tmp_path / "x86_64-unknown-linux-gnu" / "release" / "bundle" / "appimage"
    bundle_dir.mkdir(parents=True)
    installer = bundle_dir / "NBER-CLI-Desktop_0.8.1_amd64.AppImage"
    installer.write_bytes(b"installer")

    renamed = normalizer.rename_linux_artifacts("NBER-CLI-Desktop-v0-8-1-Linux-x64")

    assert renamed == [bundle_dir / "NBER-CLI-Desktop-v0-8-1-Linux-x64.AppImage"]
    assert renamed[0].read_bytes() == b"installer"
    assert not installer.exists()


def test_rename_linux_deb_artifact(tmp_path, monkeypatch):
    normalizer = _load_artifact_normalizer()
    monkeypatch.setattr(normalizer, "TARGET_DIR", tmp_path)
    bundle_dir = tmp_path / "x86_64-unknown-linux-gnu" / "release" / "bundle" / "deb"
    bundle_dir.mkdir(parents=True)
    installer = bundle_dir / "nber-cli-desktop_0.8.1_amd64.deb"
    installer.write_bytes(b"installer")

    renamed = normalizer.rename_linux_artifacts("NBER-CLI-Desktop-v0-8-1-Linux-x64")

    assert renamed == [bundle_dir / "NBER-CLI-Desktop-v0-8-1-Linux-x64.deb"]
    assert renamed[0].read_bytes() == b"installer"
    assert not installer.exists()
