"""Unit tests for path resolution and upload-filename sanitization."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.security import PathTraversalError, resolve_within_root, sanitize_upload_filename


def test_resolve_within_root_rejects_empty_path(tmp_path):
    with pytest.raises(PathTraversalError):
        resolve_within_root(tmp_path, "")


def test_resolve_within_root_rejects_absolute_path(tmp_path):
    with pytest.raises(PathTraversalError):
        resolve_within_root(tmp_path, str(tmp_path / "escape.txt"))


def test_resolve_within_root_rejects_parent_climb(tmp_path):
    with pytest.raises(PathTraversalError):
        resolve_within_root(tmp_path, "../outside.txt")


def test_resolve_within_root_accepts_nested_file(tmp_path):
    nested = tmp_path / "assets" / "app.js"
    nested.parent.mkdir()
    nested.write_text("x", encoding="utf-8")
    assert resolve_within_root(tmp_path, "assets/app.js") == nested


def test_resolve_within_root_accepts_deep_fallback(tmp_path):
    assert resolve_within_root(tmp_path, "some/spa/route") == (tmp_path / "some/spa/route").resolve()


def test_sanitize_upload_filename_strips_traversal(tmp_path):
    assert sanitize_upload_filename("../../etc/passwd.csv") == "passwd.csv"


def test_sanitize_upload_filename_keeps_basename(tmp_path):
    assert sanitize_upload_filename("C:/users/me/report.xlsx") == "report.xlsx"


def test_sanitize_upload_filename_falls_back_on_empty(tmp_path):
    assert sanitize_upload_filename("") == "upload.xlsx"
    assert sanitize_upload_filename("   ") == "upload.xlsx"
