import httpx

from app.crawler import crawl, normalize_url


def test_scope_deduplication_extraction_and_budget():
    requested = []

    def handle(request):
        requested.append(str(request.url))
        return httpx.Response(200, headers={"content-type": "text/html"}, text='''
            <title>Guide</title><nav>Navigation noise</nav><main><h1>Install</h1>
            <p>Install the package.</p><script>secret()</script></main>
            <a href="/next#one">Next</a><a href="/next?sort=asc">Duplicate</a>
            <a href="https://other.test/">External</a><a href="/third">Third</a>
            <a href="/fourth">Fourth</a>''')

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        pages, attempted, errors = crawl("https://docs.test/", 3, client)
    assert requested == ["https://docs.test/", "https://docs.test/next", "https://docs.test/third"]
    assert attempted == len(pages) == 3
    assert errors == []
    assert pages[0]["title"] == "Guide"
    assert pages[0]["text"] == "Install Install the package."
    assert normalize_url("https://DOCS.test:443/path?q=1#section") == "https://docs.test/path"
    assert normalize_url("https://user:password@docs.test/") is None


def test_redirects_never_leave_host_or_exceed_budget():
    requested = []

    def handle(request):
        requested.append(str(request.url))
        location = "/next" if request.url.path == "/" else "https://other.test/"
        return httpx.Response(302, headers={"location": location})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        assert crawl("https://docs.test/", 5, client)[:2] == ([], 2)
        assert requested == ["https://docs.test/", "https://docs.test/next"]
        requested.clear()
        assert crawl("https://docs.test/", 1, client)[:2] == ([], 1)
        assert requested == ["https://docs.test/"]


def test_failures_non_html_and_large_pages_are_reported(monkeypatch):
    monkeypatch.setattr("app.crawler.MAX_RESPONSE_BYTES", 500)

    def handle(request):
        if request.url.path == "/":
            return httpx.Response(200, headers={"content-type": "text/html"}, text='''
                <main>Home</main><a href="/timeout">T</a><a href="/pdf">P</a>
                <a href="/large">L</a><a href="/missing">M</a>''')
        if request.url.path == "/timeout":
            raise httpx.ReadTimeout("Timed out", request=request)
        if request.url.path == "/pdf":
            return httpx.Response(200, headers={"content-type": "application/pdf"})
        if request.url.path == "/missing":
            return httpx.Response(404)
        return httpx.Response(200, headers={"content-type": "text/html"}, text="x" * 501)

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        pages, attempted, errors = crawl("https://docs.test/", 5, client)
    assert len(pages) == 1
    assert attempted == 5
    assert len(errors) == 4
