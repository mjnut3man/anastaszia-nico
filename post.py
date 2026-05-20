#!/usr/bin/env python3
"""
Anastaszia Nico — Instagram Auto Poster
Runs automatically at 8:00 AM and 7:00 PM daily.

Usage:
  python3 post.py              → posts the next scheduled item
  python3 post.py POST_005     → posts a specific post (single or carousel)
  python3 post.py --preview    → shows what would post without posting
"""

import os
import sys
import time
import requests
import cloudinary
import cloudinary.uploader
from datetime import datetime
from pathlib import Path

BASE   = Path(__file__).parent
READY  = BASE / "ready-to-post"
POSTED = BASE / "posted"

# Load .env for local dev; GitHub Actions injects these as real env vars
try:
    from dotenv import dotenv_values
    for k, v in dotenv_values(BASE / ".env").items():
        os.environ.setdefault(k, v)
except Exception:
    pass

ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
USER_ID      = os.environ["INSTAGRAM_USER_ID"]

cloudinary.config(
    cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
    api_key=os.environ["CLOUDINARY_API_KEY"],
    api_secret=os.environ["CLOUDINARY_API_SECRET"],
    secure=True
)

# Caption bank — keyed by post number, falls back to rotation
CAPTIONS = {
    1:  ("she walked in and the room adjusted 🖤", "#darkaesthetic #altgirl #anastaszianico #aiinfluencer #portrait"),
    2:  ("she doesn't need a reason 🖤", "#portrait #altgirl #darkaesthetic #anastaszianico #aimodel"),
    3:  ("mornings hit different from this angle ☀️", "#morningvibes #homegirl #naturallight #anastaszianico"),
    4:  ("golden hour found me first 🌅", "#goldenhour #outdoors #altgirl #anastaszianico #summergirl"),
    5:  ("outfit did the talking today 🖤", "#ootd #altfashion #anastaszianico #outfitcheck #darkstyle"),
    6:  ("she showed up and that was enough", "#altgirl #darkaesthetic #anastaszianico #aiinfluencer #portrait"),
    7:  ("the glasses stay on 🖤", "#altgirl #glasses #aesthetic #anastaszianico #dayinmylife"),
    8:  ("soft colors, sharp stare", "#fashion #ootd #altgirl #anastaszianico #aesthetic"),
    9:  ("still waters 🖤", "#portrait #editorial #darkaesthetic #anastaszianico #aimodel"),
    10: ("minimalist era, permanently", "#minimalist #ootd #fashion #anastaszianico #altgirl"),
    11: ("said everything without saying a word", "#portrait #altgirl #anastaszianico #darkaesthetic #aimodel"),
    12: ("mirror check ✓", "#mirrorselfie #ootd #homegirl #anastaszianico #altgirl"),
    13: ("she lifts. she leaves. she gets coffee. 💪", "#gym #fitgirl #thatgirl #anastaszianico #workout"),
    14: ("going somewhere. probably nowhere important. 🚗", "#carselfie #dayinmylife #altgirl #anastaszianico"),
    15: ("same energy, different angle 🖤", "#ootd #carousel #altfashion #anastaszianico #outfitcheck"),
    16: ("sitting in the sunlight like it owes me something ☀️", "#bedroomaesthetic #morningvibes #cozygirl #anastaszianico"),
    17: ("she's thinking. don't interrupt.", "#portrait #altgirl #anastaszianico #darkaesthetic #aimodel"),
    18: ("close enough 🖤", "#portrait #closeup #anastaszianico #naturalbeauty #altgirl"),
    19: ("not a morning person but here we are", "#homegirl #dayinmylife #reallife #anastaszianico #altgirl"),
    20: ("café as a personality trait ☕", "#coffeeshop #cafevibes #coffeeaesthetic #anastaszianico #altgirl"),
    21: ("outdoor is a vibe when the light cooperates 🌿", "#outdoor #nature #altgirl #anastaszianico #aesthetic"),
    22: ("one look wasn't enough 🖤", "#carousel #altgirl #anastaszianico #lifestyle #aesthetic"),
    23: ("green was always her color 💚", "#bikini #summervibes #anastaszianico #swimwear #aesthetic"),
    24: ("office hours, her way 💼", "#officegirl #workfit #9to5 #anastaszianico #altgirl"),
    25: ("desk job, main character energy 💼", "#officegirl #workfit #anastaszianico #altgirl #dayinmylife"),
    26: ("sand between the thoughts 🏖️", "#beach #beachvibes #bikini #anastaszianico #summervibes"),
    27: ("grocery store run. still serving. 🛒", "#grocerystore #dayinmylife #reallife #anastaszianico #altgirl"),
    28: ("soft mode activated 🦋", "#softgirl #fairyaesthetic #anastaszianico #aesthetic #altgirl"),
    29: ("fairy hours only 🦋✨", "#fairycore #softaesthetic #anastaszianico #altgirl #vibes"),
}


