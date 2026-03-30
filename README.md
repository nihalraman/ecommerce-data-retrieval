# Ecommerce Search Results Capture Tool

Captures first-page search results from ecommerce sites for research purposes. Not for commercial use.

The primary workflow is **bookmarklet + local server**: a research assistant scrolls a page and clicks a bookmarklet, which captures the HTML, parses it into structured product data, and uploads everything to Dropbox automatically. Three additional collection methods are available for different use cases.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium          # Only needed for Playwright mode
cp .env.example .env                 # Add DROPBOX_ACCESS_TOKEN (required for upload)
```

## Collection Methods

### 1. Bookmarklet + Server (primary)

A browser bookmarklet captures page HTML and sends it to a local server, which auto-detects the retailer, runs the site-specific parser, and uploads the raw capture, parsed CSV, and screenshot to Dropbox -- all in one click.

**Start the server:**
```bash
python server.py
```

**Generate the bookmarklet:**
```bash
python bookmarklet/build.py
```

Copy the "Capture & Upload" `javascript:...` string and save it as a browser bookmark.

**Collect data:**
1. Navigate to the search results page in an incognito window
2. Scroll slowly to the bottom (loads lazy-loaded products), then back to the top
3. Click the **Capture & Upload** bookmark
4. Confirm the product category and whether to include a screenshot
5. Wait for the green banner confirming success

If the server is unreachable, the bookmarklet falls back to saving a JSON file locally.

### 2. Bookmarklet (manual, no server)

The "Capture Only" bookmarklet downloads a JSON file locally without contacting the server. Parse it afterward with a site-specific parser:

```bash
python webpage_data_parsing/parse_amazon.py --category "Coffee Maker" capture.json
python webpage_data_parsing/parse_walmart.py --category "Coffee Maker" capture.json
python webpage_data_parsing/parse_target.py --category "Bottled Water" capture.html
```

Parsers accept both `.json` (bookmarklet captures) and `.html` (raw DevTools HTML) files.

### 3. Playwright Scraping

Opens a real browser, extracts product data via DOM selectors, takes a screenshot, and writes results to CSV.

```bash
python run.py --mode scrape --site costco "coffee maker"
```

Output: `outputs/costco/results.csv` + `outputs/costco/screenshots/`

### 4. Claude AI Agent

Claude controls your browser via the Chrome extension and extracts product data visually from screenshots. No selectors needed.

```bash
claude --chrome                                  # Launch with Chrome extension
/scrape-agent --site costco "coffee maker"       # Run inside Claude Code
```

## Parsers

Each supported site has a parser in `webpage_data_parsing/` that extracts structured product data from captured HTML. Every parser outputs a CSV with these columns:

> Retailer, Product Category, Product Description, Brand, Price, Size, Rating, # of Reviews, Page, Row, Column, Private Label, Sponsored, Merchandising Tag, Remarks

Each site requires its own parser because HTML structure differs across retailers. See [`webpage_data_parsing/parse_guide.md`](webpage_data_parsing/parse_guide.md) for how to write a new one.

## Cloud Storage (Dropbox)

The server uploads captures, parsed CSVs, and screenshots to Dropbox automatically.

### Configure

Add to `.env`:
```
DROPBOX_ACCESS_TOKEN=your-token
```

### Manual upload

```bash
python cloud/upload.py --website amazon --category "coffee maker" \
    --capture capture.json --screenshot shot.png --csv parsed.csv
```

### Download all results as one CSV

```bash
python cloud/download_all.py --website amazon --output amazon_all_results.csv
python cloud/download_all.py --output all_results.csv   # All retailers
```

## Adding New Sites

- **Playwright mode**: Add an entry to `config/sites.json`
- **Bookmarklet mode**: Write a new parser in `webpage_data_parsing/` (see [`parse_guide.md`](webpage_data_parsing/parse_guide.md)) and register it in `server.py`'s `PARSER_MAP`
