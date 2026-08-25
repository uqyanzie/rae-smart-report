"""Regression tests for master product catalog, orderings, Lipcare structure, and shade resolution."""

import pytest
from app.domain.catalog import (
    CASE_COLORS,
    FAMILIES,
    FAMILY_BY_NAME,
    LIPCARE_INTRA_BUNDLE_LABELS,
    OTG_INTRA_BUNDLE_LABELS,
    PRODUK_GROUP_ORDER,
    resolve_family,
    resolve_shade,
)


def test_family_count_and_names():
    """Verifies that all 7 master product families are loaded."""
    expected_names = [
        "Glow Up Tint",
        "Swipe To Glow",
        "Power Frosted Velvet Matte",
        "Tinted Jelly Balm",
        "The Bloom Perfect Matte Lipstick",
        "Over The Glaze",
        "Lipcare",
    ]
    assert [f.name for f in FAMILIES] == expected_names
    assert len(FAMILY_BY_NAME) == 7


def test_glow_up_tint_orderings():
    """
    Verifies Glow Up Tint sequences as strictly ordered lists.
    CRITICAL: In display_order and cross_order, Strong (09) must precede Happy (10).
    """
    gut = FAMILY_BY_NAME["Glow Up Tint"]

    expected_singles = [
        "Active", "Brave", "Cheerful", "Confident", "Dynamic", "Energic",
        "Gorgeous", "Happy", "Incredible", "Joyful", "Strong",
    ]
    expected_display = [
        "Active", "Brave", "Cheerful", "Confident", "Dynamic", "Energic",
        "Gorgeous", "Strong", "Happy", "Incredible", "Joyful",
    ]

    assert list(gut.order_for_singles()) == expected_singles
    assert list(gut.order_for_pairs()) == expected_display
    assert list(gut.order_for_cross()) == expected_display
    assert gut.order_for_pairs().index("Strong") < gut.order_for_pairs().index("Happy")


def test_swipe_to_glow_orderings():
    """Verifies Swipe To Glow singles vs display/cross sequences."""
    stg = FAMILY_BY_NAME["Swipe To Glow"]

    expected_singles = ["Brunch", "Date", "Holiday", "Party", "School", "Work"]
    expected_display = ["Date", "Work", "School", "Brunch", "Holiday", "Party"]

    assert list(stg.order_for_singles()) == expected_singles
    assert list(stg.order_for_pairs()) == expected_display
    assert list(stg.order_for_cross()) == expected_display


def test_power_frosted_velvet_matte_orderings_and_short_labels():
    """Verifies Power Frosted orderings and short-name bundle formatting."""
    pfvm = FAMILY_BY_NAME["Power Frosted Velvet Matte"]

    expected_singles = [
        "Ambition Power", "Classy Power", "Heart Power",
        "Honest Power", "Kind Power", "Smart Power",
    ]
    expected_display = [
        "Kind Power", "Honest Power", "Classy Power",
        "Smart Power", "Heart Power", "Ambition Power",
    ]

    assert list(pfvm.order_for_singles()) == expected_singles
    assert list(pfvm.order_for_pairs()) == expected_display
    assert list(pfvm.order_for_cross()) == expected_display

    # Bundle label drops the " Power" suffix
    assert pfvm.bundle_label("Kind Power", "Honest Power") == "Kind + Honest"
    assert pfvm.bundle_label("Ambition Power", "Smart Power") == "Ambition + Smart"


def test_tinted_jelly_balm_and_case_colors():
    """Verifies Tinted Jelly Balm shades and 3D case colors."""
    tjb = FAMILY_BY_NAME["Tinted Jelly Balm"]
    expected_shades = [
        "Bunny Pink", "Wild Mauve", "Nudy Caramel",
        "Spill Nude", "Red Babe", "Hippie Rose",
    ]

    assert list(tjb.order_for_singles()) == expected_shades
    assert list(CASE_COLORS) == ["Fizzy Pop", "Sweetie Pop", "Cherry Pop"]


def test_the_bloom_lipstick_orderings():
    """Verifies The Bloom lipstick shade ordering."""
    bloom = FAMILY_BY_NAME["The Bloom Perfect Matte Lipstick"]
    expected_shades = ["Peony", "Gerbera", "Daisy", "Tulip", "Orchid", "Dahlia"]

    assert list(bloom.order_for_singles()) == expected_shades
    assert list(bloom.order_for_pairs()) == expected_shades
    assert list(bloom.order_for_cross()) == expected_shades


def test_over_the_glaze_explicit_bundles():
    """Verifies Over The Glaze literal 15 intra bundle labels."""
    otg = FAMILY_BY_NAME["Over The Glaze"]

    assert len(OTG_INTRA_BUNDLE_LABELS) == 15
    assert otg.explicit_bundle_labels == OTG_INTRA_BUNDLE_LABELS
    assert OTG_INTRA_BUNDLE_LABELS[0] == "Over Cute + Lovie"
    assert "Over React + Over Drama" in OTG_INTRA_BUNDLE_LABELS


