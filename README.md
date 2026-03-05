# Ecommerce Search Results Scraper

Captures first-page search results from ecommerce sites using a headed Playwright browser.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

Optionally add Costco credentials to `.env` to get logged-in results. Leave blank to scrape as a guest.

## Run

```bash
python run.py --mode scrape --site costco "water bottle"
```

## Output

- **CSV**: `outputs/costco/results.csv` — appended after each run
- **Screenshot**: `outputs/costco/screenshots/<timestamp>_<keyword>.png`

## Notes

- The browser window will open visibly during the run.
- If selectors break, inspect the page in the headed browser or add `await page.pause()` after `goto` in `scrapers/classic.py` to launch the Playwright inspector.
- New sites can be added to `config/sites.json` without changing any code.
