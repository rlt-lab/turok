"""Header widget with title, search input, and indicators."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widgets import Input, Static


class Header(Static):
    """Header with title, search input, sort indicator, and timer."""

    sort_mode = reactive("seeders")
    search_time = reactive(0.0)

    SORT_LABELS = {
        "seeders": "↕ Seeders",
        "size": "↕ Size",
        "name": "↕ Name",
    }

    def compose(self) -> ComposeResult:
        yield Static("🦖 TUROK", id="title")
        with Horizontal(id="search-row"):
            yield Static("🔍 ", id="search-icon")
            yield Input(placeholder="Search torrents...", id="search-input")
            yield Static(self.SORT_LABELS[self.sort_mode], id="sort-indicator")
            yield Static("", id="timer")

    def watch_sort_mode(self, mode: str) -> None:
        """Update sort indicator when mode changes."""
        try:
            indicator = self.query_one("#sort-indicator", Static)
            indicator.update(self.SORT_LABELS.get(mode, "↕ Seeders"))
        except Exception:
            pass

    def watch_search_time(self, time: float) -> None:
        """Update timer display."""
        try:
            timer = self.query_one("#timer", Static)
            if time > 0:
                timer.update(f"⏱ {time:.1f}s")
            else:
                timer.update("")
        except Exception:
            pass

    def focus_search(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", Input).focus()

    def get_search_query(self) -> str:
        """Get the current search query."""
        return self.query_one("#search-input", Input).value

    def set_search_query(self, query: str) -> None:
        """Set the search query."""
        self.query_one("#search-input", Input).value = query
