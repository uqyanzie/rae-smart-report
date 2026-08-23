---
name: llm-structured-profiler
description: Manages LLM structured output schema mapping as an unknown-format fallback, header signature SHA-256 caching, platform heuristics, and confidence validation while enforcing zero-LLM math boundaries.
---

# LLM Structured Profiler & Mapping Specialist

This skill defines how to profile and map unknown e-commerce spreadsheet schemas into the canonical schema deterministically with zero math hallucinations.

---

## 1. Core Directives & Boundaries

1. **Deterministic Adapters Precede LLM:** Recognized platforms (Shopee, TikTok Shop) use hardcoded deterministic adapters. The LLM profiler is invoked **only** for unknown export schemas.
2. **Zero Math Responsibility:** The LLM only identifies column roles and suggests regex cleaning patterns. It is strictly forbidden from computing sums, averages, or shares.
3. **Template Cache First (SHA-256):** Compute a SHA-256 hash of the normalized header array. If a matching template exists in `mapping_templates`, bypass the LLM entirely.
4. **Mandatory Human Review on Fallback:** When LLM profiling generates a new mapping for an unknown file, route the result to human confirmation before committing to `mapping_templates`.
5. **Optional Parent Row Rules:** Platforms vary in structure; Shopee has parent summary rows whereas TikTok Shop is atomic per SKU. `parentRowRule` must remain optional (`null` when no parent rows exist).

---

## 2. Invariants & Decision Checklist

- [ ] Is `header_signature_hash` checked against the database before calling the LLM API?
- [ ] Are all 4 required canonical fields (`productGroup`, `rawVariant`, `qtySold`, `revenue`) mapped?
- [ ] Is `parentRowRule` set only if the marketplace format actually contains summary/parent rows?
- [ ] Are regex cleaning rules validated for non-destructive replacement?

---

## 3. Modular Code References

- **Pydantic Schemas & SHA-256 Hashing:** [references/profiler_schemas.py](references/profiler_schemas.py)
- **System Prompt & Payload Contracts:** [references/system_prompt.md](references/system_prompt.md)
