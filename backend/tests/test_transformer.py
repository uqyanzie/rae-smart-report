"""Unit and integration test suite for transformation, normalization, fold-back, and fixed grid generator."""

from __future__ import annotations

import pytest
from app.domain.models import VariantRecord
from app.modules.ingestion.reader import extract_spreadsheet_rows
from app.modules.profiler.adapters import (
    RawRecord,
    ShopeeAdapter,
    TikTokShopAdapter,
)
from app.modules.transformer import (
    FoldBackEngine,
    InvalidVariantError,
    VariantNormalizer,
    extract_case_color,
    generate_cross_family_grid,
    generate_full_produk2_grid,
    generate_full_produk_grid,
    generate_intra_family_grid,
    strip_ordinal_prefix,
    strip_packaging_noise,
    transform_records,
)


class TestNormalizerHelpers:
    """Test individual string and token normalizer helper functions."""

    def test_strip_packaging_noise(self) -> None:
        assert strip_packaging_noise("Cheerful / Tanpa Keychain") == "Cheerful"
        assert strip_packaging_noise("Brave, Random Keychain") == "Brave"
        assert strip_packaging_noise("Dynamic, random keychain") == "Dynamic"
        assert strip_packaging_noise("Active / Free Keychain") == "Active"
        assert strip_packaging_noise("Orchid / Aplikator") == "Orchid"
        assert strip_packaging_noise("Plain Shade") == "Plain Shade"

    def test_strip_ordinal_prefix(self) -> None:
        assert strip_ordinal_prefix("05. Dynamic") == "Dynamic"
        assert strip_ordinal_prefix("01 Peony") == "Peony"
        assert strip_ordinal_prefix("08-Gorgeous") == "Gorgeous"
        assert strip_ordinal_prefix("10. Happy") == "Happy"
        assert strip_ordinal_prefix("11 / Joyful") == "Joyful"
        assert strip_ordinal_prefix("Active") == "Active"

    def test_extract_case_color(self) -> None:
        text, cc = extract_case_color("Over Cute + Bunny Pink, Fizzy Pop")
        assert cc == "Fizzy Pop"
        assert text == "Over Cute + Bunny Pink"

        text, cc = extract_case_color("Sweetie Pop")
        assert cc == "Sweetie Pop"

        text, cc = extract_case_color("Active + Brave")
        assert cc is None
        assert text == "Active + Brave"


