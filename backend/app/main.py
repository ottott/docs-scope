from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import psycopg

from app import db
from app.api.websites import router as website_router


@asynccontextmanager
async def lifespan(app):
    db.initialize()
    yield


app = FastAPI(title="Docs Scope", lifespan=lifespan)


@app.exception_handler(psycopg.OperationalError)
def database_unavailable(request: Request, exc):
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


@app.get("/health")
def health():
    with db.connect() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


app.include_router(website_router)
