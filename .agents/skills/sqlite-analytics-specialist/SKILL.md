---
name: sqlite-analytics-specialist
description: Maintains atomic SQLite schema, writes optimized analytical CTE SQL queries for variant and master product contributions, manages indexing, and ensures high-performance local data operations.
---

# SQLite Analytics Specialist

This skill provides operational rules, schema designs, indexes, transaction management directives, and SQL analytical CTE queries for local persistence and reporting.

---

## 1. Core Directives & Architectural Mandates

1. **Zero Static Aggregation Tables:** Aggregated metrics must **never** be stored in static tables. All reports, UI data grids, and Excel exports must be derived on-demand via SQL `GROUP BY`, `SUM`, and Common Table Expressions (CTEs) against `transaction_items`.
2. **Deterministic Mathematics:** All percentage contributions, totals, and metrics are calculated in SQL with 100% precision.
3. **Optimized Engine PRAGMAs:** Enforce Write-Ahead Logging (WAL), memory temp stores, and foreign keys on all database connections.

---

## 2. Invariants & Decision Checklist

- [ ] Is Write-Ahead Logging (WAL) enabled on engine initialization?
- [ ] Are composite indexes created on `(import_batch_id, product_group)` and `(platform, period_start, period_end)`?
- [ ] Are all analytical queries parameterized using `:batch_id` or `:start_date`?
- [ ] Does `contribution_pct` guard against division-by-zero (`CASE WHEN total > 0`)?

---

## 3. Modular Code References

- **SQLAlchemy Models & Engine PRAGMAs:** [references/schema_models.py](references/schema_models.py)
- **Analytical CTE Query Catalog:** [references/analytics_queries.sql](references/analytics_queries.sql)
