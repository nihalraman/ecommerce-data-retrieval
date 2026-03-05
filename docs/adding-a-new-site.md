# Adding a New Site

All site configuration lives in `config/sites.json`. Adding a new site means adding one entry to that file — no Python changes required.

---

## Step 1: Find the product tile selector

Open the target site's search results page in Chrome. Search for any keyword so products are visible.

1. Right-click a product tile and choose **Inspect**
2. In DevTools, look at the element that wraps the entire tile (image + title + price)
3. Find a CSS selector that matches **all tiles and only tiles** on the page

Run this in the DevTools console to verify your selector:
```js
document.querySelectorAll("YOUR_SELECTOR_HERE").length
// should return the number of products on the page (e.g. 24)
```

This becomes `productContainer`.

**Tips:**
- Prefer `data-testid` or `data-automation` attributes over class names — classes change frequently
- Use attribute prefix matching if IDs include dynamic suffixes: `[data-testid^='ProductTile_']`
- If tiles have inconsistent markup, pick the most common parent wrapper

---

## Step 2: Find field selectors

For each field, click into a tile in the DevTools element tree and find a selector that works **relative to the tile** (not the whole page).

Test each one in the console:
```js
var tile = document.querySelectorAll("YOUR_PRODUCT_CONTAINER")[0];
tile.querySelector("YOUR_FIELD_SELECTOR").innerText;
```

| Field | What to find | Set to `null` if... |
|---|---|---|
| `fields.title` | Product name element | Never — title is always required |
| `fields.price` | Price element | Price isn't shown on search results |
| `fields.brand` | Dedicated brand element | Brand isn't a separate element — set `null` and it will be parsed from the title |

**Brand parsing fallback** (when `fields.brand` is `null`): the extractor splits the title on ` - ` first, then `,`. This works for titles like `"Kirkland Signature - Olive Oil, 2L"` but may need verification per site.

---

## Step 3: Find optional selectors

**Sponsored indicator** (`sponsored_selector`): Inspect a tile that says "Sponsored" or "Ad". Find the child element unique to sponsored tiles.

```js
// Verify: should return null for organic tiles, an element for sponsored ones
tile.querySelector("YOUR_SPONSORED_SELECTOR");
```

If no reliable element exists, omit `sponsored_selector` entirely. The extractor will fall back to searching the tile's text for the word "sponsored". If the site uses a different word (e.g. "promoted"), set `sponsored_text_fallback`.

**Badges** (`badge_selector`): Look for "Best Seller", "Our Pick", or similar label elements inside tiles. Find a selector that matches all badge elements. Omit if the site doesn't use badges.

---

## Step 4: Add the config entry

```json
"TARGET_SITE": {
  "siteName": "TARGET_SITE",
  "base_url": "https://www.example.com/search?q={keyword}",
  "login_url": null,
  "productContainer": "[data-testid^='ProductTile_']",
  "fields": {
    "title": "[data-testid$='_title']",
    "price": ".price",
    "brand": null,
    "metadata": []
  },
  "sponsored_selector": ".sponsored-label",
  "badge_selector": null,
  "private_label_brands": ["Example Brand"],
  "max_results": 24
}
```

- `{keyword}` in `base_url` is replaced at runtime with the search string
- `login_url` can be `null` if no login is needed
- `max_results` should match the site's typical first-page product count (check by counting tiles)
- `private_label_brands` is a list of the retailer's own brand names, used to flag `is_private_label`

---

## Step 5: Verify

**Quick console test** — before running the scraper, paste this into the DevTools console on the search results page:

```js
// Paste the contents of core/extractVirtualPlanogram.js, then:
extractVirtualPlanogram(YOUR_CONFIG_OBJECT_HERE);
```

Check that the returned array has the right number of products and that title, price, and brand look correct.

**Playwright mode:**
```bash
python run.py --mode scrape --site TARGET_SITE "test keyword"
```

**Bookmarklet:**
```bash
python bookmarklet/build.py --site TARGET_SITE
# Paste the output URI into a browser bookmark and test on the site
```

---

## Common problems

**`productContainer` matches 0 elements** — The site may use lazy rendering. Try scrolling to the bottom first, then re-running. Also check if tiles are inside a shadow DOM (right-click → Inspect, look for `#shadow-root`). Shadow DOM requires a different approach.

**Brand is always empty** — Set `fields.brand` to `null` and verify the title format is parseable (contains ` - ` or `,`). If titles don't follow that pattern, you'll need a dedicated brand selector or `metadata` entry.

**Sponsored detection is unreliable** — Check if the site appends sponsored tiles at the end of the DOM out of visual order. If so, the bounding-box sort will still rank them correctly, but `is_sponsored` may miss some. Inspect several sponsored tiles to find a more reliable selector.

**All tiles show `is_sponsored: true`** — Your `sponsored_text_fallback` word appears in every tile's text (e.g. a footer or disclaimer). Set `sponsored_selector` to a specific element instead of relying on the text fallback.
