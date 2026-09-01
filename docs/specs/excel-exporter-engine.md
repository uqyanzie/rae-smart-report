# Module Specification: Excel Exporter Engine

## 1. Overview
The Excel Exporter engine transforms SQL query results and declarative master product catalog grids into executive-grade `.xlsx` workbooks using OpenPyXL. It generates side-by-side dual tables, applies native Indonesian accounting currency and percentage number formatting, constructs exact dynamic Excel formulas, and outputs a multi-sheet structure matching executive reporting standards.

---

## 2. Master 16-Sheet Taxonomy & Delivery Phases

The complete reporting system encompasses 16 sheets across 4 e-commerce platforms:

| Sheet Type | Suffix `S` (Shopee) | Suffix `T` (TikTok Shop) | Suffix `TP` (Tokopedia) | Suffix `L` (Lazada) | Phase Scope |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`Produk`** (Single & Intra-Family Bundles) | Y | Y | Y | Y | **Phase 1 (`S`, `T`)** / Phase 2 (`TP`, `L`) |
| **`Produk 2`** (Cross-Family Bundles / *Bundling Silang*) | Y | Y | — | — | **Phase 1 (`S`, `T`)** |
| **`Tidak Terlaporkan`** (Unreported Entries, 2026-08-26) | Y | Y | — | — | **Phase 1 (`S`, `T`)** |
| **`Tinjauan Data`** (Daily Performance Series) | Y | Y | Y | Y | Phase 2 |
| **`Promosi`** (Discounts & Flash Sales) | Y | Y | Y | Y | Phase 2 |
| **`BC`** (Broadcast Chat Performance) | Y | — | — | — | Phase 2 |
| **`Ekspor`** (Destination Country Breakdown) | Y | — | — | — | Phase 2 |

> [!IMPORTANT]
> **Phase 1 Target:** Focuses on the four product performance sheets plus the unreported sheets with complete raw exports and verified golden oracle workbooks: `Produk S`, `Produk T`, `Produk 2 S`, `Produk 2 T`, and `Tidak Terlaporkan S` / `Tidak Terlaporkan T`. The unreported sheets carry **persisted non-reportable** entries (off-grid variants such as standalone `tidak boleh ecer` / `free gift`, and non-catalog product groups); they are additive and never alter the four Produk sheets.

---

## 3. Fixed Combinatorial Grid Architecture

The report layout is a **fixed combinatorial template**, generated declaratively from the master product catalog:

1. **Intra-Family Single Products:** All active shades for each product family (e.g. 11 shades for Glow Up Tint).
2. **Intra-Family Combinatorial Bundles:** All unordered distinct pairs $C(n, 2)$ within the family (e.g. $C(11, 2) = 55$ rows for Bundling Glow Up Tint, $C(6, 2) = 15$ for Bundling Swipe To Glow).
3. **Cross-Family Combinatorial Bundles (`Produk 2`):** Cartesian products of shades across two distinct families (e.g. $11 \times 6 = 66$ rows for Glow Up Tint & Over The Glaze). **Case colour does NOT expand the grid.** Tinted Jelly Balm totals aggregate by shade across all case colours, so a TJB cross grid is $n \times m$, not $n \times m \times 3$. The reference workbook's three 108-row TJB case grids (324 rows total) are empty scaffolding that has never carried data, and no raw export contains a cross-family TJB bundle sale.
4. **Asymmetric Density — Sparse Variants, Complete Groups:** The catalog defines the full combinatorial space and its canonical row order, but the two tables emit it at different densities:
   - **Table 1 (variant rows) is sparse.** Only combinations with non-zero quantity are emitted; zero-sale combinations are omitted entirely. Measured survival for the reference period: `Produk S` 102/181, `Produk T` 92/181, `Produk 2 S` 7/516, `Produk 2 T` 13/840.
   - **Table 2 (group summary) is complete.** Every catalog group is always emitted in `PRODUK_GROUP_ORDER` sequence, with `0` quantity and `0` revenue when it contributed no sales. This keeps the group list stable period-over-period and matches the reference template's group structure.
