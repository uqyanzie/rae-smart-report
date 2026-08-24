"""Security primitives for path traversal protection and upload sanitization."""

from __future__ import annotations

import re
from pathlib import Path

__all__ = [
    "PathTraversalError",
    "resolve_within_root",
    "sanitize_upload_filename",
]

_CONTROL_OR_FORBIDDEN = re.compile(r'[\x00-\x1f\x7f\\/"\'<>|:*?]')


class PathTraversalError(ValueError):
    """Raised when a candidate path escapes its configured root directory."""


def resolve_within_root(root: Path, candidate: str) -> Path:
    """Resolves ``candidate`` against ``root``, rejecting any escape.

    Absolute candidates and ``..`` climbs are rejected before filesystem
    resolution so a bundled application can never serve outside ``root``.
    """
    if not candidate:
        raise PathTraversalError("Empty path is not resolvable")
    raw = Path(candidate)
    if raw.is_absolute():
        raise PathTraversalError(f"Absolute path rejected: {candidate}")
    root_resolved = root.resolve()
    resolved = (root_resolved / raw).resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise PathTraversalError(f"Path escapes root: {candidate}") from exc
    return resolved


def sanitize_upload_filename(filename: str) -> str:
    """Returns a safe basename for an uploaded file.

    Strips directory components and filesystem-hostile characters; falls
    back to ``upload.xlsx`` when nothing usable remains.
    """
    if not filename:
        return "upload.xlsx"
    name = Path(filename).name
    name = _CONTROL_OR_FORBIDDEN.sub("", name).strip()
    name = name.strip(". ")
    if not name:
        return "upload.xlsx"
    return name
