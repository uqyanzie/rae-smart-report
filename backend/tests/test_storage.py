"""Integration tests for SQLite persistence, analytical CTE queries, and grid population.

Golden numbers referenced below are read from ``fixtures/golden_totals.json``
(the reference-workbook oracle), e.g. ``active_contribution_ratio``,
``shopee_summary_groups`` and the Shopee variant rows for Tinted Jelly Balm.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.domain.models import VariantRecord
from app.modules.ingestion.reader import extract_spreadsheet_rows
from app.modules.profiler.adapters import ShopeeAdapter, TikTokShopAdapter
from app.modules.storage import AnalyticsRepository, SkippedTally
from app.modules.storage.database import init_db, session_scope
from app.modules.storage.models import TransactionItem
from app.modules.transformer import (
    generate_full_produk2_grid,
    generate_full_produk_grid,
    transform_records,
)

PERIOD_START = datetime(2026, 7, 13)
PERIOD_END = datetime(2026, 7, 19, 23, 59, 59)
BATCH_SHOPEE = "SHOPEE-2026-07-13-19"
BATCH_TIKTOK = "TIKTOK-2026-07-13-19"

GOLDEN_ACTIVE_RATIO = 0.05974791292
GOLDEN_TJB_QTY = 24
GOLDEN_TJB_REVENUE = 2_234_703
GOLDEN_STG_QTY = 72
GOLDEN_STG_REVENUE = 6_094_067
GOLDEN_BUNDLING_STG_QTY = 5
GOLDEN_BUNDLING_STG_REVENUE = 747_485
GOLDEN_ACTIVE_QTY = 365
GOLDEN_GUT_QTY = 6_109

SHOPEE_SKIPPED_COUNT = 180
SHOPEE_SKIPPED_QTY = 1
SHOPEE_SKIPPED_REVENUE = 4_950

TJB_SHADES = {
    "Bunny Pink",
    "Wild Mauve",
    "Nudy Caramel",
    "Spill Nude",
    "Red Babe",
    "Hippie Rose",
}


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    init_db(eng)
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="module")
def shopee_result(raw_shopee_path):
    _, raw_rows = extract_spreadsheet_rows(raw_shopee_path)
    return transform_records(ShopeeAdapter().adapt(raw_rows))


@pytest.fixture(scope="module")
def tiktok_result(raw_tts_path):
    _, raw_rows = extract_spreadsheet_rows(raw_tts_path)
    return transform_records(TikTokShopAdapter().adapt(raw_rows))


@pytest.fixture(scope="module")
def persisted(factory, shopee_result, tiktok_result):
    """Persists both reference-period batches once; returns the PersistResults."""
    with session_scope(factory) as session:
        repo = AnalyticsRepository(session)
        shopee = repo.persist_batch(
            BATCH_SHOPEE, "SHOPEE", PERIOD_START, PERIOD_END, shopee_result.records
        )
        tiktok = repo.persist_batch(
            BATCH_TIKTOK,
            "TIKTOK_SHOP",
            PERIOD_START,
            PERIOD_END,
            tiktok_result.records,
        )
    return {"shopee": shopee, "tiktok": tiktok}


def _repo(factory):
    session = factory()
    return AnalyticsRepository(session), session


# ---------------------------------------------------------------------------
# Ignorable-token warning channel (plan item: register TJB case-colour tokens)
# ---------------------------------------------------------------------------


def test_warning_counts_after_ignorable_tokens(shopee_result, tiktok_result):
    """Shopee warnings drop 220 -> 184 (180 dash + 4 residual '2' quantity
    prefixes not covered by the enumerated token list); TikTok 15 -> 0."""
    shopee_warnings = shopee_result.warnings
    assert len(shopee_warnings) == 184

    dash_class = [w for w in shopee_warnings if w.raw_variant.strip() == "-"]
    residual = [w for w in shopee_warnings if w.raw_variant.strip() != "-"]
    assert len(dash_class) == 180
    assert len(residual) == 4
    assert all(w.unmapped_tokens == ("2",) for w in residual)

    assert tiktok_result.warnings == []


# ---------------------------------------------------------------------------
# Persistence boundary: golden-file scope exclusion (Execution Rule 2)
# ---------------------------------------------------------------------------


def test_skipped_unreported_tally(shopee_result, persisted):
    """The auditable excluded-volume tally reports exactly 180 Shopee
    exclusions (qty 1, Rp 4,950) and TikTok's single off-grid orphan
    (qty 1, Rp 22,637)."""
    shopee = persisted["shopee"]
    assert shopee.skipped_unreported == SkippedTally(
        count=SHOPEE_SKIPPED_COUNT,
        qty=SHOPEE_SKIPPED_QTY,
        revenue=SHOPEE_SKIPPED_REVENUE,
    )

    # Reason breakdown must sum back to the combined tally (audit invariant).
    breakdown = (
        shopee.skipped_dash_variant + shopee.skipped_unresolved_group + shopee.skipped_off_grid
    )
    assert breakdown == shopee.skipped_unreported
    # Out-of-catalog products (Body Toner, Face Toner, Lippie Serum, Blurring
    # Powder, deleted listings) carry zero revenue this period.
    assert shopee.skipped_unresolved_group.revenue == 0
    assert shopee.skipped_unresolved_group.count == 13
    assert shopee.skipped_dash_variant.count == 167
    # R7 keeps Shopee's only off-grid pair on-grid ('Over Cute + Lovie'), so
    # the off-grid bucket stays empty for Shopee.
    assert shopee.skipped_off_grid == SkippedTally(0, 0, 0)

    tiktok = persisted["tiktok"]
    assert tiktok.skipped_unreported == SkippedTally(1, 1, 22_637)
    assert tiktok.skipped_off_grid == SkippedTally(1, 1, 22_637)
    assert tiktok.skipped_dash_variant == SkippedTally(0, 0, 0)
    assert tiktok.skipped_unresolved_group == SkippedTally(0, 0, 0)

    # Transform-level cross-check: 180 dash-variant records exist pre-persist.
    transform_dash = [
        r
        for r in shopee_result.records
        if r.clean_variant.strip() in ("-", "")
    ]
    assert len(transform_dash) == SHOPEE_SKIPPED_COUNT
    assert sum(r.qty_sold for r in transform_dash) == SHOPEE_SKIPPED_QTY
    assert sum(r.revenue for r in transform_dash) == SHOPEE_SKIPPED_REVENUE


# ---------------------------------------------------------------------------
# Query A: variant-level analytics (never groups by case_color)
# ---------------------------------------------------------------------------


def test_query_a_active_contribution_ratio(factory, persisted):
    """Query A returns the golden Active contribution ratio to 11 dp."""
    repo, session = _repo(factory)
    try:
        rows = repo.variant_analytics(BATCH_SHOPEE, is_cross_bundling=0)
    finally:
        session.close()

    by_key = {(r["product_group"], r["clean_variant"]): r for r in rows}
    active = by_key[("Glow Up Tint", "Active")]
    assert active["total_qty"] == GOLDEN_ACTIVE_QTY
    assert round(active["contribution_ratio"], 11) == GOLDEN_ACTIVE_RATIO


def test_query_a_glow_up_tint_ratios_sum_to_one(factory, persisted):
    """Variant ratios within Glow Up Tint partition the group total: sum == 1.0."""
    repo, session = _repo(factory)
    try:
        rows = repo.variant_analytics(BATCH_SHOPEE, is_cross_bundling=0)
    finally:
        session.close()

    gut = [r for r in rows if r["product_group"] == "Glow Up Tint"]
    assert len(gut) == 11  # one row per canonical shade, none split by case color
    assert sum(r["total_qty"] for r in gut) == GOLDEN_GUT_QTY
    assert sum(r["contribution_ratio"] for r in gut) == 1.0


def test_query_a_tinted_jelly_balm_six_shade_rows(factory, persisted):
    """Tinted Jelly Balm aggregates to exactly 6 shade rows (qty 24,
    revenue 2,234,703): case color never splits a row."""
    repo, session = _repo(factory)
    try:
        rows = repo.variant_analytics(BATCH_SHOPEE, is_cross_bundling=0)
    finally:
        session.close()

    tjb = [r for r in rows if r["product_group"] == "Tinted Jelly Balm"]
    assert len(tjb) == 6
    assert {r["clean_variant"] for r in tjb} == TJB_SHADES
    assert sum(r["total_qty"] for r in tjb) == GOLDEN_TJB_QTY
    assert sum(r["total_revenue"] for r in tjb) == GOLDEN_TJB_REVENUE


def test_query_a_ratio_no_fanout_on_untrimmed_group(factory, persisted):
    """R3: untrimmed group keys inserted directly via ORM must not fan out.

    Query A's CTE, join, and GROUP BY are rtrim()-normalized, so two
    spellings of one group collapse to two rows whose ratios sum to 1.0.
    """
    _, session = _repo(factory)
    try:
        session.add_all(
            [
                TransactionItem(
                    id=str(uuid4()),
                    import_batch_id="R3-BATCH",
                    platform="SHOPEE",
                    product_group="Swipe To Glow",
                    raw_variant="Date",
                    clean_variant="Date",
                    is_bundling=False,
                    is_cross_bundling=False,
                    qty_sold=10,
                    revenue=600_000,
                ),
                TransactionItem(
                    id=str(uuid4()),
                    import_batch_id="R3-BATCH",
                    platform="SHOPEE",
                    # Trailing space survives a direct ORM insert (persist_batch
                    # strips keys, so this only happens bypassing it).
                    product_group="Swipe To Glow ",
                    raw_variant="Work",
                    clean_variant="Work",
                    is_bundling=False,
                    is_cross_bundling=False,
                    qty_sold=5,
                    revenue=300_000,
                ),
            ]
        )
        session.commit()
    finally:
        session.close()

    repo, session = _repo(factory)
    try:
        rows = repo.variant_analytics("R3-BATCH", is_cross_bundling=0)
    finally:
        session.close()

    assert len(rows) == 2
    assert all(r["product_group"] == "Swipe To Glow" for r in rows)
    by_variant = {r["clean_variant"]: r for r in rows}
    assert by_variant["Date"]["total_qty"] == 10
    assert by_variant["Work"]["total_qty"] == 5
    assert by_variant["Date"]["contribution_ratio"] == 10 / 15
    assert by_variant["Work"]["contribution_ratio"] == 5 / 15
    assert sum(r["contribution_ratio"] for r in rows) == 1.0

    # Clean up: R3-BATCH carries deliberately dirty keys that would otherwise
    # pollute the whole-table hygiene tests later in this module.
    _, session = _repo(factory)
    try:
        session.execute(delete(TransactionItem).where(TransactionItem.import_batch_id == "R3-BATCH"))
        session.commit()
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Persisted-key hygiene (report-key whitespace normalization)
# ---------------------------------------------------------------------------


def test_no_dash_or_whitespace_keys_persisted(factory, persisted):
    """No persisted clean_variant in ('-', ''); no product_group or
    clean_variant carries leading/trailing whitespace."""
    _, session = _repo(factory)
    try:
        n_dash = session.execute(
            select(func.count())
            .select_from(TransactionItem)
            .where(TransactionItem.clean_variant.in_(["-", ""]))
        ).scalar_one()
        assert n_dash == 0

        n_ws = session.execute(
            select(func.count())
            .select_from(TransactionItem)
            .where(
                (TransactionItem.product_group != func.rtrim(TransactionItem.product_group))
                | (TransactionItem.clean_variant != func.rtrim(TransactionItem.clean_variant))
            )
        ).scalar_one()
        assert n_ws == 0
    finally:
        session.close()


def test_swipe_to_glow_singles_join_clean_grid_group(factory, persisted, shopee_result, tiktok_result):
    """The plan's 75 Swipe To Glow singles (64 Shopee + 11 TikTok) at transform
    level include 13 '-' parent rows (qty 0, rev 0) excluded by the scope
    boundary, so 62 persisted singles land under the grid's clean group."""
    _, session = _repo(factory)
    try:
        n_stg = session.execute(
            select(func.count())
            .select_from(TransactionItem)
            .where(
                TransactionItem.product_group == "Swipe To Glow",
                TransactionItem.is_bundling.is_(False),
                TransactionItem.is_cross_bundling.is_(False),
            )
        ).scalar_one()
    finally:
        session.close()
    assert n_stg == 62

    def stg_singles(result):
        return [
            r
            for r in result.records
            if r.product_group.strip() == "Swipe To Glow"
            and not r.is_bundling
            and not r.is_cross_bundling
        ]

    transform_singles = stg_singles(shopee_result) + stg_singles(tiktok_result)
    assert len(transform_singles) == 75
    assert sum(1 for r in transform_singles if r.clean_variant.strip() in ("-", "")) == 13
    assert sum(1 for r in transform_singles if r.clean_variant.strip() not in ("-", "")) == 62


