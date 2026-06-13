"""FastAPI 진입점. [delegate 스캐폴딩 — 라우트 살은 당신이]"""

from fastapi import FastAPI

app = FastAPI(title="Onseal", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# TODO(reviewer): /ingest, /query 라우트 — app/api/ 에 작성 후 여기서 include_router
