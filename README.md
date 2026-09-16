# Docs Scope

A small FastAPI backend that crawls documentation HTML, stores page titles, URLs and readable text in PostgreSQL, and searches them with PostgreSQL full-text search. Crawls run sequentially within the HTTP request. There is no frontend, AI integration or worker service.

## Setup on Ubuntu/Linux

Requires Python 3.10+, Docker Engine and Docker Compose v2 or newer. On Ubuntu 24.04 or newer, install prerequisites with:

```bash
sudo apt update
sudo apt install -y git curl python3 python3-venv docker.io docker-compose-v2
sudo systemctl enable --now docker
```

If Docker is already installed, keep your existing installation. Ubuntu supplies [Compose v2](https://packages.ubuntu.com/noble/docker-compose-v2); other Linux distributions can use Docker's [Engine](https://docs.docker.com/engine/install/) and [Compose](https://docs.docker.com/compose/install/linux/) instructions. Commands below use `sudo` for Docker; omit it if your account already has Docker access.

From a fresh clone:

```bash
git clone https://github.com/ottott/docs-scope.git
cd docs-scope
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
sudo docker compose up -d --wait
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The API creates its table and search index on startup. No migration or manual SQL step is needed. PostgreSQL must be ready before starting the API. The existing `pgvector/pgvector:pg17` image is retained, but no vector extension is enabled or used. Data is kept in the existing `postgres_data` Docker volume, and port 5432 is bound to localhost.

In another terminal:

```bash
curl --fail http://127.0.0.1:8000/health
curl --fail -X POST http://127.0.0.1:8000/websites \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://docs.python.org/3/tutorial/", "max_pages":5}'
curl --fail --get http://127.0.0.1:8000/search \
  --data-urlencode 'q=python' --data-urlencode 'limit=5'
```

Interactive API docs: <http://127.0.0.1:8000/docs>.

## API

- `GET /health`: checks database connectivity; returns `{"status":"ok"}` or HTTP 503 if the database is unavailable.
- `POST /websites`: accepts `url` (HTTP/HTTPS, no credentials) and optional `max_pages`. Returns `{"indexed":5,"attempted":5,"errors":[]}`. The response waits for crawling and persistence to finish. Failed pages are reported in `errors`; successful pages are still saved. HTTP 422 means invalid input or no readable pages were found. Re-crawling updates rows by URL; pages not revisited remain stored.
- `GET /search?q=install&limit=10`: searches all stored pages, returning `{"results":[{"title":"Installation","url":"https://example.org/install","snippet":"Install the package ..."}]}`. Results are ranked by relevance with title matches weighted higher; snippets are plain text capped at 300 characters. No matches returns an empty list. Queries must be 1–200 characters and nonblank; limits are 1–50.

Search uses PostgreSQL's [English full-text search](https://www.postgresql.org/docs/17/textsearch-controls.html), including word stemming, quoted phrases and `OR`. It is word search, not substring or semantic search. Stop-word-only queries can return no results.

## Configuration and crawl limits

Set environment variables before starting Uvicorn; `.env` files are not loaded automatically.

| Variable | Default | Allowed values |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/docsscope` | PostgreSQL connection URL |
| `MAX_CRAWL_PAGES` | `20` | 1–100; default and upper bound for each request's `max_pages` |
| `REQUEST_TIMEOUT` | `10` | Greater than 0, at most 30 seconds per network operation |

For example:

```bash
MAX_CRAWL_PAGES=10 REQUEST_TIMEOUT=5 \
  python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The fetch budget includes failed requests, non-HTML responses and redirect hops. Each normalized URL is fetched at most once per crawl. Only the original hostname is allowed, including for redirects; subdomains are separate hosts. HTTP/HTTPS and port changes on that hostname are allowed. Fragments and query strings are removed to avoid duplicate sections and query traps, so query-driven documentation sites are not supported. Link discovery includes navigation links, then extraction prefers `main`, `role="main"` or `article`, falling back to the body after removing common navigation and script elements.

Responses are limited to 2 MB of decoded bytes, readable text to 100,000 characters, and titles to 1,000 characters per page. Requests use [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/); the timeout is an inactivity/operation limit, not a total crawl deadline. JavaScript is not executed. There is no robots.txt handling, sitemap discovery, retry system or scheduled refresh. Crawl only sites you have permission to fetch. This is a local tool for trusted callers: URL requests can access local/private addresses, and the API has no authentication or aggregate concurrency limit. Keep the default localhost binding.

## Tests

From the repository root with the virtual environment activated:

```bash
python -m pytest -q
```

Four tests run without a database; the PostgreSQL integration test is skipped unless explicitly enabled:

```bash
sudo docker compose up -d --wait
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/docsscope \
  python -m pytest -q
```

The integration test serves a tiny local documentation site and checks crawling, ranking, snippets, persistence across app lifespans and updates without duplicate rows. It uses a temporary database schema that is removed afterward, without modifying your indexed pages. The test database user needs permission to create schemas.

For a reproducible manual crawl without an external website, create a local fixture in another terminal:

```bash
DOCS_SAMPLE_DIR=$(mktemp -d)
printf '%s\n' '<title>Install guide</title><main>Install the package.</main><a href="/usage.html">Usage</a>' > "$DOCS_SAMPLE_DIR/index.html"
printf '%s\n' '<title>Usage</title><main>Run the application after install.</main>' > "$DOCS_SAMPLE_DIR/usage.html"
python3 -m http.server 8001 --bind 127.0.0.1 --directory "$DOCS_SAMPLE_DIR"
```

With the API still running:

```bash
curl --fail -X POST http://127.0.0.1:8000/websites \
  -H 'Content-Type: application/json' \
  -d '{"url":"http://127.0.0.1:8001/","max_pages":2}'
curl --fail --get http://127.0.0.1:8000/search --data-urlencode 'q=install'
```

The crawl returns `{"indexed":2,"attempted":2,"errors":[]}`. Search includes both pages, with **Install guide** ranked first in an otherwise empty database.

## Stopping and troubleshooting

Stop Uvicorn and the optional fixture server with Ctrl+C. Run `sudo docker compose down` to stop PostgreSQL while keeping indexed data. `sudo docker compose down -v` also **deletes all database data**.

- Docker permission denied: use `sudo docker compose ...` as above.
- Port 5432 already in use: stop the conflicting local service or change the Compose host port and match it in `DATABASE_URL` and `TEST_DATABASE_URL`.
- API startup fails to connect: run `sudo docker compose ps` and `sudo docker compose logs postgres`; check your connection URL and that PostgreSQL is healthy.
- Existing volume has different credentials: use that volume's credentials in `DATABASE_URL`; changing Compose environment variables does not reset an initialized database.
