# Docs Scope

Docs Scope is a small documentation search backend built with FastAPI and PostgreSQL.

Given a documentation URL, it crawls a bounded number of pages on the same host, extracts readable text, stores the pages in PostgreSQL, and exposes a full-text search API.

The project is intentionally focused on crawling and search rather than AI or frontend features.

## Features

- Crawl documentation websites from a starting URL
- Stay within the original host
- Avoid duplicate URLs
- Extract page titles and readable content
- Store and update indexed pages in PostgreSQL
- Search indexed content using PostgreSQL full-text search
- Return ranked results with short text snippets
- Basic crawler and API tests

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- BeautifulSoup
- HTTPX
- Docker Compose
- pytest

## Running Locally

Requirements:

- Python 3.10+
- Docker Engine
- Docker Compose

Clone the repository:

```bash
git clone https://github.com/ottott/docs-scope.git
cd docs-scope
```

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
```

Start PostgreSQL:

```bash
docker compose up -d
```

Start the API:

```bash
python -m uvicorn app.main:app --app-dir backend --reload
```

The API is available at:

- http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs

## Example

Index up to five pages:

```bash
curl -X POST http://127.0.0.1:8000/websites \
  -H "Content-Type: application/json" \
  -d '{"url":"https://docs.python.org/3/tutorial/","max_pages":5}'
```

Search the indexed documentation:

```bash
curl "http://127.0.0.1:8000/search?q=install&limit=5"
```

## API

### `POST /websites`

Crawls and indexes pages starting from a supplied URL.

Example:

```json
{
  "url": "https://docs.python.org/3/tutorial/",
  "max_pages": 5
}
```

### `GET /search`

Searches indexed documentation.

```text
/search?q=python&limit=10
```

### `GET /health`

Checks that the API and database are available.

## Tests

Run:

```bash
python -m pytest -q
```

The tests cover crawl boundaries, URL normalization, content extraction, error handling, and PostgreSQL search behavior.

## Scope

Docs Scope is deliberately small.

It does not currently execute JavaScript, run background crawl jobs, provide a frontend, or use embeddings or LLM-based retrieval. The goal is to demonstrate a simple end-to-end documentation indexing and search pipeline.