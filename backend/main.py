import os
from fastapi import FastAPI
from .auth import router as auth_router

app = FastAPI(title="Content Feed Auth API")
app.include_router(auth_router, prefix="/auth")

# Optional: expose a health endpoint
@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
