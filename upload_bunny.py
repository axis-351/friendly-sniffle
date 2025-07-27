#!/usr/bin/env python3
"""
upload_bunny.py — Phase‑2 uploader (Bunny creds baked‑in)
========================================================
Uploads every `*.mp4` + thumbnail pair from the *downloads/* directory to your
Bunny Stream library **473187** using API key **e579d849‑3a35‑4e40‑bda011272190‑2ddc‑4d6f**.

Override values with flags or env vars if you ever need a different account.

Dependencies: `pip install requests tenacity tqdm`
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

import requests
from tenacity import retry, stop_after_attempt, wait_fixed, wait_random_exponential
from tqdm import tqdm

# ————————————————————————————————————————————————————————————————
# Default credentials (can be overridden by flags or env vars)
# ————————————————————————————————————————————————————————————————
API_KEY_DEFAULT = "e579d849-3a35-4e40-bda011272190-2ddc-4d6f"
LIB_ID_DEFAULT  = 473187

BASE_URL = "https://video.bunnycdn.com"
EMBED_PATTERN = "https://iframe.mediadelivery.net/embed/{lib}/{vid}"

# ——————————————————————————— helper functions ——————————————————————————

def _headers(api_key: str, ct: str | None = None) -> Dict[str, str]:
    h = {"AccessKey": api_key, "Accept": "application/json"}
    if ct:
        h["Content-Type"] = ct
    return h


@retry(stop=stop_after_attempt(3), wait=wait_random_exponential(2, 10))
def create_video(api_key: str, lib: int, title: str) -> str:
    url = f"{BASE_URL}/library/{lib}/videos"
    r = requests.post(url, headers=_headers(api_key, "application/json"), json={"title": title})
    if r.status_code not in (200, 201):
        raise RuntimeError(f"create_video [{r.status_code}]: {r.text[:200]}")
    data = r.json()
    return data.get("guid") or data.get("videoId")


@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def upload_binary(api_key: str, lib: int, vid: str, mp4: Path):
    url = f"{BASE_URL}/library/{lib}/videos/{vid}"
    with mp4.open("rb") as fh:
        r = requests.put(url, headers=_headers(api_key, "application/octet-stream"), data=fh)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"upload_binary [{r.status_code}]: {r.text[:200]}")


@retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
def set_thumb(api_key: str, lib: int, vid: str, jpg: Path):
    url = f"{BASE_URL}/library/{lib}/videos/{vid}/thumbnail"
    with jpg.open("rb") as fh:
        r = requests.post(url, headers=_headers(api_key, "application/octet-stream"), data=fh)
    if r.status_code not in (200, 201, 204):
        raise RuntimeError(f"set_thumbnail [{r.status_code}]: {r.text[:200]}")

# ——————————————————————————— worker ————————————————————————————

def process(idx: int, mp4: Path, jpg: Path | None, key: str, lib: int, results: List[dict]):
    title = mp4.stem.split("_", 1)[-1].replace("_", " ")
    try:
        vid = create_video(key, lib, title)
        upload_binary(key, lib, vid, mp4)
        if jpg and jpg.exists():
            set_thumb(key, lib, vid, jpg)
        embed = EMBED_PATTERN.format(lib=lib, vid=vid)
        results.append({"title": title, "video_id": vid, "embed_url": embed, "status": "ok"})
        print(f"[OK] {idx}: {title} -> {vid}")
    except Exception as e:
        results.append({"title": title, "status": "error", "error": str(e)})
        print(f"[FAIL] {idx}: {title} – {e}")

# ——————————————————————————— main —————————————————————————————

def main():
    ap = argparse.ArgumentParser(description="Upload MP4s to Bunny Stream & collect embed links")
    ap.add_argument("--dir", default="downloads", help="Directory with MP4/JPG pairs [downloads]")
    ap.add_argument("--workers", type=int, default=4, help="Parallel uploads")
    ap.add_argument("--api-key", default=os.getenv("BUNNY_API_KEY", API_KEY_DEFAULT))
    ap.add_argument("--library", type=int, default=int(os.getenv("BUNNY_LIBRARY_ID", str(LIB_ID_DEFAULT))))
    ap.add_argument("--out", default="bunny_results.json", help="JSON summary file")
    args = ap.parse_args()

    mp4_files = sorted(Path(args.dir).glob("*.mp4"))
    if not mp4_files:
        sys.exit("No MP4 files found; run Phase‑1 first.")

    results: List[dict] = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = []
        for idx, mp4 in enumerate(mp4_files, 1):
            jpg = mp4.with_suffix(".jpg")
            futs.append(ex.submit(process, idx, mp4, jpg if jpg.exists() else None,
                                   args.api_key, args.library, results))
        for f in tqdm(cf.as_completed(futs), total=len(futs), desc="Uploading"):
            _ = f.result()

    Path(args.out).write_text(json.dumps(results, indent=2))
    errs = [r for r in results if r["status"] != "ok"]
    print(f"\nCompleted: {len(results)} – successes: {len(results)-len(errs)} – failures: {len(errs)}")
    sys.exit(1 if errs else 0)

if __name__ == "__main__":
    main()
