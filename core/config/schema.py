"""Configuration schema for dynamic sites."""

from dataclasses import dataclass, field


@dataclass
class SearchConfig:
    """Search configuration for a site."""

    url_template: str  # e.g., "{base_url}/?s={query}"
    method: str = "GET"


@dataclass
class SelectorsConfig:
    """CSS selectors for extracting data from pages."""

    result_item: str  # Selector for each result item
    title: str  # Selector for title within result item
    magnet: str = "a[href^='magnet:']"  # Selector for magnet link (on detail page)
    title_link: str | None = None  # If different from title selector
    size: str | None = None  # Optional selector for size
    seeders: str | None = None  # Optional selector for seeders
    leechers: str | None = None  # Optional selector for leechers


@dataclass
class PatternsConfig:
    """Regex patterns for extracting data."""

    size_regex: str = r"(\d+(?:\.\d+)?\s*(?:GB|MB|KB|TB))"


@dataclass
class SiteConfig:
    """Configuration for a dynamic torrent site."""

    name: str
    base_url: str
    search: SearchConfig
    selectors: SelectorsConfig
    patterns: PatternsConfig = field(default_factory=PatternsConfig)
    enabled: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary for YAML serialization."""
        return {
            "name": self.name,
            "base_url": self.base_url,
            "enabled": self.enabled,
            "search": {
                "url_template": self.search.url_template,
                "method": self.search.method,
            },
            "selectors": {
                "result_item": self.selectors.result_item,
                "title": self.selectors.title,
                "magnet": self.selectors.magnet,
                "title_link": self.selectors.title_link,
                "size": self.selectors.size,
                "seeders": self.selectors.seeders,
                "leechers": self.selectors.leechers,
            },
            "patterns": {
                "size_regex": self.patterns.size_regex,
            },
        }

    @classmethod
    def from_dict(cls, key: str, data: dict) -> "SiteConfig":
        """Create from dictionary (YAML deserialization)."""
        search_data = data.get("search", {})
        selectors_data = data.get("selectors", {})
        patterns_data = data.get("patterns", {})

        return cls(
            name=data.get("name", key),
            base_url=data["base_url"],
            enabled=data.get("enabled", True),
            search=SearchConfig(
                url_template=search_data["url_template"],
                method=search_data.get("method", "GET"),
            ),
            selectors=SelectorsConfig(
                result_item=selectors_data["result_item"],
                title=selectors_data["title"],
                magnet=selectors_data.get("magnet", "a[href^='magnet:']"),
                title_link=selectors_data.get("title_link"),
                size=selectors_data.get("size"),
                seeders=selectors_data.get("seeders"),
                leechers=selectors_data.get("leechers"),
            ),
            patterns=PatternsConfig(
                size_regex=patterns_data.get(
                    "size_regex", r"(\d+(?:\.\d+)?\s*(?:GB|MB|KB|TB))"
                ),
            ),
        )
