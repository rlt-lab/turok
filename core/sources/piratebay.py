"""The Pirate Bay torrent source."""

from ..models import TorrentResult
from .base import Source


class PirateBaySource(Source):
    """The Pirate Bay torrent source via apibay."""

    name = "TPB"

    def search(self, query: str) -> list[TorrentResult]:
        """Search The Pirate Bay via apibay."""
        results = []
        try:
            url = f"https://apibay.org/q.php?q={query.replace(' ', '+')}"
            resp = self._get(url)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list) and data and data[0].get("id") != "0":
                for item in data[:30]:
                    info_hash = item.get("info_hash", "")
                    name = item.get("name", "")
                    if not info_hash or not name:
                        continue

                    magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={name}"
                    results.append(
                        TorrentResult(
                            title=name,
                            seeders=int(item.get("seeders", 0)),
                            leechers=int(item.get("leechers", 0)),
                            size=int(item.get("size", 0)),
                            detail_url=None,
                            magnet_link=magnet,
                            source=self.name,
                        )
                    )
        except Exception:
            pass
        return results
