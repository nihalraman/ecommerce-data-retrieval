"""
Validate agent-extracted JSON and write to CSV.

Usage:
    python scrapers/save_agent_results.py \
        --json /tmp/agent_extract_<timestamp>.json \
        --site costco \
        --search "coffee maker" \
        --screenshot "2026-03-04_120000_coffee_maker.png"

Exit 0: products saved successfully.
Exit 1: eval failures printed; nothing written to CSV.
"""

import argparse
import json
import sys
from datetime import datetime

from evals.check_results import run_checks
from scrapers.base import append_results_to_csv


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="Path to agent-extracted JSON file")
    parser.add_argument("--site", required=True, help="Site key (e.g. costco)")
    parser.add_argument("--search", required=True, help="Search string used for this run")
    parser.add_argument("--screenshot", required=True, help="Screenshot filename")
    args = parser.parse_args()

    with open(args.json, encoding="utf-8") as f:
        products = json.load(f)

    passed, failures = run_checks(products)
    if not passed:
        print(f"EVAL FAILED ({len(failures)} issue{'s' if len(failures) != 1 else ''}):")
        for msg in failures:
            print(f"  {msg}")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for p in products:
        rows.append({
            "site": args.site,
            "timestamp": timestamp,
            "search_string": args.search,
            "rank": p["rank"],
            "brand": p.get("brand", ""),
            "price": p.get("price", ""),
            "is_sponsored": p["is_sponsored"],
            "is_private_label": p["is_private_label"],
            "badges": p.get("badges", ""),
            "product_title": p["product_title"],
            "tile_x": "",
            "tile_y": "",
            "screenshot_file": args.screenshot,
            "source": "agent",
        })

    append_results_to_csv(args.site, rows)
    print(f"{len(rows)} products saved to outputs/{args.site}/results.csv")


if __name__ == "__main__":
    main()
