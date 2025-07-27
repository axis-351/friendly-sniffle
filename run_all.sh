#!/bin/bash
set -e

if [ -f .env ]; then
    set -a
    . .env
    set +a
fi

python3 download_videos.py "$@"
python3 upload_bunny.py
python3 wp_publish.py --site "$WP_SITE"

echo "All steps completed"
