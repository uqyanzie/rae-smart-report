---
name: excel-styling-formatter
description: Generates executive-grade Excel (.xlsx) workbooks using OpenPyXL with dual-table layouts, native accounting currency and percentage formatting, total formulas, and professional visual styling.
---

# Excel Styling & Formatter Specialist

This skill defines the visual rules, layout geometry, format strings, and OpenPyXL implementation patterns for rendering executive e-commerce sales reports.

---

## 1. Core Directives & Layout Standards

1. **Dual-Table Representation:** Table 1 contains granular Variant-Level Performance (populated over a catalog-defined fixed grid); Table 2 contains the Master Product Group Grand Summary.
2. **Native Accounting Formats:** Format numbers directly at the cell level using Excel number format strings (`FORMAT_CURRENCY_IDR`, `FORMAT_INTEGER`, `FORMAT_PERCENTAGE`). Never write pre-formatted strings into numeric cells.
3. **0–1 Unit Share Ratios:** Contribution values represent 0–1 quantity shares formatted via Excel `0.00%`.
4. **Auto-Adjusting Column Widths:** Compute safe lengths from non-formula text to prevent truncated `###` cells without miscalculating formula expressions.
5. **Professional Corporate Palette:** Slate Navy (`#1E293B`) headers, bold white text (`#FFFFFF`), Soft Slate subtotals (`#F1F5F9`), and double bottom borders on totals.

---

## 2. Invariants & Decision Checklist

- [ ] Are cell values written as raw numeric ints/floats rather than formatted string text?
- [ ] Is `FORMAT_CURRENCY_IDR` applied to all revenue cells?
- [ ] Is `FORMAT_PERCENTAGE` applied with raw 0–1 ratio values?
- [ ] Are dynamic Excel `=SUM(...)` formulas injected for grand total rows?
- [ ] Is `ws.sheet_view.showGridLines = True` enabled on each worksheet view?

---

## 3. Modular Code References

- **Format Masks & Typography Constants:** [references/format_constants.py](references/format_constants.py)
- **Workbook Generator Implementation:** [examples/report_generator.py](examples/report_generator.py)
