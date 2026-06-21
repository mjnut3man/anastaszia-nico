#!/usr/bin/env python3
"""
Anastaszia Nico — Instagram Reels Auto Poster

Companion to post.py (photos). Posts the next video Reel from reels-to-post/.
Each Reel is a pair:  REEL_XXX.mp4  +  REEL_XXX.json  (the .json holds "caption").

Usage:
  python3 post_reel.py              → posts the next Reel in the queue
  python3 post_reel.py REEL_003     → posts a specific Reel
  python3 post_reel.py --preview    → shows what would post without posting
"""

import os
import sys
import json
import time
import requests
import cloudinary
import cloudinary.uploader
from datetime import datetime
from pathlib import Path

BASE   = Path(__file__).parent
READY  = BASE / "reels-to-post"
POSTED = BASE / "reels-posted"

# Load .env for local dev; GitHub Actions injects these as real env vars
try:
    from dotenv import dotenv_values
    for k, v in dotenv_values(BASE / ".env").items():
        os.environ.setdefault(k, v)
except Exception:
    pass

ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
USER_ID      = os.environ["INSTAGRAM_USER_ID"]
GRAPH        = "https://graph.instagram.com/v21.0"

cloudinary.config(
    cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
    api_key=os.environ["CLOUDINARY_API_KEY"],
    api_secret=os.environ["CLOUDINARY_API_SECRET"],
    secure=True
)

# How long to wait for Instagram to finish processing the uploaded video
PROCESS_TIMEOUT_S = 360   # 6 minutes
PROCESS_POLL_S    = 8


def find_next():
    """Return the next REEL_XXX.mp4 in the queue (alphabetical = order)."""
    vids = sorted(READY.glob("REEL_*.mp4"))
    return vids[0] if vids else None


def find_specific(target):
    target = target.replace(".mp4", "").replace(".json", "")
    p = READY / f"{target}.mp4"
    return p if p.exists() else None


def get_caption(mp4_path):
    """Read the caption from the matching .json sidecar."""
    meta_path = mp4_path.with_suffix(".json")
    if meta_path.exists():
        data = json.loads(meta_path.read_text())
        return data.get("caption", "").strip()
    return ""


def upload(mp4_path):
    print(f"    Uploading {mp4_path.name} to Cloudinary (video)...")
    result = cloudinary.uploader.upload_large(
        str(mp4_path),
        folder="anastaszianico_reels",
        public_id=mp4_path.stem,
        overwrite=True,
        resource_type="video",
    )
    return result["secure_url"]


def create_reel_container(video_url, caption):
    r = requests.post(
        f"{GRAPH}/{USER_ID}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": "true",
            "access_token": ACCESS_TOKEN,
        },
    )
    data = r.json()
    if "id" not in data:
        raise Exception(f"Container error: {data}")
    return data["id"]


def wait_until_ready(container_id):
    """Poll the container until Instagram finishes transcoding the video."""
    deadline = time.time() + PROCESS_TIMEOUT_S
    while time.time() < deadline:
        r = requests.get(
            f"{GRAPH}/{container_id}",
            params={"fields": "status_code,status", "access_token": ACCESS_TOKEN},
        )
        data = r.json()
        status = data.get("status_code")
        print(f"    ...processing: {status}")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise Exception(f"Processing failed: {data}")
        time.sleep(PROCESS_POLL_S)
    raise Exception("Timed out waiting for Instagram to process the video.")


def publish(container_id):
    r = requests.post(
        f"{GRAPH}/{USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": ACCESS_TOKEN},
    )
    data = r.json()
    if "id" not in data:
        raise Exception(f"Publish error: {data}")
    return data["id"]


def move_to_posted(mp4_path):
    POSTED.mkdir(exist_ok=True)
    mp4_path.rename(POSTED / mp4_path.name)
    meta = mp4_path.with_suffix(".json")
    if meta.exists():
        meta.rename(POSTED / meta.name)


def run(target=None, preview=False):
    print(f"\n=== Anastaszia Nico — Reels Poster ===")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    mp4 = find_specific(target) if target else find_next()
    if not mp4:
        print("  Nothing to post — reels-to-post/ is empty.")
        return

    caption = get_caption(mp4)
    print(f"  File:    {mp4.name}")
    print(f"  Caption: {caption.splitlines()[0] if caption else '(none)'}")

    if preview:
        print(f"\n  [PREVIEW — not posted]\n\n  Full caption:\n{caption}")
        return

    print()
    video_url = upload(mp4)
    print(f"    Cloudinary URL: {video_url}")

    print("  Creating Reel container...")
    container_id = create_reel_container(video_url, caption)

    print("  Waiting for Instagram to process the video...")
    wait_until_ready(container_id)

    print("  Publishing...")
    post_id = publish(container_id)

    move_to_posted(mp4)

    print(f"\n  ✅ Posted Reel! ID: {post_id}")
    print(f"  instagram.com/anastaszianico\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    preview = "--preview" in args
    args = [a for a in args if a != "--preview"]
    target = args[0] if args else None
    run(target=target, preview=preview)
