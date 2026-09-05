"""
Web Crawler Module — Safe multi-page company ingestion.

Features:
- Strict SSRF / private IP protection
- Registered-domain link discovery & prioritization
- Page timeout, size limit, HTML content-type validation
- Boilerplate removal & text deduplication
- Per-page fault tolerance
"""

from __future__ import annotations
import asyncio
import socket
import ipaddress
import re
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup

from storage.models import SourceDocument, new_id


def is_private_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
    except ValueError:
        return True


def validate_target_url(url: str) -> bool:
    if not url:
        return False
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False
        if hostname.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return False
        
        # Resolve IP addresses
        addr_info = socket.getaddrinfo(hostname, None)
        for item in addr_info:
            ip = item[4][0]
            if is_private_ip(ip):
                return False
        return True
    except Exception:
        return False


def get_base_domain(url: str) -> str:
    hostname = urlparse(url).hostname or ""
    parts = hostname.lower().split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return hostname.lower()


PRIORITY_KEYWORDS = ["about", "product", "solutions", "customers", "careers", "pricing", "news", "blog"]


def score_link(path: str) -> int:
    path_lower = path.lower()
    for idx, kw in enumerate(PRIORITY_KEYWORDS):
        if kw in path_lower:
            return len(PRIORITY_KEYWORDS) - idx
    return 0


def clean_html_content(html_text: str) -> tuple[str | None, str]:
    soup = BeautifulSoup(html_text, "html.parser")
    
    # Extract title
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    
    # Remove boilerplate elements
    for el in soup(["script", "style", "nav", "footer", "header", "noscript", "iframe"]):
        el.decompose()
        
    for el in soup.find_all(class_=re.compile(r"(cookie|banner|consent|menu|sidebar|footer)", re.I)):
        el.decompose()

    text = " ".join(soup.get_text(separator=" ", strip=True).split())
    return title, text


async def crawl_company(company_url: str | None, max_pages: int = 10) -> list[SourceDocument]:
    if not company_url:
        return []

    # Normalize protocol if missing
    target_url = company_url
    if not (target_url.startswith("http://") or target_url.startswith("https://")):
        target_url = f"https://{target_url}"

    if not validate_target_url(target_url):
        return [
            SourceDocument(
                url=company_url,
                title="Invalid or Blocked URL",
                content="",
                status="blocked",
                error="URL failed SSRF validation or resolved to a private/local IP address",
            )
        ]

    base_domain = get_base_domain(target_url)
    visited_urls: set[str] = set()
    queue: list[str] = [target_url]
    documents: list[SourceDocument] = []
    seen_texts: set[str] = set()

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        while queue and len(documents) < max_pages:
            current_url = queue.pop(0)
            if current_url in visited_urls:
                continue
            visited_urls.add(current_url)

            # SSRF check on each URL in queue
            if not validate_target_url(current_url):
                documents.append(
                    SourceDocument(
                        url=current_url,
                        title=None,
                        content="",
                        status="blocked",
                        error="SSRF validation failed for link target",
                    )
                )
                continue

            try:
                resp = await client.get(current_url)
                
                # Verify final redirect domain match
                final_domain = get_base_domain(str(resp.url))
                if final_domain != base_domain:
                    documents.append(
                        SourceDocument(
                            url=current_url,
                            title=None,
                            content="",
                            status="dead_end",
                            error=f"Redirected to external domain {final_domain}",
                        )
                    )
                    continue

                content_type = resp.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                    continue

                if len(resp.content) > 2 * 1024 * 1024:  # 2MB cap
                    continue

                title, text = clean_html_content(resp.text)
                
                # Check for duplicate content (first 500 chars snippet signature)
                snippet = text[:500]
                if not text or snippet in seen_texts:
                    continue
                seen_texts.add(snippet)

                doc = SourceDocument(
                    doc_id=new_id("doc"),
                    url=str(resp.url),
                    title=title,
                    content=text[:4000],  # Cap content per doc
                    status="success",
                )
                documents.append(doc)

                # Discover links if under cap
                soup = BeautifulSoup(resp.text, "html.parser")
                discovered: list[tuple[int, str]] = []
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"].strip()
                    full_link = urljoin(str(resp.url), href)
                    parsed_link = urlparse(full_link)
                    
                    # Sanitize URL (strip fragment & query for canonical matching)
                    clean_link = f"{parsed_link.scheme}://{parsed_link.netloc}{parsed_link.path}".rstrip("/")
                    
                    if get_base_domain(clean_link) == base_domain and clean_link not in visited_urls:
                        score = score_link(parsed_link.path)
                        discovered.append((score, clean_link))

                # Sort discovered links by priority score descending
                discovered.sort(key=lambda x: x[0], reverse=True)
                for _, link in discovered:
                    if link not in queue and link not in visited_urls:
                        queue.append(link)

            except Exception as exc:
                documents.append(
                    SourceDocument(
                        url=current_url,
                        title=None,
                        content="",
                        status="error",
                        error=str(exc),
                    )
                )

    return documents
