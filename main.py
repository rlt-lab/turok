#!/usr/bin/env python3
"""Turok: CLI torrent search via public trackers."""

import argparse
import platform
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from core.analyzer import SiteAnalyzer
from core.config import ConfigManager

# User agent to avoid blocks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TIMEOUT = 15

# Public trackers to help find peers for metadata
TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://tracker.bittor.pw:1337/announce",
    "udp://public.popcorn-tracker.org:6969/announce",
    "udp://tracker.dler.org:6969/announce",
    "udp://exodus.desync.com:6969/announce",
    "udp://open.demonii.com:1337/announce",
]


def add_trackers(magnet: str) -> str:
    """Add public trackers to a magnet link if missing."""
    if not magnet or "&tr=" in magnet:
        return magnet
    from urllib.parse import quote
    tracker_params = "".join(f"&tr={quote(t, safe='')}" for t in TRACKERS)
    return magnet + tracker_params


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def parse_size(size_str: str) -> int:
    """Parse size string like '1.5 GB' to bytes."""
    size_str = size_str.upper().strip()
    match = re.match(r"([\d.]+)\s*(B|KB|MB|GB|TB|KIB|MIB|GIB|TIB)", size_str)
    if not match:
        return 0
    value = float(match.group(1))
    unit = match.group(2)
    multipliers = {
        "B": 1, "KB": 1024, "KIB": 1024,
        "MB": 1024**2, "MIB": 1024**2,
        "GB": 1024**3, "GIB": 1024**3,
        "TB": 1024**4, "TIB": 1024**4,
    }
    return int(value * multipliers.get(unit, 1))


def search_1337x(query: str) -> list[dict]:
    """Search 1337x.to via scraping."""
    results = []
    try:
        url = f"https://1337x.to/search/{query.replace(' ', '+')}/1/"
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        rows = soup.select("tbody tr")
        for row in rows[:30]:  # Limit to 30 per source
            cols = row.find_all("td")
            if len(cols) < 5:
                continue

            title_link = cols[0].select_one("a:nth-of-type(2)")
            if not title_link:
                continue

            title = title_link.text.strip()
            detail_url = "https://1337x.to" + title_link["href"]

            seeders = int(cols[1].text.strip()) if cols[1].text.strip().isdigit() else 0
            leechers = int(cols[2].text.strip()) if cols[2].text.strip().isdigit() else 0
            size_text = cols[4].text.strip().split()[0:2]
            size = parse_size(" ".join(size_text)) if size_text else 0

            results.append({
                "title": title,
                "seeders": seeders,
                "leechers": leechers,
                "size": size,
                "detail_url": detail_url,
                "magnet_link": None,  # Fetched on demand
                "source": "1337x",
            })
    except Exception:
        pass  # Silently fail, aggregate from other sources
    return results


def get_1337x_magnet(detail_url: str) -> str | None:
    """Fetch magnet link from 1337x detail page."""
    try:
        resp = requests.get(detail_url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        magnet_link = soup.select_one("a[href^='magnet:']")
        if magnet_link:
            return magnet_link["href"]
    except Exception:
        pass
    return None


def search_piratebay(query: str) -> list[dict]:
    """Search The Pirate Bay via apibay."""
    results = []
    try:
        url = f"https://apibay.org/q.php?q={query.replace(' ', '+')}"
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, list) and data and data[0].get("id") != "0":
            for item in data[:30]:
                info_hash = item.get("info_hash", "")
                name = item.get("name", "")
                if not info_hash or not name:
                    continue

                magnet = f"magnet:?xt=urn:btih:{info_hash}&dn={name}"
                results.append({
                    "title": name,
                    "seeders": int(item.get("seeders", 0)),
                    "leechers": int(item.get("leechers", 0)),
                    "size": int(item.get("size", 0)),
                    "detail_url": None,
                    "magnet_link": magnet,
                    "source": "TPB",
                })
    except Exception:
        pass
    return results


