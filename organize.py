#!/usr/bin/env python3
"""
Organizes Anastaszia Nico's photo folder:
- Removes true duplicates (by MD5 hash)
- Cleans up extension-less copies
- Renames files to clean sequential names
- Generates a posting calendar (every other day from May 2, 2026)
"""

import os
import shutil
import hashlib
from datetime import date, timedelta

BASE = "/Users/leihoutian/Documents/Anastaszia Nico"

FOLDERS = {
    "ready-to-post": os.path.join(BASE, "ready-to-post"),
    "videos":        os.path.join(BASE, "videos"),
    "duplicates":    os.path.join(BASE, "duplicates"),
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov"}

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def setup_folders():
    for folder in FOLDERS.values():
        os.makedirs(folder, exist_ok=True)

def collect_files():
    files = []
    for name in os.listdir(BASE):
        path = os.path.join(BASE, name)
        if os.path.isfile(path) and not name.startswith(".") and name != "organize.py":
            files.append(path)
    return files

def deduplicate(files):
    seen_hashes = {}
    unique = []
    dupes = []

    for path in files:
        h = md5(path)
        if h in seen_hashes:
            dupes.append(path)
        else:
            seen_hashes[h] = path
            unique.append(path)

    return unique, dupes

def move_dupes(dupes):
    for path in dupes:
        dest = os.path.join(FOLDERS["duplicates"], os.path.basename(path))
        shutil.move(path, dest)
        print(f"  [dupe] {os.path.basename(path)}")

def rename_and_sort(unique):
    images = []
    videos = []

    for path in unique:
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        if ext in IMAGE_EXTS:
            images.append(path)
        elif ext in VIDEO_EXTS:
            videos.append(path)
        else:
            # file with no extension — try to detect by content header
            with open(path, "rb") as f:
                header = f.read(12)
            if header[:4] in (b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\xff\xd8\xff\xdb'):
                images.append(path)  # JPEG
            elif header[:8] == b'\x89PNG\r\n\x1a\n':
                images.append(path)  # PNG
            else:
                print(f"  [skip] unknown type: {os.path.basename(path)}")

    # Sort by file modification time (oldest first = natural generation order)
    images.sort(key=lambda p: os.path.getmtime(p))
    videos.sort(key=lambda p: os.path.getmtime(p))

    # Move images with clean names
    for i, path in enumerate(images, start=1):
        _, ext = os.path.splitext(path)
        ext = ext.lower() or ".jpg"
        new_name = f"AN_{i:03d}{ext}"
        dest = os.path.join(FOLDERS["ready-to-post"], new_name)
        shutil.move(path, dest)
        print(f"  [photo] {os.path.basename(path)} → {new_name}")

    # Move videos with clean names
    for i, path in enumerate(videos, start=1):
        _, ext = os.path.splitext(path)
        new_name = f"AN_video_{i:02d}{ext}"
        dest = os.path.join(FOLDERS["videos"], new_name)
        shutil.move(path, dest)
        print(f"  [video] {os.path.basename(path)} → {new_name}")

    return images, videos

def generate_calendar(n_images):
    cal_path = os.path.join(BASE, "content-plan.md")

    # Post 1 was May 2, 2026. Every other day after that.
    first_post = date(2026, 5, 2)
    today = date.today()

    lines = [
        "# Anastaszia Nico — Instagram Content Plan",
        f"**Handle:** @anastaszianico  |  **Frequency:** every other day  |  **Generated:** {today}",
        "",
        "| # | Date | File | Status | Caption idea | Hashtags |",
        "|---|------|------|--------|--------------|---------|",
    ]

    for i in range(1, n_images + 1):
        post_date = first_post + timedelta(days=(i - 1) * 2)
        file_name = f"AN_{i:03d}.jpg"
        status = "✅ posted" if post_date < today else ("📅 next" if post_date == today or post_date == today + timedelta(days=1) else "🔲 queued")
        caption, hashtags = caption_idea(i)
        lines.append(f"| {i} | {post_date.strftime('%b %d')} | `{file_name}` | {status} | {caption} | {hashtags} |")

    lines += [
        "",
        "---",
        "## Notes",
        "- Post between **6–9pm** local time for best Instagram reach",
        "- Mix portrait → lifestyle → fashion → home, then repeat",
        "- Always reply to comments within first 30 min after posting (boosts algorithm)",
        "- Stories: post a story the same day as each feed post to drive profile visits",
        "",
        "## Caption Template",
        "```",
        "[1–2 line caption that sounds personal, lowercase preferred]",
        "",
        "[hashtags on a separate line or hidden in first comment]",
        "```",
    ]

    with open(cal_path, "w") as f:
        f.write("\n".join(lines))

    print(f"\n  [calendar] content-plan.md written ({n_images} posts mapped)")

# Rotate through caption ideas by category pattern: portrait → lifestyle → fashion → home
CAPTIONS = [
    ("two different eyes, one mood 🖤", "#heterochromia #darkaesthetic #altgirl #anastaszianico #aiinfluencer"),
    ("iced coffee is my love language ☕", "#coffeegirl #cafevibes #aesthetic #altlifestyle #anastaszianico"),
    ("this fit lives rent free in my head", "#ootd #altfashion #darkstyle #fashioninspo #anastaszianico"),
    ("slow morning > fast everything else 🌙", "#morningvibes #cozygirl #bedroomaesthetic #anastaszianico"),
    ("no filter needed when the lighting hits right", "#nofilter #naturalbeauty #altgirl #anastaszianico #aimodel"),
    ("somewhere between here and there 🚗", "#carridevibes #dayinmylife #lifestyle #anastaszianico"),
    ("dressed in black because my mood said so", "#allblack #darkfashion #ootd #altgirl #anastaszianico"),
    ("mornings feel different lately ✨", "#morningroutine #cozy #homegirl #anastaszianico"),
]

def caption_idea(post_num):
    idx = (post_num - 1) % len(CAPTIONS)
    return CAPTIONS[idx]

if __name__ == "__main__":
    print("=== Anastaszia Nico — Folder Organizer ===\n")

    setup_folders()
    files = collect_files()
    print(f"Found {len(files)} files total.\n")

    print("Step 1: Deduplicating...")
    unique, dupes = deduplicate(files)
    print(f"  {len(dupes)} duplicate(s) found, {len(unique)} unique files.\n")

    if dupes:
        print("Moving duplicates...")
        move_dupes(dupes)
        print()

    print("Step 2: Sorting and renaming...")
    images, videos = rename_and_sort(unique)
    print()

    print("Step 3: Generating content calendar...")
    generate_calendar(len(images))

    print("\n=== Done ===")
    print(f"  Photos ready to post: {len(images)}")
    print(f"  Videos:               {len(videos)}")
    days_of_content = len(images) * 2
    print(f"  Content runway:       ~{days_of_content} days ({days_of_content // 30} months)")
    print(f"\n  Open: {BASE}/content-plan.md")
