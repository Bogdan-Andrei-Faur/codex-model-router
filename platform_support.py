"""Small OS boundary shared by the bridge, launcher and smoke checks."""
import os
from pathlib import Path
import signal
import select
import subprocess


def backend_path(config):
    binary = Path(config["codex"]).expanduser().resolve(strict=True)
    expected = "codex.exe" if os.name == "nt" else "codex"
    if binary.name.lower() != expected or not binary.is_file():
        raise ValueError("Unexpected backend filename")
    if os.name != "nt" and not os.access(binary, os.X_OK):
        raise ValueError("Backend is not executable")
    return binary


def creation_flags():
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def uses_stdio(args):
    # Desktop puts global -c overrides BEFORE the subcommand on macOS.
    # Consume only known global options, never search a prompt for app-server.
    index = 0
    while index < len(args):
        arg = args[index]
        if arg in ("-c", "--config", "--enable", "--disable"):
            if index + 1 >= len(args):
                return False
            index += 2
        elif arg.startswith(("--config=", "--enable=", "--disable=")) or (arg.startswith("-c") and len(arg) > 2):
            index += 1
        else:
            break
    if index >= len(args) or args[index] != "app-server":
        return False
    server_args = args[index + 1:]
    index = 0
    while index < len(server_args):
        arg = server_args[index]
        if arg in ("-c", "--config", "--enable", "--disable"):
            index += 2
            continue
        if arg in ("daemon", "proxy", "generate-ts", "generate-json-schema"):
            return False
        if arg == "--listen":
            if index + 1 >= len(server_args) or server_args[index + 1] != "stdio://":
                return False
            index += 2
            continue
        if arg.startswith("--listen=") and arg != "--listen=stdio://":
            return False
        index += 1
    return True


def stop_backend(proc):
    """Bounded shutdown; on POSIX the bridge owns a separate process group."""
    def send(sig):
        try:
            if os.name == "nt":
                proc.terminate() if sig == signal.SIGTERM else proc.kill()
            else:
                os.killpg(proc.pid, sig)
        except ProcessLookupError:
            pass
    send(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            proc.kill()
        else:
            send(signal.SIGKILL)
        proc.wait(timeout=5)


def input_lines(stream, stop):
    """Avoid a daemon holding Python's buffered stdin lock during POSIX exit."""
    if os.name == "nt":
        yield from stream
        return
    pending = b""
    while not stop.is_set():
        if not select.select([stream.fileno()], [], [], 0.2)[0]:
            continue
        chunk = os.read(stream.fileno(), 65536)
        if not chunk:
            if pending:
                yield pending
            return
        pending += chunk
        while b"\n" in pending:
            line, pending = pending.split(b"\n", 1)
            yield line + b"\n"
