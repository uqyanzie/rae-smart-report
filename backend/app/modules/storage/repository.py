"""Analytical CTE repository: persistence boundary and on-demand report queries.

All aggregation happens in SQLite SQL (zero LLM math). Report keys are
rtrim()-normalized on both sides of every comparison/join (rae-report-template
rule 7) as defense-in-depth; the persist boundary already strips keys, so the
grid left-join always matches the catalog grid vocabulary.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, time
from itertools import combinations
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.domain.catalog import CROSS_PAIRABLE_FAMILY_NAMES, PRODUK_GROUP_ORDER
from app.domain.models import GridRow, VariantRecord
from app.modules.storage.models import MappingTemplate, TransactionItem
from app.modules.transformer.grid import generate_full_produk2_grid, generate_full_produk_grid

__all__ = [
    "AnalyticsRepository",
    "PersistResult",
    "SkippedTally",
]

# Canonical catalog groups: the 16 PRODUK_GROUP_ORDER entries plus every
# cross-family "Bundling A & B" group the normalizer can emit. Cross groups pair
# only the six Bundling Silang families (C(6,2) = 15); Lipcare is a Produk-sheet
# family only and never appears in a cross group.
_CANONICAL_GROUPS: frozenset[str] = frozenset(
    {group.strip() for group in PRODUK_GROUP_ORDER}
    | {
        f"Bundling {family_a} & {family_b}"
        for family_a, family_b in combinations(CROSS_PAIRABLE_FAMILY_NAMES, 2)
    }
)

# Catalog grid keys, indexed by report boundary. persist_batch rejects rows
# whose (product_group, clean_variant) pair lands on no grid row (R1): the
# grid left-join silently swallows such rows, so the tally must catch them at
# the persistence boundary instead of letting them vanish.
_PRODUK_GRID_KEYS: frozenset[tuple[str, str]] = frozenset(
    (row.product_group, row.clean_variant) for row in generate_full_produk_grid()
)
_PRODUK2_GRID_KEYS: frozenset[tuple[str, str]] = frozenset(
    (row.product_group, row.clean_variant) for row in generate_full_produk2_grid()
)

# -- Query A: Variant-level performance & contribution ratio (Table 1) -------
# Groups by (product_group, clean_variant) ONLY. case_color is deliberately
# excluded: Tinted Jelly Balm totals are reported by shade across all case
# colours (verified: golden 'Bunny Pink' = 15 units spanning four case colours
# as ONE row). contribution_ratio is a 0-1 unit share (quantity based).
_QUERY_A_VARIANT_ANALYTICS = """
WITH product_totals AS (
    SELECT
        rtrim(product_group) AS product_group,
        SUM(qty_sold) AS total_product_qty
    FROM transaction_items
    WHERE import_batch_id = :batch_id
      AND is_cross_bundling = :is_cross_bundling
      AND (:is_bundling IS NULL OR is_bundling = :is_bundling)
      AND is_reported = 1
    GROUP BY rtrim(product_group)
)
SELECT
    rtrim(t.product_group) AS product_group,
    t.clean_variant,
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
JOIN product_totals pt ON rtrim(t.product_group) = pt.product_group
WHERE t.import_batch_id = :batch_id
  AND t.is_cross_bundling = :is_cross_bundling
  AND (:is_bundling IS NULL OR t.is_bundling = :is_bundling)
  AND t.is_reported = 1
GROUP BY rtrim(t.product_group), t.clean_variant, t.is_bundling, t.is_cross_bundling,
         pt.total_product_qty