def search_rarbg(query: str) -> list[dict]:
    """Search RARBG via torrentapi (if available) or mirrors."""
    results = []
    # RARBG shut down in 2023. Try common mirror/clone APIs.
    mirrors = [
        f"https://torrentapi.org/pubapi_v2.php?mode=search&search_string={query.replace(' ', '+')}&format=json_extended&app_id=turok",
    ]

    for mirror_url in mirrors:
        try:
            # torrentapi requires a token first
            token_resp = requests.get(
                "https://torrentapi.org/pubapi_v2.php?get_token=get_token&app_id=turok",
                headers=HEADERS,
                timeout=TIMEOUT,
            )
            token_data = token_resp.json()
            token = token_data.get("token")
            if not token:
                continue

            import time
            time.sleep(2)  # API rate limit

            url = f"{mirror_url}&token={token}"
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            data = resp.json()

            if "torrent_results" in data:
                for item in data["torrent_results"][:30]:
                    results.append({
                        "title": item.get("title", ""),
                        "seeders": int(item.get("seeders", 0)),
                        "leechers": int(item.get("leechers", 0)),
                        "size": int(item.get("size", 0)),
                        "detail_url": None,
                        "magnet_link": item.get("download", ""),
                        "source": "RARBG",
                    })
                break
        except Exception:
            continue
    return results


def search_all(query: str, limit: int = 10, sort_by: str = "seeders") -> list[dict]:
    """Search all sources in parallel and aggregate results."""
    all_results = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(search_1337x, query): "1337x",
            executor.submit(search_piratebay, query): "TPB",
            executor.submit(search_rarbg, query): "RARBG",
        }

        for future in as_completed(futures):
            try:
                results = future.result()
                all_results.extend(results)
            except Exception:
                pass

    # Sort results
    if sort_by == "size":
        all_results.sort(key=lambda x: x["size"], reverse=True)
    else:
        all_results.sort(key=lambda x: x["seeders"], reverse=True)

    return all_results[:limit]


def print_results(results: list[dict]):
    """Display search results in a formatted list."""
    for i, r in enumerate(results, 1):
        size_str = format_size(r["size"])
        print(f"[{i}] {r['title']} ({size_str}) - {r['seeders']}↑ {r['leechers']}↓ [{r['source']}]")


def get_magnet(result: dict) -> str | None:
    """Get magnet link, fetching from detail page if needed."""
    magnet = result["magnet_link"]
    if not magnet and result["detail_url"] and result["source"] == "1337x":
        magnet = get_1337x_magnet(result["detail_url"])
        result["magnet_link"] = magnet
    if magnet:
        return add_trackers(magnet)
    return None


