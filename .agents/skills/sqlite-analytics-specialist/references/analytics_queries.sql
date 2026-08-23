-- =========================================================================
-- SQL Analytics Query Catalog (ELT On-Demand Reporting)
-- Standardized Metric: contribution_ratio is a 0-1 unit share (quantity based)
-- =========================================================================

-- Query A: Variant-Level Performance & Contribution Ratio (Table 1)
-- Parameter :is_cross_bundling: 0 for Sheet 'Produk S'/'Produk T', 1 for Sheet 'Produk 2 S'/'Produk 2 T'
-- NOTE: case_color participates in the grouping key. Tinted Jelly Balm cross
-- grids expand to n x m x 3 rows (one per case colour), so omitting it here
-- would collapse three distinct report rows into one and triple their totals.
-- It is NULL for every other family, which groups harmlessly.
WITH product_totals AS (
    SELECT 
        product_group,
        SUM(qty_sold) AS total_product_qty
    FROM transaction_items
    WHERE import_batch_id = :batch_id
      AND is_cross_bundling = :is_cross_bundling
    GROUP BY product_group
)
SELECT 
    t.product_group,
    t.clean_variant,
    t.case_color,
    t.is_bundling,
    t.is_cross_bundling,
    SUM(t.qty_sold) AS total_qty,
    SUM(t.revenue) AS total_revenue,
    CASE 
        WHEN pt.total_product_qty > 0 THEN 
            CAST(SUM(t.qty_sold) AS FLOAT) / pt.total_product_qty
        ELSE 0.0 
    END AS contribution_ratio
FROM transaction_items t
JOIN product_totals pt ON t.product_group = pt.product_group
WHERE t.import_batch_id = :batch_id
  AND t.is_cross_bundling = :is_cross_bundling
GROUP BY t.product_group, t.clean_variant, t.case_color, t.is_bundling, t.is_cross_bundling, pt.total_product_qty
ORDER BY t.product_group ASC, t.is_bundling ASC, total_qty DESC;


-- Query B: Master Product Group Summary (Table 2)
-- Summarizes grand performance across master product groups and calculates overall quantity share.
-- case_color is deliberately NOT in the grouping key here: this is a
-- group-level rollup, so all case colours belong in the same product-group row.
WITH grand_total AS (
    SELECT COALESCE(SUM(qty_sold), 0) AS grand_qty 
    FROM transaction_items 
    WHERE import_batch_id = :batch_id
      AND is_cross_bundling = :is_cross_bundling
)
SELECT 
    product_group,
    SUM(qty_sold) AS total_qty,
    SUM(revenue) AS total_revenue,
    CASE 
        WHEN (SELECT grand_qty FROM grand_total) > 0 THEN 
            CAST(SUM(qty_sold) AS FLOAT) / (SELECT grand_qty FROM grand_total)
        ELSE 0.0 
    END AS contribution_ratio
FROM transaction_items
WHERE import_batch_id = :batch_id
  AND is_cross_bundling = :is_cross_bundling
GROUP BY product_group
ORDER BY total_qty DESC;


-- Query C: Multi-Batch / Date-Range Multi-Platform Aggregation
-- case_color is part of the grouping key for the same reason as Query A.
WITH grand_total AS (
    SELECT COALESCE(SUM(qty_sold), 0) AS grand_qty 
    FROM transaction_items 
    WHERE (:platform IS NULL OR platform = :platform)
      AND (:start_date IS NULL OR period_start >= :start_date)
      AND (:end_date IS NULL OR period_end <= :end_date)
      AND (:is_cross_bundling IS NULL OR is_cross_bundling = :is_cross_bundling)
)
SELECT 
    platform,
    product_group,
    clean_variant,
    case_color,
    SUM(qty_sold) AS total_qty,
    SUM(revenue) AS total_revenue,
    CASE 
        WHEN (SELECT grand_qty FROM grand_total) > 0 THEN 
            CAST(SUM(qty_sold) AS FLOAT) / (SELECT grand_qty FROM grand_total)
        ELSE 0.0 
    END AS contribution_ratio
FROM transaction_items
WHERE (:platform IS NULL OR platform = :platform)
  AND (:start_date IS NULL OR period_start >= :start_date)
  AND (:end_date IS NULL OR period_end <= :end_date)
  AND (:is_cross_bundling IS NULL OR is_cross_bundling = :is_cross_bundling)
GROUP BY platform, product_group, clean_variant, case_color
ORDER BY total_qty DESC;


-- Query D: Batch History & Upload Overview
-- ORDER BY uses the aggregate, not a bare non-grouped column: ordering by an
-- ungrouped `created_at` yields an arbitrary row's value under SQLite.
SELECT 
    import_batch_id,
    platform,
    MIN(period_start) AS period_start,
    MAX(period_end) AS period_end,
    COUNT(DISTINCT product_group) AS total_products,
    SUM(qty_sold) AS grand_total_qty,
    SUM(revenue) AS grand_total_revenue,
    MIN(created_at) AS created_at
FROM transaction_items
GROUP BY import_batch_id, platform
ORDER BY MIN(created_at) DESC;


-- Query E: Delete Import Batch
DELETE FROM transaction_items
WHERE import_batch_id = :batch_id;


-- Query F: Lookup Mapping Template by Hash
SELECT platform_name, column_mapping_json, cleaning_rules_json, parent_row_rule_json
FROM mapping_templates
WHERE header_signature_hash = :signature_hash;
