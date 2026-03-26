"""Download and concatenate all extracted CSVs from Dropbox into a single local file.

Usage:
    python cloud/download_all.py --website amazon --output amazon_all_results.csv
    python cloud/download_all.py --output all_results.csv
"""

import argparse
import csv
import io
import os

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
    if website.isdigit():
        return website
    return website.capitalize()


def list_csv_files(dbx, website=None):
    """Recursively list all .csv files under the base path (optionally filtered by website)."""
    search_path = DROPBOX_BASE_PATH
    if website:
        search_path = "%s/%s" % (DROPBOX_BASE_PATH, capitalize_site(website))

    csv_paths = []
    try:
        result = dbx.files_list_folder(search_path, recursive=True)
    except dropbox.exceptions.ApiError:
        return csv_paths

    while True:
        for entry in result.entries:
            if isinstance(entry, dropbox.files.FileMetadata) and entry.name.endswith(".csv"):
                csv_paths.append(entry.path_display)
        if not result.has_more:
            break
        result = dbx.files_list_folder_continue(result.cursor)

    return sorted(csv_paths)


def download_and_concatenate(dbx, paths, output_path):
    """Download all CSVs and write them as a single file with one header."""
    header_written = False
    row_count = 0

    with open(output_path, "w", newline="", encoding="utf-8") as out:
        writer = None
        for path in paths:
            _, response = dbx.files_download(path)
            body = response.content.decode("utf-8")
            reader = csv.DictReader(io.StringIO(body))

            if not header_written:
                fieldnames = reader.fieldnames
                if not fieldnames:
                    continue
                writer = csv.DictWriter(out, fieldnames=fieldnames)
                writer.writeheader()
                header_written = True

            for row in reader:
                writer.writerow(row)
                row_count += 1

    return row_count


def main():
    parser = argparse.ArgumentParser(
        description="Download all extracted CSVs from Dropbox into one file"
    )
    parser.add_argument("--website", help="Filter by website (e.g., amazon, walmart)")
    parser.add_argument("--output", "-o", required=True, help="Output CSV file path")
    args = parser.parse_args()

    dbx = get_dropbox_client()
    paths = list_csv_files(dbx, args.website)

    if not paths:
        search_path = DROPBOX_BASE_PATH
        if args.website:
            search_path = "%s/%s" % (DROPBOX_BASE_PATH, capitalize_site(args.website))
        print("No CSV files found under %s" % search_path)
        return

    print("Found %d CSV files, downloading..." % len(paths))
    row_count = download_and_concatenate(dbx, paths, args.output)
    print("Wrote %d rows to %s" % (row_count, args.output))


if __name__ == "__main__":
    main()
