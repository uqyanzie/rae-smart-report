export type ParentRowIgnoreCondition = "EQUALS_DASH" | "IS_EMPTY" | "CONTAINS_TOTAL";

export interface IngestionResultDTO {
  fileId: string;
  fileName: string;
  fileSizeBytes: number;
  detectedDelimiter: string;
  availableSheets: string[];
  activeSheet: string;
  totalRows: number;
  rawHeaders: string[];
  sampleRows: Record<string, any>[];
}

export interface ColumnMappingDTO {
  productGroup: string;
  rawVariant: string;
  qtySold: string;
  revenue: string;
  sku?: string | null;
  caseColor?: string | null;
}

export interface ParentRowRuleDTO {
  targetColumn: string;
  ignoreCondition: ParentRowIgnoreCondition;
}

export interface CleaningRuleDTO {
  pattern: string;
  replacement: string;
  description: string;
}

export interface ProfilerResponseDTO {
  isCached: boolean;
  platform: string;
  confidence: number;
  columnMapping: ColumnMappingDTO;
  parentRowRule?: ParentRowRuleDTO | null;
  suggestedCleaningRules: CleaningRuleDTO[];
}

export interface TransformAndSaveRequestDTO {
  fileId: string;
  activeSheet?: string;
  platform: string;
  periodStart?: string;
  periodEnd?: string;
  columnMapping: ColumnMappingDTO;
  parentRowRule?: ParentRowRuleDTO | null;
  cleaningRules: CleaningRuleDTO[];
  saveAsTemplate?: boolean; // defaults to true on the backend
}

export interface VariantPerformanceDTO {
  productGroup: string;
  cleanVariant: string;
  isBundling: boolean;
  isCrossBundling: boolean;
  totalQty: number;
  totalRevenue: number;
  contributionRatio: number; // 0-1 unit share
  caseColor?: string | null; // SQL aggregates by shade; retained for parity, always null
}

export interface ProductSummaryDTO {
  productGroup: string;
  totalQty: number;
  totalRevenue: number;
  contributionRatio: number; // 0-1 unit share
}

export interface AggregateRowDTO {
  platform: string;
  productGroup: string;
  cleanVariant: string;
  totalQty: number;
  totalRevenue: number;
  contributionRatio: number; // 0-1 unit share
}

export interface BatchMetaDTO {
  importBatchId: string;
  platform: string;
  periodStart?: string;
  periodEnd?: string;
  createdAt?: string;
}

export interface BatchSummaryDTO extends BatchMetaDTO {
  // Storage-level batch summary (raw transaction sums). These are whole-batch
  // figures INCLUDING cross-bundling rows; they are NOT the workbook
  // (grid-intersected) totals -- use the `reported*` fields on the transform
  // response for those.
  totalProducts: number;
  grandTotalQty: number;
  grandTotalRevenue: number;
}

export interface TransformResponseDTO extends BatchMetaDTO {
  // Report-boundary (grid-intersected) workbook totals, distinct from the
  // storage-level `grandTotal*` figures on BatchSummaryDTO.
  reportedProductCount: number;
  reportedTotalQty: number;
  reportedTotalRevenue: number;
  insertedCount: number;
  skippedCount: number;
  skippedQty: number;
  skippedRevenue: number;
  warningCount: number;
}
