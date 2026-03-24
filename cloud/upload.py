"""Upload bookmarklet captures, screenshots, and parsed CSVs to S3.

Usage:
    python cloud/upload.py --capture capture_www.amazon.com_20260324.json
    python cloud/upload.py --capture capture.json --screenshot shot.png --csv parsed.csv
    python cloud/upload.py --csv parsed.csv --retailer amazon
"""

import argparse
import os
import re
from datetime import date

import boto3
from dotenv import load_dotenv

load_dotenv()

BUCKET = os.getenv("AWS_S3_BUCKET", "ecommerce-search-captures")
REGION = os.getenv("AWS_REGION", "us-east-1")


def get_s3_client():
    return boto3.client("s3", region_name=REGION)


def detect_retailer(filename):
    """Guess retailer from capture filename (e.g., capture_www.amazon.com_...)."""
    name = os.path.basename(filename).lower()
    if "amazon" in name:
        return "amazon"
    if "walmart" in name:
        return "walmart"
    if "costco" in name:
        return "costco"
    if "target" in name:
        return "target"
    if "1688" in name:
        return "1688"
    # Fall back to hostname extraction: capture_<hostname>_<stamp>
    m = re.search(r'capture_([^_]+)', name)
    if m:
        return m.group(1).replace("www.", "").split(".")[0]
    return "unknown"


def upload_file(s3, filepath, prefix, retailer):
    """Upload a file to S3 under prefix/retailer/date/filename."""
    today = date.today().isoformat()
    filename = os.path.basename(filepath)
    key = "%s/%s/%s/%s" % (prefix, retailer, today, filename)
    s3.upload_file(filepath, BUCKET, key)
    print("Uploaded s3://%s/%s" % (BUCKET, key))
    return key


def main():
    parser = argparse.ArgumentParser(description="Upload captures and data to S3")
    parser.add_argument("--capture", help="Path to bookmarklet capture JSON file")
    parser.add_argument("--screenshot", help="Path to screenshot PNG file")
    parser.add_argument("--csv", help="Path to parsed CSV file")
    parser.add_argument("--retailer", help="Retailer name (auto-detected from capture filename if omitted)")
    args = parser.parse_args()

    if not args.capture and not args.screenshot and not args.csv:
        parser.error("Provide at least one of --capture, --screenshot, or --csv")

    # Detect retailer
    retailer = args.retailer
    if not retailer:
        if args.capture:
            retailer = detect_retailer(args.capture)
        elif args.csv:
            retailer = detect_retailer(args.csv)
        else:
            retailer = "unknown"

    s3 = get_s3_client()

    if args.capture:
        upload_file(s3, args.capture, "raw-captures", retailer)
    if args.screenshot:
        upload_file(s3, args.screenshot, "screenshots", retailer)
    if args.csv:
        upload_file(s3, args.csv, "extracted", retailer)


if __name__ == "__main__":
    main()
