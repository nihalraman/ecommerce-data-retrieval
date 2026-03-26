# Guide: Writing an HTML Parser for Ecommerce Search Results

Reference for a Claude agent to write a site-specific parser. Input is a `.html` file containing HTML copied from Chrome DevTools (Elements panel → right-click `<html>` → Copy outer HTML).

---

## Output CSV Columns

```
Retailer, Product Category, Product Description, Brand, Price, Size, Rating, # of Reviews, Page, Row (top to bottom), Column (left to right), Private Label (Yes: 1, No: 0), Sponsored (Yes:1, No:0), Merchandising Tag (Yes: 1, No:0), Remarks
```

- **Retailer**: Site name (e.g., "Target"). Passed via CLI `--retailer` or inferred from script name.
- **Product Category**: Passed via CLI `--category`.
- **Page**: Passed via CLI `--page` (default: 1).
- **Size**: Extract if visible on tile; leave blank otherwise.
- **Rating / # of Reviews**: Extract if visible; leave blank otherwise.
- **Private Label**: 1 if brand matches a known retailer private-label list, else 0.
- **Merchandising Tag**: 1 if any badge/tag found on the tile, else 0. Put the tag text in **Remarks**.

---

## CLI Interface

```bash
python parse_<site>.py --category "Cooking Oil" [--page 1] [--output results.csv] input.html
```

Write to stdout by default; `--output` writes to file.

---

## Parsing Steps

```python
from bs4 import BeautifulSoup
import csv, argparse

# 1. Read raw HTML
with open(input_path) as f:
    html = f.read()

# 2. Parse and clean
soup = BeautifulSoup(html, "html.parser")
for script in soup.find_all("script"):
    script.decompose()

# 3. Find product tiles
tiles = soup.select(PRODUCT_TILE_SELECTOR)

# 4. Extract fields per tile (DOM order = display order)
for i, tile in enumerate(tiles):
    rank = i + 1
    row = ((rank - 1) // GRID_COLS) + 1
    col = ((rank - 1) % GRID_COLS) + 1
    # ... extract title, brand, price, etc.
```

---

## How to Identify Selectors

1. Open the captured HTML in a browser or text editor.
2. Search for a known product title to locate the tile HTML.
3. Look for a **repeating container** wrapping each product. Common patterns:
   - `[class*="product"]`, `[class*="card"]`, `[class*="tile"]`, `[class*="item"]`, `[class*="result"]`
   - `[data-testid*="product"]`, `[data-component*="product"]`
4. The correct selector returns a count matching visible products (typically 20–60).
5. Inspect 2–3 tiles to find consistent child selectors for each field.

---

## Field Extraction Guidance

| Field | Where to look |
|-------|--------------|
| **Product Description** | Most prominent text: `<a>`, `<h2>`, `<h3>`, `<span>` with class containing `title`, `name`, `description`, `product` |
| **Brand** | Dedicated element with class containing `brand`, `manufacturer`, `vendor`. If none, parse first word(s) of title. For marketplace sites, use shop/store name. |
| **Price** | Elements with class containing `price`, `cost`, `amount`. Keep currency symbol. If multiple prices (original + sale), take the current/sale price. |
| **Size** | Often part of the product title (e.g., "- 16.9 fl oz"). May also be a separate element near price. Extract if visible; leave blank if not on tile. |
| **Rating** | Look for star rating elements: `[class*="rating"]`, `[class*="star"]`, `aria-label` containing "out of 5". Extract numeric value. |
| **# of Reviews** | Usually near rating: `[class*="review"]`, `[class*="count"]`. Extract the number only. |
| **Sponsored** | Check in order: (1) data attributes: `data-ad`, `data-sponsored`, `data-is-sponsored`; (2) classes: `ad`, `sponsored`, `promoted`, `paid`; (3) visible text: "Sponsored", "Ad", "Promoted". |
| **Private Label** | Compare extracted brand against a hardcoded list of the retailer's own brands. |
| **Merchandising Tag** | Small UI elements: `[class*="badge"]`, `[class*="tag"]`, `[class*="label"]`, `[class*="pill"]`, `[class*="banner"]`. Examples: "Best Seller", "Top Rated", "New", "Sale". |

---

## Grid Layout

Determine column count by:
1. CSS classes on the container (e.g., `grid-cols-4`, `columns-5`)
2. Counting tiles that share the first visible row
3. Common defaults: desktop usually 4–5 columns for search results

Compute from rank:
```python
row = ((rank - 1) // GRID_COLS) + 1
col = ((rank - 1) % GRID_COLS) + 1
```

---

## Private Label Lists (Common Retailers)

- **Target**: Good & Gather, Market Pantry, Up & Up, Favorite Day, Kindfull, Threshold, Room Essentials, Brightroom, Figmint, Dealworthy, Smartly, Everspring, Cloud Island, Cat & Jack, All in Motion, Wild Fable, A New Day, Mondo Llama, Spritz, Hyde & EEK!
- **Costco**: Kirkland Signature
- **Walmart**: Great Value, Equate, Mainstays, Parent's Choice, Sam's Choice, Spring Valley
- **Amazon**: Amazon Basics, Amazon Essentials, Amazon Commercial, Solimo, Presto!

---

## Server Integration

For the auto-upload workflow (`server.py`), every parser must expose:

- `CSV_COLUMNS` — module-level list of column header strings
- `parse_html_string(html, category, page=1)` — accepts a raw HTML string (not a file path), returns a list of row dicts

The recommended pattern is to extract core logic into `_parse_soup(soup, category, page)` and have both `parse_html()` (file-based CLI) and `parse_html_string()` (string-based server) call it:

```python
def _parse_soup(soup, category, page=1):
    # All extraction logic here
    return rows

def parse_html(html_path, category, page=1):
    html = load_html(html_path)
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        script.decompose()
    return _parse_soup(soup, category, page)

def parse_html_string(html, category, page=1):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        script.decompose()
    return _parse_soup(soup, category, page)
```

---

## Important Notes

- **Scroll before copying HTML.** Lazy-loaded tiles won't appear in the DOM unless the page was fully scrolled first.
- **DOM order = display order** on virtually all ecommerce sites. Use DOM index as rank.
- **Sponsored tiles** may have different wrapper classes — compare an ad tile to a normal tile.
- Some sites embed JSON-LD or `data-*` attributes with structured data — these are more reliable than scraping visible text when available.
