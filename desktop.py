"""Install, diagnose and remove the per-user Desktop connection.

The CODEX_CLI_PATH seam is observed in Desktop, not a public compatibility API.
Registration never means an already-running Desktop is connected. No process is
terminated and neither application binaries nor Codex settings are modified.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import plistlib
import queue
import subprocess
import sys
import tempfile
import threading
import time

from desktop_runtime import discover, DiscoveryError
from application_layout import code_root, data_root, manifest, installed_path, runtime_command

CODE_ROOT = code_root()
ROOT = data_root(CODE_ROOT)
CONFIG = ROOT / "config.local.json"
STATE = ROOT / "state"
VARIABLE = "CODEX_CLI_PATH"
LABEL = "local.codex-model-router.connection"


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def config():
    value = json.loads(CONFIG.read_text(encoding="utf-8-sig"))
    if sys.platform == "darwin" and value.get("platform") != "darwin":
        raise DiscoveryError("Esta configuración pertenece a otra instalación. Prepara este Mac con macos.py setup.")
    if sys.platform == "win32" and value.get("platform") in ("darwin", "linux"):
        raise DiscoveryError("Esta configuración pertenece a otro sistema. Usa la configuración local de Windows.")
    if sys.platform == "linux" and value.get("platform") != "linux":
        raise DiscoveryError("Esta configuración pertenece a otro sistema. Ejecuta linux.py setup.")
    changed = False
    for key, default in (("inference_telemetry", True), ("prompt_logging", True),
                         ("phase_routing", True), ("history_days", 0)):
        if key not in value:
            value[key] = default
            changed = True
    if changed:
        atomic_json(CONFIG, value)
    return value


def wrapper_path():
    if manifest(CODE_ROOT):
        return installed_path(CODE_ROOT, 'bridge')
    return ROOT / "dist" / ("codex-router.exe" if sys.platform == "win32" else "codex-router")


def registration_path():
    return STATE / "desktop-integration.json"


def read_registration():
    try:
        return json.loads(registration_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def read_environment():
    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                value, kind = winreg.QueryValueEx(key, VARIABLE)
                if kind not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
                    raise DiscoveryError("El ajuste de conexión existente tiene un formato no compatible.")
                return {"value": value, "kind": kind}
        except FileNotFoundError:
            return {"value": None, "kind": winreg.REG_SZ}
    result = subprocess.run(["/bin/launchctl", "getenv", VARIABLE], capture_output=True, text=True, timeout=5)
    if result.returncode not in (0, 1):
        raise DiscoveryError("No se pudo consultar el entorno de la sesión de macOS.")
    return {"value": result.stdout.rstrip("\n") or None, "kind": 1}


def write_environment(value, kind=1):
    if sys.platform == "win32":
        import winreg
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            if value is None:
                try:
                    winreg.DeleteValue(key, VARIABLE)
                except FileNotFoundError:
                    pass
            else:
                winreg.SetValueEx(key, VARIABLE, 0, kind, value)
        # Explorer refreshes the environment used by future normal shortcuts.
        result = ctypes.c_size_t()
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 2, 3000, ctypes.byref(result))
    else:
        command = ["/bin/launchctl", "unsetenv", VARIABLE] if value is None else ["/bin/launchctl", "setenv", VARIABLE, value]
        subprocess.run(command, check=True, capture_output=True, timeout=5)


def agent_path():
    return Path.home() / "Library/LaunchAgents" / (LABEL + ".plist")


def launch_agent_definition():
    command = (runtime_command('desktop', CODE_ROOT, ROOT) if manifest(CODE_ROOT)
               else [sys.executable, str(ROOT / 'desktop.py')])
    return {"Label": LABEL, "ProgramArguments": command + ["restore-session"],
            "RunAtLoad": True, "ProcessType": "Background"}


def ensure_login_agent():
    path = agent_path()
    desired = launch_agent_definition()
    if path.exists():
        if plistlib.loads(path.read_bytes()) != desired:
            raise DiscoveryError("Ya existe otra conexión de Codex automático para esta sesión de macOS.")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "wb") as stream:
        plistlib.dump(desired, stream)
    # RunAtLoad restores the connection on the next login. Apply this session
    # directly below: no launchctl bootstrap race and no background polling.


def probe_bridge(wrapper):
    """Read-only protocol check of the exact wrapper; never create a task/turn."""
    process = subprocess.Popen([str(wrapper), "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    messages = queue.Queue()
    def read():
        try:
            for line in process.stdout:
                messages.put(json.loads(line))
        except (OSError, ValueError):
            pass
        finally:
            messages.put(None)
    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    def send(value):
        process.stdin.write((json.dumps(value) + "\n").encode())
        process.stdin.flush()
    def call(identifier, method, params):
        send({"id": identifier, "method": method, "params": params})
        deadline = time.monotonic() + 30
        while True:
            message = messages.get(timeout=max(.01, deadline - time.monotonic()))
            if message is None:
                raise DiscoveryError("El puente se cerró antes de completar la prueba de conexión.")
            if message.get("id") == identifier and "method" not in message:
                if "error" in message:
                    raise DiscoveryError("Esta versión de Desktop no supera la prueba de compatibilidad del puente.")
                return message.get("result") or {}
            if time.monotonic() >= deadline:
                raise queue.Empty()
    try:
        call(1, "initialize", {"clientInfo": {"name": "router_connection_check", "version": "1.0"}})
        send({"method": "initialized", "params": {}})
        result = call(2, "model/list", {})
        if not isinstance(result.get("data"), list) or not result["data"]:
            raise DiscoveryError("Codex no devolvió un catálogo de modelos válido.")
        return {"handshake": True, "catalog": True}
    except (queue.Empty, BrokenPipeError) as error:
        raise DiscoveryError("El puente no respondió a tiempo; no se ha activado la conexión habitual.") from error
    finally:
        try:
            process.stdin.close()
            process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            process.terminate()
            try:
                process.wait(timeout=12)  # POSIX bridge reaps its native process group.
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)
        reader.join(timeout=1)
        process.stdout.close()


def install():
    cfg = config()
    installation = discover(cfg)  # Discovery and staging before registration.
    if sys.platform == "linux":
        from linux_desktop import install as install_linux
        return install_linux(ROOT, cfg, installation, probe_bridge)
    wrapper = wrapper_path().resolve(strict=True)
    desired = str(wrapper)
    previous = read_environment()
    record = read_registration()
    if record and (record.get("wrapper") != desired or record.get("platform") != sys.platform):
        raise DiscoveryError("Hay una conexión anterior de otra instalación. Desconéctala desde su instalación original.")
    if previous["value"] not in (None, "", desired):
        raise DiscoveryError("Desktop ya usa otra conexión personalizada. No se ha sustituido.")
    if not record:
        record = {"schema": 1, "platform": sys.platform, "wrapper": desired, "previous": previous,
                  "installed_at": time.time(), "status": "preparing"}
        atomic_json(registration_path(), record)
    # Preflight the exact launcher that Desktop will use. Config migration is
    # reversible on failure; do not register a bridge that cannot start.
    updated = dict(cfg, installation_mode="auto")
    atomic_json(CONFIG, updated)
    try:
        check = subprocess.run([desired, "--version"], capture_output=True, timeout=45,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if check.returncode or not check.stdout.startswith(b"codex-cli "):
            raise DiscoveryError("El puente no supera la prueba de arranque. No se ha conectado al inicio habitual.")
        checks = probe_bridge(wrapper)
    except (OSError, subprocess.SubprocessError, DiscoveryError):
        if config() == updated:
            atomic_json(CONFIG, cfg)
        raise
    if sys.platform == "darwin":
        ensure_login_agent()
    write_environment(desired)
    record.update(status="registered", registered_at=time.time(), protocol_checks=checks, desktop_version=installation.version)
    atomic_json(registration_path(), record)
    # Keep local routing choices, history and credentials untouched.
    return {"registered": True, "desktop_version": installation.version,
            "message": "Conexión instalada. Cierra Desktop cuando terminen tus tareas y ábrelo desde su acceso habitual."
                       " La app que ya está abierta conserva su conexión anterior."}


def uninstall():
    if sys.platform == "linux":
        from linux_desktop import uninstall as uninstall_linux
        return uninstall_linux(ROOT)
    record = read_registration()
    if not record:
        return {"registered": False, "message": "Esta instalación no tiene una conexión registrada."}
    if sys.platform == "darwin" and agent_path().exists() and plistlib.loads(agent_path().read_bytes()) != launch_agent_definition():
        raise DiscoveryError("El ajuste de inicio de sesión cambió; se ha conservado.")
    current = read_environment()
    if current["value"] == record["wrapper"]:
        previous = record["previous"]
        write_environment(previous["value"], previous["kind"])
    elif current["value"] not in (None, "", record["previous"]["value"]):
        raise DiscoveryError("La conexión fue cambiada por otra herramienta. Se ha conservado; no se ha desinstalado automáticamente.")
    if sys.platform == "darwin" and agent_path().exists():
        if plistlib.loads(agent_path().read_bytes()) != launch_agent_definition():
            raise DiscoveryError("El ajuste de inicio de sesión cambió; se ha conservado.")
        subprocess.run(["/bin/launchctl", "bootout", "gui/" + str(os.getuid()) + "/" + LABEL],
                       capture_output=True, timeout=5)  # It may not be loaded yet.
        agent_path().unlink()
    registration_path().unlink()
    return {"registered": False, "message": "Conexión retirada. El siguiente arranque habitual usará el motor original. Tu historial se conserva."}


def restore_session():
    if sys.platform == "linux":
        from linux_desktop import registered
        return {"restored": registered(ROOT)}
    record = read_registration()
    if not record or record.get("status") != "registered" or not Path(record["wrapper"]).is_file():
        return {"restored": False}
    current = read_environment()
    if current["value"] not in (None, "", record["wrapper"]):
        return {"restored": False}
    write_environment(record["wrapper"])
    return {"restored": True}


def doctor():
    report = {"schema": 1, "checked_at": time.time(), "platform": sys.platform,
              "discovery": "unavailable", "registered": False, "bridge_sessions": 0,
              "desktop_sessions": 0, "compatibility": "not_tested"}
    try:
        found = discover(config())
        report.update(discovery="ready", desktop_version=found.version, desktop=str(found.desktop), backend=str(found.backend))
        result = subprocess.run([str(found.backend), "--version"], capture_output=True, timeout=15,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        report["backend_version"] = result.stdout.decode("utf-8", errors="replace").strip()[:120] if result.returncode == 0 else "unavailable"
        report["compatibility"] = "version_checked" if result.returncode == 0 else "failed"
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report["message"] = str(error) if isinstance(error, DiscoveryError) else "No se pudo preparar el motor de Desktop."
    try:
        record = read_registration()
        if sys.platform == "linux":
            from linux_desktop import registered
            report["registered"] = registered(ROOT)
        else:
            report["registered"] = bool(record and record.get("status") == "registered" and
                                        read_environment()["value"] == record["wrapper"] and Path(record["wrapper"]).is_file())
    except (OSError, ValueError, subprocess.SubprocessError):
        report["registration_error"] = True
    for path in STATE.glob("status-*.json"):
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            if time.time() - float(snapshot.get("heartbeat", 0)) > 8:
                continue
            events = snapshot.get("events", [])
            if events and events[-1].get("event") == "bridge_stopped":
                continue
            report["bridge_sessions"] += 1
            if snapshot.get("handshake_complete") and snapshot.get("client_name") in ("codex_desktop", "codex_app", "Codex Desktop"):
                report["desktop_sessions"] += 1
        except (OSError, ValueError, TypeError):
            continue
    report["connection"] = "desktop_connected" if report["desktop_sessions"] else (
        "bridge_observed" if report["bridge_sessions"] else "restart_pending" if report["registered"] else "not_registered")
    atomic_json(STATE / "connection-report.json", report)
    return report


def open_app():
    if sys.platform == "linux":
        from linux import open_app as open_linux
        return open_linux()
    installation = discover(config())
    if sys.platform == "darwin":
        from macos import app_running, open_monitor
        running = app_running(installation.desktop)
    else:
        # App names are constants; never put configurable text into shell code.
        result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                                 "@(Get-Process ChatGPT,Codex -ErrorAction SilentlyContinue).Count"],
                                capture_output=True, text=True, timeout=10,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0:
            raise DiscoveryError("No se pudo comprobar si Desktop sigue abierto.")
        running = int(result.stdout.strip() or "0") > 0
    if running:
        raise DiscoveryError("Desktop sigue abierto. Termina tus tareas y ciérralo por completo antes de cambiar la conexión.")
    env = dict(os.environ, CODEX_CLI_PATH=str(wrapper_path()), PERSONAL_CODEX_ROUTER_CONFIG=str(CONFIG))
    subprocess.Popen([str(installation.desktop)], env=env, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), start_new_session=sys.platform != "win32")
    try:
        if sys.platform == "darwin":
            open_monitor()
        else:
            subprocess.Popen([str(ROOT / "dist/codex-monitor-v24.exe"), "--tray"], creationflags=subprocess.CREATE_NO_WINDOW)
    except OSError:
        pass
    return {"opened": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("doctor", "install", "uninstall", "restore-session", "open"))
    args = parser.parse_args()
    try:
        if sys.platform not in ("win32", "darwin", "linux"):
            raise DiscoveryError("Esta conexión requiere Windows, macOS o Linux.")
        output = {"doctor": doctor, "install": install, "uninstall": uninstall,
                  "restore-session": restore_session, "open": open_app}[args.action]()
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        message = str(error) if isinstance(error, DiscoveryError) else "No se pudo completar la conexión. Ejecuta el diagnóstico; no se han cerrado tus tareas."
        print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
