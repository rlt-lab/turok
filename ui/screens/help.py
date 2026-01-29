"""Help overlay screen."""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal, Center
from textual.screen import ModalScreen
from textual.widgets import Static


class HelpScreen(ModalScreen):
    """Modal help screen with keybinding reference."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("question_mark", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Center(id="help-overlay"):
            with Vertical(id="help-container"):
                yield Static("🦖 TUROK HELP", id="help-title")

                with Vertical(classes="help-section"):
                    yield Static("Navigation", classes="help-section-title")
                    yield self._help_row("↑ / k", "Move selection up")
                    yield self._help_row("↓ / j", "Move selection down")
                    yield self._help_row("g / Home", "Jump to first result")
                    yield self._help_row("G / End", "Jump to last result")
                    yield self._help_row("Tab", "Cycle focus between panels")

                with Vertical(classes="help-section"):
                    yield Static("Actions", classes="help-section-title")
                    yield self._help_row("Enter", "Download selected torrent")
                    yield self._help_row("y", "Copy magnet link to clipboard")
                    yield self._help_row("o", "Open detail page in browser")
                    yield self._help_row("r", "Refresh search results")

                with Vertical(classes="help-section"):
                    yield Static("Search & Sort", classes="help-section-title")
                    yield self._help_row("/", "Focus search input")
                    yield self._help_row("Esc", "Cancel search, return to results")
                    yield self._help_row("s", "Cycle sort: Seeders → Size → Name")

                with Vertical(classes="help-section"):
                    yield Static("General", classes="help-section-title")
                    yield self._help_row("?", "Show this help")
                    yield self._help_row("q", "Quit")

                yield Static("")
                yield Static(
                    "Press Esc or ? to close",
                    id="help-close-hint",
                )

    def _help_row(self, key: str, desc: str) -> Horizontal:
        """Create a help row with key and description."""
        return Horizontal(
            Static(key, classes="help-key"),
            Static(desc, classes="help-desc"),
            classes="help-row",
        )

    def action_dismiss(self) -> None:
        """Close the help screen."""
        self.app.pop_screen()
