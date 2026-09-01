"""Dual-table executive workbook builder for RAE Smart Report.

Layout per sheet (rows 1+)::

    A-E  Left table  (Variant Breakdown)   - full catalog grid, every row
    F    Blank separator column (width 4)
    G-J  Right table (Group Summary)       - complete: every catalog group

Rules enforced here (2026-08-25 golden-display scope; export display only):

* **Full grid left table** - the left table emits EVERY catalog grid row per
  group, sold or not, so the export reproduces the golden file's data
  display. Unsold variants carry their variant name in col B with C (qty)
  and D (revenue) left blank.
* **Unguarded contribution formulas** - Col E is always
  ``=(C{r}/$H${summary})*100%`` and Col J is always
  ``=(H{r}/$H$grand_total)*100%``, never guarded against a zero divisor;
  zero-total groups therefore evaluate to ``#DIV/0!``, reproducing the
  golden workbook's known cell pattern (user-confirmed).
* **Always-on SUM ranges** - every group's H/I is ``=SUM(C{start}:C{end})``
  / ``=SUM(D{start}:D{end})`` over its full contiguous grid span (the
  Empty-Group literal-0 rule is removed because every group always emits a
  span).
* **No hardcoded anchors** - all ``=SUM(Cx:Cy)`` ranges and ``$H$n`` anchors
  are derived from actually-emitted row indices.
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.domain.models import GridRow
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
    "UnreportedSheet",
    "generate_executive_workbook",
    "render_side_by_side_sheet",
    "render_unreported_sheet",
]

LEFT_HEADERS: tuple[str, ...] = ("Produk", "Nama Variasi", "Produk Terjual", "Revenue", "Kontribusi")
RIGHT_HEADERS: tuple[str, ...] = ("Produk", "Produk Terjual", "Revenue", "Kontribusi")
UNREPORTED_HEADERS: tuple[str, ...] = (
    "Produk",
    "Nama Variasi",
    "Raw Product",
    "Raw Variant",
    "Produk Terjual",
    "Revenue",
)
SEPARATOR_WIDTH = 4
MIN_COLUMN_WIDTH = 14

# Right-table columns: (col, number format)
_INTEGER_COLS = {3, 8}  # Produk Terjual
_CURRENCY_COLS = {4, 9}  # Revenue
_PERCENT_COLS = {5, 10}  # Kontribusi


@dataclass(frozen=True)
class ReportSheet:
    """Inputs for one report sheet: title plus populated grid data."""

    title: str
    populated: Sequence[dict[str, Any]]  # AnalyticsRepository.populate_grid() rows
    grid: Sequence[GridRow]  # canonical catalog grid rows (variant order source)
    group_order: Sequence[str]  # canonical group emission order


@dataclass(frozen=True)
class UnreportedSheet:
    """Inputs for one unreported sheet (Tidak Terlaporkan S/T): title + rows."""

    title: str
    rows: Sequence[dict[str, Any]]  # AnalyticsRepository.unreported_analytics() rows


def _write_header(ws: Worksheet) -> None:
    """Writes and styles the dual-table header row (row 1)."""
    for col, header in enumerate(LEFT_HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER_REGULAR
    for col, header in enumerate(RIGHT_HEADERS, start=7):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER_REGULAR


def _style_data_cell(ws: Worksheet, row: int, col: int) -> None:
    """Applies regular data-cell styling + the column's number mask."""
    cell = ws.cell(row=row, column=col)
    cell.font = FONT_REGULAR
    cell.border = BORDER_REGULAR
    cell.alignment = ALIGN_RIGHT if col in (3, 4, 5, 8, 9, 10) else ALIGN_LEFT
    if col in _INTEGER_COLS:
        cell.number_format = FORMAT_INTEGER
    elif col in _CURRENCY_COLS:
        cell.number_format = FORMAT_CURRENCY_IDR
    elif col in _PERCENT_COLS:
        cell.number_format = FORMAT_PERCENTAGE


def _style_total_row(ws: Worksheet, row: int) -> None:
    """Styles the grand-total row (G/H/I; J intentionally left empty)."""
    for col in (7, 8, 9):
        cell = ws.cell(row=row, column=col)
        cell.font = FONT_TOTAL
        cell.fill = FILL_TOTAL
        cell.border = BORDER_TOTAL
        cell.alignment = ALIGN_RIGHT if col in (8, 9) else ALIGN_LEFT
    ws.cell(row=row, column=8).number_format = FORMAT_INTEGER
    ws.cell(row=row, column=9).number_format = FORMAT_CURRENCY_IDR