# ---------------------------------------------------------------------------
# Left-join grid population
# ---------------------------------------------------------------------------


def test_grid_population_preserves_all_rows_and_stg_totals(factory, persisted):
    """The 181-row catalog grid left-joins onto persisted aggregates: every
    row present with coalesced 0 defaults, and the Swipe To Glow / Bundling
    Swipe To Glow groups match the golden totals."""
    repo, session = _repo(factory)
    try:
        rows = repo.populate_grid(BATCH_SHOPEE, is_cross_bundling=0)
    finally:
        session.close()

    assert len(rows) == 181
    assert all(r["total_qty"] >= 0 and r["total_revenue"] >= 0 for r in rows)
    # Grid keys round-trip cleanly: no whitespace introduced by the join.
    assert all(
        r["product_group"] == r["product_group"].strip()
        and r["clean_variant"] == r["clean_variant"].strip()
        for r in rows
    )

    by_group = {}
    for row in rows:
        by_group.setdefault(row["product_group"], []).append(row)

    stg = by_group["Swipe To Glow"]
    assert len(stg) == 6
    assert sum(r["total_qty"] for r in stg) == GOLDEN_STG_QTY
    assert sum(r["total_revenue"] for r in stg) == GOLDEN_STG_REVENUE

    bundling_stg = by_group["Bundling Swipe To Glow"]
    assert len(bundling_stg) == 15  # C(6,2) intra-family pairs
    assert sum(r["total_qty"] for r in bundling_stg) == GOLDEN_BUNDLING_STG_QTY
    assert sum(r["total_revenue"] for r in bundling_stg) == GOLDEN_BUNDLING_STG_REVENUE

    # Every persisted (group, variant) key with sales lands on a grid row.
    grid_keys = {(r["product_group"], r["clean_variant"]) for r in rows}
    _, session2 = _repo(factory)
    try:
        sold_keys = set(
            session2.execute(
                select(TransactionItem.product_group, TransactionItem.clean_variant).where(
                    TransactionItem.import_batch_id == BATCH_SHOPEE,
                    TransactionItem.is_cross_bundling.is_(False),
                    TransactionItem.qty_sold > 0,
                )
            ).all()
        )
    finally:
        session2.close()
    assert sold_keys.issubset(grid_keys)


