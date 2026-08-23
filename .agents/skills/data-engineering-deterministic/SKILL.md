---
name: data-engineering-deterministic
description: Enforces deterministic tabular data ingestion, parent-row double-counting elimination, locale-aware currency parsing (id-ID default), regex variant normalization, bundling detection, and zero-LLM math rules.
---

# Data Engineering Deterministic Specialist

This skill provides operational rules, invariants, and pipeline directives for ingesting e-commerce sales reports with 100% determinism.

---

## 1. Core Directives & Boundaries

1. **Zero-LLM Math:** The LLM is **NEVER** permitted to perform summations, aggregations, percentages, or financial metrics. All arithmetic operations are computed via deterministic Python or SQLite SQL queries.
2. **Deterministic Parent-Row Elimination:** Marketplace exports (such as Shopee) contain summary/parent rows (e.g. `Nama Variasi: "-"`). Prune these rows before loading into the database to prevent double-counting.
3. **Locale-Aware Number Sanitization:** Default to Indonesian Rupiah convention (id-ID: `.` is thousands separator, `,` is decimal separator). Values such as `Rp 50.000`, `100.000`, and `(1.000)` must parse with 100% precision. Never guess locale per-value.
4. **Pinned Column Adapters:** Use deterministic platform adapters with exact verified column names (`"Penjualan (Pesanan Siap Dikirim) (IDR)"` and `"Produk (Pesanan Siap Dikirim)"` for Shopee; `"GMV"` and `"Produk terjual"` for TikTok Shop). Fail loudly if required columns are absent.
5. **Idempotent Cleaning Pipelines:** Apply normalization rules to strip marketing suffixes (`Random Keychain`, `Tanpa Keychain`) and detect product bundling (`+`, `&`, `Bundling`).

---

## 2. Invariants & Decision Checklist

- [ ] Has delimiter been auto-detected across `,`, `;`, and `\t`?
- [ ] Is `id-ID` numeric parsing applied (`.` = thousands, `,` = decimal), correctly parsing `Rp 50.000` to `50000.0`?
- [ ] Are required column headers validated to exist before row iteration?
- [ ] Is `rawVariant` checked against `"-"`, `""`, and `parentRowRule` before row insertion?
- [ ] Are currency strings converted to numeric primitives before database storage?
- [ ] Is `is_bundling` and `is_cross_bundling` properly identified?

---

## 3. Modular Code References

- **Currency & Delimiter Sanitizer:** [references/currency_sanitizer.py](references/currency_sanitizer.py)
- **Row Filtering & Transformation Pipeline:** [references/row_filter_pipeline.py](references/row_filter_pipeline.py)
