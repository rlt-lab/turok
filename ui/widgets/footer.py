"""Footer widget with keybinding hints."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static


class Footer(Static):
    """Footer with keybinding hints."""

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static("/", classes="keyhint-key")
            yield Static("search  ", classes="keyhint")
            yield Static("↑↓", classes="keyhint-key")
            yield Static("navigate  ", classes="keyhint")
            yield Static("enter", classes="keyhint-key")
            yield Static("download  ", classes="keyhint")
            yield Static("y", classes="keyhint-key")
            yield Static("copy  ", classes="keyhint")
            yield Static("s", classes="keyhint-key")
            yield Static("sort  ", classes="keyhint")
            yield Static("?", classes="keyhint-key")
            yield Static("help  ", classes="keyhint")
            yield Static("q", classes="keyhint-key")
            yield Static("quit", classes="keyhint")
