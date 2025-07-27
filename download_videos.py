#!/usr/bin/env python3
"""
Batch video downloader & thumbnail generator
===========================================

Reads **upload.txt** where each line is of the form
```
https://example.com/video123 - My Awesome Title
```
Downloads each URL (adult‑friendly) with **yt‑dlp**, merges/forces the
resulting file into **MP4** (universally accepted by Bunny.net Stream), renames
it to include the user‑supplied title, and ensures a matching thumbnail:

* MP4 container guaranteed via `merge_output_format="mp4"` so even if the
  source arrives as WebM, it is remuxed to MP4 without re‑encoding (fast &
  lossless).
* If the site provides a thumbnail, yt‑dlp fetches it automatically; otherwise
  a random frame is grabbed with **ffmpeg**.
* Tasks run in parallel yet remain transactional: every video & its thumbnail
  share the same stem, preventing mismatches.

Dependencies
------------
* Python ≥ 3.8
* yt‑dlp → `pip install -U yt-dlp`
* FFmpeg in PATH
* (Optional) cookies.txt – exported browser cookies for age‑gated sites

Usage
-----
```bash
python download_videos.py                  # uses upload.txt in current dir
python download_videos.py --workers 6 \
                        --cookies mycookies.txt \
                        --out downloads_dir
```
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import random
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

from yt_dlp import YoutubeDL

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def sanitize(name: str) -> str:
    """Return a filesystem‑safe version of *name*."""
    return re.sub(r"[^\w\-_.() ]", "", name).strip().replace(" ", "_")


def parse_pairs(lines: List[str]) -> List[Tuple[str, str]]:
    pairs = []
    for ln in lines:
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        if " - " not in ln:
            print(f"[WARN] Skipped malformed line: {ln!r}")
            continue
        url, title = map(str.strip, ln.split(" - ", 1))
        pairs.append((url, title))
    return pairs


def mkdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def random_ts(duration: float) -> float:
    if duration and duration > 10:
        return random.uniform(5, duration * 0.9)
    return 5.0

# ---------------------------------------------------------------------------
# worker
# ---------------------------------------------------------------------------

def process(idx: int, url: str, title: str, out_dir: Path, cookies: Path | None):
    stem = f"{idx:03d}_{sanitize(title)}"
    outfile = out_dir / f"{stem}.mp4"

    ydl_opts = {
        "outtmpl": str(outfile),
        "noplaylist": True,
        "quiet": True,
        "nocheckcertificate": True,
        "writethumbnail": True,
        "concurrent_fragment_downloads": 4,
        # unify container for Bunny.net
        "merge_output_format": "mp4",
        # format selection: best that can be merged into mp4
        "format": "bestvideo+bestaudio/best",
    }
    if cookies and cookies.exists():
        ydl_opts["cookiefile"] = str(cookies)

    print(f"[INFO] ▲ {stem}: downloading …")
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        print(f"[ERROR] {stem}: download failed – {e}")
        return

    thumb = outfile.with_suffix(".jpg")
    if not thumb.exists():
        # Fall back to ffmpeg snapshot
        duration = info.get("duration") or 0
        ts = random_ts(duration)
        cmd = [
            "ffmpeg", "-y", "-ss", str(ts), "-i", str(outfile), "-frames:v", "1", str(thumb),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"[INFO]    thumbnail generated at {ts:.1f}s → {thumb.name}")
        except subprocess.CalledProcessError:
            print(f"[WARN]    unable to generate thumbnail for {stem}")
    else:
        print(f"[INFO]    thumbnail downloaded → {thumb.name}")

    print(f"[INFO] ▼ {stem}: done\n")

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Bulk downloader with Bunny.net‑ready MP4 output")
    ap.add_argument("--src", default="upload.txt", help="Input list file [default: upload.txt]")
    ap.add_argument("--out", default="downloads", help="Output directory [default: downloads]")
    ap.add_argument("--cookies", default="cookies.txt", help="Cookie file for age‑gated sites")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4, help="Parallel workers")
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        sys.exit(f"Input file not found: {src}")

    pairs = parse_pairs(src.read_text("utf-8").splitlines())
    if not pairs:
        sys.exit("No URL‑title pairs detected in input file.")

    out_dir = Path(args.out)
    mkdir(out_dir)
    cookies = Path(args.cookies) if args.cookies else None

    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = [pool.submit(process, i + 1, u, t, out_dir, cookies) for i, (u, t) in enumerate(pairs)]
        for f in cf.as_completed(futs):
            _ = f.result()

    print("All downloads finished.")

if __name__ == "__main__":
    main()
