import re
from urllib.parse import urljoin, urlparse

import requests


class UrlExtractionError(Exception):
    """Raised when URL extraction fails."""


def _to_text(html: str) -> str:
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html, "html.parser")
        main = soup.find("main")
        if main:
            return main.get_text(separator=" ", strip=True)

        paragraphs = soup.find_all("p")
        return " ".join(p.get_text(separator=" ", strip=True) for p in paragraphs)
    except Exception:
        cleaned = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
        cleaned = re.sub(r"<style[\s\S]*?</style>", " ", cleaned, flags=re.I)
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip()


def _extract_internal_links(html: str, base_url: str, max_links: int) -> list[str]:
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html, "html.parser")
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        keywords = ("about", "amenit", "location", "gallery", "spec", "overview", "floor-plan", "plan")
        links: list[str] = []

        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", "")).strip()
            if not href:
                continue
            lower = href.lower()
            if (href.startswith("/") or href.startswith(base)) and any(k in lower for k in keywords):
                full_url = urljoin(base, href)
                if full_url not in links:
                    links.append(full_url)
            if len(links) >= max_links:
                break
        return links
    except Exception:
        return []


def extract_website_text(url: str, max_pages: int = 4, timeout_seconds: int = 12) -> str:
    cleaned_url = (url or "").strip()
    if not cleaned_url:
        return ""

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(cleaned_url, timeout=timeout_seconds, headers=headers)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise UrlExtractionError(f"Failed to fetch {cleaned_url}: {exc}") from exc

    visited: list[str] = [cleaned_url]
    visited.extend(_extract_internal_links(response.text, cleaned_url, max(max_pages - 1, 0)))

    chunks: list[str] = []
    for page_url in visited[:max_pages]:
        try:
            page_response = requests.get(page_url, timeout=timeout_seconds, headers=headers)
            page_response.raise_for_status()
            text = _to_text(page_response.text)
            if text:
                chunks.append(f"Content from {page_url}:\n{text[:2200]}")
        except requests.RequestException:
            continue

    return "\n\n".join(chunks)[:9000]
