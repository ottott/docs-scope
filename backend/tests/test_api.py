from fastapi.testclient import TestClient

from app.main import app


def test_validation_and_empty_crawl(monkeypatch):
    client = TestClient(app)  # No lifespan: these validation checks need no database.
    for payload in ({"url": "file:///tmp/file"}, {"url": "https://docs.test", "max_pages": 101},
                    {"url": "https://docs.test", "max_pages": 0},
                    {"url": "https://user:pass@docs.test"}):
        assert client.post("/websites", json=payload).status_code == 422
    for params in ({"q": " "}, {"q": "x", "limit": 0}, {}):
        assert client.get("/search", params=params).status_code == 422
    monkeypatch.setattr("app.api.websites.crawl", lambda *args: ([], 1, []))
    response = client.post("/websites", json={"url": "https://docs.test"})
    assert response.status_code == 422
    assert response.json()["detail"]["message"] == "No pages indexed"
