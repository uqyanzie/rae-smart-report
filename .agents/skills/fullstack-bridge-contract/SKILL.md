---
name: fullstack-bridge-contract
description: Synchronizes FastAPI Pydantic models with React TypeScript interfaces, establishes REST API endpoints, streaming downloads, and unified error handling conventions.
---

# Fullstack Bridge Contract Specialist

This skill establishes the strict end-to-end interface contracts, DTO synchronization rules, API route definitions, and data exchange conventions between the Python FastAPI backend and the React TypeScript frontend.

---

## 1. Core Directives

1. **Exact DTO Parity:** Every Python Pydantic schema in the backend must have an identical TypeScript interface in the frontend.
2. **CamelCase Serialization via `CamelModel`:** Python backend models inherit from `CamelModel` using Pydantic v2 `ConfigDict(alias_generator=to_camel, populate_by_name=True)`. This ensures backend pythonic `snake_case` automatically serializes to frontend `camelCase` over HTTP.
3. **Unified Error Envelope:** All HTTP 4xx/5xx responses must return a standardized JSON error structure.
4. **Binary Stream Handling:** Excel export endpoints return `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` with appropriate `Content-Disposition` headers.
5. **Standardized Ratio Scale:** `contributionRatio` is exchanged as a 0–1 floating point ratio across all DTOs and database boundaries.

---

## 2. Invariants & Decision Checklist

- [ ] Does every Pydantic DTO inherit from `CamelModel` with `populate_by_name=True`?
- [ ] Does every newly added backend field exist in `frontend_dtos.ts` in exact matching type and casing?
- [ ] Are date fields serialized as ISO strings (`YYYY-MM-DD`) across boundaries?
- [ ] Do file export endpoints set `Content-Disposition: attachment; filename="report.xlsx"`?
- [ ] Are error responses wrapped in `{ status: "error", code: "...", message: "..." }`?

---

## 3. Modular Code References

- **FastAPI Pydantic DTOs:** [references/backend_dtos.py](references/backend_dtos.py)
- **React TypeScript Interfaces:** [references/frontend_dtos.ts](references/frontend_dtos.ts)
- **REST API Endpoint Catalog:** [references/api_endpoints.md](references/api_endpoints.md)
