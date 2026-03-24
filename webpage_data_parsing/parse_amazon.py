"""Parse Amazon.com search results page HTML into structured CSV.

Usage:
    python webpage_data_parsing/parse_amazon.py --category "Coffee Maker" capture.json
    python webpage_data_parsing/parse_amazon.py --category "Coffee Maker" --page 1 --output results.csv page.html
"""

import argparse
import csv
import json
import os
import re
import sys
from bs4 import BeautifulSoup

RETAILER = "Amazon"

BRAND_CANONICAL = {
    "amazon basics": "Amazon Basics",
    "amazonbasics": "Amazon Basics",
    "amazon essentials": "Amazon Essentials",
    "amazon commercial": "Amazon Commercial",
    "solimo": "Solimo",
    "presto!": "Presto!",
    "happy belly": "Happy Belly",
    "mama bear": "Mama Bear",
    "amazon elements": "Amazon Elements",
    "wickedly prime": "Wickedly Prime",
    "365 by whole foods market": "365 by Whole Foods Market",
    "whole foods market": "365 by Whole Foods Market",
}

PRIVATE_LABEL_BRANDS = [
    "Amazon Basics", "Amazon Essentials", "Amazon Commercial",
    "Solimo", "Presto!", "Happy Belly", "Mama Bear",
    "Amazon Elements", "Wickedly Prime", "365 by Whole Foods Market",
]

GRID_COLS = 4

CSV_COLUMNS = [
    "Retailer", "Product Category", "Product Description", "Brand",
    "Price", "Size", "Rating", "# of Reviews", "Page",
    "Row (top to bottom)", "Column (left to right)",
    "Private Label (Yes: 1, No: 0)", "Sponsored (Yes:1 , No:0)",
    "Merchandising Tag (Yes: 1, No:0)", "Remarks",
]


def load_html(filepath):
    """Load HTML from a .json bookmarklet capture or a raw .html file."""
    if filepath.endswith(".json"):
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        return data["html"]
    with open(filepath, encoding="utf-8") as f:
        return f.read()


def parse_brand_from_title(title):
    """Extract brand from Amazon product title.

    Amazon titles often start with the brand name, e.g.:
      "Keurig K-Classic Coffee Maker..."
      "BLACK+DECKER 12-Cup Digital Coffee Maker..."
    """
    if not title:
        return ""
    # Amazon titles typically lead with brand — take first 1-3 words
    # before generic product terms
    words = title.split()
    brand_words = []
    generic = {
        "coffee", "maker", "machine", "brewer", "pot", "filter",
        "single", "serve", "cup", "with", "for", "and", "the",
        "portable", "programmable", "automatic", "electric", "digital",
        "stainless", "steel", "thermal", "drip", "iced", "hot", "cold",
        "12-cup", "10-cup", "5-cup", "4-cup", "2-pack", "3-pack",
    }
    for w in words:
        clean = w.lower().rstrip("™®,")
        if clean in generic:
            break
        if re.match(r'\d+(?:oz|pk|pack|fl|gal|l|ml|ct|cup)\b', clean, re.IGNORECASE):
            break
        brand_words.append(w.rstrip("™®"))
        if len(brand_words) >= 3:
            break
    brand = " ".join(brand_words) if brand_words else ""
    # Normalize to canonical casing
    canonical = BRAND_CANONICAL.get(brand.lower())
    if canonical:
        return canonical
    first_word = brand.split()[0].lower() if brand else ""
    canonical_first = BRAND_CANONICAL.get(first_word)
    if canonical_first:
        return canonical_first
    return brand


def parse_size_from_title(title):
    """Extract size/quantity info from product title."""
    m = re.search(
        r'(\d+\s*(?:pack|pk|count|ct))?[/\s]*'
        r'(\d+(?:\.\d+)?\s*(?:fl\s*oz|oz|gal|gallon|l|liter|litre|ml|ct|count))',
        title, re.IGNORECASE
    )
    if m:
        parts = [p.strip() for p in m.groups() if p]
        return "/".join(parts)
    return ""


def is_private_label(brand):
    """Check if brand is an Amazon private label."""
    if not brand:
        return False
    return any(pl.lower() in brand.lower() for pl in PRIVATE_LABEL_BRANDS)


def _is_in_carousel(tile):
    """Check if a search result is inside a carousel (Related, Highly Rated, etc.)."""
    parent = tile.parent
    for _ in range(10):
        if not parent:
            break
        classes = " ".join(parent.get("class", []))
        if "carousel" in classes.lower() or "widget-content" in classes.lower():
            return True
        parent = parent.parent
    return False


