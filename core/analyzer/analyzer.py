"""Site analyzer for auto-detecting torrent site configurations."""

from dataclasses import dataclass
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from ..config import PatternsConfig, SearchConfig, SelectorsConfig, SiteConfig
from ..sources.base import HEADERS, TIMEOUT
from .detectors import (
    detect_magnet_selector,
    detect_result_structure,
    detect_search_patterns,
)
from .validator import ValidationResult, validate_config


@dataclass
class AnalysisResult:
    """Result of analyzing a site."""

    success: bool
    config: SiteConfig | None = None
    validation: ValidationResult | None = None
    error: str | None = None
    attempts: list[str] | None = None


class SiteAnalyzer:
    """Analyzes torrent sites to auto-generate configurations."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._attempts: list[str] = []

    def _log(self, msg: str) -> None:
        """Log a message if verbose mode is on."""
        self._attempts.append(msg)
        if self.verbose:
            print(f"  {msg}")

    def analyze(self, url: str, test_query: str = "test") -> AnalysisResult:
        """Analyze a site and generate a configuration."""
        self._attempts = []

        # Parse URL
        parsed = urlparse(url)
        if not parsed.scheme:
            url = f"https://{url}"
            parsed = urlparse(url)

        base_url = f"{parsed.scheme}://{parsed.netloc}"
        site_key = parsed.netloc.replace(".", "_").replace("-", "_")
        site_name = parsed.netloc.split(".")[0].title()

        self._log(f"Analyzing {base_url}...")

        # Fetch the homepage
        try:
            resp = requests.get(base_url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            return AnalysisResult(
                success=False,
                error=f"Failed to fetch site: {e}",
                attempts=self._attempts,
            )

        # Detect search patterns
        self._log("Detecting search patterns...")
        search_patterns = detect_search_patterns(soup, base_url)

        if not search_patterns:
            return AnalysisResult(
                success=False,
                error="Could not detect search functionality",
                attempts=self._attempts,
            )

        # Try each search pattern
        for pattern in search_patterns:
            self._log(f"Trying pattern: {pattern.url_template}")

            # Fetch search results
            try:
                search_url = pattern.url_template.format(
                    base_url=base_url,
                    query=test_query.replace(" ", "+"),
                )
                resp = requests.get(search_url, headers=HEADERS, timeout=TIMEOUT)
                resp.raise_for_status()
                results_soup = BeautifulSoup(resp.text, "html.parser")
            except Exception as e:
                self._log(f"  Failed: {e}")
                continue

            # Detect result structure
            self._log("Detecting result structure...")
            structures = detect_result_structure(results_soup)

            if not structures:
                self._log("  No result structure detected")
                continue

            # Try each structure
            for structure in structures:
                self._log(f"Trying structure: {structure.result_item} / {structure.title}")

                # Detect magnet selector
                magnet_selector = detect_magnet_selector(results_soup) or "a[href^='magnet:']"

                # Build config
                config = SiteConfig(
                    name=site_name,
                    base_url=base_url,
                    search=SearchConfig(
                        url_template=pattern.url_template,
                        method=pattern.method,
                    ),
                    selectors=SelectorsConfig(
                        result_item=structure.result_item,
                        title=structure.title,
                        title_link=structure.title_link,
                        magnet=magnet_selector,
                    ),
                    patterns=PatternsConfig(),
                )

                # Validate
                self._log("Validating configuration...")
                validation = validate_config(config, test_query)

                if validation.success:
                    self._log(f"Success! Found {validation.results_found} results")
                    return AnalysisResult(
                        success=True,
                        config=config,
                        validation=validation,
                        attempts=self._attempts,
                    )
                else:
                    self._log(f"  Validation failed: {validation.error}")

        return AnalysisResult(
            success=False,
            error="Could not find a working configuration",
            attempts=self._attempts,
        )

    def analyze_with_known_patterns(
        self, url: str, test_query: str = "test"
    ) -> AnalysisResult:
        """Try known patterns for common site types."""
        self._attempts = []

        parsed = urlparse(url)
        if not parsed.scheme:
            url = f"https://{url}"
            parsed = urlparse(url)

        base_url = f"{parsed.scheme}://{parsed.netloc}"
        site_name = parsed.netloc.split(".")[0].title()

        # Known patterns for common site types
        known_configs = [
            # WordPress-style
            SiteConfig(
                name=site_name,
                base_url=base_url,
                search=SearchConfig(url_template=f"{base_url}/?s={{query}}"),
                selectors=SelectorsConfig(
                    result_item="article",
                    title="h2 a",
                    magnet="a[href^='magnet:']",
                ),
            ),
            # 1337x-style
            SiteConfig(
                name=site_name,
                base_url=base_url,
                search=SearchConfig(url_template=f"{base_url}/search/{{query}}/1/"),
                selectors=SelectorsConfig(
                    result_item="tbody tr",
                    title="td a:nth-of-type(2)",
                    magnet="a[href^='magnet:']",
                ),
            ),
            # Generic search with q parameter
            SiteConfig(
                name=site_name,
                base_url=base_url,
                search=SearchConfig(url_template=f"{base_url}/search?q={{query}}"),
                selectors=SelectorsConfig(
                    result_item=".result, .item, article",
                    title="h2 a, h3 a, .title a",
                    magnet="a[href^='magnet:']",
                ),
            ),
        ]

        for config in known_configs:
            self._log(f"Trying known pattern: {config.search.url_template}")
            validation = validate_config(config, test_query)

            if validation.success:
                self._log(f"Success! Found {validation.results_found} results")
                return AnalysisResult(
                    success=True,
                    config=config,
                    validation=validation,
                    attempts=self._attempts,
                )
            else:
                self._log(f"  Failed: {validation.error}")

        return AnalysisResult(
            success=False,
            error="No known patterns matched",
            attempts=self._attempts,
        )
