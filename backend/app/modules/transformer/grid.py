"""Declarative fixed-grid generator for RAE Smart Report."""

from __future__ import annotations

from itertools import combinations
from typing import Final

from app.domain.catalog import (
    CASE_COLORS,
    CROSS_PAIRABLE_FAMILY_NAMES,
    FAMILIES,
    FAMILY_BY_NAME,
)
from app.domain.models import GridRow

__all__ = [
    "PRODUK2_GROUP_ORDER",
    "FixedGridGenerator",
    "generate_cross_family_grid",
    "generate_full_produk2_grid",
    "generate_full_produk_grid",
    "generate_intra_family_grid",
]


class FixedGridGenerator:
    """Generates canonical report grids based on domain catalog sequence definitions."""

    def __init__(self) -> None:
        self._families = FAMILIES
        self._family_by_name = FAMILY_BY_NAME

    def generate_intra_family_grid(self, family_name: str) -> list[GridRow]:
        """Generates single-shade rows followed by intra-family bundle rows for a product family.

        - Singles follow ``family.order_for_singles()`` (or ``explicit_groups`` for Lipcare).
        - Pairs follow ``family.order_for_pairs()`` via upper-triangle C(n, 2) combinations,
          or literal ``explicit_bundle_labels`` for OTG and Lipcare.
        """
        family = self._family_by_name.get(family_name)
        if not family:
            return []

        rows: list[GridRow] = []

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
        bundle_group_name = "Bundling Lipcare" if family.name == "Lipcare" else f"Bundling {family.name}"

        if family.explicit_bundle_labels:
            pair_labels = list(family.explicit_bundle_labels)
        else:
            pairs_order = family.order_for_pairs()
            pair_labels = [family.bundle_label(s1, s2) for s1, s2 in combinations(pairs_order, 2)]

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
    ) -> list[GridRow]:
        """Generates cross-category bundling (Bundling Silang) combinations.

        - Plain cross-family: n x m rows, joined with ', ' (e.g. 'Active, Over Cute').
        - Tinted Jelly Balm cross-family with ``include_case_colors=True``: each
          shade pair emits its plain (case-colour-free) catch-all row PLUS one
          row per enumerated case colour, joined with ' + ' then ', ' before the
          colour (e.g. 'Bunny Pink, Over React' followed by
          'Bunny Pink + Over React, Fizzy Pop'). The catch-all row keeps any
          case-less sale attributable to the pair inside its group totals.
          Case colour is not a reporting axis by default -- this is the opt-in
          Produk 2 export view only, and it is a no-op for pairs that do not
          involve Tinted Jelly Balm.
        """
        f1 = self._family_by_name.get(family_name_1)
        f2 = self._family_by_name.get(family_name_2)
        if not f1 or not f2:
            return []

        group_name = f"Bundling {f1.name} & {f2.name}"
        left = f1.order_for_cross()
        right = f2.order_for_cross()
        rows: list[GridRow] = []

        # Case colours belong to the Tinted Jelly Balm SKU; the per-colour
        # expansion is only meaningful (and only ever requested) for pairs that
        # include it.
        expand_cases = include_case_colors and (
            f1.name == "Tinted Jelly Balm" or f2.name == "Tinted Jelly Balm"
        )

        if not expand_cases:
            for s1 in left:
                for s2 in right:
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

        for s1 in left:
            for s2 in right:
                # Case-less catch-all: matches stored records whose variant
                # carried no case colour (plain label, case_color NULL).
                plain = f"{s1}, {s2}".rstrip()
                rows.append(
                    GridRow(
                        product_group=group_name.rstrip(),
                        clean_variant=plain,
                        is_bundling=True,
                        is_cross_bundling=True,
                        expected_label=plain,
                        case_color=None,
                    )
                )
                for case_color in CASE_COLORS:
                    label = f"{s1} + {s2}, {case_color}".rstrip()
                    rows.append(
                        GridRow(
                            product_group=group_name.rstrip(),
                            clean_variant=label,
                            is_bundling=True,
                            is_cross_bundling=True,
                            expected_label=label,
                            case_color=case_color.rstrip(),
                            # Records are stored with the case-colour-free
                            # label; the colour lives in their case_color
                            # column, so the join base is the plain pair label.
                            match_variant=plain,
                        )
                    )

        return rows

    def generate_full_produk_grid(self) -> list[GridRow]:
        """Generates all 181 declarative rows for the primary 'Produk' sheet (singles + intra bundles)."""
        rows: list[GridRow] = []
        for family in self._families:
            rows.extend(self.generate_intra_family_grid(family.name))
        return rows


def generate_intra_family_grid(family_name: str) -> list[GridRow]:
    """Helper to generate intra-family grid using default generator."""
    return FixedGridGenerator().generate_intra_family_grid(family_name)


def generate_cross_family_grid(
    family_name_1: str,
    family_name_2: str,
    include_case_colors: bool = False,
) -> list[GridRow]:
    """Helper to generate cross-family grid using default generator."""
    return FixedGridGenerator().generate_cross_family_grid(family_name_1, family_name_2, include_case_colors)


def generate_full_produk_grid() -> list[GridRow]:
    """Helper to generate full 181-row Produk sheet grid."""
    return FixedGridGenerator().generate_full_produk_grid()


def generate_full_produk2_grid(include_case_colors: bool = False) -> list[GridRow]:
    """Generates all cross-family rows for the 'Produk 2' sheets (15 groups).

    Iterates ``combinations(CROSS_PAIRABLE_FAMILY_NAMES, 2)`` so the per-group
    names match the normalizer's emission order (``Bundling {a.name} &
    {b.name}``), and so each group's rows follow the families' ``cross_order``
    token sequences. Lipcare is deliberately absent: it is a Produk-sheet
    family only and never pairs in the Bundling Silang catalog.

    ``include_case_colors=True`` requests the opt-in per-case-colour expansion
    for the five Tinted Jelly Balm cross-family groups (plain catch-all row per
    shade pair plus one row per enumerated case colour). Non-TJB groups are
    unaffected.
    """
    rows: list[GridRow] = []
    for a_name, b_name in combinations(CROSS_PAIRABLE_FAMILY_NAMES, 2):
        rows.extend(generate_cross_family_grid(a_name, b_name, include_case_colors))
    return rows


# Canonical 15 cross-family groups in emission order (C(6, 2) = 15 pairs).
# Lipcare never participates in the Bundling Silang catalog.
PRODUK2_GROUP_ORDER: Final[tuple[str, ...]] = tuple(
    f"Bundling {a_name} & {b_name}"
    for a_name, b_name in combinations(CROSS_PAIRABLE_FAMILY_NAMES, 2)
)
