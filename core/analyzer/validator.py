"""Validation for detected site configurations."""

from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from ..config import SiteConfig
from ..sources.base import HEADERS, TIMEOUT


@dataclass
class ValidationResult:
    """Result of validating a site configuration."""

    success: bool
    results_found: int = 0
    has_detail_links: bool = False
    has_magnets: bool = False
    sample_titles: list[str] | None = None
    error: str | None = None


def validate_config(config: SiteConfig, test_query: str = "test") -> ValidationResult:
    """Validate a site configuration by running a test search."""
    try:
        # Build search URL
        url = config.search.url_template.format(
            base_url=config.base_url,
            query=test_query.replace(" ", "+"),
        )

        # Fetch search results
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find result items
        items = soup.select(config.selectors.result_item)
        if not items:
            return ValidationResult(
                success=False,
                error=f"No results found with selector '{config.selectors.result_item}'",
            )

        # Check titles
        sample_titles = []
        has_detail_links = False
        has_magnets = False

        for item in items[:5]:
            title_elem = item.select_one(config.selectors.title)
            if title_elem:
                title = title_elem.get_text(strip=True)
                if title:
                    sample_titles.append(title)

                    # Check for detail link
                    if title_elem.name == "a" and title_elem.get("href"):
                        has_detail_links = True
                    elif config.selectors.title_link:
                        link_elem = item.select_one(config.selectors.title_link)
                        if link_elem and link_elem.get("href"):
                            has_detail_links = True

            # Check for magnets in search results
            magnet_elem = item.select_one(config.selectors.magnet)
            if magnet_elem and magnet_elem.get("href", "").startswith("magnet:"):
                has_magnets = True

        if not sample_titles:
            return ValidationResult(
                success=False,
                error=f"Could not extract titles with selector '{config.selectors.title}'",
            )

        return ValidationResult(
            success=True,
            results_found=len(items),
            has_detail_links=has_detail_links,
            has_magnets=has_magnets,
            sample_titles=sample_titles,
        )

    except requests.RequestException as e:
        return ValidationResult(success=False, error=f"Network error: {e}")
    except Exception as e:
        return ValidationResult(success=False, error=f"Validation error: {e}")


def validate_magnet_fetch(config: SiteConfig, detail_url: str) -> str | None:
    """Validate that magnets can be fetched from a detail page."""
    try:
        resp = requests.get(detail_url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        magnet_elem = soup.select_one(config.selectors.magnet)
        if magnet_elem:
            href = magnet_elem.get("href", "")
            if href.startswith("magnet:"):
                return href

    except Exception:
        pass
    return None
