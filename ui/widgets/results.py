"""Results list widget."""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static, ListItem, ListView

from core.models import TorrentResult


def format_number(n: int) -> str:
    """Format number with comma separators."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


class ResultItem(ListItem):
    """A single result in the list."""

    class Selected(Message):
        """Message when a result is selected."""

        def __init__(self, result: TorrentResult) -> None:
            self.result = result
            super().__init__()

    def __init__(self, result: TorrentResult, **kwargs) -> None:
        super().__init__(**kwargs)
        self.result = result
        self.add_class("result-item")

    def compose(self) -> ComposeResult:
        r = self.result
        yield Static(r.title, classes="result-title")
        meta = f"{r.size_formatted}  ·  {r.source}  ·  {format_number(r.seeders)} ↑  {format_number(r.leechers)} ↓"
        yield Static(meta, classes="result-meta")
        with Horizontal(classes="health-bar"):
            health_width = self._calc_health_width()
            yield Static(
                "━" * health_width,
                classes=f"health-bar-fill {r.health}",
            )
            yield Static(f" health: {r.health}", classes="health-label")

    def _calc_health_width(self) -> int:
        """Calculate the health bar width based on health status."""
        health_widths = {
            "excellent": 40,
            "good": 30,
            "fair": 20,
            "poor": 10,
            "dead": 3,
        }
        return health_widths.get(self.result.health, 10)


class SourceStatus(Static):
    """Status indicator for a search source."""

    def __init__(self, name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.source_name = name
        self.add_class("source-status")
        self._status = "pending"
        self._count = 0

    def set_status(self, status: str, count: int = 0) -> None:
        """Update the source status."""
        self._status = status
        self._count = count
        self.remove_class("pending", "loading", "done", "error")
        self.add_class(status)
        self._update_display()

    def _update_display(self) -> None:
        icons = {
            "pending": "○",
            "loading": "◐",
            "done": "✓",
            "error": "✗",
        }
        icon = icons.get(self._status, "○")
        if self._status == "done":
            text = f"{icon} {self.source_name:<10} {self._count} results"
        elif self._status == "loading":
            text = f"{icon} {self.source_name:<10} loading..."
        elif self._status == "error":
            text = f"{icon} {self.source_name:<10} error"
        else:
            text = f"{icon} {self.source_name:<10}"
        self.update(text)


class ResultsList(Vertical):
    """Scrollable list of search results with streaming support."""

    results = reactive(list, always_update=True)
    is_loading = reactive(False)

    class ResultHighlighted(Message):
        """Message when a result is highlighted."""

        def __init__(self, result: TorrentResult | None) -> None:
            self.result = result
            super().__init__()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._source_statuses: dict[str, SourceStatus] = {}
        self._results: list[TorrentResult] = []

    def compose(self) -> ComposeResult:
        yield Static("Results", id="results-title")
        yield ListView(id="results-list")

    def on_mount(self) -> None:
        """Set up the list view."""
        list_view = self.query_one("#results-list", ListView)
        list_view.can_focus = True

    def set_loading(self, sources: list[str]) -> None:
        """Show loading state for sources."""
        self.is_loading = True
        self._results = []
        list_view = self.query_one("#results-list", ListView)
        list_view.clear()

        # Create source status widgets
        self._source_statuses = {}
        for source in sources:
            status = SourceStatus(source)
            status.set_status("loading")
            self._source_statuses[source] = status
            list_view.append(ListItem(status))

        self._update_title(0)

    def update_source(self, source: str, status: str, count: int = 0) -> None:
        """Update status for a specific source."""
        if source in self._source_statuses:
            self._source_statuses[source].set_status(status, count)

    def add_results(self, results: list[TorrentResult]) -> None:
        """Add results from a source."""
        self._results.extend(results)

    def finish_loading(self, sorted_results: list[TorrentResult]) -> None:
        """Finish loading and display sorted results."""
        self.is_loading = False
        self._results = sorted_results

        list_view = self.query_one("#results-list", ListView)
        list_view.clear()
        self._source_statuses = {}

        for result in sorted_results:
            list_view.append(ResultItem(result))

        self._update_title(len(sorted_results))

        # Select first item if available
        if sorted_results:
            list_view.index = 0

    def _update_title(self, count: int) -> None:
        """Update the results title with count."""
        title = self.query_one("#results-title", Static)
        if self.is_loading:
            title.update(f"Results (searching...)")
        elif count > 0:
            title.update(f"Results ({count} found)")
        else:
            title.update("Results")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Handle result highlight."""
        if event.item and isinstance(event.item, ResultItem):
            self.post_message(self.ResultHighlighted(event.item.result))
        else:
            self.post_message(self.ResultHighlighted(None))

    def get_selected(self) -> TorrentResult | None:
        """Get the currently selected result."""
        list_view = self.query_one("#results-list", ListView)
        if list_view.highlighted_child and isinstance(
            list_view.highlighted_child, ResultItem
        ):
            return list_view.highlighted_child.result
        return None

    def focus_list(self) -> None:
        """Focus the results list."""
        self.query_one("#results-list", ListView).focus()
