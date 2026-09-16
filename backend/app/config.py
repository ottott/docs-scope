import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/docsscope"
)
MAX_CRAWL_PAGES = int(os.getenv("MAX_CRAWL_PAGES", "20"))
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10"))
if not 1 <= MAX_CRAWL_PAGES <= 100:
    raise ValueError("MAX_CRAWL_PAGES must be between 1 and 100")
if not 0 < REQUEST_TIMEOUT <= 30:
    raise ValueError("REQUEST_TIMEOUT must be greater than 0 and at most 30 seconds")
