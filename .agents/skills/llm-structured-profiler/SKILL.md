---
name: llm-structured-profiler
description: Manages LLM structured output schema mapping, header signature SHA-256 caching, platform heuristics, and confidence validation while enforcing zero-LLM math boundaries.
---

# LLM Structured Profiler & Mapping Specialist

This skill defines how to map unknown e-commerce spreadsheet schemas into the canonical schema deterministically with zero math hallucinations.

---

## 1. Core Directives & Boundaries

1. **Zero Math Responsibility:** The LLM only identifies column roles and suggests regex cleaning patterns. It is strictly forbidden from computing sums, averages, or shares.
2. **Template Cache First (SHA-256):** Compute a SHA-256 hash of the normalized header array. If a matching template exists in `mapping_templates`, bypass the LLM entirely.
3. **Strict Pydantic Validation:** Always validate LLM responses against structured output models. Trigger retry or UI review on validation errors.
4. **Confidence Thresholding:** If model confidence is below `0.85` or required columns are ambiguous, trigger the Mapping Review Modal in the UI.

---

## 2. Invariants & Decision Checklist

- [ ] Is `header_signature_hash` checked against the database before calling the LLM API?
- [ ] Are all 4 required canonical fields (`productGroup`, `rawVariant`, `qtySold`, `revenue`) mapped?
- [ ] Is `parentRowRule` identified for the detected marketplace format?
- [ ] Are regex cleaning rules validated for non-destructive replacement?

---

## 3. Modular Code References

- **Pydantic Schemas & SHA-256 Hashing:** [references/profiler_schemas.py](references/profiler_schemas.py)
- **System Prompt & Payload Contracts:** [references/system_prompt.md](references/system_prompt.md)
