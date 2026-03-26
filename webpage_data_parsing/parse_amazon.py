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
    "arm & hammer": "ARM & HAMMER",
    "arm &amp; hammer": "ARM & HAMMER",
}

# Known brand names to match at the start of titles (longest-first matching).
# This prevents sub-brand words from being absorbed into the brand.
KNOWN_BRANDS = [
    "ARM & HAMMER", "Amazon Basics", "Amazon Essentials", "Amazon Commercial",
    "Seventh Generation", "The Laundress", "The Clean People",
    "Mrs. Meyer's", "365 by Whole Foods Market",
    "Tide", "Gain", "Persil", "All", "Downy", "OxiClean", "Dreft",
    "Purex", "Era", "Foca", "Snuggle", "Ecos", "Method", "DedCool",
    "ATTITUDE", "HEX", "Soulink", "Sudstainables", "Tyler",
    "Keurig", "BLACK+DECKER", "Cuisinart", "Hamilton Beach", "Ninja",
    "Mr. Coffee", "Breville", "De'Longhi", "Nespresso", "Bonavita",
]

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

    Uses KNOWN_BRANDS for exact prefix matching first, then falls back
    to heuristic word extraction.
    """
    if not title:
        return ""
    title_lower = title.lower()

    # 1) Check known brands (case-insensitive prefix match)
    for brand in sorted(KNOWN_BRANDS, key=len, reverse=True):
        if title_lower.startswith(brand.lower()):
            after = title[len(brand):]
            # Must be followed by space, punctuation, or end of string
            if not after or after[0] in " ,|-–—:;":
                canonical = BRAND_CANONICAL.get(brand.lower())
                return canonical if canonical else brand

    # 2) Fallback: take first 1-2 words before generic product terms
    words = title.split()
    brand_words = []
    generic = {
        "coffee", "maker", "machine", "brewer", "pot", "filter",
        "single", "serve", "cup", "with", "for", "and",
        "portable", "programmable", "automatic", "electric", "digital",
        "stainless", "steel", "thermal", "drip", "iced", "hot", "cold",
        "laundry", "detergent", "liquid", "pods", "pacs", "fabric",
        "softener", "stain", "remover", "booster", "scent", "fresh",
        "clean", "free", "gentle", "original", "he", "high", "efficiency",
        "loads", "wash", "concentrated", "plant-based", "hypoallergenic",
        "natural", "organic", "biodegradable", "non-toxic",
        "plus", "ultra", "simply", "powder", "flings!", "odor",
        "gallon", "super", "oxi", "purclean", "4-in-1",
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
        r'(\d+(?:\.\d+)?\s*(?:fl\s*oz|oz|gal|gallon|liter|litre|ml|ct|count|loads?|lb|lbs)\b)',
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
        comp = parent.get("data-component-type", "")
        if comp in ("s-searchgrid-carousel", "s-impression-logger"):
            return True
        classes = " ".join(parent.get("class", []))
        if "carousel" in classes.lower() or "widget-content" in classes.lower():
            return True
        parent = parent.parent
    return False


def _parse_soup(soup, category, page=1):
    """Core extraction logic operating on a BeautifulSoup object."""
    # Amazon search result tiles have data-component-type="s-search-result"
    all_tiles = soup.select('div[data-component-type="s-search-result"]')
    # Only keep tiles that have a product faceout (data-cy) and are not in carousels
    tiles = [
        t for t in all_tiles
        if t.select_one('[data-cy="asin-faceout-container"]') and not _is_in_carousel(t)
    ]
    if not tiles:
        print("Warning: no product tiles found", file=sys.stderr)
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

        # Title — use data-cy="title-recipe" container, fall back to h2
        title = ""
        title_recipe = tile.select_one('[data-cy="title-recipe"]')
        if title_recipe:
            title_el = title_recipe.select_one("h2")
            title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            title_el = tile.select_one("h2 a span") or tile.select_one("h2 span")
            title = title_el.get_text(strip=True) if title_el else ""

        # Price — use data-cy="price-recipe" container, fall back to span.a-price
        price = ""
        price_recipe = tile.select_one('[data-cy="price-recipe"]')
        price_container = price_recipe if price_recipe else tile
        price_el = price_container.select_one("span.a-price span.a-offscreen")
        if price_el:
            price_text = price_el.get_text(strip=True)
            price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
            if price_match:
                price = float(price_match.group(1).replace(",", ""))

        # Brand — try dedicated brand element, but exclude badge text
        brand = ""
        badge_keywords = {"choice", "pick", "seller", "best", "overall", "amazon's"}
        brand_el = tile.select_one("span.a-size-base-plus.a-color-base")
        if brand_el:
            candidate = brand_el.get_text(strip=True)
            if not any(kw in candidate.lower() for kw in badge_keywords):
                brand = candidate
        if not brand:
            brand = parse_brand_from_title(title)
        # Normalize
        canonical = BRAND_CANONICAL.get(brand.lower())
        if canonical:
            brand = canonical

        # Size — try DOM element first (e.g. "80 Fl Oz (Pack of 1)"), then title
        size = ""
        for span in tile.select("span.a-size-base"):
            stxt = span.get_text(strip=True)
            if re.match(
                r'^\d+(?:\.\d+)?\s*(?:fl\s*oz|oz|gal|l|ml|ct|count|loads?)\b',
                stxt, re.IGNORECASE
            ):
                size = stxt
                break
        if not size:
            size = parse_size_from_title(title)

        # Rating — use data-cy="reviews-ratings-slot", fall back to span.a-icon-alt
        rating = ""
        ratings_slot = tile.select_one('[data-cy="reviews-ratings-slot"]')
        rating_container = ratings_slot if ratings_slot else tile
        rating_el = rating_container.select_one("span.a-icon-alt")
        if rating_el:
            rm = re.search(r'([\d.]+)\s*out of', rating_el.get_text(strip=True))
            if rm:
                rating = float(rm.group(1))

        # Review count — use data-cy="reviews-block", format may be "(4.5K)" or "(1,234)"
        num_reviews = ""
        reviews_block = tile.select_one('[data-cy="reviews-block"]')
        reviews_container = reviews_block if reviews_block else tile
        reviews_el = reviews_container.select_one("span.s-underline-text")
        if reviews_el:
            rev_text = reviews_el.get_text(strip=True)
            km = re.search(r'([\d.]+)\s*[Kk]', rev_text)
            if km:
                num_reviews = int(float(km.group(1)) * 1000)
            else:
                rvm = re.search(r'([\d,]+)', rev_text)
                if rvm:
                    num_reviews = int(rvm.group(1).replace(",", ""))

        # Sponsored — check for sponsored label, AdHolder class, or component type
        is_sponsored = 0
        sponsored_el = tile.select_one("span.puis-label-popover-default")
        if sponsored_el and "sponsor" in sponsored_el.get_text(strip=True).lower():
            is_sponsored = 1
        if not is_sponsored:
            tile_classes = " ".join(tile.get("class", []))
            if "AdHolder" in tile_classes:
                is_sponsored = 1
        if not is_sponsored:
            sp_attr = tile.get("data-component-type", "")
            if "sp-sponsored" in sp_attr:
                is_sponsored = 1

        # Badges / merchandising tags
        remarks_parts = []
        has_merch_tag = 0
        seen_badges = set()

        def _add_badge(text):
            nonlocal has_merch_tag
            if not text:
                return
            for existing in list(seen_badges):
                if text in existing or existing in text:
                    return
            seen_badges.add(text)
            article = "an" if text[0] in "AEIOUaeiou" else "a"
            remarks_parts.append('Has %s "%s" badge (merchandising tag)' % (article, text))
            has_merch_tag = 1

        # Best Seller, Amazon's Choice, Overall Pick — badge spans
        badge_els = tile.select("span.a-badge-text")
        for badge in badge_els:
            _add_badge(badge.get_text(strip=True))
        badge_type_els = tile.select("span[data-a-badge-type]")
        for badge in badge_type_els:
            text = badge.get_text(strip=True)
            if text:
                _add_badge(text)
        # Badge text from non-badge spans (Amazon's Choice / Overall Pick)
        for span in tile.select("span.a-size-base-plus.a-color-base"):
            text = span.get_text(strip=True)
            if any(kw in text.lower() for kw in ("choice", "pick", "seller")):
                already = any(text in s or s in text for s in seen_badges)
                if not already:
                    _add_badge(text)
        # "Limited time deal" and similar labels
        for span in tile.select("span"):
            text = span.get_text(strip=True)
            if "deal" in text.lower() and len(text) < 50 and text not in seen_badges:
                seen_badges.add(text)
                remarks_parts.append('Has a "%s" label (merchandising tag)' % text)
                has_merch_tag = 1
        # Climate Pledge Friendly — via data-cy="certification-recipe" or text match
        cert_recipe = tile.select_one('[data-cy="certification-recipe"]')
        if cert_recipe:
            cert_text = cert_recipe.get_text(strip=True)
            if "climate pledge" in cert_text.lower() and "Climate Pledge Friendly" not in seen_badges:
                seen_badges.add("Climate Pledge Friendly")
                remarks_parts.append('Has a "Climate Pledge Friendly" badge (merchandising tag)')
                has_merch_tag = 1
        if "Climate Pledge Friendly" not in seen_badges:
            for span in tile.select("span"):
                text = span.get_text(strip=True)
                if "climate pledge" in text.lower():
                    seen_badges.add("Climate Pledge Friendly")
                    remarks_parts.append('Has a "Climate Pledge Friendly" badge (merchandising tag)')
                    has_merch_tag = 1
                    break

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
    """Parse Amazon HTML file and return list of product dicts."""
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
