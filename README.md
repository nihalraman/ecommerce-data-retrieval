# Ecommerce Search Results Capture Tool

Captures first-page search results from ecommerce sites for research purposes. Supports three collection methods: automated Playwright scraping, a Claude AI agent, and a bookmarklet for assisted manual collection.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env  # Add credentials (optional)
```

## 1. Playwright Scraping (Automated)

Opens a real browser, extracts product data via DOM selectors, takes a screenshot, and writes results to CSV.

```bash
python run.py --mode scrape --site costco "coffee maker"
```

Output: `outputs/costco/results.csv` + `outputs/costco/screenshots/`

## 2. Claude AI Agent

Claude controls your browser via the Chrome extension and extracts product data visually from screenshots. No selectors needed — works on any site.

```bash
claude --chrome                                  # Launch with Chrome extension
/scrape-agent --site costco "coffee maker"       # Run inside Claude Code
```

## 3. Bookmarklet (Manual)

A browser bookmarklet captures the full page HTML as a JSON file. The same bookmarklet works on any site. Product data is extracted later with site-specific parsers.

### Generate the bookmarklet

```bash
python bookmarklet/build.py
```

Copy the printed `javascript:...` string and save it as a browser bookmark.

### Capture a page

1. Navigate to the search results page
2. **Scroll slowly to the bottom** (loads lazy-loaded products), wait 2-3 seconds
3. Scroll back to the top
4. Click the bookmarklet — a JSON file downloads automatically
5. Take a manual screenshot (Cmd+Shift+4 / Win+Shift+S) for audit trail

The bookmarklet strips scripts, tracking pixels, and comments before saving to reduce file size (~70% smaller than raw HTML).

### Parse captured HTML

```bash
python webpage_data_parsing/parse_amazon.py --category "Coffee Maker" capture.json
python webpage_data_parsing/parse_walmart.py --category "Coffee Maker" capture.json
python webpage_data_parsing/parse_target.py --category "Bottled Water" capture.html
```

Each parser outputs a CSV with: Retailer, Product Category, Product Description, Brand, Price, Size, Rating, Reviews, Page, Row, Column, Private Label, Sponsored, Merchandising Tag, Remarks.

Parsers accept both `.json` (bookmarklet captures) and `.html` (raw HTML) files.

See [docs/mturk-worker-instructions.md](docs/mturk-worker-instructions.md) for the full worker guide.

## AWS S3 Storage

Captures, screenshots, and parsed CSVs can be uploaded to S3 for centralized access.

### Configure

Add to `.env`:
```
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=ecommerce-search-captures
AWS_REGION=us-east-1
```

Or configure `~/.aws/credentials` — boto3 picks it up automatically.

### Upload

```bash
# Upload any combination of capture, screenshot, and parsed CSV
python cloud/upload.py --capture capture.json --screenshot shot.png --csv parsed.csv
```

Files are organized on S3 as:
```
raw-captures/{retailer}/{date}/{filename}.json
screenshots/{retailer}/{date}/{filename}.png
extracted/{retailer}/{date}/{filename}.csv
```

### Download all results as one CSV

```bash
python cloud/download_all.py --retailer amazon --output amazon_all_results.csv
python cloud/download_all.py --output all_results.csv   # All retailers
```

## Adding New Sites

Add an entry to `config/sites.json` (Playwright mode) or write a new parser in `webpage_data_parsing/` (bookmarklet mode). See [docs/adding-a-new-site.md](docs/adding-a-new-site.md).
