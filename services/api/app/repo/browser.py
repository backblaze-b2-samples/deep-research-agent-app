"""Headless-browser source fetcher — the agent's ``fetch_source`` executor.

Given a URL this module:

1. Blocks SSRF targets (private / loopback / link-local IPs and non-http(s)
   schemes) *before* navigating — the agent can ask to fetch arbitrary URLs,
   and fetched page content is untrusted (see docs/SECURITY.md).
2. Navigates with Playwright Chromium, capturing the *rendered* HTML.
3. Extracts readable text (Markdown) with trafilatura.
4. Captures a full-page PNG screenshot. **Resilient:** if the screenshot step
   fails, we log and continue — HTML + text are still cached (RELIABILITY.md).

This is the only module that imports ``playwright`` / ``trafilatura``. It does
*not* touch B2 — the service layer orchestrates caching via ``b2_research`` so
the repo layer stays free of business logic.
"""

import hashlib
import ipaddress
import logging
import socket
from dataclasses import dataclass, field
from urllib.parse import urlparse

import trafilatura
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from app.config import settings

logger = logging.getLogger(__name__)


class UnsafeUrlError(Exception):
    """Raised when a URL fails SSRF / scheme validation."""


@dataclass
class FetchedPage:
    url: str
    title: str
    html: bytes
    text_markdown: str
    screenshot_png: bytes | None = field(default=None, repr=False)
    sha256: str = ""

    @property
    def has_screenshot(self) -> bool:
        return self.screenshot_png is not None


def _is_private_host(host: str) -> bool:
    """Resolve a host and return True if any address is private/loopback/etc."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # Can't resolve — treat as unsafe rather than letting the browser try.
        return True
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return True
    return False


def validate_url(url: str) -> None:
    """Reject non-http(s) schemes and private/loopback targets (SSRF guard)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if not parsed.hostname:
        raise UnsafeUrlError("URL has no host")
    if _is_private_host(parsed.hostname):
        raise UnsafeUrlError("Refusing to fetch a private/loopback address")


def fetch_page(url: str) -> FetchedPage:
    """Fetch, extract, and screenshot a single page.

    Raises ``UnsafeUrlError`` if the URL is blocked, or RuntimeError if the
    page can't be loaded at all. A failed screenshot is non-fatal.
    """
    validate_url(url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                viewport={
                    "width": settings.screenshot_viewport_width,
                    "height": settings.screenshot_viewport_height,
                },
                user_agent=(
                    "Mozilla/5.0 (compatible; b2ai-deep-research-agent-app/0.1; "
                    "+https://github.com/backblaze-b2-samples/deep-research-agent-app)"
                ),
            )
            page = context.new_page()
            try:
                page.goto(
                    url,
                    timeout=settings.fetch_timeout_ms,
                    wait_until="domcontentloaded",
                )
            except PlaywrightError as e:
                raise RuntimeError(f"Failed to load {url}: {e}") from e

            title = (page.title() or url).strip()
            html_str = page.content()
            html = html_str.encode("utf-8")[: settings.fetch_max_bytes]

            text_markdown = (
                trafilatura.extract(
                    html_str,
                    output_format="markdown",
                    include_links=True,
                    include_images=False,
                )
                or ""
            )

            # Screenshot is best-effort — one bad page must not kill the run.
            screenshot_png: bytes | None = None
            try:
                screenshot_png = page.screenshot(
                    full_page=True,
                    timeout=settings.screenshot_timeout_ms,
                )
            except PlaywrightError as e:
                logger.warning("Screenshot failed for %s: %s", url, e)

            return FetchedPage(
                url=url,
                title=title,
                html=html,
                text_markdown=text_markdown,
                screenshot_png=screenshot_png,
                sha256=hashlib.sha256(html).hexdigest(),
            )
        finally:
            browser.close()