def test_reconciliation_grid_plus_skipped_equals_transform(
    factory, persisted, shopee_result, tiktok_result
):
    """R1 acceptance: grid qty + grid2 qty + skipped == transform records.

    For both reference batches, every sheet's grid rows plus every skipped
    tally equals the transform-level totals exactly -- nothing leaks past the
    audit boundary -- and the same holds for revenue.
    """
    repo, session = _repo(factory)
    try:
        for batch_id, result, persist_result in (
            (BATCH_SHOPEE, shopee_result, persisted["shopee"]),
            (BATCH_TIKTOK, tiktok_result, persisted["tiktok"]),
        ):
            grid0 = repo.populate_grid(
                batch_id, is_cross_bundling=0, grid=generate_full_produk_grid()
            )
            grid1 = repo.populate_grid(
                batch_id, is_cross_bundling=1, grid=generate_full_produk2_grid()
            )
            grid_qty = sum(r["total_qty"] for r in grid0) + sum(
                r["total_qty"] for r in grid1
            )
            grid_rev = sum(r["total_revenue"] for r in grid0) + sum(
                r["total_revenue"] for r in grid1
            )
            rec_qty = sum(r.qty_sold for r in result.records)
            rec_rev = sum(r.revenue for r in result.records)
            assert grid_qty + persist_result.skipped_unreported.qty == rec_qty
            assert grid_rev + persist_result.skipped_unreported.revenue == rec_rev
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Query B: product group summary
# ---------------------------------------------------------------------------


