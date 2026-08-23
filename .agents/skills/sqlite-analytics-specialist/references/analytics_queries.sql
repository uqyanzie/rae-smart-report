-- =========================================================================
-- SQL Analytics Query Catalog (ELT On-Demand Reporting)
-- =========================================================================

-- Query A: Variant-Level Performance & Contribution % (Table 1)
-- Parameter :is_cross_bundling: 0 for Sheet 'Produk S'/'Produk T', 1 for Sheet 'Produk 2 S'/'Produk 2 T'
WITH product_totals AS (
    SELECT 
        product_group,
        SUM(revenue) AS total_product_revenue
    FROM transaction_items
    WHERE import_batch_id = :batch_id
      AND is_cross_bundling = :is_cross_bundling
    GROUP BY product_group
)
SELECT 
    t.product_group,
    t.clean_variant,
    t.is_bundling,
    t.is_cross_bundling,
    SUM(t.qty_sold) AS total_qty,
    SUM(t.revenue) AS total_revenue,
    CASE 
        WHEN pt.total_product_revenue > 0 THEN 
            ROUND((CAST(SUM(t.revenue) AS FLOAT) / pt.total_product_revenue) * 100.0, 2)
        ELSE 0.0 
    END AS contribution_pct
FROM transaction_items t
JOIN product_totals pt ON t.product_group = pt.product_group
WHERE t.import_batch_id = :batch_id
  AND t.is_cross_bundling = :is_cross_bundling
GROUP BY t.product_group, t.clean_variant, t.is_bundling, t.is_cross_bundling, pt.total_product_revenue
ORDER BY t.product_group ASC, t.is_bundling ASC, total_revenue DESC;


-- Query B: Master Product Group Summary (Table 2)
-- Summarizes grand performance across master product groups and calculates overall revenue share.
WITH grand_total AS (
    SELECT COALESCE(SUM(revenue), 0.0) AS grand_revenue 
    FROM transaction_items 
    WHERE import_batch_id = :batch_id
      AND is_cross_bundling = :is_cross_bundling
)
SELECT 
    product_group,
    SUM(qty_sold) AS total_qty,
    SUM(revenue) AS total_revenue,
    CASE 
        WHEN (SELECT grand_revenue FROM grand_total) > 0 THEN 
            ROUND((CAST(SUM(revenue) AS FLOAT) / (SELECT grand_revenue FROM grand_total)) * 100.0, 2)
        ELSE 0.0 
    END AS contribution_pct
FROM transaction_items
WHERE import_batch_id = :batch_id
  AND is_cross_bundling = :is_cross_bundling
GROUP BY product_group
ORDER BY total_revenue DESC;


-- Query C: Multi-Batch / Date-Range Multi-Platform Aggregation
WITH grand_total AS (
    SELECT COALESCE(SUM(revenue), 0.0) AS grand_revenue 
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
    SUM(qty_sold) AS total_qty,
    SUM(revenue) AS total_revenue,
    CASE 
        WHEN (SELECT grand_revenue FROM grand_total) > 0 THEN 
            ROUND((CAST(SUM(revenue) AS FLOAT) / (SELECT grand_revenue FROM grand_total)) * 100.0, 2)
        ELSE 0.0 
    END AS contribution_pct
FROM transaction_items
WHERE (:platform IS NULL OR platform = :platform)
  AND (:start_date IS NULL OR period_start >= :start_date)
  AND (:end_date IS NULL OR period_end <= :end_date)
  AND (:is_cross_bundling IS NULL OR is_cross_bundling = :is_cross_bundling)
GROUP BY platform, product_group, clean_variant
ORDER BY total_revenue DESC;


-- Query D: Batch History & Upload Overview
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
ORDER BY created_at DESC;
