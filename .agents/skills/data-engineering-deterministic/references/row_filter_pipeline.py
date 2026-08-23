import re
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd

try:
    from .currency_sanitizer import sanitize_currency, sanitize_integer
except (ImportError, ValueError):
    from currency_sanitizer import sanitize_currency, sanitize_integer

BUNDLE_KEYWORDS = [
    "+", "&", "bundling", "bundle", "combo",
    "isi 2", "isi 3", "isi 4", "isi 5",
    "duo", "trio", "paket"
]

def is_parent_or_summary_row(raw_variant: Optional[str], ignore_condition: str = "EQUALS_DASH") -> bool:
    """
    Evaluates if a row represents an aggregate/parent row that must be excluded.
    Prevents double-counting in marketplace sales reports.
    """
    if raw_variant is None:
        return True
    
    cleaned = str(raw_variant).strip()
    if cleaned in ("None", "nan", "null"):
        return True
    
    if ignore_condition == "EQUALS_DASH":
        return cleaned in ("-", "--", "")
    elif ignore_condition == "IS_EMPTY":
        return not cleaned
    elif ignore_condition == "CONTAINS_TOTAL":
        return any(k in cleaned.lower() for k in ["total", "ringkasan", "semua"])
        
    return False

def parse_tiktok_concatenated_title(title_str: str) -> Tuple[str, str]:
    """
    Parses TikTok Shop concatenated title format:
    '<Master Product Title>: <Variant / Marketing Suffix>'
    e.g. 'Raecca Glow Up Tint...: Cheerful / Tanpa Keychain'
    Returns: (product_title: str, raw_variant: str)
    """
    if not title_str or pd.isna(title_str):
        return "Unknown Product", ""
        
    s = str(title_str).strip()
    if ":" in s:
        parts = s.split(":", 1)
        return parts[0].strip(), parts[1].strip()
    return s, ""

def extract_clean_variant_and_bundles(
    raw_variant: str,
    product_group: str = "",
    cleaning_rules: Optional[List[Dict[str, str]]] = None
) -> Tuple[str, bool, bool]:
    """
    Cleans raw variant string using deterministic regex rules and detects bundling types:
    - is_bundling: True if product is an intra-line bundle (e.g. 'Active + Brave')
    - is_cross_bundling: True if product is a cross-category combo (e.g. 'Bundling Glow Up Tint & Over The Glaze')
    Returns: (clean_variant: str, is_bundling: bool, is_cross_bundling: bool)
    """
    if not raw_variant:
        cleaned = "Default"
    else:
        cleaned = str(raw_variant).strip()
    
    # 1. Apply user-defined / LLM-suggested regex cleaning rules
    if cleaning_rules:
        for rule in cleaning_rules:
            pattern = rule.get("pattern", "")
            replacement = rule.get("replacement", "")
            if pattern:
                cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE).strip()
    
    # 2. Standard suffix stripping (e.g. '/ Tanpa Keychain', ', Random Keychain')
    cleaned = re.sub(r'[/,]\s*(random keychain|tanpa keychain|free gift|free pouch|gift).*$', '', cleaned, flags=re.IGNORECASE).strip()
    
    # 3. Detect bundling categories
    combined_text = f"{product_group} {cleaned}".lower()
    
    # Cross-product bundling (e.g. contains '&' joining two distinct product groups)
    is_cross_bundling = bool(re.search(r'bundling\s+.*?(&|\bx\b)\s+.*?', product_group, flags=re.IGNORECASE)) or (
        "&" in product_group and "bundling" in product_group.lower()
    )
    
    # Intra-product or standard bundling
    is_bundling = is_cross_bundling or any(kw in combined_text for kw in BUNDLE_KEYWORDS)
    
    # Clean leading/trailing artifacts
    cleaned = re.sub(r'^[,\-\s/]+|[,\-\s/]+$', '', cleaned).strip()
    if not cleaned:
        cleaned = "Default"
        
    return cleaned, is_bundling, is_cross_bundling

