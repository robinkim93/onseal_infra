"""FastAPI 진입점. [delegate 스캐폴딩 — 라우트 살은 당신이]"""

from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Onseal", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(router)