class TestVariantNormalizer:
    """Test VariantNormalizer token parsing, alias resolution, and classification."""

    @pytest.fixture
    def normalizer(self) -> VariantNormalizer:
        return VariantNormalizer()

    def test_normalize_single_shade(self, normalizer: VariantNormalizer) -> None:
        raw = RawRecord(
            platform="SHOPEE",
            product_title="Raecca Glow Up Tint",
            raw_variant="05. Dynamic",
            qty_sold=10,
            revenue=149000,
        )
        rec, warn, is_foldback = normalizer.normalize_single(raw)
        assert warn is None
        assert is_foldback is False
        assert rec is not None
        assert rec.product_group == "Glow Up Tint"
        assert rec.clean_variant == "Dynamic"
        assert rec.is_bundling is False
        assert rec.is_cross_bundling is False
        assert rec.qty_sold == 10
        assert rec.revenue == 149000

    def test_normalize_alias_resolution(self, normalizer: VariantNormalizer) -> None:
        # 'Cheerfull' -> 'Cheerful'
        raw1 = RawRecord(
            platform="SHOPEE",
            product_title="Raecca Glow Up Tint",
            raw_variant="Cheerfull",
            qty_sold=5,
            revenue=75000,
        )
        rec1, _, _ = normalizer.normalize_single(raw1)
        assert rec1 is not None
        assert rec1.clean_variant == "Cheerful"

        # 'ov hype' -> 'Over Hype'
        raw2 = RawRecord(
            platform="SHOPEE",
            product_title="Raecca Over The Glaze",
            raw_variant="03. Ov Hype",
            qty_sold=8,
            revenue=120000,
        )
        rec2, _, _ = normalizer.normalize_single(raw2)
        assert rec2 is not None
        assert rec2.clean_variant == "Over Hype"

        # 'bunpink' -> 'Bunny Pink'
        raw3 = RawRecord(
            platform="SHOPEE",
            product_title="Raecca Tinted Jelly Balm",
            raw_variant="bunpink",
            qty_sold=2,
            revenue=50000,
        )
        rec3, _, _ = normalizer.normalize_single(raw3)
        assert rec3 is not None
        assert rec3.clean_variant == "Bunny Pink"

    def test_normalize_intra_bundle_gut(self, normalizer: VariantNormalizer) -> None:
        raw = RawRecord(
            platform="SHOPEE",
            product_title="Raecca Bundling Glow Up Tint",
            raw_variant="Active, Brave",
            qty_sold=4,
            revenue=522234,
        )
        rec, warn, is_foldback = normalizer.normalize_single(raw)
        assert warn is None
        assert is_foldback is False
        assert rec is not None
        assert rec.product_group == "Bundling Glow Up Tint"
        assert rec.clean_variant == "Active + Brave"
        assert rec.is_bundling is True
        assert rec.is_cross_bundling is False

    def test_normalize_tjb_bundle_nudy_aliases(self, normalizer: VariantNormalizer) -> None:
        """TJB bundle variants using 'NudCara'/'NudCaramel' for 'Nudy Caramel'
        must resolve to the full two-shade grid label instead of degrading to a
        single-shade row in the unreported sheet (alias drift from the skill
        reference catalog)."""
        title = (
            "[NEW CASE LAUNCHING] Bundling Raecca Tinted Jelly Balm - "
            "Rekomendasi Lipbalm Melembabkan Bibir Kering #1stLipSpecialist"
        )
        cases = [
            ("Wild Mauve + NudCara,Fizzy + Sweetie", "Wild Mauve + Nudy Caramel"),
            ("BunPink + NudCaramel,Fizzy + Cherry", "Bunny Pink + Nudy Caramel"),
            ("NudCara + Red Babe,Fizzy + Cherry", "Nudy Caramel + Red Babe"),
        ]
        for raw_variant, expected in cases:
            raw = RawRecord(
                platform="SHOPEE",
                product_title=title,
                raw_variant=raw_variant,
                qty_sold=1,
                revenue=97500,
            )
            rec, warn, is_foldback = normalizer.normalize_single(raw)
            assert warn is None, raw_variant
            assert is_foldback is False
            assert rec is not None
            assert rec.product_group == "Bundling Tinted Jelly Balm"
            assert rec.clean_variant == expected
            assert rec.is_bundling is True
            assert rec.is_cross_bundling is False

    def test_normalize_same_shade_detection(self, normalizer: VariantNormalizer) -> None:
        raw = RawRecord(
            platform="SHOPEE",
            product_title="Raecca Bundling Glow Up Tint",
            raw_variant="Dynamic, 05. Dynamic",
            qty_sold=1,
            revenue=139900,
        )
        rec, warn, is_foldback = normalizer.normalize_single(raw)
        assert warn is None
        assert is_foldback is True
        assert rec is not None
        assert rec.product_group == "Glow Up Tint"
        assert rec.clean_variant == "Dynamic"

    def test_normalize_same_shade_triple_raises(self, normalizer: VariantNormalizer) -> None:
        """R2/A2: a same-shade N>2 pack violates the fold-back contract (N=2
        only) and raises the dedicated InvalidVariantError with the shade, raw
        variant, and SKU named."""
        raw = RawRecord(
            platform="SHOPEE",
            product_title="Raecca Bundling Glow Up Tint",
            raw_variant="Dynamic, 05. Dynamic, Dynamic",
            qty_sold=3,
            revenue=419700,
            sku="SKU-TRIPLE-01",
        )
        with pytest.raises(InvalidVariantError) as excinfo:
            normalizer.normalize_single(raw)
        exc = excinfo.value
        assert isinstance(exc, InvalidVariantError)
        assert exc.shade == "Dynamic"
        assert exc.raw_variant == "Dynamic, 05. Dynamic, Dynamic"
        assert exc.sku == "SKU-TRIPLE-01"
        assert exc.multiplicity == 3
        message = str(exc)
        assert "Dynamic" in message
        assert "Dynamic, 05. Dynamic, Dynamic" in message
        assert "SKU-TRIPLE-01" in message

    def test_normalize_otg_asymmetric_label_reachable(
        self, normalizer: VariantNormalizer
    ) -> None:
        """R7: 'Ov Cute + Ov Lovie' resolves to the grid label
        'Over Cute + Lovie' instead of landing off-grid."""
        raw = RawRecord(
            platform="SHOPEE",
            product_title="Raecca Bundling Over The Glaze",
            raw_variant="Ov Cute + Ov Lovie",
            qty_sold=0,
            revenue=0,
        )
        rec, warn, is_foldback = normalizer.normalize_single(raw)
        assert warn is None
        assert is_foldback is False
        assert rec is not None
        assert rec.product_group == "Bundling Over The Glaze"
        assert rec.clean_variant == "Over Cute + Lovie"
        assert rec.is_bundling is True
        assert rec.is_cross_bundling is False

    def test_normalize_lipcare_singles_and_bundles(self, normalizer: VariantNormalizer) -> None:
        # Lipcare single shade maps to distinct group
        raw_single = RawRecord(
            platform="SHOPEE",
            product_title="Raecca Lipcare",
            raw_variant="Lip Moist",
            qty_sold=10,
            revenue=600000,
        )
        rec_s, _, _ = normalizer.normalize_single(raw_single)
        assert rec_s is not None
        assert rec_s.product_group == "Lip Moist"
        assert rec_s.clean_variant == "Lip Moist"
        assert rec_s.is_bundling is False

        # Lipcare explicit bundle label
        raw_bundle = RawRecord(
            platform="SHOPEE",
            product_title="Raecca Bundling Lipcare",
            raw_variant="Lip Moist (2pcs)",
            qty_sold=3,
            revenue=300000,
        )
        rec_b, _, _ = normalizer.normalize_single(raw_bundle)
        assert rec_b is not None
        assert rec_b.product_group == "Bundling Lipcare"
        assert rec_b.clean_variant == "Lip Moist (2pcs)"
        assert rec_b.is_bundling is True

    def test_normalize_power_frosted_short_form(self, normalizer: VariantNormalizer) -> None:
        # Power Frosted intra-bundle uses short forms
        raw = RawRecord(
            platform="SHOPEE",
            product_title="Raecca Bundling Power Frosted Velvet Matte",
            raw_variant="Kind + Honest",
            qty_sold=2,
            revenue=200000,
        )
        rec, _, _ = normalizer.normalize_single(raw)
        assert rec is not None
        assert rec.product_group == "Bundling Power Frosted Velvet Matte"
        assert rec.clean_variant == "Kind + Honest"

    def test_normalize_cross_family_bundle(self, normalizer: VariantNormalizer) -> None:
        raw = RawRecord(
            platform="SHOPEE",
            product_title="Bundling Glow Up Tint & Over The Glaze",
            raw_variant="Active, Over Cute",
            qty_sold=3,
            revenue=300000,
        )
        rec, _, _ = normalizer.normalize_single(raw)
        assert rec is not None
        assert rec.product_group == "Bundling Glow Up Tint & Over The Glaze"
        assert rec.clean_variant == "Active, Over Cute"
        assert rec.is_bundling is True
        assert rec.is_cross_bundling is True

    def test_normalize_power_frosted_space_short_pair(
        self, normalizer: VariantNormalizer
    ) -> None:
        # 2026-08-26 sample: 'Honest Smart' (space-joined short forms) must
        # resolve to the on-grid intra-family pair 'Honest + Smart'.
        raw = RawRecord(
            platform="TIKTOK_SHOP",
            product_title="Bundling Power Frosted Velvet Matte",
            raw_variant="Honest Smart",
            qty_sold=1,
            revenue=58700,
        )
        rec, _, _ = normalizer.normalize_single(raw)
        assert rec is not None
        assert rec.product_group == "Bundling Power Frosted Velvet Matte"
        assert rec.clean_variant == "Honest + Smart"
        assert rec.is_bundling is True
        assert rec.is_cross_bundling is False
        grid_keys = {(r.product_group, r.clean_variant) for r in generate_full_produk_grid()}
        assert (rec.product_group, rec.clean_variant) in grid_keys

    def test_normalize_cross_tjb_otg_drops_case_color(
        self, normalizer: VariantNormalizer
    ) -> None:
        # 2026-08-26 sample: a cross TJB-OTG bundle with a case colour must
        # report to the case-colour-free Produk 2 label ('Bunny Pink, Over
        # React'); case_color stays stored as SKU metadata only.
        raw = RawRecord(
            platform="TIKTOK_SHOP",
            product_title="Bundling Tinted Jelly Balm & Over The Glaze",
            raw_variant="Over React + Bunny Pink / Fizzy Pop",
            qty_sold=1,
            revenue=178770,
        )
        rec, _, _ = normalizer.normalize_single(raw)
        assert rec is not None
        assert rec.product_group == "Bundling Tinted Jelly Balm & Over The Glaze"
        assert rec.clean_variant == "Bunny Pink, Over React"
        assert rec.case_color == "Fizzy Pop"
        assert rec.is_bundling is True
        assert rec.is_cross_bundling is True
        grid_keys = {(r.product_group, r.clean_variant) for r in generate_full_produk2_grid()}
        assert (rec.product_group, rec.clean_variant) in grid_keys


