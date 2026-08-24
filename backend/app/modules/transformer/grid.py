"""Declarative fixed-grid generator for RAE Smart Report."""

from __future__ import annotations

from itertools import combinations, product
from typing import Final, List, Optional, Tuple

from app.domain.catalog import (
    CASE_COLORS,
    FAMILIES,
    FAMILY_BY_NAME,
    LIPCARE_INTRA_BUNDLE_LABELS,
    OTG_INTRA_BUNDLE_LABELS,
    PRODUK_GROUP_ORDER,
    Family,
)
from app.domain.models import GridRow

__all__ = [
    "FixedGridGenerator",
    "generate_intra_family_grid",
    "generate_cross_family_grid",
    "generate_full_produk_grid",
    "generate_full_produk2_grid",
    "PRODUK2_GROUP_ORDER",
]


class FixedGridGenerator:
    """Generates canonical report grids based on domain catalog sequence definitions."""

    def __init__(self) -> None:
        self._families = FAMILIES
        self._family_by_name = FAMILY_BY_NAME

    def generate_intra_family_grid(self, family_name: str) -> List[GridRow]:
        """Generates single-shade rows followed by intra-family bundle rows for a product family.

        - Singles follow ``family.order_for_singles()`` (or ``explicit_groups`` for Lipcare).
        - Pairs follow ``family.order_for_pairs()`` via upper-triangle C(n, 2) combinations,
          or literal ``explicit_bundle_labels`` for OTG and Lipcare.
        """
        family = self._family_by_name.get(family_name)
        if not family:
            return []

        rows: List[GridRow] = []

        # 1. Singles
        if family.explicit_groups:
            # Special case for Lipcare: each shade has its own group name
            for shade, group_name in family.explicit_groups:
                clean_lbl = shade.rstrip()
                rows.append(
                    GridRow(
                        product_group=group_name.rstrip(),
                        clean_variant=clean_lbl,
                        is_bundling=False,
                        is_cross_bundling=False,
                        expected_label=clean_lbl,
                    )
                )
        else:
            for shade in family.order_for_singles():
                clean_lbl = shade.rstrip()
                rows.append(
                    GridRow(
                        product_group=family.name.rstrip(),
                        clean_variant=clean_lbl,
                        is_bundling=False,
                        is_cross_bundling=False,
                        expected_label=clean_lbl,
                    )
                )

        # 2. Intra-family pairs
        bundle_group_name = (
            "Bundling Lipcare" if family.name == "Lipcare" else f"Bundling {family.name}"
        )

        if family.explicit_bundle_labels:
            pair_labels = list(family.explicit_bundle_labels)
        else:
            pairs_order = family.order_for_pairs()
            pair_labels = [
                family.bundle_label(s1, s2)
                for s1, s2 in combinations(pairs_order, 2)
            ]

        for label in pair_labels:
            clean_lbl = label.rstrip()
            rows.append(
                GridRow(
                    product_group=bundle_group_name.rstrip(),
                    clean_variant=clean_lbl,
                    is_bundling=True,
                    is_cross_bundling=False,
                    expected_label=clean_lbl,
                )
            )

        return rows

    def generate_cross_family_grid(
        self,
        family_name_1: str,
        family_name_2: str,
        include_case_colors: bool = False,
    ) -> List[GridRow]:
        """Generates cross-category bundling (Bundling Silang) combinations.

        - Plain cross-family: n x m rows, joined with ', ' (e.g. 'Active, Over Cute').
        - With Case Colors: n x m x 3 rows, joined with ' + ' then ', ' before case color
          (e.g. 'Over Cute + Bunny Pink, Fizzy Pop').
        """
        f1 = self._family_by_name.get(family_name_1)
        f2 = self._family_by_name.get(family_name_2)
        if not f1 or not f2:
            return []

        group_name = f"Bundling {f1.name} & {f2.name}"
        left = f1.order_for_cross()
        right = f2.order_for_cross()
        rows: List[GridRow] = []

        if include_case_colors:
            for s1, s2, case_color in product(left, right, CASE_COLORS):
                label = f"{s1} + {s2}, {case_color}".rstrip()
                rows.append(
                    GridRow(
                        product_group=group_name.rstrip(),
                        clean_variant=label,
                        is_bundling=True,
                        is_cross_bundling=True,
                        expected_label=label,
                        case_color=case_color.rstrip(),
                    )
                )
        else:
            for s1, s2 in product(left, right):
                label = f"{s1}, {s2}".rstrip()
                rows.append(
                    GridRow(
                        product_group=group_name.rstrip(),
                        clean_variant=label,
                        is_bundling=True,
                        is_cross_bundling=True,
                        expected_label=label,
                        case_color=None,
                    )
                )

        return rows

    def generate_full_produk_grid(self) -> List[GridRow]:
        """Generates all 181 declarative rows for the primary 'Produk' sheet (singles + intra bundles)."""
        rows: List[GridRow] = []
        for family in self._families:
            rows.extend(self.generate_intra_family_grid(family.name))
        return rows


def generate_intra_family_grid(family_name: str) -> List[GridRow]:
    """Helper to generate intra-family grid using default generator."""
    return FixedGridGenerator().generate_intra_family_grid(family_name)


def generate_cross_family_grid(
    family_name_1: str,
    family_name_2: str,
    include_case_colors: bool = False,
) -> List[GridRow]:
    """Helper to generate cross-family grid using default generator."""
    return FixedGridGenerator().generate_cross_family_grid(
        family_name_1, family_name_2, include_case_colors
    )


def generate_full_produk_grid() -> List[GridRow]:
    """Helper to generate full 181-row Produk sheet grid."""
    return FixedGridGenerator().generate_full_produk_grid()


def generate_full_produk2_grid() -> List[GridRow]:
    """Generates all cross-family rows for the 'Produk 2' sheets (21 groups).

    Iterates ``combinations(FAMILIES, 2)`` in canonical family order so the
    per-group names match the normalizer's emission order
    (``Bundling {a.name} & {b.name}``), and so each group's rows follow the
    families' ``cross_order`` token sequences.
    """
    rows: List[GridRow] = []
    for a, b in combinations(FAMILIES, 2):
        rows.extend(generate_cross_family_grid(a.name, b.name))
    return rows


# Canonical 21 cross-family groups in emission order (C(7, 2) = 21 pairs).
PRODUK2_GROUP_ORDER: Final[Tuple[str, ...]] = tuple(
    f"Bundling {a.name} & {b.name}" for a, b in combinations(FAMILIES, 2)
)
