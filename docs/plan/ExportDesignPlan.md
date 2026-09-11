# Context & Objective
Refactor the current "Export Excel" batch selection interface. The current design suffers from:
1. Checkboxes being used for radio-button behavior (selecting a 2nd batch replaces the 1st).
2. Unformatted ISO strings and raw batch IDs cluttering the UI.
3. Requiring redundant date selections across 4 platforms (Shopee, TikTok Shop, Tokopedia, Lazada) that usually share the same reporting window.

Replace it with a **Synchronized Period Selector** layout where platforms are grouped under a shared reporting window, with inline platform toggles and granular export settings.

---

## 1. Functional Requirements

### A. Period Selection (Single Choice)
- Present available reporting periods as interactive preset cards (e.g., "31 Aug – 06 Sep 2026", "24 Aug – 30 Aug 2026", "August 2026 (Monthly)").
- Selecting a period updates the selected batch for all enabled platforms to match that date range.
- Provide an escape hatch: a toggle or link to switch to "Custom / Individual Platform Selection" mode if a user needs mismatched date ranges across channels.

### B. Platform Batch List & Granular Settings
Replace the 4 disjointed platform boxes with a unified batch summary table or list:
- **Columns / Attributes per row:**
  1. **Platform Toggle/Checkbox:** Enable or disable inclusion of the platform in the exported workbook (Shopee, TikTok Shop, Tokopedia, Lazada).
  2. **Platform Identity:** Logo/badge + Platform name.
  3. **Batch Details:** Clean date format (human-readable, no raw ISO timestamps like `T00:00:00`) + subtle short batch hash (e.g., `#f45a94`).
  4. **Metrics:** Units count and Total GMV (IDR formatted, e.g., `Rp 402.967.705`).
  5. **Granular Export Option (Per-Platform):** 
     - Checkbox: `Expand case colours (Produk 2)`.
     - Only show or enable this option for platforms that support cross-bundling logic (e.g., Shopee & TikTok Shop).
     - When checked, only that specific platform's sheet will expand case colours into individual rows.

### C. Sticky Footer Summary & Action
- Display total aggregate summary:
  - Total Platforms selected (e.g., `4 platforms selected`).
  - Combined Units (sum of all enabled platform batches).
  - Combined Revenue/GMV (sum of all enabled platform batches).
- Primary CTA: `Export Workbook (.xlsx)` (disabled if 0 platforms are selected).

---

## 2. Data Contract & State Model

```typescript
export interface BatchRecord {
  id: string; // e.g. "SHOPEE-2026-08-31-2026-09-06-f45a94"
  shortHash: string; // e.g. "f45a94"
  platform: 'SHOPEE' | 'TIKTOK_SHOP' | 'TOKOPEDIA' | 'LAZADA';
  startDate: string; // "2026-08-31"
  endDate: string; // "2026-09-06"
  periodLabel: string; // "31 Aug – 06 Sep 2026"
  units: number;
  revenue: number;
  supportsCaseColours: boolean; // true for Shopee & TikTok Shop
}

export interface PlatformExportConfig {
  platform: 'SHOPEE' | 'TIKTOK_SHOP' | 'TOKOPEDIA' | 'LAZADA';
  enabled: boolean;
  selectedBatchId: string | null;
  includeCaseColours: boolean;
}

export interface ExportPayload {
  periodKey: string;
  platforms: Array<{
    platform: string;
    batchId: string;
    includeCaseColours: boolean;
  }>;
}
