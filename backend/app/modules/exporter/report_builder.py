"""Dual-table executive workbook builder for RAE Smart Report.

Layout per sheet (rows 1+)::

    A-E  Left table  (Variant Breakdown)   - sparse: only qty > 0 rows
    F    Blank separator column (width 4)
    G-J  Right table (Group Summary)       - complete: every catalog group

Rules enforced here (see ``excel-styling-formatter`` skill):

* **Sparse left / complete right** - the left table emits only variant rows
  with ``total_qty > 0``, while the right table always emits every group in
  ``group_order``, even when it sold nothing, so the group list stays stable
  period-over-period.
* **Empty-Group Rule** - a group with zero emitted left-table rows gets a
  literal integer ``0`` in its H/I cells, never a ``=SUM(...)`` over an
  absent range (a broken reference).
* **Contribution Guard** - Col E and Col J divide by a group/grand total;
  when the divisor is ``0`` a literal ``0`` is written instead of a formula,
  so the workbook never reproduces the reference workbook's ``#DIV/0!``.
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
    "generate_executive_workbook",
    "render_side_by_side_sheet",
]

LEFT_HEADERS: tuple[str, ...] = ("Produk", "Nama Variasi", "Produk Terjual", "Revenue", "Kontribusi")
RIGHT_HEADERS: tuple[str, ...] = ("Produk", "Produk Terjual", "Revenue", "Kontribusi")
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


def _contribution_or_zero(numerator: str, denominator: str, divisor_is_zero: bool) -> str | int:
    """Returns ``=(<numerator>/<denominator>)*100%`` or literal ``0`` when the divisor is zero."""
    if divisor_is_zero:
        return 0
    return f"=({numerator}/{denominator})*100%"


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

    # Pass 1: sparse left table (cols A-D), tracking each group's emitted span
    # and quantity totals (never re-read cells for arithmetic).
    spans: dict[str, tuple[int, int]] = {}
    group_totals: dict[str, int] = {}
    sheet_total_qty = 0
    next_row = 2
    for group in group_order:
        group_key = group.rstrip()
        start = next_row
        group_total_qty = 0
        for gr in grid:
            if gr.product_group.rstrip() != group_key:
                continue
            pop = lookup.get((group_key, gr.clean_variant.rstrip()))
            if pop is None or int(pop["total_qty"]) <= 0:
                continue
            if next_row == start:
                # Group name only on the group's first emitted row.
                ws.cell(row=next_row, column=1, value=group_key)
            ws.cell(row=next_row, column=2, value=gr.clean_variant.rstrip())
            ws.cell(row=next_row, column=3, value=int(pop["total_qty"]))
            ws.cell(row=next_row, column=4, value=int(pop["total_revenue"]))
            _style_data_cell(ws, next_row, 1)
            _style_data_cell(ws, next_row, 2)
            _style_data_cell(ws, next_row, 3)
            _style_data_cell(ws, next_row, 4)
            group_total_qty += int(pop["total_qty"])
            next_row += 1
        if next_row > start:
            spans[group_key] = (start, next_row - 1)
            group_totals[group_key] = group_total_qty
            sheet_total_qty += group_total_qty

    grand_total_row = 2 + len(group_order)
    last_summary_row = grand_total_row - 1

    # Pass 2: Col E contribution formulas for emitted variant rows. The divisor
    # is the group's own H total, so it can only be 0 when the group has no
    # emitted rows -- in which case there are no E cells either. Guard anyway.
    for group, (start, end) in spans.items():
        summary_row = 2 + group_order.index(group)
        divisor_is_zero = group_totals[group] <= 0
        for r in range(start, end + 1):
            ws.cell(
                row=r,
                column=5,
                value=_contribution_or_zero(f"C{r}", f"$H${summary_row}", divisor_is_zero),
            )
            _style_data_cell(ws, r, 5)

    # Pass 3: complete right table (cols G-J) at fixed summary rows.
    for group_index, group in enumerate(group_order):
        summary_row = 2 + group_index
        group_key = group.rstrip()
        span = spans.get(group_key)
        ws.cell(row=summary_row, column=7, value=group_key)
        if span is None:
            # Empty-Group Rule: literal 0, never =SUM() over an absent range.
            ws.cell(row=summary_row, column=8, value=0)
            ws.cell(row=summary_row, column=9, value=0)
        else:
            ws.cell(row=summary_row, column=8, value=f"=SUM(C{span[0]}:C{span[1]})")
            ws.cell(row=summary_row, column=9, value=f"=SUM(D{span[0]}:D{span[1]})")
        ws.cell(
            row=summary_row,
            column=10,
            value=_contribution_or_zero(f"H{summary_row}", f"$H${grand_total_row}", sheet_total_qty <= 0),
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


def generate_executive_workbook(sheets: Sequence[ReportSheet]) -> io.BytesIO:
    """Builds the executive multi-sheet workbook and returns it as bytes.

    Sheet order follows ``sheets`` (``Produk S``, ``Produk T``,
    ``Produk 2 S``, ``Produk 2 T`` for the standard report).
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
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
