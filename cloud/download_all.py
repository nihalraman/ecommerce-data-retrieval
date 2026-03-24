"""Download and concatenate all extracted CSVs from S3 into a single local file.

Usage:
    python cloud/download_all.py --retailer amazon --output amazon_all_results.csv
    python cloud/download_all.py --output all_results.csv
"""

import argparse
import csv
import io
import os

import boto3
from dotenv import load_dotenv

load_dotenv()

BUCKET = os.getenv("AWS_S3_BUCKET", "ecommerce-search-captures")
REGION = os.getenv("AWS_REGION", "us-east-1")


def get_s3_client():
    return boto3.client("s3", region_name=REGION)


def list_csv_keys(s3, retailer=None):
    """List all CSV file keys under extracted/ prefix."""
    prefix = "extracted/%s/" % retailer if retailer else "extracted/"
    keys = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".csv"):
                keys.append(obj["Key"])
    return sorted(keys)


def download_and_concatenate(s3, keys, output_path):
    """Download all CSVs and write them as a single file with one header."""
    header_written = False
    row_count = 0

    with open(output_path, "w", newline="", encoding="utf-8") as out:
        writer = None
        for key in keys:
            response = s3.get_object(Bucket=BUCKET, Key=key)
            body = response["Body"].read().decode("utf-8")
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
        description="Download all extracted CSVs from S3 into one file"
    )
    parser.add_argument("--retailer", help="Filter by retailer (e.g., amazon, walmart)")
    parser.add_argument("--output", "-o", required=True, help="Output CSV file path")
    args = parser.parse_args()

    s3 = get_s3_client()
    keys = list_csv_keys(s3, args.retailer)

    if not keys:
        prefix = "extracted/%s/" % args.retailer if args.retailer else "extracted/"
        print("No CSV files found under s3://%s/%s" % (BUCKET, prefix))
        return

    print("Found %d CSV files, downloading..." % len(keys))
    row_count = download_and_concatenate(s3, keys, args.output)
    print("Wrote %d rows to %s" % (row_count, args.output))


if __name__ == "__main__":
    main()
