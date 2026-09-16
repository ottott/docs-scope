from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx
from bs4 import BeautifulSoup

from app.config import REQUEST_TIMEOUT

MAX_RESPONSE_BYTES = 2_000_000
MAX_TEXT_CHARS = 100_000


def normalize_url(url):
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        if parsed.username is not None or parsed.password is not None:
            return None
        host = parsed.hostname.lower()
        if ":" in host:
            host = f"[{host}]"
        port = parsed.port
        if port and (parsed.scheme, port) not in {("http", 80), ("https", 443)}:
            host += f":{port}"
        # Query variants commonly produce crawler traps; index the base page only.
        return urlunsplit((parsed.scheme, host, parsed.path or "/", "", ""))
    except ValueError:
        return None


def crawl(url, max_pages, client=None):
    start = normalize_url(url)
    if not start:
        raise ValueError("Use an HTTP(S) URL without credentials")
    host = urlsplit(start).hostname
    pending = deque([start])
    seen = {start}
    pages, errors = [], []
    attempted = 0

    def enqueue(candidate, base):
        target = normalize_url(urljoin(base, candidate))
        if (target and urlsplit(target).hostname == host and target not in seen
                and len(pending) + attempted < max_pages):
            seen.add(target)
            pending.append(target)

    def run(http):
        nonlocal attempted
        while pending and attempted < max_pages:
            current = pending.popleft()
            attempted += 1
            try:
                with http.stream("GET", current, follow_redirects=False) as response:
                    if response.is_redirect:
                        enqueue(response.headers.get("location", ""), current)
                        continue
                    response.raise_for_status()
                    if response.headers.get("content-type", "").split(";")[0].strip().lower() not in {
                        "text/html", "application/xhtml+xml"
                    }:
                        errors.append({"url": current, "error": "Not an HTML page"})
                        continue
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_RESPONSE_BYTES:
                            raise ValueError("Page exceeds 2 MB limit")
                    soup = BeautifulSoup(bytes(body), "html.parser")
                title = soup.title.get_text(" ", strip=True) if soup.title else current
                for link in soup.find_all("a", href=True):
                    enqueue(link["href"], current)
                for element in soup.select("script, style, nav, header, footer, aside, noscript, template"):
                    element.decompose()
                content = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.find("article") or soup.body or soup
                text = " ".join(content.get_text(" ", strip=True).replace("\x00", "").split())[:MAX_TEXT_CHARS]
                if text:
                    pages.append({"url": current, "title": title.replace("\x00", "")[:1000], "text": text})
                else:
                    errors.append({"url": current, "error": "No readable text"})
            except (httpx.HTTPError, ValueError) as exc:
                errors.append({"url": current, "error": str(exc)})

    if client is not None:
        run(client)
    else:
        with httpx.Client(timeout=REQUEST_TIMEOUT, headers={"User-Agent": "DocsScope/0.1"}) as http:
            run(http)
    return pages, attempted, errors
