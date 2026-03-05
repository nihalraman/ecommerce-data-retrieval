# Ecommerce Search Results Scraper

Captures first-page search results from ecommerce sites for research purposes. Supports three collection methods: automated Playwright scraping, a Claude AI agent, and a bookmarklet for assisted manual collection.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

Optionally add Costco credentials to `.env` to get logged-in results from Playwright mode. Leave blank to scrape as a guest.

## Collection Methods

### 1. Playwright (automated)

Fully automated. Python opens a real browser, navigates to the search page, extracts product data using DOM selectors, takes a screenshot, and saves results to CSV.

```bash
python run.py --mode scrape --site costco "water bottle"
```

### 2. Claude AI Agent

Claude controls your real browser via the **Claude for Chrome** extension. It navigates to the search page, scrolls to load all products, takes a full-page screenshot, and extracts product data visually — no CSS selectors needed. This makes it easy to add new retailers without any selector configuration.

**Prerequisites (agent mode only):** [Claude Code](https://claude.ai/code) must be installed. Install the Claude for Chrome extension, then launch Claude Code with the `--chrome` flag:

```bash
claude --chrome
```

Then run the agent skill inside Claude Code:

```
/scrape-agent --site costco "water bottle"
```

Claude will handle navigation, scrolling, extraction, and saving results to the same CSV as the Playwright mode.

### 3. Bookmarklet (manual / MTurk workers)

Workers run a small JavaScript bookmarklet in their own browser to extract and download product data as JSON — no Python required. See **[docs/mturk-worker-instructions.md](docs/mturk-worker-instructions.md)** for the full worker guide.

To generate the bookmarklet for a site:

```bash
python bookmarklet/build.py --site costco
```

## Output

- **CSV**: `outputs/costco/results.csv` — appended after each run (all three modes write to the same file)
- **Screenshot**: `outputs/costco/screenshots/<timestamp>_<keyword>.png` — Playwright and agent modes only; bookmarklet workers take a manual screenshot

## Notes

- The browser window will open visibly during Playwright runs.
- If selectors break, inspect the page in the headed browser or add `await page.pause()` after `goto` in `scrapers/classic.py` to launch the Playwright inspector.
- New sites can be added to `config/sites.json` without changing any code.
