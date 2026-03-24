# Agent Guide: Capture and Parse Ecommerce Search Results

This document tells you how to capture a search results page and extract structured product data from it. The workflow has two phases: **capture** (save the page) and **parse** (extract fields from the saved HTML).

---

## Phase 1: Capture

### Goal

Save the full rendered HTML of a search results page as a JSON file.

### Steps

1. **Navigate** to the search URL for the target site and keyword.
2. **Wait** for the page to finish loading (product images and prices should be visible).
3. **Scroll slowly to the bottom** of the search results. Many sites lazy-load product tiles — they won't appear in the HTML unless you scroll past them.
4. **Wait 2–3 seconds** at the bottom for any final content to load.
5. **Scroll back to the top.**
6. **Run the bookmarklet.** Either click the "Capture Page" bookmark in the toolbar, or execute the contents of `bookmarklet/capture.js` in the browser console. A green banner will confirm success.
7. A JSON file downloads automatically to the default downloads folder.

### Captured JSON structure

```json
{
  "url": "https://www.example.com/search?q=coffee+maker",
  "title": "Page title",
  "timestamp": "2026-03-15T20:54:58.568Z",
  "viewport": { "width": 1280, "height": 900 },
  "scrollHeight": 14200,
  "scrollY": 0,
  "html": "<!DOCTYPE html>..."
}
```

### Sanity checks after capture

- `scrollHeight` should be large (thousands of pixels) for a page with many results. A value under ~1500 likely means products didn't load.
- `scrollY` of 0 is expected (you scrolled back to the top before capturing).
- Open the JSON, extract the `html` field, and spot-check that product titles and prices are present in the raw text.

---

## Phase 2: Parse

### Goal

Extract one row per product from the captured HTML. Each row must include the fields listed below.

### Required fields

| Field | Description | How to find it |
|-------|-------------|----------------|
| **rank** | Position in search results (1 = first product shown). | Use DOM order of the product tile elements. The first tile in the HTML is rank 1, second is rank 2, etc. Do not rely on pixel positions — DOM order matches display order on virtually all ecommerce sites. |
| **grid_position** | Human-readable location on the page (e.g., "row 1, col 1" or "top-left"). | Determine the number of columns in the product grid (typically 3–5). Derive row and column from rank: `row = ceil(rank / cols)`, `col = ((rank - 1) % cols) + 1`. The column count can usually be inferred from the CSS grid/flex classes on the product container, or by counting how many tiles share the first visible row. |
| **product_title** | Full product name as displayed. | Look for the most prominent text element inside each product tile — usually an `<a>`, `<h2>`, `<h3>`, or `<span>` with a class containing words like `title`, `name`, `description`, or `product`. |
| **brand** | Brand or manufacturer name. | Some sites have a dedicated brand element (look for classes like `brand`, `manufacturer`, `vendor`). If there is no separate brand element, the brand is often the first few words of the product title (e.g., "KitchenAid 5-Cup Food Chopper" → brand is "KitchenAid"). For B2B sites like 1688.com, the shop/store name serves as the brand. |
| **price** | Listed price. | Look for elements with classes containing `price`, `cost`, or `amount`. Extract the text and keep the currency symbol. If there are multiple prices (e.g., original + sale), capture the most prominent one (usually the sale/current price). |
| **is_sponsored** | Whether the product placement is paid advertising. | Check for any of these signals, in order of reliability: (1) data attributes like `data-ad`, `data-sponsored`, `_p_isad`, `sub_object_type=p4p`; (2) CSS classes containing `ad`, `sponsored`, `promoted`, `paid`; (3) visible text labels like "Sponsored", "Ad", "Promoted", or the site's local-language equivalent. |
| **is_private_label** | Whether the product is the retailer's own brand. | This requires knowing which brands belong to the retailer. Check the product's brand against a known list of private labels for the site (e.g., "Kirkland Signature" for Costco, "Amazon Basics" for Amazon, "Great Value" for Walmart). If no list is available, flag this field as unknown rather than guessing. |
| **badges** | Any special labels, tags, or banners on the product tile. | Look for small UI elements within the tile with classes like `badge`, `tag`, `label`, `pill`, `banner`, `ribbon`, or `flag`. Common examples: "Best Seller", "Our Recommendation", "Top Rated", "Limited Time", "New Arrival", price-related tags like "限时价" (limited-time price) or "全网低价" (lowest price online). Capture all badge texts as a comma-separated list. |

