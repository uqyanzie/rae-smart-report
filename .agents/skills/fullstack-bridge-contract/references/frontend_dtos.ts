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
}

export interface ParentRowRuleDTO {
  targetColumn: string;
  ignoreCondition: "EQUALS_DASH" | "IS_EMPTY" | "CONTAINS_TOTAL";
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
  parentRowRule: ParentRowRuleDTO;
  suggestedCleaningRules: CleaningRuleDTO[];
}

export interface TransformAndSaveRequestDTO {
  fileId: string;
  activeSheet?: string;
  platform: string;
  periodStart?: string;
  periodEnd?: string;
  columnMapping: ColumnMappingDTO;
  parentRowRule: ParentRowRuleDTO;
  cleaningRules: CleaningRuleDTO[];
  saveAsTemplate: boolean;
}

export interface VariantPerformanceDTO {
  productGroup: string;
  cleanVariant: string;
  isBundling: boolean;
  isCrossBundling: boolean;
  totalQty: number;
  totalRevenue: number;
  contributionPct: number;
}

export interface ProductSummaryDTO {
  productGroup: string;
  totalQty: number;
  totalRevenue: number;
  contributionPct: number;
}

export interface BatchSummaryDTO {
  importBatchId: string;
  platform: string;
  periodStart?: string;
  periodEnd?: string;
  totalProducts: number;
  grandTotalQty: number;
  grandTotalRevenue: number;
  createdAt: string;
}
