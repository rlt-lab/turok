#!/usr/bin/env python3
"""Turok: CLI torrent search via public trackers."""

import argparse
import re
import sys
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

# User agent to avoid blocks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TIMEOUT = 15


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
    if result["magnet_link"]:
        return result["magnet_link"]
    if result["detail_url"] and result["source"] == "1337x":
        magnet = get_1337x_magnet(result["detail_url"])
        result["magnet_link"] = magnet
        return magnet
    return None


def download(result: dict):
    """Open magnet link in default torrent client."""
    magnet = get_magnet(result)
    if magnet:
        webbrowser.open(magnet)
        print(f"Sent to torrent client: {result['title']}")
    else:
        print(f"Could not get magnet link for: {result['title']}")


def main():
    parser = argparse.ArgumentParser(description="Search torrents via public trackers")
    parser.add_argument("query", nargs="+", help="Search query")
    parser.add_argument("-n", "--number", type=int, default=10, help="Number of results (default: 10)")
    parser.add_argument("-s", "--sort", choices=["seeders", "size"], default="seeders", help="Sort by (default: seeders)")

    args = parser.parse_args()
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


if __name__ == "__main__":
    main()
