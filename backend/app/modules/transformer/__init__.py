"""Transformer package for RAE Smart Report.

Provides variant normalization, same-shade fold-back arithmetic, and fixed-grid generation.
"""

from __future__ import annotations

from app.domain.models import VariantRecord
from app.modules.profiler.adapters import RawRecord
from app.modules.transformer.foldback import (
    FoldBackEngine,
    fold_back_same_shade_records,
)
from app.modules.transformer.grid import (
    PRODUK2_GROUP_ORDER,
    FixedGridGenerator,
    generate_cross_family_grid,
    generate_full_produk2_grid,
    generate_full_produk_grid,
    generate_intra_family_grid,
)
from app.modules.transformer.normalizer import (
    TransformationResult,
    TransformationWarning,
    VariantNormalizer,
    extract_case_color,
    strip_ordinal_prefix,
    strip_packaging_noise,
)

__all__ = [
    "PRODUK2_GROUP_ORDER",
    "FixedGridGenerator",
    "FoldBackEngine",
    "TransformationResult",
    "TransformationWarning",
    "VariantNormalizer",
    "extract_case_color",
    "fold_back_same_shade_records",
    "generate_cross_family_grid",
    "generate_full_produk2_grid",
    "generate_full_produk_grid",
    "generate_intra_family_grid",
    "strip_ordinal_prefix",
    "strip_packaging_noise",
    "transform_records",
]


def transform_records(
    raw_records: list[RawRecord],
    normalizer: VariantNormalizer | None = None,
    foldback_engine: FoldBackEngine | None = None,
) -> TransformationResult:
    """Transforms a batch of RawRecords into normalized VariantRecords with fold-back applied."""
    norm = normalizer or VariantNormalizer()
    fb = foldback_engine or FoldBackEngine()

    intermediate: list[tuple[VariantRecord, bool]] = []
    warnings: list[TransformationWarning] = []

    for raw in raw_records:
        rec, warn, is_foldback = norm.normalize_single(raw)
        if warn:
            warnings.append(warn)
        if rec:
            intermediate.append((rec, is_foldback))

    final_records = fb.process_records(intermediate)

    total_qty = sum(r.qty_sold for r in final_records)
    total_rev = sum(r.revenue for r in final_records)

    return TransformationResult(
        records=final_records,
        warnings=warnings,
        total_qty=total_qty,
        total_revenue=total_rev,
    )
