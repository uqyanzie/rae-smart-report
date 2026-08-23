---
name: excel-styling-formatter
description: Generates executive-grade Excel (.xlsx) workbooks using OpenPyXL with dual-table layouts, native accounting currency and percentage formatting, total formulas, and professional visual styling.
---

# Excel Styling & Formatter Specialist

This skill defines the visual rules, layout geometry, format strings, and OpenPyXL implementation patterns for rendering executive e-commerce sales reports.

---

## 1. Core Directives & Layout Standards

1. **Dual-Table Representation:** Table 1 contains granular Variant-Level Performance; Table 2 contains the Master Product Group Grand Summary.
2. **Native Accounting Formats:** Format numbers directly at the cell level using Excel number format strings. Never write pre-formatted strings like `"Rp 100.000"` into numeric cells.
3. **Auto-Adjusting Column Widths:** Compute string lengths for all column values and set widths dynamically to prevent truncated `###` cells.
4. **Professional Corporate Palette:** Slate Navy (`#1E293B`) headers, bold white text (`#FFFFFF`), Soft Slate subtotals (`#F1F5F9`), and double bottom borders on totals.

---

## 2. Invariants & Decision Checklist

- [ ] Are cell values written as raw numeric floats/ints rather than formatted string text?
- [ ] Is `FORMAT_CURRENCY_IDR` applied to all revenue cells?
- [ ] Is `FORMAT_PERCENTAGE` applied with contribution values divided by 100 (`val / 100.0`)?
- [ ] Are dynamic Excel `=SUM(...)` formulas injected for grand total rows?
- [ ] Is `showGridLines = True` enabled on the worksheet view?

---

## 3. Modular Code References

- **Format Masks & Typography Constants:** [references/format_constants.py](references/format_constants.py)
- **Workbook Generator Implementation:** [examples/report_generator.py](examples/report_generator.py)
