"""Parse Target.com search/category page HTML into structured CSV.

Usage:
    python webpage_data_parsing/parse_target.py --category "Bottled Water" target_page.html
    python webpage_data_parsing/parse_target.py --category "Cooking Oil" --page 2 --output results.csv page2.html
    
    
    python webpage_data_parsing/parse_target.py --category "" webpage_data_parsing/target_page_data.html
"""

import argparse
import csv
import os
import re
import sys
from bs4 import BeautifulSoup

RETAILER = "Target"
# Canonical brand name casing (lowercase key -> display name)
BRAND_CANONICAL = {
    "smartwater": "smartwater",
    "bubbl'r": "BUBBL'R",
    "dasani": "Dasani",
    "evian": "Evian",
    "fiji": "FIJI",
    "essentia": "Essentia",
    "pure life": "Pure Life",
    "topo chico": "Topo Chico",
    "ice mountain": "Ice Mountain",
    "core": "Core Hydration",
    "core hydration": "Core Hydration",
    "saratoga": "Saratoga",
    "bubba": "Bubba",
}

PRIVATE_LABEL_BRANDS = [
    "Good & Gather", "Market Pantry", "Up & Up", "Favorite Day",
    "Kindfull", "Threshold", "Room Essentials", "Brightroom", "Figmint",
    "Dealworthy", "Smartly", "Everspring", "Cloud Island", "Cat & Jack",
    "All in Motion", "Wild Fable", "A New Day", "Mondo Llama", "Spritz",
    "Hyde & EEK!", "Heyday",
]

CSV_COLUMNS = [
    "Retailer", "Product Category", "Product Description", "Brand",
    "Price", "Size", "Rating", "# of Reviews", "Page",
    "Row (top to bottom)", "Column (left to right)",
    "Private Label (Yes: 1, No: 0)", "Sponsored (Yes:1 , No:0)",
    "Merchandising Tag (Yes: 1, No:0)", "Remarks",
]


def parse_brand_from_title(title):
    """Extract brand from Target product title.

    Target titles typically follow one of these patterns:
      "Brand Name Product Description - Size"
      "Product Description - Size - Brand Name™"
    """
    # Check for brand after last dash with trademark symbol
    parts = title.rsplit(" - ", 1)
    if len(parts) == 2:
        candidate = parts[1].strip().rstrip("™®")
        for brand in PRIVATE_LABEL_BRANDS:
            if brand.lower() in candidate.lower():
                return brand
    # Check for brand at end after dash (common Target pattern)
    # e.g., "Purified Water - 32pk/16.9 fl oz Bottles - Good & Gather™"
    segments = [s.strip() for s in title.split(" - ")]
    for seg in reversed(segments):
        cleaned = seg.rstrip("™®").strip()
        for brand in PRIVATE_LABEL_BRANDS:
            if brand.lower() == cleaned.lower():
                return brand
    # Fall back to first word(s) before a size/quantity pattern or generic word
    # Strip everything after " - " to isolate the product name portion
    name_part = title.split(" - ")[0].strip()
    first_words = name_part.split()
    brand_words = []
    generic = {"water", "purified", "spring", "sparkling", "drinking",
               "natural", "mineral", "distilled", "flavored", "enhanced",
               "oil", "olive", "cooking", "vegetable", "canola", "avocado",
               "organic", "extra", "virgin", "100%", "bottled", "bottles",
               "bottle", "cans", "pack", "thickened", "unflavored",
               "artesian", "alkaline", "hydration", "clear",
               # Flavors — stop brand extraction before flavor words
               "watermelon", "lime", "lemon", "berry", "strawberry",
               "raspberry", "cherry", "mango", "peach", "orange",
               "grape", "apple", "pineapple", "coconut", "vanilla",
               "mint", "cucumber", "ginger", "tangerine", "grapefruit"}
    # Known multi-word brands where only the first word is in the title prefix
    multi_word_brands = {
        "thick-it": "Thick-It",
        "core hydration": "Core Hydration",
    }
    for w in first_words:
        clean = w.lower().rstrip("™®,'")
        if clean in generic:
            break
        # Stop at size-like tokens (e.g., "24oz", "6pk")
        if re.match(r'\d+(?:oz|pk|pack|fl|gal|l|ml|ct)\b', clean, re.IGNORECASE):
            break
        brand_words.append(w.rstrip("™®"))
        # Most brands are 1-2 words; stop at 3
        if len(brand_words) >= 3:
            break
    brand = " ".join(brand_words) if brand_words else ""
    # Check for multi-word brand matches (e.g., "Thick-It" -> keep, drop "Clear Advantage")
    for key, canonical in multi_word_brands.items():
        if brand.lower().startswith(key):
            return canonical
    # Normalize to canonical casing — also check first word only for brands
    # where the parser grabbed extra words (e.g., "Bubba Daydreamin" -> "Bubba")
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
    # Match patterns like "32 Pack/16.9 Fl Oz", "24pk/16.9 fl oz", "128 fl oz"
    m = re.search(
        r'(\d+\s*(?:pack|pk))?[/\s]*'
        r'(\d+(?:\.\d+)?\s*(?:fl\s*oz|oz|gal|gallon|l|liter|litre|ml|ct|count))',
        title, re.IGNORECASE
    )
    if m:
        parts = [p.strip() for p in m.groups() if p]
        return "/".join(parts)
    return ""