def _style_unreported_cell(ws: Worksheet, row: int, col: int) -> None:
    """Applies regular styling + the unreported sheet's number masks.

    Columns: A Produk (text), B Nama Variasi (text), C Raw Product (text),
    D Raw Variant (text), E Produk Terjual (integer), F Revenue (IDR currency).
    """
    cell = ws.cell(row=row, column=col)
    cell.font = FONT_REGULAR
    cell.border = BORDER_REGULAR
    cell.alignment = ALIGN_RIGHT if col in (5, 6) else ALIGN_LEFT
    if col == 5:
        cell.number_format = FORMAT_INTEGER
    elif col == 6:
        cell.number_format = FORMAT_CURRENCY_IDR


def _auto_fit_columns(ws: Worksheet) -> None:
    """Auto-fits columns A-J measuring non-formula strings; F fixed at 4."""
    for col_idx in range(1, 11):
        letter = get_column_letter(col_idx)
        if letter == "F":
            ws.column_dimensions[letter].width = SEPARATOR_WIDTH
            continue
        max_len = 0
        for row in ws.iter_rows(min_col=col_idx, max_col=col_idx):
            value = row[0].value
            if value is None:
                continue
            text = str(value)
            if text.startswith("="):
                continue  # formula expressions measure nothing useful
            max_len = max(max_len, len(text))
        ws.column_dimensions[letter].width = max(max_len + 4, MIN_COLUMN_WIDTH)


def render_side_by_side_sheet(
    ws: Worksheet,
    *,
    populated: Sequence[dict[str, Any]],
    grid: Sequence[GridRow],
    group_order: Sequence[str],
) -> None:
    """Renders one dual-table report sheet into ``ws``.

    ``populated`` rows come from ``AnalyticsRepository.populate_grid`` (which
    returns SQL-alphabetical order); ``grid`` supplies the canonical per-group
    variant sequence, so variant order is never trusted to SQL ordering.
    """
    ws.sheet_view.showGridLines = True
    _write_header(ws)

    # rstrip() on both sides of every key lookup (rae-report-template rule 7).
    lookup: dict[tuple[str, str], dict[str, Any]] = {
        (row["product_group"].rstrip(), row["clean_variant"].rstrip()): row for row in populated
    }

    # Pass 1: full-grid left table (cols A-D). Every catalog grid row is
    # emitted per group in canonical order; the group name lands only on the
    # group's first row. Unsold variants get blank C/D (golden display); the
    # populated lookup is defensive (populate_grid already left-joins zeros).
    spans: dict[str, tuple[int, int]] = {}
    next_row = 2
    for group in group_order:
        group_key = group.rstrip()
        start = next_row
        for gr in grid:
            if gr.product_group.rstrip() != group_key:
                continue
            if next_row == start:
                ws.cell(row=next_row, column=1, value=group_key)
            ws.cell(row=next_row, column=2, value=gr.clean_variant.rstrip())
            pop = lookup.get((group_key, gr.clean_variant.rstrip()))
            if pop is not None and int(pop["total_qty"]) > 0:
                ws.cell(row=next_row, column=3, value=int(pop["total_qty"]))
                ws.cell(row=next_row, column=4, value=int(pop["total_revenue"]))
            _style_data_cell(ws, next_row, 1)
            _style_data_cell(ws, next_row, 2)
            _style_data_cell(ws, next_row, 3)
            _style_data_cell(ws, next_row, 4)
            next_row += 1
        spans[group_key] = (start, next_row - 1)

    grand_total_row = 2 + len(group_order)
    last_summary_row = grand_total_row - 1

    # Pass 2: Col E contribution formulas for every left-table row. The
    # divisor is the group's own H SUM cell; unguarded so zero-total groups
    # reproduce the golden `#DIV/0!`.
    for group, (start, end) in spans.items():
        summary_row = 2 + group_order.index(group)
        for r in range(start, end + 1):
            ws.cell(row=r, column=5, value=f"=(C{r}/$H${summary_row})*100%")
            _style_data_cell(ws, r, 5)

    # Pass 3: complete right table (cols G-J) at fixed summary rows.
    for group_index, group in enumerate(group_order):
        summary_row = 2 + group_index
        group_key = group.rstrip()
        span = spans[group_key]
        ws.cell(row=summary_row, column=7, value=group_key)
        ws.cell(row=summary_row, column=8, value=f"=SUM(C{span[0]}:C{span[1]})")
        ws.cell(row=summary_row, column=9, value=f"=SUM(D{span[0]}:D{span[1]})")
        ws.cell(
            row=summary_row,
            column=10,
            value=f"=(H{summary_row}/$H${grand_total_row})*100%",
        )
        _style_data_cell(ws, summary_row, 7)
        _style_data_cell(ws, summary_row, 8)
        _style_data_cell(ws, summary_row, 9)
        _style_data_cell(ws, summary_row, 10)

    # Grand total row.
    ws.cell(row=grand_total_row, column=7, value="TOTAL")
    ws.cell(row=grand_total_row, column=8, value=f"=SUM(H2:H{last_summary_row})")
    ws.cell(row=grand_total_row, column=9, value=f"=SUM(I2:I{last_summary_row})")
    _style_total_row(ws, grand_total_row)

    # Blank separator column (F) is never written to; pin its width here.
    ws.column_dimensions["F"].width = SEPARATOR_WIDTH


