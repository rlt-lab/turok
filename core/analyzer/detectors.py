"""Detection strategies for site analysis."""

from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


@dataclass
class SearchPattern:
    """A detected search pattern."""

    url_template: str
    method: str = "GET"
    confidence: float = 0.0


@dataclass
class ResultStructure:
    """Detected result page structure."""

    result_item: str
    title: str
    title_link: str | None = None
    confidence: float = 0.0


def detect_search_patterns(soup: BeautifulSoup, base_url: str) -> list[SearchPattern]:
    """Detect search form patterns on a page."""
    patterns = []

    # Look for search forms
    forms = soup.select("form")
    for form in forms:
        action = form.get("action", "")
        method = form.get("method", "GET").upper()

        # Look for text input that might be the search field
        text_inputs = form.select("input[type='text'], input[type='search'], input:not([type])")
        for inp in text_inputs:
            name = inp.get("name", "")
            if not name:
                continue

            # Check if this looks like a search input
            search_indicators = ["s", "q", "query", "search", "term", "keyword"]
            is_search = any(
                ind in name.lower() or ind in inp.get("id", "").lower()
                for ind in search_indicators
            )

            if is_search or len(text_inputs) == 1:
                # Build URL template
                if action:
                    full_action = urljoin(base_url, action)
                else:
                    full_action = base_url

                url_template = f"{full_action}?{name}={{query}}"
                confidence = 0.8 if is_search else 0.5

                patterns.append(
                    SearchPattern(
                        url_template=url_template,
                        method=method,
                        confidence=confidence,
                    )
                )

    # Common URL patterns to try
    parsed = urlparse(base_url)
    common_patterns = [
        f"{base_url}/?s={{query}}",
        f"{base_url}/?q={{query}}",
        f"{base_url}/search?q={{query}}",
        f"{base_url}/search/{{query}}",
        f"{base_url}/search?query={{query}}",
    ]

    for pattern in common_patterns:
        # Check if pattern wasn't already found via forms
        if not any(p.url_template == pattern for p in patterns):
            patterns.append(
                SearchPattern(
                    url_template=pattern,
                    method="GET",
                    confidence=0.3,
                )
            )

    return sorted(patterns, key=lambda p: p.confidence, reverse=True)


def detect_result_structure(soup: BeautifulSoup) -> list[ResultStructure]:
    """Detect result item structures on a page."""
    structures = []

    # Strategy 1: Table-based results (common for torrent sites)
    tbody_rows = soup.select("tbody tr")
    if len(tbody_rows) >= 3:
        # Check if rows have links that could be titles
        for row in tbody_rows[:3]:
            links = row.select("a")
            if links:
                # Find the most likely title link (usually has longer text)
                title_link = max(links, key=lambda a: len(a.get_text(strip=True)))
                structures.append(
                    ResultStructure(
                        result_item="tbody tr",
                        title="a",
                        title_link=None,
                        confidence=0.7,
                    )
                )
                break

    # Strategy 2: Article-based (WordPress style)
    articles = soup.select("article")
    if len(articles) >= 2:
        for article in articles[:2]:
            # Look for title patterns
            title_selectors = ["h2 a", "h3 a", ".entry-title a", ".post-title a", "h2", "h3"]
            for sel in title_selectors:
                title_elem = article.select_one(sel)
                if title_elem and title_elem.get_text(strip=True):
                    structures.append(
                        ResultStructure(
                            result_item="article",
                            title=sel,
                            title_link=sel if "a" in sel else None,
                            confidence=0.8,
                        )
                    )
                    break

    # Strategy 3: Card/div layouts
    card_selectors = [
        ".card",
        ".result",
        ".item",
        ".post",
        ".entry",
        "[class*='result']",
        "[class*='item']",
    ]
    for card_sel in card_selectors:
        cards = soup.select(card_sel)
        if len(cards) >= 3:
            for card in cards[:2]:
                # Look for title
                title_selectors = ["h2 a", "h3 a", "h4 a", ".title a", "a.title", "h2", "h3"]
                for title_sel in title_selectors:
                    title_elem = card.select_one(title_sel)
                    if title_elem and title_elem.get_text(strip=True):
                        structures.append(
                            ResultStructure(
                                result_item=card_sel,
                                title=title_sel,
                                title_link=title_sel if "a" in title_sel else None,
                                confidence=0.6,
                            )
                        )
                        break
            break

    # Strategy 4: List items
    list_items = soup.select("ul li, ol li")
    if len(list_items) >= 5:
        for item in list_items[:3]:
            links = item.select("a")
            if links:
                structures.append(
                    ResultStructure(
                        result_item="li",
                        title="a",
                        confidence=0.4,
                    )
                )
                break

    return sorted(structures, key=lambda s: s.confidence, reverse=True)


def detect_magnet_selector(soup: BeautifulSoup) -> str:
    """Detect the best selector for magnet links."""
    # Look for magnet links - this is the standard selector
    magnets = soup.select("a[href^='magnet:']")
    if magnets:
        return "a[href^='magnet:']"

    # Default to standard magnet selector even if not found on search page
    # (magnets are often on detail pages only)
    return "a[href^='magnet:']"
