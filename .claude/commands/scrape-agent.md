# /scrape-agent Skill

Usage: `/scrape-agent --site <site_key> "<search terms>"`
Requires: `claude --chrome` (Chrome extension connected)

## Steps

1. Parse `--site` and the search string from the skill arguments.

2. Read `config/sites.json` and find the entry for the site. Extract `base_url`,
   `private_label_brands`, and `max_results`. If not found, stop with an error.

3. Check robots.txt:
   ```
   python -c "from utils.helpers import is_path_allowed; print(is_path_allowed('<search_url>', '<path>'))"
   ```
   If output is `False`, stop.

4. Construct the search URL (replace `{keyword}` with the search string, spaces → `+`).
   Open in Chrome and wait for the page to load.

5. Check for CAPTCHA / bot detection. If you see a CAPTCHA, "verify you are human",
   "access denied", or similar challenge, report failure and stop. Do not attempt to solve it.

6. Three-stage scroll (triggers lazy-loaded product tiles):
   - Scroll to ~1/3 page height. Wait 2 seconds.
   - Scroll to ~2/3 page height. Wait 2 seconds.
   - Scroll back to top. Wait 2 seconds.

7. Save a full-page screenshot:
   ```
   mkdir -p outputs/<site>/screenshots
   ```
   Save to: `outputs/<site>/screenshots/<YYYY-MM-DD_HHMMSS>_<search_underscored>.png`

8. Extract up to `max_results` product tiles visually, in top-to-bottom left-to-right order:

   | Field | Extraction rule |
   |-------|----------------|
   | `rank` | Integer position starting at 1. Reading order: top row left→right, then next row, etc. |
   | `product_title` | Full product name exactly as displayed. Do not truncate. |
   | `brand` | Use dedicated brand label if present. Otherwise parse from title: text before ` - ` or before first comma. If neither, use first word(s) if they appear to be a brand; otherwise empty string. |
   | `price` | Price as displayed, including currency symbol (e.g. `"$29.99"`). Ranges: `"$X.XX - $Y.YY"`. No price visible: empty string. |
   | `is_sponsored` | `true` (boolean) if tile has any label: "Sponsored", "Ad", "Promoted", "Paid". `false` otherwise. |
   | `is_private_label` | `true` (boolean) if brand matches any entry in `private_label_brands` (case-insensitive). `false` otherwise. |
   | `badges` | Semicolon-separated visible badge labels: "Best Seller", "Our Recommendation", "New", "Sale", "Top Rated". Empty string if none. |

   **SKIP**: "People also viewed" sections, promotional banners, navigation elements,
   comparison widgets, pagination. Only include actual search result product tiles.

   **IMPORTANT**: `is_sponsored` and `is_private_label` must be JSON booleans (`true`/`false`),
   not strings. Ranks must be integers. Do not hallucinate products not on the page.
   If fewer than 5 products are visible, report the issue and stop.

9. Write extracted data to a temp file:
   `/tmp/agent_extract_<YYYYMMDD_HHMMSS>.json`

10. Run:
    ```bash
    python scrapers/save_agent_results.py \
      --json /tmp/agent_extract_<timestamp>.json \
      --site <site> \
      --search "<search_string>" \
      --screenshot "<screenshot_filename>"
    ```

11. If exit code 0: report success (N products saved, CSV path).
    If exit code 1: the script prints specific eval failures. Re-examine the page
    screenshot and correct the data. Write a new JSON and repeat step 10 (one retry).
    If the retry also fails, report all failures to the user and stop.

---

## Eval Checks (run by save_agent_results.py)

`save_agent_results.py` calls `evals/check_results.py` before writing anything to CSV.
All checks are deterministic — no network, no LLM.

| Code | Check |
|------|-------|
| `SCHEMA` | All required keys present: `rank`, `product_title`, `brand`, `price`, `is_sponsored`, `is_private_label`, `badges` |
| `MIN_COUNT` | At least 5 products captured |
| `RANK_INTEGRITY` | Ranks are sequential integers 1..N, no gaps, no duplicates |
| `EMPTY_TITLE` | All `product_title` values are non-empty strings |
| `DUPE_TITLE` | No two products share the same `product_title` |
| `PRICE_FORMAT` | Each non-empty price contains at least one digit (handles ranges, units, currency variants) |
| `BOOLEAN_TYPE` | `is_sponsored` and `is_private_label` are actual booleans, not strings |
| `SPONSORED_RATE` | Sponsored product fraction < 70% |

Failure output format:
```
EVAL FAILED (2 issues):
  [BOOLEAN_TYPE] is_sponsored is string "true" at rank 3 (must be boolean)
  [RANK_INTEGRITY] Ranks [1, 2, 2, 4] contain duplicates
```

The eval module can also be run standalone for debugging:
```bash
python -m evals.check_results /tmp/agent_extract_<timestamp>.json
```
