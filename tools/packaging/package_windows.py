"""Build a self-contained Windows ZIP without bundling Desktop or user data.

The resulting archive is per-user, discovers the current Desktop installation at
runtime, and keeps history/keys out of the archive. It is not signed yet.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import zipfile


ROOT = Path(__file__).resolve().parents[2]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
RELEASE = ROOT / "release"
STAGE = RELEASE / "Codex-automatico"


def run(*args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--framework-reference-path', type=Path,
                        help='Use an existing .NET Framework 4.8 reference directory for the native build.')
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("El paquete autocontenido de esta entrega se compila en Windows.")
    build = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ROOT / "build.ps1"), "-BuildOnly"]
    if args.framework_reference_path:
        build += ["-FrameworkReferencePath", str(args.framework_reference_path.resolve())]
    run(*build)
    run(sys.executable, str(ROOT / "run.py"), "build-identity")
    RELEASE.mkdir(exist_ok=True)
    if STAGE.resolve().parent != RELEASE.resolve() or STAGE.name != "Codex-automatico":
        raise ValueError("Unexpected package destination")
    shutil.rmtree(STAGE, ignore_errors=True)
    STAGE.mkdir()
    temporary = Path(tempfile.mkdtemp(prefix="codex-router-package-", dir=RELEASE))
    try:
        bin_dir = STAGE / "bin"; dist_dir = STAGE / "dist"; state_dir = STAGE / "state"
        bin_dir.mkdir(); dist_dir.mkdir(); state_dir.mkdir()
        for entry, name in (("router.py", "codex-router-core"), ("desktop.py", "codex-desktop-core"), ("monitor_service.py", "codex-monitor-core")):
            run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--name", name,
                "--distpath", str(bin_dir), "--workpath", str(temporary / "work" / name),
                "--specpath", str(temporary / "spec"), "--paths", str(ROOT / "src"),
                "--paths", str(ROOT), "--hidden-import", "build_stamp",
                "--collect-submodules", "codex_model_router", str(ROOT / entry))
        shutil.copy2(ROOT / "dist" / "codex-router-v19.exe", dist_dir / "codex-router.exe")
        shutil.copy2(ROOT / "dist" / "codex-monitor-v24.exe", dist_dir / "codex-monitor-v24.exe")
        for name in ("Microsoft.Web.WebView2.Core.dll", "Microsoft.Web.WebView2.Wpf.dll"):
            shutil.copy2(ROOT / "dist" / name, dist_dir / name)
        shutil.copytree(ROOT / "dist/runtimes", dist_dir / "runtimes")
        shutil.copytree(ROOT / "dist/windows-ui", dist_dir / "windows-ui")
        config = json.loads((ROOT / "config.example.json").read_text(encoding="utf-8"))
        config.pop("python", None)
        config.update({"desktop_runtime": r"bin\\codex-desktop-core.exe", "router_runtime": r"bin\\codex-router-core.exe", "monitor_runtime": r"bin\\codex-monitor-core.exe"})
        (STAGE / "config.example.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        shutil.copy2(ROOT / "VERSION", STAGE / "VERSION")
        shutil.copy2(ROOT / "BUILD.json", STAGE / "BUILD.json")
        shutil.copytree(ROOT / "assets", STAGE / "assets")
        shutil.copy2(ROOT / "README.md", STAGE / "README.md")
        shutil.copytree(ROOT / "docs", STAGE / "docs")
        (STAGE / "INSTALAR.txt").write_text(
            "Requisitos: .NET Framework 4.8 y Microsoft Edge WebView2 Runtime (Evergreen).\n"
            "Instala el runtime desde https://developer.microsoft.com/microsoft-edge/webview2/ si falta.\n"
            "1. Extrae esta carpeta en una ubicación permanente.\n"
            "2. Ejecuta dist\\codex-router.exe --install-integration.\n"
            "3. Cuando no haya tareas activas, reinicia ChatGPT Desktop desde su acceso habitual.\n"
            "4. Abre dist\\codex-router.exe --status para ver el monitor.\n\n"
            "Para actualizar: termina las tareas, cierra Desktop y el monitor y extrae la nueva versión en la MISMA carpeta.\n"
            "El ZIP no contiene config.local.json ni datos de state: se conservan tus preferencias, claves e historial.\n"
            "El paquete descubre cada actualización de Desktop al arrancar y no contiene tu historial ni tus claves.\n",
            encoding="utf-8")
        archive = RELEASE / (STAGE.name + "-" + VERSION + "-windows.zip")
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
            for path in STAGE.rglob("*"):
                if path.is_file(): out.write(path, path.relative_to(RELEASE))
        print(json.dumps({"archive": str(archive), "version": VERSION}, ensure_ascii=False))
    finally:
        if temporary.resolve().parent != RELEASE.resolve():
            raise ValueError("Unexpected build workspace")
        shutil.rmtree(temporary, ignore_errors=True)


if __name__ == "__main__":
    main()
