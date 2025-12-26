"""Helper to restart uvicorn safely on the same port.

Run as a separate Python process. It waits until the target host:port is
no longer accepting connections (meaning the current server has shut down),
then starts a new uvicorn process with the provided interpreter.

Usage:
  python -m app.utils.server_restart --host 127.0.0.1 --port 8000 --py path_to_python
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path


def _is_listening(host: str, port: int, timeout: float = 0.2) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except Exception:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--py", dest="python_bin", default=sys.executable)
    args = p.parse_args(argv)

    host = args.host
    port = args.port
    python_bin = args.python_bin or sys.executable

    # Wait until the current server releases the port
    start = time.time()
    while _is_listening(host, port):
        time.sleep(0.2)
        # Safety timeout to avoid infinite waits (10s)
        if time.time() - start > 10:
            break

    # Start a new uvicorn process
    cmd = [
        python_bin,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    try:
        subprocess.Popen(cmd, cwd=str(Path.cwd()), creationflags=creationflags)
    except Exception:
        # We swallow exceptions here; the caller already exited.
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
