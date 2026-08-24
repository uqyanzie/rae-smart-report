"""Executive OpenPyXL report exporter (Phase 5).

Provides the dual-table workbook builder (sparse variant breakdown + complete
group summary) with native accounting number formats and dynamic formula
ranges. See ``report_builder.py`` and ``styles.py``.
"""

from __future__ import annotations

from app.modules.exporter.report_builder import (
    ReportSheet,
    generate_executive_workbook,
    render_side_by_side_sheet,
)
from app.modules.exporter.styles import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    BORDER_REGULAR,
    BORDER_TOTAL,
    FILL_HEADER,
    FILL_TOTAL,
    FONT_HEADER,
    FONT_REGULAR,
    FONT_TOTAL,
    FORMAT_CURRENCY_IDR,
    FORMAT_INTEGER,
    FORMAT_PERCENTAGE,
)

__all__ = [
    "ReportSheet",
    "generate_executive_workbook",
    "render_side_by_side_sheet",
    "FORMAT_CURRENCY_IDR",
    "FORMAT_PERCENTAGE",
    "FORMAT_INTEGER",
    "FONT_HEADER",
    "FONT_REGULAR",
    "FONT_TOTAL",
    "FILL_HEADER",
    "FILL_TOTAL",
    "ALIGN_LEFT",
    "ALIGN_RIGHT",
    "ALIGN_CENTER",
    "BORDER_REGULAR",
    "BORDER_TOTAL",
]