class TestFoldBackEngine:
    """Test same-shade fold-back arithmetic, scoping, and duplicate aggregation."""

    def test_foldback_glow_up_tint_multiplication(self) -> None:
        engine = FoldBackEngine()
        records: list[tuple[VariantRecord, bool]] = [
            (
                VariantRecord(
                    platform="SHOPEE",
                    product_group="Glow Up Tint",
                    raw_variant="Dynamic, 05. Dynamic",
                    clean_variant="Dynamic",
                    is_bundling=True,
                    is_cross_bundling=False,
                    qty_sold=1,
                    revenue=139900,
                ),
                True,
            )
        ]
        result = engine.process_records(records)
        assert len(result) == 1
        assert result[0].clean_variant == "Dynamic"
        assert result[0].qty_sold == 2  # 1 * 2
        assert result[0].revenue == 139900  # 1x rev
        assert result[0].is_bundling is False

    def test_foldback_duplicate_aggregation(self) -> None:
        engine = FoldBackEngine()
        records: list[tuple[VariantRecord, bool]] = [
            (
                VariantRecord(
                    platform="SHOPEE",
                    product_group="Glow Up Tint",
                    raw_variant="Gorgeous, 08. Gorgeous",
                    clean_variant="Gorgeous",
                    is_bundling=True,
                    is_cross_bundling=False,
                    qty_sold=2,
                    revenue=200000,
                ),
                True,
            ),
            (
                VariantRecord(
                    platform="SHOPEE",
                    product_group="Glow Up Tint",
                    raw_variant="Gorgeous, 08. Gorgeous (Line 2)",
                    clean_variant="Gorgeous",
                    is_bundling=True,
                    is_cross_bundling=False,
                    qty_sold=3,
                    revenue=300000,
                ),
                True,
            ),
        ]
        result = engine.process_records(records)
        assert len(result) == 1
        assert result[0].clean_variant == "Gorgeous"
        assert result[0].qty_sold == (2 + 3) * 2  # 10
        assert result[0].revenue == 200000 + 300000  # 500000

    def test_foldback_unverified_family_raises(self) -> None:
        engine = FoldBackEngine()
        records: list[tuple[VariantRecord, bool]] = [
            (
                VariantRecord(
                    platform="SHOPEE",
                    product_group="Swipe To Glow",
                    raw_variant="Date, Date",
                    clean_variant="Date",
                    is_bundling=True,
                    is_cross_bundling=False,
                    qty_sold=1,
                    revenue=100000,
                ),
                True,
            )
        ]
        with pytest.raises(ValueError, match="unverified family"):
            engine.process_records(records)

    def test_foldback_allowed_families_empty_set_stays_empty(self) -> None:
        """R8: an explicit empty allow-list is respected, not replaced by
        the default family set."""
        engine = FoldBackEngine(allowed_families=set())
        assert engine.allowed_families == frozenset()


