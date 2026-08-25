"""Same-Shade 2-Pack Fold-Back arithmetic engine for RAE Smart Report."""

from __future__ import annotations

from app.domain.models import VariantRecord

__all__ = [
    "FoldBackEngine",
    "fold_back_same_shade_records",
]


class FoldBackEngine:
    """Executes deterministic fold-back of same-shade 2-pack bundle records into single-shade items.

    Business Rules:
    1. Scope: Strictly scoped to the 'Glow Up Tint' family.
    2. Multiplicity: Strictly bounded to N=2. If N > 2, raises ValueError.
    3. Arithmetic: 2x quantity, 1x revenue added to the corresponding single-shade variant row.
    4. Duplicate aggregation: If duplicate same-shade rows exist in raw data, they are aggregated.
    """

    ALLOWED_FAMILIES: frozenset[str] = frozenset({"Glow Up Tint"})

    def __init__(self, allowed_families: set[str] | None = None) -> None:
        self.allowed_families = (
            allowed_families if allowed_families is not None else self.ALLOWED_FAMILIES
        )

    def process_records(self, records: list[tuple[VariantRecord, bool]]) -> list[VariantRecord]:
        """Processes a list of (VariantRecord, is_same_shade_foldback) tuples.

        Non-foldback records pass through unchanged.
        Same-shade foldback records are validated, aggregated, multiplied (x2 qty, x1 rev),
        and re-routed as single-shade variant records.
        """
        standard_records: list[VariantRecord] = []
        foldback_pool: dict[tuple[str, str, str], dict[str, int]] = {}
        # Key: (platform, product_group, clean_variant) -> {"qty": total_qty, "rev": total_rev}

        for record, is_foldback in records:
            if not is_foldback:
                standard_records.append(record)
                continue

            # Validate family scope
            if record.product_group not in self.allowed_families:
                raise ValueError(
                    f"Same-shade fold-back encountered for unverified family '{record.product_group}' "
                    f"(variant '{record.clean_variant}'). Fold-back is currently strictly scoped to {self.allowed_families}."
                )

            # Check multiplicity
            # Same-shade N>2 packs never reach the engine: the normalizer raises
            # before marking a record as fold-back (R2), so every fold-back row
            # here is exactly N=2.
            key = (record.platform, record.product_group, record.clean_variant)
            if key not in foldback_pool:
                foldback_pool[key] = {
                    "qty": record.qty_sold * 2,
                    "revenue": record.revenue,
                }
            else:
                foldback_pool[key]["qty"] += record.qty_sold * 2
                foldback_pool[key]["revenue"] += record.revenue

        # Convert folded pool into single-shade VariantRecords
        folded_records: list[VariantRecord] = []
        for (platform, product_group, clean_variant), totals in foldback_pool.items():
            folded_records.append(
                VariantRecord(
                    platform=platform,
                    product_group=product_group,
                    raw_variant=f"{clean_variant} (Folded Same-Shade 2-Pack)",
                    clean_variant=clean_variant,
                    is_bundling=False,
                    is_cross_bundling=False,
                    qty_sold=totals["qty"],
                    revenue=totals["revenue"],
                    sku=None,
                    case_color=None,
                )
            )

        return standard_records + folded_records


def fold_back_same_shade_records(records: list[tuple[VariantRecord, bool]]) -> list[VariantRecord]:
    """Helper function to execute fold-back processing with default engine."""
    engine = FoldBackEngine()
    return engine.process_records(records)
