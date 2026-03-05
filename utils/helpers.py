import asyncio
import random
import socket
import urllib.robotparser
from urllib.parse import urlparse


def is_path_allowed(site_url: str, path: str) -> bool:
    parsed = urlparse(site_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    old_timeout = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(10)
        rp.read()
    except OSError:
        print(f"[warning] Could not fetch robots.txt from {parsed.netloc} — allowing by default.")
        return True
    finally:
        socket.setdefaulttimeout(old_timeout)
    return rp.can_fetch("*", f"{parsed.scheme}://{parsed.netloc}{path}")


async def random_delay(min: float = 2.0, max: float = 5.0) -> None:
    await asyncio.sleep(random.uniform(min, max))
