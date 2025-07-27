# Video Upload Kit

This kit provides a lightweight pipeline for downloading videos, uploading them
 to Bunny.net Stream and publishing posts on WordPress.

## Setup
Run `./setup.sh` once to install the required packages (Python modules and
ffmpeg).

## Workflow
1. Add your links and titles to `upload.txt` (`url - My Title` per line).
2. Run `python master.py --site https://example.com` to download videos,
   upload them to Bunny Stream, publish posts on WordPress and clean up the
   temporary files.

If you prefer to execute each phase manually:

```
python download_videos.py
python upload_bunny.py
python wp_publish.py --site https://example.com
./cleanup.sh
```

A `.env.example` file is provided as a template. Copy it to `.env` and add your
keys there. The scripts automatically load this file (via `python-dotenv`) and
read these variables:
- `BUNNY_API_KEY` and `BUNNY_LIBRARY_ID`
- `WP_USER` and `WP_APP_PW`
- `WP_SITE` (used by `master.py` and `run_all.sh`)

A small `run_all.sh` shell script is also included for Unix systems, but
`master.py` works on Windows and Linux alike.
