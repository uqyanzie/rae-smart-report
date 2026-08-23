# Module Specification: Excel Exporter Engine

## 1. Overview
The Excel Exporter engine transforms SQL query results into formatted `.xlsx` workbooks containing styled side-by-side dual tables, appropriate number formatting (accounting IDR and percentage formats), and structured multi-sheet representations matching executive reporting standards.

---

## 2. Multi-Sheet Taxonomy & Structure

The generated workbook outputs dedicated sheets per platform:
* **`Produk S` (Shopee Single & Intra-Product Bundling):** Contains single products and single-line bundles (e.g. `Glow Up Tint`, `Bundling Glow Up Tint`).
* **`Produk 2 S` (Shopee Cross-Product Bundling / *Bundling Silang*):** Contains cross-product combinations (e.g. `Bundling Glow Up Tint & Over The Glaze`).
* **`Produk T` (TikTok Shop Single & Intra-Product Bundling):** Single products and intra-product bundles from TikTok Shop.
* **`Produk 2 T` (TikTok Shop Cross-Product Bundling / *Bundling Silang*):** Cross-product combos from TikTok Shop.

---

## 3. Side-by-Side Dual-Table Layout Geometry

Each sheet contains two synchronized tables placed side-by-side with a 1-column separator (Column F):

```text
+---------------------------------------------+   +------------------------------------------------------=+
|        LEFT TABLE: VARIANT BREAKDOWN        |   |       RIGHT TABLE: PRODUCT GROUP SUMMARY              |
| Cols A - E                                  |   | Cols G - L                                            |
+---------------------------------------------+   +-------------------------------------------------------+
| Product Group | Variant | Qty | Rev | Cont% |   | Product Group          | Total Qty | Total Rev | Sh%  |
|---------------+---------+-----+-----+-------|   |------------------------+-----------+-----------+------|
| Glow Up Tint  | Active  | 854 | 46M | =(C/H)|   | Glow Up Tint           | =SUM(C:C) | =SUM(D:D) | %    |
|               | Brave   | 791 | 44M | =(C/H)|   | Bundling Glow Up Tint  | =SUM(C:C) | =SUM(D:D) | %    |
+---------------------------------------------+   | ...                    |           |           |      |
                                                  | TOTAL                  | =SUM(H:H) | =SUM(I:I) | 100% |
                                                  +-------------------------------------------------------+
```

### Table 1 (Left Table: Columns A – E)
* **Col A (`Produk`):** Master Product Group Name (written on the first row of the group; subsequent rows for that group are blank).
* **Col B (`Nama Variasi`):** Clean variant name (e.g., `Active`, `Brave`, `Active + Brave`, `Active, Over Cute`).
* **Col C (`Produk Terjual`):** Quantity sold (raw integer value formatted as `#,##0`).
* **Col D (`Revenue`):** Total sales revenue (raw float value formatted as `_("Rp"* #,##0_);_("Rp"* (#,##0);_("Rp"* "-"_);_(@_)`).
* **Col E (`Kontribusi`):** Variant percentage contribution relative to its product group, calculated via Excel formula: `=(C{row}/$H${summary_row})*100%` (formatted as `0.00%`).

### Table 2 (Right Table: Columns G – J)
* **Col G (`Produk`):** Master Product Group Name.
* **Col H (`Produk Terjual`):** Group total quantity calculated via Excel formula: `=SUM(C{start_row}:C{end_row})`.
* **Col I (`Revenue`):** Group total revenue calculated via Excel formula: `=SUM(D{start_row}:D{end_row})`.
* **Col J (`Kontribusi`):** Product group share of overall platform sales calculated via Excel formula: `=(H{row}/$H${grand_total_row})*100%`.
* **Grand Total Row:** Placed at the bottom with `=SUM(H2:H{last_row})` and `=SUM(I2:I{last_row})`.

---

## 4. Visual Styling & Formatting Specifications

* **Header Fill:** Slate Navy (`#1E293B`) with white bold text (`#FFFFFF`), centered alignment.
* **Number Formats:**
  * Currency (IDR): `_("Rp"* #,##0_);_("Rp"* (#,##0);_("Rp"* "-"_);_(@_)`
  * Percentage: `0.00%`
  * Quantities: `#,##0`
* **Borders:** Thin slate borders (`#CBD5E1`) for data cells; accounting double bottom border for Grand Total rows.
* **Worksheet Views:** Explicitly enable gridlines (`ws.views.sheetView[0].showGridLines = True`).
* **Auto-Column Widths:** Dynamically calculate max character length + 4 padding to prevent `###` truncated cells.

---

## 5. Reference Skill
- Detailed implementation patterns and generator scripts are located in [../../.agents/skills/excel-styling-formatter/SKILL.md](../../.agents/skills/excel-styling-formatter/SKILL.md).