"""SPA static mounting with path traversal protection and index fallback."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.errors import error_response
from app.core.config import get_settings
from app.core.security import PathTraversalError, resolve_within_root

__all__ = ["mount_frontend_spa"]


def mount_frontend_spa(app: FastAPI) -> None:
    """Mounts the built frontend as a static SPA with index fallback.

    No-op (API-only mode) when ``frontend/dist`` does not exist yet, so the
    backend runs standalone until the frontend build is produced.
    """
    dist = get_settings().frontend_dist
    if not dist.is_dir():
        return

    assets_dir = dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str, request: Request):
        # API, docs, and schema routes must never fall through to the SPA.
        if full_path.startswith(("api/", "docs")) or full_path in ("api", "openapi.json"):
            return error_response(404, "HTTP_ERROR", "API endpoint not found")

        index_file = dist / "index.html"

        # The root path has no candidate to resolve; serve the index directly.
        if not full_path:
            if index_file.is_file():
                return FileResponse(index_file)
            return error_response(404, "HTTP_ERROR", "Not Found")

        try:
            candidate = resolve_within_root(dist, full_path)
        except PathTraversalError:
            return error_response(403, "HTTP_ERROR", "Access denied")

        if candidate.is_file():
            return FileResponse(candidate)

        if index_file.is_file():
            return FileResponse(index_file)

        return error_response(404, "HTTP_ERROR", "Not Found")
