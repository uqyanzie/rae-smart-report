"""Runtime configuration and environment-aware path resolution.

Packaged-mode paths resolve to the OS writable data directory
(``%LOCALAPPDATA%/RAESmartReport`` on Windows) so bundled executables never
write into ``sys._MEIPASS``.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

__all__ = [
    "Settings",
    "get_settings",
    "get_writable_app_dir",
    "resolve_database_url",
    "resolve_frontend_dist",
]

_APP_DIR_NAME = "RAESmartReport"
_DEV_DATABASE_URL = "sqlite:///rae_smart_report.db"
_DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


def _is_frozen() -> bool:
    """True when running inside a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def _exe_dir() -> Path:
    """Directory containing the running executable."""
    return Path(sys.executable).resolve().parent


def get_writable_app_dir() -> Path:
    """Returns a writable per-user application directory.

    Priority: ``%LOCALAPPDATA%/RAESmartReport`` on Windows -> frozen exe dir ->
    current working directory.
    """
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            app_dir = Path(local_app_data) / _APP_DIR_NAME
            app_dir.mkdir(parents=True, exist_ok=True)
            return app_dir
    if _is_frozen():
        return _exe_dir()
    return Path.cwd()


def resolve_database_url() -> str:
    """Resolves the SQLite database URL.

    Priority: ``RAE_DATABASE_URL`` env var -> packaged writable dir ->
    CWD-relative ``rae_smart_report.db`` (historical dev default).
    """
    env_url = os.environ.get("RAE_DATABASE_URL")
    if env_url:
        return env_url
    if _is_frozen():
        return f"sqlite:///{(get_writable_app_dir() / 'app_data.db').as_posix()}"
    return _DEV_DATABASE_URL


def _find_repo_root() -> Path:
    """Walks upward from CWD looking for repository sentinels."""
    current = Path.cwd().resolve()
    for ancestor in (current, *current.parents):
        if (ancestor / "AGENTS.md").is_file() or (ancestor / ".git").is_dir():
            return ancestor
    return current


def resolve_frontend_dist() -> Path:
    """Resolves the built frontend ``dist`` directory.

    Priority: ``RAE_FRONTEND_DIST`` env var -> bundled ``sys._MEIPASS/frontend/dist``
    -> repository root ``frontend/dist``.
    """
    env_dist = os.environ.get("RAE_FRONTEND_DIST")
    if env_dist:
        return Path(env_dist)
    if _is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass) / "frontend" / "dist"
        return _exe_dir() / "frontend" / "dist"
    return _find_repo_root() / "frontend" / "dist"


@dataclass(frozen=True)
class Settings:
    """Application settings resolved at startup."""

    app_name: str = "RAESmartReport"
    database_url: str = field(default_factory=resolve_database_url)
    frontend_dist: Path = field(default_factory=resolve_frontend_dist)
    host: str = "127.0.0.1"
    port: int = 8000
    max_upload_bytes: int = _DEFAULT_MAX_UPLOAD_BYTES
    cors_allow_origins: List[str] = field(default_factory=lambda: ["*"])


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Returns the process-wide cached Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
