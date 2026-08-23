---
name: excel-styling-formatter
description: Generates executive-grade Excel (.xlsx) workbooks using OpenPyXL with dual-table layouts, native accounting currency and percentage formatting, total formulas, and professional visual styling.
---

# Excel Styling & Formatter Specialist

This skill defines the visual rules, layout geometry, format strings, and OpenPyXL implementation patterns for rendering executive e-commerce sales reports.

---

## 1. Core Directives & Layout Standards

1. **Dual-Table Representation:** Table 1 contains granular Variant-Level Performance (populated over a catalog-defined fixed grid); Table 2 contains the Master Product Group Grand Summary.
2. **Asymmetric Density — Sparse Left, Complete Right:** Table 1 emits only variant rows with non-zero quantity. Table 2 **always** emits every catalog group in canonical order, including groups with no sales, so the group list stays stable period-over-period.
3. **Empty-Group Rule:** When a group has zero emitted Table 1 rows, write a literal `0` into its quantity and revenue cells rather than a `=SUM(...)` formula. A SUM over an absent range is a broken reference. This is common, not exceptional — in the reference period, 7 of 10 cross-family groups on one sheet had no sales at all.
4. **Zero-Divisor Guard:** Contribution cells divide by a group or grand total. When that divisor is `0`, write a literal `0` instead of a formula. Never emit a division that resolves to `#DIV/0!`.
5. **Native Accounting Formats:** Format numbers directly at the cell level using Excel number format strings (`FORMAT_CURRENCY_IDR`, `FORMAT_INTEGER`, `FORMAT_PERCENTAGE`). Never write pre-formatted strings into numeric cells.
6. **0–1 Unit Share Ratios:** Contribution values represent 0–1 quantity shares formatted via Excel `0.00%`.
7. **No Hardcoded Row Anchors:** All formula ranges and `$H$n` anchors must be computed from actually-emitted row indices. Because Table 1 is sparse, anchors copied from a reference workbook will point at the wrong rows.
8. **Auto-Adjusting Column Widths:** Compute safe lengths from non-formula text to prevent truncated `###` cells without miscalculating formula expressions.
9. **Professional Corporate Palette:** Slate Navy (`#1E293B`) headers, bold white text (`#FFFFFF`), Soft Slate subtotals (`#F1F5F9`), and double bottom borders on totals.

---

## 2. Invariants & Decision Checklist

- [ ] Are cell values written as raw numeric ints/floats rather than formatted string text?
- [ ] Is `FORMAT_CURRENCY_IDR` applied to all revenue cells?
- [ ] Is `FORMAT_PERCENTAGE` applied with raw 0–1 ratio values?
- [ ] Does the summary table contain **every** catalog group, including zero-activity ones?
- [ ] Do zero-activity groups carry a literal `0` rather than a `=SUM(...)` over an empty range?
- [ ] Is every contribution formula guarded against a zero divisor?
- [ ] Are all formula ranges and `$H$n` anchors derived from real emitted row indices, never hardcoded?
- [ ] Are dynamic Excel `=SUM(...)` formulas injected for grand total rows?
- [ ] Is `ws.sheet_view.showGridLines = True` enabled on each worksheet view?

---

## 3. Modular Code References

- **Format Masks & Typography Constants:** [references/format_constants.py](references/format_constants.py)
- **Workbook Generator Implementation:** [examples/report_generator.py](examples/report_generator.py)
