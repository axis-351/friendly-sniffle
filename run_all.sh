#!/bin/bash
set -e

python3 download_videos.py "$@"
python3 upload_bunny.py
python3 wp_publish.py --site "$WP_SITE"

echo "All steps completed"
