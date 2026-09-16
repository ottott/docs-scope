from fastapi import APIRouter, HTTPException, Query

from app import db
from app.crawler import crawl
from app.schemas.website import WebsiteCreate

router = APIRouter()


@router.post("/websites")
def create_website(website: WebsiteCreate):
    pages, attempted, errors = crawl(str(website.url), website.max_pages)
    if not pages:
        raise HTTPException(status_code=422, detail={"message": "No pages indexed", "errors": errors})
    db.save_pages(pages)
    return {"indexed": len(pages), "attempted": attempted, "errors": errors}


@router.get("/search")
def search(q: str = Query(min_length=1, max_length=200), limit: int = Query(default=10, ge=1, le=50)):
    if not q.strip():
        raise HTTPException(status_code=422, detail="Search query must not be blank")
    return {"results": db.search_pages(q, limit)}
