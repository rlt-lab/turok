"""1337x torrent source."""

from bs4 import BeautifulSoup

from ..models import TorrentResult
from .base import Source, add_trackers, parse_size


class X1337Source(Source):
    """1337x.to torrent source."""

    name = "1337x"

    def search(self, query: str) -> list[TorrentResult]:
        """Search 1337x.to via scraping."""
        results = []
        try:
            url = f"https://1337x.to/search/{query.replace(' ', '+')}/1/"
            resp = self._get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            rows = soup.select("tbody tr")
            for row in rows[:30]:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                title_link = cols[0].select_one("a:nth-of-type(2)")
                if not title_link:
                    continue

                title = title_link.text.strip()
                detail_url = "https://1337x.to" + title_link["href"]

                seeders = (
                    int(cols[1].text.strip())
                    if cols[1].text.strip().isdigit()
                    else 0
                )
                leechers = (
                    int(cols[2].text.strip())
                    if cols[2].text.strip().isdigit()
                    else 0
                )
                size_text = cols[4].text.strip().split()[0:2]
                size = parse_size(" ".join(size_text)) if size_text else 0

                results.append(
                    TorrentResult(
                        title=title,
                        seeders=seeders,
                        leechers=leechers,
                        size=size,
                        detail_url=detail_url,
                        magnet_link=None,
                        source=self.name,
                    )
                )
        except Exception:
            pass
        return results

    def get_magnet(self, result: TorrentResult) -> str | None:
        """Fetch magnet link from 1337x detail page."""
        if result.magnet_link:
            return add_trackers(result.magnet_link)

        if not result.detail_url:
            return None

        try:
            resp = self._get(result.detail_url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            magnet_link = soup.select_one("a[href^='magnet:']")
            if magnet_link:
                magnet = magnet_link["href"]
                result.magnet_link = magnet
                return add_trackers(magnet)
        except Exception:
            pass
        return None