### General parsing approach

1. **Load the HTML** from the JSON file's `html` field using an HTML parser (e.g., BeautifulSoup in Python).
2. **Remove `<script>` tags** to avoid noise in text extraction.
3. **Identify the product tile selector.** Look for a repeating container element that wraps each product. Common patterns:
   - `[class*="product"]`, `[class*="offer"]`, `[class*="item"]`, `[class*="card"]`, `[class*="tile"]`, `[class*="result"]`
   - Data attributes like `[data-testid*="Product"]`, `[data-component="product"]`
   - The correct selector is the one that returns a count matching the number of visible products (typically 20–60 for a first page).
4. **Iterate tiles in DOM order** and extract each field using the guidance above.
5. **Output as CSV** with columns: `rank, grid_position, product_title, brand, price, is_sponsored, is_private_label, badges, url, capture_timestamp`.

### Tips for writing a site-specific parser

- Inspect 2–3 product tiles from the captured HTML before writing selectors. Look for consistent class names or data attributes.
- Sponsored products often have a different wrapper class or an extra child element compared to organic results — compare an ad tile to a normal tile to spot the difference.
- Some sites embed structured data as JSON-LD or `data-*` attributes on the tile. These are often more reliable than scraping visible text.
- If the site uses a component framework (React, Vue), look for `data-testid`, `data-qa`, or `data-component` attributes — these tend to be stable across site redesigns.
- Badge/label text varies by locale. A Chinese site won't say "Best Seller" — look for the equivalent UI pattern (small colored tag overlaid on the product image or near the price).

---

## Example: parsing a captured 1688.com page

```python
from bs4 import BeautifulSoup
import json, re, csv, math

with open("capture_s.1688.com_20260315_205458.json") as f:
    data = json.load(f)

soup = BeautifulSoup(data["html"], "html.parser")
for script in soup.find_all("script"):
    script.decompose()

cards = soup.select(".search-offer-wrapper")
COLS = 4  # 1688 uses a 4-column grid

rows = []
for i, card in enumerate(cards):
    rank = i + 1
    report = card.get("data-aplus-report", "")

    # Sponsored: check class and data attributes
    is_ad_class = "cardui-adOffer" in card.get("class", [])
    is_p4p = "sub_object_type@p4p" in report
    is_isad = "_p_isad@1" in report
    is_sponsored = is_ad_class or is_p4p or is_isad

    title_el = card.select_one(".title-text")
    price_el = card.select_one(".offer-price-row .price-item")
    shop_el = card.select_one(".offer-shop-row .col-left")

    tags = card.select(".offer-tag-row .offer-desc-item")
    promos = card.select(".offer-desc-row .offer-desc-item")
    badge_texts = [t.get_text(strip=True) for t in tags + promos]

    row_num = math.ceil(rank / COLS)
    col_num = ((rank - 1) % COLS) + 1

    rows.append({
        "rank": rank,
        "grid_position": f"row {row_num}, col {col_num}",
        "product_title": title_el.get_text(strip=True) if title_el else "",
        "brand": shop_el.get_text(strip=True) if shop_el else "",
        "price": price_el.get_text(strip=True) if price_el else "",
        "is_sponsored": is_sponsored,
        "is_private_label": False,  # not applicable for 1688
        "badges": ", ".join(badge_texts),
    })
```
