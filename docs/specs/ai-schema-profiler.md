# Module Specification: AI Schema Profiler & Mapping Engine

## 1. Overview
The AI Schema Profiler examines sampled raw headers and records from ingested files to map disparate e-commerce export formats (e.g., TikTok Shop, Shopee, Tokopedia, Lazada) into a canonical internal schema. It operates with strict deterministic validation to prevent runtime hallucination.

## 2. Canonical Target Schema
All ingested data must resolve to these canonical attributes:
- `productGroup` (string, required): Master product name / group (e.g., "Glow Up Tint").
- `rawVariant` (string, required): Original variant string as exported by the marketplace.
- `sku` (string, optional): Stock Keeping Unit identifier.
- `qtySold` (number, required): Units sold within the period.
- `revenue` (number, required): Total gross/net sales value.
- `skipRowIndicator` (boolean condition): Rule to identify and prune aggregated parent rows or summary rows.

## 3. AI Agent Directives & Prompting Rules

### 3.1 LLM Boundary & Guardrails
- **Zero Math Responsibility:** The LLM is NEVER used to perform calculations, summations, or percentage metrics.
- **Strict Structured Output:** All LLM responses must strictly adhere to JSON schema validation (e.g., via OpenAI Structured Outputs or Zod schemas).

### 3.2 System Prompt Contract
```text
You are an expert E-Commerce Data Engineer.
Given a list of column headers and sample data rows from an e-commerce export file, identify the marketplace platform, map the source columns to the canonical schema, and output cleaning strategies for variant names.

Output JSON format:
{
  "platform": "TIKTOK_SHOP" | "SHOPEE" | "TOKOPEDIA" | "LAZADA" | "UNKNOWN",
  "confidence": number,
  "columnMapping": {
    "productGroup": string,
    "rawVariant": string,
    "sku": string | null,
    "qtySold": string,
    "revenue": string
  },
  "parentRowRule": {
    "targetColumn": string,
    "ignoreCondition": "EQUALS_DASH" | "IS_EMPTY" | "CONTAINS_TOTAL"
  },
  "suggestedCleaningRules": [
    {
      "pattern": string,
      "replacement": string,
      "description": string
    }
  ]
}