def test_query_b_product_group_summary(factory, persisted):
    """Group-level rollup reproduces the golden Swipe To Glow / TJB rows."""
    repo, session = _repo(factory)
    try:
        rows = repo.product_group_summary(BATCH_SHOPEE, is_cross_bundling=0)
    finally:
        session.close()

    by_group = {r["product_group"]: r for r in rows}
    stg = by_group["Swipe To Glow"]
    assert stg["total_qty"] == GOLDEN_STG_QTY
    assert stg["total_revenue"] == GOLDEN_STG_REVENUE

    tjb = by_group["Tinted Jelly Balm"]
    assert tjb["total_qty"] == GOLDEN_TJB_QTY
    assert tjb["total_revenue"] == GOLDEN_TJB_REVENUE

    # Shares partition the grand total: sum of ratios == 1.0 (to 12 dp).
    assert round(sum(r["contribution_ratio"] for r in rows), 12) == 1.0


# ---------------------------------------------------------------------------
# Query C: multi-platform / date-range aggregation
# ---------------------------------------------------------------------------


def test_query_c_multi_platform_and_date_range(factory, persisted):
    """Unfiltered aggregation spans both platforms; date-range and platform
    filters narrow correctly."""
    repo, session = _repo(factory)
    try:
        all_rows = repo.multi_platform_aggregation()
        by_key = {
            (r["platform"], r["product_group"], r["clean_variant"]): r
            for r in all_rows
        }
        active_shopee = by_key[("SHOPEE", "Glow Up Tint", "Active")]
        assert active_shopee["total_qty"] == GOLDEN_ACTIVE_QTY

        platforms = {r["platform"] for r in all_rows}
        assert platforms == {"SHOPEE", "TIKTOK_SHOP"}

        # R9: a bare end-of-day datetime and a bare date both resolve to an
        # inclusive upper bound (23:59:59.999999), so the full period matches.
        for end in (
            datetime(2026, 7, 19, 23, 59, 59),
            datetime(2026, 7, 19).date(),
        ):
            period_rows = repo.multi_platform_aggregation(
                start_date=PERIOD_START, end_date=end
            )
            assert len(period_rows) == len(all_rows)

        # Platform filter -> only that platform's rows.
        shopee_rows = repo.multi_platform_aggregation(platform="SHOPEE")
        assert len(shopee_rows) > 0
        assert all(r["platform"] == "SHOPEE" for r in shopee_rows)
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Query D: batch history
# ---------------------------------------------------------------------------


