"""Turok TUI Application."""

import platform
import subprocess
import webbrowser
from pathlib import Path

from textual.app import App
from textual.widgets import ListView

from core.search import SearchOrchestrator
from ui.screens import MainScreen


class TurokApp(App):
    """Turok TUI Application."""

    TITLE = "Turok"
    CSS_PATH = Path(__file__).parent / "styles.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("enter", "download", "Download"),
        ("y", "copy_magnet", "Copy Magnet"),
        ("o", "open_browser", "Open in Browser"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        ("g", "cursor_first", "First"),
        ("G", "cursor_last", "Last"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orchestrator = SearchOrchestrator()

    def on_mount(self) -> None:
        """Push the main screen on mount."""
        self.push_screen(MainScreen())

    def action_download(self) -> None:
        """Download the selected torrent."""
        main_screen = self._get_main_screen()
        if not main_screen:
            return

        result = main_screen.get_selected_result()
        if not result:
            self.notify("No torrent selected", severity="warning")
            return

        # Get magnet link (may need to fetch)
        self.run_worker(self._download_torrent(result))

    async def _download_torrent(self, result) -> None:
        """Download a torrent asynchronously."""
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor() as executor:
            magnet = await self.run_in_executor(
                executor, self.orchestrator.get_magnet, result
            )

        if not magnet:
            self.notify(f"Could not get magnet link for: {result.title}", severity="error")
            return

        if self._open_magnet(magnet):
            self.notify(f"Sent to torrent client: {result.title}", severity="information")
        else:
            self.notify(f"Failed to open magnet link", severity="error")

    def _open_magnet(self, magnet: str) -> bool:
        """Open magnet link using system protocol handler."""
        try:
            system = platform.system()
            if system == "Darwin":
                subprocess.run(["open", magnet], check=True, capture_output=True)
            elif system == "Linux":
                subprocess.run(["xdg-open", magnet], check=True, capture_output=True)
            elif system == "Windows":
                subprocess.run(
                    ["start", "", magnet], shell=True, check=True, capture_output=True
                )
            else:
                return False
            return True
        except subprocess.CalledProcessError:
            return False

    def action_copy_magnet(self) -> None:
        """Copy magnet link to clipboard."""
        main_screen = self._get_main_screen()
        if not main_screen:
            return

        result = main_screen.get_selected_result()
        if not result:
            self.notify("No torrent selected", severity="warning")
            return

        # Get magnet and copy
        self.run_worker(self._copy_magnet(result))

    async def _copy_magnet(self, result) -> None:
        """Copy magnet to clipboard asynchronously."""
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor() as executor:
            magnet = await self.run_in_executor(
                executor, self.orchestrator.get_magnet, result
            )

        if not magnet:
            self.notify(f"Could not get magnet link", severity="error")
            return

        try:
            import pyperclip

            pyperclip.copy(magnet)
            self.notify("Magnet link copied to clipboard", severity="information")
        except ImportError:
            self.notify(
                "pyperclip not installed - cannot copy to clipboard", severity="error"
            )
        except Exception as e:
            self.notify(f"Failed to copy: {e}", severity="error")

    def action_open_browser(self) -> None:
        """Open detail page in browser."""
        main_screen = self._get_main_screen()
        if not main_screen:
            return

        result = main_screen.get_selected_result()
        if not result:
            self.notify("No torrent selected", severity="warning")
            return

        if result.detail_url:
            webbrowser.open(result.detail_url)
            self.notify(f"Opened in browser", severity="information")
        else:
            self.notify("No detail URL available for this torrent", severity="warning")

    def action_cursor_down(self) -> None:
        """Move cursor down in the list."""
        self._move_cursor(1)

    def action_cursor_up(self) -> None:
        """Move cursor up in the list."""
        self._move_cursor(-1)

    def action_cursor_first(self) -> None:
        """Move cursor to first item."""
        try:
            list_view = self.query_one("#results-list", ListView)
            if list_view.children:
                list_view.index = 0
        except Exception:
            pass

    def action_cursor_last(self) -> None:
        """Move cursor to last item."""
        try:
            list_view = self.query_one("#results-list", ListView)
            if list_view.children:
                list_view.index = len(list_view.children) - 1
        except Exception:
            pass

    def _move_cursor(self, delta: int) -> None:
        """Move the cursor by delta positions."""
        try:
            list_view = self.query_one("#results-list", ListView)
            if list_view.children:
                new_index = list_view.index + delta
                new_index = max(0, min(new_index, len(list_view.children) - 1))
                list_view.index = new_index
        except Exception:
            pass

    def _get_main_screen(self) -> MainScreen | None:
        """Get the main screen if it's active."""
        if isinstance(self.screen, MainScreen):
            return self.screen
        return None

    async def run_in_executor(self, executor, func, *args):
        """Run a function in an executor."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, func, *args)