def open_magnet(magnet: str) -> bool:
    """Open magnet link using system protocol handler (bypasses browser)."""
    try:
        system = platform.system()
        if system == "Darwin":
            subprocess.run(["open", magnet], check=True, capture_output=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", magnet], check=True, capture_output=True)
        elif system == "Windows":
            subprocess.run(["start", "", magnet], shell=True, check=True, capture_output=True)
        else:
            return False
        return True
    except subprocess.CalledProcessError:
        return False


def download(result: dict):
    """Open magnet link in default torrent client."""
    magnet = get_magnet(result)
    if magnet:
        if open_magnet(magnet):
            print(f"Sent to torrent client: {result['title']}")
        else:
            print(f"Failed to open magnet link for: {result['title']}")
    else:
        print(f"Could not get magnet link for: {result['title']}")


def cmd_search(args):
    """Handle the search command."""
    query = " ".join(args.query)

    print(f"Searching for '{query}'...")
    results = search_all(query, limit=args.number, sort_by=args.sort)

    if not results:
        print(f"No results for '{query}'")
        sys.exit(0)

    print()
    print_results(results)
    print()

    # Interactive loop
    while True:
        try:
            user_input = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_input == "q":
            break

        try:
            idx = int(user_input)
            if 1 <= idx <= len(results):
                download(results[idx - 1])
            else:
                print(f"Enter a number 1-{len(results)} or 'q' to quit")
        except ValueError:
            print(f"Enter a number 1-{len(results)} or 'q' to quit")


def cmd_add(args):
    """Handle the add command - auto-detect and add a site."""
    url = args.url
    test_query = args.query or "test"
    verbose = args.verbose

    # Parse URL
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        parsed = urlparse(url)

    print(f"Analyzing {url}...")

    analyzer = SiteAnalyzer(verbose=verbose)

    # Try auto-detection first
    result = analyzer.analyze(url, test_query)

    # Fall back to known patterns if auto-detection fails
    if not result.success:
        if verbose:
            print("Auto-detection failed, trying known patterns...")
        result = analyzer.analyze_with_known_patterns(url, test_query)

    if not result.success:
        print(f"Failed to analyze site: {result.error}")
        if verbose and result.attempts:
            print("\nAttempts:")
            for attempt in result.attempts:
                print(f"  {attempt}")
        sys.exit(1)

    config = result.config
    validation = result.validation

    # Generate site key
    site_key = parsed.netloc.replace(".", "_").replace("-", "_")

    print(f"\nDetected configuration for '{config.name}':")
    print(f"  Base URL: {config.base_url}")
    print(f"  Search: {config.search.url_template}")
    print(f"  Result selector: {config.selectors.result_item}")
    print(f"  Title selector: {config.selectors.title}")

    if validation:
        print(f"\nValidation:")
        print(f"  Results found: {validation.results_found}")
        print(f"  Has detail links: {validation.has_detail_links}")
        print(f"  Has magnets in results: {validation.has_magnets}")
        if validation.sample_titles:
            print(f"  Sample titles:")
            for title in validation.sample_titles[:3]:
                print(f"    - {title[:60]}{'...' if len(title) > 60 else ''}")

    # Save config
    manager = ConfigManager()
    manager.save(site_key, config)

    print(f"\nSaved to {manager.config_path}")
    print(f"Site '{config.name}' added successfully!")


def cmd_sites(args):
    """Handle the sites command - list configured sites."""
    manager = ConfigManager()

    if args.all:
        sites = manager.load_all()
    else:
        sites = manager.load_enabled()

    if not sites:
        print("No configured sites.")
        print("Use 'turok add <url>' to add a site.")
        return

    print("Configured sites:\n")
    for key, config in sites.items():
        status = "enabled" if config.enabled else "disabled"
        print(f"  {key}: {config.name} ({config.base_url}) [{status}]")


def cmd_remove(args):
    """Handle the remove command - remove a site."""
    name = args.name
    manager = ConfigManager()

    if manager.remove(name):
        print(f"Removed site '{name}'")
    else:
        print(f"Site '{name}' not found")
        sys.exit(1)


def cmd_enable(args):
    """Handle the enable command - enable a site."""
    name = args.name
    manager = ConfigManager()

    if manager.set_enabled(name, True):
        print(f"Enabled site '{name}'")
    else:
        print(f"Site '{name}' not found")
        sys.exit(1)


def cmd_disable(args):
    """Handle the disable command - disable a site."""
    name = args.name
    manager = ConfigManager()

    if manager.set_enabled(name, False):
        print(f"Disabled site '{name}'")
    else:
        print(f"Site '{name}' not found")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Turok: CLI torrent search via public trackers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Search command (default behavior for backwards compatibility)
    search_parser = subparsers.add_parser("search", help="Search for torrents")
    search_parser.add_argument("query", nargs="+", help="Search query")
    search_parser.add_argument(
        "-n", "--number", type=int, default=10, help="Number of results (default: 10)"
    )
    search_parser.add_argument(
        "-s", "--sort", choices=["seeders", "size"], default="seeders",
        help="Sort by (default: seeders)"
    )
    search_parser.set_defaults(func=cmd_search)

    # Add command
    add_parser = subparsers.add_parser("add", help="Auto-detect and add a torrent site")
    add_parser.add_argument("url", help="URL of the site to add")
    add_parser.add_argument(
        "-q", "--query", help="Test query for validation (default: 'test')"
    )
    add_parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed analysis"
    )
    add_parser.set_defaults(func=cmd_add)

    # Sites command
    sites_parser = subparsers.add_parser("sites", help="List configured sites")
    sites_parser.add_argument(
        "-a", "--all", action="store_true", help="Include disabled sites"
    )
    sites_parser.set_defaults(func=cmd_sites)

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a configured site")
    remove_parser.add_argument("name", help="Site key to remove")
    remove_parser.set_defaults(func=cmd_remove)

    # Enable command
    enable_parser = subparsers.add_parser("enable", help="Enable a configured site")
    enable_parser.add_argument("name", help="Site key to enable")
    enable_parser.set_defaults(func=cmd_enable)

    # Disable command
    disable_parser = subparsers.add_parser("disable", help="Disable a configured site")
    disable_parser.add_argument("name", help="Site key to disable")
    disable_parser.set_defaults(func=cmd_disable)

    # Handle backwards compatibility - if first arg isn't a known command, assume search
    known_commands = {"search", "add", "sites", "remove", "enable", "disable", "-h", "--help"}
    if len(sys.argv) > 1 and sys.argv[1] not in known_commands:
        sys.argv.insert(1, "search")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
