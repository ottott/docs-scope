"""Opt-in test against real PostgreSQL, isolated in a temporary schema."""
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.rows import dict_row

from app import db
from app.main import app


def test_crawl_persistence_search_and_recrawl(tmp_path, monkeypatch):
    dsn = os.getenv("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Set TEST_DATABASE_URL to run the PostgreSQL integration test")
    schema = "test_" + uuid4().hex
    with psycopg.connect(dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    monkeypatch.setattr(db, "connect", lambda: psycopg.connect(
        dsn, row_factory=dict_row, options=f"-csearch_path={schema}", connect_timeout=5))
    (tmp_path / "index.html").write_text('<title>Install guide</title><main>Install the package.</main><a href="/usage.html">Usage</a>')
    (tmp_path / "usage.html").write_text('<title>Usage</title><main>Run the application after install.</main>')
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(tmp_path)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    try:
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
            response = client.post("/websites", json={"url": url, "max_pages": 2})
            assert response.json() == {"indexed": 2, "attempted": 2, "errors": []}
        # A new app lifespan verifies that data survives app restarts.
        with TestClient(app) as client:
            results = client.get("/search", params={"q": "install"}).json()["results"]
            assert len(results) == 2
            assert results[0]["title"] == "Install guide"
            assert results[0]["url"] == url
            assert results[0]["snippet"] == "Install the package"
            assert len(results[0]["snippet"]) <= 300
            assert client.get("/search", params={"q": "unfindableword"}).json() == {"results": []}
            assert client.get("/search", params={"q": "install", "limit": 1}).json()["results"] == results[:1]
            (tmp_path / "index.html").write_text('<title>Updated</title><main>Replacement content.</main>')
            assert client.post("/websites", json={"url": url, "max_pages": 1}).json()["indexed"] == 1
            with db.connect() as conn:
                assert conn.execute("SELECT count(*) AS n FROM pages").fetchone()["n"] == 2
            assert client.get("/search", params={"q": "replacement"}).json()["results"][0]["title"] == "Updated"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        with psycopg.connect(dsn, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
