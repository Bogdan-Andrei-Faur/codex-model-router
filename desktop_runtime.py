"""Discover Desktop at process startup; never patch the installed application.

Windows Store resources cannot be executed directly. Stage a version-specific
copy with its companion executables, rather than guessing a hashed Codex path.
No network access, credentials, model requests or user configuration writes.
"""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass


class DiscoveryError(ValueError):
    pass


@dataclass(frozen=True)
class Installation:
    desktop: Path
    backend: Path
    version: str
    source: str
    package_family: str = ""


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def windows_packages():
    # Constant code, no interpolation of configuration or filesystem paths.
    command = "[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); " \
        "@(Get-AppxPackage | Where-Object { $_.Name -in @('OpenAI.Codex','OpenAI.ChatGPT') } | " \
        "Select-Object Name,Version,InstallLocation,PackageFamilyName) | ConvertTo-Json -Compress"
    shell = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    try:
        result = subprocess.run([str(shell), "-NoProfile", "-NonInteractive", "-Command", command],
                                capture_output=True, encoding="utf-8-sig", timeout=20,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=True)
        data = json.loads(result.stdout or "[]")
        return data if isinstance(data, list) else [data]
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise DiscoveryError("No se pudo consultar la instalación registrada de Desktop.") from error


def stage_windows_runtime(resources, cache):
    required = ("codex.exe", "codex-code-mode-host.exe", "codex-windows-sandbox-setup.exe", "codex-command-runner.exe")
    optional = ("rg.exe", "codex-windows-sandbox-service.exe")
    if not all((resources / name).is_file() for name in required):
        raise DiscoveryError("La instalación de Desktop está incompleta: faltan componentes del motor.")
    names = list(required) + [name for name in optional if (resources / name).is_file()]
    stamp = {name: [(resources / name).stat().st_size, (resources / name).stat().st_mtime_ns] for name in names}
    key = hashlib.sha256(json.dumps([str(resources.resolve()), stamp], sort_keys=True).encode()).hexdigest()[:24]
    destination = cache / key

    def valid():
        try:
            manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
            return manifest["source"] == str(resources.resolve()) and manifest["stamp"] == stamp and all(
                (destination / name).is_file() and (destination / name).stat().st_size == stamp[name][0]
                and digest(destination / name) == manifest["sha256"][name] for name in names)
        except (OSError, ValueError, KeyError, TypeError):
            return False

    if valid():
        return destination / "codex.exe"
    # Repair beside an invalid cache; never overwrite a file used by a live
    # process. Only source/stamp/hash-verified repairs of THIS build qualify.
    if destination.exists():
        for repair in sorted(cache.glob(key + "-repair-*")):
            destination = repair
            if valid():
                return destination / "codex.exe"
        destination = cache / (key + "-repair-" + uuid.uuid4().hex[:12])
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".prepare-", dir=cache) as temporary:
        staged = Path(temporary) / "runtime"
        staged.mkdir()
        hashes = {}
        for name in names:
            shutil.copy2(resources / name, staged / name)
            hashes[name] = digest(staged / name)
            if hashes[name] != digest(resources / name):
                raise DiscoveryError("Desktop cambió mientras se preparaba el motor. Vuelve a intentarlo.")
        current = {name: [(resources / name).stat().st_size, (resources / name).stat().st_mtime_ns] for name in names}
        if current != stamp:
            raise DiscoveryError("Desktop se está actualizando. Vuelve a intentarlo cuando termine.")
        (staged / "manifest.json").write_text(json.dumps({"source": str(resources.resolve()), "stamp": stamp,
                                                        "sha256": hashes}, indent=2), encoding="utf-8")
        try:
            staged.rename(destination)
        except OSError:
            # Another bridge may have prepared the same version concurrently.
            if not valid():
                raise
    return destination / "codex.exe"


def discover_windows(packages=None, cache=None):
    packages = windows_packages() if packages is None else packages
    usable = []
    for package in packages:
        try:
            if package["Name"] not in ("OpenAI.Codex", "OpenAI.ChatGPT"):
                continue
            app = Path(package["InstallLocation"]) / "app"
            desktop = next((app / name for name in ("ChatGPT.exe", "Codex.exe") if (app / name).is_file()), None)
            version = tuple(int(part) for part in package["Version"].split("."))
            usable.append((version, package, desktop))
        except (ValueError, KeyError, TypeError):
            continue
    if not usable:
        raise DiscoveryError("No se encuentra una instalación registrada de Desktop con Codex.")
    _, package, desktop = max(usable, key=lambda item: item[0])
    if desktop is None:
        raise DiscoveryError("La instalación más reciente de Desktop está incompleta. Espera a que termine la actualización.")
    cache = Path(cache) if cache else Path(os.environ["LOCALAPPDATA"]) / "CodexModelRouter/runtime"
    backend = stage_windows_runtime(desktop.parent / "resources", cache)
    return Installation(desktop, backend, package["Version"], "windows-package", package.get("PackageFamilyName", ""))


def discover_macos(explicit=None, roots=None):
    candidates = [Path(explicit).expanduser()] if explicit else [
        root / name for root in (roots or (Path("/Applications"), Path.home() / "Applications"))
        for name in ("ChatGPT.app", "Codex.app")]
    for app in candidates:
        try:
            contents = app.resolve() / "Contents"
            with (contents / "Info.plist").open("rb") as stream:
                info = plistlib.load(stream)
            executable = info["CFBundleExecutable"]
            if Path(executable).name != executable:
                continue
            desktop = contents / "MacOS" / executable
            resources = contents / "Resources"
            # New Desktop bundles package the CLI with its own launcher. Keep
            # that entry point so companion binaries resolve inside its bundle.
            # An incomplete packaged CLI must not fall back to a stale engine.
            packaged = resources / "codex-cli"
            backend = packaged / "bin/codex" if packaged.exists() else resources / "codex"
            if all(path.is_file() and os.access(path, os.X_OK) for path in (desktop, backend)):
                return Installation(desktop, backend, str(info.get("CFBundleShortVersionString", "unknown")), "macos-bundle")
        except (OSError, ValueError, KeyError, plistlib.InvalidFileException):
            continue
    raise DiscoveryError("No se encuentra Desktop con Codex. Indica la ubicación de la app en Ajustes o ejecuta setup --app.")


def discover(config=None):
    config = config or {}
    if sys.platform == "win32":
        return discover_windows()
    if sys.platform == "darwin":
        return discover_macos(config.get("desktop_app"))
    raise DiscoveryError("La integración con Desktop requiere Windows o macOS.")