def render_unreported_sheet(ws: Worksheet, *, rows: Sequence[dict[str, Any]]) -> None:
    """Renders one unreported sheet (Tidak Terlaporkan S/T) into ``ws``.

    A single six-column table backed by ``unreported_analytics`` (Query G,
    ``is_reported = 0``): product group, clean variant, raw product, raw
    variant, qty, revenue, plus a TOTAL row. No combinatorial grid and no
    contribution column. Persisted unreported entries appear only here -- never
    in the Produk sheets.
    """
    ws.sheet_view.showGridLines = True
    for col, header in enumerate(UNREPORTED_HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = FONT_HEADER
        cell.fill = FILL_HEADER
        cell.alignment = ALIGN_CENTER
        cell.border = BORDER_REGULAR

    next_row = 2
    for row in rows:
        ws.cell(row=next_row, column=1, value=row["product_group"])
        ws.cell(row=next_row, column=2, value=row["clean_variant"])
        ws.cell(row=next_row, column=3, value=row.get("raw_product"))
        ws.cell(row=next_row, column=4, value=row["raw_variant"])
        ws.cell(row=next_row, column=5, value=int(row["total_qty"]))
        ws.cell(row=next_row, column=6, value=int(row["total_revenue"]))
        for col in range(1, 7):
            _style_unreported_cell(ws, next_row, col)
        next_row += 1

    # TOTAL row: SUM formulas over the data span, or literal 0 when the sheet
    # has no unreported rows (a valid, empty unreported period).
    last_data = next_row - 1
    ws.cell(row=next_row, column=1, value="TOTAL")
    if last_data >= 2:
        ws.cell(row=next_row, column=5, value=f"=SUM(E2:E{last_data})")
        ws.cell(row=next_row, column=6, value=f"=SUM(F2:F{last_data})")
    else:
        ws.cell(row=next_row, column=5, value=0)
        ws.cell(row=next_row, column=6, value=0)
    for col in (1, 5, 6):
        cell = ws.cell(row=next_row, column=col)
        cell.font = FONT_TOTAL
        cell.fill = FILL_TOTAL
        cell.border = BORDER_TOTAL
        cell.alignment = ALIGN_RIGHT if col in (5, 6) else ALIGN_LEFT
    ws.cell(row=next_row, column=5).number_format = FORMAT_INTEGER
    ws.cell(row=next_row, column=6).number_format = FORMAT_CURRENCY_IDR


def _auto_fit_unreported_columns(ws: Worksheet) -> None:
    """Auto-fits columns A-F of an unreported sheet measuring cell strings."""
    for col_idx in range(1, 7):
        letter = get_column_letter(col_idx)
        max_len = 0
        for row in ws.iter_rows(min_col=col_idx, max_col=col_idx):
            value = row[0].value
            if value is None:
                continue
            text = str(value)
            if text.startswith("="):
                continue
            max_len = max(max_len, len(text))
        ws.column_dimensions[letter].width = max(max_len + 4, MIN_COLUMN_WIDTH)


def generate_executive_workbook(
    sheets: Sequence[ReportSheet],
    unreported: Sequence[UnreportedSheet] = (),
) -> io.BytesIO:
    """Builds the executive multi-sheet workbook and returns it as bytes.

    Sheet order follows ``sheets`` (``Produk S``, ``Produk T``,
    ``Produk 2 S``, ``Produk 2 T`` for the standard report); ``unreported``
    sheets (``Tidak Terlaporkan S/T``) are appended after them.
    """
    wb = Workbook()
    if wb.active is not None:
        wb.remove(wb.active)  # drop the default empty sheet
    for sheet in sheets:
        ws = wb.create_sheet(title=sheet.title)
        render_side_by_side_sheet(
            ws,
            populated=sheet.populated,
            grid=sheet.grid,
            group_order=sheet.group_order,
        )
        _auto_fit_columns(ws)
    for usheet in unreported:
        ws = wb.create_sheet(title=usheet.title)
        render_unreported_sheet(ws, rows=usheet.rows)
        _auto_fit_unreported_columns(ws)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
