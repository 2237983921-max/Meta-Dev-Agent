from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = int(os.getenv("AI_BRIEFING_PORT", "8765"))


def is_server_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.35)
        return sock.connect_ex((HOST, PORT)) == 0


def run_generator(demo: bool) -> int:
    command = [sys.executable, str(ROOT / "generate_briefing.py")]
    if demo:
        command.append("--demo")
    print("Refreshing briefing data...")
    completed = subprocess.run(command, cwd=str(ROOT), check=False)
    return completed.returncode


def start_server() -> bool:
    (ROOT / "data").mkdir(parents=True, exist_ok=True)
    log_path = ROOT / "data" / "server.log"
    log_handle = log_path.open("ab")
    subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "-d", str(ROOT)],
        cwd=str(ROOT),
        stdout=log_handle,
        stderr=log_handle,
        start_new_session=True,
    )

    for _ in range(30):
        if is_server_running():
            return True
        time.sleep(0.2)
    return False


def open_browser(url: str) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", url], check=False)
        return
    if os.name == "nt":
        os.startfile(url)  # type: ignore[attr-defined]
        return
    subprocess.run(["xdg-open", url], check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Launch the AI daily briefing site.")
    parser.add_argument("--demo", action="store_true", help="use demo data")
    parser.add_argument("--skip-refresh", action="store_true", help="do not refresh the JSON before opening")
    parser.add_argument("--no-open", action="store_true", help="start the site without opening the browser")
    args = parser.parse_args()

    if not args.skip_refresh:
        return_code = run_generator(args.demo)
        if return_code != 0:
            print("Refreshing the briefing failed.")
            return return_code

    if not is_server_running():
        print("Starting local site...")
        if not start_server():
            print("Failed to start the local web server.")
            return 1
    else:
        print("Local site is already running.")

    url = f"http://{HOST}:{PORT}/index.html"
    if not args.no_open:
        open_browser(url)

    print(f"AI briefing ready: {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
