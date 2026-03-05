import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from scrapers.base import append_results_to_csv, save_screenshot
from utils.helpers import is_path_allowed, random_delay

CAPTCHA_SIGNALS = ["captcha", "robot", "verify you are human", "unusual traffic", "access denied", "you don't have permission"]


def load_site_config(site: str) -> dict:
    config_path = os.path.join("config", "sites.json")
    with open(config_path, encoding="utf-8") as f:
        all_sites = json.load(f)
    if site not in all_sites:
        raise ValueError(f"Site '{site}' not found in config/sites.json")
    return all_sites[site]


async def maybe_login(page, site: str, config: dict) -> None:
    email = os.environ.get("COSTCO_EMAIL") or os.environ.get(f"{site.upper()}_EMAIL")
    password = os.environ.get("COSTCO_PASSWORD") or os.environ.get(f"{site.upper()}_PASSWORD")
    if not (email and password):
        print(f"[info] No credentials found for {site} — proceeding without login.")
        return
    login_url = config.get("login_url")
    if not login_url:
        print(f"[info] No login_url configured for {site} — skipping login.")
        return
    print(f"[info] Logging in to {site}...")
    await page.goto(login_url, wait_until="domcontentloaded")
    await random_delay(1.5, 3.0)
    await page.fill("#signInName", email)
    await page.fill("#password", password)
    await page.click("#next")
    await page.wait_for_load_state("domcontentloaded")
    await random_delay(2.0, 4.0)
    print(f"[info] Login completed for {site}.")


async def extract_products(page, config: dict, site: str, search_string: str, screenshot_file: str) -> list[dict]:
    js_path = Path(__file__).parent.parent / "core" / "extractVirtualPlanogram.js"
    js_code = js_path.read_text()
    raw = await page.evaluate(
        "(config) => { " + js_code + "; return extractVirtualPlanogram(config); }",
        config
    )
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for item in raw:
        rows.append({
            "site": site,
            "timestamp": timestamp,
            "search_string": search_string,
            "rank": item["index"],
            "brand": item["brand"],
            "price": item["price"],
            "is_sponsored": item["is_sponsored"],
            "is_private_label": item["is_private_label"],
            "badges": item["badges"],
            "product_title": item["title"],
            "tile_x": item["tile_x"],
            "tile_y": item["tile_y"],
            "screenshot_file": screenshot_file,
            "source": "playwright",
        })
    return rows


async def run_scrape(site: str, search_string: str) -> None:
    config = load_site_config(site)

    search_url = config["base_url"].replace("{keyword}", search_string.replace(" ", "+"))
    parsed = urlparse(search_url)
    search_path = parsed.path + ("?" + parsed.query if parsed.query else "")

    if not is_path_allowed(search_url, search_path):
        print(f"[warning] robots.txt disallows scraping '{search_path}' on {site}. Exiting.")
        return

    profile_dir = Path(__file__).parent.parent / ".browser_profiles" / site
    profile_dir.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(profile_dir),
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1280, "height": 900},
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        pages = context.pages
        page = pages[0] if pages else await context.new_page()

        await maybe_login(page, site, config)

        print(f"[info] Navigating to: {search_url}")
        await page.goto(search_url, wait_until="domcontentloaded")
        await random_delay()

        body_text = (await page.inner_text("body")).lower()
        for signal in CAPTCHA_SIGNALS:
            if signal in body_text:
                print(f"[warning] CAPTCHA/bot detection triggered ('{signal}'). Exiting.")
                await context.close()
                return

        # Three-stage human scroll
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 3)")
        await random_delay(1.0, 2.0)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 2 / 3)")
        await random_delay(1.0, 2.0)
        await page.evaluate("window.scrollTo(0, 0)")
        await random_delay(1.0, 2.0)

        screenshot_file = await save_screenshot(page, site, search_string)
        print(f"[info] Screenshot saved: {screenshot_file}")

        rows = await extract_products(page, config, site, search_string, screenshot_file)
        print(f"[info] Extracted {len(rows)} products.")

        await context.close()

    append_results_to_csv(site, rows)
    print(f"[info] Results appended to outputs/{site}/results.csv")
