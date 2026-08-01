from pydantic import BaseModel, HttpUrl


class WebsiteCreate(BaseModel):
    url: HttpUrl