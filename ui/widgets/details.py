"""Details panel widget."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static

from core.models import TorrentResult


class DetailsPanel(Static):
    """Panel showing details of the selected torrent."""

    result: reactive[TorrentResult | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static("Select a torrent to view details", id="details-title")
        with Vertical(id="details-grid"):
            with Horizontal():
                yield Static("Size", classes="detail-label")
                yield Static("-", classes="detail-value", id="detail-size")
                yield Static("Category", classes="detail-label")
                yield Static("-", classes="detail-value", id="detail-category")
            with Horizontal():
                yield Static("Seeders", classes="detail-label")
                yield Static("-", classes="detail-value", id="detail-seeders")
                yield Static("Uploaded", classes="detail-label")
                yield Static("-", classes="detail-value", id="detail-uploaded")
            with Horizontal():
                yield Static("Leechers", classes="detail-label")
                yield Static("-", classes="detail-value", id="detail-leechers")
                yield Static("Source", classes="detail-label")
                yield Static("-", classes="detail-value", id="detail-source")
        yield Static("", id="magnet-preview")

    def watch_result(self, result: TorrentResult | None) -> None:
        """Update display when result changes."""
        if result is None:
            self._clear_display()
            return

        self.query_one("#details-title", Static).update(result.title)
        self.query_one("#detail-size", Static).update(result.size_formatted)
        self.query_one("#detail-category", Static).update(result.category or "-")
        self.query_one("#detail-seeders", Static).update(f"{result.seeders:,}")
        self.query_one("#detail-uploaded", Static).update(result.uploaded or "-")
        self.query_one("#detail-leechers", Static).update(f"{result.leechers:,}")
        self.query_one("#detail-source", Static).update(result.source)

        # Show truncated magnet preview
        magnet = result.magnet_link
        if magnet:
            preview = magnet[:60] + "..." if len(magnet) > 60 else magnet
            self.query_one("#magnet-preview", Static).update(f"Magnet: {preview}")
        else:
            self.query_one("#magnet-preview", Static).update(
                "Magnet: (press Enter to fetch)"
            )

    def _clear_display(self) -> None:
        """Clear the details display."""
        self.query_one("#details-title", Static).update(
            "Select a torrent to view details"
        )
        self.query_one("#detail-size", Static).update("-")
        self.query_one("#detail-category", Static).update("-")
        self.query_one("#detail-seeders", Static).update("-")
        self.query_one("#detail-uploaded", Static).update("-")
        self.query_one("#detail-leechers", Static).update("-")
        self.query_one("#detail-source", Static).update("-")
        self.query_one("#magnet-preview", Static).update("")
