"""RARBG torrent source."""

import time

from ..models import TorrentResult
from .base import Source


class RarbgSource(Source):
    """RARBG torrent source via torrentapi."""

    name = "RARBG"

    def search(self, query: str) -> list[TorrentResult]:
        """Search RARBG via torrentapi."""
        results = []
        try:
            # torrentapi requires a token first
            token_resp = self._get(
                "https://torrentapi.org/pubapi_v2.php?get_token=get_token&app_id=turok"
            )
            token_data = token_resp.json()
            token = token_data.get("token")
            if not token:
                return results

            time.sleep(2)  # API rate limit

            url = f"https://torrentapi.org/pubapi_v2.php?mode=search&search_string={query.replace(' ', '+')}&format=json_extended&app_id=turok&token={token}"
            resp = self._get(url)
            data = resp.json()

            if "torrent_results" in data:
                for item in data["torrent_results"][:30]:
                    results.append(
                        TorrentResult(
                            title=item.get("title", ""),
                            seeders=int(item.get("seeders", 0)),
                            leechers=int(item.get("leechers", 0)),
                            size=int(item.get("size", 0)),
                            detail_url=None,
                            magnet_link=item.get("download", ""),
                            source=self.name,
                        )
                    )
        except Exception:
            pass
        return results
