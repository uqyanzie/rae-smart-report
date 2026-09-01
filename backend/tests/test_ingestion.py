"""Tests for multi-sheet spreadsheet ingestion, delimiter detection, and platform adapters."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.ingestion.exceptions import (
    MissingRequiredColumnError,
    SheetNotFoundError,
    SpreadsheetEmptyError,
    UnsupportedFormatError,
)
from app.modules.ingestion.reader import (
    extract_spreadsheet_rows,
    read_spreadsheet,
)
from app.modules.profiler.adapters import (
    PlatformEnum,
    ShopeeAdapter,
    TikTokShopAdapter,
    TokopediaAdapter,
    LazadaAdapter,
    detect_adapter,
    get_adapter,
    is_parent_or_summary_row,
)
from app.modules.profiler.fallback import (
    ParentRowIgnoreCondition,
    compute_header_signature,
    profile_spreadsheet_headers,
)



class TestShopeeIngestion:
    """Tests for Shopee sales performance workbook parsing and parent-row elimination."""

    def test_shopee_sheet_detection_and_metadata(self, raw_shopee_path: Path):
        assert raw_shopee_path.exists(), f"Missing fixture at {raw_shopee_path}"
        meta = read_spreadsheet(raw_shopee_path)

        assert meta.active_sheet == "Produk dengan Performa Terbaik"
        assert len(meta.available_sheets) == 7
        assert "Produk dengan Performa Terbaik" in meta.available_sheets
        assert meta.total_rows == 1061
        assert len(meta.raw_headers) == 40
        assert "Produk" in meta.raw_headers
        assert "Nama Variasi" in meta.raw_headers
        assert "Produk (Pesanan Siap Dikirim)" in meta.raw_headers
        assert "Penjualan (Pesanan Siap Dikirim) (IDR)" in meta.raw_headers
        assert len(meta.sample_rows) == 10

    def test_shopee_adapter_prunes_exact_295_parent_rows(self, raw_shopee_path: Path):
        headers, rows = extract_spreadsheet_rows(raw_shopee_path)
        assert len(rows) == 1061

        adapter = ShopeeAdapter()
        adapter.validate_headers(headers)
        records = adapter.adapt(rows)

        # 1061 total rows:
        # - 295 rows have '-' variant
        # - 110 of those belong to products WITH child variants (true parent summary duplicates -> pruned)
        # - 185 belong to standalone products WITHOUT child variants (e.g. single Lipcare tubes -> preserved)
        # - 766 child variant rows preserved
        # Total preserved records = 766 child + 185 standalone = 951
        assert len(records) == 951
        dash_rows_count = sum(
            1 for r in rows if is_parent_or_summary_row(r.get("Nama Variasi"), "EQUALS_DASH")
        )
        assert dash_rows_count == 295

        for rec in records:
            assert rec.platform == PlatformEnum.SHOPEE.value
            assert rec.qty_sold >= 0
            assert rec.revenue >= 0
            assert not rec.product_title.lower().startswith("raecca ")

    def test_shopee_adapter_detection(self, raw_shopee_path: Path):
        headers, _ = extract_spreadsheet_rows(raw_shopee_path)
        adapter = detect_adapter(headers)
        assert isinstance(adapter, ShopeeAdapter)
        assert adapter.platform == PlatformEnum.SHOPEE


class TestTikTokShopIngestion:
    """Tests for TikTok Shop export parsing and concatenated title splitting."""

    def test_tiktok_metadata_and_row_count(self, raw_tts_path: Path):
        assert raw_tts_path.exists(), f"Missing fixture at {raw_tts_path}"
        meta = read_spreadsheet(raw_tts_path)

        assert meta.active_sheet == "Sheet1"
        assert meta.available_sheets == ["Sheet1"]
        assert meta.total_rows == 270
        assert "Produk" in meta.raw_headers
        assert "Produk terjual" in meta.raw_headers
        assert "GMV" in meta.raw_headers
        assert len(meta.sample_rows) == 10

    def test_tiktok_adapter_extracts_all_270_rows(self, raw_tts_path: Path):
        headers, rows = extract_spreadsheet_rows(raw_tts_path)
        assert len(rows) == 270

        adapter = TikTokShopAdapter()
        adapter.validate_headers(headers)
        records = adapter.adapt(rows)

        # All 270 rows are atomic SKU level; 0 parent rows pruned
        assert len(records) == 270
        for rec in records:
            assert rec.platform == PlatformEnum.TIKTOK_SHOP.value
            assert rec.qty_sold >= 0
            assert rec.revenue >= 0
            assert not rec.product_title.lower().startswith("raecca ")

    def test_tiktok_adapter_detection(self, raw_tts_path: Path):
        headers, _ = extract_spreadsheet_rows(raw_tts_path)
        adapter = detect_adapter(headers)
        assert isinstance(adapter, TikTokShopAdapter)
        assert adapter.platform == PlatformEnum.TIKTOK_SHOP


class TestTokopediaIngestion:
    """Tests for Tokopedia export parsing.

    Tokopedia exports share the exact column schema with TikTok Shop
    ('SKU ID', 'Product ID', 'Produk', 'Status', 'GMV', 'Pesanan SKU',
    'Produk terjual') including the concatenated '<Master>: <Variant>' title
    format, so extraction is identical; only the platform tag differs.
    """

    def test_tokopedia_metadata_and_row_count(self, raw_tp_path: Path):
        assert raw_tp_path.exists(), f"Missing fixture at {raw_tp_path}"
        meta = read_spreadsheet(raw_tp_path)

        assert meta.active_sheet == "Sheet1"
        assert meta.available_sheets == ["Sheet1"]
        assert meta.total_rows == 121
        assert "Produk" in meta.raw_headers
        assert "Produk terjual" in meta.raw_headers
        assert "GMV" in meta.raw_headers
        assert len(meta.sample_rows) == 10

    def test_tokopedia_adapter_extracts_all_rows(self, raw_tp_path: Path):
        headers, rows = extract_spreadsheet_rows(raw_tp_path)
        assert len(rows) == 121

        adapter = TokopediaAdapter()
        adapter.validate_headers(headers)
        records = adapter.adapt(rows)

        # All 121 rows are atomic SKU level; 0 parent rows pruned.
        assert len(records) == 121
        for rec in records:
            assert rec.platform == PlatformEnum.TOKOPEDIA.value
            assert rec.qty_sold >= 0
            assert rec.revenue >= 0
            assert not rec.product_title.lower().startswith("raecca ")

    def test_tokopedia_adapter_parses_concatenated_title(self, raw_tp_path: Path):
        headers, rows = extract_spreadsheet_rows(raw_tp_path)
        records = TokopediaAdapter().adapt(rows)

        # First data row: '... #1stLipSpecialist: Cheerful / Tanpa Keychain'
        # splits into master title + variant exactly like TikTok Shop.
        first = records[0]
        assert first.raw_variant == "Cheerful / Tanpa Keychain"
        assert first.product_title.startswith("Glow Up Tint")
        assert first.sku == "1729821744670737438"

    def test_tokopedia_get_adapter(self):
        adapter = get_adapter(PlatformEnum.TOKOPEDIA)
        assert isinstance(adapter, TokopediaAdapter)
        assert adapter.platform == PlatformEnum.TOKOPEDIA
        assert get_adapter("TOKOPEDIA").platform == PlatformEnum.TOKOPEDIA

    def test_tokopedia_headers_match_tiktok_signature(self, raw_tp_path: Path, raw_tts_path: Path):
        """Tokopedia shares TikTok's exact 7-column schema, so header-signature
        detection cannot distinguish them (TikTok wins the tie); the platform
        is resolved explicitly via get_adapter."""
        tp_headers, _ = extract_spreadsheet_rows(raw_tp_path)
        tts_headers, _ = extract_spreadsheet_rows(raw_tts_path)

        assert compute_header_signature(tp_headers) == compute_header_signature(tts_headers)
        adapter = detect_adapter(tp_headers)
        assert isinstance(adapter, TikTokShopAdapter)


class TestLazadaIngestion:
    """Tests for Lazada 'Bisnis Analisis - Kinerja Produk' parsing.

    Lazada exports carry 5 preamble rows (source/description) before the real
    header at row index 5, and product-level parent rows whose 'Seller SKU' is
    '-' or empty (verified: parent qty == sum of child SKU qty).
    """

    def test_lazada_preamble_skip_and_metadata(self, raw_laz_aug_path: Path):
        assert raw_laz_aug_path.exists(), f"Missing fixture at {raw_laz_aug_path}"
        meta = read_spreadsheet(raw_laz_aug_path)

        assert meta.active_sheet == "Produk"
        assert meta.available_sheets == ["Produk"]
        # 109 data rows after the 5 preamble rows + header (115 total - 6).
        assert meta.total_rows == 109
        assert meta.raw_headers[0] == "Kinerja Produk"
        assert meta.raw_headers[1] == "Nama Produk"
        assert "Seller SKU" in meta.raw_headers
        assert "Unit Terjual" in meta.raw_headers
        assert "Pendapatan" in meta.raw_headers
        assert len(meta.sample_rows) == 10

    def test_lazada_metadata_aug24(self, raw_laz_aug24_path: Path):
        meta = read_spreadsheet(raw_laz_aug24_path)
        assert meta.total_rows == 56
        assert "Seller SKU" in meta.raw_headers

    def test_lazada_adapter_prunes_parent_rows(self, raw_laz_aug_path: Path):
        headers, rows = extract_spreadsheet_rows(raw_laz_aug_path)
        assert len(rows) == 109

        adapter = LazadaAdapter()
        adapter.validate_headers(headers)
        records = adapter.adapt(rows)

        # 109 data rows: 32 product-level parents pruned, 77 atomic SKU rows kept.
        assert len(records) == 77
        parent_count = sum(
            1 for r in rows if is_parent_or_summary_row(r.get("Seller SKU"), "EQUALS_DASH")
        )
        assert parent_count == 32
        for rec in records:
            assert rec.platform == PlatformEnum.LAZADA.value
            assert rec.sku is not None and rec.sku != "-"
            assert rec.qty_sold >= 0
            assert rec.revenue >= 0

    def test_lazada_adapter_prunes_parent_rows_aug24(self, raw_laz_aug24_path: Path):
        headers, rows = extract_spreadsheet_rows(raw_laz_aug24_path)
        records = LazadaAdapter().adapt(rows)
        assert len(records) == 32

    def test_lazada_exact_sku_resolution(self, raw_laz_aug_path: Path):
        headers, rows = extract_spreadsheet_rows(raw_laz_aug_path)
        records = LazadaAdapter().adapt(rows)
        by_sku = {rec.sku: rec for rec in records}

        # Exact lookup in sku_mapping.json: product_title is brand-stripped,
        # raw_variant is the mapped 'Nama Variasi'.
        raeglt003 = by_sku["RAEGLT-003"]
        assert raeglt003.product_title == "Glow Up Tint"
        assert raeglt003.raw_variant == "Cheerfull,Tanpa Keychain"

        raectbl004 = by_sku["RAECTBL-004"]
        assert raectbl004.product_title == "The Bloom Perfect Matte Lipstick"
        assert raectbl004.raw_variant == "04 Tulip,Tanpa Keychain"

        rotg001 = by_sku["ROTG-001"]
        assert rotg001.product_title == "Over The Glaze"
        assert rotg001.raw_variant == "Over Cute,Tanpa Keychain"

    def test_lazada_reverse_order_sku_resolution(self, raw_laz_aug_path: Path):
        headers, rows = extract_spreadsheet_rows(raw_laz_aug_path)
        records = LazadaAdapter().adapt(rows)
        by_sku = {rec.sku: rec for rec in records}

        # RAEGLT-008-006 reverses to RAEGLT-006-008 (Energic,08. Gorgeous),
        # which the normalizer folds into the on-grid 'Energic + Gorgeous'.
        rec = by_sku["RAEGLT-008-006"]
        assert rec.product_title == "Bundling Raecca Glow Up Tint"
        assert rec.raw_variant == "Energic,08. Gorgeous"
        assert rec.qty_sold == 1
        assert rec.revenue == 150_555

        # RAEGLT-006-003 reverses to RAEGLT-003-006 (Cheerful,06. Energic).
        rec = by_sku["RAEGLT-006-003"]
        assert rec.product_title == "Bundling Raecca Glow Up Tint"
        assert rec.raw_variant == "Cheerful,06. Energic"

    def test_lazada_dash_prefix_auto_sku_decode(self, raw_laz_aug_path: Path):
        headers, rows = extract_spreadsheet_rows(raw_laz_aug_path)
        records = LazadaAdapter().adapt(rows)
        by_sku = {rec.sku: rec for rec in records}

        # '-'-prefixed auto-SKUs decode the variant label ('-' -> ', ') so the
        # normalizer folds back same-shade 2-packs (qty 0 in this sample).
        rec = by_sku["-Cheerfull-03. Cheerfull"]
        assert rec.product_title == "Bundling Raecca Glow Up Tint - Bundle 2 Lip Tint #1stLipSpecialist"
        assert rec.raw_variant == ", Cheerfull, 03. Cheerfull"
        assert rec.qty_sold == 0

    def test_lazada_fallback_title_and_sku_variant(self, raw_laz_aug_path: Path):
        headers, rows = extract_spreadsheet_rows(raw_laz_aug_path)
        records = LazadaAdapter().adapt(rows)
        by_sku = {rec.sku: rec for rec in records}

        # Unknown SKUs fall back to the 'Nama Produk' title + the SKU as the
        # raw variant; they persist as unreported (qty 0 in the sample).
        rec = by_sku["STD-14"]
        assert rec.product_title == "Bundling Raecca Swipe To Glow - Bundle 2 Lip Gloss #1stLipSpecialist"
        assert rec.raw_variant == "STD-14"

        rec = by_sku["F"]
        assert "Heart Mirror" in rec.product_title
        assert rec.raw_variant == "F"

    def test_lazada_adapter_detection(self, raw_laz_aug_path: Path):
        headers, _ = extract_spreadsheet_rows(raw_laz_aug_path)
        adapter = detect_adapter(headers)
        assert isinstance(adapter, LazadaAdapter)
        assert adapter.platform == PlatformEnum.LAZADA

    def test_lazada_get_adapter(self):
        adapter = get_adapter(PlatformEnum.LAZADA)
        assert isinstance(adapter, LazadaAdapter)
        assert adapter.platform == PlatformEnum.LAZADA
        assert get_adapter("LAZADA").platform == PlatformEnum.LAZADA


class TestCSVIngestionAndDelimiters:
    """Tests for CSV parsing across comma, semicolon, tab, and character encodings."""

    @pytest.mark.parametrize(
        "delim,data",
        [
            (",", "Produk,Nama Variasi,Produk (Pesanan Siap Dikirim),Penjualan (Pesanan Siap Dikirim) (IDR)\nRaecca Glow Up Tint,05. Dynamic,10,149.000\n"),
            (";", "Produk;Nama Variasi;Produk (Pesanan Siap Dikirim);Penjualan (Pesanan Siap Dikirim) (IDR)\nRaecca Glow Up Tint;05. Dynamic;10;149.000\n"),
            ("\t", "Produk\tNama Variasi\tProduk (Pesanan Siap Dikirim)\tPenjualan (Pesanan Siap Dikirim) (IDR)\nRaecca Glow Up Tint\t05. Dynamic\t10\t149.000\n"),
        ],
    )
    def test_csv_delimiters(self, delim: str, data: str):
        content = data.encode("utf-8")
        meta = read_spreadsheet(content, filename="test.csv")
        assert meta.detected_delimiter == delim
        assert meta.total_rows == 1
        assert "Produk" in meta.raw_headers

    def test_csv_mojibake_encoding_handling(self):
        # Corrupted characters in title (e.g. Winona's Ombre Picks with replacement char)
        csv_bytes = (
            "Produk,Produk terjual,GMV\n"
            "Raecca Winona\uFFFDs Ombre Picks: Dynamic,5,75000\n"
        ).encode("utf-8")

        meta = read_spreadsheet(csv_bytes, filename="mojibake.csv")
        assert meta.total_rows == 1
        assert "Produk" in meta.raw_headers
        assert len(meta.sample_rows) == 1


class TestProfilerAndHeaderSignatures:
    """Tests for SHA-256 signature hashing and schema profiler models."""

    def test_header_signature_order_invariance(self):
        h1 = ["Produk", "Nama Variasi", "SKU Induk", "GMV"]
        h2 = ["GMV", "SKU Induk", "Nama Variasi", "Produk"]
        h3 = ["  produk  ", "NAMA VARIASI", "SKU INDUK", "gmv "]

        sig1 = compute_header_signature(h1)
        sig2 = compute_header_signature(h2)
        sig3 = compute_header_signature(h3)

        assert sig1 == sig2 == sig3
        assert len(sig1) == 64  # SHA-256 hex string

    def test_profiler_shopee_detection(self, raw_shopee_path: Path):
        headers, _ = extract_spreadsheet_rows(raw_shopee_path)
        profile = profile_spreadsheet_headers(headers)

        assert profile.platform == PlatformEnum.SHOPEE
        assert profile.confidence == 1.0
        assert profile.column_mapping.product_group == "Produk"
        assert profile.column_mapping.raw_variant == "Nama Variasi"
        assert profile.parent_row_rule is not None
        assert profile.parent_row_rule.ignore_condition == ParentRowIgnoreCondition.EQUALS_DASH

    def test_profiler_tiktok_detection(self, raw_tts_path: Path):
        headers, _ = extract_spreadsheet_rows(raw_tts_path)
        profile = profile_spreadsheet_headers(headers)

        assert profile.platform == PlatformEnum.TIKTOK_SHOP
        assert profile.confidence == 1.0
        assert profile.column_mapping.qty_sold == "Produk terjual"
        assert profile.column_mapping.revenue == "GMV"
        assert profile.parent_row_rule is None

    def test_profiler_unknown_fallback(self):
        unknown_headers = ["ColA", "ColB", "RandomHeader"]
        profile = profile_spreadsheet_headers(unknown_headers)

        assert profile.platform == PlatformEnum.UNKNOWN
        assert profile.confidence == 0.0
        assert profile.parent_row_rule is None

    def test_profiler_lazada_detection(self, raw_laz_aug_path: Path):
        headers, _ = extract_spreadsheet_rows(raw_laz_aug_path)
        profile = profile_spreadsheet_headers(headers)

        assert profile.platform == PlatformEnum.LAZADA
        assert profile.confidence == 1.0
        assert profile.column_mapping.product_group == "Nama Produk"
        assert profile.column_mapping.raw_variant == "Seller SKU"
        assert profile.column_mapping.qty_sold == "Unit Terjual"
        assert profile.column_mapping.revenue == "Pendapatan"
        assert profile.column_mapping.sku == "SKU ID"
        assert profile.parent_row_rule is not None
        assert profile.parent_row_rule.target_column == "Seller SKU"
        assert profile.parent_row_rule.ignore_condition == ParentRowIgnoreCondition.EQUALS_DASH
        assert profile.suggested_cleaning_rules == []


class TestIngestionExceptions:
    """Tests for structured error raising on invalid files, missing sheets, and missing columns."""

    def test_unsupported_format_xls(self):
        with pytest.raises(UnsupportedFormatError) as exc_info:
            read_spreadsheet(b"fake-content", filename="report.xls")
        assert "Unsupported file format" in str(exc_info.value)
        assert ".xls" in str(exc_info.value)

    def test_sheet_not_found(self, raw_shopee_path: Path):
        with pytest.raises(SheetNotFoundError) as exc_info:
            extract_spreadsheet_rows(raw_shopee_path, sheet_name="NonExistentSheet")
        assert "NonExistentSheet" in str(exc_info.value)

    def test_missing_required_column_in_shopee(self):
        # Missing ready-to-ship columns (e.g. only contains created orders)
        bad_headers = ["Produk", "Nama Variasi", "Pesanan Dibuat"]
        adapter = ShopeeAdapter()
        with pytest.raises(MissingRequiredColumnError) as exc_info:
            adapter.validate_headers(bad_headers)
        assert "Missing required column(s)" in str(exc_info.value)
        assert "Produk (Pesanan Siap Dikirim)" in str(exc_info.value)

    def test_empty_spreadsheet_raises(self):
        with pytest.raises(SpreadsheetEmptyError):
            read_spreadsheet(b"", filename="empty.csv")
