from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType


def _load_script(name: str) -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_debian_package_layout_and_control_file(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    build_deb = _load_script("build_deb")
    app_dir = tmp_path / "release" / "DebugTableAuto"
    app_dir.mkdir(parents=True)
    (app_dir / "DebugTableAuto").write_bytes(b"executable")
    (app_dir / "联调测试表导入模版.xls").write_bytes(b"template")
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.2.3\n", encoding="utf-8")
    package_root = tmp_path / "build" / "debian-package"
    calls: list[list[str]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(build_deb, "ROOT", tmp_path)
    monkeypatch.setattr(build_deb, "RELEASE_ROOT", tmp_path / "release")
    monkeypatch.setattr(build_deb, "APP_DIR", app_dir)
    monkeypatch.setattr(build_deb, "PACKAGE_ROOT", package_root)
    monkeypatch.setattr(build_deb, "INSTALL_ROOT", package_root / "opt/debug-table-auto")
    monkeypatch.setattr(build_deb.subprocess, "run", fake_run)

    build_deb.main()

    control = (package_root / "DEBIAN/control").read_text(encoding="utf-8")
    launcher = package_root / "usr/bin/debug-table-auto"
    assert "Version: 1.2.3" in control
    assert "Architecture: amd64" in control
    assert launcher.read_text(encoding="utf-8").startswith("#!/bin/sh")
    assert (package_root / "opt/debug-table-auto/联调测试表导入模版.xls").is_file()
    assert calls[0][:3] == ["dpkg-deb", "--build", "--root-owner-group"]
