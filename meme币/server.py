from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from live_data import DexMemeService, unique_keywords

ROOT = Path(__file__).resolve().parent

app = FastAPI(title="MemeRadar Live", version="1.0.0")
service = DexMemeService()

app.mount("/css", StaticFiles(directory=ROOT / "css"), name="css")
app.mount("/js", StaticFiles(directory=ROOT / "js"), name="js")


@app.on_event("startup")
async def on_startup() -> None:
    await service.startup()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await service.shutdown()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": "live"}


@app.get("/api/dashboard")
async def dashboard(
    keywords: str | None = Query(default=None, description="Comma-separated meme search keywords"),
) -> dict:
    parsed_keywords = unique_keywords(keywords.split(",") if keywords else None)
    return await service.get_dashboard(parsed_keywords)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/{path_name:path}")
async def spa_fallback(path_name: str) -> FileResponse:
    candidate = ROOT / path_name
    if candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(ROOT / "index.html")
