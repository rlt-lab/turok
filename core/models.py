"""Data models for Turok."""

from dataclasses import dataclass


@dataclass
class TorrentResult:
    """A single torrent search result."""

    title: str
    seeders: int
    leechers: int
    size: int  # bytes
    source: str  # "1337x", "TPB", "RARBG"
    magnet_link: str | None = None
    detail_url: str | None = None
    category: str | None = None
    uploaded: str | None = None
    uploader: str | None = None

    @property
    def health(self) -> str:
        """Calculate health based on seeder/leecher ratio."""
        if self.seeders == 0:
            return "dead"
        ratio = self.seeders / max(self.leechers, 1)
        if self.seeders > 100 and ratio > 2:
            return "excellent"
        if self.seeders > 20 and ratio > 1:
            return "good"
        if self.seeders > 5:
            return "fair"
        return "poor"

    @property
    def size_formatted(self) -> str:
        """Format bytes to human-readable size."""
        size_bytes = self.size
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} PB"
