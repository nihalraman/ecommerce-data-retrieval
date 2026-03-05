import argparse
import asyncio
from scrapers.classic import run_scrape

from dotenv import load_dotenv

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Ecommerce search results scraper")
    parser.add_argument("--mode", choices=["scrape"], required=True, help="Scraping mode")
    parser.add_argument("--site", required=True, help="Site key from config/sites.json")
    parser.add_argument("search", help="Search string")
    args = parser.parse_args()

    if args.mode == "scrape":
        asyncio.run(run_scrape(args.site, args.search))


if __name__ == "__main__":
    main()
