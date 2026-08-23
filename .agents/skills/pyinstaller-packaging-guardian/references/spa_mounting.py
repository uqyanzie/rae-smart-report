import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

try:
    from .path_resolver import get_bundle_dir
except (ImportError, ValueError):
    from path_resolver import get_bundle_dir

def mount_frontend_spa(app: FastAPI):
    """
    Mounts Vite frontend static files with SPA fallback routing.
    IMPORTANT: This MUST be registered AFTER all API routers are included on `app`
    so API routes take precedence over the wildcard fallback.
    """
    bundle_dir = get_bundle_dir()
    frontend_dist = (bundle_dir / "frontend" / "dist").resolve()
    
    if not frontend_dist.exists():
        # In dev mode, frontend is typically served via Vite dev server
        return

    # Mount static assets (/assets -> frontend/dist/assets)
    assets_dir = (frontend_dist / "assets").resolve()
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA Fallback for non-API client routes
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Exclude reserved API/docs endpoints
        if full_path.startswith("api/") or full_path == "api" or full_path.startswith("docs") or full_path == "openapi.json":
            raise HTTPException(status_code=404, detail="API endpoint not found.")
            
        # Path traversal guard: resolve candidate against frontend_dist root
        safe_full_path = full_path.lstrip("/")
        requested_file = (frontend_dist / safe_full_path).resolve()
        
        try:
            # Ensure resolved path is strictly within frontend_dist
            requested_file.relative_to(frontend_dist)
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied.")
            
        if requested_file.exists() and requested_file.is_file():
            return FileResponse(requested_file)
            
        index_path = (frontend_dist / "index.html").resolve()
        if index_path.exists():
            return FileResponse(index_path)
            
        raise HTTPException(status_code=404, detail="Frontend index.html not found.")
