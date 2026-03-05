# MTurk Worker Instructions

You will visit a shopping website, search for a product, and capture the results using a bookmarklet (a special browser bookmark). The whole task takes about 5 minutes.

---

## Step 1: Add the bookmarklet to your browser

1. Right-click your browser's bookmarks bar and choose **Add page** or **Add bookmark**
2. Give it any name (e.g. "Capture Results")
3. In the URL field, paste the `javascript:` code provided in the HIT
4. Save it

> The bookmarks bar must be visible. In Chrome: View → Always Show Bookmarks Bar. In Firefox: View → Toolbars → Bookmarks Toolbar.

---

## Step 2: Go to the search page

1. Open the website listed in your HIT (e.g. costco.com)
2. Search for the keyword listed in your HIT
3. Wait for the results to fully load

---

## Step 3: Scroll the page

This step is required — do not skip it.

1. Slowly scroll down to the **bottom** of the search results
2. Pause for 2–3 seconds
3. Scroll back up to the **top** of the page

This ensures all products are loaded before capture.

---

## Step 4: Run the bookmarklet

1. Click the bookmarklet in your bookmarks bar
2. A JSON file will download automatically (e.g. `costco_planogram.json`)
3. If nothing downloads, check that your browser allows downloads from this site

---

## Step 5: Take a screenshot

1. Take a screenshot of the full search results page as it appears on your screen
2. Save it as a PNG or JPG file

**Mac**: Press `Cmd + Shift + 3` for full screen, or `Cmd + Shift + 4` to select an area
**Windows**: Press `Win + Shift + S`, then save the image

---

## Step 6: Submit

Upload both files to the HIT:
- The downloaded JSON file
- Your screenshot

---

## Troubleshooting

**The bookmarklet didn't do anything** — Make sure you pasted the full `javascript:` code into the URL field of the bookmark, not the name field. Try again on the search results page (not the homepage).

**No file downloaded** — Your browser may have blocked the download. Check for a blocked download notice in the address bar and allow it.

**I see a CAPTCHA or "robot check"** — Stop and return the HIT. Do not attempt to bypass it.
