"""Deterministic platform adapters for marketplace sales exports (Shopee, TikTok Shop)."""

from __future__ import annotations

import abc
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from app.core.numeric import is_blank_marker, sanitize_currency, sanitize_integer
from app.modules.ingestion.exceptions import MissingRequiredColumnError



class PlatformEnum(str, Enum):
    """Supported e-commerce platforms."""

    SHOPEE = "SHOPEE"
    TIKTOK_SHOP = "TIKTOK_SHOP"
    TOKOPEDIA = "TOKOPEDIA"
    LAZADA = "LAZADA"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RawRecord:
    """Canonical raw extracted record prior to deep domain transformation."""

    platform: str
    product_title: str
    raw_variant: str
    qty_sold: int
    revenue: int
    sku: Optional[str] = None
    case_color: Optional[str] = None


def is_parent_or_summary_row(
    raw_variant: Optional[Any], ignore_condition: str = "EQUALS_DASH"
) -> bool:
    """
    Evaluates if a row represents an aggregate/parent row that must be excluded.
    Prevents double-counting in marketplace sales reports.
    """
    if raw_variant is None:
        return True

    cleaned = str(raw_variant).strip()
    if is_blank_marker(cleaned):
        return True

    if ignore_condition == "EQUALS_DASH":
        return cleaned in ("-", "--", "")
    elif ignore_condition == "IS_EMPTY":
        return not cleaned
    elif ignore_condition == "CONTAINS_TOTAL":
        return any(k in cleaned.lower() for k in ["total", "ringkasan", "semua"])

    return False


def clean_brand_prefix(title: str) -> str:
    """Strips leading brand names (e.g. 'Raecca ') from product titles."""
    if not title:
        return ""
    return re.sub(r"^raecca\s+", "", title.strip(), flags=re.IGNORECASE).strip()


def parse_tiktok_concatenated_title(title_str: Any) -> Tuple[str, str]:
    """
    Parses TikTok Shop concatenated title format:
    '<Master Product Title>: <Variant / Marketing Suffix>'
    e.g. 'Raecca Glow Up Tint...: Cheerful / Tanpa Keychain' -> ('Raecca Glow Up Tint...', 'Cheerful / Tanpa Keychain')
    """
    if title_str is None:
        return "", ""
    s = str(title_str).strip()
    if ":" in s:
        parts = s.split(":", 1)
        return parts[0].strip(), parts[1].strip()
    return s, ""


class BasePlatformAdapter(abc.ABC):
    """Abstract base class for deterministic platform adapters."""

    platform: PlatformEnum

    @abc.abstractmethod
    def validate_headers(self, headers: List[str]) -> None:
        """Validates that all required columns exist in headers, raising MissingRequiredColumnError if not."""

    @abc.abstractmethod
    def adapt(self, rows: List[Dict[str, Any]]) -> List[RawRecord]:
        """Extracts and filters raw spreadsheet rows into atomic RawRecords."""


class ShopeeAdapter(BasePlatformAdapter):
    """
    Deterministic adapter for Shopee Sales Performance export ('Produk dengan Performa Terbaik').

    Target Columns:
    - Product: 'Produk' (Col B)
    - Variant: 'Nama Variasi' (Col E)
    - SKU: 'SKU Induk' (Col H)
    - Qty Sold: 'Produk (Pesanan Siap Dikirim)' (Col S) [Shipped only]
    - Revenue: 'Penjualan (Pesanan Siap Dikirim) (IDR)' (Col J) [Shipped only]

    Parent-row pruning: Drops rows where 'Nama Variasi' is '-' or empty (295 parent rows in reference).
    """

    platform = PlatformEnum.SHOPEE

    COL_PROD = "Produk"
    COL_VAR = "Nama Variasi"
    COL_SKU = "SKU Induk"
    COL_QTY = "Produk (Pesanan Siap Dikirim)"
    COL_REV = "Penjualan (Pesanan Siap Dikirim) (IDR)"

    REQUIRED_COLS = [COL_PROD, COL_VAR, COL_QTY, COL_REV]

    def validate_headers(self, headers: List[str]) -> None:
        headers_set = set(headers)
        missing = [col for col in self.REQUIRED_COLS if col not in headers_set]
        if missing:
            raise MissingRequiredColumnError(
                missing_columns=missing,
                available_headers=headers,
                platform=self.platform.value,
            )

    def adapt(self, rows: List[Dict[str, Any]]) -> List[RawRecord]:
        # Pass 1: Identify which products have explicit child variants
        products_with_children: set[str] = set()
        for row in rows:
            raw_prod = row.get(self.COL_PROD)
            raw_var = row.get(self.COL_VAR)
            if raw_prod is not None and not is_parent_or_summary_row(raw_var, "EQUALS_DASH"):
                prod_key = str(raw_prod).strip().casefold()
                products_with_children.add(prod_key)

        records: List[RawRecord] = []
        for row in rows:
            raw_prod = row.get(self.COL_PROD)
            if raw_prod is None:
                continue
            prod_str = str(raw_prod).strip()
            if not prod_str or prod_str.lower() in ("total", "nan", "none"):
                continue

            raw_variant = row.get(self.COL_VAR)
            prod_key = prod_str.casefold()

            # Deterministic parent-row pruning:
            # If the row has '-' variant AND the product has other child variant rows, prune it as a parent duplicate.
            # If the product has NO other child variant rows (standalone product), keep it.
            if is_parent_or_summary_row(raw_variant, "EQUALS_DASH"):
                if prod_key in products_with_children:
                    continue
                raw_var_str = "-"
            else:
                raw_var_str = str(raw_variant).strip() if raw_variant is not None else ""

            product_title = clean_brand_prefix(prod_str)
            qty_sold = sanitize_integer(row.get(self.COL_QTY, 0))
            revenue_val = sanitize_currency(row.get(self.COL_REV, 0.0))
            revenue = int(round(revenue_val))

            sku_val = row.get(self.COL_SKU)
            sku = (
                str(sku_val).strip()
                if sku_val is not None and not is_blank_marker(sku_val)
                else None
            )

            records.append(
                RawRecord(
                    platform=self.platform.value,
                    product_title=product_title,
                    raw_variant=raw_var_str,
                    qty_sold=qty_sold,
                    revenue=revenue,
                    sku=sku,
                )
            )
        return records


