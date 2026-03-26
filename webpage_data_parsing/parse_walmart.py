"""Parse Walmart.com search results page HTML into structured CSV.

Usage:
    python webpage_data_parsing/parse_walmart.py --category "Coffee Maker" capture.json
    python webpage_data_parsing/parse_walmart.py --category "Coffee Maker" --page 1 --output results.csv page.html
"""

import argparse
import csv
import json
import os
import re
import sys
from bs4 import BeautifulSoup

RETAILER = "Walmart"

BRAND_CANONICAL = {
    "great value": "Great Value",
    "equate": "Equate",
    "mainstays": "Mainstays",
    "parent's choice": "Parent's Choice",
    "sam's choice": "Sam's Choice",
    "spring valley": "Spring Valley",
    "ol' roy": "ol' Roy",
    "special kitty": "Special Kitty",
    "george": "George",
    "no boundaries": "No Boundaries",
    "athletic works": "Athletic Works",
    "time and tru": "Time and Tru",
    "wonder nation": "Wonder Nation",
    "pen+gear": "Pen+Gear",
    "vibrant life": "Vibrant Life",
}

PRIVATE_LABEL_BRANDS = [
    "Great Value", "Equate", "Mainstays", "Parent's Choice",
    "Sam's Choice", "Spring Valley", "ol' Roy", "Special Kitty",
    "George", "No Boundaries", "Athletic Works", "Time and Tru",
    "Wonder Nation", "Pen+Gear", "Vibrant Life",
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
    """Extract brand from Walmart product title.

    Walmart titles sometimes follow "Brand - Product Description" or
    just lead with the brand name.
    """
    if not title:
        return ""
    # Check for "Brand - Description" pattern
    parts = title.split(" - ", 1)
    if len(parts) == 2:
        candidate = parts[0].strip()
        # If the first part is short (1-3 words), it's likely the brand
        if len(candidate.split()) <= 3:
            canonical = BRAND_CANONICAL.get(candidate.lower())
            return canonical if canonical else candidate

    # Fall back to first 1-3 words before generic terms
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
    """Check if brand is a Walmart private label."""
    if not brand:
        return False
    return any(pl.lower() in brand.lower() for pl in PRIVATE_LABEL_BRANDS)


def _is_in_carousel(tile):
    """Check if a product tile is inside a carousel section."""
    parent = tile.parent
    for _ in range(10):
        if not parent:
            break
        classes = " ".join(parent.get("class", []))
        if "carousel" in classes.lower():
            return True
        role = parent.get("role", "")
        if role == "group":
            # Walmart carousels often use role="group"
            carousel_label = parent.get("aria-label", "").lower()
            if "related" in carousel_label or "similar" in carousel_label:
                return True
        parent = parent.parent
    return False


def _parse_soup(soup, category, page=1):
    """Core extraction logic operating on a BeautifulSoup object."""
    # Walmart uses data-item-id on product tiles
    all_tiles = soup.select("div[data-item-id]")
    tiles = [t for t in all_tiles if not _is_in_carousel(t)]

    if not tiles:
        print("Warning: no product tiles found", file=sys.stderr)
        return []

    rows = []
    seen_ids = set()
    for tile in tiles:
        # Deduplicate by item ID
        item_id = tile.get("data-item-id", "")
        if item_id:
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)

        rank = len(rows) + 1

        # Title
        title_el = tile.select_one('span[data-automation-id="product-title"]')
        if not title_el:
            title_el = tile.select_one("span.lh-title")
        title = title_el.get_text(strip=True) if title_el else ""

        # Price
        price = ""
        price_el = tile.select_one('div[data-automation-id="product-price"]')
        if price_el:
            price_text = price_el.get_text(strip=True)
            price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
            if price_match:
                price = float(price_match.group(1).replace(",", ""))

        # Brand — Walmart sometimes shows brand as a separate link/span above title
        brand = ""
        brand_el = tile.select_one('span[data-automation-id="product-brand"]')
        if brand_el:
            brand = brand_el.get_text(strip=True)
        if not brand:
            brand = parse_brand_from_title(title)
        canonical = BRAND_CANONICAL.get(brand.lower())
        if canonical:
            brand = canonical

        # Size
        size = parse_size_from_title(title)

        # Rating
        rating = ""
        rating_el = tile.select_one('span[data-automation-id="product-ratings"]')
        if not rating_el:
            rating_el = tile.select_one("span.w_Cs")
        if rating_el:
            # Look for aria-label like "Rating: 4.5 out of 5 stars"
            aria = rating_el.get("aria-label", "")
            rm = re.search(r'([\d.]+)\s*out of', aria)
            if rm:
                rating = float(rm.group(1))
            else:
                text = rating_el.get_text(strip=True)
                rm = re.search(r'([\d.]+)', text)
                if rm:
                    rating = float(rm.group(1))

        # Review count
        num_reviews = ""
        # Walmart typically shows review count near the rating
        reviews_el = tile.select_one('span[data-automation-id="product-reviews"]')
        if reviews_el:
            rvm = re.search(r'([\d,]+)', reviews_el.get_text(strip=True))
            if rvm:
                num_reviews = int(rvm.group(1).replace(",", ""))

        # Sponsored
        is_sponsored = 0
        ad_el = tile.select_one("div[data-ad-id]")
        if ad_el:
            is_sponsored = 1
        if not is_sponsored:
            # Check for "Sponsored" text in the tile
            tile_text = tile.get_text(separator=" ")
            if re.search(r'\bSponsored\b', tile_text):
                is_sponsored = 1

        # Badges / merchandising tags
        remarks_parts = []
        has_merch_tag = 0
        # "Best seller", "Popular pick", "Rollback" badges
        badge_els = tile.select("span.w_DP, span.w_Cs")
        for badge in badge_els:
            text = badge.get_text(strip=True)
            if text and text.lower() in ("best seller", "popular pick", "rollback",
                                          "reduced price", "clearance", "new"):
                remarks_parts.append(text)
                has_merch_tag = 1
        # Fallback: look for common badge class patterns
        badge_generic = tile.select("[class*='badge'], [class*='Badge'], [class*='flag'], [class*='Flag']")
        for badge in badge_generic:
            text = badge.get_text(strip=True)
            if text and text not in remarks_parts and len(text) < 50:
                remarks_parts.append(text)
                has_merch_tag = 1
        # Rollback / savings info
        savings_el = tile.select_one("[data-automation-id='product-savings']")
        if savings_el:
            savings_text = savings_el.get_text(strip=True)
            if savings_text and savings_text not in remarks_parts:
                remarks_parts.append(savings_text)

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


def parse_html(html_path, category, page=1):
    """Parse Walmart HTML file and return list of product dicts."""
    html = load_html(html_path)
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        script.decompose()
    return _parse_soup(soup, category, page)


def parse_html_string(html, category, page=1):
    """Parse raw HTML string (no file I/O). Used by server.py."""
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        script.decompose()
    return _parse_soup(soup, category, page)


def main():
    parser = argparse.ArgumentParser(
        description="Parse Walmart.com HTML into product CSV"
    )
    parser.add_argument("html_file", help="Path to saved .html or bookmarklet .json file")
    parser.add_argument("--category", required=True, help="Product category name")
    parser.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    parser.add_argument("--output", "-o", help="Output CSV path (default: walmart_parsed.csv)")
    args = parser.parse_args()

    rows = parse_html(args.html_file, args.category, args.page)

    if args.output:
        output_path = args.output
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "walmart_parsed.csv")

    with open(output_path, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print("Wrote %d products to %s" % (len(rows), output_path), file=sys.stderr)


if __name__ == "__main__":
    main()