ORDER BY t.product_group ASC, t.is_bundling ASC, total_qty DESC
"""

# -- Query B: Master product group summary (Table 2) -------------------------
# Group-level rollup: neither clean_variant nor case_color participates.
_QUERY_B_PRODUCT_GROUP_SUMMARY = """
WITH grand_total AS (
    SELECT COALESCE(SUM(qty_sold), 0) AS grand_qty
    FROM transaction_items
    WHERE import_batch_id = :batch_id
      AND is_cross_bundling = :is_cross_bundling
      AND (:is_bundling IS NULL OR is_bundling = :is_bundling)
      AND is_reported = 1
)
SELECT
    rtrim(product_group) AS product_group,
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
  AND (:is_bundling IS NULL OR is_bundling = :is_bundling)
  AND is_reported = 1
GROUP BY rtrim(product_group)
ORDER BY total_qty DESC
"""

# -- Query C: Multi-batch / date-range multi-platform aggregation ------------
# case_color excluded from the grouping key, same rule as Query A.
_QUERY_C_MULTI_PLATFORM = """
WITH grand_total AS (
    SELECT COALESCE(SUM(qty_sold), 0) AS grand_qty
    FROM transaction_items
    WHERE (:platform IS NULL OR platform = :platform)
      AND (:start_date IS NULL OR period_start >= :start_date)
      AND (:end_date IS NULL OR period_end <= :end_date)
      AND (:is_cross_bundling IS NULL OR is_cross_bundling = :is_cross_bundling)
      AND is_reported = 1
)
SELECT
    platform,
    rtrim(product_group) AS product_group,
    clean_variant,
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
  AND is_reported = 1
GROUP BY platform, rtrim(product_group), clean_variant
ORDER BY total_qty DESC
"""

# -- Query D: Batch history & upload overview --------------------------------
# ORDER BY uses the aggregate, not a bare non-grouped column. Only reported
# rows (is_reported = 1) count toward grand totals -- persisted unreported
# entries never inflate the batch-list figures.
_QUERY_D_BATCH_HISTORY = """
SELECT
    import_batch_id,
    platform,
    MIN(period_start) AS period_start,
    MAX(period_end) AS period_end,
    COUNT(DISTINCT rtrim(product_group)) AS total_products,
    SUM(qty_sold) AS grand_total_qty,
    SUM(revenue) AS grand_total_revenue,
    MIN(created_at) AS created_at
FROM transaction_items
WHERE is_reported = 1
GROUP BY import_batch_id, platform
ORDER BY MIN(created_at) DESC
"""

# -- Query E: Delete import batch --------------------------------------------
_QUERY_E_DELETE_BATCH = """
DELETE FROM transaction_items
WHERE import_batch_id = :batch_id
"""

# -- Query G: Persisted unreported breakdown ---------------------------------
# is_reported = 0 rows only: off-grid variants (standalone 'tidak boleh ecer',
# 'free gift', etc.) and non-catalog product groups. raw_variant and
# raw_product are carried so the UI/export can show full provenance back to
# the original spreadsheet row.
_QUERY_G_UNREPORTED = """
SELECT
    rtrim(product_group) AS product_group,
    clean_variant,
    raw_variant,
    raw_product,
    SUM(qty_sold) AS total_qty,
    SUM(revenue) AS total_revenue
FROM transaction_items
WHERE import_batch_id = :batch_id
  AND is_reported = 0
GROUP BY rtrim(product_group), clean_variant, raw_variant, raw_product
ORDER BY total_qty DESC, total_revenue DESC
"""

# -- Query F: Lookup mapping template by header signature hash ---------------
_QUERY_F_TEMPLATE_LOOKUP = """
SELECT platform_name, column_mapping_json, cleaning_rules_json, parent_row_rule_json
FROM mapping_templates
WHERE header_signature_hash = :signature_hash
"""

# -- Query H: Per-case-colour cross-family aggregation (opt-in export view) ---
# Aggregates reported cross rows to (product_group, clean_variant, case_color)
# grain so populate_grid can attach them onto the per-case-colour Produk 2
# rows (include_case_colors=True). Colour-less rows keep an empty case key and
# land on the shade pair's plain catch-all row.
_QUERY_CASE_COLOR_CROSS_AGG = """
SELECT
    rtrim(product_group) AS product_group,
    clean_variant,
    COALESCE(case_color, '') AS case_color,
    SUM(qty_sold) AS total_qty,
    SUM(revenue) AS total_revenue
