#!/usr/bin/env python3
"""Run the entire video pipeline then clean up.

This convenience script executes ``download_videos.py``, ``upload_bunny.py``
and ``wp_publish.py`` in sequence. It is cross-platform so it can be used
natively on Windows without Bash.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values, find_dotenv
import logging


def _load_env() -> dict:
    env_file = find_dotenv(usecwd=True)
    if not env_file:
        return {}
    logger = logging.getLogger("dotenv.main")
    msgs: list[logging.LogRecord] = []

    class _Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            msgs.append(record)

    handler = _Handler()
    logger.addHandler(handler)
    try:
        values = dotenv_values(env_file)
    except Exception as e:  # pragma: no cover - just in case
        logger.removeHandler(handler)
        sys.exit(f"Failed to parse .env – {e}")
    logger.removeHandler(handler)
    if msgs or not values:
        line = msgs[0].args[0] if msgs else "unknown"
        sys.exit(
            f"Failed to parse .env – check for stray spaces or quotes on line {line}."
        )
    return {k: v for k, v in values.items() if v is not None}


ENV = _load_env()


def run(cmd: list[str]):
    print("\n>", " ".join(cmd))
    subprocess.check_call(cmd)


def cleanup():
    print("\n> cleaning temporary files")
    targets = ["downloads", "bunny_results.json", "wp_results.json", "__pycache__"]
    for t in targets:
        p = Path(t)
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()
    print("Cleanup complete")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run download, upload, publish, then clean")
    ap.add_argument("--site", default=os.getenv("WP_SITE") or ENV.get("WP_SITE"), help="WordPress site URL")
    ap.add_argument("download_args", nargs=argparse.REMAINDER,
                    help="Extra arguments passed to download_videos.py")
    args = ap.parse_args()

    if not args.site:
        sys.exit("Provide --site or set WP_SITE")

    run(["python", "download_videos.py", *args.download_args])
    run(["python", "upload_bunny.py"])
    run(["python", "wp_publish.py", "--site", args.site])
    cleanup()


if __name__ == "__main__":
    main()
