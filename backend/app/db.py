import psycopg
from psycopg.rows import dict_row

from app.config import DATABASE_URL


def connect():
    return psycopg.connect(DATABASE_URL, connect_timeout=5, row_factory=dict_row)


def initialize():
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pages (
                url TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                crawled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                search_vector TSVECTOR GENERATED ALWAYS AS (
                    setweight(to_tsvector('english', title), 'A') ||
                    setweight(to_tsvector('english', text), 'B')
                ) STORED
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS pages_search_idx ON pages USING GIN(search_vector)")


def save_pages(pages):
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.executemany("""
                INSERT INTO pages (url, title, text) VALUES (%(url)s, %(title)s, %(text)s)
                ON CONFLICT (url) DO UPDATE SET
                    title = EXCLUDED.title, text = EXCLUDED.text, crawled_at = now()
            """, pages)


def search_pages(query, limit):
    with connect() as conn:
        return conn.execute("""
            SELECT title, url, left(ts_headline('english', text, query,
                'StartSel="", StopSel="", MaxWords=35, MinWords=15, MaxFragments=1'), 300) AS snippet
            FROM pages, websearch_to_tsquery('english', %s) query
            WHERE search_vector @@ query
            ORDER BY ts_rank_cd(search_vector, query) DESC, url
            LIMIT %s
        """, (query, limit)).fetchall()
