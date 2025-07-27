#!/usr/bin/env python3
"""
Phase‑3: WordPress autoposter
=============================

Publishes Bunny.net embed codes to a WordPress site. Credentials are
provided via command‑line flags or the ``WP_USER`` and ``WP_APP_PW``
environment variables.

Pipeline
--------
1. Reads *bunny_results.json* (output of Phase‑2).
2. For each successful video:
   • Upload thumbnail → `/wp-json/wp/v2/media`  
   • Create post → `/wp-json/wp/v2/posts` with iframe embed & featured image.
3. Logs progress, writes *wp_results.json*, exits non‑zero on any failure.

Dependencies
------------
```bash
pip install requests tenacity tqdm
```
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from pathlib import Path
from typing import List

from dotenv import dotenv_values, find_dotenv
import logging
import requests
from tenacity import retry, stop_after_attempt, wait_random_exponential
from tqdm import tqdm

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

# --- default credentials from environment ------------------------------------
DEFAULT_USER = os.getenv("WP_USER") or ENV.get("WP_USER")
DEFAULT_PW = os.getenv("WP_APP_PW") or ENV.get("WP_APP_PW")

# -----------------------------------------------------------------------------

def auth_header(user: str, pw: str) -> str:
    token = base64.b64encode(f"{user}:{pw}".encode()).decode()
    return f"Basic {token}"


@retry(stop=stop_after_attempt(3), wait=wait_random_exponential(multiplier=2, max=10))
def upload_media(site: str, auth: str, img: Path) -> int:
    url = f"{site.rstrip('/')}/wp-json/wp/v2/media"
    headers = {
        "Authorization": auth,
        "Content-Disposition": f"attachment; filename={img.name}",
        "Content-Type": "image/jpeg",
    }
    with img.open("rb") as fh:
        r = requests.post(url, headers=headers, data=fh)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"media upload failed [{r.status_code}]: {r.text[:200]}")
    return r.json()["id"]


@retry(stop=stop_after_attempt(3), wait=wait_random_exponential(multiplier=2, max=10))
def create_post(site: str, auth: str, title: str, content: str, media_id: int, status: str) -> int:
    url = f"{site.rstrip('/')}/wp-json/wp/v2/posts"
    payload = {
        "title": title,
        "content": content,
        "featured_media": media_id,
        "status": status,
    }
    r = requests.post(url, headers={"Authorization": auth, "Content-Type": "application/json"}, json=payload)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"create_post failed [{r.status_code}]: {r.text[:200]}")
    return r.json()["id"]


def make_iframe(embed_url: str, width: int = 640, height: int = 360) -> str:
    return (
        f'<figure class="wp-block-embed is-type-video is-provider-bunnystream">\n'
        f'  <iframe src="{embed_url}" loading="lazy" allowfullscreen '
        f'width="{width}" height="{height}" frameborder="0"></iframe>\n'
        f'</figure>'
    )

# -----------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Publish Bunny embeds to WordPress")
    ap.add_argument("--site", required=True, help="Base WP site URL, e.g. https://example.com")
    ap.add_argument("--input", default="bunny_results.json", help="Input JSON from Phase‑2")
    ap.add_argument("--status", default="publish", help="Post status: publish|draft|private")
    ap.add_argument("--width", type=int, default=640, help="Iframe width")
    ap.add_argument("--height", type=int, default=360, help="Iframe height")
    # allow override of env credentials
    ap.add_argument("--user", default=DEFAULT_USER, help="WordPress username [env WP_USER]")
    ap.add_argument("--password", default=DEFAULT_PW, help="WordPress application password [env WP_APP_PW]")
    args = ap.parse_args()

    if not args.user or not args.password:
        sys.exit("WordPress credentials required. Use flags or set WP_USER and WP_APP_PW.")

    auth = auth_header(args.user, args.password)

    src = Path(args.input)
    if not src.exists():
        sys.exit("Input JSON not found.")

    records = json.loads(src.read_text())
    ok_records = [r for r in records if r.get("status") == "ok"]
    if not ok_records:
        sys.exit("No successful Bunny uploads available.")

    wp_res: List[dict] = []
    for rec in tqdm(ok_records, desc="Posting to WP"):
        title = rec["title"]
        embed = rec["embed_url"]
        thumb_path = Path(rec["thumbnail"]) if "thumbnail" in rec else None
        try:
            media_id = upload_media(args.site, auth, thumb_path) if thumb_path and thumb_path.exists() else 0
            content = make_iframe(embed, args.width, args.height)
            post_id = create_post(args.site, auth, title, content, media_id, args.status)
            wp_res.append({"title": title, "post_id": post_id, "status": "ok"})
            tqdm.write(f"[OK] {title} → post {post_id}")
        except Exception as e:
            wp_res.append({"title": title, "status": "error", "error": str(e)})
            tqdm.write(f"[FAIL] {title} – {e}")

    Path("wp_results.json").write_text(json.dumps(wp_res, indent=2))
    errors = [x for x in wp_res if x["status"] != "ok"]
    print(f"\nPosts created: {len(wp_res) - len(errors)} / {len(wp_res)}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
