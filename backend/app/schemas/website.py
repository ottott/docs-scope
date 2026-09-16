from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.config import MAX_CRAWL_PAGES


class WebsiteCreate(BaseModel):
    url: HttpUrl
    max_pages: int = Field(default=MAX_CRAWL_PAGES, ge=1, le=MAX_CRAWL_PAGES)

    @field_validator("url")
    @classmethod
    def no_credentials(cls, value):
        if value.username is not None or value.password is not None:
            raise ValueError("URL credentials are not supported")
        return value
