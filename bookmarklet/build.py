"""Build page-capture bookmarklets. Usage: python bookmarklet/build.py"""
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent

def minify(js):
    """Collapse whitespace to produce a single-line bookmarklet."""
    import re
    # Remove single-line comments (but not URLs like http:// or https://)
    js = re.sub(r'(?<![:\"\'])//.*', '', js)
    # Collapse all whitespace (newlines, tabs, multiple spaces) to single spaces
    js = re.sub(r'\s+', ' ', js).strip()
    return js

def main():
    # Original capture-only bookmarklet
    capture_js = (ROOT / "capture.js").read_text()
    print("=== Capture Only (saves file locally) ===")
    print(f"javascript:{quote(minify(capture_js), safe='')}")
    print()

    # Capture + auto-upload bookmarklet
    upload_js = (ROOT / "capture_and_upload.js").read_text()
    print("=== Capture & Upload (sends to local server + Dropbox) ===")
    print(f"javascript:{quote(minify(upload_js), safe='')}")

if __name__ == "__main__":
    main()
