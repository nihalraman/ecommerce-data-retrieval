"""Build bookmarklets per site. Usage: python bookmarklet/build.py [--site costco]"""
import json, sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent.parent

def main():
    js_code = (ROOT / "core" / "extractVirtualPlanogram.js").read_text()
    sites = json.loads((ROOT / "config" / "sites.json").read_text())
    filter_site = sys.argv[sys.argv.index("--site") + 1] if "--site" in sys.argv else None

    if filter_site and filter_site not in sites:
        raise ValueError(f"Site '{filter_site}' not found in config/sites.json. Available sites: {', '.join(sites)}")

    for name, config in sites.items():
        if filter_site and name != filter_site:
            continue
        cfg_json = json.dumps(config, separators=(",", ":"))
        payload = (
            "(function(){" + js_code +
            ";var r=extractVirtualPlanogram(" + cfg_json + ");" +
            "var b=new Blob([JSON.stringify(r,null,2)],{type:'application/json'});" +
            "var a=document.createElement('a');" +
            "a.href=URL.createObjectURL(b);" +
            "a.download='" + name + "_planogram.json';" +
            "a.click();})()"
        )
        print(f"=== {name} ===\njavascript:{quote(payload, safe='')}\n")

if __name__ == "__main__":
    main()
