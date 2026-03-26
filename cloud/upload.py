"""Upload bookmarklet captures, screenshots, and parsed CSVs to Dropbox.

Usage:
    python cloud/upload.py --website amazon --category "coffee maker" \
        --capture capture.json --screenshot shot.png --csv parsed.csv
"""

import argparse
import os
from datetime import datetime

import dropbox
from dotenv import load_dotenv

load_dotenv()

DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN", "")
DROPBOX_BASE_PATH = "/CM in China/ECommerce Project"


def get_dropbox_client():
    if not DROPBOX_ACCESS_TOKEN:
        raise RuntimeError("DROPBOX_ACCESS_TOKEN not set in environment")
    return dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)


def capitalize_site(website):
    """Map website key to capitalized Dropbox subdirectory name."""
    if website.isdigit():
        return website  # e.g. "1688" stays as-is
    return website.capitalize()


def build_base_name(website, category):
    """Build the shared base name: {website}_{category}_{YYYY-MM-DD}T{HH-mm-ss}."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M-%S")
    cat = category.lower().replace(" ", "-")
    return "%s_%s_%sT%s" % (website.lower(), cat, date_str, time_str)


def upload_file(dbx, local_path, dropbox_path):
    """Upload a single file to Dropbox."""
    with open(local_path, "rb") as f:
        dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
    print("Uploaded %s" % dropbox_path)


def main():
    parser = argparse.ArgumentParser(description="Upload captures and data to Dropbox")
    parser.add_argument("--capture", help="Path to bookmarklet capture JSON file")
    parser.add_argument("--screenshot", help="Path to screenshot image file (PNG or JPEG)")
    parser.add_argument("--csv", help="Path to parsed CSV file")
    parser.add_argument("--website", required=True, help="Website name (e.g. amazon, walmart)")
    parser.add_argument("--category", required=True, help="Product category (e.g. 'coffee maker')")
    args = parser.parse_args()

    if not args.capture and not args.screenshot and not args.csv:
        parser.error("Provide at least one of --capture, --screenshot, or --csv")

    dbx = get_dropbox_client()
    site_dir = capitalize_site(args.website)
    base_name = build_base_name(args.website, args.category)
    folder_path = "%s/%s/%s" % (DROPBOX_BASE_PATH, site_dir, base_name)

    screenshot_ext = os.path.splitext(args.screenshot)[1] if args.screenshot else ".jpg"
    file_map = {
        args.capture: ".json",
        args.screenshot: screenshot_ext,
        args.csv: ".csv",
    }

    for local_path, ext in file_map.items():
        if local_path:
            dropbox_path = "%s/%s%s" % (folder_path, base_name, ext)
            upload_file(dbx, local_path, dropbox_path)


if __name__ == "__main__":
    main()
