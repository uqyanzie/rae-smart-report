import { z } from 'zod'

const isoDatePattern = /^\d{4}-\d{2}-\d{2}$/

export const transformRequestSchema = z
  .object({
    fileId: z.string().min(1, 'File is required.'),
    activeSheet: z.string().min(1, 'Sheet is required.'),
    platform: z.enum(['SHOPEE', 'TIKTOK_SHOP', 'TOKOPEDIA'], {
      message: 'Select a platform (SHOPEE, TIKTOK_SHOP or TOKOPEDIA).',
    }),
    periodStart: z
      .string()
      .min(1, 'Period start is required.')
      .regex(isoDatePattern, 'Period start must be a valid date (YYYY-MM-DD).'),
    periodEnd: z
      .string()
      .min(1, 'Period end is required.')
      .regex(isoDatePattern, 'Period end must be a valid date (YYYY-MM-DD).'),
    columnMapping: z.object({
      productGroup: z.string().min(1, 'Product group is required.'),
      rawVariant: z.string().min(1, 'Raw variant is required.'),
      qtySold: z.string().min(1, 'Qty sold is required.'),
      revenue: z.string().min(1, 'Revenue is required.'),
      sku: z.string().nullable().optional(),
      caseColor: z.string().nullable().optional(),
    }),
    parentRowRule: z
      .object({
        targetColumn: z.string().min(1, 'Parent-row rule needs a target column.'),
        ignoreCondition: z.enum(['EQUALS_DASH', 'IS_EMPTY', 'CONTAINS_TOTAL']),
      })
      .nullable()
      .optional(),
    cleaningRules: z
      .array(
        z.object({
          pattern: z.string().min(1, 'Cleaning rule pattern cannot be empty.'),
          replacement: z.string().optional(),
          description: z.string().optional(),
        }),
      )
      .optional(),
    saveAsTemplate: z.boolean().optional(),
  })
  .superRefine((data, ctx) => {
    if (data.periodStart && data.periodEnd && data.periodStart > data.periodEnd) {
      ctx.addIssue({
        code: 'custom',
        path: ['periodStart'],
        message: 'Period start must be on or before period end.',
      })
    }
  })
