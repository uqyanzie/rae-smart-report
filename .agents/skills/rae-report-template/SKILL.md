---
name: rae-report-template
description: Authoritative domain authority for master product families, ordered shades, alias resolution, combinatorial grid generation (C(n,2) intra-family and cross-family Cartesian), same-shade 2-pack fold-back rules, and the 16-sheet workbook taxonomy.
---

# RAE Report Template Specialist

This skill provides domain logic, product catalog models, fixed-grid layout specifications, and fold-back business rules for generating executive sales reports.

---

## 1. Core Directives & Domain Rules

1. **Declarative Grid vs GROUP BY:** The report's row order and vocabulary come from the product catalog, not from `ORDER BY revenue DESC`. Generate the full three-dimensional grid, then left-join SQL aggregates onto it. The grid's purpose is **canonical ordering and label vocabulary** — it guarantees a variant lands in the right position when it does sell.
2. **Sparse Variant Rows, Complete Group Rows:** After the left-join, the exporter emits only variant rows with non-zero quantity, but **every** group in `PRODUK_GROUP_ORDER` regardless of activity. Fully-zero groups are common, not exceptional (in the reference period, 7 of 10 cross-family groups on `Produk 2 S` had no sales). Groups with no emitted variant rows must render a literal `0` rather than a `=SUM()` over an absent range.
3. **Canonical Catalog & Alias Dictionary:** Single source of truth for all 7 product families (`Glow Up Tint`, `Swipe To Glow`, `Power Frosted Velvet Matte`, `Tinted Jelly Balm`, `The Bloom Perfect Matte Lipstick`, `Over The Glaze`, `Lipcare`) and their observed misspellings/abbreviations (`Cheerfull` -> `Cheerful`, `Ov Hype` -> `Over Hype`, `BunPink` -> `Bunny Pink`).
4. **Tinted Jelly Balm Case Colours Are SKU Metadata, Not A Report Axis:** TJB ships in coloured cases (`Fizzy Pop`, `Sweetie Pop`, `Cherry Pop`, `Buttered Yellow`, `Matcha Strawberry`, and future additions). Extract the colour into `case_color` for traceability, but **aggregate report totals by shade across all colours**. Verified: the reference workbook reports `Bunny Pink` = 15 units spanning four distinct case colours as a single row, and its three `n x m x 3` cross-family case grids (324 rows) are entirely empty scaffolding that has never carried data. Never expand the grid by case colour and never place `case_color` in a reporting `GROUP BY`. Unknown or new colour names are safe to ignore — they cost nothing because the shade total already includes them.
5. **Same-Shade 2-Pack Fold-Back Rule:** Intra-family bundles with identical shades (e.g. `Dynamic, 05. Dynamic`) fold back into the corresponding single shade: revenue is added as-is ($\times 1$), quantity is added doubled ($\times 2$). Aggregate duplicate rows; raise an explicit error if $N > 2$.
6. **Three Distinct Orderings Per Family:** Each family carries up to three sequences, and they are **not** interchangeable:
   - `singles_order` — single-shade rows in the left table (largely alphabetical).
   - `display_order` — intra-family bundle pair generation. Follows **marketplace shade ordinals**, so Glow Up Tint places `Strong` (09) *before* `Happy` (10) despite S > H alphabetically.
   - `cross_order` — cross-family (`Produk 2`) grids; differs again from both.

   Pair generation is a strict upper triangle over `display_order`, i.e. `combinations(family.order_for_pairs(), 2)`. Passing the alphabetical `family.shades` tuple instead silently misplaces rows (it misorders 37 of 55 Glow Up Tint labels). All sequences live in `references/catalog_spec.py`; use the `order_for_*()` accessors rather than reading `shades` directly.
7. **Exact Label Formatting:**
   - Intra-family bundles join with ` + ` (`Active + Brave`).
   - Cross-family bundles join with `, ` (`Active, Over Cute`).
   - Cross-family with case colour uses ` + ` between shades then `, ` before the colour (`Over Cute + Bunny Pink, Fizzy Pop`).
   - `Power Frosted Velvet Matte` intra-family bundles use **short** shade names via `Family.bundle_label()` (`Kind + Honest`); cross-family labels keep full names (`Kind Power, Peony`).
   - **Trailing whitespace:** the reference workbook contains 57 manually-entered trailing spaces. Do not reproduce them; normalise with `.rstrip()` on **both** sides of every comparison and join.
8. **Hand-Ordered Exception:** `Bundling Over The Glaze` does not follow the upper-triangle rule, and one label drops its prefix (`Over Cute + Lovie`). Its 15 intra-bundle labels are supplied verbatim as `OTG_INTRA_BUNDLE_LABELS`.
9. **16-Sheet Workbook Taxonomy:**
   - Platform Suffixes: `S` (Shopee), `T` (TikTok Shop), `TP` (Tokopedia), `L` (Lazada).
   - Sheet Types: `Produk` (singles + intra bundles), `Produk 2` (cross bundles), `Tinjauan Data` (daily metrics), `Promosi`, `BC`, `Ekspor`.
   - Phase 1 Target: `Produk S`, `Produk T`, `Produk 2 S`, `Produk 2 T`.
10. **Reference-Workbook Defects — Do Not Replicate:** The source workbook is hand-maintained and contains known errors. Emit the corrected form:
   - `Produk 2 S` group 9 sums 72 rows (`C374:C445`) instead of 36, double-counting Power Frosted combinations.
   - `Cheerfull` (double-L) in all 24 cross-family rows, while `Produk S`/`Produk T` correctly use `Cheerful`.
   - `Classy power` (lowercase p) in 6 rows, against 76 correct `Classy Power`.
   - `#DIV/0!` in zero-revenue groups; emit `0` or blank instead.
   Normalising these means generated cross-family grids differ from the source by exactly 30 labels. That divergence is **intended**.

---

## 2. Invariants & Decision Checklist

- [ ] Are report grids populated from the declarative catalog rather than derived from `ORDER BY revenue DESC`?
- [ ] Does the **variant** table emit only non-zero rows, while the **group** summary retains every catalog group?
- [ ] Do zero-activity groups render a literal `0` instead of a `=SUM()` over an absent range?
- [ ] Is pair generation iterating `display_order` (**not** the alphabetical `shades` tuple)?
- [ ] Are cross-family labels joined with `, ` rather than ` + `?
- [ ] Are labels compared/joined after `.rstrip()` on **both** sides?
- [ ] Is the same-shade fold-back applied with $\times 2$ quantity and $\times 1$ revenue?
- [ ] Is an error raised if an intra-family bundle has multiplicity $N > 2$?
- [ ] Are unmapped variant tokens flagged and surfaced for review rather than dropped?
- [ ] Does the regression test compare generated labels against golden as **ordered lists**, not sets? (Order is the failure mode; a set comparison hides it.)

---

## 3. Modular Code References

- **Canonical Catalog, Orderings & Shade Resolver:** [references/catalog_spec.py](references/catalog_spec.py)
- **Combinatorial Grid & Fold-Back Engine:** [references/grid_engine.py](references/grid_engine.py)