class TestFixedGridGenerator:
    """Test fixed grid generation, row counts, and sequence adherence."""

    def test_glow_up_tint_intra_grid_counts_and_order(self) -> None:
        rows = generate_intra_family_grid("Glow Up Tint")
        # 11 singles + 55 pairs = 66
        assert len(rows) == 66

        # Singles first
        singles = [r for r in rows if not r.is_bundling]
        assert len(singles) == 11
        assert singles[0].clean_variant == "Active"
        assert singles[-1].clean_variant == "Strong"

        # Check that Strong (09) precedes Happy (10) in pairs
        pairs = [r for r in rows if r.is_bundling]
        assert len(pairs) == 55

        # Active + Strong should precede Active + Happy
        labels = [p.clean_variant for p in pairs]
        assert "Active + Strong" in labels
        assert "Active + Happy" in labels
        assert labels.index("Active + Strong") < labels.index("Active + Happy")

    def test_full_produk_grid_has_181_rows(self) -> None:
        grid = generate_full_produk_grid()
        assert len(grid) == 181

    def test_cross_family_grid_counts(self) -> None:
        # GUT & OTG: 11 x 6 = 66
        gut_otg = generate_cross_family_grid("Glow Up Tint", "Over The Glaze")
        assert len(gut_otg) == 66
        assert gut_otg[0].clean_variant == "Active, Over Cute"

        # OTG & TJB with case colors: 6 x 6 x 3 = 108
        otg_tjb = generate_cross_family_grid(
            "Over The Glaze", "Tinted Jelly Balm", include_case_colors=True
        )
        assert len(otg_tjb) == 108
        assert otg_tjb[0].clean_variant == "Over Cute + Bunny Pink, Fizzy Pop"
        assert otg_tjb[0].case_color == "Fizzy Pop"


