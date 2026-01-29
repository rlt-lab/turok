"""Dynamic source that uses configuration to scrape any site."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..config import SiteConfig
from ..models import TorrentResult
from .base import Source, add_trackers, parse_size


class DynamicSource(Source):
    """A torrent source that uses SiteConfig to scrape any site."""

    def __init__(self, config: SiteConfig):
        self.config = config
        self.name = config.name

    def search(self, query: str) -> list[TorrentResult]:
        """Search the configured site."""
        results = []
        try:
            # Build search URL
            url = self.config.search.url_template.format(
                base_url=self.config.base_url,
                query=query.replace(" ", "+"),
            )

            resp = self._get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find result items
            items = soup.select(self.config.selectors.result_item)

            for item in items[:30]:  # Limit results
                result = self._parse_result(item)
                if result:
                    results.append(result)

        except Exception:
            pass
        return results

    def _parse_result(self, item) -> TorrentResult | None:
        """Parse a single result item into a TorrentResult."""
        selectors = self.config.selectors

        # Get title and link
        title_elem = item.select_one(selectors.title)
        if not title_elem:
            return None

        title = title_elem.get_text(strip=True)
        if not title:
            return None

        # Get link (either from title_link selector or from title element)
        link_elem = (
            item.select_one(selectors.title_link)
            if selectors.title_link
            else title_elem
        )
        detail_url = None
        if link_elem and link_elem.name == "a":
            href = link_elem.get("href", "")
            if href:
                detail_url = urljoin(self.config.base_url, href)
        elif link_elem:
            # Maybe it's inside an <a> tag
            a_tag = link_elem.find_parent("a") or link_elem.find("a")
            if a_tag:
                href = a_tag.get("href", "")
                if href:
                    detail_url = urljoin(self.config.base_url, href)

        # Get size if selector available
        size = 0
        if selectors.size:
            size_elem = item.select_one(selectors.size)
            if size_elem:
                size = parse_size(size_elem.get_text(strip=True))

        # Get seeders if selector available
        seeders = 0
        if selectors.seeders:
            seeders_elem = item.select_one(selectors.seeders)
            if seeders_elem:
                try:
                    seeders = int(seeders_elem.get_text(strip=True))
                except ValueError:
                    pass

        # Get leechers if selector available
        leechers = 0
        if selectors.leechers:
            leechers_elem = item.select_one(selectors.leechers)
            if leechers_elem:
                try:
                    leechers = int(leechers_elem.get_text(strip=True))
                except ValueError:
                    pass

        # Check for magnet link directly in search results
        magnet_elem = item.select_one(selectors.magnet)
        magnet_link = None
        if magnet_elem:
            href = magnet_elem.get("href", "")
            if href.startswith("magnet:"):
                magnet_link = href

        return TorrentResult(
            title=title,
            seeders=seeders,
            leechers=leechers,
            size=size,
            detail_url=detail_url,
            magnet_link=magnet_link,
            source=self.name,
        )

    def get_magnet(self, result: TorrentResult) -> str | None:
        """Get magnet link for a result, fetching from detail page if needed."""
        if result.magnet_link:
            return add_trackers(result.magnet_link)

        if not result.detail_url:
            return None

        try:
            resp = self._get(result.detail_url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find magnet link
            magnet_elem = soup.select_one(self.config.selectors.magnet)
            if magnet_elem:
                href = magnet_elem.get("href", "")
                if href.startswith("magnet:"):
                    result.magnet_link = href

                    # Try to extract size if not already set
                    if result.size == 0:
                        self._extract_size(soup, result)

                    return add_trackers(href)

        except Exception:
            pass
        return None

    def _extract_size(self, soup: BeautifulSoup, result: TorrentResult) -> None:
        """Extract file size from page content using regex pattern."""
        content = soup.get_text()
        size_pattern = re.search(
            self.config.patterns.size_regex,
            content,
            re.IGNORECASE,
        )
        if size_pattern:
            result.size = parse_size(size_pattern.group(1))
