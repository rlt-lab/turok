"""Base class for torrent sources."""

import re
from abc import ABC, abstractmethod
from urllib.parse import quote

import requests

from ..models import TorrentResult

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TIMEOUT = 15

TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.bittor.pw:1337/announce",
    "udp://public.popcorn-tracker.org:6969/announce",
    "udp://tracker.dler.org:6969/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://open.demonii.com:1337/announce",
]


def add_trackers(magnet: str) -> str:
    """Add public trackers to a magnet link if missing."""
    if not magnet or "&tr=" in magnet:
        return magnet
    tracker_params = "".join(f"&tr={quote(t, safe='')}" for t in TRACKERS)
    return magnet + tracker_params


def parse_size(size_str: str) -> int:
    """Parse size string like '1.5 GB' to bytes."""
    size_str = size_str.upper().strip()
    match = re.match(r"([\d.]+)\s*(B|KB|MB|GB|TB|KIB|MIB|GIB|TIB)", size_str)
    if not match:
        return 0
    value = float(match.group(1))
    unit = match.group(2)
    multipliers = {
        "B": 1,
        "KB": 1024,
        "KIB": 1024,
        "MB": 1024**2,
        "MIB": 1024**2,
        "GB": 1024**3,
        "GIB": 1024**3,
        "TB": 1024**4,
        "TIB": 1024**4,
    }
    return int(value * multipliers.get(unit, 1))


class Source(ABC):
    """Abstract base class for torrent sources."""

    name: str = "Unknown"

    @abstractmethod
    def search(self, query: str) -> list[TorrentResult]:
        """Search for torrents matching the query."""
        ...

    def get_magnet(self, result: TorrentResult) -> str | None:
        """Get magnet link for a result, fetching if needed."""
        if result.magnet_link:
            return add_trackers(result.magnet_link)
        return None

    def _get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request with standard headers."""
        return requests.get(url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
