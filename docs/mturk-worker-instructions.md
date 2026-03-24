# MTurk Worker Instructions

You will visit a shopping website, search for a product, and save a copy of the search results page. The whole task takes about 5 minutes.

## What you'll be doing

You are saving a snapshot of a search results page so we can study how products are displayed. You'll use a special bookmark (called a "bookmarklet") that saves the page as a file — one click and it downloads automatically. No software to install.

---

## One-time setup: Add the bookmarklet to your browser

You only need to do this once. After that, the bookmark stays in your browser for all future HITs.

1. Make sure your **bookmarks bar is visible**
   - **Chrome**: Menu → Bookmarks → Show Bookmarks Bar (or press `Ctrl+Shift+B` / `Cmd+Shift+B`)
   - **Firefox**: Menu → View → Toolbars → Bookmarks Toolbar
2. **Right-click** on the bookmarks bar and choose **Add page** (Chrome) or **Add Bookmark** (Firefox)
3. For the **Name**, type anything you like (e.g. "Capture Page")
4. For the **URL**, paste the long `javascript:...` code provided in the HIT description
5. Click **Save**

You should now see your new bookmark on the bar.

---

## For each HIT

### Step 1: Go to the search page

1. Open the website listed in the HIT (e.g. costco.com, amazon.com)
2. Type the search keyword from the HIT into the site's search box and press Enter
3. Wait for the results to fully load

### Step 2: Scroll the entire page (do not skip this)

Many shopping sites load products as you scroll. If you skip this step, some products will be missing from the capture.

1. **Scroll slowly all the way down** to the bottom of the search results
2. **Wait 2–3 seconds** at the bottom
3. **Scroll back up** to the top of the page

### Step 3: Click the bookmarklet

1. Click the "Capture Page" bookmark you created during setup
2. A file will download automatically (named something like `capture_www.costco.com_20260315_143022.json`)
3. Don't open the file — just note where it was saved

### Step 4: Take a screenshot

Take a screenshot of the search results page as it appears on your screen. This is used as a visual reference to verify the capture.

- **Mac**: `Cmd + Shift + 3` (full screen) or `Cmd + Shift + 4` (select area)
- **Windows**: `Win + Shift + S`, then save the image

### Step 5: Upload and submit

Upload both files to the HIT:
1. The downloaded `.json` file
2. Your screenshot image

---

## Troubleshooting

**The bookmarklet didn't do anything** — Make sure you pasted the full `javascript:...` code into the **URL** field of the bookmark (not the Name field). Also make sure you're on the search results page, not the site's homepage.

**No file downloaded** — Your browser may have blocked the download. Look for a "blocked download" icon in the address bar or a notification at the bottom of the window, and click "Allow" or "Keep".

**I see a CAPTCHA or "are you a robot?" check** — Do not try to get past it. Return the HIT and move on to the next one.

**The page looks different from what I expected** — As long as you can see search results (product images, prices, titles), proceed normally. Some sites look different when you're not logged in, and that's fine.
