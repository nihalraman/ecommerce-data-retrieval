import csv
import os
from datetime import datetime

CSV_COLUMNS = [
    "site", "timestamp", "search_string", "rank",
    "brand", "price", "is_sponsored", "is_private_label",
    "badges", "badges_en", "product_title", "product_title_en",
    "tile_x", "tile_y", "screenshot_file", "source",
]


async def save_screenshot(page, site: str, search_string: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    safe_search = search_string.replace(" ", "_")
    filename = f"{timestamp}_{safe_search}.png"
    dir_path = os.path.join("outputs", site, "screenshots")
    os.makedirs(dir_path, exist_ok=True)
    await page.screenshot(path=os.path.join(dir_path, filename), full_page=True)
    return filename


def append_results_to_csv(site: str, rows: list[dict]) -> None:
    dir_path = os.path.join("outputs", site)
    os.makedirs(dir_path, exist_ok=True)
    csv_path = os.path.join(dir_path, "results.csv")
    write_header = not os.path.exists(csv_path)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)
