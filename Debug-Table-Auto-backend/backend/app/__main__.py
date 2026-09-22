"""Executable entry point for source and packaged local operation."""

from __future__ import annotations

import argparse
import os
import sys
import threading
import webbrowser
from dataclasses import replace

import uvicorn

from app.config import Settings, apply_packaged_defaults
from app.main import create_app


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Debug Table Auto local service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--mode", choices=("mock", "formal"), default=None)
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    is_frozen = bool(getattr(sys, "frozen", False))
    settings = apply_packaged_defaults(Settings.from_environment(), is_frozen=is_frozen)
    default_mode = "formal" if is_frozen else settings.mode
    settings = replace(settings, mode=args.mode or default_mode)
    url = f"http://{args.host}:{args.port}/"
    if not args.no_browser and args.host in {"127.0.0.1", "localhost"}:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()
    uvicorn.run(create_app(settings), host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUTF8", "1")
    main()
