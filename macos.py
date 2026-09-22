"""macOS setup and launcher. Never edits the installed app or global Codex settings."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile

from platform_support import backend_path
from routing import DEFAULT_ROUTES

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config.local.json"
DIST = ROOT / "dist"
MONITOR = DIST / "Monitor de Codex.app" / "Contents" / "MacOS" / "codex-monitor-mac"


def discover_app(explicit=None):
    candidates = [Path(explicit).expanduser()] if explicit else [
        base / name for base in (Path("/Applications"), Path.home() / "Applications")
        for name in ("Codex.app", "ChatGPT.app")]
    for app in candidates:
        try:
            with (app / "Contents/Info.plist").open("rb") as stream:
                info = plistlib.load(stream)
            desktop = app / "Contents/MacOS" / info["CFBundleExecutable"]
            binary = backend_path({"codex": str(app / "Contents/Resources/codex")})
            if desktop.is_file() and os.access(desktop, os.X_OK):
                return app.resolve(), desktop.resolve(), binary
        except (OSError, KeyError, ValueError):
            continue
    raise ValueError("No se encuentra Codex. Indica --app /ruta/Codex.app o /ruta/ChatGPT.app.")


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
    if CONFIG.exists():
        config = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
        # A copied Windows config may enable external classification. Do not
        # silently activate it when bootstrapping this machine.
        if config.get("platform") != "darwin":
            raise ValueError("Ya existe config.local.json de otra instalación. Consérvalo con otro nombre antes de preparar Mac.")
        config.update(python=sys.executable, codex=str(binary), desktop=str(desktop))
    else:
        config = {"platform": "darwin", "enabled": True, "sync_picker": True,
                  "history_days": 90, "routing_engine": "rules", "comparison_engines": [],
                  "python": sys.executable, "codex": str(binary), "desktop": str(desktop),
                  "routes": DEFAULT_ROUTES}
    DIST.mkdir(exist_ok=True)
    MONITOR.parent.mkdir(parents=True, exist_ok=True)
    # Compile before replacing any working configuration or launcher.
    staged_monitor = MONITOR.with_suffix(".new")
    subprocess.run(["/usr/bin/xcrun", "swiftc", str(ROOT / "MonitorMac.swift"),
                    "-o", str(staged_monitor), "-framework", "AppKit", "-framework", "WebKit", "-framework", "Security",
                    "-target", platform.machine() + "-apple-macosx12.0"], check=True)
    ui = MONITOR.parent.parent / "Resources" / "ui"
    shutil.copytree(ROOT / "monitor-ui", ui, dirs_exist_ok=True)
    shutil.copyfile(ROOT / "assets" / "codex-ui-1024.png", ui / "codex.png")
    os.replace(staged_monitor, MONITOR)
    with (MONITOR.parent.parent / "Info.plist").open("wb") as stream:
        plistlib.dump({"CFBundleExecutable": MONITOR.name, "CFBundleIdentifier": "local.codex-model-router.monitor",
                      "CFBundleName": "Monitor de Codex", "CFBundlePackageType": "APPL",
                      "CFBundleVersion": "2", "LSMinimumSystemVersion": "12.0", "LSUIElement": True}, stream)
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
    with (contents / "Info.plist").open("wb") as stream:
        plistlib.dump({"CFBundleExecutable": "launcher", "CFBundleIdentifier": "local.codex-model-router.launcher",
                      "CFBundleName": "Codex automático", "CFBundlePackageType": "APPL",
                      "CFBundleVersion": "1", "LSUIElement": True}, stream)
    wrapper(contents / "MacOS/launcher", [sys.executable, ROOT / "macos.py", "open"])
    print("Preparado: " + str(bundle))
    print("Motor: " + str(binary))


def app_running(desktop):
    result = subprocess.run(["/bin/ps", "-axo", "comm="], capture_output=True, text=True, check=True)
    return str(desktop) in (line.strip() for line in result.stdout.splitlines())


def open_app():
    config = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    backend_path(config)
    desktop = Path(config["desktop"])
    if app_running(desktop):
        raise ValueError("Codex sigue abierto. Termina tus tareas, cierra la app por completo y abre Codex automático.")
    bridge = DIST / "codex-router"
    if not bridge.is_file():
        raise ValueError("Ejecuta primero macos.py setup.")
    env = dict(os.environ, CODEX_CLI_PATH=str(bridge), PERSONAL_CODEX_ROUTER_CONFIG=str(CONFIG), PYTHONUTF8="1")
    subprocess.Popen([str(desktop)], env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    open_monitor()


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