def test_query_d_batch_history(factory, persisted):
    """Both reference-period batches appear with correct platform/period/volume."""
    repo, session = _repo(factory)
    try:
        rows = repo.batch_history()
    finally:
        session.close()

    by_batch = {r["import_batch_id"]: r for r in rows}
    shopee = by_batch[BATCH_SHOPEE]
    assert shopee["platform"] == "SHOPEE"
    assert shopee["period_start"] == PERIOD_START
    assert shopee["period_end"] == PERIOD_END
    assert shopee["grand_total_qty"] == 6_917
    assert shopee["grand_total_revenue"] == 526_984_429

    tiktok = by_batch[BATCH_TIKTOK]
    assert tiktok["platform"] == "TIKTOK_SHOP"
    # R1: the Tinted Jelly Balm 'Default' orphan (qty 1, rev 22,637) is now
    # excluded at the persistence boundary, so stored totals drop accordingly.
    assert tiktok["grand_total_qty"] == 11_588
    assert tiktok["grand_total_revenue"] == 660_510_387


# ---------------------------------------------------------------------------
# Query E: batch deletion
# ---------------------------------------------------------------------------


def test_query_e_delete_batch(factory, persisted):
    """Deleting a batch removes exactly its rows and it disappears from history."""
    repo, session = _repo(factory)
    try:
        _ = repo.persist_batch(
            "DEL-BATCH",
            "SHOPEE",
            PERIOD_START,
            PERIOD_END,
            [
                VariantRecord(
                    platform="SHOPEE",
                    product_group="Glow Up Tint",
                    raw_variant="05. Active",
                    clean_variant="Active",
                    is_bundling=False,
                    is_cross_bundling=False,
                    qty_sold=2,
                    revenue=150_000,
                ),
                VariantRecord(
                    platform="SHOPEE",
                    product_group="Swipe To Glow",
                    raw_variant="Brunch",
                    clean_variant="Brunch",
                    is_bundling=False,
                    is_cross_bundling=False,
                    qty_sold=1,
                    revenue=60_000,
                ),
            ],
        )
        deleted = repo.delete_batch("DEL-BATCH")
        assert deleted == 2

        remaining = session.execute(
            select(func.count())
            .select_from(TransactionItem)
            .where(TransactionItem.import_batch_id == "DEL-BATCH")
        ).scalar_one()
        assert remaining == 0
        assert all(
            r["import_batch_id"] != "DEL-BATCH" for r in repo.batch_history()
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Mapping template cache (Query F)
# ---------------------------------------------------------------------------


def test_mapping_template_save_and_lookup(factory, persisted):
    """Cached mapping templates upsert by header signature hash."""
    repo, session = _repo(factory)
    try:
        template_id = repo.save_mapping_template(
            "SHOPEE",
            "deadbeef1234",
            '{"Produk": "product_group"}',
            cleaning_rules_json='{"rule": "strip"}',
        )
        assert template_id
        loaded = repo.get_mapping_template("deadbeef1234")
        assert loaded is not None
        assert loaded["platform_name"] == "SHOPEE"
        assert loaded["column_mapping_json"] == '{"Produk": "product_group"}'
        assert loaded["cleaning_rules_json"] == '{"rule": "strip"}'

        # Upsert path keeps the same id.
        _ = repo.save_mapping_template(
            "SHOPEE", "deadbeef1234", '{"Produk": "product_group_v2"}'
        )
        updated = repo.get_mapping_template("deadbeef1234")
        assert updated is not None
        assert updated["column_mapping_json"] == '{"Produk": "product_group_v2"}'
    finally:
        session.close()