def parse_html(html_path, category, page=1):
    """Parse Amazon HTML file and return list of product dicts."""
    html = load_html(html_path)

    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        script.decompose()

    # Amazon search result tiles have data-component-type="s-search-result"
    all_tiles = soup.select('div[data-component-type="s-search-result"]')
    tiles = [t for t in all_tiles if not _is_in_carousel(t)]
    if not tiles:
        print("Warning: no product tiles found in %s" % html_path, file=sys.stderr)
        return []

    rows = []
    seen_asins = set()
    for tile in tiles:
        # Deduplicate by ASIN
        asin = tile.get("data-asin", "")
        if asin:
            if asin in seen_asins:
                continue
            seen_asins.add(asin)

        rank = len(rows) + 1

        # Title
        title_el = tile.select_one("h2 a span")
        title = title_el.get_text(strip=True) if title_el else ""

        # Price — Amazon uses span.a-offscreen inside span.a-price for accessible price text
        price = ""
        price_el = tile.select_one("span.a-price span.a-offscreen")
        if price_el:
            price_text = price_el.get_text(strip=True)
            price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
            if price_match:
                price = float(price_match.group(1).replace(",", ""))

        # Brand — Amazon sometimes has a separate brand line, otherwise parse from title
        brand = ""
        brand_el = tile.select_one("span.a-size-base-plus.a-color-base")
        if brand_el:
            brand = brand_el.get_text(strip=True)
        if not brand:
            brand = parse_brand_from_title(title)
        # Normalize
        canonical = BRAND_CANONICAL.get(brand.lower())
        if canonical:
            brand = canonical

        # Size
        size = parse_size_from_title(title)

        # Rating
        rating = ""
        rating_el = tile.select_one("span.a-icon-alt")
        if rating_el:
            rm = re.search(r'([\d.]+)\s*out of', rating_el.get_text(strip=True))
            if rm:
                rating = float(rm.group(1))

        # Review count
        num_reviews = ""
        reviews_el = tile.select_one("span.a-size-base.s-underline-text")
        if reviews_el:
            rvm = re.search(r'([\d,]+)', reviews_el.get_text(strip=True))
            if rvm:
                num_reviews = int(rvm.group(1).replace(",", ""))

        # Sponsored — check for sponsored label or sponsored result component
        is_sponsored = 0
        sponsored_el = tile.select_one("span.puis-label-popover-default")
        if sponsored_el and "sponsor" in sponsored_el.get_text(strip=True).lower():
            is_sponsored = 1
        if not is_sponsored:
            sp_attr = tile.get("data-component-type", "")
            if "sp-sponsored" in sp_attr:
                is_sponsored = 1

        # Badges / merchandising tags
        remarks_parts = []
        has_merch_tag = 0
        # Best Seller, Amazon's Choice, etc.
        badge_els = tile.select("span.a-badge-text")
        for badge in badge_els:
            text = badge.get_text(strip=True)
            if text:
                remarks_parts.append(text)
                has_merch_tag = 1
        # data-a-badge-type badges
        badge_type_els = tile.select("span[data-a-badge-type]")
        for badge in badge_type_els:
            text = badge.get_text(strip=True)
            if text and text not in remarks_parts:
                remarks_parts.append(text)
                has_merch_tag = 1
        # "Limited time deal" and similar labels
        deal_el = tile.select_one("span.a-color-secondary:-soup-contains('deal')")
        if not deal_el:
            deal_el = tile.select_one("span[data-a-color='secondary']")
        if deal_el:
            deal_text = deal_el.get_text(strip=True)
            if "deal" in deal_text.lower() and deal_text not in remarks_parts:
                remarks_parts.append(deal_text)
                has_merch_tag = 1

        rows.append({
            "Retailer": RETAILER,
            "Product Category": category,
            "Product Description": title,
            "Brand": brand,
            "Price": price,
            "Size": size,
            "Rating": rating,
            "# of Reviews": num_reviews,
            "Page": page,
            "Row (top to bottom)": ((rank - 1) // GRID_COLS) + 1,
            "Column (left to right)": ((rank - 1) % GRID_COLS) + 1,
            "Private Label (Yes: 1, No: 0)": 1 if is_private_label(brand) else 0,
            "Sponsored (Yes:1 , No:0)": is_sponsored,
            "Merchandising Tag (Yes: 1, No:0)": has_merch_tag,
            "Remarks": "; ".join(remarks_parts),
        })

    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Parse Amazon.com HTML into product CSV"
    )
    parser.add_argument("html_file", help="Path to saved .html or bookmarklet .json file")
    parser.add_argument("--category", required=True, help="Product category name")
    parser.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    parser.add_argument("--output", "-o", help="Output CSV path (default: amazon_parsed.csv)")
    args = parser.parse_args()

    rows = parse_html(args.html_file, args.category, args.page)

    if args.output:
        output_path = args.output
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "amazon_parsed.csv")

    with open(output_path, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print("Wrote %d products to %s" % (len(rows), output_path), file=sys.stderr)


if __name__ == "__main__":
    main()
