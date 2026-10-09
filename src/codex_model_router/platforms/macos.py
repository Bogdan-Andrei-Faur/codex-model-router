"""macOS setup and launcher. Never edits the installed app or global Codex settings."""
import argparse
import json
import os
from pathlib import Path
from codex_model_router.paths import resource_root
import plistlib
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile

from codex_model_router.platforms.platform_support import backend_path
from codex_model_router.routing.routing import DEFAULT_ROUTES
from codex_model_router.platforms.desktop_runtime import discover_macos

ROOT = resource_root()
CONFIG = ROOT / "config.local.json"
DIST = ROOT / "dist"
MONITOR = DIST / "Monitor de Codex.app" / "Contents" / "MacOS" / "codex-monitor-mac"


def discover_app(explicit=None):
    found = discover_macos(explicit)
    return found.desktop.parent.parent.parent, found.desktop, found.backend


def save_config(config):
    # Replacing a file never exposes a partially written configuration to a turn.
    fd, name = tempfile.mkstemp(prefix=".router-config-", dir=ROOT)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(config, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(name, CONFIG)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def wrapper(path, command):
    path.write_text("#!/bin/sh\nexec " + " ".join(shlex.quote(str(x)) for x in command) + ' "$@"\n', encoding="utf-8")
    path.chmod(0o755)


def setup(app_path=None):
    app, desktop, binary = discover_app(app_path)
    version = (ROOT / "VERSION").read_text().strip()
    if CONFIG.exists():
        config = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
        # A copied Windows config may enable external classification. Do not
        # silently activate it when bootstrapping this machine.
        if config.get("platform") != "darwin":
            raise ValueError("Ya existe config.local.json de otra instalación. Consérvalo con otro nombre antes de preparar Mac.")
        for key, default in (("inference_telemetry", True), ("prompt_logging", True),
                             ("phase_routing", True), ("history_days", 0)):
            config.setdefault(key, default)
        config.update(python=sys.executable, codex=str(binary), desktop=str(desktop))
    else:
        config = {"platform": "darwin", "enabled": True, "sync_picker": True,
                  "history_days": 0, "inference_telemetry": True, "prompt_logging": True,
                  "phase_routing": True, "routing_engine": "rules", "comparison_engines": [],
                  "python": sys.executable, "codex": str(binary), "desktop": str(desktop),
                  "routes": DEFAULT_ROUTES}
    config["installation_mode"] = "auto"
    if app_path:
        config["desktop_app"] = str(app)
    DIST.mkdir(exist_ok=True)
    MONITOR.parent.mkdir(parents=True, exist_ok=True)
    # Compile before replacing any working configuration or launcher.
    staged_monitor = MONITOR.with_suffix(".new")
    subprocess.run(["/usr/bin/xcrun", "swiftc", str(ROOT / "native/macos/MonitorMac.swift"),
                    "-o", str(staged_monitor), "-framework", "AppKit", "-framework", "WebKit", "-framework", "Security",
                    "-target", platform.machine() + "-apple-macosx12.0"], check=True)
    ui = MONITOR.parent.parent / "Resources" / "ui"
    shutil.copytree(ROOT / "monitor-ui", ui, dirs_exist_ok=True)
    shutil.copyfile(ROOT / "assets" / "brand" / "router-1024.png", ui / "codex.png")
    shutil.copyfile(ROOT / "assets/brand/router.icns", ui.parent / "router.icns")
    os.replace(staged_monitor, MONITOR)
    with (MONITOR.parent.parent / "Info.plist").open("wb") as stream:
        from codex_model_router.build_identity import identity, router_identity
        plistlib.dump({"CFBundleExecutable": MONITOR.name, "CFBundleIdentifier": "local.codex-model-router.monitor",
                      "CFBundleName": "Monitor de Codex", "CFBundlePackageType": "APPL",
                      "CFBundleIconFile": "router.icns",
                      "CFBundleVersion": version,
                      "CFBundleShortVersionString": version,
                      "RouterBuildId": identity(ROOT)[1],
                      "RouterEngineBuildId": router_identity(ROOT),
                      "RouterCodeRoot": str(ROOT),
                      "LSMinimumSystemVersion": "12.0", "LSUIElement": True}, stream)
    save_config(config)
    wrapper(DIST / "codex-router", [sys.executable, ROOT / "router.py"])
    # The config path is fixed even when Desktop launches from another cwd.
    bridge = DIST / "codex-router"
    bridge.write_text("#!/bin/sh\nexport PERSONAL_CODEX_ROUTER_CONFIG=" + shlex.quote(str(CONFIG)) +
                      "\nexport PYTHONUTF8=1\nexec " + shlex.quote(sys.executable) + " " +
                      shlex.quote(str(ROOT / "router.py")) + ' "$@"\n', encoding="utf-8")
    bundle = DIST / "Codex automático.app"
    contents = bundle / "Contents"
    (contents / "MacOS").mkdir(parents=True, exist_ok=True)
    (contents / "Resources").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "assets/brand/router.icns", contents / "Resources/router.icns")
    with (contents / "Info.plist").open("wb") as stream:
        plistlib.dump({"CFBundleExecutable": "launcher", "CFBundleIdentifier": "local.codex-model-router.launcher",
                      "CFBundleName": "Codex automático", "CFBundlePackageType": "APPL",
                      "CFBundleIconFile": "router.icns",
                      "CFBundleVersion": version, "CFBundleShortVersionString": version,
                      "LSUIElement": True}, stream)
    wrapper(contents / "MacOS/launcher", [sys.executable, ROOT / "macos.py", "open"])
    print("Preparado: " + str(bundle))
    print("Motor: " + str(binary))


def app_running(desktop):
    result = subprocess.run(["/bin/ps", "-axo", "comm="], capture_output=True, text=True, check=True)
    return str(desktop) in (line.strip() for line in result.stdout.splitlines())


def open_app():
    from codex_model_router.platforms.desktop import open_app as open_desktop
    return open_desktop()


def open_monitor():
    subprocess.Popen([str(MONITOR), str(ROOT)],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("setup", "doctor", "open", "monitor", "pause", "resume"))
    parser.add_argument("--app", help="Ruta a la app instalada; solo para setup/doctor")
    args = parser.parse_args()
    try:
        if sys.platform != "darwin":
            raise ValueError("Este lanzador requiere macOS. En Windows usa build.ps1.")
        if args.action == "setup":
            setup(args.app)
        elif args.action == "doctor":
            app, desktop, binary = discover_app(args.app)
            print("App compatible: " + str(app))
            print("Motor ejecutable: " + str(binary))
            print("App abierta: " + ("sí" if app_running(desktop) else "no"))
            print("La activación del enrutamiento se confirma observando un envío aceptado en el monitor.")
            print("Configuración local: " + ("presente" if CONFIG.exists() else "pendiente de setup"))
        elif args.action == "open":
            open_app()
        elif args.action == "monitor":
            open_monitor()
        else:
            config = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
            config["enabled"] = args.action == "resume"
            save_config(config)
            print("Selector " + ("activado" if config["enabled"] else "pausado") + " para los siguientes mensajes.")
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        # Avoid leaking configuration values or command lines on launch failure.
        message = str(error) if type(error) is ValueError else "No se ha podido preparar o abrir el selector. Revisa la configuración local."
        print(message, file=sys.stderr)
        if args.action == "open":
            subprocess.run(["/usr/bin/osascript", "-e",
                            'on run argv\ndisplay alert "Codex automático" message (item 1 of argv)\nend run', message],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
