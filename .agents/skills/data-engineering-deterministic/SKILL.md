---
name: data-engineering-deterministic
description: Enforces deterministic tabular data ingestion, parent-row double-counting elimination, locale-aware currency parsing, regex variant normalization, bundling detection, and zero-LLM math rules.
---

# Data Engineering Deterministic Specialist

This skill provides operational rules, invariants, and pipeline directives for ingesting e-commerce sales reports with 100% determinism.

---

## 1. Core Directives & Boundaries

1. **Zero-LLM Math:** The LLM is **NEVER** permitted to perform summations, aggregations, percentages, or financial metrics. All arithmetic operations are computed via Python/Polars or SQLite SQL.
2. **Deterministic Parent-Row Elimination:** Every marketplace export contains summary/parent rows (e.g. `Nama Variasi: "-"`). Drop these rows immediately before loading to prevent double-counting.
3. **Locale-Aware Number Sanitization:** Normalize Indonesian Rupiah formats (`Rp 261.911.314`, `261.911.314,00`), standard European comma decimals, and US/International currencies into clean `float` and `int`.
4. **Idempotent Cleaning Pipelines:** Apply regex rules to strip marketing suffixes (`Random Keychain`, `Free Gift`) and flag product bundling (`+`, `&`, `Bundling`).

---

## 2. Invariants & Decision Checklist

- [ ] Has delimiter been auto-detected across `,`, `;`, and `\t`?
- [ ] Is `rawVariant` checked against `"-"`, `""`, and `parentRowRule` before row insertion?
- [ ] Are currency strings converted to numeric primitives before database storage?
- [ ] Is `is_bundling` properly set to `True` when multi-item keywords are detected?

---

## 3. Modular Code References

- **Currency & Delimiter Sanitizer:** [references/currency_sanitizer.py](references/currency_sanitizer.py)
- **Row Filtering & Transformation Pipeline:** [references/row_filter_pipeline.py](references/row_filter_pipeline.py)
