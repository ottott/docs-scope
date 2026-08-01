from fastapi import APIRouter

from app.schemas.website import WebsiteCreate

router = APIRouter()

@router.post("/websites")
def create_website(website: WebsiteCreate):
    return website