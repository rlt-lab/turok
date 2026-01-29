"""Search orchestration for Turok."""

import asyncio
from collections.abc import AsyncIterator, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from .models import TorrentResult
from .sources import PirateBaySource, RarbgSource, Source, X1337Source
from .sources.base import add_trackers


@dataclass
class SourceStatus:
    """Status of a source search."""

    name: str
    status: str  # "pending", "loading", "done", "error"
    count: int = 0
    error: str | None = None


@dataclass
class SearchUpdate:
    """An update from the search orchestrator."""

    source: str
    status: str
    results: list[TorrentResult]
    error: str | None = None


class SearchOrchestrator:
    """Orchestrates searches across multiple sources."""

    def __init__(self):
        self.sources: list[Source] = [
            X1337Source(),
            PirateBaySource(),
            RarbgSource(),
        ]
        self._source_map = {s.name: s for s in self.sources}

    def search_sync(
        self, query: str, limit: int = 50, sort_by: str = "seeders"
    ) -> list[TorrentResult]:
        """Synchronous search across all sources."""
        all_results = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(s.search, query): s for s in self.sources}

            for future in futures:
                try:
                    results = future.result()
                    all_results.extend(results)
                except Exception:
                    pass

        return self._sort_results(all_results, sort_by)[:limit]

    async def search_streaming(
        self, query: str, callback: Callable[[SearchUpdate], Any]
    ) -> list[TorrentResult]:
        """Search with streaming updates via callback."""
        all_results: list[TorrentResult] = []
        loop = asyncio.get_event_loop()

        async def search_source(source: Source):
            try:
                # Run the blocking search in a thread
                results = await loop.run_in_executor(None, source.search, query)
                all_results.extend(results)
                callback(
                    SearchUpdate(
                        source=source.name,
                        status="done",
                        results=results,
                    )
                )
            except Exception as e:
                callback(
                    SearchUpdate(
                        source=source.name,
                        status="error",
                        results=[],
                        error=str(e),
                    )
                )

        # Notify that all sources are starting
        for source in self.sources:
            callback(
                SearchUpdate(
                    source=source.name,
                    status="loading",
                    results=[],
                )
            )

        # Run all searches concurrently
        await asyncio.gather(*[search_source(s) for s in self.sources])

        return all_results

    async def search_streaming_iter(
        self, query: str
    ) -> AsyncIterator[SearchUpdate]:
        """Search with streaming updates via async iterator."""
        loop = asyncio.get_event_loop()
        queue: asyncio.Queue[SearchUpdate | None] = asyncio.Queue()

        async def search_source(source: Source):
            try:
                results = await loop.run_in_executor(None, source.search, query)
                await queue.put(
                    SearchUpdate(
                        source=source.name,
                        status="done",
                        results=results,
                    )
                )
            except Exception as e:
                await queue.put(
                    SearchUpdate(
                        source=source.name,
                        status="error",
                        results=[],
                        error=str(e),
                    )
                )

        # Start all searches
        for source in self.sources:
            yield SearchUpdate(
                source=source.name,
                status="loading",
                results=[],
            )

        # Create tasks for all sources
        tasks = [asyncio.create_task(search_source(s)) for s in self.sources]

        # Yield results as they come in
        completed = 0
        while completed < len(self.sources):
            update = await queue.get()
            if update:
                completed += 1
                yield update

        # Ensure all tasks are done
        await asyncio.gather(*tasks)

    def get_magnet(self, result: TorrentResult) -> str | None:
        """Get magnet link for a result, fetching if needed."""
        source = self._source_map.get(result.source)
        if source:
            return source.get_magnet(result)
        if result.magnet_link:
            return add_trackers(result.magnet_link)
        return None

    @staticmethod
    def _sort_results(
        results: list[TorrentResult], sort_by: str
    ) -> list[TorrentResult]:
        """Sort results by the specified field."""
        if sort_by == "size":
            return sorted(results, key=lambda x: x.size, reverse=True)
        elif sort_by == "name":
            return sorted(results, key=lambda x: x.title.lower())
        else:  # seeders
            return sorted(results, key=lambda x: x.seeders, reverse=True)