5. **Empty-Group Rule:** When a group has zero emitted Table 1 rows, its Table 2 quantity and revenue cells must contain a literal `0`, **not** a `=SUM(...)` formula — a SUM over an absent range is a broken reference. Fully-zero groups are common rather than exceptional: in the reference period, `Produk S` and `Produk T` each had 1 of 16, while `Produk 2 S` had **7 of 10** and `Produk 2 T` had **7 of 13**.
6. **Dynamic Anchors Only:** Because Table 1 is sparse, all formula ranges and `$H$n` anchors must be computed from actually-emitted row indices. Anchors transcribed from the reference workbook (e.g. `$H$18`, `sum(C2:C12)`) will reference the wrong rows.

---

## 4. Side-by-Side Dual-Table Layout Geometry

Each product sheet contains two synchronized tables separated by an empty spacing column (Column F):

```text
+---------------------------------------------+   +-------------------------------------------------------+
|        LEFT TABLE: VARIANT BREAKDOWN        |   |       RIGHT TABLE: PRODUCT GROUP SUMMARY              |
| Cols A - E                                  |   | Cols G - J                                            |
+---------------------------------------------+   +-------------------------------------------------------+
| Product Group | Variant | Qty | Rev | Cont% |   | Product Group          | Total Qty | Total Rev | Sh%  |
|---------------+---------+-----+-----+-------|   |------------------------+-----------+-----------+------|
| Glow Up Tint  | Active  | 365 | 25M | =(C/H)|   | Glow Up Tint           | =SUM(C:C) | =SUM(D:D) | %    |
|               | Brave   | 340 | 24M | =(C/H)|   | Bundling Glow Up Tint  | =SUM(C:C) | =SUM(D:D) | %    |
+---------------------------------------------+   | ...                    |           |           |      |
                                                  | TOTAL                  | =SUM(H:H) | =SUM(I:I) | 100% |
                                                  +-------------------------------------------------------+
```

### Table 1: Variant Breakdown (Columns A – E)
* **Col A (`Produk`):** Product Group Name (written only on the first row of the group; subsequent rows for that group are blank).
* **Col B (`Nama Variasi`):** Clean variant label.
  * **Intra-Family Separator:** Joins with ` + ` (e.g., `Active + Brave`).
  * **Cross-Family Separator:** Joins with `, ` (e.g., `Active, Over Cute`).
  * **Case Colour:** Not part of any label or grid dimension. It is captured on the stored record for traceability but never rendered, and never used to split a row. Tinted Jelly Balm rows aggregate by shade across all case colours.
  * **Short-Form Exception:** `Power Frosted Velvet Matte` intra-family bundles drop the ` Power` suffix (`Kind + Honest`, not `Kind Power + Honest Power`). Cross-family labels retain it (`Kind Power, Peony`).
  * **Trailing Whitespace:** Do **not** reproduce the reference workbook's trailing spaces (57 occur in `Produk S` alone, from manual entry). Emit `.rstrip()`-normalised labels and normalise both sides of any comparison.
  * **Row Order:** Labels are emitted in the catalog's **display order**, which differs from its singles order. The authoritative sequences and the `order_for_singles()` / `order_for_pairs()` / `order_for_cross()` accessors live in `.agents/skills/rae-report-template/references/catalog_spec.py`.
* **Col C (`Produk Terjual`):** Quantity sold (integer formatted as `#,##0`).
* **Col D (`Revenue`):** Total sales revenue (raw float formatted as `_("Rp"* #,##0_);_("Rp"* (#,##0);_("Rp"* "-"_);_(@_)`).
* **Col E (`Kontribusi`):** Variant **quantity share** relative to its group total, calculated via Excel formula: `=(C{row}/$H${summary_row})*100%` (formatted as `0.00%`).

