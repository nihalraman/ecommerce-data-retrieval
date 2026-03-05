"""
Deterministic eval checks for agent-extracted product data.
No network calls, no LLM — pure validation logic.

Usage:
    python -m evals.check_results /tmp/agent_extract_<timestamp>.json
    Exit 0 = all pass. Exit 1 = failures printed with codes.
"""

import json
import re
import sys

REQUIRED_KEYS = {"rank", "product_title", "brand", "price", "is_sponsored", "is_private_label", "badges"}


def run_checks(products: list[dict]) -> tuple[bool, list[str]]:
    failures = []

    # SCHEMA — all required keys present
    for i, p in enumerate(products):
        missing = REQUIRED_KEYS - p.keys()
        if missing:
            failures.append(f"[SCHEMA] Product at index {i} missing keys: {sorted(missing)}")

    # RANK_INTEGRITY — sequential 1..N, no gaps, no duplicates
    ranks = [p.get("rank") for p in products if "rank" in p]
    if ranks:
        sorted_ranks = sorted(ranks)
        expected = list(range(1, len(ranks) + 1))
        if sorted_ranks != expected:
            failures.append(f"[RANK_INTEGRITY] Ranks {sorted_ranks} are not sequential 1..{len(ranks)}")

    # EMPTY_TITLE — all product_title values non-empty
    for p in products:
        if "product_title" in p and not (isinstance(p["product_title"], str) and p["product_title"].strip()):
            failures.append(f"[EMPTY_TITLE] product_title is empty at rank {p.get('rank', '?')}")

    # DUPE_TITLE — no two products share the same product_title
    titles = [p["product_title"] for p in products if isinstance(p.get("product_title"), str) and p["product_title"].strip()]
    seen = set()
    for p in products:
        title = p.get("product_title", "")
        if title and title in seen:
            failures.append(f"[DUPE_TITLE] Duplicate product_title '{title}' at rank {p.get('rank', '?')}")
        seen.add(title)

    # PRICE_FORMAT — non-empty prices must contain at least one digit
    for p in products:
        price = p.get("price", "")
        if isinstance(price, str) and price and not re.search(r"\d", price):
            failures.append(f"[PRICE_FORMAT] price '{price}' at rank {p.get('rank', '?')} contains no digits")

    # BOOLEAN_TYPE — is_sponsored and is_private_label must be actual booleans
    for p in products:
        for field in ("is_sponsored", "is_private_label"):
            val = p.get(field)
            if field in p and not isinstance(val, bool):
                failures.append(f"[BOOLEAN_TYPE] {field} is {type(val).__name__} {val!r} at rank {p.get('rank', '?')} (must be boolean)")
                

    passed = len(failures) == 0
    return passed, failures


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m evals.check_results <path_to_json>", file=sys.stderr)
        sys.exit(2)

    with open(sys.argv[1], encoding="utf-8") as f:
        products = json.load(f)

    passed, failures = run_checks(products)

    if passed:
        print(f"All checks passed ({len(products)} products).")
        sys.exit(0)
    else:
        print(f"EVAL FAILED ({len(failures)} issue{'s' if len(failures) != 1 else ''}):")
        for msg in failures:
            print(f"  {msg}")
        sys.exit(1)
