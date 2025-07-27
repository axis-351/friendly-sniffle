# Video Upload Kit

This kit provides a lightweight pipeline for downloading videos, uploading them
 to Bunny.net Stream and publishing posts on WordPress.

## Setup
Run `./setup.sh` once to install the required packages (Python modules and
ffmpeg).

## Workflow
1. Add your links and titles to `upload.txt` (`url - My Title` per line).
2. Run `python download_videos.py` to fetch videos and thumbnails.
3. Run `python upload_bunny.py` to upload them to Bunny Stream.
4. Run `python wp_publish.py --site https://example.com` to create WordPress posts.
5. Run `./cleanup.sh` to remove temporary files when finished.

A `.env.example` file is provided as a template. Copy it to `.env` and add your
keys there. The scripts read these variables:
- `BUNNY_API_KEY` and `BUNNY_LIBRARY_ID`
- `WP_USER` and `WP_APP_PW`
- `WP_SITE` (used by `run_all.sh`)

A convenience script `run_all.sh` executes the three phases in sequence using
those environment variables.