class TikTokShopAdapter(BasePlatformAdapter):
    """
    Deterministic adapter for TikTok Shop export ('Sheet1').

    Target Columns:
    - Product & Variant: 'Produk' (Col C) concatenated with ':' delimiter
    - SKU: 'SKU ID' (Col A)
    - Qty Sold: 'Produk terjual' (Col G)
    - Revenue: 'GMV' (Col E)

    Parent-row pruning: None (all TikTok rows are atomic SKU level).
    """

    platform = PlatformEnum.TIKTOK_SHOP

    COL_PROD = "Produk"
    COL_SKU = "SKU ID"
    COL_QTY = "Produk terjual"
    COL_REV = "GMV"

    REQUIRED_COLS = [COL_PROD, COL_QTY, COL_REV]

    def validate_headers(self, headers: List[str]) -> None:
        headers_set = set(headers)
        missing = [col for col in self.REQUIRED_COLS if col not in headers_set]
        if missing:
            raise MissingRequiredColumnError(
                missing_columns=missing,
                available_headers=headers,
                platform=self.platform.value,
            )

    def adapt(self, rows: List[Dict[str, Any]]) -> List[RawRecord]:
        records: List[RawRecord] = []
        for row in rows:
            raw_prod = row.get(self.COL_PROD)
            if raw_prod is None:
                continue

            product_title_raw, raw_variant = parse_tiktok_concatenated_title(raw_prod)
            if not product_title_raw or product_title_raw.lower() in ("total", "nan", "none"):
                continue

            product_title = clean_brand_prefix(product_title_raw)

            qty_sold = sanitize_integer(row.get(self.COL_QTY, 0))
            revenue_val = sanitize_currency(row.get(self.COL_REV, 0.0))
            revenue = int(round(revenue_val))

            sku_val = row.get(self.COL_SKU)
            sku = (
                str(sku_val).strip()
                if sku_val is not None and not is_blank_marker(sku_val)
                else None
            )

            records.append(
                RawRecord(
                    platform=self.platform.value,
                    product_title=product_title,
                    raw_variant=raw_variant,
                    qty_sold=qty_sold,
                    revenue=revenue,
                    sku=sku,
                )
            )
        return records


def detect_adapter(
    headers: List[str], sheet_name: Optional[str] = None
) -> Optional[BasePlatformAdapter]:
    """
    Inspects column headers and sheet name to detect matching deterministic platform adapter.
    """
    headers_set = set(headers)

    # Shopee detection
    if {
        ShopeeAdapter.COL_PROD,
        ShopeeAdapter.COL_VAR,
        ShopeeAdapter.COL_QTY,
        ShopeeAdapter.COL_REV,
    }.issubset(headers_set):
        return ShopeeAdapter()

    # TikTok Shop detection
    if {
        TikTokShopAdapter.COL_PROD,
        TikTokShopAdapter.COL_QTY,
        TikTokShopAdapter.COL_REV,
    }.issubset(headers_set):
        return TikTokShopAdapter()

    return None


def get_adapter(platform: PlatformEnum | str) -> BasePlatformAdapter:
    """Returns platform adapter by platform enum/string."""
    p_str = platform.value if isinstance(platform, PlatformEnum) else str(platform).upper()
    if p_str == PlatformEnum.SHOPEE.value:
        return ShopeeAdapter()
    elif p_str == PlatformEnum.TIKTOK_SHOP.value:
        return TikTokShopAdapter()
    raise ValueError(f"No adapter registered for platform '{platform}'")
