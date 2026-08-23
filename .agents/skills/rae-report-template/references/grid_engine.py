"""Combinatorial grid generator and same-shade fold-back engine.

Generates the fixed 3D declarative grid for executive sales reports:
1. Intra-family singles and C(n, 2) pair combinations.
2. Cross-family n x m and n x m x 3 (case colors) combinations.
3. Same-shade fold-back arithmetic (x2 qty, x1 rev, aggregate duplicates).
"""

from typing import List, Dict, Any, Tuple, Optional
from itertools import combinations, product

try:
    from .catalog_spec import (
        FAMILIES, FAMILY_BY_NAME, CASE_COLORS, OTG_INTRA_BUNDLE_LABELS,
    )
except (ImportError, ValueError):
    from catalog_spec import (
        FAMILIES, FAMILY_BY_NAME, CASE_COLORS, OTG_INTRA_BUNDLE_LABELS,
    )


def generate_intra_family_grid(family_name: str) -> List[Dict[str, Any]]:
    """
    Generates single shade rows followed by C(n, 2) pair bundle rows.

    Singles follow ``order_for_singles()``; pairs follow ``order_for_pairs()``.
    These are DIFFERENT sequences -- see the catalog_spec module docstring.
    Example for Glow Up Tint (11 shades):
    - 11 single shades
    - 55 bundle pairs (Active + Brave, Active + Cheerful, ...)
    Total: 66 rows.

    'Over The Glaze' pairs come from the literal OTG_INTRA_BUNDLE_LABELS
    because that family is hand-ordered in the reference workbook and does not
    follow the upper-triangle rule.
    """
    family = FAMILY_BY_NAME.get(family_name)
    if not family:
        return []

    rows: List[Dict[str, Any]] = []

    # 1. Singles -- singles order (largely alphabetical)
    for shade in family.order_for_singles():
        rows.append({
            "product_group": family.name,
            "clean_variant": shade,
            "is_bundling": False,
            "is_cross_bundling": False,
            "expected_label": shade,
        })

    # 2. Intra-family pairs: strict upper triangle over DISPLAY order
    bundle_group_name = f"Bundling {family.name}"

    if family.name == "Over The Glaze":
        pair_labels = list(OTG_INTRA_BUNDLE_LABELS)
    else:
        pair_labels = [
            family.bundle_label(s1, s2)
            for s1, s2 in combinations(family.order_for_pairs(), 2)
        ]

    for label in pair_labels:
        rows.append({
            "product_group": bundle_group_name,
            "clean_variant": label,
            "is_bundling": True,
            "is_cross_bundling": False,
            "expected_label": label,
        })

    return rows


def generate_cross_family_grid(
    family_name_1: str,
    family_name_2: str,
    include_case_colors: bool = False
) -> List[Dict[str, Any]]:
    """
    Generates cross-category bundling (Bundling Silang) combinations:
    - Standard: n x m rows (e.g. 11 x 6 = 66 rows for GUT & OTG)
    - With Case Colors: n x m x 3 rows (e.g. 6 x 6 x 3 = 108 rows for OTG & TJB)

    Token order comes from ``order_for_cross()``, which differs from BOTH the
    singles and the intra-family pair orderings.

    Separators: plain cross-family pairs join with ``", "`` (e.g.
    'Active, Over Cute'). With case colours the two shades join with ``" + "``
    and the colour follows after ``", "`` (e.g.
    'Over Cute + Bunny Pink, Fizzy Pop').
    """
    f1 = FAMILY_BY_NAME.get(family_name_1)
    f2 = FAMILY_BY_NAME.get(family_name_2)
    if not f1 or not f2:
        return []

    group_name = f"Bundling {f1.name} & {f2.name}"
    left = f1.order_for_cross()
    right = f2.order_for_cross()
    rows: List[Dict[str, Any]] = []

    if include_case_colors:
        for s1, s2, case_color in product(left, right, CASE_COLORS):
            label = f"{s1} + {s2}, {case_color}"
            rows.append({
                "product_group": group_name,
                "clean_variant": label,
                "is_bundling": True,
                "is_cross_bundling": True,
                "case_color": case_color,
                "expected_label": label,
            })
    else:
        for s1, s2 in product(left, right):
            label = f"{s1}, {s2}"
            rows.append({
                "product_group": group_name,
                "clean_variant": label,
                "is_bundling": True,
                "is_cross_bundling": True,
                "case_color": None,
                "expected_label": label,
            })

    return rows


def fold_back_same_shade_bundles(
    raw_bundle_rows: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Executes the Same-Shade 2-Pack Fold-Back rule:
    - When an intra-family bundle consists of two identical shades (e.g. 'Dynamic, 05. Dynamic'),
      it cannot occupy a C(n, 2) cell.
    - Rule: Revenue is added as-is (x1); Quantity is doubled (x2).
    - Aggregates duplicate rows if multiple same-shade lines exist.
    - Raises ValueError if N > 2 identical items are encountered.
    """
    folded: Dict[str, Dict[str, Any]] = {}

    for row in raw_bundle_rows:
        shade = row["canonical_shade"]
        multiplicity = row.get("multiplicity", 2)
        
        if multiplicity > 2:
            raise ValueError(f"Encountered same-shade bundle with N={multiplicity} (> 2) for shade '{shade}'. Manual review required.")

        raw_qty = row.get("qty_sold", 0)
        raw_rev = row.get("revenue", 0)

        if shade not in folded:
            folded[shade] = {
                "canonical_shade": shade,
                "qty_to_add": raw_qty * 2,
                "revenue_to_add": raw_rev,
            }
        else:
            folded[shade]["qty_to_add"] += raw_qty * 2
            folded[shade]["revenue_to_add"] += raw_rev

    return folded
