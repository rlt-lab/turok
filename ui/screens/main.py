"""Main screen for Turok TUI."""

import time

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Input
from textual.worker import Worker, WorkerState

from core.models import TorrentResult
from core.search import SearchOrchestrator
from ui.widgets import Header, ResultsList, DetailsPanel, Footer


class MainScreen(Screen):
    """Main search and results screen."""

    BINDINGS = [
        ("slash", "focus_search", "Search"),
        ("escape", "cancel_search", "Cancel"),
        ("s", "cycle_sort", "Sort"),
        ("r", "refresh", "Refresh"),
        ("question_mark", "show_help", "Help"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.orchestrator = SearchOrchestrator()
        self._all_results: list[TorrentResult] = []
        self._sort_mode = "seeders"
        self._search_start_time = 0.0
        self._current_query = ""
        self._source_results: dict[str, list[TorrentResult]] = {}

    def compose(self) -> ComposeResult:
        yield Header(id="header")
        yield ResultsList(id="results-panel")
        yield DetailsPanel(id="details-panel")
        yield Footer(id="footer")

    def on_mount(self) -> None:
        """Focus search on mount."""
        self.query_one(Header).focus_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search submission."""
        if event.input.id == "search-input":
            query = event.value.strip()
            if query:
                self._current_query = query
                self._start_search(query)

    def _start_search(self, query: str) -> None:
        """Start searching across all sources."""
        self._search_start_time = time.time()
        self._all_results = []
        self._source_results = {}

        # Get source names
        sources = [s.name for s in self.orchestrator.sources]

        # Set loading state
        results_list = self.query_one(ResultsList)
        results_list.set_loading(sources)

        # Focus on results
        results_list.focus_list()

        # Start a worker for each source
        for source in self.orchestrator.sources:
            self.run_worker(
                self._search_source(source, query),
                name=f"search_{source.name}",
                thread=True,
            )

    async def _search_source(self, source, query: str) -> tuple[str, list[TorrentResult]]:
        """Search a single source (runs in thread)."""
        try:
            results = source.search(query)
            return (source.name, results)
        except Exception:
            return (source.name, [])

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes to update UI."""
        if not event.worker.name or not event.worker.name.startswith("search_"):
            return

        source_name = event.worker.name.replace("search_", "")
        results_list = self.query_one(ResultsList)

        if event.state == WorkerState.RUNNING:
            results_list.update_source(source_name, "loading")
        elif event.state == WorkerState.SUCCESS:
            result = event.worker.result
            if result:
                name, source_results = result
                self._source_results[name] = source_results
                results_list.update_source(name, "done", len(source_results))
            self._check_search_complete()
        elif event.state in (WorkerState.ERROR, WorkerState.CANCELLED):
            results_list.update_source(source_name, "error")
            self._check_search_complete()

    def _check_search_complete(self) -> None:
        """Check if all sources have completed and finalize results."""
        source_names = {s.name for s in self.orchestrator.sources}
        completed = set(self._source_results.keys())

        # Also count errors/cancellations
        for worker in self.workers:
            if worker.name and worker.name.startswith("search_"):
                name = worker.name.replace("search_", "")
                if worker.state in (WorkerState.ERROR, WorkerState.CANCELLED):
                    completed.add(name)

        if completed >= source_names:
            self._finish_search()

    def _finish_search(self) -> None:
        """Finish the search and display sorted results."""
        # Collect all results
        self._all_results = []
        for results in self._source_results.values():
            self._all_results.extend(results)

        # Sort results
        sorted_results = self.orchestrator._sort_results(
            self._all_results, self._sort_mode
        )

        # Update UI
        results_list = self.query_one(ResultsList)
        results_list.finish_loading(sorted_results)

        # Update timer
        elapsed = time.time() - self._search_start_time
        header = self.query_one(Header)
        header.search_time = elapsed

    def on_results_list_result_highlighted(
        self, event: ResultsList.ResultHighlighted
    ) -> None:
        """Update details panel when a result is highlighted."""
        details = self.query_one(DetailsPanel)
        details.result = event.result

    def action_focus_search(self) -> None:
        """Focus the search input."""
        self.query_one(Header).focus_search()

    def action_cancel_search(self) -> None:
        """Cancel search and return to results."""
        self.query_one(ResultsList).focus_list()

    def action_cycle_sort(self) -> None:
        """Cycle through sort modes."""
        modes = ["seeders", "size", "name"]
        current_idx = modes.index(self._sort_mode)
        self._sort_mode = modes[(current_idx + 1) % len(modes)]

        # Update header
        header = self.query_one(Header)
        header.sort_mode = self._sort_mode

        # Re-sort current results
        if self._all_results:
            sorted_results = self.orchestrator._sort_results(
                self._all_results, self._sort_mode
            )
            self.query_one(ResultsList).finish_loading(sorted_results)

    def action_refresh(self) -> None:
        """Refresh the current search."""
        if self._current_query:
            self._start_search(self._current_query)

    def action_show_help(self) -> None:
        """Show the help overlay."""
        from .help import HelpScreen

        self.app.push_screen(HelpScreen())

    def get_selected_result(self) -> TorrentResult | None:
        """Get the currently selected result."""
        return self.query_one(ResultsList).get_selected()
