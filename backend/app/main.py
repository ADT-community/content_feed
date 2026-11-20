"""content_feed backend.

Run from backend/:  uvicorn app.main:app --reload
Interactive docs:   http://127.0.0.1:8000/docs
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import auth

# INFO on the root logger so the mocked SMS codes show up on the console.
logging.basicConfig(
    level=os.environ.get("FEED_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
)

app = FastAPI(
    title="content_feed API",
    version="0.1.0",
    description="Backend skeleton. Phone sign-in with one-time codes (SMS mocked).",
)

# The web app in web/ is served from a different origin and points at this API
# via FEED_CONFIG.apiUrl, so it needs CORS. Lock this down in production with
# FEED_CORS_ORIGINS="https://example.org,https://www.example.org".
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("FEED_CORS_ORIGINS", "*").split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}
