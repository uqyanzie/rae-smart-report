import json
from pathlib import Path
import openpyxl

def safe_float(val, default=0.0):
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    try:
        s = str(val).strip()
        if s.startswith("#") or s == "":
            return default
        return float(s)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return int(round(val))
    try:
        s = str(val).strip()
        if s.startswith("#") or s == "":
            return default
        return int(round(float(s)))
    except (ValueError, TypeError):
        return default

def extract_golden_fixtures():
    base_dir = Path(__file__).resolve().parent.parent.parent.parent
    xlsx_path = base_dir / "sample_data" / "expected_output" / "output_13_19_Jul26.xlsx"
    fixtures_dir = Path(__file__).resolve().parent
    
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    
    # 1. Extract Produk S (Shopee) left table variant totals
    shopee_sheet = wb["Produk S"]
    shopee_variants = []
    # Left table: Cols A (Family/Group), B (Clean Variant), C (Qty Sold), D (Revenue IDR), E (Contribution %)
    # Iterate row 2 onwards until empty row in col B or total
    row_idx = 2
    while True:
        family = shopee_sheet.cell(row=row_idx, column=1).value
        variant = shopee_sheet.cell(row=row_idx, column=2).value
        qty = shopee_sheet.cell(row=row_idx, column=3).value
        revenue = shopee_sheet.cell(row=row_idx, column=4).value
        contrib = shopee_sheet.cell(row=row_idx, column=5).value
        
        if not variant and not family:
            break
        if variant:
            shopee_variants.append({
                "row_index": row_idx,
                "family": str(family).strip() if family else "",
                "variant": str(variant).strip(),
                "qty": safe_int(qty),
                "revenue": safe_int(revenue),
                "contribution_ratio": safe_float(contrib)
            })
        row_idx += 1

    # 2. Extract Produk T (TikTok Shop) left table variant totals
    tts_sheet = wb["Produk T"]
    tts_variants = []
    row_idx = 2
    while True:
        family = tts_sheet.cell(row=row_idx, column=1).value
        variant = tts_sheet.cell(row=row_idx, column=2).value
        qty = tts_sheet.cell(row=row_idx, column=3).value
        revenue = tts_sheet.cell(row=row_idx, column=4).value
        contrib = tts_sheet.cell(row=row_idx, column=5).value
        
        if not variant and not family:
            break
        if variant:
            tts_variants.append({
                "row_index": row_idx,
                "family": str(family).strip() if family else "",
                "variant": str(variant).strip(),
                "qty": safe_int(qty),
                "revenue": safe_int(revenue),
                "contribution_ratio": safe_float(contrib)
            })
        row_idx += 1

    # 3. Specific oracles defined in plan
    # Active contribution ratio in Glow Up Tint
    active_entry = next((v for v in shopee_variants if v["variant"] == "Active"), None)
    active_ratio = active_entry["contribution_ratio"] if active_entry else 0.05974791292

    # Foldback addends verified from sample data
    foldback_addends = {
        "Dynamic": {
            "qty_addend": 0,
            "revenue_addend": 139900
        },
        "Energic": {
            "qty_addend": 10,
            "revenue_addend": 654649
        }
    }

    # Summary grand totals from Right Table (Cols G-J)
    def extract_right_table(ws):
        groups = []
        r = 2
        while True:
            group_name = ws.cell(row=r, column=7).value
            qty = ws.cell(row=r, column=8).value
            rev = ws.cell(row=r, column=9).value
            share = ws.cell(row=r, column=10).value
            if not group_name:
                break
            if str(group_name).strip() == "Total":
                break
            groups.append({
                "group_name": str(group_name).strip(),
                "qty": safe_int(qty),
                "revenue": safe_int(rev),
                "share": safe_float(share)
            })
            r += 1
        return groups

    shopee_summary = extract_right_table(shopee_sheet)
    tts_summary = extract_right_table(tts_sheet)

    golden_data = {
        "source_file": "sample_data/expected_output/output_13_19_Jul26.xlsx",
        "description": "Deterministic oracle totals extracted from golden reference workbook",
        "shopee_variants": shopee_variants,
        "tiktok_variants": tts_variants,
        "shopee_summary_groups": shopee_summary,
        "tiktok_summary_groups": tts_summary,
        "active_contribution_ratio": active_ratio,
        "foldback_addends": foldback_addends,
        "counts": {
            "shopee_variant_count": len(shopee_variants),
            "tiktok_variant_count": len(tts_variants),
            "shopee_summary_group_count": len(shopee_summary),
            "tiktok_summary_group_count": len(tts_summary)
        }
    }

    output_path = fixtures_dir / "golden_totals.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(golden_data, f, indent=2)

    print(f"Successfully extracted {len(shopee_variants)} Shopee variants and {len(tts_variants)} TikTok variants.")
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    extract_golden_fixtures()

