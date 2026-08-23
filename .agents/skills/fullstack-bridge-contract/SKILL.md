---
name: fullstack-bridge-contract
description: Synchronizes FastAPI Pydantic models with React TypeScript interfaces, establishes REST API endpoints, streaming downloads, and unified error handling conventions.
---

# Fullstack Bridge Contract Specialist

This skill establishes the strict end-to-end interface contracts, DTO synchronization rules, API route definitions, and data exchange conventions between the Python FastAPI backend and the React TypeScript frontend.

---

## 1. Core Directives

1. **Exact DTO Parity:** Every Python Pydantic schema in the backend must have an identical TypeScript interface in the frontend.
2. **CamelCase Serialization:** HTTP payloads delivered over HTTP must follow camelCase JSON conventions for seamless TypeScript consumption.
3. **Unified Error Envelope:** All HTTP 4xx/5xx responses must return a standardized JSON error structure.
4. **Binary Stream Handling:** Excel export endpoints return `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` with appropriate `Content-Disposition` headers.

---

## 2. Invariants & Decision Checklist

- [ ] Does every newly added backend field exist in `frontend_dtos.ts`?
- [ ] Are date fields serialized as ISO strings (`YYYY-MM-DD`) across boundaries?
- [ ] Do file export endpoints set `Content-Disposition: attachment; filename="report.xlsx"`?
- [ ] Are error responses wrapped in `{ status: "error", code: "...", message: "..." }`?

---

## 3. Modular Code References

- **FastAPI Pydantic DTOs:** [references/backend_dtos.py](references/backend_dtos.py)
- **React TypeScript Interfaces:** [references/frontend_dtos.ts](references/frontend_dtos.ts)
- **REST API Endpoint Catalog:** [references/api_endpoints.md](references/api_endpoints.md)