def test_lipcare_multi_group_structure_and_bundles():
    """
    Verifies Lipcare custom architecture:
    - 3 canonical shades mapping to 3 distinct report groups.
    - 7 explicit bundle labels under Bundling Lipcare.
    """
    lipcare = FAMILY_BY_NAME["Lipcare"]

    assert list(lipcare.shades) == ["Lip Moist", "Lip Exfoliant", "Lip Sunscreen"]
    assert len(lipcare.explicit_groups) == 3
    assert lipcare.explicit_groups == (
        ("Lip Moist", "Lip Moist"),
        ("Lip Exfoliant", "Lip Exfoliant"),
        ("Lip Sunscreen", "Lip Sunscreen"),
    )

    assert len(LIPCARE_INTRA_BUNDLE_LABELS) == 7
    assert lipcare.explicit_bundle_labels == LIPCARE_INTRA_BUNDLE_LABELS
    expected_bundles = [
        "Lip Exfoliant (2pcs)",
        "Lip Exfoliant + Sunscreen",
        "Lip Moist (2pcs)",
        "Lip Moist + Exfoliant",
        "Lip Moist + Exfoliant+ Sunscreen",
        "Lip Moist + Sunscreen",
        "Lip Sunscreen (2pcs)",
    ]
    assert list(LIPCARE_INTRA_BUNDLE_LABELS) == expected_bundles


def test_produk_group_order_contains_16_groups():
    """Verifies that PRODUK_GROUP_ORDER contains exactly the 16 canonical groups in sequence."""
    assert len(PRODUK_GROUP_ORDER) == 16
    assert PRODUK_GROUP_ORDER == (
        "Glow Up Tint",
        "Bundling Glow Up Tint",
        "Swipe To Glow",
        "Bundling Swipe To Glow",
        "Power Frosted Velvet Matte",
        "Bundling Power Frosted Velvet Matte",
        "Tinted Jelly Balm",
        "Bundling Tinted Jelly Balm",
        "The Bloom Perfect Matte Lipstick",
        "Bundling The Bloom Perfect Matte Lipstick",
        "Over The Glaze",
        "Bundling Over The Glaze",
        "Lip Moist",
        "Lip Exfoliant",
        "Lip Sunscreen",
        "Bundling Lipcare",
    )


@pytest.mark.parametrize(
    "token, expected_family, expected_shade",
    [
        ("Active", "Glow Up Tint", "Active"),
        ("active", "Glow Up Tint", "Active"),
        ("cheerfull", "Glow Up Tint", "Cheerful"),
        ("joyfull", "Glow Up Tint", "Joyful"),
        ("energetic", "Glow Up Tint", "Energic"),
        ("gorgeus", "Glow Up Tint", "Gorgeous"),
        ("confidence", "Glow Up Tint", "Confident"),
        ("ov cute", "Over The Glaze", "Over Cute"),
        ("cute", "Over The Glaze", "Over Cute"),
        ("ov hype", "Over The Glaze", "Over Hype"),
        ("ov lovie", "Over The Glaze", "Over Lovie"),
        ("bunpink", "Tinted Jelly Balm", "Bunny Pink"),
        ("bun pink", "Tinted Jelly Balm", "Bunny Pink"),
        ("wildmauv", "Tinted Jelly Balm", "Wild Mauve"),
        ("hiprose", "Tinted Jelly Balm", "Hippie Rose"),
        ("nudy", "Tinted Jelly Balm", "Nudy Caramel"),
        ("spill", "Tinted Jelly Balm", "Spill Nude"),
        ("red", "Tinted Jelly Balm", "Red Babe"),
        ("ambition", "Power Frosted Velvet Matte", "Ambition Power"),
        ("smart", "Power Frosted Velvet Matte", "Smart Power"),
        ("moist", "Lipcare", "Lip Moist"),
        ("pdrn glow lip moist", "Lipcare", "Lip Moist"),
        ("exfo", "Lipcare", "Lip Exfoliant"),
        ("suns", "Lipcare", "Lip Sunscreen"),
        ("sun glow protect", "Lipcare", "Lip Sunscreen"),
        ("Peony", "The Bloom Perfect Matte Lipstick", "Peony"),
        ("Gerbera", "The Bloom Perfect Matte Lipstick", "Gerbera"),
    ],
)
def test_resolve_shade_aliases(token, expected_family, expected_shade):
    """Verifies fast shade token resolution and alias normalizations."""
    result = resolve_shade(token)
    assert result is not None
    family_name, canonical_shade = result
    assert family_name == expected_family
    assert canonical_shade == expected_shade


@pytest.mark.parametrize(
    "token, expected_family_name",
    [
        ("Glow Up Tint", "Glow Up Tint"),
        ("glow up tint", "Glow Up Tint"),
        ("liptint", "Glow Up Tint"),
        ("gut", "Glow Up Tint"),
        ("Swipe To Glow", "Swipe To Glow"),
        ("lipgloss", "Swipe To Glow"),
        ("stg", "Swipe To Glow"),
        ("Power Frosted Velvet Matte", "Power Frosted Velvet Matte"),
        ("pfvm", "Power Frosted Velvet Matte"),
        ("Tinted Jelly Balm", "Tinted Jelly Balm"),
        ("jelly balm", "Tinted Jelly Balm"),
        ("tjb", "Tinted Jelly Balm"),
        ("The Bloom Perfect Matte Lipstick", "The Bloom Perfect Matte Lipstick"),
        ("bloom", "The Bloom Perfect Matte Lipstick"),
        ("Over The Glaze", "Over The Glaze"),
        ("lip vinyl", "Over The Glaze"),
        ("otg", "Over The Glaze"),
        ("Lipcare", "Lipcare"),
        ("lip care", "Lipcare"),
    ],
)
def test_resolve_family(token, expected_family_name):
    """Verifies fast family name and alias resolution."""
    family = resolve_family(token)
    assert family is not None
    assert family.name == expected_family_name
