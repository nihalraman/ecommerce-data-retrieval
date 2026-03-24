"""Build site-agnostic page-capture bookmarklet. Usage: python bookmarklet/build.py"""
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent

def minify(js):
    """Collapse whitespace to produce a single-line bookmarklet."""
    import re
    # Remove single-line comments
    js = re.sub(r'//.*', '', js)
    # Collapse all whitespace (newlines, tabs, multiple spaces) to single spaces
    js = re.sub(r'\s+', ' ', js).strip()
    return js

def main():
    js_code = (ROOT / "capture.js").read_text()
    print(f"javascript:{quote(minify(js_code), safe='')}")

if __name__ == "__main__":
    main()