### Table 2: Product Group Summary (Columns G – J)
* **Col G (`Produk`):** Master Product Group Name.
* **Col H (`Produk Terjual`):** Group total quantity via formula: `=SUM(C{start_row}:C{end_row})`.
* **Col I (`Revenue`):** Group total revenue via formula: `=SUM(D{start_row}:D{end_row})`.
* **Col J (`Kontribusi`):** Product group **quantity share** of platform total via formula: `=(H{row}/$H${grand_total_row})*100%`.
* **Grand Total Row:** Placed immediately below the summary table with `=SUM(H2:H{last_row})` and `=SUM(I2:I{last_row})`.

### 4.1 Unreported Entries Sheet (Tidak Terlaporkan S / T)

Added by the 2026-08-26 scope extension. One sheet per platform batch present in the export (`Tidak Terlaporkan S`, `Tidak Terlaporkan T`), rendered **after** the platform's `Produk` and `Produk 2` sheets. The sheet is a single simple table backed by Query G (`is_reported = 0`) — it has no combinatorial grid and no contribution column:

| Col | Header | Source | Format |
| :--- | :--- | :--- | :--- |
| A | `Produk` | `product_group` | text |
| B | `Nama Variasi` | `clean_variant` | text |
| C | `Raw Product` | `raw_product` (verbatim source product column) | text |
| D | `Raw Variant` | `raw_variant` (full provenance) | text |
| E | `Produk Terjual` | `total_qty` | `#,##0` |
| F | `Revenue` | `total_revenue` | IDR accounting |

- **TOTAL row:** `=SUM(E{start}:E{end})` and `=SUM(F{start}:F{end})` beneath the last data row, styled with the double-bottom accounting border.
- **Styling:** identical slate palette, header fill, thin borders, and number masks as the Produk sheets.
- **Boundary:** unreported rows appear **only** here — never in `Produk S/T` or `Produk 2 S/T`, whose queries filter `is_reported = 1`. When a platform batch has no unreported entries, its `Tidak Terlaporkan` sheet is still emitted with only the header + a `0` TOTAL row.

---

## 5. Visual Styling & Workbook Construction Rules

1. **Header Palette:** Dark Slate Navy fill (`#1E293B`) with white bold text (`#FFFFFF`), centered alignment.
2. **Number Formats (Native Accounting):**
   * Currency (IDR): `_("Rp"* #,##0_);_("Rp"* (#,##0);_("Rp"* "-"_);_(@_)`
   * Percentage: `0.00%`
   * Quantity / Integer: `#,##0`
3. **Borders:** Thin slate borders (`#CBD5E1`) for data cells; double bottom accounting border for Grand Total row.
4. **Worksheet Views:** Explicitly enable grid lines:
   ```python
   ws.sheet_view.showGridLines = True
   ```
5. **Dynamic Column Widths:** Auto-calculate column widths based on maximum rendered string length + 4 padding (skipping formula strings to avoid truncated `###` cells).
6. **Defect Prevention In Formulas:**
   - **No Double-Counting Range Overruns:** In `Produk 2 S`, ensure formula ranges strictly match exact group boundaries (do NOT replicate the reference-file defect where Group 9 summed `C374:C445`, overrunning into Power Frosted).
   - **Empty-Range Guard:** Never emit `=SUM(...)` for a group with no emitted variant rows; write a literal `0`. See section 3 rule 5.
   - **Division by Zero Guard:** Contribution cells (Col E, Col J) divide by a group or grand total. When that divisor is `0`, write a literal `0` instead of a formula, so no cell can render `#DIV/0!` as the reference workbook does in `Produk L`.

---

## 6. Reference Implementation
- Authoritative master product catalog, combinatorial pairing rules, and shade aliases are maintained in `@rae-report-template`.
- Formatting constants and openpyxl styling routines are maintained in `@excel-styling-formatter`.