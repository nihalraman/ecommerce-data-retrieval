"""Local capture server — receives bookmarklet POSTs, parses, uploads to Dropbox.

Start:  python server.py
Test:   curl -X POST http://localhost:8585/capture -H 'Content-Type: application/json' -d '{...}'
"""

import base64
import concurrent.futures
import csv
import json
import os
import sys
import tempfile
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from cloud.upload import (
    get_dropbox_client,
    build_base_name,
    capitalize_site,
    upload_file,
    DROPBOX_BASE_PATH,
)

# Site detection: hostname substring -> site key
SITE_MAP = {
    "amazon": "amazon",
    "walmart": "walmart",
    "target": "target",
    "costco": "costco",
    "1688": "1688",
}

# Parser modules (lazy-imported)
PARSER_MAP = {
    "amazon": "webpage_data_parsing.parse_amazon",
    "walmart": "webpage_data_parsing.parse_walmart",
    "target": "webpage_data_parsing.parse_target",
}


def detect_site(url):
    """Extract site key from URL hostname."""
    hostname = urlparse(url).hostname or ""
    hostname = hostname.lower()
    for key, site in SITE_MAP.items():
        if key in hostname:
            return site
    raise ValueError("Unknown site: %s" % hostname)


def get_parser(site):
    """Import and return the parser module for a site. Raises if not found."""
    module_name = PARSER_MAP.get(site)
    if not module_name:
        raise ValueError("No parser for site: %s" % site)
    import importlib
    return importlib.import_module(module_name)


def process_capture(data):
    """Main pipeline: parse JSON payload, run parser, upload to Dropbox."""
    url = data.get("url", "")
    html = data.get("html", "")
    category = data.get("category", "")
    screenshot_b64 = data.get("screenshot_b64", "")

    if not url:
        raise ValueError("Missing required field: url")
    if not html:
        raise ValueError("Missing required field: html")
    if not category:
        raise ValueError("Missing required field: category")

    site = detect_site(url)
    parser_mod = get_parser(site)

    base_name = build_base_name(site, category)
    site_dir = capitalize_site(site)
    folder_path = "%s/%s/%s" % (DROPBOX_BASE_PATH, site_dir, base_name)

    tmp_files = []
    try:
        # 1. Save capture JSON
        capture_data = {
            "url": url,
            "title": data.get("title", ""),
            "timestamp": data.get("timestamp", ""),
            "viewport": data.get("viewport", {}),
            "scrollHeight": data.get("scrollHeight", 0),
            "scrollY": data.get("scrollY", 0),
            "html": html,
        }
        json_fd, json_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(json_fd, "w", encoding="utf-8") as f:
            json.dump(capture_data, f)
        tmp_files.append(json_path)

        # 2. Save screenshot JPEG (if provided)
        img_path = None
        if screenshot_b64:
            img_fd, img_path = tempfile.mkstemp(suffix=".jpg")
            with os.fdopen(img_fd, "wb") as f:
                f.write(base64.b64decode(screenshot_b64))
            tmp_files.append(img_path)

        # 3. Parse HTML -> rows
        rows = parser_mod.parse_html_string(html, category)
        products_found = len(rows)

        # 4. Write CSV
        csv_fd, csv_path = tempfile.mkstemp(suffix=".csv")
        with os.fdopen(csv_fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=parser_mod.CSV_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        tmp_files.append(csv_path)

        # 5. Upload all to Dropbox (in parallel)
        dbx = get_dropbox_client()
        uploads = [
            (dbx, json_path, "%s/%s.json" % (folder_path, base_name)),
            (dbx, csv_path, "%s/%s.csv" % (folder_path, base_name)),
        ]
        if img_path:
            uploads.append((dbx, img_path, "%s/%s.jpg" % (folder_path, base_name)))

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(upload_file, *args) for args in uploads]
            for future in concurrent.futures.as_completed(futures):
                future.result()  # raises on failure

        return {
            "success": True,
            "products_found": products_found,
            "dropbox_folder": folder_path,
        }
    finally:
        for f in tmp_files:
            try:
                os.unlink(f)
            except OSError:
                pass


class CaptureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Capture server is running</h1>"
            b"<p>Use the bookmarklet to send captures here.</p></body></html>"
        )

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path != "/capture":
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
        except (json.JSONDecodeError, ValueError) as e:
            self._send_json(400, {"success": False, "error": "Invalid JSON: %s" % e})
            return

        try:
            result = process_capture(data)
            self._send_json(200, result)
        except Exception as e:
            self._send_json(500, {"success": False, "error": str(e)})

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, status, data):
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), format % args))


def main():
    server = HTTPServer(("localhost", 8585), CaptureHandler)
    print("Capture server running on http://localhost:8585")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
