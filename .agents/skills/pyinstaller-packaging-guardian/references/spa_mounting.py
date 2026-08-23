import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from .path_resolver import get_bundle_dir

def mount_frontend_spa(app: FastAPI):
    """
    Mounts Vite frontend static files with SPA fallback routing.
    """
    bundle_dir = get_bundle_dir()
    frontend_dist = bundle_dir / "frontend" / "dist"
    
    if not frontend_dist.exists():
        # In dev mode, frontend might be served by Vite server directly
        return

    # Mount static assets (js, css, images)
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA Fallback for all non-API routes
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        if full_path.startswith("api") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            raise HTTPException(status_code=404, detail="Not Found")
            
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
            
        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
            
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