FROM transaction_items
WHERE import_batch_id = :batch_id
  AND is_cross_bundling = 1
  AND is_reported = 1
GROUP BY rtrim(product_group), clean_variant, COALESCE(case_color, '')
"""

# -- Grid population: catalog grid left-joined onto persisted aggregates -----
# Placeholders are generated per grid row (5 fields each); named params only
# (SQLAlchemy text() does not bind positional '?' placeholders).
_GRID_LEFT_JOIN_TEMPLATE = """
WITH grid_rows(product_group, clean_variant, is_bundling, is_cross_bundling,
               expected_label) AS (
    VALUES {placeholders}
)
SELECT
    g.product_group,
    g.clean_variant,
    g.is_bundling,
    g.is_cross_bundling,
    g.expected_label,
    COALESCE(SUM(t.qty_sold), 0) AS total_qty,
    COALESCE(SUM(t.revenue), 0) AS total_revenue
FROM grid_rows g
LEFT JOIN transaction_items t
    ON rtrim(g.product_group) = rtrim(t.product_group)
   AND rtrim(g.clean_variant) = rtrim(t.clean_variant)
   AND t.import_batch_id = :batch_id
   AND t.is_cross_bundling = :is_cross_bundling
   AND t.is_reported = 1
GROUP BY g.product_group, g.clean_variant, g.is_bundling, g.is_cross_bundling,
         g.expected_label