def process_shopee_dataframe(
    df: pd.DataFrame,
    import_batch_id: str,
    period_start = None,
    period_end = None
) -> List[Dict[str, Any]]:
    """
    Ingests and processes Shopee raw data from 'Produk dengan Performa Terbaik' sheet.
    Explicit Column Standards:
    - Revenue: 'Penjualan (Pesanan Siap Dikirim) (IDR)'
    - Quantity: 'Produk (Pesanan Siap Dikirim)'
    - Variant: 'Nama Variasi'
    - Product: 'Produk'
    """
    records = []
    
    col_prod = "Produk"
    col_var = "Nama Variasi"
    col_qty = "Produk (Pesanan Siap Dikirim)"
    col_rev = "Penjualan (Pesanan Siap Dikirim) (IDR)"
    col_sku = "SKU Induk"
    
    # Assert required columns are present to fail loudly on unexpected header shifts
    required_cols = [col_prod, col_var, col_qty, col_rev]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise KeyError(f"Shopee export missing required column(s): {missing}. Available: {list(df.columns)}")
    
    for _, row in df.iterrows():
        raw_variant = str(row.get(col_var, "")).strip() if pd.notna(row.get(col_var)) else ""
        
        # 1. Filter out parent/summary rows (where variant is '-')
        if is_parent_or_summary_row(raw_variant, "EQUALS_DASH"):
            continue
        
        product_title = str(row.get(col_prod, "")).strip()
        if not product_title or product_title.lower() in ("total", "nan", "none"):
            continue
        
        # Normalize brand prefix
        product_group = re.sub(r'^Raecca\s+', '', product_title, flags=re.IGNORECASE).strip()
            
        qty_sold = sanitize_integer(row.get(col_qty, 0))
        revenue = sanitize_currency(row.get(col_rev, 0.0))
        
        clean_variant, is_bundling, is_cross = extract_clean_variant_and_bundles(raw_variant, product_group)
        sku = str(row.get(col_sku, "")).strip() if col_sku in row and pd.notna(row.get(col_sku)) else None
        
        records.append({
            "import_batch_id": import_batch_id,
            "platform": "SHOPEE",
            "period_start": period_start,
            "period_end": period_end,
            "product_group": product_group,
            "raw_variant": raw_variant,
            "clean_variant": clean_variant,
            "is_bundling": is_bundling,
            "is_cross_bundling": is_cross,
            "sku": sku,
            "qty_sold": qty_sold,
            "revenue": revenue
        })
        
    return records

def process_tiktok_dataframe(
    df: pd.DataFrame,
    import_batch_id: str,
    period_start = None,
    period_end = None
) -> List[Dict[str, Any]]:
    """
    Ingests and processes TikTok Shop raw export data.
    Explicit Column Standards:
    - Product & Variant: Concatenated in 'Produk' split by ':'
    - Revenue: 'GMV'
    - Quantity: 'Produk terjual'
    - SKU ID: 'SKU ID'
    """
    records = []
    
    col_prod = "Produk"
    col_qty = "Produk terjual"
    col_rev = "GMV"
    col_sku = "SKU ID"
    
    required_cols = [col_prod, col_qty, col_rev]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise KeyError(f"TikTok export missing required column(s): {missing}. Available: {list(df.columns)}")
    
    for _, row in df.iterrows():
        raw_title = row.get(col_prod, "")
        product_title, raw_variant = parse_tiktok_concatenated_title(raw_title)
        
        # Normalize brand prefix from master product title
        product_group = re.sub(r'^Raecca\s+', '', product_title, flags=re.IGNORECASE).strip()
        
        qty_sold = sanitize_integer(row.get(col_qty, 0))
        revenue = sanitize_currency(row.get(col_rev, 0.0))
        
        clean_variant, is_bundling, is_cross = extract_clean_variant_and_bundles(raw_variant, product_group)
        sku = str(row.get(col_sku, "")).strip() if col_sku in row and pd.notna(row.get(col_sku)) else None
        
        records.append({
            "import_batch_id": import_batch_id,
            "platform": "TIKTOK_SHOP",
            "period_start": period_start,
            "period_end": period_end,
            "product_group": product_group,
            "raw_variant": raw_variant,
            "clean_variant": clean_variant,
            "is_bundling": is_bundling,
            "is_cross_bundling": is_cross,
            "sku": sku,
            "qty_sold": qty_sold,
            "revenue": revenue
        })
        
    return records