FALLBACK = [
    ("she walked in and the room adjusted 🖤", "#altgirl #anastaszianico #aiinfluencer #darkaesthetic #portrait"),
    ("she showed up 🖤", "#altgirl #anastaszianico #aimodel #aesthetic #darkaesthetic"),
    ("no context needed", "#anastaszianico #altgirl #aiinfluencer #portrait #aesthetic"),
    ("unbothered 🖤", "#altgirl #anastaszianico #aimodel #darkaesthetic #aesthetic"),
    ("let the fit speak", "#ootd #altfashion #anastaszianico #altgirl #fashion"),
]

def get_caption(post_num):
    if post_num in CAPTIONS:
        caption, tags = CAPTIONS[post_num]
    else:
        caption, tags = FALLBACK[(post_num - 1) % len(FALLBACK)]
    return f"{caption}\n\n{tags}"

def get_post_num(filename):
    try:
        return int(''.join(filter(str.isdigit, Path(filename).stem.rstrip('abcdefgh'))))
    except:
        return 1

def find_next_group():
    """Return (post_num, [list of files]) for the next post."""
    files = sorted(READY.glob("POST_*"))
    if not files:
        return None, []

    groups = {}
    for f in files:
        stem = f.stem  # POST_005a
        base = stem.rstrip('abcdefgh')
        if base not in groups:
            groups[base] = []
        groups[base].append(f)

    first_key = sorted(groups.keys())[0]
    post_num = get_post_num(first_key)
    return post_num, sorted(groups[first_key])

def find_specific_group(target):
    """Find files for a specific POST_XXX target."""
    files = sorted(READY.glob(f"{target}*"))
    if not files:
        return None, []
    post_num = get_post_num(files[0].stem)
    return post_num, files

def upload(filepath):
    print(f"    Uploading {filepath.name}...")
    result = cloudinary.uploader.upload(
        str(filepath),
        folder="anastaszianico",
        public_id=filepath.stem,
        overwrite=True,
        resource_type="image"
    )
    return result["secure_url"]

def post_single(image_url, caption):
    """Post a single photo."""
    r = requests.post(
        f"https://graph.instagram.com/v21.0/{USER_ID}/media",
        data={"image_url": image_url, "caption": caption, "access_token": ACCESS_TOKEN}
    )
    data = r.json()
    if "id" not in data:
        raise Exception(f"Container error: {data}")
    container_id = data["id"]

    time.sleep(5)

    r2 = requests.post(
        f"https://graph.instagram.com/v21.0/{USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": ACCESS_TOKEN}
    )
    data2 = r2.json()
    if "id" not in data2:
        raise Exception(f"Publish error: {data2}")
    return data2["id"]

def post_carousel(image_urls, caption):
    """Post multiple photos as a carousel."""
    item_ids = []
    for url in image_urls:
        r = requests.post(
            f"https://graph.instagram.com/v21.0/{USER_ID}/media",
            data={"image_url": url, "is_carousel_item": "true", "access_token": ACCESS_TOKEN}
        )
        data = r.json()
        if "id" not in data:
            raise Exception(f"Carousel item error: {data}")
        item_ids.append(data["id"])
        time.sleep(2)

    r2 = requests.post(
        f"https://graph.instagram.com/v21.0/{USER_ID}/media",
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(item_ids),
            "caption": caption,
            "access_token": ACCESS_TOKEN
        }
    )
    data2 = r2.json()
    if "id" not in data2:
        raise Exception(f"Carousel container error: {data2}")
    carousel_id = data2["id"]

    time.sleep(5)

    r3 = requests.post(
        f"https://graph.instagram.com/v21.0/{USER_ID}/media_publish",
        data={"creation_id": carousel_id, "access_token": ACCESS_TOKEN}
    )
    data3 = r3.json()
    if "id" not in data3:
        raise Exception(f"Carousel publish error: {data3}")
    return data3["id"]

def move_to_posted(files):
    POSTED.mkdir(exist_ok=True)
    for f in files:
        f.rename(POSTED / f.name)

def run(target=None, preview=False):
    print(f"\n=== Anastaszia Nico — Instagram Poster ===")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    if target:
        post_num, files = find_specific_group(target)
    else:
        post_num, files = find_next_group()

    if not files:
        print("  Nothing to post — ready-to-post/ is empty.")
        return

    caption = get_caption(post_num)
    is_carousel = len(files) > 1

    print(f"  Type:    {'Carousel (' + str(len(files)) + ' photos)' if is_carousel else 'Single photo'}")
    print(f"  Files:   {', '.join(f.name for f in files)}")
    print(f"  Caption: {caption[:60]}...")

    if preview:
        print(f"\n  [PREVIEW — not posted]\n\n  Full caption:\n{caption}")
        return

    # Upload all images
    print()
    urls = [upload(f) for f in files]
    time.sleep(2)

    # Post
    if is_carousel:
        print("  Posting carousel...")
        post_id = post_carousel(urls, caption)
    else:
        print("  Posting single photo...")
        post_id = post_single(urls[0], caption)

    move_to_posted(files)

    print(f"\n  ✅ Posted! ID: {post_id}")
    print(f"  instagram.com/anastaszianico\n")

if __name__ == "__main__":
    args = sys.argv[1:]
    preview = "--preview" in args
    args = [a for a in args if a != "--preview"]
    target = args[0] if args else None
    run(target=target, preview=preview)
