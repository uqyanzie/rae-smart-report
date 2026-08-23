"""Structured exception classes for spreadsheet ingestion."""

from __future__ import annotations

from typing import List, Optional


class IngestionError(Exception):
    """Base exception for all ingestion failures."""


class UnsupportedFormatError(IngestionError):
    """Raised when an unsupported file format or extension is provided."""

    def __init__(self, filename: str, supported: Optional[List[str]] = None) -> None:
        supported_str = ", ".join(supported) if supported else ".xlsx, .csv"
        super().__init__(
            f"Unsupported file format for '{filename}'. Only {supported_str} are supported."
        )
        self.filename = filename


class SpreadsheetEmptyError(IngestionError):
    """Raised when the uploaded spreadsheet contains no data or rows."""

    def __init__(self, sheet_name: Optional[str] = None) -> None:
        msg = f"Sheet '{sheet_name}' is empty." if sheet_name else "Spreadsheet contains no data rows."
        super().__init__(msg)
        self.sheet_name = sheet_name


class SheetNotFoundError(IngestionError):
    """Raised when the requested sheet does not exist in the workbook."""

    def __init__(self, requested_sheet: str, available_sheets: List[str]) -> None:
        super().__init__(
            f"Sheet '{requested_sheet}' not found. Available sheets: {', '.join(available_sheets)}"
        )
        self.requested_sheet = requested_sheet
        self.available_sheets = available_sheets


class MissingRequiredColumnError(IngestionError):
    """Raised when mandatory marketplace columns are absent from the spreadsheet."""

    def __init__(self, missing_columns: List[str], available_headers: List[str], platform: str = "") -> None:
        platform_prefix = f"[{platform}] " if platform else ""
        super().__init__(
            f"{platform_prefix}Missing required column(s): {missing_columns}. "
            f"Available headers: {available_headers}"
        )
        self.missing_columns = missing_columns
        self.available_headers = available_headers
        self.platform = platform


class InvalidSpreadsheetError(IngestionError):
    """Raised when the spreadsheet file is corrupted or unparseable."""

    def __init__(self, filename: str, reason: str) -> None:
        super().__init__(f"Failed to parse spreadsheet '{filename}': {reason}")
        self.filename = filename
        self.reason = reason
