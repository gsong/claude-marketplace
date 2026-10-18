#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27", "defusedxml>=0.7"]
# ///
"""Mirror Anthropic's public doc sets into .cache/docs-mirror/<host>/.

Run it through `mise run docs:mirror`. Each set is discovered from its
llms.txt index, saved as Markdown, and recorded in a per-host manifest.json.
A page fetched within --max-age hours is skipped unless --force. Prints one
summary line per host and compares the page count to the host's sitemap.
Exits 1 if any page failed.
"""

import argparse
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import defusedxml.ElementTree as ET
import httpx

USER_AGENT = "claude-marketplace-docs-mirror/1.0 (+https://github.com/gsong/claude-marketplace)"
RETRIES = 2
TIMEOUT = 30.0
LINK = re.compile(r"https?://[^\s)<>\"]+")


@dataclass(frozen=True)
class Source:
    host: str
    index: str
    sitemap: str
    prefix: str  # a page belongs to the set when its path starts with this
    exclude: str | None = None  # ... and does not start with this


SOURCES = [
    Source("claude.com", "https://claude.com/docs/llms.txt", "https://claude.com/sitemap.xml", "/docs/"),
    Source(
        "code.claude.com",
        "https://code.claude.com/docs/llms.txt",
        "https://code.claude.com/sitemap.xml",
        "/docs/en/",
    ),
    Source(
        "support.claude.com",
        "https://support.claude.com/llms.txt",
        "https://support.claude.com/sitemap.xml",
        "/en/articles/",
    ),
    Source(
        "platform.claude.com",
        "https://platform.claude.com/llms.txt",
        "https://platform.claude.com/sitemap.xml",
        "/docs/en/",
        exclude="/docs/en/api/",
    ),
]


def main() -> int:
    args = parse_args()
    wanted = [s for s in SOURCES if not args.host or s.host in args.host]
    cache = Path(args.cache)
    failed = 0
    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=TIMEOUT,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=args.concurrency),
    ) as client:
        for source in wanted:
            failed += mirror(client, source, cache / source.host, args)
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--force", action="store_true", help="refetch pages even if fresh")
    p.add_argument("--max-age", type=float, default=24, help="hours a page stays fresh (default 24)")
    p.add_argument("--concurrency", type=int, default=8, help="parallel requests (default 8)")
    p.add_argument("--cache", default=".cache/docs-mirror", help="mirror directory")
    p.add_argument("--host", action="append", help="only this host; repeatable")
    return p.parse_args()


def mirror(client: httpx.Client, source: Source, root: Path, args: argparse.Namespace) -> int:
    start = time.monotonic()
    urls = list_pages(client, source)
    manifest_path = root / "manifest.json"
    manifest = load_manifest(manifest_path)
    cutoff = datetime.now(UTC) - timedelta(hours=args.max_age)
    todo = [u for u in urls if args.force or not is_fresh(manifest.get(u), cutoff, root, u)]
    skipped = len(urls) - len(todo)

    def work(url: str) -> tuple[str, dict]:
        return url, fetch_page(client, root, url)

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for done, (url, entry) in enumerate(pool.map(work, todo), 1):
            manifest[url] = entry
            if done % 100 == 0:
                print(f"  {source.host}: {done}/{len(todo)}", file=sys.stderr)
    # Keep only entries still listed, so the manifest describes the current set.
    manifest = {u: manifest[u] for u in urls if u in manifest}
    root.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")

    failures = [u for u in todo if manifest[u]["status"] != 200]
    print(
        f"{source.host}: listed {len(urls)}, fetched {len(todo) - len(failures)}, "
        f"skipped {skipped}, failed {len(failures)} ({time.monotonic() - start:.0f}s)"
    )
    for u in failures:
        print(f"  failed: {u} ({manifest[u]['status']})")
    compare_sitemap(client, source, urls)
    return len(failures)


def list_pages(client: httpx.Client, source: Source) -> list[str]:
    """Return the set's page URLs from its llms.txt, as .md URLs, in index order."""
    text = get_text(client, source.index)
    seen: dict[str, None] = {}
    for link in LINK.findall(text):
        parts = urlsplit(link.rstrip(".,;:"))
        path = parts.path
        if parts.netloc != source.host or not path.startswith(source.prefix):
            continue
        if source.exclude and path.startswith(source.exclude):
            continue
        if not path.endswith(".md"):
            path += ".md"
        seen[f"https://{source.host}{path}"] = None
    return list(seen)


def compare_sitemap(client: httpx.Client, source: Source, urls: list[str]) -> None:
    try:
        tree = ET.fromstring(get_text(client, source.sitemap))
    except (httpx.HTTPError, ET.ParseError) as e:
        print(f"  sitemap: unavailable ({e})")
        return
    # Read <loc> and hreflang links, since support may list English only as an alternate.
    found: set[str] = set()
    for el in tree.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "loc" and el.text:
            link = el.text.strip()
        elif tag == "link" and el.get("href"):
            link = el.get("href")
        else:
            continue
        parts = urlsplit(link)
        path = parts.path.rstrip("/")
        if parts.netloc != source.host or not path.startswith(source.prefix.rstrip("/") + "/"):
            continue
        if source.exclude and path.startswith(source.exclude):
            continue
        found.add(f"https://{source.host}{path.removesuffix('/index')}")
    if not found:
        print("  sitemap: lists no pages for this set, so no count to compare")
        return
    mirrored = {u.removesuffix(".md").removesuffix("/index") for u in urls}
    sitemap_only = sorted(found - mirrored)
    index_only = sorted(mirrored - found)
    print(
        f"  sitemap: {len(found)} pages, index {len(mirrored)}, "
        f"difference {len(mirrored) - len(found):+d} "
        f"({len(sitemap_only)} in sitemap only, {len(index_only)} in index only)"
    )
    for label, items in (("sitemap only", sitemap_only), ("index only", index_only)):
        for u in items[:5]:
            print(f"    {label}: {u}")
        if len(items) > 5:
            print(f"    {label}: ... {len(items) - 5} more")


def fetch_page(client: httpx.Client, root: Path, url: str) -> dict:
    status = 0
    for attempt in range(RETRIES + 1):
        try:
            resp = client.get(url)
            status = resp.status_code
            if status == 200:
                path = page_path(root, url)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(resp.text)
                break
            if status < 500 and status != 429:
                break
        except httpx.HTTPError:
            status = 0
        if attempt < RETRIES:
            time.sleep(2**attempt)
    return {"fetched_at": datetime.now(UTC).isoformat(timespec="seconds"), "status": status}


def page_path(root: Path, url: str) -> Path:
    return root / urlsplit(url).path.lstrip("/")


def is_fresh(entry: dict | None, cutoff: datetime, root: Path, url: str) -> bool:
    if not entry or entry.get("status") != 200 or not page_path(root, url).exists():
        return False
    return datetime.fromisoformat(entry["fetched_at"]) >= cutoff


def load_manifest(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def get_text(client: httpx.Client, url: str) -> str:
    for attempt in range(RETRIES + 1):
        try:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPError:
            if attempt == RETRIES:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


if __name__ == "__main__":
    sys.exit(main())
