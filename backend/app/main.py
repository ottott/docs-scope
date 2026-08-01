from fastapi import FastAPI

from app.api.websites import router as website_router

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(website_router)