def _canonicalize_oracle_group(raw_group: str) -> str:
    """Normalizes raw family headers from the reference workbook to canonical group names."""
    g = raw_group.strip()
    if g == "PHA Glow Lip Exfoliant":
        return "Lip Exfoliant"
    if g == "PDRN Glow Lip Moist":
        return "Lip Moist"
    if g == "Sun Glow Protect Lip Sunscreen":
        return "Lip Sunscreen"
    if g in ("Bundling Lip Care", "Bundling Lipcare"):
        return "Bundling Lipcare"
    return g


class TestTransformationGoldenOracleMatch:
    """Integration test verifying exact numerical match against golden reference totals."""

    def test_shopee_transformation_against_golden_totals(
        self, raw_shopee_path, golden_totals
    ) -> None:
        _, raw_rows = extract_spreadsheet_rows(raw_shopee_path)
        shopee_adapter = ShopeeAdapter()
        raw_records = shopee_adapter.adapt(raw_rows)

        result = transform_records(raw_records)

        # Aggregate by (product_group, clean_variant)
        aggregated: dict[tuple[str, str], dict[str, int]] = {}
        for rec in result.records:
            key = (rec.product_group.rstrip(), rec.clean_variant.rstrip())
            if key not in aggregated:
                aggregated[key] = {"qty": 0, "revenue": 0}
            aggregated[key]["qty"] += rec.qty_sold
            aggregated[key]["revenue"] += rec.revenue

        # Verify golden oracle variants for Shopee
        expected_shopee = golden_totals["shopee_variants"]
        non_zero_expected = sum(
            1 for e in expected_shopee if e["qty"] > 0 or e["revenue"] > 0
        )
        current_family = ""
        matched_count = 0

        for expected in expected_shopee:
            if expected.get("family"):
                current_family = _canonicalize_oracle_group(expected["family"])
            variant_name = expected["variant"].rstrip()
            expected_qty = expected["qty"]
            expected_rev = expected["revenue"]
            key = (current_family, variant_name)
            actual = aggregated.get(key, {"qty": 0, "revenue": 0})

            if expected_qty > 0 or expected_rev > 0:
                assert actual["qty"] == expected_qty, (
                    f"Shopee Qty mismatch for {key}: expected {expected_qty}, got {actual['qty']}"
                )
                assert actual["revenue"] == expected_rev, (
                    f"Shopee Revenue mismatch for {key}: expected {expected_rev}, got {actual['revenue']}"
                )
                matched_count += 1
            else:
                # Golden reports zero for this variant: output must not fabricate volume.
                assert actual["qty"] == 0 and actual["revenue"] == 0, (
                    f"Shopee over-production for {key}: golden expects 0/0, "
                    f"got {actual['qty']}/{actual['revenue']}"
                )

        assert matched_count == non_zero_expected, (
            f"Matched {matched_count}/{non_zero_expected} non-zero Shopee variants"
        )

    def test_tiktok_transformation_against_golden_totals(
        self, raw_tts_path, golden_totals
    ) -> None:
        _, raw_rows = extract_spreadsheet_rows(raw_tts_path)
        tts_adapter = TikTokShopAdapter()
        raw_records = tts_adapter.adapt(raw_rows)

        result = transform_records(raw_records)

        # Aggregate by (product_group, clean_variant)
        aggregated: dict[tuple[str, str], dict[str, int]] = {}
        for rec in result.records:
            key = (rec.product_group.rstrip(), rec.clean_variant.rstrip())
            if key not in aggregated:
                aggregated[key] = {"qty": 0, "revenue": 0}
            aggregated[key]["qty"] += rec.qty_sold
            aggregated[key]["revenue"] += rec.revenue

        expected_tiktok = golden_totals["tiktok_variants"]
        non_zero_expected = sum(
            1 for e in expected_tiktok if e["qty"] > 0 or e["revenue"] > 0
        )
        current_family = ""
        matched_count = 0

        for expected in expected_tiktok:
            if expected.get("family"):
                current_family = _canonicalize_oracle_group(expected["family"])
            variant_name = expected["variant"].rstrip()
            expected_qty = expected["qty"]
            expected_rev = expected["revenue"]
            key = (current_family, variant_name)
            actual = aggregated.get(key, {"qty": 0, "revenue": 0})

            if expected_qty > 0 or expected_rev > 0:
                assert actual["qty"] == expected_qty, (
                    f"TikTok Qty mismatch for {key}: expected {expected_qty}, got {actual['qty']}"
                )
                assert actual["revenue"] == expected_rev, (
                    f"TikTok Revenue mismatch for {key}: expected {expected_rev}, got {actual['revenue']}"
                )
                matched_count += 1
            else:
                # Golden reports zero for this variant: output must not fabricate volume.
                assert actual["qty"] == 0 and actual["revenue"] == 0, (
                    f"TikTok over-production for {key}: golden expects 0/0, "
                    f"got {actual['qty']}/{actual['revenue']}"
                )

        assert matched_count == non_zero_expected, (
            f"Matched {matched_count}/{non_zero_expected} non-zero TikTok variants"
        )

    def test_shopee_revenue_is_conserved_through_transform(
        self, raw_shopee_path
    ) -> None:
        """Adapter -> transform conserves total revenue byte-for-byte.

        Fold-back applies 1x revenue and 2x quantity, so revenue must never
        leak or be fabricated anywhere in the pipeline (review item 4.4).
        """
        _, raw_rows = extract_spreadsheet_rows(raw_shopee_path)
        raw_records = ShopeeAdapter().adapt(raw_rows)
        result = transform_records(raw_records)

        assert sum(r.revenue for r in result.records) == sum(
            r.revenue for r in raw_records
        ), "Shopee revenue leaked or was fabricated through transformation"

    def test_tiktok_revenue_is_conserved_through_transform(
        self, raw_tts_path
    ) -> None:
        """Adapter -> transform conserves total revenue byte-for-byte on TikTok."""
        _, raw_rows = extract_spreadsheet_rows(raw_tts_path)
        raw_records = TikTokShopAdapter().adapt(raw_rows)
        result = transform_records(raw_records)

        assert sum(r.revenue for r in result.records) == sum(
            r.revenue for r in raw_records
        ), "TikTok revenue leaked or was fabricated through transformation"

    def test_tiktok_aug26_offgrid_corrections(self, raw_tts_aug_path) -> None:
        """2026-08-26 sample: the previously-unreported 'Honest Smart' and
        cross TJB-OTG case-colour rows are now classified as reported.

        'Honest Smart' -> 'Bundling Power Frosted Velvet Matte / Honest + Smart'
        and 'Over React + Bunny Pink / Fizzy Pop' ->
        'Bundling Tinted Jelly Balm & Over The Glaze / Bunny Pink, Over React'
        (case colour dropped from the Produk 2 label). Both pairs must land on
        their catalog grid so the persistence boundary reports them.
        """
        _, raw_rows = extract_spreadsheet_rows(raw_tts_aug_path)
        result = transform_records(TikTokShopAdapter().adapt(raw_rows))

        aggregated: dict[tuple[str, str], dict[str, int]] = {}
        for rec in result.records:
            key = (rec.product_group.rstrip(), rec.clean_variant.rstrip())
            entry = aggregated.setdefault(key, {"qty": 0, "revenue": 0})
            entry["qty"] += rec.qty_sold
            entry["revenue"] += rec.revenue

        pfvm_pair = aggregated.get(
            ("Bundling Power Frosted Velvet Matte", "Honest + Smart")
        )
        assert pfvm_pair == {"qty": 1, "revenue": 58700}, pfvm_pair

        tjb_otg_pair = aggregated.get(
            ("Bundling Tinted Jelly Balm & Over The Glaze", "Bunny Pink, Over React")
        )
        assert tjb_otg_pair == {"qty": 1, "revenue": 178770}, tjb_otg_pair

        # Both clean keys must be on their respective catalog grids (reported).
        grid1 = {(r.product_group, r.clean_variant) for r in generate_full_produk_grid()}
        grid2 = {(r.product_group, r.clean_variant) for r in generate_full_produk2_grid()}
        assert ("Bundling Power Frosted Velvet Matte", "Honest + Smart") in grid1
        assert ("Bundling Tinted Jelly Balm & Over The Glaze", "Bunny Pink, Over React") in grid2

        # No record retains the buggy case-colour-suffixed cross label.
        assert not any(
            rec.clean_variant.rstrip().endswith(", Fizzy Pop") for rec in result.records
        )
