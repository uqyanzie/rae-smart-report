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

__all__ = [
    "Settings",
    "get_settings",
    "get_writable_app_dir",
    "resolve_database_url",
    "resolve_frontend_dist",
    "resolve_sku_mapping_path",
]

_APP_DIR_NAME = "RAESmartReport"
_APP_VERSION = "0.1.0"
_DEV_DATABASE_URL = "sqlite:///rae_smart_report.db"
_DEFAULT_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB


def _is_frozen() -> bool:
    """True when running inside a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def _exe_dir() -> Path:
    """Directory containing the running executable."""
    return Path(sys.executable).resolve().parent


def _resolve_tray() -> bool:
    """Tray enabled by default only in a frozen build; ``RAE_TRAY`` overrides."""
    raw = os.environ.get("RAE_TRAY")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return _is_frozen()


def _resolve_idle_shutdown_seconds() -> int:
    """Auto-exit grace period; ``0`` keeps the app running until tray Exit."""
    raw = os.environ.get("RAE_IDLE_SHUTDOWN_SECONDS")
    if raw is None:
        return 180
    try:
        return max(0, int(raw))
    except ValueError:
        return 180


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


def resolve_sku_mapping_path() -> Path:
    """Resolves the Lazada ``sku_mapping.json`` runtime artifact.

    Priority: ``RAE_SKU_MAPPING`` env var -> bundled ``sys._MEIPASS/data`` or
    the executable directory for PyInstaller builds -> repository
    ``backend/app/data/sku_mapping.json`` for development.
    """
    env_path = os.environ.get("RAE_SKU_MAPPING")
    if env_path:
        return Path(env_path)
    if _is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass) / "data" / "sku_mapping.json"
        return _exe_dir() / "data" / "sku_mapping.json"
    return _find_repo_root() / "backend" / "app" / "data" / "sku_mapping.json"


@dataclass(frozen=True)
class Settings:
    """Application settings resolved at startup."""

    app_name: str = "RAESmartReport"
    version: str = _APP_VERSION
    database_url: str = field(default_factory=resolve_database_url)
    frontend_dist: Path = field(default_factory=resolve_frontend_dist)
    host: str = field(default_factory=lambda: os.environ.get("RAE_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.environ.get("RAE_PORT", "8000")))
    skip_browser: bool = field(
        default_factory=lambda: os.environ.get("RAE_SKIP_BROWSER", "").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    tray: bool = field(default_factory=_resolve_tray)
    idle_shutdown_seconds: int = field(default_factory=_resolve_idle_shutdown_seconds)
    max_upload_bytes: int = _DEFAULT_MAX_UPLOAD_BYTES
    cors_allow_origins: list[str] = field(default_factory=lambda: ["*"])


_settings: Settings | None = None


def get_settings() -> Settings:
    """Returns the process-wide cached Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
