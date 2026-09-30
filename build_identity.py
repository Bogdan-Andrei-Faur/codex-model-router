"""Identity of code loaded by this process, separate from files installed later."""
import hashlib
import json
from pathlib import Path
import sys

POLICY_VERSION = 8


def identity(root):
    root = Path(root)
    if getattr(sys, "frozen", False):
        from build_stamp import PRODUCT_VERSION, BUILD_ID
        return PRODUCT_VERSION, BUILD_ID
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    digest = hashlib.sha256()
    paths = sorted([*root.glob("*.py"), *root.glob("*.cs"), *root.glob("*.swift"), *root.glob("monitor-ui/*"), *root.glob("assets/*")])
    for path in paths:
        if path.is_file() and path.name != "build_stamp.py":
            digest.update(str(path.relative_to(root)).replace("\\", "/").encode())
            digest.update(path.read_bytes())
    digest.update(version.encode())
    return version, digest.hexdigest()[:16]


def router_identity(root):
    """Fingerprint backend Python code independently of native and web UI."""
    if getattr(sys, "frozen", False):
        from build_stamp import ROUTER_BUILD_ID
        return ROUTER_BUILD_ID
    root = Path(root)
    digest = hashlib.sha256()
    for path in sorted(root.glob("*.py")):
        if path.is_file() and path.name != "build_stamp.py":
            digest.update(path.name.encode())
            digest.update(path.read_bytes())
    digest.update((root / "VERSION").read_text(encoding="utf-8").strip().encode())
    return digest.hexdigest()[:16]


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    version, build_id = identity(root)
    router_build_id = router_identity(root)
    (root / "BUILD.json").write_text(json.dumps({"product_version": version, "build_id": build_id, "router_build_id": router_build_id, "policy_version": POLICY_VERSION}) + "\n", encoding="utf-8")
    (root / "build_stamp.py").write_text("PRODUCT_VERSION = " + repr(version) + "\nBUILD_ID = " + repr(build_id) + "\nROUTER_BUILD_ID = " + repr(router_build_id) + "\n", encoding="utf-8")