ORDER BY g.product_group ASC, g.is_bundling ASC, g.clean_variant ASC
"""


@dataclass(frozen=True)
class SkippedTally:
    """Auditable excluded-volume tally (count / qty / revenue)."""

    count: int = 0
    qty: int = 0
    revenue: int = 0

    def __add__(self, other: SkippedTally) -> SkippedTally:
        return SkippedTally(
            count=self.count + other.count,
            qty=self.qty + other.qty,
            revenue=self.revenue + other.revenue,
        )


@dataclass(frozen=True)
class PersistResult:
    """Outcome of a persistence call (inserted rows + audit tallies).

    ``inserted_count`` counts every persisted row (reported + unreported).
    ``inserted_reported`` is the volume that participates in report queries.
    ``persisted_unreported`` (split into ``unreported_off_grid`` /
    ``unreported_unresolved_group``) is the volume stored for traceability but
    excluded from every report figure (Phase 7, DevelopmentFeedback20260826).
    ``skipped_dash_variant`` is the only truly-dropped bucket: dash/empty
    parent rows within catalog groups.
    """

    import_batch_id: str
    inserted_count: int = 0
    inserted_reported: SkippedTally = field(default_factory=SkippedTally)
    persisted_unreported: SkippedTally = field(default_factory=SkippedTally)
    unreported_off_grid: SkippedTally = field(default_factory=SkippedTally)
    unreported_unresolved_group: SkippedTally = field(default_factory=SkippedTally)
    skipped_dash_variant: SkippedTally = field(default_factory=SkippedTally)


class AnalyticsRepository:
    """Persistence boundary + analytical CTE queries over ``transaction_items``."""

    def __init__(self, session: Session) -> None:
        self._session: Session = session

    # ------------------------------------------------------------------
    # Persistence boundary (golden-file scope exclusion, Execution Rule 2)
    # ------------------------------------------------------------------

    @staticmethod
    def is_catalog_resolvable(product_group: str) -> bool:
        """True when the report key resolves to a canonical catalog group."""
        return product_group.strip() in _CANONICAL_GROUPS

    def persist_batch(
        self,
        import_batch_id: str,
        platform: str,
        period_start: datetime | None,
        period_end: datetime | None,
        records: Sequence[VariantRecord],
    ) -> PersistResult:
        """Persists normalized records under one import batch.

        Phase 7 boundary (DevelopmentFeedback20260826): every NON-DASH record
        is persisted. On-grid rows carry ``is_reported = True``; off-grid
        variants (standalone 'tidak boleh ecer', 'free gift', etc.) and
        non-catalog product groups carry ``is_reported = False`` and are
        surfaced via Query G / the 'Tidak Terlaporkan S/T' sheets -- never a
        report figure. Only dash/empty-variant parent rows within catalog
        groups are dropped, and they are tallied in ``skipped_dash_variant``.
        Report keys are stored stripped so the grid left-join matches exactly.
        """
        unresolved = SkippedTally()
        dash = SkippedTally()
        off_grid = SkippedTally()
        reported = SkippedTally()
        inserted: list[TransactionItem] = []

        for rec in records:
            product_group = rec.product_group.strip()
            clean_variant = rec.clean_variant.strip()

            # Priority preserved from the pre-Phase-7 boundary: a non-catalog
            # product group is classified BEFORE the dash/empty rule, so its
            # (usually '-') variant row persists as an unreported listing
            # instead of being silently dropped.
            if product_group not in _CANONICAL_GROUPS:
                unresolved = SkippedTally(
                    count=unresolved.count + 1,
                    qty=unresolved.qty + rec.qty_sold,
                    revenue=unresolved.revenue + rec.revenue,
                )
                is_reported = False
            elif clean_variant in ("-", ""):
                dash = SkippedTally(
                    count=dash.count + 1,
                    qty=dash.qty + rec.qty_sold,
                    revenue=dash.revenue + rec.revenue,
                )
                continue
            else:
                # Off-grid variant: a catalog group with a variant label the
                # grid does not contain. The grid LEFT JOIN would silently
                # absorb it, so it is classified unreported here (R1).
                grid_keys = _PRODUK2_GRID_KEYS if rec.is_cross_bundling else _PRODUK_GRID_KEYS
                if (product_group, clean_variant) not in grid_keys:
                    off_grid = SkippedTally(
                        count=off_grid.count + 1,
                        qty=off_grid.qty + rec.qty_sold,
                        revenue=off_grid.revenue + rec.revenue,
                    )
                    is_reported = False
                else:
                    is_reported = True

            if is_reported:
                reported = SkippedTally(
                    count=reported.count + 1,
                    qty=reported.qty + rec.qty_sold,
                    revenue=reported.revenue + rec.revenue,
                )

            inserted.append(
                TransactionItem(
                    id=str(uuid4()),
                    import_batch_id=import_batch_id,
                    platform=platform,
                    period_start=period_start,
                    period_end=period_end,
                    product_group=product_group,
                    raw_variant=rec.raw_variant,
                    clean_variant=clean_variant,
                    is_bundling=rec.is_bundling,
                    is_cross_bundling=rec.is_cross_bundling,
                    case_color=rec.case_color,
                    sku=rec.sku,
                    raw_product=rec.raw_product,
                    qty_sold=rec.qty_sold,
                    revenue=rec.revenue,
                    is_reported=is_reported,
                )
            )

        self._session.add_all(inserted)
        self._session.flush()

        return PersistResult(
            import_batch_id=import_batch_id,
            inserted_count=len(inserted),
            inserted_reported=reported,
            persisted_unreported=unresolved + off_grid,
            unreported_off_grid=off_grid,
            unreported_unresolved_group=unresolved,
            skipped_dash_variant=dash,
        )

    # ------------------------------------------------------------------
    # Query A: Variant-level analytics
    # ------------------------------------------------------------------

    def variant_analytics(
        self,
        import_batch_id: str,
        is_cross_bundling: bool | int = 0,
        is_bundling: bool | int | None = None,
    ) -> list[dict[str, Any]]:
        """Per-(product_group, clean_variant) totals with 0-1 unit share.

        ``is_bundling`` (0 = Single, 1 = Bundling, None = both) narrows the
        subset inside both the CTE and the outer query so contribution ratios
        are computed within the selected partition.
        """
        rows = (
            self._session.execute(
                text(_QUERY_A_VARIANT_ANALYTICS),
                {
                    "batch_id": import_batch_id,
                    "is_cross_bundling": int(bool(is_cross_bundling)),
                    "is_bundling": self._coerce_bundling_flag(is_bundling),
                },
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Query B: Master product group summary
    # ------------------------------------------------------------------

    def product_group_summary(
        self,
        import_batch_id: str,
        is_cross_bundling: bool | int = 0,
        is_bundling: bool | int | None = None,
    ) -> list[dict[str, Any]]:
        """Group-level rollup with share against grand total quantity.

        ``is_bundling`` narrows the subset inside both the CTE and the outer
        query so ``contribution_ratio`` is computed within the partition.
        """
        rows = (
            self._session.execute(
                text(_QUERY_B_PRODUCT_GROUP_SUMMARY),
                {
                    "batch_id": import_batch_id,
                    "is_cross_bundling": int(bool(is_cross_bundling)),
                    "is_bundling": self._coerce_bundling_flag(is_bundling),
                },
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    @staticmethod
    def _coerce_bundling_flag(value: bool | int | None) -> int | None:
        """Normalizes the optional ``is_bundling`` filter for SQLite binding."""
        return None if value is None else int(bool(value))

    # ------------------------------------------------------------------
    # Query G: Persisted unreported breakdown
    # ------------------------------------------------------------------

    def unreported_analytics(self, import_batch_id: str) -> list[dict[str, Any]]:
        """Query G: persisted non-reportable entries for a batch.

        Returns ``is_reported = 0`` rows aggregated per
        ``(product_group, clean_variant, raw_variant, raw_product)`` -- off-grid
        variants and non-catalog product groups -- with their qty/revenue for
        the dashboard and the 'Tidak Terlaporkan S/T' export sheets. Rows carry
        their raw product/variant labels so the original spreadsheet row stays
        traceable.
        """
        rows = (
            self._session.execute(
                text(_QUERY_G_UNREPORTED),
                {"batch_id": import_batch_id},
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Query C: Multi-platform / date-range aggregation
    # ------------------------------------------------------------------

    def multi_platform_aggregation(
        self,
        platform: str | None = None,
        start_date: datetime | date | None = None,
        end_date: datetime | date | None = None,
        is_cross_bundling: bool | int | None = None,
    ) -> list[dict[str, Any]]:
        """Cross-batch aggregation with optional platform/date/cross filters."""
        params: dict[str, Any] = {
            "platform": platform,
            "start_date": self._coerce_start_bound(start_date),
            "end_date": self._coerce_end_bound(end_date),
            "is_cross_bundling": (None if is_cross_bundling is None else int(bool(is_cross_bundling))),
        }
        rows = self._session.execute(text(_QUERY_C_MULTI_PLATFORM), params).mappings().all()
        return [dict(row) for row in rows]

    @staticmethod
    def _coerce_start_bound(value: datetime | date | None) -> datetime | None:
        """Normalizes a start bound to an inclusive midnight datetime for SQLite."""
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, time.min)
        return value

    @staticmethod
    def _coerce_end_bound(value: datetime | date | None) -> datetime | None:
        """Normalizes an end bound to an inclusive upper bound for SQLite.

        SQLAlchemy's DateTime stores microsecond-suffixed ISO text
        ('...23:59:59.000000'); a bare end-of-day bound ('...23:59:59')
        compares lexicographically below it and silently excludes the intended
        day (R9). Both a bare ``date`` and an exact 23:59:59 ``datetime``
        therefore resolve to 23:59:59.999999.
        """
        if isinstance(value, datetime):
            if value.time() == time(23, 59, 59):
                return value.replace(microsecond=999999)
            return value
        if isinstance(value, date):
            return datetime.combine(value, time(23, 59, 59, 999999))
        return value

    # ------------------------------------------------------------------
    # Query D: Batch history & upload overview
    # ------------------------------------------------------------------

    def batch_history(self) -> list[dict[str, Any]]:
        """Overview of every persisted batch, newest first.

        ``MIN(period_start)`` / ``MAX(period_end)`` / ``MIN(created_at)`` come
        back as raw SQLite ISO strings over ``text()``; they are parsed back
        to datetimes so callers get the ORM column types.
        """
        rows = self._session.execute(text(_QUERY_D_BATCH_HISTORY)).mappings().all()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            for key in ("period_start", "period_end", "created_at"):
                value = item.get(key)
                if isinstance(value, str):
                    item[key] = datetime.fromisoformat(value)
            result.append(item)
        return result

    # ------------------------------------------------------------------
    # Query E: Batch deletion
    # ------------------------------------------------------------------

    def delete_batch(self, import_batch_id: str) -> int:
        """Deletes all rows for a batch; returns the deleted row count."""
        result = self._session.execute(text(_QUERY_E_DELETE_BATCH), {"batch_id": import_batch_id})
        assert isinstance(result, CursorResult)
        return int(result.rowcount or 0)

    # ------------------------------------------------------------------
    # Left-join grid population
    # ------------------------------------------------------------------

    def populate_grid(
        self,
        import_batch_id: str,
        is_cross_bundling: bool | int = 0,
        grid: Sequence[GridRow] | None = None,
        include_case_colors: bool = False,
    ) -> list[dict[str, Any]]:
        """Left-joins catalog grid rows onto persisted aggregates.

        Every grid row is preserved; variants with no sales coalesce to
        qty 0 / revenue 0 while keeping group presence. Join keys are
        rtrim()-normalized on both sides (rule 7).

        ``include_case_colors=True`` (Produk 2 export option) switches to the
        per-case-colour aggregation path: grid rows carrying a ``case_color``
        are matched to reported rows by their plain ``match_variant`` plus that
        case colour, colour-less rows land on the plain catch-all rows, and the
        default SQL path is bypassed (its 5-field VALUES join cannot express
        the case-aware key).
        """
        grid_rows = list(grid) if grid is not None else list(generate_full_produk_grid())
        if not grid_rows:
            return []

        is_cross = int(bool(is_cross_bundling))
        if include_case_colors and is_cross == 1:
            return self._populate_grid_case_colors(import_batch_id, grid_rows)

        # Host-parameter ceiling: SQLite binds at most 32,766 parameters, and
        # each grid row binds 5 (product_group, clean_variant, is_bundling,
        # is_cross_bundling, expected_label) plus 2 fixed batch params. The
        # Produk 2 grid (690 rows -> 3,452 params) has ~9x headroom; the
        # ceiling lands at ~6,550 grid rows. Chunk the VALUES list if the
        # catalog ever approaches that size (R10).

        placeholders = ", ".join(
            f"(:p{i}, :p{i + 1}, :p{i + 2}, :p{i + 3}, :p{i + 4})" for i in range(0, len(grid_rows) * 5, 5)
        )
        params: dict[str, Any] = {
            "batch_id": import_batch_id,
            "is_cross_bundling": is_cross,
        }
        for i, row in enumerate(grid_rows):
            params[f"p{i * 5 + 0}"] = row.product_group
            params[f"p{i * 5 + 1}"] = row.clean_variant
            params[f"p{i * 5 + 2}"] = int(row.is_bundling)
            params[f"p{i * 5 + 3}"] = int(row.is_cross_bundling)
            params[f"p{i * 5 + 4}"] = row.expected_label

        sql = _GRID_LEFT_JOIN_TEMPLATE.format(placeholders=placeholders)
        rows = self._session.execute(text(sql), params).mappings().all()
        return [dict(row) for row in rows]

    def _populate_grid_case_colors(
        self, import_batch_id: str, grid_rows: Sequence[GridRow]
    ) -> list[dict[str, Any]]:
        """Attaches reported cross rows onto the per-case-colour Produk 2 grid.

        Aggregates stored rows at ``(product_group, clean_variant, case_color)``
        grain (Query H) and matches each grid row by its plain match base:
        ``GridRow.match_variant`` when present (per-colour row), else its own
        ``clean_variant``; ``case_color`` separates the colour rows from the
        plain catch-all row. Unmatched grid rows emit literal zeros.
        """
        rows = (
            self._session.execute(
                text(_QUERY_CASE_COLOR_CROSS_AGG),
                {"batch_id": import_batch_id},
            )
            .mappings()
            .all()
        )
        aggregates: dict[tuple[str, str, str], tuple[int, int]] = {}
        for row in rows:
            key = (row["product_group"], row["clean_variant"].strip(), row["case_color"].strip())
            aggregates[key] = (int(row["total_qty"]), int(row["total_revenue"]))

        result: list[dict[str, Any]] = []
        for gr in grid_rows:
            group = gr.product_group.rstrip()
            match_variant = (gr.match_variant or gr.clean_variant).rstrip()
            case_key = "" if gr.case_color is None else gr.case_color.rstrip()
            total_qty, total_revenue = aggregates.get((group, match_variant, case_key), (0, 0))
            result.append(
                {
                    "product_group": group,
                    "clean_variant": gr.clean_variant.rstrip(),
                    "is_bundling": gr.is_bundling,
                    "is_cross_bundling": gr.is_cross_bundling,
                    "expected_label": gr.expected_label.rstrip(),
                    "case_color": gr.case_color,
                    "total_qty": total_qty,
                    "total_revenue": total_revenue,
                }
            )
        return result

    # ------------------------------------------------------------------
    # Mapping templates (Query F)
    # ------------------------------------------------------------------

    def get_mapping_template(self, signature_hash: str) -> dict[str, Any] | None:
        """Loads a cached mapping template by header signature hash."""
        row = (
            self._session.execute(
                text(_QUERY_F_TEMPLATE_LOOKUP),
                {"signature_hash": signature_hash},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def save_mapping_template(
        self,
        platform_name: str,
        header_signature_hash: str,
        column_mapping_json: str,
        cleaning_rules_json: str | None = None,
        parent_row_rule_json: str | None = None,
    ) -> str:
        """Upserts a mapping template by header signature hash; returns its id."""
        existing_id = self._session.execute(
            text("SELECT id FROM mapping_templates WHERE header_signature_hash = :signature_hash"),
            {"signature_hash": header_signature_hash},
        ).scalar_one_or_none()

        if existing_id is None:
            template_id = str(uuid4())
            self._session.add(
                MappingTemplate(
                    id=template_id,
                    platform_name=platform_name,
                    header_signature_hash=header_signature_hash,
                    column_mapping_json=column_mapping_json,
                    cleaning_rules_json=cleaning_rules_json,
                    parent_row_rule_json=parent_row_rule_json,
                )
            )
            self._session.flush()
            return template_id

        self._session.execute(
            text(
                "UPDATE mapping_templates SET platform_name = :platform_name, "
                "column_mapping_json = :column_mapping_json, cleaning_rules_json = :cleaning_rules_json, "
                "parent_row_rule_json = :parent_row_rule_json WHERE header_signature_hash = :signature_hash"
            ),
            {
                "platform_name": platform_name,
                "column_mapping_json": column_mapping_json,
                "cleaning_rules_json": cleaning_rules_json,
                "parent_row_rule_json": parent_row_rule_json,
                "signature_hash": header_signature_hash,
            },
        )
        return str(existing_id)
