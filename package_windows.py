"""Build a self-contained Windows ZIP without bundling Desktop or user data.

The resulting archive is per-user, discovers the current Desktop installation at
runtime, and keeps history/keys out of the archive. It is not signed yet.
"""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


ROOT = Path(__file__).resolve().parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
RELEASE = ROOT / "release"
STAGE = RELEASE / ("Codex-automatico-" + VERSION + "-windows")


def run(*args):
    subprocess.run(args, check=True)


def main():
    if sys.platform != "win32":
        raise SystemExit("El paquete autocontenido de esta entrega se compila en Windows.")
    run("powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "build.ps1"), "-BuildOnly")
    RELEASE.mkdir(exist_ok=True)
    shutil.rmtree(STAGE, ignore_errors=True)
    STAGE.mkdir()
    temporary = Path(tempfile.mkdtemp(prefix="codex-router-package-", dir=RELEASE))
    try:
        bin_dir = STAGE / "bin"; dist_dir = STAGE / "dist"; state_dir = STAGE / "state"
        bin_dir.mkdir(); dist_dir.mkdir(); state_dir.mkdir()
        for entry, name in (("router.py", "codex-router-core"), ("desktop.py", "codex-desktop-core")):
            run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--name", name,
                "--distpath", str(bin_dir), "--workpath", str(temporary / "work" / name),
                "--specpath", str(temporary / "spec"), str(ROOT / entry))
        shutil.copy2(ROOT / "dist" / "codex-router-v19.exe", dist_dir / "codex-router.exe")
        shutil.copy2(ROOT / "dist" / "codex-monitor-v24.exe", dist_dir / "codex-monitor-v24.exe")
        config = json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
        config.pop("python", None)
        config.update({"desktop_runtime": r"bin\\codex-desktop-core.exe", "router_runtime": r"bin\\codex-router-core.exe"})
        (STAGE / "config.local.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        shutil.copy2(ROOT / "VERSION", STAGE / "VERSION")
        shutil.copy2(ROOT / "README.md", STAGE / "README.md")
        (STAGE / "INSTALAR.txt").write_text(
            "1. Extrae esta carpeta en una ubicación permanente.\n"
            "2. Ejecuta dist\\codex-router.exe --install-integration.\n"
            "3. Cuando no haya tareas activas, reinicia ChatGPT Desktop desde su acceso habitual.\n"
            "4. Abre dist\\codex-router.exe --status para ver el monitor.\n\n"
            "El paquete descubre cada actualización de Desktop al arrancar y no contiene tu historial ni tus claves.\n",
            encoding="utf-8")
        archive = RELEASE / (STAGE.name + ".zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
            for path in STAGE.rglob("*"):
                if path.is_file(): out.write(path, path.relative_to(RELEASE))
        print(json.dumps({"archive": str(archive), "version": VERSION}, ensure_ascii=False))
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


if __name__ == "__main__":
    main()
