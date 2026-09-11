---
name: sqlite-analytics-specialist
description: Maintains atomic SQLite schema, writes optimized analytical CTE SQL queries for variant and master product contributions, manages indexing, and ensures high-performance local data operations.
---

# SQLite Analytics Specialist

This skill provides operational rules, schema designs, indexes, transaction management directives, and SQL analytical CTE queries for local persistence and reporting.

---

## 1. Core Directives & Architectural Mandates

1. **Zero Static Aggregation Tables:** Aggregated metrics must **never** be stored in static tables. All reports, UI data grids, and Excel exports must be derived on-demand via SQL `GROUP BY`, `SUM`, and Common Table Expressions (CTEs) against `transaction_items`.
2. **Deterministic Precision:** All percentage contributions, totals, and metrics are calculated in SQL with 100% precision. `revenue` is stored as an integer (exact IDR) to eliminate floating-point arithmetic drift.
3. **Unit Share Contribution Scale:** `contribution_ratio` computes the 0–1 quantity unit share (`SUM(qty_sold) / total_qty`) rendered via `0.00%` cell formatting in Excel.
4. **Case Colour Is Not A Reporting Dimension (by default):** `case_color` is stored as SKU-level provenance but must **never** appear in a reporting `GROUP BY` in the default report. Tinted Jelly Balm totals are aggregated by shade across all case colours — verified: golden `Bunny Pink` = 15 units spanning four different case colours, reported as a single row. Grouping by `case_color` would split one expected row into four. Variant-level analytics group by `(product_group, clean_variant)` only. Single exception: the opt-in Produk 2 export view (`populate_grid(..., include_case_colors=True)`) aggregates reported cross rows at `(product_group, clean_variant, case_color)` grain to feed the per-case-colour TJB rows; it is OFF by default and does not touch Queries A–G.
5. **Optimized SQLite PRAGMAs:** Enforce Write-Ahead Logging (WAL), memory temp stores, and foreign keys on SQLite database connections.

---

## 2. Invariants & Decision Checklist

- [ ] Is Write-Ahead Logging (WAL) enabled on SQLite initialization?
- [ ] Are composite indexes created on `(import_batch_id, is_cross_bundling, product_group)` and `(platform, period_start, period_end)`?
- [ ] Do variant-level queries group by `(product_group, clean_variant)` **without** `case_color` (default report)?
- [ ] Is `case_color` absent from every reporting `GROUP BY` and `SELECT` used to build default report rows (opt-in per-case export view excepted)?
- [ ] Are all analytical queries parameterized using `:batch_id` or `:start_date`?
- [ ] Does `contribution_ratio` guard against division-by-zero (`CASE WHEN total_product_qty > 0`)?
- [ ] Is the persisted column named `is_cross_bundling` (not `is_cross_family`) everywhere, including DTOs?
- [ ] Does any `GROUP BY` query `ORDER BY` an aggregate rather than a bare non-grouped column?
- [ ] Are batch deletion and template lookup queries parameterized?

---

## 3. Modular Code References

- **SQLAlchemy Models & Engine PRAGMAs:** [references/schema_models.py](references/schema_models.py)
- **Analytical CTE Query Catalog:** [references/analytics_queries.sql](references/analytics_queries.sql)
