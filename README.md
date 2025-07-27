# Video Upload Kit

This kit provides a lightweight pipeline for downloading videos, uploading them
 to Bunny.net Stream and publishing posts on WordPress.

## Setup
On **Linux/macOS** run `./setup.sh` once to install the required Python
packages (which include `python-dotenv`) and `ffmpeg`.

On **Windows** install the Python dependencies manually with
`pip install -r requirements.txt` (make sure `python-dotenv` is included) and
download and install `ffmpeg` separately, adding it to your `PATH`.

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

Running `upload_bunny.py` creates `bunny_results.json` containing the embed URL
for each video and, when available, the local path to the thumbnail image. The
uploader now defaults to the latest Bunny.net API endpoint at
`https://api.bunny.net`. You can override this by setting `BUNNY_BASE_URL` in
your `.env` file if needed.

A `.env.example` file is provided as a template. Copy it to `.env` and add your
keys there. Each line must be written as `KEY=value` with no extra spaces or
quotes (for example: `WP_SITE=https://example.com`). This example file
illustrates the required formats for each variable. The scripts automatically
load this file (via [`python-dotenv`](https://github.com/theskumar/python-dotenv)) and
read these variables:
- `BUNNY_API_KEY` and `BUNNY_LIBRARY_ID`
- `BUNNY_BASE_URL` (optional API host, defaults to `https://api.bunny.net`)
- `WP_USER` and `WP_APP_PW`
- `WP_SITE` (used by `master.py` and `run_all.sh`)

A small `run_all.sh` shell script is also included for Unix systems, but
`master.py` works on Windows and Linux alike.
