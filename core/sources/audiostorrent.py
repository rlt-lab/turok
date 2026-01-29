"""Audiostorrent.com source for audio software torrents."""

import re

from bs4 import BeautifulSoup

from ..models import TorrentResult
from .base import Source, add_trackers, parse_size


class AudiostorrentSource(Source):
    """audiostorrent.com torrent source for audio software."""

    name = "Audiostorrent"

    def search(self, query: str) -> list[TorrentResult]:
        """Search audiostorrent.com via scraping."""
        results = []
        try:
            url = f"https://audiostorrent.com/?s={query.replace(' ', '+')}"
            resp = self._get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find all article links - WordPress search results
            articles = soup.select("article")
            for article in articles[:30]:
                title_elem = article.select_one("h2 a, .entry-title a")
                if not title_elem:
                    continue

                title = title_elem.text.strip()
                detail_url = title_elem.get("href", "")

                if not detail_url:
                    continue

                results.append(
                    TorrentResult(
                        title=title,
                        seeders=0,  # Not available on search page
                        leechers=0,
                        size=0,  # Need to fetch from detail page
                        detail_url=detail_url,
                        magnet_link=None,
                        source=self.name,
                    )
                )
        except Exception:
            pass
        return results

    def get_magnet(self, result: TorrentResult) -> str | None:
        """Fetch magnet link from audiostorrent detail page."""
        if result.magnet_link:
            return add_trackers(result.magnet_link)

        if not result.detail_url:
            return None

        try:
            resp = self._get(result.detail_url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find magnet link
            magnet_elem = soup.select_one("a[href^='magnet:']")
            if magnet_elem:
                magnet = magnet_elem["href"]
                result.magnet_link = magnet

                # Try to extract size from page content
                if result.size == 0:
                    self._extract_size(soup, result)

                return add_trackers(magnet)
        except Exception:
            pass
        return None

    def _extract_size(self, soup: BeautifulSoup, result: TorrentResult) -> None:
        """Extract file size from page content."""
        # Look for size patterns like "1.24 GB" or "Size: 500 MB"
        content = soup.get_text()
        size_pattern = re.search(
            r"(?:size[:\s]*)?(\d+(?:\.\d+)?\s*(?:GB|MB|KB|TB))",
            content,
            re.IGNORECASE,
        )
        if size_pattern:
            result.size = parse_size(size_pattern.group(1))