def is_private_label(brand):
    """Check if brand is a Target private label."""
    if not brand:
        return False
    return any(pl.lower() in brand.lower() for pl in PRIVATE_LABEL_BRANDS)


def _is_in_carousel(tile):
    """Check if a product tile is inside a carousel (Deals, Related, etc.)."""
    parent = tile.parent
    for _ in range(10):
        if not parent:
            break
        classes = " ".join(parent.get("class", []))
        # Carousel containers or section rows that aren't the main product grid
        if "Carousel" in classes or "carousel" in classes:
            return True
        dt = parent.get("data-test", "")
        if dt == "product-grid":
            return False
        parent = parent.parent
    return False


def parse_html(html_path, category, page=1):
    """Parse Target HTML file and return list of product dicts."""
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        script.decompose()

    # Select only main-grid product cards, not carousel items
    all_tiles = soup.select(
        '[data-test="@web/site-top-of-funnel/ProductCardWrapper"]'
    )
    tiles = [t for t in all_tiles if not _is_in_carousel(t)]
    if not tiles:
        print(f"Warning: no product tiles found in {html_path}", file=sys.stderr)
        return []

    rows = []
    seen_product_ids = set()
    for i, tile in enumerate(tiles):
        # Deduplicate by product ID (products can appear as both sponsored and organic)
        wrapper = tile.select_one('[style*="view-transition-name"]')
        if wrapper:
            m = re.search(r'product-info-(\d+)', wrapper.get("style", ""))
            if m:
                pid = m.group(1)
                if pid in seen_product_ids:
                    continue
                seen_product_ids.add(pid)

        rank = len(rows) + 1

        # Title
        title_el = tile.select_one('[data-test="@web/ProductCard/title"]')
        title = title_el.get_text(strip=True) if title_el else ""

        # Price
        price_el = tile.select_one('[data-test="current-price"]')
        price_text = price_el.get_text(strip=True) if price_el else ""
        # Extract numeric price
        price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
        price = float(price_match.group(1).replace(",", "")) if price_match else ""

        # Brand
        brand = parse_brand_from_title(title)

        # Size
        size = parse_size_from_title(title)

        # Rating and reviews live in div.styles_ratingsAndReviews__*
        # Structure: <span aria-hidden="true">4.7</span> ... <span aria-label="24683 ratings">(24683)</span>
        rating = ""
        num_reviews = ""
        ratings_div = tile.select_one('[class*="ratingsAndReviews"]')
        if ratings_div:
            score_el = ratings_div.select_one('span[aria-hidden="true"]')
            if score_el:
                try:
                    rating = float(score_el.get_text(strip=True))
                except ValueError:
                    pass
            count_el = ratings_div.select_one('span[aria-label$="ratings"]')
            if count_el:
                rvm = re.search(r'([\d,]+)', count_el.get_text(strip=True))
                if rvm:
                    num_reviews = int(rvm.group(1).replace(",", ""))

        # Sponsored
        sponsored_el = tile.select_one('[data-test="sponsoredText"]')
        is_sponsored = 1 if sponsored_el else 0

        # Merchandising tags / badges
        remarks_parts = []
        has_merch_tag = 0
        # "Highly rated" marker badge — this is the merchandising tag
        highly_rated_el = tile.select_one('[aria-label*="Highly rated"]')
        if highly_rated_el:
            remarks_parts.append(highly_rated_el.get("aria-label", "Highly rated"))
            has_merch_tag = 1
        # Check for "Sale" urgency message
        sale_el = tile.select_one('[data-test="urgency-message"]')
        if sale_el:
            sale_text = sale_el.get_text(strip=True)
            if sale_text:
                remarks_parts.append(sale_text)
        # Check for promo details (goes in Remarks but not merch tag)
        promo_el = tile.select_one(
            '[data-test="@web/Price/PriceAndPromoMinimal/PromoDetails"]'
        )
        if promo_el:
            remarks_parts.append(promo_el.get_text(strip=True))
        # Check for first regular promo
        first_promo = tile.select_one('[data-test="first-regular-promo"]')
        if first_promo:
            remarks_parts.append(first_promo.get_text(strip=True))

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
            "Row (top to bottom)": rank,
            "Column (left to right)": "",
            "Private Label (Yes: 1, No: 0)": 1 if is_private_label(brand) else 0,
            "Sponsored (Yes:1 , No:0)": is_sponsored,
            "Merchandising Tag (Yes: 1, No:0)": has_merch_tag,
            "Remarks": "; ".join(remarks_parts),
        })

    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Parse Target.com HTML into product CSV"
    )
    parser.add_argument("html_file", help="Path to saved .html file")
    parser.add_argument("--category", required=True, help="Product category name")
    parser.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    parser.add_argument("--output", "-o", help="Output CSV path (default: stdout)")
    args = parser.parse_args()

    rows = parse_html(args.html_file, args.category, args.page)

    if args.output:
        output_path = args.output
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "target_parsed.csv")

    with open(output_path, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} products to {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
